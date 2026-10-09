from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import claim_verifier as cv  # noqa: E402

SOURCE = (
    "Harbor Capital closed a $50 million loan on Pier House, a 120-unit apartment building in Brooklyn. "
    "Meridian Bank provided the two-year loan. Broker Dana Lee said the deal was \"a fair price for the block\". "
    "The interest rate was not disclosed."
)


def _items(user: str):
    atomic = "SENTENCES TO CHECK:" not in user
    block = (user.split("SENTENCES:")[1].split("For each sentence:")[0] if atomic
             else user.split("SENTENCES TO CHECK:")[1].split("Rules by kind:")[0])
    return json.loads(block), atomic


def judge(user: str, bad=lambda sentence: False, issue: str = "adds a claim", only_pass: str = "") -> str:
    items, atomic = _items(user)
    pass_name = "atomic" if atomic else "first"
    rows = []
    for i in items:
        flagged = bad(i["sentence"]) and (not only_pass or only_pass == pass_name)
        row = {"id": i["id"], "verdict": "unsupported" if flagged else "supported", "issue": issue if flagged else ""}
        if atomic:
            row["claims"] = [{"claim": i["sentence"], "supported": not flagged}]
        rows.append(row)
    return json.dumps({"results": rows})


def supportive(system: str, user: str) -> str:
    return judge(user)


def draft(**overrides) -> dict:
    base = {
        "title": "Harbor Capital closes Pier House loan", "title_quote": "Harbor Capital closed a $50 million loan on Pier House",
        "excerpt": "Harbor Capital closed a $50 million loan on Pier House in Brooklyn.", "excerpt_quote": "Harbor Capital closed a $50 million loan on Pier House, a 120-unit apartment building in Brooklyn",
        "paragraphs": [[{"text": "Harbor Capital closed a $50 million loan on Pier House.", "kind": "fact",
                         "quotes": ["Harbor Capital closed a $50 million loan on Pier House"]}]],
    }
    base.update(overrides)
    return base


def body(*sentences: dict) -> dict:
    return draft(paragraphs=[list(sentences)])


def fact(text: str, *quotes: str) -> dict:
    return {"text": text, "kind": "fact", "quotes": list(quotes)}


class DeterministicTests(unittest.TestCase):
    def kept(self, d: dict) -> list[str]:
        v = cv.verify_draft(d, SOURCE, supportive)
        return [i.text for p in v.paragraphs for i in p]

    def test_quote_must_be_verbatim_in_the_source(self):
        good = fact("Meridian Bank provided the loan.", "Meridian Bank provided the two-year loan")
        fake = fact("Meridian Bank guaranteed the loan.", "Meridian Bank guaranteed the whole loan")
        self.assertEqual(self.kept(body(good, fake)), ["Meridian Bank provided the loan."])

    def test_punctuation_and_case_cannot_hide_a_mismatch_but_do_not_cause_one(self):
        ok = fact("Harbor Capital closed it.", "harbor capital CLOSED a $50 million loan")
        self.assertEqual(self.kept(body(ok)), ["Harbor Capital closed it."])

    def test_numbers_and_spelled_numbers_must_be_in_the_quote(self):
        wrong = fact("Meridian Bank provided a three-year loan.", "Meridian Bank provided the two-year loan")
        wrong2 = fact("Harbor Capital closed a $60 million loan.", "Harbor Capital closed a $50 million loan on Pier House")
        self.assertEqual(self.kept(body(wrong, wrong2)), [])

    def test_names_must_be_in_the_quote(self):
        self.assertEqual(self.kept(body(fact("Harbor Capital bought it from Tishman Speyer.",
                                             "Harbor Capital closed a $50 million loan on Pier House"))), [])

    def test_quoted_words_must_exist_in_the_source(self):
        real = fact('Lee called it "a fair price for the block".', 'Dana Lee said the deal was "a fair price for the block"')
        fake = fact('Lee called it "a steal".', 'Dana Lee said the deal was "a fair price for the block"')
        self.assertEqual(self.kept(body(real, fake)), ['Lee called it "a fair price for the block".'])

    def test_short_quote_is_not_evidence(self):
        self.assertEqual(self.kept(body(fact("Harbor closed it.", "Harbor Capital closed"))), [])

    def test_opinion_sentences_are_never_kept(self):
        f = fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House")
        d = draft(paragraphs=[[f], [{"text": "Our read: lenders likely stay patient.", "kind": "view", "quotes": []}]])
        v = cv.verify_draft(d, SOURCE, supportive)
        self.assertEqual([i.kind for p in v.paragraphs for i in p], ["fact"])
        self.assertIn("only sentences backed by a source quote", " ".join(i.reason for i in v.rejected))

    def test_dropped_qualifiers_and_attribution_are_rejected(self):
        src = "Meridian Bank said it expects to keep most of the loan. Dana Lee said the block was a fair price."
        q1 = "Meridian Bank said it expects to keep most of the loan"
        q2 = "Dana Lee said the block was a fair price"
        v = cv.verify_draft(body(fact("Meridian Bank keeps the loan.", q1),
                                 fact("Meridian Bank said it expects to keep most of the loan.", q1),
                                 fact("The block was a fair price.", q2),
                                 fact("Dana Lee said the block was a fair price.", q2)), src, supportive)
        kept = [i.text for p in v.paragraphs for i in p]
        self.assertEqual(kept, ["Meridian Bank said it expects to keep most of the loan.",
                                "Dana Lee said the block was a fair price."])
        reasons = " ".join(i.reason for i in v.rejected)
        self.assertIn("drops the qualifier", reasons)
        self.assertIn("drops the attribution", reasons)

    def test_unusable_shapes_raise(self):
        with self.assertRaises(ValueError):
            cv.verify_draft({"title": "x", "paragraphs": []}, SOURCE, supportive)
        with self.assertRaises(ValueError):
            cv.verify_draft(body({"text": "x y z", "kind": "opinion", "quotes": []}), SOURCE, supportive)


class VerifierModelTests(unittest.TestCase):
    def test_model_veto_removes_the_sentence_and_records_the_reason(self):
        def veto(system: str, user: str) -> str:
            return judge(user, bad=lambda sentence: "Meridian" in sentence, issue="reverses who lent")
        d = body(fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House"),
                 fact("Meridian Bank provided the loan.", "Meridian Bank provided the two-year loan"))
        v = cv.verify_draft(d, SOURCE, veto)
        self.assertEqual([i.text for p in v.paragraphs for i in p], ["Harbor Capital closed a $50 million loan on Pier House."])
        self.assertIn("reverses who lent", v.rejected_report()[0])

    def test_incomplete_or_malformed_verifier_output_fails_closed(self):
        d = body(fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House"))
        with self.assertRaises(ValueError):
            cv.verify_draft(d, SOURCE, lambda s, u: json.dumps({"results": []}))
        with self.assertRaises(ValueError):
            cv.verify_draft(d, SOURCE, lambda s, u: json.dumps({"results": [{"id": "s1", "verdict": "maybe"}]}))
        with self.assertRaises(json.JSONDecodeError):
            cv.verify_draft(d, SOURCE, lambda s, u: "not json")

    def test_the_second_pass_can_veto_what_the_first_pass_accepted(self):
        def only_second(system: str, user: str) -> str:
            return judge(user, bad=lambda sentence: "Meridian" in sentence, issue="partial claim", only_pass="atomic")
        d = body(fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House"),
                 fact("Meridian Bank provided the loan.", "Meridian Bank provided the two-year loan"))
        v = cv.verify_draft(d, SOURCE, only_second)
        self.assertEqual([i.text for p in v.paragraphs for i in p], ["Harbor Capital closed a $50 million loan on Pier House."])
        self.assertIn("partial claim", v.rejected_report()[0])

    def test_sentences_failing_deterministic_checks_are_never_sent_to_the_model(self):
        seen = []
        def spy(system: str, user: str) -> str:
            seen.append(user)
            return supportive(system, user)
        d = body(fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House"),
                 fact("It was a $99 million loan.", "Harbor Capital closed a $50 million loan on Pier House"))
        cv.verify_draft(d, SOURCE, spy)
        self.assertTrue(all("$99 million" not in call for call in seen))

    def test_assembly_joins_verified_sentences_by_paragraph(self):
        f1 = fact("Harbor Capital closed a $50 million loan on Pier House.", "Harbor Capital closed a $50 million loan on Pier House")
        f2 = fact("Meridian Bank provided the loan.", "Meridian Bank provided the two-year loan")
        v = cv.verify_draft(draft(paragraphs=[[f1, f2]]), SOURCE, supportive)
        self.assertEqual(cv.assemble_paragraphs(v),
                         ["Harbor Capital closed a $50 million loan on Pier House. Meridian Bank provided the loan."])


if __name__ == "__main__":
    unittest.main()
