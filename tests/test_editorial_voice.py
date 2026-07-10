from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from editorial_voice import editorial_quality_issues, select_editorial_brief
from enhanced_prompts import USER_PROMPT_TEMPLATE
from linkedin_essay_agent import _revision_prompt, generate_essay_package, save_to_queue
from linkedin_essay_agent import decorate_package


class EditorialVoiceTests(unittest.TestCase):
    def test_editorial_mode_avoids_recent_mode(self) -> None:
        article = {"slug": "sample-refi", "title": "Sample Refi", "category": "Debt & Equity"}
        brief = select_editorial_brief(article, [{"voice_mode": "Underwriting margin"}])
        self.assertNotEqual(brief["name"], "Underwriting margin")
        self.assertIn("opening_move", brief)
        self.assertIn("stance", brief)

    def test_quality_gate_detects_repeated_ai_patterns_and_mojibake(self) -> None:
        draft = (
            "The most important number in this deal is not the price.\n\n"
            "The real story is the capital stack.\n\n"
            "This is a useful sentence. â€” Broken encoding is not publishable."
        )
        issues = editorial_quality_issues(draft, min_characters=1)
        self.assertTrue(any("canned" in issue for issue in issues))
        self.assertIn("possible character-encoding corruption", issues)

    def test_fallback_essay_never_enters_publish_queue(self) -> None:
        article = {
            "slug": "sample-refi",
            "title": "Sample Refi",
            "excerpt": "A lender refinanced a mixed-use building.",
            "category": "Debt & Equity",
        }
        package = generate_essay_package(article, api_key="")
        self.assertFalse(package["publish_ready"])
        self.assertEqual(package["editorial_review"]["status"], "needs_revision")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_to_queue(package, Path(directory) / "essay-queue.json")

    def test_invalid_optional_hook_is_removed_before_review(self) -> None:
        article = {"slug": "sample", "title": "Sample", "excerpt": "Source-backed detail."}
        brief = select_editorial_brief(article)
        package = decorate_package(
            {
                "voice_mode": brief["name"],
                "linkedin_essay": "A" * 800,
                "alternate_hooks": ["The real story is the debt.", "A specific fresh observation."],
                "strong_closing_lines": ["A complete, source-grounded implication."],
            },
            article,
            "https://lighttowergroup.co/insights/sample.html",
            "standard",
            brief,
        )
        self.assertEqual(package["alternate_hooks"], ["A specific fresh observation."])

    def test_revision_prompt_carries_the_independent_findings(self) -> None:
        brief = select_editorial_brief({"slug": "sample", "title": "Sample"})
        prompt = _revision_prompt({"linkedin_essay": "Draft"}, ["canned 'real story' pivot"], brief)
        self.assertIn("canned 'real story' pivot", prompt)
        self.assertIn(brief["name"], prompt)

    def test_insight_prompt_accepts_an_assigned_editorial_brief(self) -> None:
        brief = select_editorial_brief({"slug": "sample", "title": "Sample"})
        prompt = USER_PROMPT_TEMPLATE.format(
            title="Sample",
            source="Source",
            url="https://example.org/source",
            published_date="July 10, 2026",
            summary="A reported fact.",
            full_text="More reported facts.",
            addresses_block="",
            today="July 10, 2026",
            voice_brief=str(brief),
        )
        self.assertIn(brief["name"], prompt)


if __name__ == "__main__":
    unittest.main()
