"""Enforce the spending and time limits that config has always declared.

`config/thresholds.json` has carried `max_daily_llm_cost_usd: 25.00`, per-phase
timeouts and a pipeline timeout since the beginning. No code read any of them.
A run recently spent forty minutes of model calls, produced nothing, and no
ceiling was ever in play. Configuration that looks like a brake but isn't is
worse than none, because it gets trusted.

This makes them real. Two rules:

Refuse rather than overspend
    `Budget.allow()` is asked before each model call. Over the daily ceiling it
    returns False and the caller skips that work. Nothing raises, because a
    budget stop is a normal outcome -- the edition simply comes out shorter, and
    says why.

Spend survives the process
    The ledger is keyed by date on disk, so several runs in one day share one
    ceiling. A crash-and-retry loop cannot spend the daily limit repeatedly.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SITE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = SITE_ROOT / "config" / "thresholds.json"
LEDGER_PATH = SITE_ROOT / ".editorial-state" / "spend-ledger.json"

#: Published prices per million tokens, used to estimate spend when a provider
#: does not return cost. Deliberately rounded up: a budget that under-estimates
#: is not a budget.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "deepseek-v4-pro": (0.30, 1.20),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "default": (1.00, 4.00),
}


def _load_limits() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@dataclass
class StageSpend:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    seconds: float = 0.0
    refused: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["usd"] = round(self.usd, 4)
        data["seconds"] = round(self.seconds, 2)
        return data


class BudgetExceeded(RuntimeError):
    """Raised only by `require()`, for callers that cannot degrade gracefully."""


class PhaseTimeout(RuntimeError):
    """Raised when a phase runs past its configured ceiling."""


class Budget:
    """Tracks spend and time against the configured ceilings."""

    def __init__(
        self,
        *,
        daily_usd: float | None = None,
        per_article_usd: float | None = None,
        ledger_path: Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        limits = (config if config is not None else _load_limits()).get("cost_limits", {})
        timing = (config if config is not None else _load_limits()).get("timing", {})

        # An operator override always wins over config, so a run can be capped
        # tighter without editing the repo.
        env_daily = os.environ.get("LTG_MAX_DAILY_USD")
        self.daily_usd = float(
            daily_usd if daily_usd is not None
            else (env_daily if env_daily else limits.get("max_daily_llm_cost_usd", 25.0))
        )
        self.per_article_usd = float(
            per_article_usd if per_article_usd is not None
            else limits.get("max_per_article_cost_usd", 0.15)
        )
        self.max_cheap_calls = int(limits.get("cheap_model_max_daily_calls", 500))
        self.max_premium_calls = int(limits.get("premium_model_max_daily_calls", 250))
        self.phase_timeouts = dict(timing.get("per_phase_timeout_seconds", {}))
        self.pipeline_timeout_s = int(timing.get("pipeline_timeout_minutes", 330)) * 60

        self.ledger_path = ledger_path or LEDGER_PATH
        self.stages: dict[str, StageSpend] = {}
        self.article_usd: dict[str, float] = {}
        self.started = time.monotonic()
        self._lock = threading.Lock()
        self._prior_usd = self._load_prior_spend()

    # ── ledger ─────────────────────────────────────────────────────────────

    @property
    def today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load_prior_spend(self) -> float:
        """Spend already recorded today, so repeated runs share one ceiling."""
        try:
            ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0.0
        return float(ledger.get("days", {}).get(self.today, {}).get("usd", 0.0))

    def persist(self) -> None:
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                ledger = {"schema_version": 1, "days": {}}
            day = ledger.setdefault("days", {}).setdefault(self.today, {"usd": 0.0, "calls": 0})
            day["usd"] = round(self._prior_usd + self.session_usd, 4)
            day["calls"] = int(day.get("calls", 0)) + self.total_calls
            day["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Keep the file small; 60 days is plenty for trend and audit.
            days = ledger["days"]
            for stale in sorted(days)[:-60]:
                days.pop(stale, None)
            self.ledger_path.write_text(
                json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        except OSError:
            pass  # a ledger write failure must never fail a run

    # ── totals ─────────────────────────────────────────────────────────────

    @property
    def session_usd(self) -> float:
        return round(sum(s.usd for s in self.stages.values()), 4)

    @property
    def spent_today(self) -> float:
        return round(self._prior_usd + self.session_usd, 4)

    @property
    def remaining(self) -> float:
        return round(max(0.0, self.daily_usd - self.spent_today), 4)

    @property
    def total_calls(self) -> int:
        return sum(s.calls for s in self.stages.values())

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    # ── decisions ──────────────────────────────────────────────────────────

    def allow(self, stage: str, *, estimated_usd: float = 0.0, article_id: str = "") -> bool:
        """May this call proceed? False means skip it, not fail."""
        with self._lock:
            if self.spent_today + estimated_usd > self.daily_usd:
                self.stages.setdefault(stage, StageSpend()).refused += 1
                return False
            if article_id:
                spent = self.article_usd.get(article_id, 0.0)
                if spent + estimated_usd > self.per_article_usd:
                    self.stages.setdefault(stage, StageSpend()).refused += 1
                    return False
            if self.elapsed > self.pipeline_timeout_s:
                self.stages.setdefault(stage, StageSpend()).refused += 1
                return False
            return True

    def require(self, stage: str, *, estimated_usd: float = 0.0, article_id: str = "") -> None:
        if not self.allow(stage, estimated_usd=estimated_usd, article_id=article_id):
            raise BudgetExceeded(
                f"{stage}: ${self.spent_today:.2f} of ${self.daily_usd:.2f} daily budget used"
            )

    def record(
        self,
        stage: str,
        *,
        model: str = "default",
        input_tokens: int = 0,
        output_tokens: int = 0,
        seconds: float = 0.0,
        usd: float | None = None,
        article_id: str = "",
    ) -> float:
        """Record one completed call. Returns the cost attributed to it."""
        if usd is None:
            price_in, price_out = MODEL_PRICES.get(model, MODEL_PRICES["default"])
            usd = (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
        with self._lock:
            entry = self.stages.setdefault(stage, StageSpend())
            entry.calls += 1
            entry.input_tokens += input_tokens
            entry.output_tokens += output_tokens
            entry.seconds += seconds
            entry.usd += usd
            if article_id:
                self.article_usd[article_id] = self.article_usd.get(article_id, 0.0) + usd
        return usd

    def phase_deadline(self, phase: str, *, default: int = 600) -> float:
        """Monotonic timestamp by which a phase must finish."""
        return time.monotonic() + float(self.phase_timeouts.get(phase, default))

    def check_phase(self, phase: str, deadline: float) -> None:
        if time.monotonic() > deadline:
            raise PhaseTimeout(
                f"{phase} exceeded its {self.phase_timeouts.get(phase, 'configured')}s ceiling"
            )

    # ── reporting ──────────────────────────────────────────────────────────

    def report(self) -> dict[str, Any]:
        return {
            "date": self.today,
            "daily_limit_usd": self.daily_usd,
            "spent_before_this_run_usd": round(self._prior_usd, 4),
            "spent_this_run_usd": self.session_usd,
            "spent_today_usd": self.spent_today,
            "remaining_usd": self.remaining,
            "exhausted": self.remaining <= 0,
            "total_calls": self.total_calls,
            "refused_calls": sum(s.refused for s in self.stages.values()),
            "elapsed_seconds": round(self.elapsed, 1),
            "by_stage": {name: s.to_dict() for name, s in sorted(self.stages.items())},
            "most_expensive_articles": sorted(
                ({"id": k, "usd": round(v, 4)} for k, v in self.article_usd.items()),
                key=lambda r: -r["usd"],
            )[:10],
        }

    def summary(self) -> str:
        r = self.report()
        lines = [
            f"  spend  ${r['spent_this_run_usd']:.3f} this run, "
            f"${r['spent_today_usd']:.3f} of ${r['daily_limit_usd']:.2f} today"
            f"  ({r['total_calls']} calls)"
        ]
        if r["refused_calls"]:
            lines.append(f"    {r['refused_calls']} call(s) refused by the budget")
        for name, stage in r["by_stage"].items():
            if stage["calls"]:
                lines.append(
                    f"    {name:22} {stage['calls']:>4} calls  ${stage['usd']:.3f}"
                    f"  {stage['seconds']:.0f}s"
                )
        return "\n".join(lines)


_ACTIVE: Budget | None = None


def active() -> Budget:
    """Process-wide budget, so any stage can reach it without threading it through."""
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = Budget()
    return _ACTIVE


def reset(budget: Budget | None = None) -> Budget:
    global _ACTIVE
    _ACTIVE = budget or Budget()
    return _ACTIVE
