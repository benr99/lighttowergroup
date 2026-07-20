from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bucketed_editorial import bucketed_volume_selection, route_story
from story_normalizer import normalize_story


def story(title: str, summary: str = "", source: str = "The Real Deal") -> dict:
    return normalize_story({
        "title": title,
        "summary": summary,
        "source": source,
        "url": "https://example.org/story",
        "published": "2026-07-20T12:00:00+00:00",
    })


class BucketedEditorialTests(unittest.TestCase):
    def test_cre_refinance_routes_and_publishes(self) -> None:
        item = story("JPMorgan provides $80M refinance for Manhattan multifamily building")
        self.assertEqual(route_story(item)["primary_bucket"], "cre_capital_markets")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["selected_stories"][0]["decision"], "publish")

    def test_development_approval_routes_and_publishes(self) -> None:
        item = story("Related wins approval for 1,324-unit Brooklyn housing development")
        self.assertEqual(route_story(item)["primary_bucket"], "cre_transactions_development")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["selected_stories"][0]["decision"], "publish")

    def test_bank_cre_reserves_route_and_publish(self) -> None:
        item = story("JPMorgan raises commercial real estate loan-loss reserves as lending standards tighten")
        self.assertEqual(route_story(item)["primary_bucket"], "banking_credit")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["selected_stories"][0]["decision"], "publish")

    def test_private_credit_fund_routes_and_publishes(self) -> None:
        item = story("Blackstone closes $1B private credit fund for commercial real estate debt")
        self.assertEqual(route_story(item)["primary_bucket"], "private_equity_private_capital")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["selected_stories"][0]["decision"], "publish")

    def test_fed_rate_story_routes_and_publishes(self) -> None:
        item = story("Federal Reserve cuts interest rates, changing commercial real estate financing conditions",
                     source="Federal Reserve Monetary Policy")
        self.assertEqual(route_story(item)["primary_bucket"], "policy_rates_public_markets")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["selected_stories"][0]["decision"], "publish")

    def test_consumer_mortgage_noise_is_rejected(self) -> None:
        item = story("The zero-down mortgage for single-family home buyers")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["decision_counts"].get("reject"), 1)
        self.assertEqual(selection["selected_stories"], [])

    def test_non_us_story_without_us_transmission_is_rejected(self) -> None:
        item = story("Lendlease establishes Japan modernization partnership with PGGM")
        selection = bucketed_volume_selection([item], api_key="")
        self.assertEqual(selection["decision_counts"].get("reject"), 1)
        self.assertEqual(selection["selected_stories"], [])

    def test_no_limit_keeps_all_qualified_bucket_stories(self) -> None:
        items = [
            story("JPMorgan provides $80M refinance for Manhattan multifamily building"),
            story("Wells Fargo provides $60M refinance for Brooklyn apartment building"),
        ]
        unlimited = bucketed_volume_selection(items, api_key="", article_limit=None)
        capped = bucketed_volume_selection(items, api_key="", article_limit=1)
        self.assertEqual(len(unlimited["selected_stories"]), 2)
        self.assertEqual(len(capped["selected_stories"]), 1)
        self.assertEqual(unlimited["published_by_bucket"]["cre_capital_markets"], 2)


if __name__ == "__main__":
    unittest.main()
