"""Offline proofs for the bounded, fact-checked v4 article writer."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intelligence_object import IntelligenceObject, RetrievalStatus, SourceRef  # noqa: E402
import v4_generation  # noqa: E402

FACTS = [
    "Harbor Capital closed a $50 million loan on Pier House, a 120-unit apartment building in Brooklyn.",
    "Meridian Bank provided the three-year floating-rate loan.",
    "This loan replaces a $38 million construction loan from 2023.",
    "Occupancy reached 92% in June, the sponsor said.",
    "Harbor Capital did not disclose the interest rate.",
    "Pier House opened in 2025 and has 24 income-restricted units.",
    "Walker Advisors arranged the financing.",
    "Its ground floor includes 8,000 square feet of retail.",
    "Meridian Bank said it expects to keep the loan on its balance sheet.",
    "Pier House sits two blocks from the Atlantic Avenue subway station.",
    "Harbor Capital bought the site in 2021 from a local family.",
    "A rooftop deck and a bike room are included.",
    "Residents began moving in during March.",
    "Meridian Bank has lent to Harbor Capital on two earlier projects.",
]
SOURCE = " ".join(FACTS)
GROUPS = [[0, 1], [2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12, 13]]
VIEW = "Our read: the borrower likely wanted time to lease up before a long-term loan."
ACTION = "Ask your lender what it would take to refinance construction debt on similar terms."


def _obj(name: str) -> IntelligenceObject:
    obj = IntelligenceObject(
        object_id=name.lower().replace(" ", "-"),
        cluster_id=name,
        primary_sector="commercial_real_estate",
        title=name,
        what_happened="A documented transaction occurred.",
        sources=[SourceRef(item_id="source-1", source_name="Source",
                           canonical_url="https://source.example/story",
                           source_tier=1, text_chars=5000,
                           retrieved_text=SOURCE,
                           retrieval_status=RetrievalStatus.FULL_TEXT)],
        eligible=True,
        selected=True,
        final_score=80,
    )
    obj.assess_evidence()
    obj.cap_depth_to_evidence("tier_b")
    return obj


def _fact(text: str) -> dict:
    return {"text": text, "kind": "fact", "quotes": [text]}


def _draft() -> dict:
    paragraphs = [[_fact(FACTS[i]) for i in group] for group in GROUPS]
    return {
        "title": "Harbor Capital closes $50 million Pier House loan",
        "title_quote": "Harbor Capital closed a $50 million loan on Pier House",
        "excerpt": "Harbor Capital closed a $50 million loan on Pier House, a 120-unit building in Brooklyn.",
        "excerpt_quote": FACTS[0],
        "paragraphs": paragraphs,
    }


class FakeVerifier:
    """Stands in for the second model. Supports everything unless told otherwise."""

    def __init__(self, reject: tuple[str, ...] = (), error: Exception | None = None):
        self.reject, self.error, self.calls, self.used = reject, error, 0, "fake/verifier"

    def __call__(self, system: str, user: str) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        atomic = "SENTENCES TO CHECK:" not in user
        block = (user.split("SENTENCES:")[1].split("For each sentence:")[0] if atomic
                 else user.split("SENTENCES TO CHECK:")[1].split("Rules by kind:")[0])
        results = []
        for item in json.loads(block):
            bad = any(marker in item["sentence"] for marker in self.reject)
            row = {"id": item["id"], "verdict": "unsupported" if bad else "supported",
                   "issue": "not in the source" if bad else ""}
            if atomic:
                row["claims"] = [{"claim": item["sentence"], "supported": not bad}]
            results.append(row)
        return json.dumps({"results": results})


class _Response:
    def __init__(self, payload: dict, status: int = 200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


def _ok(draft: dict) -> _Response:
    return _Response({"choices": [{"message": {"content": json.dumps(draft)}, "finish_reason": "stop"}]})


PROVIDER = {
    "provider": "deepseek", "model": "deepseek-v4-pro", "api_key": "test-key",
    "url": "https://example.invalid/chat/completions",
}


def _write(name="One story", *, responses, verifier=None, **kwargs):
    verifier = verifier or FakeVerifier()
    with patch.object(v4_generation.requests, "post", side_effect=responses) as post:
        result = v4_generation.write_one(
            _obj(name), provider=PROVIDER, deadline=v4_generation.time.monotonic() + 30,
            verifier=verifier, **kwargs)
    return result, post, verifier


class V4GenerationTests(unittest.TestCase):
    def test_verified_draft_is_assembled_from_checked_sentences(self):
        result, post, verifier = _write(responses=[_ok(_draft())])
        self.assertEqual(result.status, "completed")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(verifier.calls, 4)  # 16 items in chunks of 8, two differently framed passes
        self.assertEqual(result.stages_run, ["bounded_writer", "fact_check", "local_validation"])
        article = result.article
        self.assertTrue(article["fact_checked"])
        self.assertEqual(article["title"], "Harbor Capital closes $50 million Pier House loan")
        self.assertEqual(article["sources"], [{"name": "Source", "url": "https://source.example/story"}])
        self.assertIn("<p>Harbor Capital closed a $50 million loan", article["body_html"])
        self.assertNotIn("Our read", article["body_html"])
        self.assertEqual(result.diagnostics["fact_check"]["rejected"], 0)

    def test_v4_does_not_call_the_old_multi_stage_pipeline(self):
        with patch("editorial_pipeline.run_editorial_pipeline", side_effect=AssertionError("old pipeline called")):
            result, _, _ = _write("No reviewers", responses=[_ok(_draft())])
        self.assertTrue(result.ok)

    def test_permanent_http_error_is_not_retried(self):
        result, post, _ = _write("Unauthorized", responses=[_Response({}, status=401)])
        self.assertEqual(result.status, "failed")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result.diagnostics["attempts"], 1)

    def test_transient_error_has_at_most_one_retry(self):
        import requests
        result, post, _ = _write("Slow story", responses=requests.Timeout("slow"))
        self.assertEqual(result.status, "failed")
        self.assertEqual(post.call_count, 2)

    def test_invented_quote_is_dropped_and_a_rewrite_requested(self):
        bad = _draft()
        bad["paragraphs"][0].append({"text": "Meridian Bank guaranteed the loan.", "kind": "fact",
                                     "quotes": ["Meridian Bank guaranteed the entire loan balance."]})
        result, post, _ = _write(responses=[_ok(bad), _ok(_draft())])
        self.assertEqual(result.status, "completed")
        self.assertEqual(post.call_count, 2)
        retry_prompt = post.call_args_list[1].kwargs["json"]["messages"][1]["content"]
        self.assertIn("quote not found verbatim", retry_prompt)
        self.assertNotIn("guaranteed", result.article["body_html"])

    def test_figure_missing_from_its_quote_is_removed_even_if_the_rewrite_repeats_it(self):
        bad = _draft()
        bad["paragraphs"][0].append({"text": "That is a $75 million loan.", "kind": "fact", "quotes": [FACTS[0]]})
        result, post, _ = _write(responses=[_ok(bad), _ok(bad)])
        self.assertEqual(result.status, "completed")
        self.assertNotIn("75", result.article["body_html"])
        self.assertTrue(any("figures not in its quote" in r
                            for r in result.diagnostics["sentences_rejected_by_fact_check"]))

    def test_opinions_and_closing_advice_are_never_published(self):
        draft = _draft()
        draft["paragraphs"].append([{"text": VIEW, "kind": "view", "quotes": []}])
        draft["paragraphs"].append([{"text": ACTION, "kind": "action", "quotes": []}])
        result, post, _ = _write(responses=[_ok(draft), _ok(draft)])
        self.assertEqual(result.status, "completed")
        self.assertNotIn("lease up", result.article["body_html"])
        self.assertNotIn("Ask your lender", result.article["body_html"])
        self.assertTrue(any("only sentences backed by a source quote" in r
                            for r in result.diagnostics["sentences_rejected_by_fact_check"]))

    def test_a_sentence_that_drops_its_quotes_qualifier_or_attribution_is_removed(self):
        draft = _draft()
        quote = "Meridian Bank said it expects to keep the loan on its balance sheet."
        draft["paragraphs"][0].append({"text": "Meridian Bank will keep the loan on its balance sheet.",
                                       "kind": "fact", "quotes": [quote]})
        result, _, _ = _write(responses=[_ok(draft), _ok(draft)])
        self.assertNotIn("will keep", result.article["body_html"])
        reasons = " ".join(result.diagnostics["sentences_rejected_by_fact_check"])
        self.assertIn("drops the qualifier", reasons)

    def test_second_model_veto_removes_a_sentence(self):
        result, _, _ = _write(responses=[_ok(_draft()), _ok(_draft())], verifier=FakeVerifier(reject=("Occupancy",)))
        self.assertEqual(result.status, "completed")
        self.assertNotIn("Occupancy", result.article["body_html"])
        self.assertIn("Walker Advisors", result.article["body_html"])

    def test_story_with_too_little_verified_text_is_withheld_not_failed(self):
        thin = _draft()
        thin["paragraphs"] = [[_fact(FACTS[0]), _fact(FACTS[1])]]
        result, post, _ = _write(responses=[_ok(thin), _ok(thin)])
        self.assertEqual(result.status, "withheld")
        self.assertIsNone(result.article)
        self.assertFalse(result.ok)
        with patch.object(v4_generation.requests, "post", side_effect=[_ok(thin), _ok(thin)]):
            results, report = v4_generation.write_all([_obj("Thin story")], provider=PROVIDER,
                                                      deadline_s=30, article_budget_s=10,
                                                      verbose=False, verifier=FakeVerifier())
        self.assertEqual((report.withheld, report.failed, report.written), (1, 0, 0))

    def test_fact_check_unavailable_fails_closed(self):
        verifier = FakeVerifier(error=RuntimeError("fact-check unavailable: down"))
        result, _, _ = _write(responses=[_ok(_draft()), _ok(_draft())], verifier=verifier)
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.article)
        self.assertEqual(result.diagnostics["error_kind"], "verifier")

    def test_unsupported_title_falls_back_to_the_story_title(self):
        draft = _draft()
        draft["title"] = "Harbor Capital closes $99 million Pier House loan"
        result, _, _ = _write("Plain story title", responses=[_ok(draft), _ok(draft)])
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.article["title"], "Plain story title")

    def test_hard_to_read_layout_gets_one_rewrite_and_still_ships_if_it_fails(self):
        wall = _draft()
        wall["paragraphs"] = [[_fact(t) for t in FACTS]] + wall["paragraphs"][-2:]
        result, post, _ = _write(responses=[_ok(wall), _ok(_draft())])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(result.diagnostics["readability_warnings"], [])
        import requests
        result, post, _ = _write(responses=[_ok(wall), requests.Timeout("slow")])
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.diagnostics["readability_warnings"])

    def test_three_article_run_has_finite_attempts_and_preserves_successes(self):
        with patch.object(v4_generation.requests, "post", return_value=_ok(_draft())):
            results, report = v4_generation.write_all(
                [_obj(f"Story {i}") for i in range(3)], provider=PROVIDER,
                deadline_s=30, article_budget_s=10, verbose=False,
                state_dir=Path(tempfile.mkdtemp()), run_id="test-run", verifier=FakeVerifier(),
            )
        self.assertEqual(len(results), 3)
        self.assertEqual(report.written, 3)
        self.assertEqual(report.attempts, 3)
        self.assertLessEqual(report.attempts, v4_generation.MAX_TOTAL_ATTEMPTS)

    def test_edition_deadline_stops_new_articles(self):
        with patch.object(v4_generation.requests, "post") as post:
            results, report = v4_generation.write_all(
                [_obj("First"), _obj("Second")], provider=PROVIDER,
                deadline_s=1, article_budget_s=4, verbose=False, verifier=FakeVerifier(),
            )
        self.assertEqual(len(results), 2)
        self.assertEqual(report.skipped, 2)
        self.assertEqual(post.call_count, 0)

    def test_checked_article_is_reused_from_cache_and_evidence_is_written(self):
        state = Path(tempfile.mkdtemp())
        with patch.object(v4_generation.requests, "post", return_value=_ok(_draft())) as post:
            first = v4_generation.write_one(_obj("Reusable story"), provider=PROVIDER,
                                            deadline=v4_generation.time.monotonic() + 30,
                                            state_dir=state, run_id="first", verifier=FakeVerifier())
            second = v4_generation.write_one(_obj("Reusable story"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30,
                                             state_dir=state, run_id="second", verifier=FakeVerifier())
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertTrue(second.diagnostics["cache_reused"])
        self.assertEqual(post.call_count, 1)
        evidence = json.loads(next((state / "v4-evidence").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(evidence["verifier"], "fake/verifier")
        self.assertTrue(evidence["paragraphs"][0][0]["quotes"])

    def test_cached_article_without_the_fact_check_stamp_is_not_reused(self):
        import hashlib
        state = Path(tempfile.mkdtemp())
        obj = _obj("Legacy cache")
        cache = v4_generation._cache_path(state, obj.object_id)
        cache.parent.mkdir(parents=True)
        dossier = v4_generation._safe_dossier(obj)
        digest = hashlib.sha256(json.dumps(dossier, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        cache.write_text(json.dumps({"dossier_hash": digest, "depth": obj.recommended_depth,
                                     "prompt_version": v4_generation.WRITER_PROMPT_VERSION,
                                     "article": {"title": "Old", "excerpt": "Old.", "body_html": "<p>x</p>"}}),
                         encoding="utf-8")
        with patch.object(v4_generation.requests, "post", return_value=_ok(_draft())) as post:
            result = v4_generation.write_one(obj, provider=PROVIDER, state_dir=state,
                                             deadline=v4_generation.time.monotonic() + 30,
                                             verifier=FakeVerifier())
        self.assertEqual(post.call_count, 1)
        self.assertTrue(result.article["fact_checked"])

    def test_validation_rejects_non_paragraph_html_and_wrong_sources(self):
        dossier = v4_generation.object_to_dossier(_obj("Structure"))
        article = {"title": "T", "excerpt": "An excerpt.", "format": "analysis",
                   "body_html": "<div>" + "word " * 200 + "</div>",
                   "sources": [{"name": "X", "url": "https://invented.example/nope"}]}
        validation = v4_generation.validate_article(article, dossier, v4_generation.DEPTH_SPEC["tier_b"])
        self.assertIn("invalid_html", validation.codes)
        self.assertIn("source_not_in_dossier", validation.codes)


if __name__ == "__main__":
    unittest.main()
