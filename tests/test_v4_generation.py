"""Offline proofs for the bounded v4 article writer."""

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
                           retrieved_text="A documented transaction occurred.",
                           retrieval_status=RetrievalStatus.FULL_TEXT)],
        eligible=True,
        selected=True,
        final_score=80,
    )
    obj.assess_evidence()
    obj.cap_depth_to_evidence("tier_b")
    return obj


def _article() -> dict:
    words = " ".join(f"evidence{i}" for i in range(450))
    return {
        "title": "A documented transaction closes",
        "excerpt": "A concise evidence-based summary.",
        "body_html": f"<p>{words}</p>",
        "format": "analysis",
        "sources": [{"name": "Source", "url": "https://source.example/story"}],
        "evidence_level": "single_source_full_text",
    }


class _Response:
    def __init__(self, payload: dict, status: int = 200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


PROVIDER = {
    "provider": "deepseek", "model": "deepseek-v4-pro", "api_key": "test-key",
    "url": "https://example.invalid/chat/completions",
}


class V4GenerationTests(unittest.TestCase):
    def test_one_valid_article_uses_one_direct_writer_request(self):
        response = _Response({"choices": [{"message": {"content": json.dumps(_article())},
                                             "finish_reason": "stop"}]})
        with patch.object(v4_generation.requests, "post", return_value=response) as post:
            result = v4_generation.write_one(_obj("One story"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertEqual(result.status, "completed")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result.stages_run, ["bounded_writer", "local_validation"])

    def test_v4_does_not_call_the_old_multi_stage_pipeline(self):
        response = _Response({"choices": [{"message": {"content": json.dumps(_article())},
                                             "finish_reason": "stop"}]})
        with patch.object(v4_generation.requests, "post", return_value=response), \
             patch("editorial_pipeline.run_editorial_pipeline", side_effect=AssertionError("old pipeline called")):
            result = v4_generation.write_one(_obj("No reviewers"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertTrue(result.ok)

    def test_permanent_http_error_is_not_retried(self):
        response = _Response({}, status=401)
        with patch.object(v4_generation.requests, "post", return_value=response) as post:
            result = v4_generation.write_one(_obj("Unauthorized"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertEqual(result.status, "failed")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(result.diagnostics["attempts"], 1)

    def test_transient_error_has_at_most_one_retry(self):
        import requests
        with patch.object(v4_generation.requests, "post", side_effect=requests.Timeout("slow")) as post:
            result = v4_generation.write_one(_obj("Slow story"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertEqual(result.status, "failed")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(result.diagnostics["attempts"], 2)

    def test_source_outside_dossier_fails_locally_without_retry(self):
        article = _article()
        article["sources"][0]["url"] = "https://invented.example/nope"
        response = _Response({"choices": [{"message": {"content": json.dumps(article)},
                                             "finish_reason": "stop"}]})
        with patch.object(v4_generation.requests, "post", return_value=response) as post:
            result = v4_generation.write_one(_obj("Bad source"), provider=PROVIDER,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertEqual(result.status, "failed")
        self.assertEqual(post.call_count, 1)
        self.assertIn("source_not_in_dossier", result.diagnostics["validation"]["codes"])

    def test_three_article_run_has_finite_attempts_and_preserves_successes(self):
        response = _Response({"choices": [{"message": {"content": json.dumps(_article())},
                                             "finish_reason": "stop"}]})
        with patch.object(v4_generation.requests, "post", return_value=response):
            results, report = v4_generation.write_all(
                [_obj(f"Story {i}") for i in range(3)], provider=PROVIDER,
                deadline_s=30, article_budget_s=10, verbose=False,
                state_dir=Path(tempfile.mkdtemp()), run_id="test-run",
            )
        self.assertEqual(len(results), 3)
        self.assertEqual(report.written, 3)
        self.assertEqual(report.attempts, 3)
        self.assertLessEqual(report.attempts, v4_generation.MAX_TOTAL_ATTEMPTS)

    def test_edition_deadline_stops_new_articles(self):
        with patch.object(v4_generation.requests, "post") as post:
            results, report = v4_generation.write_all(
                [_obj("First"), _obj("Second")], provider=PROVIDER,
                deadline_s=1, article_budget_s=4, verbose=False,
            )
        self.assertEqual(len(results), 2)
        self.assertEqual(report.skipped, 2)
        self.assertEqual(post.call_count, 0)


if __name__ == "__main__":
    unittest.main()
