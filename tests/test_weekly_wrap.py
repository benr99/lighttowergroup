from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import weekly_wrap as w  # noqa: E402


def rec(title: str, day: str, *tags: str, **extra) -> dict:
    base = {
        "title": title, "slug": w.re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
        "date": day, "category": "Deal Intelligence", "excerpt": f"{title}. More detail follows here.",
        "tags": list(tags), "format": "brief", "mustReadScore": 40, "sourceCount": 1,
        "sourceName": "Test Wire", "sourceUrl": "https://example.com/a",
    }
    base.update(extra)
    return base


class WindowTests(unittest.TestCase):
    def test_latest_friday_and_window(self) -> None:
        self.assertEqual(w.latest_friday(date(2026, 10, 9)), date(2026, 10, 9))
        self.assertEqual(w.latest_friday(date(2026, 10, 8)), date(2026, 10, 2))
        self.assertEqual(w.latest_friday(date(2026, 10, 11)), date(2026, 10, 9))
        start, end = w.week_window(date(2026, 10, 9))
        self.assertEqual((start, end), (date(2026, 10, 3), date(2026, 10, 9)))
        self.assertEqual(w.week_label(start, end), "Oct 3 to Oct 9")

    def test_load_week_items_filters_window_wraps_and_bad_dates(self) -> None:
        manifest = [
            rec("In window", "2026-10-05"),
            rec("Too early", "2026-10-02"),
            rec("Too late", "2026-10-10"),
            rec("Legacy date", "April 29, 2026"),
            rec("Prior wrap", "2026-10-05", format="weekly", category="Weekly Wrap"),
            {"title": "No slug", "date": "2026-10-05"},
        ]
        got = w.load_week_items(manifest, date(2026, 10, 3), date(2026, 10, 9))
        self.assertEqual([r["title"] for r in got], ["In window"])


class ClassifyTests(unittest.TestCase):
    def test_tags_decide_first(self) -> None:
        cases = {
            "fed_rates": rec("Cook speaks", "2026-10-05", "fed_macro"),
            "data_centers": rec("Campus filed", "2026-10-05", "commercial_real_estate", "data_centers"),
            "multifamily": rec("Bridge loan on a tower", "2026-10-05", "commercial_real_estate", "multifamily"),
            "industrial": rec("Logistics park trades", "2026-10-05", "industrial_logistics"),
            "debt_capital": rec("Bank enforcement", "2026-10-05", "banking_credit", "multifamily"),
            "private_equity": rec("Fund closes", "2026-10-05", "private_equity"),
            "policy": rec("Council vote", "2026-10-05", "local_government", "city_council"),
            "energy": rec("Storage awards", "2026-10-05", "energy", "battery_storage"),
        }
        for expected, record in cases.items():
            self.assertEqual(w.classify(record), expected, record["title"])

    def test_keyword_fallback_for_untagged_items(self) -> None:
        self.assertEqual(w.classify(rec("New hotel opens in Midtown", "2026-10-05", "SL Green")), "hospitality")
        self.assertEqual(w.classify(rec("CMBS spreads tighten on lender demand", "2026-10-05", "Capital Markets")), "debt_capital")
        self.assertEqual(w.classify(rec("Founder profile", "2026-10-05", "Misc")), "other_cre")


class SelectionTests(unittest.TestCase):
    def test_dedup_cap_and_order(self) -> None:
        items = [rec(f"Apartment deal {n}", "2026-10-05", "multifamily", mustReadScore=80 - n, eventId=f"e{n}")
                 for n in range(10)]
        items.append(rec("Apartment deal 1", "2026-10-06", "multifamily", mustReadScore=10, eventId="e1"))
        items.append(rec("Treasury yields jump", "2026-10-06", "fed_macro", mustReadScore=50))
        picked = w.select_for_wrap(items, max_per_section=5)
        self.assertEqual(list(picked), ["fed_rates", "multifamily"])  # page order, not insertion order
        self.assertEqual(len(picked["multifamily"]), 5)
        titles = [r["title"] for r in picked["multifamily"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_cre_relevant_story_outranks_adjacent_news(self) -> None:
        items = [
            rec("Fintech charter approved", "2026-10-05", "fed_macro", mustReadScore=50, excerpt="A card bank gets approval."),
            rec("Lender trims mortgage rates", "2026-10-05", "fed_macro", mustReadScore=45, excerpt="Mortgage lenders cut rates."),
        ]
        picked = w.select_for_wrap(items, max_per_section=1)
        self.assertEqual(picked["fed_rates"][0]["title"], "Lender trims mortgage rates")


class ReadLeadTests(unittest.TestCase):
    def test_extracts_body_paragraphs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page = (
                '<p>nav text that is long enough to be ignored by the body extractor ok</p>'
                '<div class="article-body" itemprop="articleBody"><p>First body paragraph with enough words to count here.</p>'
                '<p>Second body paragraph also carries real reporting detail for the wrap.</p></div>\n\n'
                '      <div class="article-tags"></div><p>Talk to Light Tower Group and more footer words here too</p>'
            )
            (Path(tmp) / "x.html").write_text(page, encoding="utf-8")
            lead = w.read_lead("x", insights_dir=Path(tmp))
            self.assertIn("First body paragraph", lead)
            self.assertIn("Second body paragraph", lead)
            self.assertNotIn("nav text", lead)
            self.assertNotIn("Talk to Light Tower", lead)
            self.assertEqual(w.read_lead("missing", insights_dir=Path(tmp)), "")


class GuardTests(unittest.TestCase):
    def test_unsupported_numbers(self) -> None:
        source = "Walker arranged a $238 million bridge loan on 631 units at 6.5% in Doral. Cap rate 5,500 bps."
        self.assertEqual(w.unsupported_numbers("A $238 million loan, 631 units, 6.5%", source), [])
        self.assertEqual(w.unsupported_numbers("A $239 million loan on 631 units", source), ["239"])
        self.assertEqual(w.unsupported_numbers("5,500 bps", source), [])

    def test_first_sentences_never_cuts_mid_sentence(self) -> None:
        cut = "Treasury hired a longtime strategist as counselor to the Secretary, adding a vocal advocate for lower rates and a"
        out = w.first_sentences(cut)
        self.assertTrue(out.endswith("…"), out)
        self.assertEqual(w.first_sentences("One. Two is a bit longer than one. Three arrives last.", 40), "One. Two is a bit longer than one.")

    def test_scheduled_guard(self) -> None:
        ny = w.NEW_YORK
        self.assertEqual(w._scheduled_guard(datetime(2026, 10, 9, 16, 30, tzinfo=ny)), "")
        self.assertIn("Friday", w._scheduled_guard(datetime(2026, 10, 8, 16, 30, tzinfo=ny)))
        self.assertIn("window", w._scheduled_guard(datetime(2026, 10, 9, 15, 30, tzinfo=ny)))


def _items(n: int, tag: str = "multifamily") -> list[dict]:
    out = []
    for i in range(n):
        item = rec(f"Loan {i} closes", "2026-10-05", tag)
        item["_id"] = f"m{i + 1}"
        item["_context"] = f"{item['excerpt']} Lender provided $50 million for 100 units."
        out.append(item)
    return out


class WriteSectionTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        items = _items(2)

        def llm(system: str, user: str) -> str:
            return json.dumps({"read": "Lenders stayed active.", "items": [
                {"id": "m1", "summary": "A lender provided $50 million for 100 units.", "take": "Banks still back sponsors with clean plans."},
                {"id": "m2", "summary": "Another $50 million loan closed.", "take": "Pricing looks steady for now."},
            ]})

        result = w.write_section("multifamily", items, "Oct 3 to Oct 9", llm)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.fallback_ids, [])
        self.assertEqual(result.read, "Lenders stayed active.")
        self.assertEqual(result.notes["m1"]["take"], "Banks still back sponsors with clean plans.")

    def test_invented_number_triggers_retry_then_passes(self) -> None:
        items = _items(1)
        calls = []

        def llm(system: str, user: str) -> str:
            calls.append(user)
            summary = "A lender provided $75 million." if len(calls) == 1 else "A lender provided $50 million."
            return json.dumps({"read": "", "items": [{"id": "m1", "summary": summary, "take": "Steady credit."}]})

        result = w.write_section("multifamily", items, "w", llm)
        self.assertEqual(result.attempts, 2)
        self.assertIn("not in the item text: 75", calls[1])
        self.assertEqual(result.fallback_ids, [])
        self.assertIn("$50 million", result.notes["m1"]["summary"])

    def test_persistent_failure_falls_back_to_excerpt_without_take(self) -> None:
        items = _items(1)

        def llm(system: str, user: str) -> str:
            return json.dumps({"items": [{"id": "m1", "summary": "A $999 million deal.", "take": "Wow."}]})

        result = w.write_section("multifamily", items, "w", llm)
        self.assertEqual(result.fallback_ids, ["m1"])
        self.assertEqual(result.notes["m1"]["take"], "")
        self.assertTrue(result.notes["m1"]["summary"])

    def test_banned_phrase_is_rejected(self) -> None:
        items = _items(1)
        outputs = iter(["It remains to be seen how this plays out.", "Lenders are likely to stay selective."])

        def llm(system: str, user: str) -> str:
            return json.dumps({"items": [{"id": "m1", "summary": "A $50 million loan closed.", "take": next(outputs)}]})

        result = w.write_section("multifamily", items, "w", llm)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.notes["m1"]["take"], "Lenders are likely to stay selective.")

    def test_no_llm_uses_excerpts(self) -> None:
        result = w.write_section("multifamily", _items(2), "w", None)
        self.assertEqual(result.attempts, 0)
        self.assertEqual(len(result.fallback_ids), 2)


def _verifier(*reject: str, error: Exception | None = None):
    def check(system: str, user: str) -> str:
        if error:
            raise error
        atomic = "SENTENCES TO CHECK:" not in user
        block = (user.split("SENTENCES:")[1].split("For each sentence:")[0] if atomic
                 else user.split("SENTENCES TO CHECK:")[1].split("Rules by kind:")[0])
        results = []
        for entry in json.loads(block):
            bad = any(marker in entry["sentence"] for marker in reject)
            row = {"id": entry["id"], "verdict": "unsupported" if bad else "supported",
                   "issue": "adds a claim" if bad else ""}
            if atomic:
                row["claims"] = [{"claim": entry["sentence"], "supported": not bad}]
            results.append(row)
        return json.dumps({"results": results})
    return check


class FactCheckTests(unittest.TestCase):
    @staticmethod
    def _llm(summary: str, take: str):
        def llm(system: str, user: str) -> str:
            return json.dumps({"read": "", "items": [{"id": "m1", "summary": summary, "take": take}]})
        return llm

    def test_a_take_the_checker_rejects_is_omitted(self) -> None:
        result = w.write_section("multifamily", _items(1), "w",
                                 self._llm("A lender provided $50 million for 100 units.", "Banks likely stay patient."),
                                 verifier=_verifier("patient"))
        self.assertEqual(result.notes["m1"]["take"], "")
        self.assertEqual(result.fallback_ids, [])
        self.assertIn("$50 million", result.notes["m1"]["summary"])
        self.assertTrue(any("take rejected" in p for p in result.problems))

    def test_a_summary_the_checker_rejects_reverts_to_the_excerpt(self) -> None:
        result = w.write_section("multifamily", _items(1), "w",
                                 self._llm("A lender provided $50 million for 100 units.", "Banks likely stay patient."),
                                 verifier=_verifier("lender provided"))
        self.assertEqual(result.fallback_ids, ["m1"])
        self.assertEqual(result.notes["m1"]["take"], "")
        self.assertNotIn("lender provided", result.notes["m1"]["summary"])

    def test_an_unavailable_checker_fails_closed(self) -> None:
        result = w.write_section("multifamily", _items(1), "w",
                                 self._llm("A lender provided $50 million for 100 units.", "Banks likely stay patient."),
                                 verifier=_verifier(error=RuntimeError("fact-check unavailable")))
        self.assertEqual(result.fallback_ids, ["m1"])
        self.assertEqual(result.notes["m1"]["take"], "")

    def test_a_take_that_adds_a_figure_never_reaches_the_checker(self) -> None:
        seen = []
        def spy(system: str, user: str) -> str:
            seen.append(user)
            return _verifier()(system, user)
        result = w.write_section("multifamily", _items(1), "w",
                                 self._llm("A lender provided $50 million.", "Banks likely lend 7 more."), verifier=spy)
        self.assertEqual(result.notes["m1"]["take"], "")
        self.assertNotIn("lend 7 more", seen[0] if seen else "")


class BuildWrapTests(unittest.TestCase):
    def test_insufficient_items_does_not_build(self) -> None:
        out = w.build_wrap([rec("Only one", "2026-10-05", "multifamily")], date(2026, 10, 9), None, min_items=8)
        self.assertEqual(out["status"], "insufficient_items")
        self.assertNotIn("article", out)

    def test_full_build_without_llm_is_valid_and_escaped(self) -> None:
        manifest = [rec(f"Tower <{i}> & Co refinance", "2026-10-06", "multifamily", mustReadScore=50 - i)
                    for i in range(6)]
        manifest += [rec(f"Hotel deal {i}", "2026-10-07", "hospitality") for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            out = w.build_wrap(manifest, date(2026, 10, 9), None, insights_dir=Path(tmp),
                               now=datetime(2026, 10, 9, 20, 30, tzinfo=w.timezone.utc))
        self.assertEqual(out["status"], "ok")
        article = out["article"]
        self.assertEqual(article["slug"], "weekly-wrap-2026-10-09")
        self.assertEqual(article["editorial_format"], "weekly")
        self.assertEqual(article["category"], "Weekly Wrap")
        self.assertNotIn("&", article["title"].replace("&amp;", ""))
        self.assertNotIn("<Tower", article["body_html"])  # raw item markup is escaped
        self.assertIn("&lt;0&gt;", article["body_html"])
        self.assertIn("<h2>Multifamily</h2>", article["body_html"])
        self.assertIn("<h2>Hospitality</h2>", article["body_html"])
        self.assertTrue(article["sources"][0]["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
