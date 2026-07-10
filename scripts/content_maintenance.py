"""Safe, repeatable maintenance for public editorial indexes.

Usage:
  python scripts/content_maintenance.py dedupe-insight OLD_SLUG CANONICAL_SLUG

The old article file is deliberately retained. Pair this command with a Netlify
301 redirect so existing links continue to work while public discovery indexes
only the canonical analysis.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]


def dedupe_insight(old_slug: str, canonical_slug: str) -> None:
    manifest_path = SITE_ROOT / "insights.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    retained = [record for record in records if record.get("slug") != old_slug]
    if len(retained) == len(records):
        raise SystemExit(f"No insight found for slug: {old_slug}")
    if not any(record.get("slug") == canonical_slug for record in retained):
        raise SystemExit(f"Canonical insight not found: {canonical_slug}")
    manifest_path.write_text(json.dumps(retained, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    old_url = f"https://lighttowergroup.co/insights/{old_slug}.html"
    for filename, item_pattern in (
        ("sitemap.xml", rf"\s*<url>\s*<loc>{re.escape(old_url)}</loc>[\s\S]*?</url>"),
        ("feed.xml", rf"\s*<item>[\s\S]*?<link>{re.escape(old_url)}</link>[\s\S]*?</item>"),
    ):
        path = SITE_ROOT / filename
        content = path.read_text(encoding="utf-8")
        updated, count = re.subn(item_pattern, "", content, count=1)
        if count:
            path.write_text(updated, encoding="utf-8")
            print(f"Removed {old_slug} from {filename}")

    print(f"Retired duplicate {old_slug}; canonical record is {canonical_slug}")


def normalise_insights_manifest() -> None:
    """Backfill stable public URLs so every card has an explicit contract."""
    manifest_path = SITE_ROOT / "insights.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    updated = 0
    for record in records:
        slug = str(record.get("slug", "")).strip()
        expected_url = f"/insights/{slug}.html"
        if slug and record.get("url") != expected_url:
            record["url"] = expected_url
            updated += 1
    manifest_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Normalized {updated} Insight URL record(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain Light Tower public content indexes")
    subparsers = parser.add_subparsers(dest="command", required=True)
    dedupe = subparsers.add_parser("dedupe-insight", help="Remove a duplicate from public indexes")
    dedupe.add_argument("old_slug")
    dedupe.add_argument("canonical_slug")
    subparsers.add_parser("normalise-insights", help="Backfill stable URLs in insights.json")
    args = parser.parse_args()
    if args.command == "dedupe-insight":
        dedupe_insight(args.old_slug, args.canonical_slug)
    elif args.command == "normalise-insights":
        normalise_insights_manifest()


if __name__ == "__main__":
    main()
