"""Diagnose every configured feed and report why it does or does not deliver.

The production ingester reports only "empty" for a feed that yields nothing,
which conflates a dead URL, a redirect, a blocked bot, a parser mismatch and a
genuinely quiet publication. Those need different responses, so this probes each
source directly and classifies the outcome.

Read-only with respect to config: it never edits config/sources.json. Writes a
single JSON report and exits non-zero when usable coverage falls below
--min-healthy-pct, so it can gate a scheduled health check.

    python scripts/source_health_probe.py --out .editorial-state/source-probe.json
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

SITE_ROOT = Path(__file__).resolve().parents[1]
UA = "LightTowerGroup-NewsAgent/2.0 (+https://lighttowergroup.co)"
USABLE_STATUSES = frozenset({"healthy", "quiet_but_healthy", "healthy_no_dates"})


def classify(source: dict, lookback_hours: int) -> dict:
    url = source.get("url", "")
    row = {
        "name": source.get("name"),
        "url": url,
        "domain": "",
        "tier": source.get("tier"),
        "sectors": source.get("sectors") or [],
        "source_type": source.get("source_type"),
        "geographic_scope": source.get("geographic_scope"),
        "verified_flag": source.get("verified"),
        "http_status": None,
        "final_url": None,
        "redirected": False,
        "content_type": None,
        "latency_ms": None,
        "entries_total": 0,
        "entries_in_window": 0,
        "newest_age_hours": None,
        "bozo": False,
        "bozo_reason": "",
        "status": "unknown",
        "action": "",
    }
    if not url or url == "newsapi.org":
        row["status"] = "not_a_feed"
        row["action"] = "n/a - discovery query, not an RSS source"
        return row

    row["domain"] = url.split("/")[2] if "://" in url else url
    started = time.perf_counter()
    body = None
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
            timeout=(8, 15),
            allow_redirects=True,
        )
        row["latency_ms"] = int((time.perf_counter() - started) * 1000)
        row["http_status"] = resp.status_code
        row["final_url"] = resp.url
        row["redirected"] = resp.url.rstrip("/") != url.rstrip("/")
        row["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0]
        body = resp.content
    except requests.exceptions.SSLError as exc:
        row["status"] = "tls_error"
        row["bozo_reason"] = str(exc)[:160]
    except requests.exceptions.ConnectTimeout:
        row["status"] = "connect_timeout"
    except requests.exceptions.ReadTimeout:
        row["status"] = "read_timeout"
    except requests.exceptions.ConnectionError as exc:
        row["status"] = "dns_or_connection_error"
        row["bozo_reason"] = str(exc)[:160]
    except Exception as exc:  # noqa: BLE001
        row["status"] = "request_error"
        row["bozo_reason"] = f"{type(exc).__name__}: {exc}"[:160]

    if row["latency_ms"] is None:
        row["latency_ms"] = int((time.perf_counter() - started) * 1000)

    if body is None:
        row["action"] = "investigate or replace - source unreachable"
        return row

    code = row["http_status"] or 0
    if code in (401, 403):
        row["status"] = "blocked"
        row["action"] = "respect block; find licensed/primary alternative"
        return row
    if code == 404:
        row["status"] = "not_found"
        row["action"] = "replace feed URL"
        return row
    if code == 410:
        row["status"] = "gone"
        row["action"] = "remove"
        return row
    if code == 429:
        row["status"] = "rate_limited"
        row["action"] = "back off; reduce fetch frequency"
        return row
    if code >= 500:
        row["status"] = "server_error"
        row["action"] = "recheck later; replace if persistent"
        return row
    if code != 200:
        row["status"] = f"http_{code}"
        row["action"] = "investigate"
        return row

    parsed = feedparser.parse(body)
    row["bozo"] = bool(getattr(parsed, "bozo", False))
    if row["bozo"] and getattr(parsed, "bozo_exception", None):
        row["bozo_reason"] = str(parsed.bozo_exception)[:160]
    entries = getattr(parsed, "entries", []) or []
    row["entries_total"] = len(entries)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    newest = None
    in_window = 0
    for entry in entries:
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        if not stamp:
            continue
        published = datetime(*stamp[:6], tzinfo=timezone.utc)
        newest = published if newest is None or published > newest else newest
        if published > cutoff:
            in_window += 1
    row["entries_in_window"] = in_window
    if newest:
        row["newest_age_hours"] = round(
            (datetime.now(timezone.utc) - newest).total_seconds() / 3600, 1
        )

    ctype = row["content_type"] or ""
    if not entries:
        if "html" in ctype:
            row["status"] = "html_not_feed"
            row["action"] = "wrong URL - find the real feed or drop"
        elif row["bozo"]:
            row["status"] = "unparseable"
            row["action"] = "fix URL or parser"
        else:
            row["status"] = "empty_feed"
            row["action"] = "verify feed still published"
        return row

    if in_window == 0:
        age = row["newest_age_hours"]
        if age is None:
            row["status"] = "healthy_no_dates"
            row["action"] = "usable but undated - dedupe/novelty risk"
        elif age > 24 * 30:
            row["status"] = "abandoned"
            row["action"] = "remove or replace"
        elif age > 24 * 7:
            row["status"] = "stale"
            row["action"] = "low frequency - keep but do not rely on"
        else:
            row["status"] = "quiet_but_healthy"
            row["action"] = "keep"
        return row

    row["status"] = "healthy"
    row["action"] = "keep"
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(SITE_ROOT))
    parser.add_argument(
        "--out", default=str(SITE_ROOT / ".editorial-state" / "source-probe.json")
    )
    parser.add_argument("--min-healthy-pct", type=float, default=0.0)
    parser.add_argument("--lookback-hours", type=int, default=36)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    config = json.loads(
        (Path(args.repo) / "config" / "sources.json").read_text(encoding="utf-8")
    )
    sources = config["sources"]
    print(f"probing {len(sources)} sources ...", flush=True)

    rows = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {
            pool.submit(classify, source, args.lookback_hours): source
            for source in sources
        }
        for done, future in enumerate(futures.as_completed(pending), 1):
            try:
                rows.append(future.result())
            except Exception as exc:  # noqa: BLE001
                source = pending[future]
                rows.append(
                    {
                        "name": source.get("name"),
                        "url": source.get("url"),
                        "status": "probe_crashed",
                        "bozo_reason": str(exc)[:160],
                    }
                )
            if done % 25 == 0:
                print(f"  {done}/{len(sources)}", flush=True)

    rows.sort(key=lambda r: (r.get("status") or "", r.get("name") or ""))
    usable = [r for r in rows if r.get("status") in USABLE_STATUSES]

    by_sector: dict[str, dict[str, int]] = {}
    for row in rows:
        for sector in row.get("sectors") or ["(unassigned)"]:
            entry = by_sector.setdefault(sector, {"sources": 0, "usable": 0, "items": 0})
            entry["sources"] += 1
            if row.get("status") in USABLE_STATUSES:
                entry["usable"] += 1
                entry["items"] += row.get("entries_in_window") or 0

    healthy_pct = len(usable) / len(rows) if rows else 0.0
    payload = {
        "schema_version": 1,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": args.lookback_hours,
        "source_count": len(rows),
        "usable_count": len(usable),
        "usable_pct": round(healthy_pct * 100, 1),
        "items_in_window": sum(r.get("entries_in_window") or 0 for r in usable),
        "status_counts": dict(
            sorted(Counter(r.get("status") for r in rows).items(), key=lambda kv: -kv[1])
        ),
        "sector_coverage": dict(sorted(by_sector.items())),
        "sources": rows,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        f"\n  usable {len(usable)}/{len(rows)} ({payload['usable_pct']}%), "
        f"{payload['items_in_window']} items in {args.lookback_hours}h"
    )
    for sector, entry in payload["sector_coverage"].items():
        print(f"    {sector:24} {entry['usable']:>3}/{entry['sources']:<3} usable, "
              f"{entry['items']:>4} items")
    print(f"  wrote {out_path}")

    if args.min_healthy_pct and healthy_pct * 100 < args.min_healthy_pct:
        print(
            f"::error::usable source coverage {payload['usable_pct']}% is below the "
            f"required {args.min_healthy_pct}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
