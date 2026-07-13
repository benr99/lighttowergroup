import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from editorial_scoring import _normalize_score_row, daily_top_news_selection, is_publishable_daily_candidate
from story_normalizer import has_reported_amount_at_least_ten_million, normalize_story


class EditorialScoringTests(unittest.TestCase):
    def _candidate(self, *, strong: bool) -> dict:
        return {
            "title": "Major lender refinances $850M Manhattan office tower" if strong else "Local design trend draws attention",
            "source": "Commercial Observer" if strong else "Unknown Blog",
            "url": "https://example.org/story",
            "summary": "A named lender refinanced a major office building." if strong else "A general-interest item.",
            "source_tier": 1 if strong else 3,
            "source_domains": ["cre", "finance"] if strong else ["general"],
            "topics": ["capital_placement", "bank_credit"] if strong else ["other"],
            "entities": {"amounts": ["$850M"] if strong else [], "companies": ["wells fargo"] if strong else []},
            "attention_features": {
                "has_big_number": strong,
                "has_known_institution": strong,
                "has_transaction_language": strong,
                "has_distress_language": False,
            },
        }

    def test_strong_evidence_backed_story_can_clear_publish_floor(self):
        row = _normalize_score_row(
            {"score": 92, "capital_markets_significance": 23, "specificity": 14, "penalty": 0},
            self._candidate(strong=True),
            1,
        )
        self.assertTrue(is_publishable_daily_candidate(row))

    def test_weak_story_cannot_fill_daily_quota(self):
        weak = _normalize_score_row(
            {"score": 45, "capital_markets_significance": 8, "specificity": 4, "penalty": 20},
            self._candidate(strong=False),
            1,
        )
        selection = daily_top_news_selection([weak["candidate"]], article_count=30, api_key="", today="2026-07-12")
        self.assertFalse(is_publishable_daily_candidate(weak))
        self.assertEqual(selection["selected_stories"], [])

    def test_material_multifamily_loan_is_admitted_and_ranked_as_a_transaction(self):
        story = {
            "title": "Family office provides $42M construction loan for Miami multifamily project",
            "summary": "The financing supports a 280-unit apartment development.",
            "source": "Commercial Observer",
            "url": "https://example.org/multifamily-loan",
            "published": "2026-07-13T10:00:00Z",
        }
        candidate = normalize_story(story)
        self.assertTrue(candidate["attention_features"]["has_material_transaction"])
        row = _normalize_score_row(
            {"score": 88, "capital_markets_significance": 21, "specificity": 13, "penalty": 0},
            candidate,
            1,
        )
        self.assertTrue(is_publishable_daily_candidate(row))

    def test_material_amount_threshold_is_ten_million(self):
        self.assertTrue(has_reported_amount_at_least_ten_million("A $10M office acquisition closed."))
        self.assertTrue(has_reported_amount_at_least_ten_million("The loan totals $10,000,000."))
        self.assertTrue(has_reported_amount_at_least_ten_million("Investor committed $1.2B."))
        self.assertFalse(has_reported_amount_at_least_ten_million("A $9.9M renovation is planned."))


if __name__ == "__main__":
    unittest.main()
