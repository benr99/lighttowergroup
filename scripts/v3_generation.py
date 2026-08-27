"""Turn selected intelligence objects into articles, in parallel and on budget.

This is the join that was missing. v3 chose stories and wrote them to a file;
the writer took its input from the v2 path; nothing connected the two, so a run
that selected 47 good stories still published nothing.

Two problems had to be solved together.

Time
    Each article passes seven model stages and takes roughly five to six
    minutes. Forty-seven articles in series is about four and a half hours
    against a two-hour job limit. They are written concurrently instead, which
    is safe because each article is independent -- the only shared state is the
    budget, and that is locked.

Ambition
    The old path asked for deep analysis of everything and was refused for
    claims it could not support. Depth is now taken from the object, which
    already capped it by evidence: a summary-only story is written as a brief
    that says what happened, a corroborated one earns the full treatment. The
    fact checker stops being an obstacle because nothing overreaches.

Nothing here publishes. It returns drafts and a report.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from intelligence_object import EvidenceLevel, IntelligenceObject

#: Written concurrently. Six is a compromise: enough to fit the job window,
#: few enough to stay inside provider rate limits with retries in hand.
DEFAULT_WORKERS = 6

#: Rough cost of one article, used to ask the budget before starting rather
#: than discovering halfway through that the money ran out.
ESTIMATED_USD_PER_ARTICLE = {"tier_a": 0.12, "tier_b": 0.07, "tier_c": 0.03}

#: What each depth is allowed to attempt. `format` is the contract the existing
#: editorial pipeline already understands.
DEPTH_SPEC = {
    "tier_a": {"format": "flagship", "min_words": 750, "max_words": 1400},
    "tier_b": {"format": "analysis", "min_words": 400, "max_words": 800},
    "tier_c": {"format": "brief", "min_words": 180, "max_words": 380},
}


@dataclass
class DraftResult:
    object_id: str = ""
    title: str = ""
    sector: str = ""
    depth: str = ""
    status: str = "pending"
    article: dict[str, Any] | None = None
    stages_run: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    seconds: float = 0.0
    usd: float = 0.0
    skipped_reason: str = ""

    #: What the editorial pipeline actually returns on success. Checking for
    #: "complete" instead of "completed" made a run report 0 written when seven
    #: articles had in fact been produced.
    SUCCESS_STATUSES = frozenset({"completed", "revised"})

    @property
    def ok(self) -> bool:
        return bool(self.article) and self.status in self.SUCCESS_STATUSES

    @property
    def needs_review(self) -> bool:
        """Written, but the pipeline wants a human to look before publishing."""
        return self.status == "review_required" and bool(self.article)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        data["needs_review"] = self.needs_review
        data.pop("article", None)  # drafts are returned separately, not in the report
        return data


@dataclass
class GenerationReport:
    requested: int = 0
    written: int = 0
    needs_review: int = 0
    held: int = 0
    skipped_budget: int = 0
    failed: int = 0
    elapsed_seconds: float = 0.0
    usd: float = 0.0
    by_depth: dict[str, int] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def object_to_canonical(obj: IntelligenceObject) -> Any:
    """Rebuild the CanonicalItem shape the editorial pipeline expects."""
    from canonical_item import CanonicalItem

    primary = obj.sources[0] if obj.sources else None
    item = CanonicalItem(
        item_id=obj.object_id,
        headline=obj.title,
        raw_summary=obj.what_happened,
        source_name=(primary.source_name if primary else ""),
        source_url=(primary.canonical_url or primary.source_url) if primary else "",
        canonical_url=(primary.canonical_url if primary else ""),
        publication_date=(primary.publication_date if primary else ""),
        source_tier=(primary.source_tier if primary else 3),
        source_authority="primary" if obj.primary_source_count else "secondary",
        primary_sector=obj.primary_sector,
        secondary_sectors=list(obj.secondary_sectors),
        subsector=obj.primary_subsector,
        event_type=obj.event_type,
    )
    item.companies = [e.get("name", "") for e in obj.entities if e.get("name")]
    return item


def _stage_diagnostics(stages: Any) -> dict[str, Any]:
    """Persist gate decisions without duplicating complete generated articles."""
    if not isinstance(stages, dict):
        return {}
    allowed = {
        "status", "passed", "score_1_10", "summary", "issues", "reason",
        "opening_quality", "worst_sentence", "error",
    }
    diagnostics: dict[str, Any] = {}
    for name, payload in stages.items():
        if not isinstance(payload, dict):
            continue
        diagnostics[str(name)] = {
            key: value for key, value in payload.items() if key in allowed
        }
    return diagnostics


def object_to_dossier(obj: IntelligenceObject) -> dict[str, Any]:
    """Assemble the evidence the writer is permitted to use.

    Only what the object actually holds. The dossier is the factual boundary,
    so anything absent here is something the article may not assert.
    """
    sources = [
        {
            "name": ref.source_name,
            "source": ref.source_name,
            "url": ref.canonical_url or ref.source_url,
            "published": ref.publication_date,
            "authority": "primary" if ref.is_primary_authority else "secondary",
            "tier": ref.source_tier,
            "source_tier": ref.source_tier,
            "is_primary": ref.is_primary_authority,
            "retrieval": ref.retrieval_status,
            "chars": ref.text_chars,
            "text": ref.retrieved_text,
            "full_text_excerpt": ref.retrieved_text,
            "summary": obj.what_happened if index == 0 else "",
            "reported_facts": [
                fact.to_dict() for fact in obj.facts if fact.source_item_id == ref.item_id
            ],
        }
        for index, ref in enumerate(obj.sources)
    ]
    facts = [
        {
            "name": fact.name,
            "value": fact.value,
            "unit": fact.unit,
            "evidence": fact.evidence_span,
            "corroborated": fact.is_corroborated,
            "is_inference": fact.is_inference,
        }
        for fact in obj.facts
    ]
    try:
        from fact_extractor import extract_facts
        source_facts = extract_facts("\n".join(ref.retrieved_text for ref in obj.sources))
    except Exception:  # noqa: BLE001
        source_facts = {}
    return {
        "event_id": obj.object_id,
        "title": obj.title,
        "what_happened": obj.what_happened,
        "sector": obj.primary_sector,
        "subsector": obj.primary_subsector,
        "event_type": obj.event_type,
        "sources": sources,
        "facts": facts,
        "reported_facts": facts,
        "source_facts": source_facts,
        "material_claims": list(obj.material_claims),
        "market_consequences": list(obj.market_consequences),
        "missing_information": list(obj.missing_information),
        "reporting_gaps": list(obj.missing_information),
        "evidence_level": obj.evidence_level,
        "independent_source_count": obj.independent_source_count,
        "primary_source_count": obj.primary_source_count,
        "usable_full_text_count": obj.usable_full_text_count,
        "novelty": obj.novelty_state,
        "prior_coverage": list(obj.prior_published_slugs),
        "material_changes": list(obj.material_changes),
        "longform_allowed": (
            obj.independent_source_count >= 3 and obj.usable_full_text_count >= 2
        ),
        "evidence_level_note": (
            "Single feed summary only. State what happened and stop; do not "
            "advance a thesis this cannot support."
            if obj.evidence_level == EvidenceLevel.SINGLE_SUMMARY
            else "Corroborated across independent sources; analysis is supportable."
            if obj.evidence_level in (EvidenceLevel.CORROBORATED, EvidenceLevel.PRIMARY_CORROBORATED)
            else "One source read in full; analysis must stay close to it."
        ),
    }


def write_one(
    obj: IntelligenceObject,
    *,
    api_key: str = "",
    provider: dict[str, Any] | None = None,
    budget: Any = None,
) -> DraftResult:
    """Write a single article. Never raises."""
    depth = obj.recommended_depth or "tier_c"
    spec = DEPTH_SPEC.get(depth, DEPTH_SPEC["tier_c"])
    result = DraftResult(
        object_id=obj.object_id, title=obj.title,
        sector=obj.primary_sector, depth=depth,
    )
    started = time.perf_counter()

    if depth == "none":
        result.status = "skipped"
        result.skipped_reason = "evidence does not support any coverage"
        return result

    estimate = ESTIMATED_USD_PER_ARTICLE.get(depth, 0.05)
    if budget is not None and not budget.allow(
        "generation", estimated_usd=estimate, article_id=obj.object_id
    ):
        result.status = "skipped"
        result.skipped_reason = "daily budget exhausted"
        return result

    try:
        from editorial_pipeline import run_editorial_pipeline

        outcome = run_editorial_pipeline(
            object_to_canonical(obj),
            dossier=object_to_dossier(obj),
            api_key=api_key,
            provider=provider,
            article_format=spec["format"],
        )
        result.status = outcome.get("status", "unknown")
        result.article = outcome.get("article")
        result.stages_run = list(outcome.get("stages_run") or outcome.get("stages", {}).keys())
        result.errors = list(outcome.get("errors") or [])
        result.diagnostics = _stage_diagnostics(outcome.get("stages"))
        if result.article and not result.article.get("format"):
            result.article["format"] = spec["format"]
    except Exception as exc:  # noqa: BLE001
        result.status = "failed"
        result.errors.append(f"{type(exc).__name__}: {exc}"[:200])

    result.seconds = round(time.perf_counter() - started, 1)
    if budget is not None:
        # The pipeline does not report tokens, so charge the estimate. Better to
        # over-count than to discover the ceiling was fictional.
        result.usd = budget.record(
            "generation", usd=estimate, seconds=result.seconds, article_id=obj.object_id
        )
    return result


def write_all(
    objects: Sequence[IntelligenceObject],
    *,
    api_key: str = "",
    provider: dict[str, Any] | None = None,
    budget: Any = None,
    workers: int = DEFAULT_WORKERS,
    deadline_s: float | None = None,
    verbose: bool = True,
) -> tuple[list[DraftResult], GenerationReport]:
    """Write every selected story concurrently, within time and budget."""
    objects = list(objects)
    report = GenerationReport(requested=len(objects))
    results: list[DraftResult] = []
    if not objects:
        return results, report

    started = time.perf_counter()
    # Deepest first: if time or money runs out, the most important stories are
    # already written rather than the cheapest.
    order = {"tier_a": 0, "tier_b": 1, "tier_c": 2, "none": 3}
    ordered = sorted(
        objects, key=lambda o: (order.get(o.recommended_depth, 3), -o.final_score)
    )

    printed = threading.Lock()

    def _task(obj: IntelligenceObject) -> DraftResult:
        if deadline_s is not None and time.perf_counter() - started > deadline_s:
            out = DraftResult(
                object_id=obj.object_id, title=obj.title,
                sector=obj.primary_sector, depth=obj.recommended_depth,
                status="skipped", skipped_reason="generation window closed",
            )
            return out
        out = write_one(obj, api_key=api_key, provider=provider, budget=budget)
        if verbose:
            with printed:
                mark = "ok " if out.ok else out.status[:4]
                print(f"    [{mark}] {out.depth:7} {out.seconds:5.0f}s  {out.title[:58]}",
                      flush=True)
        return out

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(_task, obj): obj for obj in ordered}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                obj = futures[future]
                results.append(DraftResult(
                    object_id=obj.object_id, title=obj.title, status="failed",
                    errors=[f"{type(exc).__name__}: {exc}"[:200]],
                ))

    for item in results:
        report.by_depth[item.depth] = report.by_depth.get(item.depth, 0) + 1
        report.usd += item.usd
        if item.ok:
            report.written += 1
        elif item.needs_review:
            report.needs_review += 1
        elif item.status == "skipped":
            report.skipped_budget += 1
        elif item.status in {"failed", "draft_failed", "revision_failed"} or item.status.endswith("_failed"):
            report.failed += 1
        else:
            report.held += 1

    report.usd = round(report.usd, 4)
    report.elapsed_seconds = round(time.perf_counter() - started, 1)
    report.results = [r.to_dict() for r in results]
    return results, report


def summarise(report: GenerationReport) -> str:
    lines = [
        f"  wrote {report.written}/{report.requested} in {report.elapsed_seconds:.0f}s"
        f"  (${report.usd:.3f})",
    ]
    if report.needs_review:
        lines.append(f"    {report.needs_review} written but flagged for review")
    if report.held:
        lines.append(f"    {report.held} held by the quality gates")
    if report.failed:
        lines.append(f"    {report.failed} failed")
    if report.skipped_budget:
        lines.append(f"    {report.skipped_budget} skipped on budget or time")
    if report.by_depth:
        lines.append(f"    depth {report.by_depth}")
    return "\n".join(lines)
