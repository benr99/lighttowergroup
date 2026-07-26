from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from edition_manager import build_edition_document
from editorial_intelligence import select_edition
from editorial_room import excellence_issues, run_editorial_room
from research_dossier import build_research_dossier
from story_normalizer import normalize_story


def _story(title: str, source: str, url: str, summary: str) -> dict:
    return normalize_story({
        "title": title,
        "source": source,
        "url": url,
        "summary": summary,
        "published": "2026-07-23T12:00:00+00:00",
    })


class CuratedPipelineIntegrationTests(unittest.TestCase):
    def test_deep_event_survives_selection_research_room_and_edition_contracts(self) -> None:
        stories = [
            _story(
                "Historic Orchard Stadium District $1.2B loan enters special servicing",
                "The Real Deal",
                "https://therealdeal.com/orchard-stadium",
                (
                    "The owner missed a payment on the mixed-use project. The debt matures "
                    "in 2026, the district employs 4,000 workers, and foreclosure is possible."
                ),
            ),
            _story(
                "Orchard Stadium District's $1.2B loan hits special servicing after default",
                "Commercial Observer",
                "https://commercialobserver.com/orchard-stadium",
                (
                    "The missed payment threatens tenants, 4,000 jobs, and a taxpayer-backed "
                    "subsidy while the 2026 maturity approaches."
                ),
            ),
            _story(
                "$1.2B Orchard Stadium District debt faces foreclosure after owner default",
                "Bloomberg",
                "https://bloomberg.com/orchard-stadium",
                (
                    "The stadium development faces a workout after a missed payment, exposing "
                    "local businesses and public money to the restructuring."
                ),
            ),
        ]

        selection = select_edition(stories)
        self.assertEqual(selection["event_count"], 1)
        self.assertEqual(len(selection["selected_stories"]), 1)
        assignment = selection["selected_stories"][0]
        self.assertEqual(assignment["provisional_format"], "flagship")
        self.assertGreaterEqual(assignment["must_read_score"], 72)

        fetched = {
            stories[0]["url"]: (
                "The servicer reported that the $1.2 billion loan matures in 2026. "
                'A spokesperson said "The district remains open while talks continue."'
            ),
            stories[1]["url"]: (
                "Records show the project supports 4,000 workers and received a public subsidy. "
                "The borrower missed its scheduled payment."
            ),
            stories[2]["url"]: (
                "The financing entered special servicing after the default. "
                "Foreclosure and an extension are among the possible outcomes."
            ),
        }
        dossier = build_research_dossier(assignment, fetched_text_by_url=fetched)
        self.assertEqual(dossier["evidence_level"], "deep")
        self.assertTrue(dossier["longform_allowed"])

        room = run_editorial_room(assignment, dossier, api_key="")
        self.assertEqual(room["decision"], "write")
        self.assertEqual(room["final_format"], "flagship")

        memorable_line = "The debt clock is now part of the district's public life."
        sources = [{"url": source["url"], "name": source["source"]} for source in stories]
        article = {
            "event_id": assignment["event_id"],
            "title": "When a Stadium District's Debt Clock Becomes Public",
            "subtitle": "A missed payment changes more than the lender's timetable.",
            "slug": "orchard-stadium-debt-clock",
            "category": "Capital Markets",
            "editorial_format": room["final_format"],
            "editorial_format_label": "Flagship Analysis",
            "franchise": assignment["franchise"],
            "must_read_score": assignment["must_read_score"],
            "research_evidence_level": dossier["evidence_level"],
            "body_html": f"<p>{'reported analysis ' * 400}{memorable_line}</p>",
            "sources": sources,
            "excellence_ledger": {
                "why_now": "The loan has newly entered special servicing.",
                "original_inference": "The maturity now affects public as well as private choices.",
                "counterargument": "An extension could still preserve the original operating plan.",
                "concrete_detail": "The district supports 4,000 workers.",
                "human_stakes": "Workers, tenants, and taxpayers share the consequences.",
                "reader_value": "The structure identifies where bargaining power has shifted.",
                "memorable_line": memorable_line,
                "claim_evidence": [{
                    "claim": "The loan matures in 2026.",
                    "source_url": stories[0]["url"],
                }],
            },
        }
        self.assertEqual(
            excellence_issues(article, dossier, article_format="flagship"),
            [],
        )

        edition = build_edition_document(
            edition_date=date(2026, 7, 23),
            selection=selection,
            articles=[article],
        )
        self.assertEqual(edition["status"], "ready")
        self.assertEqual(edition["flagship"]["slug"], article["slug"])
        self.assertEqual(edition["selection_summary"]["articles"], 1)
        self.assertFalse(edition["selection_summary"]["no_flagship"])


if __name__ == "__main__":
    unittest.main()
