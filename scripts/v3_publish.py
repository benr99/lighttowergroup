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
    article.setdefault("date_iso", datetime.now(timezone.utc).isoformat())
    article.setdefault("tags", [t for t in (obj.primary_sector, obj.primary_subsector,
                                            obj.event_type) if t])
    article.setdefault("editorial_format", draft.depth)
    article.setdefault("pipeline_version", "v3")
    article.setdefault("event_id", obj.object_id)
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
            if memory is not None:
                memory.save()
        except Exception as exc:  # noqa: BLE001
            report.failed += 1
            report.results.append(
                {"status": "failed", "reason": f"index update: {type(exc).__name__}: {exc}"[:160]}
            )
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
