#!/usr/bin/env python3
"""Collect LinkedIn engagement metrics for published articles and feed back into audience signals."""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
QUEUE_PATH = SITE_ROOT / "linkedin_essay_queue.json"
ENGAGEMENT_PATH = SITE_ROOT / ".editorial-state" / "linkedin-engagement.json"
SIGNALS_PATH = SITE_ROOT / ".editorial-state" / "audience-signals.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def collect_engagement() -> dict[str, Any]:
    """Collect engagement data. Currently uses heuristics from essay queue metadata.
    In production, this would use the LinkedIn API."""
    essays = load_json(QUEUE_PATH)
    if not isinstance(essays, list):
        essays = []

    engagement_by_topic: dict[str, dict[str, int]] = {}
    essays_processed = 0

    for essay in essays:
        if not isinstance(essay, dict):
            continue
        essays_processed += 1
        fact_anchors = essay.get("fact_anchors", [])
        topics_from_facts = set()
        for fact in fact_anchors:
            fact_lower = str(fact).lower()
            for keyword, topic in [
                ("distress", "distress"), ("bank", "bank_credit"),
                ("cmbs", "cmbs"), ("refinanc", "capital_placement"),
                ("sale", "major_sale"), ("fed", "fed_rates"),
                ("private equity", "private_equity"), ("loan", "bank_credit"),
                ("development", "development_finance"), ("policy", "policy"),
            ]:
                if keyword in fact_lower:
                    topics_from_facts.add(topic)

        for topic in topics_from_facts:
            engagement_by_topic.setdefault(topic, {"essays": 0})
            engagement_by_topic[topic]["essays"] += 1

    result = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "essays_analyzed": essays_processed,
        "method": "heuristic-based from essay queue (LinkedIn API integration pending)",
        "topic_engagement": engagement_by_topic,
    }
    return result


def update_audience_signals(engagement: dict[str, Any]) -> dict[str, Any]:
    """Update audience-signals.json with engagement-derived weights."""
    signals = load_json(SIGNALS_PATH) or {"schema_version": 1, "weights": {}, "updated_at": None}
    weights = signals.get("weights", {})
    if not isinstance(weights, dict):
        weights = {}

    topic_engagement = engagement.get("topic_engagement", {})
    for topic, data in topic_engagement.items():
        essay_count = data.get("essays", 0)
        if essay_count >= 3:
            weight_key = f"topic:{topic}"
            current = int(weights.get(weight_key, 0) or 0)
            weights[weight_key] = min(5, max(-5, current + 1))
            print(f"  topic:{topic}: {current:+d} -> {weights[weight_key]:+d} ({essay_count} essays)")

    signals["weights"] = weights
    signals["updated_at"] = datetime.now(timezone.utc).isoformat()
    return signals


def main():
    print("LinkedIn Engagement Scraper")
    print("===========================")
    engagement = collect_engagement()
    print(f"Analyzed {engagement['essays_analyzed']} essay packages")
    print(f"Topic engagement: {len(engagement['topic_engagement'])} topics found")

    ENGAGEMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENGAGEMENT_PATH.write_text(json.dumps(engagement, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Engagement data saved: {ENGAGEMENT_PATH.relative_to(SITE_ROOT)}")

    signals = update_audience_signals(engagement)
    SIGNALS_PATH.write_text(json.dumps(signals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Audience signals updated: {SIGNALS_PATH.relative_to(SITE_ROOT)}")


if __name__ == "__main__":
    main()
