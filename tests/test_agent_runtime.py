from __future__ import annotations

import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import CalledProcessError
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from agent_runtime import local_scheduler_enabled, sync_action
from source_health import SourceHealthLedger
try:
    import daily_news_agent
    import edition_manager
    _HAS_AGENT_DEPS = True
except ImportError:
    _HAS_AGENT_DEPS = False


class AgentRuntimeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not _HAS_AGENT_DEPS:
            raise unittest.SkipTest("feedparser not installed — skipping agent runtime tests")
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

    def test_local_scheduler_requires_explicit_lease(self) -> None:
        with TemporaryDirectory() as temp_dir:
            control = Path(temp_dir) / "scheduler.json"
            self.assertFalse(local_scheduler_enabled(control))
            control.write_text('{"active_scheduler":"github-actions"}', encoding="utf-8")
            self.assertFalse(local_scheduler_enabled(control))
            control.write_text('{"active_scheduler":"local-scheduler"}', encoding="utf-8")
            self.assertTrue(local_scheduler_enabled(control))

    def test_failed_push_is_reported_as_deployment_failure(self) -> None:
        def fake_run(args, **kwargs):
            raise CalledProcessError(1, args, stderr="network unavailable")

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "insights").mkdir()
            (root / "insights" / "test.html").write_text("test", encoding="utf-8")
            for name in ("insights.json", "feed.xml", "sitemap.xml"):
                (root / name).write_text("", encoding="utf-8")
            state = root / ".editorial-state"
            state.mkdir()
            (state / "generated-files.json").write_text(
                '{"schema_version":1,"files":["insights/test.html","insights.json","feed.xml","sitemap.xml"]}',
                encoding="utf-8",
            )
            with (
                patch.object(daily_news_agent, "SITE_ROOT", root),
                patch.object(daily_news_agent, "ESSAY_QUEUE", root / "queue.json"),
                patch.object(daily_news_agent.subprocess, "run", side_effect=fake_run),
            ):
                with redirect_stdout(StringIO()):
                    result = daily_news_agent.git_commit_push([{"slug": "test", "title": "Test"}])
        self.assertTrue(result["attempted"])
        self.assertFalse(result["commit_created"])
        self.assertFalse(result["push_ok"])
        self.assertIn("network unavailable", result["error"])

    def test_no_candidate_edition_still_writes_complete_workflow_contract(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / ".editorial-state"
            with (
                patch.object(daily_news_agent, "SITE_ROOT", root),
                patch.object(daily_news_agent, "SOURCE_HEALTH_FILE", state / "source-health.json"),
                patch.object(daily_news_agent, "LOG_FILE", root / "agent-log.json"),
                patch.object(daily_news_agent, "validate_repository", return_value=[]),
                patch.object(edition_manager, "SITE_ROOT", root),
                patch.object(edition_manager, "EDITIONS_DIR", root / "editions"),
                patch.object(edition_manager, "LATEST_EDITION_PATH", root / "latest-edition.json"),
                patch.object(edition_manager, "STATE_DIR", state),
                patch.object(edition_manager, "RUNS_DIR", state / "runs"),
                patch.object(edition_manager, "EVENT_MEMORY_PATH", state / "event-memory.json"),
                patch.object(edition_manager, "GENERATED_FILES_PATH", state / "generated-files.json"),
                patch.object(edition_manager, "PUBLICATION_DECISION_PATH", state / "publication-decision.json"),
            ):
                with redirect_stdout(StringIO()):
                    daily_news_agent.finalize_no_story_edition(
                        start=daily_news_agent.datetime(
                            2026, 7, 23, 12, 0, tzinfo=daily_news_agent.timezone.utc
                        ),
                        run_data={"raw_count": 0, "candidate_count": 0},
                        args=SimpleNamespace(
                            dry_run=False,
                            shadow=False,
                            skip_git=True,
                            run_origin="github-actions",
                        ),
                        reason="No event cleared triage.",
                    )

            decision = json.loads(
                (state / "publication-decision.json").read_text(encoding="utf-8")
            )
            manifest = json.loads(
                (state / "generated-files.json").read_text(encoding="utf-8")
            )
            latest = json.loads((root / "latest-edition.json").read_text(encoding="utf-8"))
        self.assertEqual(latest["status"], "no_publishable_story")
        self.assertFalse(decision["review_required"])
        self.assertTrue(decision["auto_publish_allowed"])
        self.assertIn("latest-edition.json", manifest["files"])
        self.assertIn(".editorial-state/run-summary.md", manifest["files"])

    def test_data_note_uses_ink_not_white_for_metric_values(self) -> None:
        article = {
            "slug": "contrast-check",
            "title": "Contrast Check",
            "subtitle": "A source-backed visual check.",
            "category": "Capital Markets",
            "meta_description": "A source-backed visual check.",
            "date_iso": "2026-07-28",
            "date": "July 28, 2026",
            "tags": ["contrast"],
            "body_html": "<p>Reported detail.</p>",
            "sources": [{"name": "Source", "url": "https://example.org/source"}],
            "data_points": [{"label": "Reported metric", "value": "$14.6M"}],
        }
        html = daily_news_agent.render_html(article)
        self.assertIn('class="article-data-point"><strong>$14.6M</strong>', html)
        self.assertIn(
            ".article-data-point strong { font-family: var(--serif); font-size: 1.65rem; color: var(--body-txt); }",
            html,
        )
        stylesheet = (ROOT / "experience-2026.css").read_text(encoding="utf-8")
        self.assertIn(".article-data-note .article-data-point strong", stylesheet)
        self.assertIn("color: var(--x26-ink) !important;", stylesheet)


if __name__ == "__main__":
    unittest.main()
