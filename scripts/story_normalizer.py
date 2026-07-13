"""
Normalize raw news items for the Light Tower editorial desk.

This module is deliberately lightweight: it adds enough structure for scoring
without introducing a database, crawler framework, or hidden state.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urlparse

try:
    from news_sources import SOURCE_METADATA
except Exception:  # pragma: no cover - defensive for standalone use
    SOURCE_METADATA = {}


KNOWN_INSTITUTIONS = [
    "blackstone", "brookfield", "apollo", "starwood", "ares", "kkr",
    "carlyle", "tpg", "sl green", "vornado", "related", "tishman",
    "jpmorgan", "jp morgan", "goldman", "morgan stanley", "wells fargo",
    "bank of america", "citigroup", "citi", "deutsche bank", "barclays",
    "federal reserve", "fed", "fdic", "occ", "treasury", "fannie mae",
    "freddie mac", "hud", "cbrem", "cbre", "jll", "cushman",
]

TOPIC_PATTERNS = {
    "major_sale": r"\b(sale|sells|sold|buys|bought|buys? stake|acquisition|acquires|acquired|disposition|purchases?)\b",
    "capital_placement": r"\b(refinanc|loan|mortgage|financ|debt|credit facility|capital raise|capital placement|equity investment|equity commitment|preferred equity|mezzanine|construction financing|joint venture capital)\b",
    "mna": r"\b(merger|acquisition|m&a|takeover|combination|joint venture)\b",
    "fed_rates": r"\b(federal reserve|fed|rate cut|rate hike|interest rate|treasury yield|sofr|inflation)\b",
    "bank_credit": r"\b(bank|lender|credit loss|loan loss|reserve|charge-off|commercial real estate exposure)\b",
    "private_credit": r"\b(private credit|debt fund|direct lending|alternative lender|bridge lender)\b",
    "private_equity": r"\b(private equity|family office|pension fund|sovereign wealth|fundraise|fund closes|opportunistic fund|real estate fund)\b",
    "distress": r"\b(default|distress|foreclosure|bankruptcy|receivership|workout|special servicing|note sale)\b",
    "cmbs": r"\b(cmbs|cre clo|securiti[sz]ation|special servicer|trepp)\b",
    "policy": r"\b(policy|regulation|zoning|tax|abatement|hud|fha|fannie|freddie|legislation)\b",
    "reit_public_markets": r"\b(reit|public markets|earnings|guidance|stock|shares)\b",
    "development_finance": r"\b(construction loan|development|groundbreaking|permits|completion)\b",
}

ASSET_CLASSES = {
    "office": r"\boffice\b",
    "multifamily": r"\b(multifamily|apartment|rental building|housing)\b",
    "industrial": r"\b(industrial|warehouse|logistics)\b",
    "retail": r"\b(retail|shopping center|mall)\b",
    "hotel": r"\b(hotel|hospitality)\b",
    "data_center": r"\b(data center|datacenter)\b",
}

US_MARKETS = [
    "new york", "nyc", "manhattan", "brooklyn", "queens", "bronx",
    "los angeles", "san francisco", "chicago", "miami", "dallas",
    "austin", "houston", "boston", "washington", "dc", "atlanta",
    "seattle", "denver", "phoenix", "philadelphia", "nashville",
]


def clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def stable_story_id(story: dict[str, Any]) -> str:
    key = "|".join([
        clean_text(story.get("source")).lower(),
        clean_text(story.get("title")).lower(),
        clean_text(story.get("url")).lower(),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def source_metadata(source: str) -> dict[str, Any]:
    meta = SOURCE_METADATA.get(source, {})
    return {
        "tier": int(meta.get("tier", 3)),
        "domains": list(meta.get("domains", ["general"])),
    }


def _find_amounts(text: str) -> list[str]:
    patterns = [
        r"\$[\d,.]+(?:\.\d+)?\s?(?:billion|million|trillion|bn|mm|m|b)?",
        r"\b\d+(?:\.\d+)?\s?(?:bps|basis points|percent|%)\b",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(item.strip() for item in found if item.strip()))[:8]


def has_reported_amount_at_least_ten_million(text: str) -> bool:
    """Return whether the text reports a dollar amount at or above $10 million."""
    for match in re.finditer(
        r"\$\s*([\d,.]+(?:\.\d+)?)\s*(million|billion|trillion|mm|bn|m|b)?\b",
        text,
        flags=re.IGNORECASE,
    ):
        raw_number, unit = match.groups()
        try:
            value = float(raw_number.replace(",", ""))
        except ValueError:
            continue
        multiplier = {
            "m": 1_000_000, "mm": 1_000_000, "million": 1_000_000,
            "b": 1_000_000_000, "bn": 1_000_000_000, "billion": 1_000_000_000,
            "trillion": 1_000_000_000_000,
        }.get((unit or "").lower(), 1)
        if value * multiplier >= 10_000_000:
            return True
    return False


def _has_material_transaction(text: str, amounts: list[str], topics: list[str]) -> bool:
    """Identify an announced CRE capital event worth elevating for editorial review.

    This is an *intake* signal, not a publication decision: the editorial scorer
    still requires reported evidence, a clear CRE connection, and a 70+ score.
    """
    transaction_topics = {"major_sale", "capital_placement", "mna", "private_equity", "development_finance"}
    if not (set(topics) & transaction_topics):
        return False
    # The scorer/model verifies that the amount is actually tied to the deal.
    return has_reported_amount_at_least_ten_million(text) and bool(re.search(
        r"\b(acquir|purchas|buy|sold|sale|invest|commit|loan|lend|financ|refinanc|equity|joint venture|recapitaliz|development)\b",
        text,
        flags=re.IGNORECASE,
    ))


def _find_topics(text: str) -> list[str]:
    topics = [
        topic for topic, pattern in TOPIC_PATTERNS.items()
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    return topics or ["general_market"]


def _find_asset_classes(text: str) -> list[str]:
    return [
        name for name, pattern in ASSET_CLASSES.items()
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def _find_markets(text: str) -> list[str]:
    lower = text.lower()
    return [market for market in US_MARKETS if market in lower][:8]


def _find_known_institutions(text: str) -> list[str]:
    lower = text.lower()
    found = [name for name in KNOWN_INSTITUTIONS if name in lower]
    return list(dict.fromkeys(found))[:10]


def _parse_published(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except Exception:
        return text


def normalize_story(story: dict[str, Any]) -> dict[str, Any]:
    title = clean_text(story.get("title"))
    summary = clean_text(story.get("summary"))
    source = clean_text(story.get("source")) or "Unknown"
    url = clean_text(story.get("url"))
    text = f"{title} {summary}"
    meta = source_metadata(source)
    amounts = _find_amounts(text)
    institutions = _find_known_institutions(text)
    topics = _find_topics(text)
    material_transaction = _has_material_transaction(text, amounts, topics)
    parsed = urlparse(url)

    return {
        "id": stable_story_id(story),
        "title": title,
        "source": source,
        "url": url,
        "domain": parsed.netloc.lower().replace("www.", ""),
        "published": _parse_published(story.get("published")),
        "summary": summary,
        "source_tier": meta["tier"],
        "source_domains": meta["domains"],
        "topics": topics,
        "entities": {
            "companies": institutions,
            "people": [],
            "markets": _find_markets(text),
            "amounts": amounts,
            "asset_classes": _find_asset_classes(text),
        },
        "attention_features": {
            "has_big_number": bool(amounts),
            "has_known_institution": bool(institutions),
            "has_transaction_language": any(t in topics for t in ("major_sale", "capital_placement", "mna")),
            "has_material_transaction": material_transaction,
            "has_distress_language": "distress" in topics,
            "has_policy_or_rate_language": any(t in topics for t in ("policy", "fed_rates")),
        },
    }


def normalize_stories(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    seen_ids = set()
    for story in stories:
        item = normalize_story(story)
        if not item["title"] or not item["url"] or item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        normalized.append(item)
    return normalized
