"""Canonical editorial-intelligence object: the ranking unit of the pipeline.

A `CanonicalItem` is one retrieved document -- an article, a filing, a release.
An `IntelligenceObject` is one underlying *thing that happened*: an event, an
update to an event, a data release, a market movement, a disclosure or a trend.
Several documents reporting the same transaction collapse into one object.

This distinction is the point. Ranking URLs let three outlets covering one
$500m acquisition occupy three slots in a ten-story slate, and left the system
with `independent_source_count: 1` on every story because corroborating
coverage was never merged. Ranking objects fixes both.

Schema is versioned. `SCHEMA_VERSION` must be incremented on any change that
alters the meaning of an existing field, so persisted objects remain readable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

SCHEMA_VERSION = 2


# ── Controlled vocabularies ────────────────────────────────────────────────
# Deliberately explicit rather than free strings: an unknown value is a bug we
# want surfaced by validation, not silently ranked.

class ObjectClass:
    """What kind of intelligence this object represents."""

    DISCRETE_EVENT = "discrete_event"
    EVENT_UPDATE = "event_update"
    DATA_RELEASE = "data_release"
    MARKET_MOVEMENT = "market_movement"
    TREND = "trend"
    DISCLOSURE = "disclosure"
    ANALYTICAL_FINDING = "analytical_finding"

    ALL = frozenset({
        DISCRETE_EVENT, EVENT_UPDATE, DATA_RELEASE, MARKET_MOVEMENT,
        TREND, DISCLOSURE, ANALYTICAL_FINDING,
    })


class ContentType:
    """What kind of source material this is. Gates eligibility."""

    NEWS_REPORT = "news_report"
    PRESS_RELEASE = "press_release"
    PRIMARY_DOCUMENT = "primary_document"
    REGULATORY_FILING = "regulatory_filing"
    EARNINGS_MATERIAL = "earnings_material"
    DATA_PUBLICATION = "data_publication"
    RESEARCH_REPORT = "research_report"
    INTERVIEW = "interview"
    OPINION = "opinion"
    EXPLAINER = "explainer"
    MARKETING = "marketing"
    PERSONNEL_NOTICE = "personnel_notice"
    LISTICLE = "listicle"
    EVENT_PROMOTION = "event_promotion"
    ADMINISTRATIVE_NOTICE = "administrative_notice"
    DIGEST = "digest"
    UNKNOWN = "unknown"

    ALL = frozenset({
        NEWS_REPORT, PRESS_RELEASE, PRIMARY_DOCUMENT, REGULATORY_FILING,
        EARNINGS_MATERIAL, DATA_PUBLICATION, RESEARCH_REPORT, INTERVIEW,
        OPINION, EXPLAINER, MARKETING, PERSONNEL_NOTICE, LISTICLE,
        EVENT_PROMOTION, ADMINISTRATIVE_NOTICE, DIGEST, UNKNOWN,
    })

    #: Content that is never editorial intelligence on its own. An interview or
    #: opinion piece is NOT here -- those are eligible on material disclosure,
    #: which is a separate test, per the editorial mandate.
    NEVER_ELIGIBLE = frozenset({
        MARKETING, EXPLAINER, PERSONNEL_NOTICE, LISTICLE, EVENT_PROMOTION,
        ADMINISTRATIVE_NOTICE,
        DIGEST,
    })

    #: Content carrying primary authority; corroboration requirements relax.
    PRIMARY_AUTHORITY = frozenset({
        PRIMARY_DOCUMENT, REGULATORY_FILING, DATA_PUBLICATION, EARNINGS_MATERIAL,
    })


class EvidenceLevel:
    """How much the scorer is actually allowed to claim."""

    PRIMARY_CORROBORATED = "primary_corroborated"
    CORROBORATED = "corroborated"
    SINGLE_FULL_TEXT = "single_full_text"
    SINGLE_SUMMARY = "single_summary"
    INSUFFICIENT = "insufficient"

    ALL = frozenset({
        PRIMARY_CORROBORATED, CORROBORATED, SINGLE_FULL_TEXT,
        SINGLE_SUMMARY, INSUFFICIENT,
    })

    #: Depth each level can honestly support. Phase 1 found the system asking
    #: for an original thesis while holding one thin secondary source, then
    #: correctly refusing to publish it. Depth is now capped by evidence.
    MAX_DEPTH = {
        PRIMARY_CORROBORATED: "tier_a",
        CORROBORATED: "tier_a",
        SINGLE_FULL_TEXT: "tier_b",
        SINGLE_SUMMARY: "tier_c",
        INSUFFICIENT: "none",
    }


class RetrievalStatus:
    """What the scorer actually received, so it never assumes evidence."""

    FULL_TEXT = "full_text"
    PARTIAL_TEXT = "partial_text"
    SUMMARY_ONLY = "summary_only"
    STRUCTURED_DATA = "structured_data"
    BLOCKED = "blocked"
    FAILED = "failed"

    ALL = frozenset({
        FULL_TEXT, PARTIAL_TEXT, SUMMARY_ONLY, STRUCTURED_DATA, BLOCKED, FAILED,
    })


class NoveltyState:
    """Relationship to prior coverage. Replaces the hardcoded novelty score."""

    NEW = "new"
    MATERIAL_UPDATE = "material_update"
    NEW_STAGE = "new_stage"
    MINOR_FOLLOW_UP = "minor_follow_up"
    DUPLICATE = "duplicate"
    ALREADY_PUBLISHED = "already_published"

    ALL = frozenset({
        NEW, MATERIAL_UPDATE, NEW_STAGE, MINOR_FOLLOW_UP, DUPLICATE,
        ALREADY_PUBLISHED,
    })


DEPTHS = ("tier_a", "tier_b", "tier_c", "none")


# ── Provenance ─────────────────────────────────────────────────────────────

@dataclass
class SourceRef:
    """One document supporting an object, with how it was obtained."""

    item_id: str = ""
    source_name: str = ""
    source_url: str = ""
    canonical_url: str = ""
    source_tier: int = 3
    content_type: str = ContentType.UNKNOWN
    retrieval_status: str = RetrievalStatus.SUMMARY_ONLY
    publication_date: str = ""
    is_primary_authority: bool = False
    text_chars: int = 0
    retrieved_text: str = ""
    discovery_channel: str = "rss"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fact:
    """An extracted fact with the evidence that supports it.

    `evidence_span` must be text actually present in a supporting document.
    A fact with no span is an inference and must be labelled as such, so the
    generator can separate verified facts from analysis.
    """

    name: str = ""
    value: Any = None
    unit: str = ""
    evidence_span: str = ""
    source_item_id: str = ""
    corroborating_item_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    is_inference: bool = False
    conflicts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_corroborated(self) -> bool:
        return len(self.corroborating_item_ids) > 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["is_corroborated"] = self.is_corroborated
        return data


@dataclass
class ScoreComponent:
    """A dimension score that must explain itself.

    Phase 1 found three of ten dimensions constant across 288 candidates and no
    rationale recorded anywhere. A bare number is not acceptable output.
    """

    name: str = ""
    score: float = 0.0
    weight: float = 1.0
    rationale: str = ""
    evidence: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["weighted"] = round(self.weighted, 3)
        return data


# ── The object ─────────────────────────────────────────────────────────────

@dataclass
class IntelligenceObject:
    """One underlying event or signal, assembled from one or more documents."""

    # Identity
    object_id: str = ""
    cluster_id: str = ""
    schema_version: int = SCHEMA_VERSION
    processing_version: str = ""

    # Nature
    object_class: str = ObjectClass.DISCRETE_EVENT
    content_type: str = ContentType.UNKNOWN
    event_type: str = ""
    signal_type: str = ""

    # Placement
    primary_sector: str = ""
    secondary_sectors: list[str] = field(default_factory=list)
    primary_subsector: str = ""
    secondary_subsectors: list[str] = field(default_factory=list)
    geography: dict[str, str] = field(default_factory=dict)
    classification_confidence: float = 0.0
    classification_evidence: list[str] = field(default_factory=list)

    # Substance
    title: str = ""
    what_happened: str = ""
    entities: list[dict[str, str]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    material_claims: list[str] = field(default_factory=list)
    market_consequences: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    event_status: str = ""

    # Time
    publication_date: str = ""
    event_date: str = ""
    observation_date: str = ""
    first_seen: str = ""
    last_material_update: str = ""

    # Evidence
    sources: list[SourceRef] = field(default_factory=list)
    evidence_level: str = EvidenceLevel.INSUFFICIENT
    evidence_confidence: float = 0.0
    conflicts: list[dict[str, Any]] = field(default_factory=list)

    # Memory
    novelty_state: str = NoveltyState.NEW
    novelty_score: float = 0.0
    prior_object_ids: list[str] = field(default_factory=list)
    prior_published_slugs: list[str] = field(default_factory=list)
    material_changes: list[str] = field(default_factory=list)

    # Scoring
    eligible: bool = False
    eligibility_reason: str = ""
    disqualifiers: list[str] = field(default_factory=list)
    importance_components: list[ScoreComponent] = field(default_factory=list)
    importance_score: float = 0.0
    editorial_opportunity_score: float = 0.0
    penalties: list[ScoreComponent] = field(default_factory=list)
    final_score: float = 0.0

    # Ranking and selection
    subsector_rank: int = 0
    sector_rank: int = 0
    global_rank: int = 0
    sector_percentile: float = 0.0
    tier: str = ""
    recommended_depth: str = "none"
    selected: bool = False
    selection_rationale: str = ""

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ── Derived ────────────────────────────────────────────────────────────

    @property
    def independent_source_count(self) -> int:
        """Distinct publishers, not distinct URLs.

        Syndication partners republishing one wire story are not independent
        corroboration, so identical source names collapse.
        """
        return len({(s.source_name or s.canonical_url or s.source_url).lower() for s in self.sources})

    @property
    def primary_source_count(self) -> int:
        return sum(1 for s in self.sources if s.is_primary_authority)

    @property
    def usable_full_text_count(self) -> int:
        return sum(
            1 for s in self.sources
            if s.retrieval_status in (RetrievalStatus.FULL_TEXT, RetrievalStatus.STRUCTURED_DATA)
        )

    @property
    def max_supportable_depth(self) -> str:
        return EvidenceLevel.MAX_DEPTH.get(self.evidence_level, "none")

    def generate_id(self) -> str:
        basis = self.cluster_id or f"{self.primary_sector}|{self.title}|{self.event_date}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    # ── Evidence assessment ────────────────────────────────────────────────

    def assess_evidence(self) -> str:
        """Derive the evidence level from what was actually retrieved."""
        independent = self.independent_source_count
        primary = self.primary_source_count
        full_text = self.usable_full_text_count

        if independent == 0:
            level = EvidenceLevel.INSUFFICIENT
        elif primary >= 1 and independent >= 2:
            level = EvidenceLevel.PRIMARY_CORROBORATED
        elif independent >= 2 and full_text >= 1:
            level = EvidenceLevel.CORROBORATED
        elif full_text >= 1:
            level = EvidenceLevel.SINGLE_FULL_TEXT
        else:
            level = EvidenceLevel.SINGLE_SUMMARY

        self.evidence_level = level
        corroborated = sum(1 for f in self.facts if f.is_corroborated)
        fact_ratio = corroborated / len(self.facts) if self.facts else 0.0
        base = {
            EvidenceLevel.PRIMARY_CORROBORATED: 0.95,
            EvidenceLevel.CORROBORATED: 0.8,
            EvidenceLevel.SINGLE_FULL_TEXT: 0.55,
            EvidenceLevel.SINGLE_SUMMARY: 0.3,
            EvidenceLevel.INSUFFICIENT: 0.0,
        }[level]
        self.evidence_confidence = round(min(1.0, base + 0.05 * fact_ratio), 3)
        return level

    def cap_depth_to_evidence(self, requested: str) -> str:
        """Never ask for more analysis than the evidence can support."""
        order = {"tier_a": 3, "tier_b": 2, "tier_c": 1, "none": 0}
        allowed = self.max_supportable_depth
        chosen = requested if order.get(requested, 0) <= order.get(allowed, 0) else allowed
        self.recommended_depth = chosen
        return chosen

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sources"] = [s.to_dict() for s in self.sources]
        data["facts"] = [f.to_dict() for f in self.facts]
        data["importance_components"] = [c.to_dict() for c in self.importance_components]
        data["penalties"] = [p.to_dict() for p in self.penalties]
        data["derived"] = {
            "independent_source_count": self.independent_source_count,
            "primary_source_count": self.primary_source_count,
            "usable_full_text_count": self.usable_full_text_count,
            "max_supportable_depth": self.max_supportable_depth,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntelligenceObject":
        payload = dict(data)
        payload.pop("derived", None)
        payload["sources"] = [SourceRef(**s) for s in payload.get("sources", [])]
        payload["facts"] = [
            Fact(**{k: v for k, v in f.items() if k != "is_corroborated"})
            for f in payload.get("facts", [])
        ]
        payload["importance_components"] = [
            ScoreComponent(**{k: v for k, v in c.items() if k != "weighted"})
            for c in payload.get("importance_components", [])
        ]
        payload["penalties"] = [
            ScoreComponent(**{k: v for k, v in p.items() if k != "weighted"})
            for p in payload.get("penalties", [])
        ]
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in payload.items() if k in known})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=1)

    # ── Validation ─────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return structural problems. Empty list means the object is sane."""
        errors: list[str] = []
        if not self.object_id:
            errors.append("object_id is required")
        if self.object_class not in ObjectClass.ALL:
            errors.append(f"unknown object_class: {self.object_class!r}")
        if self.content_type not in ContentType.ALL:
            errors.append(f"unknown content_type: {self.content_type!r}")
        if self.evidence_level not in EvidenceLevel.ALL:
            errors.append(f"unknown evidence_level: {self.evidence_level!r}")
        if self.novelty_state not in NoveltyState.ALL:
            errors.append(f"unknown novelty_state: {self.novelty_state!r}")
        if self.recommended_depth not in DEPTHS:
            errors.append(f"unknown recommended_depth: {self.recommended_depth!r}")
        if self.schema_version != SCHEMA_VERSION:
            errors.append(
                f"schema_version {self.schema_version} != current {SCHEMA_VERSION}; migrate first"
            )
        if not self.primary_sector:
            errors.append("primary_sector is required")
        if self.eligible and not self.sources:
            errors.append("an eligible object must cite at least one source")
        if self.selected and not self.selection_rationale:
            errors.append("a selected object must record why it was selected")
        if self.selected and not self.eligible:
            errors.append("an ineligible object must never be selected")
        order = {"tier_a": 3, "tier_b": 2, "tier_c": 1, "none": 0}
        if order.get(self.recommended_depth, 0) > order.get(self.max_supportable_depth, 0):
            errors.append(
                f"recommended_depth {self.recommended_depth} exceeds what "
                f"{self.evidence_level} evidence supports ({self.max_supportable_depth})"
            )
        for fact in self.facts:
            if not fact.is_inference and not fact.evidence_span:
                errors.append(f"fact {fact.name!r} claims to be observed but cites no evidence span")
        return errors

    def is_valid(self) -> bool:
        return not self.validate()


def source_ref_from_item(item: Any, *, discovery_channel: str = "rss") -> SourceRef:
    """Build a SourceRef from a CanonicalItem without importing it (avoids a cycle)."""
    text_chars = len(getattr(item, "raw_text", "") or "")
    summary_chars = len(getattr(item, "raw_summary", "") or "")
    if text_chars > 1000:
        retrieval = RetrievalStatus.FULL_TEXT
    elif text_chars > 0:
        retrieval = RetrievalStatus.PARTIAL_TEXT
    elif summary_chars > 0:
        retrieval = RetrievalStatus.SUMMARY_ONLY
    else:
        retrieval = RetrievalStatus.FAILED
    tier = int(getattr(item, "source_tier", 3) or 3)
    return SourceRef(
        item_id=getattr(item, "item_id", "") or "",
        source_name=getattr(item, "source_name", "") or "",
        source_url=getattr(item, "source_url", "") or "",
        canonical_url=getattr(item, "canonical_url", "") or "",
        source_tier=tier,
        is_primary_authority=(
            str(getattr(item, "source_authority", "")).lower() == "primary"
        ),
        publication_date=getattr(item, "publication_date", "") or "",
        retrieval_status=retrieval,
        text_chars=text_chars or summary_chars,
        retrieved_text=(getattr(item, "raw_text", "") or "")[:12_000],
        discovery_channel=discovery_channel,
    )


def merge_sources(refs: Iterable[SourceRef]) -> list[SourceRef]:
    """Deduplicate source refs by canonical URL, keeping the richest retrieval."""
    best: dict[str, SourceRef] = {}
    rank = {
        RetrievalStatus.STRUCTURED_DATA: 5,
        RetrievalStatus.FULL_TEXT: 4,
        RetrievalStatus.PARTIAL_TEXT: 3,
        RetrievalStatus.SUMMARY_ONLY: 2,
        RetrievalStatus.BLOCKED: 1,
        RetrievalStatus.FAILED: 0,
    }
    for ref in refs:
        key = (ref.canonical_url or ref.source_url or ref.item_id).lower().rstrip("/")
        current = best.get(key)
        if current is None or rank.get(ref.retrieval_status, 0) > rank.get(current.retrieval_status, 0):
            best[key] = ref
    return list(best.values())
