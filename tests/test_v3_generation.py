"""Writing the selected stories: in parallel, on budget, within the evidence.

The pipeline is faked throughout, so these run offline. What they check is the
bridge: that depth follows evidence, that the dossier contains only what the
object holds, that concurrency actually happens, and that money and time stop
work rather than being discovered afterwards.
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v3_generation  # noqa: E402
from budget import Budget  # noqa: E402
from intelligence_object import (  # noqa: E402
    EvidenceLevel,
    Fact,
    IntelligenceObject,
    RetrievalStatus,
    SourceRef,
)
from v3_generation import (  # noqa: E402
    DEPTH_SPEC,
    object_to_canonical,
    object_to_dossier,
    write_all,
    write_one,
)


def _obj(title: str, *, depth: str = "tier_b", sources: int = 1,
         full_text: bool = True, score: float = 55.0,
         sector: str = "commercial_real_estate") -> IntelligenceObject:
    refs = [
        SourceRef(
            item_id=f"s{i}", source_name=f"Publisher {i}",
            canonical_url=f"https://p{i}.example.com/story",
            source_tier=2, text_chars=4000 if full_text else 200,
            retrieved_text=("Blackstone closed the transaction for $450 million."
                            if full_text else ""),
            retrieval_status=RetrievalStatus.FULL_TEXT if full_text else RetrievalStatus.SUMMARY_ONLY,
        )
        for i in range(sources)
    ]
    node = IntelligenceObject(
        object_id=f"obj-{abs(hash(title)) % 99999}", cluster_id="c",
        primary_sector=sector, title=title,
        what_happened="A transaction occurred.", sources=refs,
        final_score=score, eligible=True, selected=True,
        selection_rationale="ranked in sector",
    )
    node.assess_evidence()
    node.cap_depth_to_evidence(depth)
    return node


def _budget(daily=5.0) -> Budget:
    return Budget(ledger_path=Path(tempfile.mkdtemp()) / "l.json",
                  config={"cost_limits": {"max_daily_llm_cost_usd": daily,
                                          "max_per_article_cost_usd": 0.50},
                          "timing": {"pipeline_timeout_minutes": 330,
                                     "per_phase_timeout_seconds": {}}})


class _FakePipeline:
    """Stands in for the seven-stage writer."""

    def __init__(self, *, delay=0.0, status="completed", raises=False):
        self.delay, self.status, self.raises = delay, status, raises
        self.calls: list[dict] = []

    def __call__(self, item, dossier=None, api_key="", provider=None, article_format=None):
        self.calls.append({"item": item, "dossier": dossier, "format": article_format})
        if self.delay:
            time.sleep(self.delay)
        if self.raises:
            raise RuntimeError("model unavailable")
        return {
            "status": self.status,
            "article": {"title": item.headline, "body_html": "<p>text</p>"}
                       if self.status in ("completed", "revised", "review_required") else None,
            "stages_run": ["draft", "review"],
            "errors": [],
        }


def _install(monkey: _FakePipeline):
    import editorial_pipeline
    original = editorial_pipeline.run_editorial_pipeline
    editorial_pipeline.run_editorial_pipeline = monkey
    return original


def _restore(original):
    import editorial_pipeline
    editorial_pipeline.run_editorial_pipeline = original


class DepthFollowsEvidence(unittest.TestCase):
    """The fix for stories held over claims their sources could not support."""

    def test_a_summary_only_story_is_written_as_a_brief(self) -> None:
        obj = _obj("Small deal closes", depth="tier_a", full_text=False)
        self.assertEqual(obj.evidence_level, EvidenceLevel.SINGLE_SUMMARY)
        self.assertEqual(obj.recommended_depth, "tier_c")

        fake = _FakePipeline()
        original = _install(fake)
        try:
            write_one(obj, budget=_budget())
        finally:
            _restore(original)
        self.assertEqual(fake.calls[0]["format"], DEPTH_SPEC["tier_c"]["format"])

    def test_a_corroborated_story_earns_the_full_treatment(self) -> None:
        obj = _obj("Major acquisition completes", depth="tier_a", sources=2)
        self.assertEqual(obj.recommended_depth, "tier_a")

        fake = _FakePipeline()
        original = _install(fake)
        try:
            write_one(obj, budget=_budget())
        finally:
            _restore(original)
        self.assertEqual(fake.calls[0]["format"], DEPTH_SPEC["tier_a"]["format"])

    def test_an_unsupportable_story_is_not_written_at_all(self) -> None:
        obj = _obj("Nothing to go on", depth="tier_c")
        obj.sources = []
        obj.assess_evidence()
        obj.cap_depth_to_evidence("tier_c")
        self.assertEqual(obj.recommended_depth, "none")

        result = write_one(obj, budget=_budget())
        self.assertEqual(result.status, "skipped")
        self.assertIn("does not support", result.skipped_reason)


class TheDossierIsTheBoundary(unittest.TestCase):
    def test_it_carries_only_what_the_object_holds(self) -> None:
        obj = _obj("Deal closes", sources=2)
        obj.facts = [Fact(name="price", value=450_000_000, unit="USD",
                          evidence_span="$450 million", source_item_id="s0")]
        dossier = object_to_dossier(obj)
        self.assertEqual(len(dossier["sources"]), 2)
        self.assertEqual(dossier["facts"][0]["evidence"], "$450 million")
        self.assertEqual(dossier["independent_source_count"], 2)
        self.assertIn("evidence_level_note", dossier)
        self.assertIn("$450 million", dossier["sources"][0]["text"])

    def test_a_thin_dossier_says_so_in_words_the_writer_will_read(self) -> None:
        dossier = object_to_dossier(_obj("Thin story", full_text=False))
        self.assertIn("do not advance a thesis", dossier["evidence_level_note"].lower())

    def test_prior_coverage_travels_with_the_story(self) -> None:
        obj = _obj("Follow-up story")
        obj.prior_published_slugs = ["earlier-article"]
        obj.material_changes = ["figure moved from $2.5bn to $3.3bn"]
        dossier = object_to_dossier(obj)
        self.assertEqual(dossier["prior_coverage"], ["earlier-article"])
        self.assertTrue(dossier["material_changes"])

    def test_the_canonical_item_keeps_identity_and_sector(self) -> None:
        obj = _obj("Deal closes", sector="private_equity")
        item = object_to_canonical(obj)
        self.assertEqual(item.item_id, obj.object_id)
        self.assertEqual(item.headline, obj.title)
        self.assertEqual(item.primary_sector, "private_equity")


class WritesConcurrently(unittest.TestCase):
    """Forty-seven articles in series will not fit the job window."""

    def test_articles_are_written_in_parallel_not_one_by_one(self) -> None:
        objects = [_obj(f"Story number {i}") for i in range(6)]
        fake = _FakePipeline(delay=0.25)
        original = _install(fake)
        try:
            started = time.perf_counter()
            _, report = write_all(objects, budget=_budget(), workers=6, verbose=False)
            elapsed = time.perf_counter() - started
        finally:
            _restore(original)
        self.assertEqual(report.written, 6)
        self.assertLess(elapsed, 1.0,
                        "six articles at 0.25s each must not take 1.5s in series")

    def test_the_deepest_stories_are_written_first(self) -> None:
        objects = [
            _obj("Brief story", depth="tier_c", full_text=False),
            _obj("Feature story", depth="tier_a", sources=2),
            _obj("Standard story", depth="tier_b"),
        ]
        fake = _FakePipeline()
        original = _install(fake)
        try:
            write_all(objects, budget=_budget(), workers=1, verbose=False)
        finally:
            _restore(original)
        formats = [c["format"] for c in fake.calls]
        self.assertEqual(formats[0], DEPTH_SPEC["tier_a"]["format"],
                         "if time runs out the most important must already be written")


class MoneyAndTimeStopWork(unittest.TestCase):
    def test_generation_stops_when_the_budget_is_gone(self) -> None:
        budget = _budget(daily=0.10)
        objects = [_obj(f"Story {i}", depth="tier_a", sources=2) for i in range(5)]
        fake = _FakePipeline()
        original = _install(fake)
        try:
            _, report = write_all(objects, budget=budget, workers=1, verbose=False)
        finally:
            _restore(original)
        self.assertGreater(report.skipped_budget, 0)
        self.assertLess(report.written, 5)
        self.assertLessEqual(budget.spent_today, 0.11)

    def test_spend_is_attributed_per_article(self) -> None:
        budget = _budget()
        fake = _FakePipeline()
        original = _install(fake)
        try:
            result = write_one(_obj("A story", sources=2), budget=budget)
        finally:
            _restore(original)
        self.assertGreater(result.usd, 0)
        self.assertIn(result.object_id, budget.article_usd)

    def test_the_generation_window_closes(self) -> None:
        objects = [_obj(f"Story {i}") for i in range(4)]
        fake = _FakePipeline(delay=0.2)
        original = _install(fake)
        try:
            _, report = write_all(objects, budget=_budget(), workers=1,
                                  deadline_s=0.25, verbose=False)
        finally:
            _restore(original)
        self.assertGreater(report.skipped_budget, 0, "the window must cut work short")


class FailureIsolation(unittest.TestCase):
    def test_one_failed_article_does_not_stop_the_others(self) -> None:
        objects = [_obj(f"Story {i}") for i in range(3)]
        calls = {"n": 0}

        def flaky(item, dossier=None, api_key="", provider=None, article_format=None):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("model unavailable")
            return {"status": "completed", "article": {"title": item.headline},
                    "stages_run": [], "errors": []}

        original = _install(flaky)
        try:
            _, report = write_all(objects, budget=_budget(), workers=1, verbose=False)
        finally:
            _restore(original)
        self.assertEqual(report.written, 2)
        self.assertEqual(report.failed, 1)

    def test_a_held_article_is_counted_separately_from_a_failure(self) -> None:
        """Held means the gates produced no article; failed means it errored."""
        fake = _FakePipeline(status="draft_failed")
        original = _install(fake)
        try:
            _, report = write_all([_obj("Held story")], budget=_budget(), verbose=False)
        finally:
            _restore(original)
        self.assertEqual(report.held, 1)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.written, 0)

    def test_nothing_to_write_is_handled(self) -> None:
        _, report = write_all([], budget=_budget(), verbose=False)
        self.assertEqual(report.requested, 0)
        self.assertEqual(report.written, 0)


class StatusVocabularyMatchesThePipeline(unittest.TestCase):
    """A one-letter mismatch reported 0 written when 7 articles existed."""

    def test_the_success_status_is_the_one_the_pipeline_returns(self) -> None:
        source = (ROOT / "scripts" / "editorial_pipeline.py").read_text(encoding="utf-8")
        self.assertIn('"completed"', source)
        self.assertIn("completed", v3_generation.DraftResult.SUCCESS_STATUSES)

    def test_a_completed_article_counts_as_written(self) -> None:
        fake = _FakePipeline(status="completed")
        original = _install(fake)
        try:
            _, report = write_all([_obj("A story")], budget=_budget(), verbose=False)
        finally:
            _restore(original)
        self.assertEqual(report.written, 1)
        self.assertEqual(report.held, 0)

    def test_review_required_is_written_but_flagged(self) -> None:
        fake = _FakePipeline(status="review_required")
        original = _install(fake)
        try:
            results, report = write_all([_obj("A story")], budget=_budget(), verbose=False)
        finally:
            _restore(original)
        self.assertEqual(report.needs_review, 1)
        self.assertEqual(report.written, 0)
        self.assertTrue(results[0].needs_review)

    def test_a_status_with_no_article_is_genuinely_held(self) -> None:
        fake = _FakePipeline(status="draft_failed")
        original = _install(fake)
        try:
            _, report = write_all([_obj("A story")], budget=_budget(), verbose=False)
        finally:
            _restore(original)
        self.assertEqual(report.written, 0)
        self.assertEqual(report.held, 1)


class DoesNotPublish(unittest.TestCase):
    def test_the_writer_has_no_route_to_the_site(self) -> None:
        source = (ROOT / "scripts" / "v3_generation.py").read_text(encoding="utf-8")
        for forbidden in ("insights.json", "sitemap.xml", "feed.xml",
                          "publish_generated", "git commit", "git push"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
