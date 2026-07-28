#!/usr/bin/env python3
"""Weekly retrospective report for Light Tower Insights editorial pipeline."""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
EDITIONS_DIR = SITE_ROOT / "editions"
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
STATE_DIR = SITE_ROOT / ".editorial-state"
REPORTS_DIR = SITE_ROOT / "data" / "weekly-reports"
SIGNALS_PATH = STATE_DIR / "audience-signals.json"
READ_EVENTS_PATH = STATE_DIR / "read-events.jsonl"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_edition_runs(days: int = 7) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    runs = []
    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.json"), reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            try:
                run_date = datetime.fromisoformat(str(data.get("run_at", "")[:10]) + "T00:00:00+00:00")
                if run_date >= cutoff:
                    runs.append(data)
            except (TypeError, ValueError):
                continue
    return runs


def load_editions(days: int = 7) -> list[dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    editions = []
    if EDITIONS_DIR.exists():
        for path in sorted(EDITIONS_DIR.glob("*.json"), reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            try:
                ed_date = datetime.fromisoformat(str(data.get("edition_date", ""))).date()
                if ed_date >= cutoff:
                    editions.append(data)
            except (TypeError, ValueError):
                continue
    return editions


def load_read_events(days: int = 7) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    if READ_EVENTS_PATH.exists():
        for line in READ_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                ts = datetime.fromisoformat(str(event.get("timestamp", "")).replace("Z", "+00:00"))
                if ts >= cutoff:
                    events.append(event)
            except (json.JSONDecodeError, ValueError):
                continue
    return events


def load_audience_signals() -> dict[str, Any]:
    return load_json(SIGNALS_PATH) or {}


def generate_report() -> str:
    runs = load_edition_runs(7)
    editions = load_editions(7)
    read_events = load_read_events(7)
    signals = load_audience_signals()

    total_runs = len(runs)
    runs_with_articles = [r for r in runs if r.get("articles")]
    publish_rate = len(runs_with_articles) / max(1, total_runs) * 100

    total_articles = sum(len(r.get("articles", [])) for r in runs)
    total_candidates = sum(r.get("candidate_count", r.get("raw_count", 0)) for r in runs)

    edition_statuses = []
    for ed in editions:
        status = ed.get("status", "unknown")
        has_flagship = bool(ed.get("flagship"))
        has_briefs = bool(ed.get("briefs"))
        edition_statuses.append(f"  {ed.get('edition_date')}: {status}" +
                               (f" (flagship + {len(ed.get('briefs', []))} briefs)" if has_flagship or has_briefs else " (no articles)"))

    read_by_slug = {}
    for event in read_events:
        slug = event.get("slug", "")
        if slug:
            read_by_slug.setdefault(slug, {"views": 0, "scrolls_50": 0, "scrolls_100": 0, "shares": 0})
            action = event.get("action", "view")
            if action in read_by_slug[slug]:
                read_by_slug[slug][action] += 1

    top_read = sorted(read_by_slug.items(), key=lambda x: x[1]["views"], reverse=True)[:5]

    signal_weights = signals.get("weights", {})
    active_signals = {k: v for k, v in signal_weights.items() if v != 0}

    estimated_cost = total_articles * 0.07  # ~$0.07 per article (scoring + writing)

    report = f"""# Light Tower Insights — Weekly Retrospective
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**Period:** Last 7 days

---

## Pipeline Performance

| Metric | Value |
|--------|-------|
| Total runs | {total_runs} |
| Runs with articles | {len(runs_with_articles)} |
| Publish rate | {publish_rate:.0f}% |
| Total articles published | {total_articles} |
| Average articles/day | {total_articles / max(1, total_runs):.1f} |
| Total candidates processed | {total_candidates} |
| Estimated LLM cost | ${estimated_cost:.2f} |

## Edition Status
{chr(10).join(edition_statuses) if edition_statuses else '  No editions in period'}

## Reader Engagement
{chr(10).join(f'  **{slug}**: {data["views"]} views, {data["shares"]} shares' for slug, data in top_read) if top_read else '  No read-tracking data available yet'}

## Audience Signals
{chr(10).join(f'  {k}: {v:+d}' for k, v in active_signals.items()) if active_signals else '  No audience signals collected yet'}

## Health Check
- RSS feeds: check source-health.json for quarantine status
- LLM provider: primary (DeepSeek) — verify in provider-log.jsonl
- Pipeline costs this period: **${estimated_cost:.2f}**

---
*This report supports data-driven editorial decisions. Review top-performing topics and double down.*
"""
    return report


def main():
    today = datetime.now(timezone.utc).date()
    iso_week = today.isocalendar()
    week_label = f"{today.year}-W{iso_week.week:02d}"

    report = generate_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{week_label}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Weekly retrospective saved: {report_path.relative_to(SITE_ROOT)}")
    print()
    print(report)


if __name__ == "__main__":
    main()
