"""Quick Takes: five verified lines per story, every line checked, nothing posted."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import takes  # noqa: E402
from linkedin_post import Story  # noqa: E402
from test_v4_generation import FakeVerifier  # noqa: E402

FACTS = [
    "Median family income rose 7 percent to $82,200.",
    "Mean family income fell 6 percent to $145,200.",
    "The figures compare the 2022 and 2025 surveys.",
    "Families in the upper ends of the distribution saw declines.",
]


def story(n: int = 1, facts=FACTS) -> Story:
    return Story(id=f"s{n}", object_id=f"obj{n}", title=f"Fed survey {n}", sector="fed_macro", score=80 - n,
                 url=f"https://lighttowergroup.co/insights/survey-{n}.html", facts=list(facts), reads=[])


GOOD = {"formula": "Two Numbers, One Story", "lines": [
    {"kind": "fact", "text": "Median family income rose 7 percent to $82,200."},
    {"kind": "fact", "text": "Mean family income fell 6 percent to $145,200."},
    {"kind": "read", "text": "I read that as quieter, broader gains."},
    {"kind": "kicker", "text": "Averages flatter. Medians tell you how people live."},
]}
WORSE = {"formula": "Translate the Jargon", "lines": [
    {"kind": "fact", "text": "Mean family income fell 6 percent to $145,200."},
    {"kind": "fact", "text": "That is a $63,000 gap between mean and median."},          # arithmetic: cut
    {"kind": "read", "text": "I think the top is trying to hide its losses."},            # motive: cut
    {"kind": "kicker", "text": "#Economics matters."},                                     # hashtag: cut
]}
NO_HOOK = {"formula": "History Rhymes", "lines": [
    {"kind": "kicker", "text": "Some things never change."},
    {"kind": "read", "text": "I read this as a familiar pattern."},
]}


class Writer:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def __call__(self, system, user):
        self.calls += 1
        return json.dumps(self.payload)


class TakeTests(unittest.TestCase):
    def build(self, payload, checker=None, stories=None):
        return takes.build_takes(stories or [story()], Writer(payload), checker or FakeVerifier(), workers=1)

    def test_best_candidate_wins_and_the_rest_are_alternates(self):
        out = self.build({"takes": [WORSE, GOOD, NO_HOOK]})
        self.assertEqual(len(out), 1)
        take = out[0]
        self.assertEqual(take.formula, "Two Numbers, One Story")
        self.assertEqual(take.text.splitlines()[0], "Median family income rose 7 percent to $82,200.")
        self.assertEqual(len(take.text.splitlines()), 4)
        self.assertEqual(take.alternates, [])  # WORSE keeps one line after its cuts; NO_HOOK has no fact hook
        self.assertEqual(take.rank, 1)
        self.assertEqual(take.article_url, "https://lighttowergroup.co/insights/survey-1.html")

    def test_invented_figure_motive_and_hashtag_are_cut(self):
        self.assertEqual(self.build({"takes": [WORSE]}), [])  # one line left is not a take
        take = self.build({"takes": [GOOD, WORSE]})[0]
        self.assertNotIn("63,000", take.text)
        self.assertNotIn("trying to", take.text)
        self.assertNotIn("#", take.text)
        self.assertTrue(all("63,000" not in a["text"] for a in take.alternates))
        reasons = " ".join(take.dropped)
        self.assertIn("figures not in the source", reasons)
        self.assertIn("trying to", reasons)
        self.assertIn("hashtag", reasons)

    def test_a_kicker_may_state_no_fact(self):
        payload = {"takes": [{"formula": "x", "lines": GOOD["lines"][:2] + [
            {"kind": "kicker", "text": "Watch the 2028 survey."}]}]}
        take = self.build(payload)[0]
        self.assertNotIn("2028", take.text)

    def test_second_model_veto_removes_a_fact_line(self):
        take = self.build({"takes": [GOOD]}, checker=FakeVerifier(reject=("Mean family",)))[0]
        self.assertNotIn("Mean family", take.text)

    def test_thin_stories_get_no_take(self):
        self.assertEqual(self.build({"takes": [GOOD]}, stories=[story(1, FACTS[:2])]), [])

    def test_never_longer_than_five_lines_or_450_characters(self):
        long_lines = [{"kind": "fact", "text": FACTS[i % 4]} for i in range(8)]
        take = self.build({"takes": [{"formula": "x", "lines": long_lines}]})[0]
        self.assertLessEqual(len(take.text.splitlines()), takes.MAX_LINES)
        self.assertLessEqual(len(take.text), takes.MAX_CHARS)

    def test_feed_is_newest_first_replaces_a_story_and_drops_old_takes(self):
        path = Path(tempfile.mkdtemp()) / "takes.json"
        path.write_text(json.dumps({"takes": [
            {"id": "take-obj1", "date": "2026-10-20", "rank": 1, "text": "old take"},
            {"id": "take-old", "date": "2026-07-01", "rank": 1, "text": "ancient"},
            {"id": "take-other", "date": "2026-10-20", "rank": 2, "text": "kept"},
        ]}), encoding="utf-8")
        today = self.build({"takes": [GOOD]})
        feed = takes.merge_feed(path, today, now=datetime(2026, 10, 23))
        ids = [e["id"] for e in feed]
        self.assertEqual(ids[0], "take-obj1")
        self.assertNotIn("take-old", ids)
        self.assertIn("take-other", ids)
        self.assertEqual(sum(1 for i in ids if i == "take-obj1"), 1)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["takes"][0]["chars"], len(today[0].text))


if __name__ == "__main__":
    unittest.main()
