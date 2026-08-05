"""Remembering what we covered, so an unattended system stops repeating itself.

Novelty was a constant 7 for every story. These tests exist because the moment
the pipeline publishes without a person watching, a memory failure means the
same deal runs twice.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from editorial_memory import EditorialMemory, MemoryRecord  # noqa: E402
from intelligence_object import IntelligenceObject, NoveltyState, SourceRef  # noqa: E402


def _obj(title: str, summary: str = "", *, sector: str = "commercial_real_estate",
         selected: bool = False) -> IntelligenceObject:
    node = IntelligenceObject(
        object_id=title[:16], cluster_id=title[:16], primary_sector=sector,
        title=title, what_happened=summary, selected=selected,
        sources=[SourceRef(item_id="s1", source_name="Wire",
                           canonical_url=f"https://x.com/{abs(hash(title)) % 9999}")],
    )
    node.assess_evidence()
    return node


def _memory() -> EditorialMemory:
    return EditorialMemory(Path(tempfile.mkdtemp()) / "memory.json")


class NewStories(unittest.TestCase):
    def test_an_unseen_story_is_new_and_scores_high(self) -> None:
        verdict = _memory().assess(_obj("Blackstone acquires Phoenix portfolio for $450 million"))
        self.assertEqual(verdict.state, NoveltyState.NEW)
        self.assertGreaterEqual(verdict.score, 8)

    def test_unrelated_stories_do_not_match_each_other(self) -> None:
        memory = _memory()
        memory.observe([_obj("Blackstone acquires Phoenix portfolio for $450 million")])
        verdict = memory.assess(_obj("Fed holds rates steady at September meeting", sector="fed_macro"))
        self.assertEqual(verdict.state, NoveltyState.NEW)


class RepeatCoverage(unittest.TestCase):
    """The failure that matters most once it publishes unattended."""

    def test_a_published_story_is_not_run_again(self) -> None:
        memory = _memory()
        story = _obj("Starwood REIT sells $1 billion stake in apartments")
        memory.mark_published(story, "starwood-reit-sells-1b-stake")

        again = _obj("Starwood REIT sells $1 billion stake in apartments")
        verdict = memory.assess(again)
        self.assertEqual(verdict.state, NoveltyState.ALREADY_PUBLISHED)
        self.assertLessEqual(verdict.score, 2)
        self.assertIn("starwood", verdict.reason)

    def test_seeing_the_same_story_repeatedly_without_change_is_a_duplicate(self) -> None:
        memory = _memory()
        story = _obj("Segro accepts $18.8B takeover approach")
        memory.observe([story])
        memory.observe([story])
        verdict = memory.assess(_obj("Segro accepts $18.8B takeover approach"))
        self.assertEqual(verdict.state, NoveltyState.DUPLICATE)
        self.assertLessEqual(verdict.score, 2)

    def test_seen_once_with_nothing_new_is_a_minor_follow_up(self) -> None:
        memory = _memory()
        memory.observe([_obj("Segro accepts $18.8B takeover approach")])
        verdict = memory.assess(_obj("Segro accepts $18.8B takeover approach"))
        self.assertEqual(verdict.state, NoveltyState.MINOR_FOLLOW_UP)


class RealDevelopments(unittest.TestCase):
    """A story that genuinely moves on is news again."""

    def test_a_changed_figure_makes_it_a_new_stage(self) -> None:
        memory = _memory()
        first = _obj("Griffin and Vornado seek $2.5 billion loan for Park Avenue")
        memory.mark_published(first, "griffin-vornado-loan")

        verdict = memory.assess(
            _obj("Griffin and Vornado near record $3.3 billion loan for Park Avenue")
        )
        self.assertEqual(verdict.state, NoveltyState.NEW_STAGE)
        self.assertTrue(verdict.changes)
        self.assertIn("figure moved", verdict.changes[0])

    def test_a_status_change_counts_as_movement(self) -> None:
        memory = _memory()
        memory.observe([_obj("Blackstone proposes $450 million Phoenix portfolio purchase")])
        verdict = memory.assess(_obj("Blackstone closed $450 million Phoenix portfolio purchase"))
        self.assertIn(verdict.state, (NoveltyState.MATERIAL_UPDATE, NoveltyState.NEW_STAGE))
        self.assertTrue(any("status" in c for c in verdict.changes))

    def test_a_newly_disclosed_amount_is_material(self) -> None:
        memory = _memory()
        memory.observe([_obj("Henderson Park acquires San Diego shopping centre")])
        verdict = memory.assess(
            _obj("Henderson Park acquires San Diego shopping centre for $120 million")
        )
        self.assertEqual(verdict.state, NoveltyState.MATERIAL_UPDATE)
        self.assertTrue(any("disclosed" in c for c in verdict.changes))

    def test_an_old_theme_returns_as_news_after_the_lookback(self) -> None:
        memory = EditorialMemory(Path(tempfile.mkdtemp()) / "m.json", lookback_days=7)
        stale = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        memory.records["k"] = MemoryRecord(
            event_key="k", title="CMBS distress hits a new high",
            primary_sector="commercial_real_estate", last_seen=stale, times_seen=3,
        )
        verdict = memory.assess(_obj("CMBS distress hits a new high"))
        self.assertEqual(verdict.state, NoveltyState.NEW,
                         "a recurring theme is legitimately news again later")


class AppliesToTheSlate(unittest.TestCase):
    def test_novelty_lands_on_the_objects_and_stops_being_constant(self) -> None:
        memory = _memory()
        published = _obj("Starwood REIT sells $1 billion stake in apartments")
        memory.mark_published(published, "starwood")

        batch = [
            _obj("Starwood REIT sells $1 billion stake in apartments"),
            _obj("Prologis buys Dallas logistics park for $310 million"),
            _obj("KKR closes $8.5 billion buyout fund", sector="private_equity"),
        ]
        tally = memory.apply(batch)
        scores = {o.novelty_score for o in batch}
        self.assertGreater(len(scores), 1, "novelty must vary across a real batch")
        self.assertEqual(batch[0].novelty_state, NoveltyState.ALREADY_PUBLISHED)
        self.assertIn(NoveltyState.NEW, tally)

    def test_a_prior_slug_is_carried_onto_the_object(self) -> None:
        memory = _memory()
        memory.mark_published(_obj("Segro accepts $18.8B takeover"), "segro-takeover")
        batch = [_obj("Segro accepts $18.8B takeover")]
        memory.apply(batch)
        self.assertEqual(batch[0].prior_published_slugs, ["segro-takeover"])


class Persistence(unittest.TestCase):
    def test_memory_survives_a_restart(self) -> None:
        path = Path(tempfile.mkdtemp()) / "memory.json"
        first = EditorialMemory(path)
        first.mark_published(_obj("Segro accepts $18.8B takeover"), "segro")
        first.save()

        second = EditorialMemory(path)
        verdict = second.assess(_obj("Segro accepts $18.8B takeover"))
        self.assertEqual(verdict.state, NoveltyState.ALREADY_PUBLISHED)

    def test_a_corrupt_file_does_not_stop_a_run(self) -> None:
        path = Path(tempfile.mkdtemp()) / "memory.json"
        path.write_text("{ broken", encoding="utf-8")
        memory = EditorialMemory(path)
        self.assertEqual(memory.records, {})
        memory.observe([_obj("Something happened for $10 million")])
        memory.save()  # must not raise

    def test_the_published_archive_seeds_day_one(self) -> None:
        manifest = Path(tempfile.mkdtemp()) / "insights.json"
        manifest.write_text(json.dumps([
            {"title": "Starwood REIT sells $1 billion stake in apartments",
             "slug": "starwood", "date": "2026-08-01", "category": "Capital Markets"},
            {"title": "Prologis buys Dallas logistics park", "slug": "prologis",
             "date": "2026-08-02", "category": "Deal Intelligence"},
        ]), encoding="utf-8")

        memory = _memory()
        self.assertEqual(memory.seed_from_manifest(manifest), 2)
        verdict = memory.assess(_obj("Starwood REIT sells $1 billion stake in apartments"))
        self.assertEqual(verdict.state, NoveltyState.ALREADY_PUBLISHED,
                         "articles already on the site must count as covered")

    def test_the_report_describes_the_store(self) -> None:
        memory = _memory()
        memory.observe([_obj("A deal for $10 million")])
        memory.mark_published(_obj("Another deal for $20 million"), "another")
        report = memory.report()
        self.assertEqual(report["published"], 1)
        self.assertGreaterEqual(report["events_remembered"], 2)


if __name__ == "__main__":
    unittest.main()
