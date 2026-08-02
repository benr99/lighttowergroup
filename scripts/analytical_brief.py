"""Structured analytical brief generation — pre-writing reasoning for every story.

Before an article is written, this module produces a comprehensive analytical
brief covering: event summary, parties and incentives, transaction economics,
market context, central financial question, core tension, thesis,
counterargument, unknowns, reader relevance, article architecture, depth,
and key numbers.

This is NOT prose generation. It is structured reasoning output that the
writing stage consumes as input.
"""

from __future__ import annotations
import json
import re
from typing import Any

from canonical_item import CanonicalItem


def _safe_float(value: Any) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r'[^\d.\-eE]', '', value.strip())
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def build_analytical_brief(
    item: CanonicalItem,
    dossier: dict[str, Any] | None = None,
    source_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Build a complete analytical brief for a news story.

    This is a deterministic + LLM-assisted process that produces structured
    reasoning output. It does NOT generate article prose.

    Args:
        item: The classified and scored CanonicalItem.
        dossier: The research dossier (from research_dossier.py).
        source_texts: Full text from each source in the dossier.

    Returns:
        A dict with all analytical brief fields.
    """
    brief = {
        "event_summary": _build_event_summary(item, dossier),
        "parties_and_incentives": _build_parties(item, dossier),
        "transaction_economics": _build_economics(item, dossier, source_texts),
        "market_context": _build_market_context(item, dossier),
        "central_financial_question": _identify_central_question(item),
        "core_tension": _identify_tension(item),
        "thesis": _build_thesis(item),
        "counterargument": _build_counterargument(item),
        "unknowns": _identify_unknowns(item, dossier),
        "reader_relevance": _build_reader_relevance(item),
        "article_architecture": _select_architecture(item),
        "article_depth": _select_depth(item),
        "key_numbers": _extract_key_numbers(item),
    }
    return brief


def _build_event_summary(item: CanonicalItem, dossier: dict[str, Any] | None) -> dict[str, Any]:
    """Extract confirmed facts and flag uncertainties."""
    facts = []
    if dossier and isinstance(dossier, dict):
        for fact in dossier.get("reported_facts", [])[:10]:
            if isinstance(fact, dict):
                facts.append(fact.get("fact", str(fact)))
            else:
                facts.append(str(fact)[:500])

    return {
        "headline": item.headline,
        "confirmed_facts": facts[:8],
        "primary_source": item.source_name,
        "source_authority": "primary" if item.source_tier == 1 else "secondary",
        "corroborating_sources": _count_corroborating(dossier),
        "unclear_or_unconfirmed": _identify_gaps(dossier),
    }


def _build_parties(item: CanonicalItem, dossier: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Identify every party and analyze their incentives."""
    parties = []

    def add_party(name: str, role: str, gain: str = "", risk: str = "", timing: str = "", constraint: str = ""):
        if name and name.strip():
            parties.append({
                "name": name.strip(),
                "role": role,
                "what_they_gain": gain or _infer_gain(name, role, item),
                "risk_accepted": risk or _infer_risk(name, role, item),
                "timing_motivation": timing or "Unknown — not disclosed in sources",
                "constraint": constraint or "Unknown — not disclosed in sources",
            })

    for name in (item.buyers if isinstance(item.buyers, list) else []):
        add_party(name, "Buyer")
    for name in (item.sellers if isinstance(item.sellers, list) else []):
        add_party(name, "Seller")
    for name in (item.lenders if isinstance(item.lenders, list) else []):
        add_party(name, "Lender")
    for name in (item.developers if isinstance(item.developers, list) else []):
        add_party(name, "Developer")
    for name in (item.companies if isinstance(item.companies, list) else []):
        if name not in [p["name"] for p in parties]:
            add_party(name, "Company/Investor")

    if not parties:
        parties.append({
            "name": "Unknown",
            "role": "Unknown — sources did not identify specific parties",
            "what_they_gain": "Unknown",
            "risk_accepted": "Unknown",
            "timing_motivation": "Unknown",
            "constraint": "Unknown",
        })

    return parties


def _build_economics(
    item: CanonicalItem, dossier: dict[str, Any] | None, source_texts: list[str] | None
) -> dict[str, Any]:
    """Extract all financial figures. Mark each as REPORTED or CALCULATED."""
    economics = {
        "reported": {},
        "calculated": {},
        "unavailable": [],
    }

    tv = item.transaction_value if isinstance(item.transaction_value, (int, float)) else _safe_float(item.transaction_value)
    debt = item.debt_amount if isinstance(item.debt_amount, (int, float)) else _safe_float(item.debt_amount)
    fund = item.fund_size if isinstance(item.fund_size, (int, float)) else _safe_float(item.fund_size)
    mw = item.megawatts if isinstance(item.megawatts, (int, float)) else _safe_float(item.megawatts)
    uc = item.unit_count if isinstance(item.unit_count, int) else int(_safe_float(item.unit_count))
    sf = item.square_footage if isinstance(item.square_footage, int) else int(_safe_float(item.square_footage))

    if item.transaction_value_raw:
        economics["reported"]["transaction_value"] = {
            "value": item.transaction_value_raw,
            "source": item.source_name,
        }
    if item.debt_amount:
        economics["reported"]["debt_amount"] = {
            "value": f"${debt:,.0f}",
            "source": item.source_name,
        }
    if item.fund_size:
        economics["reported"]["fund_size"] = {
            "value": f"${fund:,.0f}",
            "source": item.source_name,
        }
    if item.megawatts:
        economics["reported"]["megawatts"] = {
            "value": f"{mw:.0f} MW",
            "source": item.source_name,
        }
    if item.unit_count:
        economics["reported"]["unit_count"] = {
            "value": str(uc),
            "source": item.source_name,
        }
    if item.square_footage:
        economics["reported"]["square_footage"] = {
            "value": f"{sf:,} SF",
            "source": item.source_name,
        }

    if item.transaction_value_raw and tv <= 0:
        economics["unavailable"].append("Numeric transaction value not parsed from raw value")
    if tv > 0 and uc > 0:
        per_unit = tv / uc
        economics["calculated"]["price_per_unit"] = {
            "value": f"${per_unit:,.0f}",
            "derived_from": "transaction_value / unit_count",
            "note": "CALCULATED — verify against source",
        }
    if tv > 0 and sf > 0:
        per_sf = tv / sf
        economics["calculated"]["price_per_sf"] = {
            "value": f"${per_sf:,.0f}",
            "derived_from": "transaction_value / square_footage",
            "note": "CALCULATED — verify against source",
        }
    if tv > 0 and mw > 0:
        per_mw = tv / mw
        economics["calculated"]["price_per_mw"] = {
            "value": f"${per_mw:,.0f}",
            "derived_from": "transaction_value / megawatts",
            "note": "CALCULATED — verify against source",
        }

    if not item.transaction_value_raw and not item.fund_size:
        economics["unavailable"].append("Deal value / transaction amount")
    if item.primary_sector == "commercial_real_estate" and not item.unit_count and not item.square_footage:
        economics["unavailable"].append("Property scale (units or square footage)")
    if item.primary_sector == "data_centers" and not item.megawatts:
        economics["unavailable"].append("Power capacity (megawatts)")

    return economics


def _build_market_context(item: CanonicalItem, dossier: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize relevant market conditions."""
    return {
        "sector": item.primary_sector or "unknown",
        "market": item.market or "not specified",
        "city": item.city or "",
        "state": item.state or "",
        "interest_rate_environment": "Current market conditions — see dossier for specifics",
        "credit_conditions": "Current market conditions — see dossier for specifics",
        "comparable_transactions": "See dossier for prior Light Tower coverage and source-provided comparables",
        "regulatory_environment": "See dossier for relevant regulatory context",
    }


def _identify_central_question(item: CanonicalItem) -> str:
    """Determine the ONE question this article must answer."""
    sector = item.primary_sector or ""
    text = f"{item.headline} {item.raw_summary}".lower()

    questions = {
        "commercial_real_estate": [
            "Is the buyer acquiring a durable asset at a temporary discount, or overpaying for scarce supply?",
            "Does the financing structure reveal how difficult conventional debt has become for this asset class?",
            "Is the seller accepting a weak price to solve a liquidity problem, or is this a fair market transaction?",
        ],
        "private_equity": [
            "How does the sponsor expect to create value — multiple expansion, operational improvement, or leverage?",
            "Is this a platform acquisition betting on sector consolidation, or a standalone value play?",
        ],
        "data_centers": [
            "Is the scarce resource constraining this project capital, land, power, or political permission?",
        ],
        "energy": [
            "What conditions must hold for this project to earn its expected return?",
        ],
        "banking_credit": [
            "Where does the risk sit in this transaction, and who is being compensated for bearing it?",
        ],
        "fed_macro": [
            "What actually changed in the policy outlook, and what was already priced in?",
        ],
        "local_government": [
            "Who bears the economic cost of this decision, and who captures the benefit?",
        ],
    }

    sector_questions = questions.get(sector, questions["commercial_real_estate"])
    return sector_questions[0]


def _identify_tension(item: CanonicalItem) -> str:
    """State the central tension in one sentence."""
    text = f"{item.headline} {item.raw_summary}".lower()

    tensions = []
    if any(w in text for w in ["discount", "below", "distressed", "foreclosure"]):
        tensions.append("Price vs. value: the asset sold below perceived intrinsic value")
    if any(w in text for w in ["refinanc", "maturity", "extension", "expiring"]):
        tensions.append("Liquidity vs. duration: time pressure vs. long-term asset value")
    if any(w in text for w in ["leveraged", "leverage", "debt", "financing", "loan"]):
        tensions.append("Growth vs. leverage: expansion funded by debt that must be serviced")
    if any(w in text for w in ["regulation", "zoning", "policy", "compliance"]):
        tensions.append("Policy intent vs. market consequence: regulation designed for one outcome may produce another")
    if any(w in text for w in ["buyer", "seller", "acquired", "sold", "purchased"]):
        tensions.append("Buyer confidence vs. seller necessity: different motivations at the same price point")

    return tensions[0] if tensions else "Risk vs. return: the central tension requires further analysis"


def _build_thesis(item: CanonicalItem) -> str:
    """State the most defensible claim in 1-3 sentences."""
    sector = item.primary_sector or ""
    headline = item.headline or ""
    return f"Analysis thesis pending for: {headline}. " \
           f"The central claim will be developed during the editorial stage using the full source material."


def _build_counterargument(item: CanonicalItem) -> str:
    """What alternative interpretation could be valid?"""
    return "The strongest counterargument will be identified during editorial review. " \
           "Consider: could market conditions alone explain the outcome without the inferred strategic intent?"


def _identify_unknowns(item: CanonicalItem, dossier: dict[str, Any] | None) -> list[str]:
    """List important unavailable facts."""
    unknowns = []
    if not item.transaction_value_raw:
        unknowns.append("Exact transaction value not disclosed")
    if not item.companies and not item.buyers:
        unknowns.append("Specific parties not named in available sources")
    if dossier and isinstance(dossier, dict):
        gaps = dossier.get("reporting_gaps", [])
        unknowns.extend([str(g) for g in gaps[:5]])
    if not unknowns:
        unknowns.append("Key metrics unavailable — limited source material")
    return unknowns


def _build_reader_relevance(item: CanonicalItem) -> str:
    """Why should the target audience care?"""
    sector = item.primary_sector or "general"
    personas = {
        "commercial_real_estate": "CRE investors, lenders, and developers should watch for pricing signals and financing availability",
        "private_equity": "PE professionals should assess the value-creation logic and exit pathway",
        "data_centers": "Data center operators and investors should evaluate power availability and capital requirements",
        "energy": "Energy developers and investors should assess regulatory risk and return expectations",
        "banking_credit": "Lenders and credit investors should evaluate risk transfer and compensation",
        "fed_macro": "All capital allocators should reassess rate expectations and credit conditions",
        "local_government": "Developers and investors should assess how this decision changes project feasibility",
    }
    return personas.get(sector, "Market participants should evaluate the implications for their sector")


def _select_architecture(item: CanonicalItem) -> dict[str, str]:
    """Select the most appropriate article structure."""
    text = f"{item.headline} {item.raw_summary}".lower()
    sector = item.primary_sector or ""

    if sector in ("fed_macro", "local_government"):
        return {"name": "The Policy Consequence", "reason": "Policy/regulatory story"}
    if item.tier == "tier_1_must_cover" and item.composite_score >= 75:
        return {"name": "The Hidden Bet", "reason": "High-significance story with strategic depth"}
    if any(w in text for w in ["price", "sold for", "acquired for", "valued at"]):
        return {"name": "The Price Signal", "reason": "Price-focused story"}
    if len(item.companies) >= 3 or len(item.buyers) + len(item.sellers) >= 2:
        return {"name": "The Incentive Conflict", "reason": "Multiple parties with distinct interests"}
    if item.composite_score < 50:
        return {"name": "The Constraint", "reason": "Smaller story — focus on the limiting factor"}

    return {"name": "The Hidden Bet", "reason": "Default structure for analytical stories"}


def _select_depth(item: CanonicalItem) -> dict[str, Any]:
    """Select appropriate article depth."""
    score = item.composite_score
    if score >= 70:
        return {"depth": "deep", "words": "1400-2500"}
    elif score >= 50:
        return {"depth": "standard", "words": "800-1300"}
    else:
        return {"depth": "brief", "words": "400-700"}


def _extract_key_numbers(item: CanonicalItem) -> list[dict[str, Any]]:
    """Identify 3-5 numbers that will anchor the analysis."""
    numbers = []
    if item.transaction_value_raw:
        numbers.append({"number": item.transaction_value_raw, "meaning": "Transaction value", "interpretation": "Scale of the deal"})
    if item.debt_amount:
        debt = item.debt_amount if isinstance(item.debt_amount, (int, float)) else _safe_float(item.debt_amount)
        numbers.append({"number": f"${debt:,.0f}", "meaning": "Debt financing", "interpretation": "Leverage and lender confidence"})
    if item.megawatts:
        mw = item.megawatts if isinstance(item.megawatts, (int, float)) else _safe_float(item.megawatts)
        numbers.append({"number": f"{mw:.0f} MW", "meaning": "Power capacity", "interpretation": "Scale of infrastructure commitment"})
    if item.unit_count:
        uc = item.unit_count if isinstance(item.unit_count, int) else int(_safe_float(item.unit_count))
        numbers.append({"number": str(uc), "meaning": "Unit count", "interpretation": "Scale relative to market supply"})
    return numbers[:5]


def _count_corroborating(dossier: dict[str, Any] | None) -> int:
    if dossier and isinstance(dossier, dict):
        return dossier.get("independent_source_count", 0)
    return 0


def _identify_gaps(dossier: dict[str, Any] | None) -> list[str]:
    if dossier and isinstance(dossier, dict):
        return [str(g) for g in dossier.get("reporting_gaps", [])[:5]]
    return ["No dossier available — limited source material"]


def _infer_gain(name: str, role: str, item: CanonicalItem) -> str:
    return f"{role} gains: To be determined from source analysis"


def _infer_risk(name: str, role: str, item: CanonicalItem) -> str:
    return f"{role} risk: To be determined from source analysis"


def enhance_brief_with_llm(
    brief: dict[str, Any],
    item: CanonicalItem,
    api_key: str = "",
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Use LLM to improve thesis, counterargument, and central question."""
    if not api_key:
        return brief  # No LLM available, keep deterministic output

    try:
        from editorial_scoring import call_deepseek

        summary_clean = re.sub(r'<[^>]+>', ' ', (item.raw_summary or item.raw_text or '')).strip()
        summary_clean = re.sub(r'\s+', ' ', summary_clean)

        prompt = f"""You are a financial analyst preparing an editorial brief.

STORY: {item.headline}
SECTOR: {item.primary_sector}
SUMMARY: {summary_clean}

PARTIES: {_safe_truncate_json(brief.get('parties_and_incentives', []), max_chars=800)}
ECONOMICS: {_safe_truncate_json(brief.get('transaction_economics', {}), max_chars=800)}

Produce three things:
1. CENTRAL FINANCIAL QUESTION: The ONE question this article can answer from
   the supplied summary and economics. Do not require an IRR, return target,
   debt cost, valuation, or financing term that the source did not disclose.
2. THESIS: A specific, bounded, defensible claim (1-3 sentences).
3. COUNTERARGUMENT: The strongest alternative interpretation.

Do not introduce new numbers, private motives, or undisclosed assumptions.

Return JSON: {{central_question: string, thesis: string, counterargument: string}}
"""
        raw = call_deepseek(
            prompt,
            api_key,
            max_tokens=800,
            temperature=0.3,
            json_mode=True,
            provider=provider,
        )
        data = _extract_json(raw)

        if data.get("central_question"):
            brief["central_financial_question"] = data["central_question"]
        if data.get("thesis"):
            brief["thesis"] = data["thesis"]
        if data.get("counterargument"):
            brief["counterargument"] = data["counterargument"]

    except Exception:
        pass  # Keep deterministic output on failure

    return brief


def _safe_truncate_json(data: Any, max_chars: int) -> str:
    """Dump data as JSON, truncating safely to avoid broken JSON."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    if len(json_str) <= max_chars:
        return json_str

    if isinstance(data, list):
        truncated = []
        for item in data:
            candidate = json.dumps(truncated + [item], indent=2, ensure_ascii=False)
            if len(candidate) > max_chars:
                break
            truncated.append(item)
        if not truncated and data:
            return json.dumps(
                [{"_truncated": f"{len(data)} items, first item too large"}],
                indent=2, ensure_ascii=False,
            )
        return json.dumps(truncated, indent=2, ensure_ascii=False)

    if isinstance(data, dict):
        truncated: dict[str, Any] = {}
        for key, value in data.items():
            candidate = json.dumps(truncated | {key: value}, indent=2, ensure_ascii=False)
            if len(candidate) > max_chars:
                break
            truncated[key] = value
        if not truncated and data:
            return json.dumps(
                {"_truncated": f"{len(data)} keys, first value too large"},
                indent=2, ensure_ascii=False,
            )
        return json.dumps(truncated, indent=2, ensure_ascii=False)

    return json_str[:max_chars]


def _extract_json(raw: str) -> dict[str, Any]:
    """Extract JSON from LLM response. Raises ValueError on failure."""
    match = re.search(r'\{[\s\S]*\}', raw or "")
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from response: {str(raw)[:200]}")
