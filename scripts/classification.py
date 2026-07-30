"""Multi-label sector and event type classification for news items.

Classifies every ingested story into primary sector, secondary sectors,
event type, subsector, and geography. Uses source-based priors, regex
pattern matching, entity recognition against watchlists, and optional
LLM for ambiguous cases.

No story is ever rejected at this stage — only classified.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from canonical_item import CanonicalItem

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SITE_ROOT / "config"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_sectors() -> dict[str, Any]:
    return _load_json(CONFIG_DIR / "sectors.json").get("sectors", {})


def _load_watchlists() -> dict[str, Any]:
    return _load_json(CONFIG_DIR / "watchlists.json").get("entities", {})


# Sector-indicator keyword patterns — broad signals, NOT hard gates
# Compiled regex patterns for performance
_SECTOR_SIGNALS: dict[str, list[str]] = {
    "commercial_real_estate": [
        r"\b(?:multifamily|apartment building|office building|retail center|industrial property|warehouse|"
        r"mixed.use|commercial real estate|cap rate|occupancy|tenant|landlord|lease|sq.?ft|"
        r"square feet|cmbs|noi|dscr|ltv|refinanc\w*|bridge loan|construction loan|"
        r"ground lease|sale.leaseback|joint venture.*real estate)\b"
    ],
    "private_equity": [
        r"\b(?:buyout|take.private|leveraged buyout|growth equity|platform acquisition|"
        r"add.on acquisition|sponsor.*exit|continuation (?:fund|vehicle)|secondary sale|"
        r"gp.led|fund close|fundraising|private credit|direct lending|nav financing|"
        r"subscription facility|structured equity|portfolio company|carried interest)\b"
    ],
    "data_centers": [
        r"\b(?:data center|datacenter|hyperscale|colocation|edge data|powered land|"
        r"cloud infrastructure|server farm|fiber network|subsea cable|"
        r"gpu cluster|ai infrastructure.*data|compute capacity|rack space|"
        r"power usage effectiveness|pue|cooling system.*data|redundant power)\b"
    ],
    "energy": [
        r"\b(?:power (?:plant|generation|grid)|electric utility|natural gas|nuclear reactor|"
        r"solar farm|wind farm|battery storage|transmission line|pipeline|"
        r"lng (?:terminal|export)|microgrid|distributed generation|interconnection queue|"
        r"capacity market|power purchase agreement|ppa|renewable energy credit|"
        r"rate base|utility commission|ferc|nerc|rto|iso)\b"
    ],
    "banking_credit": [
        r"\b(?:bank (?:failure|merger|acquisition|regulation)|"
        r"loan.loss (?:reserve|provision)|charge.off|credit quality|"
        r"lending standard|capital ratio|basel|ccar|stress test|"
        r"fdic.*insured|occ.*cease|cease.and.desist|consent order|"
        r"community reinvestment act|cra.*exam|camels rating|"
        r"brokered deposit|wholesale funding|net interest margin)\b"
    ],
    "fed_macro": [
        r"\b(?:federal reserve|fomc|federal funds rate|dot plot|"
        r"quantitative (?:tightening|easing)|balance sheet.*fed|"
        r"treasury (?:yield|auction|market)|sofr|consumer price index|cpi|"
        r"personal consumption expenditure|pce|nonfarm payroll|unemployment rate|"
        r"gdp.*growth|inflation.*report|recession (?:risk|probability))\b"
    ],
    "local_government": [
        r"\b(?:city council|planning board|zoning board|board of supervisors|"
        r"zoning (?:change|amendment|variance|approval)|entitlement|"
        r"building permit|site plan approval|environmental impact (?:report|statement)|"
        r"tax abatement|pilot agreement|property tax.*(?:increase|decrease|change)|"
        r"affordable housing.*(?:mandate|requirement|ordinance)|"
        r"rent (?:control|stabilization|regulation)|eminent domain|"
        r"land.use.*(?:change|regulation|ordinance)|moratorium)\b"
    ],
}

_SECTOR_SIGNALS_COMPILED: dict[str, list[re.Pattern]] = {}
for _sector, _patterns in _SECTOR_SIGNALS.items():
    _SECTOR_SIGNALS_COMPILED[_sector] = [re.compile(p, re.IGNORECASE) for p in _patterns]

# Source-name to primary sector mapping (source-based priors)
_SOURCE_SECTOR_PRIORS: dict[str, str] = {
    # CRE sources
    "The Real Deal": "commercial_real_estate",
    "Commercial Observer": "commercial_real_estate",
    "Bisnow": "commercial_real_estate",
    "GlobeSt": "commercial_real_estate",
    "Connect CRE": "commercial_real_estate",
    "Propmodo": "commercial_real_estate",
    "NREI": "commercial_real_estate",
    "Multi-Housing News": "commercial_real_estate",
    "HousingWire": "commercial_real_estate",
    "Construction Dive": "commercial_real_estate",
    "RE Business Online": "commercial_real_estate",
    "CoStar": "commercial_real_estate",
    "Real Estate Weekly": "commercial_real_estate",
    "Crain's NY Business": "commercial_real_estate",
    "NY YIMBY": "commercial_real_estate",
    # PE sources
    "PE Hub": "private_equity",
    "Buyouts Insider": "private_equity",
    "Buyouts": "private_equity",
    "PitchBook News": "private_equity",
    "PEI": "private_equity",
    "Private Equity International": "private_equity",
    "Secondaries Investor": "private_equity",
    "Infrastructure Investor": "private_equity",
    "Venture Capital Journal": "private_equity",
    "Mergers & Acquisitions": "private_equity",
    "The Deal": "private_equity",
    "Term Sheet": "private_equity",
    "Private Debt Investor": "private_equity",
    "Institutional Investor": "private_equity",
    "PERE News": "private_equity",
    # DC sources
    "Data Center Dynamics": "data_centers",
    "Data Center Frontier": "data_centers",
    "DatacenterHawk": "data_centers",
    "Data Center Knowledge": "data_centers",
    # Energy sources
    "Utility Dive": "energy",
    "Power Magazine": "energy",
    "Renewable Energy World": "energy",
    "Greentech Media": "energy",
    "PV Magazine": "energy",
    "Windpower Monthly": "energy",
    "Energy Storage News": "energy",
    "Canary Media": "energy",
    # Banking sources
    "American Banker": "banking_credit",
    "Bank Director": "banking_credit",
    "Banking Dive": "banking_credit",
    "S&P Global Market Intelligence": "banking_credit",
    "The Financial Brand": "banking_credit",
    "Risk.net": "banking_credit",
    "MBA Newslink": "banking_credit",
    # Fed sources
    "Federal Reserve": "fed_macro",
    "FDIC": "banking_credit",
    "OCC": "banking_credit",
    "SEC": "banking_credit",
    "FHFA": "banking_credit",
    "Treasury": "fed_macro",
    "Bureau of Labor Statistics": "fed_macro",
    "Bureau of Economic Analysis": "fed_macro",
    # Local gov sources
    "NYC Gov": "local_government",
    "NYC Department of City Planning": "local_government",
    "NYC Department of Buildings": "local_government",
    "CityLand NYC": "local_government",
}


def _score_signal_matches(text: str, patterns: list) -> float:
    """Count how many sector signal patterns match the text."""
    text_lower = text.lower()
    matches = sum(1 for p in patterns if p.search(text_lower))
    total = len(patterns)
    return matches / max(1, total)


def classify_source_prior(item: CanonicalItem) -> str | None:
    """Return the primary sector based on source name matching."""
    source_lower = item.source_name.lower()
    for name, sector in _SOURCE_SECTOR_PRIORS.items():
        if name.lower() in source_lower:
            return sector
    return None


def classify_regex_signals(item: CanonicalItem) -> dict[str, float]:
    """Score each sector based on keyword signal density in the text."""
    text = f"{item.headline} {item.raw_summary} {item.raw_text}"
    scores = {}
    for sector, patterns in _SECTOR_SIGNALS_COMPILED.items():
        scores[sector] = _score_signal_matches(text, patterns)
    return scores


def classify_item(item: CanonicalItem) -> CanonicalItem:
    """Classify a single CanonicalItem. Returns the classified item."""
    # Step 1: Source-based prior
    source_sector = classify_source_prior(item)
    
    # Step 2: Regex signal scores for all sectors
    signal_scores = classify_regex_signals(item)
    
    # Step 3: Determine primary sector
    if source_sector and signal_scores.get(source_sector, 0) > 0.01:
        # Source prior confirmed by signal match — high confidence
        primary = source_sector
        confidence = 0.85
        method = "source_prior_and_regex"
    elif source_sector:
        # Source prior but no signal match — medium confidence
        primary = source_sector
        confidence = 0.60
        method = "source_prior_only"
    else:
        # No source prior — use best signal match
        ranked = sorted(signal_scores.items(), key=lambda x: x[1], reverse=True)
        if ranked and ranked[0][1] > 0.02:
            primary = ranked[0][0]
            confidence = min(0.70, ranked[0][1] * 3)
            method = "regex_signals"
        else:
            # No strong signals — needs LLM classification
            primary = "commercial_real_estate"  # fallback, mark for LLM
            confidence = 0.30
            method = "needs_llm"
    
    # Step 4: Determine secondary sectors from signal scores
    secondary = []
    threshold = 0.015
    for sector, score in signal_scores.items():
        if sector != primary and score > threshold:
            secondary.append(sector)
    secondary = secondary[:3]  # Cap at 3 secondary sectors
    
    # Step 5: Set classification on the item
    item.set_classification(
        primary=primary,
        secondary=secondary,
        event_type="",  # TODO: event type classification (Phase 2)
        subsector="",
        confidence=confidence,
        method=method,
    )
    
    return item


def classify_batch(items: list[CanonicalItem]) -> list[CanonicalItem]:
    """Classify a batch of items. No filtering — all items proceed."""
    results = []
    needs_llm = []
    
    for item in items:
        classified = classify_item(item)
        if classified.classification_method == "needs_llm":
            needs_llm.append(classified)
        results.append(classified)
    
    if needs_llm:
        print(f"  Classification: {len(needs_llm)}/{len(items)} items need LLM classification")
    
    return results


def get_sector_stats(items: list[CanonicalItem]) -> dict[str, int]:
    """Count items per primary sector."""
    stats: dict[str, int] = {}
    for item in items:
        sector = item.primary_sector or "unclassified"
        stats[sector] = stats.get(sector, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
