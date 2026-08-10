"""Event clustering: consolidate reporting, without over-merging.

Fixtures are drawn from the real 2026-08-03 corpus. The positive cases are
duplicate pairs measured in Phase 1; the negative cases guard the failure that
actually matters -- collapsing two genuinely different deals into one object,
which would silently drop a story from the slate.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from event_clustering import (  # noqa: E402
    MERGE_THRESHOLD,
    _Signature,
    build_intelligence_object,
    cluster_items,
    cluster_to_objects,
    similarity,
)
from intelligence_object import RetrievalStatus  # noqa: E402


def item(headline: str, *, summary: str = "", source: str = "Wire", url: str = "",
         tier: int = 3, sector: str = "commercial_real_estate",
         authority: str = "secondary", text: str = "") -> types.SimpleNamespace:
    node = types.SimpleNamespace()
    node.item_id = url or headline[:24]
    node.headline = headline
    node.raw_summary = summary
    node.raw_text = text
    node.source_name = source
    node.source_url = url or f"https://example.com/{abs(hash(headline)) % 10**8}"
    node.canonical_url = node.source_url
    node.source_tier = tier
    node.source_authority = authority
    node.primary_sector = sector
    node.secondary_sectors = []
    node.subsector = ""
    node.event_type = ""
    node.publication_date = ""
    return node


class MergesRealDuplicates(unittest.TestCase):
    def test_same_deal_reported_by_two_outlets_merges(self) -> None:
        pair = [
            item("Marcus & Millichap Brokers $13 Million Sale of Retail Center in Hacienda Heights",
                 source="Shopping Center Business", url="https://scb.com/a"),
            item("Marcus & Millichap Brokers $13M Sale of Retail Center in Hacienda Heights",
                 source="RE Business Online", url="https://rebusiness.com/b"),
        ]
        clusters, audit = cluster_items(pair)
        self.assertEqual(len(clusters), 1, "one deal must produce one cluster")
        self.assertTrue(any("shared amount" in r for r in audit[0]["reasons"]))

    def test_syndicated_copies_merge(self) -> None:
        pair = [
            item("Slate Property Group closes $1b separately managed account focused on logistics",
                 source="Institutional Real Estate", url="https://irei.com/news/slate"),
            item("Slate Property Group closes $1b separately managed account focused on logistics",
                 source="IREI News", url="https://irei.com/news/slate"),
        ]
        clusters, _ = cluster_items(pair)
        self.assertEqual(len(clusters), 1)

    def test_identical_headline_without_amounts_still_merges(self) -> None:
        pair = [
            item("Henderson Park, Lowe acquire shopping center in San Diego", source="A", url="https://a.com/1"),
            item("Henderson Park, Lowe acquire shopping center in San Diego", source="B", url="https://b.com/1"),
        ]
        self.assertEqual(len(cluster_items(pair)[0]), 1)


class DoesNotOverMerge(unittest.TestCase):
    """Over-merging silently deletes a story. These must stay separate."""

    def test_different_amounts_same_parties_stay_separate(self) -> None:
        pair = [
            item("Blackstone acquires Phoenix industrial portfolio for $450 million"),
            item("Blackstone acquires Phoenix industrial portfolio for $1.2 billion"),
        ]
        score, reasons = similarity(_Signature.build(pair[0]), _Signature.build(pair[1]))
        self.assertLess(score, MERGE_THRESHOLD, f"scored {score:.2f}: {reasons}")
        self.assertEqual(len(cluster_items(pair)[0]), 2)

    def test_different_deals_by_the_same_sponsor_stay_separate(self) -> None:
        pair = [
            item("KKR closes $8.5B North America buyout fund", sector="private_equity"),
            item("KKR acquires Dallas logistics park from Prologis", sector="private_equity"),
        ]
        self.assertEqual(len(cluster_items(pair)[0]), 2)

    def test_unrelated_stories_stay_separate(self) -> None:
        docs = [
            item("Fed holds rates steady at September meeting", sector="fed_macro"),
            item("CyrusOne breaks ground on Texas data center campus", sector="data_centers"),
            item("Welltower sells medical office portfolio", sector="commercial_real_estate"),
        ]
        self.assertEqual(len(cluster_items(docs)[0]), 3)

    def test_same_company_different_event_type_stays_separate(self) -> None:
        pair = [
            item("Hamilton Lane backs $270m single-asset continuation vehicle"),
            item("Hamilton Lane names new head of European private credit"),
        ]
        self.assertEqual(len(cluster_items(pair)[0]), 2)


class ObjectAssembly(unittest.TestCase):
    def test_primary_authority_source_becomes_the_anchor(self) -> None:
        cluster = [
            item("Fed holds rates steady", source="Trade Blog", tier=4, sector="fed_macro"),
            item("Federal Reserve issues FOMC statement", source="Federal Reserve",
                 tier=1, authority="primary", sector="fed_macro", text="x" * 3000),
        ]
        obj = build_intelligence_object(cluster)
        self.assertEqual(obj.title, "Federal Reserve issues FOMC statement")
        self.assertEqual(obj.primary_sector, "fed_macro")
        self.assertTrue(any(source.is_primary_authority for source in obj.sources))

    def test_tier_one_publication_is_not_mislabeled_primary_authority(self) -> None:
        obj = build_intelligence_object([
            item("Reuters reports a $500 million acquisition", tier=1, authority="secondary")
        ])
        self.assertFalse(obj.sources[0].is_primary_authority)

    def test_object_records_every_supporting_source(self) -> None:
        cluster = [
            item("Savills completes $1.1B acquisition of Eastdil", source="A", url="https://a.com/1"),
            item("Savills completes $1.1B acquisition of Eastdil Secured", source="B", url="https://b.com/2"),
        ]
        obj = build_intelligence_object(cluster)
        self.assertEqual(len(obj.sources), 2)
        self.assertEqual(obj.independent_source_count, 2)
        self.assertEqual(obj.validate(), [])

    def test_full_text_upgrades_the_evidence_level(self) -> None:
        cluster = [
            item("Savills completes $1.1B acquisition", source="A", url="https://a.com/1", text="x" * 4000),
            item("Savills completes $1.1B acquisition of Eastdil", source="B", url="https://b.com/2", text="y" * 4000),
        ]
        obj = build_intelligence_object(cluster)
        self.assertEqual(obj.sources[0].retrieval_status, RetrievalStatus.FULL_TEXT)
        self.assertEqual(obj.evidence_level, "corroborated")
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_a")

    def test_generated_ids_are_stable_and_unique(self) -> None:
        objs, _ = cluster_to_objects([
            item("Deal A closes for $10 million"),
            item("Deal B closes for $90 million"),
        ])
        ids = [o.object_id for o in objs]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(ids))


class AuditTrail(unittest.TestCase):
    def test_report_explains_what_was_consolidated(self) -> None:
        docs = [
            item("Slate closes $1b account", source="A", url="https://a.com/1"),
            item("Slate closes $1b account", source="B", url="https://b.com/2"),
            item("Unrelated office tower trades in Denver"),
        ]
        objects, report = cluster_to_objects(docs)
        self.assertEqual(report["documents_in"], 3)
        self.assertEqual(report["objects_out"], 2)
        self.assertEqual(report["clusters_merged"], 1)
        self.assertEqual(report["documents_consolidated"], 1)
        self.assertTrue(report["merges"][0]["reasons"])

    def test_empty_input_is_handled(self) -> None:
        objects, report = cluster_to_objects([])
        self.assertEqual(objects, [])
        self.assertEqual(report["objects_out"], 0)


if __name__ == "__main__":
    unittest.main()
