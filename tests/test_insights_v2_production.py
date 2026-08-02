from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from canonical_item import CanonicalItem
from editorial_pipeline import EditorialPipeline
from v2_editorial import (
    canonical_item_to_editorial_event,
    generate_v2_article,
    is_article_level_url,
    select_daily_items,
)


def make_item(
    headline: str = "Acme closes a $100 million financing",
    *,
    sector: str = "commercial_real_estate",
    score: float = 72.0,
    url: str = "https://news.example.com/markets/acme-financing",
) -> CanonicalItem:
    item = CanonicalItem()
    item.headline = headline
    item.source_name = "Example Markets"
    item.source_url = url
    item.canonical_url = url
    item.raw_summary = (
        "Acme closed a $100 million financing on August 1, 2026. "
        "The five-year loan refinances a 300-unit property."
    )
    item.publication_date = "2026-08-01T12:00:00+00:00"
    item.source_tier = 2
    item.source_authority = "secondary"
    item.primary_sector = sector
    item.composite_score = score
    item.tier = "tier_2_strongly_recommended"
    item.status = "scored"
    item.item_id = item.generate_id()
    item.transaction_value = 100_000_000
    item.transaction_value_raw = "$100 million"
    item.companies = ["Acme"]
    return item


def dossier_for(item: CanonicalItem) -> dict:
    return {
        "title": item.headline,
        "evidence_level": "thin",
        "independent_source_count": 1,
        "primary_source_count": 0,
        "usable_full_text_count": 1,
        "sources": [{
            "name": item.source_name,
            "url": item.source_url,
            "domain": "news.example.com",
            "published": item.publication_date,
            "authority": "secondary",
            "tier": 2,
            "summary": item.raw_summary,
            "full_text_excerpt": item.raw_summary,
            "reported_facts": [item.raw_summary],
        }],
        "reported_facts": [{
            "fact": item.raw_summary,
            "source_url": item.source_url,
            "source_name": item.source_name,
        }],
        "reporting_gaps": ["A second independent source has not corroborated the event."],
    }


class InsightsV2ProductionTests(unittest.TestCase):
    def test_model_router_keeps_healthy_writing_provider(self):
        import model_router

        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": "key", "openai": None}),
            patch.object(model_router, "check_provider_health", return_value=True),
        ):
            provider = model_router.select_provider(for_writing=True)
        self.assertEqual(provider["provider"], "deepseek")
        self.assertEqual(provider["model"], "deepseek-v4-pro")
        self.assertEqual(provider["purpose"], "writing")
        self.assertFalse(provider["fallback"])

    def test_model_router_fails_closed_without_a_provider(self):
        import model_router

        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": None, "openai": None}),
            patch.object(model_router, "check_provider_health", return_value=False),
        ):
            with self.assertRaises(RuntimeError):
                model_router.select_provider(for_writing=True)

    def test_article_level_url_rejects_publication_homepage(self):
        self.assertFalse(is_article_level_url("https://news.example.com/"))
        self.assertTrue(is_article_level_url("https://news.example.com/article/123"))

    def test_daily_selection_prefers_cross_sector_leaders(self):
        cre = make_item("CRE story", sector="commercial_real_estate", score=90)
        pe = make_item("PE story", sector="private_equity", score=80, url="https://pe.example.com/deals/1")
        dc = make_item("DC story", sector="data_centers", score=70, url="https://dc.example.com/campus/1")
        chosen = select_daily_items(
            {"commercial_real_estate": [cre], "private_equity": [pe], "data_centers": [dc]},
            limit=3,
        )
        self.assertEqual([item.primary_sector for item in chosen], [
            "commercial_real_estate", "private_equity", "data_centers"
        ])

    def test_pipeline_v2_exposes_ranked_items_to_the_production_orchestrator(self):
        import pipeline_v2

        item = make_item()
        with (
            patch.object(pipeline_v2, "load_sources", return_value=[{"name": "Example"}]),
            patch.object(pipeline_v2, "fetch_all_sources", return_value=[item]),
            patch.object(pipeline_v2, "classify_batch", return_value=[item]),
            patch.object(pipeline_v2, "get_sector_stats", return_value={item.primary_sector: 1}),
            patch.object(pipeline_v2, "score_batch", return_value=[item]),
            patch.object(pipeline_v2, "get_scoring_stats", return_value={"tier_distribution": {item.tier: 1}, "sector_stats": {}}),
            patch.object(pipeline_v2, "rank_and_select", return_value=({item.primary_sector: [item]}, {"total_selected": 1})),
        ):
            result = pipeline_v2.run_pipeline(shadow=True, verbose=False)
        self.assertEqual(result["status"], "complete")
        self.assertIs(result["_selected"][item.primary_sector][0], item)

    def test_v2_event_preserves_canonical_source_and_item(self):
        item = make_item()
        event = canonical_item_to_editorial_event(item)
        self.assertEqual(event["sources"][0]["url"], item.source_url)
        self.assertEqual(event["candidate"]["pipeline_version"], "v2")
        self.assertEqual(event["candidate"]["canonical_item"]["item_id"], item.item_id)

    def test_prompt_contains_the_actual_dossier_evidence(self):
        item = make_item()
        dossier = dossier_for(item)
        pipeline = EditorialPipeline(
            api_key="",
            provider={"provider": "deepseek", "model": "deepseek-v4-pro", "url": "https://api.deepseek.com/v1/chat/completions"},
        )
        brief = pipeline.stage_analytical_brief(item, dossier)
        prompt = pipeline.stage_assemble_prompt(item, brief, dossier)["user_prompt"]
        self.assertIn(item.source_url, prompt)
        self.assertIn("SOURCE DOSSIER", prompt)
        self.assertIn("$100 million", prompt)

    def test_financial_review_failure_is_not_approved(self):
        pipeline = EditorialPipeline(api_key="key")
        with patch("editorial_pipeline.call_deepseek", side_effect=RuntimeError("provider down")):
            review = pipeline.stage_financial_review(
                {"body_html": "<p>Article</p>"},
                {"central_financial_question": "Why?", "thesis": "Test", "key_numbers": []},
            )
        self.assertFalse(review["passed"])
        self.assertEqual(review["status"], "unavailable")
        self.assertEqual(review["score_1_10"], 0)

    def test_pipeline_returns_review_required_when_review_cannot_clear(self):
        item = make_item()
        dossier = dossier_for(item)
        pipeline = EditorialPipeline(api_key="key")
        draft = {
            "title": "Acme's $100 Million Clock",
            "body_html": "<p>Acme closed a $100 million financing.</p>",
            "excerpt": "Acme refinanced the property.",
            "sources": [{"name": item.source_name, "url": item.source_url}],
        }
        with (
            patch.object(pipeline, "stage_draft", return_value={"status": "completed", "article": draft}),
            patch.object(pipeline, "stage_financial_review", return_value={"passed": False, "issues": ["review unavailable"]}),
            patch.object(pipeline, "stage_editorial_review", return_value={"passed": True, "issues": []}),
            patch.object(pipeline, "stage_fact_verification", return_value={"passed": True, "issues": []}),
            patch.object(pipeline, "stage_final_revision", return_value={"status": "revision_failed", "article": draft}),
        ):
            result = pipeline.run(item, dossier)
        self.assertEqual(result["status"], "review_required")

    def test_generated_article_uses_dossier_sources_not_model_sources(self):
        item = make_item()
        event = canonical_item_to_editorial_event(item)
        story = event["candidate"] | {
            "research_dossier": dossier_for(item),
            "editorial_event_id": event["event_id"],
            "editorial_format": "brief",
            "franchise": event["franchise"],
            "must_read_score": event["must_read_score"],
        }
        fake_result = {
            "status": "completed",
            "errors": [],
            "stages": {},
            "article": {
                "title": "Acme's $100 Million Refinancing",
                "slug": "acme-refinancing",
                "body_html": "<p>Acme closed a $100 million financing.</p>",
                "excerpt": "A five-year refinancing changes the sponsor's clock.",
                "sources": [{"name": "Invented", "url": "https://invented.example/bad"}],
                "tags": ["refinancing"],
            },
        }
        pipeline_instance = Mock()
        pipeline_instance.run.return_value = fake_result
        with patch("v2_editorial.EditorialPipeline", return_value=pipeline_instance):
            article = generate_v2_article(
                story,
                api_key="key",
                provider={"provider": "deepseek", "model": "deepseek-v4-pro", "url": "https://api.deepseek.com/v1/chat/completions"},
            )
        self.assertEqual(article["sources"], [{"name": item.source_name, "url": item.source_url}])
        self.assertEqual(article["source_count"], 1)
        self.assertEqual(article["pipeline_version"], "v2")
        import daily_news_agent

        html = daily_news_agent.render_html(article)
        self.assertIn(item.source_url, html)
        self.assertIn("1 source", html)
        self.assertIn("Acme's $100 Million Refinancing", html)

    def test_active_insights_path_has_no_retired_deepseek_model(self):
        for path in SCRIPTS.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("deepseek-chat", text, path.name)

    def test_workflow_invokes_v2_and_exposes_honest_fallback_configuration(self):
        workflow = (ROOT / ".github" / "workflows" / "daily-insights-agent.yml").read_text(encoding="utf-8")
        self.assertIn("--pipeline-v2", workflow)
        self.assertIn("DEEPSEEK_MODEL: deepseek-v4-pro", workflow)
        self.assertIn("OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}", workflow)


if __name__ == "__main__":
    unittest.main()
