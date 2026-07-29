from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteContractTests(unittest.TestCase):
    def test_public_content_indexes_are_well_formed(self) -> None:
        records = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))
        self.assertGreater(len(records), 0)
        self.assertEqual(len({item["slug"] for item in records}), len(records))
        self.assertTrue(all(item.get("title") and item.get("url", "").startswith("/insights/") for item in records))
        ET.parse(ROOT / "sitemap.xml")
        ET.parse(ROOT / "feed.xml")

    def test_insights_filters_only_use_real_manifest_categories(self) -> None:
        records = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))
        categories = {item["category"] for item in records}
        expected = {
            "Capital Markets", "Capital Markets Research", "Market Commentary",
            "Deal Intelligence", "Architecture & Capital Markets", "Market Analysis",
            "Debt & Equity", "Policy & Regulation",
        }
        self.assertTrue(expected.issubset(categories))

    def test_core_conversion_and_recovery_pages_exist(self) -> None:
        privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
        messaging_terms = (ROOT / "sms-terms.html").read_text(encoding="utf-8")
        not_found = (ROOT / "404.html").read_text(encoding="utf-8")
        self.assertIn("Privacy Notice | Light Tower Group", privacy)
        self.assertIn('href="/privacy.html"', privacy)
        self.assertIn("Capital Readiness Diagnostic", privacy)
        self.assertIn("Messaging Terms | Light Tower Group", messaging_terms)
        self.assertIn("Reply <strong>STOP</strong>", messaging_terms)
        self.assertIn('name="robots" content="noindex, follow"', messaging_terms)
        self.assertIn('name="robots" content="noindex, follow"', not_found)

        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://lighttowergroup.co/privacy.html", sitemap)
        self.assertNotIn("https://lighttowergroup.co/404.html", sitemap)

    def test_homepage_claims_and_transaction_summary_are_consistent(self) -> None:
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Debt and equity capital", homepage)
        self.assertIn("for commercial real estate.", homepage)
        self.assertIn("transactions of $5 million and above", homepage)
        self.assertIn("Request a Confidential Deal Review", homepage)
        self.assertNotIn("250,000", homepage)
        self.assertIn("$23M", homepage)
        self.assertIn("Mixed-Use Development", homepage)
        self.assertIn("Manhattan, NY", homepage)
        self.assertNotIn("Multifamily Acquisition", homepage)

    def test_homepage_structured_data_references_real_assets(self) -> None:
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        match = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', homepage, re.S)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        organization = data["@graph"][0]
        self.assertEqual(organization["logo"], "https://lighttowergroup.co/favicon.svg")
        self.assertTrue((ROOT / "favicon.svg").exists())
        self.assertNotIn("foundingDate", organization)

    def test_optimized_hero_assets_stay_within_budget(self) -> None:
        source = ROOT / "capital-intelligence-hero.png"
        optimized = ROOT / "capital-intelligence-hero.webp"
        responsive = ROOT / "capital-intelligence-hero-960.webp"
        self.assertTrue(optimized.exists())
        self.assertTrue(responsive.exists())
        self.assertLess(optimized.stat().st_size, 250_000)
        self.assertLess(responsive.stat().st_size, 100_000)
        self.assertLess(optimized.stat().st_size, source.stat().st_size)

    def test_insights_page_is_article_first_and_edition_assets_remain_managed(self) -> None:
        edition = json.loads((ROOT / "latest-edition.json").read_text(encoding="utf-8"))
        self.assertIn(edition["status"], {"ready", "no_publishable_story"})
        self.assertIn("reader_prompt", edition)
        insights = (ROOT / "insights.html").read_text(encoding="utf-8")
        self.assertNotIn('id="daily-edition"', insights)
        self.assertNotIn('href="/edition.css"', insights)
        self.assertNotIn('src="/edition.js"', insights)
        self.assertIn('id="insights-search"', insights)
        self.assertIn('id="insights-grid"', insights)
        self.assertTrue((ROOT / "edition.js").exists())
        self.assertTrue((ROOT / "edition.css").exists())
        self.assertTrue((ROOT / "netlify" / "functions" / "newsletter-subscribe.js").exists())
        self.assertTrue((ROOT / "netlify" / "functions" / "editorial-feedback.js").exists())

    def test_capital_diagnostic_reaches_existing_and_future_articles(self) -> None:
        site_script = (ROOT / "site.js").read_text(encoding="utf-8")
        diagnostic_script = (ROOT / "capital-diagnostic.js").read_text(encoding="utf-8")
        diagnostic_styles = (ROOT / "capital-diagnostic.css").read_text(encoding="utf-8")
        generator = (ROOT / "scripts" / "daily_news_agent.py").read_text(encoding="utf-8")
        config = (ROOT / "netlify.toml").read_text(encoding="utf-8")

        self.assertIn("loadCapitalDiagnostic", site_script)
        self.assertIn("/capital-diagnostic.js", site_script)
        self.assertIn("/capital-diagnostic.css", site_script)
        self.assertIn("scoreSubmission", diagnostic_script)
        self.assertIn("diagnostic_contact_submit", diagnostic_script)
        self.assertIn("@media (max-width: 600px)", diagnostic_styles)
        self.assertIn('<script src="/site.js" defer></script>', generator)
        self.assertIn('for = "/capital-diagnostic.js"', config)
        self.assertTrue((ROOT / "netlify" / "functions" / "capital-diagnostic.js").exists())

        article_files = list((ROOT / "insights").glob("*.html"))
        self.assertGreater(len(article_files), 800)
        missing_shared_script = [
            path.name for path in article_files
            if "/site.js" not in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(missing_shared_script, [])

    def test_private_first_party_visitor_intelligence_contract(self) -> None:
        site_script = (ROOT / "site.js").read_text(encoding="utf-8")
        tracker = (ROOT / "visitor-analytics.js").read_text(encoding="utf-8")
        dashboard = (ROOT / "analytics-dashboard.html").read_text(encoding="utf-8")
        dashboard_script = (ROOT / "analytics-dashboard.js").read_text(encoding="utf-8")
        privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
        config = (ROOT / "netlify.toml").read_text(encoding="utf-8")
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")

        self.assertIn("loadVisitorAnalytics", site_script)
        self.assertIn("/visitor-analytics.js", site_script)
        self.assertIn("ltgFirstPartyTrack", site_script)
        self.assertIn("navigator.globalPrivacyControl", tracker)
        self.assertIn("navigator.doNotTrack", tracker)
        self.assertIn("ltg_analytics_optout", tracker)
        self.assertIn("sessionStorage", tracker)
        self.assertNotIn("localStorage.setItem('ltg_analytics_session", tracker)
        self.assertIn('name="robots" content="noindex, nofollow, noarchive"', dashboard)
        self.assertIn("Article-to-mandate funnel", dashboard)
        self.assertIn("Capital-readiness leads", dashboard)
        self.assertIn("analytics-dashboard", dashboard_script)
        self.assertIn("first-party analytics system", privacy)
        self.assertIn("does not use advertising pixels", privacy)
        self.assertIn("scheduled for deletion after 180 days", privacy)
        self.assertIn("data-analytics-choice", privacy)
        self.assertIn('from   = "/command-center"', config)
        self.assertIn('[functions."analytics-retention"]', config)
        self.assertIn('schedule = "@daily"', config)
        self.assertIn('for = "/analytics-dashboard.html"', config)
        self.assertNotIn("analytics-dashboard", sitemap)

        for filename in (
            "visitor-track.js",
            "analytics-auth.js",
            "analytics-dashboard.js",
            "analytics-retention.js",
        ):
            self.assertTrue((ROOT / "netlify" / "functions" / filename).exists())

    def test_editorial_state_is_blocked_from_public_deployment(self) -> None:
        config = (ROOT / "netlify.toml").read_text(encoding="utf-8")
        self.assertIn('from   = "/.editorial-state/*"', config)
        self.assertIn('to     = "/"', config)

    def test_daily_workflow_validates_before_publishing(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "daily-insights-agent.yml").read_text(encoding="utf-8")
        self.assertIn("--selection-mode edition", workflow)
        self.assertIn("--articles 5", workflow)
        self.assertIn("--daily-target 3", workflow)
        self.assertIn("--skip-git", workflow)
        self.assertIn("github.event.schedule", workflow)
        self.assertIn("resolve_schedule_policy.py", workflow)
        self.assertNotIn("date +%H", workflow)
        self.assertIn("shadow) args+=(--shadow)", workflow)
        self.assertIn("preview) args+=(--dry-run)", workflow)
        self.assertIn("steps.policy.outputs.mode == 'publish'", workflow)
        self.assertIn("include-hidden-files: true", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertNotIn("--no-limit", workflow)
        self.assertNotIn("ANTHROPIC_API_KEY", workflow)
        self.assertLess(
            workflow.index("Validate the generated edition before deployment"),
            workflow.index("Publish the validated generated files"),
        )
        self.assertIn("publication-decision.json", workflow)
        self.assertIn("gh pr create", workflow)


if __name__ == "__main__":
    unittest.main()
