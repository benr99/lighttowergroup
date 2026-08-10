"""Live release verification and guarded rollback behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rollback_release  # noqa: E402
import verify_deployment  # noqa: E402


class _Response:
    def __init__(self, *, payload=None, text="", status=200):
        self.payload = payload
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self):
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, *_args, **_kwargs):
        return self.responses.pop(0)


def _completed(stdout=""):
    return subprocess.CompletedProcess(["git"], 0, stdout=stdout, stderr="")


class DeploymentVerification(unittest.TestCase):
    def test_matching_edition_and_article_are_verified(self) -> None:
        edition = {
            "edition_date": "2026-08-10",
            "generated_at": "2026-08-10T12:00:00+00:00",
            "status": "ready",
            "flagship": None,
            "briefs": [{"slug": "apollo-closes-fund", "title": "Apollo Closes Fund"}],
            "culture_signal": None,
            "data_note": None,
        }
        path = Path(tempfile.mkdtemp()) / "latest-edition.json"
        path.write_text(json.dumps(edition), encoding="utf-8")
        session = _Session([
            _Response(payload=edition),
            _Response(text="<html><h1>Apollo Closes Fund</h1></html>"),
        ])
        with patch.object(verify_deployment, "LATEST_EDITION", path):
            ok, message = verify_deployment.verify(
                base_url="https://example.com",
                release_sha="a" * 40,
                timeout_seconds=0,
                session=session,
            )
        self.assertTrue(ok, message)

    def test_stale_live_edition_fails_closed(self) -> None:
        expected = {
            "edition_date": "2026-08-10", "generated_at": "new", "status": "ready",
            "flagship": None, "briefs": [], "culture_signal": None, "data_note": None,
        }
        stale = {**expected, "generated_at": "old"}
        path = Path(tempfile.mkdtemp()) / "latest-edition.json"
        path.write_text(json.dumps(expected), encoding="utf-8")
        with patch.object(verify_deployment, "LATEST_EDITION", path):
            ok, message = verify_deployment.verify(
                base_url="https://example.com",
                release_sha="b" * 40,
                timeout_seconds=0,
                session=_Session([_Response(payload=stale)]),
            )
        self.assertFalse(ok)
        self.assertIn("generated_at", message)


class GuardedRollback(unittest.TestCase):
    def test_remote_movement_prevents_rollback(self) -> None:
        release = "a" * 40
        with patch.object(
            rollback_release,
            "git",
            side_effect=[_completed(release + "\n"), _completed("b" * 40 + "\trefs/heads/main\n")],
        ) as git:
            with self.assertRaisesRegex(RuntimeError, "origin/main moved"):
                rollback_release.rollback(release)
        self.assertEqual(git.call_count, 2)

    def test_release_is_reverted_and_remote_sha_is_verified(self) -> None:
        release, revert = "a" * 40, "c" * 40
        responses = [
            _completed(release + "\n"),
            _completed(release + "\trefs/heads/main\n"),
            _completed(),
            _completed(),
            _completed(revert + "\n"),
            _completed(revert + "\trefs/heads/main\n"),
        ]
        with patch.object(rollback_release, "git", side_effect=responses) as git:
            self.assertEqual(rollback_release.rollback(release), revert)
        self.assertEqual(git.call_count, 6)
        self.assertEqual(git.call_args_list[2].args[:2], ("revert", "--no-edit"))


if __name__ == "__main__":
    unittest.main()
