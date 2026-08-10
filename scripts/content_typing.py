"""Classify what a document *is* before asking how important it is.

The v2 pipeline never populated `event_type` or `subsector` -- both were
hardcoded to "" with a "TODO Phase 2" comment -- so nothing downstream could
tell a completed transaction from a vendor explainer. Eligibility therefore fell
back to a single keyword OR-match over headline plus summary, and an
edge-computing explainer entered a three-story edition on the incidental phrase
"data center" while a promotional interview entered on "investment" and
"subsidiary" appearing in the subject's biography.

Content type is the missing gate. Marketing, explainers, listicles and personnel
notices are never editorial intelligence. Interviews and opinion are *not*
blanket-excluded -- they qualify on material disclosure, which is tested
separately, per the editorial mandate.

Everything here is deterministic and returns its evidence, so a classification
can be explained and regression-tested. Semantic escalation is reserved for
genuinely ambiguous cases and is not required for correctness.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from intelligence_object import ContentType

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@lru_cache(maxsize=1)
def _sector_taxonomy() -> dict[str, Any]:
    try:
        data = json.loads((CONFIG_DIR / "sectors.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("sectors", data)


# ── Content-type signals ───────────────────────────────────────────────────
# Ordered: the first matching rule wins, most specific first.

_CONTENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (ContentType.ADMINISTRATIVE_NOTICE, re.compile(
        r"^(?:agency information collection activities|sunshine act meetings?|"
        r"submission for omb review|comment request on .+ forms?|"
        r"joint industry plan;?\s+order|notice of (?:public )?meeting|"
        r"information collection request|request for comments? on information collection)\b",
        re.I)),
    (ContentType.DIGEST, re.compile(
        r"\b(?:sunday summary|week(?:ly|end) (?:roundup|recap|digest)|daily digest|"
        r"morning news|recent news from .{1,100}:\s*(?:jan|feb|mar|apr|may|jun|jul|"
        r"aug|sep|oct|nov|dec)\.?\s+\d{1,2})\b", re.I)),
    (ContentType.EVENT_PROMOTION, re.compile(
        r"\b(?:webinar|register (?:now|today)|save the date|join us|"
        r"conference|summit|expo|awards? (?:gala|dinner|ceremony)|nominations? open)\b", re.I)),
    (ContentType.MARKETING, re.compile(
        r"\b(?:sponsored|advertorial|partner content|brought to you by|"
        r"our (?:solution|platform|product)|contact us today|request a demo|"
        r"white ?paper|case study|sign up for|subscribe to|newsletter sign[- ]?up|"
        r"request access|invalid feed)\b", re.I)),
    (ContentType.LISTICLE, re.compile(
        r"\b(?:top \d+|best \d+|\d+ (?:ways|things|tips|reasons|trends|predictions)|"
        r"ranking of|the \d+ (?:best|worst))\b", re.I)),
    (ContentType.EXPLAINER, re.compile(
        r"(?:\bwhat is\b|\bhow (?:to|do(?:es)? \w+ work)\b|\bexplained\b|"
        r"\bguide to\b|\bbeginner'?s?\b|\bprimer\b|\b101\b|\bfundamentals\b|"
        r"\bchoosing the right\b|\bvs\.?\s|\bversus\b|\bunderstanding\b|"
        r"\bwhen to use\b|\bpros and cons\b|\bTL;?DR\b)", re.I)),
    (ContentType.PERSONNEL_NOTICE, re.compile(
        r"\b(?:appoints?|names?|hires?|promotes?|joins?|welcomes?|"
        r"steps? down|retires?|departs?|new (?:chief|head of|managing director)|"
        r"expands? \w+ team|bolsters? \w+ team)\b", re.I)),
    (ContentType.INTERVIEW, re.compile(
        r"\b(?:talks|interview|q ?& ?a|sits down|in conversation|discusses|"
        r"on the record|speaks (?:with|to)|shares (?:his|her|their) (?:views|outlook))\b", re.I)),
    (ContentType.EARNINGS_MATERIAL, re.compile(
        r"\b(?:q[1-4]\s*(?:20\d\d)?\s*(?:results|earnings)|"
        r"(?:first|second|third|fourth)[- ]quarter (?:results|earnings)|"
        r"full[- ]year results|earnings call|reports? (?:net income|revenue|ffo))\b", re.I)),
    (ContentType.REGULATORY_FILING, re.compile(
        r"\b(?:8-k|10-k|10-q|s-1|13[dfg]|form d|prospectus|proxy statement|"
        r"sec filing|files? with the sec)\b", re.I)),
    (ContentType.DATA_PUBLICATION, re.compile(
        r"\b(?:index (?:rose|fell|increased|declined)|cpi|ppi|ism|pmi|"
        r"(?:non-?farm )?payrolls|unemployment rate|gdp (?:grew|rose|fell|expanded|contracted)|"
        r"consumer price|producer price|housing starts|building permits|"
        r"economic indicators?|data release|survey (?:shows|finds)|"
        r"sector (?:expanded|contracted)|(?:rose|fell|climbed|declined) (?:to|by) [\d.]+%?|"
        r"reading (?:of|came in)|beat|missed) ", re.I)),
    (ContentType.RESEARCH_REPORT, re.compile(
        r"\b(?:research (?:note|report)|working paper|study finds|"
        r"analysis (?:shows|finds)|according to (?:a|the) (?:new )?report|"
        r"outlook report|market report)\b", re.I)),
    (ContentType.OPINION, re.compile(
        r"\b(?:opinion|commentary|viewpoint|column|editorial|"
        r"why i |we (?:believe|think)|the case for|the case against|"
        r"op-?ed)\b", re.I)),
    (ContentType.PRESS_RELEASE, re.compile(
        r"\b(?:announced today|is pleased to announce|today announced|"
        r"press release|/PRNewswire|business ?wire)\b", re.I)),
)

#: A transaction verb bound to real activity. Presence of one of these is what
#: separates "an event happened" from "this text mentions capital".
_TRANSACTION_VERBS = re.compile(
    r"\b(?:acquir\w+|purchas\w+|sold|sells?|buys?|bought|merg\w+|"
    r"clos(?:e|ed|es|ing)|financ\w+|refinanc\w+|originat\w+|lend[s]?|lent|"
    r"rais\w+|launch\w+|invest(?:s|ed|ing)?|commit(?:s|ted)?|"
    r"approv\w+|reject\w+|rezon\w+|permit(?:s|ted)?|"
    r"default\w*|foreclos\w+|restructur\w+|file[sd]? for bankruptcy|"
    r"break(?:s|ing)? ground|deliver\w+|lease[sd]?|sign(?:s|ed)?|"
    r"back(?:s|ed)|anchor(?:s|ed)|underwrit\w+|arrang\w+|broker(?:s|ed)|"
    r"secur(?:es|ed)|obtain(?:s|ed)|land(?:s|ed)|award(?:s|ed)|negotiat\w+|"
    # Transaction nouns: headlines routinely nominalise the action
    # ("JLL Negotiates Sale of...", "Acquisition of ... Completed").
    r"sale|acquisition|disposition|merger|refinancing|recapitalization|"
    r"foreclosure|securitization|joint venture)\b",
    re.I,
)

_MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?\s*(?:billion|bn|million|mm|trillion|[bmk])?\b", re.I)

#: Signals that an interview or opinion piece carries real intelligence.
_MATERIAL_DISCLOSURE = (
    ("stated_allocation", re.compile(
        r"\b(?:will (?:allocate|deploy|invest)|plans? to (?:allocate|deploy|invest|raise|sell|buy)|"
        r"targeting \$|earmarked \$|committing \$)", re.I)),
    ("named_transaction", re.compile(
        r"\b(?:we (?:acquired|bought|sold|closed|financed)|"
        r"(?:acquired|sold|closed) (?:a|an|the) \$)", re.I)),
    ("strategy_change", re.compile(
        r"\b(?:we(?:'re| are) (?:exiting|entering|shifting|pivoting|pulling back|stepping back)|"
        r"no longer (?:buying|lending|investing)|moving (?:away from|into))\b", re.I)),
    ("forward_guidance", re.compile(
        r"\b(?:we expect \w+ to (?:rise|fall|decline|increase)|"
        r"we (?:forecast|project|anticipate)|by (?:the end of )?20\d\d we)\b", re.I)),
    ("proprietary_data", re.compile(
        r"\b(?:our (?:data|portfolio|book|research) shows|"
        r"across our \$?[\d,]+|in our portfolio(?: of)?)\b", re.I)),
    ("risk_warning", re.compile(
        r"\b(?:we(?:'re| are) (?:worried|concerned) (?:about|that)|"
        r"the (?:biggest|real) risk is|we see (?:stress|distress|trouble))\b", re.I)),
)


def classify_content_type(
    headline: str,
    summary: str = "",
    *,
    source_type: str = "",
) -> tuple[str, float, list[str]]:
    """Return (content_type, confidence, evidence spans)."""
    headline = headline or ""
    summary = summary or ""
    blob = f"{headline} {summary}"

    matches: list[tuple[str, float, str]] = []
    for content_type, pattern in _CONTENT_RULES:
        # Headline evidence outweighs body evidence: boilerplate lives in bodies.
        found = pattern.search(headline)
        if found:
            matches.append((content_type, 0.85, f"headline: {found.group(0)!r}"))
            continue
        found = pattern.search(summary)
        if found:
            matches.append((content_type, 0.6, f"summary: {found.group(0)!r}"))

    if matches:
        content_type, confidence, evidence = matches[0]
        # A transaction verb plus money in the headline outranks a weak
        # body-only signal: real deal coverage often quotes an executive.
        if confidence < 0.85 and _TRANSACTION_VERBS.search(headline) and _MONEY.search(headline):
            return ContentType.NEWS_REPORT, 0.75, [
                "headline states a transaction with an amount",
                f"(overrode weak {content_type} signal: {evidence})",
            ]
        return content_type, confidence, [evidence]

    # Primary provenance is meaningful, but it cannot convert a procedural
    # notice or another known low-value content shape into editorial signal.
    if source_type in {"government", "government_research", "regulator"}:
        return ContentType.PRIMARY_DOCUMENT, 0.9, [f"source_type={source_type}"]

    if _TRANSACTION_VERBS.search(blob):
        return ContentType.NEWS_REPORT, 0.7, ["transaction verb present"]
    return ContentType.UNKNOWN, 0.3, ["no distinguishing signal"]


def has_material_disclosure(text: str) -> tuple[bool, list[str]]:
    """Does an interview or opinion piece carry real intelligence?

    A prominent subject and a capital-markets biography are not disclosure.
    """
    evidence = []
    for name, pattern in _MATERIAL_DISCLOSURE:
        found = pattern.search(text or "")
        if found:
            evidence.append(f"{name}: {found.group(0)!r}")
    return bool(evidence), evidence


def classify_event_type(text: str, sector: str) -> tuple[str, float, list[str]]:
    """Map text to one of the sector's configured event types."""
    taxonomy = _sector_taxonomy().get(sector) or {}
    event_types: list[str] = list(taxonomy.get("event_types") or [])
    if not event_types:
        return "", 0.0, []

    blob = (text or "").lower()
    best: tuple[str, int, str] | None = None
    for event_type in event_types:
        words = [w for w in event_type.split("_") if len(w) > 2]
        if not words:
            continue
        hits = [w for w in words if re.search(rf"\b{re.escape(w)}\w*", blob)]
        if len(hits) == len(words) and words:
            return event_type, 0.8, [f"all terms of {event_type!r} present"]
        # A single shared word is noise -- "water" in an edge-computing piece
        # once matched `wastewater`-adjacent types. Require at least two terms
        # before proposing a partial match, and label the low confidence.
        if len(hits) >= 2 and (best is None or len(hits) > best[1]):
            best = (event_type, len(hits), f"partial match on {hits}")
    if best:
        return best[0], 0.45, [best[2]]
    return "", 0.0, []


def classify_subsector(text: str, sector: str) -> tuple[str, float, list[str]]:
    """Map text to one of the sector's configured subsectors."""
    taxonomy = _sector_taxonomy().get(sector) or {}
    subsectors: list[str] = list(taxonomy.get("subsectors") or [])
    if not subsectors:
        return "", 0.0, []

    blob = (text or "").lower()
    aliases = {
        "multifamily": ["multifamily", "apartment", "rental housing", "units"],
        "industrial_logistics": ["industrial", "logistics", "warehouse", "distribution center"],
        "office": ["office tower", "office building", "office space", "office market"],
        "retail": ["retail", "shopping center", "mall", "grocery-anchored"],
        "hospitality": ["hotel", "hospitality", "resort", "keys"],
        "self_storage": ["self storage", "self-storage"],
        "student_housing": ["student housing"],
        "senior_housing": ["senior housing", "assisted living"],
        "medical_office": ["medical office", "mob"],
        "life_sciences": ["life science", "lab space"],
        "mixed_use": ["mixed-use", "mixed use"],
        "data_center": ["data center", "data centre"],
        "hyperscale": ["hyperscale", "hyperscaler"],
        "colocation": ["colocation", "colo "],
        "powered_land": ["powered land", "powered shell"],
        "continuation_vehicle": ["continuation vehicle", "continuation fund"],
        "fund_close": ["closes", "final close", "closed on"],
        "fundraising": ["raises", "raising", "fundraise"],
        "private_credit": ["private credit", "direct lending"],
        "cmbs": ["cmbs", "securitization", "conduit"],
        "regional_banks": ["regional bank"],
        "major_banks": ["jpmorgan", "bank of america", "citigroup", "wells fargo", "goldman"],
        "solar": ["solar", "photovoltaic"],
        "wind": ["wind farm", "offshore wind", "onshore wind"],
        "nuclear": ["nuclear", "reactor", "smr"],
        "battery_storage": ["battery storage", "bess", "energy storage"],
        "transmission": ["transmission line", "transmission project"],
        "inflation": ["inflation", "cpi", "consumer price"],
        "employment": ["payrolls", "unemployment", "jobs report", "labor market"],
        "gdp": ["gdp", "gross domestic product"],
        "fomc": ["fomc", "federal open market committee"],
        "rate_decisions": ["rate decision", "raised rates", "cut rates", "holds rates"],
        "fed_speeches": ["speech", "testimony", "remarks"],
        "housing_data": ["housing starts", "home sales", "mortgage rate"],
        "rezoning_decision": ["rezoning", "rezone"],
        "zoning_board": ["zoning board", "zoning"],
        "city_council": ["city council", "council approved"],
    }
    for subsector in subsectors:
        terms = aliases.get(subsector, [subsector.replace("_", " ")])
        for term in terms:
            if re.search(rf"\b{re.escape(term)}", blob):
                return subsector, 0.75, [f"matched {term!r}"]
    return "", 0.0, []


def describe(headline: str, summary: str = "", *, sector: str = "",
             source_type: str = "") -> dict[str, Any]:
    """Full classification pass for one document."""
    content_type, ct_conf, ct_evidence = classify_content_type(
        headline, summary, source_type=source_type
    )
    blob = f"{headline} {summary}"
    event_type, et_conf, et_evidence = classify_event_type(blob, sector)
    subsector, ss_conf, ss_evidence = classify_subsector(blob, sector)
    disclosure, disclosure_evidence = has_material_disclosure(blob)
    return {
        "content_type": content_type,
        "content_type_confidence": ct_conf,
        "content_type_evidence": ct_evidence,
        "event_type": event_type,
        "event_type_confidence": et_conf,
        "event_type_evidence": et_evidence,
        "subsector": subsector,
        "subsector_confidence": ss_conf,
        "subsector_evidence": ss_evidence,
        "has_material_disclosure": disclosure,
        "material_disclosure_evidence": disclosure_evidence,
        "has_transaction_verb": bool(_TRANSACTION_VERBS.search(blob)),
        "has_monetary_amount": bool(_MONEY.search(blob)),
    }
