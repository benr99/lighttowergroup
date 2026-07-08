#!/usr/bin/env python3
"""
Light Tower Group Social Strategy Selector (2026)

Analyzes each insight and recommends the optimal format mix for maximum
engagement and lead generation.

Decision logic:
- High data density + actionable → Carousel primary
- Contrarian framing + low data → Debate thread primary
- Policy/macro + reference value → Report primary
- Market observation + high curiosity → Debate thread primary
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

STRATEGY_SYSTEM_PROMPT = """\
You are Light Tower Group's Content Strategy Selector for 2026.

For each insight, you recommend the optimal format(s) to maximize engagement
and lead generation among CRE capital professionals.

THE 2026 CONTENT MIX
====================
- 60% Carousels (scannable, high engagement, high completion)
- 25% Debate/Opinion Posts (punchy threads, spark discussion)
- 10% Polls (quick market sentiment)
- 5% Deep Reports (full research, policy)

YOUR JOB: Analyze the insight and recommend format(s).

ANALYSIS FRAMEWORK
===================
1. Data Density: Heavy numbers + specific figures?
2. Debate Potential: Challenges assumptions? Contrarian? Newsworthy?
3. Actionability: Can sponsors/lenders apply this immediately?
4. Novelty: Breaking new ground or confirming patterns?
5. Emotional Hook: FOMO? Curiosity? Market tension?

RECOMMENDATION LOGIC
=====================
IF high data density + actionable + novel
  → Primary: CAROUSEL (shows numbers clearly, high completion)
  → Secondary: Debate post (spark discussion about implications)
  → Reason: Data is easier to scan in carousel format

IF high debate potential + contrarian + low-to-medium data density
  → Primary: DEBATE_THREAD (conversational, fast-moving)
  → Secondary: Carousel (if it warrants full development)
  → Reason: Threads feel more peer-to-peer, debate-ready

IF heavy research + policy/macro lens + reference value
  → Primary: REPORT (full research piece)
  → Secondary: Carousel (summary version for LinkedIn)
  → Reason: Deep research needs proper formatting

IF simple market observation + high curiosity factor
  → Primary: DEBATE_THREAD (conversational, immediate)
  → Secondary: Carousel (if broader implications warrant)
  → Reason: Threads spark faster engagement

IF market sentiment question + binary or multi-choice angle
  → Primary: POLL (ask market, get feedback)
  → Secondary: Follow-up thread (explore responses)
  → Reason: Polls drive high engagement + market input

STRONG SIGNALS FOR CAROUSEL PRIMARY:
- 3+ specific financial figures or metrics
- Deal with names, amounts, locations
- "Here's how to think about X" framework
- Macro-to-micro translation
- Visual story potential (before/after, timeline, comp table)

STRONG SIGNALS FOR DEBATE_THREAD PRIMARY:
- Contrarian framing ("Everyone says X, but Y")
- Market contradiction or tension
- "Here's what I'm seeing" observation
- Naturally ends with "what's your take?"
- Emotional resonance (deal crunch, opportunity)

STRONG SIGNALS FOR REPORT PRIMARY:
- 1500+ words of research
- Policy/regulation analysis
- Comprehensive market study
- Requires multiple charts/tables
- Reference/archive value

STRONG SIGNALS FOR POLL PRIMARY:
- Simple binary or clear multi-choice question
- Market sentiment question
- "Will X happen by Y date?"
- "How are you underwriting Z?"
- NOT suitable for complex nuance

OUTPUT FORMAT
===============
Return JSON with:
- primary_format: carousel | thread | poll | report
- secondary_formats: [list of optional secondary formats]
- rationale: Why this format for this insight (2-3 sentences)
- engagement_potential: high | medium | low
- lead_potential: high | medium | low
- recommended_schedule: cadence and timing
- content_angle: How to frame it
- key_hooks: 2-3 specific angles to emphasize
"""

STRATEGY_USER_TEMPLATE = """\
Recommend the optimal 2026 content strategy for this insight.

INSIGHT SUMMARY
================
Title: {title}
Category: {category}
Date: {date}
Excerpt: {excerpt}

ARTICLE TEXT
=============
{article_text}

TASK
====
Analyze and recommend format(s), timeline, and strategy.

Return valid JSON:

{{
  "primary_format": "carousel | thread | poll | report",
  "secondary_formats": ["format", "format"],
  "rationale": "Why this format for this insight",
  "engagement_potential": "high | medium | low",
  "lead_potential": "high | medium | low",
  "estimated_completion_rate": "70-85% or similar",
  "content_angle": "How to frame the primary format",
  "key_hooks": ["Hook 1", "Hook 2", "Hook 3"],
  "debate_angle": "If debate thread: what question sparks engagement?",
  "carousel_focus": "If carousel: what's the hero slide hook?",
  "publication_timing": "Immediate | Next 48 hours | Schedule for opportunity",
  "cta_recommendation": "What CTA works best for this topic",
  "lead_source_likelihood": "Which format likely drives actual inquiries?"
}}

Be concise. Format recommendations should be data-driven, not generic.
Return only valid JSON.
"""


def analyze_article_characteristics(article_text: str, article_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze article for strategy selection signals."""
    text_lower = article_text.lower()
    word_count = len(article_text.split())

    # Count financial figures
    figures = re.findall(r"\$[\d,.]+(?:\.\d+)?\s?(?:billion|million|bn|mm|B|M)?", article_text)
    percents = re.findall(r"\b\d+(?:\.\d+)?\%", article_text)

    # Check for contrarian language
    contrarian_phrases = [
        "everyone says", "not about", "not just", "real story",
        "what people miss", "despite", "contrary to", "assumption",
    ]
    contrarian_score = sum(1 for phrase in contrarian_phrases if phrase in text_lower)

    # Check for policy/regulation keywords
    policy_keywords = [
        "policy", "regulation", "law", "bill", "congress", "senate",
        "fha", "fannie", "freddie", "sec", "cftc", "fdic",
    ]
    policy_score = sum(1 for kw in policy_keywords if kw in text_lower)

    # Check for data density
    data_density = len(figures) + len(percents)

    # Check for actionability
    actionable_keywords = [
        "how to", "framework", "strategy", "underwrite", "structure",
        "approach", "model", "calculate", "metric", "measure",
    ]
    actionability_score = sum(1 for kw in actionable_keywords if kw in text_lower)

    return {
        "word_count": word_count,
        "financial_figures": len(figures),
        "percentages": len(percents),
        "data_density_score": data_density,
        "contrarian_score": contrarian_score,
        "policy_score": policy_score,
        "actionability_score": actionability_score,
        "has_deal_specifics": bool(re.search(r"\$\d+[BM]|\d+% |square feet", article_text)),
    }


def recommend_format(article_text: str, article_data: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    """Recommend content format using DeepSeek or heuristics."""
    api_key = api_key if api_key is not None else DEEPSEEK_API_KEY

    # Get article characteristics for heuristic fallback
    characteristics = analyze_article_characteristics(article_text, article_data)

    if not api_key:
        # Use heuristics if no API key
        return _heuristic_recommendation(article_data, characteristics)

    # Use DeepSeek for smarter analysis
    try:
        prompt = STRATEGY_USER_TEMPLATE.format(
            title=article_data.get("title", ""),
            category=article_data.get("category", ""),
            date=article_data.get("date", ""),
            excerpt=article_data.get("excerpt") or article_data.get("subtitle") or "",
            article_text=article_text[:5000],  # Limit for API
        )

        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "max_tokens": 1500,
                "temperature": 0.35,
                "messages": [
                    {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("No JSON found")

        result = json.loads(match.group())
        result["characteristics"] = characteristics
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["method"] = "deepseek"
        return result

    except Exception as e:
        print(f"[WARN] Strategy analysis failed: {e}")
        return _heuristic_recommendation(article_data, characteristics)


def _heuristic_recommendation(article_data: dict[str, Any], characteristics: dict[str, Any]) -> dict[str, Any]:
    """Recommend format based on heuristic analysis."""
    data_density = characteristics["data_density_score"]
    contrarian = characteristics["contrarian_score"]
    policy = characteristics["policy_score"]
    actionability = characteristics["actionability_score"]
    has_deal_specifics = characteristics["has_deal_specifics"]

    # Decision logic
    if data_density >= 5 and has_deal_specifics:
        primary = "carousel"
        engagement = "high"
        lead_potential = "high"
        rationale = "High data density with specific deal details. Carousel format maximizes clarity and completion rate."

    elif contrarian >= 3 and data_density <= 3:
        primary = "thread"
        engagement = "high"
        lead_potential = "medium"
        rationale = "Contrarian framing with lower data density. Debate thread format sparks engagement and discussion."

    elif policy >= 3:
        primary = "report"
        engagement = "medium"
        lead_potential = "medium"
        rationale = "Policy/regulation focus. Report format best for comprehensive analysis and reference value."

    elif contrarian >= 2:
        primary = "thread"
        engagement = "high"
        lead_potential = "medium"
        rationale = "Market observation with contrarian angle. Thread format enables conversational engagement."

    else:
        primary = "carousel"
        engagement = "medium"
        lead_potential = "medium"
        rationale = "Balanced insight. Carousel provides structured, scannable format."

    return {
        "primary_format": primary,
        "secondary_formats": ["carousel"] if primary != "carousel" else ["thread"],
        "rationale": rationale,
        "engagement_potential": engagement,
        "lead_potential": lead_potential,
        "estimated_completion_rate": "70-80%" if primary == "carousel" else "High (thread engagement)",
        "content_angle": f"Lead with data and deal specifics" if primary == "carousel" else "Lead with contrarian insight or market observation",
        "key_hooks": [
            "Specific market data or deal details",
            "Capital stack implication",
            "Who should care and why",
        ],
        "publication_timing": "Immediate",
        "cta_recommendation": "Call to debate/discuss if thread, deep read if carousel",
        "lead_source_likelihood": "High" if lead_potential == "high" else "Medium",
        "characteristics": characteristics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "heuristic",
    }


def main() -> None:
    """CLI for strategy analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Strategy Selector")
    parser.add_argument("--slug", help="Analyze specific insight")
    parser.add_argument("--dry-run", action="store_true", help="Print without saving")
    args = parser.parse_args()

    if not args.slug:
        print("Usage: python social_strategy_selector.py --slug <insight_slug>")
        return

    # Load article (placeholder - would load from actual data)
    print(f"Analyzing strategy for: {args.slug}")
    print("Strategy analysis complete.")


if __name__ == "__main__":
    main()
