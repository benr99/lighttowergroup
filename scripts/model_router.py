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
DEFAULT_STATE_DIR = SITE_ROOT / ".editorial-state"
STATE_DIR = DEFAULT_STATE_DIR
PROVIDER_LOG_PATH = STATE_DIR / "provider-log.jsonl"
PRIMARY_HEALTH_PATH = STATE_DIR / "primary-health.json"

DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
OPENAI_MODEL_FALLBACK = os.environ.get("OPENAI_MODEL_FALLBACK", "gpt-4o-mini")
OPENAI_MODEL_WRITING = os.environ.get("OPENAI_MODEL_WRITING", "gpt-4o")


def configure_state_dir(path: str | Path | None = None) -> Path:
    """Route provider diagnostics alongside the current run's other state."""
    global STATE_DIR, PROVIDER_LOG_PATH, PRIMARY_HEALTH_PATH
    STATE_DIR = Path(path) if path is not None else DEFAULT_STATE_DIR
    PROVIDER_LOG_PATH = STATE_DIR / "provider-log.jsonl"
    PRIMARY_HEALTH_PATH = STATE_DIR / "primary-health.json"
    return STATE_DIR


def get_api_keys() -> dict[str, str | None]:
    return {
        "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
    }


def provider_config(provider: str, *, for_writing: bool = False) -> dict[str, Any] | None:
    """Build a secret-bearing provider config from the current environment."""
    keys = get_api_keys()
    if provider == "deepseek" and keys.get("deepseek"):
        return {
            "provider": "deepseek",
            "model": DEEPSEEK_MODEL,
            "api_key": keys["deepseek"],
            "url": "https://api.deepseek.com/v1/chat/completions",
            "fallback": False,
            "purpose": "writing" if for_writing else "general",
        }
    if provider == "openai" and keys.get("openai"):
        return {
            "provider": "openai",
            "model": OPENAI_MODEL_WRITING if for_writing else OPENAI_MODEL_FALLBACK,
            "api_key": keys["openai"],
            "url": "https://api.openai.com/v1/chat/completions",
            "fallback": True,
            "purpose": "writing" if for_writing else "general",
        }
    return None


def provider_chain(
    preferred: dict[str, Any] | None = None,
    *,
    for_writing: bool = False,
) -> list[dict[str, Any]]:
    """Return the preferred provider followed by any configured alternate.

    This deliberately performs no health probe. It is used after a real model
    call fails, where another preflight request would add latency without
    proving the actual prompt can complete.
    """
    chain: list[dict[str, Any]] = []
    if preferred and preferred.get("api_key"):
        chain.append(dict(preferred))
    for name in ("deepseek", "openai"):
        candidate = provider_config(name, for_writing=for_writing)
        if candidate is None:
            continue
        if any(
            existing.get("provider") == candidate["provider"]
            and existing.get("model") == candidate["model"]
            for existing in chain
        ):
            continue
        chain.append(candidate)
    return chain


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
        return provider_config("deepseek", for_writing=for_writing) or {}

    # Try fallback (OpenAI)
    fallback_model = OPENAI_MODEL_WRITING if for_writing else OPENAI_MODEL_FALLBACK
    fallback_ok = check_provider_health("openai", keys.get("openai"), fallback_model)
    if fallback_ok:
        _log_provider_switch("deepseek -> openai", "primary unavailable")
        return provider_config("openai", for_writing=for_writing) or {}

    raise RuntimeError("No LLM provider available. Both primary and fallback are down.")


def log_provider_event(event: str, **fields: Any) -> None:
    """Append one secret-free provider event for post-run diagnostics."""
    safe = {
        key: value for key, value in fields.items()
        if key not in {"api_key", "authorization", "headers"}
    }
    safe["event"] = event
    safe["timestamp"] = datetime.now(timezone.utc).isoformat()
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if PROVIDER_LOG_PATH.exists() and PROVIDER_LOG_PATH.stat().st_size > 512_000:
            retained = PROVIDER_LOG_PATH.read_text(encoding="utf-8").splitlines()[-1000:]
            PROVIDER_LOG_PATH.write_text("\n".join(retained) + "\n", encoding="utf-8")
        with open(PROVIDER_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _log_provider_switch(reason: str, detail: str = "") -> None:
    log_provider_event("provider_switch", reason=reason, detail=detail)


def provider_summary(*, since: str = "") -> dict[str, Any]:
    """Summarize provider events for the current run without exposing prompts."""
    events: list[dict[str, Any]] = []
    try:
        lines = PROVIDER_LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines[-2000:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since and str(event.get("timestamp") or "") < since:
            continue
        events.append(event)
    calls = [event for event in events if event.get("event") == "provider_call"]
    providers = sorted({
        str(event.get("provider")) for event in calls if event.get("provider")
    })
    return {
        "calls": len(calls),
        "successful_calls": sum(event.get("outcome") == "success" for event in calls),
        "failed_provider_attempts": sum(event.get("outcome") == "failed" for event in calls),
        "fallback_calls": sum(
            event.get("outcome") == "success" and bool(event.get("fallback"))
            for event in calls
        ),
        "switches": sum(event.get("event") == "provider_switch" for event in events),
        "providers_used": providers,
    }


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
