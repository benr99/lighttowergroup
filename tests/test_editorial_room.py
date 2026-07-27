from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from editorial_room import deterministic_room_plan, excellence_issues, run_editorial_room


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

    def test_fact_rich_daily_depth_brief_is_not_killed_for_being_single_source(self) -> None:
        event = {
            "candidate": {"title": "A reported office upgrade", "summary": "Reported facts."},
            "provisional_format": "brief",
            "selection_tier": "daily_depth",
            "legal_or_allegation_risk": False,
            "franchise": {"promise": "Explain the institutional capital decision."},
        }
        evidence = {
            **dossier(),
            "usable_full_text_count": 1,
            "reported_facts": [
                {"fact": f"Reported fact {index}.", "source_url": "https://source.example/story"}
                for index in range(4)
            ],
        }
        model_result = {
            "decision": "defer",
            "final_format": "brief",
            "kill_reason": "Only one source is available and there are no human stakes.",
        }
        with patch(
            "editorial_room.call_deepseek",
            return_value=json.dumps(model_result),
        ):
            plan = run_editorial_room(event, evidence, api_key="test-key")
        self.assertEqual(plan["decision"], "shorten")
        self.assertEqual(plan["final_format"], "brief")
        self.assertTrue(plan["daily_depth_floor_applied"])

    def test_daily_depth_floor_never_overrides_a_legal_risk_stop(self) -> None:
        event = {
            "candidate": {"title": "A disputed transaction", "summary": "Reported facts."},
            "provisional_format": "brief",
            "selection_tier": "daily_depth",
            "legal_or_allegation_risk": False,
        }
        evidence = {
            **dossier(),
            "usable_full_text_count": 1,
            "reported_facts": [
                {"fact": f"Reported fact {index}.", "source_url": "https://source.example/story"}
                for index in range(4)
            ],
        }
        model_result = {
            "decision": "defer",
            "final_format": "brief",
            "kill_reason": "The source contains fraud allegations and active litigation.",
        }
        with patch(
            "editorial_room.call_deepseek",
            return_value=json.dumps(model_result),
        ):
            plan = run_editorial_room(event, evidence, api_key="test-key")
        self.assertEqual(plan["decision"], "defer")
        self.assertFalse(plan.get("daily_depth_floor_applied", False))

    def test_brief_rejects_redevelopment_mislabeled_as_new_supply(self) -> None:
        article = {
            "body_html": (
                "<p>The $200 million redevelopment will deliver 350,000 square "
                "feet of new office supply in 2028.</p>"
            ),
            "sources": [{"url": "https://source.example/story"}],
        }
        evidence = {
            **dossier(),
            "sources": [{
                "url": "https://source.example/story",
                "summary": "The owner will modernize the existing office tower.",
                "full_text_excerpt": (
                    "The gut renovation strips the 350,000-square-foot building "
                    "to its steel frame and installs a new curtain wall."
                ),
            }],
        }
        issues = excellence_issues(article, evidence, article_format="brief")
        self.assertIn(
            "excellence gate: redevelopment is mislabeled as net-new supply",
            issues,
        )

    def test_brief_rejects_a_stack_of_hypothetical_scenarios(self) -> None:
        body = (
            "The project may miss its budget. It could struggle to find tenants. "
            "The owner might delay construction. The site could remain vacant. "
            + "Reported facts and bounded analysis. " * 45
        )
        article = {
            "body_html": f"<p>{body}</p>",
            "sources": [{"url": "https://source.example/story"}],
        }
        issues = excellence_issues(article, dossier(), article_format="brief")
        self.assertIn(
            "excellence gate: brief stacks too many hypothetical claims",
            issues,
        )


if __name__ == "__main__":
    unittest.main()
