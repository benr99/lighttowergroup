"""HTML, hub, feed, and sitemap rendering for Light Tower Ideas."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SITE_URL = "https://lighttowergroup.co"

STATIC_IDEAS = [
    {
        "title": "The Office Tower That Forgot Why People Go to Work",
        "slug": "the-office-tower-that-forgot-why",
        "date": "2026-06-25",
        "readTime": 8,
        "category": "Ideas",
        "excerpt": "When architects design for capital efficiency instead of human collaboration, buildings become monuments to financing rather than places where thinking happens.",
        "url": "/ideas/the-office-tower-that-forgot-why.html",
        "tags": ["Ideas", "The Built World", "Office", "Architecture", "Capital"],
        "idea_score": None,
        "quality_score": None,
    }
]


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def with_static_ideas(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep hand-authored evergreen Ideas visible beside generated essays."""
    combined = list(manifest)
    existing = {item.get("slug") for item in combined}
    for item in STATIC_IDEAS:
        if item["slug"] not in existing:
            combined.append(dict(item))
    return sorted(combined, key=lambda item: item.get("date", ""), reverse=True)


def nav_html(active: str = "Ideas") -> str:
    links = [
        ("/#practice", "Practice"),
        ("/#advantage", "Advantage"),
        ("/#leadership", "Leadership"),
        ("/insights.html", "Insights"),
        ("/ideas.html", "Ideas"),
        ("/buildings.html", "Buildings"),
        ("/services.html", "Services"),
        ("/about.html", "About"),
    ]
    desktop = "\n".join(_nav_link(href, label, active, indent="        ") for href, label in links)
    mobile = "\n".join(_nav_link(href, label, active, indent="      ") for href, label in links)
    return f"""  <nav class="site-nav" role="navigation" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="/" class="nav-logo" aria-label="Light Tower Group home">Light Tower Group</a>
      <div class="nav-links">
{desktop}
        <button onclick="openLTGChat()" class="nav-cta">Initiate Mandate</button>
      </div>
      <button class="nav-menu-btn" id="nav-menu-btn" aria-label="Open menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
    <div class="nav-mobile" id="nav-mobile" role="menu">
{mobile}
      <button onclick="openLTGChat()" class="nav-mobile-cta">Initiate Mandate</button>
    </div>
  </nav>"""


def _nav_link(href: str, label: str, active: str, *, indent: str) -> str:
    class_attr = ' class="active"' if label == active else ""
    return f'{indent}<a href="{href}"{class_attr}>{label}</a>'


def footer_html() -> str:
    year = datetime.now().year
    return f"""  <footer class="footer" role="contentinfo">
    <div class="container">
      <div class="footer-top">
        <div>
          <div class="footer-brand-name">Light Tower Group</div>
          <p>Institutional capital advisory for complex commercial real estate mandates. Debt placement, equity structuring, and investment advisory nationwide.</p>
        </div>
        <nav aria-label="Site navigation">
          <span class="footer-col-label">Navigate</span>
          <a href="/#practice" class="footer-link">The Practice</a>
          <a href="/#advantage" class="footer-link">The Advantage</a>
          <a href="/insights.html" class="footer-link">Insights</a>
          <a href="/ideas.html" class="footer-link">Ideas</a>
          <a href="/buildings.html" class="footer-link">Buildings</a>
          <a href="/about.html" class="footer-link">About</a>
        </nav>
        <div>
          <span class="footer-col-label">Contact</span>
          <a href="mailto:ben@lighttowergroup.co" class="footer-contact-link">ben@lighttowergroup.co</a>
          <a href="tel:+13475540093" class="footer-contact-link">(347) 554-0093</a>
          <a href="https://www.linkedin.com/in/benrohr/" target="_blank" rel="noopener" class="footer-contact-link">LinkedIn</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p class="copyright">&copy; {year} Light Tower Group / All Rights Reserved</p>
        <p class="footer-disclaimer">Light Tower Group is a commercial real estate capital advisory firm. Services are provided to qualified sponsors and institutional clients. Not a licensed securities dealer or registered investment advisor.</p>
      </div>
    </div>
  </footer>"""


def site_script_html() -> str:
    return """  <script>
    var menuBtn = document.getElementById('nav-menu-btn');
    var mobileNav = document.getElementById('nav-mobile');
    if (menuBtn && mobileNav) {
      menuBtn.addEventListener('click', function () {
        var open = mobileNav.classList.toggle('open');
        menuBtn.classList.toggle('open', open);
        menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
  </script>
  <script src="/chat-widget.js"></script>"""


def render_article(article: dict[str, Any]) -> str:
    page_url = f"{SITE_URL}/ideas/{article['slug']}.html"
    date_iso = article["date_iso"]
    tags = article.get("tags", [])
    sources = article.get("sources", [])
    tags_html = " ".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags)
    sources_html = "\n".join(
        f'          <li><a href="{esc(src.get("url"))}" target="_blank" rel="noopener nofollow">{esc(src.get("name"))}</a></li>'
        for src in sources
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["meta_description"],
        "url": page_url,
        "datePublished": date_iso,
        "dateModified": article.get("updated_iso", date_iso),
        "author": {"@type": "Person", "name": "Benjamin Rohr", "url": f"{SITE_URL}/about.html"},
        "publisher": {"@type": "Organization", "name": "Light Tower Group", "url": SITE_URL, "logo": f"{SITE_URL}/favicon.svg"},
        "mainEntityOfPage": page_url,
        "articleSection": "Light Tower Ideas",
        "keywords": tags,
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <title>{esc(article.get('seo_title') or article['title'])} | Light Tower Group</title>
  <meta name="description" content="{esc(article['meta_description'])}">
  <meta name="robots" content="index, follow">
  <meta name="author" content="Benjamin Rohr, Light Tower Group">
  <link rel="canonical" href="{page_url}">
  <link rel="alternate" type="application/rss+xml" title="Light Tower Ideas" href="{SITE_URL}/ideas/feed.xml">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{page_url}">
  <meta property="og:title" content="{esc(article['title'])}">
  <meta property="og:description" content="{esc(article['meta_description'])}">
  <meta property="og:image" content="{SITE_URL}/network.jpg">
  <meta property="article:published_time" content="{date_iso}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(article['title'])}">
  <meta name="twitter:description" content="{esc(article['meta_description'])}">
  <meta name="twitter:image" content="{SITE_URL}/network.jpg">
  <script type="application/ld+json">
{json.dumps(schema, indent=2, ensure_ascii=False)}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Space+Grotesk:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/site.css">
</head>
<body>
{nav_html("Ideas")}
  <main class="article-wrap ideas-article-wrap">
    <article itemscope itemtype="https://schema.org/Article" class="ideas-article">
      <div class="article-category">Light Tower Ideas</div>
      <h1 class="article-title" itemprop="headline">{esc(article['title'])}</h1>
      <p class="article-subtitle">{esc(article['subtitle'])}</p>
      <div class="article-byline">
        <span itemprop="author" itemscope itemtype="https://schema.org/Person"><a href="/about.html" itemprop="url"><span itemprop="name">Ben Rohr</span></a></span>
        <span><time itemprop="datePublished" datetime="{date_iso}">{esc(article['date'])}</time></span>
        <span>{int(article.get('reading_time', 7))} min read</span>
      </div>
      <hr class="article-rule">
      <div class="article-body" itemprop="articleBody">
{article['body_html']}
      </div>
      <div class="article-tags">{tags_html}</div>
      <div class="sources-block">
        <h2>Sources</h2>
        <ul>
{sources_html}
        </ul>
      </div>
      <p class="article-back-link"><a href="/ideas.html">Back to Ideas</a></p>
    </article>
  </main>
{footer_html()}
{site_script_html()}
</body>
</html>
"""


def update_manifest(article: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    data = read_json(manifest_path, [])
    entry = {
        "title": article["title"],
        "slug": article["slug"],
        "date": article["date_iso"][:10],
        "readTime": int(article.get("reading_time", 7)),
        "category": "Ideas",
        "excerpt": article["excerpt"],
        "url": f"/ideas/{article['slug']}.html",
        "tags": article.get("tags", []),
        "idea_score": article.get("idea_score"),
        "quality_score": article.get("quality_score"),
    }
    data = [item for item in data if item.get("slug") != article["slug"]]
    data.insert(0, entry)
    data.sort(key=lambda item: item.get("date", ""), reverse=True)
    write_json(manifest_path, data)
    return data


def render_hub(manifest: list[dict[str, Any]]) -> str:
    manifest = with_static_ideas(manifest)
    cards = "\n".join(_hub_card(item) for item in manifest)
    if not cards:
        cards = """        <div class="idea-card">
          <div>
            <div class="idea-kicker">Coming Soon</div>
          </div>
          <div>
            <h2 class="idea-title">Light Tower Ideas</h2>
            <p class="idea-desc">Essays on buildings, money, power, design, and the psychology of place.</p>
          </div>
        </div>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Ideas",
        "url": f"{SITE_URL}/ideas.html",
        "description": "Essays from Light Tower Group on buildings, capital, design, institutions, and the psychology of place.",
        "publisher": {"@type": "Organization", "name": "Light Tower Group", "url": SITE_URL},
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <title>Ideas | Light Tower Group</title>
  <meta name="description" content="Essays from Light Tower Group on buildings, capital, design, institutions, and the psychology of place.">
  <meta name="robots" content="index, follow">
  <meta name="author" content="Benjamin Rohr, Light Tower Group">
  <link rel="canonical" href="{SITE_URL}/ideas.html">
  <link rel="alternate" type="application/rss+xml" title="Light Tower Ideas" href="{SITE_URL}/ideas/feed.xml">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE_URL}/ideas.html">
  <meta property="og:title" content="Ideas | Light Tower Group">
  <meta property="og:description" content="Essays on buildings, money, power, and the psychology of place.">
  <meta property="og:image" content="{SITE_URL}/network.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Ideas | Light Tower Group">
  <meta name="twitter:description" content="Essays on buildings, money, power, and the psychology of place.">
  <meta name="twitter:image" content="{SITE_URL}/network.jpg">
  <script type="application/ld+json">
{json.dumps(schema, indent=2, ensure_ascii=False)}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Space+Grotesk:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/site.css">
</head>
<body>
{nav_html("Ideas")}
  <main>
    <section class="hero container ideas-hero">
      <span class="eyebrow">Ideas</span>
      <h1>Buildings, Capital & Culture</h1>
      <p>Essays on the built world as a cultural and financial text: how architecture, underwriting, institutions, and human behavior shape the places where capital becomes physical.</p>
    </section>
    <section class="ideas-section container" aria-label="Latest ideas">
      <div class="ideas-grid">
{cards}
      </div>
    </section>
  </main>
{footer_html()}
{site_script_html()}
</body>
</html>
"""


def _hub_card(item: dict[str, Any]) -> str:
    date = item.get("date", "")
    try:
        date_label = datetime.fromisoformat(date).strftime("%B %-d, %Y")
    except Exception:
        try:
            date_label = datetime.fromisoformat(date).strftime("%B %#d, %Y")
        except Exception:
            date_label = date
    tags = item.get("tags", [])
    kicker = tags[1] if len(tags) > 1 else "Light Tower Ideas"
    return f"""        <a class="idea-card" href="{esc(item.get('url'))}">
          <div>
            <div class="idea-kicker">{esc(kicker)}</div>
            <div class="idea-meta">{esc(date_label)} / {int(item.get('readTime', 7))} min read</div>
          </div>
          <div>
            <h2 class="idea-title">{esc(item.get('title'))}</h2>
            <p class="idea-desc">{esc(item.get('excerpt'))}</p>
          </div>
        </a>"""


def render_ideas_feed(manifest: list[dict[str, Any]]) -> str:
    manifest = with_static_ideas(manifest)
    items = []
    for entry in manifest[:50]:
        url = f"{SITE_URL}{entry.get('url')}"
        d = _parse_date(entry.get("date", ""))
        pub = d.strftime("%a, %d %b %Y 07:00:00 +0000")
        items.append(f"""    <item>
      <title><![CDATA[{entry.get('title', '')}]]></title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <pubDate>{pub}</pubDate>
      <description><![CDATA[{entry.get('excerpt', '')}]]></description>
      <category>Light Tower Ideas</category>
    </item>""")
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Light Tower Ideas</title>
    <link>{SITE_URL}/ideas.html</link>
    <description>Essays on buildings, capital, design, institutions, and the psychology of place.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/ideas/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""


def update_sitemap(sitemap_path: Path, manifest: list[dict[str, Any]]) -> None:
    manifest = with_static_ideas(manifest)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    if sitemap_path.exists():
        root = ET.parse(sitemap_path).getroot()
    else:
        root = ET.Element(f"{{{ns}}}urlset")
    approved_ideas_urls = {f"{SITE_URL}/ideas.html"}
    approved_ideas_urls.update(f"{SITE_URL}{item['url']}" for item in manifest if item.get("url"))
    for url_el in list(root.findall(f"{{{ns}}}url")):
        loc_el = url_el.find(f"{{{ns}}}loc")
        loc = loc_el.text if loc_el is not None else ""
        if loc.startswith(f"{SITE_URL}/ideas/") and loc not in approved_ideas_urls:
            root.remove(url_el)
    existing = {loc.text for loc in root.findall(f"{{{ns}}}url/{{{ns}}}loc") if loc.text}

    def add_url(loc: str, lastmod: str, changefreq: str, priority: str) -> None:
        if loc in existing:
            return
        url_el = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(url_el, f"{{{ns}}}loc").text = loc
        ET.SubElement(url_el, f"{{{ns}}}lastmod").text = lastmod
        ET.SubElement(url_el, f"{{{ns}}}changefreq").text = changefreq
        ET.SubElement(url_el, f"{{{ns}}}priority").text = priority
        existing.add(loc)

    today = datetime.now().strftime("%Y-%m-%d")
    add_url(f"{SITE_URL}/ideas.html", today, "daily", "0.8")
    for item in manifest:
        if not item.get("url"):
            continue
        add_url(f"{SITE_URL}{item['url']}", item.get("date", today), "monthly", "0.7")

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(sitemap_path, encoding="utf-8", xml_declaration=True)


def _parse_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
