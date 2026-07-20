"""Volume-oriented editorial routing and scoring for Light Tower Insights.

The existing ``daily-top-news`` desk selects a small ranked list.  This module
implements a separate mode: every distinct, relevant story is routed to its
proper editorial lane and may publish when it clears that lane's evidence and
score requirements.  It deliberately has no category quota or final ranking
cap.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from editorial_scoring import MODEL_NAME, call_deepseek


PUBLISH_SCORE = 65
REVIEW_SCORE = 55

BUCKETS = (
    "cre_capital_markets",
    "cre_transactions_development",
    "banking_credit",
    "private_equity_private_capital",
    "policy_rates_public_markets",
)

_BUCKET_LABELS = {
    "cre_capital_markets": "CRE Capital Markets",
    "cre_transactions_development": "CRE Transactions & Development",
    "banking_credit": "Banking & Credit",
    "private_equity_private_capital": "Private Equity & Private Capital",
    "policy_rates_public_markets": "Policy, Rates & Public Markets",
}

_BUCKET_PATTERNS = {
    "cre_capital_markets": (
        r"\b(refinanc\w*|bridge loan|construction loan|mortgage|debt fund|credit facility|"
        r"mezzanine|cmbs|cre clo|special servic\w*|default\w*|foreclos\w*|workout\w*|note sale|"
        r"capital stack|lender|loan)\b",
    ),
    "cre_transactions_development": (
        r"\b(acquir|purchas|buys?|sold|sale|disposition|leasing|lease|development|"
        r"groundbreaking|approved|approval|permit|conversion|rezoning|units?|tower|project)\b",
    ),
    "banking_credit": (
        r"\b(bank|banking|loan.loss|loss reserve|charge-off|credit standard|capital ratio|"
        r"lending standard|commercial real estate exposure|fdic|occ|bank regulator)\b",
    ),
    "private_equity_private_capital": (
        r"\b(private equity|private capital|private credit|fundraise|fund closes|fund launch|"
        r"capital raise|institutional allocat|pension fund|sovereign wealth|family office|"
        r"joint venture|\bjv\b|investment manager|asset manager)\b",
    ),
    "policy_rates_public_markets": (
        r"\b(federal reserve|\bfed\b|treasury|rate cut|rate hike|interest rate|sofr|"
        r"inflation|reit|earnings|guidance|shares|fhfa|hud|sec |zoning|tax credit|"
        r"legislation|regulation|final rule|proposed rule|public hearing)\b",
    ),
}

_POLICY_AUTHORITIES = ("federal reserve", "fdic", "occ", "treasury", "fhfa", "hud", "sec ")
_EXCLUDED_NOISE = (
    "single-family home", "single family home", "open house", "celebrity home", "home decor",
    "interior design", "renovation tips", "diy home", "reality tv", "weather forecast",
)
_NON_US_MARKERS = (
    "japan", "india", "european", "europe", "london", "singapore", "australia", "canada",
    "germany", "france", "china", "hong kong", "dubai", "uk ", "united kingdom",
)


def _text(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()


def _matches(text: str, bucket: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _BUCKET_PATTERNS[bucket])


def _has_property_context(text: str, candidate: dict[str, Any]) -> bool:
    asset_classes = (candidate.get("entities") or {}).get("asset_classes") or []
    return bool(asset_classes) or bool(re.search(
        r"\b(commercial real estate|real estate|multifamily|apartment|office|industrial|warehouse|"
        r"retail|hotel|housing|development|property|building|land|mixed-use)\b", text,
    ))


def route_story(candidate: dict[str, Any]) -> dict[str, Any]:
    """Assign a primary editorial bucket plus relevant secondary buckets."""
    text = _text(candidate)
    topics = set(candidate.get("topics") or [])
    features = candidate.get("attention_features") or {}
    matches = [bucket for bucket in BUCKETS if _matches(text, bucket)]

    # Policy and bank stories need a demonstrated CRE/credit transmission; a
    # generic political or corporate headline must not enter the desk.
    if "policy_rates_public_markets" in matches:
        policy_related = any(authority in text for authority in _POLICY_AUTHORITIES) or "reit" in text
        if not policy_related and not (_has_property_context(text, candidate) and "zoning" in text):
            matches.remove("policy_rates_public_markets")
    if "banking_credit" in matches and not (
        _has_property_context(text, candidate)
        or any(topic in topics for topic in {"bank_credit", "capital_placement", "cmbs", "distress"})
        or "commercial real estate" in text
    ):
        matches.remove("banking_credit")

    if not matches:
        return {"primary_bucket": None, "secondary_buckets": [], "route_reason": "No qualifying editorial bucket"}

    # Specific direct activity should lead the angle. The remaining matching
    # buckets are still retained for reporting and topical context.
    priority = [
        "banking_credit" if any(term in text for term in ("loan loss", "loss reserve", "charge-off", "credit standard", "capital ratio")) else "",
        "private_equity_private_capital" if any(term in text for term in ("fundraise", "fund closes", "pension fund", "sovereign wealth", "family office", "private equity")) else "",
        "cre_capital_markets" if any(topic in topics for topic in {"capital_placement", "cmbs", "distress", "private_credit"}) or features.get("has_material_transaction") else "",
        "cre_transactions_development" if any(topic in topics for topic in {"major_sale", "development_finance", "mna"}) else "",
        "policy_rates_public_markets" if features.get("has_federal_source") or "reit" in text else "",
    ]
    primary = next((bucket for bucket in priority if bucket and bucket in matches), matches[0])
    secondary = [bucket for bucket in matches if bucket != primary]
    return {
        "primary_bucket": primary,
        "secondary_buckets": secondary,
        "route_reason": f"Matched {_BUCKET_LABELS[primary]} signals",
    }


def _points(condition: bool, amount: int) -> int:
    return amount if condition else 0


def _evidence(candidate: dict[str, Any]) -> tuple[bool, int]:
    entities = candidate.get("entities") or {}
    text = _text(candidate)
    signals = sum((
        bool(entities.get("amounts")),
        bool(entities.get("companies")),
        bool(entities.get("markets")),
        bool(entities.get("asset_classes")),
        bool(re.search(r"\b(?:loan|sale|fund|approval|reserve|rule|refinanc|acquir|invest)\b", text)),
    ))
    return signals >= 2, signals


def _source_points(candidate: dict[str, Any], maximum: int) -> int:
    tier = int(candidate.get("source_tier", 3) or 3)
    return maximum if tier <= 1 else max(1, maximum - 2) if tier == 2 else max(0, maximum - 4)


def _score_breakdown(candidate: dict[str, Any], bucket: str) -> dict[str, int]:
    text = _text(candidate)
    entities = candidate.get("entities") or {}
    features = candidate.get("attention_features") or {}
    topics = set(candidate.get("topics") or [])
    has_amount = bool(entities.get("amounts"))
    has_party = bool(entities.get("companies"))
    has_market_or_asset = bool(entities.get("markets")) or bool(entities.get("asset_classes"))
    has_property = _has_property_context(text, candidate)
    institutional = features.get("has_known_institution") or has_party
    fresh = 10

    if bucket == "cre_capital_markets":
        return {
            "capital_stack_impact": _points(
                bool(topics & {"capital_placement", "cmbs", "distress", "private_credit"})
                or any(term in text for term in ("refinanc", "loan", "mortgage", "debt", "cmbs", "lender", "mezzanine")),
                25,
            ),
            "transaction_scale": _points(has_amount, 20),
            "deal_evidence": min(20, _points(has_amount, 8) + _points(has_party, 6) + _points(has_market_or_asset, 6)),
            "pricing_or_risk_signal": _points(bool(topics & {"distress", "cmbs", "bank_credit"}), 15),
            "institutional_importance": _points(bool(institutional), 10),
            "timeliness": fresh,
        }
    if bucket == "cre_transactions_development":
        return {
            "transaction_or_project_significance": _points(bool(topics & {"major_sale", "development_finance", "mna"}) or "approval" in text, 25),
            "market_or_supply_implication": _points(has_property and has_market_or_asset, 20),
            "specific_evidence": min(20, _points(has_amount, 7) + _points(has_party, 6) + _points(has_market_or_asset, 7)),
            "asset_market_importance": _points(has_property, 15),
            "institutional_relevance": _points(bool(institutional), 10),
            "timeliness": fresh,
        }
    if bucket == "banking_credit":
        return {
            "cre_credit_transmission": _points(has_property or "commercial real estate" in text, 30),
            "lender_or_regulator_materiality": _points(bool(institutional) or any(a in text for a in _POLICY_AUTHORITIES), 20),
            "credit_or_capital_consequence": _points(any(term in text for term in ("reserve", "charge-off", "credit standard", "lending", "capital ratio", "loss")), 20),
            "specific_evidence": min(15, _points(has_amount, 5) + _points(has_party, 5) + _points(has_market_or_asset, 5)),
            "market_consequence": _points(any(term in text for term in ("lending", "credit", "liquidity", "loan")), 10),
            "timeliness": 5,
        }
    if bucket == "private_equity_private_capital":
        return {
            "capital_activity": _points(any(term in text for term in ("fundraise", "fund closes", "capital raise", "investment", "commitment", "private credit", "joint venture")), 25),
            "cre_or_credit_consequence": _points(has_property or bool(topics & {"private_credit", "capital_placement", "private_equity"}), 20),
            "manager_or_investor_significance": _points(bool(institutional), 15),
            "strategy_or_allocation_signal": _points(any(term in text for term in ("strategy", "allocation", "fund", "deploy", "investment")), 15),
            "specific_evidence": min(15, _points(has_amount, 5) + _points(has_party, 5) + _points(has_market_or_asset, 5)),
            "timeliness": fresh,
        }
    return {
        "direct_transmission": _points(has_property or any(a in text for a in _POLICY_AUTHORITIES) or "reit" in text, 30),
        "event_materiality": _points(has_amount or bool(features.get("has_federal_source")) or "reit" in text, 20),
        "specific_evidence": min(15, _points(has_amount, 5) + _points(has_party, 5) + _points(has_market_or_asset, 5)),
        "financing_values_or_supply_impact": _points(any(term in text for term in ("rate", "credit", "zoning", "tax", "housing", "reit", "financ")), 15),
        "institutional_market_importance": _points(bool(institutional) or bool(features.get("has_federal_source")), 10),
        "timeliness": fresh,
    }


def _noise_penalty(candidate: dict[str, Any]) -> int:
    text = _text(candidate)
    if any(term in text for term in _EXCLUDED_NOISE):
        return 40
    if "single-family" in text or "0-down" in text or "zero-down" in text:
        return 30
    if any(marker in text for marker in _NON_US_MARKERS) and not any(
        marker in text for marker in ("u.s.", "us capital", "united states", "new york", "manhattan", "brooklyn")
    ):
        return 20
    if not _has_property_context(text, candidate) and not any(authority in text for authority in _POLICY_AUTHORITIES):
        return 15
    return 0


def _model_prompt(items: list[dict[str, Any]], today: str) -> str:
    payload = [
        {
            "index": item["index"],
            "bucket": item["primary_bucket"],
            "title": item["candidate"]["title"],
            "summary": item["candidate"].get("summary", "")[:360],
            "deterministic_score": item["deterministic_score"],
        }
        for item in items
    ]
    return f"""You are an editorial second-opinion system for Light Tower Group. Score each news item 0-100 for its assigned bucket only. Today's date is {today}.

Do not compare stories against other buckets. Reward a concrete, evidenced story that matters to its assigned CRE, banking, private-capital, or policy audience. Penalize noise, vague claims, and weak transmission to the assigned audience.

Return only JSON: {{\"scores\":[{{\"index\":1,\"score\":72,\"reason\":\"one concise explanation\"}}]}}.

Items:\n{json.dumps(payload, ensure_ascii=False)}"""


def _extract_model_scores(raw: str) -> dict[int, dict[str, Any]]:
    try:
        match = re.search(r"\{[\s\S]*\}", raw or "")
        payload = json.loads(match.group() if match else raw)
        return {int(row["index"]): row for row in payload.get("scores", []) if isinstance(row, dict) and row.get("index")}
    except Exception:
        return {}


def bucketed_volume_selection(
    candidates: list[dict[str, Any]],
    *,
    api_key: str,
    today: str | None = None,
    article_limit: int | None = None,
) -> dict[str, Any]:
    """Route and score all candidates; never apply a category quota."""
    today = today or datetime.now(timezone.utc).date().isoformat()
    routed: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        route = route_story(candidate)
        evidence_ok, evidence_signals = _evidence(candidate)
        if not route["primary_bucket"]:
            routed.append({
                "index": index, "candidate": candidate, **route, "decision": "reject",
                "reason": route["route_reason"], "evidence_ok": evidence_ok,
            })
            continue
        breakdown = _score_breakdown(candidate, route["primary_bucket"])
        penalty = _noise_penalty(candidate)
        deterministic_score = max(0, min(100, sum(breakdown.values()) - penalty))
        routed.append({
            "index": index, "candidate": candidate, **route, "score_breakdown": breakdown,
            "penalty": penalty, "deterministic_score": deterministic_score,
            "evidence_ok": evidence_ok, "evidence_signals": evidence_signals,
        })

    model_scores: dict[int, dict[str, Any]] = {}
    eligible_for_model = [item for item in routed if item.get("primary_bucket")]
    if api_key and eligible_for_model:
        for start in range(0, len(eligible_for_model), 15):
            batch = eligible_for_model[start:start + 15]
            try:
                model_scores.update(_extract_model_scores(call_deepseek(
                    _model_prompt(batch, today), api_key, max_tokens=2200, temperature=0.1, json_mode=True,
                )))
            except Exception as exc:
                print(f"  [WARN] Bucketed editorial second opinion failed: {exc}; using deterministic scores")

    for item in routed:
        if not item.get("primary_bucket"):
            continue
        model = model_scores.get(item["index"], {})
        model_score = int(round(float(model.get("score", item["deterministic_score"])))) if model else item["deterministic_score"]
        item["model_score"] = max(0, min(model_score, 100))
        item["model_reason"] = str(model.get("reason", "Deterministic bucket score used."))
        item["final_score"] = round(0.65 * item["deterministic_score"] + 0.35 * item["model_score"])
        if not item["evidence_ok"]:
            item["decision"] = "reject"
            item["reason"] = "Insufficient specific evidence for automatic editorial coverage"
        elif item["penalty"] >= 20:
            item["decision"] = "reject"
            item["reason"] = "Excluded consumer, lifestyle, or non-editorial story"
        elif item["final_score"] >= PUBLISH_SCORE:
            item["decision"] = "publish"
            item["reason"] = f"Cleared {_BUCKET_LABELS[item['primary_bucket']]} publishing threshold ({PUBLISH_SCORE})"
        elif item["final_score"] >= REVIEW_SCORE:
            item["decision"] = "review"
            item["reason"] = f"Real story below automatic threshold; save for editorial review ({REVIEW_SCORE}-{PUBLISH_SCORE - 1})"
        else:
            item["decision"] = "reject"
            item["reason"] = f"Below {_BUCKET_LABELS[item['primary_bucket']]} review threshold ({REVIEW_SCORE})"

    publishable = [item for item in routed if item.get("decision") == "publish"]
    publishable.sort(key=lambda item: item["final_score"], reverse=True)
    if article_limit is not None:
        publishable = publishable[:article_limit]
    bucket_counts = Counter(item.get("primary_bucket") for item in routed if item.get("primary_bucket"))
    decision_counts = Counter(item.get("decision") for item in routed)
    published_by_bucket = Counter(item["primary_bucket"] for item in publishable)
    return {
        "selection_mode": "bucketed-volume",
        "model": MODEL_NAME if api_key else "deterministic-fallback",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "today": today,
        "candidate_count": len(candidates),
        "bucket_counts": dict(bucket_counts),
        "decision_counts": dict(decision_counts),
        "published_by_bucket": dict(published_by_bucket),
        "publishable_candidate_count": len([item for item in routed if item.get("decision") == "publish"]),
        "selected_stories": publishable,
        "review_stories": [item for item in routed if item.get("decision") == "review"],
        "scored_candidates": routed,
        "duplicate_groups": [],
    }


def print_bucketed_volume_report(selection: dict[str, Any]) -> None:
    print("\nBucketed Volume Editorial Report:")
    for bucket in BUCKETS:
        print(f"  {_BUCKET_LABELS[bucket]}: {selection.get('bucket_counts', {}).get(bucket, 0)} candidate(s), "
              f"{selection.get('published_by_bucket', {}).get(bucket, 0)} publishable")
    print(f"  Decisions: {json.dumps(selection.get('decision_counts', {}), ensure_ascii=False)}")
    for item in selection.get("selected_stories", []):
        print(f"  PUBLISH [{item['final_score']}/100] {_BUCKET_LABELS[item['primary_bucket']]}: "
              f"{item['candidate']['title'][:95]}")
    for item in selection.get("review_stories", [])[:10]:
        print(f"  REVIEW [{item['final_score']}/100] {_BUCKET_LABELS[item['primary_bucket']]}: "
              f"{item['candidate']['title'][:95]}")
