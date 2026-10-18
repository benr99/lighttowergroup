"""Unit and contract tests for the Light Tower Group NYC >$10M Transaction Desk."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from nyc_transactions.economics import (
    build_ammo_sheet,
    compute_economics,
    evaluate_eligibility,
)
from nyc_transactions.generation import (
    generate_nyc_transaction_article,
    verify_nyc_story,
)
from nyc_transactions.models import (
    MortgageRecord,
    NycTransactionDossier,
    PriorSaleRecord,
    PropertyIdentity,
)
from nyc_transactions.sources import (
    classify_mortgage_doc_type,
    get_curated_nyc_transactions,
)
import site_renderer


def _make_sample_dossier(
    sale_price_usd: float = 25_000_000.0,
    borough: str = "Manhattan",
    building_class: str = "O4",
    is_related_party_or_nominal: bool = False,
    is_single_condo_or_coop_unit: bool = False,
) -> NycTransactionDossier:
    return NycTransactionDossier(
        transaction_id="test-nyc-deal-1",
        property_info=PropertyIdentity(
            address="100 Test Avenue",
            borough=borough,
            neighborhood="Midtown South",
            bbl="1-00800-0010",
            building_class=building_class,
            asset_type="Office Building",
            gross_sqft=100_000,
            lot_sqft=10_000,
            buildable_sqft=100_000,
            total_units=50,
            residential_units=50,
            stories=10,
            year_built=1960,
            zoning="C6-4",
            is_single_condo_or_coop_unit=is_single_condo_or_coop_unit,
        ),
        sale_price_usd=sale_price_usd,
        closing_date="2026-03-10",
        recorded_date="2026-03-15",
        buyer="Test Capital Partners via 100 Test Owner LLC",
        seller="Legacy Holdings via 100 Test Seller LLC",
        broker="Eastdil Secured",
        is_related_party_or_nominal=is_related_party_or_nominal,
        mortgages=[
            MortgageRecord(
                document_id="2026031500112234",
                instrument_type="CEMA Senior Loan",
                amount_usd=15_000_000.0,
                lender="Test Debt Fund",
                recorded_date="2026-03-15",
                is_modification_or_assignment_only=False,
            )
        ],
        prior_sales=[
            PriorSaleRecord(
                closing_date="2021-03-10",
                price_usd=20_000_000.0,
                document_id="2021031500998877",
                same_scope=True,
            )
        ],
        notes=["Verified test deed transfer for 100 Test Avenue."],
    )


class TestNycTransactionsEligibility(unittest.TestCase):
    def test_strictly_greater_than_10m_threshold(self):
        d_99 = _make_sample_dossier(sale_price_usd=9_900_000.0)
        d_100 = _make_sample_dossier(sale_price_usd=10_000_000.0)
        d_101 = _make_sample_dossier(sale_price_usd=10_100_000.0)

        self.assertFalse(evaluate_eligibility(d_99).eligible)
        self.assertFalse(evaluate_eligibility(d_100).eligible)
        self.assertEqual(evaluate_eligibility(d_100).status, "boundary_review")
        self.assertTrue(evaluate_eligibility(d_101).eligible)

    def test_borough_and_building_class_gates(self):
        non_nyc = _make_sample_dossier(borough="Jersey City")
        self.assertFalse(evaluate_eligibility(non_nyc).eligible)

        single_condo = _make_sample_dossier(building_class="R4", is_single_condo_or_coop_unit=True)
        self.assertFalse(evaluate_eligibility(single_condo).eligible)

        bulk_condo = _make_sample_dossier(building_class="R4", is_single_condo_or_coop_unit=False)
        self.assertTrue(evaluate_eligibility(bulk_condo).eligible)

        related_party = _make_sample_dossier(is_related_party_or_nominal=True)
        self.assertFalse(evaluate_eligibility(related_party).eligible)


class TestNycTransactionsEconomics(unittest.TestCase):
    def test_deterministic_economics_and_ammo_sheet(self):
        dossier = _make_sample_dossier(sale_price_usd=25_000_000.0)
        econ = compute_economics(dossier)

        self.assertEqual(econ.price_per_gsf, 250.0)
        self.assertEqual(econ.price_per_unit, 500_000.0)
        self.assertEqual(econ.acquisition_debt_usd, 15_000_000.0)
        self.assertEqual(econ.implied_ltv_pct, 60.0)
        self.assertEqual(econ.implied_equity_usd, 10_000_000.0)
        self.assertEqual(econ.prior_sale_change_usd, 5_000_000.0)
        self.assertEqual(econ.prior_sale_change_pct, 25.0)
        self.assertAlmostEqual(econ.hold_period_years or 0.0, 5.0, places=1)

        ammo = build_ammo_sheet(dossier)
        ammo_json = json.dumps(ammo)
        self.assertIn("$25M", ammo_json)
        self.assertIn("60%", ammo_json)
        self.assertIn("CEMA", ammo_json)

    def test_pure_modification_excluded_from_new_acquisition_debt(self):
        dossier = _make_sample_dossier(sale_price_usd=25_000_000.0)
        dossier.mortgages[0].is_modification_or_assignment_only = True
        econ = compute_economics(dossier)
        self.assertIsNone(econ.acquisition_debt_usd)
        self.assertIsNone(econ.implied_ltv_pct)

    def test_classify_mortgage_doc_type(self):
        is_cema, is_mod = classify_mortgage_doc_type("M&CON", "Consolidation and extension")
        self.assertTrue(is_cema)
        self.assertFalse(is_mod)

        is_cema2, is_mod2 = classify_mortgage_doc_type("AL&R", "")
        self.assertFalse(is_cema2)
        self.assertTrue(is_mod2)


class TestNycTransactionsGenerationAndSiteIntegration(unittest.TestCase):
    def test_curated_dossiers_generate_valid_articles_and_html(self):
        dossiers = get_curated_nyc_transactions()
        self.assertGreaterEqual(len(dossiers), 3)

        for dossier in dossiers:
            self.assertTrue(evaluate_eligibility(dossier).eligible)
            article = generate_nyc_transaction_article(dossier, use_llm=False)
            self.assertEqual(article["vertical"], "nyc_transactions")
            self.assertEqual(article["category"], "NYC $10M+ Transaction Desk")
            self.assertGreaterEqual(len(article["data_points"]), 5)

            econ = compute_economics(dossier)
            ok, errs = verify_nyc_story(article, dossier, econ)
            self.assertTrue(ok, f"Verification failed for {dossier.transaction_id}: {errs}")

            rendered = site_renderer.render_html(article)
            self.assertIn("Verified ACRIS &amp; PLUTO Deal Sheet", rendered)
            self.assertIn(dossier.property_info.bbl, rendered)

    def test_insights_html_has_nyc_transactions_filter(self):
        insights_html = (ROOT / "insights.html").read_text(encoding="utf-8")
        self.assertIn('data-filter="nyc_transactions"', insights_html)
        self.assertIn("NYC $10M+ Deals", insights_html)
        self.assertIn("post.vertical === 'nyc_transactions'", insights_html)


if __name__ == "__main__":
    unittest.main()
