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
    RSS_FEEDS, FEDERAL_RSS_FEEDS, CRE_KEYWORDS, EXCLUDE_KEYWORDS,
    NEWSAPI_QUERIES, SITE_URL,
    FEED_TITLE, FEED_DESCRIPTION,
)
from enhanced_prompts import SYSTEM_PROMPT_ENHANCED, USER_PROMPT_TEMPLATE
from social_image_generator import generate_article_image
from linkedin_essay_agent import ESSAY_QUEUE, generate_essay_package, save_to_queue
from story_normalizer import has_reported_amount_at_least_ten_million, normalize_stories
from editorial_scoring import (
    daily_top_news_selection,
    generate_weekly_market_review,
    print_daily_selection_report,
    print_weekly_review_report,
)
from bucketed_editorial import (
    bucketed_volume_selection,
    print_bucketed_volume_report,
    route_story,
)
from editorial_store import (
    load_weekly_editorial_runs,
    save_editorial_run,
    save_weekly_review,
)
from content_governance import independent_quality_issues, load_insight_records, near_duplicate_matches
from editorial_voice import narrative_finance_issues, select_editorial_brief
from source_health import SourceHealthLedger

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
    ("/privacy.html",               "0.3", "yearly"),
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
LINKEDIN_PDF_QUEUE = SCRIPT_DIR / "linkedin_pdf_queue.json"
SOURCE_HEALTH_FILE = SITE_ROOT / "tmp" / "source_health.json"

# The original NYC and national CRE feed universe remains intact.  Federal
# feeds are additive and are fetched in the same run so major policy and
# banking events enter the existing editorial pipeline immediately.
ALL_RSS_FEEDS = RSS_FEEDS + FEDERAL_RSS_FEEDS

ANTHROPIC_API_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY      = os.environ.get("DEEPSEEK_API_KEY", "")
NEWSAPI_KEY           = os.environ.get("NEWSAPI_KEY", "")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN   = os.environ.get("LINKEDIN_PERSON_URN", "")


def redact_secret_text(value: object) -> str:
    """Return log-safe text with API keys and bearer tokens removed."""
    text = str(value)
    text = re.sub(
        r"([?&](?:apiKey|key|token|access_token)=)[^&\s)]+",
        r"\1[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsk-[A-Za-z0-9._-]+", "sk-[REDACTED]", text)
    return text


MOJIBAKE_RE = re.compile("[" + chr(0x00E2) + chr(0x00C3) + chr(0xFFFD) + "]")


def assert_no_mojibake(label: str, payload: object) -> None:
    """Fail fast when generated user-visible content has obvious encoding damage."""
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    match = MOJIBAKE_RE.search(text)
    if match:
        start = max(match.start() - 40, 0)
        end = min(match.end() + 40, len(text))
        snippet = text[start:end].replace("\n", " ")
        raise ValueError(f"{label} contains possible mojibake near: {snippet}")


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
    failed_feeds = 0
    empty_feeds = 0
    attempted_feeds = 0
    failures = []
    health = SourceHealthLedger(SOURCE_HEALTH_FILE)
    for source_name, feed_url in ALL_RSS_FEEDS:
        if health.is_quarantined(source_name):
            print(f"  [SKIP] RSS {source_name} is temporarily quarantined after repeated failures")
            continue
        attempted_feeds += 1
        started = time.perf_counter()
        try:
            feed = feedparser.parse(
                feed_url,
                request_headers={"User-Agent": "LightTowerGroup-NewsAgent/1.0"},
            )
            if getattr(feed, "bozo", False) and not getattr(feed, "entries", None):
                # An empty/bozo feed can mean a harmless feed-format change or
                # a temporary network restriction. It is not evidence that a
                # specific publisher is down, so retry it on the next run.
                empty_feeds += 1
                health.record_empty(
                    source_name,
                    int((time.perf_counter() - started) * 1000),
                    "feedparser returned no entries",
                )
                continue
            # Score every recent entry the source exposes. The 36-hour recency
            # filter below, not an arbitrary per-feed headline cap, determines
            # the daily candidate universe.
            for entry in feed.entries:
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
            health.record_success(source_name, len(getattr(feed, "entries", []) or []), int((time.perf_counter() - started) * 1000))
        except Exception as e:
            failed_feeds += 1
            error = redact_secret_text(e)
            failures.append((source_name, error, int((time.perf_counter() - started) * 1000)))
            print(f"  [WARN] RSS {source_name}: {error}")
        time.sleep(0.05)

    # Do not convert a computer-wide connectivity problem into dozens of
    # independent publisher failures. A shared outage should preserve retry
    # access to every feed on the next scheduled run.
    shared_outage = attempted_feeds >= 8 and len(failures) >= max(4, attempted_feeds // 2)
    if shared_outage:
        released = health.release_quarantines()
        for source_name, error, elapsed_ms in failures:
            health.record_transient_outage(source_name, error, elapsed_ms)
        print(
            f"  [WARN] Shared RSS connectivity outage: {len(failures)}/{attempted_feeds} feeds failed; "
            f"no publishers quarantined ({released} prior quarantine(s) released)"
        )
    else:
        for source_name, error, elapsed_ms in failures:
            health.record_failure(source_name, error, elapsed_ms)

    try:
        health.save()
    except OSError as e:
        print(f"  [WARN] Could not persist RSS source health: {redact_secret_text(e)}")

    print(f"  RSS: {len(stories)} raw stories from {len(ALL_RSS_FEEDS)} feeds ({len(FEDERAL_RSS_FEEDS)} federal)")
    if failed_feeds:
        print(f"  [WARN] RSS feed exceptions: {failed_feeds}/{attempted_feeds} attempted")
    if empty_feeds:
        print(f"  [INFO] RSS feeds with no parseable entries: {empty_feeds}/{attempted_feeds}; they will be retried next run")
    return stories


def fetch_newsapi_stories(lookback_hours: int = 24) -> list:
    """Supplement with NewsAPI.org keyword search (free tier: 100 req/day)."""
    if not NEWSAPI_KEY:
        return []

    stories = []
    from_date = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime("%Y-%m-%d")

    # Use a broader additive set while staying comfortably inside NewsAPI's
    # free-tier request ceiling. RSS remains the primary source of truth.
    for query in NEWSAPI_QUERIES[:8]:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "from":     from_date,
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
            print(f"  [WARN] NewsAPI query '{query[:30]}': {redact_secret_text(e)}")
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


def triage(stories: list, recent_hours: int = 36) -> list:
    relevant = [s for s in stories if s["url"] and _is_cre_relevant(s) and _is_recent(s, recent_hours)]
    unique   = _deduplicate(relevant)
    print(f"  Triage: {len(stories)} raw \u2192 {len(relevant)} relevant \u2192 {len(unique)} unique")
    return unique


DAILY_TOP_NEWS_KEYWORDS = CRE_KEYWORDS + [
    "bank", "banks", "banking", "credit", "loan losses", "loss reserves",
    "private credit", "private equity", "fundraise", "fund closes", "debt fund",
    "m&a", "merger", "acquisition", "takeover", "portfolio sale", "building sale",
    "capital placement", "financing", "refinancing", "recapitalization",
    "federal reserve", "fed", "rate cut", "rate hike", "treasury yield", "inflation",
    "reit", "earnings", "guidance", "shares", "cmbs", "special servicing",
    "default", "foreclosure", "bankruptcy", "distress", "note sale",
    "blackstone", "brookfield", "apollo", "starwood", "ares", "kkr",
    "jpmorgan", "goldman", "wells fargo", "morgan stanley", "sl green",
]

_DAILY_FINANCE_SIGNALS = (
    "bank", "credit", "loan", "lender", "private equity", "private credit",
    "family office", "pension fund", "sovereign wealth", "fund", "refinanc", "financ",
    "acquisition", "acquire", "purchased", "purchas", "merger", "m&a", "reit",
    "equity investment", "equity commitment", "preferred equity", "mezzanine", "joint venture",
    "recapitaliz", "invested", "invests", "capital commitment", "construction loan",
    "fed", "federal reserve", "treasury", "cmbs", "default", "distress",
    "foreclosure", "bankruptcy", "policy", "zoning", "regulation",
)
_DAILY_PROPERTY_OR_MARKET_SIGNALS = (
    "commercial real estate", "real estate", "multifamily", "office", "industrial",
    "warehouse", "retail", "hotel", "data center", "housing", "development", "apartment",
    "student housing", "senior housing", "medical office", "life science", "self-storage",
    "land parcel", "mixed-use", "shopping center", "manufactured housing",
    "mortgage", "agency debt", "fannie", "freddie", "hud", "cre ",
)
_DAILY_INSTITUTIONAL_SIGNALS = (
    "blackstone", "brookfield", "apollo", "ares", "kkr", "starwood", "carlyle",
    "jpmorgan", "goldman", "wells fargo", "morgan stanley", "bank of america",
    "citigroup", "federal reserve", "fdic", "treasury", "reit", "sec ", "family office",
    "pension fund", "sovereign wealth", "investment management", "asset manager",
)

_DAILY_TRANSACTION_SIGNALS = (
    "acquisition", "acquired", "acquires", "purchased", "purchases", "bought", "sale",
    "sold", "investment", "invests", "invested", "loan", "lending", "financing",
    "refinancing", "equity", "joint venture", "recapitalization", "capital commitment",
)

# Additive policy signals. These do not alter the existing NYC relevance test;
# they open a second intake path for federal action and a third path for
# government developments in the ten tracked MSAs.
_FEDERAL_AUTHORITY_SIGNALS = (
    "federal reserve", "fdic", "occ", "securities and exchange commission", "sec ",
    "treasury department", "department of the treasury", "fhfa", "hud ",
    "federal housing administration", "federal register", "congress", "senate",
    "house financial services", "cfpb", "cftc",
)
_GOVERNMENT_ACTION_SIGNALS = (
    "rule", "regulation", "guidance", "enforcement", "testimony", "legislation",
    "bill", "ordinance", "zoning", "rezoning", "tax credit", "budget", "appropriation",
    "executive order", "public hearing", "comment period", "planning commission",
    "city council", "mayor", "governor", "county commission", "land use",
)
_TOP_MSA_SIGNALS = (
    "new york", "nyc", "manhattan", "brooklyn", "los angeles", "chicago", "dallas",
    "fort worth", "dfw", "houston", "washington", "district of columbia", "miami",
    "fort lauderdale", "atlanta", "boston", "san francisco", "bay area",
)


def _is_federal_or_msa_government_relevant(text: str) -> bool:
    """Admit government stories only when they have a CRE/finance transmission path."""
    has_finance = any(signal in text for signal in _DAILY_FINANCE_SIGNALS)
    has_property = any(signal in text for signal in _DAILY_PROPERTY_OR_MARKET_SIGNALS)
    has_action = any(signal in text for signal in _GOVERNMENT_ACTION_SIGNALS)
    has_federal_authority = any(signal in text for signal in _FEDERAL_AUTHORITY_SIGNALS)
    has_msa = any(signal in text for signal in _TOP_MSA_SIGNALS)
    # Federal stories may be macro, but must still show a banking, credit,
    # housing, capital-markets, or CRE transmission path.
    federal_path = has_federal_authority and has_action and has_finance
    msa_path = has_msa and has_action and (has_property or has_finance)
    return federal_path or msa_path


def _is_material_cre_transaction(text: str) -> bool:
    """Allow concrete CRE deal announcements into scoring, without admitting generic finance news."""
    has_property = any(signal in text for signal in _DAILY_PROPERTY_OR_MARKET_SIGNALS)
    has_transaction = any(signal in text for signal in _DAILY_TRANSACTION_SIGNALS)
    # $10M is the desk's normal transaction-intake threshold.  We also admit a
    # named institutional transaction without an amount because RSS headlines
    # often omit a figure that is present in the article itself; scoring still
    # decides whether it is significant enough to publish.
    has_material_amount = has_reported_amount_at_least_ten_million(text)
    has_institution = any(signal in text for signal in _DAILY_INSTITUTIONAL_SIGNALS)
    return has_property and has_transaction and (has_material_amount or has_institution)


def _is_daily_top_news_relevant(story: dict) -> bool:
    text = (story.get("title", "") + " " + story.get("summary", "")).lower()
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    has_finance = any(signal in text for signal in _DAILY_FINANCE_SIGNALS)
    has_property_or_market = any(signal in text for signal in _DAILY_PROPERTY_OR_MARKET_SIGNALS)
    has_institutional_actor = any(signal in text for signal in _DAILY_INSTITUTIONAL_SIGNALS)
    # Require a real CRE/banking/PE transmission path. A passing keyword alone
    # (for example, "industrial" in a defense story) is not enough.
    return (
        (has_property_or_market and has_finance)
        or (has_finance and has_institutional_actor)
        or _is_material_cre_transaction(text)
        or _is_federal_or_msa_government_relevant(text)
    )


def triage_daily_top_news(stories: list, recent_hours: int = 36) -> list:
    """Broader triage for daily top-news selection across CRE, banking, finance, and PE."""
    relevant = [
        s for s in stories
        if s.get("url") and _is_daily_top_news_relevant(s) and _is_recent(s, recent_hours)
    ]
    unique = _deduplicate(relevant)
    print(f"  Daily top-news triage: {len(stories)} raw \u2192 {len(relevant)} relevant \u2192 {len(unique)} unique")
    return unique


def triage_bucketed_volume(stories: list, recent_hours: int = 36) -> list:
    """Admit every recent story that belongs to at least one editorial bucket.

    The bucket scorer performs the tougher evidence and quality decisions. This
    intake stage intentionally avoids using a single CRE-debt-shaped filter that
    would hide a valid bank, PE, or policy story before it can be scored.
    """
    relevant = []
    for story in stories:
        text = (story.get("title", "") + " " + story.get("summary", "")).lower()
        if not story.get("url") or not _is_recent(story, recent_hours):
            continue
        if any(kw in text for kw in EXCLUDE_KEYWORDS):
            continue
        if route_story(story).get("primary_bucket"):
            relevant.append(story)
    unique = _deduplicate(relevant)
    print(f"  Bucketed-volume triage: {len(stories)} raw \u2192 {len(relevant)} relevant \u2192 {len(unique)} unique")
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
        print(f"  [WARN] Scoring failed ({redact_secret_text(e)}), using raw order")
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
        print(f"  [WARN] trafilatura failed for {url[:50]}: {redact_secret_text(e)}")
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
    lane_context = (
        f"Editorial lane: {story.get('source_lane', 'market')} | "
        f"MSA government markets: {', '.join(story.get('entities', {}).get('msa_government_markets', [])) or 'not tagged'} | "
        f"Policy actions: {', '.join(story.get('entities', {}).get('policy_actions', [])) or 'none'}"
    )
    addresses_block = "\n".join(part for part in (addresses_block, lane_context) if part)

    editorial_brief = select_editorial_brief({
        "slug": story.get("url", ""),
        "title": story.get("title", ""),
        "category": "Capital Markets",
    })
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=story['title'],
        source=story['source'],
        url=story['url'],
        published_date=story.get('published', 'Unknown'),
        summary=story['summary'],
        full_text=full_text_block,
        addresses_block=addresses_block,
        today=now_utc.strftime('%B %d, %Y'),
        voice_brief=json.dumps(editorial_brief, ensure_ascii=False),
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
    article = _extract_article_json(data["choices"][0]["message"]["content"])
    # The writer's self-assessment is not trusted. Repair drafts against the
    # same independent gate used immediately before publication.
    for _ in range(2):
        control_findings = _article_control_findings(article)
        if not control_findings:
            break
        revision = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "max_tokens": 5200,
                "temperature": 0.15,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_ENHANCED},
                    {"role": "user", "content": user_prompt},
                    {
                        "role": "user",
                        "content": _article_revision_prompt(article, control_findings),
                    },
                ],
            },
            timeout=120,
        )
        revision.raise_for_status()
        article = _extract_article_json(revision.json()["choices"][0]["message"]["content"])
    article["date"]       = now_utc.strftime("%B %d, %Y")
    article["date_iso"]   = now_utc.isoformat()
    article["source_url"] = story["url"]
    article["source_name"] = story["source"]
    article["source_lane"] = story.get("source_lane", "market")
    article["msa_government_markets"] = story.get("entities", {}).get("msa_government_markets", [])
    article["policy_actions"] = story.get("entities", {}).get("policy_actions", [])
    return article


def _extract_article_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON object found in DeepSeek article response")
    return json.loads(match.group())


def _article_revision_prompt(article: dict, issues: list[str]) -> str:
    return """\
The previous article failed an independent publication control check. Rewrite
the COMPLETE JSON article, preserving only source-grounded facts. Correct every
listed issue and include a complete narrative_ledger. The body_html must be
800-1,050 words and never under 700 words. Expand through source-grounded
analysis of mechanism, incentives, constraints, and open questions—not filler.
Do not explain the revision, invent a scene, invent a source, or use a generic
template phrase.

CONTROL FINDINGS
{issues}

CURRENT ARTICLE JSON
{article}
""".format(
        issues=json.dumps(issues, ensure_ascii=False),
    article=json.dumps(article, ensure_ascii=False),
)


def _article_control_findings(article: dict) -> list[str]:
    """Return the independent publication checks a draft must clear."""
    findings = independent_quality_issues(article, require_sections=False)
    findings.extend(narrative_finance_issues(article.get("narrative_ledger")))
    return list(dict.fromkeys(findings))


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
              onclick='navigator.clipboard.writeText({js_url}).then(function(){{this.textContent="Copied!"}}.bind(this))'>Copy Link</button>
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
    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": article["title"],
        "description": article["meta_description"],
        "url": page_url,
        "datePublished": article["date_iso"],
        "dateModified": article["date_iso"],
        "author": {
            "@type": "Person",
            "name": "Benjamin Rohr",
            "url": f"{SITE_URL}/#principal",
        },
        "publisher": {
            "@type": "Organization",
            "name": "Light Tower Group",
            "url": SITE_URL,
            "logo": f"{SITE_URL}/favicon.svg",
        },
        "image": social_image_url,
        "mainEntityOfPage": page_url,
        "articleSection": article.get("category", "Market Analysis"),
        "keywords": article.get("tags", []),
    }, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(article['title'])} | Light Tower Group</title>
  <meta name="description" content="{esc(article['meta_description'])}">
  <meta name="robots" content="index, follow">
  <meta name="author" content="Benjamin Rohr, Light Tower Group">
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

  <script type="application/ld+json">
{schema_json}
  </script>

  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --black: #f5f4f0;
      --navy: #ffffff;
      --gold:     #c9a84c;
      --gold-dim: rgba(0,0,0,0.08);
      --white: #121212;
      --muted: #555555;
      --body-txt: #333333;
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
      font-family: var(--sans); font-size: 1.1rem; letter-spacing: 0.18em;
      color: var(--gold); text-decoration: none; text-transform: uppercase;
      font-weight: 700; margin-right: auto;
    }}
    .nav-links {{ display: flex; gap: 2.8rem; }}
    .nav-links a {{
      font-family: var(--sans); font-size: 0.9rem; color: var(--muted);
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
    .article-wrap {{ max-width: 780px; margin: 0 auto; padding: 5rem 2.5rem 8rem; }}

    /* ── Header ── */
    .article-category {{
      font-family: var(--sans); font-size: 0.8rem; letter-spacing: 0.2em;
      text-transform: uppercase; color: var(--gold); margin-bottom: 1.3rem;
      font-weight: 600;
    }}
    .article-title {{
      font-family: var(--serif);
      font-size: clamp(2.4rem, 6vw, 3.8rem);
      font-weight: normal; line-height: 1.15;
      color: var(--white); margin-bottom: 1rem;
    }}
    .article-subtitle {{
      font-size: 1.6rem; color: var(--muted); font-style: italic;
      line-height: 1.65; margin-bottom: 1.8rem;
    }}
    .article-byline {{
      font-family: var(--sans); font-size: 1rem; color: var(--muted);
      display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 2rem;
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
    .share-tw  {{ color: var(--white); border-color: rgba(0,0,0,0.18); }}
    .share-tw:hover  {{ background: rgba(255,255,255,0.07); }}
    .share-copy {{ color: var(--gold); border-color: var(--gold-dim); }}
    .share-copy:hover {{ background: rgba(201,168,76,0.1); }}

    /* ── Body ── */
    .article-body {{ font-size: 1.3rem; line-height: 1.9; }}
    .article-body p {{
      margin-bottom: 1.45rem; color: var(--body-txt);
    }}
    .article-body strong {{ color: var(--white); }}
    .article-body a {{ color: var(--gold); }}

    /* ── Tags ── */
    .article-tags {{ display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 2.5rem 0 1.5rem; }}
    .tag {{
      font-family: var(--sans); font-size: 0.75rem; letter-spacing: 0.1em;
      text-transform: uppercase; color: var(--muted);
      border: 1px solid rgba(138,155,176,0.28); padding: 0.35rem 0.8rem;
      border-radius: 2px;
      font-weight: 500;
    }}

    /* ── Sources ── */
    .sources-block {{
      margin-top: 3.5rem; padding-top: 2rem;
      border-top: 1px solid var(--gold-dim);
    }}
    .sources-block h3 {{
      font-family: var(--sans); font-size: 0.8rem; letter-spacing: 0.15em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 1rem;
      font-weight: 600;
    }}
    .sources-block ul {{ list-style: none; }}
    .sources-block li {{ font-size: 0.95rem; margin-bottom: 0.5rem; }}
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
    .nav-mobile {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(245,244,240,0.98); padding: 5rem 2rem 2rem; flex-direction: column; gap: 1.5rem; z-index: 200; }}
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
  <link rel="stylesheet" href="/site.css">
  <script src="/site.js" defer></script>
</head>
<body>

    <nav class="site-nav" role="navigation" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="/" class="nav-logo" aria-label="Light Tower Group home">Light Tower Group</a>
      <div class="nav-links">
        <a href="/#practice">Practice</a>
        <a href="/#advantage">Advantage</a>
        <a href="/#leadership">Leadership</a>
        <a href="/#faq">FAQ</a>
        <a href="/insights.html">Insights</a>
        <a href="/buildings.html">Buildings</a>
        <a href="/services.html">Services</a>
        <a href="/about.html">About</a>
        <a href="/#contact">Contact</a>
        <button class="nav-cta" onclick="openLTGChat()">Initiate Mandate</button>
      </div>
      <button class="nav-menu-btn" id="nav-menu-btn" aria-label="Open menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
    <div class="nav-mobile" id="nav-mobile" role="menu">
      <a href="/#practice">Practice</a>
      <a href="/#advantage">Advantage</a>
      <a href="/#leadership">Leadership</a>
      <a href="/#faq">FAQ</a>
      <a href="/insights.html">Insights</a>
      <a href="/buildings.html">Buildings</a>
      <a href="/services.html">Services</a>
      <a href="/about.html">About</a>
      <a href="/#contact">Contact</a>
      <button class="nav-mobile-cta" onclick="openLTGChat()">Initiate Mandate</button>
    </div>
  </nav>

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
      <a href="/#contact">Contact</a>
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
    assert_no_mojibake("manifest entry", entry)
    # Remove any existing entry with same slug
    data = [e for e in data if e.get("slug") != article["slug"]]
    data.insert(0, entry)

    manifest_json = json.dumps(data, indent=2, ensure_ascii=False)
    assert_no_mojibake("insights.json", manifest_json)
    INSIGHTS_JSON.write_text(manifest_json, encoding="utf-8")
    print(f"  insights.json updated ({len(data)} total entries)")


def generate_carousel_pdf(article_slug: str, dry_run: bool = False):
    """Legacy manual carousel command; the daily flow now creates article PDFs."""
    try:
        from auto_carousel_generator import generate_carousel_for_article
        pdf_path = generate_carousel_for_article(article_slug, dry_run=dry_run)
        if pdf_path:
            print(f"  ✓ Carousel PDF created: {article_slug}_carousel.pdf")
        else:
            print(f"  [WARN] Carousel PDF generation failed for {article_slug}")
    except Exception as e:
        print(f"  [WARN] Carousel PDF generation error: {e}")


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


def git_commit_push(articles: list, dry_run: bool = False) -> dict:
    """Commit and verify deployment, returning an explicit, log-safe result."""
    result = {
        "attempted": False, "commit_created": False, "commit_sha": None,
        "push_ok": False, "remote_main_sha": None, "error": None,
    }
    if dry_run:
        print("  [DRY-RUN] Skipping git commit/push")
        return result

    if not articles:
        return result

    result["attempted"] = True

    files = []
    for article in articles:
        slug = article["slug"]
        candidates = [
            f"insights/{slug}.html",
            f"insights/{slug}_social.png",
            f"insights/{slug}_article.pdf",
            f"insights/{slug}_article-data.json",
            f"insights/linkedin-post-{slug}.txt",
        ]
        files.extend(path for path in candidates if (SITE_ROOT / path).exists())
    files += ["insights.json", "feed.xml", "sitemap.xml"]
    if ESSAY_QUEUE.exists():
        files.append(str(ESSAY_QUEUE.relative_to(SITE_ROOT)))

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
        result["commit_created"] = True
        result["commit_sha"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=SITE_ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
        # The scheduled agent may run from a delivery branch rather than the
        # local `main` branch.  Push the commit we just created (HEAD) to the
        # deployment branch explicitly; `git push origin main` would otherwise
        # push the stale local main branch and leave the new articles stranded.
        subprocess.run(
            ["git", "push", "origin", "HEAD:refs/heads/main"],
            cwd=SITE_ROOT,
            check=True,
            capture_output=True,
        )
        remote_sha = subprocess.run(
            ["git", "ls-remote", "--exit-code", "origin", "refs/heads/main"],
            cwd=SITE_ROOT, check=True, capture_output=True, text=True,
        ).stdout.split()[0]
        result["remote_main_sha"] = remote_sha
        if remote_sha != result["commit_sha"]:
            raise RuntimeError("origin/main did not resolve to the commit created by this run")
        result["push_ok"] = True
        print(f"  Git: committed {len(articles)} articles, pushed, and verified origin/main")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        result["error"] = redact_secret_text(stderr or str(e))[:300]
    except Exception as e:
        result["error"] = redact_secret_text(e)[:300]

    if not result["push_ok"]:
        print(f"  [ERROR] Git deployment failed: {result['error'] or 'unknown git error'}")
    return result


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
    package = article.get("linkedin_essay_package") or {}
    essay_text = (
        package.get("linkedin_essay")
        or article.get("linkedin_essay")
        or article.get("linkedin_hook")
        or article["title"]
    )
    essay_text = essay_text.strip()
    if len(essay_text) > 2950:
        essay_text = essay_text[:2940].rstrip()

    if dry_run:
        print(f"  [DRY-RUN] LinkedIn essay text:\n  {essay_text[:700]}...")
        return False

    if package:
        overall_score = ((package.get("quality_score") or {}).get("overall") or 0)
        review = package.get("editorial_review") or {}
        if (
            package.get("fallback")
            or overall_score < 8
            or not package.get("publish_ready")
            or review.get("status") != "ready_for_review"
        ):
            print(
                "  [SKIP] LinkedIn Essay Desk package did not meet the independent editorial gate; "
                "saved to queue for review instead."
            )
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

    # The Essay Desk writes the social-native post. The URL is carried by the
    # article card; the richer first comment is saved in the content queue.
    post_text = essay_text

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
            print(f"  [WARN] LinkedIn {resp.status_code}: {redact_secret_text(resp.text)[:200]}")
    except Exception as e:
        print(f"  [WARN] LinkedIn request failed: {redact_secret_text(e)}")

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


def write_linkedin_pdf_queue(articles: list) -> None:
    """Persist the exact daily article order for paced LinkedIn document posts."""
    queue = {
        "date": datetime.now().astimezone().date().isoformat(),
        "slugs": [article["slug"] for article in articles],
        "count": len(articles),
    }
    LINKEDIN_PDF_QUEUE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    print(f"  LinkedIn PDF queue updated ({queue['count']} slots)")


def safe_queue_pdf_generation(article: dict):
    """Create the final Insight as a LinkedIn-ready article document PDF."""
    if not article.get("body_html"):
        return
    try:
        from pdf_queue import queue_article_pdf_generation
    except Exception as e:
        print(f"  [WARN] PDF queue unavailable; skipping article PDF for {article.get('slug')}: {redact_secret_text(e)}")
        return
    try:
        queue_article_pdf_generation(
            article_html=article["body_html"],
            article_data=article,
            output_dir=str(INSIGHTS_DIR),
        )
    except Exception as e:
        print(f"  [WARN] PDF queue failed for {article.get('slug')}: {redact_secret_text(e)}")


def safe_post_linkedin_pdfs(articles: list, dry_run: bool = False) -> dict:
    """Publish every generated carousel PDF as a native LinkedIn document post."""
    try:
        from linkedin_pdf_post import post_article_pdfs
    except Exception as e:
        print(f"  [WARN] LinkedIn PDF poster unavailable: {redact_secret_text(e)}")
        return {"ok": False, "posted_count": 0, "attempted_count": len(articles), "error": str(e)}

    try:
        return post_article_pdfs(articles, dry_run=dry_run)
    except Exception as e:
        print(f"  [WARN] LinkedIn PDF batch failed: {redact_secret_text(e)}")
        return {"ok": False, "posted_count": 0, "attempted_count": len(articles), "error": str(e)}


def run_weekly_review(args) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    runs = load_weekly_editorial_runs()
    print(f"\n[Weekly Review] Loaded {len(runs)} editorial run file(s) for this week")
    review = generate_weekly_market_review(runs, api_key=DEEPSEEK_API_KEY, today=today)
    path = save_weekly_review(review)
    print_weekly_review_report(review)
    print(f"\nSaved weekly review: {path.relative_to(SITE_ROOT)}")


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
                        help="Number of articles to publish per run (default: 5, max: 30)")
    parser.add_argument("--no-limit", action="store_true",
                        help="In bucketed-volume mode, publish every qualifying non-duplicate story")
    parser.add_argument("--lookback-hours", type=int, default=36, metavar="H",
                        help="Story recency window in hours (default: 36; use 168 for a seven-day backfill)")
    parser.add_argument("--linkedin-length", choices=["standard", "edge", "compressed"],
                        default="standard",
                        help="Essay Desk length mode for LinkedIn output")
    parser.add_argument("--auto-post-linkedin", action="store_true",
                        help="Post the Essay Desk LinkedIn essay automatically after publishing")
    parser.add_argument("--auto-post-linkedin-pdfs", action="store_true",
                        help="Post every generated carousel PDF as a native LinkedIn document post")
    parser.add_argument("--selection-mode", choices=["legacy", "daily-top-news", "bucketed-volume"],
                        default="legacy",
                        help="Story selection mode. legacy preserves current scheduled behavior.")
    parser.add_argument("--shadow", action="store_true",
                        help="Score and write the full editorial audit without generating or publishing articles")
    parser.add_argument("--weekly-review", action="store_true",
                        help="Generate a Friday State of the Markets Review from this week's editorial runs")
    args = parser.parse_args()
    if args.weekly_review:
        run_weekly_review(args)
        return
    MAX_ARTICLES = max(1, min(args.articles, 30))
    article_limit = None if args.no_limit and args.selection_mode == "bucketed-volume" else MAX_ARTICLES
    LOOKBACK_HOURS = max(1, args.lookback_hours)

    start    = datetime.now(timezone.utc)
    run_data = {"run_at": start.isoformat(), "status": "started", "dry_run": args.dry_run}
    known_insights = load_insight_records(SITE_ROOT)

    print(f"\n{'='*62}")
    print(f"  Light Tower Group \u2014 Daily News Agent")
    print(f"  {start.strftime('%Y-%m-%d %H:%M UTC')}"
          + ("  [DRY-RUN]" if args.dry_run else ""))
    print(f"  Selection mode: {args.selection_mode}")
    print(f"  Lookback window: {LOOKBACK_HOURS} hours")
    if args.selection_mode == "bucketed-volume":
        print(f"  Publishing limit: {'none (all qualified stories)' if article_limit is None else article_limit}")
    if args.shadow:
        print("  [SHADOW MODE] No articles will be generated or published")
    print(f"{'='*62}\n")

    # \u2500 Phase 1: Gather \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("[1/8] Gathering stories...")
    all_stories = fetch_rss_stories() + fetch_newsapi_stories(LOOKBACK_HOURS)
    run_data["raw_count"] = len(all_stories)
    run_data["lookback_hours"] = LOOKBACK_HOURS

    # \u2500 Phase 2: Triage \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("\n[2/8] Triaging...")
    if args.selection_mode == "daily-top-news":
        candidates = triage_daily_top_news(all_stories, LOOKBACK_HOURS)
    elif args.selection_mode == "bucketed-volume":
        candidates = triage_bucketed_volume(all_stories, LOOKBACK_HOURS)
    else:
        candidates = triage(all_stories, LOOKBACK_HOURS)
    run_data["candidate_count"] = len(candidates)
    run_data["selection_mode"] = args.selection_mode

    if not candidates:
        print("  No relevant stories found for any editorial bucket. Exiting.")
        run_data["status"] = "no_stories"
        write_log(run_data)
        return

    # \u2500 Phase 3: Score \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[3/8] Scoring {len(candidates)} stories...")
    editorial_selection = None
    if args.selection_mode == "daily-top-news":
        normalized_candidates = normalize_stories(candidates)
        print(f"  Normalized {len(normalized_candidates)} candidate(s) for daily top-news scoring")
        editorial_selection = daily_top_news_selection(
            normalized_candidates,
            article_count=MAX_ARTICLES,
            api_key=DEEPSEEK_API_KEY,
            today=start.date().isoformat(),
        )
        print_daily_selection_report(editorial_selection, limit=MAX_ARTICLES)
        audit_payload = {
            "run_at": start.isoformat(),
            "date": start.date().isoformat(),
            "selection_mode": args.selection_mode,
            "dry_run": args.dry_run,
            "raw_count": len(all_stories),
            "candidate_count": len(candidates),
            "articles_requested": MAX_ARTICLES,
            **editorial_selection,
        }
        audit_path = save_editorial_run(audit_payload, run_date=start.date())
        print(f"  Editorial audit saved: {audit_path.relative_to(SITE_ROOT)}")
        ranked = [item["candidate"] for item in editorial_selection["selected_stories"]]
    elif args.selection_mode == "bucketed-volume":
        normalized_candidates = normalize_stories(candidates)
        print(f"  Normalized {len(normalized_candidates)} candidate(s) for bucketed-volume scoring")
        editorial_selection = bucketed_volume_selection(
            normalized_candidates,
            article_limit=article_limit,
            api_key=DEEPSEEK_API_KEY,
            today=start.date().isoformat(),
        )
        print_bucketed_volume_report(editorial_selection)
        audit_payload = {
            "run_at": start.isoformat(),
            "date": start.date().isoformat(),
            "selection_mode": args.selection_mode,
            "dry_run": args.dry_run,
            "shadow": args.shadow,
            "raw_count": len(all_stories),
            "candidate_count": len(candidates),
            "article_limit": article_limit,
            **editorial_selection,
        }
        audit_path = save_editorial_run(audit_payload, run_date=start.date())
        print(f"  Editorial audit saved: {audit_path.relative_to(SITE_ROOT)}")
        ranked = [item["candidate"] for item in editorial_selection["selected_stories"]]
        run_data["bucket_counts"] = editorial_selection.get("bucket_counts", {})
        run_data["decision_counts"] = editorial_selection.get("decision_counts", {})
        run_data["review_candidate_count"] = len(editorial_selection.get("review_stories", []))
    else:
        ranked = score_stories(candidates)

    if args.selection_mode == "bucketed-volume" and args.shadow:
        run_data.update({
            "status": "shadow_complete",
            "publishable_candidate_count": len(ranked),
            "editorial_audit": str(audit_path.relative_to(SITE_ROOT)),
        })
        write_log(run_data)
        print("  Shadow run complete. No articles were generated or published.")
        return

    if args.selection_mode == "bucketed-volume" and not ranked:
        print("  No stories cleared their bucket publication threshold. Exiting.")
        run_data["status"] = "no_bucket_eligible_stories"
        write_log(run_data)
        return

    # \u2500 Phase 4: Enrich \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[4/8] Enriching {'all qualified' if article_limit is None else f'up to {article_limit}'} candidates...")
    enriched_candidates = []
    checked = 0
    candidate_pool = ranked if args.selection_mode in {"daily-top-news", "bucketed-volume"} else ranked[:20]
    for candidate in candidate_pool:  # scan top 20 legacy stories, or final daily top-news selections
        if article_limit is not None and len(enriched_candidates) >= article_limit:
            break
        checked += 1
        preview_slug = re.sub(r"[^a-z0-9]+", "-", candidate["title"].lower())[:50].strip("-")
        if not args.force and already_published(preview_slug):
            print(f"  [{checked}] Already published (slug preview '{preview_slug[:35]}'), skipping...")
            continue
        print(f"  [{checked}] Enriching: {candidate['title'][:65]}")
        enriched_candidates.append(enrich_story(candidate))

    if not enriched_candidates:
        print("  No unpublished qualifying stories remained after duplicate checks. Exiting.")
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
            print(f"  [WARN] Article {i} generation failed: {redact_secret_text(e)} — skipping")
            continue

        try:
            assert_no_mojibake(f"article {i}", article)
        except ValueError as e:
            print(f"  [WARN] Article {i} failed content QA: {redact_secret_text(e)} -- skipping")
            continue

        independent_errors = _article_control_findings(article)
        narrative_errors = []
        duplicate_errors = near_duplicate_matches(article.get("title", ""), known_insights)
        if independent_errors or narrative_errors or duplicate_errors:
            reasons = independent_errors + narrative_errors + duplicate_errors
            print(f"  [WARN] Article {i} held by independent quality gate: {'; '.join(reasons[:2])}")
            continue

        # The ledger is editorial control data, not public-page content.
        article.pop("narrative_ledger", None)

        if not args.force and already_published(article["slug"]):
            print(f"  Slug '{article['slug']}' already published, skipping...")
            continue

        print(f"  [{i}] Title:    {article['title']}")
        print(f"  [{i}] Slug:     {article['slug']}")
        print(f"  [{i}] Category: {article['category']}")
        articles.append(article)
        known_insights.append(article)

    if not articles:
        print("  All generated articles had slug collisions or failed. Exiting.")
        run_data["status"] = "slug_collision"
        write_log(run_data)
        return

    print(f"  Successfully generated {len(articles)} article(s)")

    # ─ Phase 5b: LinkedIn Essay Desk ─────────────────────────────────────
    print(f"\n[5b/8] Generating LinkedIn Essay Desk package(s)...")
    essay_packages = []
    for i, article in enumerate(articles, 1):
        try:
            package = generate_essay_package(
                article,
                length_mode=args.linkedin_length,
                api_key=DEEPSEEK_API_KEY,
                site_url=SITE_URL,
            )
        except Exception as e:
            print(f"  [WARN] Essay Desk failed for article {i}: {redact_secret_text(e)} — using fallback package")
            package = generate_essay_package(
                article,
                length_mode=args.linkedin_length,
                api_key="",
                site_url=SITE_URL,
            )

        review = package.get("editorial_review") or {}
        approved = bool(package.get("publish_ready")) and review.get("status") == "ready_for_review"
        article["linkedin_essay_package"] = package
        article["linkedin_essay"] = package.get("linkedin_essay", "") if approved else ""
        article["linkedin_hook"] = article["linkedin_essay"] or article.get("linkedin_hook", "")
        article["linkedin_first_comment"] = package.get("first_comment", "") if approved else ""
        essay_packages.append(package)

        score = (package.get("quality_score") or {}).get("overall", "?")
        mode = package.get("voice_mode", "unknown")
        if not approved:
            reasons = "; ".join(review.get("issues", [])[:3]) or "independent review required"
            print(f"  [{i}] Essay Desk HELD: {mode} | {reasons}")
            continue
        print(f"  [{i}] Essay Desk: {mode} | score {score}/10")
        if not args.dry_run:
            save_to_queue(package)

    if args.dry_run and essay_packages:
        print(f"  [DRY-RUN] Essay package (article 1):\n{json.dumps(essay_packages[0], indent=2, ensure_ascii=False)[:1600]}...")

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
        "linkedin_essay_queue": str(ESSAY_QUEUE.relative_to(SITE_ROOT)),
    })

    # \u2500 Phase 6: Publish \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print(f"\n[6/8] Publishing {len(articles)} article(s)...")
    if not args.dry_run:
        INSIGHTS_DIR.mkdir(exist_ok=True)

        for article in articles:
            out = INSIGHTS_DIR / f"{article['slug']}.html"
            html = render_html(article)
            assert_no_mojibake(f"html {article['slug']}", html)
            out.write_text(html, encoding="utf-8")
            print(f"  Saved: insights/{article['slug']}.html")

            # Generate branded social media image
            img_path = INSIGHTS_DIR / f"{article['slug']}_social.png"
            if generate_article_image(article['title'], article['subtitle'], img_path):
                article['social_image'] = str(img_path)
                print(f"  Image: insights/{article['slug']}_social.png")

            update_manifest(article)

        update_feed_xml()
        update_sitemap_xml()

        print("\n[6b/8] Generating LinkedIn article PDF package(s)...")
        for article in articles:
            safe_queue_pdf_generation(article)
        write_linkedin_pdf_queue(articles)

        git_result = git_commit_push(articles, dry_run=False)
        run_data["git"] = git_result
        if not git_result["push_ok"]:
            run_data.update({
                "status": "deployment_failed",
                "articles_count": len(articles),
                "elapsed_seconds": round((datetime.now(timezone.utc) - start).total_seconds()),
            })
            write_log(run_data)
            print("\n  STOPPED: articles were generated locally but were not verified on origin/main.")
            raise SystemExit(1)
    else:
        for article in articles:
            print(f"  [DRY-RUN] Would save: insights/{article['slug']}.html")
        print(f"  [DRY-RUN] LinkedIn essay (article 1):\n  {articles[0].get('linkedin_essay','')}")

    # \u2500 Phase 7: LinkedIn \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    print("\n[7/8] LinkedIn publishing...")
    li_pdf_result = {"ok": False, "posted_count": 0, "attempted_count": len(articles), "dry_run": args.dry_run}
    if args.auto_post_linkedin:
        print("  Auto-post enabled for top-ranked article.")
        li_ok = post_to_linkedin(articles[0], dry_run=args.dry_run)
    else:
        li_ok = False
        print("  Link-share auto-post disabled.")

    if args.auto_post_linkedin_pdfs:
        print(f"  PDF auto-post enabled for {len(articles)} article(s).")
        li_pdf_result = safe_post_linkedin_pdfs(articles, dry_run=args.dry_run)
    else:
        print("  PDF auto-post disabled. Review/edit carousel PDFs before posting.")
        print(f"  Queue: {ESSAY_QUEUE.relative_to(SITE_ROOT)}")

    run_data["linkedin_posted"] = li_ok
    run_data["linkedin_pdf_posted_count"] = li_pdf_result.get("posted_count", 0)
    run_data["linkedin_pdf_attempted_count"] = li_pdf_result.get("attempted_count", len(articles))
    run_data["linkedin_pdf_results"] = li_pdf_result.get("results", [])
    run_data["linkedin_review_required"] = not (args.auto_post_linkedin or args.auto_post_linkedin_pdfs)

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
        if args.auto_post_linkedin_pdfs:
            posted = li_pdf_result.get("posted_count", 0)
            attempted = li_pdf_result.get("attempted_count", len(articles))
            print(f"  LinkedIn PDFs: posted {posted}/{attempted}")
        else:
            print(f"  LinkedIn: {'posted (article 1)' if li_ok else 'queued for review'}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
