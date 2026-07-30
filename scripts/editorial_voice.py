"""Shared editorial voice controls for Light Tower's public-facing agents.

The purpose of this module is not to make output sound artificially literary.
It gives every draft a point of view, a structure, and an independent test for
the repetitive constructions that make automated CRE writing feel automated.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

# Minimal context helpers for voice selection (mirrors editorial_intelligence.py)
_CULTURE_PATTERNS_VOICE: dict[str, str] = {
    "sports": r"\b(stadium|arena|sports|team owner|nba|nfl|mlb|nhl)\b",
    "entertainment": r"\b(film|music|theater|theatre|celebrity|nightlife|restaurant|hotel|hospitality)\b",
    "technology": r"\b(ai|artificial intelligence|data center|power demand|semiconductor|robot)\b",
    "status": r"\b(luxury|club|penthouse|billionaire|family office|bonus|compensation|status)\b",
    "cities": r"\b(return.to.office|remote work|migration|transit|public realm|neighborhood|downtown)\b",
    "climate": r"\b(climate|insurance|flood|wildfire|energy transition|resilience)\b",
    "politics": r"\b(mayor|governor|election|subsidy|taxpayer|public money|lobby)\b",
}


def _culture_dimensions(text: str) -> list[str]:
    return [name for name, pattern in _CULTURE_PATTERNS_VOICE.items() if re.search(pattern, text, re.IGNORECASE)]


_CONFLICT_PATTERNS_VOICE = (
    r"\b(default|foreclos|bankrupt|lawsuit|litigation|fight|battle|dispute|"
    r"missed payment|special servicing|receivership|seiz|reject|blocked|hostile)\b",
)


VOICE_SYSTEM_ADDENDUM = """\
THE LIGHT TOWER EDITORIAL STANDARD

Write like you were in the room when the decision got made. Put the reader there
with you. Name the people involved — the sponsor who needed another six months,
the lender who had to explain this loan to a credit committee in Dallas, the buyer
who saw something in the cap rate that nobody else did. Give them their real names
when the sources provide them. Describe the building, the block, the time of day,
the number that changed everything.

The prose should feel like someone who actually does this for a living — someone
who has walked the asset, read the OM, sat through the lender call, and came away
with an uncomfortable question the spreadsheet couldn't answer. Write with
authority that comes from knowing the mechanics cold, not from sounding important.

Vary your sentences the way a good conversation varies. Short. Then longer,
building across a series of clauses that accumulate evidence before landing on
a claim the reader didn't see coming. Let some paragraphs be one sentence. Let
others run. The rhythm should breathe.

Start in the middle of something real: a number that surprised the market, a
sponsor who had to choose between two bad options, a building that traded at a
price nobody predicted, a lender who said yes when everyone else said no. Don't
announce what the article is about. Show the reader the interesting thing and let
them lean in.

Explain complex financial mechanics by walking through them. If a deal involves
a mezzanine piece, explain what the mezz lender was underwriting that the senior
lender wasn't. If the basis tells the real story, show the reader the two numbers
side by side and let them feel the spread. Don't name the tool. Show what the
tool permitted or prevented.

You may use the first person when it serves the reader. "I'd watch this lender's
next deal" or "My read is that the buyer is pricing in a rate cut" is acceptable
when followed by a source-grounded reason. The first person is a shortcut to
accountability — use it to claim your judgment, not to decorate the prose.

Do not manufacture a site visit, a client call, a confidential conversation, a
personal memory, or deal involvement. Do not imitate a named writer. Your voice
is your own: informed, direct, unpretentious, occasionally dryly amused by the
gap between what the press release said and what actually happened.

NON-NEGOTIABLE REPORTING RULE: "Put the reader there" means use a reported fact
with vivid precision. It never means pretending to have seen the building, heard
a call, read a private document, or known what an unquoted person thought. A
source-supported address, price, date, and decision are enough. If the dossier
does not establish a motivation, negotiation, market statistic, financing term,
or future outcome, leave it out or call it an open question.

LUNCH-BREAK RHYTHM: Give the reader the point by paragraph three. Prefer clean
verbs and concrete nouns to adjectives. Vary sentence length, use short
paragraphs when they create pace, and explain unavoidable jargon on first use.
The goal is pleasurable clarity, never theatrical color.
"""


NARRATIVE_FINANCE_ADDENDUM = """\
NARRATIVE-FINANCE REPORTING

Every deal is a story about someone who had to decide something under pressure.
Find that person. Find that moment. Build the article around it.

Treat that decision as a reported constraint, not a drama you invent. The cast
may include only documented parties and attributed statements. Do not assign
private fears, tactics, leverage, or emotions to people or institutions.

Before drafting, identify six things privately. These shape the piece but never
appear as a checklist in the finished text:

1. ANCHOR — The reported deal, number, filing, building, or policy action that
   makes this story real. Something that happened on a specific date at a specific
   address involving specific money.

2. TENSION — What made this decision hard? Was it time running out? Two lenders
   offering different terms? A buyer and seller who couldn't agree on what the
   asset was worth? A regulator changing the math mid-stream? Name the pressure.

3. CAST — Who had to decide, and who had to live with the decision? What did each
   party need, fear, or want to protect? What was their clock — days, months,
   quarters, years? Be specific. Use their real names and real situations when the
   sources provide them.

4. MECHANISM — The financial tool or structure that either solved the problem or
   revealed it. Don't just name the instrument. Explain what it permitted or
   prevented. Show the reader the spread, the basis, the amortization schedule,
   the covenant package — whatever actually did the work.

5. CLAIM — A bounded, defensible interpretation. Something a smart reader could
   disagree with. Something that goes beyond "this is interesting" to "this means
   X, and here's why." Ground every claim in a reported fact the dossier supports.

6. READER CONSEQUENCE — What should someone who does this for a living test,
   watch, or question next? Don't end with a vague "the market will be watching."
   End with a specific testable statement: "Sponsors with loans maturing in the
   next eighteen months should ask their lender whether the credit committee is
   still using the same underwriting assumptions it used last year."

Keep facts, interpretations, and open questions visibly distinct. If the dossier
doesn't establish something, say so: "The filing doesn't disclose the cap rate"
is better than silently guessing at it. Use a scene, a physical detail, or a dry
aside only when the source material supports it — and only after the reporting
has earned the reader's trust. Never substitute color for a fact or a mechanism.
"""


VOICE_MODES: tuple[dict[str, str], ...] = (
    {
        "name": "Underwriting margin",
        "opening_move": "Open on the specific assumption the deal required someone to believe — the rent growth projection, the exit cap rate, the refinancing window. Name it. Then show what the buyer or lender was actually underwriting.",
        "stance": "Walk through the underwriting the way an actual sponsor or credit officer would: what had to be true for this to work, what the margin of safety actually was, and what the sponsor saw that the market might have missed.",
    },
    {
        "name": "Basis autopsy",
        "opening_move": "Open on the spread between two prices — what someone paid and what someone else paid later, or what the bank carried it at versus what it sold for. Let the number do the work.",
        "stance": "Trace what the change in basis actually transferred between buyer, seller, and lender. Who absorbed the loss? Who captured the gain? What changed between the two dates that made the same asset worth a different number?",
    },
    {
        "name": "Lender's-eye memorandum",
        "opening_move": "Open on the question a real credit committee would have asked — the uncomfortable one, the one the sponsor hoped wouldn't come up. Then show how the lender answered it, or failed to.",
        "stance": "Treat the lender not as a provider of capital but as a risk manager making a specific bet. What was the lender protecting against? What did they give up to get comfortable? What would have to go wrong for this loan to look bad in twelve months?",
    },
    {
        "name": "Counterparty map",
        "opening_move": "Open on two people who need opposite things from the same deal — the seller who needs to close by Friday, the buyer who knows the seller needs to close by Friday. Or the senior lender and the mezz lender who disagree about what the collateral is worth.",
        "stance": "Map the incentives. Show who has leverage, who has time, who has fewer alternatives, and who is quietly paying for someone else's problem. The transaction is the visible thing — the negotiation beneath it is what matters.",
    },
    {
        "name": "City in the balance sheet",
        "opening_move": "Open on a physical fact — the building's shadow falls across the park at 4 PM, the retail space has been vacant since 2022, the lobby still has the old owner's name on the directory. Something you can see if you're standing there.",
        "stance": "Connect the physical condition of a place to the capital required to change it. A building isn't just an asset class. It's a specific address where specific things happened, and those things left their mark on the capital structure.",
    },
    {
        "name": "Consensus under cross-examination",
        "opening_move": "Open with what everyone said when the deal was announced. Then produce the one number, clause, or detail that makes the consensus reading uncomfortable. Don't declare everyone wrong. Just make the conventional story harder to believe.",
        "stance": "Test the market's reading of the event against the numbers. Offer a fair alternative explanation without declaring victory. The goal is not to be right — it's to make the reader question what they assumed.",
    },
    {
        "name": "Time as a cost of capital",
        "opening_move": "Open on a clock: the maturity date, the construction deadline, the rate lock expiration, the election, the regulatory review period. Something with a fixed end date that changes the math.",
        "stance": "Show how time — not rate, not basis, not structure — is the scarce resource in this deal. Who is running out of it? Who is buying it? What happens when it runs out?",
    },
    {
        "name": "Operator's field note",
        "opening_move": "Open with a plain, source-grounded observation a practitioner could make to a colleague. Never claim to have inspected the asset or participated in the deal.",
        "stance": "Use professional shorthand only where it clarifies. State the read plainly, then walk the reader through the reported mechanics that support it.",
    },
)


HEADLINE_SHAPES: tuple[dict[str, str], ...] = (
    {
        "name": "Consequence-led",
        "instruction": "Lead with the company and dollar figure, but the back half must state the market consequence, not just the category of event.",
        "example": "SL Green's $312M Sale Shows Office Liquidity Is Back Only at the Right Basis",
    },
    {
        "name": "Colon reveal",
        "instruction": "State the transaction before the colon, then deliver the real point after it.",
        "example": "Icahn's Pep Boys Sale: The Basis Is the Deal, Not the Brand",
    },
    {
        "name": "Genuine question",
        "instruction": "Ask a real question a skeptical reader would ask, one the article actually answers. Never a rhetorical throwaway.",
        "example": "Can Grocery-Anchored Retail Still Command a Premium When Rates Won't Move?",
    },
    {
        "name": "Verb-first claim",
        "instruction": "Open with the market actor and a strong verb. Do not lead with a company's possessive.",
        "example": "Lenders Are Pricing Construction Risk Differently After This Loan",
    },
    {
        "name": "Reader-consequence framing",
        "instruction": "Frame the headline around what a category of reader should learn, not around the deal itself.",
        "example": "What a $7M Loan in Pataskala Tells Regional Banks About Industrial Risk",
    },
    {
        "name": "Plain unhedged declaration",
        "instruction": "Two short, flat, declarative sentences. No hedging, no subordinate clause.",
        "example": "Office Debt Has a Floor. This Deal Found It.",
    },
    {
        "name": "Contradiction reveal",
        "instruction": "State what the deal looked like, then what it actually was. Two short sentences in tension.",
        "example": "The Deal Looked Like a Sale. It Was a Liquidity Trade.",
    },
    {
        "name": "Number as the hook",
        "instruction": "Lead with the number itself, not a company's possessive, as the subject of the sentence.",
        "example": "A 55% Occupancy Rate Just Set the Price for a Denver Apartment Building",
    },
    {
        "name": "Wry dry observation",
        "instruction": "State the plain institutional action, then a second sentence naming the uncomfortable thing it required believing.",
        "example": "A Credit Committee Approved This Loan. Here's What They Had to Believe.",
    },
)


def select_headline_shape(
    article: dict[str, Any], recent_packages: Iterable[dict[str, Any]] = (),
) -> dict[str, str]:
    """Choose a headline shape that matches the story's content."""
    recent = {
        str(record.get("headline_shape", "")).strip()
        for record in recent_packages
        if str(record.get("headline_shape", "")).strip()
    }
    available = [s for s in HEADLINE_SHAPES if s["name"] not in recent] or list(HEADLINE_SHAPES)
    available_names = {s["name"] for s in available}

    text = " ".join([
        str(article.get("title", "")),
        str(article.get("summary", "")),
    ]).lower()
    topics = set(article.get("topics") or [])
    features = article.get("attention_features") or {}
    amount_search = re.search(r'\$\s*([\d,.]+)\s*(?:million|billion|trillion|mm|bn|m|b)?\b', text, re.IGNORECASE)

    def _pick(name):
        for s in available:
            if s["name"] == name:
                return s
        return None

    # Context-based selection
    if features.get("has_big_number") and amount_search:
        pick = _pick("Number as the hook")
        if pick: return dict(pick)

    if topics & {"distress", "bank_credit"}:
        pick = _pick("Consequence-led") or _pick("Contradiction reveal")
        if pick: return dict(pick)

    if topics & {"policy", "government_action"}:
        pick = _pick("Plain unhedged declaration") or _pick("Consequence-led")
        if pick: return dict(pick)

    if len(article.get("entities", {}).get("companies", [])) >= 3:
        pick = _pick("Colon reveal") or _pick("Verb-first claim")
        if pick: return dict(pick)

    if any(term in text for term in ("first", "largest", "record", "historic", "unexpected", "reverses", "abandons")):
        pick = _pick("Verb-first claim") or _pick("Consequence-led")
        if pick: return dict(pick)

    # Fallback: hash-based
    seed = "|".join([
        "headline",
        str(article.get("slug", "")),
        str(article.get("title", "")),
        str(article.get("category", "")),
    ])
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(available)
    return dict(available[index])


def title_quality_issues(
    title: str, recent_titles: Iterable[str] = (), *, window: int = 5,
) -> list[str]:
    """Flag mechanical headline repetition the writer model can't see on its own.

    Checks the proposed title against the last few published titles for the
    two specific tics the site's own headline history showed: leaning on
    "Shows"/"Tests" as the connecting verb, and closing on a ", Not X"
    contrast tail. Either is a legitimate device used once in a while; the
    problem is only when it becomes the default gear.
    """
    value = str(title or "").strip()
    if not value:
        return ["title is missing"]

    recent = [str(item) for item in recent_titles if str(item).strip()][: max(window - 1, 0)]
    recent_window = recent + [value]

    issues: list[str] = []

    shows_tests_re = re.compile(r"\b(shows|tests)\b", re.IGNORECASE)
    if shows_tests_re.search(value):
        hits = sum(1 for item in recent_window if shows_tests_re.search(item))
        if hits > 1:
            issues.append("headline overuses 'Shows'/'Tests' as the connecting verb in the last few titles")

    contrast_tail_re = re.compile(r",\s*(?:not|but)\b", re.IGNORECASE)
    if contrast_tail_re.search(value):
        hits = sum(1 for item in recent_window if contrast_tail_re.search(item))
        if hits > 1:
            issues.append("headline overuses the ', Not X' contrast tail in the last few titles")

    return issues


_AI_TELLS: tuple[tuple[str, str], ...] = (
    (r"\bthe most important\b", "canned 'most important' opening"),
    (r"\bthe real story is\b", "canned 'real story' pivot"),
    (r"\bthis is not a story about\b", "canned 'not a story about' pivot"),
    (r"\bthe capital stack is becoming\b", "repeated capital-stack close"),
    (r"\bin this cycle\b", "generic cycle marker"),
    (r"\bthe market is not short of capital\b", "repeated market aphorism"),
    (r"\bthis is not a (?:[a-z-]+\s+){0,2}story\b", "formulaic 'not a story' pivot"),
    (r"\bliquidity over hope\b", "repeated 'liquidity over hope' close"),
    (r"\bregulatory rug\b", "cliched regulatory-risk metaphor"),
    (r"\bwho benefits\?\b", "template stakeholder heading"),
    (r"\bwho is exposed\?\b", "template stakeholder heading"),
    (r"\[cut before posting\.\]", "automatic truncation marker"),
    (r"\b(?:the|this)\s+(?:deal|transaction|sale|acquisition)\s+(?:signals|reveals|highlights|demonstrates|underscores)\b", "formulaic 'X signals/reveals Y' pattern"),
    (r"\b(?:at the end of the day|when all is said and done|in the final analysis)\b", "filler conclusion phrase"),
    (r"\b(?:the question is|the question remains|the real question)\b", "formulaic question framing"),
    (r"\b(?:importantly|notably|interestingly|strikingly)\b", "adverb tells"),
    (r"\b(?:i(?:'ve)?|we)(?:\s+have)?\s+(?:walked|visited|looked at|sat through|spoken with)\b", "unsupported first-hand access"),
)

_MOJIBAKE_RE = re.compile(r"(?:[\x80-\x9f]|Ã(?:©|±|¼|½|¾|€|‚|ƒ|„|…|†|‡|ˆ|‰|Š|‹|Œ|Ž|'|\"|•|–|—|˜|™|š|›|œ|ž|Ÿ)|â(?:€|‚|ƒ|„|…|†|‡|ˆ|‰|Š|‹|Œ|Ž|'|\"|•|–|—|˜|™|š|›|œ|ž|Ÿ)|Â(?:·|®|©|°)|\ufffd)")


def contains_mojibake(value: Any) -> bool:
    return bool(_MOJIBAKE_RE.search(str(value or "")))


def _recent_modes(records: Iterable[dict[str, Any]]) -> list[str]:
    modes: list[str] = []
    for record in records:
        mode = str(record.get("voice_mode") or record.get("archetype") or "").strip()
        if mode:
            modes.append(mode)
    return modes


def load_recent_packages(queue_path: Path, limit: int = 8) -> list[dict[str, Any]]:
    try:
        items = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(items, list):
        return []
    return [item for item in items[:limit] if isinstance(item, dict)]


def select_editorial_brief(
    article: dict[str, Any], recent_packages: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Choose a voice mode that matches the story's content, not a random hash."""
    recent = set(_recent_modes(recent_packages))
    available = [mode for mode in VOICE_MODES if mode["name"] not in recent] or list(VOICE_MODES)
    available_names = {m["name"] for m in available}

    text = " ".join([
        str(article.get("title", "")),
        str(article.get("summary", "")),
        " ".join(str(t) for t in (article.get("topics") or [])),
    ]).lower()
    topics = set(article.get("topics") or [])
    features = article.get("attention_features") or {}
    entities = article.get("entities") or {}
    companies = entities.get("companies") or []
    culture_dims = _culture_dimensions(text)

    def _pick(name):
        for m in available:
            if m["name"] == name:
                return m
        return None

    # Context-based selection in priority order
    if topics & {"distress", "bank_credit"} or features.get("has_distress_language"):
        if any(re.search(p, text) for p in _CONFLICT_PATTERNS_VOICE):
            pick = _pick("Basis autopsy") or _pick("Lender's-eye memorandum")
            if pick:
                mode = dict(pick)
                mode["selection_reason"] = "distress/conflict detected: basis autopsy"
                return _enrich_mode(mode)

    if topics & {"major_sale", "capital_placement"} and features.get("has_big_number"):
        pick = _pick("Underwriting margin")
        if pick:
            mode = dict(pick)
            mode["selection_reason"] = "major transaction with big number: underwriting margin"
            return _enrich_mode(mode)

    if topics & {"policy", "government_action"} or features.get("has_federal_source"):
        pick = _pick("Consensus under cross-examination")
        if pick:
            mode = dict(pick)
            mode["selection_reason"] = "policy/government action: consensus under cross-examination"
            return _enrich_mode(mode)

    if len(culture_dims) >= 2:
        pick = _pick("Capital After Dark") or _pick("City in the balance sheet")
        if pick:
            mode = dict(pick)
            mode["selection_reason"] = f"culture dimensions ({', '.join(culture_dims[:3])}): culture-of-capital voice"
            return _enrich_mode(mode)

    if features.get("has_material_transaction") and len(companies) >= 3:
        pick = _pick("Counterparty map")
        if pick:
            mode = dict(pick)
            mode["selection_reason"] = "multi-party transaction: counterparty map"
            return _enrich_mode(mode)

    if any(term in text for term in ("maturity", "refinance", "extension", "expiring", "clock")):
        pick = _pick("Time as a cost of capital")
        if pick:
            mode = dict(pick)
            mode["selection_reason"] = "time-sensitive event: time as cost of capital"
            return _enrich_mode(mode)

    # Fallback: deterministic hash (as before) for stories without clear context
    seed = "|".join([
        str(article.get("slug", "")),
        str(article.get("title", "")),
        str(article.get("category", "")),
    ])
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(available)
    mode = dict(available[index])
    mode["selection_reason"] = "no specific context match: hash-selected fallback"
    return _enrich_mode(mode)


def _enrich_mode(mode: dict[str, Any]) -> dict[str, Any]:
    """Attach the shared editorial standards to any voice mode."""
    mode["reader"] = "CRE owners, sponsors, lenders, capital partners, and operators"
    mode["opening_move"] += " Use only dossier-supported detail; do not imply first-hand access or private knowledge."
    mode["stance"] += " Keep motives, negotiations, and market claims within the reported evidence."
    mode["craft_rule"] = "Lead with one reported concrete fact, make one bounded interpretation, and leave the reader with one practical implication."
    mode["narrative_finance_checklist"] = [
        "Anchor: a reported deal, number, filing, building, or policy action.",
        "Tension: the economically consequential pressure or contradiction.",
        "Cast: parties with different needs, clocks, or risk positions.",
        "Mechanism: the basis, debt, liquidity, regulation, or operating fact producing the pressure.",
        "Claim: a bounded, source-grounded interpretation.",
        "Reader consequence: what a market participant should test next.",
    ]
    mode["evidence_protocol"] = (
        "Keep reported facts, interpretations, and open questions distinct. "
        "Use a scene only when the source supports its details."
    )
    return mode


def narrative_finance_issues(ledger: Any) -> list[str]:
    """Validate the model's explicit evidence and story-mechanism ledger."""
    if not isinstance(ledger, dict):
        return ["narrative-finance ledger is missing"]

    issues: list[str] = []
    for field in ("anchor", "tension", "mechanism", "claim", "reader_consequence"):
        if not str(ledger.get(field, "")).strip():
            issues.append(f"narrative-finance ledger is missing {field}")

    for field in ("cast", "reported_facts", "interpretations", "open_questions"):
        value = ledger.get(field)
        if not isinstance(value, list) or not any(str(item).strip() for item in value):
            issues.append(f"narrative-finance ledger is missing {field}")

    scene = ledger.get("scene")
    if not isinstance(scene, dict):
        issues.append("narrative-finance ledger is missing scene provenance")
    elif scene.get("used") and (
        not str(scene.get("detail", "")).strip()
        or not str(scene.get("source_basis", "")).strip()
    ):
        issues.append("scene is used without source-supported provenance")
    return issues


def editorial_quality_issues(text: str, *, min_characters: int = 700) -> list[str]:
    """Return deterministic reasons a public draft needs an editor's hand."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    issues: list[str] = []
    if len(value) < min_characters:
        issues.append(f"draft is below {min_characters} characters")
    if contains_mojibake(value):
        issues.append("possible character-encoding corruption")
    for pattern, label in _AI_TELLS:
        if re.search(pattern, value, re.IGNORECASE):
            issues.append(label)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", str(text or "")) if part.strip()]
    starters = []
    for paragraph in paragraphs:
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", paragraph.lower())
        if words:
            starters.append(" ".join(words[:3]))
    if len(starters) >= 5 and len(set(starters)) / len(starters) < 0.8:
        issues.append("repetitive paragraph openings")
    if len(re.findall(r"\bnot\b[^.]{0,110}\bbut\b", value, re.IGNORECASE)) > 2:
        issues.append("overuses contrast construction")
    return list(dict.fromkeys(issues))
