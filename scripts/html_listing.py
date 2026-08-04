"""Read publications that serve us openly but publish no feed.

Roughly a third of the serious CRE and capital-markets universe has no RSS --
CBRE, JLL, PERE, ENR, Marcus & Millichap, CREFC, ICSC and others. Their index
pages are ordinary public pages, they serve our identified agent normally, and
their robots.txt permits crawling. Reading those is lawful and is the difference
between covering the market and covering whichever publishers happen to offer
XML.

The boundary this module enforces
    robots.txt is authoritative and is checked twice -- once for the index page
    and again for every individual article before it is fetched. A site that
    returns 401/403/429 to our agent is recorded as refusing us and is never
    retried with a different identity. There is no user-agent rotation, no
    proxy support, and no mechanism here that could defeat a bot wall. If a
    publisher does not want us, this module cannot get in, by construction.

All fetching goes through `retrieval.Retriever`, so listings inherit the same
timeouts, per-domain throttle, size ceiling, caching and failure isolation.
"""

from __future__ import annotations

import re
import urllib.parse as urlparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from intelligence_object import RetrievalStatus
from retrieval import Retriever

#: Path fragments that are never articles.
_NON_ARTICLE = re.compile(
    r"/(?:tag|tags|category|categories|author|authors|page|search|login|signin|"
    r"register|subscribe|privacy|terms|cookie|contact|about|careers|events?|"
    r"webinar|newsletter|rss|feed|sitemap|wp-content|wp-admin|static|assets)(?:/|$)",
    re.I,
)
_FILE_EXT = re.compile(r"\.(?:pdf|jpg|jpeg|png|gif|svg|zip|mp4|mp3|css|js)$", re.I)

#: An article URL usually has a readable slug or a dated path. This is the main
#: precision lever. Four or more hyphenated words. Three was too loose: site navigation such as
#: /insights/invest-finance-value matched and produced category links dressed as
#: headlines. Real headlines almost always run longer than a nav label.
_SLUGGY = re.compile(r"/[a-z0-9]+(?:-[a-z0-9]+){3,}/?$", re.I)
_DATED = re.compile(r"/(?:19|20)\d{2}/\d{1,2}/", re.I)
#: Numeric article identifiers, common on trade publications.
_NUMERIC_ID = re.compile(r"/\d{5,}[-/]", re.I)

_ANCHOR = re.compile(
    r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*?>(.*?)</a>", re.I | re.S
)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


@dataclass
class ListingItem:
    url: str = ""
    title: str = ""
    source_name: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    discovery_channel: str = "html_listing"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ListingReport:
    source_name: str = ""
    listing_url: str = ""
    status: str = ""
    candidates_seen: int = 0
    items_kept: int = 0
    robots_skipped: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_title(fragment: str) -> str:
    text = _TAGS.sub(" ", fragment or "")
    text = (
        text.replace("&amp;", "&").replace("&#8217;", "’").replace("&#039;", "’")
        .replace("&quot;", '"').replace("&nbsp;", " ").replace("&#8211;", "–")
    )
    return _WS.sub(" ", text).strip()


def looks_like_article(url: str) -> bool:
    """Is this plausibly an article rather than navigation?"""
    parts = urlparse.urlsplit(url)
    path = parts.path or "/"
    if path in ("", "/"):
        return False
    if _FILE_EXT.search(path) or _NON_ARTICLE.search(path):
        return False
    if len(path.strip("/").split("/")) > 6:
        return False
    return bool(_SLUGGY.search(path) or _DATED.search(path) or _NUMERIC_ID.search(path))


def extract_links(html: str, base_url: str, *, min_title_words: int = 5) -> list[ListingItem]:
    """Pull plausible article links and titles from an index page."""
    seen: set[str] = set()
    items: list[ListingItem] = []
    host = urlparse.urlsplit(base_url).netloc.lower()

    for href, inner in _ANCHOR.findall(html or ""):
        absolute = urlparse.urljoin(base_url, href.strip())
        split = urlparse.urlsplit(absolute)
        if split.scheme not in ("http", "https"):
            continue
        if split.netloc.lower() != host:
            continue  # stay on the publication
        clean = urlparse.urlunsplit((split.scheme, split.netloc, split.path, "", ""))
        if clean in seen or not looks_like_article(clean):
            continue
        title = _clean_title(inner)
        if len(title.split()) < min_title_words:
            continue
        seen.add(clean)
        items.append(ListingItem(url=clean, title=title[:300]))
    return items


def read_listing(
    listing_url: str,
    *,
    source_name: str = "",
    retriever: Retriever | None = None,
    max_items: int = 25,
) -> tuple[list[ListingItem], ListingReport]:
    """Read one index page and return the articles it links to.

    Never raises. A publisher that refuses us produces an empty list and a
    report saying so.
    """
    retriever = retriever or Retriever()
    report = ListingReport(source_name=source_name, listing_url=listing_url)

    if retriever.respect_robots and not retriever._robots.allows(listing_url):  # noqa: SLF001
        report.status = "robots_denied"
        report.note = "robots.txt disallows the index page"
        return [], report

    result = retriever.fetch(listing_url, use_cache=False)
    report.status = result.status

    if result.status == RetrievalStatus.BLOCKED:
        report.note = "publisher refuses our agent; not retried"
        return [], report
    if not result.ok and not result.text:
        report.note = result.error or "index page could not be read"
        return [], report

    # `Retriever` returns extracted main text; for an index we need the markup,
    # so fetch through the same session with all its limits still applied.
    try:
        response = retriever._session.get(  # noqa: SLF001
            listing_url,
            headers={"User-Agent": "LightTowerGroup-NewsAgent/2.0 (+https://lighttowergroup.co)"},
            timeout=(8, 15),
            allow_redirects=True,
        )
        html = response.text if response.status_code == 200 else ""
    except Exception as exc:  # noqa: BLE001
        report.status = RetrievalStatus.FAILED
        report.note = f"index unreadable ({type(exc).__name__})"
        return [], report

    found = extract_links(html, listing_url)
    report.candidates_seen = len(found)

    kept: list[ListingItem] = []
    for item in found:
        if len(kept) >= max_items:
            break
        if retriever.respect_robots and not retriever._robots.allows(item.url):  # noqa: SLF001
            report.robots_skipped += 1
            continue
        item.source_name = source_name
        kept.append(item)

    report.items_kept = len(kept)
    report.note = report.note or f"{len(kept)} articles linked from the index"
    return kept, report


def read_listings(
    sources: Sequence[dict[str, Any]],
    *,
    retriever: Retriever | None = None,
    max_items_per_source: int = 25,
) -> tuple[list[ListingItem], list[ListingReport]]:
    """Read several index pages. One failure never stops the rest."""
    retriever = retriever or Retriever()
    all_items: list[ListingItem] = []
    reports: list[ListingReport] = []
    for source in sources:
        url = source.get("listing_url") or source.get("url") or ""
        if not url:
            continue
        try:
            items, report = read_listing(
                url,
                source_name=source.get("name", ""),
                retriever=retriever,
                max_items=max_items_per_source,
            )
        except Exception as exc:  # noqa: BLE001
            items, report = [], ListingReport(
                source_name=source.get("name", ""), listing_url=url,
                status=RetrievalStatus.FAILED, note=f"{type(exc).__name__}: {exc}"[:140],
            )
        all_items.extend(items)
        reports.append(report)
    return all_items, reports


def to_canonical_items(items: Iterable[ListingItem], *, source_tier: int = 3) -> list[Any]:
    """Adapt listing results to the shape the rest of the pipeline expects."""
    from canonical_item import CanonicalItem

    out = []
    for item in items:
        node = CanonicalItem(
            headline=item.title,
            source_url=item.url,
            canonical_url=item.url,
            source_name=item.source_name,
            source_type="html_listing",
            source_tier=source_tier,
            discovery_date=item.discovered_at,
        )
        node.item_id = node.generate_id()
        out.append(node)
    return out
