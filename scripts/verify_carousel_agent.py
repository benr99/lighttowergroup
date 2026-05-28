"""
Offline verification for the DeepSeek carousel PDF writer.

Runs without network access. It verifies fallback behavior, mock model output
normalization, fact-safety rejection, and LinkedIn companion copy.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from article_adapter import transform_article_to_pdf_schema
from build_linkedin_post import build_linkedin_post_text
from carousel_script_agent import (
    generate_carousel_script,
    normalize_carousel_schema,
    validate_fact_safety,
    validate_slides,
)
from fetch_brand_colors import FALLBACK_COLORS
from generate_carousel_pdf import CarouselPDFGenerator
from validate_pdf import run_validation_report


SLUG = "fertitta-caesars-17-6b-acquisition"


def load_article(slug: str = SLUG) -> tuple[str, dict]:
    html = (ROOT / "insights" / f"{slug}.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))
    item = next(entry for entry in manifest if entry["slug"] == slug)
    match = re.search(r'<div class="article-body" itemprop="articleBody">([\s\S]*?)</div>', html)
    body = match.group(1) if match else html
    data = dict(item)
    data["body"] = body
    data["body_html"] = body
    data["title"] = item.get("title") or item.get("headline")
    return body, data


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_fallback_schema(body: str, data: dict) -> dict:
    fallback = transform_article_to_pdf_schema(body, data)
    schema = generate_carousel_script(body, data, fallback, api_key="")
    assert_true(schema.get("carousel_agent", {}).get("fallback") is True, "Fallback flag missing")
    warnings = validate_slides(schema["slides"])
    assert_true(isinstance(warnings, list), "Slide validation did not return warnings")
    return schema


def verify_mock_normalization(body: str, data: dict, fallback: dict) -> dict:
    article_text = re.sub(r"<[^>]+>", " ", body)
    mock = {
        "slides": [
            {
                "system": "hero",
                "headline": "Fertitta takes Caesars private",
                "subhead": (
                    "Tilman Fertitta is using private control and a large balance sheet "
                    "to absorb Caesars at a price public markets could not ignore."
                ),
                "figures": [{"number": "$17.6 billion", "label": "Transaction value"}],
            },
            {
                "system": "data",
                "headline": "The debt is part of the price",
                "figures": [
                    {"number": "$17.6 billion", "label": "Transaction value"},
                    {"number": "$11.9 billion", "label": "Debt assumed"},
                    {"number": "$31", "label": "Offer price"},
                ],
            },
            *[
                {
                    "system": "story",
                    "headline": f"Private capital changes the read {i}",
                    "subhead": (
                        "The story is not only the acquisition price. It is the way "
                        "control, leverage, and timing move when one buyer can act "
                        "without waiting for a syndicated capital market."
                    ),
                }
                for i in range(1, 8)
            ],
            {
                "system": "kicker",
                "headline": "Why it matters",
                "subhead": (
                    "The transaction shows how private balance sheets can still move "
                    "when public markets are slower, more selective, and more exposed "
                    "to rate pressure."
                ),
            },
        ]
    }
    schema = normalize_carousel_schema(mock, fallback, article_text)
    assert_true(8 <= len(schema["slides"]) <= 14, "Mock schema slide count invalid")
    assert_true(schema["slides"][0]["system"] == "hero", "Mock schema missing hero")
    assert_true(schema["slides"][1]["system"] == "data", "Mock schema missing data slide")
    assert_true(schema["slides"][-1]["system"] == "kicker", "Mock schema missing kicker")
    assert_true(schema["slides"][-1]["eyebrow"] == "WHY IT MATTERS", "Mock schema closing eyebrow invalid")
    return schema


def verify_fact_safety_rejects_new_facts(fallback: dict, body: str) -> None:
    bad_slides = [
        {
            "system": "hero",
            "headline": "Blackstone buys Caesars for $99 billion",
            "subhead": "Blackstone entered the process with a new bid that was not in the article.",
            "figures": [{"number": "$99 billion", "label": "Unsupported figure"}],
        },
        {
            "system": "data",
            "headline": "Unsupported figures",
            "subhead": "",
            "figures": [{"number": "$99 billion", "label": "Unsupported figure"}],
        },
        *[
            {
                "system": "story",
                "headline": f"Unsupported story {i}",
                "subhead": "This slide has enough words to pass length checks but includes Blackstone.",
                "figures": [],
            }
            for i in range(1, 7)
        ],
        {
            "system": "kicker",
            "headline": "Why it matters",
            "subhead": "The unsupported Blackstone claim should force fact-safety rejection.",
            "figures": [],
        },
    ]
    try:
        validate_fact_safety(bad_slides, fallback, re.sub(r"<[^>]+>", " ", body))
    except ValueError:
        return
    raise AssertionError("Fact safety failed to reject unsupported output")


async def verify_pdf_render(schema: dict) -> None:
    output = ROOT / "tmp_carousel_verify.pdf"
    try:
        ok = await CarouselPDFGenerator(FALLBACK_COLORS).generate_pdf(schema, str(output))
        assert_true(ok, "PDF render failed")
        report = run_validation_report(str(output), schema)
        assert_true(report["valid"], f"PDF validation failed: {report['errors']}")
    finally:
        if output.exists():
            output.unlink()


def verify_linkedin_post(schema: dict) -> None:
    post = build_linkedin_post_text(schema)
    lower = post.lower()
    assert_true("five stories" not in lower, "LinkedIn post still says five stories")
    assert_true("five institutional capital developments" not in lower, "LinkedIn post has old hook")
    assert_true("attached carousel" in lower, "LinkedIn post does not reference attached carousel")


async def main() -> None:
    body, data = load_article()
    fallback = verify_fallback_schema(body, data)
    mock_schema = verify_mock_normalization(body, data, fallback)
    verify_fact_safety_rejects_new_facts(fallback, body)
    verify_linkedin_post(mock_schema)
    await verify_pdf_render(mock_schema)
    print("carousel agent verification passed")


if __name__ == "__main__":
    asyncio.run(main())
