"""The v3 pipeline running as one pass, and the wall between it and production.

The most important tests here are in `ShadowIsolation`. v3 runs inside the daily
job, so it must be structurally incapable of altering the edition -- if it can
publish, select, or crash the run, the shadow is not a shadow.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import insights_v3  # noqa: E402
from insights_v3 import RunReport, format_summary  # noqa: E402
from insights_v3 import run as _run_v3  # noqa: E402

_TMP_STATE = Path(tempfile.mkdtemp())


def run(**kwargs):
    """Isolate every side effect a real run would have.

    Artifacts go to a temp directory so tests never clobber a live run's output,
    and memory is a fresh empty store -- seeded memory would mark fixture
    stories as already published and silently empty the enrichment shortlist.
    """
    from editorial_memory import EditorialMemory

    kwargs.setdefault("state_dir", _TMP_STATE)
    kwargs.setdefault("memory", EditorialMemory(Path(tempfile.mkdtemp()) / "memory.json"))
    return _run_v3(**kwargs)

FIXTURE = ROOT / "tests" / "fixtures" / "ranker_corpus_2026-08-03.json"


def _document(headline, summary="", *, sector="commercial_real_estate",
              source="Wire", url="", tier=3):
    node = types.SimpleNamespace()
    node.item_id = url or headline[:24]
    node.headline = headline
    node.raw_summary = summary
    node.raw_text = ""
    node.source_name = source
    node.source_url = url or f"https://example.com/{abs(hash(headline)) % 10**8}"
    node.canonical_url = node.source_url
    node.source_tier = tier
    node.source_authority = "secondary"
    node.primary_sector = sector
    node.secondary_sectors = []
    node.subsector = ""
    node.event_type = ""
    node.publication_date = ""
    node.classification_method = ""
    node.classification_confidence = 0.0
    node.companies = []
    node.people = []
    node.megawatts = 0
    node.transaction_value_raw = ""
    return node


def _fixture_documents():
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        _document(r["headline"], r["summary"], sector=r["primary_sector"],
                  source=r["source_name"] or "Wire", url=r["url"], tier=r["source_tier"])
        for r in records
    ]


class RunsEndToEnd(unittest.TestCase):
    def test_the_whole_pass_completes_and_reports(self) -> None:
        report, slates = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        self.assertGreater(report.documents_ingested, 0)
        self.assertGreater(report.objects_after_clustering, 0)
        self.assertIsNotNone(slates)
        self.assertGreater(report.elapsed_seconds, 0)
        self.assertTrue(report.timings, "each stage must record its duration")

    def test_the_two_known_false_positives_are_not_selected(self) -> None:
        _, slates = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        chosen = " ".join(
            o.title for slate in slates.sectors.values() for o in slate.selected
        )
        self.assertNotIn("Edge Computing", chosen)
        self.assertNotIn("Chase Bolding", chosen)

    def test_duplicates_are_consolidated_before_ranking(self) -> None:
        docs = [
            _document("Slate Property Group closes $1b managed account",
                      source="A", url="https://a.com/1"),
            _document("Slate Property Group closes $1b managed account",
                      source="B", url="https://b.com/2"),
            _document("Unrelated Denver office tower trades for $90 million"),
        ]
        report, _ = run(items=docs, enrich_limit=0, verbose=False)
        self.assertEqual(report.documents_ingested, 3)
        self.assertEqual(report.objects_after_clustering, 2)
        self.assertEqual(report.documents_consolidated, 1)

    def test_nothing_selected_below_the_quality_floor(self) -> None:
        from selection import QUALITY_FLOOR

        _, slates = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        for slate in slates.sectors.values():
            for obj in slate.selected:
                self.assertGreaterEqual(obj.final_score, QUALITY_FLOOR)
                self.assertTrue(obj.eligible)
                self.assertTrue(obj.selection_rationale)

    def test_a_short_sector_says_so_rather_than_filling_the_slate(self) -> None:
        report, _ = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        short = [s for s, d in report.sectors.items() if d["selected"] < d["target"]]
        self.assertTrue(short, "the fixture is small, so shortfalls are expected")
        for sector in short:
            self.assertTrue(
                report.sectors[sector]["shortfall_reason"],
                f"{sector} came up short without saying why",
            )

    def test_depth_never_exceeds_what_the_evidence_supports(self) -> None:
        _, slates = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        order = {"tier_a": 3, "tier_b": 2, "tier_c": 1, "none": 0}
        for slate in slates.sectors.values():
            for obj in slate.selected:
                self.assertLessEqual(
                    order[obj.recommended_depth], order[obj.max_supportable_depth],
                    f"{obj.title[:40]!r} asks for more depth than its sources carry",
                )

    def test_empty_input_degrades_quietly(self) -> None:
        report, slates = run(items=[], enrich_limit=0, verbose=False)
        self.assertEqual(report.documents_ingested, 0)
        self.assertIsNone(slates)
        self.assertTrue(report.errors)


class WritesArtifacts(unittest.TestCase):
    def test_the_full_candidate_universe_is_persisted(self) -> None:
        run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        path = _TMP_STATE / "v3-candidates.json"
        self.assertTrue(path.exists())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreater(payload["count"], 0)
        self.assertEqual(len(payload["candidates"]), payload["count"])
        first = payload["candidates"][0]
        for key in ("importance_components", "eligibility_reason", "final_score", "sources"):
            self.assertIn(key, first)

    def test_the_run_report_and_slates_are_written(self) -> None:
        run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        for name in ("v3-run.json", "v3-slates.json"):
            path = _TMP_STATE / name
            self.assertTrue(path.exists(), name)
            json.loads(path.read_text(encoding="utf-8"))

    def test_the_summary_is_ascii_safe_for_a_windows_console(self) -> None:
        """A stray arrow once aborted the whole run at the final print."""
        report, _ = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        summary = format_summary(report)
        summary.encode("cp1252")  # raises if a non-ASCII character slipped in


class ShadowIsolation(unittest.TestCase):
    """v3 must be unable to affect the edition it runs beside."""

    def test_the_orchestrator_never_touches_public_indexes_directly(self) -> None:
        source = (ROOT / "scripts" / "insights_v3.py").read_text(encoding="utf-8")
        for forbidden in ("insights.json", "sitemap.xml", "feed.xml",
                          "publish_generated", "git commit", "git push"):
            self.assertNotIn(forbidden, source,
                             f"the orchestrator references {forbidden!r} directly")

    def test_default_mode_is_shadow_and_does_not_write_or_publish(self) -> None:
        report, _ = run(items=_fixture_documents(), enrich_limit=0, verbose=False)
        self.assertEqual(report.mode, "shadow")
        self.assertEqual(report.generation, {})
        self.assertEqual(report.publication, {})

    def test_shadow_rejects_generation_or_publication(self) -> None:
        with self.assertRaisesRegex(ValueError, "shadow mode"):
            run(items=_fixture_documents(), enrich_limit=0, generate=True, verbose=False)
        with self.assertRaisesRegex(ValueError, "shadow mode"):
            run(items=_fixture_documents(), enrich_limit=0,
                generate=True, publish_articles=True, verbose=False)

    def test_preview_generates_but_cannot_publish(self) -> None:
        with self.assertRaisesRegex(ValueError, "preview mode"):
            run(items=_fixture_documents(), enrich_limit=0, mode="preview",
                publish_articles=True, generate=True, verbose=False)

    def test_publication_requires_generation_when_called_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires generation"):
            run(items=_fixture_documents(), enrich_limit=0, mode="publish",
                publish_articles=True, generate=False, verbose=False)

    def test_generation_is_bounded_to_the_global_publication_slate(self) -> None:
        source = (ROOT / "scripts" / "insights_v3.py").read_text(encoding="utf-8")
        self.assertIn("chosen = list(slate_report.publication_slate)", source)
        self.assertNotIn(
            "chosen = [o for s in slate_report.sectors.values() for o in s.selected]",
            source,
        )

    def test_v3_writes_only_inside_the_editorial_state_directory(self) -> None:
        self.assertEqual(insights_v3.STATE_DIR.name, ".editorial-state")
        self.assertEqual(insights_v3.STATE_DIR.parent, insights_v3.SITE_ROOT)

    def test_the_daily_agent_swallows_a_v3_failure(self) -> None:
        agent = (ROOT / "scripts" / "daily_news_agent.py").read_text(encoding="utf-8")
        self.assertIn("--shadow-v3", agent)
        block = agent[agent.index("if args.shadow_v3:"):]
        block = block[: block.index("v2_results = None")]
        self.assertIn("except Exception", block,
                      "a v3 failure must never reach the edition")
        self.assertIn("production continues", block)

    def test_the_workflow_runs_v3_with_an_explicit_v2_rollback_path(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "daily-insights-agent.yml").read_text(encoding="utf-8")
        self.assertIn("python insights_v3.py", workflow)
        self.assertIn("inputs.pipeline || 'v3'", workflow)
        self.assertIn("v2)", workflow)
        self.assertIn("--pipeline-v2", workflow,
                      "v2 must remain available as the operator rollback path")


class BoundedWork(unittest.TestCase):
    def test_enrichment_is_capped_by_count(self) -> None:
        calls = {"n": 0}

        def _fake_enrich(objects, **kwargs):  # noqa: ARG001
            calls["n"] = len(list(objects))
            from retrieval import RetrievalReport
            return RetrievalReport(requested=calls["n"])

        import retrieval
        original = retrieval.enrich_objects
        retrieval.enrich_objects = _fake_enrich
        try:
            report, _ = run(items=_fixture_documents(), enrich_limit=3, verbose=False)
        finally:
            retrieval.enrich_objects = original
        self.assertLessEqual(calls["n"], 3)
        self.assertLessEqual(report.enriched, 3)

    def test_only_eligible_candidates_are_read(self) -> None:
        seen = {"objects": []}

        def _fake_enrich(objects, **kwargs):  # noqa: ARG001
            seen["objects"] = list(objects)
            from retrieval import RetrievalReport
            return RetrievalReport(requested=len(seen["objects"]))

        import retrieval
        original = retrieval.enrich_objects
        retrieval.enrich_objects = _fake_enrich
        try:
            run(items=_fixture_documents(), enrich_limit=50, verbose=False)
        finally:
            retrieval.enrich_objects = original
        self.assertTrue(seen["objects"])
        self.assertTrue(all(o.eligible for o in seen["objects"]),
                        "expensive reading must not be spent on ineligible items")


if __name__ == "__main__":
    unittest.main()
