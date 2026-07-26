#!/usr/bin/env python3
"""Safely publish only files declared by the editorial generation run."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
MANIFEST = SITE_ROOT / ".editorial-state" / "generated-files.json"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=SITE_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def load_files() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, list) or not files:
        raise RuntimeError("generated-files manifest is empty")
    safe: list[str] = []
    root = SITE_ROOT.resolve()
    for value in files + [".editorial-state/generated-files.json"]:
        relative = Path(str(value))
        if relative.is_absolute() or ".." in relative.parts or relative.parts[0] == ".git":
            raise RuntimeError(f"unsafe generated path: {value}")
        resolved = (SITE_ROOT / relative).resolve()
        resolved.relative_to(root)
        if not resolved.exists():
            raise RuntimeError(f"declared generated file is missing: {value}")
        normalized = relative.as_posix()
        if normalized not in safe:
            safe.append(normalized)
    return safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", default="main")
    parser.add_argument("--message", default="Publish curated Light Tower Insights edition")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    files = load_files()
    if args.dry_run:
        print("\n".join(files))
        return 0

    git("add", "--", *files)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("No generated changes to publish.")
        return 0
    git(
        "commit",
        "-m",
        f"{args.message}\n\nGenerated-By: DeepSeek editorial pipeline <automation@lighttowergroup.co>",
    )

    # If main moved during a long editorial run, rebase the generated commit.
    # Any content conflict stops publication rather than overwriting newer work.
    remote_exists = bool(git("ls-remote", "--heads", "origin", f"refs/heads/{args.branch}").stdout.strip())
    if remote_exists:
        git("fetch", "origin", args.branch)
        remote_ref = f"origin/{args.branch}"
        if git("merge-base", "--is-ancestor", remote_ref, "HEAD", check=False).returncode != 0:
            rebase = git("rebase", remote_ref, check=False)
            if rebase.returncode:
                git("rebase", "--abort", check=False)
                raise RuntimeError(
                    "Remote branch changed and generated artifacts conflict; publication was safely stopped."
                )

    git("push", "origin", f"HEAD:refs/heads/{args.branch}")
    local_sha = git("rev-parse", "HEAD").stdout.strip()
    remote_sha = git("ls-remote", "origin", f"refs/heads/{args.branch}").stdout.split()[0]
    if local_sha != remote_sha:
        raise RuntimeError("Remote branch does not match the generated publication commit")
    print(f"Published and verified {local_sha}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
