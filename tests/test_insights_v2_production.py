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
from editorial_pipeline import EditorialPipeline, _extract_json
from v2_editorial import (
    canonical_item_to_editorial_event,
    generate_v2_article,
    is_article_level_url,
    is_daily_article_candidate,
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
    def test_reviewer_json_accepts_unescaped_newline_without_inventing_fields(self):
        parsed = _extract_json(
            '{"issues": [], "passed": true, "summary": "line one\nline two"}'
        )

        self.assertEqual(parsed["issues"], [])
        self.assertIs(parsed["passed"], True)
        self.assertEqual(parsed["summary"], "line one\nline two")

    def test_reviewer_json_accepts_a_trailing_comma_but_requires_an_object(self):
        self.assertEqual(_extract_json('{"passed": false,}'), {"passed": False})
        with self.assertRaises(ValueError):
            _extract_json('[]')

    def test_reasoning_model_reviewers_have_room_for_complete_json(self):
        source = (ROOT / "scripts" / "editorial_pipeline.py").read_text(encoding="utf-8")

        self.assertGreaterEqual(source.count("max_tokens=4000"), 2)

    def test_shadow_summary_reports_target_as_not_evaluated(self):
        from edition_manager import render_run_summary

        summary = render_run_summary({
            "status": "shadow_complete",
            "daily_target": 1,
            "daily_target_met": None,
            "research_candidate_count": 1,
            "articles": [],
        })

        self.assertIn("Status: **shadow_complete**", summary)
        self.assertIn("Articles: **0**", summary)
        self.assertIn("Daily target met: **not evaluated**", summary)

    def test_preview_summary_does_not_claim_candidates_were_published(self):
        from edition_manager import render_run_summary

        summary = render_run_summary({
            "status": "preview_complete",
            "daily_target": 1,
            "daily_target_met": True,
            "articles": [{"title": "A verified preview", "source_count": 2}],
        })

        self.assertIn("## Preview candidates", summary)
        self.assertNotIn("## Published candidates", summary)

    def test_daily_agent_uses_a_fallback_research_pool_but_caps_generation(self):
        source = (ROOT / "scripts" / "daily_news_agent.py").read_text(encoding="utf-8")

        self.assertIn("RESEARCH_CANDIDATE_CEILING", source)
        self.assertIn("if len(articles) >= MAX_ARTICLES", source)
        self.assertNotIn("if len(enriched_candidates) >= MAX_ARTICLES", source)
        self.assertIn("generation held", source)

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

    def test_source_registry_sector_survives_ambiguous_classification(self):
        from classification import classify_item

        item = CanonicalItem.from_rss_entry(
            {
                "title": "Funding for renewables is ready",
                "link": "https://energy.example.com/story/1",
                "summary": "Capital is available for a new project.",
            },
            {
                "name": "Clean Energy Desk",
                "sectors": ["energy"],
                "tier": 2,
                "source_type": "rss",
            },
        )

        classified = classify_item(item)
        self.assertEqual(classified.primary_sector, "energy")
        self.assertNotEqual(classified.classification_method, "needs_llm")

    def test_daily_selection_skips_reserve_and_product_review_items(self):
        reserve = make_item("A reserve story", score=90)
        reserve.tier = "tier_4_reserve"
        review = make_item(
            "Test Drive: an electric family car",
            sector="energy",
            score=80,
            url="https://energy.example.com/reviews/car",
        )
        qualified = make_item(
            "Developer secures construction financing",
            score=70,
            url="https://news.example.com/deals/construction",
        )

        self.assertFalse(is_daily_article_candidate(reserve))
        self.assertFalse(is_daily_article_candidate(review))
        self.assertEqual(
            select_daily_items(
                {"commercial_real_estate": [reserve, qualified], "energy": [review]},
                limit=3,
            ),
            [qualified],
        )

    def test_development_brief_does_not_assign_an_acquisition_question(self):
        from analytical_brief import build_analytical_brief

        item = make_item("980-unit development proposal advances", score=60)
        item.raw_summary = "The developer filed a proposal for 980 housing units."
        question = build_analytical_brief(item)["central_financial_question"]

        self.assertIn("development", question)
        self.assertNotIn("buyer", question.lower())

    def test_financial_reviewer_is_calibrated_to_thin_brief_evidence(self):
        item = make_item()
        dossier = dossier_for(item)
        pipeline = EditorialPipeline(api_key="key")
        captured = {}

        def fake_review(prompt, *_args, **_kwargs):
            captured["prompt"] = prompt
            return '{"issues": [], "passed": true, "score_1_10": 9, "summary": "bounded"}'

        with patch("editorial_pipeline.call_deepseek", side_effect=fake_review):
            review = pipeline.stage_financial_review(
                {"body_html": "<p>Acme disclosed a financing; pricing was not disclosed.</p>"},
                {"central_financial_question": "What is known?", "thesis": "Bounded", "key_numbers": []},
                dossier=dossier,
                article_format="brief",
            )

        self.assertTrue(review["passed"])
        self.assertIn("one credible source", captured["prompt"])
        self.assertIn("Do NOT fail", captured["prompt"])

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
        prompt = pipeline.stage_assemble_prompt(
            item,
            brief,
            dossier,
            article_format="brief",
        )["user_prompt"]
        self.assertIn(item.source_url, prompt)
        self.assertIn("SOURCE DOSSIER", prompt)
        self.assertIn("$100 million", prompt)
        self.assertIn("HARD LENGTH CONTRACT: 240-430 words", prompt)
        self.assertNotIn("Editorial significance score", prompt)

    def test_internal_composite_score_is_not_a_public_key_number(self):
        from analytical_brief import build_analytical_brief

        item = make_item(score=56.2)
        brief = build_analytical_brief(item, dossier_for(item))
        numbers = [entry.get("number") for entry in brief["key_numbers"]]

        self.assertNotIn("56.2", numbers)

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
        self.assertEqual(pipeline_instance.run.call_args.kwargs["article_format"], "brief")
        self.assertEqual(article["sources"], [{"name": item.source_name, "url": item.source_url}])
        self.assertEqual(article["source_count"], 1)
        self.assertEqual(article["pipeline_version"], "v2")
        import daily_news_agent

        html = daily_news_agent.render_html(article)
        self.assertIn(item.source_url, html)
        self.assertIn("1 source", html)
        self.assertIn("Acme's $100 Million Refinancing", html)

    def test_v2_failure_exposes_the_rejecting_stage_without_approving_it(self):
        item = make_item()
        event = canonical_item_to_editorial_event(item)
        story = event["candidate"] | {
            "research_dossier": dossier_for(item),
            "editorial_event_id": event["event_id"],
            "editorial_format": "brief",
            "franchise": event["franchise"],
            "must_read_score": event["must_read_score"],
        }
        pipeline_instance = Mock()
        pipeline_instance.run.return_value = {
            "status": "review_required",
            "errors": [],
            "stages": {
                "post_revision_financial_review": {
                    "status": "completed",
                    "passed": False,
                    "issues": ["Unsupported leverage claim"],
                },
            },
        }
        with patch("v2_editorial.EditorialPipeline", return_value=pipeline_instance):
            with self.assertRaisesRegex(
                RuntimeError,
                "post_revision_financial_review: Unsupported leverage claim",
            ):
                generate_v2_article(
                    story,
                    api_key="key",
                    provider={"provider": "deepseek", "model": "deepseek-v4-pro"},
                )

    def test_v2_control_does_not_require_the_retired_legacy_ledger(self):
        import daily_news_agent

        findings = daily_news_agent._article_control_findings(
            {
                "title": "A specific capital-markets headline",
                "body_html": "<p>" + ("Source-grounded analysis. " * 40) + "</p>",
            },
            article_format="brief",
            require_narrative_ledger=False,
        )

        self.assertFalse(any("narrative-finance ledger" in finding for finding in findings))

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
