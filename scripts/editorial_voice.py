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


VOICE_SYSTEM_ADDENDUM = """\
THE LIGHT TOWER EDITORIAL STANDARD
Write with the judgment of a CRE capital-markets professional who has spent time
with underwriting, incentives, and the built environment. The prose may be
elegant, but elegance must come from exact observation, clean syntax, rhythm,
and a genuine point of view—not from ornamental metaphors or borrowed authorial
voices.

Use enduring craft principles: begin in a concrete fact or pressure; make a
claim that a serious reader could disagree with; move from reported detail to
economic consequence; vary sentence length deliberately; and leave the reader
with a sharper question than the headline supplied. Never imitate a named,
living, or deceased writer. Never manufacture a site visit, a client call, a
confidential conversation, a personal memory, or deal involvement for Ben.

Personal voice means accountable judgment, not fictional autobiography. It is
acceptable to write "My read is" or "I would watch" only when followed by a
source-grounded reason. Do not use first-person merely as decoration.

Avoid formulaic pivots such as "the real story," "the most important number is
not," "this is not a story about," "the capital stack is becoming," and "in
this cycle." Do not force a closing question. Ask one only when a specific
professional could answer it from experience.
"""


NARRATIVE_FINANCE_ADDENDUM = """\
NARRATIVE-FINANCE REPORTING
Make finance compelling by following the decision that reveals the system. Find
the actor whose choice exposes the mechanism: a borrower seeking time, a lender
deciding whether to extend, a buyer accepting a basis, a developer assembling a
site, or a regulator changing the underwriting math. Describe the role and the
decision accurately; never invent a biography, a conversation, or colorful
deal lore.

Before drafting, identify six things privately: (1) the anchor—a reported deal,
number, filing, building, or policy action; (2) the tension; (3) the cast and
their different needs or clocks; (4) the capital mechanism; (5) the defensible
claim; and (6) the reader consequence. The article should explain what a
financial tool permits or prevents, not merely name it.

Keep causality clean. Separate reported facts, reasonable interpretations, and
unresolved questions. A scene is allowed only when its concrete details appear
in the supplied source material. Use controlled color sparingly: one precise
image, metaphor, or dry aside may relieve density after the reporting has earned
the reader's trust. Never use color as a substitute for a fact or a mechanism.
"""


VOICE_MODES: tuple[dict[str, str], ...] = (
    {
        "name": "Underwriting margin",
        "opening_move": "Open on the assumption the deal requires someone to believe.",
        "stance": "Name the underwriting condition that separates an investable deal from an attractive story.",
    },
    {
        "name": "Basis autopsy",
        "opening_move": "Open on the spread between two prices, two dates, or two valuations.",
        "stance": "Explain what the change in basis transferred between buyer, seller, and lender.",
    },
    {
        "name": "Lender's-eye memorandum",
        "opening_move": "Open on the question a prudent credit committee would have to answer.",
        "stance": "Treat the lender's decision as a risk-allocation choice, not a vote of confidence.",
    },
    {
        "name": "Counterparty map",
        "opening_move": "Open on two parties who need different things from the same transaction.",
        "stance": "Show where incentives align, where they do not, and which party is buying time.",
    },
    {
        "name": "City in the balance sheet",
        "opening_move": "Open on a precise physical fact about the building, block, or submarket.",
        "stance": "Connect the physical condition of a place to the capital required to change it.",
    },
    {
        "name": "Consensus under cross-examination",
        "opening_move": "Open by testing the conventional reading of the headline against one inconvenient fact.",
        "stance": "Offer a fair alternative reading without declaring everyone else wrong.",
    },
    {
        "name": "Time as a cost of capital",
        "opening_move": "Open on a maturity, lease-up period, entitlement clock, or execution deadline.",
        "stance": "Explain how time changes leverage, bargaining power, and the available exit paths.",
    },
    {
        "name": "Operator's field note",
        "opening_move": "Open with a concise professional observation anchored in the reported facts.",
        "stance": "Give a measured personal read, then show the mechanics that justify it.",
    },
)


_AI_TELLS: tuple[tuple[str, str], ...] = (
    (r"\bthe most important\b", "canned 'most important' opening"),
    (r"\bthe real story is\b", "canned 'real story' pivot"),
    (r"\bthis is not a story about\b", "canned 'not a story about' pivot"),
    (r"\bthe capital stack is becoming\b", "repeated capital-stack close"),
    (r"\bin this cycle\b", "generic cycle marker"),
    (r"\bthe market is not short of capital\b", "repeated market aphorism"),
    (r"\bthis is not a (?:[a-z-]+\s+){0,2}story\b", "formulaic 'not a story' pivot"),
    (r"\bliquidity over hope\b", "repeated 'liquidity over hope' close"),
    (r"\bregulatory rug\b", "clichéd regulatory-risk metaphor"),
    (r"\bwho benefits\?\b", "template stakeholder heading"),
    (r"\bwho is exposed\?\b", "template stakeholder heading"),
    (r"\[cut before posting\.\]", "automatic truncation marker"),
)

_MOJIBAKE_RE = re.compile(r"(?:â€|â€”|â†|âœ|Ãƒ|Ã¢|�)")


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
    """Choose a deterministic mode while avoiding recently used structures."""
    recent = set(_recent_modes(recent_packages))
    candidates = [mode for mode in VOICE_MODES if mode["name"] not in recent] or list(VOICE_MODES)
    seed = "|".join(
        [
            str(article.get("slug", "")),
            str(article.get("title", "")),
            str(article.get("category", "")),
        ]
    )
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(candidates)
    mode = dict(candidates[index])
    mode["reader"] = "CRE owners, sponsors, lenders, capital partners, and operators"
    mode["craft_rule"] = "Use one concrete fact, one defensible interpretation, and one practical implication."
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
