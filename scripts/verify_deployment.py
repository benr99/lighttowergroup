#!/usr/bin/env python3
"""Verify that the generated edition and article pages reached the live site."""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

SITE_ROOT = Path(__file__).resolve().parents[1]
LATEST_EDITION = SITE_ROOT / "latest-edition.json"


def _slugs(edition: dict[str, Any]) -> list[str]:
    records = []
    if edition.get("flagship"):
        records.append(edition["flagship"])
    records.extend(edition.get("briefs") or [])
    if edition.get("culture_signal"):
        records.append(edition["culture_signal"])
    if edition.get("data_note"):
        records.append(edition["data_note"])
    return [str(record.get("slug")) for record in records if record.get("slug")]


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def check_once(
    expected: dict[str, Any],
    *,
    base_url: str,
    release_sha: str,
    session: requests.Session | Any,
) -> tuple[bool, str]:
    cache_key = release_sha[:12] or str(int(time.time()))
    edition_url = f"{base_url.rstrip('/')}/latest-edition.json?release={cache_key}"
    try:
        response = session.get(
            edition_url,
            timeout=20,
            headers={"Cache-Control": "no-cache", "User-Agent": "LTG-Deploy-Verify/1.0"},
        )
        response.raise_for_status()
        live = response.json()
    except Exception as exc:  # noqa: BLE001
        return False, f"latest edition unavailable ({type(exc).__name__}: {exc})"

    for field in ("edition_date", "generated_at", "status"):
        if str(live.get(field) or "") != str(expected.get(field) or ""):
            return False, f"latest edition {field} has not reached the live site"
    expected_slugs = _slugs(expected)
    live_slugs = set(_slugs(live))
    missing = [slug for slug in expected_slugs if slug not in live_slugs]
    if missing:
        return False, f"latest edition is missing slugs: {', '.join(missing)}"

    expected_titles = {
        str(record.get("slug")): str(record.get("title") or "")
        for record in [
            *([expected["flagship"]] if expected.get("flagship") else []),
            *(expected.get("briefs") or []),
            *([expected["culture_signal"]] if expected.get("culture_signal") else []),
            *([expected["data_note"]] if expected.get("data_note") else []),
        ]
        if record.get("slug")
    }
    for slug in expected_slugs:
        try:
            page = session.get(
                f"{base_url.rstrip('/')}/insights/{slug}.html?release={cache_key}",
                timeout=20,
                headers={"Cache-Control": "no-cache", "User-Agent": "LTG-Deploy-Verify/1.0"},
            )
            page.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return False, f"article {slug} unavailable ({type(exc).__name__}: {exc})"
        title = _plain(expected_titles.get(slug, ""))
        if title and title.lower() not in _plain(page.text).lower():
            return False, f"article {slug} does not contain its expected title"
    return True, f"edition {expected.get('edition_date')} and {len(expected_slugs)} article(s) are live"


def verify(
    *,
    base_url: str,
    release_sha: str,
    timeout_seconds: int = 600,
    interval_seconds: int = 15,
    session: requests.Session | Any | None = None,
) -> tuple[bool, str]:
    expected = json.loads(LATEST_EDITION.read_text(encoding="utf-8"))
    session = session or requests.Session()
    deadline = time.monotonic() + max(0, timeout_seconds)
    last = "deployment was not checked"
    while True:
        ok, last = check_once(
            expected, base_url=base_url, release_sha=release_sha, session=session
        )
        if ok:
            return True, last
        if time.monotonic() >= deadline:
            return False, last
        time.sleep(max(1, interval_seconds))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://lighttowergroup.co")
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--interval-seconds", type=int, default=15)
    args = parser.parse_args()
    ok, message = verify(
        base_url=args.base_url,
        release_sha=args.release_sha,
        timeout_seconds=args.timeout_seconds,
        interval_seconds=args.interval_seconds,
    )
    print(("VERIFIED: " if ok else "NOT VERIFIED: ") + message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
