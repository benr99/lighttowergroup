"""Sector-aware article generation for the Light Tower multi-sector pipeline.

Routes classified and scored stories to the appropriate writing prompt
based on their primary sector. Handles article type selection, voice mode
assignment, quality gate checking, and generation statistics.

The module is designed to integrate with the existing generate_article()
function in daily_news_agent.py — it provides the prompt routing and
context-building layer without duplicating the LLM call infrastructure.
"""

from __future__ import annotations
from typing import Any

from canonical_item import CanonicalItem
from sector_prompts import (
    PE_SYSTEM_PROMPT,
    DC_SYSTEM_PROMPT,
    ENERGY_SYSTEM_PROMPT,
    BANKING_SYSTEM_PROMPT,
    FED_SYSTEM_PROMPT,
    LOCALGOV_SYSTEM_PROMPT,
)

# ── Prompt routing ─────────────────────────────────────────────────────

SECTOR_PROMPTS: dict[str, str] = {
    "private_equity": PE_SYSTEM_PROMPT,
    "data_centers": DC_SYSTEM_PROMPT,
    "energy": ENERGY_SYSTEM_PROMPT,
    "banking_credit": BANKING_SYSTEM_PROMPT,
    "fed_macro": FED_SYSTEM_PROMPT,
    "local_government": LOCALGOV_SYSTEM_PROMPT,
    # commercial_real_estate uses SYSTEM_PROMPT_ENHANCED from enhanced_prompts.py
}

SECTOR_LABELS: dict[str, str] = {
    "private_equity": "Private Equity",
    "data_centers": "Data Centers",
    "energy": "Energy",
    "banking_credit": "Banking & Credit",
    "fed_macro": "Fed & Macro",
    "local_government": "Local Government",
    "commercial_real_estate": "Commercial Real Estate",
}

SECTOR_CATEGORIES: dict[str, str] = {
    "private_equity": "Deal Intelligence",
    "data_centers": "Market Analysis",
    "energy": "Market Analysis",
    "banking_credit": "Debt & Equity",
    "fed_macro": "Policy & Regulation",
    "local_government": "Policy & Regulation",
    "commercial_real_estate": "Capital Markets",
}

# ── Article type routing ───────────────────────────────────────────────

ARTICLE_TYPES: dict[str, str] = {
    # Private equity
    "fund_close": "fundraising_analysis",
    "fund_launch": "fundraising_analysis",
    "buyout": "transaction_brief",
    "exit_sale": "exit_analysis",
    "dividend_recap": "transaction_brief",
    "continuation_vehicle": "transaction_brief",
    "gp_stake_sale": "transaction_brief",
    "take_private": "transaction_brief",
    "growth_equity": "transaction_brief",
    "add_on_acquisition": "deal_analysis",
    "sponsor_acquisition": "deal_analysis",
    "sponsor_to_sponsor": "deal_analysis",
    # Data centers
    "dc_development": "development_brief",
    "dc_lease": "lease_analysis",
    "dc_acquisition": "deal_analysis",
    "dc_power_agreement": "energy_brief",
    # Energy
    "power_agreement": "energy_brief",
    "project_finance": "deal_analysis",
    "ppa_signing": "energy_brief",
    "plant_development": "development_brief",
    "plant_acquisition": "deal_analysis",
    "regulatory_decision": "policy_analysis",
    "rate_case": "policy_analysis",
    "interconnection_approval": "energy_brief",
    # Banking / credit
    "bank_earnings": "data_note",
    "loan_origination": "transaction_brief",
    "loan_sale": "deal_analysis",
    "credit_event": "deal_analysis",
    "regulatory_action": "policy_analysis",
    "enforcement_action": "policy_analysis",
    "private_credit_deal": "transaction_brief",
    # Fed / macro
    "fomc_decision": "macro_brief",
    "fomc_minutes": "macro_brief",
    "inflation_report": "data_note",
    "employment_report": "data_note",
    "gdp_report": "data_note",
    "treasury_auction": "macro_brief",
    "fed_speech": "macro_brief",
    # Local government
    "rezoning_decision": "local_impact_analysis",
    "development_approval": "development_brief",
    "tax_abatement": "local_impact_analysis",
    "building_code_update": "policy_analysis",
    "permit_decision": "development_brief",
    "city_council_vote": "local_impact_analysis",
    "state_legislation": "policy_analysis",
    # General
    "property_acquisition": "deal_analysis",
    "portfolio_acquisition": "deal_analysis",
}

ARTICLE_TYPE_LABELS: dict[str, str] = {
    "deal_analysis": "Deal Analysis",
    "transaction_brief": "Transaction Brief",
    "fundraising_analysis": "Fundraising Analysis",
    "exit_analysis": "Exit Analysis",
    "development_brief": "Development Brief",
    "lease_analysis": "Lease Analysis",
    "energy_brief": "Energy Brief",
    "policy_analysis": "Policy Analysis",
    "macro_brief": "Macro Brief",
    "data_note": "Data Note",
    "local_impact_analysis": "Local Impact Analysis",
    "general": "Market Analysis",
}

# ── Word count specs ───────────────────────────────────────────────────

WORD_COUNTS: dict[str, dict[str, int]] = {
    "deal_analysis": {"min": 450, "max": 800},
    "transaction_brief": {"min": 250, "max": 450},
    "fundraising_analysis": {"min": 400, "max": 700},
    "exit_analysis": {"min": 350, "max": 650},
    "development_brief": {"min": 250, "max": 450},
    "lease_analysis": {"min": 250, "max": 450},
    "energy_brief": {"min": 250, "max": 500},
    "policy_analysis": {"min": 350, "max": 650},
    "macro_brief": {"min": 300, "max": 550},
    "data_note": {"min": 180, "max": 350},
    "local_impact_analysis": {"min": 300, "max": 550},
    "general": {"min": 250, "max": 500},
}

# ── Category to expected word ranges (higher-level grouping) ───────────

CATEGORY_WORD_RANGES: dict[str, dict[str, int]] = {
    "Deal Intelligence": {"min": 400, "max": 800},
    "Debt & Equity": {"min": 350, "max": 650},
    "Capital Markets": {"min": 350, "max": 700},
    "Market Analysis": {"min": 250, "max": 500},
    "Policy & Regulation": {"min": 300, "max": 650},
}


# ── Public API ─────────────────────────────────────────────────────────

def get_sector_prompt(sector: str) -> str:
    """Return the system prompt for a given sector.

    Falls back to importing SYSTEM_PROMPT_ENHANCED for
    commercial_real_estate and unknown/empty sectors. If that import fails,
    returns the private_equity prompt as a reasonable default.
    """
    if not sector or sector == "commercial_real_estate":
        try:
            from enhanced_prompts import SYSTEM_PROMPT_ENHANCED
            return SYSTEM_PROMPT_ENHANCED
        except ImportError:
            pass
        return SECTOR_PROMPTS.get("private_equity", "")
    return SECTOR_PROMPTS.get(
        sector,
        SECTOR_PROMPTS.get("private_equity", ""),
    )


def get_sector_label(sector: str) -> str:
    """Return a human-readable label for a sector key."""
    return SECTOR_LABELS.get(
        sector,
        sector.replace("_", " ").title(),
    )


def get_sector_category(sector: str) -> str:
    """Return the default article category for a sector."""
    return SECTOR_CATEGORIES.get(sector, "Capital Markets")


def get_article_type(item: CanonicalItem) -> str:
    """Determine the best article type for a story based on its event type.

    Falls back to 'general' if the event type is not mapped.
    """
    event = item.event_type or ""
    return ARTICLE_TYPES.get(event, "general")


def get_article_type_label(article_type: str) -> str:
    """Human-readable label for an article type."""
    return ARTICLE_TYPE_LABELS.get(article_type, article_type.replace("_", " ").title())


def get_word_count(article_type: str) -> dict[str, int]:
    """Return the {min, max} word counts for an article type."""
    return WORD_COUNTS.get(article_type, WORD_COUNTS["general"])


def get_category_word_range(category: str) -> dict[str, int]:
    """Return the expected word range for a category."""
    return CATEGORY_WORD_RANGES.get(
        category,
        CATEGORY_WORD_RANGES["Capital Markets"],
    )


# ── Context builder ────────────────────────────────────────────────────

def build_generation_context(item: CanonicalItem) -> dict[str, Any]:
    """Build the context dict needed for article generation.

    Extracts all relevant metadata from a CanonicalItem that the writing
    LLM needs: sector, event type, parties, amounts, geography, source
    information, and quality metadata.

    This dict is designed to be passed to generate_article() or its
    sector-aware equivalent.
    """
    article_type = get_article_type(item)
    wc = get_word_count(article_type)

    return {
        "headline": item.headline,
        "source_name": item.source_name,
        "source_url": item.source_url,
        "source_tier": item.source_tier,
        "publication_date": item.publication_date,
        "summary": item.raw_summary,
        "full_text": item.raw_text or item.raw_summary,
        # Sector
        "sector": item.primary_sector,
        "sector_label": get_sector_label(item.primary_sector),
        "sector_category": get_sector_category(item.primary_sector),
        "secondary_sectors": item.secondary_sectors,
        "subsector": item.subsector,
        # Event
        "event_type": item.event_type or "general",
        "article_type": article_type,
        "article_type_label": get_article_type_label(article_type),
        # Parties
        "companies": item.companies,
        "buyers": item.buyers,
        "sellers": item.sellers,
        "lenders": item.lenders,
        "developers": item.developers,
        "government_bodies": item.government_bodies,
        # Financials
        "transaction_value": item.transaction_value_raw or "",
        "debt_amount": str(item.debt_amount) if item.debt_amount else "",
        "fund_size": str(item.fund_size) if item.fund_size else "",
        "unit_count": item.unit_count,
        "square_footage": item.square_footage,
        "megawatts": item.megawatts,
        "property_type": item.property_type,
        # Geography
        "city": item.city,
        "state": item.state,
        "market": item.market,
        "property_address": item.property_address,
        # Scoring
        "composite_score": item.composite_score,
        "tier": item.tier,
        "must_read_score": getattr(item, "must_read_score", None),
        # Processing
        "item_id": item.item_id,
        "word_count_min": wc["min"],
        "word_count_max": wc["max"],
    }


def get_primary_prompt_for_item(item: CanonicalItem) -> str:
    """Return the primary system prompt for a CanonicalItem's sector.

    Convenience wrapper around get_sector_prompt that accepts an item.
    """
    return get_sector_prompt(item.primary_sector or "")


def get_secondary_prompts(item: CanonicalItem) -> list[str]:
    """Return system prompts for any secondary sectors on this item.

    Useful when a story crosses sectors (e.g. a data center energy deal
    touches both DC and energy domains).
    """
    prompts = []
    for sector in item.secondary_sectors:
        prompt = get_sector_prompt(sector)
        if prompt and prompt not in prompts:
            prompts.append(prompt)
    return prompts


# ── Statistics ─────────────────────────────────────────────────────────

def get_generation_stats(
    selected: dict[str, list[CanonicalItem]],
) -> dict[str, Any]:
    """Compute article generation statistics across all selected stories.

    Arguments:
        selected: dict mapping sector key to list of CanonicalItems selected
                  for generation.

    Returns:
        Per-sector and total article counts, estimated word counts, and
        approximate LLM token estimates.
    """
    stats: dict[str, Any] = {}
    total_articles = 0
    total_words = 0

    for sector, items in selected.items():
        sector_articles = 0
        sector_words = 0
        for item in items:
            art_type = get_article_type(item)
            wc = get_word_count(art_type)
            sector_articles += 1
            sector_words += wc["max"]

        stats[sector] = {
            "label": get_sector_label(sector),
            "articles": sector_articles,
            "estimated_words": sector_words,
            "avg_words_per_article": round(
                sector_words / max(1, sector_articles),
            ),
            "estimated_llm_tokens": sector_articles * 2500,
        }
        total_articles += sector_articles
        total_words += sector_words

    # Token estimate: system prompt + user prompt + article output
    # Roughly 2000 tokens of model output per article, plus prompt overhead
    avg_tokens_per_article = 2500
    stats["total"] = {
        "articles": total_articles,
        "estimated_words": total_words,
        "avg_words_per_article": round(
            total_words / max(1, total_articles),
        ),
        "estimated_llm_input_tokens": total_articles * 3000,
        "estimated_llm_output_tokens": total_articles * avg_tokens_per_article,
        "sectors_with_articles": sum(
            1 for s in stats
            if s != "total" and stats[s]["articles"] > 0
        ),
    }

    return stats


def print_generation_summary(
    stats: dict[str, Any],
) -> None:
    """Print a formatted generation summary to stdout."""
    total = stats.get("total", {})
    print(f"\n{'='*60}")
    print("  Multi-Sector Generation Summary")
    print(f"{'='*60}")
    print(
        f"  Total articles: {total.get('articles', 0)} "
        f"across {total.get('sectors_with_articles', 0)} sector(s)"
    )
    print(
        f"  Estimated words: {total.get('estimated_words', 0):,}"
    )
    print(
        f"  Estimated LLM tokens: "
        f"~{total.get('estimated_llm_input_tokens', 0):,} input, "
        f"~{total.get('estimated_llm_output_tokens', 0):,} output"
    )
    print(f"{'-'*60}")
    for sector, data in sorted(stats.items()):
        if sector == "total":
            continue
        if data["articles"] == 0:
            continue
        print(
            f"  {data['label']:<25s} "
            f"{data['articles']:>3d} articles  "
            f"~{data['estimated_words']:>6,} words  "
            f"({data['avg_words_per_article']} avg)"
        )
    print(f"{'='*60}")


# ── Validation ─────────────────────────────────────────────────────────

def validate_item_for_generation(item: CanonicalItem) -> list[str]:
    """Run pre-flight checks on a CanonicalItem before generation.

    Returns a list of issues. An empty list means the item is ready.
    """
    issues = []
    if not item.headline:
        issues.append("Missing headline")
    if not item.raw_summary and not item.raw_text:
        issues.append("No source content (summary or full text)")
    if not item.source_url:
        issues.append("Missing source URL")
    if not item.primary_sector:
        issues.append("No primary sector assigned")
    if item.composite_score is None or item.composite_score <= 0:
        issues.append("Item has not been scored")
    return issues


def filter_ready_items(
    items: list[CanonicalItem],
) -> tuple[list[CanonicalItem], list[tuple[CanonicalItem, list[str]]]]:
    """Split items into ready and blocked, returning issues for blocked items.

    Returns:
        (ready_items, [(blocked_item, issues), ...])
    """
    ready = []
    blocked = []
    for item in items:
        issues = validate_item_for_generation(item)
        if issues:
            blocked.append((item, issues))
        else:
            ready.append(item)
    return ready, blocked
