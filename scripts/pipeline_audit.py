"""
Pipeline audit: analyze all editorial runs and editions, produce a baseline report.

Usage:  python scripts/pipeline_audit.py
Output: data/pipeline-baseline.json + stdout summary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
EDITIONS_DIR = SITE_ROOT / "editions"
OUTPUT_PATH = SITE_ROOT / "data" / "pipeline-baseline.json"

LLM_CALLS_PER_ARTICLE = 3
COST_PER_INPUT_TOKEN = 0.27 / 1_000_000
COST_PER_OUTPUT_TOKEN = 1.10 / 1_000_000
EST_TOKENS_IN_PER_ARTICLE = 4000
EST_TOKENS_OUT_PER_ARTICLE = 2000
EST_COST_PER_ARTICLE_SCORING = 0.02
EST_COST_PER_ARTICLE_WRITING = 0.05


def _parse_run(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    run_date = data.get("date") or data.get("today") or ""
    raw_candidates = data.get("raw_count") or 0

    summary = data.get("selection_summary") or {}
    distinct_events = summary.get("distinct_events")
    articles = summary.get("articles")
    deal_tape_items = summary.get("deal_tape_items")
    duplicate_groups = summary.get("duplicate_groups")

    if articles is None:
        articles = data.get("publishable_candidate_count", 0)
    if articles is None:
        selected = data.get("selected_stories") or []
        articles = len(selected)

    if distinct_events is None:
        distinct_events = data.get("candidate_count") or 0

    if deal_tape_items is None:
        deal_tape_items = data.get("decision_counts", {}).get("publish", 0)

    if duplicate_groups is None:
        duplicate_groups = len(data.get("duplicate_groups") or [])

    candidates = data.get("scored_candidates") or []
    candidate_count = len(candidates)

    run_status = "published" if (articles and articles > 0) else "no_articles"

    return {
        "date": run_date,
        "run_status": run_status,
        "raw_candidates": raw_candidates,
        "distinct_events": distinct_events,
        "articles": articles,
        "deal_tape_items": deal_tape_items,
        "duplicate_groups": duplicate_groups,
        "candidate_count": candidate_count,
        "selection_mode": data.get("selection_mode", ""),
        "dry_run": bool(data.get("dry_run")),
        "shadow": bool(data.get("shadow")),
        "model": data.get("model", ""),
    }


def _load_editions() -> list[dict[str, Any]]:
    editions: list[dict[str, Any]] = []
    if not EDITIONS_DIR.is_dir():
        return editions
    for path in sorted(EDITIONS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("edition_date"):
            editions.append(data)
    return editions


def main() -> None:
    runs: list[dict[str, Any]] = []
    if RUNS_DIR.is_dir():
        for path in sorted(RUNS_DIR.glob("*.json")):
            entry = _parse_run(path)
            if entry:
                runs.append(entry)

    total_runs = len(runs)
    dates_with_runs = {r["date"] for r in runs}
    runs_with_zero = [r for r in runs if r["articles"] == 0]
    runs_with_articles = [r for r in runs if r["articles"] and r["articles"] > 0]

    avg_candidates_per_day = (
        sum(r["candidate_count"] for r in runs) / total_runs if total_runs else 0
    )
    avg_articles_per_day = (
        sum(r["articles"] for r in runs) / total_runs if total_runs else 0
    )
    publish_rate = len(runs_with_articles) / total_runs * 100 if total_runs else 0

    total_articles = sum(r["articles"] for r in runs)
    est_cost_scoring = total_articles * EST_COST_PER_ARTICLE_SCORING
    est_cost_writing = total_articles * EST_COST_PER_ARTICLE_WRITING
    est_cost_total = est_cost_scoring + est_cost_writing

    editions = _load_editions()
    edition_dates = {e.get("edition_date", "") for e in editions}
    dates_with_both = dates_with_runs & edition_dates
    dates_runs_only = dates_with_runs - edition_dates
    dates_editions_only = edition_dates - dates_with_runs

    null_flagship_count = sum(
        1 for e in editions if e.get("flagship") is None
    )
    empty_briefs_count = sum(
        1 for e in editions
        if isinstance(e.get("briefs"), list) and len(e.get("briefs") or []) == 0
    )

    report = {
        "total_runs": total_runs,
        "runs_with_0_articles": len(runs_with_zero),
        "runs_with_1plus_articles": len(runs_with_articles),
        "avg_candidates_per_day": round(avg_candidates_per_day, 1),
        "avg_articles_per_day": round(avg_articles_per_day, 1),
        "publish_rate_pct": round(publish_rate, 1),
        "total_articles_published": total_articles,
        "estimated_cost_scoring_usd": round(est_cost_scoring, 2),
        "estimated_cost_writing_usd": round(est_cost_writing, 2),
        "estimated_cost_total_usd": round(est_cost_total, 2),
        "editions": {
            "total_editions": len(editions),
            "dates_with_both_edition_and_run": len(dates_with_both),
            "dates_with_run_only": len(dates_runs_only),
            "dates_with_edition_only": len(dates_editions_only),
            "editions_null_flagship": null_flagship_count,
            "editions_empty_briefs": empty_briefs_count,
        },
        "per_run_details": runs,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("=" * 60)
    print("  PIPELINE AUDIT — Baseline Report")
    print("=" * 60)
    print(f"  Total runs analyzed:              {total_runs}")
    print(f"  Runs with 0 articles:             {len(runs_with_zero)}")
    print(f"  Runs with 1+ articles:            {len(runs_with_articles)}")
    print(f"  Avg candidates/day:               {avg_candidates_per_day:.1f}")
    print(f"  Avg articles/day:                 {avg_articles_per_day:.1f}")
    print(f"  Publish rate:                     {publish_rate:.1f}%")
    print(f"  Total articles published:         {total_articles}")
    print(f"  Estimated LLM cost (scoring):     ${est_cost_scoring:.2f}")
    print(f"  Estimated LLM cost (writing):     ${est_cost_writing:.2f}")
    print(f"  Estimated LLM cost (total):       ${est_cost_total:.2f}")
    print("-" * 60)
    print(f"  Editions total:                   {len(editions)}")
    print(f"  Dates with both edition + run:    {len(dates_with_both)}")
    print(f"  Dates with run only (no edition): {len(dates_runs_only)}")
    print(f"  Dates with edition only:          {len(dates_editions_only)}")
    print(f"  Editions with null flagship:      {null_flagship_count}")
    print(f"  Editions with empty briefs:       {empty_briefs_count}")
    print("=" * 60)
    print(f"  Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
