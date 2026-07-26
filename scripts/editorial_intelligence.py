"""Deterministic editorial intelligence for the Light Tower Insights edition.

This module decides whether a reported event deserves attention before an LLM
is asked to write about it.  It clusters multiple headlines about the same
event, compares candidates with the published archive, scores editorial value,
and builds a deliberately scarce daily portfolio.

The scorer is intentionally inspectable.  It rewards consequence, novelty,
conflict, explanatory value, culture, human stakes, evidence, and Light
Tower's right to add value.  Routine transactions are penalized even when they
contain a large dollar amount.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse


MUST_READ_THRESHOLD = 56
FLAGSHIP_CANDIDATE_THRESHOLD = 72
DEAL_TAPE_THRESHOLD = 34
DAILY_RESEARCH_FLOOR = 24
AUTO_PUBLISH_BRIEF_FLOOR = 24
DEFAULT_DAILY_ARTICLE_TARGET = 3

DAILY_BRIEF_TOPICS = {
    "capital_placement", "cmbs", "private_credit", "bank_credit", "distress",
    "fed_rates", "policy", "government_action", "reit_public_markets",
    "major_sale", "mna", "private_equity", "capital_expenditure",
    "market_fundamentals", "leasing",
}

FORMAT_SPECS: dict[str, dict[str, Any]] = {
    "flagship": {
        "label": "Flagship Analysis",
        "min_words": 750,
        "max_words": 1050,
        "minimum_independent_sources": 3,
        "purpose": "A deeply reported, thesis-led analysis that changes how the reader understands the event.",
    },
    "brief": {
        "label": "Intelligence Brief",
        "min_words": 240,
        "max_words": 430,
        "minimum_independent_sources": 1,
        "purpose": "A compressed explanation of what changed, why it matters, and what to watch next.",
    },
    "culture_signal": {
        "label": "Culture of Capital",
        "min_words": 300,
        "max_words": 550,
        "minimum_independent_sources": 2,
        "purpose": "A reported look at where money, status, place, policy, and human behavior collide.",
    },
    "data_note": {
        "label": "One Chart, One Argument",
        "min_words": 200,
        "max_words": 400,
        "minimum_independent_sources": 1,
        "purpose": "Use a primary data release or filing to make one bounded, legible argument.",
    },
    "deal_tape": {
        "label": "Deal Tape",
        "min_words": 0,
        "max_words": 80,
        "minimum_independent_sources": 1,
        "purpose": "Structured facts and one bounded implication; not a padded standalone essay.",
    },
}

FRANCHISES: dict[str, dict[str, str]] = {
    "credit_committee_theater": {
        "name": "Credit Committee Theater",
        "promise": "What the structure reveals about the lender's real risk test.",
    },
    "five_minutes_before_maturity": {
        "name": "Five Minutes Before Maturity",
        "promise": "How time, extensions, and refinancing pressure redistribute bargaining power.",
    },
    "who_got_paid_who_got_stuck": {
        "name": "Who Got Paid / Who Got Stuck",
        "promise": "Follow the economics through every party rather than repeating the transaction headline.",
    },
    "what_the_release_left_out": {
        "name": "What the Press Release Left Out",
        "promise": "Separate the announcement from the constraints, incentives, and unanswered questions.",
    },
    "capital_after_dark": {
        "name": "Capital After Dark",
        "promise": "Where finance meets status, culture, politics, entertainment, and the life of a city.",
    },
    "the_expensive_assumption": {
        "name": "The Most Expensive Assumption",
        "promise": "Identify the premise on which the capital plan quietly depends.",
    },
}

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "its", "new", "of", "on", "or", "the", "to",
    "with", "after", "over", "under", "real", "estate", "commercial", "deal",
    "says", "gets", "plans", "announces",
}
_NOVELTY_PATTERNS = (
    r"\b(first|largest|record|historic|rare|unexpected|reverses?|abandons?|returns?|revives?)\b",
    r"\b(collaps\w*|bankrupt\w*|resign\w*|oust\w*|withdraw\w*|scraps?|freezes?|halts?)\b",
)
_CONFLICT_PATTERNS = (
    r"\b(default\w*|foreclos\w*|bankrupt\w*|lawsuit|litigation|fight|battle|dispute|"
    r"missed payment|special servicing|receivership|seiz\w*|reject\w*|blocked|hostile)\b",
)
_CULTURE_PATTERNS = {
    "sports": r"\b(stadium|arena|sports|team owner|nba|nfl|mlb|nhl)\b",
    "entertainment": r"\b(film|music|theater|theatre|celebrity|nightlife|restaurant|hotel|hospitality)\b",
    "technology": r"\b(ai|artificial intelligence|data center|power demand|semiconductor|robot)\b",
    "status": r"\b(luxury|club|penthouse|billionaire|family office|bonus|compensation|status)\b",
    "cities": r"\b(return.to.office|remote work|migration|transit|public realm|neighborhood|downtown)\b",
    "climate": r"\b(climate|insurance|flood|wildfire|energy transition|resilience)\b",
    "politics": r"\b(mayor|governor|election|subsidy|taxpayer|public money|lobby\w*)\b",
}
_HUMAN_PATTERNS = (
    r"\b(tenants?|residents?|renters?|workers?|employees?|jobs?|layoffs?|households?|"
    r"students?|patients?|families|family|communities|community|neighborhoods?|"
    r"affordab\w*|homeless\w*|evict\w*)\b",
)
_ROUTINE_PATTERNS = (
    r"\b(provides?|secures?|lands?|closes?)\s+\$?[\d,.]+\s*(?:m|mm|million|b|bn|billion)?\s+"
    r"(?:loan|refinanc\w*|financing)\b",
    r"\b(signs?|renews?)\s+(?:a\s+)?[\d,]+\s*(?:square[- ]?foot|sf)\s+lease\b",
    r"\b(acquires?|purchases?|sells?)\s+.+\s+for\s+\$[\d,.]+\b",
)


def _text(item: dict[str, Any]) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')}".lower()


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _ratio(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _entity_values(item: dict[str, Any], key: str) -> set[str]:
    values = ((item.get("entities") or {}).get(key) or [])
    normalized = set()
    for value in values:
        clean = str(value).strip().lower()
        if not clean:
            continue
        if key == "amounts":
            clean = re.sub(r"\s+", "", clean)
            clean = re.sub(r"(billion|bn)$", "b", clean)
            clean = re.sub(r"(million|mm)$", "m", clean)
        normalized.add(clean)
    return normalized


def event_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Return a 0-1 likelihood that two normalized stories describe one event."""
    left_url = str(left.get("url", "")).split("#", 1)[0].rstrip("/")
    right_url = str(right.get("url", "")).split("#", 1)[0].rstrip("/")
    if left_url and left_url == right_url:
        return 1.0

    title_score = _ratio(_tokens(left.get("title", "")), _tokens(right.get("title", "")))
    company_score = _ratio(_entity_values(left, "companies"), _entity_values(right, "companies"))
    amount_score = _ratio(_entity_values(left, "amounts"), _entity_values(right, "amounts"))
    market_score = _ratio(_entity_values(left, "markets"), _entity_values(right, "markets"))
    asset_score = _ratio(_entity_values(left, "asset_classes"), _entity_values(right, "asset_classes"))

    # A shared amount plus either a party or a location/property context is a
    # stronger event signal than similar generic financing vocabulary.
    if amount_score and title_score >= 0.15:
        return min(
            1.0,
            0.64 + 0.22 * title_score + 0.09 * company_score
            + 0.03 * market_score + 0.02 * asset_score,
        )

    return (
        0.55 * title_score
        + 0.20 * company_score
        + 0.15 * amount_score
        + 0.05 * market_score
        + 0.05 * asset_score
    )


def event_fingerprint(items: Iterable[dict[str, Any]]) -> str:
    """Build a stable identifier from the event's most persistent features."""
    records = list(items)
    tokens = Counter(token for item in records for token in _tokens(item.get("title", "")))
    companies = sorted({value for item in records for value in _entity_values(item, "companies")})
    amounts = sorted({value for item in records for value in _entity_values(item, "amounts")})
    markets = sorted({value for item in records for value in _entity_values(item, "markets")})
    assets = sorted({value for item in records for value in _entity_values(item, "asset_classes")})
    key = "|".join([
        " ".join(sorted(token for token, count in tokens.items() if count >= max(1, len(records) // 2))[:12]),
        ",".join(companies[:5]),
        ",".join(amounts[:4]),
        ",".join(markets[:3]),
        ",".join(assets[:3]),
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def _event_from_members(members: Iterable[dict[str, Any]]) -> dict[str, Any]:
    members = list(members)
    ordered = sorted(
        members,
        key=lambda item: (
            int(item.get("source_tier", 3) or 3),
            0 if item.get("source_authority") == "primary" else 1,
            -len(str(item.get("summary", ""))),
        ),
    )
    independent_domains = sorted({
        str(item.get("domain") or urlparse(str(item.get("url", ""))).netloc).lower()
        for item in members if item.get("url")
    })
    return {
        "event_id": event_fingerprint(members),
        "candidate": ordered[0],
        "sources": ordered,
        "source_count": len(independent_domains),
        "independent_domains": independent_domains,
        "cross_source": len(independent_domains) >= 2,
    }


def cluster_events(
    candidates: list[dict[str, Any]],
    *,
    threshold: float = 0.61,
) -> list[dict[str, Any]]:
    """Group semantically related headlines into reported events."""
    clusters: list[list[dict[str, Any]]] = []
    for candidate in candidates:
        best_index = -1
        best_score = 0.0
        for index, members in enumerate(clusters):
            score = max(event_similarity(candidate, member) for member in members)
            if score > best_score:
                best_index, best_score = index, score
        if best_index >= 0 and best_score >= threshold:
            clusters[best_index].append(candidate)
        else:
            clusters.append([candidate])

    return [_event_from_members(members) for members in clusters]


def attach_corroborating_sources(
    events: list[dict[str, Any]],
    candidates: Iterable[dict[str, Any]],
    *,
    threshold: float = 0.61,
    max_sources: int = 5,
) -> list[dict[str, Any]]:
    """Attach matching stories from the wider feed pool without admitting new events."""
    pool = list(candidates)
    expanded = []
    for event in events:
        members = list(event.get("sources", []))
        known_urls = {str(item.get("url", "")) for item in members}
        known_domains = {
            str(item.get("domain") or urlparse(str(item.get("url", ""))).netloc).lower()
            for item in members
        }
        matches = []
        for candidate in pool:
            url = str(candidate.get("url", ""))
            domain = str(
                candidate.get("domain") or urlparse(url).netloc
            ).lower()
            if not url or url in known_urls or domain in known_domains:
                continue
            similarity = max(
                event_similarity(candidate, member)
                for member in members
            )
            if similarity >= threshold:
                matches.append((similarity, candidate))
        matches.sort(
            key=lambda pair: (
                -pair[0],
                int(pair[1].get("source_tier", 3) or 3),
            )
        )
        for _, candidate in matches:
            if len(members) >= max_sources:
                break
            domain = str(
                candidate.get("domain")
                or urlparse(str(candidate.get("url", ""))).netloc
            ).lower()
            if domain in known_domains:
                continue
            members.append(candidate)
            known_domains.add(domain)
        expanded.append(_event_from_members(members))
    return expanded


def _dollar_amount_values(value: str) -> set[int]:
    amounts = set()
    for number, unit in re.findall(
        r"\$\s*([\d,.]+(?:\.\d+)?)\s*(million|billion|trillion|mm|bn|m|b)?\b",
        str(value or ""),
        flags=re.IGNORECASE,
    ):
        try:
            base = float(number.replace(",", ""))
        except ValueError:
            continue
        multiplier = {
            "m": 1_000_000,
            "mm": 1_000_000,
            "million": 1_000_000,
            "b": 1_000_000_000,
            "bn": 1_000_000_000,
            "billion": 1_000_000_000,
            "trillion": 1_000_000_000_000,
        }.get(unit.lower(), 1)
        amounts.add(round(base * multiplier))
    return amounts


def _street_addresses(value: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", match.lower()).strip()
        for match in re.findall(
            r"\b\d{1,5}\s+(?:(?:west|east|north|south|w|e)\s+)?"
            r"[a-z0-9'-]+(?:\s+[a-z0-9'-]+){0,2}\s+"
            r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|terrace|place)\b",
            str(value or ""),
            flags=re.IGNORECASE,
        )
    }


def _archive_is_recent(candidate: dict[str, Any], record: dict[str, Any], *, days: int = 7) -> bool:
    try:
        candidate_date = datetime.fromisoformat(
            str(candidate.get("published", "")).replace("Z", "+00:00")
        ).date()
        record_date = datetime.fromisoformat(
            str(record.get("date", ""))[:10]
        ).date()
    except (TypeError, ValueError):
        return False
    return abs((candidate_date - record_date).days) <= days


def archive_matches(
    event: dict[str, Any],
    archive_records: Iterable[dict[str, Any]],
    *,
    threshold: float = 0.38,
) -> list[dict[str, Any]]:
    """Find earlier Light Tower stories that may cover the same event or arc."""
    candidate = event["candidate"]
    event_sources = event.get("sources") or [candidate]
    candidate_title = str(candidate.get("title", ""))
    candidate_context = " ".join(
        " ".join([
            _text(source),
            " ".join((source.get("entities") or {}).get("companies") or []),
        ])
        for source in event_sources
    )
    candidate_companies = {
        str(company).lower()
        for source in event_sources
        for company in ((source.get("entities") or {}).get("companies") or [])
        if len(str(company)) >= 4
    }
    candidate_amounts = _dollar_amount_values(candidate_context)
    candidate_addresses = _street_addresses(candidate_context)
    matches: list[dict[str, Any]] = []
    for record in archive_records:
        record_title = str(record.get("title", ""))
        record_context = " ".join([
            record_title,
            str(record.get("excerpt", "")),
            " ".join(str(tag) for tag in (record.get("tags") or [])),
        ])
        title_score = _ratio(_tokens(candidate_title), _tokens(record_title))
        context_score = _ratio(_tokens(candidate_context), _tokens(record_context))
        amount_overlap = bool(candidate_amounts & _dollar_amount_values(record_context))
        address_overlap = bool(candidate_addresses & _street_addresses(record_context))
        entity_overlap = any(
            company in record_context.lower()
            for company in candidate_companies
        )
        same_event = bool(
            title_score >= 0.57
            or (amount_overlap and context_score >= 0.16)
            or (address_overlap and context_score >= 0.14)
            or (entity_overlap and context_score >= 0.24)
            or context_score >= threshold
        )
        if not same_event:
            continue
        score = max(
            title_score,
            context_score,
            0.78 if amount_overlap else 0,
            0.74 if address_overlap else 0,
            0.68 if entity_overlap else 0,
        )
        if score >= threshold:
            matches.append({
                "slug": record.get("slug"),
                "title": record.get("title"),
                "date": record.get("date"),
                "url": record.get("url"),
                "similarity": round(score, 3),
                "same_event": True,
                "recent": _archive_is_recent(candidate, record),
                "signals": {
                    "amount_overlap": amount_overlap,
                    "address_overlap": address_overlap,
                    "entity_overlap": entity_overlap,
                },
            })
    return sorted(matches, key=lambda item: item["similarity"], reverse=True)[:5]


def _presence_score(text: str, patterns: Iterable[str], maximum: int) -> int:
    hits = sum(bool(re.search(pattern, text, re.IGNORECASE)) for pattern in patterns)
    return min(maximum, hits * max(1, maximum // 2))


def _culture_dimensions(text: str) -> list[str]:
    return [name for name, pattern in _CULTURE_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]


def _source_quality(event: dict[str, Any]) -> int:
    sources = event.get("sources", [])
    tiers = [int(item.get("source_tier", 3) or 3) for item in sources]
    primary = any(item.get("source_authority") == "primary" for item in sources)
    count = int(event.get("source_count", 0))
    return min(10, (4 if tiers and min(tiers) <= 1 else 2) + min(4, max(0, count - 1) * 2) + (2 if primary else 0))


def _is_routine(
    text: str,
    item: dict[str, Any],
    *,
    aggregate_topics: set[str] | None = None,
) -> bool:
    routine_shape = any(re.search(pattern, text, re.IGNORECASE) for pattern in _ROUTINE_PATTERNS)
    topics = aggregate_topics if aggregate_topics is not None else set(item.get("topics") or [])
    counter_signal = bool(topics & {"distress", "policy", "fed_rates", "bank_credit", "government_action"})
    return routine_shape and not counter_signal and not _culture_dimensions(text)


def _event_topics(event: dict[str, Any]) -> set[str]:
    return {
        str(topic)
        for source in event.get("sources", [event.get("candidate", {})])
        for topic in (source.get("topics") or [])
    }


def _event_feature(event: dict[str, Any], name: str) -> bool:
    return any(
        bool((source.get("attention_features") or {}).get(name))
        for source in event.get("sources", [event.get("candidate", {})])
    )


def _event_entity_values(event: dict[str, Any], name: str) -> set[str]:
    return {
        str(value)
        for source in event.get("sources", [event.get("candidate", {})])
        for value in ((source.get("entities") or {}).get(name) or [])
    }


def score_event(
    event: dict[str, Any],
    archive_records: Iterable[dict[str, Any]] = (),
    *,
    audience_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score whether an event is worth a reader's finite attention."""
    item = event["candidate"]
    text = " ".join(_text(source) for source in event.get("sources", [item]))
    topics = _event_topics(event)
    features = {
        name: _event_feature(event, name)
        for name in {
            "has_material_transaction", "has_material_operating_signal",
            "has_big_number", "has_federal_source",
        }
    }
    culture_dimensions = _culture_dimensions(text)
    previous = archive_matches(event, archive_records)

    consequence = 4
    if features.get("has_material_transaction"):
        consequence += 5
    if features.get("has_material_operating_signal"):
        consequence += 4
    if features.get("has_big_number"):
        consequence += 3
    if topics & {"distress", "bank_credit", "fed_rates", "policy", "government_action"}:
        consequence += 5
    if re.search(r"\b(billion|bn|systemic|marketwide|national|industrywide)\b", text):
        consequence += 3
    consequence = min(15, consequence)

    novelty = _presence_score(text, _NOVELTY_PATTERNS, 15)
    if event.get("cross_source"):
        novelty += 3
    novelty = min(15, novelty)

    conflict = _presence_score(text, _CONFLICT_PATTERNS, 15)
    if topics & {"distress", "government_action"}:
        conflict = min(15, conflict + 4)

    explanatory_value = min(15, 3 + len(topics) * 2)
    if any(term in text for term in ("because", "pressure", "maturity", "liquidity", "insurance", "power", "constraint")):
        explanatory_value = min(15, explanatory_value + 3)

    cultural_relevance = min(10, len(culture_dimensions) * 3)
    human_stakes = 8 if re.search(_HUMAN_PATTERNS[0], text, re.IGNORECASE) else 0
    if human_stakes and topics & {"policy", "government_action", "distress"}:
        human_stakes = 10

    evidence_depth = _source_quality(event)
    right_to_win = 2
    if topics & {"capital_placement", "cmbs", "private_credit", "bank_credit", "distress"}:
        right_to_win += 5
    if _event_entity_values(event, "markets"):
        right_to_win += 2
    if _event_entity_values(event, "asset_classes"):
        right_to_win += 3
    if topics & {"capital_expenditure", "market_fundamentals", "leasing"}:
        right_to_win += 2
    if item.get("source_lane") in {"federal", "msa_government"}:
        right_to_win += 1
    right_to_win = min(10, right_to_win)

    conversation = min(10, (conflict // 3) + (cultural_relevance // 2) + (novelty // 4))
    signal_weights = (audience_signals or {}).get("weights", {})
    audience_adjustment = 0
    if isinstance(signal_weights, dict):
        for topic in topics:
            audience_adjustment += int(signal_weights.get(f"topic:{topic}", 0) or 0)
        for dimension in culture_dimensions:
            audience_adjustment += int(signal_weights.get(f"culture:{dimension}", 0) or 0)
        audience_adjustment += int(signal_weights.get(
            f"source:{item.get('domain', '')}", 0
        ) or 0)
    audience_adjustment = max(-5, min(5, audience_adjustment))
    routine_penalty = 18 if _is_routine(text, item, aggregate_topics=topics) else 0
    archive_repeat = any(match.get("recent") for match in previous)
    archive_penalty = 18 if archive_repeat else min(18, 9 * len(previous))

    breakdown = {
        "consequence": consequence,
        "novelty": novelty,
        "conflict_and_power": conflict,
        "explanatory_value": explanatory_value,
        "cultural_relevance": cultural_relevance,
        "human_stakes": human_stakes,
        "evidence_depth": evidence_depth,
        "light_tower_right_to_win": right_to_win,
        "conversation_potential": conversation,
        "audience_learning_adjustment": audience_adjustment,
        "routine_event_penalty": -routine_penalty,
        "archive_repetition_penalty": -archive_penalty,
    }
    score = max(0, min(100, sum(breakdown.values())))
    if archive_repeat:
        decision_reason = "Recent Light Tower coverage already addresses the same event or news arc."
    elif previous and score < 70:
        decision_reason = "Prior Light Tower coverage makes this an update, not a new standalone thesis."
    elif routine_penalty:
        decision_reason = "Routine transaction retained only if it earns a concise format."
    elif cultural_relevance:
        decision_reason = "Material capital event with a culture-of-money dimension."
    else:
        decision_reason = "Scored on consequence, evidence, explanatory value, and Light Tower relevance."

    return {
        **event,
        "must_read_score": score,
        "must_read_breakdown": breakdown,
        "culture_dimensions": culture_dimensions,
        "legal_or_allegation_risk": bool(re.search(
            r"\b(alleged|allegedly|fraud|criminal|charged|indicted|lawsuit|litigation|trial|guilty|not guilty)\b",
            text,
            re.IGNORECASE,
        )),
        "archive_matches": previous,
        "archive_repeat": archive_repeat,
        "aggregate_signals": {
            "topics": sorted(topics),
            "markets": sorted(_event_entity_values(event, "markets")),
            "asset_classes": sorted(_event_entity_values(event, "asset_classes")),
            "has_material_transaction": features.get("has_material_transaction", False),
            "has_material_operating_signal": features.get("has_material_operating_signal", False),
        },
        "decision_reason": decision_reason,
    }


def assign_franchise(scored_event: dict[str, Any]) -> dict[str, str]:
    item = scored_event["candidate"]
    text = " ".join(_text(source) for source in scored_event.get("sources", [item]))
    topics = _event_topics(scored_event)
    if scored_event.get("culture_dimensions"):
        key = "capital_after_dark"
    elif topics & {"distress", "cmbs"} or re.search(r"\b(maturity|extension|special servic)\b", text):
        key = "five_minutes_before_maturity"
    elif topics & {"bank_credit", "private_credit", "capital_placement"}:
        key = "credit_committee_theater"
    elif item.get("source_authority") == "primary" or topics & {"policy", "government_action"}:
        key = "what_the_release_left_out"
    elif topics & {"major_sale", "mna", "private_equity"}:
        key = "who_got_paid_who_got_stuck"
    else:
        key = "the_expensive_assumption"
    return {"id": key, **FRANCHISES[key]}


def daily_brief_eligible(item: dict[str, Any]) -> bool:
    """Return whether an event may enter the deeper daily research queue."""
    topics = _event_topics(item)
    features = {
        "has_material_transaction": _event_feature(item, "has_material_transaction"),
        "has_material_operating_signal": _event_feature(item, "has_material_operating_signal"),
    }
    asset_classes = _event_entity_values(item, "asset_classes")
    markets = _event_entity_values(item, "markets")
    has_capital_or_operating_signal = bool(
        topics & DAILY_BRIEF_TOPICS
        or features.get("has_material_transaction")
        or features.get("has_material_operating_signal")
    )
    has_cre_anchor = bool(
        asset_classes
        or markets
        or topics & {
            "capital_placement", "cmbs", "private_credit", "bank_credit",
            "distress", "reit_public_markets", "development_finance",
            "capital_expenditure", "market_fundamentals", "leasing",
        }
        or features.get("has_material_transaction")
        or features.get("has_material_operating_signal")
    )
    return bool(
        item.get("must_read_score", 0) >= DAILY_RESEARCH_FLOOR
        and has_capital_or_operating_signal
        and has_cre_anchor
        and not item.get("archive_repeat")
        and not item.get("legal_or_allegation_risk")
    )


def select_edition(
    candidates: list[dict[str, Any]],
    *,
    archive_records: Iterable[dict[str, Any]] = (),
    corroboration_candidates: Iterable[dict[str, Any]] = (),
    audience_signals: dict[str, Any] | None = None,
    max_briefs: int = 3,
    max_deal_tape: int = 8,
    max_articles: int = 5,
    daily_target: int = DEFAULT_DAILY_ARTICLE_TARGET,
) -> dict[str, Any]:
    """Create an evidence-sized portfolio with a quality-bounded daily floor."""
    archive = list(archive_records)
    events = cluster_events(candidates)
    corroboration_pool = list(corroboration_candidates)
    if corroboration_pool:
        events = attach_corroborating_sources(events, corroboration_pool)
    scored = [
        score_event(event, archive, audience_signals=audience_signals)
        for event in events
    ]
    scored.sort(key=lambda item: item["must_read_score"], reverse=True)
    for item in scored:
        item["franchise"] = assign_franchise(item)

    flagship = next((
        item for item in scored
        if item["must_read_score"] >= FLAGSHIP_CANDIDATE_THRESHOLD
        and not item.get("archive_repeat")
        and (item["source_count"] >= 2 or item["candidate"].get("source_authority") == "primary")
    ), None)

    selected: list[dict[str, Any]] = []
    if flagship:
        flagship["provisional_format"] = "flagship"
        flagship["decision"] = "research"
        flagship["selection_tier"] = "flagship"
        selected.append(flagship)

    source_usage: Counter[str] = Counter()
    for item in selected:
        source_usage[item["candidate"].get("domain", "")] += 1

    cultural = next((
        item for item in scored
        if item not in selected
        and not item.get("archive_repeat")
        and item["must_read_score"] >= MUST_READ_THRESHOLD
        and item["must_read_breakdown"]["cultural_relevance"] >= 6
    ), None)
    if cultural and len(selected) < max_articles:
        cultural["provisional_format"] = "culture_signal"
        cultural["decision"] = "research"
        cultural["selection_tier"] = "culture_signal"
        selected.append(cultural)
        source_usage[cultural["candidate"].get("domain", "")] += 1

    data_note = next((
        item for item in scored
        if item not in selected
        and not item.get("archive_repeat")
        and item["must_read_score"] >= 50
        and item["candidate"].get("source_authority") == "primary"
        and "data_release" in (
            (item["candidate"].get("entities") or {}).get("policy_actions") or []
        )
    ), None)
    if data_note and len(selected) < max_articles:
        data_note["provisional_format"] = "data_note"
        data_note["decision"] = "research"
        data_note["selection_tier"] = "data_note"
        selected.append(data_note)
        source_usage[data_note["candidate"].get("domain", "")] += 1

    for item in scored:
        if (
            item in selected
            or len(selected) >= max_articles
            or len([entry for entry in selected if entry["provisional_format"] == "brief"]) >= max_briefs
        ):
            continue
        domain = item["candidate"].get("domain", "")
        if (
            item.get("archive_repeat")
            or item["must_read_score"] < MUST_READ_THRESHOLD
            or source_usage[domain] >= 2
        ):
            continue
        item["provisional_format"] = "brief"
        item["decision"] = "research"
        item["selection_tier"] = "must_read"
        selected.append(item)
        source_usage[domain] += 1

    # A strict score remains the gateway to long-form. The daily research queue
    # is a separate, bounded path for clearly CRE-relevant events whose feed
    # snippets are too thin to establish their full value. These candidates
    # still face dossier, editorial-room, writing, duplication, and excellence
    # gates before an article can exist.
    research_target = min(max_articles, max(0, daily_target) + 2)
    for item in scored:
        if (
            item in selected
            or len(selected) >= research_target
            or len(selected) >= max_articles
            or len([entry for entry in selected if entry["provisional_format"] == "brief"]) >= max_briefs
        ):
            continue
        domain = item["candidate"].get("domain", "")
        if source_usage[domain] >= 2 or not daily_brief_eligible(item):
            continue
        item["provisional_format"] = "brief"
        item["decision"] = "research"
        item["selection_tier"] = "daily_depth"
        item["decision_reason"] = (
            "Entered the daily depth queue: concrete CRE capital or operating "
            "signal requires full-text research before a publication decision."
        )
        selected.append(item)
        source_usage[domain] += 1

    deal_tape: list[dict[str, Any]] = []
    for item in scored:
        if item in selected or len(deal_tape) >= max_deal_tape:
            continue
        if item.get("archive_repeat") or item.get("legal_or_allegation_risk"):
            continue
        features = {
            "has_material_transaction": _event_feature(item, "has_material_transaction"),
            "has_material_operating_signal": _event_feature(item, "has_material_operating_signal"),
        }
        if item["must_read_score"] < DEAL_TAPE_THRESHOLD and not (
            features.get("has_material_transaction")
            or features.get("has_material_operating_signal")
        ):
            continue
        item["provisional_format"] = "deal_tape"
        item["decision"] = "deal_tape"
        item["selection_tier"] = "deal_tape"
        deal_tape.append(item)

    for item in scored:
        if item not in selected and item not in deal_tape:
            if item.get("archive_repeat"):
                item["decision"] = "archive_repeat"
            else:
                item["decision"] = "reject"
            item["rejection_reason"] = item.get("decision_reason")

    status = "edition_ready" if selected or deal_tape else "no_publishable_story"
    return {
        "selection_mode": "edition",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "candidate_count": len(candidates),
        "event_count": len(scored),
        "selected_stories": selected,
        "deal_tape": deal_tape,
        "scored_events": scored,
        "duplicate_groups": [
            {
                "event_id": item["event_id"],
                "titles": [source["title"] for source in item["sources"]],
                "source_count": item["source_count"],
            }
            for item in scored if len(item["sources"]) > 1
        ],
        "archive_repeats": [
            {
                "event_id": item["event_id"],
                "title": item["candidate"]["title"],
                "matches": item.get("archive_matches", []),
            }
            for item in scored if item.get("archive_repeat")
        ],
        "daily_target": min(max_articles, max(0, daily_target)),
        "research_target": research_target,
        "edition_limits": {
            "flagship": 1,
            "culture_signal": 1,
            "data_note": 1,
            "brief": max_briefs,
            "deal_tape": max_deal_tape,
            "total_articles": max_articles,
        },
    }


def print_edition_report(selection: dict[str, Any]) -> None:
    print("\nEdition Editorial Report:")
    print(
        f"  {selection.get('candidate_count', 0)} candidates became "
        f"{selection.get('event_count', 0)} distinct events"
    )
    print(
        f"  Daily target: {selection.get('daily_target', 0)} article(s); "
        f"research queue: {len(selection.get('selected_stories', []))}/"
        f"{selection.get('research_target', 0)}"
    )
    if selection.get("archive_repeats"):
        print(f"  Suppressed {len(selection['archive_repeats'])} recent archive repeat(s)")
    if not selection.get("selected_stories") and not selection.get("deal_tape"):
        print("  No event earned publication today. A no-story edition is valid.")
        return
    for item in selection.get("selected_stories", []):
        spec = FORMAT_SPECS[item["provisional_format"]]["label"]
        print(
            f"  RESEARCH [{item['must_read_score']}/100] {spec} "
            f"({item.get('selection_tier', 'standard')}): "
            f"{item['candidate']['title'][:95]}"
        )
    for item in selection.get("deal_tape", []):
        print(f"  TAPE [{item['must_read_score']}/100]: {item['candidate']['title'][:95]}")
