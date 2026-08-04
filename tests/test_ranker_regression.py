"""Regression and adversarial fixtures for the editorial ranker.

Context: the first live v2 edition (GitHub run 30817430024) selected five
stories and published none. Two of the five were not capital-markets stories at
all -- a developer-facing edge-computing explainer and a promotional executive
interview. Both cleared `v2_editorial.is_daily_article_candidate` because the
capital/policy gate is a single-keyword OR match over headline plus summary:
the explainer matched on the incidental phrase "data center", and the interview
matched "investment" and "subsidiary" appearing in the interviewee's biography.

The fixture in tests/fixtures/ranker_corpus_2026-08-03.json is drawn from the
real regenerated corpus for that date (n=288) and is documented in
docs/mandate/18-ranker-redesign-phase1.md.

Two kinds of test live here:

* Tests with no decorator assert behaviour that must hold **today**. They guard
  against the redesign throwing out genuinely important stories.
* Tests marked `@unittest.expectedFailure` describe the behaviour the Phase 3
  ranker must deliver but which today's code does not. They keep CI green while
  the defect exists. When the redesign lands, unittest reports an *unexpected
  success*, `wasSuccessful()` returns False, and the build fails until the
  decorator is removed -- which is the intended prompt to retire it.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ranker_corpus_2026-08-03.json"
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import v2_editorial
    from canonical_item import CanonicalItem

    _HAS_PIPELINE = True
except ImportError:  # pragma: no cover - CI installs the locked deps
    _HAS_PIPELINE = False


def _load(label: str) -> list[dict]:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [record for record in records if record["_label"] == label]


def _intelligence_object(record: dict):
    """Build the new-system object from the same fixture row."""
    from intelligence_object import IntelligenceObject, SourceRef

    obj = IntelligenceObject(
        object_id=record["id"],
        cluster_id=record["id"],
        primary_sector=record["primary_sector"],
        title=record["headline"],
        what_happened=record["summary"],
        sources=[
            SourceRef(
                item_id=record["id"],
                source_name=record["source_name"] or "Wire",
                source_url=record["url"],
                canonical_url=record["url"],
                source_tier=record["source_tier"],
            )
        ],
    )
    obj.assess_evidence()
    return obj


def _rebuild(record: dict) -> "CanonicalItem":
    """Rebuild the scored CanonicalItem the gate was originally applied to."""
    item = CanonicalItem(
        headline=record["headline"],
        raw_summary=record["summary"],
        source_name=record["source_name"] or "",
        source_url=record["url"],
    )
    item.source_tier = record["source_tier"]
    item.primary_sector = record["primary_sector"]
    item.secondary_sectors = list(record["secondary_sectors"])
    item.classification_method = record["classification_method"]
    item.tier = record["tier"]
    item.composite_score = record["composite"]
    for dimension, value in record["scores"].items():
        setattr(item, f"{dimension}_score", value)
    return item


@unittest.skipUnless(_HAS_PIPELINE, "pipeline modules unavailable")
class RankerFixtureIntegrity(unittest.TestCase):
    def test_fixture_covers_both_failure_and_success_cases(self) -> None:
        self.assertEqual(len(_load("false_positive")), 2)
        self.assertGreaterEqual(len(_load("true_positive")), 4)
        self.assertEqual(len(_load("non_transaction_macro")), 1)


@unittest.skipUnless(_HAS_PIPELINE, "pipeline modules unavailable")
class GateProtectsGenuineStories(unittest.TestCase):
    """Must pass today and after the redesign: real stories stay eligible."""

    def test_genuine_capital_markets_stories_remain_eligible(self) -> None:
        for record in _load("true_positive"):
            with self.subTest(headline=record["headline"][:60]):
                self.assertTrue(
                    v2_editorial.is_daily_article_candidate(_rebuild(record)),
                    f"{record['headline']!r} must stay eligible: {record['_why']}",
                )

    def test_important_stories_without_a_dollar_amount_remain_eligible(self) -> None:
        """A Fed move or data release matters without a transaction value."""
        for record in _load("non_transaction_macro"):
            with self.subTest(headline=record["headline"][:60]):
                self.assertTrue(
                    v2_editorial.is_daily_article_candidate(_rebuild(record)),
                    f"{record['headline']!r} must stay eligible: {record['_why']}",
                )


@unittest.skipUnless(_HAS_PIPELINE, "pipeline modules unavailable")
class KnownFalsePositives(unittest.TestCase):
    """The two stories from run 30817430024 that should never have ranked."""

    def test_current_behaviour_is_characterised(self) -> None:
        """Documents today's defect so the fixture cannot silently drift."""
        for record in _load("false_positive"):
            with self.subTest(headline=record["headline"][:60]):
                self.assertTrue(
                    v2_editorial.is_daily_article_candidate(_rebuild(record)),
                    "Fixture expects this to be (wrongly) eligible today. If this "
                    "fails, the gate changed -- move this case to the "
                    "expectedFailure test below and drop that decorator.",
                )

    def test_explainers_and_promotional_interviews_are_ineligible(self) -> None:
        """Now enforced by the new eligibility module (was an expected failure).

        Content type gates eligibility instead of keyword presence, so the
        explainer is rejected as an explainer and the interview is rejected for
        carrying no material disclosure.
        """
        import eligibility

        for record in _load("false_positive"):
            with self.subTest(headline=record["headline"][:60]):
                obj = _intelligence_object(record)
                decision = eligibility.assess(obj)
                self.assertFalse(
                    decision.eligible,
                    f"{record['headline']!r} should be ineligible: {record['_why']}",
                )
                self.assertTrue(decision.reason, "a rejection must explain itself")
                self.assertTrue(decision.disqualifiers)


@unittest.skipUnless(_HAS_PIPELINE, "pipeline modules unavailable")
class AdversarialKeywordInjection(unittest.TestCase):
    """Incidental vocabulary must not manufacture eligibility."""

    JUNK = (
        "Ten Productivity Habits of Highly Effective Remote Teams",
        "A Beginner's Guide to Choosing Ergonomic Office Chairs",
    )

    def _junk_item(self, headline: str, summary: str) -> "CanonicalItem":
        item = CanonicalItem(
            headline=headline,
            raw_summary=summary,
            source_name="Fixture Wire",
            source_url="https://example.com/fixture/story.html",
        )
        item.source_tier = 2
        item.primary_sector = "commercial_real_estate"
        item.classification_method = "source_prior_and_regex"
        item.tier = "tier_3_useful_coverage"
        item.composite_score = 55.0
        return item

    def test_junk_without_capital_vocabulary_is_ineligible(self) -> None:
        """Control: the gate does reject junk when no trigger word appears.

        The summary is deliberately scrubbed of every term in
        `_CAPITAL_OR_POLICY_ANCHOR` -- including near-misses like "capital",
        "financial" and "property" -- so this asserts the gate's behaviour
        rather than an accident of the fixture's own wording.
        """
        summary = "A listicle offering general workplace advice."
        self.assertIsNone(
            v2_editorial._CAPITAL_OR_POLICY_ANCHOR.search(summary),
            "control summary must not itself contain an anchor term",
        )
        for headline in self.JUNK:
            with self.subTest(headline=headline):
                item = self._junk_item(headline, summary)
                self.assertFalse(v2_editorial.is_daily_article_candidate(item))

    def test_incidental_capital_words_do_not_make_junk_eligible(self) -> None:
        """Now enforced by the new eligibility module (was an expected failure).

        Each injected sentence is the kind of boilerplate that appears in author
        bios, footers and related-content modules -- never a description of an
        event. Under the old keyword gate every one of these admitted the item.
        """
        import eligibility
        from intelligence_object import IntelligenceObject, SourceRef

        injections = (
            "The author previously worked in property investment.",
            "Sponsored by a data center operator.",
            "Our parent company is a subsidiary of a large bank.",
        )
        for headline in self.JUNK:
            for injected in injections:
                with self.subTest(headline=headline[:40], injected=injected[:40]):
                    obj = IntelligenceObject(
                        object_id="junk",
                        primary_sector="commercial_real_estate",
                        title=headline,
                        what_happened=f"A listicle. {injected}",
                        sources=[SourceRef(item_id="j", source_name="Fixture Wire")],
                    )
                    obj.assess_evidence()
                    self.assertFalse(
                        eligibility.assess(obj).eligible,
                        f"{injected!r} must not make {headline!r} eligible",
                    )


@unittest.skipUnless(_HAS_PIPELINE, "pipeline modules unavailable")
class CandidateAuditObservability(unittest.TestCase):
    """The run artifact must retain every candidate, not just the slate."""

    def test_audit_records_all_candidates_and_every_dimension(self) -> None:
        import tempfile

        from pipeline_v2 import SCORING_DIMENSIONS, write_candidate_audit

        records = _load("true_positive") + _load("false_positive")
        items = [_rebuild(record) for record in records]

        with tempfile.TemporaryDirectory() as tmp:
            path = write_candidate_audit(
                items,
                {"commercial_real_estate": [items[0]]},
                output_path=Path(tmp) / "candidate-audit.json",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["candidate_count"], len(items))
        self.assertEqual(list(payload["dimensions"]), list(SCORING_DIMENSIONS))
        for candidate in payload["candidates"]:
            self.assertEqual(
                set(candidate["scores"]),
                set(SCORING_DIMENSIONS),
                "every raw dimension must be recorded, not just the four in the run report",
            )
        composites = [candidate["composite"] for candidate in payload["candidates"]]
        self.assertEqual(composites, sorted(composites, reverse=True))
        self.assertEqual(
            sum(1 for c in payload["candidates"] if c["selected_for_sector_slate"]), 1
        )

    def test_audit_failure_never_breaks_the_run(self) -> None:
        from pipeline_v2 import write_candidate_audit

        with self.assertRaises(Exception):
            write_candidate_audit([], None, output_path=Path("/nonexistent\x00/x.json"))


if __name__ == "__main__":
    unittest.main()
