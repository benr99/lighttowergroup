"""
DeepSeek carousel writing pass for LinkedIn-native PDF scripts.

This module turns the finished article into a purpose-written carousel script.
It is intentionally downstream of article generation: the article remains the
source of truth, and this pass only reshapes that reporting for swipe reading.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from article_adapter import clean_text, compact_sentence, legacy_stories_from_slides
from editorial_voice import NARRATIVE_FINANCE_ADDENDUM, VOICE_SYSTEM_ADDENDUM, editorial_quality_issues, select_editorial_brief


logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL_NAME = "deepseek-chat"

CAROUSEL_SYSTEM_PROMPT = """\
You are the editorial carousel writer for Light Tower Group, a commercial real
estate capital markets advisory platform.

Turn finished CRE, banking, finance, and private-equity reporting into a
LinkedIn PDF carousel script.

Voice:
- Wall Street Journal clarity.
- Light Tower Group capital-markets intelligence.
- Precise, direct, vivid, and professional.
- Strategic and pattern-seeking, with calm high conviction.
- Written for owners, developers, lenders, brokers, private-equity investors,
  family offices, and capital markets professionals.
- The reader should feel the economic tension, not a marketing pitch.

Editorial rules:
- Do not invent facts, numbers, names, sources, quotes, dates, markets, or outcomes.
- Use only facts present in the article or supplied metadata.
- Preserve all important dollar amounts, percentages, entities, and risk signals.
- Every slide gets one idea.
- Headlines must be unique, article-specific, and complete.
- No generic repeated headlines such as "The money", "The deal", "The market",
  "The story", "Capital stack", or "What happened".
- No hype, emojis, motivational language, or sales copy.
- No "game changer", "unlock", "revolutionary", "ecosystem", "landscape",
  "stakeholders", "going forward", "it remains to be seen", or "in recent years".
- If a fact is uncertain, frame it as uncertainty.

Write like a sharp markets reporter who understands incentives, leverage,
basis, timing, risk transfer, and why capital chooses one deal over another.

Voice calibration:
Bad: "The deal matters because it shows a shift in the market."
Better: "The buyer is not just acquiring assets. It is underwriting a view on
where capital still has room to move."

Bad: "The money tells the story."
Better: "The price is only the first number. The structure is where the risk lives."

Bad: "This is an important transaction."
Better: "The transaction is notable because the capital is moving before
consensus has fully returned."
"""

CAROUSEL_SYSTEM_PROMPT += "\n\n" + VOICE_SYSTEM_ADDENDUM
CAROUSEL_SYSTEM_PROMPT += "\n\n" + NARRATIVE_FINANCE_ADDENDUM

CAROUSEL_USER_TEMPLATE = """\
Create a LinkedIn PDF carousel script from this article.

Target structure:
- 9 to 12 slides.
- Slide 1 system must be "hero".
- Slide 2 system must be "data".
- Middle slides must be "story".
- Final slide must be "kicker" and must use eyebrow "WHY IT MATTERS" and headline
  "Why it matters".

Slide copy:
- Hero headline: strong, specific hook based on the central tension.
- Data slide: highlight the key figures with clean labels.
- Story slides: translate the article into a swipeable narrative.
- Final slide: one professional, article-specific market implication.
- Story slide body copy must be 35 to 75 words.
- Hero subhead must be 25 to 45 words.
- Final slide body must be 25 to 55 words.
- Body copy should be 35 to 75 words on story slides.
- Use complete sentences.
- Avoid repeated sentence openings.
- Make it engaging, but never promotional or speculative beyond the article.
- Do not use generic headlines like "The Deal", "The Money", "The Market",
  "The Story", "Capital Stack", "The Takeaway", or "Market Reaction".
- Do not end headlines with weak words like "with", "for", "into", "because",
  "and", "the", "of", or "to".
- Use only figures from the allowed figure list or article text.

Output only valid JSON. No markdown. No commentary.

Required JSON shape:
{{
  "slides": [
    {{
      "system": "hero",
      "eyebrow": "CAPITAL INTELLIGENCE",
      "headline": "string",
      "subhead": "string",
      "figures": [{{"number": "string", "label": "string"}}]
    }},
    {{
      "system": "data",
      "eyebrow": "THE FIGURES",
      "headline": "string",
      "figures": [{{"number": "string", "label": "string"}}]
    }},
    {{
      "system": "story",
      "eyebrow": "STORY 01",
      "headline": "string",
      "subhead": "string"
    }},
    {{
      "system": "kicker",
      "eyebrow": "WHY IT MATTERS",
      "headline": "Why it matters",
      "subhead": "string"
    }}
  ]
}}

Metadata:
Title: {title}
Subtitle: {subtitle}
Category: {category}
Source: {source}
Date: {date}

Editorial brief (use it to vary the narrative; do not print its labels):
{editorial_brief}

Allowed figures from the source article:
{figures_json}

Article text:
{article_text}
"""


def article_text_from_html(article_html: str, article_data: dict[str, Any]) -> str:
    body_html = article_data.get("body") or article_data.get("body_html") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
        if clean_text(p.get_text(" ", strip=True))
    ]
    if paragraphs:
        return "\n\n".join(paragraphs)
    return clean_text(soup.get_text(" ", strip=True))


def _review_carousel(schema: dict[str, Any], *, fallback: bool) -> dict[str, Any]:
    copy = "\n".join(
        " ".join(
            [
                str(slide.get("headline", "")),
                str(slide.get("subhead", "")),
            ]
        )
        for slide in schema.get("slides", [])
        if isinstance(slide, dict)
    )
    issues = editorial_quality_issues(copy, min_characters=60)
    if fallback:
        issues.append("automated fallback is never publishable")
    schema["editorial_review"] = {
        "status": "ready_for_review" if not issues else "needs_revision",
        "issues": list(dict.fromkeys(issues)),
        "independent_checks": True,
    }
    schema["publish_ready"] = not issues
    return schema


def generate_carousel_script(
    article_html: str,
    article_data: dict[str, Any],
    fallback_schema: dict[str, Any],
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Return a PDF schema, using DeepSeek when available and fallback otherwise."""
    key = api_key if api_key is not None else DEEPSEEK_API_KEY
    editorial_brief = select_editorial_brief(article_data)
    if not key:
        fallback_schema["carousel_agent"] = {
            "name": "deterministic_adapter",
            "fallback": True,
            "reason": "DEEPSEEK_API_KEY not set",
        }
        fallback_schema["voice_mode"] = editorial_brief["name"]
        fallback_schema["editorial_brief"] = editorial_brief
        return _review_carousel(fallback_schema, fallback=True)

    article_text = article_text_from_html(article_html, article_data)[:9000]
    try:
        prompt = CAROUSEL_USER_TEMPLATE.format(
            title=article_data.get("title") or article_data.get("headline") or "",
            subtitle=article_data.get("subtitle") or article_data.get("meta_description") or "",
            category=article_data.get("category") or "",
            source=article_data.get("source_name") or "Light Tower Group Analysis",
            date=article_data.get("date") or article_data.get("date_iso") or "",
            figures_json=json.dumps(allowed_figures(fallback_schema), ensure_ascii=True),
            article_text=article_text,
            editorial_brief=json.dumps(editorial_brief, ensure_ascii=False),
        )
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": MODEL_NAME,
                "max_tokens": 5200,
                "temperature": 0.38,
                "messages": [
                    {"role": "system", "content": CAROUSEL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        candidate = parse_model_json(raw)
        schema = normalize_carousel_schema(candidate, fallback_schema, article_text)
        schema["carousel_agent"] = {
            "name": "deepseek_carousel_writer",
            "model": MODEL_NAME,
            "fallback": False,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "validation_warnings": schema.pop("_carousel_validation_warnings", []),
        }
        schema["voice_mode"] = editorial_brief["name"]
        schema["editorial_brief"] = editorial_brief
        return _review_carousel(schema, fallback=False)
    except Exception as exc:
        logger.warning("[PDF] DeepSeek carousel script failed, using fallback: %s", exc)
        fallback_schema["carousel_agent"] = {
            "name": "deterministic_adapter",
            "fallback": True,
            "reason": str(exc),
        }
        fallback_schema["voice_mode"] = editorial_brief["name"]
        fallback_schema["editorial_brief"] = editorial_brief
        return _review_carousel(fallback_schema, fallback=True)


def parse_model_json(raw: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON object found in carousel response")
    return json.loads(match.group())


def allowed_figures(schema: dict[str, Any]) -> list[dict[str, str]]:
    figures: list[dict[str, str]] = []
    for slide in schema.get("slides", []):
        for fig in slide.get("figures", []) or []:
            number = clean_text(fig.get("number", ""))
            label = clean_text(fig.get("label", ""))
            if number:
                figures.append({"number": number, "label": label})
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for fig in figures:
        key = fig["number"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(fig)
    return deduped[:6]


def canonical_figure(value: str) -> str:
    text = clean_text(value).lower()
    text = text.replace(",", "")
    text = re.sub(r"\busd\b", "$", text)
    text = re.sub(r"\s+", " ", text).strip()
    money = re.match(r"^\$?\s*([\d.]+)\s*(billion|bn|b|million|mm|m|trillion|tn|t|k)?$", text)
    if money:
        number, unit = money.groups()
        unit_map = {
            "billion": "b",
            "bn": "b",
            "b": "b",
            "million": "m",
            "mm": "m",
            "m": "m",
            "trillion": "t",
            "tn": "t",
            "t": "t",
            "k": "k",
            None: "",
        }
        return f"${number}{unit_map[unit]}"
    percent = re.match(r"^([\d.]+)\s*percent$", text)
    if percent:
        return f"{percent.group(1)}%"
    return text


def normalize_carousel_schema(
    candidate: dict[str, Any],
    fallback_schema: dict[str, Any],
    article_text: str,
) -> dict[str, Any]:
    slides = candidate.get("slides")
    if not isinstance(slides, list):
        raise ValueError("Carousel response missing slides array")

    normalized: list[dict[str, Any]] = []
    source = "Light Tower Group"
    fallback_figures = allowed_figures(fallback_schema)
    for index, slide in enumerate(slides[:12]):
        if not isinstance(slide, dict):
            continue
        system = normalize_system(slide.get("system"), index, len(slides))
        eyebrow = normalize_eyebrow(slide.get("eyebrow"), system, index)
        headline = clean_text(slide.get("headline", ""))
        subhead = clean_text(slide.get("subhead") or slide.get("body") or "")
        figures = normalize_figures(slide.get("figures"), fallback_figures, article_text)

        if system == "kicker":
            eyebrow = "WHY IT MATTERS"
            headline = "Why it matters"
        elif system == "data":
            eyebrow = "THE FIGURES"
        elif system == "story" and not eyebrow.startswith("STORY"):
            eyebrow = f"STORY {story_number(normalized):02d}"
        elif system == "hero":
            eyebrow = "CAPITAL INTELLIGENCE"

        normalized.append({
            "system": system,
            "eyebrow": compact_sentence(eyebrow, 40).upper() if system != "story" else eyebrow,
            "headline": compact_sentence(headline, 96),
            "subhead": compact_sentence(subhead, 300 if system == "kicker" else 430),
            "bullets": [],
            "figures": figures,
            "quote": "",
            "kicker": "",
            "source": source,
        })

    normalized = ensure_required_slides(normalized, fallback_schema)
    warnings = validate_slides(normalized)
    warnings.extend(validate_fact_safety(normalized, fallback_schema, article_text))

    schema = dict(fallback_schema)
    schema["slides"] = normalized
    raw_date = schema.get("publication", {}).get("issue_date", "")
    category = fallback_schema.get("stories", [{}])[0].get("category", "Capital Markets")
    schema["stories"] = legacy_stories_from_slides(normalized, raw_date, category, source)
    schema["_carousel_validation_warnings"] = warnings
    return schema


def normalize_system(value: Any, index: int, total: int) -> str:
    system = clean_text(value).lower()
    if system in {"hero", "data", "story", "kicker"}:
        return system
    if system in {"figures", "numbers"}:
        return "data"
    if system in {"why_it_matters", "why it matters", "close", "closing"}:
        return "kicker"
    if index == 0:
        return "hero"
    if index == 1:
        return "data"
    if index == total - 1:
        return "kicker"
    return "story"


def normalize_eyebrow(value: Any, system: str, index: int) -> str:
    eyebrow = clean_text(value)
    if eyebrow:
        return eyebrow
    defaults = {
        "hero": "CAPITAL INTELLIGENCE",
        "data": "THE FIGURES",
        "kicker": "WHY IT MATTERS",
    }
    return defaults.get(system, f"STORY {index:02d}")


def story_number(slides: list[dict[str, Any]]) -> int:
    return 1 + sum(1 for slide in slides if slide.get("system") == "story")


def normalize_figures(value: Any, fallback_figures: list[dict[str, str]], article_text: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    allowed = {canonical_figure(fig["number"]): fig for fig in fallback_figures}
    article_lower = article_text.lower()
    article_figures = {canonical_figure(match) for match in extract_figures_from_text(article_text)}
    figures: list[dict[str, str]] = []
    for fig in value[:4]:
        if not isinstance(fig, dict):
            continue
        number = clean_text(fig.get("number", ""))
        if not number:
            continue
        canonical = canonical_figure(number)
        if number.lower() not in article_lower and canonical not in allowed and canonical not in article_figures:
            continue
        label = clean_text(fig.get("label", "")) or allowed.get(canonical, {}).get("label", "Key figure")
        figures.append({"number": compact_sentence(number, 32), "label": compact_sentence(label, 36)})
    return figures


def ensure_required_slides(slides: list[dict[str, Any]], fallback_schema: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_slides = fallback_schema.get("slides", [])
    if len(slides) < 8:
        raise ValueError(f"Carousel has only {len(slides)} slides")

    if slides[0]["system"] != "hero":
        slides.insert(0, fallback_slides[0])
    if not any(slide["system"] == "data" for slide in slides[:3]):
        data_slide = next((slide for slide in fallback_slides if slide.get("system") == "data"), None)
        if data_slide:
            slides.insert(1, data_slide)
    if slides[-1]["system"] != "kicker":
        kicker = next((slide for slide in reversed(fallback_slides) if slide.get("system") == "kicker"), None)
        if kicker:
            slides.append(kicker)

    story_index = 1
    for slide in slides:
        if slide.get("system") == "story":
            slide["eyebrow"] = f"STORY {story_index:02d}"
            story_index += 1
    return slides[:14]


def validate_slides(slides: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not 8 <= len(slides) <= 14:
        raise ValueError(f"Carousel slide count {len(slides)} outside 8-14")
    if slides[0].get("system") != "hero":
        raise ValueError("First slide must be hero")
    if not any(slide.get("system") == "data" for slide in slides[:3]):
        raise ValueError("Data slide missing near front")
    if slides[-1].get("system") != "kicker":
        raise ValueError("Final slide must be kicker")

    headlines: set[str] = set()
    generic_headlines = {
        "the deal", "the money", "the market", "the story", "capital stack",
        "the takeaway", "market reaction", "what happened",
    }
    weak_endings = {"with", "for", "into", "because", "and", "the", "of", "to", "in", "on"}
    for i, slide in enumerate(slides, 1):
        headline = clean_text(slide.get("headline", ""))
        if headline.lower() != "why it matters" and len(headline.split()) < 3:
            raise ValueError(f"Slide {i} headline too short")
        if headline.lower() in generic_headlines:
            raise ValueError(f"Slide {i} has generic headline: {headline}")
        if headline.split() and headline.split()[-1].lower().strip(".,;:") in weak_endings:
            raise ValueError(f"Slide {i} headline has weak ending: {headline}")
        key = headline.lower()
        if key in headlines and key not in {"why it matters"}:
            raise ValueError(f"Duplicate headline: {headline}")
        headlines.add(key)
        if slide.get("system") in {"hero", "story", "kicker"} and not clean_text(slide.get("subhead", "")):
            raise ValueError(f"Slide {i} missing body/subhead")
        body_words = len(clean_text(slide.get("subhead", "")).split())
        if slide.get("system") == "story" and not 25 <= body_words <= 95:
            warnings.append(f"Slide {i} story body has {body_words} words")
        if slide.get("system") == "hero" and body_words and not 18 <= body_words <= 55:
            warnings.append(f"Hero subhead has {body_words} words")
        if slide.get("system") == "kicker" and body_words and not 18 <= body_words <= 65:
            warnings.append(f"Final slide body has {body_words} words")
    return warnings


def validate_fact_safety(
    slides: list[dict[str, Any]],
    fallback_schema: dict[str, Any],
    article_text: str,
) -> list[str]:
    warnings: list[str] = []
    source_text = source_truth_text(fallback_schema, article_text)
    source_lower = source_text.lower()
    allowed_entities = extract_allowed_entities(source_text)
    allowed_figures = {canonical_figure(value) for value in extract_figures_from_text(source_text)}

    unsupported_figures: list[str] = []
    unsupported_entities: list[str] = []
    for slide in slides:
        text = " ".join([
            clean_text(slide.get("headline", "")),
            clean_text(slide.get("subhead", "")),
            " ".join(clean_text(fig.get("number", "")) for fig in slide.get("figures", []) or []),
        ])
        for figure in extract_figures_from_text(text):
            canonical = canonical_figure(figure)
            if canonical and canonical not in allowed_figures:
                unsupported_figures.append(figure)
        for entity in extract_output_entities(text):
            if entity.lower() not in allowed_entities and entity.lower() not in source_lower:
                unsupported_entities.append(entity)

    if unsupported_figures:
        unique = sorted(set(unsupported_figures))
        raise ValueError(f"Unsupported figures in carousel output: {unique}")
    if unsupported_entities:
        unique = sorted(set(unsupported_entities))
        raise ValueError(f"Unsupported named entities in carousel output: {unique[:10]}")
    if not any(slide.get("carousel_agent") for slide in []):
        warnings.append("Fact safety checked with lexical entity/figure validation")
    return warnings


def source_truth_text(fallback_schema: dict[str, Any], article_text: str) -> str:
    metadata = json.dumps(fallback_schema.get("publication", {}), ensure_ascii=False)
    slides_text = " ".join(
        " ".join([
            clean_text(slide.get("headline", "")),
            clean_text(slide.get("subhead", "")),
            " ".join(clean_text(fig.get("number", "")) for fig in slide.get("figures", []) or []),
        ])
        for slide in fallback_schema.get("slides", [])
    )
    return f"{article_text}\n{metadata}\n{slides_text}"


def extract_figures_from_text(text: str) -> list[str]:
    money = re.findall(
        r"\$[\d,.]+(?:\.\d+)?\s?(?:trillion|billion|million|bn|mm|tn|B|M|T|K)?",
        text,
        flags=re.IGNORECASE,
    )
    percents = re.findall(r"\b\d+(?:\.\d+)?\s?(?:%|percent)\b", text, flags=re.IGNORECASE)
    return [clean_text(value) for value in money + percents]


ENTITY_STOPWORDS = {
    "The", "This", "That", "There", "These", "Those", "A", "An", "And", "But",
    "For", "With", "Without", "Inside", "Why", "What", "When", "Where", "How",
    "Capital", "Market", "Markets", "Real", "Estate", "Debt", "Equity", "Fund",
    "Funds", "Loan", "Loans", "Office", "Retail", "Industrial", "Multifamily",
    "Portfolio", "Properties", "Investors", "Lenders", "Developers", "Story",
    "Light", "Tower", "Group", "CRE", "PDF", "LinkedIn",
}

ALLOWED_BRAND_ENTITIES = {
    "light tower group", "light tower", "ltg", "cre", "pdf", "linkedin",
    "wall street journal",
}


def extract_allowed_entities(text: str) -> set[str]:
    entities = {entity.lower() for entity in extract_output_entities(text)}
    entities.update(ALLOWED_BRAND_ENTITIES)
    return entities


def extract_output_entities(text: str) -> list[str]:
    entities: list[str] = []
    # Multi-word proper nouns: Bain Capital, Harbor Group International, New York.
    for match in re.findall(r"\b(?:[A-Z][A-Za-z&.'-]+|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z&.'-]+|[A-Z]{2,})){1,5}\b", text):
        cleaned = clean_entity(match)
        if cleaned:
            entities.append(cleaned)
    # Important single-word names/brands that are easy for models to invent.
    for match in re.findall(r"\b[A-Z][A-Za-z&.'-]{3,}\b|\b[A-Z]{2,}\b", text):
        cleaned = clean_entity(match)
        if cleaned:
            entities.append(cleaned)
    return list(dict.fromkeys(entities))


def clean_entity(value: str) -> str:
    value = clean_text(value).strip(" ,.;:()[]{}")
    if not value:
        return ""
    parts = [part for part in value.split() if part not in ENTITY_STOPWORDS]
    if not parts:
        return ""
    cleaned = " ".join(parts)
    if cleaned.lower() in ALLOWED_BRAND_ENTITIES:
        return cleaned
    if len(cleaned) < 3:
        return ""
    return cleaned
