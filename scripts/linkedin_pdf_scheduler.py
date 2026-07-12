"""Post one explicitly queued Light Tower article PDF in a scheduled slot.

The daily news agent creates the queue. Completed slots are recorded so a retry
or duplicate trigger can never create a duplicate LinkedIn post.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from linkedin_pdf_post import post_article_pdf


SCRIPT_DIR = Path(__file__).resolve().parent
QUEUE_PATH = SCRIPT_DIR / "linkedin_pdf_queue.json"
STATE_PATH = SCRIPT_DIR / "linkedin_pdf_post_state.json"


def read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def run_slot(slot: int, publish: bool) -> int:
    queue = read_json(QUEUE_PATH, {})
    slugs = queue.get("slugs", [])
    if slot < 1 or slot > len(slugs):
        print(f"No prepared article for LinkedIn slot {slot}; nothing posted.")
        return 0

    queue_date = queue.get("date")
    today = datetime.now().astimezone().date().isoformat()
    if queue_date != today:
        print(f"Queue is for {queue_date or 'an unknown date'}, not today; nothing posted.")
        return 0

    state = read_json(STATE_PATH, {"posted": {}})
    key = f"{queue_date}:{slot}"
    if key in state.get("posted", {}):
        print(f"LinkedIn slot {slot} was already posted; nothing posted.")
        return 0

    slug = slugs[slot - 1]
    article = {"slug": slug, "title": slug.replace("-", " ").title()}
    result = post_article_pdf(article, dry_run=not publish)
    if not result.get("ok"):
        print(f"LinkedIn slot {slot} failed: {result.get('error', 'unknown error')}")
        return 1
    if publish:
        state.setdefault("posted", {})[key] = {
            "slug": slug,
            "post_id": result.get("post_id"),
            "posted_at": datetime.now().astimezone().isoformat(),
        }
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"LinkedIn slot {slot}: {'posted' if publish else 'validated'} {slug}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Post one queued LinkedIn PDF slot.")
    parser.add_argument("--slot", type=int, required=True, help="One-based queue slot (1-30).")
    parser.add_argument("--publish", action="store_true", help="Create a real post; otherwise dry-run.")
    args = parser.parse_args()
    return run_slot(args.slot, args.publish)


if __name__ == "__main__":
    sys.exit(main())
