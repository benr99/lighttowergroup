from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import readability as r  # noqa: E402


class NumberGuardTests(unittest.TestCase):
    source = "A $16,782,000 loan on 631 units; a 479 million bridge; NOI $12.5M; rate 6.5%."

    def test_rescaling_and_rounding_are_faithful(self) -> None:
        self.assertEqual(r.unsupported_numbers("$16.8 million on 631 units at 6.5%", self.source), [])
        self.assertEqual(r.unsupported_numbers("a $479 million bridge", self.source), [])

    def test_derived_and_hypothetical_numbers_are_flagged(self) -> None:
        self.assertEqual(r.unsupported_numbers("equity of $149 million", self.source), ["149"])
        self.assertEqual(r.unsupported_numbers("a 25-basis-point hike", self.source), ["25"])


class NameGuardTests(unittest.TestCase):
    def test_flags_places_the_source_never_named(self) -> None:
        source = "TPG bought the portfolio in Florida and Georgia from DRA Advisors."
        text = "TPG bought it. The buildings sit in Florida, Georgia and Tampa. DRA Advisors sold."
        self.assertEqual(r.unsupported_names(text, source), ["Tampa"])

    def test_sentence_openers_and_months_are_not_names(self) -> None:
        self.assertEqual(r.unsupported_names("Ask your lender. Why it matters: rates moved in August.", "rates moved"), [])


class WarningTests(unittest.TestCase):
    def test_clean_short_copy_has_no_warnings(self) -> None:
        paras = ["A lender priced a loan at 6.5%. That is cheaper than last month.",
                 "Why it matters: sponsors can refinance sooner.",
                 "Ask your lender whether the same terms are on offer."]
        self.assertEqual(r.readability_warnings(paras, excerpt="A lender priced a loan at 6.5%, and sponsors may refinance sooner than planned."), [])

    def test_dense_copy_is_flagged_with_actionable_messages(self) -> None:
        long_sentence = " ".join(["word"] * 50) + "."
        warnings = " ".join(r.readability_warnings([long_sentence, "What remains unknown is the price."]))
        self.assertIn("Split these sentences", warnings)
        self.assertIn("Do not close on what is unknown", warnings)

    def test_banned_phrases_and_bad_excerpt(self) -> None:
        text = " ".join(r.readability_warnings(["It is worth noting the landscape shifted."], excerpt="Too short"))
        self.assertIn("landscape", text)
        self.assertIn("excerpt must be one complete sentence", text)

    def test_trim_to_sentence_never_cuts_mid_word(self) -> None:
        out = r.trim_to_sentence("First sentence is here. Second sentence runs on and on without stopping soon.", 40)
        self.assertEqual(out, "First sentence is here.")
        out = r.trim_to_sentence("one two three four five six seven eight nine ten eleven twelve", 30)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn("elev", out)


if __name__ == "__main__":
    unittest.main()
