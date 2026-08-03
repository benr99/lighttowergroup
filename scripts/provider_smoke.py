#!/usr/bin/env python3
"""Bounded, secret-safe provider smoke test for release validation."""

from __future__ import annotations

import json
import re

from editorial_scoring import call_deepseek
from model_router import select_provider


def main() -> int:
    provider = select_provider(for_writing=True)
    raw = call_deepseek(
        'Return only this JSON object: {"ok": true, "contract": "insights-v2"}',
        provider["api_key"],
        max_tokens=64,
        temperature=0,
        json_mode=True,
        provider=provider,
        system="You are a JSON contract checker. Return JSON only.",
    )
    match = re.search(r"\{[\s\S]*\}", raw or "")
    if not match:
        raise RuntimeError("Provider smoke response did not contain JSON")
    payload = json.loads(match.group())
    if payload.get("ok") is not True or payload.get("contract") != "insights-v2":
        raise RuntimeError("Provider smoke response failed its contract")
    print(
        f"Provider smoke passed: {provider['provider']} "
        f"({provider['model']}) | JSON contract valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
