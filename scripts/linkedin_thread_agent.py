#!/usr/bin/env python3
"""
Light Tower Group LinkedIn Thread Agent (2026)

Converts a finished CRE insight into a native LinkedIn thread: 5-8 short,
punchy posts designed for maximum engagement and debate-sparking on LinkedIn.

Thread posts can be:
1. Posted individually to LinkedIn (as separate posts with threading)
2. Formatted as a 9-slide carousel (thread structure → carousel structure)
3. Used as caption copy under a carousel

Voice: Peer-to-peer insider, conversational, specific, actionable.
Target: CRE sponsors, lenders, equity partners, developers, brokers.
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

from editorial_voice import (
    VOICE_SYSTEM_ADDENDUM,
    editorial_quality_issues,
    load_recent_packages,
    select_editorial_brief,
)

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
THREAD_QUEUE = SITE_ROOT / "linkedin_thread_queue.json"
SITE_URL = os.environ.get("SITE_URL", "https://lighttowergroup.co").rstrip("/")
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


# ============================================================================
# PROMPTS (from UPDATED_PROMPTS_2026.py)
# ============================================================================

THREAD_SYSTEM_PROMPT = """\
You are Benjamin Rohr of Light Tower Group.

Your job is to help the CRE industry understand what important news means.

You transform daily CRE headlines into warm, clear, intelligent explanations of the capital markets context.

Your voice is:

- A great teacher: You make complexity simpler. You respect the reader. You avoid showing off.
- An operator: You understand deals, capital, timing, structure, leverage, basis, and incentives.
- A capital markets translator: You help people see what the money story is beneath the headline.
- A thoughtful colleague: You write like you are helping a peer understand the market.
- A relationship-oriented professional: You are fair, respectful, and never mock distress.

The goal of every post is not attention.

The goal is understanding.

Not virality.

Trust.

Your reader should come away thinking:

"That was helpful. I understand the market better now. Ben is someone I want to stay close to."

CORE PHILOSOPHY
================
- Helpful > Clever
- Clear > Impressive
- Specific > Generic
- Warm > Cool
- Teaching > Hot-taking
- Trust > Engagement
- Fair > Provocative
- Generous > Witty
- Respectful > Edgy

VOICE & TONE
=============
- Warm and professional. Like texting a colleague you respect.
- Clear and direct. One idea per thought. Short sentences when possible.
- Calm even when discussing distress. Do not dramatize. Do not use apocalyptic language.
- Generous. Assume good faith from sponsors, lenders, brokers, investors.
- Curious, not certain. "This is worth studying" beats "This proves everything."
- Respectful. The people in the article may be one degree away. Write fairly.
- Generous with insight. The point is to help the reader understand, not to withhold or gatekeep.
- First-person when authentic. "What I'm seeing" or "In my experience" when true. But not forced.
- Specific. Deal names, numbers, locations, metrics matter. Do not generalize.
- Grounded. Every insight connected to actual capital markets mechanics, not speculation.
- Teaching-oriented. Assume the reader wants to learn and understand better.

THREAD ARCHITECTURE (for 5-8 posts)
====================================
Post 1 (Hook): Grab attention with a specific stat, market contradiction, or deal detail.
            Two-sentence max. No fluff.

Posts 2-4 (Narrative): Build the story. One idea per post. Why does it matter?
           What does it reveal about capital, leverage, timing, or structure?
           2-4 sentences per post. Reference the hook, push forward.

Posts 5-7 (Deep Cut): Who benefits? Who is exposed? What's the second-order effect?
          What do lenders or sponsors need to watch next?
          This is where your CRE expertise shines. Actionable insight.

Post 8 (Close + Question): Strong analytical close paired with ONE specific question
          that would start a real conversation in a capital stack meeting.

TEXT LIMITS:
- Aim for 150-250 characters per post (reads naturally on LinkedIn)
- 2-4 sentences per post max
- Each post should work standalone but build the narrative

FORBIDDEN PHRASES (Never use, they sound like AI):
- game changer, unlocking value, transformative, robust, market dynamics
- capital is flowing, in today's market, only time will tell, it remains to be seen
- everyone is wrong, nobody understands, the real story, this changes everything
- shocking truth, the market is broken, the sponsor is trapped, only smart investors
- the lender blinked, this deal is dead, insane, bloodbath, disaster, in today's dynamic
- navigating uncertainty, market participants, stakeholders, it highlights, it underscores
- poised for growth, strategic opportunity, this underscores, in recent years
- seemingly, arguably, essentially, it is worth noting, notably, interestingly

PREFERRED PHRASES (Build warmth and trust):
- "A useful way to think about this is…"
- "This matters because…"
- "The important context is…"
- "From a capital markets perspective…"
- "One thing worth watching is…"
- "The practical question is…"
- "This is a helpful example of…"
- "The simple version is…"
- "The nuance is…"
- "In situations like this…"
- "A fair way to read this is…"
- "There are a few moving pieces here…"
- "This connects to a broader theme…"
- "The lesson here is…"
- "What I'm seeing in the market…"
- "In my experience…"
- "Often, the conversation becomes…"
- "A way to separate this is…"

RESPECT RULES (Never write in a way that disrespects or humiliates):
- Bad: "The sponsor is trapped" → Better: "The sponsor may be working through difficult choices around timing and capital"
- Bad: "The lender blinked" → Better: "The lender may be choosing a clearer resolution over a longer process"
- Bad: "This deal is doomed" → Better: "The original business plan was likely built for a different financing environment"
- Bad: "Only smart investors understand" → Better: "A useful lens is…"
- Bad: "Everyone is missing this" → Better: "There is another layer here worth paying attention to"

CHECKPOINT BEFORE OUTPUT:
- Did I explain what happened clearly and calmly?
- Did I identify the capital markets angle?
- Did I explain the practical business issue?
- Did I respectfully map out what different parties might care about?
- Did I connect this to a broader theme?
- Did I teach one useful lesson?
- Did I avoid all forbidden phrases and AI language?
- Would the sponsor, lender, or broker in this story feel this was fair?
- Does this sound like Benjamin Rohr helping a peer understand the market?
- Would I be proud to post this under my own name?

Return only valid JSON. No markdown. No text outside the JSON.
"""

THREAD_SYSTEM_PROMPT += "\n\n" + VOICE_SYSTEM_ADDENDUM

THREAD_USER_TEMPLATE = """\
LIGHT TOWER INSIGHT

Title: {title}
Category: {category}
Date: {date}
Insight URL: {insight_url}

ARTICLE TEXT

{article_text}

EDITORIAL BRIEF
{editorial_brief}

TASK

Create a native LinkedIn thread: 5-8 posts written to spark useful
conversation among CRE capital markets professionals. Follow the assigned
editorial mode without naming it in the posts. Avoid the usual generated
patterns: no "the real story," "the most important number is not," "who
benefits," "who is exposed," or manufactured debate.

Each post should work standalone but build narrative cohesion. Format your
output as valid JSON:

{{
  "thread_title": "Short internal label for this thread",
  "posts": [
    {{
      "post_number": 1,
      "post_text": "Post content (aim for 150-250 characters)",
      "format": "hook",
      "character_count": 180
    }},
    {{
      "post_number": 2,
      "post_text": "Post content",
      "format": "narrative",
      "character_count": 200
    }},
    ...
  ],
  "thread_summary": "One sentence: core thesis of this thread",
  "engagement_hooks": ["3 potential debate angles this thread might spark"],
  "final_cta": "The specific question that ends Post 8",
  "suitable_for_carousel": true,
    "format_recommendation": "thread_only | carousel_primary | debate_thread"
}}

CRITICAL CONSTRAINTS:
- Each post is a complete thought but builds the narrative.
- NO generic headlines. Real specificity.
- Open with data/specificity. Don't save the number for later.
- Max 4 sentences per post. Shorter is better.
- Posts 1 and 5 should be the "hook" and "deep cut" moments.
- Return only valid JSON.
"""


def loads_thread_json(raw_json: str) -> dict[str, Any]:
    """Parse model JSON with repair for common harmless syntax slips."""
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


def article_text_from_html(slug: str) -> str:
    """Load article text from HTML file."""
    path = INSIGHTS_DIR / f"{slug}.html"
    if not path.exists():
        return ""
    return strip_html(path.read_text(encoding="utf-8", errors="replace"))


def insight_url(article: dict[str, Any], site_url: str = SITE_URL) -> str:
    """Build insight URL."""
    url = article.get("url") or f"/insights/{article.get('slug', '')}.html"
    if url.startswith("http"):
        return url
    return f"{site_url}{url}"


def _fallback_thread(article: dict[str, Any], site_url: str = SITE_URL) -> dict[str, Any]:
    """Generate a basic fallback thread when API fails."""
    title = article.get("title", "Market Insight")
    url = insight_url(article, site_url)
    excerpt = article.get("excerpt") or article.get("subtitle") or ""
    posts = [
        {
            "post_number": 1,
            "post_text": f"{title}\n\nA useful way to read this is through the capital stack, not only the headline.",
            "format": "hook",
        },
        {
            "post_number": 2,
            "post_text": excerpt or "The simple version: the headline tells you what happened. The financing context tells you why it matters.",
            "format": "narrative",
        },
        {
            "post_number": 3,
            "post_text": "In this cycle, the question is not only whether capital exists. The question is where it has permission to move.",
            "format": "narrative",
        },
        {
            "post_number": 4,
            "post_text": "For sponsors, that means basis, timing, execution risk, and lender appetite matter as much as the asset story.",
            "format": "deep_cut",
        },
        {
            "post_number": 5,
            "post_text": "For lenders and equity partners, the practical read is whether the deal can survive today's cost of capital and still leave a clean exit.",
            "format": "deep_cut",
        },
        {
            "post_number": 6,
            "post_text": "What would you watch next: rent growth, lender appetite, construction timing, or the exit market?",
            "format": "close",
        },
    ]
    for post in posts:
        post["character_count"] = len(post["post_text"])

    return {
        "thread_title": title,
        "posts": posts,
        "thread_summary": "Market structure and capital flow dynamics.",
        "engagement_hooks": [
            "Capital availability vs. capital permission",
            "Sponsor quality and balance sheet strength",
            "Deal timing and market cycles",
        ],
        "final_cta": "What's the capital move you're tracking right now?",
        "suitable_for_carousel": True,
        "format_recommendation": "carousel_primary",
        "insight_url": url,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "agent": "Light Tower LinkedIn Thread (Fallback)",
        "fallback": True,
    }


def generate_thread_package(
    article: dict[str, Any],
    *,
    article_text: str | None = None,
    api_key: str | None = None,
    site_url: str = SITE_URL,
) -> dict[str, Any]:
    """Generate a LinkedIn thread package from an article."""
    api_key = api_key if api_key is not None else DEEPSEEK_API_KEY
    url = insight_url(article, site_url)
    editorial_brief = select_editorial_brief(article, load_recent_packages(THREAD_QUEUE))

    # Get article text
    text = (article_text or article.get("body_text") or "").strip()
    if not text and article.get("body_html"):
        text = strip_html(article["body_html"])
    if not text and article.get("slug"):
        text = article_text_from_html(article["slug"])
    if not text:
        text = article.get("excerpt") or article.get("subtitle") or article.get("title", "")
    text = text[:7000]

    if not api_key:
        package = _fallback_thread(article, site_url)
        package["voice_mode"] = editorial_brief["name"]
        package["editorial_brief"] = editorial_brief
        package["editorial_review"] = {
            "status": "needs_revision",
            "issues": ["automated fallback is never publishable"],
            "independent_checks": True,
        }
        package["publish_ready"] = False
        return package

    prompt = THREAD_USER_TEMPLATE.format(
        title=article.get("title", ""),
        category=article.get("category", ""),
        date=article.get("date", ""),
        insight_url=url,
        article_text=text,
        editorial_brief=json.dumps(editorial_brief, ensure_ascii=False),
    )

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "max_tokens": 4000,
                "temperature": 0.42,
                "messages": [
                    {"role": "system", "content": THREAD_SYSTEM_PROMPT},
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
            raise ValueError("No JSON found in response")

        package = loads_thread_json(match.group())
        package["insight_url"] = url
        package["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        package["agent"] = "Light Tower LinkedIn Thread (DeepSeek)"
        package["fallback"] = False
        package["slug"] = article.get("slug", "")
        package["insight_title"] = article.get("title", "")
        package["voice_mode"] = editorial_brief["name"]
        package["editorial_brief"] = editorial_brief
        joined = "\n\n".join(str(post.get("post_text", "")) for post in package.get("posts", []) if isinstance(post, dict))
        issues = editorial_quality_issues(joined, min_characters=350)
        package["editorial_review"] = {
            "status": "ready_for_review" if not issues else "needs_revision",
            "issues": issues,
            "independent_checks": True,
        }
        package["publish_ready"] = not issues
        return package

    except Exception as e:
        print(f"[WARN] Thread generation failed: {e}", file=sys.stderr)
        package = _fallback_thread(article, site_url)
        package["voice_mode"] = editorial_brief["name"]
        package["editorial_brief"] = editorial_brief
        package["editorial_review"] = {
            "status": "needs_revision",
            "issues": ["automated fallback is never publishable"],
            "independent_checks": True,
        }
        package["publish_ready"] = False
        return package


def save_thread_to_queue(package: dict[str, Any], queue_path: Path = THREAD_QUEUE) -> None:
    """Save thread package to queue."""
    if not package.get("publish_ready"):
        raise ValueError("only independently approved thread packages may enter the publishing queue")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue: list[dict[str, Any]] = []
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception:
            queue = []

    slug = package.get("slug")
    queue = [item for item in queue if item.get("slug") != slug]
    queue.insert(0, package)
    queue = queue[:200]

    queue_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def load_manifest() -> list[dict[str, Any]]:
    """Load insights manifest."""
    if not INSIGHTS_JSON.exists():
        return []
    return json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))


def select_article(slug: str | None = None) -> dict[str, Any]:
    """Select an article from manifest."""
    manifest = load_manifest()
    if not manifest:
        raise FileNotFoundError("No insights.json entries found")
    if slug:
        for article in manifest:
            if article.get("slug") == slug:
                return article
        raise ValueError(f"Slug not found: {slug}")
    return manifest[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Light Tower LinkedIn Thread Agent (2026)")
    parser.add_argument("--slug", help="Generate for a specific Insight slug")
    parser.add_argument("--latest", action="store_true", help="Generate for latest insight")
    parser.add_argument("--no-api", action="store_true", help="Use fallback without calling DeepSeek")
    parser.add_argument("--dry-run", action="store_true", help="Print package without saving")
    args = parser.parse_args()

    article = select_article(args.slug)
    package = generate_thread_package(
        article,
        api_key="" if args.no_api else None,
    )

    if args.dry_run:
        print(json.dumps(package, indent=2, ensure_ascii=False))
    else:
        save_thread_to_queue(package)
        print(f"✓ Saved thread package for {package.get('slug')} → {THREAD_QUEUE}")
        print(f"\nThread posts ({len(package.get('posts', []))} total):")
        for post in package.get("posts", [])[:3]:
            print(f"\n[Post {post.get('post_number')}] {post.get('post_text', '')[:100]}...")


if __name__ == "__main__":
    main()
