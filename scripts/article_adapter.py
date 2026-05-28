"""
Transform Insight article HTML into a LinkedIn-native carousel script.

The PDF should read like a deliberately written swipe story, not like a report
export. This adapter extracts the article's own facts, money, tension, and
market read into repeatable slide systems.
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

TENSION_WORDS = [
    "debt", "risk", "pressure", "default", "foreclosure", "distress",
    "refinancing", "rates", "valuation", "discount", "premium", "loss",
    "maturity", "capital", "liquidity", "private", "public", "lender",
]

ANALYSIS_WORDS = [
    "signals", "reveals", "means", "shows", "demonstrates", "underscores",
    "suggests", "reflects", "changes", "matters", "question", "market",
]


def clean_text(text: Any) -> str:
    text = unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentences_from_paragraphs(paragraphs: list[str]) -> list[str]:
    sentences: list[str] = []
    for paragraph in paragraphs:
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            sentence = clean_text(sentence)
            if 8 <= len(sentence.split()) <= 42:
                sentences.append(sentence)
    return sentences


def compact(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return trimmed + "..."


def paragraph_excerpt(paragraph: str, limit: int = 520) -> str:
    """Keep the article's prose intact enough to read as a narrative slide."""
    return compact(paragraph, limit)


def extract_figures(text: str) -> list[dict[str, str]]:
    money = re.findall(
        r"\$[\d,.]+(?:\.\d+)?\s?(?:T|B|M|K|trillion|billion|million)?",
        text,
        flags=re.IGNORECASE,
    )
    percents = re.findall(r"\b\d+(?:\.\d+)?%", text)
    counts = re.findall(r"\b\d{2,}(?:,\d{3})?\s?(?:sf|square feet|units|assets|properties|stories)\b", text, re.IGNORECASE)
    figures = []
    for value in list(dict.fromkeys(money + percents + counts)):
        figures.append({"number": clean_text(value), "label": figure_label(value, text)})
        if len(figures) >= 4:
            break
    return figures


def figure_label(value: str, text: str) -> str:
    lower = value.lower()
    if "$" in value and any(w in text.lower() for w in ["debt", "loan", "refi", "mortgage"]):
        return "Debt / financing"
    if "$" in value and any(w in text.lower() for w in ["acquire", "sale", "buy", "purchase"]):
        return "Transaction value"
    if "%" in value:
        return "Market move"
    if "unit" in lower or "asset" in lower or "propert" in lower:
        return "Portfolio scale"
    return "Key figure"


def extract_entities(text: str) -> list[str]:
    # Capture useful proper-noun chunks without trying to become full NER.
    matches = re.findall(
        r"\b(?:[A-Z][A-Za-z&.'-]+(?:\s+|$)){2,5}",
        text,
    )
    cleaned = []
    stop = {"Light Tower Group", "Capital Markets", "New York", "United States"}
    for match in matches:
        value = clean_text(match)
        if value and value not in stop and len(value) < 55:
            cleaned.append(value)
    return list(dict.fromkeys(cleaned))[:8]


def select_sentences(sentences: list[str], keywords: list[str], count: int, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    picked = []
    for sentence in sentences:
        lower = sentence.lower()
        if sentence in exclude:
            continue
        if any(keyword in lower for keyword in keywords):
            picked.append(sentence)
        if len(picked) >= count:
            break
    if len(picked) < count:
        for sentence in sentences:
            if sentence not in picked and sentence not in exclude:
                picked.append(sentence)
            if len(picked) >= count:
                break
    return picked[:count]


def bullets_from_sentences(sentences: list[str], count: int = 3, limit: int = 92) -> list[str]:
    return [compact(sentence, limit) for sentence in sentences[:count]]


def extract_pull_quote(paragraphs: list[str]) -> str:
    sentences = sentences_from_paragraphs(paragraphs)
    for sentence in sentences:
        lower = sentence.lower()
        if 12 <= len(sentence.split()) <= 28 and any(word in lower for word in ANALYSIS_WORDS):
            return sentence
    return sentences[-1] if sentences else "The capital stack is the story."


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


def infer_category(text: str, fallback: str = "Capital Markets") -> str:
    categories = {
        "Debt & Equity": ["debt", "loan", "refi", "financing", "mortgage", "credit"],
        "Policy": ["policy", "regulation", "law", "bill", "fed", "rate", "treasury"],
        "Transactions": ["acquisition", "sale", "deal", "sold", "purchased", "merger", "buyout"],
        "Development": ["development", "construction", "built", "building", "lease"],
    }
    lower = text.lower()
    for category, keywords in categories.items():
        if any(keyword in lower for keyword in keywords):
            return category
    return fallback


def make_slide(
    system: str,
    eyebrow: str,
    headline: str,
    *,
    subhead: str = "",
    bullets: list[str] | None = None,
    figures: list[dict[str, str]] | None = None,
    quote: str = "",
    kicker: str = "",
    source: str = "",
    subhead_limit: int = 180,
) -> dict[str, Any]:
    return {
        "system": system,
        "eyebrow": eyebrow,
        "headline": compact(headline, 96),
        "subhead": compact(subhead, subhead_limit),
        "bullets": bullets or [],
        "figures": figures or [],
        "quote": compact(quote, 190),
        "kicker": compact(kicker, 120),
        "source": source,
    }


def build_carousel_slides(
    *,
    title: str,
    subtitle: str,
    paragraphs: list[str],
    category: str,
    source: str,
) -> list[dict[str, Any]]:
    text = " ".join(paragraphs)
    sentences = sentences_from_paragraphs(paragraphs)
    figures = extract_figures(text)
    entities = extract_entities(text)
    quote = extract_pull_quote(paragraphs)

    used: set[str] = set()
    fact_sentences = select_sentences(sentences, ["acquire", "buy", "sale", "deal", "close", "provide", "lend", "raise"], 4)
    used.update(fact_sentences[:2])
    money_sentences = select_sentences(sentences, ["$", "%", "debt", "loan", "valuation", "premium", "discount"], 3, used)
    used.update(money_sentences[:2])
    tension_sentences = select_sentences(sentences, TENSION_WORDS, 4, used)
    used.update(tension_sentences[:2])
    analysis_sentences = select_sentences(sentences, ANALYSIS_WORDS, 4, used)
    player_bullets = [f"{entity}: central to the transaction." for entity in entities[:3]]
    if len(player_bullets) < 3:
        player_bullets.extend(bullets_from_sentences(fact_sentences, 3 - len(player_bullets)))

    hero_headline = title
    analysis_one = analysis_sentences[0] if analysis_sentences else quote
    analysis_quote = "" if clean_text(analysis_one).lower() == clean_text(quote).lower() else quote
    final_sentence = sentences[-1] if sentences else quote

    narrative = paragraphs[:10]
    slides = [
        make_slide(
            "hero",
            category.upper(),
            hero_headline,
            subhead=paragraph_excerpt(narrative[0], 260),
            subhead_limit=260,
            figures=figures[:1],
            source=source,
        ),
        make_slide(
            "data",
            "THE MONEY",
            "The numbers tell the story",
            figures=figures[:3],
            bullets=bullets_from_sentences(money_sentences, 2, 100),
            source=source,
        ),
    ]

    labels = [
        "WHAT HAPPENED",
        "THE SETUP",
        "THE PLAYERS",
        "THE CAPITAL STACK",
        "THE TENSION",
        "THE MARKET READ",
        "THE RISK",
        "THE SIGNAL",
        "THE TAKEAWAY",
        "THE CLOSE",
    ]
    for i, paragraph in enumerate(narrative):
        slide_bullets: list[str] = []
        if i == 0:
            slide_bullets = bullets_from_sentences(fact_sentences, 2, 98)
        elif i == 3:
            slide_bullets = bullets_from_sentences(money_sentences, 2, 98)
        elif i == 5:
            slide_bullets = bullets_from_sentences(tension_sentences, 2, 98)
        slides.append(make_slide(
            "story",
            labels[min(i, len(labels) - 1)],
            headline_from_paragraph(paragraph, labels[min(i, len(labels) - 1)].title()),
            subhead=paragraph_excerpt(paragraph, 520),
            subhead_limit=430,
            bullets=slide_bullets,
            quote=analysis_quote if i == 5 else "",
            source=source,
        ))

    slides.append(
        make_slide(
            "kicker",
            "LTG READ",
            compact(final_sentence, 96),
            subhead="The headline is the transaction. The story is the structure.",
            kicker="If the capital stack works, the deal becomes a signal. If it does not, it becomes a warning.",
            source="Light Tower Group",
        )
    )
    return slides


def headline_from_paragraph(paragraph: str, fallback: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", clean_text(paragraph))[0].strip()
    if not sentence:
        return fallback
    # Keep the headline punchy, but article-specific.
    words = sentence.split()
    if len(words) > 11:
        sentence = " ".join(words[:11])
    return compact(sentence, 82)


def legacy_stories_from_slides(slides: list[dict[str, Any]], date: str, category: str, source: str) -> list[dict[str, Any]]:
    stories = []
    content_slides = [slide for slide in slides if slide["system"] != "kicker"][:5]
    for i, slide in enumerate(content_slides, 1):
        stories.append({
            "number": i,
            "category": category,
            "headline": slide["headline"],
            "deck": slide.get("subhead") or " ".join(slide.get("bullets", [])[:2]),
            "dateline": "NEW YORK",
            "date": date,
            "source": source,
            "key_figures": slide.get("figures", []),
            "pull_quote": slide.get("quote", ""),
            "paragraphs": slide.get("bullets", []) or [slide.get("subhead", "")],
        })
    return stories


def transform_article_to_pdf_schema(
    article_html: str,
    article_data: dict[str, Any],
    theme: str | None = None,
) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    body_html = article_data.get("body") or article_data.get("body_html") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
        if clean_text(p.get_text(" ", strip=True))
    ]
    if len(paragraphs) < 2:
        raise ValueError(f"Article has {len(paragraphs)} paragraphs, need at least 2")

    title = article_data.get("headline") or article_data.get("title") or "Capital Markets Analysis"
    subtitle = article_data.get("subtitle") or article_data.get("meta_description") or ""
    category = infer_category(" ".join(paragraphs) + " " + title, article_data.get("category") or "Capital Markets")
    source = article_data.get("source_name") or "Light Tower Group Analysis"
    raw_date = str(article_data.get("date") or article_data.get("date_iso") or datetime.now().isoformat()[:10])[:10]
    issue_month = datetime.fromisoformat(raw_date).strftime("%B %Y")
    slides = build_carousel_slides(
        title=title,
        subtitle=subtitle,
        paragraphs=paragraphs,
        category=category,
        source=source,
    )

    pub_meta = get_publication_metadata()
    return {
        "publication": {
            "volume": pub_meta["current_volume"],
            "issue_date": raw_date,
            "issue_month": issue_month,
            "theme": theme or title,
        },
        "author": {
            "name": "Benjamin Rohr",
            "title": "Principal, Light Tower Group",
            "email": "ben@lighttowergroup.co",
        },
        "slides": slides,
        "stories": legacy_stories_from_slides(slides, raw_date, category, source),
    }
