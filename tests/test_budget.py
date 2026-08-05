"""Spending and time ceilings that actually stop work.

These settings sat in config unread while a run spent forty minutes producing
nothing. The tests that matter are the ones proving a limit *refuses* work
rather than merely recording that it happened.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from budget import (  # noqa: E402
    Budget,
    BudgetExceeded,
    PhaseTimeout,
    active,
    reset,
)

CONFIG = {
    "cost_limits": {
        "max_daily_llm_cost_usd": 1.00,
        "max_per_article_cost_usd": 0.10,
        "cheap_model_max_daily_calls": 500,
        "premium_model_max_daily_calls": 250,
    },
    "timing": {
        "pipeline_timeout_minutes": 330,
        "per_phase_timeout_seconds": {"generation": 1800, "enrichment": 600},
    },
}


def _budget(**kwargs) -> Budget:
    tmp = Path(tempfile.mkdtemp()) / "ledger.json"
    return Budget(ledger_path=tmp, config=CONFIG, **kwargs)


class ReadsTheConfigItWasGiven(unittest.TestCase):
    def test_limits_come_from_config_not_hardcoded(self) -> None:
        b = _budget()
        self.assertEqual(b.daily_usd, 1.00)
        self.assertEqual(b.per_article_usd, 0.10)
        self.assertEqual(b.phase_timeouts["generation"], 1800)
        self.assertEqual(b.pipeline_timeout_s, 330 * 60)

    def test_an_operator_override_wins(self) -> None:
        b = _budget(daily_usd=0.25)
        self.assertEqual(b.daily_usd, 0.25)


class RefusesWorkOverTheCeiling(unittest.TestCase):
    def test_calls_are_allowed_until_the_daily_limit_then_refused(self) -> None:
        b = _budget()
        self.assertTrue(b.allow("generation", estimated_usd=0.5))
        b.record("generation", usd=0.5)
        self.assertTrue(b.allow("generation", estimated_usd=0.4))
        b.record("generation", usd=0.4)
        self.assertFalse(
            b.allow("generation", estimated_usd=0.5),
            "a call that would exceed the daily limit must be refused",
        )

    def test_a_refusal_is_counted_not_hidden(self) -> None:
        b = _budget()
        b.record("generation", usd=1.0)
        b.allow("generation", estimated_usd=0.5)
        self.assertEqual(b.report()["refused_calls"], 1)

    def test_per_article_ceiling_stops_one_runaway_story(self) -> None:
        b = _budget()
        b.record("generation", usd=0.09, article_id="story-1")
        self.assertFalse(b.allow("generation", estimated_usd=0.05, article_id="story-1"))
        self.assertTrue(
            b.allow("generation", estimated_usd=0.05, article_id="story-2"),
            "one expensive story must not block the rest of the edition",
        )

    def test_require_raises_for_callers_that_cannot_degrade(self) -> None:
        b = _budget()
        b.record("generation", usd=1.0)
        with self.assertRaises(BudgetExceeded):
            b.require("generation", estimated_usd=0.5)

    def test_refusal_is_the_normal_path_and_does_not_raise(self) -> None:
        b = _budget()
        b.record("generation", usd=1.0)
        self.assertFalse(b.allow("generation", estimated_usd=0.5))  # no exception


class CostsAreEstimatedWhenNotReported(unittest.TestCase):
    def test_token_counts_become_dollars(self) -> None:
        b = _budget()
        usd = b.record("draft", model="deepseek-v4-pro",
                       input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(usd, 1.50, places=2)

    def test_an_unknown_model_falls_back_rather_than_scoring_zero(self) -> None:
        b = _budget()
        usd = b.record("draft", model="some-new-model", input_tokens=1_000_000)
        self.assertGreater(usd, 0.0, "an unknown model must not be treated as free")

    def test_a_reported_cost_is_used_verbatim(self) -> None:
        b = _budget()
        self.assertEqual(b.record("draft", usd=0.42, input_tokens=999_999), 0.42)


class SpendSurvivesTheProcess(unittest.TestCase):
    def test_a_second_run_inherits_the_days_spend(self) -> None:
        ledger = Path(tempfile.mkdtemp()) / "ledger.json"
        first = Budget(ledger_path=ledger, config=CONFIG)
        first.record("generation", usd=0.8)
        first.persist()

        second = Budget(ledger_path=ledger, config=CONFIG)
        self.assertAlmostEqual(second.spent_today, 0.8, places=3)
        self.assertFalse(
            second.allow("generation", estimated_usd=0.5),
            "a crash-and-retry loop must not spend the daily limit repeatedly",
        )

    def test_the_ledger_is_written_readably(self) -> None:
        ledger = Path(tempfile.mkdtemp()) / "ledger.json"
        b = Budget(ledger_path=ledger, config=CONFIG)
        b.record("draft", usd=0.05)
        b.persist()
        payload = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertIn(b.today, payload["days"])
        self.assertAlmostEqual(payload["days"][b.today]["usd"], 0.05, places=3)

    def test_a_broken_ledger_does_not_stop_a_run(self) -> None:
        ledger = Path(tempfile.mkdtemp()) / "ledger.json"
        ledger.write_text("{ not json", encoding="utf-8")
        b = Budget(ledger_path=ledger, config=CONFIG)
        self.assertEqual(b.spent_today, 0.0)
        b.record("draft", usd=0.01)
        b.persist()  # must not raise


class PhaseTimeouts(unittest.TestCase):
    def test_a_phase_past_its_deadline_is_stopped(self) -> None:
        b = _budget()
        deadline = time.monotonic() - 1  # already expired
        with self.assertRaises(PhaseTimeout):
            b.check_phase("generation", deadline)

    def test_a_phase_inside_its_deadline_passes(self) -> None:
        b = _budget()
        b.check_phase("generation", b.phase_deadline("generation"))  # must not raise

    def test_an_unconfigured_phase_still_gets_a_ceiling(self) -> None:
        b = _budget()
        self.assertGreater(b.phase_deadline("something_new", default=30), time.monotonic())


class Reporting(unittest.TestCase):
    def test_the_report_shows_where_the_money_went(self) -> None:
        b = _budget()
        b.record("draft", usd=0.30, input_tokens=1000, seconds=2.0, article_id="a")
        b.record("review", usd=0.10, seconds=1.0, article_id="a")
        report = b.report()
        self.assertAlmostEqual(report["spent_this_run_usd"], 0.40, places=3)
        self.assertAlmostEqual(report["remaining_usd"], 0.60, places=3)
        self.assertEqual(report["by_stage"]["draft"]["calls"], 1)
        self.assertEqual(report["most_expensive_articles"][0]["id"], "a")

    def test_the_summary_is_ascii_safe(self) -> None:
        b = _budget()
        b.record("draft", usd=0.1)
        b.summary().encode("cp1252")

    def test_exhausted_is_reported_plainly(self) -> None:
        b = _budget()
        b.record("draft", usd=1.0)
        self.assertTrue(b.report()["exhausted"])


class ProcessWideAccess(unittest.TestCase):
    def test_reset_installs_a_fresh_budget(self) -> None:
        first = reset(_budget())
        first.record("draft", usd=0.2)
        self.assertIs(active(), first)
        second = reset(_budget())
        self.assertIsNot(second, first)
        self.assertEqual(second.session_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
