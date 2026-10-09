"""Publishing no longer depends on the 2,872-line legacy agent (plan item 3.1, flag F1)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _loaded_after(statement: str) -> set[str]:
    code = f"import sys; {statement}; print(','.join(sorted(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=SCRIPTS, capture_output=True, text=True, check=True)
    return set(out.stdout.strip().split(","))


class RendererIsIndependent(unittest.TestCase):
    def test_publishers_do_not_load_the_legacy_agent(self):
        for statement in (
            "import site_renderer",
            "import v3_publish",
            "import weekly_wrap",
        ):
            with self.subTest(statement=statement):
                loaded = _loaded_after(statement)
                self.assertNotIn("daily_news_agent", loaded)
                self.assertNotIn("linkedin_essay_agent", loaded)
                self.assertNotIn("feedparser", loaded)

    def test_legacy_agent_reexports_the_same_functions(self):
        sys.path.insert(0, str(SCRIPTS))
        import daily_news_agent
        import site_renderer
        for name in ("render_html", "update_manifest", "update_feed_xml", "update_sitemap_xml", "sanitize_html"):
            self.assertIs(getattr(daily_news_agent, name), getattr(site_renderer, name))



class SectorReachesTheFilters(unittest.TestCase):
    """F14: four sector buttons matched nothing because the manifest had no sector."""

    def test_manifest_entry_carries_the_sector(self):
        import json
        import tempfile
        from unittest import mock
        sys.path.insert(0, str(SCRIPTS))
        import site_renderer
        manifest = Path(tempfile.mkdtemp()) / "insights.json"
        manifest.write_text("[]", encoding="utf-8")
        article = {"title": "T", "slug": "t", "date_iso": "2026-10-09T11:00:00+00:00", "category": "Market Commentary",
                   "meta_description": "An excerpt.", "body_html": "<p>x</p>", "sector": "energy"}
        with mock.patch.object(site_renderer, "INSIGHTS_JSON", manifest):
            site_renderer.update_manifest(article)
            site_renderer.update_manifest({**article, "slug": "legacy", "sector": ""})
        entries = {e["slug"]: e for e in json.loads(manifest.read_text(encoding="utf-8"))}
        self.assertEqual(entries["t"]["sector"], "energy")
        self.assertNotIn("sector", entries["legacy"])

    def test_page_filters_on_sector_when_present(self):
        page = (ROOT / "insights.html").read_text(encoding="utf-8")
        self.assertIn("if (post.sector && filter !== 'weekly_wrap') return post.sector === filter;", page)
        for key in ("energy", "banking_credit", "fed_macro", "local_government"):
            self.assertIn(f'data-filter="{key}"', page)


if __name__ == "__main__":
    unittest.main()
