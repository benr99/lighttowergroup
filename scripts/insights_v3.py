"""The v3 editorial pipeline, end to end.

Eight modules were built separately and tested separately. This runs them as one
pass, which is the only way the design actually delivers anything:

    ingest      RSS feeds, plus index pages for publications with no feed
    classify    sector, using the existing v2 classifier
    cluster     documents reporting one event become one intelligence object
    typing      what each thing IS -- news, explainer, interview, filing
    eligibility per-event-family rules, not one keyword gate
    enrich      read the actual articles, so evidence stops being a summary;
                recover borderline rejects and re-run the gate on the body
    score       0-100, every measure varying, every score explaining itself
    select      broad scouting slates plus a capped global publication slate

Order matters and is not arbitrary. A bounded discovery read runs after the
initial cheap gate: clearly invalid content is excluded, while borderline
objects are read and re-evaluated against the retrieved article. Enrichment
runs before final scoring because evidence strength is itself a scored measure
and depth is capped by it.

Shadow by default. Preview writes drafts but never public files. Publish mode is
explicit and uses the tested v3 publisher; production remains on v2 until the
workflow cutover is approved.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from intelligence_object import ContentType, IntelligenceObject

SITE_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = SITE_ROOT / ".editorial-state"

PIPELINE_VERSION = "v3.0"

#: Enrichment is the expensive step, so it is bounded twice: by how many
#: candidates may be read at all, and by a wall-clock budget for the phase.
# Set above the typical eligible count deliberately. Reading 60 of 171 eligible
# candidates left `evidence` with no discriminating power and cost real
# coverage: raising it to read them all took selections from 29 to 47, evidence
# upgrades from 30 to 78, and lifted every short sector -- for five extra
# seconds. Retrieval is cheap; the model calls that follow are not, which is why
# the budget guards those rather than this.
DEFAULT_ENRICH_LIMIT = 250
DEFAULT_ENRICH_BUDGET_S = 420
DEFAULT_LISTING_LIMIT = 12


def _is_readable_discovery_candidate(obj: IntelligenceObject) -> bool:
    """Return whether a borderline object merits one bounded article read.

    The cheap gate has already classified permanent junk. Those objects must
    not consume retrieval budget. Everything else can be a legitimate event
    whose RSS summary was too thin for a final eligibility decision.
    """
    return obj.content_type not in ContentType.NEVER_ELIGIBLE


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
    publication_candidates: int = 0
    daily_target: int = 3
    article_limit: int = 5
    daily_target_met: bool = False
    sectors: dict[str, Any] = field(default_factory=dict)
    depth_counts: dict[str, int] = field(default_factory=dict)
    shortfalls: list[str] = field(default_factory=list)
    degenerate_measures: list[str] = field(default_factory=list)
    score_distribution: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=dict)
    novelty: dict[str, int] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    spend: dict[str, Any] = field(default_factory=dict)
    generation: dict[str, Any] = field(default_factory=dict)
    publication: dict[str, Any] = field(default_factory=dict)
    provider: dict[str, Any] = field(default_factory=dict)
    timings: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
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
    pipeline: str = "v3",
    mode: str = "shadow",
    sectors: Sequence[str] | None = None,
    enrich_limit: int = DEFAULT_ENRICH_LIMIT,
    enrich_budget_s: int = DEFAULT_ENRICH_BUDGET_S,
    listing_limit: int = DEFAULT_LISTING_LIMIT,
    items: Sequence[Any] | None = None,
    generate: bool = False,
    publish_articles: bool = False,
    include_review_required: bool = False,
    daily_target: int = 3,
    article_limit: int = 5,
    quality_floor: float = 40.0,
    generation_workers: int = 6,
    generation_deadline_s: float = 3600,
    verbose: bool = True,
    state_dir: Path | None = None,
    budget: Any = None,
    memory: Any = None,
) -> tuple[RunReport, Any]:
    """Run the full v3 pass. Returns (report, slate_report).

    `items` lets a caller supply pre-ingested documents, which is how tests and
    shadow comparisons avoid hitting the network.
    """
    from budget import Budget
    from classification import classify_batch
    from editorial_memory import EditorialMemory
    from event_clustering import cluster_to_objects
    from importance import distribution_report, score_all
    from selection import MAX_DAILY_ARTICLES, build_slates
    import eligibility
    from model_router import configure_state_dir

    if pipeline not in {"v3", "v4"}:
        raise ValueError(f"unsupported pipeline: {pipeline}")
    if mode not in {"shadow", "preview", "publish"}:
        raise ValueError(f"unsupported v3 mode: {mode}")
    if mode == "shadow" and (generate or publish_articles):
        raise ValueError("shadow mode cannot generate or publish")
    if mode == "preview" and publish_articles:
        raise ValueError("preview mode cannot publish")
    if publish_articles and not generate:
        raise ValueError("publishing requires generation")
    if mode == "preview":
        generate = True
    if mode == "publish":
        generate = True
        publish_articles = True

    # Keep preview/test diagnostics out of production durable state. Production
    # runs without an override explicitly reset the router to the canonical
    # repository state directory in case this function is reused in-process.
    configure_state_dir(state_dir)

    daily_target = max(0, min(int(daily_target), MAX_DAILY_ARTICLES))
    article_limit = max(daily_target, min(int(article_limit), MAX_DAILY_ARTICLES))

    started = time.perf_counter()
    report = RunReport(
        run_at=_now(), pipeline_version=("v4.0" if pipeline == "v4" else PIPELINE_VERSION), mode=mode,
        daily_target=daily_target, article_limit=article_limit,
    )
    budget = budget or Budget(
        ledger_path=(state_dir / "spend-ledger.json") if state_dir is not None else None
    )
    store = None
    slate_report = None
    drafts: list[Any] = []
    pub_report = None
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
                        report.warnings.append(f"{blocked} index page(s) refused our agent")
            except Exception as exc:  # noqa: BLE001
                report.warnings.append(f"listing read failed: {type(exc).__name__}: {exc}"[:200])
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

    # ── memory ─────────────────────────────────────────────────────────────
    # Runs before scoring because novelty is one of the scored measures, and
    # before enrichment so budget is never spent reading a story we published.
    with stage("check against what we covered"):
        try:
            store = memory if memory is not None else EditorialMemory(
                path=(state_dir / "editorial-memory.json") if state_dir is not None else None
            )
            if not store.records:
                seeded = store.seed_from_manifest()
                if seeded:
                    report.memory["seeded_from_archive"] = seeded
            report.novelty = store.apply(objects)
            report.memory.update(store.report())
        except Exception as exc:  # noqa: BLE001
            store = None
            report.errors.append(f"memory failed: {type(exc).__name__}: {exc}"[:200])

    # ── enrich ─────────────────────────────────────────────────────────────
    # The initial eligibility pass is intentionally cheap, but it cannot be the
    # final authority: many borderline objects fail only because their RSS
    # summary omits the beat anchor, transaction amount, or action verb that is
    # present in the article body. Read approved objects plus a bounded set of
    # recoverable rejects, then re-run the gate using retrieved text. Permanent
    # exclusions (marketing, explainers, personnel notices, etc.) never enter
    # this discovery read.
    with stage("read the articles"):
        try:
            from retrieval import Retriever, enrich_objects

            from intelligence_object import NoveltyState

            stale = {NoveltyState.ALREADY_PUBLISHED, NoveltyState.DUPLICATE}
            candidates = [
                o for o in objects
                if o.novelty_state not in stale and _is_readable_discovery_candidate(o)
            ]
            # Keep the approved pool first, then use source tier as the cheap
            # tie-breaker for borderline rejects. The count and wall-clock
            # budget keep this from becoming an unbounded crawl.
            candidates.sort(key=lambda o: (
                0 if o.eligible else 1,
                min((s.source_tier for s in o.sources), default=9),
                -o.final_score,
                o.title,
            ))
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
                for obj in shortlist:
                    if obj.eligible:
                        continue
                    body = "\n".join(
                        ref.retrieved_text[:12_000]
                        for ref in obj.sources
                        if ref.retrieved_text
                    )
                    if body:
                        eligibility.apply(obj, text=f"{obj.title}\n{obj.what_happened}\n{body}")
                report.eligible = sum(1 for o in objects if o.eligible)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"enrichment failed: {type(exc).__name__}: {exc}"[:200])

    # ── score ──────────────────────────────────────────────────────────────
    with stage("score importance"):
        score_all(objects)
        distribution = distribution_report(objects)
        report.degenerate_measures = distribution.get("degenerate", [])
        report.score_distribution = distribution.get("final_score", {})
        if report.degenerate_measures:
            report.warnings.append(
                "scoring measures with no discriminating power: "
                + ", ".join(report.degenerate_measures)
            )

    # ── select ─────────────────────────────────────────────────────────────
    with stage("choose the slates"):
        slate_report = build_slates(
            objects,
            sectors=sectors,
            floor=quality_floor,
            publication_target=daily_target,
            article_limit=article_limit,
        )
        report.selected = slate_report.total_selected
        report.publication_candidates = len(slate_report.publication_slate)
        report.daily_target_met = slate_report.publication_target_met
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

    # ── write ──────────────────────────────────────────────────────────────
    # Off by default. When on, the selected slate is written concurrently at the
    # depth each story's evidence earned. Still returns drafts rather than
    # publishing them.
    if generate and slate_report is not None:
        with stage("write the slate"):
            try:
                from model_router import select_provider
                if pipeline == "v4":
                    from v4_generation import summarise, write_all
                else:
                    from v3_generation import summarise, write_all

                # Per-sector slates are scouting diagnostics. Only the bounded
                # global publication slate may consume model calls or reach the
                # site.
                chosen = list(slate_report.publication_slate)
                provider = None
                api_key = ""
                try:
                    provider = select_provider(for_writing=True)
                    api_key = provider.get("api_key", "")
                    report.provider = {
                        key: provider.get(key)
                        for key in ("provider", "model", "fallback", "purpose")
                    }
                except Exception as exc:  # noqa: BLE001
                    report.errors.append(f"no writing provider: {type(exc).__name__}")

                if api_key:
                    generation_kwargs = {
                        "provider": provider,
                        "budget": budget,
                        "deadline_s": (720 if pipeline == "v4" else generation_deadline_s),
                        "verbose": verbose,
                        "state_dir": state_dir,
                        "run_id": report.run_at,
                    }
                    if pipeline == "v4":
                        generation_kwargs["article_budget_s"] = 240
                    else:
                        generation_kwargs.update({
                            "api_key": api_key,
                            "workers": generation_workers,
                        })
                    drafts, gen_report = write_all(chosen, **generation_kwargs)
                    report.generation = gen_report.to_dict()
                    if gen_report.failed:
                        message = (
                            f"{gen_report.failed} of {gen_report.requested} article generations failed"
                        )
                        if gen_report.written == 0 and gen_report.needs_review == 0:
                            report.errors.append(message)
                        else:
                            report.warnings.append(message)
                    if verbose:
                        print(summarise(gen_report), flush=True)
                else:
                    report.generation = {"skipped": "no API key available"}
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"generation failed: {type(exc).__name__}: {exc}"[:200])

    # -- publish -------------------------------------------------------------
    # Explicit and off in shadow/preview. The publisher is idempotent and holds
    # review-required work unless a human deliberately overrides that behavior.
    if publish_articles:
        with stage("publish"):
            try:
                from v3_publish import publish as publish_drafts
                from v3_publish import summarise as summarise_publish

                by_id = {o.object_id: o for o in objects}
                pub_report = publish_drafts(
                    drafts,
                    by_id,
                    memory=store,
                    include_review_required=include_review_required,
                )
                report.publication = pub_report.to_dict()
                if pub_report.failed:
                    message = f"{pub_report.failed} publication operation(s) failed"
                    if pub_report.published == 0:
                        report.errors.append(message)
                    else:
                        report.warnings.append(message)
                if pub_report.published < daily_target:
                    report.warnings.append(
                        f"published {pub_report.published} of the daily target {daily_target}"
                    )
                if verbose:
                    print(summarise_publish(pub_report), flush=True)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"publish failed: {type(exc).__name__}: {exc}"[:200])

    with stage("record what we saw"):
        try:
            if store is not None:
                store.observe(objects)
                store.save()
                report.memory.update(store.report())
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"memory write failed: {type(exc).__name__}"[:120])

    budget.persist()
    report.spend = budget.report()
    try:
        from model_router import provider_summary
        report.provider.update(provider_summary(since=report.run_at))
    except Exception:  # noqa: BLE001
        pass
    report.timings = [t.to_dict() for t in timings]
    report.elapsed_seconds = round(time.perf_counter() - started, 2)

    _write_artifacts(report, slate_report, objects, drafts=drafts, state_dir=state_dir)
    if publish_articles and pub_report is not None:
        try:
            from v3_publish import finalize_publication

            finalize_publication(
                pub_report,
                report,
                slate_report,
                objects,
                memory=store,
                budget=budget,
                state_dir=state_dir,
            )
            report.publication = pub_report.to_dict()
        except Exception as exc:  # noqa: BLE001
            report.errors.append(
                f"publication finalization failed: {type(exc).__name__}: {exc}"[:400]
            )
        _write_artifacts(report, slate_report, objects, drafts=drafts, state_dir=state_dir)
    if verbose:
        print(format_summary(report), flush=True)
    return report, slate_report


def _write_artifacts(
    report: RunReport,
    slate_report: Any,
    objects: Sequence[Any],
    *,
    drafts: Sequence[Any] = (),
    state_dir: Path | None = None,
) -> None:
    """Persist the run so a decision can be inspected afterwards.

    `state_dir` is overridable so tests never overwrite the artifacts a real run
    left behind -- which they were doing, making the last live run unreadable.
    """
    target = state_dir or STATE_DIR
    try:
        target.mkdir(parents=True, exist_ok=True)
        (target / "v3-run.json").write_text(
            json.dumps(report.to_dict(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if slate_report is not None:
            (target / "v3-slates.json").write_text(
                json.dumps(slate_report.to_dict(), indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        # Every candidate, not just the chosen ones -- the audit gap that made
        # the previous ranker impossible to diagnose after the fact.
        (target / "v3-candidates.json").write_text(
            json.dumps(
                {
                    "run_at": report.run_at,
                    "pipeline_version": report.pipeline_version,
                    "count": len(objects),
                    "candidates": [o.to_dict() for o in objects],
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if drafts:
            (target / "v3-drafts.json").write_text(
                json.dumps(
                    {
                        "run_at": report.run_at,
                        "pipeline_version": report.pipeline_version,
                        "count": len(drafts),
                        "drafts": [
                            {**draft.to_dict(), "article": draft.article}
                            for draft in drafts
                        ],
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
        f"    publication    {report.publication_candidates}/{report.article_limit} candidates"
        f"  (daily target {report.daily_target}; met {str(report.daily_target_met).lower()})",
    ]
    if report.score_distribution:
        d = report.score_distribution
        lines.append(
            f"    scores         {d.get('min')}-{d.get('max')} of 100"
            f"  (mean {d.get('mean')}, range used {d.get('range_used')})"
        )
    if report.depth_counts:
        lines.append(f"    depth          {report.depth_counts}")
    if report.novelty:
        lines.append(f"    novelty        {report.novelty}")
    if report.provider:
        lines.append(
            f"    provider       {report.provider.get('provider', 'not selected')}"
            f"/{report.provider.get('model', '')}"
            f"  ({report.provider.get('successful_calls', 0)} calls,"
            f" {report.provider.get('fallback_calls', 0)} fallback)"
        )
    if report.generation and report.generation.get("requested"):
        g = report.generation
        lines.append(
            f"    written        {g.get('written', 0)}/{g.get('requested', 0)}"
            f"  in {g.get('elapsed_seconds', 0):.0f}s"
            f"  (held {g.get('held', 0)}, failed {g.get('failed', 0)})"
        )
    if report.publication:
        p = report.publication
        lines.append(
            f"    published      {p.get('published', 0)}/{p.get('requested', 0)}"
            f"  ({p.get('skipped_review', 0)} held for review,"
            f" {p.get('skipped_existing', 0)} already live)"
        )
    if report.spend:
        s = report.spend
        lines.append(
            f"    spend          ${s.get('spent_this_run_usd', 0):.3f} this run, "
            f"${s.get('spent_today_usd', 0):.3f} of ${s.get('daily_limit_usd', 0):.2f} today"
        )
    for sector, data in sorted(report.sectors.items()):
        flag = "  <- short" if data["shortfall_reason"] else ""
        lines.append(
            f"      {sector:24} {data['selected']}/{data['target']}"
            f"   eligible {data['eligible']}/{data['considered']}{flag}"
        )
    if report.degenerate_measures:
        lines.append(f"    WARNING: dead measures {report.degenerate_measures}")
    for warning in report.warnings[:5]:
        lines.append(f"    ~ {warning}")
    for err in report.errors[:5]:
        lines.append(f"    ! {err}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the editorial pipeline")
    parser.add_argument("--pipeline", default="v3", choices=["v3", "v4"],
                        help="generation engine; v4 is the bounded single-writer path")
    parser.add_argument("--mode", default="shadow", choices=["shadow", "preview", "publish"],
                        help="shadow scores, preview writes drafts, publish updates the site")
    parser.add_argument("--enrich-limit", type=int, default=DEFAULT_ENRICH_LIMIT)
    parser.add_argument("--enrich-budget", type=int, default=DEFAULT_ENRICH_BUDGET_S)
    parser.add_argument("--listing-limit", type=int, default=DEFAULT_LISTING_LIMIT)
    parser.add_argument("--sector", action="append", dest="sectors")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--daily-target", type=int, default=3)
    parser.add_argument("--article-limit", type=int, default=5,
                        help="maximum publication slate; v4 workflow uses 70 (10 per sector)")
    parser.add_argument("--quality-floor", type=float, default=40.0)
    parser.add_argument("--include-review", action="store_true",
                        help="manual only: include drafts flagged for editorial review")
    parser.add_argument("--state-dir", type=Path,
                        help="operator/testing override for run artifacts and durable state")
    args = parser.parse_args()

    report, _ = run(
        pipeline=args.pipeline,
        mode=args.mode,
        sectors=args.sectors,
        enrich_limit=args.enrich_limit,
        enrich_budget_s=args.enrich_budget,
        listing_limit=args.listing_limit,
        generate=args.mode in {"preview", "publish"},
        publish_articles=args.mode == "publish",
        include_review_required=args.include_review,
        daily_target=args.daily_target,
        article_limit=args.article_limit,
        quality_floor=args.quality_floor,
        generation_workers=args.workers,
        state_dir=args.state_dir,
    )
    # Shadow is diagnostic and may report weak measures without taking down the
    # production v2 edition. Preview and publish must fail visibly on real errors.
    return 0 if not report.errors or args.mode == "shadow" else 1


if __name__ == "__main__":
    raise SystemExit(main())
