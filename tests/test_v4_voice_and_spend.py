"""Offline proofs for the writer's spending cap, outage handling and Ben's voice path."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import v4_generation  # noqa: E402
from test_v4_generation import (  # noqa: E402
    FACTS, GROUPS, PROVIDER, FakeVerifier, _Response, _draft, _obj, _ok,
)


def _usage(draft: dict) -> _Response:
    response = _ok(draft)
    response.payload["usage"] = {"prompt_tokens": 100_000, "completion_tokens": 50_000}
    return response


def _budget(daily: float):
    from budget import Budget
    return Budget(daily_usd=daily, per_article_usd=10.0,
                  ledger_path=Path(tempfile.mkdtemp()) / "spend.json", config={})


class SpendAndOutageTests(unittest.TestCase):
    def test_spend_is_recorded_and_reported(self):
        budget = _budget(25.0)
        with patch.object(v4_generation.requests, "post", return_value=_usage(_draft())):
            _, report = v4_generation.write_all([_obj("Paid story")], provider=PROVIDER, budget=budget,
                                                deadline_s=30, article_budget_s=10, verbose=False,
                                                verifier=FakeVerifier())
        self.assertEqual(report.written, 1)
        self.assertGreater(budget.session_usd, 0)
        self.assertEqual(report.spend_usd, round(budget.session_usd, 4))

    def test_exhausted_budget_skips_stories_without_calling_the_model(self):
        with patch.object(v4_generation.requests, "post") as post:
            results, report = v4_generation.write_all([_obj("One"), _obj("Two")], provider=PROVIDER,
                                                      budget=_budget(0.0), deadline_s=30, article_budget_s=10,
                                                      verbose=False, verifier=FakeVerifier())
        self.assertEqual(post.call_count, 0)
        self.assertEqual(report.skipped, 2)
        self.assertIn("budget", report.stop_reason)
        self.assertTrue(all("budget" in r.skipped_reason for r in results))

    def test_budget_reached_mid_story_skips_it_rather_than_failing(self):
        budget = _budget(25.0)
        with (patch.object(budget, "allow", side_effect=[True, False, False, False]),
              patch.object(v4_generation.requests, "post", return_value=_ok(_draft()))):
            result = v4_generation.write_one(_obj("Half paid"), provider=PROVIDER, budget=budget,
                                             deadline=v4_generation.time.monotonic() + 30)
        self.assertEqual(result.status, "skipped")
        self.assertIn("budget", result.skipped_reason)

    def test_persistent_outage_stops_new_stories(self):
        stories = [_obj(f"Outage {i}") for i in range(6)]
        with (patch.object(v4_generation.requests, "post", return_value=_Response({}, status=503)) as post,
              patch.object(v4_generation.time, "sleep")):
            _, report = v4_generation.write_all(stories, provider=PROVIDER, deadline_s=60,
                                                article_budget_s=20, workers=1, verbose=False,
                                                verifier=FakeVerifier())
        self.assertIn("DeepSeek unavailable", report.stop_reason)
        self.assertEqual(report.failed + report.skipped, 6)
        self.assertGreaterEqual(report.skipped, 3)
        self.assertLessEqual(post.call_count,
                             v4_generation.OUTAGE_THRESHOLD * len(v4_generation.REQUEST_RETRY_PAUSES))

    def test_unauthorised_key_stops_the_day_at_once(self):
        with patch.object(v4_generation.requests, "post", return_value=_Response({}, status=401)) as post:
            _, report = v4_generation.write_all([_obj("A"), _obj("B"), _obj("C")], provider=PROVIDER,
                                                deadline_s=30, article_budget_s=10, workers=1,
                                                verbose=False, verifier=FakeVerifier())
        self.assertEqual(post.call_count, 1)
        self.assertEqual((report.failed, report.skipped), (1, 2))

    def test_verifier_is_deepseek_only(self):
        import model_router
        with (patch.object(model_router, "get_api_keys", return_value={"deepseek": "k", "openai": "o"}),
              patch.object(v4_generation.requests, "post",
                           return_value=_Response({"choices": [{"message": {"content": "{}"},
                                                                "finish_reason": "stop"}]})) as post):
            check = v4_generation._make_verifier(PROVIDER)
            check("system", "user")
        self.assertIn("deepseek", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["json"]["thinking"], {"type": "enabled"})


BRIEF = {"protagonist": "Harbor Capital", "tension": "none", "shape": "The Price Tells the Truth",
         "lens": "capital cycle", "hooks": [{"text": FACTS[0], "quote": FACTS[0]}], "headlines": ["x"],
         "pick": {"hook": 0, "headline": 0, "why": "x"}}
FAIR_TAKE = "I read this as a lender at ease with a familiar borrower."
UNFOUNDED_TAKE = "Harbor Capital wants to sell Pier House soon, I think."


def _voice_draft(*, thin: bool = False) -> dict:
    counter = iter(range(1, 100))

    def fact(i: int) -> dict:
        return {"id": f"s{next(counter)}", "kind": "fact", "text": FACTS[i], "quotes": [FACTS[i]]}

    groups = [[0, 1], [2, 3]] if thin else GROUPS
    paragraphs = [{"role": "detail", "sentences": [fact(i) for i in g]} for g in groups]
    if not thin:
        last = paragraphs[-1]["sentences"][-1]["id"]  # Meridian Bank has lent to Harbor Capital before
        paragraphs.append({"role": "meaning", "sentences": [
            {"id": "t1", "kind": "take", "text": FAIR_TAKE, "because": [last]},
            {"id": "t2", "kind": "take", "text": UNFOUNDED_TAKE, "because": [last]},
        ]})
        paragraphs.append({"role": "kicker", "sentences": [
            {"id": "v1", "kind": "voice", "text": "Not a bad week to be a borrower."}]})
    return {"title": "Harbor Capital closes $50 million Pier House loan",
            "title_quote": "Harbor Capital closed a $50 million loan on Pier House",
            "excerpt": "Harbor Capital closed a $50 million loan on Pier House, a 120-unit building in Brooklyn.",
            "excerpt_quote": FACTS[0], "paragraphs": paragraphs}


def _write_voiced(name: str, responses: list, **kwargs):
    with patch.object(v4_generation.requests, "post", side_effect=responses) as post:
        result = v4_generation.write_one(_obj(name), provider=PROVIDER, voice=True,
                                         deadline=v4_generation.time.monotonic() + 60,
                                         verifier=FakeVerifier(), **kwargs)
    return result, post


class VoicePathTests(unittest.TestCase):
    def test_voice_keeps_facts_and_a_fair_take_and_deletes_an_unfounded_one(self):
        result, post = _write_voiced("Voiced", [_ok(BRIEF), _ok(_voice_draft()), _ok(_voice_draft())])
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.article["voice"], "ben")
        self.assertIn("voice_gate", result.stages_run)
        body = result.article["body_html"]
        self.assertIn("I read this as a lender at ease", body)
        self.assertNotIn("wants to sell", body)
        self.assertIn("Harbor Capital closed a $50 million loan", body)
        self.assertTrue(any("private state" in r for r in result.diagnostics["sentences_rejected_by_fact_check"]))
        self.assertEqual(post.call_args_list[0].kwargs["json"]["temperature"], v4_generation.VOICE_TEMPERATURE)

    def test_voice_evidence_records_every_sentence_kind(self):
        state = Path(tempfile.mkdtemp())
        result, _ = _write_voiced("Evidence", [_ok(BRIEF), _ok(_voice_draft()), _ok(_voice_draft())],
                                  state_dir=state, run_id="r")
        import json
        evidence = json.loads(next((state / "v4-evidence").glob("*.json")).read_text(encoding="utf-8"))
        kinds = {item["kind"] for para in evidence["paragraphs"] for item in para}
        self.assertEqual(evidence["mode"], "voice")
        self.assertIn("take", kinds)
        self.assertTrue(any(r["kind"] == "take" for r in evidence["rejected"]))

    def test_voice_falls_back_to_the_facts_writer_when_too_little_survives(self):
        thin = _voice_draft(thin=True)
        result, _ = _write_voiced("Fallback", [_ok(BRIEF), _ok(thin), _ok(thin), _ok(_draft())])
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.article["voice"], "facts")
        self.assertTrue(result.diagnostics.get("voice_fallback"))

    def test_voice_is_off_unless_switched_on(self):
        with patch.dict(v4_generation.os.environ, {"INSIGHTS_VOICE": "off"}):
            self.assertFalse(v4_generation.voice_enabled())
        with patch.dict(v4_generation.os.environ, {"INSIGHTS_VOICE": "on"}):
            self.assertTrue(v4_generation.voice_enabled())

    def test_briefs_never_use_the_voice_path(self):
        obj = _obj("Brief story")
        obj.recommended_depth = "tier_c"
        with patch.object(v4_generation.requests, "post", side_effect=[_ok(_draft())]):
            result = v4_generation.write_one(obj, provider=PROVIDER, voice=True,
                                             deadline=v4_generation.time.monotonic() + 30,
                                             verifier=FakeVerifier())
        self.assertEqual(result.article["voice"], "facts")


if __name__ == "__main__":
    unittest.main()
