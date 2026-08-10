"""Per-family eligibility rules for the new ranker.

The old gate asked one question of every candidate. These tests assert that the
families genuinely differ: a Fed decision needs no dollar amount, a property
trade needs parties and scale, an interview needs a disclosure.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import eligibility  # noqa: E402
from intelligence_object import (  # noqa: E402
    ContentType,
    IntelligenceObject,
    ObjectClass,
    RetrievalStatus,
    SourceRef,
)

FIXTURE = ROOT / "tests" / "fixtures" / "ranker_corpus_2026-08-03.json"


def obj(title: str, summary: str = "", *, sector: str = "commercial_real_estate",
        sources: int = 1, object_class: str = ObjectClass.DISCRETE_EVENT,
        tier: int = 3, full_text: bool = False,
        primary_authority: bool = False) -> IntelligenceObject:
    refs = [
        SourceRef(
            item_id=f"s{i}",
            source_name=f"Publisher {i}",
            canonical_url=f"https://p{i}.com/a",
            source_tier=tier,
            is_primary_authority=primary_authority,
            retrieval_status=RetrievalStatus.FULL_TEXT if full_text else RetrievalStatus.SUMMARY_ONLY,
        )
        for i in range(sources)
    ]
    node = IntelligenceObject(
        object_id="o1", cluster_id="c1", primary_sector=sector,
        title=title, what_happened=summary, sources=refs, object_class=object_class,
    )
    node.assess_evidence()
    return node


class TransactionFamily(unittest.TestCase):
    def test_named_party_with_amount_qualifies(self) -> None:
        decision = eligibility.assess(obj("Savills Completes $1.1B Acquisition of Eastdil Secured"))
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.family, "transaction_or_development")
        self.assertTrue(decision.evidence)

    def test_physical_scale_substitutes_for_a_dollar_amount(self) -> None:
        decision = eligibility.assess(
            obj("JLL Negotiates Sale of 767,520 SF Industrial Building in Brookshire")
        )
        self.assertTrue(decision.eligible, decision.reason)

    def test_undisclosed_amount_qualifies_when_corroborated(self) -> None:
        decision = eligibility.assess(
            obj("Henderson Park and Lowe Acquire San Diego Shopping Center", sources=2)
        )
        self.assertTrue(decision.eligible, decision.reason)
        self.assertIn("corroborated", decision.reason)

    def test_vague_capital_language_without_an_event_is_rejected(self) -> None:
        decision = eligibility.assess(
            obj("Investors weigh the outlook for property capital markets")
        )
        self.assertFalse(decision.eligible)
        self.assertTrue(decision.disqualifiers)


class PolicyAndMacroFamily(unittest.TestCase):
    """Importance without a transaction value."""

    def test_fed_decision_qualifies_without_a_dollar_amount(self) -> None:
        decision = eligibility.assess(
            obj("Fed holds rates steady at 4.25% amid mixed inflation data", sector="fed_macro")
        )
        self.assertTrue(decision.eligible, decision.reason)
        self.assertEqual(decision.family, "policy_or_macro")

    def test_data_release_qualifies(self) -> None:
        decision = eligibility.assess(
            obj("ISM: Manufacturing sector expanded in July", sector="banking_credit",
                object_class=ObjectClass.DATA_RELEASE)
        )
        self.assertTrue(decision.eligible, decision.reason)
        self.assertEqual(decision.family, "data_or_signal")

    def test_rezoning_decision_qualifies(self) -> None:
        decision = eligibility.assess(
            obj("City Council approves rezoning for 1,200 units downtown",
                sector="local_government")
        )
        self.assertTrue(decision.eligible, decision.reason)

    def test_market_movement_qualifies(self) -> None:
        decision = eligibility.assess(
            obj("Ten-year Treasury yield climbs 18 basis points on jobs data",
                sector="fed_macro", object_class=ObjectClass.MARKET_MOVEMENT)
        )
        self.assertTrue(decision.eligible, decision.reason)


class GovernmentActionInAnySector(unittest.TestCase):
    """What a story IS decides how it is judged, not which sector it sits in.

    Routing by sector alone sent regulatory stories to the transaction rules,
    which demand a transaction verb and an amount. Forty-three of sixty-eight
    data-centre stories were thrown away for "no transaction verb" while being
    among the most consequential items of the day.
    """

    CASES = (
        ("Texas Gov. Greg Abbott Halts Data Center Connections To State Grid", "data_centers"),
        ("Dozens of NJ towns are banning data centers", "data_centers"),
        ("Trump Reportedly Preparing Ban On Chinese Data Center Companies", "data_centers"),
        ("FERC approves new interconnection rules for large loads", "energy"),
        ("OCC finalises capital rules for regional banks", "banking_credit"),
    )

    def test_regulatory_action_is_judged_as_policy_whatever_the_sector(self) -> None:
        for title, sector in self.CASES:
            with self.subTest(title=title[:44]):
                decision = eligibility.assess(obj(title, sector=sector))
                self.assertEqual(decision.family, "policy_or_macro")
                self.assertTrue(decision.eligible, decision.reason)

    def test_an_abbreviated_title_still_reads_as_a_public_body(self) -> None:
        """"Gov." ends in a period, which defeats a trailing word boundary."""
        decision = eligibility.assess(
            obj("Gov. Hochul signs housing bill", sector="commercial_real_estate")
        )
        self.assertEqual(decision.family, "policy_or_macro")

    def test_a_commercial_deal_is_still_judged_as_a_transaction(self) -> None:
        decision = eligibility.assess(
            obj("Blackstone acquires Phoenix industrial portfolio for $450 million")
        )
        self.assertEqual(decision.family, "transaction_or_development")
        self.assertTrue(decision.eligible)

    def test_a_company_merely_mentioning_regulation_is_not_policy(self) -> None:
        decision = eligibility.assess(
            obj("Prologis leases 400,000 sf warehouse in Dallas")
        )
        self.assertEqual(decision.family, "transaction_or_development")


class InterviewFamily(unittest.TestCase):
    def test_promotional_interview_is_rejected(self) -> None:
        record = next(
            r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))
            if "Bolding" in r["headline"]
        )
        decision = eligibility.assess(obj(record["headline"], record["summary"]))
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.family, "interview_or_opinion")
        self.assertIn("no material disclosure", decision.disqualifiers)

    def test_interview_with_material_disclosure_qualifies(self) -> None:
        decision = eligibility.assess(obj(
            "Invesco's Chase Bolding Talks Market Opportunity",
            "We are exiting suburban office entirely and plan to deploy $2 billion into industrial.",
        ))
        self.assertTrue(decision.eligible, decision.reason)
        self.assertTrue(decision.evidence)


class HardDisqualifiers(unittest.TestCase):
    def test_explainer_is_rejected_regardless_of_vocabulary(self) -> None:
        decision = eligibility.assess(obj(
            "Edge Computing vs. Cloud Computing: Choosing the Right Architecture",
            "TL;DR a guide. Mentions a data center and capital in passing.",
        ))
        self.assertFalse(decision.eligible)
        self.assertIn("content_type=explainer", decision.disqualifiers)

    def test_object_without_sources_is_rejected(self) -> None:
        node = IntelligenceObject(
            object_id="x", primary_sector="commercial_real_estate",
            title="Blackstone acquires portfolio for $400 million",
        )
        node.assess_evidence()
        self.assertFalse(eligibility.assess(node).eligible)

    def test_unclassified_sector_is_rejected(self) -> None:
        decision = eligibility.assess(obj("Something happened for $50 million", sector=""))
        self.assertFalse(decision.eligible)

    def test_administrative_notice_is_rejected_even_from_primary_authority(self) -> None:
        node = obj(
            "Agency Information Collection Activities: Comment Request",
            sector="banking_credit",
            tier=1,
            primary_authority=True,
        )
        decision = eligibility.assess(node)
        self.assertFalse(decision.eligible)
        self.assertIn("content_type=administrative_notice", decision.disqualifiers)
        eligibility.apply(node)
        self.assertEqual(node.content_type, ContentType.ADMINISTRATIVE_NOTICE)

    def test_source_priors_cannot_turn_unrelated_finance_into_cre(self) -> None:
        for title, summary in (
            ("HFTs Shun India Stock Closing Auction", "SEBI changed short-selling rules."),
            ("SGL Carbon Q2 Earnings Call Transcript", "The manufacturer reported revenue."),
            (
                "Foreign licensing business earns $59.5 million as Gulf developers pay",
                "Two developers paid brand licensing fees.",
            ),
        ):
            with self.subTest(title=title):
                decision = eligibility.assess(obj(title, summary))
                self.assertFalse(decision.eligible)
                self.assertIn("no Light Tower beat anchor", decision.disqualifiers)

    def test_consumer_house_story_is_not_institutional_real_estate(self) -> None:
        decision = eligibility.assess(obj(
            "Historic Maine house selling for $1 before demolition",
            "A single-family home must be moved by its buyer.",
        ))
        self.assertFalse(decision.eligible)
        self.assertIn("no Light Tower beat anchor", decision.disqualifiers)


class DecisionContract(unittest.TestCase):
    def test_every_decision_explains_itself(self) -> None:
        for node in (
            obj("Savills Completes $1.1B Acquisition of Eastdil Secured"),
            obj("Ten Productivity Habits for Remote Teams"),
            obj("Fed holds rates steady", sector="fed_macro"),
        ):
            decision = eligibility.assess(node)
            with self.subTest(title=node.title[:40]):
                self.assertTrue(decision.reason)
                self.assertTrue(decision.family)
                self.assertGreater(decision.confidence, 0.0)
                if decision.eligible:
                    self.assertTrue(decision.evidence)
                else:
                    self.assertTrue(decision.disqualifiers)

    def test_apply_records_the_decision_and_taxonomy_on_the_object(self) -> None:
        node = obj("Blackstone acquires a 400-unit apartment complex for $95 million")
        eligibility.apply(node)
        self.assertTrue(node.eligible)
        self.assertTrue(node.eligibility_reason)
        self.assertEqual(node.content_type, ContentType.NEWS_REPORT)
        self.assertEqual(node.primary_subsector, "multifamily",
                         "the dormant subsector taxonomy must now be populated")
        self.assertEqual(node.validate(), [])


if __name__ == "__main__":
    unittest.main()
