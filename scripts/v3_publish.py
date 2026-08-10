"""Put finished drafts on the site.

The last link. Everything before this chooses stories and writes them; this puts
them where a reader can see them, using the same renderer, manifest and index
updates the existing path already uses. Nothing here reimplements page markup or
feed handling -- duplicating those is how two systems drift apart.

What it adds over the old path is the discipline an unattended system needs:

    idempotent      an article whose slug already exists is skipped, so a job
                    that runs twice does not publish twice
    atomic-ish      pages are written first and the indexes updated once at the
                    end, so a crash midway leaves orphan pages rather than a
                    manifest pointing at files that do not exist
    remembered      every published story is recorded in editorial memory, so
                    tomorrow's run knows not to write it again
    reversible      returns the exact list of files touched, which is what a
                    rollback needs

Publishing is off unless explicitly asked for.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

SITE_ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_DIR = SITE_ROOT / "insights"
MANIFEST_PATH = SITE_ROOT / "insights.json"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


@dataclass
class PublishResult:
    object_id: str = ""
    slug: str = ""
    title: str = ""
    sector: str = ""
    depth: str = ""
    status: str = "pending"
    path: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PublishReport:
    requested: int = 0
    published: int = 0
    skipped_existing: int = 0
    skipped_review: int = 0
    failed: int = 0
    files_written: list[str] = field(default_factory=list)
    articles: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_slug(title: str, *, existing: set[str] | None = None) -> str:
    """A stable, readable slug that will not collide."""
    base = _SLUG_STRIP.sub("-", (title or "").lower()).strip("-")[:80].strip("-")
    if not base:
        base = "insight"
    if existing is None:
        return base
    slug, n = base, 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


def _article_payload(draft: Any, obj: Any, slug: str) -> dict[str, Any]:
    """Shape a draft into what render_html and update_manifest expect."""
    article = dict(draft.article or {})
    article.setdefault("title", obj.title)
    article["slug"] = slug
    article.setdefault("subtitle", article.get("excerpt", "")[:160])
    article.setdefault("meta_description", article.get("excerpt", "")[:200])
    article.setdefault("category", _category_for(obj.primary_sector))
    now = datetime.now(timezone.utc)
    article.setdefault("date_iso", now.isoformat())
    # The shared article renderer displays this human-readable field while its
    # structured data uses date_iso. v3 originally supplied only the latter,
    # so otherwise-valid production drafts failed at render time.
    article.setdefault("date", now.strftime("%B %d, %Y"))
    article.setdefault("tags", [t for t in (obj.primary_sector, obj.primary_subsector,
                                            obj.event_type) if t])
    article.setdefault(
        "editorial_format",
        article.get("format") or {
            "tier_a": "flagship", "tier_b": "analysis", "tier_c": "brief"
        }.get(draft.depth, "brief"),
    )
    article.setdefault("pipeline_version", "v3")
    article.setdefault("event_id", obj.object_id)
    article.setdefault("must_read_score", round(float(obj.final_score or 0)))
    article.setdefault("selection_tier", "v3_daily_slate")
    article.setdefault("research_evidence_level", obj.evidence_level)
    article.setdefault("research_usable_full_text_count", obj.usable_full_text_count)
    article.setdefault("research_reported_fact_count", len(obj.facts))
    article["source_count"] = obj.independent_source_count
    article["source_name"] = obj.sources[0].source_name if obj.sources else ""
    article["source_url"] = (
        obj.sources[0].canonical_url or obj.sources[0].source_url if obj.sources else ""
    )
    if not article.get("sources"):
        article["sources"] = [
            {"name": ref.source_name, "url": ref.canonical_url or ref.source_url}
            for ref in obj.sources
            if (ref.canonical_url or ref.source_url)
        ]
    return article


def _article_summary(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": article.get("event_id"),
        "title": article.get("title"),
        "slug": article.get("slug"),
        "url": f"/insights/{article.get('slug')}.html",
        "category": article.get("category"),
        "format": article.get("editorial_format", "brief"),
        "source_count": article.get("source_count", 0),
        "must_read_score": article.get("must_read_score", 0),
        "selection_tier": article.get("selection_tier", "v3_daily_slate"),
        "evidence_level": article.get("research_evidence_level", ""),
    }


def _write_related(article: dict[str, Any]) -> Path:
    """Write up to three useful archive links based on tag overlap."""
    from content_governance import load_insight_records

    tags = set(article.get("tags") or [])
    related: list[dict[str, Any]] = []
    for record in load_insight_records(SITE_ROOT):
        if record.get("slug") == article.get("slug"):
            continue
        overlap = len(tags & set(record.get("tags") or []))
        if overlap < 1:
            continue
        related.append({
            "title": record.get("title"),
            "slug": record.get("slug"),
            "url": record.get("url") or f"/insights/{record.get('slug')}.html",
            "overlap": overlap,
        })
    related.sort(key=lambda value: (-value["overlap"], str(value.get("title") or "")))
    path = INSIGHTS_DIR / f"{article['slug']}_related.json"
    path.write_text(json.dumps(related[:3], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


#: Sector keys are internal; the site's categories are reader-facing.
_CATEGORY = {
    "commercial_real_estate": "Deal Intelligence",
    "banking_credit": "Debt & Equity",
    "fed_macro": "Market Analysis",
    "private_equity": "Private Equity",
    "data_centers": "Data Centers",
    "energy": "Market Commentary",
    "local_government": "Policy & Regulation",
}


def _category_for(sector: str) -> str:
    return _CATEGORY.get(sector, "Capital Markets")


def publish(
    drafts: Sequence[Any],
    objects_by_id: dict[str, Any],
    *,
    memory: Any = None,
    include_review_required: bool = False,
    dry_run: bool = False,
) -> PublishReport:
    """Write finished drafts to the site. Never raises."""
    from daily_news_agent import render_html, update_feed_xml, update_manifest, update_sitemap_xml

    report = PublishReport(requested=len(drafts))
    existing = {p.stem for p in INSIGHTS_DIR.glob("*.html")}
    published_articles: list[dict[str, Any]] = []

    for draft in drafts:
        obj = objects_by_id.get(draft.object_id)
        result = PublishResult(
            object_id=draft.object_id, title=draft.title,
            sector=draft.sector, depth=draft.depth,
        )
        if obj is None or not draft.article:
            result.status = "skipped"
            result.reason = "no article to publish"
            report.results.append(result.to_dict())
            continue
        if draft.needs_review and not include_review_required:
            result.status = "skipped"
            result.reason = "flagged for review"
            report.skipped_review += 1
            report.results.append(result.to_dict())
            continue
        if not draft.ok and not draft.needs_review:
            result.status = "skipped"
            result.reason = f"draft status {draft.status}"
            report.results.append(result.to_dict())
            continue

        try:
            # Deliberately WITHOUT the uniquifier. Asking for a unique slug
            # first would return "...-2" and the duplicate check below could
            # never fire, which is how a repeated job would publish the same
            # story twice under two URLs.
            slug = make_slug(draft.article.get("title") or draft.title)
            result.slug = slug
            # Idempotence: the same story must never be published twice, however
            # many times the job runs.
            if slug in existing:
                result.status = "skipped"
                result.reason = "already on the site"
                report.skipped_existing += 1
                report.results.append(result.to_dict())
                continue

            article = _article_payload(draft, obj, slug)
            page = INSIGHTS_DIR / f"{slug}.html"
            if not dry_run:
                try:
                    from social_image_generator import generate_article_image

                    social = INSIGHTS_DIR / f"{slug}_social.png"
                    if generate_article_image(
                        str(article.get("title") or ""),
                        str(article.get("subtitle") or article.get("excerpt") or ""),
                        social,
                    ):
                        article["social_image"] = f"/insights/{social.name}"
                        report.files_written.append(str(social.relative_to(SITE_ROOT)))
                except Exception:  # noqa: BLE001
                    pass  # a social card may degrade; the article may not
                page.write_text(render_html(article), encoding="utf-8")
                report.files_written.append(str(page.relative_to(SITE_ROOT)))
            existing.add(slug)
            published_articles.append(article)
            result.status = "published"
            result.path = f"insights/{slug}.html"
            report.published += 1
            if memory is not None and not dry_run:
                memory.mark_published(obj, slug)
        except Exception as exc:  # noqa: BLE001
            result.status = "failed"
            result.reason = f"{type(exc).__name__}: {exc}"[:160]
            report.failed += 1
        report.results.append(result.to_dict())

    # Indexes are updated once, after every page exists. A crash before this
    # leaves unreferenced pages, which is recoverable; the reverse is not.
    if published_articles and not dry_run:
        try:
            for article in published_articles:
                update_manifest(article)
            update_feed_xml()
            update_sitemap_xml()
            report.files_written += ["insights.json", "feed.xml", "sitemap.xml"]
            for article in published_articles:
                related = _write_related(article)
                report.files_written.append(str(related.relative_to(SITE_ROOT)))
            if memory is not None:
                memory.save()
        except Exception as exc:  # noqa: BLE001
            report.failed += 1
            report.results.append(
                {"status": "failed", "reason": f"index update: {type(exc).__name__}: {exc}"[:160]}
            )
    report.articles = [_article_summary(article) for article in published_articles]
    return report


def summarise(report: PublishReport) -> str:
    lines = [f"  published {report.published}/{report.requested}"]
    if report.skipped_review:
        lines.append(f"    {report.skipped_review} held back for review")
    if report.skipped_existing:
        lines.append(f"    {report.skipped_existing} already on the site")
    if report.failed:
        lines.append(f"    {report.failed} failed")
    if report.files_written:
        lines.append(f"    {len(report.files_written)} files written")
    return "\n".join(lines)


def finalize_publication(
    report: PublishReport,
    run_report: Any,
    slate_report: Any,
    objects: Sequence[Any],
    *,
    memory: Any = None,
    budget: Any = None,
    state_dir: Path | None = None,
) -> list[str]:
    """Create the edition, audit, release decision, and deployment manifest.

    This is intentionally called only after memory, spend, and v3 diagnostics
    have been written. The generated-files manifest therefore contains the
    public edition *and* the durable state tomorrow's clean runner must inherit.
    """
    from edition_manager import (
        PUBLICATION_DECISION_PATH,
        build_edition_document,
        render_run_summary,
        save_public_edition,
        save_run_record,
        write_generated_files,
    )
    from validate_publication import validate_repository

    now = datetime.now(timezone.utc)
    state_dir = state_dir or SITE_ROOT / ".editorial-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    edition_status = "ready" if report.published else "no_publishable_story"
    edition_articles = [
        {
            **article,
            "editorial_format": article.get("format", "brief"),
            "body_html": "",
            "sources": [],
        }
        for article in report.articles
    ]
    selection = {
        "candidate_count": getattr(run_report, "documents_ingested", 0),
        "event_count": getattr(run_report, "objects_after_clustering", 0),
        "daily_target": getattr(run_report, "daily_target", 3),
        "deal_tape": [],
        "duplicate_groups": [],
        "archive_repeats": [],
    }
    edition = build_edition_document(
        edition_date=now.date(),
        selection=selection,
        articles=edition_articles,
        run_status=edition_status,
    )
    paths = [SITE_ROOT / value for value in report.files_written]
    paths.extend(save_public_edition(edition))

    held = [
        result.get("title") or result.get("object_id") or "Untitled"
        for result in report.results
        if result.get("status") == "skipped" and result.get("reason") == "flagged for review"
    ]
    decision = {
        "schema_version": 2,
        "pipeline_version": "v3.0",
        "edition_status": edition_status,
        # Review-required drafts were withheld before this point. The safe
        # completed subset can continue to main without one held article
        # blocking the day's entire edition.
        "review_required": False,
        "auto_publish_allowed": report.failed == 0,
        "reasons": [],
        "held_for_review": held,
        "article_count": report.published,
        "failed_count": report.failed,
        "generated_at": now.replace(microsecond=0).isoformat(),
    }
    PUBLICATION_DECISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLICATION_DECISION_PATH.write_text(
        json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    paths.append(PUBLICATION_DECISION_PATH)

    run_payload = {
        **run_report.to_dict(),
        "status": "success" if report.failed == 0 else "partial_failure",
        "candidate_count": getattr(run_report, "documents_ingested", 0),
        "event_count": getattr(run_report, "objects_after_clustering", 0),
        "articles": report.articles,
        "held": held,
        "daily_target_met": report.published >= getattr(run_report, "daily_target", 3),
        "article_count": report.published,
        "publication": report.to_dict(),
    }
    run_path = save_run_record(run_payload, run_date=now.date())
    paths.append(run_path)
    summary_path = state_dir / "run-summary.md"
    summary_path.write_text(render_run_summary(run_payload), encoding="utf-8")
    paths.append(summary_path)

    # The large candidate/slate diagnostics remain workflow artifacts. Only the
    # compact provider history belongs in Git-backed durable state.
    for name in ("provider-log.jsonl", "source-health.json"):
        path = state_dir / name
        if path.exists():
            paths.append(path)
    if memory is not None and getattr(memory, "path", None):
        paths.append(Path(memory.path))
    if budget is not None and getattr(budget, "ledger_path", None):
        paths.append(Path(budget.ledger_path))

    validation_errors = validate_repository(latest_only=True)
    if validation_errors:
        raise RuntimeError(
            "pre-deployment validation failed: " + "; ".join(validation_errors[:8])
        )

    existing = [path for path in paths if path.exists()]
    generated = write_generated_files(existing)
    report.files_written = list(dict.fromkeys(
        str(path.relative_to(SITE_ROOT)).replace("\\", "/")
        for path in [*existing, generated]
    ))
    return report.files_written
