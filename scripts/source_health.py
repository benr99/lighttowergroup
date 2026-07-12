"""Persistent, conservative source-health tracking for editorial intake.

The publisher must not keep treating a broken RSS endpoint as a normal source.
This module records only operational metadata (never article content) and opens a
temporary circuit after repeated failures.  A source is retried after the
cooldown so a transient publisher outage can recover without manual work.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class SourceHealthLedger:
    """Small JSON-backed circuit breaker for RSS sources."""

    def __init__(self, path: Path, *, failure_threshold: int = 3, cooldown_hours: int = 24) -> None:
        self.path = path
        self.failure_threshold = failure_threshold
        self.cooldown_hours = cooldown_hours
        self.records = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def is_quarantined(self, source: str, now: datetime | None = None) -> bool:
        record = self.records.get(source, {})
        if int(record.get("consecutive_failures", 0)) < self.failure_threshold:
            return False
        last_failure = self._parse_time(record.get("last_failure_at"))
        if last_failure is None:
            return False
        now = now or datetime.now(timezone.utc)
        return now < last_failure + timedelta(hours=self.cooldown_hours)

    def record_success(self, source: str, story_count: int, elapsed_ms: int) -> None:
        record = self.records.setdefault(source, {})
        record.update({
            "status": "healthy",
            "consecutive_failures": 0,
            "last_success_at": self._now(),
            "last_story_count": story_count,
            "last_elapsed_ms": elapsed_ms,
        })

    def record_failure(self, source: str, error: str, elapsed_ms: int) -> None:
        record = self.records.setdefault(source, {})
        record.update({
            "status": "degraded",
            "consecutive_failures": int(record.get("consecutive_failures", 0)) + 1,
            "last_failure_at": self._now(),
            "last_error": error[:240],
            "last_elapsed_ms": elapsed_ms,
        })

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _parse_time(value: Any) -> datetime | None:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
