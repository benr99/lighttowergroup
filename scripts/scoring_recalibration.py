#!/usr/bin/env python3
"""Monthly scoring recalibration: evaluate whether scoring heuristics match reader engagement.

Compares deterministic scores against actual read events to recommend
scoring prompt adjustments.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
STATE_DIR = SITE_ROOT / ".editorial-state"
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
EVAL_DIR = SITE_ROOT / "data" / "scoring-evaluations"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_read_events(days: int = 30) -> dict[str, dict[str, int]]:
    """Load read events, keyed by slug with engagement counts."""
    events_path = STATE_DIR / "read-events.jsonl"
    engagement: dict[str, dict[str, int]] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        for line in events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            ts = datetime.fromisoformat(str(event.get("timestamp", "")).replace("Z", "+00:00"))
            if ts < cutoff:
                continue
            slug = event.get("slug", "")
            action = event.get("action", "view")
            if not slug:
                continue
            engagement.setdefault(slug, {"views": 0, "scrolls_50": 0, "scrolls_100": 0, "shares": 0})
            if action in engagement[slug]:
                engagement[slug][action] += 1
    except (OSError, FileNotFoundError):
        pass
    return engagement


def load_article_scores(days: int = 30) -> list[dict[str, Any]]:
    """Load article metadata with scores from editorial runs."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    articles = []
    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.json"), reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            for article in data.get("articles", []):
                slug = article.get("slug", "")
                score = article.get("must_read_score") or article.get("score", 0)
                if slug and score:
                    articles.append({
                        "slug": slug,
                        "score": int(score),
                        "title": article.get("title", ""),
                    })
    return articles


def compute_correlation(articles: list[dict], engagement: dict) -> dict[str, Any]:
    """Compute simple rank correlation between scores and engagement."""
    if len(articles) < 10:
        return {"error": "Insufficient data (need 10+ articles)", "sample_size": len(articles)}

    pairs = []
    for a in articles:
        slug = a["slug"]
        if slug in engagement:
            eng = engagement[slug]
            engagement_score = eng["views"] * 1 + eng["scrolls_100"] * 3 + eng["shares"] * 5
            pairs.append((a["score"], engagement_score, a["title"]))

    if len(pairs) < 10:
        return {"error": "Insufficient matched pairs", "sample_size": len(pairs)}

    # Simple rank-based agreement: what % of top-scored articles are top-engaged?
    sorted_by_score = sorted(pairs, key=lambda x: x[0], reverse=True)
    sorted_by_engagement = sorted(pairs, key=lambda x: x[1], reverse=True)

    top_n = max(3, len(pairs) // 3)
    top_by_score = {p[2] for p in sorted_by_score[:top_n]}
    top_by_engagement = {p[2] for p in sorted_by_engagement[:top_n]}
    overlap = top_by_score & top_by_engagement
    overlap_pct = len(overlap) / top_n * 100 if top_n else 0

    recommendation = "keep"
    if overlap_pct < 30:
        recommendation = "recalibrate — scoring does not predict engagement"
    elif overlap_pct < 50:
        recommendation = "review — scoring partially predicts engagement"
    elif overlap_pct >= 70:
        recommendation = "strong — scoring is a good engagement predictor"

    return {
        "sample_size": len(pairs),
        "top_n": top_n,
        "top_by_score": sorted([p[2][:50] for p in sorted_by_score[:top_n]]),
        "top_by_engagement": sorted([p[2][:50] for p in sorted_by_engagement[:top_n]]),
        "overlap_count": len(overlap),
        "overlap_pct": round(overlap_pct, 1),
        "recommendation": recommendation,
    }


def main():
    today = datetime.now(timezone.utc).date()
    articles = load_article_scores(30)
    engagement = load_read_events(30)
    result = compute_correlation(articles, engagement)

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": 30,
        "articles_with_scores": len(articles),
        "articles_with_engagement": len([a for a in articles if a["slug"] in engagement]),
        **result,
    }
    eval_path = EVAL_DIR / f"{today.isoformat()}.json"
    eval_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Scoring recalibration saved: {eval_path.relative_to(SITE_ROOT)}")
    print(f"  Sample: {report.get('sample_size', 0)} articles")
    print(f"  Overlap: {report.get('overlap_pct', 0)}%")
    print(f"  Recommendation: {report.get('recommendation', 'unknown')}")


if __name__ == "__main__":
    main()
