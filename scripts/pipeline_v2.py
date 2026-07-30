#!/usr/bin/env python3
"""Light Tower Group Multi-Sector Intelligence Pipeline (v2).

New pipeline that ingests from 150+ sources across 7 sectors, classifies
every story via multi-label classification, scores with sector-specific
profiles, and produces per-sector rankings.

Runs alongside the existing daily_news_agent.py — does not modify it.
Can run in shadow mode (no publishing) or preview mode (generate reports).
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent

from ingestion import (
    fetch_all_sources,
    fetch_sector_items,
    load_sources,
    load_sources_by_sector,
    get_source_stats,
)
from classification import classify_batch, get_sector_stats
from scoring_engine import score_batch, get_scoring_stats
from ranking import rank_and_select


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_pipeline(
    shadow: bool = True,
    verbose: bool = True,
    sectors: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full multi-sector pipeline.

    Args:
        shadow: If True, score and rank only — no writing/publishing.
        verbose: If True, print detailed progress.
        sectors: Optional list of sector keys to limit ingestion. If None,
            all active sources are fetched.

    Returns:
        Dict with pipeline results and statistics.
    """
    start = datetime.now(timezone.utc)
    results: dict[str, Any] = {
        "run_at": start.isoformat(),
        "mode": "shadow" if shadow else "preview",
    }

    # ── Phase 1: Ingestion ──
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Light Tower Multi-Sector Pipeline v2")
        print(f"  {start.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Mode: {'SHADOW' if shadow else 'PREVIEW'}")
        print(f"{'='*60}\n")

    print("[1/4] Ingesting from all sources...")
    sources = load_sources()
    results["sources_configured"] = len(sources)

    if sectors:
        print(f"  Sector filter: {', '.join(sectors)}")
        all_items: list = []
        for sector in sectors:
            items = fetch_sector_items(sector, sources=sources)
            all_items.extend(items)
    else:
        all_items = fetch_all_sources(sources)

    results["ingestion"] = {
        "sources_configured": len(sources),
        "items_ingested": len(all_items),
    }

    if not all_items:
        print("  No items ingested. Pipeline stopping.")
        results["status"] = "no_items"
        return results

    source_counts = get_source_stats(all_items)
    top_sources = ", ".join(f"{s}({c})" for s, c in list(source_counts.items())[:5])
    print(f"  Top sources: {top_sources}")

    # ── Phase 2: Classification ──
    print(f"\n[2/4] Classifying {len(all_items)} items...")
    classified = classify_batch(all_items)
    sector_counts = get_sector_stats(classified)
    results["classification"] = {
        "items_classified": len(classified),
        "sector_distribution": sector_counts,
    }
    for sector, count in sorted(sector_counts.items()):
        print(f"  {sector}: {count} items")

    # ── Phase 3: Scoring ──
    print(f"\n[3/4] Scoring {len(classified)} items...")
    scored = score_batch(classified)
    score_stats = get_scoring_stats(scored)
    results["scoring"] = score_stats

    # Estimate costs
    items_ingested = len(all_items)
    classified_count = len(classified)
    llm_classifications = sum(1 for c in classified if c.classification_method == "needs_llm")
    results["cost_estimate"] = {
        "items_ingested": items_ingested,
        "classified_count": classified_count,
        "llm_classifications_needed": llm_classifications,
        "llm_classification_pct": round(llm_classifications / max(1, classified_count) * 100, 1),
        "estimated_llm_cost_usd": round(llm_classifications * 0.001, 4),
        "note": "Article generation cost not included (separate phase)"
    }

    tier_dist = score_stats.get("tier_distribution", {})
    print(f"  Tier distribution: {tier_dist}")
    for sector, data in sorted(score_stats.get("sector_stats", {}).items()):
        print(f"  {sector}: {data['count']} items, avg composite {data['avg_composite']}")

    # ── Phase 4: Per-Sector Ranking and Selection ──
    if verbose:
        print(f"\n[4/4] Ranking and selecting per sector...")
    selected, ranking_report = rank_and_select(scored)
    results["ranking"] = ranking_report

    if verbose:
        for sector in sorted(sector_counts.keys()):
            sector_items = selected.get(sector, [])
            top_n = min(5, len(sector_items))
            if top_n == 0:
                continue
            print(f"\n  --- {sector.upper()} (top {top_n}) ---")
            for i, item in enumerate(sector_items[:top_n], 1):
                print(f"  [{item.tier}] {item.composite_score:.1f} | {item.headline[:80]}")
                if item.source_name:
                    print(f"       Source: {item.source_name} | Method: {item.classification_method}")

    # ── Results ──
    elapsed = round((datetime.now(timezone.utc) - start).total_seconds())
    results["elapsed_seconds"] = elapsed
    results["status"] = "complete"
    results["_items"] = scored

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Pipeline complete in {elapsed}s")
        print(f"  {len(all_items)} ingested -> {len(classified)} classified -> {len(scored)} scored")
        publishable = [s for s in scored if s.tier != "rejected"]
        print(f"  {len(publishable)} items above rejection threshold")
        print(f"{'='*60}")

    return results


def run_shadow_pipeline(sectors: list[str] | None = None) -> dict[str, Any]:
    """Convenience wrapper: run in shadow mode and return results dict."""
    return run_pipeline(shadow=True, verbose=True, sectors=sectors)


def preview_pipeline(sectors: list[str] | None = None) -> dict[str, Any]:
    """Convenience wrapper: run in preview mode and return results dict."""
    return run_pipeline(shadow=False, verbose=True, sectors=sectors)


def build_sector_report(items: list, output_path: Path | None = None) -> dict[str, Any]:
    """Build a per-sector JSON report from already-processed items.

    Args:
        items: A list of scored CanonicalItem objects.
        output_path: If provided, writes the report JSON to this path.

    Returns:
        A dict structured by sector with top headlines, stats, and metadata.
    """
    report: dict[str, Any] = {
        "generated_at": _now_iso(),
        "total_items": len(items),
        "sectors": {},
    }

    # Group by primary sector
    by_sector: dict[str, list] = {}
    for item in items:
        sector = item.primary_sector or "unclassified"
        by_sector.setdefault(sector, []).append(item)

    for sector, sector_items in sorted(by_sector.items()):
        sector_items.sort(key=lambda x: x.composite_score, reverse=True)
        publishable = [i for i in sector_items if i.tier != "rejected"]

        top_items = []
        for i in publishable[:10]:
            top_items.append({
                "headline": i.headline,
                "source": i.source_name,
                "url": i.canonical_url,
                "composite_score": i.composite_score,
                "tier": i.tier,
                "classification_method": i.classification_method,
                "published": i.publication_date,
            })

        report["sectors"][sector] = {
            "total": len(sector_items),
            "publishable": len(publishable),
            "avg_composite": round(
                sum(i.composite_score for i in publishable) / max(1, len(publishable)), 1
            ),
            "top_stories": top_items,
        }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LTG Multi-Sector Intelligence Pipeline v2"
    )
    parser.add_argument(
        "--shadow", action="store_true", default=True,
        help="Score and rank only — no writing or publishing (default)",
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Run in preview mode (generate reports, equivalent to --no-shadow)",
    )
    parser.add_argument(
        "--verbose", action="store_true", default=True,
        help="Print detailed progress",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--save-results", action="store_true",
        help="Save pipeline results to .editorial-state/pipeline-v2-results.json",
    )
    parser.add_argument(
        "--save-report", action="store_true",
        help="Save per-sector report to .editorial-state/sector-report-v2.json",
    )
    parser.add_argument(
        "--sectors", nargs="*", default=None,
        help="Limit to specific sector keys (e.g. commercial_real_estate private_equity)",
    )
    args = parser.parse_args()

    shadow_mode = args.shadow and not args.preview
    verbose_mode = not args.quiet

    results = run_pipeline(
        shadow=shadow_mode,
        verbose=verbose_mode,
        sectors=args.sectors,
    )

    state_dir = SITE_ROOT / ".editorial-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    if args.save_results:
        output_path = state_dir / "pipeline-v2-results.json"
        output_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"Results saved to {output_path.relative_to(SITE_ROOT)}")

    if args.save_report:
        all_items = results.get("_items", [])
        report_path = state_dir / "sector-report-v2.json"
        build_sector_report(all_items, output_path=report_path)
        print(f"Sector report saved to {report_path.relative_to(SITE_ROOT)}")

    return 0 if results.get("status") == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
