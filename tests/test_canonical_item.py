"""Canonical ingestion normalization and source-provenance regression tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canonical_item import CanonicalItem, normalize_headline, repair_mojibake  # noqa: E402


class HeadlineNormalization(unittest.TestCase):
    def test_entities_tags_and_broken_prefixes_are_removed(self) -> None:
        self.assertEqual(
            normalize_headline("'\"> <b>Tesla&#39;s</b> New Data Center &amp; Grid Deal"),
            "Tesla's New Data Center & Grid Deal",
        )

    def test_rss_ingestion_uses_normalized_title(self) -> None:
        item = CanonicalItem.from_rss_entry(
            {"title": "&quot;Apollo&#39;s $2B Fund&quot;", "link": "https://example.com/a"},
            {"name": "Example", "source_type": "rss", "tier": 1},
        )
        self.assertEqual(item.headline, "Apollo's $2B Fund")

    def test_double_encoded_feed_punctuation_is_repaired(self) -> None:
        broken = "TreasuryÃ¢â‚¬â„¢s policy Ã¢â‚¬â€ explained"
        self.assertEqual(repair_mojibake(broken), "Treasury’s policy — explained")


class SourceAuthority(unittest.TestCase):
    def test_primary_authority_is_inferred_from_source_kind_not_tier(self) -> None:
        government = CanonicalItem.from_rss_entry(
            {"title": "FOMC statement", "link": "https://federalreserve.gov/a"},
            {"name": "Federal Reserve", "source_type": "government", "tier": 1},
        )
        wire = CanonicalItem.from_rss_entry(
            {"title": "Market report", "link": "https://example.com/a"},
            {"name": "Wire", "source_type": "rss", "tier": 1},
        )
        self.assertEqual(government.source_authority, "primary")
        self.assertEqual(wire.source_authority, "secondary")

    def test_explicit_authority_override_is_respected(self) -> None:
        item = CanonicalItem.from_rss_entry(
            {"title": "Release", "link": "https://issuer.com/a"},
            {
                "name": "Issuer IR",
                "source_type": "rss",
                "source_authority": "primary",
                "tier": 2,
            },
        )
        self.assertEqual(item.source_authority, "primary")


if __name__ == "__main__":
    unittest.main()
