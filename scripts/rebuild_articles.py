#!/usr/bin/env python3
"""Rebuild all insight article HTML pages with the current unified template.

Reads article metadata from insights.json, extracts article body content
from existing HTML files, and regenerates pages with the current template.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
BACKUP_DIR = SITE_ROOT / "insights" / ".backup"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def extract_body_only(html: str) -> str:
    """Extract raw body_html content, stripping template chrome."""
    # Try <div class="article-body"> (Template B style)
    m = re.search(
        r'<div[^>]*class="[^"]*article-body[^"]*"[^>]*>\s*(.*?)</div>\s*<div[^>]*class="[^"]*article-tags',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    # Try <article class="post-body"> (Template A style)
    m = re.search(
        r'<article[^>]*class="[^"]*post-body[^"]*"[^>]*>(.*?)(?:<hr[^>]*>\s*<p[^>]*>|</article>)',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        inner = m.group(1).strip()
        inner = re.sub(r'<nav[^>]*>.*?</nav>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        inner = re.sub(r'<header[^>]*>.*?</header>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        return inner

    # Try content inside <article> tag generally
    m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
    if m:
        inner = m.group(1).strip()
        inner = re.sub(
            r'<div[^>]*class="[^"]*(?:share-bar|article-data-note|article-cta-block|article-tags|article-sources|sources-block|related-research)[^"]*"[^>]*>.*?</div>',
            '', inner, flags=re.DOTALL | re.IGNORECASE,
        )
        inner = re.sub(r'<aside[^>]*>.*?</aside>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        inner = re.sub(r'<script[^>]*>.*?</script>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        return inner.strip()

    return ""


def normalize_article(entry: dict, body_html: str) -> dict:
    """Ensure article dict has all fields required by render_html."""
    date_str = entry.get("date", "")
    date_iso = ""
    if date_str:
        for fmt in ("%Y-%m-%d", "%B %d, %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                date_iso = dt.replace(tzinfo=timezone.utc).isoformat()
                break
            except ValueError:
                continue

    return {
        **entry,
        "body_html": body_html,
        "meta_description": entry.get("meta_description") or entry.get("excerpt", entry.get("title", "")),
        "date_iso": date_iso or datetime.now(timezone.utc).isoformat(),
        "subtitle": entry.get("subtitle", ""),
        "read_time": entry.get("readTime") or entry.get("read_time", 5),
        "excerpt": entry.get("excerpt", ""),
        "social_image": entry.get("social_image", ""),
        "source_url": entry.get("source_url", ""),
        "source_name": entry.get("source_name", ""),
        "sources": entry.get("sources", []),
        "tags": entry.get("tags", []),
        "editorial_format": entry.get("editorial_format", "brief"),
        "franchise": entry.get("franchise", {"name": "Light Tower", "promise": ""}),
    }


def main():
    import sys

    manifest = load_json(INSIGHTS_JSON)
    if not manifest:
        print("No insights.json found.")
        return

    sys.path.insert(0, str(SCRIPT_DIR))
    from daily_news_agent import render_html

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rebuilt = 0
    skipped = 0
    errors = 0

    for entry in manifest:
        slug = entry.get("slug", "")
        if not slug:
            skipped += 1
            continue

        html_path = INSIGHTS_DIR / f"{slug}.html"
        if not html_path.exists():
            skipped += 1
            continue

        try:
            html = html_path.read_text(encoding="utf-8")
            body = extract_body_only(html)
            if not body.strip():
                body = entry.get("body_html", "")
                if not body.strip():
                    skipped += 1
                    continue

            article_data = normalize_article(entry, body)
            new_html = render_html(article_data)

            if "<!DOCTYPE html>" not in new_html or "</html>" not in new_html:
                print(f"  WARN: Invalid template for {slug}, skipping")
                skipped += 1
                continue

            # Backup original (overwrite if backup already exists)
            backup_path = BACKUP_DIR / f"{slug}.html"
            if backup_path.exists():
                backup_path.unlink()
            html_path.rename(backup_path)

            # Write rebuilt
            html_path.write_text(new_html, encoding="utf-8")
            rebuilt += 1
            if rebuilt % 50 == 0:
                print(f"  Rebuilt {rebuilt}...")
        except Exception as e:
            print(f"  ERROR: {slug}: {e}")
            errors += 1

    print(f"\nRebuilt: {rebuilt} | Skipped: {skipped} | Errors: {errors} | Total: {len(manifest)}")
    print(f"Backups saved to: {BACKUP_DIR.relative_to(SITE_ROOT)}")


if __name__ == "__main__":
    main()
