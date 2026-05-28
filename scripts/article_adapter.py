"""
Transform Insight article HTML into the PDF carousel schema.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def clean_text(text: Any) -> str:
    text = unescape(str(text or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_pull_quote_from_html(html: str) -> str:
    match = re.search(r"<!-- PULL_QUOTE -->(.*?)<!-- /PULL_QUOTE -->", html or "", re.DOTALL)
    if match:
        return clean_text(match.group(1))

    analytical_verbs = [
        "indicates", "signals", "suggests", "means", "reveals", "shows",
        "demonstrates", "underscores", "reflects", "drives", "determines",
        "creates", "establishes",
    ]
    text = re.sub(r"<[^>]+>", " ", html or "")
    sentences = [clean_text(s) for s in re.split(r"(?<=[.!?])\s+", text) if clean_text(s)]
    for sentence in sentences:
        words = sentence.split()
        if 15 < len(words) < 38 and any(v in sentence.lower() for v in analytical_verbs):
            return sentence
    return sentences[min(1, len(sentences) - 1)] if sentences else "LTG Capital Intelligence"


def extract_key_figures(headline: str, paragraphs: list[str]) -> list[dict[str, str]]:
    figures: list[dict[str, str]] = []
    text = " ".join([headline] + paragraphs)
    money = re.findall(
        r"\$[\d,.]+(?:\.\d+)?\s?(?:T|B|M|K|trillion|billion|million)?",
        text,
        flags=re.IGNORECASE,
    )
    percents = re.findall(r"\b\d+(?:\.\d+)?%", text)
    for value in list(dict.fromkeys(money + percents)):
        label = "Key Metric" if value in headline else "Market Data"
        figures.append({"number": clean_text(value), "label": label})
        if len(figures) >= 3:
            break
    return figures


def get_publication_metadata() -> dict[str, Any]:
    metadata_path = Path(__file__).parent.parent / "publication-metadata.json"
    if not metadata_path.exists():
        initial = {
            "current_volume": 1,
            "last_issue_date": datetime.now().isoformat()[:10],
            "publication_start": "2026-01-01",
        }
        metadata_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")
        return initial

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    last_date = datetime.fromisoformat(metadata["last_issue_date"])
    today = datetime.now()
    if (today - last_date).days > 30:
        metadata["current_volume"] += 1
        metadata["last_issue_date"] = today.isoformat()[:10]
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info("Incremented publication volume to %s", metadata["current_volume"])
    return metadata


def split_into_sections(paragraphs: list[str], target: int = 5) -> list[list[str]]:
    if len(paragraphs) <= target:
        sections = [[p] for p in paragraphs]
    else:
        sections = []
        base = len(paragraphs) // target
        extra = len(paragraphs) % target
        cursor = 0
        for i in range(target):
            size = base + (1 if i < extra else 0)
            sections.append(paragraphs[cursor:cursor + size])
            cursor += size
    while sections and len(sections) < target:
        sections.append([sections[-1][-1]])
    return sections[:target]


def headline_from_section(section: list[str], fallback: str) -> str:
    first = clean_text(section[0] if section else fallback)
    sentence = re.split(r"(?<=[.!?])\s+", first)[0].strip() or fallback
    return sentence[:92].rstrip() + ("..." if len(sentence) > 92 else "")


def deck_from_section(section: list[str], fallback: str) -> str:
    text = " ".join(section)
    sentences = [clean_text(s) for s in re.split(r"(?<=[.!?])\s+", text) if clean_text(s)]
    deck = sentences[1] if len(sentences) > 1 else fallback
    return deck[:170].rstrip() + ("..." if len(deck) > 170 else "")


def infer_category(text: str, fallback: str = "Capital Markets") -> str:
    categories = {
        "Debt & Equity": ["debt", "loan", "refi", "financing", "mortgage", "credit"],
        "Policy": ["policy", "regulation", "law", "bill", "fed", "rate", "treasury"],
        "Transactions": ["acquisition", "sale", "deal", "sold", "purchased", "merger"],
        "Development": ["development", "construction", "built", "building", "lease"],
    }
    lower = text.lower()
    for category, keywords in categories.items():
        if any(keyword in lower for keyword in keywords):
            return category
    return fallback


def transform_article_to_pdf_schema(
    article_html: str,
    article_data: dict[str, Any],
    theme: str | None = None,
) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    body_html = (
        article_data.get("body")
        or article_data.get("body_html")
        or article_html
        or ""
    )
    soup = BeautifulSoup(body_html, "html.parser")
    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
        if clean_text(p.get_text(" ", strip=True))
    ]
    if len(paragraphs) < 2:
        raise ValueError(f"Article has {len(paragraphs)} paragraphs, need at least 2")

    title = (
        article_data.get("headline")
        or article_data.get("title")
        or "Capital Markets Analysis"
    )
    category_fallback = article_data.get("category") or "Capital Markets"
    raw_date = str(article_data.get("date") or article_data.get("date_iso") or datetime.now().isoformat()[:10])[:10]
    issue_date = datetime.fromisoformat(raw_date)
    issue_month = issue_date.strftime("%B %Y")

    stories = []
    for i, section in enumerate(split_into_sections(paragraphs, target=5), 1):
        section_text = " ".join(section)
        headline = headline_from_section(section, title)
        stories.append({
            "number": i,
            "category": infer_category(section_text + " " + title, category_fallback),
            "headline": headline,
            "deck": deck_from_section(
                section,
                article_data.get("subtitle") or article_data.get("meta_description") or "",
            ),
            "dateline": "NEW YORK",
            "date": raw_date,
            "source": article_data.get("source_name") or "Light Tower Group Analysis",
            "key_figures": extract_key_figures(headline, section),
            "pull_quote": extract_pull_quote_from_html(article_html or body_html),
            "paragraphs": section,
        })

    pub_meta = get_publication_metadata()
    return {
        "publication": {
            "volume": pub_meta["current_volume"],
            "issue_date": raw_date,
            "issue_month": issue_month,
            "theme": theme or f"{title} in {issue_month}",
        },
        "author": {
            "name": "Benjamin Rohr",
            "title": "Principal, Light Tower Group",
            "email": "ben@lighttowergroup.co",
        },
        "stories": stories,
    }
