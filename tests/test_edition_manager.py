from __future__ import annotations

import sys
import unittest
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import edition_manager
from edition_manager import build_edition_document, calculate_read_time, save_publication_decision


class EditionManagerTests(unittest.TestCase):
    def test_read_time_is_calculated_from_body(self) -> None:
        self.assertEqual(calculate_read_time("<p>" + "word " * 450 + "</p>"), 2)

    def test_no_flagship_is_a_valid_edition(self) -> None:
        document = build_edition_document(
            edition_date=date(2026, 7, 23),
            selection={"candidate_count": 8, "event_count": 7, "deal_tape": [], "duplicate_groups": []},
            articles=[{
                "event_id": "event",
                "title": "A concise brief",
                "subtitle": "What changed.",
                "slug": "concise-brief",
                "category": "Capital Markets",
                "editorial_format": "brief",
                "body_html": "<p>" + "word " * 250 + "</p>",
                "sources": [{"url": "https://source.example/story"}],
            }],
        )
        self.assertIsNone(document["flagship"])
        self.assertEqual(len(document["briefs"]), 1)
        self.assertTrue(document["selection_summary"]["no_flagship"])

    def test_flagship_requires_human_editorial_review(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "decision.json"
            with patch.object(edition_manager, "PUBLICATION_DECISION_PATH", path):
                save_publication_decision(
                    edition_status="ready",
                    articles=[{
                        "title": "A consequential analysis",
                        "editorial_format": "flagship",
                        "research_evidence_level": "deep",
                        "must_read_score": 88,
                    }],
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["review_required"])
            self.assertFalse(payload["auto_publish_allowed"])


if __name__ == "__main__":
    unittest.main()
