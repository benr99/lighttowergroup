"""Editorial-room planning and positive excellence controls."""

from __future__ import annotations

import json
import re
from typing import Any

from content_governance import html_to_text
from editorial_intelligence import FORMAT_SPECS
from editorial_scoring import call_deepseek


EDITORIAL_CONSTITUTION = (
    "Light Tower publishes only when it can make a smart reader see a capital "
    "decision differently. Accuracy is the floor. The work must add consequence, "
    "mechanism, human or institutional stakes, candor, and a bounded point of "
    "view. Routine facts belong in the deal tape. Wit must be earned by a true "
    "observation. A valid editorial outcome is to kill, shorten, or defer a story."
)

_DAILY_DEPTH_HARD_STOP = re.compile(
    r"\b(?:alleg(?:ation|ed|edly)|lawsuit|litigation|criminal|fraud|indict(?:ed|ment)?|"
    r"charged|legal risk|conflicting facts?|contradict(?:ion|ory)?|unreliable source|"
    r"source authenticity|fabricat(?:ed|ion)|cannot verify|unsupported "
    r"(?:number|figure|claim)|duplicate|already covered)\b",
    re.IGNORECASE,
)


def _extract_json(raw: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", str(raw or ""))
    if not match:
        return {}
    try:
        payload = json.loads(match.group())
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def deterministic_room_plan(
    editorial_event: dict[str, Any],
    dossier: dict[str, Any],
) -> dict[str, Any]:
    """Safe plan used when a model critique is unavailable."""
    desired = editorial_event.get("provisional_format", "brief")
    final_format = desired
    if desired == "flagship" and not dossier.get("longform_allowed"):
        final_format = "brief"
    elif desired == "culture_signal" and dossier.get("independent_source_count", 0) < 2:
        final_format = "brief"
    if dossier.get("evidence_level") == "insufficient":
        final_format = "deal_tape"
    candidate = editorial_event.get("candidate", {})
    franchise = editorial_event.get("franchise", {})
    selection_tier = editorial_event.get("selection_tier")
    why_now = (
        "The event is recent and entered the quality-bounded daily-depth "
        "research queue on a concrete CRE capital or operating signal."
        if selection_tier == "daily_depth"
        else "The event is recent and cleared Light Tower's strict must-read threshold."
    )
    return {
        "decision": "write" if final_format != "deal_tape" else "deal_tape",
        "final_format": final_format,
        "angle": franchise.get("promise") or "Explain the decision, constraint, and consequence beneath the event.",
        "why_now": why_now,
        "favored_thesis": "",
        "alternate_angles": [],
        "skeptic_objections": [
            "Do not claim a market-wide shift from one transaction.",
            "Do not infer unreported motives or private negotiations.",
        ],
        "reporting_gaps": dossier.get("reporting_gaps", []),
        "human_stakes": "",
        "concrete_detail": next(
            (item.get("fact", "") for item in dossier.get("reported_facts", [])),
            candidate.get("summary", ""),
        ),
        "kill_reason": "",
        "generation_mode": "deterministic-editorial-plan",
    }


def _daily_depth_brief_is_supported(
    editorial_event: dict[str, Any],
    dossier: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    """Keep model taste from silently replacing the deterministic brief contract."""
    if editorial_event.get("selection_tier") != "daily_depth":
        return False
    if editorial_event.get("legal_or_allegation_risk"):
        return False
    if dossier.get("evidence_level") == "insufficient":
        return False
    if int(dossier.get("usable_full_text_count") or 0) < 1:
        return False
    if len(dossier.get("reported_facts") or []) < 3:
        return False
    risk_text = json.dumps({
        "kill_reason": result.get("kill_reason"),
        "reporting_gaps": result.get("reporting_gaps"),
        "skeptic_objections": result.get("skeptic_objections"),
    }, ensure_ascii=False)
    return not _DAILY_DEPTH_HARD_STOP.search(risk_text)


def run_editorial_room(
    editorial_event: dict[str, Any],
    dossier: dict[str, Any],
    *,
    api_key: str,
    editorial_priors: dict[str, Any] | None = None,
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask an angle editor and skeptic to decide whether and how to proceed."""
    fallback = deterministic_room_plan(editorial_event, dossier)
    if not api_key or fallback["decision"] == "deal_tape":
        return fallback

    candidate = editorial_event.get("candidate", {})
    prompt = f"""You are the angle editor and skeptical assigning editor for Light Tower Group.

EDITORIAL CONSTITUTION
{EDITORIAL_CONSTITUTION}

EVENT
{json.dumps({
    "title": candidate.get("title"),
    "summary": candidate.get("summary"),
    "score": editorial_event.get("must_read_score"),
    "score_breakdown": editorial_event.get("must_read_breakdown"),
    "franchise": editorial_event.get("franchise"),
    "desired_format": editorial_event.get("provisional_format"),
    "selection_tier": editorial_event.get("selection_tier"),
}, ensure_ascii=False)}

DOSSIER CONTROL DATA
{json.dumps({
    "evidence_level": dossier.get("evidence_level"),
    "independent_source_count": dossier.get("independent_source_count"),
    "primary_source_count": dossier.get("primary_source_count"),
    "reported_facts": dossier.get("reported_facts", [])[:16],
    "prior_light_tower_context": dossier.get("prior_light_tower_context"),
    "reporting_gaps": dossier.get("reporting_gaps"),
    "counterquestions": dossier.get("counterquestions"),
}, ensure_ascii=False)}

LIGHT TOWER EDITORIAL PRIORS
{json.dumps(editorial_priors or {}, ensure_ascii=False)}

Act as an editorial room, not a copywriter:
1. Propose materially different angles.
2. Select one bounded thesis supported by the dossier.
3. State the strongest skeptical objections.
4. Identify the human or institutional stakes and one source-grounded concrete detail.
5. Decide write, shorten, deal_tape, defer, or kill.
6. A flagship requires at least three independent sources and two usable full-text sources.
7. Do not reward length, seriousness, or a large dollar amount by themselves.
8. Treat editorial priors as hypotheses to test, never as facts to impose.
9. For a daily_depth brief, one reputable retrieved source is sufficient when
   it supplies at least three concrete reported facts and supports a useful,
   tightly bounded CRE implication. Do not require a second source merely to
   restate a disclosed lease, capital project, transaction, or market dataset.
10. Missing human stakes alone is not a reason to defer an asset-level brief;
    identify the institutional decision, constraint, or exposure instead.
11. Defer or kill a daily_depth brief for contradictory or unverified facts,
    legal/allegation risk, weak source authenticity, duplication, or no
    defensible CRE consequence—not merely because it is concise or single-source.

Return only JSON with:
decision, final_format, angle, why_now, favored_thesis, alternate_angles,
skeptic_objections, reporting_gaps, human_stakes, concrete_detail, kill_reason.
final_format must be flagship, brief, culture_signal, data_note, or deal_tape.
"""
    try:
        result = _extract_json(call_deepseek(
            prompt,
            api_key,
            max_tokens=1800,
            temperature=0.15,
            json_mode=True,
            provider=provider,
        ))
    except Exception as exc:
        fallback["reporting_gaps"] = list(fallback["reporting_gaps"]) + [
            f"Editorial-room model was unavailable: {type(exc).__name__}."
        ]
        return fallback

    decision = str(result.get("decision", "")).lower()
    final_format = str(result.get("final_format", "")).lower()
    if decision not in {"write", "shorten", "deal_tape", "defer", "kill"}:
        decision = fallback["decision"]
    if final_format not in FORMAT_SPECS:
        final_format = fallback["final_format"]
    if final_format == "flagship" and not dossier.get("longform_allowed"):
        final_format = "brief"
        decision = "shorten"
    if final_format == "culture_signal" and dossier.get("independent_source_count", 0) < 2:
        final_format = "brief"
        decision = "shorten"

    room_plan = {
        **fallback,
        **{key: value for key, value in result.items() if value not in (None, "")},
        "decision": decision,
        "final_format": final_format,
        "generation_mode": "deepseek-editorial-room",
    }
    if (
        decision in {"deal_tape", "defer", "kill"}
        and _daily_depth_brief_is_supported(editorial_event, dossier, result)
    ):
        room_plan.update({
            "decision": "shorten",
            "final_format": "brief",
            "kill_reason": "",
            "daily_depth_floor_applied": True,
            "original_decision": decision,
            "daily_depth_objection": str(result.get("kill_reason") or ""),
        })
    return room_plan


def excellence_issues(
    article: dict[str, Any],
    dossier: dict[str, Any],
    *,
    article_format: str,
) -> list[str]:
    """Require positive editorial qualities, not only the absence of AI tells."""
    issues: list[str] = []
    spec = FORMAT_SPECS.get(article_format, FORMAT_SPECS["brief"])
    text = html_to_text(str(article.get("body_html", "")))
    word_count = len(text.split())
    tolerance = 25
    if word_count < max(80, spec["min_words"] - tolerance):
        issues.append(f"excellence gate: {article_format} is below {spec['min_words']} words")
    if word_count > spec["max_words"] + 75:
        issues.append(f"excellence gate: {article_format} exceeds {spec['max_words']} words")

    independent_sources = {
        str(source.get("url", "")).split("/")[2].lower().removeprefix("www.")
        for source in article.get("sources", [])
        if isinstance(source, dict) and str(source.get("url", "")).startswith(("http://", "https://"))
    }
    minimum = int(spec["minimum_independent_sources"])
    if len(independent_sources) < minimum:
        issues.append(
            f"excellence gate: {article_format} requires {minimum} independent source(s)"
        )
    if article_format == "flagship" and not dossier.get("longform_allowed"):
        issues.append("excellence gate: dossier does not permit flagship long-form")
    if article_format == "brief":
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip()
        ]
        speculative_sentences = [
            sentence for sentence in sentences
            if re.search(
                r"\b(?:may|might|could|perhaps|possibly|speculative|betting)\b",
                sentence,
                re.IGNORECASE,
            )
        ]
        if len(speculative_sentences) > 3:
            issues.append(
                "excellence gate: brief stacks too many hypothetical claims"
            )

        dossier_text = " ".join(
            " ".join([
                str(source.get("summary", "")),
                str(source.get("full_text_excerpt", "")),
            ])
            for source in dossier.get("sources", [])
            if isinstance(source, dict)
        )
        redevelopment_context = re.search(
            r"\b(?:redevelop\w*|renovat\w*|moderniz\w*|reposition\w*|"
            r"gut[- ]renovat\w*)\b",
            dossier_text,
            re.IGNORECASE,
        )
        claims_new_supply = re.search(
            r"\b(?:add(?:s|ed|ing)?|deliver(?:s|ed|ing)?)\b[^.]{0,90}"
            r"\bnew (?:office |retail |industrial )?(?:space|supply)\b",
            text,
            re.IGNORECASE,
        )
        explicit_net_new_area = re.search(
            r"\b(?:ground[- ]up|new construction|additional (?:floor )?area|"
            r"net[- ]new|expand\w* (?:the )?(?:building|floor area)|"
            r"increase\w* (?:gross )?floor area)\b",
            dossier_text,
            re.IGNORECASE,
        )
        if redevelopment_context and claims_new_supply and not explicit_net_new_area:
            issues.append(
                "excellence gate: redevelopment is mislabeled as net-new supply"
            )
    allowed_urls = {
        str(source.get("url", ""))
        for source in dossier.get("sources", [])
        if isinstance(source, dict)
    }
    article_urls = {
        str(source.get("url", ""))
        for source in article.get("sources", [])
        if isinstance(source, dict)
    }
    if article_urls - allowed_urls:
        issues.append("excellence gate: article cites a URL outside the verified dossier")
    if article_format == "data_note":
        data_points = article.get("data_points")
        if not isinstance(data_points, list) or not data_points:
            issues.append("excellence gate: data note requires at least one sourced data point")
        elif any(
            str(point.get("source_url", "")) not in allowed_urls
            for point in data_points if isinstance(point, dict)
        ):
            issues.append("excellence gate: data note contains an unverified data-point URL")

    ledger = article.get("excellence_ledger")
    if not isinstance(ledger, dict):
        return issues + ["excellence gate: positive-quality ledger is missing"]
    required_text = (
        "why_now", "original_inference", "counterargument", "concrete_detail",
        "human_stakes", "reader_value", "memorable_line",
    )
    for field in required_text:
        if not str(ledger.get(field, "")).strip():
            issues.append(f"excellence gate: missing {field}")
    if not isinstance(ledger.get("claim_evidence"), list) or not ledger.get("claim_evidence"):
        issues.append("excellence gate: claim-evidence map is missing")
    elif any(
        str(item.get("source_url", "")) not in allowed_urls
        for item in ledger["claim_evidence"]
        if isinstance(item, dict)
    ):
        issues.append("excellence gate: claim-evidence map contains an unverified URL")
    if str(ledger.get("memorable_line", "")).strip() not in text:
        issues.append("excellence gate: memorable line does not appear in the article")

    if len(re.findall(r"\b(?:the question is|the signal is|the implication is|this is not|it is not)\b", text, re.I)) > 2:
        issues.append("excellence gate: article falls back on repeated house abstractions")
    return list(dict.fromkeys(issues))
