"""A/B testing variant assignment for Light Tower articles.

Assigns 15% of articles to variant conditions (different headline, CTA placement).
Tracks performance for statistical analysis.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
VARIANTS_PATH = SITE_ROOT / ".editorial-state" / "article-variants.json"

HEADLINE_VARIANTS = {
    "control": "standard_headline",
    "question": "rephrase_as_genuine_question",
    "number_first": "lead_with_the_number",
}

CTA_VARIANTS = {
    "control": "standard_bottom_cta",
    "inline": "inline_mid_article_cta",
    "none": "no_cta",
}


def assign_variant(article_slug: str, variant_type: str) -> str:
    """Deterministic variant assignment: ~15% non-control."""
    seed = f"{article_slug}-{variant_type}-v1"
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    r = (hash_val % 100) / 100.0

    if variant_type == "headline":
        if r < 0.08:
            return "question"
        if r < 0.15:
            return "number_first"
        return "control"
    elif variant_type == "cta":
        if r < 0.08:
            return "inline"
        if r < 0.15:
            return "none"
        return "control"
    return "control"


def get_variant_instruction(variant_type: str, variant_value: str) -> str:
    """Return the LLM instruction for this variant."""
    if variant_type == "headline":
        instructions = {
            "control": "Write a strong, specific headline following the selected headline shape.",
            "question": "Write the headline as a genuine, specific question the article answers. Start with 'What', 'Why', 'How', or 'Is'. Do not make it rhetorical.",
            "number_first": "Lead the headline with the most important number. Start with the dollar amount, percentage, or year.",
        }
        return instructions.get(variant_value, instructions["control"])
    elif variant_type == "cta":
        instructions = {
            "control": "Include a standard 'Request a Deal Review' CTA at the bottom of the article.",
            "inline": "Include a one-sentence CTA in the middle of the article, after the second section: 'Have a deal that needs this lens? Contact Light Tower Group.'",
            "none": "Do not include any CTA in this article.",
        }
        return instructions.get(variant_value, instructions["control"])
    return ""


def save_variant_record(article: dict[str, Any]) -> dict[str, Any]:
    """Record variant assignments for this article."""
    slug = article.get("slug", "")
    headline_variant = assign_variant(slug, "headline")
    cta_variant = assign_variant(slug, "cta")

    record = {
        "slug": slug,
        "title": article.get("title"),
        "date": article.get("date") or str(datetime.now(timezone.utc).date()),
        "headline_variant": headline_variant,
        "cta_variant": cta_variant,
        "headline_instruction": get_variant_instruction("headline", headline_variant),
        "cta_instruction": get_variant_instruction("cta", cta_variant),
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }

    VARIANTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    try:
        existing = json.loads(VARIANTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    if not isinstance(existing, list):
        existing = []
    existing.append(record)
    VARIANTS_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    return record


def compute_variant_stats() -> dict[str, Any]:
    """Compute performance statistics across all tracked variants."""
    try:
        records = json.loads(VARIANTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"error": "No variant data available"}

    if not isinstance(records, list):
        return {"error": "Invalid variant data"}

    headline_counts = {"control": 0, "question": 0, "number_first": 0}
    cta_counts = {"control": 0, "inline": 0, "none": 0}

    for r in records:
        h = r.get("headline_variant", "control")
        c = r.get("cta_variant", "control")
        headline_counts[h] = headline_counts.get(h, 0) + 1
        cta_counts[c] = cta_counts.get(c, 0) + 1

    total = max(1, len(records))
    return {
        "total_articles_tracked": total,
        "headline_distribution": headline_counts,
        "cta_distribution": cta_counts,
        "headline_control_pct": round(headline_counts.get("control", 0) / total * 100, 1),
        "cta_control_pct": round(cta_counts.get("control", 0) / total * 100, 1),
        "recommendation": "Need at least 40 articles per variant for statistical significance. Continue collecting.",
    }


if __name__ == "__main__":
    stats = compute_variant_stats()
    print(json.dumps(stats, indent=2))
