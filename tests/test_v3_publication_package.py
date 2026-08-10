"""The v3 release package includes public assets and durable next-run state."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import edition_manager  # noqa: E402
import v3_publish  # noqa: E402
from insights_v3 import RunReport  # noqa: E402
from v3_publish import PublishReport, finalize_publication  # noqa: E402


class CompleteReleasePackage(unittest.TestCase):
    def test_article_payload_never_reports_zero_when_a_source_is_present(self) -> None:
        draft = SimpleNamespace(
            depth="tier_c",
            article={
                "title": "A sourced brief",
                "excerpt": "A concise sourced brief.",
                "sources": [{"name": "Example Markets", "url": "https://example.com/story"}],
            },
        )
        obj = SimpleNamespace(
            title="A sourced brief",
            primary_sector="commercial_real_estate",
            primary_subsector="multifamily",
            event_type="transaction",
            object_id="event-1",
            final_score=50,
            evidence_level="single_full_text",
            usable_full_text_count=1,
            facts=[],
            independent_source_count=0,
            sources=[],
        )

        article = v3_publish._article_payload(draft, obj, "a-sourced-brief")

        self.assertEqual(article["source_count"], 1)

    def test_manifest_carries_memory_spend_edition_and_public_files(self) -> None:
        root = Path(tempfile.mkdtemp())
        state = root / ".editorial-state"
        insights = root / "insights"
        editions = root / "editions"
        for directory in (state, insights, editions, state / "runs"):
            directory.mkdir(parents=True, exist_ok=True)

        public = [
            insights / "apollo-closes-fund.html",
            root / "insights.json",
            root / "feed.xml",
            root / "sitemap.xml",
        ]
        public[0].write_text("<html></html>", encoding="utf-8")
        public[1].write_text("[]", encoding="utf-8")
        public[2].write_text("<rss/>", encoding="utf-8")
        public[3].write_text("<urlset/>", encoding="utf-8")
        memory_path = state / "editorial-memory.json"
        ledger_path = state / "spend-ledger.json"
        provider_path = state / "provider-log.jsonl"
        source_health = state / "source-health.json"
        memory_path.write_text('{"events": []}\n', encoding="utf-8")
        ledger_path.write_text('{"days": {}}\n', encoding="utf-8")
        provider_path.write_text('{"event": "provider_call"}\n', encoding="utf-8")
        source_health.write_text("{}\n", encoding="utf-8")
        (state / "v3-candidates.json").write_text("{}\n", encoding="utf-8")

        report = PublishReport(
            requested=1,
            published=1,
            files_written=[str(path.relative_to(root)).replace("\\", "/") for path in public],
            articles=[{
                "event_id": "event-1",
                "title": "Apollo Closes Fund",
                "slug": "apollo-closes-fund",
                "url": "/insights/apollo-closes-fund.html",
                "format": "brief",
                "source_count": 2,
                "must_read_score": 81,
                "selection_tier": "v3_daily_slate",
            }],
        )
        run_report = RunReport(
            mode="publish", documents_ingested=100, objects_after_clustering=80,
            daily_target=3, publication_candidates=3,
        )
        constants = {
            "SITE_ROOT": root,
            "EDITIONS_DIR": editions,
            "LATEST_EDITION_PATH": root / "latest-edition.json",
            "STATE_DIR": state,
            "RUNS_DIR": state / "runs",
            "EVENT_MEMORY_PATH": state / "event-memory.json",
            "GENERATED_FILES_PATH": state / "generated-files.json",
            "PUBLICATION_DECISION_PATH": state / "publication-decision.json",
        }
        with ExitStack() as stack:
            stack.enter_context(patch.object(v3_publish, "SITE_ROOT", root))
            stack.enter_context(patch.object(v3_publish, "INSIGHTS_DIR", insights))
            for name, value in constants.items():
                stack.enter_context(patch.object(edition_manager, name, value))
            stack.enter_context(patch("validate_publication.validate_repository", return_value=[]))
            finalize_publication(
                report,
                run_report,
                None,
                [],
                memory=SimpleNamespace(path=memory_path),
                budget=SimpleNamespace(ledger_path=ledger_path),
                state_dir=state,
            )

        generated = json.loads((state / "generated-files.json").read_text(encoding="utf-8"))
        files = set(generated["files"])
        for expected in (
            "insights/apollo-closes-fund.html",
            "insights.json",
            "feed.xml",
            "sitemap.xml",
            "latest-edition.json",
            ".editorial-state/editorial-memory.json",
            ".editorial-state/spend-ledger.json",
            ".editorial-state/provider-log.jsonl",
            ".editorial-state/source-health.json",
            ".editorial-state/publication-decision.json",
            ".editorial-state/run-summary.md",
        ):
            self.assertIn(expected, files)
        self.assertTrue(any(value.startswith("editions/") for value in files))
        self.assertNotIn(".editorial-state/v3-candidates.json", files)
        decision = json.loads((state / "publication-decision.json").read_text(encoding="utf-8"))
        self.assertTrue(decision["auto_publish_allowed"])
        self.assertFalse(decision["review_required"])
        edition = json.loads((root / "latest-edition.json").read_text(encoding="utf-8"))
        self.assertEqual(edition["briefs"][0]["source_count"], 2)


if __name__ == "__main__":
    unittest.main()
