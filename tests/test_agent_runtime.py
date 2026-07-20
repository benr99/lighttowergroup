from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import CalledProcessError
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from agent_runtime import sync_action
from source_health import SourceHealthLedger
import daily_news_agent


class AgentRuntimeTests(unittest.TestCase):
    def test_sync_action_only_fast_forwards_or_recovers_a_linear_history(self) -> None:
        self.assertEqual(sync_action("a", "a", head_contains_remote=True, remote_contains_head=True), "current")
        self.assertEqual(sync_action("b", "a", head_contains_remote=True, remote_contains_head=False), "recover_push")
        self.assertEqual(sync_action("a", "b", head_contains_remote=False, remote_contains_head=True), "fast_forward")
        self.assertEqual(sync_action("a", "b", head_contains_remote=False, remote_contains_head=False), "diverged")

    def test_seven_empty_runs_are_flagged_but_never_quarantined(self) -> None:
        with TemporaryDirectory() as temp_dir:
            ledger = SourceHealthLedger(Path(temp_dir) / "health.json")
            for _ in range(7):
                ledger.record_empty("Intermittent feed", 5)
            self.assertEqual(ledger.records["Intermittent feed"]["status"], "needs_review")
            self.assertFalse(ledger.is_quarantined("Intermittent feed"))

    def test_failed_push_is_reported_as_deployment_failure(self) -> None:
        class Result:
            def __init__(self, stdout: str = "") -> None:
                self.stdout = stdout

        def fake_run(args, **kwargs):
            if args[1] == "push":
                raise CalledProcessError(1, args, stderr=b"network unavailable")
            if args[1] == "rev-parse":
                return Result("abc123\n")
            return Result()

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "insights").mkdir()
            (root / "insights" / "test.html").write_text("test", encoding="utf-8")
            for name in ("insights.json", "feed.xml", "sitemap.xml"):
                (root / name).write_text("", encoding="utf-8")
            with (
                patch.object(daily_news_agent, "SITE_ROOT", root),
                patch.object(daily_news_agent, "ESSAY_QUEUE", root / "queue.json"),
                patch.object(daily_news_agent.subprocess, "run", side_effect=fake_run),
            ):
                result = daily_news_agent.git_commit_push([{"slug": "test", "title": "Test"}])
        self.assertTrue(result["commit_created"])
        self.assertFalse(result["push_ok"])
        self.assertEqual(result["commit_sha"], "abc123")


if __name__ == "__main__":
    unittest.main()
