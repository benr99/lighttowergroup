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

from editorial_voice import (
    NARRATIVE_FINANCE_ADDENDUM,
    VOICE_SYSTEM_ADDENDUM,
    contains_mojibake,
    editorial_quality_issues,
    load_recent_packages,
    narrative_finance_issues,
    select_editorial_brief,
)


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
ESSAY_QUEUE = SITE_ROOT / "linkedin_essay_queue.json"
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


def assert_no_mojibake(label: str, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    if contains_mojibake(text):
        match = re.search(r"(?:â€|â€”|â†|âœ|Ãƒ|Ã¢|�)", text)
        start = max((match.start() if match else 0) - 40, 0)
        end = min((match.end() if match else 1) + 40, len(text))
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


ESSAY_SYSTEM_PROMPT = f"""\
You are the Light Tower CRE Essay Desk. You write source-grounded LinkedIn
essays for Ben Rohr, founder of Light Tower Group, at the intersection of
commercial real estate, debt and equity placement, distressed assets, housing
policy, and the future of cities.

Your task is interpretation, not recap. A useful essay identifies the pressure
inside a fact: the basis that must clear, the lender constraint, the time risk,
or the conflict between a building's promise and its financing. It has one
defensible point of view. It does not pretend that one transaction proves an
entire market thesis.

Write for sophisticated owners, sponsors, lenders, capital partners, and
operators. Assume they are busy, have seen hundreds of generic market posts,
and will reward a precise observation or a fair disagreement. Make the opening
two lines earn attention, but do not use shock language, engagement bait, or a
formulaic contrast. Use short paragraphs with varied cadence. Preserve nuance
when the source is thin. Treat every party in a transaction with respect.

The essay must contain a factual anchor, an interpretation, and a practical
implication. It may include a personal read, but only when that judgment is
explained and never as a claim of firsthand involvement. A natural first comment
can link to the source Insight; the body itself has no URL or hashtags.

{VOICE_SYSTEM_ADDENDUM}

{NARRATIVE_FINANCE_ADDENDUM}

Return only valid JSON. No markdown or prose outside the JSON.
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

EDITORIAL BRIEF
{editorial_brief_json}

TASK

Produce a complete LinkedIn Essay Desk package that follows the editorial brief.
The assigned voice mode is a compositional constraint, not a label to repeat in
the finished post. Select a real stance that could be challenged by a thoughtful
CRE peer. Cite three or more facts from the supplied material in natural prose.

Build a narrative-finance ledger before writing. It must separate reported
facts, interpretations, and unresolved questions. If the essay uses a scene or
physical image, identify exactly what source detail supports it; otherwise set
scene.used to false. The ledger is internal control data and should not be
printed in the LinkedIn essay.

Do not use any of these repeated constructions: "the most important number is
not", "the real story", "this is not a story about", "who benefits", "who is
exposed", "in this cycle", or "the capital stack is becoming". Do not ask a
closing question unless the response would be useful to a lender, sponsor,
investor, or operator. Do not manufacture Ben's personal involvement.

Length mode: {length_mode}
Character target for linkedin_essay:
- standard: 2400 to 2700 characters
- edge: 2750 to 2950 characters
- compressed: 1500 to 1900 characters

Output this exact JSON shape:
{{
  "title": "Short internal title/headline for the LinkedIn essay",
  "voice_mode": "Exactly the assigned voice mode",
  "editorial_stance": "A source-grounded, arguable point of view in one sentence",
  "opening_move": "A concise description of how the first two lines work",
  "fact_anchors": ["3 to 5 exact facts or attributable details used in the essay"],
  "narrative_ledger": {{
    "anchor": "The reported deal, number, filing, building, or policy fact.",
    "tension": "The economically consequential pressure or contradiction.",
    "cast": ["Party: its need, constraint, or clock"],
    "mechanism": "The basis, debt, liquidity, regulation, or operating mechanism.",
    "claim": "A bounded, source-grounded interpretation.",
    "reader_consequence": "What a market participant should test next.",
    "reported_facts": ["Source-supported fact"],
    "interpretations": ["Clearly marked inference"],
    "open_questions": ["Unresolved question the source cannot establish"],
    "scene": {{"used": false, "detail": "", "source_basis": ""}}
  }},
  "technical_summary": ["5 concise bullets"],
  "hidden_thesis": "One sentence naming the deeper market thesis",
  "linkedin_essay": "The finished LinkedIn essay with line breaks. No hashtags or URL. Finish complete; stay inside the target rather than cutting.",
  "alternate_hooks": ["5 structurally different opening hooks"],
  "strong_closing_lines": ["3 possible final lines"],
  "first_comment": "A natural first comment that links to the full Light Tower Insight at {insight_url}",
  "visual_recommendation": {{
    "type": "Text only | Deal image | Map | Capital stack diagram | Screenshot of Light Tower Insight | Underwriting chart | AI platform screenshot",
    "rationale": "Why this visual fits the post"
  }},
  "follow_up_comment": "A thoughtful follow-up comment for the thread",
  "dm_follow_up": "A direct-message follow-up for serious engagers",
  "comment_question": "A specific optional question for the comments, or an empty string if no genuine question fits",
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

Revise for specificity and rhythm before returning. Scores are self-assessments;
they do not override the independent editorial review.
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


def _extract_model_package(raw: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON object found in Essay Desk response")
    return loads_model_json(match.group())


def _revision_prompt(
    package: dict[str, Any], issues: list[str], editorial_brief: dict[str, str]
) -> str:
    return """\
The draft below failed independent editorial review. Rewrite the COMPLETE JSON
package, preserving only source-grounded facts. Correct every listed issue.

Do not explain the revision. Return valid JSON only. Do not use prohibited
template language, do not shorten by cutting a sentence mid-thought, and do not
invent personal involvement or new facts. Retain the assigned voice mode.

ASSIGNED EDITORIAL BRIEF
{brief}

REQUIRED CORRECTIONS
{issues}

CURRENT PACKAGE
{package}
""".format(
        brief=json.dumps(editorial_brief, ensure_ascii=False),
        issues=json.dumps(issues, ensure_ascii=False),
        package=json.dumps(package, ensure_ascii=False),
    )


def _fallback_package(
    article: dict[str, Any], editorial_brief: dict[str, str], site_url: str = SITE_URL
) -> dict[str, Any]:
    url = insight_url(article, site_url)
    title = article.get("title", "Light Tower Insight")
    excerpt = article.get("excerpt") or article.get("subtitle") or ""
    essay = (
        "EDITORIAL REVIEW REQUIRED\n\n"
        f"The automated Essay Desk could not produce a publishable draft for: {title}.\n\n"
        f"Source note: {excerpt}\n\n"
        "Use the source Insight and the assigned editorial brief to write a fresh post. "
        "Do not publish this placeholder."
    )
    return {
        "title": title,
        "voice_mode": editorial_brief["name"],
        "editorial_stance": editorial_brief["stance"],
        "opening_move": editorial_brief["opening_move"],
        "fact_anchors": [excerpt or title],
        "narrative_ledger": {
            "anchor": title,
            "tension": "No automated narrative interpretation is approved when the Essay Desk call fails.",
            "cast": ["Editorial review: a human editor must supply the source-grounded analysis."],
            "mechanism": "Unavailable until a source-grounded draft is written.",
            "claim": "No automated claim is approved.",
            "reader_consequence": "Hold for editorial review.",
            "reported_facts": [excerpt or title],
            "interpretations": ["No interpretation is approved in a fallback."],
            "open_questions": ["What source-backed mechanism should the draft explain?"],
            "scene": {"used": False, "detail": "", "source_basis": ""},
        },
        "technical_summary": [excerpt or title],
        "hidden_thesis": "No automated thesis is approved when the Essay Desk call fails.",
        "linkedin_essay": essay[:2950],
        "alternate_hooks": [
            "Write a fresh source-grounded opening after reviewing the Insight.",
        ],
        "strong_closing_lines": ["Finish with the decision implication, not a slogan."],
        "first_comment": f"Full Light Tower Insight here: {url}",
        "visual_recommendation": {
            "type": "Screenshot of Light Tower Insight",
            "rationale": "Hold this package for an editor before selecting a visual.",
        },
        "follow_up_comment": "Hold for editorial review.",
        "dm_follow_up": "Hold for editorial review.",
        "comment_question": "",
        "quality_score": {
            "hook_strength": 0,
            "dwell_time_potential": 0,
            "specificity": 0,
            "opinion_strength": 0,
            "capital_markets_insight": 0,
            "city_future_cre_insight": 0,
            "ben_voice": 0,
            "anti_ai_feel": 0,
            "conversion_potential": 0,
            "overall": 0,
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
    editorial_brief = select_editorial_brief(
        article, load_recent_packages(ESSAY_QUEUE)
    )
    text = (article_text or article.get("body_text") or "").strip()
    if not text and article.get("body_html"):
        text = strip_html(article["body_html"])
    if not text and article.get("slug"):
        text = article_text_from_html(article["slug"])
    if not text:
        text = article.get("excerpt") or article.get("subtitle") or article.get("title", "")
    text = text[:7000]

    if not api_key:
        return decorate_package(
            _fallback_package(article, editorial_brief, site_url),
            article,
            url,
            length_mode,
            editorial_brief,
            fallback=True,
        )

    prompt = ESSAY_USER_TEMPLATE.format(
        title=article.get("title", ""),
        excerpt=article.get("excerpt") or article.get("subtitle") or article.get("meta_description", ""),
        category=article.get("category", ""),
        tags=", ".join(article.get("tags", []) or []),
        insight_url=url,
        date=article.get("date", ""),
        article_text=text,
        length_mode=length_mode,
        editorial_brief_json=json.dumps(editorial_brief, ensure_ascii=False, indent=2),
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
    package = _extract_model_package(resp.json()["choices"][0]["message"]["content"])
    decorated = decorate_package(package, article, url, length_mode, editorial_brief)
    if decorated["editorial_review"]["status"] == "ready_for_review":
        return decorated

    try:
        revision = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "max_tokens": 5200,
                "temperature": 0.25,
                "messages": [
                    {"role": "system", "content": ESSAY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {
                        "role": "user",
                        "content": _revision_prompt(
                            package,
                            decorated["editorial_review"]["issues"],
                            editorial_brief,
                        ),
                    },
                ],
            },
            timeout=120,
        )
        revision.raise_for_status()
        corrected = _extract_model_package(revision.json()["choices"][0]["message"]["content"])
        decorated = decorate_package(corrected, article, url, length_mode, editorial_brief)
    except (requests.RequestException, ValueError, KeyError, IndexError):
        decorated["revision_error"] = "revision attempt failed; draft remains held"
    decorated["revision_attempts"] = 1
    return decorated


def decorate_package(
    package: dict[str, Any],
    article: dict[str, Any],
    url: str,
    length_mode: str,
    editorial_brief: dict[str, str],
    *,
    fallback: bool = False,
) -> dict[str, Any]:
    essay = (package.get("linkedin_essay") or "").strip()
    issues = editorial_quality_issues(essay)
    issues.extend(narrative_finance_issues(package.get("narrative_ledger")))
    for field in ("alternate_hooks", "strong_closing_lines"):
        variants = package.get(field)
        if not isinstance(variants, list):
            continue
        package[field] = [
            value
            for value in variants
            if isinstance(value, str)
            and not editorial_quality_issues(value, min_characters=1)
        ]
    if len(essay) > 2950:
        issues.append("draft exceeds LinkedIn's 2,950-character publishing limit")
    if fallback:
        issues.append("automated fallback is never publishable")
    if package.get("voice_mode") != editorial_brief["name"]:
        issues.append("draft did not follow its assigned editorial mode")

    package["voice_mode"] = editorial_brief["name"]
    package["editorial_brief"] = editorial_brief
    package["slug"] = article.get("slug", "")
    package["insight_title"] = article.get("title", "")
    package["insight_url"] = url
    package["length_mode"] = length_mode
    package["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    package["agent"] = "Light Tower CRE Essay Desk"
    package["fallback"] = fallback
    _coerce_scores(package)
    issues = list(dict.fromkeys(issues))
    package["editorial_review"] = {
        "status": "ready_for_review" if not issues else "needs_revision",
        "issues": issues,
        "independent_checks": True,
    }
    package["publish_ready"] = not issues
    return package


def save_to_queue(package: dict[str, Any], queue_path: Path = ESSAY_QUEUE) -> None:
    assert_no_mojibake("essay package", package)
    if not package.get("publish_ready"):
        raise ValueError("only independently approved Essay Desk packages may enter the publishing queue")
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
