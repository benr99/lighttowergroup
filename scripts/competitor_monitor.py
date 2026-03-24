#!/usr/bin/env python3
"""
competitor_monitor.py — Weekly CRE content gap analysis for Light Tower Group.

Scans a curated list of competitor and industry publication RSS feeds,
extracts the topics they are covering, compares against LTG's existing
insights.json archive, and outputs a gap-analysis brief.

Run manually or add to Task Scheduler (weekly, e.g. every Monday at 8 AM):
  python scripts/competitor_monitor.py

Output: scripts/competitor_report.md  (overwritten each run)

Requirements: Python 3.9+, anthropic package, ANTHROPIC_API_KEY in scripts/.env
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT  = SCRIPT_DIR.parent
ENV_FILE   = SCRIPT_DIR / ".env"
INSIGHTS_JSON = SITE_ROOT / "insights.json"
REPORT_OUT    = SCRIPT_DIR / "competitor_report.md"

# Competitor and industry publication RSS feeds
COMPETITOR_FEEDS = [
    # Major CRE advisors / brokerages
    ("CBRE Research",         "https://www.cbre.com/insights/rss"),
    ("JLL Insights",          "https://www.jll.com/en/trends-and-insights/research.rss"),
    ("Cushman & Wakefield",   "https://www.cushmanwakefield.com/en/insights/rss"),
    # CRE news publications
    ("The Real Deal NYC",     "https://therealdeal.com/feed/"),
    ("Bisnow NY",             "https://www.bisnow.com/rss/new-york"),
    ("Commercial Observer",   "https://commercialobserver.com/feed/"),
    ("GlobeSt",               "https://www.globest.com/feed/"),
    ("CoStar News",           "https://www.costar.com/rss/news"),
    # Capital markets focused
    ("Trepp Wire",            "https://www.trepp.com/trepptalk/rss.xml"),
    ("MBA Newslink",          "https://www.mba.org/news-and-research/newslink/rss/newslink-rss-feed"),
]

# How many days back to include articles from
LOOKBACK_DAYS = 7

# ─── Helpers ────────────────────────────────────────────────────────────────

def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def fetch_feed(name: str, url: str, lookback: datetime) -> list[dict]:
    """Fetch RSS/Atom feed and return recent items as {title, link, pub_date}."""
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LTG-CompetitorMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(raw)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = item.findtext("pubDate") or item.findtext("dc:date", namespaces={
                "dc": "http://purl.org/dc/elements/1.1/"}) or ""
            if title:
                items.append({"source": name, "title": title, "link": link, "pub": pub})

        # Atom
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
            link_el = entry.find("atom:link", ns)
            link = (link_el.get("href", "") if link_el is not None else "")
            pub  = entry.findtext("atom:published", namespaces=ns) or ""
            if title:
                items.append({"source": name, "title": title, "link": link, "pub": pub})

    except Exception as e:
        print(f"  [WARN] Could not fetch {name}: {e}")
    return items[:30]  # cap per feed


def load_ltg_titles() -> list[str]:
    """Load all LTG article titles from insights.json."""
    if not INSIGHTS_JSON.exists():
        return []
    try:
        data = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))
        return [a.get("title", "") for a in data]
    except Exception:
        return []


def call_claude(api_key: str, prompt: str, system: str) -> str:
    """Call Claude API via urllib (no extra dependencies)."""
    import json as _json
    payload = _json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = _json.loads(resp.read().decode("utf-8"))
    return result["content"][0]["text"]


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("LTG Competitor Monitor — Weekly Gap Analysis")
    print("=" * 50)

    env = load_env()
    api_key = env.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not found in scripts/.env")
        sys.exit(1)

    lookback = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    print(f"Scanning feeds from the past {LOOKBACK_DAYS} days...\n")

    all_items = []
    for name, url in COMPETITOR_FEEDS:
        print(f"  Fetching: {name}")
        items = fetch_feed(name, url, lookback)
        all_items.extend(items)
        print(f"    → {len(items)} items")

    if not all_items:
        print("\n[WARN] No items fetched. Check network or feed URLs.")
        return

    ltg_titles = load_ltg_titles()
    print(f"\nLTG archive: {len(ltg_titles)} existing articles")

    # Build prompt
    competitor_text = "\n".join(
        f"- [{item['source']}] {item['title']}"
        for item in all_items
    )
    ltg_text = "\n".join(f"- {t}" for t in ltg_titles[:50]) or "(none yet)"

    system = (
        "You are a strategic content analyst for Light Tower Group, a NYC-based institutional "
        "CRE capital advisory firm. Analyze what competitors and industry publications are "
        "covering vs. what LTG has already covered, and identify actionable content gaps. "
        "Be specific, data-driven, and concise. Focus on debt markets, equity placement, "
        "NYC real estate, and capital markets topics most relevant to LTG's audience."
    )

    prompt = f"""Here are the articles published this week by competitors and industry publications:

{competitor_text}

Here are the most recent articles LTG has already published:

{ltg_text}

Please produce a gap analysis brief with these sections:

1. **Topics competitors are pushing this week** (3-5 bullet points — specific topics/angles)
2. **Topics LTG is NOT covering that competitors are** (3-5 gaps with brief explanation of why each matters)
3. **Topics LTG is covering that competitors are NOT** (2-3 content moats LTG should double down on)
4. **Recommended article topics for this week** (3 specific article ideas with suggested headline and 1-sentence angle)
5. **One trend to watch** (an emerging story in the feeds that could be important next week)

Keep the entire brief under 600 words. Be direct and specific."""

    print("\nRunning gap analysis via Claude...")
    try:
        analysis = call_claude(api_key, prompt, system)
    except Exception as e:
        print(f"[ERROR] Claude API call failed: {e}")
        sys.exit(1)

    # Write report
    report = (
        f"# LTG Weekly Competitor Intelligence Report\n"
        f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}\n"
        f"**Feeds scanned:** {len(COMPETITOR_FEEDS)}\n"
        f"**Articles analyzed:** {len(all_items)}\n\n"
        f"---\n\n"
        f"{analysis}\n\n"
        f"---\n\n"
        f"## Raw Feed Items This Week\n\n"
        + "\n".join(
            f"- **[{item['source']}]** {item['title']}"
            + (f" — {item['link']}" if item.get("link") else "")
            for item in all_items
        )
    )

    REPORT_OUT.write_text(report, encoding="utf-8")
    print(f"\n✓ Report written to: {REPORT_OUT}")
    print("\n" + "=" * 50)
    print(analysis)


if __name__ == "__main__":
    main()
