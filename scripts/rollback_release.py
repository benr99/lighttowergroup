#!/usr/bin/env python3
"""Revert one failed Insights release only if origin/main still points to it."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=SITE_ROOT, check=check, capture_output=True, text=True
    )


def rollback(expected_sha: str) -> str:
    expected_sha = expected_sha.strip()
    if not expected_sha:
        raise RuntimeError("expected release SHA is empty")
    local = git("rev-parse", "HEAD").stdout.strip()
    if local != expected_sha:
        raise RuntimeError(f"local HEAD moved; refusing rollback ({local} != {expected_sha})")
    remote_line = git("ls-remote", "origin", "refs/heads/main").stdout.strip()
    remote = remote_line.split()[0] if remote_line else ""
    if remote != expected_sha:
        raise RuntimeError(
            "origin/main moved after this release; refusing to revert somebody else's work"
        )
    git("revert", "--no-edit", expected_sha)
    git("push", "origin", "HEAD:refs/heads/main")
    reverted = git("rev-parse", "HEAD").stdout.strip()
    verified_line = git("ls-remote", "origin", "refs/heads/main").stdout.strip()
    verified = verified_line.split()[0] if verified_line else ""
    if verified != reverted:
        raise RuntimeError("rollback push could not be verified on origin/main")
    return reverted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    reverted = rollback(args.expected_sha)
    print(f"Rolled back failed release with verified revert commit {reverted}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
