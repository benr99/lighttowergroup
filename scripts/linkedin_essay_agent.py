#!/usr/bin/env python3
"""
Light Tower CRE Essay Desk

Companion agent for the daily Insight pipeline. It turns a finished technical
Light Tower Insight into a founder-led LinkedIn essay package:
technical summary, hidden thesis, long essay, hooks, first comment, visual
recommendation, follow-up comment, DM follow-up, and quality scoring.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
ESSAY_QUEUE = SITE_ROOT / "linkedin_essay_queue.json"
SITE_URL = os.environ.get("SITE_URL", "https://lighttowergroup.co").rstrip("/")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MOJIBAKE_RE = re.compile("[" + chr(0x00E2) + chr(0x00C3) + chr(0xFFFD) + "]")


_env = SCRIPT_DIR / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def assert_no_mojibake(label: str, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    match = MOJIBAKE_RE.search(text)
    if match:
        start = max(match.start() - 40, 0)
        end = min(match.end() + 40, len(text))
        snippet = text[start:end].replace("\n", " ")
        raise ValueError(f"{label} contains possible mojibake near: {snippet}")


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer"}:
            self.skip_depth += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3"} and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"p", "div", "li", "h1", "h2", "h3"} and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


ESSAY_SYSTEM_PROMPT = """\
You are the Light Tower CRE Essay Desk.

You write long-form LinkedIn opinion essays for Ben Rohr, founder of Light Tower Group.

Ben writes at the intersection of commercial real estate capital markets, multifamily
and development, debt and equity placement, distressed asset intelligence, NYC housing
policy, AI-driven CRE research, the future of cities, and founder/operator market
judgment.

Your job is to take a technical Light Tower Insight, deal review, market article,
transaction announcement, or underwriting note and turn it into a high-dwell LinkedIn
mini-essay. The essay should interpret the Insight, not summarize it.

The post should feel like a smart CRE columnist, capital markets operator, and
city-focused thinker explaining what this deal reveals about the broader evolution
of CRE in 2026.

Writing style:
- Opinionated, analytical, specific, deal-grounded.
- Literary but clear. Institutional but alive.
- Founder-led but not self-promotional.
- Slightly cinematic when discussing cities and buildings.
- No empty LinkedIn guru language.
- No generic AI phrasing.
- No bland congratulations.

The essay must contain:
1. A sharp two-line hook.
2. A clear thesis.
3. Specific details from the deal or article.
4. Broader interpretation for CRE.
5. A 2026 market-cycle connection.
6. A capital stack insight.
7. A city/future-of-real-estate insight.
8. Ben's operator judgment.
9. A soft Light Tower Group reference only if natural.
10. A strong closing line.

Avoid these phrases:
Excited to share, thrilled to announce, testament to, game changer, unlocking value,
navigating uncertainty, today's dynamic market, robust, transformative, blueprint,
congratulations to the teams, thoughts?

Preferred sentence patterns:
- The real story is not X. It is Y.
- This is not only a deal story. It is a capital markets story.
- The market is not short of capital. It is short of conviction.
- The question is no longer whether capital exists. The question is where it has permission to move.
- In this cycle, structure matters more than enthusiasm.
- The capital stack is becoming the real architecture of the deal.
- The future of cities will be shaped by the deals that can actually pencil.

Before writing, answer internally:
What is the visible deal? What is the hidden structure? What changed in the market?
Why does this matter in 2026? Who should care? What does this say about capital?
What does this say about cities? What would a smart sponsor, lender, or family office notice?
What is Ben's opinion? What is the memorable final sentence?

Return only valid JSON. No markdown. No prose outside the JSON.
"""


ESSAY_USER_TEMPLATE = """\
LIGHT TOWER INSIGHT

Title: {title}
Subtitle/excerpt: {excerpt}
Category: {category}
Tags: {tags}
Insight URL: {insight_url}
Date: {date}

ARTICLE TEXT

{article_text}

TASK

Produce a complete LinkedIn Essay Desk package.

Choose one archetype:
- Deal-as-signal
- Capital stack
- Future of cities
- Distress-before-headline
- Founder-operator

Length mode: {length_mode}
Character target for linkedin_essay:
- standard: 2400 to 2700 characters
- edge: 2750 to 2950 characters
- compressed: 1500 to 1900 characters

Output this exact JSON shape:
{{
  "title": "Short internal title/headline for the LinkedIn essay",
  "archetype": "One of the five archetypes",
  "technical_summary": ["5 concise bullets"],
  "hidden_thesis": "One sentence naming the deeper market thesis",
  "linkedin_essay": "The finished LinkedIn essay with line breaks. No hashtags. No URL. Stay under 2950 characters.",
  "alternate_hooks": ["10 opening hooks"],
  "strong_closing_lines": ["5 possible final lines"],
  "first_comment": "A natural first comment that links to the full Light Tower Insight at {insight_url}",
  "visual_recommendation": {{
    "type": "Text only | Deal image | Map | Capital stack diagram | Screenshot of Light Tower Insight | Underwriting chart | AI platform screenshot",
    "rationale": "Why this visual fits the post"
  }},
  "follow_up_comment": "A thoughtful follow-up comment for the thread",
  "dm_follow_up": "A direct-message follow-up for serious engagers",
  "quality_score": {{
    "hook_strength": 0,
    "dwell_time_potential": 0,
    "specificity": 0,
    "opinion_strength": 0,
    "capital_markets_insight": 0,
    "city_future_cre_insight": 0,
    "ben_voice": 0,
    "anti_ai_feel": 0,
    "conversion_potential": 0,
    "overall": 0
  }}
}}

Revise before returning until every quality score is at least 8.
"""


def strip_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    return parser.text()


def article_text_from_html(slug: str) -> str:
    path = INSIGHTS_DIR / f"{slug}.html"
    if not path.exists():
        return ""
    return strip_html(path.read_text(encoding="utf-8", errors="replace"))


def insight_url(article: dict[str, Any], site_url: str = SITE_URL) -> str:
    url = article.get("url") or f"/insights/{article.get('slug', '')}.html"
    if url.startswith("http"):
        return url
    return f"{site_url}{url}"


def _coerce_scores(package: dict[str, Any]) -> None:
    scores = package.setdefault("quality_score", {})
    score_keys = [
        "hook_strength",
        "dwell_time_potential",
        "specificity",
        "opinion_strength",
        "capital_markets_insight",
        "city_future_cre_insight",
        "ben_voice",
        "anti_ai_feel",
        "conversion_potential",
    ]
    vals = []
    for key in score_keys:
        try:
            val = int(scores.get(key, 0))
        except Exception:
            val = 0
        val = max(0, min(val, 10))
        scores[key] = val
        vals.append(val)
    scores["overall"] = max(0, min(int(scores.get("overall") or round(sum(vals) / len(vals))), 10))


def loads_model_json(raw_json: str) -> dict[str, Any]:
    """
    Parse model JSON with a small repair pass for common harmless syntax slips.

    The Essay Desk asks for strict JSON, but models occasionally leave a trailing
    comma before a closing object/array. Repair only that narrow case.
    """
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", raw_json)
        return json.loads(repaired)


def _fallback_package(article: dict[str, Any], site_url: str = SITE_URL) -> dict[str, Any]:
    url = insight_url(article, site_url)
    title = article.get("title", "Light Tower Insight")
    excerpt = article.get("excerpt") or article.get("subtitle") or ""
    essay = (
        f"The real story is not only the headline.\n"
        f"It is what the structure says about capital.\n\n"
        f"{title}\n\n"
        f"{excerpt}\n\n"
        "In this cycle, the question is no longer whether capital exists. "
        "The question is where it has permission to move.\n\n"
        "That is the lens I am using at Light Tower Group: not only which deals happen, "
        "but what they reveal about basis, lender selectivity, policy, and the future of cities.\n\n"
        "The headline is the project. The story is the structure."
    )
    return {
        "title": title,
        "archetype": "Deal-as-signal",
        "technical_summary": [excerpt or title],
        "hidden_thesis": "The deal matters because it reveals how capital is repricing structure in 2026.",
        "linkedin_essay": essay[:2950],
        "alternate_hooks": [
            "The real story is not the headline. It is the capital structure.",
            "In this cycle, structure matters more than enthusiasm.",
        ],
        "strong_closing_lines": ["The headline is the project. The story is the structure."],
        "first_comment": f"Full Light Tower Insight here: {url}",
        "visual_recommendation": {
            "type": "Screenshot of Light Tower Insight",
            "rationale": "The Insight page reinforces the technical source beneath the opinion essay.",
        },
        "follow_up_comment": "The part I would underwrite first is not the headline metric. It is the structure beneath it.",
        "dm_follow_up": "Appreciate you reading this. If you are seeing a similar structure, I would be interested in how your lender or equity partner is underwriting it.",
        "quality_score": {
            "hook_strength": 7,
            "dwell_time_potential": 7,
            "specificity": 6,
            "opinion_strength": 7,
            "capital_markets_insight": 7,
            "city_future_cre_insight": 6,
            "ben_voice": 7,
            "anti_ai_feel": 7,
            "conversion_potential": 7,
            "overall": 7,
        },
    }


def generate_essay_package(
    article: dict[str, Any],
    *,
    article_text: str | None = None,
    length_mode: str = "standard",
    api_key: str | None = None,
    site_url: str = SITE_URL,
) -> dict[str, Any]:
    api_key = api_key if api_key is not None else DEEPSEEK_API_KEY
    url = insight_url(article, site_url)
    text = (article_text or article.get("body_text") or "").strip()
    if not text and article.get("body_html"):
        text = strip_html(article["body_html"])
    if not text and article.get("slug"):
        text = article_text_from_html(article["slug"])
    if not text:
        text = article.get("excerpt") or article.get("subtitle") or article.get("title", "")
    text = text[:7000]

    if not api_key:
        return decorate_package(_fallback_package(article, site_url), article, url, length_mode, fallback=True)

    prompt = ESSAY_USER_TEMPLATE.format(
        title=article.get("title", ""),
        excerpt=article.get("excerpt") or article.get("subtitle") or article.get("meta_description", ""),
        category=article.get("category", ""),
        tags=", ".join(article.get("tags", []) or []),
        insight_url=url,
        date=article.get("date", ""),
        article_text=text,
        length_mode=length_mode,
    )

    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "deepseek-chat",
            "max_tokens": 5200,
            "temperature": 0.45,
            "messages": [
                {"role": "system", "content": ESSAY_SYSTEM_PROMPT},
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
        raise ValueError("No JSON object found in Essay Desk response")
    package = loads_model_json(match.group())
    return decorate_package(package, article, url, length_mode)


def decorate_package(
    package: dict[str, Any],
    article: dict[str, Any],
    url: str,
    length_mode: str,
    *,
    fallback: bool = False,
) -> dict[str, Any]:
    essay = (package.get("linkedin_essay") or "").strip()
    if len(essay) > 2950:
        package["linkedin_essay"] = essay[:2920].rstrip() + "\n\n[Cut before posting.]"
    package["slug"] = article.get("slug", "")
    package["insight_title"] = article.get("title", "")
    package["insight_url"] = url
    package["length_mode"] = length_mode
    package["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    package["agent"] = "Light Tower CRE Essay Desk"
    package["fallback"] = fallback
    _coerce_scores(package)
    return package


def save_to_queue(package: dict[str, Any], queue_path: Path = ESSAY_QUEUE) -> None:
    assert_no_mojibake("essay package", package)
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
    queue_json = json.dumps(queue, indent=2, ensure_ascii=False)
    assert_no_mojibake("essay queue", queue_json)
    queue_path.write_text(queue_json, encoding="utf-8")


def load_manifest() -> list[dict[str, Any]]:
    if not INSIGHTS_JSON.exists():
        return []
    return json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))


def select_article(slug: str | None = None) -> dict[str, Any]:
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
    parser = argparse.ArgumentParser(description="Light Tower CRE Essay Desk")
    parser.add_argument("--slug", help="Generate for a specific Insight slug")
    parser.add_argument("--latest", action="store_true", help="Generate for latest insight")
    parser.add_argument("--length", choices=["standard", "edge", "compressed"], default="standard")
    parser.add_argument("--no-api", action="store_true", help="Use deterministic fallback output without calling DeepSeek")
    parser.add_argument("--dry-run", action="store_true", help="Print package without saving")
    args = parser.parse_args()

    article = select_article(args.slug)
    try:
        package = generate_essay_package(
            article,
            length_mode=args.length,
            api_key="" if args.no_api else None,
        )
    except Exception as e:
        print(f"[WARN] Essay Desk API generation failed: {e}", file=sys.stderr)
        print("[WARN] Falling back to deterministic package.", file=sys.stderr)
        package = generate_essay_package(article, length_mode=args.length, api_key="")
    if args.dry_run:
        print(json.dumps(package, indent=2, ensure_ascii=False))
    else:
        save_to_queue(package)
        print(f"Saved Essay Desk package for {package.get('slug')} -> {ESSAY_QUEUE}")
        print(package.get("linkedin_essay", "")[:500])


if __name__ == "__main__":
    main()
