#!/usr/bin/env python3
"""
Light Tower Group \u2014 Daily CRE News Agent
\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
Phases:
  1. GATHER   \u2014 pull stories from 20 RSS feeds + NewsAPI
  2. TRIAGE   \u2014 filter to CRE-relevant, last 36h, deduplicate
  3. SCORE    \u2014 Claude ranks all stories by capital-markets significance
  4. ENRICH   \u2014 fetch full text of winner; extract NYC address context
  5. WRITE    \u2014 Claude generates WSJ-style editorial piece
  6. PUBLISH  \u2014 save HTML, update insights.json + feed.xml, git push
  7. LINKEDIN \u2014 auto-post link share to LinkedIn
  8. LOG      \u2014 append run record to agent_log.json

Schedule: Windows Task Scheduler, daily 7:00 AM
  Program:   python
  Arguments: C:\\...\\scripts\\daily_news_agent.py
  Start in:  C:\\...\\scripts

Usage:
  python daily_news_agent.py            # normal run
  python daily_news_agent.py --dry-run  # score + write but don\u2019t publish/post
  python daily_news_agent.py --force    # skip duplicate check
"""

import feedparser
import trafilatura
import requests
import anthropic
import json
import re
import os
import sys
import time
import difflib
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from html.parser import HTMLParser

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# \u2500\u2500 Load .env \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from news_sources import (
    RSS_FEEDS, CRE_KEYWORDS, EXCLUDE_KEYWORDS,
    NEWSAPI_QUERIES, SITE_URL, SITE_NAME,
    FEED_TITLE, FEED_DESCRIPTION, LINKEDIN_HASHTAGS,
)
from enhanced_prompts import SYSTEM_PROMPT_ENHANCED, USER_PROMPT_TEMPLATE
from social_image_generator import generate_article_image

# \u2500\u2500 Config \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
SCRIPT_DIR    = Path(__file__).parent
SITE_ROOT     = SCRIPT_DIR.parent
INSIGHTS_DIR  = SITE_ROOT / "insights"
INSIGHTS_JSON = SITE_ROOT / "insights.json"
FEED_XML      = SITE_ROOT / "feed.xml"
SITEMAP_XML   = SITE_ROOT / "sitemap.xml"

# Static pages included in every sitemap rebuild
_SITEMAP_STATIC = [
    ("/",                           "1.0", "weekly"),
    ("/insights.html",              "0.9", "daily"),
    ("/buildings.html",             "0.8", "weekly"),
    ("/services.html",              "0.9", "monthly"),
    ("/about.html",                 "0.7", "monthly"),
    ("/transactions.html",          "0.7", "monthly"),
    ("/research.html",              "0.7", "monthly"),
    ("/senior-debt.html",           "0.8", "monthly"),
    ("/bridge-financing.html",      "0.8", "monthly"),
    ("/construction-financing.html","0.8", "monthly"),
    ("/cmbs.html",                  "0.8", "monthly"),
    ("/agency-lending.html",        "0.8", "monthly"),
    ("/joint-venture-equity.html",  "0.8", "monthly"),
    ("/preferred-equity.html",      "0.8", "monthly"),
    ("/life-company-financing.html","0.8", "monthly"),
]
LOG_FILE      = SCRIPT_DIR / "agent_log.json"

ANTHROPIC_API_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY      = os.environ.get("DEEPSEEK_API_KEY", "")
NEWSAPI_KEY           = os.environ.get("NEWSAPI_KEY", "")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN   = os.environ.get("LINKEDIN_PERSON_URN", "")


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 1: GATHER
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _parse_entry_date(entry) -> str:
    """Best-effort ISO 8601 datetime from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def fetch_rss_stories() -> list:
    """Parse all configured RSS feeds and return normalised story dicts."""
    stories = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_url,
                request_headers={"User-Agent": "LightTowerGroup-NewsAgent/1.0"},
            )
            for entry in feed.entries[:20]:
                title   = (entry.get("title") or "").strip()
                url     = entry.get("link") or entry.get("id") or ""
                summary = (entry.get("summary") or entry.get("description") or "")[:600]
                # Strip HTML from summary
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                if title and url:
                    stories.append({
                        "title":     title,
                        "url":       url,
                        "summary":   summary,
                        "source":    source_name,
                        "published": _parse_entry_date(entry),
                    })
        except Exception as e:
            print(f"  [WARN] RSS {source_name}: {e}")
        time.sleep(0.05)

    print(f"  RSS: {len(stories)} raw stories from {len(RSS_FEEDS)} feeds")
    return stories


def fetch_newsapi_stories() -> list:
    """Supplement with NewsAPI.org keyword search (free tier: 100 req/day)."""
    if not NEWSAPI_KEY:
        return []

    stories = []
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d")

    for query in NEWSAPI_QUERIES[:3]:   # use only 3 of 5 to stay well under limit
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "from":     yesterday,
                    "sortBy":   "publishedAt",
                    "language": "en",
                    "pageSize": 10,
                    "apiKey":   NEWSAPI_KEY,
                },
                timeout=12,
            )
            for art in r.json().get("articles", []):
                title = (art.get("title") or "").strip()
                url   = art.get("url") or ""
                if title and url and "[Removed]" not in title:
                    stories.append({
                        "title":     title,
                        "url":       url,
                        "summary":   (art.get("description") or "")[:600],
                        "source":    art.get("source", {}).get("name", "NewsAPI"),
                        "published": art.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                    })
        except Exception as e:
            print(f"  [WARN] NewsAPI query '{query[:30]}': {e}")
        time.sleep(0.5)

    print(f"  NewsAPI: {len(stories)} additional stories")
    return stories


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 2: TRIAGE
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _is_cre_relevant(story: dict) -> bool:
    text = (story["title"] + " " + story["summary"]).lower()
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text for kw in CRE_KEYWORDS)


def _is_recent(story: dict, hours: int = 36) -> bool:
    try:
        pub = datetime.fromisoformat(story["published"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - pub) < timedelta(hours=hours)
    except Exception:
        return True   # include if date unparseable


def _deduplicate(stories: list) -> list:
    """Remove near-duplicate titles (SequenceMatcher ratio > 0.72)."""
    seen_titles = []
    unique = []
    for s in stories:
        t = s["title"].lower().strip()
        if not t:
            continue
        if any(difflib.SequenceMatcher(None, t, seen).ratio() > 0.72 for seen in seen_titles):
            continue
        seen_titles.append(t)
        unique.append(s)
    return unique


def triage(stories: list) -> list:
    relevant = [s for s in stories if s["url"] and _is_cre_relevant(s) and _is_recent(s)]
    unique   = _deduplicate(relevant)
    print(f"  Triage: {len(stories)} raw \u2192 {len(relevant)} relevant \u2192 {len(unique)} unique")
    return unique


def already_published(slug: str) -> bool:
    if not INSIGHTS_JSON.exists():
        return False
    try:
        data = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))
        return any(e.get("slug") == slug for e in data)
    except Exception:
        return False


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 3: SCORE
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def score_stories(stories: list) -> list:
    """
    Single DeepSeek call to rank all candidates by significance.
    Returns stories sorted highest-score first.
    """
    if not stories:
        return []

    story_list = "\n\n".join(
        f"[{i+1}] SOURCE: {s['source']}\n"
        f"    TITLE:   {s['title']}\n"
        f"    SUMMARY: {s['summary'][:220]}"
        for i, s in enumerate(stories[:100])
    )

    prompt = f"""You are a senior editor at a Wall Street Journal-style CRE capital markets publication.

Score each story 0\u2013100 for significance to a sophisticated NYC CRE capital markets audience
(institutional investors, lenders, developers, brokers). Criteria:

  Capital markets impact (rate moves, CMBS, loan distress, refis, maturities): 30 pts
  NYC / Brooklyn / Manhattan direct relevance:                                  25 pts
  Deal size or policy scale:                                                    20 pts
  Originality (scoop vs. press release rehash):                                15 pts
  Timeliness / breaking-news urgency:                                          10 pts

Return ONLY a JSON array \u2014 no prose before or after:
[{{"index": 1, "score": 87, "reason": "one-sentence justification"}}, ...]

Stories to score:
{story_list}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3500,
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()
        m = re.search(r"\[[\s\S]*\]", raw)
        if not m:
            raise ValueError("No JSON array found in scoring response")

        scores_raw = json.loads(m.group())
        score_map  = {item["index"] - 1: item.get("score", 0) for item in scores_raw}
        ranked_idx = sorted(range(len(stories)), key=lambda i: score_map.get(i, 0), reverse=True)

        print(f"  Top 3 stories:")
        for rank, idx in enumerate(ranked_idx[:3], 1):
            s = stories[idx]
            print(f"    #{rank} [{score_map.get(idx, 0)}/100] {s['source']}: {s['title'][:65]}")

        return [stories[i] for i in ranked_idx]

    except Exception as e:
        print(f"  [WARN] Scoring failed ({e}), using raw order")
        return stories


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 4: ENRICH
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _fetch_full_text(url: str) -> str:
    """Pull full article text via trafilatura with graceful fallback."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            if text and len(text) > 150:
                return text[:5000]
    except Exception as e:
        print(f"  [WARN] trafilatura failed for {url[:50]}: {e}")
    return ""


def _extract_nyc_addresses(text: str) -> list:
    """Find NYC street addresses in article text for optional PLUTO enrichment."""
    pattern = (
        r"\b\d{1,4}\s+"
        r"(?:West|East|North|South|W\.|E\.)\s+"
        r"\d{1,3}(?:th|st|nd|rd)?\s+"
        r"(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?)\b"
    )
    return list(dict.fromkeys(re.findall(pattern, text, re.IGNORECASE)))[:3]


def enrich_story(story: dict) -> dict:
    """Fetch full text and surface any NYC address context."""
    print(f"  Full-text fetch: {story['url'][:70]}...")
    raw_text = _fetch_full_text(story["url"])
    # Scrub prompt-injection patterns before this text is embedded in a Claude prompt
    story["full_text"] = scrub_prompt_injection(raw_text)
    chars = len(story["full_text"])
    print(f"  Extracted {chars:,} chars of article text")

    all_text = story["title"] + " " + story["summary"] + " " + story["full_text"]
    addresses = _extract_nyc_addresses(all_text)
    story["mentioned_addresses"] = addresses
    if addresses:
        print(f"  NYC addresses found: {addresses}")

    return story


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 5: WRITE
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

SYSTEM_PROMPT = """\
You are the lead capital markets correspondent for Light Tower Group, a NYC commercial
real estate capital advisory firm. Write in the precise style of WSJ "Heard on the Street":
incisive, data-driven, analytically sharp, never promotional.

Voice rules:
\u2014 Open with a specific, concrete detail: a dollar amount, a date, a named building, a named lender.
  Never open with a vague market generalisation.
\u2014 Every claim is supported by a named fact, a number, or an attributable source.
\u2014 Short paragraphs. Four sentences maximum per paragraph.
\u2014 Forbidden phrases: "in recent years", "it remains to be seen", "going forward",
  "stakeholders", "paradigm", "ecosystem", "landscape", "game-changer", "unprecedented".
\u2014 Attribute sources precisely: "per ACRIS records", "according to Trepp data", "CBRE reported".
\u2014 The kicker circles back to the lead detail with a sharper, forward-looking edge.
\u2014 Total length: 700\u20131\u2009000 words.
\u2014 Audience: institutional investors, lenders, and developers who read 10-Ks for leisure.\
"""


def generate_article(story: dict) -> dict:
    """Call DeepSeek to produce a full editorial article from the enriched story."""

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)

    full_text_block = (
        story["full_text"][:3500] if story.get("full_text")
        else "Full text not available \u2014 work from the title and summary."
    )
    addresses_block = (
        f"NYC addresses mentioned: {', '.join(story['mentioned_addresses'])}"
        if story.get("mentioned_addresses") else ""
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=story['title'],
        source=story['source'],
        url=story['url'],
        published_date=story.get('published', 'Unknown'),
        summary=story['summary'],
        full_text=full_text_block,
        addresses_block=addresses_block,
        today=now_utc.strftime('%B %d, %Y')
    )

    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": "deepseek-chat",
            "max_tokens": 4500,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_ENHANCED},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("No JSON object found in DeepSeek article response")

    article = json.loads(m.group())
    article["date"]       = now_utc.strftime("%B %d, %Y")
    article["date_iso"]   = now_utc.isoformat()
    article["source_url"] = story["url"]
    article["source_name"] = story["source"]
    return article


# ── Security utilities ────────────────────────────────────────────────────────

# Tags and attributes permitted in article body HTML (allowlist approach)
_SAFE_TAGS  = {'p', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'blockquote', 'br', 'a', 'span'}
_SAFE_ATTRS = {'a': ['href', 'target', 'rel']}


class _HtmlSanitizer(HTMLParser):
    """Strip unsafe tags and attributes from Claude-generated article HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag not in _SAFE_TAGS:
            return
        attr_dict = dict(attrs)
        safe = []
        for attr in _SAFE_ATTRS.get(tag, []):
            val = attr_dict.get(attr, '')
            if not val:
                continue
            if attr == 'href':
                if re.match(r'^\s*(javascript|data|vbscript)\s*:', val, re.IGNORECASE):
                    continue
                safe.append(f'href="{escape(val)}"')
            elif attr == 'target':
                safe.append('target="_blank"')
            elif attr == 'rel':
                safe.append('rel="noopener noreferrer"')
        if tag == 'a' and 'target="_blank"' in safe and 'rel="noopener noreferrer"' not in safe:
            safe.append('rel="noopener noreferrer"')
        attr_str = (' ' + ' '.join(safe)) if safe else ''
        if tag == 'br':
            self.out.append('<br>')
        else:
            self.out.append(f'<{tag}{attr_str}>')

    def handle_endtag(self, tag):
        if tag in _SAFE_TAGS and tag != 'br':
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        self.out.append(escape(data))

    def handle_entityref(self, name):
        self.out.append(f'&{name};')

    def handle_charref(self, name):
        self.out.append(f'&#{name};')

    def get_output(self):
        return ''.join(self.out)


def sanitize_html(raw: str) -> str:
    """
    Sanitize Claude-generated article HTML before writing to disk.
    Allowlists safe structural tags; strips script, style, event handlers,
    iframes, javascript: URIs, and any other dangerous constructs.
    """
    parser = _HtmlSanitizer()
    parser.feed(raw or '')
    return parser.get_output()


# Regex patterns that signal an adversarial prompt injection attempt embedded
# in untrusted RSS/article content that flows into Claude prompts.
_INJECTION_RE = re.compile(
    r'(ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?'
    r'|system\s*:\s*you\s+are'
    r'|<\s*/?system\s*>'
    r'|forget\s+(?:all\s+)?(?:previous|prior)\s+instructions?'
    r'|you\s+are\s+now\s+(?:a\s+)?(?:an?\s+)?(?:different|new|evil|jailbreak)'
    r'|disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?'
    r'|\[INST\]|\[\/INST\]'
    r'|<\|(?:im_start|im_end)\|>)',
    re.IGNORECASE,
)


def scrub_prompt_injection(text: str) -> str:
    """
    Strip known prompt-injection patterns from untrusted article text before
    embedding it in a Claude prompt. Logs a warning if anything was removed.
    """
    cleaned = _INJECTION_RE.sub('[removed]', text)
    if cleaned != text:
        print("  [SECURITY] Prompt-injection pattern scrubbed from article text")
    return cleaned


def _parse_manifest_date(date_str: str) -> datetime:
    """
    Parse a date from insights.json, handling both legacy and new formats.
    Legacy: "April 29, 2026" (old agent runs)
    New:    "2026-04-29"     (current agent)
    Returns a datetime at midnight UTC. Falls back to today if unparseable.
    """
    for fmt in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 6: PUBLISH
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _share_buttons(page_url: str, title: str) -> str:
    """Render LinkedIn + Twitter share buttons and a copy-link button."""
    enc_url   = requests.utils.quote(page_url, safe="")
    enc_title = requests.utils.quote(title[:100], safe="")
    li_href   = f"https://www.linkedin.com/sharing/share-offsite/?url={enc_url}"
    tw_href   = f"https://twitter.com/intent/tweet?url={enc_url}&text={enc_title}"
    # json.dumps() produces a fully safe JS string literal (handles quotes,
    # backslashes, angle brackets, and all other injection vectors)
    js_url = json.dumps(page_url)
    return f"""\
    <div class="share-bar">
      <span class="share-label">Share</span>
      <a href="{li_href}" target="_blank" rel="noopener noreferrer" class="share-btn share-li">LinkedIn</a>
      <a href="{tw_href}" target="_blank" rel="noopener noreferrer" class="share-btn share-tw">X / Twitter</a>
      <button class="share-btn share-copy"
              onclick="navigator.clipboard.writeText({js_url}).then(function(){{this.textContent='Copied!'}}.bind(this))">Copy Link</button>
    </div>"""


def render_html(article: dict) -> str:
    """Render a full standalone HTML page for a news article."""
    page_url = f"{SITE_URL}/insights/{article['slug']}.html"
    social_image_url = f"{SITE_URL}/insights/{article['slug']}_social.png"
    esc      = lambda s: escape(str(s or ""))

    sources_html = "\n".join(
        f'      <li><a href="{esc(s.get("url","#"))}" target="_blank" rel="noopener">'
        f'{esc(s.get("name",""))}</a></li>'
        for s in article.get("sources", [])
    )
    if not sources_html:
        sources_html = (
            f'      <li><a href="{esc(article.get("source_url","#"))}" '
            f'target="_blank" rel="noopener">{esc(article.get("source_name",""))}</a></li>'
        )

    tags_html  = " ".join(f'<span class="tag">{esc(t)}</span>' for t in article.get("tags", []))
    share_top  = _share_buttons(page_url, article["title"])
    share_bot  = _share_buttons(page_url, article["title"])
    year       = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(article['title'])} | Light Tower Group</title>
  <meta name="description" content="{esc(article['meta_description'])}">
  <link rel="canonical" href="{page_url}">
  <link rel="alternate" type="application/rss+xml"
        title="Light Tower Group Insights" href="{SITE_URL}/feed.xml">

  <!-- Open Graph -->
  <meta property="og:type"        content="article">
  <meta property="og:title"       content="{esc(article['title'])}">
  <meta property="og:description" content="{esc(article['meta_description'])}">
  <meta property="og:url"         content="{page_url}">
  <meta property="og:site_name"   content="Light Tower Group">
  <meta property="og:image"       content="{social_image_url}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="628">
  <meta property="og:image:alt"   content="{esc(article['title'])}">
  <meta property="article:published_time" content="{article['date_iso']}">

  <!-- Twitter Card -->
  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{esc(article['title'])}">
  <meta name="twitter:description" content="{esc(article['meta_description'])}">
  <meta name="twitter:image"       content="{social_image_url}">

  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --black:    #080c14;
      --navy:     #0d1826;
      --gold:     #c9a84c;
      --gold-dim: rgba(201,168,76,0.25);
      --white:    #f4f0e8;
      --muted:    #8a9bb0;
      --body-txt: rgba(244,240,232,0.88);
      --serif:    Georgia, 'Times New Roman', serif;
      --sans:     -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--black); color: var(--white);
            font-family: var(--serif); line-height: 1.75; }}

    /* ── Navigation ── */
    .nav {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 1.4rem 4rem;
      border-bottom: 1px solid var(--gold-dim);
    }}
    .nav-logo {{
      font-family: var(--sans); font-size: 0.85rem; letter-spacing: 0.18em;
      color: var(--gold); text-decoration: none; text-transform: uppercase;
      font-weight: 600;
    }}
    .nav-links {{ display: flex; gap: 2.5rem; }}
    .nav-links a {{
      font-family: var(--sans); font-size: 0.8rem; color: var(--muted);
      text-decoration: none; letter-spacing: 0.05em;
    }}
    .nav-links a:hover {{ color: var(--white); }}
    .nav-cta {{
      font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--gold); border: 1px solid var(--gold); padding: 0.45rem 1.1rem;
      background: none; border-radius: 2px; cursor: pointer; font-family: var(--sans);
      transition: background 0.2s, color 0.2s;
    }}
    .nav-cta:hover {{ background: var(--gold); color: var(--black); }}

    /* ── Article layout ── */
    .article-wrap {{ max-width: 740px; margin: 0 auto; padding: 4rem 2rem 7rem; }}

    /* ── Header ── */
    .article-category {{
      font-family: var(--sans); font-size: 0.68rem; letter-spacing: 0.2em;
      text-transform: uppercase; color: var(--gold); margin-bottom: 1.1rem;
    }}
    .article-title {{
      font-family: var(--serif);
      font-size: clamp(2rem, 5vw, 3.2rem);
      font-weight: normal; line-height: 1.18;
      color: var(--white); margin-bottom: 0.9rem;
    }}
    .article-subtitle {{
      font-size: 1.35rem; color: var(--muted); font-style: italic;
      line-height: 1.5; margin-bottom: 1.6rem;
    }}
    .article-byline {{
      font-family: var(--sans); font-size: 0.9rem; color: var(--muted);
      display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1.75rem;
    }}
    .article-rule {{
      border: none; border-top: 1px solid var(--gold-dim); margin: 1.75rem 0;
    }}

    /* ── Share bar ── */
    .share-bar {{
      display: flex; align-items: center; gap: 0.65rem;
      flex-wrap: wrap; margin: 1.25rem 0;
    }}
    .share-label {{
      font-family: var(--sans); font-size: 0.68rem; letter-spacing: 0.12em;
      text-transform: uppercase; color: var(--muted); margin-right: 0.2rem;
    }}
    .share-btn {{
      font-family: var(--sans); font-size: 0.72rem; letter-spacing: 0.04em;
      padding: 0.4rem 0.95rem; border-radius: 2px; cursor: pointer;
      text-decoration: none; border: 1px solid; transition: all 0.18s;
      background: transparent;
    }}
    .share-li  {{ color: #5b9bd5; border-color: rgba(91,155,213,0.45); }}
    .share-li:hover  {{ background: rgba(91,155,213,0.12); color: #7fb3e8; }}
    .share-tw  {{ color: var(--white); border-color: rgba(255,255,255,0.25); }}
    .share-tw:hover  {{ background: rgba(255,255,255,0.07); }}
    .share-copy {{ color: var(--gold); border-color: var(--gold-dim); }}
    .share-copy:hover {{ background: rgba(201,168,76,0.1); }}

    /* ── Body ── */
    .article-body {{ font-size: 1.15rem; line-height: 1.82; }}
    .article-body p {{
      margin-bottom: 1.45rem; color: var(--body-txt);
    }}
    .article-body strong {{ color: var(--white); }}
    .article-body a {{ color: var(--gold); }}

    /* ── Tags ── */
    .article-tags {{ display: flex; gap: 0.45rem; flex-wrap: wrap; margin: 2rem 0 1rem; }}
    .tag {{
      font-family: var(--sans); font-size: 0.67rem; letter-spacing: 0.1em;
      text-transform: uppercase; color: var(--muted);
      border: 1px solid rgba(138,155,176,0.28); padding: 0.28rem 0.65rem;
      border-radius: 2px;
    }}

    /* ── Sources ── */
    .sources-block {{
      margin-top: 3rem; padding-top: 1.75rem;
      border-top: 1px solid var(--gold-dim);
    }}
    .sources-block h3 {{
      font-family: var(--sans); font-size: 0.67rem; letter-spacing: 0.15em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 0.65rem;
    }}
    .sources-block ul {{ list-style: none; }}
    .sources-block li {{ font-size: 0.85rem; margin-bottom: 0.3rem; }}
    .sources-block a {{ color: var(--gold); text-decoration: none; }}
    .sources-block a:hover {{ text-decoration: underline; }}

    /* ── Footer ── */
    .site-footer {{
      border-top: 1px solid rgba(201,168,76,0.1);
      padding: 2.5rem 4rem; text-align: center;
    }}
    .site-footer p {{
      font-family: var(--sans); font-size: 0.75rem; color: var(--muted);
      line-height: 2;
    }}
    .site-footer a {{ color: var(--gold); text-decoration: none; }}
    .site-footer a:hover {{ text-decoration: underline; }}

    .nav-menu-btn {{ display: none; background: none; border: none; cursor: pointer; padding: 0.4rem; flex-direction: column; gap: 5px; }}
    .nav-menu-btn span {{ display: block; width: 22px; height: 2px; background: var(--white); transition: all 0.25s; }}
    .nav-menu-btn.open span:nth-child(1) {{ transform: translateY(7px) rotate(45deg); }}
    .nav-menu-btn.open span:nth-child(2) {{ opacity: 0; }}
    .nav-menu-btn.open span:nth-child(3) {{ transform: translateY(-7px) rotate(-45deg); }}
    .nav-mobile {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(8,12,20,0.98); padding: 5rem 2rem 2rem; flex-direction: column; gap: 1.5rem; z-index: 200; }}
    .nav-mobile.open {{ display: flex; }}
    .nav-mobile a {{ font-size: 1rem; color: var(--muted); text-decoration: none; letter-spacing: 0.05em; }}
    .nav-mobile a:hover {{ color: var(--white); }}
    .nav-mobile-close {{ position: absolute; top: 1.4rem; right: 1.5rem; background: none; border: none; color: var(--muted); font-size: 1.5rem; cursor: pointer; }}

    @media (max-width: 640px) {{
      .nav {{ padding: 1rem 1.5rem; }}
      .nav-links {{ display: none; }}
      .nav-menu-btn {{ display: flex; }}
      .article-wrap {{ padding: 2rem 1.25rem 4rem; }}
    }}
  </style>
  <!-- OneSignal Web Push — uncomment after adding YOUR_APP_ID from onesignal.com -->
  <!--
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{ appId: "YOUR_APP_ID" }});
    }});
  </script>
  -->
</head>
<body>

  <nav class="nav">
    <a href="/" class="nav-logo">Light Tower Group</a>
    <div class="nav-links">
      <a href="/insights.html">Insights</a>
      <a href="/buildings.html">Buildings</a>
      <a href="/services.html">Services</a>
      <a href="/about.html">About</a>
      <a href="/index.html#contact">Contact</a>
      <button class="nav-cta" onclick="openLTGChat()">Initiate Mandate</button>
    </div>
    <button class="nav-menu-btn" id="nav-menu-btn" aria-label="Open menu">
      <span></span><span></span><span></span>
    </button>
  </nav>
  <div class="nav-mobile" id="nav-mobile">
    <button class="nav-mobile-close" id="nav-mobile-close" aria-label="Close menu">&times;</button>
    <a href="/insights.html">Insights</a>
    <a href="/buildings.html">Buildings</a>
    <a href="/services.html">Services</a>
    <a href="/about.html">About</a>
    <a href="/index.html#contact">Contact</a>
    <button class="nav-cta" onclick="openLTGChat();document.getElementById('nav-mobile').classList.remove('open');document.getElementById('nav-menu-btn').classList.remove('open');">Initiate Mandate</button>
  </div>

  <div class="article-wrap">
    <article itemscope itemtype="https://schema.org/NewsArticle">

      <div class="article-category">{esc(article['category'])}</div>
      <h1 class="article-title" itemprop="headline">{esc(article['title'])}</h1>
      <p class="article-subtitle">{esc(article.get('subtitle',''))}</p>

      <div class="article-byline">
        <span itemprop="author" itemscope itemtype="https://schema.org/Person">
          <a href="/about.html" itemprop="url" style="color:inherit;text-decoration:none;">
            <span itemprop="name">Ben Rohr</span>
          </a>
        </span>
        <span>
          <time itemprop="datePublished" datetime="{article['date_iso']}">
            {esc(article['date'])}
          </time>
        </span>
        <span>Source: {esc(article.get('source_name',''))}</span>
      </div>

      {share_top}
      <hr class="article-rule">

      <div class="article-body" itemprop="articleBody">
        {sanitize_html(article['body_html'])}
      </div>

      <div class="article-tags">{tags_html}</div>

      {share_bot}

      <div class="sources-block">
        <h3>Sources</h3>
        <ul>
{sources_html}
        </ul>
      </div>

    </article>
  </div>

  <footer class="site-footer">
    <p>
      <a href="/">Light Tower Group</a> &nbsp;&middot;&nbsp;
      <a href="/insights.html">All Insights</a> &nbsp;&middot;&nbsp;
      <a href="/about.html">About</a> &nbsp;&middot;&nbsp;
      <a href="/feed.xml">RSS Feed</a> &nbsp;&middot;&nbsp;
      <a href="/index.html#contact">Contact</a>
    </p>
    <p>&copy; {year} Light Tower Group. All rights reserved.</p>
  </footer>

  <script>
    const menuBtn = document.getElementById('nav-menu-btn');
    const mobileNav = document.getElementById('nav-mobile');
    const closeBtn = document.getElementById('nav-mobile-close');
    menuBtn.addEventListener('click', function() {{
      const open = mobileNav.classList.toggle('open');
      menuBtn.classList.toggle('open', open);
    }});
    if (closeBtn) closeBtn.addEventListener('click', function() {{
      mobileNav.classList.remove('open');
      menuBtn.classList.remove('open');
    }});
  </script>
  <script src="/chat-widget.js"></script>

</body>
</html>"""


def update_manifest(article: dict):
    """Prepend new article entry to insights.json."""
    data = []
    if INSIGHTS_JSON.exists():
        try:
            data = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = []

    date_short = article["date_iso"][:10]   # Extract YYYY-MM-DD from ISO timestamp

    entry = {
        "title":    article["title"],
        "slug":     article["slug"],
        "date":     date_short,
        "readTime": 7,
        "category": article["category"],
        "excerpt":  article["meta_description"],
        "url":      f"/insights/{article['slug']}.html",
        "tags":     article.get("tags", []),
    }
    # Remove any existing entry with same slug
    data = [e for e in data if e.get("slug") != article["slug"]]
    data.insert(0, entry)

    INSIGHTS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  insights.json updated ({len(data)} total entries)")


def update_feed_xml():
    """
    Regenerate feed.xml from insights.json.
    Format: RSS 2.0 + Google News namespace (for Google News Publisher Center).
    """
    data = []
    if INSIGHTS_JSON.exists():
        try:
            data = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))[:50]
        except Exception:
            pass

    items = []
    for e in data:
        url = f"{SITE_URL}{e.get('url') or '/insights/' + e['slug'] + '.html'}"
        # Parse date for RSS pubDate format — handles both new "YYYY-MM-DD" and legacy "Month DD, YYYY"
        d = _parse_manifest_date(e.get("date", ""))
        pub_rss = d.strftime("%a, %d %b %Y 07:00:00 +0000")
        pub_iso = d.strftime("%Y-%m-%dT07:00:00Z")

        keywords = ", ".join(e.get("tags", [e.get("category", "")]))

        items.append(f"""    <item>
      <title><![CDATA[{e['title']}]]></title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <pubDate>{pub_rss}</pubDate>
      <description><![CDATA[{e.get('excerpt', '')}]]></description>
      <category>{escape(e.get('category', 'Capital Markets'))}</category>
      <news:news>
        <news:publication>
          <news:name>Light Tower Group</news:name>
          <news:language>en</news:language>
        </news:publication>
        <news:publication_date>{pub_iso}</news:publication_date>
        <news:title><![CDATA[{e['title']}]]></news:title>
        <news:keywords>{escape(keywords)}</news:keywords>
      </news:news>
    </item>""")

    now_rss = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>{escape(FEED_TITLE)}</title>
    <link>{SITE_URL}</link>
    <description>{escape(FEED_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{now_rss}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{SITE_URL}/logo.png</url>
      <title>Light Tower Group</title>
      <link>{SITE_URL}</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>"""

    FEED_XML.write_text(xml, encoding="utf-8")
    print(f"  feed.xml updated ({len(items)} entries)")


def update_sitemap_xml():
    """Regenerate sitemap.xml from static pages + all article entries in insights.json."""
    data = []
    if INSIGHTS_JSON.exists():
        try:
            data = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    today = datetime.now().strftime("%Y-%m-%d")
    url_blocks = []

    for path, priority, freq in _SITEMAP_STATIC:
        url_blocks.append(
            f"  <url>\n"
            f"    <loc>{SITE_URL}{path}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    for article in data:
        slug = article.get("slug", "")
        if not slug:
            continue
        d = _parse_manifest_date(article.get("date", ""))
        lastmod = d.strftime("%Y-%m-%d")
        url_blocks.append(
            f"  <url>\n"
            f"    <loc>{SITE_URL}/insights/{slug}.html</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>never</changefreq>\n"
            f"    <priority>0.6</priority>\n"
            f"  </url>"
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(url_blocks)
        + "\n</urlset>"
    )
    SITEMAP_XML.write_text(sitemap, encoding="utf-8")
    print(f"  sitemap.xml updated ({len(url_blocks)} URLs)")


def git_commit_push(articles: list, dry_run: bool = False):
    """Commit new article files and push to trigger Netlify deploy."""
    if dry_run:
        print("  [DRY-RUN] Skipping git commit/push")
        return

    if not articles:
        return

    files = [f"insights/{a['slug']}.html" for a in articles]
    files += ["insights.json", "feed.xml", "sitemap.xml"]

    titles = "; ".join(a["title"][:40] for a in articles[:3])
    if len(articles) > 3:
        titles += f" (+{len(articles)-3} more)"

    try:
        subprocess.run(["git", "add"] + files, cwd=SITE_ROOT, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m",
             f"Daily CRE analysis ({len(articles)} articles): {titles}\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"],
            cwd=SITE_ROOT, check=True, capture_output=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=SITE_ROOT, check=True, capture_output=True)
        print(f"  Git: committed {len(articles)} articles and pushed \u2192 Netlify deploying")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        print(f"  [WARN] Git failed: {stderr[:200]}")


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 7: LINKEDIN
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def post_to_linkedin(article: dict, dry_run: bool = False) -> bool:
    """
    Post an article link share to LinkedIn via the UGC Posts API.

    Prerequisites (one-time setup):
      1. Create a LinkedIn app at https://www.linkedin.com/developers/apps
      2. Add the "Share on LinkedIn" product to your app
      3. Add http://localhost:8000/callback as a redirect URI
      4. Run: python linkedin_auth.py
         This opens a browser OAuth flow and saves LINKEDIN_ACCESS_TOKEN
         and LINKEDIN_PERSON_URN to scripts/.env automatically.

    Token expiry: LinkedIn access tokens expire after ~60 days.
    Re-run linkedin_auth.py when the token expires.
    """
    if dry_run:
        print(f"  [DRY-RUN] LinkedIn post text:\n  {article.get('linkedin_hook','')[:120]}...")
        return False

    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        print(
            "  [SKIP] LinkedIn not configured.\n"
            "         Add LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN to scripts/.env\n"
            "         or run: python linkedin_auth.py"
        )
        return False

    # Warn if the token is known to be expired
    token_expiry = os.environ.get("LINKEDIN_TOKEN_EXPIRY", "")
    if token_expiry:
        try:
            expiry_date = datetime.strptime(token_expiry, "%Y-%m-%d").date()
            days_left   = (expiry_date - datetime.now().date()).days
            if days_left <= 0:
                print(
                    f"  [WARN] LinkedIn token expired on {token_expiry}.\n"
                    "         Re-run: python linkedin_auth.py"
                )
                return False
            elif days_left <= 7:
                print(f"  [WARN] LinkedIn token expires in {days_left} day(s) — refresh soon.")
        except ValueError:
            pass

    page_url = f"{SITE_URL}/insights/{article['slug']}.html"

    # Build post text: hook + hashtags
    # Note: URL is carried by the article card — omitting from text body improves reach
    hashtags = " ".join(LINKEDIN_HASHTAGS[:6])
    hook = article.get('linkedin_hook', article['title'])
    # Ensure each sentence is on its own line for LinkedIn's algorithm
    hook = re.sub(r'\. ([A-Z])', r'.\n\n\1', hook)
    post_text = f"{hook}\n\n{hashtags}"

    payload = {
        "author":         LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary":    {"text": post_text},
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status":      "READY",
                    "description": {"text": article["meta_description"]},
                    "originalUrl": page_url,
                    "title":       {"text": article["title"]},
                }],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    try:
        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization":             f"Bearer {LINKEDIN_ACCESS_TOKEN}",
                "Content-Type":              "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            post_id = resp.headers.get("x-restli-id", "unknown")
            print(f"  LinkedIn: published (id: {post_id})")
            return True
        elif resp.status_code == 401:
            print(
                "  [WARN] LinkedIn 401 Unauthorized \u2014 token may have expired.\n"
                "         Re-run: python linkedin_auth.py"
            )
        else:
            print(f"  [WARN] LinkedIn {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [WARN] LinkedIn request failed: {e}")

    return False


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# PHASE 8: LOG
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def write_log(run_data: dict):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.insert(0, run_data)
    log = log[:120]   # keep ~4 months of daily runs
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# MAIN
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def main():
    parser = argparse.ArgumentParser(description="LTG Daily CRE News Agent")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score and write the article but do not publish or post")
    parser.add_argument("--force", action="store_true",
                        help="Skip the duplicate-slug check")
    parser.add_argument("--articles", type=int, default=5, metavar="N",
                        help="Number of articles to publish per run (default: 5, max: 10)")
    args = parser.parse_args()
    MAX_ARTICLES = max(1, min(args.articles, 10))

    start    = datetime.now(timezone.utc)
    run_data = {"run_at": start.isoformat(), "status": "started", "dry_run": args.dry_run}

    print(f"\n{'='*62}")
    print(f"  Light Tower Group \u2014 Daily News Agent")
    print(f"  {start.strftime('%Y-%m-%d %H:%M UTC')}"
          + ("  [DRY-RUN]" if args.dry_run else ""))
    print(f"{'='*62}\n")

    # \u2500 Phase 1: Gather \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("[1/8] Gathering stories...")
    all_stories = fetch_rss_stories() + fetch_newsapi_stories()
    run_data["raw_count"] = len(all_stories)

    # \u2500 Phase 2: Triage \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("\n[2/8] Triaging...")
    candidates = triage(all_stories)
    run_data["candidate_count"] = len(candidates)

    if not candidates:
        print("  No relevant CRE stories found today. Exiting.")
        run_data["status"] = "no_stories"
        write_log(run_data)
        return

    # \u2500 Phase 3: Score \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[3/8] Scoring {len(candidates)} stories...")
    ranked = score_stories(candidates)

    # \u2500 Phase 4: Enrich \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[4/8] Enriching up to {MAX_ARTICLES} candidates...")
    enriched_candidates = []
    checked = 0
    for candidate in ranked[:20]:  # scan top 20 to find MAX_ARTICLES non-dupes
        if len(enriched_candidates) >= MAX_ARTICLES:
            break
        checked += 1
        preview_slug = re.sub(r"[^a-z0-9]+", "-", candidate["title"].lower())[:50].strip("-")
        if not args.force and already_published(preview_slug):
            print(f"  [{checked}] Already published (slug preview '{preview_slug[:35]}'), skipping...")
            continue
        print(f"  [{checked}] Enriching: {candidate['title'][:65]}")
        enriched_candidates.append(enrich_story(candidate))

    if not enriched_candidates:
        print("  No fresh stories found after duplicate check. Exiting.")
        run_data["status"] = "already_published"
        write_log(run_data)
        return

    print(f"  Collected {len(enriched_candidates)} candidate(s) for article generation")

    # \u2500 Phase 5: Write \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[5/8] Generating {len(enriched_candidates)} article(s)...")
    articles = []
    for i, candidate in enumerate(enriched_candidates, 1):
        print(f"  Generating article {i}/{len(enriched_candidates)}: {candidate['title'][:60]}")
        try:
            article = generate_article(candidate)
        except Exception as e:
            print(f"  [WARN] Article {i} generation failed: {e} — skipping")
            continue

        if not args.force and already_published(article["slug"]):
            print(f"  Slug '{article['slug']}' already published, skipping...")
            continue

        print(f"  [{i}] Title:    {article['title']}")
        print(f"  [{i}] Slug:     {article['slug']}")
        print(f"  [{i}] Category: {article['category']}")
        articles.append(article)

    if not articles:
        print("  All generated articles had slug collisions or failed. Exiting.")
        run_data["status"] = "slug_collision"
        write_log(run_data)
        return

    print(f"  Successfully generated {len(articles)} article(s)")

    run_data["articles"] = [
        {"title": a["title"], "slug": a["slug"],
         "source": enriched_candidates[i]["source"],
         "source_url": enriched_candidates[i]["url"]}
        for i, a in enumerate(articles)
    ]
    run_data.update({
        "title":      articles[0]["title"],
        "slug":       articles[0]["slug"],
        "source":     enriched_candidates[0]["source"],
        "source_url": enriched_candidates[0]["url"],
    })

    # \u2500 Phase 6: Publish \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[6/8] Publishing {len(articles)} article(s)...")
    if not args.dry_run:
        INSIGHTS_DIR.mkdir(exist_ok=True)

        for article in articles:
            out = INSIGHTS_DIR / f"{article['slug']}.html"
            out.write_text(render_html(article), encoding="utf-8")
            print(f"  Saved: insights/{article['slug']}.html")

            # Generate branded social media image
            img_path = INSIGHTS_DIR / f"{article['slug']}_social.png"
            if generate_article_image(article['title'], article['subtitle'], img_path):
                article['social_image'] = str(img_path)
                print(f"  Image: insights/{article['slug']}_social.png")

            update_manifest(article)

        update_feed_xml()
        update_sitemap_xml()
        git_commit_push(articles, dry_run=False)
    else:
        for article in articles:
            print(f"  [DRY-RUN] Would save: insights/{article['slug']}.html")
        print(f"  [DRY-RUN] LinkedIn hook (article 1):\n  {articles[0].get('linkedin_hook','')}")

    # \u2500 Phase 7: LinkedIn \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("\n[7/8] LinkedIn (top-ranked article only)...")
    li_ok = post_to_linkedin(articles[0], dry_run=args.dry_run)
    run_data["linkedin_posted"] = li_ok

    # \u2500 Log \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    elapsed = round((datetime.now(timezone.utc) - start).total_seconds())
    run_data.update({
        "status":           "success",
        "elapsed_seconds":  elapsed,
        "articles_count":   len(articles),
    })
    write_log(run_data)

    print(f"\n{'='*62}")
    print(f"  DONE in {elapsed}s — published {len(articles)} article(s)")
    if not args.dry_run:
        for a in articles:
            print(f"  Article: {SITE_URL}/insights/{a['slug']}.html")
        print(f"  LinkedIn: {'posted (article 1)' if li_ok else 'skipped/failed'}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
