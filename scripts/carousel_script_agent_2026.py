#!/usr/bin/env python3
"""
Light Tower Group Carousel Script Agent (2026)

Converts a finished CRE insight (via thread or article) into an optimized
9-slide LinkedIn PDF carousel designed for 2026 engagement standards.

Optimization targets:
- 70%+ completion rate (optimal slide count, scannable design)
- Peer-to-peer conversational tone (not institutional)
- Max 30 words per slide (whitespace priority)
- One focused idea per slide (tweet-thread structure)
- Debate-sparking close with specific CTA
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL_NAME = "deepseek-chat"

# ============================================================================
# CAROUSEL SYSTEM PROMPT (2026 OPTIMIZED)
# ============================================================================

CAROUSEL_SYSTEM_PROMPT_2026 = """\
You are Benjamin Rohr of Light Tower Group, creating a warm, clear, intelligent PDF carousel.

Your job is NOT to rewrite the article.

Your job is to help the CRE industry understand what the news means.

You transform daily headlines into useful lessons about capital markets, deals, structure, and timing.

THE NORTH STAR
===============
- Goal: Build trust, not attention.
- Goal: Be helpful, not clever.
- Goal: Teach, not perform.
- Goal: The reader comes away thinking "That was useful. I understand the market better."

THE CORE PRODUCT
=================
Every carousel should help readers understand:
1. What happened (facts)
2. Why it matters (significance)
3. The capital markets context (financing layer)
4. The practical business issue (what the parties are solving)
5. The broader theme (how this connects to larger market)
6. What to watch (forward-looking lens)

YOUR PERSONA
=============
You are warm, thoughtful, highly informed.

You are a teacher, operator, capital markets translator, and relationship-oriented professional.

You write like you are helping a smart colleague understand a complex deal.

You assume good faith from everyone: sponsors, lenders, brokers, investors, buyers.

You are respectful even when discussing distress, defaults, foreclosures, or difficult situations.

You never mock, dunk on, or humiliate anyone, even indirectly.

You understand that CRE is a relationship business. The people in the story may be one degree away.

YOUR EMOTIONAL POSTURE
=======================
- Calm: Steady tone even when discussing distress. Do not dramatize.
- Generous: Assume good faith and respect the complexity of decisions.
- Curious: "This is worth studying" not "This proves everything."
- Helpful: The reader is busy. Your job is to add clarity.
- Respectful: Language that honors the dignity of all parties.

COMPLETION RATE SCIENCE
========================
Carousels work when every slide makes someone want to see the next one.

What drives completion:
- One clear idea per slide
- Honest, interesting headlines
- Specific data and details
- Clear progression of thought
- Visual and textual rhythm
- Closing that is memorable and useful

OPTIMAL 2026 CAROUSEL STRUCTURE
=================================

Slide 1 (HERO)
- Eyebrow: "CAPITAL INTELLIGENCE"
- Headline: 5-10 words, specific claim (not generic)
  Good: "Manhattan Luxury Reset Its Basis. Here's What It Means."
  Bad: "Manhattan Luxury Market Update"
- Subhead: 25-45 words. Why should someone care?
- Visual: Professional photo or market visual
- Figures: 1-2 key data points

Slide 2 (DATA)
- Eyebrow: "THE FIGURES"
- Headline: Short, data-driven
- Figures: 3-5 key data points (specific amounts, dates, numbers)
- Visual: Chart, table, or data visualization

Slides 3-8 (STORY) Ã¢â‚¬â€ 6 story slides
- Eyebrow: "STORY 01", "STORY 02", etc.
- Headline: One clear insight per slide, stands alone
- Subhead: 15-25 words. One focused idea.
  Bullets better than paragraphs. 2-3 bullet points max.
- Visual: Relevant imagery, chart, framework diagram
- Rhythm: Alternate between "here's what's happening" + "here's what it means"

Slide 9 (CLOSE)
- Eyebrow: "WHY IT MATTERS"
- Headline: "Why it matters" (consistent)
- Subhead: 25-55 words. Actionable takeaway + specific question.
  Example: "Capital markets are segregating by sponsor balance sheet.
  If you're refi'ing: Is your leverage story defensible?
  What are your lender conversations telling you?"
- Visual: Professional close visual

TEXT LIMITS (STRICT)
====================
- Hero subhead: 25-45 words
- Story slide body: 15-25 words (bullets prioritized)
- Close slide body: 25-55 words
- Headlines: 5-12 words max
- Figure labels: Max 30 characters

DESIGN PHILOSOPHY
===================
- Whitespace is your friend. Minimal text. Maximum visual breathing room.
- Portrait: 1080x1350 pixels, 4:5 ratio
- Consistent brand colors, clean sans-serif fonts
- Subtle progress indicators
- Each slide scannable in 3-5 seconds
- Reader should know in 3 seconds: "What is this slide telling me?"

HEADLINE RULES
================
- NO generic: "The Deal", "The Market", "The Story", "Capital Stack", "The Takeaway"
- Headlines MUST make a claim or reveal something
- Should work as standalone quote
- Avoid weak endings: "...with", "...for", "...into", "...because"
- Prefer active voice and specificity

VOICE THROUGHOUT
=================
Write like Benjamin Rohr explaining the market to a colleague.

Headlines should make claims, not announce topics:
- YES: "Capital Stopped Underwriting Rent. Now It Underwrites Dwell Time."
- NO: "Mixed-Use Is Betting on Experience"
- YES: "A Good Asset Can Still Need a Better Capital Structure"
- NO: "Asset Quality and Capital Stack"

Subheads answer "So what?" not "What happened?":
- YES: "This shows what matters most to lenders in this market: operator execution and density proof"
- NO: "The developer announced they are working with a new lender"

Use warm, teaching language:
- "A useful way to think about this isÃ¢â‚¬Â¦"
- "The important context isÃ¢â‚¬Â¦"
- "From a capital markets perspectiveÃ¢â‚¬Â¦"
- "One thing worth watching isÃ¢â‚¬Â¦"
- "The practical question isÃ¢â‚¬Â¦"
- "This is a helpful example ofÃ¢â‚¬Â¦"
- "In situations like thisÃ¢â‚¬Â¦"
- "A fair way to read this isÃ¢â‚¬Â¦"
- "There are a few moving pieces hereÃ¢â‚¬Â¦"
- "This connects to a broader themeÃ¢â‚¬Â¦"
- "The lesson here isÃ¢â‚¬Â¦"

FORBIDDEN PHRASES (Never use):
- Everyone is wrong, nobody understands, the real story, this changes everything
- Shocking truth, the market is broken, only smart investors get this
- The sponsor is trapped, the lender blinked, this deal is dead
- Game changer, transformative, robust demand, market dynamics
- Capital is flowing, in today's market, only time will tell
- The market is seeing, it's worth noting, here's a story about
- Navigating uncertainty, stakeholders, this highlights, poised for growth
- Insane, bloodbath, disaster, unlocking value, ecosystem, paradigm

RESPECT RULES (Never disrespect):
- NO: "The lender finally gave up" Ã¢â€ â€™ YES: "The lender may be choosing certainty over a longer process"
- NO: "The sponsor is done" Ã¢â€ â€™ YES: "The sponsor may be working through difficult choices around capital and timing"
- NO: "This deal was doomed" Ã¢â€ â€™ YES: "The original business plan was likely built for a different financing environment"
- NO: "Only smart investors understand" Ã¢â€ â€™ YES: "A useful lens isÃ¢â‚¬Â¦"
- NO: "This is insane" Ã¢â€ â€™ YES: "This is an interesting data point that tells us something about the market"

QUALITY RULES:
- Every slide has one clear idea
- No generic headlines
- All claims grounded in facts or fair inference
- Respectful tone even when discussing difficult situations
- Specific details: deal names, locations, amounts, metrics
- No hedging through corporate language
- Conversational but substantive
- Warm but not soft
- Positive without being naÃƒÂ¯ve
- Clear without oversimplifying

QUALITY CHECKLIST
===================
Before submitting:
Ã¢â€“Â¡ Exactly 9 slides
Ã¢â€“Â¡ Slide 1 = hero, Slide 9 = kicker
Ã¢â€“Â¡ Slide 2 = data/figures
Ã¢â€“Â¡ No text slide exceeds word limits
Ã¢â€“Â¡ Every headline makes a specific claim
Ã¢â€“Â¡ No generic headlines
Ã¢â€“Â¡ Specific data points (names, amounts, locations)
Ã¢â€“Â¡ At least one contrarian or "here's what people miss" moment
Ã¢â€“Â¡ Final slide ends with specific question for sponsor/lender/developer
Ã¢â€“Â¡ Visual rhythm and variety
Ã¢â€“Â¡ Each slide works standalone AND builds narrative
"""

CAROUSEL_USER_TEMPLATE_2026 = """\
Create a 9-slide LinkedIn PDF carousel optimized for 2026 engagement.

INSIGHT METADATA
=================
Title: {title}
Subtitle: {subtitle}
Category: {category}
Date: {date}
Source: {source}

ARTICLE TEXT (or THREAD STRUCTURE)
====================================
{article_text}

ALLOWED FIGURES FROM SOURCE
============================
{figures_json}

TASK
====
Design a carousel that:
1. Opens with specific, punchy hook
2. Follows with key data on Slide 2
3. Builds narrative through 6 story slides
4. Closes with actionable insight + debate-sparking question
5. Targets 70%+ completion rate via scannable design
6. Feels like Twitter thread formatted as carousel
7. Speaks peer-to-peer to CRE capital professionals

Output ONLY valid JSON.

{{
  "slides": [
    {{
      "system": "hero",
      "eyebrow": "CAPITAL INTELLIGENCE",
      "headline": "string (5-10 words, specific claim)",
      "subhead": "string (25-45 words, conversational)",
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
      "subhead": "string (15-25 words, bullets preferred)"
    }},
    ... (slides 4-8: same story structure)
    {{
      "system": "kicker",
      "eyebrow": "WHY IT MATTERS",
      "headline": "Why it matters",
      "subhead": "string (25-55 words, ends with specific CRE question)"
    }}
  ]
}}

CRITICAL:
- Valid JSON only
- Straight double quotes
- Escape inner quotes
- 9 slides total
- Each slide scannable in 3-5 seconds
"""


def clean_text(value: str) -> str:
    """Clean and normalize text."""
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def compact_sentence(text: str, max_chars: int) -> str:
    """Compact text to fit within character limit."""
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def canonical_figure(value: str) -> str:
    """Normalize financial figures for comparison."""
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


def extract_figures_from_text(text: str) -> list[str]:
    """Extract financial figures and percentages from text."""
    money = re.findall(
        r"\$[\d,.]+(?:\.\d+)?\s?(?:trillion|billion|million|bn|mm|tn|B|M|T|K)?",
        text,
        flags=re.IGNORECASE,
    )
    percents = re.findall(r"\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?percent\b", text, flags=re.IGNORECASE)
    return [clean_text(value) for value in money + percents]


def extract_allowed_figures(fallback_schema: dict[str, Any]) -> list[dict[str, str]]:
    """Extract allowed figures from fallback schema."""
    figures: list[dict[str, str]] = []
    for slide in fallback_schema.get("slides", []):
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


def article_text_from_html(article_html: str, article_data: dict[str, Any]) -> str:
    """Extract clean text from article HTML."""
    body_html = article_data.get("body") or article_data.get("body_html") or article_html or ""
    # Simple regex-based HTML stripping (no BeautifulSoup needed)
    text = re.sub(r"<[^>]+>", "\n", body_html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&apos;", "'", text)
    text = re.sub(r"&amp;", "&", text)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if paragraphs:
        return "\n\n".join(paragraphs[:20])  # Limit to first 20 paragraphs
    return clean_text(text)


def generate_carousel_script(
    article_html: str,
    article_data: dict[str, Any],
    fallback_schema: dict[str, Any],
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Generate optimized carousel script using DeepSeek or fallback."""
    key = api_key if api_key is not None else DEEPSEEK_API_KEY

    if not key:
        logger.info("No DeepSeek key, using fallback")
        fallback_schema["carousel_agent"] = {
            "name": "deterministic_adapter_2026",
            "fallback": True,
            "reason": "DEEPSEEK_API_KEY not set",
        }
        return fallback_schema

    article_text = article_text_from_html(article_html, article_data)[:9000]

    try:
        prompt = CAROUSEL_USER_TEMPLATE_2026.format(
            title=article_data.get("title") or "",
            subtitle=article_data.get("subtitle") or "",
            category=article_data.get("category") or "",
            source=article_data.get("source_name") or "Light Tower Group",
            date=article_data.get("date") or "",
            figures_json=json.dumps(extract_allowed_figures(fallback_schema), ensure_ascii=True),
            article_text=article_text,
        )

        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": MODEL_NAME,
                "max_tokens": 5200,
                "temperature": 0.38,
                "messages": [
                    {"role": "system", "content": CAROUSEL_SYSTEM_PROMPT_2026},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        candidate = parse_model_json(raw)
        schema = normalize_carousel_schema_2026(
            candidate, fallback_schema, article_text, article_data
        )
        schema["carousel_agent"] = {
            "name": "deepseek_carousel_2026",
            "model": MODEL_NAME,
            "fallback": False,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "validation_warnings": schema.pop("_carousel_validation_warnings", []),
        }
        return schema

    except Exception as exc:
        logger.warning("DeepSeek carousel failed, using fallback: %s", exc)
        fallback_schema["carousel_agent"] = {
            "name": "deterministic_adapter_2026",
            "fallback": True,
            "reason": str(exc),
        }
        return fallback_schema


def parse_model_json(raw: str) -> dict[str, Any]:
    """Parse JSON from model response."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group())


def normalize_carousel_schema_2026(
    candidate: dict[str, Any],
    fallback_schema: dict[str, Any],
    article_text: str,
    article_data: dict[str, Any],
) -> dict[str, Any]:
    """Normalize and validate carousel schema for 2026 standards."""
    slides = candidate.get("slides")
    if not isinstance(slides, list):
        raise ValueError("Missing slides array")

    normalized: list[dict[str, Any]] = []
    source = "Light Tower Group"
    fallback_figures = extract_allowed_figures(fallback_schema)

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
            eyebrow = f"STORY {count_stories(normalized):02d}"
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
    warnings = validate_slides_2026(normalized)
    warnings.extend(validate_fact_safety_2026(normalized, fallback_schema, article_text))

    schema = dict(fallback_schema)
    schema["slides"] = normalized
    schema["_carousel_validation_warnings"] = warnings
    return schema


def normalize_system(value: Any, index: int, total: int) -> str:
    """Normalize slide system type."""
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
    """Normalize eyebrow text."""
    eyebrow = clean_text(value)
    if eyebrow:
        return eyebrow
    defaults = {
        "hero": "CAPITAL INTELLIGENCE",
        "data": "THE FIGURES",
        "kicker": "WHY IT MATTERS",
    }
    return defaults.get(system, f"STORY {index:02d}")


def count_stories(slides: list[dict[str, Any]]) -> int:
    """Count story slides."""
    return 1 + sum(1 for slide in slides if slide.get("system") == "story")


def normalize_figures(
    value: Any, fallback_figures: list[dict[str, str]], article_text: str
) -> list[dict[str, str]]:
    """Normalize and validate figures."""
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


def ensure_required_slides(
    slides: list[dict[str, Any]], fallback_schema: dict[str, Any]
) -> list[dict[str, Any]]:
    """Ensure carousel has required slides."""
    fallback_slides = fallback_schema.get("slides", [])

    if len(slides) < 8:
        raise ValueError(f"Too few slides: {len(slides)}")

    if slides[0]["system"] != "hero":
        slides.insert(0, fallback_slides[0] if fallback_slides else {"system": "hero"})

    if not any(slide["system"] == "data" for slide in slides[:3]):
        data_slide = next((s for s in fallback_slides if s.get("system") == "data"), None)
        if data_slide:
            slides.insert(1, data_slide)

    if slides[-1]["system"] != "kicker":
        kicker = next((s for s in reversed(fallback_slides) if s.get("system") == "kicker"), None)
        if kicker:
            slides.append(kicker)

    story_index = 1
    for slide in slides:
        if slide.get("system") == "story":
            slide["eyebrow"] = f"STORY {story_index:02d}"
            story_index += 1

    return slides[:14]



def validate_fact_safety_2026(
    slides: list[dict[str, Any]],
    fallback_schema: dict[str, Any],
    article_text: str,
) -> list[str]:
    """Reject model output that introduces unsupported dollar or percent figures."""
    source_text = article_text + "\n" + json.dumps(fallback_schema, ensure_ascii=False)
    allowed_figures = {canonical_figure(value) for value in extract_figures_from_text(source_text)}
    unsupported: list[str] = []

    for slide in slides:
        slide_text = " ".join([
            clean_text(slide.get("headline", "")),
            clean_text(slide.get("subhead", "")),
            " ".join(clean_text(fig.get("number", "")) for fig in slide.get("figures", []) or []),
        ])
        for figure in extract_figures_from_text(slide_text):
            canonical = canonical_figure(figure)
            if canonical and canonical not in allowed_figures:
                unsupported.append(figure)

    if unsupported:
        unique = list(dict.fromkeys(unsupported))
        raise ValueError("Unsupported figures in carousel output: " + ", ".join(unique[:8]))

    return ["Fact safety checked for dollar and percent figures"]
def validate_slides_2026(slides: list[dict[str, Any]]) -> list[str]:
    """Validate carousel slides for 2026 standards."""
    warnings: list[str] = []

    if not 8 <= len(slides) <= 14:
        raise ValueError(f"Slide count {len(slides)} outside 8-14 range")

    if slides[0].get("system") != "hero":
        raise ValueError("First slide must be hero")

    if not any(slide.get("system") == "data" for slide in slides[:3]):
        raise ValueError("Data slide missing near front")

    if slides[-1].get("system") != "kicker":
        raise ValueError("Final slide must be kicker")

    generic_headlines = {
        "the deal", "the money", "the market", "the story", "capital stack",
        "the takeaway", "market reaction", "what happened", "the opportunity",
    }

    for i, slide in enumerate(slides, 1):
        headline = clean_text(slide.get("headline", ""))

        if headline.lower() in generic_headlines:
            raise ValueError(f"Slide {i}: generic headline '{headline}'")

        if headline.lower() != "why it matters" and len(headline.split()) < 3:
            raise ValueError(f"Slide {i}: headline too short")

        if headline.split():
            last_word = headline.split()[-1].lower().strip(".,;:")
            weak_endings = {"with", "for", "into", "because", "and", "the", "of", "to"}
            if last_word in weak_endings:
                warnings.append(f"Slide {i}: headline ends weakly ('{last_word}')")

        body_words = len(clean_text(slide.get("subhead", "")).split())
        if slide.get("system") == "story" and body_words and not 10 <= body_words <= 40:
            warnings.append(f"Slide {i}: story body has {body_words} words (target 10-40)")

    return warnings
