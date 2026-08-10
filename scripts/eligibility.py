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
    r"\b[\d,]+(?:\.\d+)?\s*(?:units?|sf|square feet|acres?|mw|megawatts?|rooms?|keys|bps|basis points)(?![A-Za-z])",
    re.I,
)
_MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?\s*(?:billion|bn|million|mm|trillion|[bmk])?\b", re.I)

_POLICY_ACTION = re.compile(
    r"\b(?:rais(?:e|ed|es)|cut|cuts|hold(?:s)?|lower(?:s|ed)?|approv\w+|reject\w+|"
    r"propos\w+|finaliz\w+|enact\w+|rul(?:e|ed|ing)|order(?:s|ed)?|"
    r"vote[sd]?|adopt\w+|impos\w+|ban(?:s|ned)?|mandat\w+)(?![A-Za-z])",
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


#: Government or regulatory action, in any sector. A moratorium on data centres,
#: a governor halting grid connections, a bank regulator changing capital rules
#: -- none of these have a transaction verb or a dollar figure, and all of them
#: matter. Routing by sector alone sent them to the transaction rules and threw
#: them away: 43 of 68 data-centre stories were rejected for "no transaction
#: verb" while being some of the most consequential items of the day.
_GOVERNMENT_ACTOR = re.compile(
    r"\b(?:gov(?:\.|ernor)|mayor|city council|council|commission(?:er)?|regulator|legislature|senate|senator|congress|parliament|state of|county|township|towns?|city of|municipalit\w+|administration|department of|agency|authority|court|judge|attorney general|white house|president (?:trump|biden|of the united states)|trump administration|ferc|fdic|occ|epa|hud|fhfa|cfpb|federal reserve|federal government|us treasury)(?![A-Za-z])",
    re.I,
)
_GOVERNMENT_ACTION = re.compile(
    r"\b(?:bans?|banned|banning|halts?|halted|halting|blocks?|blocked|moratorium|approv\w+|reject\w+|denie[sd]|rules?|ruled|ruling|orders?|ordered|mandat\w+|restrict\w+|prohibit\w+|legislat\w+|ordinance|zoning|rezon\w+|permits?|permitted|licen[cs]\w+|sanction\w+|tariffs?|regulat\w+|investigat\w+|sued?|lawsuit|incentives?|subsid\w+|signs?|signed|vetoe?[sd]?|enact\w+|passes|passed|introduce[sd]?|curtail\w+|caps?|capped)(?![A-Za-z])",
    re.I,
)


def _is_government_action(text: str) -> bool:
    """A public body doing something, whatever sector it lands in."""
    actor = bool(_GOVERNMENT_ACTOR.search(text))
    if not actor:
        actor = bool(re.search(
            r"\btrump\b(?=.{0,60}\b(?:ban|order|tariff|sanction|rule|bill|policy)\b)",
            text,
            re.I,
        ))
    return bool(actor and _GOVERNMENT_ACTION.search(text))


_BEAT_ANCHORS = {
    "commercial_real_estate": re.compile(
        r"\b(?:commercial real estate|real estate|reit|multifamily|apartments?|"
        r"office (?:building|tower|market|space|lease|property)|industrial(?: "
        r"(?:building|portfolio|property|space))?|warehouses?|logistics (?:facility|portfolio|property)|"
        r"shopping centers?|retail (?:center|property)|hotels?|hospitality|mixed-use|"
        r"student housing|senior housing|self-storage|affordable housing|"
        r"commercial propert(?:y|ies)|investment propert(?:y|ies)|acquisition debt|"
        r"construction (?:loan|financing)|commercial mortgage|cmbs|cre clo|"
        r"\d[\d,]*\s+(?:units?|square feet|sq\.?\s*ft\.?|sf)\b|"
        r"zoning|rezoning|land use|breaks? ground|savills|eastdil|cbre|jll|"
        r"cushman|newmark|colliers|prologis|vornado|sl green)\b",
        re.I,
    ),
    "private_equity": re.compile(
        r"\b(?:private equity|buyout|take-private|portfolio company|continuation vehicle|"
        r"secondaries|fund close|fundrais\w+|general partner|limited partner|"
        r"private markets|sponsor-backed|growth equity|leveraged buyout|lp-led|gp-led)\b",
        re.I,
    ),
    "data_centers": re.compile(
        r"\b(?:data cent(?:er|re)s?|datacenter|hyperscale|colocation|server farm|"
        r"compute campus|ai infrastructure|gpu cloud|power (?:campus|demand)|megawatts?|gw)\b",
        re.I,
    ),
    "energy": re.compile(
        r"\b(?:power grid|electric utilit\w+|electricity|generation capacity|renewable|"
        r"solar|wind farm|battery storage|energy infrastructure|transmission|pipeline|"
        r"natural gas|lng|oil|nuclear|ferc|interconnection)\b",
        re.I,
    ),
    "banking_credit": re.compile(
        r"\b(?:banks?|lenders?|lending|credit|commercial loans?|deposits?|"
        r"capital requirements?|loan losses?|charge-offs?|fdic|occ|cfpb|"
        r"financial institutions?|private credit|direct lending|mortgage|cmbs|"
        r"ism|pmi|manufacturing sector)\b",
        re.I,
    ),
    "fed_macro": re.compile(
        r"\b(?:federal reserve|fomc|fed funds?|interest rates?|inflation|cpi|ppi|"
        r"gdp|payrolls?|unemployment|treasury (?:yield|market|securities)|yield curve|"
        r"monetary policy|financial conditions|strips?)\b",
        re.I,
    ),
    "local_government": re.compile(
        r"\b(?:city council|planning commission|zoning|rezoning|land use|housing|"
        r"development|property tax|tax abatement|building permits?|mayor|governor|"
        r"municipal|county)\b",
        re.I,
    ),
}

_CONSUMER_PROPERTY = re.compile(
    r"\b(?:single-family home|historic house|dream home|celebrity mansion|homebuyer|"
    r"homeowner|house (?:for sale|selling)|condo of the week)\b",
    re.I,
)


def _has_beat_anchor(obj: IntelligenceObject, text: str) -> bool:
    pattern = _BEAT_ANCHORS.get(obj.primary_sector)
    if pattern is None:
        return False
    if obj.primary_sector == "commercial_real_estate" and _CONSUMER_PROPERTY.search(text):
        institutional = re.search(
            r"\b(?:commercial|multifamily|apartments?|portfolio|reit|development|"
            r"office (?:building|tower)|industrial|mixed-use|affordable housing)\b",
            text,
            re.I,
        )
        if not institutional:
            return False
    return bool(pattern.search(text))


def _event_family(obj: IntelligenceObject, traits: dict[str, Any]) -> str:
    """Which set of rules applies to this object.

    Nature first, sector second. What a story *is* decides how it should be
    judged; the sector it belongs to is only a fallback.
    """
    if obj.object_class in _NON_TRANSACTIONAL_CLASSES:
        return "data_or_signal"
    content_type = traits["content_type"]
    if content_type in (ContentType.INTERVIEW, ContentType.OPINION):
        return "interview_or_opinion"
    if content_type == ContentType.DATA_PUBLICATION:
        return "data_or_signal"
    if content_type in ContentType.PRIMARY_AUTHORITY:
        return "primary_document"
    # Government action outranks the sector default.
    if _is_government_action(f"{obj.title} {obj.what_happened}"):
        return "policy_or_macro"
    if obj.primary_sector in _NON_TRANSACTIONAL_SECTORS:
        return "policy_or_macro"
    return "transaction_or_development"


def assess(obj: IntelligenceObject, *, text: str = "") -> EligibilityDecision:
    """Decide eligibility for one object."""
    blob = text or f"{obj.title} {obj.what_happened}"
    source_type = "government" if any(
        source.is_primary_authority for source in obj.sources
    ) else ""
    traits = describe(
        obj.title,
        obj.what_happened,
        sector=obj.primary_sector,
        source_type=source_type,
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

    if not _has_beat_anchor(obj, blob):
        decision.disqualifiers.append("no Light Tower beat anchor")
        decision.reason = (
            f"item is classified as {obj.primary_sector} but contains no specific "
            "institutional capital-markets or real-assets anchor"
        )
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
        # Use the same, broader action vocabulary that routed this here.
        # The narrower list missed "halts" and "banning" entirely, so a
        # governor halting grid connections reached the right family and
        # was then rejected inside it.
        has_action = bool(_POLICY_ACTION.search(blob) or _GOVERNMENT_ACTION.search(blob))
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
    source_type = "government" if any(
        source.is_primary_authority for source in obj.sources
    ) else ""
    traits = describe(
        obj.title,
        obj.what_happened,
        sector=obj.primary_sector,
        source_type=source_type,
    )
    obj.content_type = traits["content_type"]
    if not obj.event_type:
        obj.event_type = traits["event_type"]
    if not obj.primary_subsector:
        obj.primary_subsector = traits["subsector"]
    obj.classification_confidence = traits["content_type_confidence"]
    obj.classification_evidence = list(traits["content_type_evidence"])
    return obj
