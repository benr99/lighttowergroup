#!/usr/bin/env python3
"""Validate generated editorial artifacts before they can reach main."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_count = 0
        self.h1_count = 0
        self.canonicals: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "title":
            self.title_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "link" and data.get("rel") == "canonical":
            self.canonicals.append(str(data.get("href", "")))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_article(path: Path, record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing article file: {path.relative_to(SITE_ROOT)}"]
    text = path.read_text(encoding="utf-8")
    parser = _Parser()
    try:
        parser.feed(text)
    except Exception as exc:
        errors.append(f"{path.name}: invalid HTML parser input ({type(exc).__name__})")
    if parser.h1_count != 1:
        errors.append(f"{path.name}: expected exactly one h1, found {parser.h1_count}")
    if not parser.canonicals:
        errors.append(f"{path.name}: canonical URL is missing")
    if str(record.get("title", "")) not in text:
        errors.append(f"{path.name}: manifest title is not present")
    if "sources-block" not in text:
        errors.append(f"{path.name}: sources block is missing")
    if re.search(r"(?:Ã.|â€|Â·)", text):
        errors.append(f"{path.name}: possible mojibake")
    return errors


def validate_repository(*, latest_only: bool = True) -> list[str]:
    errors: list[str] = []
    manifest_path = SITE_ROOT / "insights.json"
    latest_path = SITE_ROOT / "latest-edition.json"
    try:
        manifest = _load_json(manifest_path)
    except Exception as exc:
        return [f"insights.json is invalid: {type(exc).__name__}"]
    if not isinstance(manifest, list):
        errors.append("insights.json must contain a list")
        manifest = []
    slugs = [str(item.get("slug", "")) for item in manifest if isinstance(item, dict)]
    if len(slugs) != len(set(slugs)):
        errors.append("insights.json contains duplicate slugs")
    records = manifest[:10] if latest_only else manifest
    for record in records:
        slug = re.sub(r"[^a-z0-9-]", "", str(record.get("slug", "")).lower())
        errors.extend(_validate_article(SITE_ROOT / "insights" / f"{slug}.html", record))

    for xml_name in ("feed.xml", "sitemap.xml"):
        try:
            ET.parse(SITE_ROOT / xml_name)
        except Exception as exc:
            errors.append(f"{xml_name} is invalid: {type(exc).__name__}")

    if latest_path.exists():
        try:
            edition = _load_json(latest_path)
        except Exception as exc:
            errors.append(f"latest-edition.json is invalid: {type(exc).__name__}")
            edition = {}
        if edition and edition.get("status") not in {"ready", "no_publishable_story"}:
            errors.append("latest-edition.json has an invalid status")
        edition_articles = []
        if isinstance(edition, dict):
            edition_articles.extend(edition.get("briefs") or [])
            if edition.get("flagship"):
                edition_articles.append(edition["flagship"])
            if edition.get("culture_signal"):
                edition_articles.append(edition["culture_signal"])
            if edition.get("data_note"):
                edition_articles.append(edition["data_note"])
        for article in edition_articles:
            if not (SITE_ROOT / str(article.get("url", "")).lstrip("/")).exists():
                errors.append(f"edition references missing article: {article.get('url')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Validate every manifest article")
    args = parser.parse_args()
    errors = validate_repository(latest_only=not args.all)
    if errors:
        print("Publication validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Publication artifacts validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
