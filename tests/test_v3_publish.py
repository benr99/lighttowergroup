"""Putting drafts on the site, safely enough to run unattended.

The tests that matter are idempotence and ordering. A job that runs twice must
not publish twice, and a crash halfway must not leave the manifest pointing at
pages that were never written.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import v3_publish  # noqa: E402
from intelligence_object import IntelligenceObject, SourceRef  # noqa: E402
from v3_generation import DraftResult  # noqa: E402
from v3_publish import _article_payload, make_slug, publish  # noqa: E402


def _obj(title: str, *, sector: str = "commercial_real_estate") -> IntelligenceObject:
    node = IntelligenceObject(
        object_id=f"obj-{abs(hash(title)) % 9999}", primary_sector=sector, title=title,
        sources=[SourceRef(item_id="s", source_name="Wire",
                           canonical_url="https://wire.example.com/a")],
    )
    node.assess_evidence()
    return node


def _draft(obj, *, status="completed", depth="tier_b", title=None) -> DraftResult:
    return DraftResult(
        object_id=obj.object_id, title=title or obj.title, sector=obj.primary_sector,
        depth=depth, status=status,
        article={"title": title or obj.title, "body_html": "<p>Text.</p>",
                 "excerpt": "An excerpt.", "sources": [{"name": "Wire", "url": "https://w.com/a"}]},
    )


class _Sandbox:
    """Redirect the module at a temporary site so tests touch nothing real."""

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "insights").mkdir()
        self._orig = (v3_publish.SITE_ROOT, v3_publish.INSIGHTS_DIR)
        v3_publish.SITE_ROOT = self.tmp
        v3_publish.INSIGHTS_DIR = self.tmp / "insights"
        self.render = mock.patch(
            "daily_news_agent.render_html", side_effect=lambda a: f"<html>{a['title']}</html>"
        )
        self.manifest = mock.patch("daily_news_agent.update_manifest")
        self.feed = mock.patch("daily_news_agent.update_feed_xml")
        self.sitemap = mock.patch("daily_news_agent.update_sitemap_xml")
        self.mocks = [m.start() for m in (self.render, self.manifest, self.feed, self.sitemap)]
        return self

    def __exit__(self, *exc):
        for m in (self.render, self.manifest, self.feed, self.sitemap):
            m.stop()
        v3_publish.SITE_ROOT, v3_publish.INSIGHTS_DIR = self._orig
        return False


class Slugs(unittest.TestCase):
    def test_a_slug_is_readable_and_url_safe(self) -> None:
        self.assertEqual(
            make_slug("Segro Accepts $18.8B Takeover Approach"),
            "segro-accepts-18-8b-takeover-approach",
        )

    def test_collisions_get_a_suffix_rather_than_overwriting(self) -> None:
        existing = {"a-deal-closes"}
        self.assertEqual(make_slug("A deal closes", existing=existing), "a-deal-closes-2")

    def test_an_empty_title_still_produces_something(self) -> None:
        self.assertTrue(make_slug(""))


class PublishesFinishedWork(unittest.TestCase):
    def test_v3_payload_satisfies_the_real_shared_renderer_contract(self) -> None:
        from daily_news_agent import render_html

        obj = _obj("Blackstone acquires Phoenix portfolio for $450 million")
        draft = _draft(obj)
        payload = _article_payload(draft, obj, make_slug(draft.title))
        html = render_html(payload)
        self.assertIn(payload["date"], html)
        self.assertIn(payload["date_iso"], html)
        self.assertIn(payload["title"], html)

    def test_a_completed_draft_becomes_a_page(self) -> None:
        obj = _obj("Blackstone acquires Phoenix portfolio for $450 million")
        with _Sandbox() as box:
            report = publish([_draft(obj)], {obj.object_id: obj})
            self.assertEqual(report.published, 1)
            pages = list((box.tmp / "insights").glob("*.html"))
            self.assertEqual(len(pages), 1)
            self.assertIn("insights.json", report.files_written)

    def test_the_indexes_are_updated_once_after_every_page_exists(self) -> None:
        objs = [_obj(f"Deal number {i} closes for ${i}00 million") for i in range(3)]
        drafts = [_draft(o) for o in objs]
        with _Sandbox() as box:
            publish(drafts, {o.object_id: o for o in objs})
            _, manifest, feed, sitemap = box.mocks
            self.assertEqual(manifest.call_count, 3)
            self.assertEqual(feed.call_count, 1, "the feed is rebuilt once, not per article")
            self.assertEqual(sitemap.call_count, 1)

    def test_a_story_flagged_for_review_is_held_back_by_default(self) -> None:
        obj = _obj("A story needing review")
        with _Sandbox():
            report = publish([_draft(obj, status="review_required")], {obj.object_id: obj})
            self.assertEqual(report.published, 0)
            self.assertEqual(report.skipped_review, 1)

    def test_review_can_be_included_deliberately(self) -> None:
        obj = _obj("A story needing review")
        with _Sandbox():
            report = publish([_draft(obj, status="review_required")], {obj.object_id: obj},
                             include_review_required=True)
            self.assertEqual(report.published, 1)

    def test_an_unfinished_draft_is_never_published(self) -> None:
        obj = _obj("A failed story")
        draft = _draft(obj, status="draft_failed")
        draft.article = None
        with _Sandbox():
            report = publish([draft], {obj.object_id: obj})
            self.assertEqual(report.published, 0)


class SafeToRunTwice(unittest.TestCase):
    """An unattended job that repeats must not duplicate the edition."""

    def test_the_same_story_is_not_published_twice(self) -> None:
        obj = _obj("Segro accepts $18.8B takeover")
        with _Sandbox():
            first = publish([_draft(obj)], {obj.object_id: obj})
            second = publish([_draft(obj)], {obj.object_id: obj})
            self.assertEqual(first.published, 1)
            self.assertEqual(second.published, 0)
            self.assertEqual(second.skipped_existing, 1)

    def test_a_dry_run_writes_nothing(self) -> None:
        obj = _obj("A deal closes for $50 million")
        with _Sandbox() as box:
            report = publish([_draft(obj)], {obj.object_id: obj}, dry_run=True)
            self.assertEqual(report.published, 1)
            self.assertEqual(list((box.tmp / "insights").glob("*.html")), [])
            self.assertEqual(report.files_written, [])

    def test_every_written_file_is_reported_for_rollback(self) -> None:
        obj = _obj("A deal closes for $50 million")
        with _Sandbox():
            report = publish([_draft(obj)], {obj.object_id: obj})
            self.assertTrue(any(f.endswith(".html") for f in report.files_written))
            self.assertIn("sitemap.xml", report.files_written)


class RemembersWhatItPublished(unittest.TestCase):
    def test_publishing_records_the_story_in_memory(self) -> None:
        from editorial_memory import EditorialMemory
        from intelligence_object import NoveltyState

        obj = _obj("Starwood sells $1 billion apartment stake")
        memory = EditorialMemory(Path(tempfile.mkdtemp()) / "m.json")
        with _Sandbox():
            publish([_draft(obj)], {obj.object_id: obj}, memory=memory)
        verdict = memory.assess(_obj("Starwood sells $1 billion apartment stake"))
        self.assertEqual(verdict.state, NoveltyState.ALREADY_PUBLISHED,
                         "tomorrow's run must know this was covered")


class FailureIsolation(unittest.TestCase):
    def test_one_bad_article_does_not_stop_the_rest(self) -> None:
        good, bad = _obj("Good story for $10 million"), _obj("Bad story for $20 million")
        drafts = [_draft(good), _draft(bad)]
        with _Sandbox() as box:
            calls = {"n": 0}

            def flaky(article):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("render exploded")
                return "<html>ok</html>"

            box.mocks[0].side_effect = flaky
            report = publish(drafts, {good.object_id: good, bad.object_id: bad})
        self.assertEqual(report.published, 1)
        self.assertEqual(report.failed, 1)

    def test_nothing_to_publish_is_handled(self) -> None:
        with _Sandbox():
            report = publish([], {})
            self.assertEqual(report.requested, 0)
            self.assertEqual(report.published, 0)


if __name__ == "__main__":
    unittest.main()
