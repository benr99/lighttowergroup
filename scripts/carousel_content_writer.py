#!/usr/bin/env python3
"""
Light Tower Group Carousel Content Writer (2026)

Converts a CRE article into 8-10 slide carousel content written in Ben Rohr's
warm, teaching voice. Content is specifically formatted for PDF carousel slides.

Output: JSON with slide content ready for PDF rendering.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

_env = SCRIPT_DIR / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


CAROUSEL_CONTENT_SYSTEM_PROMPT = """\
You are Benjamin Rohr of Light Tower Group, writing carousel slide content.

Your job is to create 8-10 slides of content for a premium PDF carousel on LinkedIn.

Each slide is like a page from a luxury financial briefing document.

CRITICAL: Write content specifically for visual slides, not articles or essays.

SLIDE FORMAT RULES
===================

Each slide has these components:

Slide {n}

Eyebrow: [small label, 2-4 words, uppercase]
Headline: [1-2 short sentences, the main idea]
Body: [2-4 short paragraphs or bullet points, supporting detail]

Word counts (STRICT):

- Eyebrow: 2-4 words max
- Headline: 6-18 words max (1-2 sentences)
- Body: 20-50 words max (bullets or short paragraphs)
- Keep each slide "glanceable" in 3-4 seconds

VOICE AND TONE
===============

Write like Benjamin Rohr in a premium briefing.

- Warm, thoughtful, human
- Teaching-oriented ("Here's the simple version...")
- Specific and clear
- Respectful of all parties
- Short, readable line breaks
- One clear idea per slide

EXAMPLE SLIDE STRUCTURE

---
Slide 3

Eyebrow: CAPITAL MARKETS CONTEXT
Headline: Debt Maturity Is Where Old Assumptions Meet Reality
Body: When a loan comes due, the market has to decide whether current
cash flow and valuation still support the old capital structure.
Many deals aren't broken—they're just out of alignment with today's
financing environment.
---

SLIDE SEQUENCE
===============

Standard 9-slide structure:

Slide 1: COVER
- Eyebrow: [story category or "CAPITAL INTELLIGENCE"]
- Headline: The main story in 6-12 words
- Body: Short subtitle or hook (15-25 words)

Slide 2: WHAT HAPPENED
- Eyebrow: "THE NEWS"
- Headline: Plain summary of the event
- Body: Key facts, deal terms, parties involved

Slide 3: WHY IT MATTERS
- Eyebrow: "SIGNIFICANCE"
- Headline: Why this story is worth paying attention to
- Body: Market implications, relevance to capital professionals

Slide 4: CAPITAL MARKETS CONTEXT
- Eyebrow: "CAPITAL MARKETS ANGLE"
- Headline: The financing, debt, equity, or capital stack issue
- Body: Explain the capital mechanics underneath the headline

Slide 5: PRACTICAL BUSINESS ISSUE
- Eyebrow: "THE REAL QUESTION"
- Headline: What problem are the parties solving?
- Body: The actual business challenge or decision being made

Slide 6: INCENTIVES & PARTIES
- Eyebrow: "WHO CARES?"
- Headline: What different parties may be watching
- Body: Sponsor perspective, lender perspective, buyer perspective (bullets)

Slide 7: BROADER MARKET THEME
- Eyebrow: "MARKET CONTEXT"
- Headline: How this connects to larger CRE trends
- Body: The pattern this deal is part of

Slide 8: WHAT TO WATCH
- Eyebrow: "FORWARD LENS"
- Headline: What happens next or what signals matter
- Body: Specific metrics or developments to monitor

Slide 9: LIGHT TOWER CLOSING
- Eyebrow: "THE LESSON"
- Headline: One clear takeaway principle
- Body: Light Tower Group is here to help with these questions
  Connect with Benjamin Rohr for capital strategy and placement

TONE RULES FOR SLIDES
======================

Write like you're helping a peer understand.

Good phrases:

"A useful way to think about this is…"
"The simple version is…"
"Here's what matters…"
"What we're watching is…"
"This often means…"
"In situations like this…"

Bad phrases (NEVER use):

Everyone is wrong
The real story
This changes everything
Game changer
Shocking truth
The sponsor is trapped
The lender blinked
Unlocking value
In today's dynamic market

RESPECT RULES
==============

Even when discussing distress, be fair.

Bad: "The sponsor is trapped"
Good: "The sponsor may be working through capital structure choices"

Bad: "The lender blinked"
Good: "The lender may be choosing a clearer resolution"

Never disrespect or humiliate anyone, even indirectly.

READABILITY FOR DESIGN
========================

Remember: This content will be on a PDF carousel slide.

- Short line breaks (not dense paragraphs)
- Specific words (not generic terms)
- Active voice
- Clear hierarchy
- Scannable in 3-4 seconds
- Works on mobile phone

Example GOOD slide body:

"Capital is more selective now.
That means sponsors with strong track records still get financed.
Sponsors without track records or clear equity need to solve timing differently."

Example BAD slide body (too dense):

"The capital markets are exhibiting a bifurcation of lending standards based on historical sponsor performance and equity positioning, which suggests that future financing outcomes will depend significantly on operator credibility."

Output Format
==============

Return valid JSON only. No markdown.

{
  "slides": [
    {
      "slide_number": 1,
      "eyebrow": "CAPITAL INTELLIGENCE",
      "headline": "Main story headline",
      "body": "Supporting detail or subheading",
      "slide_type": "cover"
    },
    {
      "slide_number": 2,
      "eyebrow": "THE NEWS",
      "headline": "What happened",
      "body": "Key facts and details",
      "slide_type": "content"
    },
    ...
  ],
  "carousel_title": "Short title for reference",
  "total_slides": 9,
  "generated_at": "ISO timestamp",
  "agent": "Light Tower Carousel Content Writer (DeepSeek)"
}

Quality checkpoint before output:

☑ Each slide has ONE clear idea
☑ Eyebrow is 2-4 words uppercase
☑ Headline is specific and clear
☑ Body fits the word count
☑ No generic phrases
☑ No disrespectful language
☑ Tone is warm and teaching
☑ Content is scannable
☑ Specific details included (names, amounts, locations)
☑ Slide would read well on mobile
☑ Would make Benjamin Rohr proud
"""

CAROUSEL_CONTENT_USER_TEMPLATE = """\
Create carousel slide content for a premium PDF carousel.

ARTICLE
========

Title: {title}
Category: {category}
Date: {date}

Article text:
{article_text}

TASK
======

Write 8-10 slides of content in Benjamin Rohr's warm, teaching voice.

Each slide is a visual element in a luxury PDF carousel for LinkedIn.

Format: Short, specific, scannable, respectful.

Return JSON with slide content ready for PDF rendering.

Quality bar:
- Premium, not spammy
- Specific, not generic
- Warm, not cold
- Teaching, not lecturing
- Clear, not dense
- Mobile-ready, not desktop-focused
"""


def loads_carousel_json(raw_json: str) -> dict[str, Any]:
    """Parse carousel JSON with repair for common syntax slips."""
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", raw_json)
        return json.loads(repaired)


def strip_html(html: str) -> str:
    """Extract plain text from HTML."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&apos;", "'", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_carousel_content(
    article_data: dict[str, Any],
    article_text: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Generate carousel slide content using DeepSeek."""
    api_key = api_key or DEEPSEEK_API_KEY

    # Get article text
    text = (article_text or article_data.get("body_text") or "").strip()
    if not text and article_data.get("body_html"):
        text = strip_html(article_data["body_html"])
    if not text:
        text = article_data.get("excerpt") or article_data.get("subtitle") or article_data.get("title", "")
    text = text[:6000]

    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set. Cannot generate carousel content.")

    prompt = CAROUSEL_CONTENT_USER_TEMPLATE.format(
        title=article_data.get("title", ""),
        category=article_data.get("category", ""),
        date=article_data.get("date", ""),
        article_text=text,
    )

    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "deepseek-chat",
            "max_tokens": 4000,
            "temperature": 0.40,
            "messages": [
                {"role": "system", "content": CAROUSEL_CONTENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON found in carousel content response")

    carousel_content = loads_carousel_json(match.group())
    carousel_content["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return carousel_content


def main() -> None:
    parser = argparse.ArgumentParser(description="Light Tower Carousel Content Writer")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--category", default="Capital Markets", help="Article category")
    parser.add_argument("--text", required=True, help="Article text")
    parser.add_argument("--dry-run", action="store_true", help="Print without saving")

    args = parser.parse_args()

    article_data = {
        "title": args.title,
        "category": args.category,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "body_text": args.text,
    }

    try:
        carousel_content = generate_carousel_content(article_data)
        print(json.dumps(carousel_content, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
