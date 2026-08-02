"""Canonical news item data model for the Light Tower Insights multi-sector pipeline.

Every story passing through the pipeline is represented as a CanonicalItem.
This replaces the ad-hoc dicts used in the current system with a typed,
validatable data structure.
"""

from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_THRESHOLDS_CACHE: dict[str, Any] | None = None
_THRESHOLDS_PATH: Path | None = None


def _get_thresholds_cache() -> dict[str, Any]:
    global _THRESHOLDS_CACHE, _THRESHOLDS_PATH
    if _THRESHOLDS_CACHE is not None:
        return _THRESHOLDS_CACHE
    _THRESHOLDS_PATH = Path(__file__).parent.parent / "config" / "thresholds.json"
    try:
        _THRESHOLDS_CACHE = json.loads(_THRESHOLDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _THRESHOLDS_CACHE = {}
    return _THRESHOLDS_CACHE


@dataclass
class CanonicalItem:
    """A single news item in canonical form, used across all pipeline phases."""
    
    # Identity
    item_id: str = ""
    source_name: str = ""
    source_url: str = ""
    canonical_url: str = ""
    headline: str = ""
    publication_date: str = ""  # ISO 8601
    discovery_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: str = ""
    
    # Content
    raw_summary: str = ""
    raw_text: str = ""
    clean_text: str = ""
    
    # Source metadata
    source_type: str = ""  # rss, api, scraper, search_api
    source_tier: int = 3  # 1=primary/authoritative, 2=established, 3=trade, 4=regional, 5=aggregator
    source_authority: str = "secondary"  # primary, secondary
    
    # Classification
    primary_sector: str = ""  # commercial_real_estate, private_equity, etc.
    secondary_sectors: list[str] = field(default_factory=list)
    event_type: str = ""
    subsector: str = ""
    classification_confidence: float = 0.0
    classification_method: str = ""  # source_prior, regex, entity_match, llm
    
    # Geography
    city: str = ""
    state: str = ""
    country: str = "US"
    market: str = ""
    property_address: str = ""
    
    # Entities
    companies: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    buyers: list[str] = field(default_factory=list)
    sellers: list[str] = field(default_factory=list)
    lenders: list[str] = field(default_factory=list)
    developers: list[str] = field(default_factory=list)
    government_bodies: list[str] = field(default_factory=list)
    
    # Financials
    transaction_value: float = 0.0
    transaction_value_raw: str = ""
    debt_amount: float = 0.0
    equity_amount: float = 0.0
    fund_size: float = 0.0
    unit_count: int = 0
    square_footage: int = 0
    acreage: float = 0.0
    megawatts: float = 0.0
    property_type: str = ""
    
    # Scoring
    financial_magnitude_score: int = 0
    party_significance_score: int = 0
    market_impact_score: int = 0
    strategic_relevance_score: int = 0
    policy_impact_score: int = 0
    novelty_score: int = 0
    source_quality_score: int = 0
    timeliness_score: int = 0
    editorial_potential_score: int = 0
    cross_sector_impact_score: int = 0
    composite_score: float = 0.0
    scoring_profile: str = ""
    tier: str = ""  # tier_1_must_cover, tier_2_strongly_recommended, etc.
    
    # Processing status
    status: str = "ingested"  # ingested, classified, scored, ranked, selected, enriched, generated, published, rejected, failed
    rejection_reason: str = ""
    rejection_code: str = ""
    retry_count: int = 0
    error_history: list[str] = field(default_factory=list)
    
    # Clustering
    cluster_id: str = ""
    is_anchor: bool = False
    
    # Article tracking
    article_slug: str = ""
    article_url: str = ""
    generated_at: str = ""
    published_at: str = ""
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def generate_id(self) -> str:
        """Generate a stable ID from source URL + headline."""
        key = f"{self.source_url}|{self.headline}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanonicalItem:
        """Create from dict, filtering to known fields."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
    
    @classmethod
    def from_rss_entry(cls, entry: dict[str, Any], source: dict[str, Any]) -> CanonicalItem:
        """Create from a feedparser RSS entry + source metadata."""
        if not isinstance(entry, dict) or not isinstance(source, dict):
            raise TypeError("entry and source must be dicts")
        item = cls()
        item.source_name = source.get("name", "")
        item.source_url = entry.get("link", "")
        item.canonical_url = entry.get("link", "")
        item.headline = (entry.get("title") or "").strip()
        item.publication_date = entry.get("published") or ""
        item.author = entry.get("author") or ""
        item.raw_summary = (entry.get("summary") or "").strip()
        item.source_type = source.get("source_type", "")
        item.source_tier = int(source.get("tier", 3))
        item.source_authority = "secondary"
        configured_sectors = [
            str(sector).strip()
            for sector in (source.get("sectors") or [])
            if str(sector).strip()
        ]
        if configured_sectors:
            # Preserve the source registry's editorial lane as a real prior.
            # The classifier may override it when article-level signals are
            # stronger, but it must not silently turn every ambiguous feed
            # item into commercial real estate.
            item.primary_sector = configured_sectors[0]
            item.secondary_sectors = configured_sectors[1:4]
            item.classification_confidence = 0.55
            item.classification_method = "source_config_prior"
        item.item_id = item.generate_id()
        if not item.publication_date:
            item.publication_date = item.discovery_date
        return item

    def set_classification(self, primary: str, secondary: list[str], event_type: str, 
                           subsector: str, confidence: float, method: str) -> None:
        self.primary_sector = primary
        self.secondary_sectors = secondary
        self.event_type = event_type
        self.subsector = subsector
        self.classification_confidence = confidence
        self.classification_method = method
        self.status = "classified"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_scoring(self, scores: dict[str, int], composite: float, profile: str, tier: str) -> None:
        self.financial_magnitude_score = scores.get("financial_magnitude", 0)
        self.party_significance_score = scores.get("party_significance", 0)
        self.market_impact_score = scores.get("market_impact", 0)
        self.strategic_relevance_score = scores.get("strategic_relevance", 0)
        self.policy_impact_score = scores.get("policy_impact", 0)
        self.novelty_score = scores.get("novelty", 0)
        self.source_quality_score = scores.get("source_quality", 0)
        self.timeliness_score = scores.get("timeliness", 0)
        self.editorial_potential_score = scores.get("editorial_potential", 0)
        self.cross_sector_impact_score = scores.get("cross_sector_impact", 0)
        self.composite_score = composite
        self.scoring_profile = profile
        self.tier = tier
        self.status = "scored"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def reject(self, reason: str, code: str) -> None:
        self.status = "rejected"
        self.rejection_reason = reason
        self.rejection_code = code
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_error(self, error: str) -> None:
        self.retry_count += 1
        self.error_history.append(error)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def is_publishable(self) -> bool:
        data = _get_thresholds_cache()
        threshold = data.get("signal_gate", {}).get("minimum_composite_score_to_write", 35)
        return self.composite_score >= threshold and self.status == "scored"
    
    def age_hours(self) -> float:
        try:
            pub = datetime.fromisoformat(self.publication_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - pub).total_seconds() / 3600
        except (ValueError, AttributeError):
            return 999
