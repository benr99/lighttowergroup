"""Consolidate documents reporting the same underlying event into one object.

The ranking unit must be the event, not the URL. Phase 1 measured 14
near-duplicate pairs in a 288-item corpus, two of which had both copies
eligible and would have consumed two slots of a three-story edition for one
event. URL matching cannot catch this, because the URLs differ.

Similarity is deliberately deterministic and inspectable -- no embeddings, no
model call -- so a clustering decision can be explained and regression-tested.
Signals, in decreasing weight:

  monetary amount agreement   a shared "$1.1B" is strong evidence of one deal
  entity overlap              shared capitalised org tokens
  headline token overlap      Jaccard over content words
  numeric agreement           shared scale figures (units, sq ft, MW)

Every merge records why, so `cluster_audit` can be inspected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from intelligence_object import (
    ContentType,
    IntelligenceObject,
    ObjectClass,
    SourceRef,
    merge_sources,
    source_ref_from_item,
)

# Merge threshold. Calibrated against the known duplicate pairs: identical
# syndicated headlines score ~1.0, genuinely distinct stories about the same
# company score well below.
MERGE_THRESHOLD = 0.62

_STOPWORDS = frozenset("""
a an the and or but of for to in on at by with from as is are was were be been
its it his her their this that these those after before over under into out up
down new now says say said report reports amid via than then which who whom
""".split())

_MONEY_RE = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|bn|b|million|mm|m|trillion|tn|k|thousand)?\b",
    re.IGNORECASE,
)
_SCALE_RE = re.compile(
    r"\b([\d,]+(?:\.\d+)?)\s*(units?|sf|square feet|acres?|mw|megawatts?|rooms?|keys)\b",
    re.IGNORECASE,
)
_MULTIPLIER = {
    "trillion": 1e12, "tn": 1e12,
    "billion": 1e9, "bn": 1e9, "b": 1e9,
    "million": 1e6, "mm": 1e6, "m": 1e6,
    "k": 1e3, "thousand": 1e3,
    None: 1.0, "": 1.0,
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'&-]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _entities(text: str) -> set[str]:
    """Capitalised multi-word runs: a cheap proxy for organisation names."""
    found = re.findall(r"\b([A-Z][A-Za-z&'.-]+(?:\s+[A-Z][A-Za-z&'.-]+)*)", text or "")
    out: set[str] = set()
    for phrase in found:
        cleaned = phrase.strip()
        if len(cleaned) < 3:
            continue
        lowered = cleaned.lower()
        if lowered in _STOPWORDS:
            continue
        out.add(lowered)
    return out


def _amounts(text: str) -> set[float]:
    values: set[float] = set()
    for raw, unit in _MONEY_RE.findall(text or ""):
        try:
            base = float(raw.replace(",", ""))
        except ValueError:
            continue
        values.add(round(base * _MULTIPLIER.get((unit or "").lower(), 1.0)))
    return values


def _scales(text: str) -> set[tuple[float, str]]:
    out: set[tuple[float, str]] = set()
    for raw, unit in _SCALE_RE.findall(text or ""):
        try:
            out.add((float(raw.replace(",", "")), unit.lower().rstrip("s")))
        except ValueError:
            continue
    return out


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class _Signature:
    item: Any
    tokens: set[str] = field(default_factory=set)
    entities: set[str] = field(default_factory=set)
    amounts: set[float] = field(default_factory=set)
    scales: set = field(default_factory=set)
    sector: str = ""

    @classmethod
    def build(cls, item: Any) -> "_Signature":
        headline = getattr(item, "headline", "") or ""
        summary = getattr(item, "raw_summary", "") or ""
        blob = f"{headline} {summary}"
        return cls(
            item=item,
            tokens=_tokens(headline),
            entities=_entities(headline),
            amounts=_amounts(blob),
            scales=_scales(blob),
            sector=getattr(item, "primary_sector", "") or "",
        )


def similarity(a: _Signature, b: _Signature) -> tuple[float, list[str]]:
    """Return a 0-1 similarity and the reasons contributing to it."""
    reasons: list[str] = []

    token_sim = _jaccard(a.tokens, b.tokens)
    entity_sim = _jaccard(a.entities, b.entities)

    shared_amounts = a.amounts & b.amounts
    amount_sim = 1.0 if shared_amounts else 0.0
    if shared_amounts:
        reasons.append(f"shared amount {sorted(shared_amounts)[0]:,.0f}")

    shared_scales = a.scales & b.scales
    scale_sim = 1.0 if shared_scales else 0.0
    if shared_scales:
        value, unit = sorted(shared_scales)[0]
        reasons.append(f"shared scale {value:,.0f} {unit}")

    score = (
        0.42 * token_sim
        + 0.28 * entity_sim
        + 0.22 * amount_sim
        + 0.08 * scale_sim
    )

    # Conflicting headline amounts are strong evidence of different deals.
    if a.amounts and b.amounts and not shared_amounts:
        score *= 0.55
        reasons.append("different monetary amounts (penalised)")

    # Cross-sector merges need to clear a higher bar.
    if a.sector and b.sector and a.sector != b.sector:
        score *= 0.85
        reasons.append("cross-sector (penalised)")

    if token_sim:
        reasons.append(f"headline overlap {token_sim:.2f}")
    if entity_sim:
        reasons.append(f"entity overlap {entity_sim:.2f}")
    return min(1.0, score), reasons


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, index: int) -> int:
        while self._parent[index] != index:
            self._parent[index] = self._parent[self._parent[index]]
            index = self._parent[index]
        return index

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_b] = root_a


def cluster_items(
    items: Sequence[Any],
    *,
    threshold: float = MERGE_THRESHOLD,
) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    """Group items into event clusters. Returns (clusters, merge_audit)."""
    signatures = [_Signature.build(item) for item in items]
    union = _UnionFind(len(items))
    audit: list[dict[str, Any]] = []

    for i in range(len(signatures)):
        for j in range(i + 1, len(signatures)):
            score, reasons = similarity(signatures[i], signatures[j])
            if score >= threshold:
                union.union(i, j)
                audit.append({
                    "a": getattr(items[i], "headline", "")[:90],
                    "b": getattr(items[j], "headline", "")[:90],
                    "score": round(score, 3),
                    "reasons": reasons,
                })

    grouped: dict[int, list[Any]] = {}
    for index, item in enumerate(items):
        grouped.setdefault(union.find(index), []).append(item)
    return list(grouped.values()), audit


def _primary_item(cluster: Sequence[Any]) -> Any:
    """Pick the strongest source: primary authority, then tier, then text depth."""
    def rank(item: Any) -> tuple:
        tier = int(getattr(item, "source_tier", 3) or 3)
        authority = 0 if str(getattr(item, "source_authority", "")) == "primary" else 1
        text = len(getattr(item, "raw_text", "") or "")
        summary = len(getattr(item, "raw_summary", "") or "")
        return (authority, tier, -text, -summary)

    return sorted(cluster, key=rank)[0]


def build_intelligence_object(
    cluster: Sequence[Any],
    *,
    processing_version: str = "",
) -> IntelligenceObject:
    """Assemble one IntelligenceObject from a cluster of documents."""
    primary = _primary_item(cluster)
    refs = merge_sources(source_ref_from_item(item) for item in cluster)

    cluster_id = ""
    for item in cluster:
        candidate = getattr(item, "item_id", "") or ""
        if candidate and (not cluster_id or candidate < cluster_id):
            cluster_id = candidate

    obj = IntelligenceObject(
        cluster_id=cluster_id,
        processing_version=processing_version,
        object_class=ObjectClass.DISCRETE_EVENT,
        content_type=ContentType.UNKNOWN,
        primary_sector=getattr(primary, "primary_sector", "") or "",
        secondary_sectors=list(getattr(primary, "secondary_sectors", []) or []),
        primary_subsector=getattr(primary, "subsector", "") or "",
        event_type=getattr(primary, "event_type", "") or "",
        title=getattr(primary, "headline", "") or "",
        what_happened=(getattr(primary, "raw_summary", "") or "")[:600],
        publication_date=getattr(primary, "publication_date", "") or "",
        sources=refs,
    )
    obj.object_id = obj.generate_id()
    obj.assess_evidence()
    return obj


def cluster_to_objects(
    items: Sequence[Any],
    *,
    threshold: float = MERGE_THRESHOLD,
    processing_version: str = "",
) -> tuple[list[IntelligenceObject], dict[str, Any]]:
    """Full pass: documents in, intelligence objects out, with an audit trail."""
    clusters, audit = cluster_items(items, threshold=threshold)
    objects = [
        build_intelligence_object(c, processing_version=processing_version)
        for c in clusters
    ]
    multi = [c for c in clusters if len(c) > 1]
    report = {
        "documents_in": len(items),
        "objects_out": len(objects),
        "clusters_merged": len(multi),
        "documents_consolidated": sum(len(c) for c in multi) - len(multi),
        "threshold": threshold,
        "merges": audit,
    }
    return objects, report
