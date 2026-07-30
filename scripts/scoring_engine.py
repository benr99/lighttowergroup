"""Multi-sector scoring engine for the Light Tower Insights pipeline.

Scores every classified CanonicalItem on 10 dimensions using sector-specific
weight profiles from config/scoring_profiles.json. 

All scores are deterministic — no LLM calls. The scoring engine uses:
- Extracted financial values (dollar amounts, MW, sq ft, etc.)
- Entity recognition against watchlists
- Source quality tiers
- Timeliness (age of story)
- Cross-sector impact (number of secondary sectors)
"""

from __future__ import annotations
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from canonical_item import CanonicalItem

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SITE_ROOT / "config"

_AMOUNT_RE = re.compile(r'\$\s*([\d,.]+)\s*(million|billion|trillion|mm|bn|m|b)?', re.IGNORECASE)
_MW_RE = re.compile(r'([\d,.]+)[-\s]*(?:mw|megawatt)', re.IGNORECASE)

_MARKET_IMPACT_RE: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\b(?:record|largest|first|historic|unprecedented)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:repric\w*|reset\w*|shift\w*|signal\w*|trend)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(?:ripple|spillover|contagion|systemic)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:federal reserve|fomc|rate hike|rate cut)\b", re.IGNORECASE), 4),
    (re.compile(r"\b(?:bankruptcy|default|insolven\w*)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:industry.wide|market.wide|across the sector)\b", re.IGNORECASE), 2),
]

_STRATEGIC_CRE_RE: list[re.Pattern] = [
    re.compile(r"\b(?:sponsor|developer|lender|borrower|investor|owner|operator)\b", re.IGNORECASE),
    re.compile(r"\b(?:development|construction|refinanc|acquisition)\b", re.IGNORECASE),
]

_STRATEGIC_CAPITAL_RE: list[re.Pattern] = [
    re.compile(r"\b(?:debt|equity|capital|fund|investment|financing)\b", re.IGNORECASE),
    re.compile(r"\b(?:return|yield|cap rate|valuation|pricing)\b", re.IGNORECASE),
]

_POLICY_IMPACT_RE: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\b(?:federal reserve|fomc|fed chair|governor.*fed)\b", re.IGNORECASE), 4),
    (re.compile(r"\b(?:congress|senate|house.*passed|signed into law|legislation)\b", re.IGNORECASE), 4),
    (re.compile(r"\b(?:fdic|occ|sec|cfpb|fhfa|hud.*rule|treasury.*rule)\b", re.IGNORECASE), 4),
    (re.compile(r"\b(?:regulation|regulatory|compliance|capital requirement)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:zoning|rezoning|land.use|entitlement|building code)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:tax.*change|tariff|subsidy|tax credit|abatement)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(?:supreme court|federal court|appeals court|ruling)\b", re.IGNORECASE), 3),
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


_profiles_cache: dict[str, Any] | None = None
_thresholds_cache: dict[str, Any] | None = None
_watchlists_cache: dict[str, Any] | None = None
_cache_lock = threading.Lock()


def _get_profiles() -> dict[str, Any]:
    global _profiles_cache
    with _cache_lock:
        if _profiles_cache is None:
            _profiles_cache = _load_json(CONFIG_DIR / "scoring_profiles.json").get("profiles", {})
        return _profiles_cache


def _get_watchlists() -> dict[str, Any]:
    global _watchlists_cache
    with _cache_lock:
        if _watchlists_cache is None:
            _watchlists_cache = _load_json(CONFIG_DIR / "watchlists.json").get("entities", {})
        return _watchlists_cache


def _get_thresholds() -> dict[str, Any]:
    global _thresholds_cache
    with _cache_lock:
        if _thresholds_cache is None:
            _thresholds_cache = _load_json(CONFIG_DIR / "thresholds.json")
        return _thresholds_cache


def _clear_caches() -> None:
    global _profiles_cache, _watchlists_cache, _thresholds_cache
    with _cache_lock:
        _profiles_cache = None
        _watchlists_cache = None
        _thresholds_cache = None


def _get_entity_tier(name: str, watchlists: dict[str, Any]) -> int:
    """Get the tier of an entity based on watchlist membership."""
    if not name or not name.strip():
        return 5  # Unknown / empty entity
    name_lower = name.lower()
    for tier_key in ["tier_1_institutions", "tier_2_companies", "tier_3_firms"]:
        tier_data = watchlists.get(tier_key, {})
        companies = tier_data.get("companies", [])
        for company in companies:
            if company.lower() in name_lower or name_lower in company.lower():
                return int(tier_key.split("_")[1])  # "1", "2", or "3"
    return 5  # Unknown entity


def _extract_amounts(text: str) -> list[float]:
    """Extract dollar amounts from text, normalized to dollars."""
    amounts = []
    for match in _AMOUNT_RE.finditer(text):
        try:
            value = float(match.group(1).replace(",", ""))
            unit = (match.group(2) or "").lower()
            if unit in ("billion", "bn", "b"):
                value *= 1_000_000_000
            elif unit in ("million", "mm", "m"):
                value *= 1_000_000
            amounts.append(value)
        except ValueError:
            continue
    return amounts


def _extract_megawatts(text: str) -> float:
    """Extract megawatt figures from text."""
    for match in _MW_RE.finditer(text):
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            continue
    return 0.0


def _score_financial_magnitude(item: CanonicalItem) -> int:
    """Score financial magnitude based on extracted values relative to sector norms."""
    text = f"{item.headline} {item.raw_summary}"
    amounts = _extract_amounts(text)
    max_amount = max(amounts) if amounts else 0.0
    megawatts = item.megawatts if item.megawatts > 0 else _extract_megawatts(text)
    
    sector = item.primary_sector
    
    # Sector-specific magnitude thresholds (in dollars)
    thresholds = {
        "commercial_real_estate": [1e6, 10e6, 50e6, 100e6, 500e6, 1e9, 5e9],
        "private_equity": [10e6, 50e6, 100e6, 500e6, 1e9, 5e9, 10e9],
        "data_centers": [5e6, 25e6, 100e6, 250e6, 500e6, 1e9, 5e9],
        "energy": [10e6, 50e6, 100e6, 500e6, 1e9, 5e9, 10e9],
        "banking_credit": [1e6, 10e6, 50e6, 100e6, 500e6, 1e9, 5e9],
        "fed_macro": [0, 0, 0, 0, 0, 0, 0],  # Not financial-magnitude-driven
        "local_government": [100e3, 1e6, 5e6, 25e6, 100e6, 500e6, 1e9],
    }
    
    sector_thresholds = thresholds.get(sector, thresholds["commercial_real_estate"])
    
    if sector == "fed_macro":
        score = 6 if "fomc" in text.lower() or "rate decision" in text.lower() else 3
        return min(10, max(1, score))

    # Score by threshold bucket
    score = 1
    for threshold in sector_thresholds:
        if max_amount >= threshold:
            score += 1
    
    # Bonus for data center megawatt scale
    if sector == "data_centers" and megawatts > 0:
        if megawatts >= 500: score = min(10, score + 3)
        elif megawatts >= 200: score = min(10, score + 2)
        elif megawatts >= 50: score = min(10, score + 1)
    
    return min(10, max(1, score))


def _score_party_significance(item: CanonicalItem) -> int:
    """Score based on whether entities appear in watchlists."""
    watchlists = _get_watchlists()
    all_entities = item.companies + item.buyers + item.sellers + item.lenders + item.developers
    
    if not all_entities:
        # Try to find known entities in text
        text_lower = f"{item.headline} {item.raw_summary} {item.raw_text}".lower()
        for tier_key in ["tier_1_institutions", "tier_2_companies"]:
            for company in watchlists.get(tier_key, {}).get("companies", []):
                if company.lower() in text_lower:
                    all_entities.append(company)
    
    best_tier = 5
    for entity in all_entities:
        tier = _get_entity_tier(entity, watchlists)
        best_tier = min(best_tier, tier)
    
    scores = {1: 10, 2: 7, 3: 4, 5: 1}
    return scores.get(best_tier, 1)


def _score_market_impact(item: CanonicalItem) -> int:
    """Score market impact based on event type and magnitude signals."""
    text = f"{item.headline} {item.raw_summary}".lower()
    score = 3  # base
    
    for pattern, bonus in _MARKET_IMPACT_RE:
        if pattern.search(text):
            score += bonus
    
    return min(10, max(1, score))


def _score_strategic_relevance(item: CanonicalItem) -> int:
    """Score relevance to Light Tower's audience."""
    text = f"{item.headline} {item.raw_summary}".lower()
    score = 3  # base
    
    for pattern in _STRATEGIC_CRE_RE:
        if pattern.search(text):
            score += 1
    
    for pattern in _STRATEGIC_CAPITAL_RE:
        if pattern.search(text):
            score += 1
    
    # Sector bonus — some sectors are inherently more relevant
    sector_bonus = {
        "commercial_real_estate": 2,
        "private_equity": 1,
        "data_centers": 0,
        "energy": 0,
        "banking_credit": 1,
        "fed_macro": 1,
        "local_government": 1,
    }
    score += sector_bonus.get(item.primary_sector, 0)
    
    return min(10, max(1, score))


def _score_policy_impact(item: CanonicalItem) -> int:
    """Score regulatory and policy impact."""
    text = f"{item.headline} {item.raw_summary}".lower()
    score = 2  # base
    
    for pattern, bonus in _POLICY_IMPACT_RE:
        if pattern.search(text):
            score += bonus
    
    return min(10, max(1, score))


def _score_source_quality(item: CanonicalItem) -> int:
    """Score based on source tier and authority."""
    tier = item.source_tier
    if tier < 1:
        tier = 5
    elif tier > 5:
        tier = 5
    authority = item.source_authority
    scores = {1: 10, 2: 7, 3: 5, 4: 3, 5: 1}
    base = scores.get(tier, 3)
    if authority == "primary":
        base = min(10, base + 2)
    return base


def _score_timeliness(item: CanonicalItem) -> int:
    """Score based on story age in hours."""
    hours = item.age_hours()
    if hours <= 1:
        return 10
    elif hours <= 6:
        return 9
    elif hours <= 12:
        return 8
    elif hours <= 24:
        return 7
    elif hours <= 48:
        return 5
    elif hours <= 72:
        return 3
    else:
        return 1


def _score_editorial_potential(item: CanonicalItem) -> int:
    """Score based on available information for writing."""
    text = f"{item.headline} {item.raw_summary} {item.raw_text}"
    word_count = len(text.split())
    
    # Amount of text available
    if word_count > 2000: score = 10
    elif word_count > 1000: score = 8
    elif word_count > 500: score = 6
    elif word_count > 200: score = 4
    else: score = 2
    
    # Named entities = more to write about
    entities = item.companies + item.people
    if len(entities) >= 5: score = min(10, score + 2)
    elif len(entities) >= 2: score = min(10, score + 1)
    
    return min(10, max(1, score))


def _score_cross_sector_impact(item: CanonicalItem) -> int:
    """Score based on how many sectors the story touches."""
    count = len(item.secondary_sectors)
    # Primary sector counts as 1, each secondary adds
    total = 1 + count
    if total >= 5: return 10
    elif total >= 4: return 8
    elif total >= 3: return 6
    elif total >= 2: return 4
    else: return 2


def score_item(item: CanonicalItem) -> CanonicalItem:
    """Score a single classified CanonicalItem using its sector's weight profile.
    
    Computes all 10 dimension scores, applies the sector-specific weight multipliers,
    calculates the composite score, and assigns a tier.
    """
    profiles = _get_profiles()
    tier_boundaries = _get_thresholds().get("tier_boundaries", {})
    
    sector = item.primary_sector or "commercial_real_estate"
    profile = profiles.get(sector, profiles.get("commercial_real_estate", {}))
    
    # Compute raw dimension scores
    raw_scores = {
        "financial_magnitude": _score_financial_magnitude(item),
        "party_significance": _score_party_significance(item),
        "market_impact": _score_market_impact(item),
        "strategic_relevance": _score_strategic_relevance(item),
        "policy_impact": _score_policy_impact(item),
        "novelty": 7,  # Default — requires event memory for real novelty scoring
        "source_quality": _score_source_quality(item),
        "timeliness": _score_timeliness(item),
        "editorial_potential": _score_editorial_potential(item),
        "cross_sector_impact": _score_cross_sector_impact(item),
    }
    
    # Apply sector-specific weights
    weighted_sum = 0.0
    weight_sum = 0.0
    for dim, score in raw_scores.items():
        weight = profile.get(dim, 1.0)
        weighted_sum += score * weight
        weight_sum += weight
    
    # Compute composite score (0-100)
    composite = round((weighted_sum / weight_sum) * 10, 1) if weight_sum > 0 else 0.0
    
    # Assign tier
    if composite >= tier_boundaries.get("tier_1_must_cover", 80):
        tier = "tier_1_must_cover"
    elif composite >= tier_boundaries.get("tier_2_strongly_recommended", 65):
        tier = "tier_2_strongly_recommended"
    elif composite >= tier_boundaries.get("tier_3_useful_coverage", 50):
        tier = "tier_3_useful_coverage"
    elif composite >= tier_boundaries.get("tier_4_reserve", 35):
        tier = "tier_4_reserve"
    else:
        tier = "rejected"
    
    item.set_scoring(raw_scores, composite, sector, tier)
    return item


def score_batch(items: list[CanonicalItem]) -> list[CanonicalItem]:
    """Score a batch of classified items."""
    _clear_caches()
    results = []
    for item in items:
        scored = score_item(item)
        results.append(scored)
    return results


def get_scoring_stats(items: list[CanonicalItem]) -> dict[str, Any]:
    """Compute scoring statistics for the batch."""
    tiers = {}
    sectors = {}
    for item in items:
        t = item.tier or "unknown"
        tiers[t] = tiers.get(t, 0) + 1
        s = item.primary_sector or "unknown"
        if s not in sectors:
            sectors[s] = {"count": 0, "avg_composite": 0.0, "top_5": []}
        sectors[s]["count"] += 1
    
    for item in items:
        s = item.primary_sector or "unknown"
        if s in sectors:
            sectors[s]["avg_composite"] += item.composite_score
    
    for s in sectors:
        if sectors[s]["count"] > 0:
            sectors[s]["avg_composite"] = round(sectors[s]["avg_composite"] / sectors[s]["count"], 1)
    
    return {
        "total_items": len(items),
        "tier_distribution": tiers,
        "sector_stats": {s: {"count": d["count"], "avg_composite": d["avg_composite"]} for s, d in sorted(sectors.items())},
    }
