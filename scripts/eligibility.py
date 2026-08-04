"""Decide whether an intelligence object deserves a slot, and say why.

This replaces `v2_editorial.is_daily_article_candidate`, which asked a single
question -- does headline+summary contain any of ~40 capital-adjacent nouns --
and therefore admitted a developer explainer on the phrase "data center" and a
promotional interview on "investment" appearing in a biography.

Eligibility here is decided per event family, because the families genuinely
differ: a property trade needs named parties and scale, a Fed decision needs no
dollar amount at all, and an interview needs a material disclosure. One
universal gate cannot express that.

Every decision returns a rationale and the evidence behind it. Nothing is
eligible by default.

Not yet wired into production selection: `v2_editorial` is unchanged pending
shadow validation and cutover.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from content_typing import describe
from intelligence_object import (
    ContentType,
    EvidenceLevel,
    IntelligenceObject,
    ObjectClass,
)

#: Sectors whose importance does not depend on a transaction amount.
_NON_TRANSACTIONAL_SECTORS = frozenset({"fed_macro", "local_government"})

#: Object classes that are inherently non-transactional.
_NON_TRANSACTIONAL_CLASSES = frozenset({
    ObjectClass.DATA_RELEASE,
    ObjectClass.MARKET_MOVEMENT,
    ObjectClass.TREND,
})

_NAMED_PARTY = re.compile(r"\b[A-Z][A-Za-z&'.-]+(?:\s+[A-Z][A-Za-z&'.-]+)*\b")
_SCALE = re.compile(
    r"\b[\d,]+(?:\.\d+)?\s*(?:units?|sf|square feet|acres?|mw|megawatts?|rooms?|keys|bps|basis points)\b",
    re.I,
)
_MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?\s*(?:billion|bn|million|mm|trillion|[bmk])?\b", re.I)

_POLICY_ACTION = re.compile(
    r"\b(?:rais(?:e|ed|es)|cut|cuts|hold(?:s)?|lower(?:s|ed)?|approv\w+|reject\w+|"
    r"propos\w+|finaliz\w+|enact\w+|rul(?:e|ed|ing)|order(?:s|ed)?|"
    r"vote[sd]?|adopt\w+|impos\w+|ban(?:s|ned)?|mandat\w+)\b",
    re.I,
)


@dataclass
class EligibilityDecision:
    eligible: bool = False
    reason: str = ""
    family: str = ""
    evidence: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "family": self.family,
            "evidence": self.evidence,
            "disqualifiers": self.disqualifiers,
            "confidence": round(self.confidence, 3),
        }


def _event_family(obj: IntelligenceObject, traits: dict[str, Any]) -> str:
    """Which set of rules applies to this object."""
    if obj.object_class in _NON_TRANSACTIONAL_CLASSES:
        return "data_or_signal"
    content_type = traits["content_type"]
    if content_type in (ContentType.INTERVIEW, ContentType.OPINION):
        return "interview_or_opinion"
    if content_type == ContentType.DATA_PUBLICATION:
        return "data_or_signal"
    if obj.primary_sector in _NON_TRANSACTIONAL_SECTORS:
        return "policy_or_macro"
    if content_type in ContentType.PRIMARY_AUTHORITY:
        return "primary_document"
    return "transaction_or_development"


def assess(obj: IntelligenceObject, *, text: str = "") -> EligibilityDecision:
    """Decide eligibility for one object."""
    blob = text or f"{obj.title} {obj.what_happened}"
    traits = describe(
        obj.title,
        obj.what_happened,
        sector=obj.primary_sector,
        source_type="",
    )
    content_type = traits["content_type"]
    family = _event_family(obj, traits)
    decision = EligibilityDecision(family=family)

    # ── Hard disqualifiers, independent of family ──────────────────────────
    if content_type in ContentType.NEVER_ELIGIBLE:
        decision.disqualifiers.append(f"content_type={content_type}")
        decision.reason = (
            f"{content_type} is never editorial intelligence "
            f"({traits['content_type_evidence'][0] if traits['content_type_evidence'] else 'no evidence'})"
        )
        decision.confidence = traits["content_type_confidence"]
        return decision

    if obj.evidence_level == EvidenceLevel.INSUFFICIENT:
        decision.disqualifiers.append("no usable source")
        decision.reason = "no source supports this object"
        decision.confidence = 0.9
        return decision

    if not obj.primary_sector:
        decision.disqualifiers.append("unclassified sector")
        decision.reason = "object has no primary sector"
        decision.confidence = 0.8
        return decision

    # ── Family rules ───────────────────────────────────────────────────────
    if family == "interview_or_opinion":
        if traits["has_material_disclosure"]:
            decision.eligible = True
            decision.confidence = 0.7
            decision.evidence = list(traits["material_disclosure_evidence"])
            decision.reason = "interview carries a material disclosure"
        else:
            decision.disqualifiers.append("no material disclosure")
            decision.reason = (
                "interview or opinion without a material disclosure; a prominent "
                "subject and a capital-markets biography are not intelligence"
            )
            decision.confidence = 0.75
        return decision

    if family in ("policy_or_macro", "data_or_signal"):
        # Deliberately no monetary requirement: a Fed decision, a rezoning or a
        # CPI print can be the most consequential item of the day.
        has_action = bool(_POLICY_ACTION.search(blob))
        has_numbers = bool(re.search(r"\d", blob))
        if has_action or has_numbers or obj.object_class in _NON_TRANSACTIONAL_CLASSES:
            decision.eligible = True
            decision.confidence = 0.7
            if has_action:
                decision.evidence.append("policy or decision verb present")
            if has_numbers:
                decision.evidence.append("quantified data present")
            decision.reason = "policy, macro or data item with a stated action or measurement"
        else:
            decision.disqualifiers.append("no action or measurement")
            decision.reason = "macro or policy item with neither a decision nor data"
            decision.confidence = 0.6
        return decision

    if family == "primary_document":
        decision.eligible = True
        decision.confidence = 0.85
        decision.evidence.append(f"primary source material ({content_type})")
        decision.reason = "primary document from an authoritative body"
        return decision

    # transaction_or_development: require evidence an event actually occurred.
    has_verb = traits["has_transaction_verb"]
    has_money = traits["has_monetary_amount"]
    has_scale = bool(_SCALE.search(blob))
    parties = [p for p in _NAMED_PARTY.findall(obj.title or "") if len(p) > 3]
    has_party = len(parties) >= 1

    if has_verb and (has_money or has_scale) and has_party:
        decision.eligible = True
        decision.confidence = 0.85
        decision.evidence = [
            "transaction verb present",
            "monetary amount present" if has_money else "physical scale present",
            f"named party: {parties[0]!r}",
        ]
        decision.reason = "named party performing a transaction with stated scale"
        return decision

    if has_verb and has_party and obj.independent_source_count >= 2:
        decision.eligible = True
        decision.confidence = 0.6
        decision.evidence = [
            "transaction verb present",
            f"named party: {parties[0]!r}",
            f"corroborated by {obj.independent_source_count} independent sources",
        ]
        decision.reason = "corroborated transaction without a disclosed amount"
        return decision

    missing = []
    if not has_verb:
        missing.append("no transaction verb")
    if not (has_money or has_scale):
        missing.append("no amount or scale")
    if not has_party:
        missing.append("no named party")
    decision.disqualifiers.extend(missing)
    decision.reason = (
        "no evidence a transaction or development occurred: " + ", ".join(missing)
    )
    decision.confidence = 0.7
    return decision


def apply(obj: IntelligenceObject, *, text: str = "") -> IntelligenceObject:
    """Assess and record the decision on the object itself."""
    decision = assess(obj, text=text)
    obj.eligible = decision.eligible
    obj.eligibility_reason = decision.reason
    obj.disqualifiers = list(decision.disqualifiers)
    traits = describe(obj.title, obj.what_happened, sector=obj.primary_sector)
    obj.content_type = traits["content_type"]
    if not obj.event_type:
        obj.event_type = traits["event_type"]
    if not obj.primary_subsector:
        obj.primary_subsector = traits["subsector"]
    obj.classification_confidence = traits["content_type_confidence"]
    obj.classification_evidence = list(traits["content_type_evidence"])
    return obj
