#!/usr/bin/env python3
"""Weekly assignment desk: identifies patterns across events and commissions original investigations.

Runs Sunday mornings. Reads the past week's editorial run records, identifies patterns,
generates investigation prompts, and queues them for Monday's edition.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
ASSIGNMENT_PATH = SITE_ROOT / ".editorial-state" / "assignment-queue.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_weekly_runs(days: int = 7) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    runs = []
    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.json"), reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            try:
                run_date = datetime.fromisoformat(str(data.get("run_at", "")[:10]) + "T00:00:00+00:00")
                if run_date >= cutoff:
                    runs.append(data)
            except (TypeError, ValueError):
                continue
    return runs


def identify_patterns(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify patterns across the week's events."""
    patterns = []
    all_topics = []
    all_companies = set()
    all_markets = set()
    deal_tape_items = []

    for run in runs:
        for article in run.get("articles", []):
            pass  # article summaries
        if run.get("deal_tape_count", 0) > 0:
            for item in run.get("deal_tape", []):
                if isinstance(item, dict):
                    deal_tape_items.append(item)

    # Pattern: loan book sales
    loan_sale_keywords = ["loan book", "loan portfolio", "note sale", "bulk sale"]
    loan_sales = [
        item for item in deal_tape_items
        if any(kw in str(item.get("title", "")).lower() for kw in loan_sale_keywords)
    ]
    if len(loan_sales) >= 2:
        patterns.append({
            "pattern": "Regional bank loan book sales accelerating",
            "question": "What is the total volume of regional bank CRE loan sales this quarter? Which banks are next?",
            "potential_sources": ["Trepp CMBS data", "MBA Newslink", "FDIC call reports", "Regional bank earnings transcripts"],
            "evidence_count": len(loan_sales),
            "priority": "high",
        })

    # Pattern: data center / AI infrastructure
    dc_keywords = ["data center", "power demand", "AI infrastructure", "semiconductor"]
    dc_items = [
        item for item in deal_tape_items
        if any(kw in str(item.get("title", "")).lower() for kw in dc_keywords)
    ]
    if dc_items:
        patterns.append({
            "pattern": "Data center and AI infrastructure capital flows",
            "question": "How is data center demand reshaping industrial and power markets? What CRE asset classes benefit?",
            "potential_sources": ["JLL Data Center Outlook", "CBRE research", "Utility IRP filings", "U.S. Energy Information Administration"],
            "evidence_count": len(dc_items),
            "priority": "medium",
        })

    # Pattern: office distress
    office_keywords = ["office", "distress", "default", "foreclosure", "special servicing"]
    office_items = [
        item for item in deal_tape_items
        if all(kw in str(item.get("title", "")).lower() for kw in ["office"]) and
        any(kw in str(item.get("title", "")).lower() for kw in ["distress", "default", "foreclosure"])
    ]
    if len(office_items) >= 2:
        patterns.append({
            "pattern": "Office distress concentrating in specific submarkets",
            "question": "Is office distress broadening beyond pre-2020 vintage loans? Which submarkets are next?",
            "potential_sources": ["Trepp", "CMBS delinquency reports", "CoStar market reports", "Moody's Analytics"],
            "evidence_count": len(office_items),
            "priority": "high",
        })

    # Pattern: policy/regulation changes
    policy_keywords = ["fed", "federal reserve", "fdic", "rate", "regulation", "zoning", "legislation"]
    policy_items = [
        item for item in deal_tape_items
        if any(kw in str(item.get("title", "")).lower() for kw in policy_keywords)
    ]
    if len(policy_items) >= 2:
        patterns.append({
            "pattern": "Policy and regulatory shifts affecting CRE capital",
            "question": "Which pending regulatory changes have the largest CRE capital transmission?",
            "potential_sources": ["Federal Register", "FDIC proposals", "Congressional Budget Office", "Trade group comment letters"],
            "evidence_count": len(policy_items),
            "priority": "medium",
        })

    return patterns


def generate_investigation_prompts(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert patterns into actionable investigation prompts."""
    prompts = []
    for i, pattern in enumerate(patterns):
        prompts.append({
            "id": f"assignment-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{i+1:02d}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern["pattern"],
            "question": pattern["question"],
            "potential_sources": pattern["potential_sources"],
            "priority": pattern["priority"],
            "status": "open",
            "evidence_count": pattern.get("evidence_count", 0),
        })
    return prompts


def main():
    print("Weekly Assignment Desk")
    print("======================")
    runs = load_weekly_runs(7)
    print(f"Analyzing {len(runs)} runs from the past 7 days")

    patterns = identify_patterns(runs)
    print(f"Identified {len(patterns)} event patterns")

    prompts = generate_investigation_prompts(patterns)
    if prompts:
        ASSIGNMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = load_json(ASSIGNMENT_PATH) or []
        if not isinstance(existing, list):
            existing = []
        existing = [p for p in existing if isinstance(p, dict) and p.get("status") == "open"]
        for prompt in prompts:
            print(f"  [{prompt['priority'].upper()}] {prompt['pattern']}: {prompt['question'][:80]}...")
            existing.append(prompt)
        ASSIGNMENT_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {len(prompts)} investigation prompt(s) to assignment queue")
    else:
        print("No significant patterns identified. Assignment queue unchanged.")


if __name__ == "__main__":
    main()
