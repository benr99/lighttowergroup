"""Deterministic fact extraction for Light Tower editorial verification.

Extracts structured facts from source text and generated articles so claims
can be traced to specific source sentences. Zero LLM calls — pure regex.
"""

from __future__ import annotations
import re
from typing import Any


def extract_amounts(text: str) -> list[dict[str, Any]]:
    """Extract dollar amounts with surrounding context."""
    amounts = []
    for match in re.finditer(
        r'\$\s*([\d,.]+(?:\.\d+)?)\s*(million|billion|trillion|mm|bn|m|b)?\b',
        str(text or ""), re.IGNORECASE
    ):
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)
        context = text[start:end].strip()
        amounts.append({
            "raw": match.group(0).strip(),
            "number": match.group(1),
            "unit": (match.group(2) or "").lower(),
            "context": context,
        })
    return amounts


def extract_percentages(text: str) -> list[dict[str, Any]]:
    """Extract percentages and basis points."""
    pcts = []
    for match in re.finditer(
        r'([\d,.]+)\s*(%|percent|bps|basis points)\b',
        str(text or ""), re.IGNORECASE
    ):
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        pcts.append({
            "raw": match.group(0).strip(),
            "number": match.group(1),
            "unit": match.group(2).lower(),
            "context": text[start:end].strip(),
        })
    return pcts


_KNOWN_INSTITUTIONS = [
    "blackstone", "brookfield", "apollo", "starwood", "ares", "kkr",
    "carlyle", "tpg", "cerberus", "sl green", "vornado", "related", "tishman",
    "jpmorgan", "jp morgan", "goldman", "morgan stanley", "wells fargo",
    "bank of america", "citigroup", "deutsche bank", "barclays",
    "federal reserve", "fdic", "occ", "treasury", "fannie mae", "freddie mac",
    "hud", "cbre", "jll", "cushman", "eastdil", "newmark", "meridian",
    "walker & dunlop", "berkadia", "northmarq", "greystone", "keybank",
    "pnc", "m&t bank", "signature bank", "new york community bank",
    "connectone", "oceanfirst", "flushing financial", "valley national",
]


def extract_companies(text: str) -> list[dict[str, Any]]:
    """Extract known institution names from text."""
    companies = []
    text_lower = str(text or "").lower()
    for institution in _KNOWN_INSTITUTIONS:
        for match in re.finditer(re.escape(institution), text_lower):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            companies.append({
                "name": institution,
                "context": text[start:end].strip(),
            })
    return companies


def extract_addresses(text: str) -> list[str]:
    """Extract US street addresses."""
    addresses = []
    for match in re.finditer(
        r'\b\d{1,5}\s+(?:(?:west|east|north|south|w|e)\s+)?'
        r'[a-z0-9\'\-]+(?:\s+[a-z0-9\'\-]+){0,2}\s+'
        r'(?:street|st|avenue|ave|road|rd|boulevard|blvd|terrace|place|drive|dr|lane|ln)\b',
        str(text or ""), re.IGNORECASE
    ):
        addresses.append(match.group(0).strip())
    return list(dict.fromkeys(addresses))


def extract_dates(text: str) -> list[str]:
    """Extract date references."""
    dates = []
    for pattern in [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b(?:Q[1-4]\s*\d{4})\b',
    ]:
        for match in re.finditer(pattern, str(text or ""), re.IGNORECASE):
            dates.append(match.group(0))
    return list(dict.fromkeys(dates))


def extract_facts(source_text: str) -> dict[str, Any]:
    """Extract all structured facts from a text block."""
    return {
        "amounts": extract_amounts(source_text),
        "percentages": extract_percentages(source_text),
        "companies": extract_companies(source_text),
        "addresses": extract_addresses(source_text),
        "dates": extract_dates(source_text),
    }


def audit_article_facts(
    article_body: str,
    source_facts: dict[str, Any],
    *,
    source_tier: int = 2,
) -> dict[str, Any]:
    """Compare facts in a generated article against source facts. Flag discrepancies."""
    article_facts = extract_facts(article_body)

    # Check amounts
    unmatched_amounts = []
    for a in article_facts["amounts"]:
        article_num = re.sub(r'[,]', '', a["number"])
        article_unit = a["unit"]
        found = False
        for s in source_facts.get("amounts", []):
            source_num = re.sub(r'[,]', '', s["number"])
            if article_num == source_num:
                found = True
                break
        if not found:
            unmatched_amounts.append(a)

    # Check companies
    article_company_names = {c["name"] for c in article_facts["companies"]}
    source_company_names = {c["name"] for c in source_facts.get("companies", [])}
    unmatched_companies = article_company_names - source_company_names

    # Check addresses
    article_addresses = set(article_facts["addresses"])
    source_addresses = set(source_facts.get("addresses", []))
    unmatched_addresses = article_addresses - source_addresses

    has_unverifiable_claim = bool(unmatched_amounts or unmatched_companies or unmatched_addresses)
    hold_for_review = has_unverifiable_claim and source_tier <= 2

    return {
        "article_facts": article_facts,
        "source_facts": source_facts,
        "unmatched_amounts": unmatched_amounts,
        "unmatched_companies": list(unmatched_companies),
        "unmatched_addresses": list(unmatched_addresses),
        "has_unverifiable_claim": has_unverifiable_claim,
        "hold_for_review": hold_for_review,
        "fact_count": len(article_facts["amounts"]) + len(article_facts["companies"]),
        "matched_count": (
            (len(article_facts["amounts"]) - len(unmatched_amounts))
            + (len(article_facts["companies"]) - len(unmatched_companies))
        ),
    }


def extract_claim_type(text: str) -> str:
    """Heuristically classify a claim as reported_fact, bounded_inference, or editorial_judgment."""
    text_lower = str(text or "").lower()
    fact_markers = [
        r'\b(?:reported|announced|filed|disclosed|closed|completed|signed|agreed|acquired|purchased|sold)\b',
        r'\$\s*[\d,.]+',
        r'\b\d+\s*(?:percent|%)\b',
    ]
    judgment_markers = [
        r'\b(?:the market has|this signals|the real|investors should|sponsors must|we believe|it appears)\b',
        r'\b(?:suggests that|implies|indicates|represents a|marks a)\b',
    ]
    fact_count = sum(1 for p in fact_markers if re.search(p, text_lower, re.IGNORECASE))
    judgment_count = sum(1 for p in judgment_markers if re.search(p, text_lower, re.IGNORECASE))
    if fact_count >= 2 and judgment_count == 0:
        return "reported_fact"
    if judgment_count >= 2:
        return "editorial_judgment"
    return "bounded_inference"


def audit_claim_semantic(
    claim_text: str,
    source_texts: list[str],
    *,
    min_proximity: int = 80,
) -> dict[str, Any]:
    """Check if the article's central claim assertions appear in source text.

    For each key assertion in the claim (split on sentence boundaries or specific
    keywords like dollar amounts, company names), search the source texts for
    supporting evidence using keyword proximity.

    Returns {claim_supported, assertions_found, assertions_missing, confidence}
    """
    if not claim_text or not source_texts:
        return {"claim_supported": False, "assertions_found": [], "assertions_missing": ["no text available"], "confidence": 0.0}

    # Extract key assertions from claim
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', str(claim_text)) if len(s.strip()) > 20]
    if not sentences:
        sentences = [claim_text]

    assertions_found = []
    assertions_missing = []

    for sentence in sentences:
        # Extract key terms (dollar amounts, percentages, comparison words, company names)
        key_terms = set()
        for match in re.finditer(r'\$\s*[\d,.]+(?:\s*(?:million|billion|trillion|mm|bn|m|b))?', sentence, re.IGNORECASE):
            key_terms.add(match.group(0).lower())
        for match in re.finditer(r'[\d.]+%', sentence):
            key_terms.add(match.group(0))
        for word in ["higher than", "lower than", "versus", "compared to", "exceeded", "below", "above", "surpassed"]:
            if word in sentence.lower():
                key_terms.add(word)

        if not key_terms:
            key_terms = {sentence.lower()[:60]}

        # Search for these terms in source texts
        found = False
        found_in = None
        for source_text in source_texts:
            source_lower = source_text.lower()
            # Check if key terms appear within proximity of each other
            matches = [source_lower.find(term) for term in key_terms if term in source_lower]
            if matches:
                positions = sorted(matches)
                # Check if any two terms are within proximity
                for i in range(len(positions) - 1):
                    if positions[i + 1] - positions[i] <= min_proximity:
                        found = True
                        found_in = source_text[:100]
                        break
                if not found and len(positions) >= 1:
                    # At least one key term found — weak match
                    found = True
                    found_in = source_text[:100]
            if found:
                break

        if found:
            assertions_found.append({"assertion": sentence[:120], "source_preview": found_in})
        else:
            assertions_missing.append(sentence[:120])

    total = len(sentences)
    found_count = len(assertions_found)
    confidence = found_count / max(1, total)

    return {
        "claim_supported": confidence >= 0.5,
        "assertions_found": assertions_found,
        "assertions_missing": assertions_missing,
        "confidence": round(confidence, 2),
        "total_assertions": total,
        "found_count": found_count,
    }
