from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ben_voice as bv  # noqa: E402
import voice_gate as vg  # noqa: E402

SOURCE = (
    "PRP Real Assets paid around $30M for the 117K SF building at 900 19th St. NW. "
    "The building is roughly 60% vacant. Tishman Speyer had owned the building since 2006."
)
Q1 = "PRP Real Assets paid around $30M for the 117K SF building at 900 19th St. NW"
Q2 = "The building is roughly 60% vacant"


def judge(system: str, user: str) -> str:
    """Stands in for the model passes: everything supported, every opinion acceptable."""
    if "SENTENCES TO RULE ON" in user:
        block = user.split("SENTENCES TO RULE ON:")[1].split("Rules.")[0]
        return json.dumps({"results": [{"id": i["id"], "verdict": "ok", "issue": ""} for i in json.loads(block)]})
    atomic = "SENTENCES TO CHECK:" not in user
    block = (user.split("SENTENCES:")[1].split("For each sentence:")[0] if atomic
             else user.split("SENTENCES TO CHECK:")[1].split("Rules by kind:")[0])
    rows = []
    for i in json.loads(block):
        row = {"id": i["id"], "verdict": "supported", "issue": ""}
        if atomic:
            row["claims"] = [{"claim": i["sentence"], "supported": True}]
        rows.append(row)
    return json.dumps({"results": rows})


def draft(*extra: dict) -> dict:
    sentences = [
        {"id": "s1", "kind": "fact", "text": "PRP Real Assets paid around $30M for the 117K SF building at 900 19th St. NW.", "quotes": [Q1]},
        {"id": "s2", "kind": "fact", "text": "The building is roughly 60% vacant.", "quotes": [Q2]},
        *extra,
    ]
    return {"title": "PRP buys a mostly empty building", "title_quote": "PRP Real Assets paid around $30M for the 117K SF building",
            "excerpt": "PRP Real Assets paid around $30M for a building at 900 19th St. NW that is roughly 60% vacant.",
            "excerpt_quote": Q1, "paragraphs": [{"role": "hook", "sentences": sentences}]}


def take(text: str, because=("s1", "s2"), kind="take", sid="s3") -> dict:
    return {"id": sid, "kind": kind, "text": text, "because": list(because)}


def kept(result: vg.VoiceDraft) -> list[str]:
    return [i.text for _, items in result.paragraphs for i in items]


class VoiceLayerTests(unittest.TestCase):
    def run_gate(self, *extra: dict, **kw) -> vg.VoiceDraft:
        return vg.verify_voice_draft(draft(*extra), SOURCE, judge, **kw)

    def test_a_framed_take_citing_verified_facts_survives(self):
        result = self.run_gate(take("I read this as a bet that the vacancy gets filled."))
        self.assertIn("I read this as a bet that the vacancy gets filled.", kept(result))
        self.assertEqual((result.fact_count, result.take_count), (2, 1))

    def test_facts_keep_the_full_gate(self):
        bad = {"id": "s9", "kind": "fact", "text": "PRP paid $35M.", "quotes": [Q1]}
        result = self.run_gate(bad)
        self.assertNotIn("PRP paid $35M.", kept(result))
        self.assertTrue(any("figures not in its quote" in r for r in result.fact_rejections))

    def test_a_take_must_cite_surviving_facts(self):
        result = self.run_gate(take("I read this as a bet.", because=()))
        self.assertEqual(result.take_count, 0)
        self.assertTrue(any("cite at least one" in i.reason for i in result.rejected))

    def test_a_take_that_rests_on_a_rejected_fact_is_dropped(self):
        bad = {"id": "s8", "kind": "fact", "text": "PRP paid $35M.", "quotes": [Q1]}
        result = self.run_gate(bad, take("I read that price as a stretch.", because=("s8",)))
        self.assertEqual(result.take_count, 0)

    def test_new_numbers_and_names_in_a_take_are_rejected(self):
        for text in ("I read this as a $40M bet.", "I read this as a signal for Blackstone."):
            result = self.run_gate(take(text))
            self.assertEqual(result.take_count, 0, text)

    def test_loaded_labels_and_attributed_decisions_are_rejected(self):
        for text in ("I read this as fresh capital buying distressed buildings at a lower basis.",
                     "I read the sale as proof that the owner decides not to reinvest."):
            result = self.run_gate(take(text))
            self.assertEqual(result.take_count, 0, text)

    def test_sweeping_market_claims_must_be_framed_as_a_reading(self):
        result = self.run_gate(take("Investors are concentrating in a few mega-managers."))
        self.assertEqual(result.take_count, 0)

    def test_experience_claims_need_a_note(self):
        result = self.run_gate(take("I toured it last week and I read this as a bet."))
        self.assertEqual(result.take_count, 0)

    def test_voice_lines_may_not_carry_numbers_names_or_experience(self):
        for text in ("Not a $30M bet.", "That is a lot for Tishman.", "I called the broker about it."):
            result = self.run_gate(take(text, kind="voice"))
            self.assertEqual(result.voice_count, 0, text)
        result = self.run_gate(take("Not a small bet.", kind="voice"))
        self.assertEqual(result.voice_count, 1)

    def test_context_and_ben_lines_need_a_real_entry_and_add_nothing(self):
        bank = [{"id": "c1", "text": "Rates rose sharply in 2022."}]
        notes = [{"id": "n1", "text": "My first deal closed in a snowstorm."}]
        ok = {"id": "s4", "kind": "context", "text": "Rates rose sharply in 2022.", "ref": "c1"}
        extra = {"id": "s5", "kind": "context", "text": "Rates rose sharply in 2022 and hit offices hardest.", "ref": "c1"}
        missing = {"id": "s6", "kind": "ben", "text": "My first deal closed in a snowstorm.", "ref": "zz"}
        real = {"id": "s7", "kind": "ben", "text": "My first deal closed in a snowstorm.", "ref": "n1"}
        result = self.run_gate(ok, extra, missing, real, context=bank, notes=notes)
        texts = kept(result)
        self.assertIn("Rates rose sharply in 2022.", texts)
        self.assertNotIn("Rates rose sharply in 2022 and hit offices hardest.", texts)
        self.assertEqual(texts.count("My first deal closed in a snowstorm."), 1)

    def test_the_rubric_pass_can_veto_an_opinion(self):
        def veto(system: str, user: str) -> str:
            if "SENTENCES TO RULE ON" in user:
                block = user.split("SENTENCES TO RULE ON:")[1].split("Rules.")[0]
                return json.dumps({"results": [{"id": i["id"], "verdict": "reject", "issue": "adds a premise"}
                                               for i in json.loads(block)]})
            return judge(system, user)
        result = vg.verify_voice_draft(draft(take("I read this as a bet.")), SOURCE, veto)
        self.assertEqual(result.take_count, 0)
        self.assertTrue(any("adds a premise" in i.reason for i in result.rejected))

    def test_an_incomplete_rubric_answer_fails_closed(self):
        def broken(system: str, user: str) -> str:
            if "SENTENCES TO RULE ON" in user:
                return json.dumps({"results": []})
            return judge(system, user)
        with self.assertRaises(ValueError):
            vg.verify_voice_draft(draft(take("I read this as a bet.")), SOURCE, broken)

    def test_unknown_kinds_and_shapes_raise(self):
        with self.assertRaises(ValueError):
            vg.parse_voice_draft({"paragraphs": [{"role": "hook", "sentences": [{"kind": "rant", "text": "x y z"}]}]})
        with self.assertRaises(ValueError):
            vg.parse_voice_draft({"paragraphs": []})


class PromptAssemblyTests(unittest.TestCase):
    def test_system_prompt_states_the_two_layer_rule_and_the_contract(self):
        text = bv.system_prompt()
        for needle in ("TWO-LAYER RULE", "ACCURACY CONTRACT", "Ben Rohr", "kind"):
            self.assertIn(needle, text)
        self.assertNotIn("astrology", text.lower().replace("never mention astrology", ""))

    def test_brief_and_article_prompts_fill_every_placeholder(self):
        brief = bv.brief_prompt("A story", "tier_b", '{"sources":[]}')
        self.assertNotIn("{{", brief)
        for name in bv.SHAPES:
            self.assertIn(name, brief)
        article = bv.article_prompt(story="A story", fmt="analysis", min_words=100, max_words=520,
                                    brief={"shape": "The Clock", "hooks": []}, sources_json="{}")
        self.assertNotIn("{{", article)
        self.assertIn("none supplied", article)  # empty banks are stated, never silently skipped
        self.assertIn("The Clock", article)

    def test_banks_show_entries_and_empty_banks_are_explicit(self):
        block = bv.banks_block([{"id": "c1", "text": "Fact."}], [])
        self.assertIn("c1: Fact.", block)
        self.assertIn("make no experience claims", block)


if __name__ == "__main__":
    unittest.main()


class RehearsalFindings(unittest.TestCase):
    """Sentences the 2026-10-09 rehearsal let through, which a human read rejected."""

    FACTS = {
        "f1": "Solomon said in a statement that their departures were part of an administrative restructuring.",
        "f2": "The termination fee is $480M.",
        "f3": "A grocery-anchored center in Huntington Beach traded for about $589 per square foot.",
    }

    def check(self, kind: str, text: str, because=("f1",)):
        from voice_gate import VoiceItem, check_voice_item
        item = VoiceItem(id="t", kind=kind, text=text, because=list(because))
        check_voice_item(item, self.FACTS, [], [])
        return item.problems

    def test_intent_claims_are_rejected(self):
        self.assertTrue(self.check("take", "My read is that the mayor is trying to rebuild a team that can close the gap."))
        self.assertTrue(self.check("take", "The pattern I see is a company paying a large price, betting that the savings will outweigh the fee.",
                                   because=("f2",)))

    def test_findings_and_predictions_elsewhere_are_rejected(self):
        self.assertTrue(self.check("take", "The resignations show how fiscal stress can destabilize city leadership."))
        self.assertTrue(self.check("take", "I read this as a pattern likely to repeat in other municipalities."))

    def test_stock_deadline_lines_are_rejected(self):
        self.assertTrue(self.check("voice", "The clock is running."))
        self.assertTrue(self.check("voice", "That is a serious charge, and the clock is already ticking."))

    def test_fair_readings_still_pass(self):
        self.assertEqual(self.check("take", "I read the price as a bet on scarcity, not just on the tenant roster.",
                                    because=("f3",)), [])
        self.assertEqual(self.check("voice", "That number says more than any press release."), [])


class DecodingRepair(unittest.TestCase):
    def test_replacement_character_between_letters_becomes_an_apostrophe(self):
        import v4_generation
        self.assertEqual(v4_generation._repair_decoding("Mayor Solomon�s office � today"),
                         "Mayor Solomon’s office  today")
