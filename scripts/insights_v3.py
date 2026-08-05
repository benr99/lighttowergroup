"""The v3 editorial pipeline, end to end.

Eight modules were built separately and tested separately. This runs them as one
pass, which is the only way the design actually delivers anything:

    ingest      RSS feeds, plus index pages for publications with no feed
    classify    sector, using the existing v2 classifier
    cluster     documents reporting one event become one intelligence object
    typing      what each thing IS -- news, explainer, interview, filing
    eligibility per-event-family rules, not one keyword gate
    enrich      read the actual articles, so evidence stops being a summary
    score       0-100, every measure varying, every score explaining itself
    select      ten per sector against a real quality floor, plus a global slate

Order matters and is not arbitrary. Enrichment runs *after* eligibility so the
expensive reading is spent only on candidates that could plausibly be published;
it runs *before* scoring because evidence strength is itself a scored measure and
depth is capped by it.

Shadow by default. `run()` writes artifacts and returns a report; it never
publishes. Production selection still belongs to v2 until a cutover is approved.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

SITE_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = SITE_ROOT / ".editorial-state"

PIPELINE_VERSION = "v3.0"

#: Enrichment is the expensive step, so it is bounded twice: by how many
#: candidates may be read at all, and by a wall-clock budget for the phase.
DEFAULT_ENRICH_LIMIT = 60
DEFAULT_ENRICH_BUDGET_S = 240
DEFAULT_LISTING_LIMIT = 12


@dataclass
class StageTiming:
    name: str = ""
    seconds: float = 0.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"stage": self.name, "seconds": round(self.seconds, 2), "note": self.note}


@dataclass
class RunReport:
    run_at: str = ""
    pipeline_version: str = PIPELINE_VERSION
    mode: str = "shadow"
    documents_ingested: int = 0
    documents_from_feeds: int = 0
    documents_from_listings: int = 0
    objects_after_clustering: int = 0
    documents_consolidated: int = 0
    eligible: int = 0
    enriched: int = 0
    evidence_upgraded: int = 0
    selected: int = 0
    sectors: dict[str, Any] = field(default_factory=dict)
    depth_counts: dict[str, int] = field(default_factory=dict)
    shortfalls: list[str] = field(default_factory=list)
    degenerate_measures: list[str] = field(default_factory=list)
    score_distribution: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=dict)
    timings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _listing_sources(limit: int) -> list[dict[str, Any]]:
    """Active sources marked as index pages rather than feeds."""
    try:
        config = json.loads((SITE_ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for source in config.get("sources", []):
        if not source.get("active"):
            continue
        if source.get("source_type") != "html_listing":
            continue
        out.append({"name": source.get("name"), "url": source.get("listing_url") or source.get("url")})
        if len(out) >= limit:
            break
    return out


def run(
    *,
    mode: str = "shadow",
    sectors: Sequence[str] | None = None,
    enrich_limit: int = DEFAULT_ENRICH_LIMIT,
    enrich_budget_s: int = DEFAULT_ENRICH_BUDGET_S,
    listing_limit: int = DEFAULT_LISTING_LIMIT,
    items: Sequence[Any] | None = None,
    verbose: bool = True,
) -> tuple[RunReport, Any]:
    """Run the full v3 pass. Returns (report, slate_report).

    `items` lets a caller supply pre-ingested documents, which is how tests and
    shadow comparisons avoid hitting the network.
    """
    from classification import classify_batch
    from event_clustering import cluster_to_objects
    from importance import distribution_report, score_all
    from selection import build_slates
    import eligibility

    started = time.perf_counter()
    report = RunReport(run_at=_now(), mode=mode)
    timings: list[StageTiming] = []

    def stage(name: str):
        class _Timer:
            def __enter__(self):
                self.t0 = time.perf_counter()
                if verbose:
                    print(f"[v3] {name} ...", flush=True)
                return self
            def __exit__(self, *exc):
                timing = StageTiming(name=name, seconds=time.perf_counter() - self.t0)
                timings.append(timing)
                return False
        return _Timer()

    # ── ingest ─────────────────────────────────────────────────────────────
    documents: list[Any] = list(items) if items is not None else []
    if items is None:
        with stage("ingest feeds"):
            try:
                from ingestion import fetch_all_sources
                documents = list(fetch_all_sources())
                report.documents_from_feeds = len(documents)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"feed ingestion failed: {type(exc).__name__}: {exc}"[:200])

        with stage("read index pages"):
            try:
                from html_listing import read_listings, to_canonical_items
                sources = _listing_sources(listing_limit)
                if sources:
                    listing_items, listing_reports = read_listings(sources, max_items_per_source=15)
                    converted = to_canonical_items(listing_items)
                    documents.extend(converted)
                    report.documents_from_listings = len(converted)
                    blocked = sum(1 for r in listing_reports if r.status == "blocked")
                    if blocked:
                        report.errors.append(f"{blocked} index page(s) refused our agent")
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"listing read failed: {type(exc).__name__}: {exc}"[:200])
    else:
        report.documents_from_feeds = len(documents)

    report.documents_ingested = len(documents)
    if not documents:
        report.errors.append("no documents ingested; nothing to do")
        report.elapsed_seconds = round(time.perf_counter() - started, 2)
        report.timings = [t.to_dict() for t in timings]
        return report, None

    # ── classify ───────────────────────────────────────────────────────────
    with stage("classify sectors"):
        try:
            documents = classify_batch(documents)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"classification failed: {type(exc).__name__}: {exc}"[:200])

    # ── cluster ────────────────────────────────────────────────────────────
    with stage("cluster into events"):
        objects, cluster_report = cluster_to_objects(
            documents, processing_version=PIPELINE_VERSION
        )
        report.objects_after_clustering = len(objects)
        report.documents_consolidated = cluster_report.get("documents_consolidated", 0)

    # ── typing + eligibility ───────────────────────────────────────────────
    with stage("type and gate"):
        for obj in objects:
            try:
                eligibility.apply(obj)
            except Exception as exc:  # noqa: BLE001
                obj.eligible = False
                obj.eligibility_reason = f"gate error: {type(exc).__name__}"
                report.errors.append(f"eligibility failed for {obj.title[:40]!r}")
        report.eligible = sum(1 for o in objects if o.eligible)

    # ── enrich ─────────────────────────────────────────────────────────────
    # Only eligible candidates are worth reading, and only the strongest of
    # those if the budget is tight. Ranking by source tier is a cheap proxy
    # before any score exists.
    with stage("read the articles"):
        try:
            from retrieval import Retriever, enrich_objects

            candidates = [o for o in objects if o.eligible]
            candidates.sort(key=lambda o: min((s.source_tier for s in o.sources), default=9))
            shortlist = candidates[:enrich_limit]
            before = {o.object_id: o.evidence_level for o in shortlist}
            if shortlist:
                retrieval_report = enrich_objects(
                    shortlist,
                    retriever=Retriever(),
                    budget_seconds=enrich_budget_s,
                )
                report.retrieval = retrieval_report.to_dict()
                report.enriched = len(shortlist)
                report.evidence_upgraded = sum(
                    1 for o in shortlist if o.evidence_level != before[o.object_id]
                )
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"enrichment failed: {type(exc).__name__}: {exc}"[:200])

    # ── score ──────────────────────────────────────────────────────────────
    with stage("score importance"):
        score_all(objects)
        distribution = distribution_report(objects)
        report.degenerate_measures = distribution.get("degenerate", [])
        report.score_distribution = distribution.get("final_score", {})
        if report.degenerate_measures:
            report.errors.append(
                "scoring measures with no discriminating power: "
                + ", ".join(report.degenerate_measures)
            )

    # ── select ─────────────────────────────────────────────────────────────
    with stage("choose the slates"):
        slate_report = build_slates(objects, sectors=sectors)
        report.selected = slate_report.total_selected
        report.depth_counts = dict(slate_report.depth_counts)
        for sector, slate in slate_report.sectors.items():
            report.sectors[sector] = {
                "considered": slate.considered,
                "eligible": slate.eligible,
                "selected": len(slate.selected),
                "target": slate.target,
                "shortfall_reason": slate.shortfall_reason,
            }
            if slate.shortfall_reason:
                report.shortfalls.append(f"{sector}: {slate.shortfall_reason}")

    report.timings = [t.to_dict() for t in timings]
    report.elapsed_seconds = round(time.perf_counter() - started, 2)

    _write_artifacts(report, slate_report, objects)
    if verbose:
        print(format_summary(report), flush=True)
    return report, slate_report


def _write_artifacts(report: RunReport, slate_report: Any, objects: Sequence[Any]) -> None:
    """Persist the run so a decision can be inspected afterwards."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "v3-run.json").write_text(
            json.dumps(report.to_dict(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if slate_report is not None:
            (STATE_DIR / "v3-slates.json").write_text(
                json.dumps(slate_report.to_dict(), indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        # Every candidate, not just the chosen ones -- the audit gap that made
        # the previous ranker impossible to diagnose after the fact.
        (STATE_DIR / "v3-candidates.json").write_text(
            json.dumps(
                {
                    "run_at": report.run_at,
                    "pipeline_version": PIPELINE_VERSION,
                    "count": len(objects),
                    "candidates": [o.to_dict() for o in objects],
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"artifact write failed: {type(exc).__name__}")


def format_summary(report: RunReport) -> str:
    lines = [
        "",
        f"  v3 pipeline ({report.mode}) - {report.elapsed_seconds}s",
        f"    ingested       {report.documents_ingested}"
        f"  (feeds {report.documents_from_feeds}, index pages {report.documents_from_listings})",
        f"    clustered      {report.objects_after_clustering} objects"
        f"  ({report.documents_consolidated} duplicates consolidated)",
        f"    eligible       {report.eligible}",
        f"    read in full   {report.enriched}  ({report.evidence_upgraded} evidence upgrades)",
        f"    selected       {report.selected}",
    ]
    if report.score_distribution:
        d = report.score_distribution
        lines.append(
            f"    scores         {d.get('min')}-{d.get('max')} of 100"
            f"  (mean {d.get('mean')}, range used {d.get('range_used')})"
        )
    if report.depth_counts:
        lines.append(f"    depth          {report.depth_counts}")
    for sector, data in sorted(report.sectors.items()):
        flag = "  <- short" if data["shortfall_reason"] else ""
        lines.append(
            f"      {sector:24} {data['selected']}/{data['target']}"
            f"   eligible {data['eligible']}/{data['considered']}{flag}"
        )
    if report.degenerate_measures:
        lines.append(f"    WARNING: dead measures {report.degenerate_measures}")
    for err in report.errors[:5]:
        lines.append(f"    ! {err}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the v3 editorial pipeline (shadow)")
    parser.add_argument("--mode", default="shadow", choices=["shadow"],
                        help="only shadow is supported; v3 does not publish")
    parser.add_argument("--enrich-limit", type=int, default=DEFAULT_ENRICH_LIMIT)
    parser.add_argument("--enrich-budget", type=int, default=DEFAULT_ENRICH_BUDGET_S)
    parser.add_argument("--listing-limit", type=int, default=DEFAULT_LISTING_LIMIT)
    parser.add_argument("--sector", action="append", dest="sectors")
    args = parser.parse_args()

    report, _ = run(
        mode=args.mode,
        sectors=args.sectors,
        enrich_limit=args.enrich_limit,
        enrich_budget_s=args.enrich_budget,
        listing_limit=args.listing_limit,
    )
    return 0 if not report.errors else 0  # diagnostics never fail the caller


if __name__ == "__main__":
    raise SystemExit(main())
