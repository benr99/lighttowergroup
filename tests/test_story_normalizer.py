from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from story_normalizer import (  # noqa: E402
    enrich_normalized_story,
    has_cre_editorial_anchor,
    normalize_story,
)


def normalize(title: str, summary: str, source: str = "NY Post Real Estate") -> dict:
    return normalize_story({
        "title": title,
        "summary": summary,
        "source": source,
        "url": "https://example.com/story",
        "published": "2026-07-26T12:00:00+00:00",
    })


class StoryNormalizerTests(unittest.TestCase):
    def test_midcentury_does_not_create_a_false_dc_market(self) -> None:
        item = normalize(
            "460 Park Ave. getting $200 million upgrade",
            "The owner will modernize the entire 22-story Midcentury property.",
        )
        self.assertNotIn("dc", item["entities"]["markets"])

    def test_full_text_recovers_the_460_park_redevelopment_signal(self) -> None:
        item = normalize(
            "460 Park Ave. getting $200 million upgrade",
            "The owner will modernize the entire 22-story Midcentury property.",
        )
        enriched = enrich_normalized_story(
            item,
            (
                "The vacant Midtown Manhattan office building will undergo a "
                "$200 million redevelopment and capital improvement program."
            ),
        )
        self.assertIn("development_finance", enriched["topics"])
        self.assertIn("capital_expenditure", enriched["topics"])
        self.assertIn("office", enriched["entities"]["asset_classes"])
        self.assertIn("manhattan", enriched["entities"]["markets"])
        self.assertTrue(enriched["attention_features"]["has_material_transaction"])
        self.assertTrue(has_cre_editorial_anchor(enriched))

    def test_large_leasing_and_occupancy_are_material_operating_signals(self) -> None:
        item = normalize(
            "SL Green signs two leases and reaches 92% occupancy",
            (
                "A 29,166 square-foot renewal and a 27,508 square-foot new lease "
                "bring the Manhattan office tower to 92% occupied."
            ),
        )
        self.assertIn("leasing", item["topics"])
        self.assertIn("market_fundamentals", item["topics"])
        self.assertTrue(item["attention_features"]["has_material_operating_signal"])

    def test_abbreviated_area_units_count_as_material_leasing(self) -> None:
        item = normalize(
            "Institutional landlord signs major logistics tenant",
            "The tenant leased 57K SF in a newly completed industrial building.",
        )
        self.assertTrue(item["attention_features"]["has_material_operating_signal"])

    def test_industrial_rent_bifurcation_is_a_cre_operating_signal(self) -> None:
        item = normalize(
            "In Industrial Real Estate, Size Is Everything Right Now",
            (
                "Industrial rent growth has plateaued, but the largest warehouses "
                "are seeing lease escalations double the pace of smaller spaces."
            ),
            source="Propmodo",
        )
        self.assertIn("industrial", item["entities"]["asset_classes"])
        self.assertIn("market_fundamentals", item["topics"])
        self.assertTrue(item["attention_features"]["has_material_operating_signal"])
        self.assertTrue(has_cre_editorial_anchor(item))

    def test_full_text_recovers_newark_project_costs(self) -> None:
        item = normalize(
            "Six New Projects to Deliver Nearly 1,200 Residential Units to Newark, New Jersey",
            "Six approved and under-construction projects will deliver nearly 1,200 apartments.",
            source="New York YIMBY",
        )
        enriched = enrich_normalized_story(
            item,
            (
                "The $100 million dormitory is under construction. A $150 million "
                "residential development and a $175 million mixed-use development "
                "are also moving forward in Newark."
            ),
        )
        self.assertIn("newark", enriched["entities"]["markets"])
        self.assertIn("multifamily", enriched["entities"]["asset_classes"])
        self.assertTrue(enriched["attention_features"]["has_material_transaction"])
        self.assertGreaterEqual(len(enriched["entities"]["amounts"]), 3)

    def test_large_non_real_estate_ipo_is_not_a_cre_anchor(self) -> None:
        item = normalize(
            "Innolight set to price Hong Kong listing below maximum",
            (
                "The optical-module maker plans a $6.8 billion capital raise "
                "as investors assess demand for the technology IPO."
            ),
            source="Bloomberg Real Estate",
        )
        self.assertTrue(item["attention_features"]["has_big_number"])
        self.assertFalse(has_cre_editorial_anchor(item))


if __name__ == "__main__":
    unittest.main()
