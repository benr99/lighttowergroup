from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
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
        self.assertIn("identity.netlify.com/v1/netlify-identity-widget.js", dashboard)
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
            "analytics-dashboard.js",
            "analytics-retention.js",
            "capital-diagnostic.js",
        ):
            function_path = ROOT / "netlify" / "functions" / filename
            self.assertTrue(function_path.exists())
            self.assertNotIn(
                "consistency: 'strong'",
                function_path.read_text(encoding="utf-8"),
                f"{filename} must use the Netlify Functions-compatible Blob consistency mode",
            )

    def test_editorial_state_is_blocked_from_public_deployment(self) -> None:
        config = (ROOT / "netlify.toml").read_text(encoding="utf-8")
        self.assertIn('from   = "/.editorial-state/*"', config)
        self.assertIn('to     = "/"', config)

    def test_daily_workflow_validates_before_publishing(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "daily-insights-agent.yml").read_text(encoding="utf-8")
        self.assertIn("--selection-mode edition", workflow)
        self.assertIn("article_count:", workflow)
        self.assertIn("ARTICLE_COUNT: ${{ inputs.article_count || '5' }}", workflow)
        self.assertIn('--articles "$ARTICLE_COUNT"', workflow)
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

    def test_csp_allows_inline_scripts_on_every_page_that_ships_them(self) -> None:
        """Regression guard for the homepage blanking introduced by merge 5278972.

        The `/*` script-src lost 'unsafe-inline' in that merge, which silently
        blocked index.html's scroll-reveal IntersectionObserver. Twenty elements
        across the transactions, practice, advantage, process and leadership
        sections stayed at opacity:0 in production. Sixteen pages were affected.
        """
        toml_text = (ROOT / "netlify.toml").read_text(encoding="utf-8")
        blocks = re.findall(
            r'\[\[headers\]\]\s*\n\s*for\s*=\s*"([^"]+)"(.*?)(?=\n\[\[headers\]\]|\Z)',
            toml_text,
            re.S,
        )
        policies: dict[str, str] = {}
        for path, body in blocks:
            match = re.search(r'Content-Security-Policy\s*=\s*"(.*?)"', body, re.S)
            if not match:
                continue
            directives = [
                part.strip()
                for part in match.group(1).split(";")
                if part.strip().startswith("script-src")
            ]
            if directives:
                policies[path] = directives[0]

        self.assertIn("/*", policies, "netlify.toml must define a default script-src")

        def script_src_for(page: str) -> str:
            """Resolve Netlify's most-specific-path-wins header matching."""
            route = f"/{page}"
            if route in policies:
                return policies[route]
            for pattern, directive in policies.items():
                if pattern.endswith("/*") and pattern != "/*" and route.startswith(pattern[:-1]):
                    return directive
            return policies["/*"]

        blocked: list[str] = []
        for page in sorted(ROOT.glob("*.html")):
            # Inline blocks inside HTML comments are inert and must not count.
            markup = re.sub(r"<!--.*?-->", "", page.read_text(encoding="utf-8"), flags=re.S)
            inline_scripts = [
                tag
                for tag in re.findall(r"<script([^>]*)>", markup)
                if "src=" not in tag and "ld+json" not in tag
            ]
            handlers = re.findall(r"\son(?:click|submit|change|input|load|error)\s*=", markup)
            if not inline_scripts and not handlers:
                continue
            if "'unsafe-inline'" not in script_src_for(page.name):
                blocked.append(page.name)

        self.assertEqual(
            blocked,
            [],
            "These pages ship inline scripts or inline event handlers but their CSP "
            f"script-src omits 'unsafe-inline', so that JavaScript is dead in production: {blocked}",
        )

    def test_every_published_article_is_listed_on_the_insights_page(self) -> None:
        """sitemap.xml + feed.xml mean published; insights.json is what readers browse.

        Thirteen articles reached the sitemap and the RSS feed but never entered
        insights.json, so search engines and feed readers could find them while
        the on-site listing could not. Run:
            python scripts/content_maintenance.py reconcile-insights --apply
        """
        records = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))
        listed = {str(record.get("slug", "")) for record in records}
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        feed = (ROOT / "feed.xml").read_text(encoding="utf-8")

        unlisted = []
        for page in sorted((ROOT / "insights").glob("*.html")):
            url = f"https://lighttowergroup.co/insights/{page.stem}.html"
            if page.stem not in listed and url in sitemap and url in feed:
                unlisted.append(page.stem)

        self.assertEqual(
            unlisted,
            [],
            "These articles are in sitemap.xml and feed.xml but missing from "
            f"insights.json, so they never appear on the Insights page: {unlisted}",
        )

    def test_insights_manifest_stays_in_descending_date_order(self) -> None:
        """The listing renders in manifest order, so newest must stay first."""
        records = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))

        def parsed(value: str):
            for fmt in ("%Y-%m-%d", "%B %d, %Y"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return datetime.min

        dates = [parsed(str(record.get("date", ""))) for record in records]
        out_of_order = [i for i in range(len(dates) - 1) if dates[i] < dates[i + 1]]
        self.assertEqual(out_of_order, [], f"manifest not newest-first at indexes {out_of_order[:5]}")

    def test_homepage_reveal_animation_has_a_script_to_unhide_it(self) -> None:
        """`.reveal` starts at opacity:0, so the observer that adds .visible must ship."""
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(".reveal.visible", homepage)
        self.assertIn("IntersectionObserver", homepage)
        self.assertIn("classList.add('visible')", homepage)


if __name__ == "__main__":
    unittest.main()
