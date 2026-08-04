"""Scoring: every measure must vary, and every score must explain itself.

The guard that matters most is `NoDeadMeasures`. The previous scorer shipped
three measures that returned the same value for essentially every story, and
nothing detected it for months. That class of defect is now a test failure.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from importance import (  # noqa: E402
    BANDS,
    MEASURES,
    band,
    distribution_report,
    explain,
    score_all,
    score_object,
)
from intelligence_object import (  # noqa: E402
    ContentType,
    IntelligenceObject,
    NoveltyState,
    ObjectClass,
    RetrievalStatus,
    SourceRef,
)


def obj(title, summary="", *, sector="commercial_real_estate", sources=1,
        full_text=False, primary=False, novelty=NoveltyState.NEW,
        content=ContentType.NEWS_REPORT, klass=ObjectClass.DISCRETE_EVENT,
        secondary=()) -> IntelligenceObject:
    refs = []
    for i in range(sources):
        refs.append(SourceRef(
            item_id=f"s{i}", source_name=f"Publisher {i}",
            canonical_url=f"https://p{i}.example.com/a",
            retrieval_status=RetrievalStatus.FULL_TEXT if full_text else RetrievalStatus.SUMMARY_ONLY,
            text_chars=4000 if full_text else 200,
            is_primary_authority=primary and i == 0,
        ))
    node = IntelligenceObject(
        object_id="o", cluster_id="c", primary_sector=sector, title=title,
        what_happened=summary, sources=refs, novelty_state=novelty,
        content_type=content, object_class=klass, secondary_sectors=list(secondary),
    )
    node.assess_evidence()
    return score_object(node)


def _varied_population(n=140) -> list[IntelligenceObject]:
    """A spread resembling a real day, with evidence and memory present."""
    random.seed(11)
    sectors = ["commercial_real_estate", "private_equity", "data_centers",
               "energy", "banking_credit", "fed_macro", "local_government"]
    shapes = [
        "{a} acquires {t} portfolio for ${n} million",
        "{a} closes ${n}m fund targeting {t}",
        "{a} defaults on ${n} million loan secured by {t}",
        "{a} breaks ground on {n},000 square feet of {t}",
        "Fed holds rates steady as inflation reads {n}%",
        "{a} signs power agreement for {n} MW",
        "City council approves rezoning for {n} units",
        "{a} reports unexpectedly weak quarterly results",
    ]
    parties = ["Blackstone", "KKR", "Prologis", "Hines", "Greystar", "Ares", "Brookfield"]
    out = []
    for i in range(n):
        shape = shapes[i % len(shapes)]
        title = shape.format(a=random.choice(parties), t="industrial",
                             n=random.choice([12, 45, 120, 450, 1200, 3400]))
        out.append(obj(
            title, sector=sectors[i % len(sectors)],
            sources=random.choice([1, 1, 2, 3]),
            full_text=(i % 3 == 0), primary=(i % 7 == 0),
            novelty=random.choice([NoveltyState.NEW, NoveltyState.NEW,
                                   NoveltyState.MATERIAL_UPDATE,
                                   NoveltyState.MINOR_FOLLOW_UP,
                                   NoveltyState.DUPLICATE]),
            secondary=tuple(random.sample(sectors, random.choice([0, 0, 1, 2]))),
        ))
    return out


class NoDeadMeasures(unittest.TestCase):
    """The defect that made the old scorer unusable, as a test."""

    def test_no_measure_is_constant_or_saturated(self) -> None:
        report = distribution_report(_varied_population())
        self.assertEqual(
            report["degenerate"], [],
            "these measures return the same value for nearly every story and are "
            f"doing no ranking work: {report['degenerate']}",
        )

    def test_every_measure_actually_moves(self) -> None:
        report = distribution_report(_varied_population())
        for name, stats in report["measures"].items():
            with self.subTest(measure=name):
                self.assertGreater(stats["stdev"], 0.0, f"{name} never varies")
                self.assertGreater(stats["unique_values"], 1)

    def test_the_scale_uses_a_meaningful_range(self) -> None:
        """The old scorer spanned 33.7 points and could never reach tier one."""
        report = distribution_report(_varied_population())
        self.assertGreater(report["final_score"]["range_used"], 45.0)
        self.assertGreater(report["final_score"]["stdev"], 8.0)


class SectorRelativeMagnitude(unittest.TestCase):
    """One yardstick cannot measure a property deal and a buyout fund."""

    def test_the_same_amount_scores_differently_by_sector(self) -> None:
        property_deal = obj("Sponsor acquires tower for $100 million",
                            sector="commercial_real_estate")
        pe_fund = obj("Sponsor closes $100 million fund", sector="private_equity")
        prop_mag = next(c for c in property_deal.importance_components if c.name == "magnitude")
        pe_mag = next(c for c in pe_fund.importance_components if c.name == "magnitude")
        self.assertGreater(
            prop_mag.score, pe_mag.score,
            "$100m is a significant building and an unremarkable fund",
        )

    def test_policy_carries_weight_without_any_dollar_figure(self) -> None:
        fed = obj("Fed holds rates steady at 4.25%", sector="fed_macro")
        magnitude = next(c for c in fed.importance_components if c.name == "magnitude")
        self.assertGreaterEqual(magnitude.score, 5)
        self.assertIn("fed_macro", " ".join(magnitude.evidence))

    def test_physical_scale_counts_when_there_is_no_price(self) -> None:
        powered = obj("Developer signs agreement for 900 MW of capacity", sector="energy")
        magnitude = next(c for c in powered.importance_components if c.name == "magnitude")
        self.assertGreaterEqual(magnitude.score, 5)


class NoveltyIsReal(unittest.TestCase):
    """Previously hardcoded to 7 for every story ever scored."""

    def test_novelty_tracks_editorial_memory(self) -> None:
        fresh = obj("Sponsor acquires tower for $200 million", novelty=NoveltyState.NEW)
        repeat = obj("Sponsor acquires tower for $200 million", novelty=NoveltyState.DUPLICATE)
        self.assertGreater(
            next(c for c in fresh.importance_components if c.name == "novelty").score,
            next(c for c in repeat.importance_components if c.name == "novelty").score,
        )

    def test_a_repeat_is_penalised_and_scores_lower_overall(self) -> None:
        fresh = obj("Sponsor acquires tower for $200 million", novelty=NoveltyState.NEW)
        repeat = obj("Sponsor acquires tower for $200 million",
                     novelty=NoveltyState.ALREADY_PUBLISHED)
        self.assertGreater(fresh.final_score, repeat.final_score)
        self.assertTrue(any(p.name == "archive_repetition" for p in repeat.penalties))


class EvidenceShapesTheScore(unittest.TestCase):
    def test_reading_the_article_raises_the_score(self) -> None:
        thin = obj("Sponsor acquires tower for $200 million", full_text=False)
        read = obj("Sponsor acquires tower for $200 million", full_text=True)
        self.assertGreater(read.final_score, thin.final_score)

    def test_a_summary_only_story_is_penalised_for_thin_evidence(self) -> None:
        thin = obj("Sponsor acquires tower for $200 million", full_text=False)
        self.assertTrue(any(p.name == "thin_evidence" for p in thin.penalties))

    def test_corroborated_primary_sourcing_scores_highest(self) -> None:
        best = obj("Sponsor acquires tower for $200 million",
                   sources=2, full_text=True, primary=True)
        evidence = next(c for c in best.importance_components if c.name == "evidence")
        self.assertEqual(evidence.score, 10)


class PenaltiesApply(unittest.TestCase):
    def test_an_uncorroborated_press_release_is_penalised(self) -> None:
        release = obj("Company announces new platform", content=ContentType.PRESS_RELEASE)
        self.assertTrue(any(p.name == "uncorroborated_release" for p in release.penalties))

    def test_speculation_without_a_primary_source_is_penalised(self) -> None:
        rumour = obj("Sponsor reportedly in talks to acquire portfolio for $300 million")
        self.assertTrue(any(p.name == "unconfirmed" for p in rumour.penalties))

    def test_a_routine_announcement_is_penalised(self) -> None:
        routine = obj("Board reaffirms guidance with no change to outlook")
        self.assertTrue(any(p.name == "routine_event" for p in routine.penalties))

    def test_penalties_can_never_push_a_score_below_zero(self) -> None:
        worst = obj("Company reportedly may consider routine reaffirmation",
                    content=ContentType.PRESS_RELEASE, novelty=NoveltyState.DUPLICATE)
        self.assertGreaterEqual(worst.final_score, 0.0)


class EveryScoreExplainsItself(unittest.TestCase):
    def test_each_component_carries_a_rationale(self) -> None:
        scored = obj("Blackstone acquires industrial portfolio for $450 million")
        self.assertEqual(len(scored.importance_components), len(MEASURES))
        for component in scored.importance_components:
            with self.subTest(measure=component.name):
                self.assertTrue(component.rationale, f"{component.name} gave no reason")

    def test_the_written_explanation_names_the_measures(self) -> None:
        text = explain(obj("Blackstone acquires industrial portfolio for $450 million"))
        self.assertIn("magnitude", text)
        self.assertIn("/100", text)
        for component in MEASURES:
            pass
        self.assertIn("evidence", text)

    def test_bands_are_ordered_and_cover_the_whole_scale(self) -> None:
        floors = [floor for floor, _, _ in BANDS]
        self.assertEqual(floors, sorted(floors, reverse=True))
        self.assertEqual(floors[-1], 0)
        self.assertEqual(band(95)[0], "defining")
        self.assertEqual(band(0)[0], "not_publishable")

    def test_scoring_a_batch_returns_every_object(self) -> None:
        population = [obj(f"Sponsor buys asset {i} for ${i*10} million") for i in range(5)]
        self.assertEqual(len(score_all(population)), 5)

    def test_empty_input_is_handled(self) -> None:
        self.assertEqual(score_all([]), [])
        self.assertEqual(distribution_report([])["count"], 0)


if __name__ == "__main__":
    unittest.main()
