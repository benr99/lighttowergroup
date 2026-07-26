from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from editorial_room import deterministic_room_plan, excellence_issues


def dossier(source_count: int = 1, longform: bool = False) -> dict:
    return {
        "evidence_level": "deep" if longform else "thin",
        "independent_source_count": source_count,
        "longform_allowed": longform,
        "sources": [{"url": "https://source.example/story"}],
        "reported_facts": [{"fact": "The $80 million loan matures in 2027."}],
        "reporting_gaps": [],
    }


class EditorialRoomTests(unittest.TestCase):
    def test_flagship_is_downgraded_when_dossier_is_thin(self) -> None:
        event = {
            "candidate": {"title": "A reported event", "summary": "Reported facts."},
            "provisional_format": "flagship",
            "franchise": {"promise": "Explain the underlying decision."},
        }
        plan = deterministic_room_plan(event, dossier())
        self.assertEqual(plan["final_format"], "brief")

    def test_excellence_gate_requires_positive_ledger(self) -> None:
        article = {
            "body_html": "<p>" + "Reported analysis " * 150 + "</p>",
            "sources": [{"url": "https://source.example/story"}],
        }
        issues = excellence_issues(article, dossier(), article_format="brief")
        self.assertIn("excellence gate: positive-quality ledger is missing", issues)

    def test_complete_brief_can_clear_excellence_gate(self) -> None:
        memorable = "The maturity date is now a negotiating party."
        body = " ".join(["Reported evidence and careful analysis."] * 62) + " " + memorable
        article = {
            "body_html": f"<p>{body}</p>",
            "sources": [{"url": "https://source.example/story"}],
            "excellence_ledger": {
                "why_now": "The extension deadline is approaching.",
                "original_inference": "Time changes the parties' alternatives.",
                "counterargument": "A private extension could resolve the pressure.",
                "concrete_detail": "The loan matures in 2027.",
                "human_stakes": "Residents depend on stable ownership.",
                "reader_value": "Test the extension path before underwriting proceeds.",
                "memorable_line": memorable,
                "claim_evidence": [{"claim": "The loan matures in 2027.", "source_url": "https://source.example/story"}],
            },
        }
        self.assertEqual(excellence_issues(article, dossier(), article_format="brief"), [])


if __name__ == "__main__":
    unittest.main()
