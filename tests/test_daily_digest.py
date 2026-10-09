"""The daily digest and health note are built offline from a run folder."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import daily_digest  # noqa: E402


def _run_folder() -> Path:
    run = Path(tempfile.mkdtemp())
    (run / "v4-evidence").mkdir()
    (run / "v3-run.json").write_text(json.dumps({
        "run_at": "2026-10-09T11:07:00+00:00", "mode": "preview", "elapsed_seconds": 1500,
        "publication_candidates": 3, "warnings": ["1 of 3 drafts were withheld"], "errors": [],
        "spend": {"spent_this_run_usd": 0.84, "spent_today_usd": 0.84, "daily_limit_usd": 25.0},
        "generation": {"requested": 3, "written": 1, "stop_reason": ""},
    }), encoding="utf-8")
    (run / "v3-drafts.json").write_text(json.dumps({"drafts": [
        {"title": "Harbor <Capital> loan", "status": "completed", "article": {"voice": "ben"}},
        {"title": "H.8 notice", "status": "withheld", "skipped_reason": "could not be verified"},
        {"title": "Slow story", "status": "failed", "errors": ["Timeout"]},
    ]}), encoding="utf-8")
    (run / "v4-evidence" / "harbor.json").write_text(json.dumps({
        "title": "Harbor <Capital> loan", "excerpt": "An excerpt.", "sector": "commercial_real_estate",
        "depth": "tier_b", "mode": "voice", "sources": ["https://source.example/a"],
        "paragraphs": [[
            {"kind": "fact", "text": "Harbor Capital closed a $50 million loan.",
             "quotes": ["Harbor Capital closed a $50 million loan"]},
            {"kind": "take", "text": "I read this as a vote of confidence.", "because": ["s1"],
             "because_text": ["Harbor Capital closed a $50 million loan."]},
        ]],
        "rejected": [{"kind": "take", "text": "Harbor wants out.", "reason": "attributes a private state"}],
    }), encoding="utf-8")
    return run


class DigestTests(unittest.TestCase):
    def test_digest_shows_sentences_quotes_cuts_and_unpublished(self):
        digest, health = daily_digest.build(_run_folder())
        page = digest.read_text(encoding="utf-8")
        self.assertIn("Harbor Capital closed a $50 million loan.", page)
        self.assertIn("<blockquote>Harbor Capital closed a $50 million loan</blockquote>", page)
        self.assertIn("Ben&#x27;s read", page)
        self.assertIn("attributes a private state", page)
        self.assertIn("could not be verified", page)
        self.assertIn("Harbor &lt;Capital&gt; loan", page)  # escaped, never raw HTML
        self.assertNotIn("<Capital>", page)
        note = health.read_text(encoding="utf-8")
        self.assertIn("1 written (1 in Ben's voice), 1 withheld", note)
        self.assertIn("NEEDS A LOOK", note)  # one story failed
        self.assertIn("$0.84", note)

    def test_clean_day_is_ok(self):
        run = _run_folder()
        drafts = json.loads((run / "v3-drafts.json").read_text(encoding="utf-8"))
        drafts["drafts"] = drafts["drafts"][:2]
        (run / "v3-drafts.json").write_text(json.dumps(drafts), encoding="utf-8")
        self.assertIn("  OK", daily_digest.health_note(daily_digest.load_run(run)).splitlines()[0])

    def test_empty_folder_still_builds(self):
        digest, health = daily_digest.build(Path(tempfile.mkdtemp()))
        self.assertIn("No stories were published", digest.read_text(encoding="utf-8"))
        self.assertTrue(health.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
