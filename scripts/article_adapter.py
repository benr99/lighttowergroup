"""
Transform Insight article HTML into a LinkedIn-native article deck.

The PDF should preserve the generated article's own prose while formatting it
as a bold, readable carousel for LinkedIn sharing.
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


def article_chunks(paragraphs: list[str], max_words: int = 72) -> list[str]:
    """Split article prose into ordered, sentence-preserving carousel chunks."""
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        sentences = [
            clean_text(sentence)
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
            if clean_text(sentence)
        ]
        if not sentences:
            continue
        for sentence in sentences:
            words = len(sentence.split())
            if current and current_words + words > max_words:
                chunks.append(" ".join(current))
                current = []
                current_words = 0
            if words > max_words:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                    current_words = 0
                chunks.append(sentence)
                continue
            current.append(sentence)
            current_words += words

    if current:
        chunks.append(" ".join(current))
    return chunks


def article_slide_headline(chunk: str, index: int) -> str:
    """Use the article's own words as a short display headline."""
    sentence = clean_text(re.split(r"(?<=[.!?])\s+", chunk)[0] if chunk else "")
    words = sentence.split()
    if not words:
        return f"Article, part {index}"
    headline = " ".join(words[:9]).rstrip(" ,;:.")
    if len(words) > 9:
        headline += "..."
    return sentence_case_headline(headline)


LTG_CLOSING_COPY = (
    "Light Tower Group is a commercial real estate capital advisory firm helping "
    "owners, developers, and investors structure and source debt, preferred equity, "
    "joint venture equity, and other institutional capital solutions.\n\n"
    "We work across acquisitions, refinancings, recapitalizations, and development "
    "projects, with a focus on clear strategy, credible execution, and capital that "
    "fits the deal.\n\n"
    "To discuss a financing need, recapitalization, or capital strategy:\n"
    "ben@lighttowergroup.co\n"
    "lighttowergroup.co"
)


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
    if "$" in value and "assets under management" in window:
        return "Assets under management"
    if "$" in value and any(phrase in window for phrase in ["per square foot", "per sf"]):
        return "Implied basis"
    if "$" in value and "fund" in window and any(w in window for w in ["close", "raise", "target"]):
        return "Fund close"
    if "$" in value and any(w in window for w in ["acquisition", "acquired", "purchase", "bought", "transaction"]):
        return "Acquisition price"
    if "$" in value and any(w in nearby for w in ["debt", "loan", "refi", "mortgage", "financing"]):
        return "Debt / financing"
    if "$" in value and any(w in window for w in ["acquire", "sale", "buy", "purchase", "transaction", "bid", "value"]):
        return "Transaction value"
    if any(phrase in window for phrase in ["square feet", "sf"]):
        return "Portfolio size"
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
    headline_limit: int = 96,
) -> dict[str, Any]:
    return {
        "system": system,
        "eyebrow": eyebrow,
        "headline": compact_sentence(headline, headline_limit),
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
    figures = extract_figures(text)
    chunks = article_chunks(paragraphs)
    sentences = sentences_from_paragraphs(paragraphs)
    analysis_sentences = [s for s in sentences if any(word in s.lower() for word in ANALYSIS_WORDS)]
    tension_sentences = [s for s in sentences if any(word in s.lower() for word in TENSION_WORDS)]
    final_sentence = sentences[-1] if sentences else "The capital stack is the story."

    hero_subhead = subtitle or (sentences[0] if sentences else "A capital markets read on the latest commercial real estate move.")
    data_subhead = (analysis_sentences or tension_sentences or sentences or [hero_subhead])[0]

    slides = [
        make_slide(
            "hero",
            "CAPITAL INTELLIGENCE",
            title,
            subhead=hero_subhead,
            subhead_limit=300,
            headline_limit=150,
            source=source,
        ),
        make_slide(
            "data",
            "THE FIGURES",
            data_slide_headline(figures, title),
            subhead=data_subhead,
            subhead_limit=220,
            figures=figures,
            source=source,
        ),
    ]

    used_headlines = {slides[0]["headline"].lower(), slides[1]["headline"].lower()}
    max_story_slides = 11
    for i, chunk in enumerate(chunks[:max_story_slides]):
        headline = story_headline(
            paragraph=chunk,
            index=i,
            total=min(len(chunks), max_story_slides),
            title=title,
            used=used_headlines,
        )
        if len(headline.split()) < 3:
            headline = secondary_fallback_headline(chunk, i)
        used_headlines.add(headline.lower())
        slides.append(make_slide(
            "story",
            story_eyebrow(chunk, i),
            headline,
            subhead=chunk,
            subhead_limit=520,
            source=source,
        ))

    why_text = why_it_matters_text(
        sentences=sentences,
        analysis_sentences=analysis_sentences,
        tension_sentences=tension_sentences,
        final_sentence=final_sentence,
    )
    slides.append(make_slide(
        "kicker",
        "WHY IT MATTERS",
        "Why it matters",
        subhead=why_text,
        subhead_limit=260,
        headline_limit=80,
        source="Light Tower Group",
    ))

    return slides

def data_slide_headline(figures: list[dict[str, str]], title: str) -> str:
    if figures:
        number = figures[0].get("number", "").strip()
        if number:
            lower = title.lower()
            label = figures[0].get("label", "").lower()
            if "fund" in label or any(word in lower for word in ["fund", "fundraise", "raise"]):
                return f"The {number} close sets the stakes"
            if any(word in lower for word in ["refi", "loan", "debt"]):
                return f"Inside the {number} financing"
            if any(word in lower for word in ["foreclosure", "distress", "default"]):
                return f"The {number} pressure point"
            if any(word in lower for word in ["acquisition", "buyout", "buys", "pay", "acquire"]):
                return f"Inside the {number} deal"
            return f"What {number} reveals"
    return "The numbers behind the move"


def story_eyebrow(paragraph: str, index: int) -> str:
    return f"STORY {index + 1:02d}"


def story_headline(
    *,
    paragraph: str,
    index: int,
    total: int,
    title: str,
    used: set[str],
) -> str:
    """Create complete, article-specific slide headlines without inventing facts."""
    sentences = paragraph_sentences(paragraph)
    lower = paragraph.lower()

    if index == 0:
        candidate = lead_headline(sentences, title)
    elif index == total - 1:
        candidate = final_read_headline(sentences)
    elif any(word in lower for word in ["signals", "reflects", "reveals", "suggests", "shows", "means"]):
        candidate = signal_headline(sentences)
    elif any(word in lower for word in ["debt", "loan", "refinancing", "lender", "capital stack", "balance sheet"]):
        candidate = structure_headline(sentences)
    elif any(word in lower for word in ["$", "billion", "million", "premium", "valuation", "price", "basis"]):
        candidate = money_headline(sentences)
    elif any(word in lower for word in ["risk", "pressure", "distress", "foreclosure", "default", "maturity"]):
        candidate = risk_headline(sentences)
    else:
        candidate = crisp_sentence_headline(sentences, title)

    candidate = polish_headline(candidate)
    if candidate.lower() in used or headline_has_weak_ending(candidate) or headline_needs_fallback(candidate):
        candidate = alternate_headline(sentences, candidate)
    if headline_has_weak_ending(candidate) or headline_needs_fallback(candidate):
        candidate = thematic_fallback_headline(paragraph, index)
    if candidate.lower() in used:
        candidate = secondary_fallback_headline(paragraph, index)
    return compact_sentence(candidate, 96)


def paragraph_sentences(paragraph: str) -> list[str]:
    return [
        clean_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
        if clean_text(sentence)
    ]


def lead_headline(sentences: list[str], title: str) -> str:
    first = sentences[0] if sentences else title
    if ":" in first:
        after_colon = first.split(":", 1)[1].strip()
        if after_colon:
            return after_colon
    match = re.search(
        r"(?:on\s+[^,]+,\s+)?(.+?)\s+(closed|acquired|bought|sold|provided|landed|raised|secured|won|took)\s+(.+)",
        first,
        flags=re.IGNORECASE,
    )
    if match:
        actor = trim_actor(match.group(1))
        verb = match.group(2).lower()
        rest = match.group(3).rstrip(".")
        return shorten_transaction_headline(actor, verb, rest)
    return crisp_sentence_headline(sentences, title)


def money_headline(sentences: list[str]) -> str:
    for sentence in sentences:
        if "$" in sentence or re.search(r"\b\d+(?:\.\d+)?%", sentence):
            if any(word in sentence.lower() for word in ["premium", "discount", "valuation", "basis"]):
                return sentence
            if "$" in sentence:
                return sentence
    return crisp_sentence_headline(sentences, "The economics are the story")


def structure_headline(sentences: list[str]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ["debt", "loan", "refinancing", "balance sheet", "capital"]):
            return sentence
    return crisp_sentence_headline(sentences, "The structure matters")


def risk_headline(sentences: list[str]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ["risk", "pressure", "distress", "default", "maturity", "foreclosure"]):
            return sentence
    return crisp_sentence_headline(sentences, "The risk is in the details")


def signal_headline(sentences: list[str]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ["signals", "reflects", "reveals", "suggests", "shows", "means"]):
            return sentence
    return crisp_sentence_headline(sentences, "The market signal is clear")


def final_read_headline(sentences: list[str]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ["will determine", "question", "watch", "if ", "whether"]):
            return sentence
    return crisp_sentence_headline(sentences, "The final read")


def crisp_sentence_headline(sentences: list[str], fallback: str) -> str:
    for sentence in sentences:
        words = sentence.split()
        if 4 <= len(words) <= 13:
            return sentence
    return sentences[0] if sentences else fallback


def trim_actor(actor: str) -> str:
    actor = clean_text(actor)
    actor = re.sub(r"^(?:on|by|after|this week),?\s+", "", actor, flags=re.IGNORECASE)
    return actor.strip(" ,")


def polish_headline(headline: str) -> str:
    headline = clean_text(headline)
    headline = re.sub(r"^On\s+[^,]+,\s+", "", headline)
    headline = re.sub(r"\s+according to .+$", "", headline, flags=re.IGNORECASE)
    headline = re.sub(r"\s+per .+$", "", headline, flags=re.IGNORECASE)
    headline = headline.rstrip(".")
    headline = sentence_case_headline(headline)
    if len(headline) <= 96:
        return headline
    for separator in [":", ";"]:
        if separator in headline:
            right = headline.split(separator, 1)[1].strip()
            if 18 <= len(right) <= 96:
                return sentence_case_headline(right.rstrip("."))
    for separator in [", but ", ", while ", ", as ", ", which ", " which ", " that ", ", and "]:
        if separator in headline:
            left = headline.split(separator, 1)[0].strip()
            if 18 <= len(left) <= 96:
                return sentence_case_headline(left.rstrip("."))
    sentences = paragraph_sentences(headline)
    if sentences and len(sentences[0]) <= 96:
        return sentence_case_headline(sentences[0].rstrip("."))
    return sentence_case_headline(headline_from_words(headline, 88))


def alternate_headline(sentences: list[str], current: str) -> str:
    for sentence in sentences[1:]:
        candidate = polish_headline(sentence)
        if candidate.lower() != current.lower() and not headline_has_weak_ending(candidate):
            return candidate
    return current


def shorten_transaction_headline(actor: str, verb: str, rest: str) -> str:
    rest = clean_text(rest)
    actor = headline_from_words(actor, 36)
    for marker in [" for ", " at ", " with ", " across ", " totaling ", " valued at "]:
        if marker in rest.lower():
            idx = rest.lower().find(marker)
            before = rest[:idx].strip()
            after = rest[idx:].strip()
            candidate = f"{actor} {verb} {before}"
            if len(candidate) >= 22:
                return sentence_case_headline(candidate)
            return sentence_case_headline(f"{candidate} {after.split()[0]}")
    return sentence_case_headline(f"{actor} {verb} {headline_from_words(rest, 52)}")


def headline_from_words(text: str, limit: int) -> str:
    words = clean_text(text).split()
    if not words:
        return ""
    kept: list[str] = []
    for word in words:
        candidate = " ".join(kept + [word])
        if len(candidate) > limit:
            break
        kept.append(word)
    headline = " ".join(kept).rstrip(" ,;:")
    dangling = {
        "a", "an", "the", "of", "for", "to", "with", "and", "or", "in", "on",
        "at", "by", "that", "which", "who", "whose", "from", "into", "than",
        "as", "but", "while", "amid", "about", "like", "including", "significant",
        "absorbing", "requires", "require", "tracks", "track", "asset", "assets",
        "sector", "sectors", "portfolio", "portfolios", "still", "residential",
        "ability", "push",
    }
    while headline.split() and headline.split()[-1].lower() in dangling:
        headline = " ".join(headline.split()[:-1])
    return headline or clean_text(text)


def sentence_case_headline(headline: str) -> str:
    headline = clean_text(headline).strip(" ,;:")
    if not headline:
        return headline
    return headline[0].upper() + headline[1:]


def headline_has_weak_ending(headline: str) -> bool:
    words = clean_text(headline).split()
    if not words:
        return True
    last = words[-1].lower().strip(".,;:")
    weak = {
        "a", "an", "the", "of", "for", "to", "with", "and", "or", "in", "on",
        "at", "by", "that", "which", "from", "into", "than", "as", "but",
        "while", "amid", "about", "like", "including", "significant",
        "absorbing", "requires", "require", "track", "asset", "sector",
        "assets", "sectors", "still", "residential", "is", "without", "logistics",
        "ability", "push", "sponsors", "sponsor",
    }
    return last.rstrip("'") in weak or last in weak or last.endswith("-asset")


def headline_needs_fallback(headline: str) -> bool:
    lower = headline.lower()
    weak_phrases = [
        "told commercial observer",
        "he said",
        "she said",
        "the statement did not disclose",
        "did not disclose",
        "track record with",
    ]
    return any(phrase in lower for phrase in weak_phrases)


def thematic_fallback_headline(paragraph: str, index: int) -> str:
    lower = paragraph.lower()
    if index == 0:
        return "The opening move is the story"
    if any(word in lower for word in ["occupancy", "lease-up", "stabilize", "stabilization"]):
        return "Lease-up risk is the test"
    if "did not disclose" in lower or "no financing details" in lower:
        return "The missing numbers matter"
    if "track record" in lower:
        return "Fertitta already knows the casino business"
    if any(word in lower for word in ["construction debt", "refinancing", "loan", "lender"]):
        return "The financing buys time"
    if any(word in lower for word in ["fund", "limited partners", "commitments"]):
        return "Capital is choosing scale"
    if any(word in lower for word in ["logistics", "residential", "southern europe"]):
        return "The strategy follows dislocation"
    if any(word in lower for word in ["portfolio", "properties", "assets"]):
        return "The asset mix matters"
    if any(word in lower for word in ["market", "valuation", "rate", "investors"]):
        return "The market is sending a signal"
    return "The details change the read"


def secondary_fallback_headline(paragraph: str, index: int) -> str:
    lower = paragraph.lower()
    if any(word in lower for word in ["occupancy", "lease-up", "stabilize", "stabilization"]):
        return "The runway is not the same as certainty"
    if any(word in lower for word in ["refinancing", "loan", "lender", "debt"]):
        return "The debt tells the second story"
    if any(word in lower for word in ["fund", "capital", "commitments"]):
        return "Scale is becoming the advantage"
    if any(word in lower for word in ["portfolio", "properties", "assets"]):
        return "The portfolio is the proof point"
    return f"The next read comes on slide {index + 1}"


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


def parse_article_issue_date(article_data: dict[str, Any]) -> tuple[str, str]:
    """Return YYYY-MM-DD and Month YYYY from generated article metadata."""
    candidates = [
        article_data.get("date_iso"),
        article_data.get("date"),
        datetime.now().isoformat(),
    ]
    formats = ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y")

    parsed = None
    for raw in candidates:
        if not raw:
            continue
        value = str(raw).strip()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            break
        except ValueError:
            pass

        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if parsed:
            break

    if parsed is None:
        parsed = datetime.now()

    return parsed.date().isoformat(), parsed.strftime("%B %Y")


def transform_article_to_pdf_schema(
    article_html: str,
    article_data: dict[str, Any],
    theme: str | None = None,
) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    body_html = article_data.get("body") or article_data.get("body_html") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    article_root = soup.select_one('[itemprop="articleBody"], .article-body') or soup
    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in article_root.find_all("p")
        if clean_text(p.get_text(" ", strip=True))
    ]
    if len(paragraphs) < 2:
        raise ValueError(f"Article has {len(paragraphs)} paragraphs, need at least 2")

    title = article_data.get("headline") or article_data.get("title") or "Capital Markets Analysis"
    subtitle = article_data.get("subtitle") or article_data.get("meta_description") or ""
    category = infer_category(" ".join(paragraphs) + " " + title, article_data.get("category") or "Capital Markets")
    source = article_data.get("source_name") or "Light Tower Group Analysis"
    issue_date, issue_month = parse_article_issue_date(article_data)
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
            "issue_date": issue_date,
            "issue_month": issue_month,
            "theme": theme or title,
        },
        "author": {
            "name": "Benjamin Rohr",
            "title": "Principal, Light Tower Group",
            "email": "ben@lighttowergroup.co",
        },
        "slides": slides,
        "stories": legacy_stories_from_slides(slides, issue_date, category, source),
    }
