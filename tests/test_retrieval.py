"""Retrieval limits, honesty about what was fetched, and failure isolation.

All network access is faked, so these run offline and deterministically.
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import requests  # noqa: E402

from intelligence_object import (  # noqa: E402
    IntelligenceObject,
    RetrievalStatus,
    SourceRef,
)
from retrieval import Retriever, enrich_objects  # noqa: E402

ARTICLE = (
    "<html><head>"
    "<link rel='canonical' href='https://example.com/canonical-story'>"
    "<meta property='article:published_time' content='2026-08-03T11:00:00Z'>"
    "</head><body><article><p>"
    + ("Blackstone agreed to acquire the portfolio for $450 million. " * 40)
    + "</p></article></body></html>"
)


class _Raw:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self, size, decode_content=True):  # noqa: ARG002
        return self._payload[:size]


class _Response:
    def __init__(self, *, status=200, body=b"", ctype="text/html", url="https://example.com/a"):
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self.url = url
        self.encoding = "utf-8"
        self.raw = _Raw(body)
        self.text = body.decode("utf-8", errors="replace")
        self.content = body

    def close(self):
        pass


class _Session:
    """Scripted session. Records calls so throttling can be observed."""

    def __init__(self, routes: dict[str, object]):
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url, **kwargs):  # noqa: ARG002
        self.calls.append(url)
        outcome = self.routes.get(url, _Response(status=404, body=b"", url=url))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _retriever(routes, **kwargs) -> tuple[Retriever, _Session]:
    session = _Session(routes)
    tmp = tempfile.mkdtemp()
    opts = {"cache_dir": Path(tmp), "respect_robots": False, "per_domain_delay": 0.0}
    opts.update(kwargs)
    return Retriever(session=session, **opts), session


class ReportsWhatItActuallyGot(unittest.TestCase):
    """The scorer must never mistake a snippet for a full reading."""

    def test_a_long_article_is_reported_as_full_text(self) -> None:
        url = "https://example.com/a"
        r, _ = _retriever({url: _Response(body=ARTICLE.encode(), url=url)})
        result = r.fetch(url)
        self.assertEqual(result.status, RetrievalStatus.FULL_TEXT)
        self.assertGreater(result.text_chars, 1200)
        self.assertIn("Blackstone", result.text)

    def test_a_thin_page_is_reported_as_partial_not_full(self) -> None:
        url = "https://example.com/thin"
        body = b"<html><body><article><p>A short note about a deal.</p></article></body></html>"
        r, _ = _retriever({url: _Response(body=body, url=url)})
        result = r.fetch(url)
        self.assertIn(result.status, (RetrievalStatus.PARTIAL_TEXT, RetrievalStatus.FAILED))
        self.assertNotEqual(result.status, RetrievalStatus.FULL_TEXT)

    def test_a_publisher_block_is_reported_as_blocked_not_failed(self) -> None:
        url = "https://paywalled.com/a"
        r, _ = _retriever({url: _Response(status=403, url=url)})
        result = r.fetch(url)
        self.assertEqual(result.status, RetrievalStatus.BLOCKED)
        self.assertIn("403", result.skipped_reason)
        self.assertFalse(result.ok)

    def test_canonical_url_and_publication_date_are_extracted(self) -> None:
        url = "https://example.com/a?utm_source=x"
        r, _ = _retriever({url: _Response(body=ARTICLE.encode(), url=url)})
        result = r.fetch(url)
        self.assertEqual(result.canonical_url, "https://example.com/canonical-story")
        self.assertTrue(result.published_at.startswith("2026-08-03"))

    def test_non_document_content_types_are_refused(self) -> None:
        url = "https://example.com/video"
        r, _ = _retriever({url: _Response(body=b"\x00\x01", ctype="video/mp4", url=url)})
        result = r.fetch(url)
        self.assertEqual(result.status, RetrievalStatus.FAILED)
        self.assertIn("content type", result.error)


class Limits(unittest.TestCase):
    def test_oversized_responses_are_truncated_not_buffered(self) -> None:
        url = "https://example.com/huge"
        huge = ("<html><body><article><p>" + "x" * 500_000 + "</p></article></body></html>").encode()
        r, _ = _retriever({url: _Response(body=huge, url=url)}, max_bytes=10_000)
        result = r.fetch(url)
        self.assertNotEqual(result.status, RetrievalStatus.FULL_TEXT,
                            "a truncated document must not be called full text")

    def test_one_request_per_domain_is_spaced(self) -> None:
        routes = {f"https://same.com/{i}": _Response(body=ARTICLE.encode(), url=f"https://same.com/{i}")
                  for i in range(3)}
        r, _ = _retriever(routes, per_domain_delay=0.12, max_workers=3)
        started = time.perf_counter()
        r.fetch_many(list(routes), budget_seconds=30)
        self.assertGreater(time.perf_counter() - started, 0.2,
                           "three requests to one domain must not fire simultaneously")

    def test_phase_budget_is_honoured(self) -> None:
        url = "https://example.com/a"
        r, _ = _retriever({url: _Response(body=ARTICLE.encode(), url=url)})
        _, report = r.fetch_many([url], budget_seconds=1)
        self.assertEqual(report.requested, 1)
        self.assertLess(report.elapsed_ms, 30_000)

    def test_the_cache_prevents_a_second_fetch(self) -> None:
        url = "https://example.com/a"
        r, session = _retriever({url: _Response(body=ARTICLE.encode(), url=url)})
        first = r.fetch(url)
        second = r.fetch(url)
        self.assertEqual(len(session.calls), 1, "the same document must not be fetched twice")
        self.assertFalse(first.from_cache)
        self.assertTrue(second.from_cache)
        self.assertEqual(second.text_chars, first.text_chars)


class FailureIsolation(unittest.TestCase):
    """One bad document must never take down a run."""

    def test_a_timeout_is_captured_not_raised(self) -> None:
        url = "https://slow.com/a"
        r, _ = _retriever({url: requests.exceptions.Timeout("too slow")})
        result = r.fetch(url)
        self.assertEqual(result.status, RetrievalStatus.FAILED)
        self.assertEqual(result.error, "timeout")

    def test_one_broken_document_does_not_stop_the_batch(self) -> None:
        good = "https://example.com/good"
        bad = "https://example.com/bad"
        r, _ = _retriever({
            good: _Response(body=ARTICLE.encode(), url=good),
            bad: requests.exceptions.ConnectionError("dns"),
        })
        results, report = r.fetch_many([good, bad], budget_seconds=30)
        self.assertEqual(results[good].status, RetrievalStatus.FULL_TEXT)
        self.assertEqual(results[bad].status, RetrievalStatus.FAILED)
        self.assertEqual(report.fetched, 1)
        self.assertEqual(report.failed, 1)

    def test_malformed_urls_are_refused_quietly(self) -> None:
        r, _ = _retriever({})
        for bad in ("", "not-a-url", "ftp://example.com/x"):
            with self.subTest(url=bad):
                self.assertEqual(r.fetch(bad).status, RetrievalStatus.FAILED)

    def test_robots_disallow_is_obeyed_not_circumvented(self) -> None:
        url = "https://noindex.com/a"
        session = _Session({
            "https://noindex.com/robots.txt": _Response(
                body=b"User-agent: *\nDisallow: /", ctype="text/plain",
                url="https://noindex.com/robots.txt"),
            url: _Response(body=ARTICLE.encode(), url=url),
        })
        r = Retriever(session=session, cache_dir=Path(tempfile.mkdtemp()),
                      respect_robots=True, per_domain_delay=0.0)
        # robots.txt is fetched with the module-level requests, so drive the
        # decision directly to keep this test hermetic.
        r._robots._cache["https://noindex.com"] = _DisallowAll()
        result = r.fetch(url)
        self.assertEqual(result.status, RetrievalStatus.BLOCKED)
        self.assertIn("robots", result.skipped_reason)
        self.assertNotIn(url, session.calls, "a disallowed URL must never be requested")


class _DisallowAll:
    def can_fetch(self, agent, url):  # noqa: ARG002
        return False


class EvidenceUpgrade(unittest.TestCase):
    """Reading properly is what raises evidence level, and therefore depth."""

    def test_reading_the_body_upgrades_evidence_and_unlocks_depth(self) -> None:
        url = "https://example.com/a"
        obj = IntelligenceObject(
            object_id="o1", primary_sector="commercial_real_estate",
            title="Blackstone acquires portfolio for $450 million",
            sources=[SourceRef(item_id="s1", source_name="Wire",
                               canonical_url=url, source_url=url)],
        )
        obj.assess_evidence()
        self.assertEqual(obj.evidence_level, "single_summary")
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_c")

        r, _ = _retriever({url: _Response(body=ARTICLE.encode(), url=url)})
        enrich_objects([obj], retriever=r, budget_seconds=30)

        self.assertEqual(obj.sources[0].retrieval_status, RetrievalStatus.FULL_TEXT)
        self.assertIn("Blackstone agreed", obj.sources[0].retrieved_text)
        self.assertTrue(
            any(fact.name == "amount" and "$450 million" in str(fact.value)
                for fact in obj.facts)
        )
        self.assertEqual(obj.evidence_level, "single_full_text")
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_b")

    def test_two_read_sources_reach_corroborated(self) -> None:
        a, b = "https://one.com/x", "https://two.com/y"
        obj = IntelligenceObject(
            object_id="o2", primary_sector="commercial_real_estate",
            title="Savills completes $1.1B acquisition",
            sources=[
                SourceRef(item_id="s1", source_name="One", canonical_url=a, source_url=a),
                SourceRef(item_id="s2", source_name="Two", canonical_url=b, source_url=b),
            ],
        )
        r, _ = _retriever({
            a: _Response(body=ARTICLE.encode(), url=a),
            b: _Response(body=ARTICLE.encode(), url=b),
        })
        enrich_objects([obj], retriever=r, budget_seconds=30)
        self.assertEqual(obj.evidence_level, "corroborated")
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_a")

    def test_a_blocked_source_does_not_inflate_evidence(self) -> None:
        url = "https://paywalled.com/a"
        obj = IntelligenceObject(
            object_id="o3", primary_sector="commercial_real_estate",
            title="Deal reported behind a paywall",
            sources=[SourceRef(item_id="s1", source_name="Paywalled",
                               canonical_url=url, source_url=url)],
        )
        r, _ = _retriever({url: _Response(status=403, url=url)})
        enrich_objects([obj], retriever=r, budget_seconds=30)
        self.assertEqual(obj.sources[0].retrieval_status, RetrievalStatus.BLOCKED)
        self.assertEqual(obj.usable_full_text_count, 0)
        self.assertEqual(obj.cap_depth_to_evidence("tier_a"), "tier_c")

    def test_report_totals_are_recorded_for_the_run_artifact(self) -> None:
        good, blocked = "https://good.com/a", "https://blocked.com/a"
        objs = [
            IntelligenceObject(object_id="a", primary_sector="x", title="A",
                               sources=[SourceRef(item_id="1", source_name="G", canonical_url=good)]),
            IntelligenceObject(object_id="b", primary_sector="x", title="B",
                               sources=[SourceRef(item_id="2", source_name="B", canonical_url=blocked)]),
        ]
        r, _ = _retriever({
            good: _Response(body=ARTICLE.encode(), url=good),
            blocked: _Response(status=403, url=blocked),
        })
        report = enrich_objects(objs, retriever=r, budget_seconds=30)
        self.assertEqual(report.requested, 2)
        self.assertEqual(report.fetched, 1)
        self.assertEqual(report.blocked, 1)
        self.assertIn(RetrievalStatus.FULL_TEXT, report.by_status)


if __name__ == "__main__":
    unittest.main()
