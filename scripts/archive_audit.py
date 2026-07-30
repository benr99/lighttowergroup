"""
Archive audit: check all 331 published articles for quality issues.

Usage:  python scripts/archive_audit.py
Output: data/archive-audit.json + stdout summary.
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
OUTPUT_PATH = SITE_ROOT / "data" / "archive-audit.json"

sys.path.insert(0, str(SCRIPT_DIR))
from content_governance import (
    independent_quality_issues,
    html_to_text,
    load_insight_records,
)

DUPE_THRESHOLD = 0.72
THIN_WORD_COUNT = 215
DAYS_WINDOW = 5

_BODY_RE = re.compile(
    r'<div[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</div>\s*(?:<div\b|</article>|<footer)',
    re.I | re.S,
)
_SOURCES_RE = re.compile(
    r'<div[^>]*class="[^"]*sources-block[^"]*"[^>]*>(.*?)</div>',
    re.I | re.S,
)
_SOURCE_URL_RE = re.compile(r'href="(https?://[^"]+)"', re.I)

_BOILERPLATE_PATTERNS = [
    r"the headline is therefore a doorway",
    r"buildings are where private capital",
    r"the capital question is simple and difficult",
    r"the built world is not merely the background",
    r"light tower group is a",
    r"for more information, please contact",
    r"this article is for informational purposes only",
]


def _extract_body_html(html_text: str) -> str:
    m = _BODY_RE.search(html_text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_source_html(html_text: str) -> str:
    m = _SOURCES_RE.search(html_text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_source_urls(source_html: str) -> list[str]:
    return _SOURCE_URL_RE.findall(source_html)


def _word_count(html_text: str) -> int:
    text = html_to_text(html_text)
    return len(text.split())


def _check_boilerplate(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in _BOILERPLATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern)
    return hits


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", str(title or "").lower())).strip()


def _title_ratio_pre(na: str, nb: str) -> float:
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _token_sim_pre(na: str, nb: str) -> float:
    sa = set(na.split())
    sb = set(nb.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> None:
    records = load_insight_records(SITE_ROOT)
    total_articles = len(records)
    print(f"Loaded {total_articles} records from insights.json")

    pre_norm = [_norm_title(r.get("title", "")) for r in records]
    pre_dates = [str(r.get("date", "")) for r in records]
    pre_slugs = [str(r.get("slug", "")) for r in records]

    results: list[dict[str, Any]] = []
    duplicate_pairs: list[dict[str, Any]] = []
    thin_articles: list[dict[str, Any]] = []
    no_source_urls: list[str] = []
    boilerplate_hits: list[dict[str, Any]] = []
    temporal_clusters: list[dict[str, Any]] = []

    from datetime import datetime

    for i in range(total_articles):
        rec = records[i]
        slug = pre_slugs[i]
        title = str(rec.get("title", ""))
        date_str = pre_dates[i]

        body_html = ""
        source_html = ""
        html_path = INSIGHTS_DIR / f"{slug}.html"
        if html_path.exists():
            try:
                raw_html = html_path.read_text(encoding="utf-8")
            except Exception:
                raw_html = ""
            body_html = _extract_body_html(raw_html)
            source_html = _extract_source_html(raw_html)

        wc = _word_count(body_html) if body_html else 0
        source_urls = _extract_source_urls(source_html)
        has_source = any(u.startswith(("https://", "http://")) for u in source_urls)
        bp = _check_boilerplate(html_to_text(body_html)) if body_html else []

        quality_issues: list[str] = []
        if body_html:
            article_for_check = {
                "body_html": body_html,
                "source_notes": source_html,
                "generation_mode": "",
                "sources": [{"url": u} for u in source_urls] if source_urls else [],
            }
            try:
                quality_issues = independent_quality_issues(
                    article_for_check, require_sections=False, article_format="brief",
                )
            except Exception:
                quality_issues = []

        is_thin = wc > 0 and wc < THIN_WORD_COUNT
        if is_thin:
            thin_articles.append({"slug": slug, "title": title, "word_count": wc})

        if not has_source:
            no_source_urls.append(slug)

        if bp:
            boilerplate_hits.append({"slug": slug, "title": title, "patterns": bp})

        results.append({
            "slug": slug, "title": title, "date": date_str,
            "word_count": wc, "is_thin": is_thin,
            "source_urls": source_urls, "has_source_urls": has_source,
            "boilerplate_patterns": bp,
            "independent_quality_issues": quality_issues,
        })

        if i % 50 == 0:
            print(f"  Extracting article {i + 1}/{total_articles}...")

        for j in range(i + 1, total_articles):
            ratio = _title_ratio_pre(pre_norm[i], pre_norm[j])
            token_sim = _token_sim_pre(pre_norm[i], pre_norm[j])
            if ratio > DUPE_THRESHOLD or token_sim >= DUPE_THRESHOLD:
                duplicate_pairs.append({
                    "slug_a": pre_slugs[i], "title_a": str(records[i].get("title", "")),
                    "date_a": pre_dates[i],
                    "slug_b": pre_slugs[j], "title_b": str(records[j].get("title", "")),
                    "date_b": pre_dates[j],
                    "title_ratio": round(ratio, 3),
                    "token_similarity": round(token_sim, 3),
                })

    for i in range(total_articles):
        for j in range(i + 1, total_articles):
            ratio = _title_ratio_pre(pre_norm[i], pre_norm[j])
            if ratio < DUPE_THRESHOLD:
                continue
            try:
                d1 = datetime.strptime(pre_dates[i], "%Y-%m-%d")
                d2 = datetime.strptime(pre_dates[j], "%Y-%m-%d")
                diff = abs((d2 - d1).days)
                if diff <= DAYS_WINDOW:
                    temporal_clusters.append({
                        "slug_a": pre_slugs[i],
                        "title_a": str(records[i].get("title", "")),
                        "date_a": pre_dates[i],
                        "slug_b": pre_slugs[j],
                        "title_b": str(records[j].get("title", "")),
                        "date_b": pre_dates[j],
                        "title_ratio": round(ratio, 3),
                        "days_apart": diff,
                    })
            except (ValueError, TypeError):
                pass

    output = {
        "total_articles": total_articles,
        "duplicate_pairs_count": len(duplicate_pairs),
        "thin_articles_count": len(thin_articles),
        "articles_without_source_urls": len(no_source_urls),
        "boilerplate_hits_count": len(boilerplate_hits),
        "temporal_clusters_5days": len(temporal_clusters),
        "duplicate_pairs": duplicate_pairs,
        "thin_articles": thin_articles,
        "no_source_url_slugs": no_source_urls,
        "boilerplate_hits": boilerplate_hits,
        "temporal_clusters": temporal_clusters,
        "per_article_results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("=" * 60)
    print("  ARCHIVE AUDIT — Quality Report")
    print("=" * 60)
    print(f"  Total articles:                   {total_articles}")
    print(f"  Near-duplicate title pairs:       {len(duplicate_pairs)}")
    print(f"  Thin articles (< {THIN_WORD_COUNT} words):      {len(thin_articles)}")
    print(f"  Articles with no source URLs:     {len(no_source_urls)}")
    print(f"  Boilerplate pattern hits:         {len(boilerplate_hits)}")
    print(f"  Temporal clusters (<=5 days):     {len(temporal_clusters)}")
    print("=" * 60)
    print(f"  Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
