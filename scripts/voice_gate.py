"""Gate for the voice layer: the sentences that carry Ben's point of view.

``claim_verifier`` proves facts. Opinion cannot be proved, so it gets a different,
equally strict standard. A "take" or "voice" sentence survives only if:

* it rests on facts that themselves survived (``because`` ids),
* it adds no number or name beyond those facts,
* it makes no claim about what a named party privately thinks, wants, fears or knows,
* it makes no claim of first-hand experience unless a real note backs it,
* it is plainly framed as opinion or reaction, and
* an independent model pass finds it asserts no new fact and is a fair reading.

Everything that fails is deleted. The fact layer is verified by ``claim_verifier``
exactly as before, so adding voice never loosens factual accuracy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from claim_verifier import (
    FACT,
    Item,
    VerifiedDraft,
    check_nonfact_deterministic,
    verify_draft,
)
from readability import words

LLM = Callable[[str, str], str]

TAKE, VOICE, CONTEXT, BEN = "take", "voice", "context", "ben"
VOICE_KINDS = (TAKE, VOICE, CONTEXT, BEN)
MAX_TAKE_WORDS = 38
MAX_VOICE_WORDS = 26

_FIRST_PERSON = re.compile(r"\b(I|I'd|I'm|I'll|I've|my|me|we|our|let's)\b", re.I)
_OPINION_FRAME = re.compile(
    r"\b(I read|I think|I suspect|I'd|my read|my guess|my take|to me|looks like|reads like|feels like|"
    r"may be|might be|could be|probably|likely|suggests?|seems?)\b", re.I)
# Claims of things Ben did or saw. Only a real "ben" note may support these.
_EXPERIENCE = re.compile(
    r"\b(I|we)\s+(?:'ve\s+|have\s+|had\s+)?(?:called|phoned|visited|toured|walked|spoke|talked|met|sat|"
    r"interviewed|emailed|texted|got a call|heard from|was told|saw (?:the|it|this) (?:building|site|deal|term sheet))\b", re.I)
_MENTAL = re.compile(
    r"\b(wants?|wanted|needs?|needed|fears?|feared|hopes?|hoped|believes?|believed|thinks?|thought|knows?|knew|"
    r"worr(?:y|ies|ied)|desperate|panick\w*|secretly|intends?|intended|assum\w+|expects?|expected|"
    r"is betting|was betting|are betting|scared|nervous|decid\w+|chos[ae]|chooses?|refus\w+|declin\w+|avoids?|"
    r"prefers?|preferred|gives? up|giving up)\b", re.I)
# Loaded labels are claims in disguise ("distressed", "bargain"). They may appear only if a cited fact uses them.
_LOADED = re.compile(
    r"\b(distress\w*|desperat\w*|fire[- ]sale|bargain\w*|steal|overpa\w+|underpric\w+|undervalu\w+|overvalu\w+|cheap|"
    r"panic\w*|bail\w*out|zombie|toxic|doomed|collaps\w+|bubble|crisis|reckless\w*|predatory|vulture|shaky|struggling|"
    r"failing|lower basis|discount\w*|cut-rate|windfall|boom|bust)\b", re.I)
_SWEEPING = re.compile(
    r"\b(the market|the industry|investors|lenders|buyers|sellers|owners|landlords|developers)\b[^.]{0,60}"
    r"\b(are|is|will|always|never|all|most|every)\b", re.I)
_FRAMED = re.compile(r"\b(may|might|could|I read|I'd|I suspect|my guess|looks like|reads like|to me)\b", re.I)
_ROLE_MENTAL = re.compile(
    r"\b(the (?:previous|prior|former|old|seller|buyer|owner|lender|sponsor|borrower|firm|company))\b[^.]{0,40}"
    r"\b(decid\w+|chos[ae]|wants?|wanted|needs?|fears?|knew|knows?|refus\w+|avoid\w*|prefers?)\b", re.I)
_NAME =re.compile(r"(?<=[a-z,;] )(?!I(?:'[a-z]+)?\b)[A-Z][A-Za-z&'.-]{2,}")

RUBRIC_SYSTEM = (
    "You are the standards editor at a financial newspaper. You are shown verified FACTS and a list of "
    "OPINION or CONNECTIVE sentences written in a columnist's voice. You rule only on whether each one is "
    "acceptable under the rules. You never rewrite. Return JSON only."
)


@dataclass
class VoiceItem:
    id: str
    kind: str
    text: str
    quotes: list[str] = field(default_factory=list)
    because: list[str] = field(default_factory=list)
    ref: str = ""
    problems: list[str] = field(default_factory=list)
    verdict: str = ""
    issue: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems and self.verdict in ("", "ok")

    @property
    def reason(self) -> str:
        return "; ".join(self.problems) or self.issue or "rejected"


@dataclass
class VoiceDraft:
    title: str
    excerpt: str
    title_ok: bool
    excerpt_ok: bool
    paragraphs: list[tuple[str, list[VoiceItem]]]  # (role, kept items)
    rejected: list[VoiceItem]
    fact_count: int
    take_count: int
    voice_count: int
    fact_rejections: list[str]

    def text_paragraphs(self) -> list[str]:
        return [" ".join(i.text for i in items) for _, items in self.paragraphs if items]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def parse_voice_draft(draft: dict[str, Any]) -> list[tuple[str, list[VoiceItem]]]:
    paragraphs = draft.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError("draft has no paragraphs")
    out: list[tuple[str, list[VoiceItem]]] = []
    counter = 0
    for para in paragraphs:
        if not isinstance(para, dict) or not isinstance(para.get("sentences"), list):
            raise ValueError("paragraph must be an object with a sentences list")
        items = []
        for raw in para["sentences"]:
            if not isinstance(raw, dict):
                raise ValueError("sentence must be an object")
            counter += 1
            kind = str(raw.get("kind") or "").strip().lower()
            if kind not in (FACT, *VOICE_KINDS):
                raise ValueError(f"unknown sentence kind: {kind!r}")
            quotes = raw.get("quotes") or []
            quotes = [quotes] if isinstance(quotes, str) else quotes
            because = raw.get("because") or []
            because = [because] if isinstance(because, str) else because
            items.append(VoiceItem(
                id=str(raw.get("id") or f"s{counter}"), kind=kind, text=_norm(raw.get("text")),
                quotes=[str(q).strip() for q in quotes if str(q).strip()][:2],
                because=[str(b) for b in because if str(b).strip()], ref=str(raw.get("ref") or "").strip()))
        items = [i for i in items if i.text]
        if items:
            out.append((str(para.get("role") or "detail"), items))
    if not out:
        raise ValueError("draft has no sentences")
    return out


def _bank_text(bank: list[dict[str, Any]], ref: str) -> str:
    for entry in bank:
        if str(entry.get("id")) == ref:
            return str(entry.get("text") or "")
    return ""


_STOP = frozenset("""a an and are as at be been but by for from had has have he her his i if in into is it its of on or our
so than that the their them then there these they this those to was we were what when which who will with would you your""".split())


def _content_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text) if w.lower() not in _STOP and len(w) > 2}


def _not_derived(text: str, base: str, label: str) -> list[str]:
    """A context or note sentence may rephrase its bank entry but may not add a claim of its own."""
    new = _content_words(text) - _content_words(base)
    # Simple inflections of an entry word are not new content ("rise" for "rose" is, "rates" for "rate" is not).
    base_stems = {w[:5] for w in _content_words(base)}
    new = {w for w in new if w[:5] not in base_stems}
    return [f"adds content beyond its {label} entry: {', '.join(sorted(new)[:4])}"] if len(new) > 1 else []


def check_voice_item(
    item: VoiceItem, facts: dict[str, str], context: list[dict[str, Any]], notes: list[dict[str, Any]],
) -> None:
    """Deterministic rules for take / voice / context / ben. ``facts`` maps surviving fact id -> text."""
    text = item.text
    if item.kind == CONTEXT:
        base = _bank_text(context, item.ref)
        if not base:
            item.problems.append("context entry not found in the approved bank")
        else:
            probe = Item(id=item.id, kind="view", text=text)
            check_nonfact_deterministic(probe, base)
            item.problems += [p for p in probe.problems if "hedged" not in p]
            item.problems += _not_derived(text, base, "context")
        return
    if item.kind == BEN:
        base = _bank_text(notes, item.ref)
        if not base:
            item.problems.append("no matching note from Ben")
        else:
            probe = Item(id=item.id, kind="view", text=text)
            check_nonfact_deterministic(probe, base)
            item.problems += [p for p in probe.problems if "hedged" not in p]
            item.problems += _not_derived(text, base, "note")
        return

    if _EXPERIENCE.search(text):
        item.problems.append("claims first-hand experience that no note supports")
    n = len(words(text))
    if item.kind == VOICE:
        if n > MAX_VOICE_WORDS:
            item.problems.append(f"voice line is {n} words; the limit is {MAX_VOICE_WORDS}")
        if re.search(r"\d", text):
            item.problems.append("voice lines may not contain numbers")
        if _NAME.search(text):
            item.problems.append("voice lines may not name anyone or anything")
        return

    # take
    if n > MAX_TAKE_WORDS:
        item.problems.append(f"take is {n} words; the limit is {MAX_TAKE_WORDS}")
    if not (_FIRST_PERSON.search(text) or _OPINION_FRAME.search(text)):
        item.problems.append("a take must be first person or plainly framed as opinion")
    cited = [facts[f] for f in item.because if f in facts]
    if not cited:
        item.problems.append("a take must cite at least one verified fact in 'because'")
        return
    cited_text = " ".join(cited)
    probe = Item(id=item.id, kind="view", text=text)
    check_nonfact_deterministic(probe, cited_text)
    item.problems += [p for p in probe.problems if "hedged" not in p]
    cited_words = set(re.findall(r"[a-z-]+", cited_text.lower()))
    loaded = sorted({m.group(0).lower() for m in _LOADED.finditer(text)} - cited_words)
    if loaded:
        item.problems.append("uses loaded labels the cited facts do not use: " + ", ".join(loaded[:4]))
    if _SWEEPING.search(text) and not _FRAMED.search(text):
        item.problems.append("states a sweeping claim about the market as fact; frame it as a reading with 'may' or 'I read'")
    if (_MENTAL.search(text) and _NAME.search(text)) or _ROLE_MENTAL.search(text):
        verbs = {m.group(0).lower() for m in _MENTAL.finditer(text)} | {m.group(2).lower() for m in _ROLE_MENTAL.finditer(text)}
        if not any(v in cited_text.lower() for v in verbs):
            item.problems.append("attributes a private state or decision (wants, fears, decided, knows...) to a party the facts do not support")


def _rubric_prompt(facts: dict[str, str], items: list[VoiceItem]) -> str:
    listing = [{"id": i.id, "kind": i.kind, "sentence": i.text, "because": [facts.get(b, "") for b in i.because]} for i in items]
    facts_block = "\n".join(f"- {t}" for t in facts.values())
    return f"""VERIFIED FACTS (the only things that are true for this piece):
{facts_block[:6000]}

SENTENCES TO RULE ON:
{json.dumps(listing, ensure_ascii=False, indent=1)}

Rules.
- take: acceptable only if it is plainly an opinion or reading, is a fair and reasonable reading of the facts it cites, and slips in no new fact (no new event, figure, name, date, or cause stated as fact). Reject it if it states a motive, intention or private knowledge of a named person or company as if known; if it predicts as fact; if it implies wrongdoing the facts do not state; or if it is far bigger than the evidence ("this changes everything").
- voice: acceptable only if it asserts nothing that could be true or false about the world (a reaction, a transition, a light joke about the situation). Reject it if it implies something happened, if it mocks a person or a hardship, or if it carries a hidden claim.
- Opinion about patterns and implications is welcome. Speculation about people's inner states, and anything presented as fact without support, is not.
- Reject a take if any premise it relies on is not in the cited facts: even a single loaded word ("distressed", "bargain", "lower basis", "struggling"), a comparison the facts do not make, a claim about what an owner, buyer or lender "decided", "chose", "wanted" or "avoided", or a broad claim about "the market" or "investors" stated as fact. A take must read as a reading ("I read this as", "may be", "I'd bet"), not as a finding.

Return exactly: {{"results": [{{"id": "...", "verdict": "ok" or "reject", "issue": "one short sentence if reject, else empty"}}]}}
Include every id once."""


def run_rubric(llm: LLM, facts: dict[str, str], items: list[VoiceItem]) -> None:
    """Independent pass over the opinion layer. Fails closed if the answer is incomplete."""
    if not items:
        return
    for start in range(0, len(items), 8):
        chunk = items[start:start + 8]
        text = llm(RUBRIC_SYSTEM, _rubric_prompt(facts, chunk)).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
        data = json.loads(text)
        results = {str(r.get("id")): r for r in (data.get("results") or []) if isinstance(r, dict)}
        for item in chunk:
            entry = results.get(item.id)
            if entry is None:
                raise ValueError(f"rubric pass did not rule on {item.id}")
            verdict = str(entry.get("verdict") or "").strip().lower()
            if verdict not in ("ok", "reject"):
                raise ValueError(f"rubric pass gave an unusable verdict for {item.id}")
            item.verdict, item.issue = verdict, str(entry.get("issue") or "").strip()


def verify_voice_draft(
    draft: dict[str, Any], source_text: str, llm: LLM, *,
    context: list[dict[str, Any]] | None = None, notes: list[dict[str, Any]] | None = None,
) -> VoiceDraft:
    """Verify the fact layer with claim_verifier, then gate the voice layer on top of it."""
    context, notes = context or [], notes or []
    roles = parse_voice_draft(draft)
    flat = [i for _, items in roles for i in items]

    # 1. Facts: exactly the existing gate.
    fact_draft = {
        "title": draft.get("title"), "title_quote": draft.get("title_quote"),
        "excerpt": draft.get("excerpt"), "excerpt_quote": draft.get("excerpt_quote"),
        "paragraphs": [[{"text": i.text, "kind": FACT, "quotes": i.quotes} for i in items if i.kind == FACT]
                       for _, items in roles],
    }
    fact_draft["paragraphs"] = [p for p in fact_draft["paragraphs"] if p] or [[]]
    verified: VerifiedDraft = verify_draft(fact_draft, source_text, llm)
    kept_fact_texts = {_norm(i.text) for p in verified.paragraphs for i in p}
    surviving: dict[str, str] = {}
    for item in flat:
        if item.kind == FACT:
            if _norm(item.text) in kept_fact_texts:
                surviving[item.id] = item.text
            else:
                item.problems.append("fact rejected by the fact check")

    # 2. Voice layer: deterministic rules, then an independent rubric pass.
    for item in flat:
        if item.kind != FACT:
            check_voice_item(item, surviving, context, notes)
    candidates = [i for i in flat if i.kind in (TAKE, VOICE) and not i.problems]
    run_rubric(llm, surviving, candidates)

    kept_roles = [(role, [i for i in items if i.ok]) for role, items in roles]
    kept_roles = [(r, its) for r, its in kept_roles if its]
    kept = [i for _, its in kept_roles for i in its]
    return VoiceDraft(
        title=verified.title, excerpt=verified.excerpt, title_ok=verified.title_ok, excerpt_ok=verified.excerpt_ok,
        paragraphs=kept_roles, rejected=[i for i in flat if not i.ok],
        fact_count=sum(1 for i in kept if i.kind == FACT), take_count=sum(1 for i in kept if i.kind == TAKE),
        voice_count=sum(1 for i in kept if i.kind == VOICE), fact_rejections=verified.rejected_report(30),
    )
