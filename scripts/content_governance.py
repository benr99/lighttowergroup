"""Shared, deterministic safeguards for Light Tower editorial automation.

This module deliberately does not call an LLM. It is the independent control
layer around model output: source material is treated as untrusted, repetitive
stories are caught before publication, and generic fallback writing cannot pass
as finished editorial work.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from editorial_voice import editorial_quality_issues


PROMPT_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?"
    r"|disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|forget\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|system\s+prompt|developer\s+message|reveal\s+(?:your|the)\s+instructions?"
    r"|act\s+as\s+(?:a\s+)?(?:different|new)\s+(?:assistant|system))",
    re.IGNORECASE,
)

GENERIC_EDITORIAL_RE = re.compile(
    r"(?:the headline is therefore a doorway|buildings are where private capital|"
    r"the capital question is simple and difficult|the built world is not merely the background)",
    re.IGNORECASE,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", parser.text()).strip()


def sanitize_untrusted_source(value: str) -> str:
    """Remove instruction-like text from retrieved articles before prompting."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return PROMPT_INJECTION_RE.sub("[editorial instruction removed]", text)


def normalise_title(value: str) -> str:
    value = re.sub(r"[^a-z0-9\s]", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", value).strip()


def _token_similarity(left: str, right: str) -> float:
    a = set(normalise_title(left).split())
    b = set(normalise_title(right).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def near_duplicate_matches(
    title: str,
    records: Iterable[dict[str, Any]],
    *,
    threshold: float = 0.86,
) -> list[str]:
    """Return human-readable duplicate warnings for editorial review."""
    title_key = normalise_title(title)
    matches: list[str] = []
    for record in records:
        existing = str(record.get("title", ""))
        existing_key = normalise_title(existing)
        if not existing_key:
            continue
        sequence = SequenceMatcher(None, title_key, existing_key).ratio()
        token = _token_similarity(title, existing)
        if title_key == existing_key or sequence >= threshold or token >= 0.82:
            slug = record.get("slug", "untitled")
            matches.append(f"near-duplicate of {slug} ({max(sequence, token):.0%} title similarity)")
    return matches


def load_json_records(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return [payload] if isinstance(payload, dict) else []


def load_idea_records(site_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in (site_root / "data" / "ideas" / "published").glob("*.json"):
        records.extend(load_json_records(path))
    return records


def load_insight_records(site_root: Path) -> list[dict[str, Any]]:
    return load_json_records(site_root / "insights.json")


def independent_quality_issues(article: dict[str, Any], *, require_sections: bool = True) -> list[str]:
    """Quality checks that do not trust a score supplied by the writer model."""
    errors: list[str] = []
    body_html = str(article.get("body_html", ""))
    text = html_to_text(body_html)
    word_count = len(text.split())
    source_notes = str(article.get("source_notes", ""))
    generation_mode = str(article.get("generation_mode", ""))

    if generation_mode.endswith("fallback") or "deterministic fallback" in source_notes.lower():
        errors.append("fallback writing requires editorial review")
    minimum_words = 800 if require_sections else 650
    if word_count < minimum_words:
        errors.append(f"independent quality gate: article is below {minimum_words} words")
    if require_sections and len(re.findall(r"<h2\b", body_html, re.IGNORECASE)) < 2:
        errors.append("independent quality gate: article needs at least two substantive sections")
    if require_sections and GENERIC_EDITORIAL_RE.search(text):
        errors.append("independent quality gate: generic boilerplate language detected")
    for issue in editorial_quality_issues(text, min_characters=1):
        if issue != "draft is below 1 characters":
            errors.append(f"independent quality gate: {issue}")

    sources = article.get("sources") or []
    if not isinstance(sources, list) or not sources:
        errors.append("independent quality gate: no attributable source")
    else:
        urls = [str(item.get("url", "")) for item in sources if isinstance(item, dict)]
        if not any(url.startswith(("https://", "http://")) for url in urls):
            errors.append("independent quality gate: source URL is invalid")
        if any("example.com" in url.lower() for url in urls):
            errors.append("independent quality gate: fixture source cannot be published")

    paragraphs = [re.sub(r"\s+", " ", item).strip().lower() for item in re.findall(r"<p[^>]*>(.*?)</p>", body_html, re.I | re.S)]
    paragraphs = [re.sub(r"<[^>]+>", "", item) for item in paragraphs]
    if len(paragraphs) >= 4 and len(set(paragraphs)) / len(paragraphs) < 0.9:
        errors.append("independent quality gate: repeated paragraph structure detected")
    return errors
