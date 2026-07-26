"""Build source-grounded research dossiers before any article is written."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from content_governance import sanitize_untrusted_source
from editorial_intelligence import FORMAT_SPECS


def _sentences(value: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(value or "")).strip()
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", clean)
        if 7 <= len(sentence.split()) <= 55
    ]


def _fact_candidates(value: str) -> list[str]:
    facts = []
    for sentence in _sentences(value):
        if re.search(
            r"(?:\$[\d,.]+|\b\d+(?:\.\d+)?%|\b\d{4}\b|\b(?:said|reported|announced|filed|"
            r"approved|acquired|sold|borrowed|lent|matures?|occupancy|units?|square feet)\b)",
            sentence,
            re.IGNORECASE,
        ):
            facts.append(sentence)
    return facts


def _quotes(value: str) -> list[str]:
    found = re.findall(r'["\u201c]([^"\u201d]{20,280})["\u201d]', str(value or ""))
    return [re.sub(r"\s+", " ", quote).strip() for quote in found[:3]]


def _independent_domain(url: str) -> str:
    return urlparse(str(url or "")).netloc.lower().removeprefix("www.")


def _archive_context(
    candidate: dict[str, Any],
    archive_records: Iterable[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    candidate_tokens = set(re.findall(r"[a-z0-9]+", str(candidate.get("title", "")).lower()))
    candidate_tags = set(candidate.get("topics") or []) | set((candidate.get("entities") or {}).get("asset_classes") or [])
    ranked = []
    for record in archive_records:
        title_tokens = set(re.findall(r"[a-z0-9]+", str(record.get("title", "")).lower()))
        tags = {str(tag).lower().replace(" ", "_") for tag in record.get("tags", [])}
        overlap = len(candidate_tokens & title_tokens) + 2 * len(candidate_tags & tags)
        if overlap >= 2:
            ranked.append((overlap, record))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "title": record.get("title"),
            "url": record.get("url"),
            "date": record.get("date"),
            "excerpt": record.get("excerpt"),
            "relationship": "Potential prior coverage or comparable; verify the relationship before citing.",
        }
        for _, record in ranked[:limit]
    ]


def build_research_dossier(
    editorial_event: dict[str, Any],
    *,
    fetched_text_by_url: dict[str, str] | None = None,
    archive_records: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Create an evidence ledger from every independent source in an event."""
    fetched = fetched_text_by_url or {}
    sources = []
    reported_facts = []
    quote_ledger = []
    seen_domains = set()
    for source in editorial_event.get("sources", []):
        url = str(source.get("url", ""))
        domain = str(source.get("domain") or _independent_domain(url))
        full_text = sanitize_untrusted_source(fetched.get(url, ""))
        summary = sanitize_untrusted_source(source.get("summary", ""))
        source_facts = _fact_candidates(f"{summary} {full_text}")[:8]
        source_quotes = _quotes(full_text)
        sources.append({
            "name": source.get("source") or domain,
            "url": url,
            "domain": domain,
            "published": source.get("published"),
            "authority": source.get("source_authority", "secondary"),
            "tier": int(source.get("source_tier", 3) or 3),
            "summary": summary,
            "full_text_excerpt": full_text[:6500],
            "reported_facts": source_facts,
            "quotes": source_quotes,
        })
        seen_domains.add(domain)
        reported_facts.extend(
            {"fact": fact, "source_url": url, "source_name": source.get("source") or domain}
            for fact in source_facts
        )
        quote_ledger.extend(
            {"quote": quote, "source_url": url, "source_name": source.get("source") or domain}
            for quote in source_quotes
        )

    independent_source_count = len({domain for domain in seen_domains if domain})
    primary_sources = [source for source in sources if source["authority"] == "primary"]
    usable_full_text_count = sum(bool(source["full_text_excerpt"]) for source in sources)
    if independent_source_count >= 3 and usable_full_text_count >= 2:
        evidence_level = "deep"
    elif independent_source_count >= 2 or primary_sources:
        evidence_level = "adequate"
    elif sources and (reported_facts or usable_full_text_count):
        evidence_level = "thin"
    else:
        evidence_level = "insufficient"

    if evidence_level == "deep":
        recommended_format = "flagship"
    elif (
        editorial_event.get("candidate", {}).get("source_authority") == "primary"
        and "data_release" in (
            (editorial_event.get("candidate", {}).get("entities") or {}).get("policy_actions") or []
        )
    ):
        recommended_format = "data_note"
    elif independent_source_count >= 2:
        recommended_format = (
            "culture_signal"
            if editorial_event.get("must_read_breakdown", {}).get("cultural_relevance", 0) >= 6
            else "brief"
        )
    elif evidence_level == "thin":
        recommended_format = "brief"
    else:
        recommended_format = "deal_tape"

    desired = editorial_event.get("provisional_format", "brief")
    desired_minimum = FORMAT_SPECS.get(desired, FORMAT_SPECS["brief"])["minimum_independent_sources"]
    format_downgraded = independent_source_count < desired_minimum

    return {
        "schema_version": 1,
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "event_id": editorial_event.get("event_id"),
        "title": editorial_event.get("candidate", {}).get("title"),
        "sources": sources,
        "independent_source_count": independent_source_count,
        "primary_source_count": len(primary_sources),
        "usable_full_text_count": usable_full_text_count,
        "evidence_level": evidence_level,
        "reported_facts": reported_facts[:24],
        "quote_ledger": quote_ledger[:8],
        "prior_light_tower_context": _archive_context(
            editorial_event.get("candidate", {}), archive_records
        ),
        "counterquestions": [
            "What material fact would make the favored interpretation wrong?",
            "Is this event representative of a market shift or merely a single transaction?",
            "Which party has the shortest clock, least liquidity, or weakest alternative?",
            "What is reported, what is inferred, and what remains unknown?",
        ],
        "reporting_gaps": [
            gap for condition, gap in (
                (independent_source_count < 2, "A second independent source has not corroborated the event."),
                (not primary_sources, "No primary document is present in the dossier."),
                (not quote_ledger, "No attributable direct quotation was captured."),
                (not reported_facts, "The available material contains too few extractable reported facts."),
            ) if condition
        ],
        "desired_format": desired,
        "recommended_format": recommended_format,
        "format_downgraded": format_downgraded,
        "longform_allowed": independent_source_count >= 3 and usable_full_text_count >= 2,
    }


def dossier_prompt_payload(dossier: dict[str, Any], *, max_chars: int = 24000) -> str:
    """Render a compact, human-readable dossier for a model prompt."""
    blocks = [
        f"EVENT: {dossier.get('title', '')}",
        (
            "EVIDENCE: "
            f"{dossier.get('evidence_level')} | "
            f"{dossier.get('independent_source_count', 0)} independent sources | "
            f"{dossier.get('primary_source_count', 0)} primary"
        ),
    ]
    for index, source in enumerate(dossier.get("sources", []), 1):
        blocks.extend([
            f"\nSOURCE {index}: {source.get('name')} | {source.get('url')}",
            f"Authority: {source.get('authority')} | Published: {source.get('published')}",
            f"Summary: {source.get('summary')}",
            f"Extract: {source.get('full_text_excerpt', '')}",
        ])
    if dossier.get("prior_light_tower_context"):
        blocks.append("\nPRIOR LIGHT TOWER CONTEXT:")
        blocks.extend(
            f"- {item.get('title')} ({item.get('date')}): {item.get('url')}"
            for item in dossier["prior_light_tower_context"]
        )
    if dossier.get("reporting_gaps"):
        blocks.append("\nREPORTING GAPS:")
        blocks.extend(f"- {gap}" for gap in dossier["reporting_gaps"])
    return "\n".join(blocks)[:max_chars]


def dossier_audit_payload(dossier: dict[str, Any]) -> dict[str, Any]:
    """Remove retrieved article text and quotations before durable persistence."""
    return {
        key: value for key, value in dossier.items()
        if key not in {"sources", "quote_ledger"}
    } | {
        "sources": [
            {
                "name": source.get("name"),
                "url": source.get("url"),
                "domain": source.get("domain"),
                "published": source.get("published"),
                "authority": source.get("authority"),
                "tier": source.get("tier"),
                "reported_fact_count": len(source.get("reported_facts", [])),
                "full_text_available": bool(source.get("full_text_excerpt")),
            }
            for source in dossier.get("sources", [])
        ],
        "quote_count": len(dossier.get("quote_ledger", [])),
    }
