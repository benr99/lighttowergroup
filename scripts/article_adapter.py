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


def compact_sentence(text: str, limit: int) -> str:
    """Shorten text without leaving a visibly broken sentence fragment."""
    text = clean_text(text)
    if len(text) <= limit:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    total = ""
    for sentence in sentences:
        candidate = " ".join(kept + [sentence]).strip()
        if len(candidate) <= limit:
            kept.append(sentence)
            total = candidate
        else:
            break
    if total:
        return total

    trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    if not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


def paragraph_excerpt(paragraph: str, limit: int = 520) -> str:
    """Keep the article's prose intact enough to read as a narrative slide."""
    return compact_sentence(paragraph, limit)


def extract_figures(text: str) -> list[dict[str, str]]:
    money = re.findall(
        r"\$[\d,.]+(?:\.\d+)?\s?(?:trillion|billion|million|T|B|M|K)?",
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
    text_lower = text.lower()
    window = context_window(value, text_lower)
    nearby = context_window(value, text_lower, radius=60)
    if "$" in value and "per share" in window:
        return "Offer price"
    if "$" in value and "fund" in window and any(w in window for w in ["close", "raise", "target"]):
        return "Fund close"
    if "$" in value and any(w in nearby for w in ["debt", "loan", "refi", "mortgage", "financing"]):
        return "Debt / financing"
    if "$" in value and any(w in window for w in ["acquire", "sale", "buy", "purchase", "transaction", "bid", "value"]):
        return "Transaction value"
    if "%" in value:
        return "Market move"
    if "unit" in lower or "asset" in lower or "propert" in lower:
        return "Portfolio scale"
    return "Key figure"


def context_window(value: str, text: str, radius: int = 120) -> str:
    normalized = clean_text(value).lower()
    variants = {
        normalized,
        normalized.replace(" billion", " b"),
        normalized.replace(" million", " m"),
        normalized.replace(" trillion", " t"),
    }
    idx = -1
    matched = normalized
    for variant in variants:
        idx = text.find(variant)
        if idx >= 0:
            matched = variant
            break
    if idx < 0:
        return text[: radius * 2]

    sentence_start = max(text.rfind(".", 0, idx), text.rfind("!", 0, idx), text.rfind("?", 0, idx))
    sentence_end_candidates = [pos for pos in (text.find(".", idx), text.find("!", idx), text.find("?", idx)) if pos >= 0]
    if radius >= 100 and sentence_end_candidates:
        sentence_end = min(sentence_end_candidates)
        return text[sentence_start + 1: sentence_end + 1].strip()

    start = max(0, idx - radius)
    end = min(len(text), idx + len(matched) + radius)
    return text[start:end]


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
    return [compact_sentence(sentence, limit) for sentence in sentences[:count]]


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
        "headline": compact_sentence(headline, 96),
        "subhead": compact_sentence(subhead, subhead_limit),
        "bullets": bullets or [],
        "figures": figures or [],
        "quote": compact_sentence(quote, 190),
        "kicker": compact_sentence(kicker, 120),
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

    hero_headline = title
    analysis_one = analysis_sentences[0] if analysis_sentences else quote
    analysis_quote = "" if clean_text(analysis_one).lower() == clean_text(quote).lower() else quote
    final_sentence = sentences[-1] if sentences else quote

    narrative = paragraphs[:10]
    slides = [
        make_slide(
            "hero",
            "CAPITAL INTELLIGENCE",
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
            source=source,
        ),
    ]

    for i, paragraph in enumerate(narrative):
        label = story_label(paragraph, i, len(narrative))
        slides.append(make_slide(
            "story",
            f"STORY {i + 1:02d}",
            label,
            subhead=paragraph_excerpt(paragraph, 520),
            subhead_limit=430,
            source=source,
        ))

    slides.append(
        make_slide(
            "kicker",
            "WHY IT MATTERS",
            "Why it matters",
            subhead=why_it_matters_text(
                sentences=sentences,
                analysis_sentences=analysis_sentences,
                tension_sentences=tension_sentences,
                final_sentence=final_sentence,
            ),
            subhead_limit=260,
            source="Light Tower Group",
        )
    )
    return slides


def story_label(paragraph: str, index: int, total: int) -> str:
    """Use complete, grammar-safe slide titles that match the paragraph's job."""
    lower = paragraph.lower()
    if index == 0:
        return "What happened"
    if index == total - 1:
        return "The final read"
    if any(word in lower for word in ["$", "billion", "million", "premium", "valuation", "price", "basis"]):
        return "The money"
    if any(word in lower for word in ["debt", "loan", "refinancing", "lender", "capital stack", "balance sheet"]):
        return "The capital structure"
    if any(word in lower for word in ["adviser", "ceo", "cfo", "president", "founder", "partner"]):
        return "The people behind it"
    if any(word in lower for word in ["shares", "stock", "market", "investors"]):
        return "The market reaction"
    if any(word in lower for word in ["risk", "pressure", "distress", "foreclosure", "default", "maturity"]):
        return "The risk"
    if any(word in lower for word in ["acquisition", "bought", "buy", "sold", "sale", "portfolio", "properties"]):
        return "The transaction"
    if any(word in lower for word in ["means", "signals", "shows", "reflects", "suggests", "matters"]):
        return "Why it matters"
    return "The story"


def kicker_headline(sentence: str) -> str:
    sentence = clean_text(sentence)
    if not sentence:
        return "The capital stack is the story."
    if len(sentence) <= 96:
        return sentence
    return "The real story is what happens next."


def why_it_matters_text(
    *,
    sentences: list[str],
    analysis_sentences: list[str],
    tension_sentences: list[str],
    final_sentence: str,
) -> str:
    """Build a professional, article-specific closing implication."""
    candidates = sentences + tension_sentences + analysis_sentences + [final_sentence]
    avoid_terms = [
        "ceo", "cfo", "president", "adviser", "role", "continuity", "said",
        "told", "described", "managing director", "founder", "did not disclose",
        "status is unclear",
    ]
    analytical_markers = [
        "signals", "reflects", "reveals", "shows", "suggests", "means",
        "takeaway", "pattern", "willing", "confidence", "implication",
    ]
    analytical_candidates = [
        sentence for sentence in candidates
        if any(marker in sentence.lower() for marker in analytical_markers)
    ]
    if analytical_candidates:
        candidates = analytical_candidates
    scored: list[tuple[int, str]] = []
    for sentence in candidates:
        sentence = clean_text(sentence)
        lower = sentence.lower()
        if not sentence:
            continue
        if len(sentence.split()) < 10:
            continue
        if any(word in lower for word in avoid_terms):
            continue
        score = 0
        for word in ["capital", "debt", "loan", "lender", "financing", "refinancing"]:
            if word in lower:
                score += 4
        for word in ["market", "valuation", "rate", "risk", "investor", "basis"]:
            if word in lower:
                score += 3
        for word in ["signals", "reflects", "suggests", "means", "shows", "matters"]:
            if word in lower:
                score += 6
        for word in ["private", "public"]:
            if word in lower:
                score += 1
        if score:
            scored.append((score, sentence))
    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        return compact_sentence(scored[0][1], 240)
    return compact_sentence(final_sentence, 240) or "The takeaway is in the capital structure, not only the headline."


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
