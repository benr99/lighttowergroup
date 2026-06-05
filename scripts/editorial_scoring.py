"""
Daily Top News editorial scoring for Light Tower Group.

The daily product ranks news items, not abstract market themes. It rewards
recognizable names, large numbers, transactions, distress, policy/rate moves,
banking relevance, and clear capital markets consequences.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any

import requests


MODEL_NAME = "deepseek-chat"

DAILY_SCORE_KEYS = [
    "newsworthiness",
    "capital_markets_significance",
    "specificity",
    "magnitude",
    "brand_recognition",
    "timeliness",
    "linkedin_potential",
]


def _extract_json_array(raw: str) -> list[Any]:
    object_match = re.search(r"\{[\s\S]*\}", raw or "")
    if object_match:
        try:
            data = json.loads(object_match.group())
            if isinstance(data, dict):
                for key in ("scores", "items", "results"):
                    if isinstance(data.get(key), list):
                        return data[key]
        except Exception:
            pass
    match = re.search(r"\[[\s\S]*\]", raw or "")
    if not match:
        raise ValueError("No JSON array found")
    return json.loads(match.group())


def _extract_json_object(raw: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", raw or "")
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group())


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _fallback_score(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    topics = set(candidate.get("topics", []))
    features = candidate.get("attention_features", {})
    source_tier = _coerce_int(candidate.get("source_tier", 3), 3)

    newsworthiness = 8
    if features.get("has_big_number"):
        newsworthiness += 7
    if features.get("has_known_institution"):
        newsworthiness += 6
    if features.get("has_transaction_language"):
        newsworthiness += 5
    if features.get("has_distress_language"):
        newsworthiness += 5

    capital = 8
    if topics & {"capital_placement", "bank_credit", "private_credit", "fed_rates", "cmbs", "distress"}:
        capital += 12
    if topics & {"private_equity", "mna", "major_sale", "reit_public_markets"}:
        capital += 7

    specificity = 5 + (5 if features.get("has_big_number") else 0) + (4 if features.get("has_known_institution") else 0)
    magnitude = 5 + (5 if features.get("has_big_number") else 0)
    brand = 4 + (6 if features.get("has_known_institution") else 0)
    timeliness = 4
    linkedin = 4 + (3 if features.get("has_distress_language") else 0) + (2 if features.get("has_transaction_language") else 0)
    penalty = 0 if source_tier <= 2 else 3

    score = newsworthiness + capital + specificity + magnitude + brand + timeliness + linkedin - penalty
    archetype = next((t for t in candidate.get("topics", []) if t != "general_market"), "other")
    return {
        "index": index,
        "score": max(0, min(score, 100)),
        "newsworthiness": max(0, min(newsworthiness, 30)),
        "capital_markets_significance": max(0, min(capital, 25)),
        "specificity": max(0, min(specificity, 15)),
        "magnitude": max(0, min(magnitude, 10)),
        "brand_recognition": max(0, min(brand, 10)),
        "timeliness": max(0, min(timeliness, 5)),
        "linkedin_potential": max(0, min(linkedin, 5)),
        "penalty": penalty,
        "story_archetype": archetype,
        "why_people_click": "It has recognizable market stakes and enough specificity to stop a CRE finance reader.",
        "capital_implication": "The item may affect pricing, liquidity, lender behavior, or investor conviction.",
        "best_angle": "Explain what changed in the capital stack and who benefits or loses.",
        "reader_personas": ["sponsor", "lender", "private equity", "banker"],
    }


def _score_prompt(candidates: list[dict[str, Any]], today: str) -> str:
    story_list = "\n\n".join(
        f"[{c.get('_score_index', i+1)}] SOURCE: {c['source']} | tier {c.get('source_tier', 3)} | domains {', '.join(c.get('source_domains', []))}\n"
        f"TITLE: {c['title']}\n"
        f"SUMMARY: {c.get('summary', '')[:360]}\n"
        f"TOPICS: {', '.join(c.get('topics', []))}\n"
        f"ENTITIES: {json.dumps(c.get('entities', {}), ensure_ascii=False)[:420]}"
        for i, c in enumerate(candidates)
    )
    return f"""You are the senior editor of Light Tower Group's daily CRE capital markets desk.

Today's date: {today}

Your job is to score news ITEMS, not broad themes. Favor exciting, specific, high-attention
stories a smart LinkedIn audience of CRE sponsors, lenders, bankers, PE investors, private
credit funds, REIT analysts, and brokers would actually stop to read.

Score each item 0-100 using this rubric:

Newsworthiness / Attention: 30
- Big names, big numbers, conflict, surprise, distress, winners/losers, market drama.

Capital Markets Significance: 25
- Effects on capital availability, pricing, refinancing, risk, valuations, lender behavior,
  borrower options, private equity strategy, or debt/equity structure.

Specificity / Evidence: 15
- Named players, property names, dollar amounts, dates, filings, deals, lenders, buyers, sellers.

Magnitude: 10
- Transaction size, fund size, policy scale, affected portfolio, or institution size.

Brand / Institution Recognition: 10
- Blackstone, Brookfield, Apollo, Starwood, SL Green, JPMorgan, Wells Fargo, Fed, FDIC,
  major REITs, major banks, large PE/private credit managers, or other known players.

Timeliness: 5
- Fresh today or materially developing.

LinkedIn Conversation Potential: 5
- Likely to invite comments, debate, reposts, or informed disagreement.

Apply penalties:
- Single-family / consumer homebuying: -30
- Celebrity / lifestyle / design: -40
- Press release with no independent substance: -15
- Generic macro without CRE/banking/finance transmission: -15
- Non-U.S. without U.S. capital implication: -20
- Duplicate/syndicated version of stronger source: -20
- Thin summary and no publishable angle: -15

Return ONLY a valid JSON object with this exact top-level shape:
{{
  "scores": [
  {{
    "index": 1,
    "score": 92,
    "newsworthiness": 28,
    "capital_markets_significance": 23,
    "specificity": 14,
    "magnitude": 9,
    "brand_recognition": 9,
    "timeliness": 5,
    "linkedin_potential": 4,
    "penalty": 0,
    "story_archetype": "major_sale | capital_placement | M&A | Fed/rates | bank_credit | private_credit | distress | CMBS | policy | REIT/public_markets | development_finance | other",
    "why_people_click": "one sentence",
    "capital_implication": "one sentence",
    "best_angle": "one sentence",
    "reader_personas": ["sponsor", "lender"]
  }}
  ]
}}

Stories:
{story_list}"""


def _selection_prompt(scored: list[dict[str, Any]], article_count: int, today: str) -> str:
    story_list = "\n\n".join(
        f"[{item['index']}] SCORE: {item.get('score', 0)} | ARCHETYPE: {item.get('story_archetype', 'other')}\n"
        f"SOURCE: {item['candidate']['source']}\n"
        f"TITLE: {item['candidate']['title']}\n"
        f"WHY CLICK: {item.get('why_people_click', '')}\n"
        f"CAPITAL IMPLICATION: {item.get('capital_implication', '')}\n"
        f"BEST ANGLE: {item.get('best_angle', '')}"
        for item in scored
    )
    return f"""You are selecting the final Light Tower Group daily top news list for {today}.

Choose the best final {article_count} news items for WSJ-style CRE capital markets analysis.

Selection rules:
- Pick specific news items, not abstract themes.
- Favor major sales, capital placements, M&A, Fed/rates, banking news, private credit,
  private equity, distress, REIT/public markets, CMBS, development finance, and policy.
- Prefer stories with names, numbers, conflict, stakes, surprise, or clear market consequence.
- Avoid duplicates or weaker syndicated versions of the same story.
- Preserve variety. Do not select too many generic macro/rate stories unless they are clearly
  among the day's biggest market-moving items.
- Keep the version/source most suitable for a sharp Light Tower analysis.

Return ONLY a JSON object:
{{
  "selected_indices": [3, 8, 14],
  "daily_editorial_theme": "one paragraph",
  "coverage_mix": {{"major_sale": 1, "capital_placement": 2}},
  "near_misses": [
    {{"index": 12, "reason": "good story but less specific than selected items"}}
  ],
  "duplicate_groups": [
    {{"kept_index": 4, "dropped_indices": [7, 11], "reason": "same transaction, stronger source kept"}}
  ]
}}

Scored candidates:
{story_list}"""


def call_deepseek(
    prompt: str,
    api_key: str,
    *,
    max_tokens: int = 5000,
    temperature: float = 0.2,
    json_mode: bool = False,
) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _normalize_score_row(row: dict[str, Any], candidate: dict[str, Any], index: int) -> dict[str, Any]:
    result = _fallback_score(candidate, index)
    for key in list(result.keys()):
        if key in row:
            result[key] = row[key]
    for key in DAILY_SCORE_KEYS + ["score", "penalty"]:
        result[key] = _coerce_int(result.get(key), 0)
    result["score"] = max(0, min(result["score"], 100))
    result["index"] = index
    result["candidate"] = candidate
    return result


def score_daily_candidates(candidates: list[dict[str, Any]], api_key: str, today: str) -> list[dict[str, Any]]:
    candidates = candidates[:120]
    fallback = [_normalize_score_row({}, candidate, i + 1) for i, candidate in enumerate(candidates)]
    if not api_key:
        return sorted(fallback, key=lambda row: row["score"], reverse=True)

    scored_by_index: dict[int, dict[str, Any]] = {}
    batch_size = 15
    for start in range(0, len(candidates), batch_size):
        batch = []
        for offset, candidate in enumerate(candidates[start:start + batch_size], start=start + 1):
            item = dict(candidate)
            item["_score_index"] = offset
            batch.append(item)
        try:
            raw = call_deepseek(
                _score_prompt(batch, today),
                api_key,
                max_tokens=3500,
                temperature=0.12,
                json_mode=True,
            )
            rows = _extract_json_array(raw)
            for row in rows:
                if isinstance(row, dict):
                    idx = _coerce_int(row.get("index"), 0)
                    if idx:
                        scored_by_index[idx] = row
        except Exception as exc:
            print(f"  [WARN] Daily top-news scoring batch {start + 1}-{start + len(batch)} failed ({exc}); using fallback for that batch")

    scored = [
        _normalize_score_row(scored_by_index.get(i + 1, {}), candidate, i + 1)
        for i, candidate in enumerate(candidates)
    ]
    return sorted(scored, key=lambda row: row["score"], reverse=True)


def select_final_daily_stories(
    scored: list[dict[str, Any]],
    article_count: int,
    api_key: str,
    today: str,
) -> dict[str, Any]:
    top = scored[:25]
    fallback_indices = [item["index"] for item in top[:article_count]]
    fallback = {
        "selected_indices": fallback_indices,
        "daily_editorial_theme": "The day's strongest CRE capital markets items were selected for specificity, capital consequence, and reader attention.",
        "coverage_mix": {},
        "near_misses": [],
        "duplicate_groups": [],
    }
    if not api_key or not top:
        return fallback

    try:
        raw = call_deepseek(
            _selection_prompt(top, article_count, today),
            api_key,
            max_tokens=3500,
            temperature=0.12,
            json_mode=True,
        )
        data = _extract_json_object(raw)
        selected = [
            _coerce_int(idx, 0)
            for idx in data.get("selected_indices", [])
            if _coerce_int(idx, 0)
        ]
        if not selected:
            selected = fallback_indices
        data["selected_indices"] = selected[:article_count]
        data.setdefault("daily_editorial_theme", fallback["daily_editorial_theme"])
        data.setdefault("coverage_mix", {})
        data.setdefault("near_misses", [])
        data.setdefault("duplicate_groups", [])
        return data
    except Exception as exc:
        print(f"  [WARN] Final daily selection failed ({exc}); using top scored items")
        return fallback


def daily_top_news_selection(
    candidates: list[dict[str, Any]],
    *,
    article_count: int,
    api_key: str,
    today: str | None = None,
) -> dict[str, Any]:
    today = today or date.today().isoformat()
    scored = score_daily_candidates(candidates, api_key, today)
    selection = select_final_daily_stories(scored, article_count, api_key, today)
    scored_by_index = {item["index"]: item for item in scored}
    selected_items = [
        scored_by_index[idx]
        for idx in selection.get("selected_indices", [])
        if idx in scored_by_index
    ]
    if len(selected_items) < article_count:
        existing = {item["index"] for item in selected_items}
        selected_items.extend([item for item in scored if item["index"] not in existing][: article_count - len(selected_items)])

    return {
        "selection_mode": "daily-top-news",
        "model": MODEL_NAME if api_key else "deterministic-fallback",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "today": today,
        "candidate_count": len(candidates),
        "scored_candidates": scored,
        "selected_stories": selected_items[:article_count],
        "daily_editorial_theme": selection.get("daily_editorial_theme", ""),
        "coverage_mix": selection.get("coverage_mix", {}),
        "near_misses": selection.get("near_misses", []),
        "duplicate_groups": selection.get("duplicate_groups", []),
    }


def print_daily_selection_report(selection: dict[str, Any], *, limit: int = 10) -> None:
    print("\nTop Daily News Items:")
    for rank, item in enumerate(selection.get("selected_stories", [])[:limit], 1):
        candidate = item["candidate"]
        print(f"  {rank}. [{item.get('score', 0)}/100] {candidate['source']}: {candidate['title'][:95]}")
        print(f"     Archetype: {item.get('story_archetype', 'other')}")
        print(f"     Why people click: {item.get('why_people_click', '')}")
        print(f"     Capital implication: {item.get('capital_implication', '')}")
        print(f"     Best angle: {item.get('best_angle', '')}")
    if selection.get("near_misses"):
        print("\nNear Misses:")
        for miss in selection["near_misses"][:5]:
            print(f"  [{miss.get('index')}] {miss.get('reason', '')}")
    if selection.get("daily_editorial_theme"):
        print(f"\nDaily Editorial Theme:\n  {selection['daily_editorial_theme']}")
    if selection.get("coverage_mix"):
        print(f"\nCoverage Mix: {json.dumps(selection['coverage_mix'], ensure_ascii=False)}")


def _weekly_prompt(runs: list[dict[str, Any]], today: str) -> str:
    items = []
    for run in runs:
        run_date = run.get("date") or run.get("today") or run.get("generated_at", "")[:10]
        for story in run.get("selected_stories", []):
            candidate = story.get("candidate", story)
            items.append({
                "date": run_date,
                "title": candidate.get("title"),
                "source": candidate.get("source"),
                "score": story.get("score"),
                "archetype": story.get("story_archetype"),
                "capital_implication": story.get("capital_implication"),
                "best_angle": story.get("best_angle"),
            })
    return f"""You are writing the internal Friday State of the Markets Review for Light Tower Group.

Today's date: {today}

Use the week's selected daily news items to synthesize what changed in CRE capital markets.
Do not merely recap headlines. Identify the week's dominant market signals, winners,
losers, capital flows, lender behavior, borrower implications, private equity/private
credit behavior, and banking/rate signals.

Return ONLY a JSON object:
{{
  "title": "...",
  "subtitle": "...",
  "week_of": "...",
  "dominant_themes": [
    {{"theme": "...", "evidence": ["story title"], "market_implication": "..."}}
  ],
  "winners": [],
  "losers": [],
  "capital_flows": [],
  "banking_signal": "...",
  "private_equity_signal": "...",
  "borrower_signal": "...",
  "lender_signal": "...",
  "friday_article_outline": [],
  "linkedin_post": "..."
}}

Weekly selected news items:
{json.dumps(items, indent=2, ensure_ascii=False)}"""


def generate_weekly_market_review(runs: list[dict[str, Any]], *, api_key: str, today: str | None = None) -> dict[str, Any]:
    today = today or date.today().isoformat()
    fallback = {
        "title": "The Week in CRE Capital Markets",
        "subtitle": "A synthesis of the week's selected CRE finance, banking, private credit, and transaction news.",
        "week_of": today,
        "dominant_themes": [],
        "winners": [],
        "losers": [],
        "capital_flows": [],
        "banking_signal": "",
        "private_equity_signal": "",
        "borrower_signal": "",
        "lender_signal": "",
        "friday_article_outline": [],
        "linkedin_post": "",
        "source_run_count": len(runs),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model": "deterministic-fallback",
    }
    if not runs or not api_key:
        return fallback
    try:
        raw = call_deepseek(
            _weekly_prompt(runs, today),
            api_key,
            max_tokens=5000,
            temperature=0.2,
            json_mode=True,
        )
        review = _extract_json_object(raw)
        review["source_run_count"] = len(runs)
        review["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        review["model"] = MODEL_NAME
        return review
    except Exception as exc:
        print(f"  [WARN] Weekly review generation failed ({exc}); using fallback package")
        return fallback


def print_weekly_review_report(review: dict[str, Any]) -> None:
    print(f"\nFriday Review: {review.get('title', 'Untitled')}")
    if review.get("subtitle"):
        print(f"  {review['subtitle']}")
    for i, theme in enumerate(review.get("dominant_themes", [])[:6], 1):
        print(f"\n  {i}. {theme.get('theme', '')}")
        print(f"     Implication: {theme.get('market_implication', '')}")
    for key in ("banking_signal", "private_equity_signal", "borrower_signal", "lender_signal"):
        if review.get(key):
            print(f"\n{key.replace('_', ' ').title()}: {review[key]}")
