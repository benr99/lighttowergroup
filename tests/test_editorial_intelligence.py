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
        self.assertTrue(scored["archive_repeat"])
        self.assertLess(scored["must_read_breakdown"]["archive_repetition_penalty"], 0)

    def test_old_archive_context_penalizes_but_does_not_suppress_a_new_update(self) -> None:
        item = story("Blackstone $500M office fund enters special servicing")
        scored = score_event(cluster_events([item])[0], [{
            "slug": "blackstone-office-fund",
            "title": "Blackstone's $500M Office Fund Faces Maturity Pressure",
            "date": "2026-06-01",
            "url": "/insights/blackstone-office-fund.html",
        }])
        self.assertTrue(scored["archive_matches"])
        self.assertFalse(scored["archive_repeat"])
        self.assertLess(scored["must_read_breakdown"]["archive_repetition_penalty"], 0)

    def test_recent_scan_memory_does_not_masquerade_as_published_coverage(self) -> None:
        item = story(
            "460 Park Ave. getting $200 million upgrade",
            source="NY Post Real Estate",
            url="https://nypost.com/460-park",
            summary=(
                "The Midtown Manhattan office building will undergo a "
                "$200 million redevelopment and capital improvement program."
            ),
        )
        edition = select_edition(
            [item],
            archive_records=[{
                "slug": "event-prior-scan",
                "title": item["title"],
                "date": "2026-07-23",
                "memory_only": True,
                "prior_decision": "reject",
            }],
            max_briefs=5,
            max_articles=5,
            daily_target=3,
        )
        scored = edition["scored_events"][0]
        self.assertTrue(scored["archive_matches"])
        self.assertTrue(scored["archive_matches"][0]["memory_only"])
        self.assertFalse(scored["archive_repeat"])
        self.assertEqual(scored["decision"], "research")
        self.assertEqual(scored["selection_tier"], "daily_depth")

    def test_archive_match_uses_facts_from_a_corroborating_source(self) -> None:
        lead = story(
            "Park Avenue office upgrade moves forward",
            url="https://example.org/park-upgrade",
            summary="The landlord has started a major Midtown modernization.",
        )
        corroborating = story(
            "460 Park Avenue begins $200M redevelopment",
            source="Commercial Observer",
            url="https://commercialobserver.com/460-park",
            summary="The owner started a $200 million office redevelopment at 460 Park Avenue.",
        )
        event = cluster_events([lead])[0]
        event["sources"].append(corroborating)
        scored = score_event(event, [{
            "slug": "460-park-redevelopment",
            "title": "The $200M Repositioning at 460 Park Avenue",
            "date": "2026-07-22",
            "excerpt": "A $200 million modernization of the Midtown office building.",
        }])
        self.assertTrue(scored["archive_repeat"])
        self.assertTrue(scored["archive_matches"][0]["signals"]["amount_overlap"])

    def test_cerberus_paraphrase_is_suppressed_as_a_recent_archive_repeat(self) -> None:
        item = story(
            "Distressed Multifamily Debt Finds Buyers as Banks Exit New York Portfolios",
            source="Propmodo",
            url="https://propmodo.com/cerberus-loan-book",
            summary=(
                "Cerberus buys a $1.3 billion New York multifamily loan book "
                "at 92 cents on the dollar."
            ),
        )
        edition = select_edition(
            [item],
            archive_records=[{
                "slug": "cerberus-multifamily-loan-book-basis",
                "title": (
                    "Cerberus Buys $1.3B Multifamily Loan Book: "
                    "The Basis Is the Deal, Not the Regulation"
                ),
                "date": "2026-07-23",
                "excerpt": (
                    "Cerberus buys a $1.3B rent-stabilized loan book at "
                    "92 cents on the dollar."
                ),
                "tags": ["Cerberus", "multifamily debt", "New York"],
            }],
            max_briefs=5,
            max_articles=5,
            daily_target=3,
        )
        scored = edition["scored_events"][0]
        self.assertEqual(scored["decision"], "archive_repeat")
        self.assertTrue(scored["archive_repeat"])
        self.assertEqual(edition["selected_stories"], [])
        self.assertEqual(edition["deal_tape"], [])
        self.assertEqual(len(edition["archive_repeats"]), 1)

    def test_daily_depth_queue_recovers_relevant_operating_and_capex_signals(self) -> None:
        candidates = [
            story(
                "460 Park Ave. getting $200 million upgrade",
                source="NY Post Real Estate",
                url="https://nypost.com/460-park",
                summary=(
                    "The vacant Midtown Manhattan office building will undergo "
                    "a $200 million redevelopment and capital improvement program."
                ),
            ),
            story(
                "In Industrial Real Estate, Size Is Everything Right Now",
                source="Propmodo",
                url="https://propmodo.com/industrial-size",
                summary=(
                    "Industrial rent growth has plateaued, but the largest warehouses "
                    "are seeing lease escalations double the pace of smaller spaces."
                ),
            ),
            story(
                "SL Green signs two leases and reaches 92% occupancy",
                source="NY Post Real Estate",
                url="https://nypost.com/sl-green-leases",
                summary=(
                    "A 29,166 square-foot renewal and a 27,508 square-foot new lease "
                    "bring the Manhattan office tower to 92% occupied."
                ),
            ),
            story(
                "Six projects deliver 1,200 Newark apartments",
                source="New York YIMBY",
                url="https://newyorkyimby.com/newark-projects",
                summary=(
                    "A $100 million dormitory, $150 million residential development, "
                    "and $175 million mixed-use development are moving forward in Newark."
                ),
            ),
            story(
                "What Sam Altman will tell the White House this week",
                source="Axios Cities",
                url="https://axios.com/altman",
                summary="The technology executive will preview a new model in Washington.",
            ),
        ]
        edition = select_edition(
            candidates,
            max_briefs=5,
            max_articles=5,
            daily_target=3,
        )
        selected_titles = {
            item["candidate"]["title"] for item in edition["selected_stories"]
        }
        self.assertEqual(len(selected_titles), 4)
        self.assertIn("460 Park Ave. getting $200 million upgrade", selected_titles)
        self.assertIn("In Industrial Real Estate, Size Is Everything Right Now", selected_titles)
        self.assertIn("SL Green signs two leases and reaches 92% occupancy", selected_titles)
        self.assertIn("Six projects deliver 1,200 Newark apartments", selected_titles)
        self.assertNotIn(
            "What Sam Altman will tell the White House this week",
            selected_titles,
        )
        self.assertTrue(all(
            item["selection_tier"] == "daily_depth"
            for item in edition["selected_stories"]
        ))

    def test_wider_feed_pool_can_add_an_independent_corroborating_source(self) -> None:
        primary = story(
            "JPMorgan provides $80M refinance for Manhattan office tower",
            source="The Real Deal",
            url="https://therealdeal.com/refinance",
        )
        corroborating = story(
            "Manhattan office tower lands $80M JPMorgan loan",
            source="Commercial Observer",
            url="https://commercialobserver.com/refinance",
        )
        edition = select_edition(
            [primary],
            corroboration_candidates=[corroborating],
            max_briefs=5,
            max_articles=5,
            daily_target=3,
        )
        self.assertEqual(edition["scored_events"][0]["source_count"], 2)
        self.assertEqual(len(edition["duplicate_groups"]), 1)

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
