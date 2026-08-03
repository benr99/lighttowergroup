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
from datetime import datetime, timezone
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


def _parse_manifest_date(date_str: str) -> datetime:
    """Parse either manifest date format.

    Mirrors daily_news_agent._parse_manifest_date. Legacy agent runs wrote
    "April 29, 2026"; current runs write "2026-04-29". Unparseable dates sort
    last so a bad record can never displace real content at the top.
    """
    for fmt in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.min.replace(tzinfo=timezone.utc)


def _unlisted_published_slugs() -> list[str]:
    """Articles that reached sitemap.xml and feed.xml but never entered insights.json.

    Those two indexes are written at publication time, so a slug present in both
    is published by every measure except the one that drives the public listing
    page. Anything missing from them is an unpublished draft and is left alone.
    """
    records = json.loads((SITE_ROOT / "insights.json").read_text(encoding="utf-8"))
    listed = {str(record.get("slug", "")) for record in records}
    sitemap = (SITE_ROOT / "sitemap.xml").read_text(encoding="utf-8")
    feed = (SITE_ROOT / "feed.xml").read_text(encoding="utf-8")
    unlisted = []
    for path in sorted((SITE_ROOT / "insights").glob("*.html")):
        slug = path.stem
        if slug in listed:
            continue
        url = f"https://lighttowergroup.co/insights/{slug}.html"
        if url in sitemap and url in feed:
            unlisted.append(slug)
    return unlisted


def _manifest_entry_from_article(slug: str) -> dict:
    """Rebuild a manifest record from the article's published JSON-LD."""
    from edition_manager import calculate_read_time

    markup = (SITE_ROOT / "insights" / f"{slug}.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', markup, re.S
    )
    payload = None
    for block in blocks:
        try:
            candidate = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("headline"):
            payload = candidate
            break
    if payload is None:
        raise SystemExit(f"No article JSON-LD found for {slug}; refusing to guess metadata")

    body = re.search(r"<article[^>]*>(.*?)</article>", markup, re.S)
    keywords = payload.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",") if part.strip()]
    return {
        "title": payload["headline"],
        "slug": slug,
        "date": str(payload.get("datePublished", ""))[:10],
        "readTime": calculate_read_time(body.group(1) if body else markup),
        "category": payload.get("articleSection") or "Capital Markets",
        "excerpt": payload.get("description", ""),
        "url": f"/insights/{slug}.html",
        "tags": list(keywords),
    }


def reconcile_insights_manifest(apply_changes: bool) -> list[str]:
    """Relist published articles that are missing from insights.json.

    Publication writes the article page, sitemap.xml and feed.xml, but a failure
    between those steps and the manifest write leaves an article that search
    engines and RSS readers can reach while the on-site listing cannot.
    """
    unlisted = _unlisted_published_slugs()
    if not unlisted:
        print("insights.json already lists every published article")
        return []

    manifest_path = SITE_ROOT / "insights.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    for slug in unlisted:
        entry = _manifest_entry_from_article(slug)
        print(f"  {'relisting' if apply_changes else 'would relist'} {entry['date']}  {slug}")
        # Insert positionally rather than re-sorting: the manifest mixes ISO dates
        # with the legacy "April 29, 2026" format, so a plain sort would reshuffle
        # the 879 existing records and put the legacy entries on top.
        when = _parse_manifest_date(entry["date"])
        for index, existing in enumerate(records):
            if _parse_manifest_date(str(existing.get("date", ""))) <= when:
                records.insert(index, entry)
                break
        else:
            records.append(entry)

    if apply_changes:
        manifest_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Relisted {len(unlisted)} article(s); {len(records)} total entries")
    else:
        print(f"{len(unlisted)} article(s) would be relisted; re-run with --apply")
    return unlisted


def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain Light Tower public content indexes")
    subparsers = parser.add_subparsers(dest="command", required=True)
    dedupe = subparsers.add_parser("dedupe-insight", help="Remove a duplicate from public indexes")
    dedupe.add_argument("old_slug")
    dedupe.add_argument("canonical_slug")
    subparsers.add_parser("normalise-insights", help="Backfill stable URLs in insights.json")
    reconcile = subparsers.add_parser(
        "reconcile-insights",
        help="Relist articles that are in sitemap.xml and feed.xml but missing from insights.json",
    )
    reconcile.add_argument("--apply", action="store_true", help="Write the changes")
    args = parser.parse_args()
    if args.command == "dedupe-insight":
        dedupe_insight(args.old_slug, args.canonical_slug)
    elif args.command == "normalise-insights":
        normalise_insights_manifest()
    elif args.command == "reconcile-insights":
        reconcile_insights_manifest(apply_changes=args.apply)


if __name__ == "__main__":
    main()
