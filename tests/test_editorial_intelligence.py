from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from editorial_intelligence import cluster_events, event_similarity, score_event, select_edition
from research_dossier import build_research_dossier
from story_normalizer import normalize_story


def story(
    title: str,
    *,
    source: str = "The Real Deal",
    url: str = "https://example.org/story",
    summary: str = "",
) -> dict:
    return normalize_story({
        "title": title,
        "summary": summary,
        "source": source,
        "url": url,
        "published": "2026-07-23T12:00:00+00:00",
    })


class EditorialIntelligenceTests(unittest.TestCase):
    def test_same_event_clusters_across_different_headlines(self) -> None:
        left = story(
            "JPMorgan provides $80M refinance for Manhattan office tower",
            url="https://therealdeal.com/a",
        )
        right = story(
            "Manhattan office tower lands $80M loan from JPMorgan",
            source="Commercial Observer",
            url="https://commercialobserver.com/b",
        )
        self.assertGreaterEqual(event_similarity(left, right), 0.61)
        clusters = cluster_events([left, right])
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["source_count"], 2)

    def test_routine_single_source_refinance_is_not_a_flagship(self) -> None:
        item = story("JPMorgan provides $80M refinance for Manhattan office tower")
        scored = score_event(cluster_events([item])[0])
        self.assertLess(scored["must_read_score"], 56)
        self.assertLess(scored["must_read_breakdown"]["routine_event_penalty"], 0)

    def test_distress_culture_and_human_stakes_raise_editorial_value(self) -> None:
        items = [
            story(
                "Stadium district loan enters special servicing after team owner misses payment",
                source="The Real Deal",
                url="https://therealdeal.com/stadium",
                summary="The $1.2 billion mixed-use stadium district employs 4,000 workers and faces foreclosure.",
            ),
            story(
                "Team owner's $1.2B stadium district debt faces foreclosure",
                source="Commercial Observer",
                url="https://commercialobserver.com/stadium",
                summary="The missed payment threatens tenants, jobs and a taxpayer-backed subsidy.",
            ),
        ]
        scored = score_event(cluster_events(items)[0])
        self.assertGreaterEqual(scored["must_read_breakdown"]["cultural_relevance"], 6)
        self.assertGreater(scored["must_read_breakdown"]["conflict_and_power"], 0)
        self.assertGreater(scored["must_read_breakdown"]["human_stakes"], 0)

    def test_edition_is_scarce_and_preserves_deal_tape(self) -> None:
        candidates = [
            story(
                "Stadium district loan enters special servicing after team owner misses payment",
                source="The Real Deal",
                url="https://therealdeal.com/stadium",
                summary="The $1.2 billion project employs 4,000 workers and faces foreclosure.",
            ),
            story(
                "Team owner's $1.2B stadium district debt faces foreclosure",
                source="Commercial Observer",
                url="https://commercialobserver.com/stadium",
                summary="The missed payment threatens tenants and a taxpayer-backed subsidy.",
            ),
        ]
        candidates.extend(
            story(
                f"Lender {index} provides ${50 + index}M refinance for Manhattan office building",
                source=f"Source {index}",
                url=f"https://source{index}.example/refi",
            )
            for index in range(8)
        )
        edition = select_edition(candidates, max_briefs=3, max_deal_tape=4)
        self.assertLessEqual(len(edition["selected_stories"]), 5)
        self.assertLessEqual(len(edition["deal_tape"]), 4)
        self.assertEqual(len(edition["duplicate_groups"]), 1)

    def test_archive_match_penalizes_repackaged_coverage(self) -> None:
        item = story("Blackstone $500M office fund enters special servicing")
        event = cluster_events([item])[0]
        scored = score_event(event, [{
            "slug": "blackstone-office-fund",
            "title": "Blackstone's $500M Office Fund Enters Special Servicing",
            "date": "2026-07-22",
            "url": "/insights/blackstone-office-fund.html",
        }])
        self.assertTrue(scored["archive_matches"])
        self.assertLess(scored["must_read_breakdown"]["archive_repetition_penalty"], 0)

    def test_audience_learning_is_bounded_and_cannot_override_editorial_controls(self) -> None:
        item = story("JPMorgan provides $80M refinance for Manhattan office tower")
        event = cluster_events([item])[0]
        scored = score_event(event, audience_signals={
            "weights": {"topic:capital_placement": 100, "source:example.org": 100}
        })
        self.assertEqual(scored["must_read_breakdown"]["audience_learning_adjustment"], 5)
        self.assertLess(scored["must_read_breakdown"]["routine_event_penalty"], 0)

    def test_dossier_forbids_longform_without_three_sources(self) -> None:
        sources = [
            story(
                "Bank's $600M housing loan faces default",
                source="The Real Deal",
                url="https://therealdeal.com/housing",
                summary="The $600 million loan matures in 2026.",
            ),
            story(
                "$600M housing debt nears maturity",
                source="Commercial Observer",
                url="https://commercialobserver.com/housing",
                summary="The loan covers 2,000 apartments.",
            ),
        ]
        event = cluster_events(sources)[0]
        event["provisional_format"] = "flagship"
        dossier = build_research_dossier(event, fetched_text_by_url={
            sources[0]["url"]: "The lender said the $600 million loan matures in 2026.",
            sources[1]["url"]: "The financing covers 2,000 apartments, according to records.",
        })
        self.assertEqual(dossier["independent_source_count"], 2)
        self.assertFalse(dossier["longform_allowed"])
        self.assertTrue(dossier["format_downgraded"])


if __name__ == "__main__":
    unittest.main()
