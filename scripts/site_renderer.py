"""Render Insights pages and the site indexes: the article page, insights.json, feed.xml, sitemap.xml.

Moved out of daily_news_agent.py (plan item 3.1, flag F1) so publishing no longer imports a
2,872-line legacy module and the eighteen modules it loads. The code is unchanged;
daily_news_agent re-exports these names so the legacy path behaves exactly as before.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import requests

from news_sources import FEED_DESCRIPTION, FEED_TITLE, SITE_URL
from edition_manager import calculate_read_time

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_DIR = SITE_ROOT / "insights"
INSIGHTS_JSON = SITE_ROOT / "insights.json"
FEED_XML = SITE_ROOT / "feed.xml"
SITEMAP_XML = SITE_ROOT / "sitemap.xml"

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


# Tags and attributes permitted in article body HTML (allowlist approach)
_SAFE_TAGS  = {'p', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'blockquote', 'br', 'a', 'span', 'h2', 'h3', 'h4', 'h5', 'h6'}
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


# Lightly topic-aware end-of-article CTA copy. Keyed by the article's
# `category` field (see the category list in USER_PROMPT_TEMPLATE); any
# category not listed here falls back to `_default` rather than erroring.
_CATEGORY_CTA_LINES: dict[str, str] = {
    "Deal Intelligence": "Working through a deal with a similar structure?",
    "Debt & Equity": "Sourcing debt or equity for something like this?",
    "Capital Markets": "Navigating a similar capital markets decision?",
    "Market Analysis": "Thinking through how this affects your next move?",
    "Policy & Regulation": "Trying to work out how this affects your capital plan?",
    "_default": "Have a deal that raises questions like this one?",
}


def render_html(article: dict) -> str:
    """Render a full standalone HTML page for a news article."""
    page_url = f"{SITE_URL}/insights/{article['slug']}.html"
    social_image_url = f"{SITE_URL}/insights/{article['slug']}_social.png"
    esc      = lambda s: escape(str(s or ""))

    sources_html = "\n".join(
        f'      <li><a href="{esc(s.get("url","#"))}" target="_blank" rel="noopener">'
        f'{esc(s.get("name",""))}</a></li>'
        for s in article.get("sources", [])
        if str(s.get("url", "")).startswith(("https://", "http://"))
    )
    if not sources_html:
        sources_html = (
            f'      <li><a href="{esc(article.get("source_url","#"))}" '
            f'target="_blank" rel="noopener">{esc(article.get("source_name",""))}</a></li>'
        )

    tags_html  = " ".join(f'<span class="tag">{esc(t)}</span>' for t in article.get("tags", []))
    share_top  = _share_buttons(page_url, article["title"])
    share_bot  = _share_buttons(page_url, article["title"])
    cta_headline = _CATEGORY_CTA_LINES.get(
        article.get("category", ""), _CATEGORY_CTA_LINES["_default"]
    )
    format_label = article.get("editorial_format_label") or article.get("category", "")
    franchise_name = (article.get("franchise") or {}).get("name", "")
    article_kicker = " · ".join(part for part in (format_label, franchise_name) if part)
    source_count = article.get("source_count", len(article.get("sources", [])))
    read_time = calculate_read_time(article.get("body_html", ""))
    data_points = [
        point for point in article.get("data_points", [])
        if isinstance(point, dict) and point.get("label") and point.get("value")
    ][:4]
    data_points_html = ""
    if data_points:
        data_points_html = (
            '<aside class="article-data-note" aria-label="Key reported data">'
            '<p class="article-data-note-label">One chart, one argument</p>'
            '<div class="article-data-grid">'
            + "".join(
                '<div class="article-data-point">'
                f'<strong>{esc(point.get("value"))}</strong>'
                f'<span>{esc(point.get("label"))}</span>'
                "</div>"
                for point in data_points
            )
            + "</div></aside>"
        )
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

  <!-- Google Analytics 4 — add your Measurement ID from analytics.google.com -->
  <!-- <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  </script> -->
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

  <link rel="stylesheet" href="/insights/article-base.css">
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
        <a href="/services.html">Capabilities</a>
        <a href="/transactions.html">Transactions</a>
        <a href="/buildings.html">NYC Maturities</a>
        <a href="/insights.html">Intelligence</a>
        <a href="/about.html">About</a>
        <a href="/#contact" class="nav-cta">Price a Deal</a>
      </div>
      <button class="nav-menu-btn" id="nav-menu-btn" aria-label="Open menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
    <div class="nav-mobile" id="nav-mobile" role="menu">
      <a href="/services.html">Capabilities</a>
      <a href="/transactions.html">Transactions</a>
      <a href="/buildings.html">NYC Maturities</a>
      <a href="/insights.html">Intelligence</a>
      <a href="/about.html">About</a>
      <a href="/#contact" class="nav-mobile-cta">Price a Deal</a>
    </div>
  </nav>

  <div class="article-wrap">
    <article itemscope itemtype="https://schema.org/NewsArticle">

      <div class="article-category">{esc(article_kicker)}</div>
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
        <span>{read_time} min read</span>
        <span>{source_count} source{'s' if source_count != 1 else ''}</span>
      </div>

      {share_top}
      <hr class="article-rule">

      {data_points_html}

      <div class="article-body" itemprop="articleBody">
        {sanitize_html(article['body_html'])}
      </div>

      <div class="article-tags">{tags_html}</div>

      {share_bot}

      <div class="article-cta-block">
        <p class="article-cta-eyebrow">Direct Placement Desk</p>
        <h3 class="article-cta-headline">{esc(cta_headline)}</h3>
        <p class="article-cta-sub">Send us the address and target loan size. Ben Rohr prices every deal personally against live lender appetite and replies within 24 hours.</p>
        <a href="/#contact" class="article-cta-btn" style="display:inline-block;text-decoration:none;">Price Your Deal &rarr;</a>
      </div>

      <div class="article-lead-capture" style="margin: 2.5rem 0; padding: 2rem; background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px;">
        <p style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin: 0 0 0.5rem 0; font-weight: 600;">Daily Desk Intelligence</p>
        <h3 style="margin: 0 0 0.5rem 0; font-size: 1.25rem; color: #0f172a;">Get Light Tower Group's Institutional CRE Brief</h3>
        <p style="margin: 0 0 1.25rem 0; font-size: 0.95rem; color: #475569; line-height: 1.5;">Direct capital markets analysis, debt &amp; equity deal mechanics, and distressed credit signals delivered straight to your inbox.</p>
        <form class="lead-capture-form" onsubmit="event.preventDefault(); var btn=this.querySelector('button'); btn.textContent='Subscribed ✓'; btn.disabled=true; this.querySelector('input').disabled=true;" style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <input type="email" name="email" placeholder="Work email address..." required aria-label="Work email address" style="flex: 1; min-width: 220px; padding: 0.75rem 1rem; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.95rem;">
          <button type="submit" style="padding: 0.75rem 1.5rem; background: #0f172a; color: #ffffff; border: none; border-radius: 4px; font-size: 0.95rem; font-weight: 600; cursor: pointer;">Subscribe</button>
        </form>
      </div>

      <section class="related-research" id="related-research">
      <h2>Related Research</h2>
      <div class="related-grid" id="related-grid">Loading...</div>
    </section>

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
      <a href="/services.html">Capabilities</a> &nbsp;&middot;&nbsp;
      <a href="/transactions.html">Transactions</a> &nbsp;&middot;&nbsp;
      <a href="/buildings.html">NYC Maturities</a> &nbsp;&middot;&nbsp;
      <a href="/insights.html">Intelligence</a> &nbsp;&middot;&nbsp;
      <a href="/about.html">About</a> &nbsp;&middot;&nbsp;
      <a href="/feed.xml">RSS Feed</a> &nbsp;&middot;&nbsp;
      <a href="/#contact">Price a Deal</a>
    </p>
    <p>&copy; {year} Light Tower Group. All rights reserved.</p>
  </footer>

  <script src="/chat-widget.js?v=20260726"></script>

</body>
</html>"""


def update_manifest(article: dict):
    """Prepend new article entry to insights.json with a .lock file to prevent concurrent race conditions."""
    import os
    import time

    lock_path = INSIGHTS_JSON.with_suffix(".lock")
    lock_acquired = False
    for _ in range(50):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            lock_acquired = True
            break
        except FileExistsError:
            time.sleep(0.1)

    try:
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
            "publishedAt": article["date_iso"],
            "readTime": calculate_read_time(article.get("body_html", "")),
            "category": article["category"],
            "excerpt":  article["meta_description"],
            "url":      f"/insights/{article['slug']}.html",
            "tags":     article.get("tags", []),
            "format":   article.get("editorial_format", "analysis"),
            "franchise": article.get("franchise"),
            "mustReadScore": article.get("must_read_score"),
            "sourceCount": article.get("source_count", len(article.get("sources", []))),
            "sourceName": article.get("source_name"),
            "sourceUrl": article.get("source_url"),
            "pipelineVersion": article.get("pipeline_version"),
            "eventId": article.get("event_id"),
        }
        if article.get("sector"):
            # The Intelligence page filters on this (F14); older entries fall back to category.
            entry["sector"] = article["sector"]
        assert_no_mojibake("manifest entry", entry)
        # Remove any existing entry with same slug
        data = [e for e in data if e.get("slug") != article["slug"]]
        data.insert(0, entry)

        manifest_json = json.dumps(data, indent=2, ensure_ascii=False)
        assert_no_mojibake("insights.json", manifest_json)
        INSIGHTS_JSON.write_text(manifest_json, encoding="utf-8")
        print(f"  insights.json updated ({len(data)} total entries)")
    finally:
        if lock_acquired and lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass


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
        try:
            d = datetime.fromisoformat(str(e.get("publishedAt", "")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            d = _parse_manifest_date(e.get("date", ""))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        d = d.astimezone(timezone.utc)
        pub_rss = d.strftime("%a, %d %b %Y %H:%M:%S +0000")
        pub_iso = d.strftime("%Y-%m-%dT%H:%M:%SZ")

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
      <url>{SITE_URL}/capital-intelligence-hero.png</url>
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
