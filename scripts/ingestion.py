"""Multi-sector news ingestion for the Light Tower Insights pipeline.

Reads config/sources.json, fetches RSS feeds via feedparser, normalizes
entries to CanonicalItem objects, and maintains per-source health tracking.

Replaces the monolithic fetch_rss_stories() in daily_news_agent.py with
a config-driven, multi-sector approach.
"""

from __future__ import annotations
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests

from canonical_item import CanonicalItem
from source_health import SourceHealthLedger

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SITE_ROOT / "config"
SOURCE_HEALTH_FILE = SITE_ROOT / ".editorial-state" / "source-health.json"

MAX_WORKERS = 8
#: Explicit fetch timeouts. Without these one slow host stalls the phase.
FEED_CONNECT_TIMEOUT = 8
FEED_READ_TIMEOUT = 15
LOOKBACK_HOURS = 36
MAX_ENTRIES_PER_FEED = 500

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def load_sources() -> list[dict[str, Any]]:
    """Load source configuration from config/sources.json.

    Returns a flat list of active source dictionaries. Supports both the
    current ``{"schema_version": ..., "sources": [...]}`` shape and a
    bare top-level array for backwards compatibility.
    """
    try:
        data = json.loads((CONFIG_DIR / "sources.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [ERROR] Could not load sources.json: {e}")
        return []

    if isinstance(data, list):
        raw_sources = data
    elif isinstance(data, dict) and "sources" in data:
        raw_sources = data["sources"]
    else:
        print("  [ERROR] sources.json has an unrecognized structure.")
        return []

    active = []
    for s in raw_sources:
        if not isinstance(s, dict):
            continue
        if not s.get("active", True):
            continue
        active.append(s)
    return active


def load_sources_by_sector() -> dict[str, list[dict[str, Any]]]:
    """Return active sources grouped by their configured primary sector."""
    sources = load_sources()
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for s in sources:
        sector_list = s.get("sectors", [])
        primary = sector_list[0] if sector_list else "unclassified"
        by_sector.setdefault(primary, []).append(s)
    return by_sector


def _parse_entry_date(entry: Any) -> str:
    """Best-effort ISO 8601 datetime from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _is_recent(published: str, lookback_hours: int = LOOKBACK_HOURS) -> bool:
    """Check if a published date is within the lookback window."""
    try:
        pub = datetime.fromisoformat(published.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc).timestamp() - (lookback_hours * 3600)
        return pub.timestamp() > cutoff
    except (ValueError, AttributeError):
        return True


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return _HTML_TAG_RE.sub(" ", str(text or "")).strip()


def _truncate_summary(text: str, max_chars: int = 600) -> str:
    """Strip HTML and truncate to max_chars at the nearest word boundary."""
    cleaned = _strip_html(text)
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars].rsplit(" ", 1)[0]
    return truncated


def fetch_single_feed(
    source: dict[str, Any],
) -> tuple[list[CanonicalItem], dict[str, Any], str | None]:
    """Fetch a single RSS feed and return normalized CanonicalItem objects.

    Returns a three-tuple of (items, updated_source_metadata, error_string).
    The updated ``source`` dict carries diagnostic keys prefixed with ``_``.
    """
    name = source.get("name", "unknown")
    url = source.get("url", "")
    items: list[CanonicalItem] = []
    error = None
    elapsed_ms = 0

    if not url or url in ("newsapi.org", ""):
        return items, source, error

    started = time.perf_counter()
    try:
        # feedparser.parse(url) fetches through urllib, which has no timeout by
        # default, so one unresponsive host could stall a worker indefinitely and
        # with it the whole ingestion phase. Fetch with explicit connect and read
        # timeouts and hand feedparser the bytes instead.
        response = requests.get(
            url,
            headers={
                "User-Agent": "LightTowerGroup-NewsAgent/2.0",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
            timeout=(FEED_CONNECT_TIMEOUT, FEED_READ_TIMEOUT),
            allow_redirects=True,
        )
        if response.status_code != 200:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            source["_health"] = "empty"
            source["_elapsed_ms"] = elapsed_ms
            source["_story_count"] = 0
            source["_http_status"] = response.status_code
            return items, source, error
        feed = feedparser.parse(response.content)

        if getattr(feed, "bozo", False) and not getattr(feed, "entries", None):
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            source["_health"] = "empty"
            source["_elapsed_ms"] = elapsed_ms
            source["_story_count"] = 0
            return items, source, error

        for entry in feed.entries:
            if len(items) >= MAX_ENTRIES_PER_FEED:
                break
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or entry.get("id") or ""
            if not title or not link:
                continue

            published = _parse_entry_date(entry)
            if not _is_recent(published):
                continue

            summary_raw = entry.get("summary") or entry.get("description") or ""
            summary = _truncate_summary(summary_raw)

            item = CanonicalItem.from_rss_entry(
                {"title": title, "link": link, "summary": summary, "published": published},
                source,
            )
            item.raw_summary = summary
            items.append(item)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        source["_health"] = "empty" if not items and getattr(feed, "entries", None) else "ok"
        source["_story_count"] = len(items)
        source["_elapsed_ms"] = elapsed_ms

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        error = str(e)[:200]
        source["_health"] = "error"
        source["_elapsed_ms"] = elapsed_ms
        source["_story_count"] = 0

    return items, source, error


def fetch_all_sources(
    sources: list[dict[str, Any]] | None = None,
    max_workers: int = MAX_WORKERS,
) -> list[CanonicalItem]:
    """Fetch all active sources concurrently and return normalized CanonicalItems.

    Args:
        sources: List of source config dicts. If None, loads from config/sources.json.
        max_workers: Number of concurrent fetch threads.

    Returns:
        List of CanonicalItem objects ingested from all sources.
    """
    if sources is None:
        sources = load_sources()

    if not sources:
        print("  No active sources configured.")
        return []

    if max_workers < 1:
        max_workers = MAX_WORKERS

    health = SourceHealthLedger(SOURCE_HEALTH_FILE)
    active_sources: list[dict[str, Any]] = []
    skipped = 0

    for source in sources:
        name = source.get("name", "")
        if health.is_quarantined(name):
            skipped += 1
            continue
        active_sources.append(source)

    print(f"  Fetching {len(active_sources)} active source(s) ({skipped} quarantined)...")

    all_items: list[CanonicalItem] = []
    failed_feeds = 0
    empty_feeds = 0
    attempted = 0
    failures: list[tuple[str, str, int]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_feed, s): s for s in active_sources}
        for future in as_completed(futures):
            attempted += 1
            try:
                items, updated_source, error = future.result()
                all_items.extend(items)

                name = updated_source.get("name", "unknown")
                h = updated_source.get("_health", "ok")
                ms = updated_source.get("_elapsed_ms", 0)

                if h == "error" and error:
                    failed_feeds += 1
                    failures.append((name, error, ms))
                elif h == "empty":
                    empty_feeds += 1
                    health.record_empty(name, ms, "feedparser returned no entries")
                else:
                    count = updated_source.get("_story_count", 0)
                    health.record_success(name, count, ms)

            except Exception as e:
                failed_feeds += 1
                source_name = futures.get(future, {}).get("name", "unknown")
                failures.append((source_name, str(e)[:200], 0))

    # Shared outage detection: when most feeds fail at once, blame the network,
    # not individual publishers. Release prior quarantines so that every source
    # gets a fair chance on the next run.
    shared_outage = attempted >= 8 and len(failures) >= max(4, attempted // 2)
    if shared_outage:
        released = health.release_quarantines()
        for name, error, ms in failures:
            health.record_transient_outage(name, error, ms)
        print(
            f"  [WARN] Shared RSS outage: {len(failures)}/{attempted} failed; "
            f"{released} quarantines released"
        )
    else:
        for name, error, ms in failures:
            health.record_failure(name, error, ms)

    try:
        health.save()
    except OSError as e:
        print(f"  [WARN] Could not persist source health: {e}")

    print(
        f"  Ingestion: {len(all_items)} items from {attempted} feeds "
        f"({failed_feeds} failed, {empty_feeds} empty)"
    )

    return all_items


def fetch_sector_items(
    sector: str,
    sources: list[dict[str, Any]] | None = None,
    max_workers: int = MAX_WORKERS,
) -> list[CanonicalItem]:
    """Fetch only sources belonging to a specific sector.

    Args:
        sector: The sector key (e.g. "commercial_real_estate").
        sources: Full source list. If None, loads from config.
        max_workers: Number of concurrent fetch threads.

    Returns:
        CanonicalItem list for the requested sector only.
    """
    if sources is None:
        sources = load_sources()

    sector_sources = [
        s for s in sources
        if sector in s.get("sectors", [])
    ]

    if not sector_sources:
        print(f"  No active sources for sector '{sector}'.")
        return []

    print(f"  Sector '{sector}': {len(sector_sources)} source(s)")
    return fetch_all_sources(sector_sources, max_workers=max_workers)


def get_source_stats(all_items: list[CanonicalItem]) -> dict[str, int]:
    """Count items per source, sorted by count descending (top 20)."""
    stats: dict[str, int] = {}
    for item in all_items:
        src = item.source_name or "unknown"
        stats[src] = stats.get(src, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True)[:20])


def get_sector_counts(all_items: list[CanonicalItem]) -> dict[str, int]:
    """Count items per primary sector."""
    counts: dict[str, int] = {}
    for item in all_items:
        sector = item.primary_sector or "unclassified"
        counts[sector] = counts.get(sector, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
