"""Sentence-level accuracy gate for generated articles.

A language model cannot be trusted to stay inside its sources, and a prompt cannot make
it so. This module makes accuracy a property of the pipeline instead:

1. The writer must return structured sentences. Every *fact* sentence carries one or
   two verbatim quotes copied from the source text.
2. Code checks, deterministically, that each quote really occurs in the source, and
   that every number, spelled-out number, name, date and quoted phrase in the sentence
   occurs in that sentence's quotes.
3. A second model, preferably from a different provider, reads the full source and
   rules on every sentence: supported or not. If that verifier cannot run, nothing is
   published (fail closed).
4. The page is assembled from the sentences that passed. Everything else is dropped.

What this guarantees: every factual sentence on a published page is traceable to words
in a source that a human can read, and was independently judged as supported.
What it cannot guarantee: that the source itself is right, or that a verifier never
misses a subtle misreading. The evidence file written for every article exists so a
person can audit those cases quickly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from readability import sentences, unsupported_names, unsupported_numbers, words

LLM = Callable[[str, str], str]  # (system, user) -> raw completion text

FACT, VIEW, ACTION = "fact", "view", "action"
SUMMARY = "summary"  # headline or lede that characterises already-verified facts (weekly wrap only)
KINDS = (FACT, VIEW, ACTION)
# Opinion sentences are off. In the 2026-10-08 audit a same-family checker approved "views" that a
# stricter audit rejected as not in the source, so an opinion cannot be called verified. Facts only.
MAX_VIEWS = 0
MIN_QUOTE_WORDS = 4
MAX_QUOTE_CHARS = 240  # tight quotes: a long quote can hide a dropped qualifier
VERIFY_CHUNK = 8  # sentences per verifier call
HEDGES = re.compile(
    r"\b(likely|suggests?|could|may|might|if|would|appears?|points? to|signals?|implies|probably)\b", re.I
)

# A sentence may not strip a qualifier or an attribution that its own quote carries.
# Each group is interchangeable: "roughly" may stand in for "about", but may not be dropped.
_QUALIFIER_GROUPS = (
    {"most", "mostly", "largely", "mainly"}, {"some", "partly", "partially"},
    {"about", "roughly", "approximately", "around", "nearly", "almost"},
    {"expected", "expects", "plans", "planned", "aims", "proposed", "intends", "intended"},
    {"could", "may", "might", "potentially"}, {"estimated", "estimates", "projected", "preliminary"},
    {"reportedly", "allegedly", "alleged", "unconfirmed"},
)
_ATTRIBUTION = {"said", "says", "told", "according", "argued", "argues", "claims", "claimed", "alleges",
                "noted", "added", "described", "called", "stated", "believes", "predicts"}

VERIFIER_SYSTEM = (
    "You are a strict fact-checker for a commercial real estate publication. You are shown SOURCE TEXT "
    "and a numbered list of sentences written from it. You never write or improve anything. You only "
    "rule on whether each sentence is supported. Return JSON only."
)


# --------------------------------------------------------------------------------------
# Deterministic checks
# --------------------------------------------------------------------------------------

def squash(text: str) -> str:
    """Lowercase letters and digits only, single-spaced: punctuation and spacing cannot hide a mismatch."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).split())


def quote_in_source(quote: str, source_text: str) -> bool:
    q = squash(quote)
    return len(q.split()) >= MIN_QUOTE_WORDS and q in squash(source_text)


def _quoted_phrases(sentence: str) -> list[str]:
    return [m.strip() for m in re.findall(r"[“\"]([^”\"]{3,})[”\"]", sentence) if m.strip()]


@dataclass
class Item:
    id: str
    kind: str
    text: str
    quotes: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # deterministic
    verdict: str = ""  # first pass: supported | unsupported
    issue: str = ""
    verdict2: str = "supported"  # second, differently framed pass; stays "supported" until a pass says otherwise
    issue2: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems and self.verdict == "supported" and self.verdict2 == "supported"

    @property
    def reason(self) -> str:
        return "; ".join(self.problems) or self.issue or self.issue2 or "not supported"


def _clean_quotes(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(q).strip() for q in raw if str(q).strip()][:2]


def check_fact_deterministic(item: Item, source_text: str, *, is_title: bool = False) -> None:
    if not item.quotes:
        item.problems.append("no source quote supplied")
        return
    for quote in item.quotes:
        if len(quote) > MAX_QUOTE_CHARS:
            item.problems.append("quote is longer than allowed")
        elif not quote_in_source(quote, source_text):
            item.problems.append(f"quote not found verbatim in the source: “{quote[:70]}”")
    if item.problems:
        return
    joined = " ".join(item.quotes)
    bad_numbers = unsupported_numbers(item.text, joined)
    if bad_numbers:
        item.problems.append("figures not in its quote: " + ", ".join(bad_numbers[:6]))
    # Headlines capitalise every word, so the name tripwire cannot read them; the model checks cover them.
    bad_names = [] if is_title else unsupported_names(item.text, joined)
    if bad_names:
        item.problems.append("names not in its quote: " + ", ".join(bad_names[:6]))
    for phrase in _quoted_phrases(item.text):
        if squash(phrase) not in squash(source_text):
            item.problems.append(f"quoted words are not in the source: “{phrase[:60]}”")
    quote_words = set(squash(joined).split())
    sentence_words = set(squash(item.text).split())
    for group in _QUALIFIER_GROUPS:
        if quote_words & group and not sentence_words & group:
            item.problems.append(f"drops the qualifier “{sorted(quote_words & group)[0]}” that its quote carries")
    if quote_words & _ATTRIBUTION and not sentence_words & _ATTRIBUTION:
        item.problems.append("drops the attribution (“said”, “according to”) that its quote carries")


def check_nonfact_deterministic(item: Item, fact_text: str) -> None:
    """Views and actions may add no figures and no names beyond the verified facts."""
    bad_numbers = unsupported_numbers(item.text, fact_text)
    if bad_numbers:
        item.problems.append("a view or action may not add figures: " + ", ".join(bad_numbers[:6]))
    tokens = item.text.split()
    title_case = len(tokens) >= 3 and sum(1 for t in tokens if t[:1].isupper()) / len(tokens) > 0.6
    bad_names = [] if title_case else unsupported_names(item.text, fact_text)  # headlines capitalise every word
    if bad_names:
        item.problems.append("a view or action may not add names: " + ", ".join(bad_names[:6]))
    if item.kind == VIEW and not HEDGES.search(item.text):
        item.problems.append("a view must be hedged (likely, suggests, could, if, may)")


# --------------------------------------------------------------------------------------
# Independent model check
# --------------------------------------------------------------------------------------

def _verifier_prompt(source_text: str, items: list[Item], fact_context: str) -> str:
    listing = [{"id": i.id, "kind": i.kind, "sentence": i.text, "quotes": i.quotes} for i in items]
    return f"""SOURCE TEXT (the only ground truth):
\"\"\"
{source_text[:14000]}
\"\"\"

SENTENCES TO CHECK:
{json.dumps(listing, ensure_ascii=False, indent=1)}

Rules by kind:
- fact: "supported" only if EVERY claim in the sentence is stated in, or follows directly from, the SOURCE TEXT: who, what, how much, which direction, when, and why. Mark "unsupported" if it adds anything; exaggerates; reverses a direction; merges two separate claims; states a cause the source does not state; adds "first", "largest", "only", "record" or any ranking the source does not give; sums or compares numbers the source does not compare; changes tense or timing; turns a plan, a request or an allegation into an accomplished fact; or attributes a statement to someone who did not make it.
- view: "supported" only if it is a cautious inference that follows from these verified facts and asserts no new fact:
{fact_context[:3000]}
- action: "supported" only if it is a suggestion to check or ask something and asserts no fact.
- summary: "supported" only if it fairly characterises the verified facts above without exaggerating, ranking, generalising beyond them, or adding any fact.

Return exactly: {{"results": [{{"id": "...", "verdict": "supported" or "unsupported", "issue": "one short sentence if unsupported, else empty"}}]}}
Include every id once."""


def run_verifier(llm: LLM, source_text: str, items: list[Item], fact_context: str) -> None:
    """Fill ``verdict``/``issue`` on every item. Raises on a malformed or incomplete answer (fail closed)."""
    if not items:
        return
    if len(items) > VERIFY_CHUNK:  # bounded output per call keeps reasoning-mode answers from truncating
        for start in range(0, len(items), VERIFY_CHUNK):
            run_verifier(llm, source_text, items[start:start + VERIFY_CHUNK], fact_context)
        return
    raw = llm(VERIFIER_SYSTEM, _verifier_prompt(source_text, items, fact_context))
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    data = json.loads(text)
    results = {str(r.get("id")): r for r in (data.get("results") or []) if isinstance(r, dict)}
    for item in items:
        entry = results.get(item.id)
        if entry is None:
            raise ValueError(f"verifier did not rule on {item.id}")
        verdict = str(entry.get("verdict") or "").strip().lower()
        if verdict not in {"supported", "unsupported"}:
            raise ValueError(f"verifier gave an unusable verdict for {item.id}")
        item.verdict = verdict
        item.issue = str(entry.get("issue") or "").strip()


def _atomic_prompt(source_text: str, items: list[Item]) -> str:
    listing = [{"id": i.id, "sentence": i.text} for i in items]
    return f"""SOURCE TEXT (the only ground truth):
\"\"\"
{source_text[:14000]}
\"\"\"

SENTENCES:
{json.dumps(listing, ensure_ascii=False, indent=1)}

For each sentence:
1. Split it into atomic claims: who did or said what, amounts, dates, places, direction of change, and every qualifier (most, about, expects, plans, could) and attribution (who said it).
2. For each atomic claim decide supported=true only if the SOURCE TEXT states it with the SAME strength and the SAME attribution. A source that says "most of" does not support "all of" or no qualifier; "plans to" does not support "will" or "did"; a person's opinion or claim does not support the same words as plain fact; a partial name or a partial total is not the whole.
3. verdict is "supported" only if every atomic claim is supported.

Return exactly: {{"results": [{{"id": "...", "claims": [{{"claim": "...", "supported": true}}], "verdict": "supported" or "unsupported", "issue": "the unsupported claim, else empty"}}]}}
Include every id once."""


def run_verifier_atomic(llm: LLM, source_text: str, items: list[Item]) -> None:
    """Second pass, framed as claim decomposition rather than a yes/no ruling. Fails closed."""
    if not items:
        return
    if len(items) > VERIFY_CHUNK:
        for start in range(0, len(items), VERIFY_CHUNK):
            run_verifier_atomic(llm, source_text, items[start:start + VERIFY_CHUNK])
        return
    text = llm(VERIFIER_SYSTEM, _atomic_prompt(source_text, items)).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    data = json.loads(text)
    results = {str(r.get("id")): r for r in (data.get("results") or []) if isinstance(r, dict)}
    for item in items:
        entry = results.get(item.id)
        if entry is None:
            raise ValueError(f"second-pass verifier did not rule on {item.id}")
        claims = entry.get("claims") if isinstance(entry.get("claims"), list) else []
        all_claims_ok = all(bool(c.get("supported")) for c in claims if isinstance(c, dict))
        verdict = str(entry.get("verdict") or "").strip().lower()
        if verdict not in {"supported", "unsupported"}:
            raise ValueError(f"second-pass verifier gave an unusable verdict for {item.id}")
        # Either signal failing is enough: a "supported" verdict that lists an unsupported claim is not trusted.
        item.verdict2 = "supported" if verdict == "supported" and all_claims_ok else "unsupported"
        item.issue2 = str(entry.get("issue") or "").strip() or next(
            (str(c.get("claim")) for c in claims if isinstance(c, dict) and not c.get("supported")), "")


# --------------------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------------------

@dataclass
class VerifiedDraft:
    title: str
    excerpt: str
    paragraphs: list[list[Item]]  # verified items only, in order
    rejected: list[Item]
    title_ok: bool
    excerpt_ok: bool
    fact_count: int
    view_count: int
    items_checked: int

    def rejected_report(self, limit: int = 12) -> list[str]:
        return [f"“{i.text[:110]}” rejected: {i.reason}" for i in self.rejected[:limit]]

    def to_evidence(self) -> dict[str, Any]:
        def dump(i: Item) -> dict[str, Any]:
            return {"kind": i.kind, "text": i.text, "quotes": i.quotes}
        return {
            "title": self.title, "excerpt": self.excerpt,
            "paragraphs": [[dump(i) for i in p] for p in self.paragraphs],
            "rejected": [{**dump(i), "reason": i.reason} for i in self.rejected],
        }


def parse_draft_items(draft: dict[str, Any]) -> tuple[Item, Item, list[list[Item]]]:
    """Turn the writer's JSON into Items. Raises ValueError when the shape is unusable."""
    counter = 0

    def make(text: Any, kind: str, quotes: Any) -> Item:
        nonlocal counter
        counter += 1
        return Item(id=f"s{counter}", kind=kind, text=re.sub(r"\s+", " ", str(text or "")).strip(),
                    quotes=_clean_quotes(quotes))

    title = make(draft.get("title"), FACT, draft.get("title_quote"))
    excerpt = make(draft.get("excerpt"), FACT, draft.get("excerpt_quote"))
    raw_paragraphs = draft.get("paragraphs")
    if not isinstance(raw_paragraphs, list) or not raw_paragraphs:
        raise ValueError("draft has no paragraphs")
    paragraphs: list[list[Item]] = []
    for raw_paragraph in raw_paragraphs:
        if not isinstance(raw_paragraph, list):
            raise ValueError("paragraph is not a list of sentences")
        row = []
        for entry in raw_paragraph:
            if not isinstance(entry, dict):
                raise ValueError("sentence is not an object")
            kind = str(entry.get("kind") or "").strip().lower()
            if kind not in KINDS:
                raise ValueError(f"unknown sentence kind: {kind!r}")
            item = make(entry.get("text"), kind, entry.get("quotes", entry.get("quote")))
            if item.text:
                row.append(item)
        if row:
            paragraphs.append(row)
    if not paragraphs:
        raise ValueError("draft has no sentences")
    return title, excerpt, paragraphs


def verify_draft(draft: dict[str, Any], source_text: str, llm: LLM, llm_b: LLM | None = None) -> VerifiedDraft:
    """Run every check. Raises if the draft is malformed or the verifier cannot rule (fail closed)."""
    title, excerpt, paragraphs = parse_draft_items(draft)
    body_items = [i for p in paragraphs for i in p]
    facts = [i for i in body_items if i.kind == FACT]

    check_fact_deterministic(title, source_text, is_title=True)
    for item in (excerpt, *facts):
        check_fact_deterministic(item, source_text)
    # Only sentences that passed the deterministic gate count as established facts.
    fact_context = " ".join(i.text for i in facts if not i.problems)
    # Every published sentence is a quoted fact. Opinions, predictions and "what to check" lines are
    # refused: in the 2026-10-08 audit they were where unsupported claims hid (a closing suggestion
    # embedded "whether full-term interest-only pricing still holds for low-leverage deals").
    for item in body_items:
        if item.kind != FACT:
            item.problems.append("only sentences backed by a source quote are published; "
                                 "no opinions, predictions or suggestions")

    to_judge = [i for i in (title, excerpt, *body_items) if not i.problems]
    run_verifier(llm, source_text, to_judge, fact_context)
    # Second, differently framed pass over what the first pass accepted (facts, title, excerpt).
    run_verifier_atomic(llm_b or llm, source_text,
                        [i for i in to_judge if i.kind == FACT and i.verdict == "supported"])

    rejected = [i for i in (title, excerpt, *body_items) if not i.ok]
    kept_paragraphs = [[i for i in p if i.ok] for p in paragraphs]
    kept_paragraphs = [p for p in kept_paragraphs if p]
    kept = [i for p in kept_paragraphs for i in p]
    return VerifiedDraft(
        title=title.text, excerpt=excerpt.text, paragraphs=kept_paragraphs, rejected=rejected,
        title_ok=title.ok, excerpt_ok=excerpt.ok,
        fact_count=sum(1 for i in kept if i.kind == FACT),
        view_count=sum(1 for i in kept if i.kind == VIEW),
        items_checked=len(body_items) + 2,
    )


def verify_unquoted(items: list[Item], source_text: str, fact_context: str, llm: LLM) -> None:
    """Gate for short derived text (the weekly wrap) where there is no quote requirement.

    Facts are checked against the whole source text; views and actions may add no figures or
    names beyond ``fact_context``. Fills ``verdict`` and ``problems``; raises if the verifier
    cannot rule (fail closed).
    """
    for item in items:
        if item.kind == FACT:
            bad_numbers = unsupported_numbers(item.text, source_text)
            if bad_numbers:
                item.problems.append("figures not in the source: " + ", ".join(bad_numbers[:6]))
            bad_names = unsupported_names(item.text, source_text)
            if bad_names:
                item.problems.append("names not in the source: " + ", ".join(bad_names[:6]))
        else:
            check_nonfact_deterministic(item, fact_context)
    judged = [i for i in items if not i.problems]
    run_verifier(llm, source_text, judged, fact_context)
    run_verifier_atomic(llm, source_text, [i for i in judged if i.kind == FACT and i.verdict == "supported"])


def assemble_paragraphs(verified: VerifiedDraft) -> list[str]:
    """Plain-text paragraphs from verified sentences; a paragraph opening on a view is labelled as one."""
    out: list[str] = []
    for paragraph in verified.paragraphs:
        text = " ".join(i.text for i in paragraph)
        if paragraph[0].kind == VIEW and not re.match(r"(?i)(our|my) read\b", text):
            text = "Our read: " + text[0].lower() + text[1:] if text else text
        out.append(text)
    return out


def source_text_from_dossier(dossier: dict[str, Any]) -> str:
    """The text the writer saw: source bodies only, never derived summaries or fact lists."""
    return "\n\n".join(
        f"[Source {n}: {s.get('name') or s.get('source') or ''}]\n{s.get('text') or ''}"
        for n, s in enumerate(dossier.get("sources") or [], 1)
        if s.get("text")
    )


__all__ = [
    "Item", "VerifiedDraft", "verify_draft", "verify_unquoted", "assemble_paragraphs", "source_text_from_dossier",
    "quote_in_source", "squash", "sentences", "words",
]
