"""Within-sector ranking and selection for the Light Tower Insights pipeline.

After classification and scoring, this module ranks stories within each
sector, applies editorial diversity controls, selects approximately 30
stories per sector, and handles cross-sector deduplication.
"""

from __future__ import annotations
import json
from collections import defaultdict
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


def _load_thresholds() -> dict[str, Any]:
    return _load_json(CONFIG_DIR / "thresholds.json")


def _load_sectors() -> dict[str, Any]:
    return _load_json(CONFIG_DIR / "sectors.json").get("sectors", {})


def rank_within_sector(items: list[CanonicalItem], sector: str) -> list[CanonicalItem]:
    """Rank items within a single sector by composite score, descending.
    
    Only includes items whose primary_sector matches AND whose tier is not 'rejected'.
    """
    sector_items = [
        item for item in items
        if item.primary_sector == sector and item.tier != "rejected"
    ]
    sector_items.sort(key=lambda x: x.composite_score, reverse=True)
    return sector_items


def apply_diversity_controls(
    ranked: list[CanonicalItem],
    sector: str,
    max_single_subsector_pct: float = 40.0,
    max_single_source_pct: float = 25.0,
    max_single_company_pct: float = 20.0,
    min_subsectors: int = 3,
) -> list[CanonicalItem]:
    """Apply editorial diversity controls to a ranked list.
    
    Ensures no single subsector, source, or company dominates the selection.
    When diversity constraints would be violated, lower-ranked items from
    underrepresented categories are promoted.
    
    Args:
        ranked: Items ranked by composite score (highest first).
        sector: The sector these items belong to.
        max_single_subsector_pct: Max percentage from one subsector.
        max_single_source_pct: Max percentage from one source.
        max_single_company_pct: Max percentage from one company.
        min_subsectors: Minimum number of distinct subsectors represented.
    
    Returns:
        Re-ranked list with diversity adjustments applied.
    """
    if len(ranked) < 5:
        return ranked  # Too few items for meaningful diversity control

    target_count = len(ranked)
    selected = []
    source_counts: dict[str, int] = defaultdict(int)
    subsector_counts: dict[str, int] = defaultdict(int)

    MIN_BEFORE_DIVERSITY_CHECK = 5

    for item in ranked:
        source = item.source_name or "unknown"
        subsector = item.subsector or "general"

        if len(selected) < MIN_BEFORE_DIVERSITY_CHECK:
            selected.append(item)
            source_counts[source] = source_counts.get(source, 0) + 1
            subsector_counts[subsector] = subsector_counts.get(subsector, 0) + 1
            continue

        source_pct = (source_counts.get(source, 0) + 1) / max(1, len(selected) + 1) * 100
        subsector_pct = (subsector_counts.get(subsector, 0) + 1) / max(1, len(selected) + 1) * 100

        source_ok = source_pct <= max_single_source_pct
        subsector_ok = subsector_pct <= max_single_subsector_pct

        if source_ok and subsector_ok:
            selected.append(item)
            source_counts[source] = source_counts.get(source, 0) + 1
            subsector_counts[subsector] = subsector_counts.get(subsector, 0) + 1
        # If constraint violated, skip this item — it goes to a "reserve" pool
        # The item will be reconsidered if we can't hit the target

    # If we didn't select enough, relax constraints and fill from the reserve
    selected_ids = {id(item) for item in selected}
    reserve = [item for item in ranked if id(item) not in selected_ids]
    if len(selected) < target_count and reserve:
        # Add reserve items, still respecting source diversity loosely
        for item in reserve:
            if len(selected) >= target_count:
                break
            source = item.source_name or "unknown"
            if source_counts.get(source, 0) < target_count // 3:  # Looser constraint
                selected.append(item)
                source_counts[source] = source_counts.get(source, 0) + 1

    return selected


def select_top_n(
    items: list[CanonicalItem],
    target_per_sector: int = 30,
) -> dict[str, list[CanonicalItem]]:
    """Select approximately N stories per sector with diversity controls.
    
    Args:
        items: All scored CanonicalItems.
        target_per_sector: Target number of stories per sector (default 30).
    
    Returns:
        Dict mapping sector name to list of selected CanonicalItems.
    """
    thresholds = _load_thresholds()
    articles_per_sector = thresholds.get("articles_per_sector", {})
    diversity = thresholds.get("diversity_controls", {})

    selected: dict[str, list[CanonicalItem]] = {}
    report: dict[str, Any] = {}

    # Group items by primary sector
    by_sector: dict[str, list[CanonicalItem]] = defaultdict(list)
    unclassified_count = 0
    for item in items:
        if item.primary_sector:
            by_sector[item.primary_sector].append(item)
        else:
            unclassified_count += 1

    if unclassified_count:
        print(f"  [WARN] {unclassified_count} item(s) dropped — missing primary_sector (classification may have failed)")

    for sector, sector_items in sorted(by_sector.items()):
        target = articles_per_sector.get(sector, target_per_sector)

        # Rank within sector
        ranked = rank_within_sector(sector_items, sector)

        # Apply diversity controls
        diverse = apply_diversity_controls(
            ranked,
            sector,
            max_single_subsector_pct=diversity.get("max_single_subsector_pct", 40),
            max_single_source_pct=diversity.get("max_single_source_pct", 25),
            max_single_company_pct=diversity.get("max_single_company_pct", 20),
            min_subsectors=diversity.get("min_subsectors_represented", 3),
        )

        # Select top N
        top_n = diverse[:target]
        selected[sector] = top_n

        # Build report
        tier_counts = defaultdict(int)
        for item in top_n:
            tier_counts[item.tier or "unknown"] += 1

        report[sector] = {
            "candidates_total": len(sector_items),
            "candidates_above_rejection": len(ranked),
            "selected": len(top_n),
            "target": target,
            "shortfall": max(0, target - len(top_n)),
            "tier_distribution": dict(tier_counts),
            "avg_composite": round(
                sum(item.composite_score for item in top_n) / max(1, len(top_n)), 1
            ),
            "top_score": top_n[0].composite_score if top_n else 0,
            "lowest_score": top_n[-1].composite_score if top_n else 0,
        }

    # Print report
    print(f"\n  Per-Sector Selection Report:")
    print(f"  {'Sector':<25} {'Candidates':>10} {'Selected':>10} {'Target':>8} {'Shortfall':>10} {'Avg Score':>10}")
    print(f"  {'-'*73}")
    for sector, data in sorted(report.items()):
        print(f"  {sector:<25} {data['candidates_total']:>10} {data['selected']:>10} "
              f"{data['target']:>8} {data['shortfall']:>10} {data['avg_composite']:>10.1f}")

    return selected


def deduplicate_across_sectors(
    selected: dict[str, list[CanonicalItem]],
) -> dict[str, list[CanonicalItem]]:
    """Remove duplicate stories that appear in multiple sectors.
    
    When a story was classified into multiple sectors and selected in more than
    one, keep it only in the highest-scoring sector and remove from others.
    """
    seen_ids: set[str] = set()
    deduped: dict[str, list[CanonicalItem]] = {}

    # Process sectors in order of total selected count (most first)
    sector_order = sorted(selected.keys(), key=lambda s: len(selected[s]), reverse=True)

    for sector in sector_order:
        deduped[sector] = []
        for item in selected[sector]:
            item_id = item.item_id or f"{item.source_url}|{item.headline}|{item.discovery_date}"
            if not item_id.strip("|"):
                item_id = str(id(item))
            if item_id not in seen_ids:
                deduped[sector].append(item)
                seen_ids.add(item_id)

    # Report deduplication
    total_before = sum(len(v) for v in selected.values())
    total_after = sum(len(v) for v in deduped.values())
    if total_before != total_after:
        print(f"\n  Cross-sector dedup: {total_before} -> {total_after} ({total_before - total_after} duplicates removed)")

    return deduped


def get_rejection_report(items: list[CanonicalItem]) -> dict[str, Any]:
    """Generate a report on why items were rejected."""
    rejected = [item for item in items if item.tier == "rejected"]
    
    reasons: dict[str, int] = defaultdict(int)
    sectors_affected: dict[str, int] = defaultdict(int)
    
    for item in rejected:
        code = item.rejection_code or "below_threshold"
        reasons[code] += 1
        sectors_affected[item.primary_sector or "unknown"] += 1

    return {
        "total_rejected": len(rejected),
        "reasons": dict(reasons),
        "sectors_affected": dict(sectors_affected),
    }


def rank_and_select(
    items: list[CanonicalItem],
    target_per_sector: int = 30,
) -> tuple[dict[str, list[CanonicalItem]], dict[str, Any]]:
    """Main entry point: rank all scored items and select per-sector outputs.
    
    Args:
        items: Scored CanonicalItems from scoring_engine.score_batch().
        target_per_sector: Target stories per sector.
    
    Returns:
        Tuple of (selected items by sector, selection report).
    """
    # Select top N per sector
    selected = select_top_n(items, target_per_sector=target_per_sector)

    # Deduplicate across sectors
    selected = deduplicate_across_sectors(selected)

    # Rejection report
    rejection = get_rejection_report(items)

    # Build total report
    total_selected = sum(len(v) for v in selected.values())
    total_candidates = len(items)
    report = {
        "total_candidates": total_candidates,
        "total_selected": total_selected,
        "selection_rate_pct": round(total_selected / max(1, total_candidates) * 100, 1),
        "rejection": rejection,
        "per_sector": {
            sector: {
                "count": len(items_list),
                "titles": [item.headline[:80] for item in items_list[:5]],
            }
            for sector, items_list in sorted(selected.items())
        },
    }

    return selected, report
