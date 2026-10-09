"""The rehearsal script runs a preview day outside the repository and never publishes."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rehearsal  # noqa: E402


class RehearsalTests(unittest.TestCase):
    def _main(self, *argv: str, env: dict | None = None):
        calls = {}

        def fake_run(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(errors=[]), None

        import insights_v3
        with (mock.patch.object(sys, "argv", ["rehearsal.py", *argv]),
              mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test"} if env is None else env, clear=False),
              mock.patch.object(insights_v3, "run", side_effect=fake_run)):
            code = rehearsal.main()
        return code, calls

    def test_preview_with_voice_in_a_dated_folder_outside_the_repo(self):
        root = Path(tempfile.mkdtemp())
        code, calls = self._main("--root", str(root), "--article-limit", "8")
        self.assertEqual(code, 0)
        self.assertEqual(calls["mode"], "preview")
        self.assertEqual(calls["pipeline"], "v4")
        self.assertTrue(calls["voice"])
        self.assertEqual(calls["article_limit"], 8)
        self.assertEqual(calls["state_dir"].parent, root)

    def test_refuses_to_write_inside_the_repository(self):
        code, calls = self._main("--root", str(ROOT / "tmp-rehearsal-test"))
        self.assertEqual(code, 2)
        self.assertFalse(calls)
        import shutil
        shutil.rmtree(ROOT / "tmp-rehearsal-test", ignore_errors=True)

    def test_needs_the_deepseek_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            code, calls = self._main("--root", tempfile.mkdtemp(), env={})
        self.assertEqual(code, 2)
        self.assertFalse(calls)


if __name__ == "__main__":
    unittest.main()
