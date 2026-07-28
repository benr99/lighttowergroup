#!/usr/bin/env python3
"""Structured public data sources for original Light Tower intelligence.

Currently handling SEC EDGAR RSS feed. Additional sources (NYC DOB permits,
ACRIS property records) planned for future expansions.
"""

from __future__ import annotations
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent

EDGAR_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"

# REITs and major CRE lenders to track in EDGAR filings
TRACKED_ENTITIES = [
    "Prologis", "Equinix", "Simon Property", "Realty Income", "AvalonBay",
    "Equity Residential", "Boston Properties", "Vornado", "SL Green",
    "Alexandria Real Estate", "Digital Realty", "Crown Castle", "American Tower",
    "Public Storage", "Welltower", "Ventas", "Extra Space Storage",
    "Starwood Property", "Blackstone Mortgage", "Ladder Capital", "Arbor Realty",
    "Ready Capital", "TPG RE Finance", "Apollo Commercial Real Estate",
    "KKR Real Estate", "Ares Commercial Real Estate",
]

CRE_KEYWORDS_IN_FILINGS = [
    "real estate", "mortgage", "property", "CRE", "commercial real estate",
    "multifamily", "office building", "industrial", "retail center",
    "loan portfolio", "CMBS", "debt fund",
]


def _fetch_edgar_rss() -> list[dict[str, Any]]:
    """Fetch and parse SEC EDGAR current filings RSS feed."""
    entries = []
    try:
        req = urllib.request.Request(EDGAR_RSS_URL, headers={"User-Agent": "LightTowerGroup research@lighttowergroup.co"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            tree = ET.parse(resp)
            root = tree.getroot()
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:link", ns)
                updated = entry.find("atom:updated", ns)
                entries.append({
                    "title": title.text if title is not None and title.text else "",
                    "summary": summary.text if summary is not None and summary.text else "",
                    "url": link.attrib.get("href", "") if link is not None else "",
                    "published": updated.text if updated is not None and updated.text else "",
                    "source": "SEC EDGAR",
                    "source_tier": 1,
                    "source_authority": "primary",
                    "source_lane": "federal",
                })
    except Exception as e:
        print(f"  EDGAR fetch error: {e}")
    return entries


def _is_cre_relevant(entry: dict[str, Any]) -> bool:
    """Check if an EDGAR filing is CRE-relevant."""
    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    # Must mention a tracked entity or CRE keyword
    entity_match = any(entity.lower() in text for entity in TRACKED_ENTITIES)
    keyword_match = any(kw.lower() in text for kw in CRE_KEYWORDS_IN_FILINGS)
    return entity_match or keyword_match


def fetch_all() -> list[dict[str, Any]]:
    """Fetch from all structured sources. Returns list of candidate stories."""
    candidates = []
    edgar_entries = _fetch_edgar_rss()
    for entry in edgar_entries:
        if _is_cre_relevant(entry):
            candidates.append(entry)
    return candidates


def main():
    print("Structured Sources Scanner")
    print("=========================")
    candidates = fetch_all()
    print(f"SEC EDGAR: {len(candidates)} CRE-relevant filing(s) found")

    for i, candidate in enumerate(candidates[:5], 1):
        print(f"  [{i}] {candidate['title'][:80]}")
        print(f"      {candidate['url'][:80]}")

    if candidates:
        output_path = SITE_ROOT / ".editorial-state" / "structured-candidates.json"
        existing = []
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        if not isinstance(existing, list):
            existing = []
        existing = existing + candidates
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(f"Saved to structured-candidates.json")


if __name__ == "__main__":
    main()
