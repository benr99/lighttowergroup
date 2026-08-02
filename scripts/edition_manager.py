"""Create the public daily edition and durable editorial operating record."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from content_governance import html_to_text
from editorial_intelligence import AUTO_PUBLISH_BRIEF_FLOOR


SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
EDITIONS_DIR = SITE_ROOT / "editions"
LATEST_EDITION_PATH = SITE_ROOT / "latest-edition.json"
STATE_DIR = SITE_ROOT / ".editorial-state"
RUNS_DIR = STATE_DIR / "runs"
EVENT_MEMORY_PATH = STATE_DIR / "event-memory.json"
GENERATED_FILES_PATH = STATE_DIR / "generated-files.json"
PUBLICATION_DECISION_PATH = STATE_DIR / "publication-decision.json"


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def calculate_read_time(body_html: str) -> int:
    words = len(html_to_text(body_html).split())
    return max(1, round(words / 225))


def _article_summary(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": article.get("event_id"),
        "title": article.get("title"),
        "subtitle": article.get("subtitle"),
        "slug": article.get("slug"),
        "url": f"/insights/{article.get('slug')}.html",
        "category": article.get("category"),
        "format": article.get("editorial_format", "brief"),
        "format_label": article.get("editorial_format_label", "Intelligence Brief"),
        "franchise": article.get("franchise"),
        "must_read_score": article.get("must_read_score"),
        "selection_tier": article.get("selection_tier"),
        "read_time": calculate_read_time(str(article.get("body_html", ""))),
        "source_count": len({
            str(source.get("url", "")).split("/")[2].lower().removeprefix("www.")
            for source in article.get("sources", [])
            if isinstance(source, dict) and str(source.get("url", "")).startswith(("http://", "https://"))
        }),
    }


def _deal_tape_summary(item: dict[str, Any]) -> dict[str, Any]:
    candidate = item.get("candidate", {})
    entities = candidate.get("entities") or {}
    return {
        "event_id": item.get("event_id"),
        "title": candidate.get("title"),
        "source": candidate.get("source"),
        "source_url": candidate.get("url"),
        "published": candidate.get("published"),
        "must_read_score": item.get("must_read_score"),
        "amounts": entities.get("amounts", []),
        "companies": entities.get("companies", []),
        "markets": entities.get("markets", []),
        "asset_classes": entities.get("asset_classes", []),
        "one_line": candidate.get("summary") or item.get("decision_reason"),
    }


def build_edition_document(
    *,
    edition_date: date,
    selection: dict[str, Any],
    articles: list[dict[str, Any]],
    run_status: str = "ready",
) -> dict[str, Any]:
    article_summaries = [_article_summary(article) for article in articles]
    flagship = next(
        (article for article in article_summaries if article["format"] == "flagship"),
        None,
    )
    culture = next(
        (article for article in article_summaries if article["format"] == "culture_signal"),
        None,
    )
    data_note = next(
        (article for article in article_summaries if article["format"] == "data_note"),
        None,
    )
    briefs = [
        article for article in article_summaries
        if article["format"] not in {"flagship", "culture_signal", "data_note"}
    ]
    prompt = (
        "Which capital-markets assumption is your team privately questioning this week?"
        if flagship
        else "What story deserves a deeper Light Tower investigation next?"
    )
    return {
        "schema_version": 1,
        "edition_date": edition_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": run_status,
        "dek": (
            "The few capital decisions worth understanding today—reported with "
            "scarcity, evidence, and a point of view."
        ),
        "flagship": flagship,
        "briefs": briefs,
        "culture_signal": culture,
        "data_note": data_note,
        "deal_tape": [_deal_tape_summary(item) for item in selection.get("deal_tape", [])],
        "reader_prompt": {
            "id": f"{edition_date.isoformat()}-capital-assumption",
            "question": prompt,
            "options": [
                "Refinancing liquidity is healthier than it looks",
                "Office recovery is broader than trophy assets",
                "Private credit pricing still compensates for risk",
                "Policy is now a larger variable than rates",
            ],
        },
        "selection_summary": {
            "raw_candidates": selection.get("candidate_count", 0),
            "distinct_events": selection.get("event_count", 0),
            "articles": len(article_summaries),
            "deal_tape_items": len(selection.get("deal_tape", [])),
            "duplicate_groups": len(selection.get("duplicate_groups", [])),
            "archive_repeats": len(selection.get("archive_repeats", [])),
            "daily_target": selection.get("daily_target", 0),
            "daily_target_met": len(article_summaries) >= int(selection.get("daily_target", 0) or 0),
            "no_flagship": flagship is None,
        },
    }


def save_public_edition(document: dict[str, Any]) -> list[Path]:
    edition_date = str(document["edition_date"])
    edition_path = EDITIONS_DIR / f"{edition_date}.json"
    _write_json(edition_path, document)
    _write_json(LATEST_EDITION_PATH, document)
    return [edition_path, LATEST_EDITION_PATH]


def save_run_record(payload: dict[str, Any], run_date: date | None = None) -> Path:
    run_date = run_date or datetime.now(timezone.utc).date()
    return _write_json(RUNS_DIR / f"{run_date.isoformat()}.json", payload)


def update_event_memory(selection: dict[str, Any], *, keep: int = 1000) -> Path:
    try:
        current = json.loads(EVENT_MEMORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = []
    if not isinstance(current, list):
        current = []
    known = {str(item.get("event_id")): item for item in current if isinstance(item, dict)}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for item in selection.get("scored_events", []):
        candidate = item.get("candidate", {})
        known[str(item.get("event_id"))] = {
            "event_id": item.get("event_id"),
            "last_seen": now,
            "title": candidate.get("title"),
            "source_urls": [source.get("url") for source in item.get("sources", [])],
            "must_read_score": item.get("must_read_score"),
            "decision": item.get("decision"),
            "archive_matches": item.get("archive_matches", []),
        }
    ordered = sorted(known.values(), key=lambda item: item.get("last_seen", ""), reverse=True)[:keep]
    return _write_json(EVENT_MEMORY_PATH, ordered)


def write_generated_files(paths: list[Path]) -> Path:
    safe = []
    root = SITE_ROOT.resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Generated file is outside the repository: {path}") from exc
        value = relative.as_posix()
        if value.startswith(".git/") or value == ".git":
            raise ValueError("Generated-file manifest may not include Git internals")
        if value not in safe:
            safe.append(value)
    return _write_json(GENERATED_FILES_PATH, {"schema_version": 1, "files": safe})


def save_publication_decision(
    *,
    articles: list[dict[str, Any]],
    edition_status: str,
) -> Path:
    reasons = []
    for article in articles:
        title = article.get("title", "Untitled")
        article_format = article.get("editorial_format")
        evidence = article.get("research_evidence_level")
        score = int(article.get("must_read_score") or 0)
        if article_format == "flagship":
            reasons.append(f"Flagship analysis requires editor approval: {title}")
        if article_format == "culture_signal":
            reasons.append(f"Culture of Capital judgment requires editor approval: {title}")
        if evidence == "insufficient":
            reasons.append(f"Insufficient evidence requires editor approval: {title}")
        full_text_count = int(article.get("research_usable_full_text_count") or 0)
        fact_count = int(article.get("research_reported_fact_count") or 0)
        selection_tier = str(article.get("selection_tier") or "")
        if article_format == "brief" and (
            evidence == "thin" or selection_tier == "daily_depth"
        ):
            if full_text_count < 1 or fact_count < 3:
                reasons.append(
                    f"Evidence-bounded brief lacks enough retrieved facts "
                    f"for automatic publication: {title}"
                )
        elif evidence == "thin":
            reasons.append(f"Thin evidence is only auto-publishable as a bounded brief: {title}")
        if article_format == "brief" and score < AUTO_PUBLISH_BRIEF_FLOOR:
            reasons.append(
                f"Brief score is below the automatic publication floor "
                f"({score} < {AUTO_PUBLISH_BRIEF_FLOOR}): {title}"
            )
        if article_format not in {"flagship", "culture_signal", "brief", "data_note"}:
            reasons.append(f"Unknown editorial format requires approval: {title}")
        room_decision = str(article.get("editorial_room_decision") or "")
        if selection_tier == "daily_depth" and not room_decision:
            reasons.append(f"Daily-depth brief lacks an editorial-room decision: {title}")
        elif room_decision and room_decision not in {"write", "shorten"}:
            reasons.append(f"Editorial room did not approve writing ({room_decision}): {title}")
        if article.get("legal_or_allegation_risk"):
            reasons.append(f"Legal or allegation risk requires editor approval: {title}")
    payload = {
        "schema_version": 1,
        "edition_status": edition_status,
        "review_required": bool(reasons),
        "auto_publish_allowed": not reasons,
        "reasons": reasons,
        "article_count": len(articles),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return _write_json(PUBLICATION_DECISION_PATH, payload)


def render_run_summary(payload: dict[str, Any]) -> str:
    articles = payload.get("articles", [])
    decisions = payload.get("decision_counts", {})
    target_met = payload.get("daily_target_met")
    target_label = "not evaluated" if target_met is None else ("yes" if target_met else "no")
    lines = [
        "# Light Tower Insights edition",
        "",
        f"- Status: **{payload.get('status', 'unknown')}**",
        f"- Candidates: **{payload.get('candidate_count', 0)}**",
        f"- Distinct events: **{payload.get('event_count', 0)}**",
        f"- Articles: **{len(articles)}**",
        f"- Daily target: **{payload.get('daily_target', 0)}**",
        f"- Daily target met: **{target_label}**",
        f"- Research candidates: **{payload.get('research_candidate_count', 0)}**",
        f"- Deal-tape items: **{payload.get('deal_tape_count', 0)}**",
        f"- Archive repeats suppressed: **{payload.get('archive_repeat_count', 0)}**",
    ]
    if decisions:
        lines.append(f"- Decisions: `{json.dumps(decisions, sort_keys=True)}`")
    if articles:
        lines.extend(["", "## Published candidates", ""])
        for article in articles:
            lines.append(
                f"- **{article.get('format', 'brief')}** — {article.get('title')} "
                f"({article.get('source_count', 0)} sources; "
                f"{article.get('selection_tier', 'standard')} selection)"
            )
    if payload.get("held"):
        lines.extend(["", "## Held or downgraded", ""])
        lines.extend(f"- {item}" for item in payload["held"])
    return "\n".join(lines) + "\n"
