"""Content typing: what a document *is*, before how important it is.

These tests encode the editorial mandate's eligibility rules. The two named
false positives come from live run 30817430024.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_typing import (  # noqa: E402
    classify_content_type,
    classify_event_type,
    classify_subsector,
    describe,
    has_material_disclosure,
)
from intelligence_object import ContentType  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "ranker_corpus_2026-08-03.json"


def _fixture(label: str) -> list[dict]:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [r for r in records if r["_label"] == label]


class BlocksPromotionalAndEvergreen(unittest.TestCase):
    def test_the_edge_computing_explainer_is_typed_as_an_explainer(self) -> None:
        record = next(r for r in _fixture("false_positive") if "Edge Computing" in r["headline"])
        content_type, _, evidence = classify_content_type(record["headline"], record["summary"])
        self.assertEqual(content_type, ContentType.EXPLAINER)
        self.assertIn(content_type, ContentType.NEVER_ELIGIBLE)
        self.assertTrue(evidence)

    def test_explainer_shapes_are_recognised(self) -> None:
        for headline in (
            "What Is a Cap Rate? A Guide for New Investors",
            "How to Underwrite a Multifamily Deal",
            "Edge vs. Cloud: Choosing the Right Architecture",
            "CMBS Explained: A Primer",
        ):
            with self.subTest(headline=headline):
                self.assertEqual(classify_content_type(headline)[0], ContentType.EXPLAINER)

    def test_marketing_and_events_are_recognised(self) -> None:
        self.assertEqual(
            classify_content_type("Sponsored: Our Platform Streamlines Loan Origination")[0],
            ContentType.MARKETING,
        )
        self.assertEqual(
            classify_content_type("Join Us for the 2026 CRE Finance Summit — Register Now")[0],
            ContentType.EVENT_PROMOTION,
        )

    def test_personnel_notices_are_recognised(self) -> None:
        self.assertEqual(
            classify_content_type("Bluerock Expands Wealth Distribution Team With Three Hires")[0],
            ContentType.PERSONNEL_NOTICE,
        )


class InterviewsRequireMaterialDisclosure(unittest.TestCase):
    def test_the_invesco_interview_has_no_material_disclosure(self) -> None:
        record = next(r for r in _fixture("false_positive") if "Bolding" in r["headline"])
        content_type, _, _ = classify_content_type(record["headline"], record["summary"])
        self.assertEqual(content_type, ContentType.INTERVIEW)
        disclosed, _ = has_material_disclosure(f"{record['headline']} {record['summary']}")
        self.assertFalse(
            disclosed,
            "a prominent subject and a capital-markets biography are not disclosure",
        )

    def test_an_interview_with_a_real_disclosure_qualifies(self) -> None:
        text = (
            "Invesco's Chase Bolding Talks Market Opportunity. "
            "We are exiting suburban office entirely and plan to deploy $2 billion "
            "into industrial over the next 18 months."
        )
        self.assertEqual(classify_content_type(text)[0], ContentType.INTERVIEW)
        disclosed, evidence = has_material_disclosure(text)
        self.assertTrue(disclosed)
        self.assertTrue(any("strategy_change" in e or "stated_allocation" in e for e in evidence))

    def test_interviews_are_not_blanket_excluded(self) -> None:
        self.assertNotIn(ContentType.INTERVIEW, ContentType.NEVER_ELIGIBLE)


class KeepsGenuineIntelligence(unittest.TestCase):
    def test_real_transactions_are_news_reports(self) -> None:
        for record in _fixture("true_positive"):
            with self.subTest(headline=record["headline"][:50]):
                content_type, _, _ = classify_content_type(record["headline"], record["summary"])
                self.assertNotIn(content_type, ContentType.NEVER_ELIGIBLE)
                self.assertEqual(content_type, ContentType.NEWS_REPORT)

    def test_data_releases_without_dollar_amounts_are_retained(self) -> None:
        """Important macro stories need no transaction value."""
        record = _fixture("non_transaction_macro")[0]
        content_type, _, _ = classify_content_type(record["headline"], record["summary"])
        self.assertEqual(content_type, ContentType.DATA_PUBLICATION)
        self.assertNotIn(content_type, ContentType.NEVER_ELIGIBLE)

    def test_a_quoted_executive_does_not_turn_a_deal_into_an_interview(self) -> None:
        content_type, _, evidence = classify_content_type(
            "Blackstone Acquires Phoenix Portfolio for $450 Million",
            "A spokesman discusses the transaction rationale.",
        )
        self.assertEqual(content_type, ContentType.NEWS_REPORT, evidence)

    def test_government_sources_are_primary_documents(self) -> None:
        content_type, confidence, _ = classify_content_type(
            "FOMC statement", source_type="government"
        )
        self.assertEqual(content_type, ContentType.PRIMARY_DOCUMENT)
        self.assertGreater(confidence, 0.8)


class TaxonomyPopulation(unittest.TestCase):
    """`event_type` and `subsector` were hardcoded empty with a TODO."""

    def test_subsector_is_populated_from_config(self) -> None:
        cases = [
            ("Blackstone buys a 400-unit apartment complex", "commercial_real_estate", "multifamily"),
            ("Prologis leases a warehouse distribution center", "commercial_real_estate", "industrial_logistics"),
            ("CyrusOne announces a hyperscale campus", "data_centers", "hyperscale"),
            ("Hamilton Lane backs a continuation vehicle", "private_equity", "continuation_vehicle"),
        ]
        for text, sector, expected in cases:
            with self.subTest(text=text[:40]):
                subsector, confidence, evidence = classify_subsector(text, sector)
                self.assertEqual(subsector, expected)
                self.assertGreater(confidence, 0.5)
                self.assertTrue(evidence)

    def test_event_type_matches_the_configured_taxonomy(self) -> None:
        event_type, _, _ = classify_event_type(
            "The city council approved a rezoning decision", "local_government"
        )
        self.assertEqual(event_type, "rezoning_decision")

    def test_single_word_overlap_does_not_invent_an_event_type(self) -> None:
        """A lone shared token produced junk classifications."""
        event_type, confidence, _ = classify_event_type(
            "Edge Computing vs. Cloud Computing: Choosing the Right Architecture",
            "data_centers",
        )
        self.assertEqual(event_type, "", f"should not guess, got {event_type!r} at {confidence}")

    def test_unknown_sector_degrades_quietly(self) -> None:
        self.assertEqual(classify_event_type("anything", "no_such_sector"), ("", 0.0, []))
        self.assertEqual(classify_subsector("anything", "no_such_sector"), ("", 0.0, []))


class DescribeContract(unittest.TestCase):
    def test_describe_returns_every_field_with_evidence(self) -> None:
        result = describe(
            "Savills Completes $1.1B Acquisition of Eastdil Secured",
            "Savills agreed to acquire Eastdil Secured.",
            sector="commercial_real_estate",
        )
        for key in (
            "content_type", "content_type_confidence", "content_type_evidence",
            "event_type", "subsector", "has_material_disclosure",
            "has_transaction_verb", "has_monetary_amount",
        ):
            self.assertIn(key, result)
        self.assertTrue(result["has_transaction_verb"])
        self.assertTrue(result["has_monetary_amount"])

    def test_empty_input_does_not_raise(self) -> None:
        result = describe("", "", sector="commercial_real_estate")
        self.assertEqual(result["content_type"], ContentType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
