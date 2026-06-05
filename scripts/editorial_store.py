"""
Persistence helpers for editorial scoring audits and weekly reviews.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
DATA_DIR = SITE_ROOT / "data"
EDITORIAL_RUNS_DIR = DATA_DIR / "editorial_runs"
WEEKLY_REVIEWS_DIR = DATA_DIR / "weekly_reviews"


def _json_safe(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def save_editorial_run(payload: dict[str, Any], run_date: date | None = None) -> Path:
    run_date = run_date or datetime.now(timezone.utc).date()
    EDITORIAL_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = EDITORIAL_RUNS_DIR / f"{run_date.isoformat()}.json"
    path.write_text(_json_safe(payload), encoding="utf-8")
    return path


def load_editorial_run(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_weekly_editorial_runs(anchor: date | None = None) -> list[dict[str, Any]]:
    anchor = anchor or datetime.now(timezone.utc).date()
    monday = anchor - timedelta(days=anchor.weekday())
    runs: list[dict[str, Any]] = []
    for offset in range(5):
        path = EDITORIAL_RUNS_DIR / f"{(monday + timedelta(days=offset)).isoformat()}.json"
        if path.exists():
            run = load_editorial_run(path)
            if run:
                runs.append(run)
    return runs


def save_weekly_review(payload: dict[str, Any], review_date: date | None = None) -> Path:
    review_date = review_date or datetime.now(timezone.utc).date()
    WEEKLY_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    path = WEEKLY_REVIEWS_DIR / f"{review_date.isoformat()}.json"
    path.write_text(_json_safe(payload), encoding="utf-8")
    return path
