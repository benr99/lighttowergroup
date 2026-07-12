from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ideas_daily_agent import create_dossier, editorial_eligibility, publish_target_met, source_evidence_error
from ideas_quality import SECRET_RE, validate_article
from source_health import SourceHealthLedger


class IdeasPublishingSafetyTests(unittest.TestCase):
    def test_legal_story_cannot_enter_automatic_queue(self) -> None:
        eligible, reason = editorial_eligibility({
            "title": "Apple sues a rival over trade secrets",
            "summary": "The dispute involves an unreleased hardware product.",
            "entities": {"asset_classes": []},
            "source_domains": ["general"],
        })
        self.assertFalse(eligible)
        self.assertIn("legal", reason)

    def test_political_story_cannot_enter_automatic_queue(self) -> None:
        eligible, reason = editorial_eligibility({
            "title": "Congress debates a housing bill",
            "summary": "The proposal could affect apartment financing.",
            "entities": {"asset_classes": ["multifamily"]},
            "source_domains": ["cre", "policy"],
        })
        self.assertFalse(eligible)
        self.assertIn("political", reason)

    def test_general_news_needs_explicit_cre_relevance(self) -> None:
        eligible, reason = editorial_eligibility({
            "title": "Tech company opens an office",
            "summary": "A new product team will work there.",
            "entities": {"asset_classes": ["office"]},
            "source_domains": ["general"],
        })
        self.assertFalse(eligible)
        self.assertIn("CRE", reason)

    def test_real_estate_story_with_anchor_is_eligible(self) -> None:
        eligible, reason = editorial_eligibility({
            "title": "Developer refinances a Manhattan apartment building",
            "summary": "The $80M mortgage supports a 220-unit multifamily property.",
            "entities": {"asset_classes": ["multifamily"]},
            "source_domains": ["cre", "finance"],
        })
        self.assertTrue(eligible, reason)

    def test_missing_or_short_source_evidence_blocks_generation(self) -> None:
        self.assertIn("unavailable", source_evidence_error({"source_evidence": {"status": "unavailable"}}))
        self.assertIn("too short", source_evidence_error({"source_evidence": {
            "status": "retrieved", "text_chars": 120, "required_min_chars": 600,
        }}))
        self.assertIsNone(source_evidence_error({"source_evidence": {
            "status": "retrieved", "text_chars": 700, "required_min_chars": 600,
        }}))
        self.assertIsNone(source_evidence_error({"source_evidence": {"status": "fixture"}}))

    def test_secret_pattern_does_not_match_risk_adjusted(self) -> None:
        self.assertIsNone(SECRET_RE.search("A risk-adjusted return is not a secret."))
        self.assertIsNotNone(SECRET_RE.search("sk-abcdefghijklmnopqrstuvwxyz123456"))

    def test_automatic_publish_requires_the_full_requested_batch(self) -> None:
        self.assertFalse(publish_target_met(2, 3, False))
        self.assertTrue(publish_target_met(3, 3, False))
        self.assertTrue(publish_target_met(2, 3, True))

    def test_offline_dossier_never_requests_the_fixture_url(self) -> None:
        idea = {
            "title": "Fixture apartment project", "summary": "A housing project.",
            "source": "Offline Review Fixture", "url": "https://example.com/fixture",
            "entities": {"amounts": [], "markets": [], "asset_classes": ["multifamily"]},
            "ideas_score": {},
        }
        with patch("ideas_daily_agent.fetch_article_text") as fetch:
            dossier = create_dossier(idea, offline=True)
        fetch.assert_not_called()
        self.assertEqual(dossier["source_evidence"]["status"], "fixture")

    def test_quality_gate_requires_review_for_litigation(self) -> None:
        article = {
            "slug": "test", "title": "Test", "subtitle": "Test", "excerpt": "Test",
            "meta_description": "Test", "body_html": "<p>lawsuit</p>" * 900,
            "sources": [{"name": "Source", "url": "https://example.org/story"}],
            "generation_mode": "ai", "quality_score": 8, "risk_score": 2,
        }
        errors = validate_article(article, {"reported_facts": [], "source_evidence": {"status": "retrieved"}})
        self.assertTrue(any("requires editorial review" in error for error in errors))

    def test_source_health_quarantines_repeated_failures_then_recovers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            ledger = SourceHealthLedger(Path(temp_dir) / "health.json", failure_threshold=2, cooldown_hours=1)
            ledger.record_failure("Broken feed", "HTTP 403", 20)
            ledger.record_failure("Broken feed", "HTTP 403", 20)
            self.assertTrue(ledger.is_quarantined("Broken feed"))
            ledger.records["Broken feed"]["last_failure_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            self.assertFalse(ledger.is_quarantined("Broken feed"))
            ledger.record_success("Broken feed", 10, 20)
            self.assertFalse(ledger.is_quarantined("Broken feed"))


if __name__ == "__main__":
    unittest.main()
