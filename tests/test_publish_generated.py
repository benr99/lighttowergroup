from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_generated


class PublishGeneratedTests(unittest.TestCase):
    def test_manifest_allows_only_existing_repo_relative_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".editorial-state"
            state.mkdir()
            article = root / "insights" / "story.html"
            article.parent.mkdir()
            article.write_text("story", encoding="utf-8")
            manifest = state / "generated-files.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "files": ["insights/story.html"]}),
                encoding="utf-8",
            )
            with (
                patch.object(publish_generated, "SITE_ROOT", root),
                patch.object(publish_generated, "MANIFEST", manifest),
            ):
                files = publish_generated.load_files()
        self.assertEqual(
            files,
            ["insights/story.html", ".editorial-state/generated-files.json"],
        )

    def test_manifest_rejects_parent_directory_escape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".editorial-state"
            state.mkdir()
            manifest = state / "generated-files.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "files": ["../outside.txt"]}),
                encoding="utf-8",
            )
            with (
                patch.object(publish_generated, "SITE_ROOT", root),
                patch.object(publish_generated, "MANIFEST", manifest),
            ):
                with self.assertRaisesRegex(RuntimeError, "unsafe generated path"):
                    publish_generated.load_files()


if __name__ == "__main__":
    unittest.main()
