"""Model provider router with automatic fallback for Light Tower editorial pipeline."""

from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
STATE_DIR = SITE_ROOT / ".editorial-state"
PROVIDER_LOG_PATH = STATE_DIR / "provider-log.jsonl"
PRIMARY_HEALTH_PATH = STATE_DIR / "primary-health.json"

DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
OPENAI_MODEL_FALLBACK = os.environ.get("OPENAI_MODEL_FALLBACK", "gpt-4o-mini")
OPENAI_MODEL_WRITING = os.environ.get("OPENAI_MODEL_WRITING", "gpt-4o")


def get_api_keys() -> dict[str, str | None]:
    return {
        "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
    }


def check_provider_health(
    provider: str,
    api_key: str | None,
    model: str | None = None,
) -> bool:
    """Quick health check: call the provider with a minimal prompt."""
    if not api_key:
        return False
    try:
        if provider == "deepseek":
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model or DEEPSEEK_MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 4},
                timeout=15,
            )
            return resp.status_code == 200
        elif provider == "openai":
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model or OPENAI_MODEL_FALLBACK, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 4},
                timeout=15,
            )
            return resp.status_code == 200
    except Exception:
        return False
    return False


def select_provider(for_writing: bool = False) -> dict[str, Any]:
    """Select the best available provider. Returns {provider, model, api_key, url, fallback}."""
    keys = get_api_keys()

    # Check primary (DeepSeek)
    primary_ok = check_provider_health("deepseek", keys.get("deepseek"), DEEPSEEK_MODEL)
    if primary_ok:
        return {
            "provider": "deepseek",
            "model": DEEPSEEK_MODEL,
            "api_key": keys["deepseek"],
            "url": "https://api.deepseek.com/v1/chat/completions",
            "fallback": False,
            "purpose": "writing" if for_writing else "general",
        }

    # Try fallback (OpenAI)
    fallback_model = OPENAI_MODEL_WRITING if for_writing else OPENAI_MODEL_FALLBACK
    fallback_ok = check_provider_health("openai", keys.get("openai"), fallback_model)
    if fallback_ok:
        _log_provider_switch("deepseek -> openai", "primary unavailable")
        return {
            "provider": "openai",
            "model": fallback_model,
            "api_key": keys["openai"],
            "url": "https://api.openai.com/v1/chat/completions",
            "fallback": True,
            "purpose": "writing" if for_writing else "general",
        }

    raise RuntimeError("No LLM provider available. Both primary and fallback are down.")


def _log_provider_switch(reason: str, detail: str = ""):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "detail": detail,
    }) + "\n"
    with open(PROVIDER_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def primary_is_healthy() -> bool:
    keys = get_api_keys()
    if keys.get("deepseek"):
        return check_provider_health("deepseek", keys["deepseek"])
    # Check cached health
    try:
        data = json.loads(PRIMARY_HEALTH_PATH.read_text(encoding="utf-8"))
        return data.get("healthy", True)
    except (OSError, json.JSONDecodeError):
        return True


if __name__ == "__main__":
    result = select_provider()
    print(f"Provider: {result['provider']} ({result['model']}) | Fallback: {result['fallback']}")
