"""The daily LinkedIn roundup: built only from verified sentences, checked again, never posted."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import linkedin_post as lp  # noqa: E402
from test_v4_generation import FakeVerifier  # noqa: E402


def _story(n: int, sector: str = "commercial_real_estate", reads: tuple[str, ...] = ()) -> lp.Story:
    return lp.Story(id=f"s{n}", object_id=f"o{n}", title=f"Harbor Capital closes loan {n}", sector=sector,
                    score=90 - n, url=f"https://lighttowergroup.co/insights/story-{n}.html",
                    facts=[f"Harbor Capital closed a ${n}0 million loan on Pier House.",
                           "Meridian Bank provided the three-year loan."],
                    reads=list(reads))


def _draft(ids, *, bad_line: str = "") -> dict:
    stories = []
    for i in ids:
        lines = [f"Harbor Capital closed a ${i}0 million loan on Pier House."]
        if bad_line:
            lines.append(bad_line)
        stories.append({"id": f"s{i}", "headline": f"Harbor Capital closes ${i}0M loan", "lines": lines,
                        "read": "I read this as a lender at ease with a familiar borrower." if i == 1 else ""})
    return {"hook": ["Harbor Capital closed a $10 million loan on Pier House.", "Not a bad week to borrow."],
            "hook_story": "s1", "stories": stories, "close": "What would you have asked the lender?"}


class Writer:
    def __init__(self, *drafts):
        self.drafts, self.calls = list(drafts), []

    def __call__(self, system, user):
        self.calls.append(user)
        return json.dumps(self.drafts[min(len(self.calls), len(self.drafts)) - 1])


class LinkedInPostTests(unittest.TestCase):
    def test_roundup_template_with_reads_question_and_link_comment(self):
        stories = [_story(1, reads=("I read this as a lender at ease with a familiar borrower.",)), _story(2), _story(3)]
        post = lp.build(stories, Writer(_draft([1, 2, 3])), FakeVerifier())
        self.assertEqual(post.status, "ok")
        text = post.text
        self.assertTrue(text.startswith("Harbor Capital closed a $10 million loan on Pier House.\nNot a bad week to borrow."))
        self.assertIn("3 stories from today's capital markets tape 👇", text)
        self.assertIn("🏢 Harbor Capital closes $20M loan\n→ Harbor Capital closed a $20 million loan", text)
        self.assertIn("💬 I read this as a lender at ease", text)
        self.assertIn("What would you have asked the lender?", text)
        self.assertIn("link in the first comment", text)
        self.assertIn("#CRE", text)
        self.assertLess(len(text), 3000)
        self.assertIn("https://lighttowergroup.co/insights.html", post.comment)
        self.assertIn("https://lighttowergroup.co/insights/story-1.html", post.comment)

    def test_a_line_with_a_figure_the_story_never_gave_is_deleted_and_rewritten_once(self):
        stories = [_story(1), _story(2)]
        writer = Writer(_draft([1, 2], bad_line="The loan carries a 6.5% rate."), _draft([1, 2]))
        post = lp.build(stories, writer, FakeVerifier())
        self.assertNotIn("6.5%", post.text)
        self.assertEqual(len(writer.calls), 2)
        self.assertIn("deleted, with the reason", writer.calls[1])
        self.assertEqual(post.dropped, [])

    def test_lines_the_second_model_rejects_never_appear(self):
        post = lp.build([_story(1), _story(2)], Writer(_draft([1, 2], bad_line="Meridian Bank provided the three-year loan.")),
                        FakeVerifier(reject=("Meridian",)))
        self.assertNotIn("Meridian", post.text)

    def test_too_few_stories_means_no_post(self):
        self.assertTrue(lp.build([_story(1)], Writer(_draft([1])), FakeVerifier()).status.startswith("skipped"))

    def test_long_days_are_trimmed_under_the_limit_and_say_how_many_more(self):
        stories = [_story(n) for n in range(1, 13)]
        draft = _draft(range(1, 9))
        for entry in draft["stories"]:
            entry["lines"].append("Meridian Bank provided the three-year loan. " * 3)
        post = lp.build(stories, Writer(draft), FakeVerifier())
        self.assertLessEqual(len(post.text), lp.MAX_CHARS)
        self.assertRegex(post.text, r"\+ \d+ more stories on the site today\.")

    def test_only_published_stories_are_used_when_the_day_published(self):
        run = Path(tempfile.mkdtemp())
        (run / "v4-evidence").mkdir()
        for oid in ("live", "held"):
            (run / "v4-evidence" / f"{oid}.json").write_text(json.dumps({
                "object_id": oid, "title": oid, "sector": "energy",
                "paragraphs": [[{"kind": "fact", "text": "A fact.", "quotes": ["A fact."]}]]}), encoding="utf-8")
        (run / "v3-run.json").write_text(json.dumps({"publication": {"articles": [
            {"event_id": "live", "url": "/insights/live.html"}]}}), encoding="utf-8")
        stories = lp.load_stories(run)
        self.assertEqual([s.object_id for s in stories], ["live"])
        self.assertEqual(stories[0].url, "https://lighttowergroup.co/insights/live.html")


if __name__ == "__main__":
    unittest.main()
