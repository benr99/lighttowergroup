"""Reading publications that have no feed — and the limits on doing so.

The tests that matter most are in `RespectsRefusal`: this module must be
incapable of getting into a site that does not want us, by construction rather
than by policy.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from html_listing import (  # noqa: E402
    extract_links,
    looks_like_article,
    read_listing,
    read_listings,
    to_canonical_items,
)
from intelligence_object import RetrievalStatus  # noqa: E402
from retrieval import Retriever  # noqa: E402

INDEX = """
<html><body>
  <nav><a href="/about-us">About</a><a href="/category/news">News</a></nav>
  <main>
    <a href="/insights/blackstone-acquires-phoenix-industrial-portfolio">
       Blackstone Acquires Phoenix Industrial Portfolio for $450 Million</a>
    <a href="/2026/08/fed-holds-rates-steady-amid-mixed-data">
       Fed Holds Rates Steady Amid Mixed Inflation Data</a>
    <a href="/insights/office-conversions-gain-momentum-in-dallas">
       Office Conversions Gain Momentum in Dallas</a>
    <a href="/tag/multifamily">Multifamily</a>
    <a href="/insights/report.pdf">Download the report</a>
    <a href="https://twitter.com/example">Follow us</a>
    <a href="/insights/short">Short</a>
  </main>
</body></html>
"""


class _Raw:
    def __init__(self, payload): self._p = payload
    def read(self, size, decode_content=True): return self._p[:size]  # noqa: ARG002


class _Response:
    def __init__(self, *, status=200, body=b"", ctype="text/html", url="https://example.com/"):
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self.url = url
        self.encoding = "utf-8"
        self.raw = _Raw(body)
        self.text = body.decode("utf-8", errors="replace")
        self.content = body
    def close(self): pass


class _Session:
    def __init__(self, routes): self.routes = routes; self.calls = []
    def get(self, url, **kwargs):  # noqa: ARG002
        self.calls.append(url)
        out = self.routes.get(url, _Response(status=404, url=url))
        if isinstance(out, Exception): raise out
        return out


class _DenyAll:
    def can_fetch(self, agent, url): return False  # noqa: ARG002


class _AllowAll:
    def can_fetch(self, agent, url): return True  # noqa: ARG002


def _retriever(routes, *, robots=True):
    session = _Session(routes)
    return Retriever(session=session, cache_dir=Path(tempfile.mkdtemp()),
                     respect_robots=robots, per_domain_delay=0.0), session


class LinkExtraction(unittest.TestCase):
    def test_it_finds_articles_and_ignores_navigation(self) -> None:
        items = extract_links(INDEX, "https://example.com/insights")
        urls = [i.url for i in items]
        self.assertIn("https://example.com/insights/blackstone-acquires-phoenix-industrial-portfolio", urls)
        self.assertIn("https://example.com/2026/08/fed-holds-rates-steady-amid-mixed-data", urls)
        self.assertNotIn("https://example.com/tag/multifamily", urls)
        self.assertNotIn("https://example.com/about-us", urls)

    def test_it_ignores_files_and_offsite_links(self) -> None:
        urls = [i.url for i in extract_links(INDEX, "https://example.com/insights")]
        self.assertFalse(any(u.endswith(".pdf") for u in urls))
        self.assertFalse(any("twitter.com" in u for u in urls))

    def test_titles_are_captured_and_cleaned(self) -> None:
        items = extract_links(INDEX, "https://example.com/insights")
        titles = [i.title for i in items]
        self.assertIn("Blackstone Acquires Phoenix Industrial Portfolio for $450 Million", titles)
        self.assertFalse(any("<" in t for t in titles))

    def test_link_text_too_short_to_be_a_headline_is_dropped(self) -> None:
        urls = [i.url for i in extract_links(INDEX, "https://example.com/insights")]
        self.assertNotIn("https://example.com/insights/short", urls)

    def test_article_shape_detection(self) -> None:
        self.assertTrue(looks_like_article("https://x.com/insights/a-real-story-about-things"))
        self.assertFalse(looks_like_article("https://x.com/insights/invest-finance-value"),
                         "three-word nav labels must not read as articles")
        self.assertTrue(looks_like_article("https://x.com/2026/08/a-dated-story"))
        for bad in ("https://x.com/", "https://x.com/tag/office",
                    "https://x.com/report.pdf", "https://x.com/news"):
            self.assertFalse(looks_like_article(bad), bad)

    def test_duplicate_links_are_collapsed(self) -> None:
        html = ('<a href="/insights/one-two-three-four">A headline of some length here</a>' * 3)
        self.assertEqual(len(extract_links(html, "https://example.com/")), 1)

    def test_query_strings_are_normalised_away(self) -> None:
        html = '<a href="/insights/one-two-three-four?utm_source=x">A headline of some length here</a>'
        items = extract_links(html, "https://example.com/")
        self.assertEqual(items[0].url, "https://example.com/insights/one-two-three-four")


class RespectsRefusal(unittest.TestCase):
    """The module must be unable to enter a site that refuses us."""

    def test_a_403_index_yields_nothing_and_is_not_retried(self) -> None:
        url = "https://walled.com/insights"
        retriever, session = _retriever({url: _Response(status=403, url=url)}, robots=False)
        items, report = read_listing(url, source_name="Walled", retriever=retriever)
        self.assertEqual(items, [])
        self.assertEqual(report.status, RetrievalStatus.BLOCKED)
        self.assertIn("refuses our agent", report.note)
        self.assertEqual(len(session.calls), 1, "a refusal must not be retried")

    def test_robots_disallow_stops_the_index_before_any_request(self) -> None:
        url = "https://noindex.com/insights"
        retriever, session = _retriever({url: _Response(body=INDEX.encode(), url=url)})
        retriever._robots._cache["https://noindex.com"] = _DenyAll()
        items, report = read_listing(url, source_name="NoIndex", retriever=retriever)
        self.assertEqual(items, [])
        self.assertEqual(report.status, "robots_denied")
        self.assertEqual(session.calls, [], "no request may be made to a disallowed index")

    def test_individual_articles_are_rechecked_against_robots(self) -> None:
        """Permission for the index is not permission for every article."""
        url = "https://example.com/insights"
        retriever, _ = _retriever({url: _Response(body=INDEX.encode(), url=url)})

        class _DenyArticles:
            def can_fetch(self, agent, target):  # noqa: ARG002
                return target.rstrip("/").endswith("/insights")

        retriever._robots._cache["https://example.com"] = _DenyArticles()
        items, report = read_listing(url, source_name="Example", retriever=retriever)
        self.assertEqual(items, [])
        self.assertGreater(report.robots_skipped, 0)

    def test_there_is_no_user_agent_rotation_available(self) -> None:
        """A structural check: nothing here can present a different identity."""
        source = (ROOT / "scripts" / "html_listing.py").read_text(encoding="utf-8")
        for banned in ("proxies", "random.choice(USER_AGENTS)", "Mozilla/", "rotate"):
            self.assertNotIn(banned, source, f"{banned!r} must not appear")


class ReadsPermittedSites(unittest.TestCase):
    def test_a_permitted_index_returns_its_articles(self) -> None:
        url = "https://example.com/insights"
        retriever, _ = _retriever({url: _Response(body=INDEX.encode(), url=url)})
        retriever._robots._cache["https://example.com"] = _AllowAll()
        items, report = read_listing(url, source_name="Example Research", retriever=retriever)
        self.assertGreaterEqual(len(items), 3)
        # An index page carries links rather than prose, so it reads as partial
        # rather than full text. What matters is that it was readable at all.
        self.assertIn(report.status, (RetrievalStatus.FULL_TEXT, RetrievalStatus.PARTIAL_TEXT))
        self.assertTrue(all(i.source_name == "Example Research" for i in items))
        self.assertTrue(all(i.discovery_channel == "html_listing" for i in items))

    def test_the_item_cap_is_honoured(self) -> None:
        url = "https://example.com/insights"
        retriever, _ = _retriever({url: _Response(body=INDEX.encode(), url=url)})
        retriever._robots._cache["https://example.com"] = _AllowAll()
        items, _ = read_listing(url, retriever=retriever, max_items=2)
        self.assertEqual(len(items), 2)

    def test_one_failing_site_does_not_stop_the_others(self) -> None:
        good, bad = "https://good.com/insights", "https://bad.com/insights"
        retriever, _ = _retriever({
            good: _Response(body=INDEX.encode(), url=good),
            bad: _Response(status=403, url=bad),
        }, robots=False)
        items, reports = read_listings([
            {"name": "Good", "url": good}, {"name": "Bad", "url": bad},
        ], retriever=retriever)
        self.assertGreater(len(items), 0)
        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[1].status, RetrievalStatus.BLOCKED)

    def test_results_convert_into_pipeline_items(self) -> None:
        url = "https://example.com/insights"
        retriever, _ = _retriever({url: _Response(body=INDEX.encode(), url=url)})
        retriever._robots._cache["https://example.com"] = _AllowAll()
        items, _ = read_listing(url, source_name="Example", retriever=retriever)
        canonical = to_canonical_items(items, source_tier=2)
        self.assertEqual(len(canonical), len(items))
        self.assertTrue(all(c.item_id for c in canonical))
        self.assertTrue(all(c.source_type == "html_listing" for c in canonical))

    def test_an_empty_index_is_handled(self) -> None:
        url = "https://example.com/insights"
        body = b"<html><body><p>Nothing here</p></body></html>"
        retriever, _ = _retriever({url: _Response(body=body, url=url)}, robots=False)
        items, report = read_listing(url, retriever=retriever)
        self.assertEqual(items, [])
        self.assertEqual(report.items_kept, 0)


if __name__ == "__main__":
    unittest.main()
