#!/usr/bin/env python3
"""Dress rehearsal: run a full Insights day in preview and build the digest Ben reads.

Nothing is published and nothing is written into the repository. Each day gets its
own folder (default ``%USERPROFILE%\\ltg-rehearsal\\<date>``) holding the run report,
every draft, the evidence files, ``digest.html`` and ``health.txt``. Ben's voice is
on for flagships and analyses, because the point of the rehearsal is to read it.

    python scripts/rehearsal.py                       # the full day (70-story slate)
    python scripts/rehearsal.py --article-limit 8     # a short, cheap day
    python scripts/rehearsal.py --max-usd 3           # cap this day's model spend

Needs DEEPSEEK_API_KEY in the environment. DeepSeek is the only provider used.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

DEFAULT_ROOT = Path(os.environ.get("USERPROFILE") or Path.home()) / "ltg-rehearsal"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a full preview day and build the digest.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="folder that holds one subfolder per day")
    parser.add_argument("--article-limit", type=int, default=70, help="stories to write (production uses 70)")
    parser.add_argument("--max-usd", type=float, default=None, help="daily model spend cap for this rehearsal")
    parser.add_argument("--voice", choices=["on", "off"], default="on")
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set; nothing was run.")
        return 2
    os.environ["LTG_PROVIDERS"] = "deepseek"
    if args.max_usd is not None:
        os.environ["LTG_MAX_DAILY_USD"] = str(args.max_usd)

    day = Path(args.root) / datetime.now().strftime("%Y-%m-%d")
    day.mkdir(parents=True, exist_ok=True)
    repo = SCRIPTS.parent.resolve()
    if repo in day.resolve().parents:
        print(f"Refusing to write a rehearsal inside the repository: {day}")
        return 2

    from insights_v3 import run

    print(f"Rehearsal folder: {day}", flush=True)
    report, _ = run(
        pipeline="v4", mode="preview", state_dir=day, voice=args.voice == "on",
        daily_target=min(args.article_limit, 70), article_limit=args.article_limit,
    )
    digest = day / "digest.html"
    print(f"\nOpen the digest: {digest}" if digest.exists() else "\nThe digest was not built; see the run report.")
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
