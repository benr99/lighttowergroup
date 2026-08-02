"""Production bridge from multi-sector v2 selection to editorial publishing.

This module intentionally contains no file or Git side effects. It converts
typed v2 candidates into the existing research-dossier contract, invokes the
seven-stage editorial pipeline, and returns an article compatible with the
validated renderer in ``daily_news_agent.py``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from canonical_item import CanonicalItem
from editorial_pipeline import EditorialPipeline
from generation import get_sector_category, get_sector_label


_LEGAL_RISK = re.compile(
    r"\b(?:alleg(?:ation|ed|edly)|lawsuit|litigation|fraud|indict(?:ed|ment)?|"
    r"criminal|charged|investigation|sanction)\b",
    re.IGNORECASE,
)


def canonical_source_url(item: CanonicalItem) -> str:
    """Return the best canonical article URL carried by a v2 item."""
    return str(item.canonical_url or item.source_url or "").strip()


def is_article_level_url(value: str) -> bool:
    """Reject missing, unsafe, and obvious publication-homepage URLs."""
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return bool(parsed.path.strip("/") or parsed.query)


def select_daily_items(
    selected_by_sector: dict[str, list[CanonicalItem]],
    *,
    limit: int,
    archive_records: Iterable[dict[str, Any]] = (),
) -> list[CanonicalItem]:
    """Choose a high-scoring, cross-sector daily slate from v2 rankings."""
    limit = max(0, int(limit))
    if not limit:
        return []

    published_urls = {
        str(record.get("source_url") or record.get("url") or "").strip()
        for record in archive_records
        if isinstance(record, dict)
    }
    pools: dict[str, list[CanonicalItem]] = {}
    for sector, items in selected_by_sector.items():
        eligible = [
            item for item in items
            if item.tier != "rejected"
            and is_article_level_url(canonical_source_url(item))
            and canonical_source_url(item) not in published_urls
        ]
        eligible.sort(key=lambda item: item.composite_score, reverse=True)
        if eligible:
            pools[sector] = eligible

    chosen: list[CanonicalItem] = []
    seen_ids: set[str] = set()

    # First pass: one strongest story per sector, ranked globally. This keeps a
    # three-piece edition from collapsing into a single source lane.
    sector_leaders = sorted(
        (items[0] for items in pools.values()),
        key=lambda item: item.composite_score,
        reverse=True,
    )
    for item in sector_leaders:
        item_id = item.item_id or item.generate_id()
        if item_id in seen_ids:
            continue
        chosen.append(item)
        seen_ids.add(item_id)
        if len(chosen) >= limit:
            return chosen

    # Second pass: fill the remaining capacity strictly by score.
    remainder = sorted(
        (item for items in pools.values() for item in items[1:]),
        key=lambda item: item.composite_score,
        reverse=True,
    )
    for item in remainder:
        item_id = item.item_id or item.generate_id()
        if item_id in seen_ids:
            continue
        chosen.append(item)
        seen_ids.add(item_id)
        if len(chosen) >= limit:
            break
    return chosen


def canonical_item_to_editorial_event(item: CanonicalItem) -> dict[str, Any]:
    """Adapt a selected v2 item to the research-dossier/editorial-room contract."""
    url = canonical_source_url(item)
    amount = item.transaction_value_raw
    if not amount:
        for value in (item.transaction_value, item.debt_amount, item.equity_amount, item.fund_size):
            if value:
                amount = f"${value:,.0f}"
                break
    source = {
        "source": item.source_name,
        "url": url,
        "domain": urlparse(url).netloc.lower().removeprefix("www."),
        "published": item.publication_date,
        "summary": item.raw_summary or item.raw_text,
        "source_tier": item.source_tier,
        "source_authority": item.source_authority or "secondary",
    }
    topics = [value for value in (item.primary_sector, item.event_type, item.subsector) if value]
    companies = list(dict.fromkeys(
        item.companies + item.buyers + item.sellers + item.lenders + item.developers
    ))
    candidate = {
        "title": item.headline,
        "url": url,
        "source": item.source_name,
        "summary": item.raw_summary or item.raw_text,
        "published": item.publication_date,
        "source_tier": item.source_tier,
        "source_authority": item.source_authority or "secondary",
        "source_lane": item.primary_sector or "market",
        "topics": topics,
        "category": get_sector_category(item.primary_sector),
        "entities": {
            "companies": companies,
            "amounts": [amount] if amount else [],
            "asset_classes": [item.property_type] if item.property_type else [],
            "markets": [value for value in (item.market, item.city, item.state) if value],
            "policy_actions": [],
            "msa_government_markets": [],
        },
        "canonical_item": item.to_dict(),
        "pipeline_version": "v2",
    }
    selection_tier = (
        "must_read"
        if item.tier in {"tier_1_must_cover", "tier_2_strongly_recommended"}
        else "daily_depth"
    )
    label = get_sector_label(item.primary_sector) or "Capital Intelligence"
    return {
        "event_id": item.item_id or item.generate_id(),
        "candidate": candidate,
        "sources": [source],
        "provisional_format": "brief",
        "must_read_score": int(round(item.composite_score)),
        "must_read_breakdown": {
            "financial_magnitude": item.financial_magnitude_score,
            "party_significance": item.party_significance_score,
            "market_impact": item.market_impact_score,
            "editorial_potential": item.editorial_potential_score,
        },
        "selection_tier": selection_tier,
        "legal_or_allegation_risk": bool(_LEGAL_RISK.search(
            f"{item.headline} {item.raw_summary}"
        )),
        "franchise": {
            "id": item.primary_sector or "capital_intelligence",
            "name": label,
            "promise": "Explain the capital decision, constraint, and consequence beneath the event.",
        },
    }


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug[:72].rstrip("-")


def _source_records(dossier: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in dossier.get("sources", []):
        if not isinstance(source, dict):
            continue
        url = str(source.get("url", "")).strip()
        if not is_article_level_url(url) or url in seen:
            continue
        records.append({"url": url, "name": str(source.get("name") or source.get("domain") or url)})
        seen.add(url)
    return records


def generate_v2_article(
    story: dict[str, Any],
    *,
    api_key: str,
    provider: dict[str, Any],
) -> dict[str, Any]:
    """Run the seven-stage writer and return a renderer-compatible article."""
    canonical_data = story.get("canonical_item")
    if not isinstance(canonical_data, dict):
        raise ValueError("V2 story is missing its canonical item")
    dossier = story.get("research_dossier")
    if not isinstance(dossier, dict):
        raise ValueError("V2 story is missing its research dossier")
    sources = _source_records(dossier)
    if not sources:
        raise ValueError("V2 story has no canonical article-level source URL")

    item = CanonicalItem.from_dict(canonical_data)
    item.raw_text = story.get("full_text") or item.raw_text
    item.raw_summary = story.get("summary") or item.raw_summary
    pipeline = EditorialPipeline(api_key=api_key, provider=provider)
    result = pipeline.run(item, dossier)
    if result.get("status") != "completed" or not isinstance(result.get("article"), dict):
        reason = result.get("errors") or result.get("error") or result.get("status")
        raise RuntimeError(f"V2 editorial pipeline did not clear publication: {reason}")

    generated = result["article"]
    body_html = str(generated.get("body_html") or "").strip()
    title = str(generated.get("title") or item.headline).strip()
    if not body_html or not title:
        raise ValueError("V2 editorial output is missing title or body_html")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    excerpt = str(
        generated.get("excerpt")
        or generated.get("meta_description")
        or generated.get("subtitle")
        or item.raw_summary
        or ""
    ).strip()
    tags = generated.get("tags") if isinstance(generated.get("tags"), list) else []
    tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    if not tags:
        tags = list(dict.fromkeys(
            [get_sector_label(item.primary_sector)] + item.companies[:4]
        ))
    slug = _safe_slug(generated.get("slug") or title)
    if not slug:
        raise ValueError("V2 editorial output could not produce a safe slug")

    article = {
        **generated,
        "title": title,
        "subtitle": str(generated.get("subtitle") or excerpt).strip(),
        "slug": slug,
        "category": str(generated.get("category") or get_sector_category(item.primary_sector)),
        "meta_description": str(generated.get("meta_description") or excerpt)[:160],
        "excerpt": excerpt[:240],
        "tags": tags,
        "body_html": body_html,
        # Source metadata is immutable evidence from the dossier. Never trust
        # a model-created URL or silently retain an empty model source array.
        "sources": sources,
        "source_count": len({urlparse(source["url"]).netloc.lower() for source in sources}),
        "source_url": sources[0]["url"],
        "source_name": sources[0]["name"],
        "date": now.strftime("%B %d, %Y"),
        "date_iso": now.isoformat(),
        "event_id": story.get("editorial_event_id") or item.item_id,
        "editorial_format": story.get("editorial_format") or "brief",
        "editorial_format_label": story.get("editorial_format_label") or "Intelligence Brief",
        "franchise": story.get("franchise"),
        "must_read_score": story.get("must_read_score") or int(round(item.composite_score)),
        "must_read_breakdown": story.get("must_read_breakdown"),
        "selection_tier": story.get("selection_tier") or item.tier,
        "legal_or_allegation_risk": story.get("legal_or_allegation_risk", False),
        "research_evidence_level": dossier.get("evidence_level"),
        "research_usable_full_text_count": dossier.get("usable_full_text_count", 0),
        "research_reported_fact_count": len(dossier.get("reported_facts", [])),
        "research_dossier": dossier,
        "editorial_room_decision": (story.get("editorial_room") or {}).get("decision"),
        "pipeline_version": "v2",
        "_v2_pipeline": {
            "provider": provider.get("provider"),
            "model": provider.get("model"),
            "stages": result.get("stages"),
            "errors": result.get("errors", []),
        },
    }
    return article
