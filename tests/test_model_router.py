"""Provider selection, diagnostics, and per-call fallback regression tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import editorial_scoring  # noqa: E402
import model_router  # noqa: E402


class _Response:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self) -> dict:
        return self._payload



def setUpModule():  # keep provider diagnostics out of the repository's .editorial-state
    model_router.configure_state_dir(Path(tempfile.mkdtemp()))


def tearDownModule():
    model_router.configure_state_dir(None)

class ProviderChain(unittest.TestCase):
    def test_diagnostics_can_follow_an_isolated_run_state_directory(self) -> None:
        original = model_router.STATE_DIR
        isolated = Path(tempfile.mkdtemp())
        try:
            model_router.configure_state_dir(isolated)
            model_router.log_provider_event("provider_call", provider="deepseek", outcome="success")
            self.assertTrue((isolated / "provider-log.jsonl").exists())
            self.assertEqual(model_router.PROVIDER_LOG_PATH.parent, isolated)
        finally:
            model_router.configure_state_dir(original)

    def test_deepseek_is_the_only_provider_by_default(self) -> None:
        with (
            patch.dict(model_router.os.environ, {}, clear=False),
            patch.object(model_router, "get_api_keys",
                         return_value={"deepseek": "deep-key", "openai": "open-key"}),
        ):
            model_router.os.environ.pop("LTG_PROVIDERS", None)
            chain = model_router.provider_chain(None, for_writing=True)
            self.assertIsNone(model_router.provider_config("openai", for_writing=True))
        self.assertEqual([entry["provider"] for entry in chain], ["deepseek"])

    def test_select_provider_retries_deepseek_then_names_it(self) -> None:
        health = [False, False, True]
        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": "k", "openai": "o"}),
            patch.object(model_router, "check_provider_health", side_effect=health) as probe,
            patch.object(model_router.time, "sleep"),
        ):
            model_router.os.environ.pop("LTG_PROVIDERS", None)
            provider = model_router.select_provider(for_writing=True)
        self.assertEqual(provider["provider"], "deepseek")
        self.assertEqual(probe.call_count, 3)
        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": "k", "openai": "o"}),
            patch.object(model_router, "check_provider_health", return_value=False),
            patch.object(model_router.time, "sleep"),
        ):
            with self.assertRaisesRegex(RuntimeError, "deepseek did not answer"):
                model_router.select_provider(for_writing=True)

    def test_configured_alternate_follows_preferred_provider(self) -> None:
        with (
            patch.dict(model_router.os.environ, {"LTG_PROVIDERS": "deepseek,openai"}),
            patch.object(
                model_router,
                "get_api_keys",
                return_value={"deepseek": "deep-key", "openai": "open-key"},
            ),
        ):
            chain = model_router.provider_chain(
                {
                    "provider": "deepseek",
                    "model": "deepseek-v4-pro",
                    "api_key": "deep-key",
                    "url": "https://api.deepseek.com/v1/chat/completions",
                },
                for_writing=True,
            )
        self.assertEqual([entry["provider"] for entry in chain], ["deepseek", "openai"])
        self.assertEqual(chain[1]["model"], model_router.OPENAI_MODEL_WRITING)

    def test_provider_events_never_persist_secrets(self) -> None:
        with patch("builtins.open") as opened:
            model_router.log_provider_event(
                "provider_call", provider="deepseek", api_key="do-not-write", outcome="failed"
            )
        written = opened.return_value.__enter__.return_value.write.call_args.args[0]
        self.assertNotIn("do-not-write", written)
        self.assertNotIn("api_key", written)


class PerCallFailover(unittest.TestCase):
    def test_long_deepseek_json_request_disables_hidden_thinking(self) -> None:
        success = {
            "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        }
        preferred = {
            "provider": "deepseek", "model": "deepseek-v4-pro", "api_key": "deep-key",
            "url": "https://api.deepseek.com/v1/chat/completions",
        }
        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": "deep-key", "openai": None}),
            patch.object(editorial_scoring.requests, "post", return_value=_Response(200, success)) as post,
        ):
            editorial_scoring.call_deepseek(
                "Return JSON", "deep-key", max_tokens=5000, json_mode=True, provider=preferred
            )
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["thinking"], {"type": "disabled"})

    def test_truncated_visible_content_is_rejected_and_logged(self) -> None:
        truncated = {
            "choices": [{
                "message": {"content": '{"partial": true}', "reasoning_content": "r" * 20},
                "finish_reason": "length",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 500},
        }
        preferred = {
            "provider": "deepseek", "model": "deepseek-v4-pro", "api_key": "deep-key",
            "url": "https://api.deepseek.com/v1/chat/completions",
        }
        with (
            patch.object(model_router, "get_api_keys", return_value={"deepseek": "deep-key", "openai": None}),
            patch.object(editorial_scoring.requests, "post", return_value=_Response(200, truncated)),
            patch.object(editorial_scoring.time, "sleep"),
            patch.object(model_router, "log_provider_event") as log,
        ):
            with self.assertRaisesRegex(RuntimeError, "provider_truncated"):
                editorial_scoring.call_deepseek("prompt", "deep-key", max_tokens=500, provider=preferred)
        self.assertTrue(any("provider_call" in call.args for call in log.call_args_list))

    def test_failed_primary_call_retries_then_uses_openai_when_opted_in(self) -> None:
        success = {
            "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        }
        responses = [_Response(503), _Response(503), _Response(200, success)]
        preferred = {
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "api_key": "deep-key",
            "url": "https://api.deepseek.com/v1/chat/completions",
        }
        with (
            patch.dict(model_router.os.environ, {"LTG_PROVIDERS": "deepseek,openai"}),
            patch.object(
                model_router,
                "get_api_keys",
                return_value={"deepseek": "deep-key", "openai": "open-key"},
            ),
            patch.object(editorial_scoring.requests, "post", side_effect=responses) as post,
            patch.object(editorial_scoring.time, "sleep"),
            patch.object(model_router, "log_provider_event") as log,
        ):
            result = editorial_scoring.call_deepseek(
                "Return JSON", "deep-key", max_tokens=500, json_mode=True, provider=preferred
            )
        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(post.call_count, 3)
        self.assertIn("api.deepseek.com", post.call_args_list[0].args[0])
        self.assertIn("api.openai.com", post.call_args_list[2].args[0])
        self.assertTrue(any(call.args[0] == "provider_switch" for call in log.call_args_list))

    def test_error_names_every_exhausted_provider(self) -> None:
        preferred = {
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "api_key": "deep-key",
            "url": "https://api.deepseek.com/v1/chat/completions",
        }
        with (
            patch.dict(model_router.os.environ, {"LTG_PROVIDERS": "deepseek,openai"}),
            patch.object(
                model_router,
                "get_api_keys",
                return_value={"deepseek": "deep-key", "openai": "open-key"},
            ),
            patch.object(editorial_scoring.requests, "post", return_value=_Response(503)),
            patch.object(editorial_scoring.time, "sleep"),
            patch.object(model_router, "log_provider_event"),
        ):
            with self.assertRaisesRegex(RuntimeError, "deepseek/.+openai/"):
                editorial_scoring.call_deepseek("prompt", "deep-key", provider=preferred)


if __name__ == "__main__":
    unittest.main()
