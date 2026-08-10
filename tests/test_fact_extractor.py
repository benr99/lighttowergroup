"""Deterministic fact extraction must respect entity boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fact_extractor import audit_article_facts, extract_companies, extract_facts  # noqa: E402


class InstitutionBoundaries(unittest.TestCase):
    def test_occ_is_not_extracted_from_occupancy_or_occupied(self) -> None:
        names = {
            item["name"] for item in extract_companies(
                "The property reached 92% occupancy and is now fully occupied."
            )
        }
        self.assertNotIn("occ", names)

    def test_occ_is_extracted_as_a_standalone_regulator(self) -> None:
        names = {
            item["name"] for item in extract_companies(
                "The OCC issued new commercial real estate lending guidance."
            )
        }
        self.assertIn("occ", names)


class EquivalentAmountRepresentations(unittest.TestCase):
    def test_thousands_and_millions_match_compacted_article_values(self) -> None:
        source = extract_facts(
            "Coupon STRIPS averaged $850 thousand and $1,567 million was reconstituted."
        )
        audit = audit_article_facts(
            "Coupon STRIPS averaged $850,000 and reconstitution totaled $1.567 billion.",
            source,
            source_tier=1,
        )
        self.assertEqual(audit["unmatched_amounts"], [])
        self.assertFalse(audit["hold_for_review"])

    def test_different_magnitudes_do_not_match(self) -> None:
        source = extract_facts("The disclosed amount was $850 thousand.")
        audit = audit_article_facts("The disclosed amount was $850 million.", source, source_tier=1)
        self.assertEqual(len(audit["unmatched_amounts"]), 1)
        self.assertTrue(audit["hold_for_review"])


if __name__ == "__main__":
    unittest.main()
