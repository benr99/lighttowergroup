"""Schema, validation, serialization and evidence-discipline tests.

The invariants here encode the two failures that produced zero-article
editions: depth was requested beyond what the evidence supported, and
corroborating coverage of one event was never merged so every story reported a
single source.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intelligence_object import (  # noqa: E402
    SCHEMA_VERSION,
    ContentType,
    EvidenceLevel,
    Fact,
    IntelligenceObject,
    NoveltyState,
    ObjectClass,
    RetrievalStatus,
    ScoreComponent,
    SourceRef,
    merge_sources,
    source_ref_from_item,
)


def _object(**overrides) -> IntelligenceObject:
    obj = IntelligenceObject(
        object_id="obj-1",
        cluster_id="cl-1",
        primary_sector="commercial_real_estate",
        title="Savills completes $1.1B acquisition of Eastdil Secured",
        object_class=ObjectClass.DISCRETE_EVENT,
        content_type=ContentType.NEWS_REPORT,
    )
    for key, value in overrides.items():
        setattr(obj, key, value)
    return obj


class SchemaBasics(unittest.TestCase):
    def test_valid_object_reports_no_errors(self) -> None:
        obj = _object(sources=[SourceRef(item_id="a", source_name="RE Business")])
        obj.assess_evidence()
        self.assertEqual(obj.validate(), [])
        self.assertTrue(obj.is_valid())

    def test_unknown_vocabulary_is_rejected(self) -> None:
        for field_name, bad in (
            ("object_class", "gossip"),
            ("content_type", "tweet"),
            ("evidence_level", "vibes"),
            ("novelty_state", "fresh"),
            ("recommended_depth", "tier_z"),
        ):
            with self.subTest(field=field_name):
                obj = _object(**{field_name: bad})
                self.assertTrue(
                    any(field_name in err for err in obj.validate()),
                    f"{field_name}={bad!r} should fail validation",
                )

    def test_schema_version_mismatch_is_flagged_for_migration(self) -> None:
        obj = _object(schema_version=SCHEMA_VERSION + 1)
        self.assertTrue(any("migrate" in e for e in obj.validate()))

    def test_round_trip_preserves_the_object(self) -> None:
        obj = _object(
            sources=[SourceRef(item_id="a", source_name="Wire", source_tier=1)],
            facts=[Fact(name="price", value=1_100_000_000, unit="USD", evidence_span="$1.1 billion", source_item_id="a")],
            importance_components=[ScoreComponent(name="magnitude", score=8, weight=1.5, rationale="$1.1B")],
        )
        obj.assess_evidence()
        restored = IntelligenceObject.from_dict(json.loads(obj.to_json()))
        self.assertEqual(restored.object_id, obj.object_id)
        self.assertEqual(restored.facts[0].value, 1_100_000_000)
        self.assertEqual(restored.importance_components[0].name, "magnitude")
        self.assertEqual(restored.validate(), [])


class EvidenceDiscipline(unittest.TestCase):
    """Depth must never exceed what the sources can support."""

    def test_single_summary_source_caps_depth_at_a_brief(self) -> None:
        obj = _object(sources=[SourceRef(item_id="a", source_name="Trade Wire",
                                         retrieval_status=RetrievalStatus.SUMMARY_ONLY)])
        obj.assess_evidence()
        self.assertEqual(obj.evidence_level, EvidenceLevel.SINGLE_SUMMARY)
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_c")

    def test_corroborated_primary_sources_unlock_a_feature(self) -> None:
        obj = _object(sources=[
            SourceRef(item_id="a", source_name="SEC", is_primary_authority=True,
                      retrieval_status=RetrievalStatus.FULL_TEXT),
            SourceRef(item_id="b", source_name="Reuters",
                      retrieval_status=RetrievalStatus.FULL_TEXT),
        ])
        obj.assess_evidence()
        self.assertEqual(obj.evidence_level, EvidenceLevel.PRIMARY_CORROBORATED)
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_a")

    def test_overreaching_depth_fails_validation(self) -> None:
        obj = _object(sources=[SourceRef(item_id="a", source_name="Trade Wire")])
        obj.assess_evidence()
        obj.recommended_depth = "tier_a"  # bypass the cap deliberately
        self.assertTrue(any("exceeds what" in e for e in obj.validate()))

    def test_no_sources_means_insufficient_and_no_coverage(self) -> None:
        obj = _object()
        obj.assess_evidence()
        self.assertEqual(obj.evidence_level, EvidenceLevel.INSUFFICIENT)
        self.assertEqual(obj.cap_depth_to_evidence("tier_c"), "none")

    def test_syndicated_copies_do_not_count_as_independent(self) -> None:
        """IREI and Institutional Real Estate carried identical stories."""
        obj = _object(sources=[
            SourceRef(item_id="a", source_name="IREI News", source_url="https://irei.com/x"),
            SourceRef(item_id="b", source_name="IREI News", source_url="https://irei.com/y"),
        ])
        self.assertEqual(obj.independent_source_count, 1)

    def test_observed_facts_must_cite_evidence(self) -> None:
        obj = _object(
            sources=[SourceRef(item_id="a", source_name="Wire")],
            facts=[Fact(name="cap_rate", value=5.5, source_item_id="a")],
        )
        obj.assess_evidence()
        self.assertTrue(any("evidence span" in e for e in obj.validate()))

    def test_inferences_are_allowed_without_a_span_but_marked(self) -> None:
        obj = _object(
            sources=[SourceRef(item_id="a", source_name="Wire")],
            facts=[Fact(name="implied_thesis", value="extended hold", is_inference=True)],
        )
        obj.assess_evidence()
        self.assertEqual(obj.validate(), [])
        self.assertTrue(obj.facts[0].is_inference)


class SelectionInvariants(unittest.TestCase):
    def test_ineligible_object_can_never_be_selected(self) -> None:
        obj = _object(eligible=False, selected=True, selection_rationale="diversity slot")
        self.assertTrue(any("never be selected" in e for e in obj.validate()))

    def test_selection_requires_a_recorded_rationale(self) -> None:
        obj = _object(eligible=True, selected=True,
                      sources=[SourceRef(item_id="a", source_name="Wire")])
        obj.assess_evidence()
        self.assertTrue(any("why it was selected" in e for e in obj.validate()))

    def test_eligible_object_must_cite_a_source(self) -> None:
        obj = _object(eligible=True)
        self.assertTrue(any("at least one source" in e for e in obj.validate()))


class ContentTypeVocabulary(unittest.TestCase):
    def test_promotional_formats_are_never_eligible(self) -> None:
        for content_type in (ContentType.MARKETING, ContentType.EXPLAINER,
                             ContentType.LISTICLE, ContentType.PERSONNEL_NOTICE):
            self.assertIn(content_type, ContentType.NEVER_ELIGIBLE)

    def test_interviews_and_opinion_are_not_blanket_excluded(self) -> None:
        """Eligible on material disclosure, per the editorial mandate."""
        self.assertNotIn(ContentType.INTERVIEW, ContentType.NEVER_ELIGIBLE)
        self.assertNotIn(ContentType.OPINION, ContentType.NEVER_ELIGIBLE)

    def test_primary_authority_set_is_coherent(self) -> None:
        self.assertTrue(ContentType.PRIMARY_AUTHORITY.issubset(ContentType.ALL))
        self.assertFalse(ContentType.PRIMARY_AUTHORITY & ContentType.NEVER_ELIGIBLE)


class SourceRefHelpers(unittest.TestCase):
    class _Item:
        item_id = "i1"
        source_name = "Wire"
        source_url = "https://example.com/a"
        canonical_url = "https://example.com/a"
        source_tier = 2
        source_authority = "secondary"
        publication_date = "2026-08-03T00:00:00+00:00"
        raw_summary = "short summary"
        raw_text = ""

    def test_retrieval_status_reflects_what_was_actually_retrieved(self) -> None:
        item = self._Item()
        self.assertEqual(source_ref_from_item(item).retrieval_status, RetrievalStatus.SUMMARY_ONLY)
        item.raw_text = "x" * 2000
        self.assertEqual(source_ref_from_item(item).retrieval_status, RetrievalStatus.FULL_TEXT)

    def test_source_authority_is_not_inferred_from_tier(self) -> None:
        item = self._Item()
        item.source_tier = 1
        item.source_authority = "secondary"
        self.assertFalse(source_ref_from_item(item).is_primary_authority)
        item.source_authority = "primary"
        self.assertTrue(source_ref_from_item(item).is_primary_authority)

    def test_merge_keeps_the_richest_retrieval_per_url(self) -> None:
        merged = merge_sources([
            SourceRef(item_id="a", canonical_url="https://x.com/1",
                      retrieval_status=RetrievalStatus.SUMMARY_ONLY),
            SourceRef(item_id="b", canonical_url="https://x.com/1",
                      retrieval_status=RetrievalStatus.FULL_TEXT),
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].retrieval_status, RetrievalStatus.FULL_TEXT)


if __name__ == "__main__":
    unittest.main()
