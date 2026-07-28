#!/usr/bin/env python3
"""Client signal digest: monitors data sources for signals matching client situations.

Runs Monday/Wednesday/Friday. Filters the same data pool for refinancing windows,
distress events, and capital events relevant to known client profiles.
Output is a private markdown digest emailed to Ben — never published publicly.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
STATE_DIR = SITE_ROOT / ".editorial-state"
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
CLIENT_WATCHLIST_PATH = SITE_ROOT / "data" / "client-watchlist.json"
DIGEST_DIR = SITE_ROOT / "data" / "client-digests"

CLIENT_WATCHLIST_DEFAULT = {
    "schema_version": 1,
    "markets": ["new york", "brooklyn", "manhattan", "queens", "bronx", "long island city", "williamsburg", "downtown brooklyn", "harlem", "midtown", "jersey city", "newark"],
    "asset_classes": ["multifamily", "office", "industrial", "retail", "mixed-use", "hotel", "data center"],
    "signal_types": ["refinancing_window", "distress_event", "capital_event", "policy_change", "lender_activity"],
    "update_frequency": "MWF",
    "note": "Edit this file to match current client situations. Add specific addresses, loan amounts, or timelines."
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_client_watchlist() -> dict[str, Any]:
    data = load_json(CLIENT_WATCHLIST_PATH)
    if not isinstance(data, dict) or not data.get("markets"):
        CLIENT_WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLIENT_WATCHLIST_PATH.write_text(json.dumps(CLIENT_WATCHLIST_DEFAULT, indent=2), encoding="utf-8")
        return CLIENT_WATCHLIST_DEFAULT
    return data


def scan_recent_runs(watchlist: dict[str, Any], days: int = 3) -> list[dict[str, Any]]:
    """Scan recent editorial runs for client-relevant signals."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    signals = []
    markets_of_interest = [m.lower() for m in watchlist.get("markets", [])]
    assets_of_interest = [a.lower() for a in watchlist.get("asset_classes", [])]

    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.json"), reverse=True)[:5]:
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            candidates = data.get("scored_candidates") or data.get("selected_stories") or []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                candidate = item.get("candidate", item)
                title = str(candidate.get("title", "")).lower()
                summary = str(candidate.get("summary", "")).lower()
                text = f"{title} {summary}"
                entities = candidate.get("entities", {})

                matched_markets = [m for m in markets_of_interest if m in text]
                matched_assets = [a for a in assets_of_interest if a in text]

                if not matched_markets and not matched_assets:
                    continue

                signal_type = "capital_event"
                if any(kw in text for kw in ["refinanc", "maturity", "expiring", "extension"]):
                    signal_type = "refinancing_window"
                if any(kw in text for kw in ["distress", "default", "foreclosure", "special servicing"]):
                    signal_type = "distress_event"
                if any(kw in text for kw in ["fed", "regulation", "zoning", "legislation", "rate"]):
                    signal_type = "policy_change"

                signals.append({
                    "title": candidate.get("title", "Untitled"),
                    "source": candidate.get("source", ""),
                    "source_url": candidate.get("url", ""),
                    "signal_type": signal_type,
                    "matched_markets": matched_markets,
                    "matched_assets": matched_assets,
                    "published": candidate.get("published", ""),
                    "implication": f"Signal: {signal_type.replace('_', ' ')} in {', '.join(matched_markets[:3] or matched_assets[:3])}",
                })

    return signals


def generate_digest(signals: list[dict[str, Any]], watchlist: dict[str, Any]) -> str:
    lines = [
        f"# Light Tower Client Signal Digest",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Watching:** {', '.join(watchlist.get('markets', [])[:8])}",
        f"**Signal types:** {', '.join(watchlist.get('signal_types', []))}",
        "",
        "---",
        "",
    ]

    if not signals:
        lines.append("No client-relevant signals detected in the past 3 days.")
        return "\n".join(lines)

    by_type: dict[str, list[dict[str, Any]]] = {}
    for s in signals:
        by_type.setdefault(s["signal_type"], []).append(s)

    for sig_type, items in by_type.items():
        emoji = {"refinancing_window": "\U0001f504", "distress_event": "\u26a0\ufe0f", "capital_event": "\U0001f4b0", "policy_change": "\U0001f4cb", "lender_activity": "\U0001f3e6"}.get(sig_type, "\U0001f4cc")
        lines.append(f"## {emoji} {sig_type.replace('_', ' ').title()} ({len(items)})")
        lines.append("")
        for item in items[:5]:
            lines.append(f"- **{item['title'][:100]}**")
            lines.append(f"  Source: {item['source']} | {item['implication']}")
            if item.get("source_url"):
                lines.append(f"  {item['source_url']}")
            lines.append("")
        if len(items) > 5:
            lines.append(f"  *...and {len(items) - 5} more*")
            lines.append("")

    lines.append("---")
    lines.append("*This digest is for internal client intelligence. Do not forward without review.*")
    return "\n".join(lines)


def main():
    today = datetime.now(timezone.utc).date()
    watchlist = load_client_watchlist()
    signals = scan_recent_runs(watchlist, days=3)

    digest = generate_digest(signals, watchlist)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    digest_path = DIGEST_DIR / f"{today.isoformat()}.md"
    digest_path.write_text(digest, encoding="utf-8")
    print(f"Client signal digest saved: {digest_path.relative_to(SITE_ROOT)}")
    print(f"Signals found: {len(signals)}")
    for s in signals[:3]:
        print(f"  [{s['signal_type']}] {s['title'][:70]}")


if __name__ == "__main__":
    main()
