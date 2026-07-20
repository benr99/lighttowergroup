#!/usr/bin/env python3
"""Run the scheduled publisher from an isolated, self-updating Git worktree."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SITE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SITE_ROOT / "scripts"
STATUS_FILE = SITE_ROOT / "tmp" / "agent_status.json"
AGENT_ARGS = ("--selection-mode", "bucketed-volume", "--no-limit")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_status(state: str, stage: str, **extra: Any) -> None:
    """Write operational metadata only; never include command output or secrets."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "updated_at": now(),
        "state": state,
        "stage": stage,
        "runtime_root": str(SITE_ROOT),
        "agent_args": list(AGENT_ARGS),
        **extra,
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=SITE_ROOT, check=check, capture_output=True, text=True,
    )


def git_text(*args: str) -> str:
    return git(*args).stdout.strip()


def sync_action(head: str, remote_main: str, *, head_contains_remote: bool, remote_contains_head: bool) -> str:
    """Return the only safe reconciliation action for a clean runtime worktree."""
    if head == remote_main:
        return "current"
    if head_contains_remote:
        return "recover_push"
    if remote_contains_head:
        return "fast_forward"
    return "diverged"


def preflight() -> dict[str, str]:
    """Require a clean, non-diverged runtime and recover a prior unpushed run."""
    if git_text("status", "--porcelain"):
        raise RuntimeError("runtime worktree is not clean; refusing to mix scheduled output with unknown changes")

    git("fetch", "origin", "main")
    head = git_text("rev-parse", "HEAD")
    remote_main = git_text("rev-parse", "origin/main")
    action = sync_action(
        head,
        remote_main,
        head_contains_remote=git("merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode == 0,
        remote_contains_head=git("merge-base", "--is-ancestor", "HEAD", "origin/main", check=False).returncode == 0,
    )
    if action == "recover_push":
        git("push", "origin", "HEAD:refs/heads/main")
        git("fetch", "origin", "main")
    elif action == "fast_forward":
        git("merge", "--ff-only", "origin/main")
    elif action == "diverged":
        raise RuntimeError("runtime and origin/main diverged; manual review is required before publishing")

    head = git_text("rev-parse", "HEAD")
    remote_main = git_text("rev-parse", "origin/main")
    if head != remote_main:
        raise RuntimeError("runtime HEAD does not match origin/main after preflight")
    return {"head": head, "remote_main": remote_main, "sync_action": action}


def latest_agent_summary() -> dict[str, Any]:
    log_path = SCRIPT_DIR / "agent_log.json"
    try:
        records = json.loads(log_path.read_text(encoding="utf-8"))
        record = records[0] if isinstance(records, list) and records else {}
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        key: record[key]
        for key in ("status", "articles_count", "elapsed_seconds", "candidate_count", "decision_counts", "git")
        if key in record
    }


def main() -> int:
    write_status("running", "preflight")
    try:
        sync = preflight()
        write_status("running", "editorial_agent", **sync)
        completed = subprocess.run(
            [sys.executable, "daily_news_agent.py", *AGENT_ARGS], cwd=SCRIPT_DIR, check=False,
        )
        summary = latest_agent_summary()
        if completed.returncode:
            write_status("failed", "editorial_agent", exit_code=completed.returncode, **sync, agent_summary=summary)
            return completed.returncode
        write_status("success", "complete", exit_code=0, **sync, agent_summary=summary)
        return 0
    except Exception as exc:
        write_status("failed", "preflight", error_type=type(exc).__name__)
        print(f"[ERROR] Agent runtime preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
