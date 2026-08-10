"""Slate selection: quality is a floor, diversity is a preference.

The defining test is `WeakItemsAreNeverPromoted` — the old rule handed a slot to
whatever a sector had, which is how an explainer reached an edition.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intelligence_object import (  # noqa: E402
    EvidenceLevel,
    IntelligenceObject,
    RetrievalStatus,
    SourceRef,
)
from selection import (  # noqa: E402
    DEFAULT_DAILY_TARGET,
    MAX_DAILY_ARTICLES,
    QUALITY_FLOOR,
    TIER_A_FLOOR,
    assign_depth,
    build_slates,
    format_slate,
    select_for_sector,
)


def obj(title, score, *, sector="commercial_real_estate", eligible=True,
        publisher="Wire", evidence=EvidenceLevel.CORROBORATED,
        full_text=True, sources=2) -> IntelligenceObject:
    refs = [
        SourceRef(item_id=f"{title[:6]}{i}", source_name=publisher,
                  canonical_url=f"https://{publisher.lower().replace(' ','')}.com/{title[:8]}{i}",
                  retrieval_status=RetrievalStatus.FULL_TEXT if full_text else RetrievalStatus.SUMMARY_ONLY,
                  text_chars=4000 if full_text else 150)
        for i in range(sources)
    ]
    node = IntelligenceObject(
        object_id=title[:12], cluster_id=title[:12], primary_sector=sector,
        title=title, sources=refs, eligible=eligible, final_score=score,
    )
    node.assess_evidence()
    node.evidence_level = evidence
    return node


class WeakItemsAreNeverPromoted(unittest.TestCase):
    """A slot stays empty rather than being filled with something weak."""

    def test_a_sector_with_only_weak_items_returns_an_empty_slate(self) -> None:
        slate = select_for_sector(
            [obj("Weak thing one", 12.0, sector="data_centers"),
             obj("Weak thing two", 20.0, sector="data_centers")],
            "data_centers", target=10,
        )
        self.assertEqual(slate.selected, [])
        self.assertEqual(slate.shortfall, 10)
        self.assertIn("quality floor", slate.shortfall_reason)

    def test_an_ineligible_item_is_never_selected_however_high_it_scores(self) -> None:
        slate = select_for_sector(
            [obj("Explainer with a huge score", 95.0, sector="data_centers", eligible=False)],
            "data_centers",
        )
        self.assertEqual(slate.selected, [])
        self.assertEqual(slate.eligible, 0)

    def test_diversity_never_promotes_something_below_the_floor(self) -> None:
        objects = [obj(f"Strong CRE {i}", 80.0 - i) for i in range(3)]
        objects.append(obj("Weak data centre item", 10.0, sector="data_centers"))
        report = build_slates(objects)
        self.assertEqual(report.sectors["data_centers"].selected, [])
        self.assertTrue(any(s["sector"] == "data_centers" for s in report.shortfalls))

    def test_the_floor_matches_the_publishable_band(self) -> None:
        self.assertEqual(QUALITY_FLOOR, 40.0)
        weak = obj("Internally not publishable", 39.9)
        weak.tier = "not_publishable"
        self.assertEqual(select_for_sector([weak], weak.primary_sector).selected, [])

    def test_not_publishable_band_never_advances_even_with_a_high_score(self) -> None:
        contradictory = obj("Bad classification", 90.0)
        contradictory.tier = "not_publishable"
        self.assertEqual(
            select_for_sector([contradictory], contradictory.primary_sector).selected,
            [],
        )


class RankingAndExplanation(unittest.TestCase):
    def test_items_are_ranked_by_score(self) -> None:
        slate = select_for_sector(
            [obj("Third", 55.0), obj("First", 88.0), obj("Second", 71.0)],
            "commercial_real_estate",
        )
        self.assertEqual([o.title for o in slate.selected], ["First", "Second", "Third"])
        self.assertEqual([o.sector_rank for o in slate.selected], [1, 2, 3])

    def test_every_selection_records_why(self) -> None:
        slate = select_for_sector([obj("A deal", 72.0)], "commercial_real_estate")
        chosen = slate.selected[0]
        self.assertTrue(chosen.selected)
        self.assertIn("rank 1", chosen.selection_rationale)
        self.assertIn("evidence", chosen.selection_rationale)
        self.assertEqual(chosen.validate(), [])

    def test_it_explains_why_the_last_in_beat_the_first_out(self) -> None:
        objects = [obj(f"Deal {i}", 90.0 - i * 5) for i in range(6)]
        slate = select_for_sector(objects, "commercial_real_estate", target=3)
        self.assertEqual(len(slate.selected), 3)
        self.assertIsNotNone(slate.runner_up)
        self.assertIn("took the final slot", slate.runner_up["explanation"])
        self.assertGreater(slate.runner_up["gap_to_last_selected"], 0)

    def test_global_ranking_spans_sectors(self) -> None:
        report = build_slates([
            obj("Huge CRE deal", 88.0),
            obj("Huge energy deal", 92.0, sector="energy"),
            obj("Modest CRE deal", 61.0),
        ])
        self.assertEqual(report.global_top[0].title, "Huge energy deal")
        self.assertEqual(report.global_top[0].global_rank, 1)
        self.assertEqual(report.total_selected, 3)

    def test_only_the_bounded_global_slate_reaches_publication(self) -> None:
        objects = [
            obj(f"Publishable deal {i}", 90.0 - i, sector="commercial_real_estate")
            for i in range(8)
        ]
        report = build_slates(objects, publication_target=3, article_limit=5)
        self.assertEqual(len(report.publication_slate), 5)
        self.assertEqual([o.final_score for o in report.publication_slate], [90, 89, 88, 87, 86])
        self.assertTrue(report.publication_target_met)
        self.assertIsNotNone(report.publication_runner_up)

    def test_default_contract_is_three_with_a_hard_maximum_of_five(self) -> None:
        objects = [obj(f"Deal {i}", 90.0 - i) for i in range(12)]
        report = build_slates(objects)
        self.assertEqual(report.publication_target, DEFAULT_DAILY_TARGET)
        self.assertEqual(report.article_limit, MAX_DAILY_ARTICLES)
        self.assertEqual(len(report.publication_slate), MAX_DAILY_ARTICLES)

    def test_article_limit_cannot_exceed_the_system_maximum(self) -> None:
        objects = [obj(f"Deal {i}", 90.0 - i) for i in range(12)]
        report = build_slates(objects, publication_target=9, article_limit=99)
        self.assertEqual(report.publication_target, MAX_DAILY_ARTICLES)
        self.assertEqual(report.article_limit, MAX_DAILY_ARTICLES)
        self.assertEqual(len(report.publication_slate), MAX_DAILY_ARTICLES)


class DepthMatchesEvidence(unittest.TestCase):
    """Ambition is capped by what the sources can support."""

    def test_a_high_score_on_thin_evidence_gets_a_brief_not_a_feature(self) -> None:
        thin = obj("Major deal reported by one outlet", 85.0,
                   evidence=EvidenceLevel.SINGLE_SUMMARY, full_text=False, sources=1)
        self.assertGreaterEqual(thin.final_score, TIER_A_FLOOR)
        self.assertEqual(assign_depth(thin), "tier_c")

    def test_a_high_score_on_strong_evidence_earns_a_feature(self) -> None:
        strong = obj(
            "Major deal, corroborated", 85.0,
            evidence=EvidenceLevel.PRIMARY_CORROBORATED, sources=3,
        )
        for index, source in enumerate(strong.sources):
            source.source_name = f"Publisher {index}"
        self.assertEqual(assign_depth(strong), "tier_a")

    def test_two_sources_support_analysis_but_not_a_flagship(self) -> None:
        strong = obj("Major deal, two sources", 85.0, evidence=EvidenceLevel.CORROBORATED)
        self.assertEqual(assign_depth(strong), "tier_b")

    def test_a_middling_story_gets_a_standard_article(self) -> None:
        middling = obj("Solid deal", 58.0, evidence=EvidenceLevel.CORROBORATED)
        self.assertEqual(assign_depth(middling), "tier_b")

    def test_depths_are_counted_for_the_run_report(self) -> None:
        flagship = obj(
            "Big corroborated", 88.0,
            evidence=EvidenceLevel.PRIMARY_CORROBORATED, sources=3,
        )
        for index, source in enumerate(flagship.sources):
            source.source_name = f"Publisher {index}"
        report = build_slates([
            flagship,
            obj("Middling", 55.0, evidence=EvidenceLevel.CORROBORATED),
            obj("Thin", 44.0, evidence=EvidenceLevel.SINGLE_SUMMARY, full_text=False, sources=1),
        ])
        self.assertEqual(sum(report.depth_counts.values()), 3)
        self.assertIn("tier_a", report.depth_counts)


class NoDomination(unittest.TestCase):
    def test_one_publisher_does_not_take_the_whole_slate(self) -> None:
        crowd = [obj(f"Story {i} from one wire", 80.0 - i, publisher="Single Wire") for i in range(6)]
        others = [obj(f"Other story {i}", 70.0 - i, publisher=f"House {i}") for i in range(4)]
        slate = select_for_sector(crowd + others, "commercial_real_estate", target=6)
        publishers = [o.sources[0].source_name for o in slate.selected]
        self.assertLessEqual(publishers.count("Single Wire"), 3)

    def test_the_slate_still_fills_when_only_one_publisher_has_news(self) -> None:
        """Diversity is a preference, not a reason to under-deliver."""
        crowd = [obj(f"Story {i}", 80.0 - i, publisher="Only Wire") for i in range(6)]
        slate = select_for_sector(crowd, "commercial_real_estate", target=5)
        self.assertEqual(len(slate.selected), 5)


class ShortfallIsVisible(unittest.TestCase):
    """A thin day must never report itself as a clean success."""

    def test_no_candidates_is_reported_as_a_discovery_problem(self) -> None:
        slate = select_for_sector([], "fed_macro", target=10)
        self.assertEqual(slate.shortfall, 10)
        self.assertIn("source health", slate.shortfall_reason)

    def test_candidates_but_none_eligible_is_distinguished(self) -> None:
        slate = select_for_sector(
            [obj(f"Not an event {i}", 60.0, sector="fed_macro", eligible=False) for i in range(4)],
            "fed_macro", target=10,
        )
        self.assertIn("none described a real event", slate.shortfall_reason)

    def test_partial_fill_reports_the_gap(self) -> None:
        report = build_slates([obj(f"Deal {i}", 70.0 - i) for i in range(3)], target=10)
        self.assertTrue(report.has_shortfall)
        gap = report.shortfalls[0]
        self.assertEqual(gap["selected"], 3)
        self.assertEqual(gap["short_by"], 7)

    def test_a_full_slate_reports_no_shortfall(self) -> None:
        report = build_slates([obj(f"Deal {i}", 80.0 - i) for i in range(10)], target=10)
        self.assertFalse(report.has_shortfall)
        self.assertEqual(report.shortfalls, [])

    def test_the_report_serialises_for_the_run_artifact(self) -> None:
        report = build_slates([obj("A deal", 72.0)], target=10)
        payload = report.to_dict()
        self.assertIn("sectors", payload)
        self.assertIn("global_top", payload)
        self.assertIn("shortfalls", payload)
        self.assertTrue(payload["sectors"]["commercial_real_estate"]["selected"][0]["why"])

    def test_formatting_reads_cleanly(self) -> None:
        slate = select_for_sector([obj("A deal", 72.0), obj("Another", 51.0)],
                                  "commercial_real_estate", target=5)
        text = format_slate(slate)
        self.assertIn("commercial_real_estate", text)
        self.assertIn("short by 3", text)


if __name__ == "__main__":
    unittest.main()
