#!/usr/bin/env python3
"""Friday weekly wrap: every major story of the week, by sector, with a short take.

The daily pipeline publishes a few dozen items a day. This job runs once a week
(Friday afternoon, New York time), reads what was *actually published* during the
Saturday-to-Friday window from ``insights.json``, groups it into sectors
(Fed & rates, debt, multifamily, industrial/warehouse, office, ...), and writes
one page: a plain-English summary and a one-line take for each major item.

Design choices worth knowing about:

* The factual boundary is the already-published article (title, excerpt, and the
  opening paragraphs of its page), not the open web. The wrap re-reports nothing.
* Every number the model writes must appear in the text it was shown; otherwise
  that item is retried once and then falls back to the plain excerpt.
* Publishing reuses the daily renderer, manifest, feed and sitemap writers, so the
  wrap shows up on the Intelligence page like any other piece (format ``weekly``).
* Idempotent: one wrap per week-ending Friday; a second run is a no-op unless
  ``--force`` is passed.

Usage:
    python weekly_wrap.py                       # preview latest Friday, no site writes
    python weekly_wrap.py --mode publish        # write page, manifest, feed, sitemap
    python weekly_wrap.py --week-ending 2026-10-02 --mode preview
    python weekly_wrap.py --no-llm              # deterministic fallback, no provider
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

INSIGHTS_DIR = SITE_ROOT / "insights"
MANIFEST_PATH = SITE_ROOT / "insights.json"
STATE_DIR = SITE_ROOT / ".editorial-state"
WRAP_STATE_DIR = STATE_DIR / "weekly-wraps"
SITE_URL = "https://lighttowergroup.co"
NEW_YORK = ZoneInfo("America/New_York")

WRAP_CATEGORY = "Weekly Wrap"
WRAP_FORMAT = "weekly"
PIPELINE_VERSION = "weekly-wrap-v1"

# (key, reader-facing label). Order is page order: macro first, then capital, then assets.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("fed_rates", "Fed, Rates & Macro"),
    ("debt_capital", "Debt & Capital Markets"),
    ("multifamily", "Multifamily"),
    ("industrial", "Industrial & Warehouse"),
    ("office", "Office"),
    ("retail", "Retail"),
    ("hospitality", "Hospitality"),
    ("data_centers", "Data Centers"),
    ("energy", "Energy & Infrastructure"),
    ("private_equity", "Private Equity & Private Credit"),
    ("policy", "Policy & Local Government"),
    ("other_cre", "Other Commercial Real Estate"),
)
SECTION_LABELS = dict(SECTIONS)

_FED_TAGS = {"fed_macro", "fed_speeches", "inflation", "inflation_report", "treasury_yield_move"}
_DC_TAGS = {"data_centers", "hyperscale", "ai_infrastructure", "dc_acquisition", "dc_development",
            "dc_lease", "dc_financing", "powered_land", "colocation"}
_ENERGY_TAGS = {"energy", "nuclear", "solar", "wind", "battery_storage", "natural_gas",
                "power_agreement", "energy_m_and_a", "power_generation", "electric_utilities"}
_PE_TAGS = {"private_equity", "fundraising", "buyout", "exit_ipo", "private_credit",
            "direct_lending", "fund_close", "continuation_fund"}
_POLICY_TAGS = {"local_government", "city_council", "eminent_domain", "nyc policy", "zoning",
                "rezoning", "tax_incentive"}
_DEBT_TAGS = {"banking_credit", "cmbs", "construction_financing", "refinancing", "fdic_action",
              "capital_rule_change", "loan_origination", "construction lending", "office refinancing"}
_ASSET_TAGS = {
    "multifamily": {"multifamily", "affordable housing", "affordable_housing", "student_housing",
                    "senior_housing", "single_family_rental", "manufactured_housing"},
    "industrial": {"industrial_logistics", "industrial", "warehouse", "self_storage"},
    "office": {"office", "life_sciences", "medical_office"},
    "retail": {"retail"},
    "hospitality": {"hospitality", "hotel"},
}
_ASSET_KEYWORDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("multifamily", re.compile(r"\b(multifamily|multi-family|apartment|rental housing|residential tower|affordable housing|student housing|condo)", re.I)),
    ("industrial", re.compile(r"\b(warehouse|industrial|logistics|distribution (?:center|hub)|cold storage|fulfillment|self[- ]storage)", re.I)),
    ("office", re.compile(r"\b(office|co-?working|return[- ]to[- ]office)\b", re.I)),
    ("retail", re.compile(r"\b(retail|shopping|mall|grocery|storefront)\b", re.I)),
    ("hospitality", re.compile(r"\b(hotel|hospitality|resort|lodging)\b", re.I)),
)
_DEBT_KEYWORDS = re.compile(
    r"\b(cmbs|clo\b|loan|lender|lending|refinanc|mortgage|bridge financing|debt|credit|bank|financing|rmbs|bond)", re.I)

# What the writer must never produce, plus the fields the validator enforces.
MAX_SUMMARY_WORDS = 45
MAX_TAKE_WORDS = 38
MAX_READ_WORDS = 40


# --------------------------------------------------------------------------------------
# Selecting the week's items
# --------------------------------------------------------------------------------------

def latest_friday(today: date) -> date:
    """The Friday on or before ``today`` (the week-ending date)."""
    return today - timedelta(days=(today.weekday() - 4) % 7)


def week_window(friday: date) -> tuple[date, date]:
    """Saturday through Friday inclusive."""
    return friday - timedelta(days=6), friday


def week_label(start: date, end: date) -> str:
    return f"{start:%b} {start.day} to {end:%b} {end.day}"


def _parse_iso_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def load_week_items(manifest: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    """Published items dated within the window, excluding earlier wraps."""
    items: list[dict[str, Any]] = []
    for record in manifest:
        if not isinstance(record, dict) or not record.get("slug") or not record.get("title"):
            continue
        if record.get("format") == WRAP_FORMAT or record.get("category") == WRAP_CATEGORY:
            continue
        published = _parse_iso_date(record.get("date"))
        if published is None or not (start <= published <= end):
            continue
        items.append(record)
    return items


def classify(record: dict[str, Any]) -> str:
    """Map one published item to a wrap section using its tags, then its words."""
    tags = {str(t).strip().lower() for t in (record.get("tags") or [])}
    category = str(record.get("category") or "").strip().lower()
    text = f"{record.get('title', '')} {record.get('excerpt', '')}"

    if tags & _FED_TAGS:
        return "fed_rates"
    if tags & _DC_TAGS or category == "data centers":
        return "data_centers"
    if tags & _ENERGY_TAGS:
        return "energy"
    if tags & _PE_TAGS or category == "private equity":
        return "private_equity"
    if "banking_credit" in tags:
        return "debt_capital"
    for section, names in _ASSET_TAGS.items():
        if tags & names:
            return section
    if tags & _POLICY_TAGS:
        return "policy"
    if tags & _DEBT_TAGS:
        return "debt_capital"
    # No decisive tag (older items, free-form tags): fall back to the words.
    for section, pattern in _ASSET_KEYWORDS:
        if pattern.search(text):
            return section
    if _DEBT_KEYWORDS.search(text):
        return "debt_capital"
    if category == "policy & regulation":
        return "policy"
    return "other_cre"


_CRE_RELEVANCE = re.compile(
    r"\b(real estate|propert(?:y|ies)|mortgages?|cmbs|multifamily|apartments?|office|retail|industrial|"
    r"warehouses?|hotels?|housing|developers?|landlords?|reits?|construction|lenders?|lending|refinanc\w*|"
    r"cap rate|rents?|leases?|data centers?|rate cuts?|interest rates?|treasury yields?|inflation|"
    r"bridge loans?|rmbs|clo)\b",
    re.I,
)


def _importance(record: dict[str, Any]) -> float:
    score = float(record.get("mustReadScore") or 0)
    # The daily slate carries adjacent finance news (payments, fintech charters). The wrap is
    # for CRE capital readers, so stories that speak to their world rank first.
    if _CRE_RELEVANCE.search(f"{record.get('title', '')} {record.get('excerpt', '')}"):
        score += 12
    if record.get("format") in {"flagship", "analysis"}:
        score += 6
    score += 2 * min(int(record.get("sourceCount") or 0), 3)
    return score


def _title_tokens(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2 or w.isdigit()}


def select_for_wrap(
    items: list[dict[str, Any]], *, max_per_section: int = 6,
) -> dict[str, list[dict[str, Any]]]:
    """Rank, de-duplicate near-identical stories, and cap each section."""
    ranked = sorted(items, key=lambda r: (-_importance(r), str(r.get("title"))))
    kept: list[dict[str, Any]] = []
    seen_events: set[str] = set()
    seen_tokens: list[set[str]] = []
    for record in ranked:
        event_id = str(record.get("eventId") or "")
        tokens = _title_tokens(str(record.get("title")))
        if event_id and event_id in seen_events:
            continue
        if tokens and any(
            len(tokens & prior) / max(1, len(tokens | prior)) >= 0.7 for prior in seen_tokens
        ):
            continue
        if event_id:
            seen_events.add(event_id)
        seen_tokens.append(tokens)
        kept.append(record)

    by_section: dict[str, list[dict[str, Any]]] = {}
    for record in kept:
        section = classify(record)
        bucket = by_section.setdefault(section, [])
        if len(bucket) < max_per_section:
            bucket.append(record)
    return {key: by_section[key] for key, _ in SECTIONS if key in by_section}


_BODY_RE = re.compile(r'itemprop="articleBody">(.*?)</div>\s*<div class="article-tags"', re.S)
_P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)


def read_lead(slug: str, *, max_chars: int = 900, insights_dir: Path = INSIGHTS_DIR) -> str:
    """The opening paragraphs of a published page: the vetted facts the wrap may use."""
    safe = re.sub(r"[^a-z0-9-]", "", slug.lower())
    try:
        page = (insights_dir / f"{safe}.html").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = _BODY_RE.search(page)
    if not match:
        return ""
    paragraphs = []
    for raw in _P_RE.findall(match.group(1)):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
        if len(text) >= 40:
            paragraphs.append(text)
    lead = " ".join(paragraphs[:3])
    return lead[:max_chars].rsplit(" ", 1)[0] if len(lead) > max_chars else lead


# --------------------------------------------------------------------------------------
# Writing: prompts, provider call, validation
# --------------------------------------------------------------------------------------

WRAP_SYSTEM = """\
You write the Friday wrap for Light Tower Insights, a commercial real estate capital \
markets publication. Readers are sponsors, lenders, brokers and investors who know the \
business but are skimming on a phone. Write the way a sharp colleague would explain the \
week over coffee: plain words, short sentences, a clear point of view.

Style rules:
- Say what happened first, with the who and the how much. Then say why it matters.
- Short sentences. One idea each. Prefer concrete verbs and nouns to abstractions.
- If you use insider shorthand (R&W, tranche, QM, DSCR on an unusual loan), explain it in a few words.
- Turn every important number into a consequence: what it means for a borrower, lender or buyer.
- The take is only what the source itself says matters or comes next: the consequence, risk or next \
step the article states, restated plainly. If the source states none, the take is an empty string. \
Never add your own view, prediction, advice or comparison.
- Vary how sentences open. Do not start every take with "This".
- No hype, no emojis, no hashtags, no rhetorical questions, no "remains to be seen", \
no "it's worth noting", no "landscape", no "navigating", no "highlights", no "underscores".
- Never claim you visited, called, toured or saw anything. No private knowledge.

Facts rule (hard): use only facts, names and numbers that appear in the supplied item text. \
Do not add any number, percentage, date, name, quote or forecast that is not in that text. \
If an item is thin, write a short honest summary and leave the take empty.
Return JSON only, no markdown fences."""


def _section_prompt(label: str, window: str, items: list[dict[str, Any]], feedback: str = "") -> str:
    payload = [
        {
            "id": item["_id"],
            "headline": item["title"],
            "published": str(item.get("date")),
            "source": item.get("sourceName") or "",
            "text": item["_context"],
        }
        for item in items
    ]
    ask = f"""Section: {label}
Week: {window}

ITEMS (the complete factual boundary):
{json.dumps(payload, ensure_ascii=False, indent=1)}

For each item write:
- "summary": 1-2 short sentences, at most {MAX_SUMMARY_WORDS - 10} words. What happened, who, how much.
- "take": one sentence, at most {MAX_TAKE_WORDS - 10} words: the consequence or next step the article itself states. Empty string if it states none.
Also write "read": one sentence, at most {MAX_READ_WORDS - 10} words, on what stood out in {label} this week. \
Only connect items if they truly connect; if they do not, say what the single most important one means.

Return exactly:
{{"read": "...", "items": [{{"id": "...", "summary": "...", "take": "..."}}]}}
Include every id once, in the same order."""
    if feedback:
        ask += "\n\nYour previous answer had problems. Fix every one and return the full JSON again:\n" + feedback
    return ask


OVERVIEW_SYSTEM = WRAP_SYSTEM + "\nYou are now writing the opening of the wrap, from the section notes only."


def _overview_prompt(window: str, count: int, sections: list[dict[str, Any]]) -> str:
    notes = [
        {"section": s["label"], "stories": s["n"], "read": s.get("read") or "", "top": s["top_titles"]}
        for s in sections
    ]
    return f"""Week: {window}. {count} stories were published across {len(sections)} sectors.

SECTION NOTES (the complete factual boundary):
{json.dumps(notes, ensure_ascii=False, indent=1)}

Write the opening of the Friday wrap:
- "headline": at most 9 words, specific, no colon, no quotes. The week's main thread.
- "lede": 2 short sentences, at most 45 words. What kind of week it was.
- "themes": exactly 3 items, each one sentence of at most 25 words. The three things a busy reader should remember.

Return exactly: {{"headline": "...", "lede": "...", "themes": ["...", "...", "..."]}}"""


LLM = Callable[[str, str], str]  # (system, user) -> raw completion text


def make_llm(provider_chain: list[dict[str, Any]], *, timeout_s: float = 120.0) -> LLM:
    """A single-callable LLM that walks the provider chain until one answers."""
    import requests

    from model_router import log_provider_event

    def call(system: str, user: str) -> str:
        last: Exception | None = None
        for provider in provider_chain:
            name = str(provider.get("provider") or "unknown")
            model = str(provider.get("model") or "")
            started = time.monotonic()
            payload: dict[str, Any] = {
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": 3200,
                "temperature": 0.4,
                "response_format": {"type": "json_object"},
            }
            if name == "deepseek":
                payload["thinking"] = {"type": "disabled"}
            try:
                response = requests.post(
                    str(provider.get("url")),
                    headers={"Authorization": f"Bearer {provider.get('api_key')}",
                             "Content-Type": "application/json"},
                    json=payload, timeout=timeout_s,
                )
                response.raise_for_status()
                choice = (response.json().get("choices") or [{}])[0]
                content = str((choice.get("message") or {}).get("content") or "").strip()
                if str(choice.get("finish_reason") or "") == "length":
                    raise ValueError("provider_truncated")
                if not content:
                    raise ValueError("empty_completion")
                log_provider_event("weekly_wrap_call", outcome="success", provider=name, model=model,
                                   attempt_seconds=round(time.monotonic() - started, 2))
                return content
            except Exception as exc:  # noqa: BLE001
                last = exc
                log_provider_event("weekly_wrap_call", outcome="failed", provider=name, model=model,
                                   attempt_seconds=round(time.monotonic() - started, 2),
                                   error=f"{type(exc).__name__}: {exc}"[:240])
        raise RuntimeError(f"all providers failed: {last}")

    return call


def parse_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("response is not a JSON object")
    return value


from readability import BANNED_PHRASES as _WRAP_BANNED  # noqa: E402
from readability import numbers_in, unsupported_numbers  # noqa: E402,F401


def _words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text or ""))


def _style_issues(text: str) -> list[str]:
    """Phrases that make the wrap read like a press release, whatever the voice module's version."""
    from editorial_voice import editorial_quality_issues

    skip = {"repetitive paragraph openings", "overuses contrast construction"}
    issues = [i for i in editorial_quality_issues(text, min_characters=1) if i not in skip]
    found = sorted({m.group(0).lower() for m in _WRAP_BANNED.finditer(text)})
    issues += [f"the phrase '{phrase}'" for phrase in found]
    return list(dict.fromkeys(issues))


def check_text(text: str, source: str, *, max_words: int, field_name: str) -> list[str]:
    problems: list[str] = []
    value = str(text or "").strip()
    if not value:
        return [f"{field_name} is empty"]
    if _words(value) > max_words:
        problems.append(f"{field_name} is {_words(value)} words; the limit is {max_words}")
    bad = unsupported_numbers(value, source)
    if bad:
        problems.append(f"{field_name} uses numbers not in the item text: {', '.join(bad)}")
    problems += [f"{field_name}: avoid {issue}" for issue in _style_issues(value)]
    if "?" in value:
        problems.append(f"{field_name} contains a question; write a statement")
    return problems


def first_sentences(text: str, max_chars: int = 220) -> str:
    """Whole sentences up to ``max_chars``; never a mid-sentence cut."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'$])", clean)
    out = ""
    for sentence in sentences:
        if out and len(out) + 1 + len(sentence) > max_chars:
            break
        out = f"{out} {sentence}".strip()
        if len(out) >= max_chars * 0.6:
            break
    if len(out) > max_chars or not out:
        out = clean[:max_chars].rsplit(" ", 1)[0]
    if out and out[-1] not in ".!?\"'”’)":
        # The source text was cut mid-sentence: back up to the last full sentence if
        # there is a reasonable one, otherwise end on a visible ellipsis.
        cut = max(out.rfind(". "), out.rfind("! "), out.rfind("? "))
        out = out[: cut + 1] if cut >= 60 else re.sub(r"\s+\w{1,2}$", "", out).rstrip(",;:- ") + "…"
    return out


@dataclass
class SectionResult:
    key: str
    label: str
    items: list[dict[str, Any]]
    read: str = ""
    notes: dict[str, dict[str, str]] = field(default_factory=dict)  # id -> {summary, take}
    fallback_ids: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    attempts: int = 0
    error: str = ""


def _verify_section(result: SectionResult, items: list[dict[str, Any]], verifier: LLM) -> None:
    """Fact-check every summary and take against the item's own text; drop what fails.

    A summary that fails reverts to the plain excerpt and loses its take. A take that fails is
    omitted. A verifier that cannot answer is treated as a failure for that item (fail closed).
    """
    from claim_verifier import ACTION, FACT, VIEW, Item, verify_unquoted

    for item in items:
        note = result.notes.get(item["_id"])
        if not note or item["_id"] in result.fallback_ids:
            continue
        source = f"{item['title']}\n{item['_context']}"
        checks = [Item(id="a", kind=FACT, text=note["summary"])]
        if note.get("take"):
            checks.append(Item(id="b", kind=FACT, text=note["take"]))
        try:
            verify_unquoted(checks, source, note["summary"], verifier)
        except Exception as exc:  # noqa: BLE001
            result.problems.append(f"{item['_id']}: fact-check unavailable ({type(exc).__name__})")
            result.fallback_ids.append(item["_id"])
            result.notes[item["_id"]] = {"summary": first_sentences(item.get("excerpt") or item["_context"]), "take": ""}
            continue
        summary_ok, take_ok = checks[0].ok, len(checks) < 2 or checks[1].ok
        if not summary_ok:
            result.problems.append(f"{item['_id']}: summary rejected: {checks[0].reason}")
            result.fallback_ids.append(item["_id"])
            result.notes[item["_id"]] = {"summary": first_sentences(item.get("excerpt") or item["_context"]), "take": ""}
        elif not take_ok:
            result.problems.append(f"{item['_id']}: take rejected: {checks[1].reason}")
            note["take"] = ""
    # The sector line characterises the surviving summaries.
    if result.read:
        summaries = " ".join(n["summary"] for n in result.notes.values())
        line = Item(id="r", kind="summary", text=result.read)
        try:
            verify_unquoted([line], summaries, summaries, verifier)
        except Exception:  # noqa: BLE001
            result.read = ""
        else:
            if not line.ok:
                result.problems.append(f"sector line rejected: {line.reason}")
                result.read = ""


def write_section(
    key: str, items: list[dict[str, Any]], window: str, llm: LLM | None, *, max_attempts: int = 2,
    verifier: LLM | None = None,
) -> SectionResult:
    label = SECTION_LABELS[key]
    result = SectionResult(key=key, label=label, items=items)
    pending = list(items)
    feedback = ""
    read_text = ""

    while llm is not None and pending and result.attempts < max_attempts:
        result.attempts += 1
        try:
            data = parse_json(llm(WRAP_SYSTEM, _section_prompt(label, window, pending, feedback)))
        except Exception as exc:  # noqa: BLE001
            result.error = f"{type(exc).__name__}: {exc}"[:200]
            feedback = f"- The response was not valid JSON ({result.error}). Return only the JSON object."
            continue

        returned = {
            str(entry.get("id")): entry for entry in (data.get("items") or []) if isinstance(entry, dict)
        }
        if not read_text:
            candidate = str(data.get("read") or "").strip()
            source_all = " ".join(i["_context"] + " " + i["title"] for i in items)
            if candidate and not check_text(candidate, source_all, max_words=MAX_READ_WORDS, field_name="read"):
                read_text = candidate

        still_pending: list[dict[str, Any]] = []
        notes_feedback: list[str] = []
        for item in pending:
            entry = returned.get(item["_id"])
            source = f"{item['title']} {item['_context']}"
            if not entry:
                still_pending.append(item)
                notes_feedback.append(f"- id {item['_id']}: missing from the response")
                continue
            summary = str(entry.get("summary") or "").strip()
            take = str(entry.get("take") or "").strip()
            problems = (check_text(summary, source, max_words=MAX_SUMMARY_WORDS, field_name="summary")
                        + (check_text(take, source, max_words=MAX_TAKE_WORDS, field_name="take") if take else []))
            if problems:
                still_pending.append(item)
                notes_feedback.extend(f"- id {item['_id']}: {p}" for p in problems)
            else:
                result.notes[item["_id"]] = {"summary": summary, "take": take}
        pending = still_pending
        feedback = "\n".join(notes_feedback)
        result.problems = notes_feedback

    result.read = read_text
    for item in pending:
        result.fallback_ids.append(item["_id"])
        result.notes[item["_id"]] = {
            "summary": first_sentences(item.get("excerpt") or item["_context"]),
            "take": "",
        }
    if not pending:
        result.problems = []
    if verifier is not None and llm is not None:
        _verify_section(result, items, verifier)
    # Preserve the editorial order of the section.
    result.notes = {i["_id"]: result.notes[i["_id"]] for i in items if i["_id"] in result.notes}
    return result


def write_overview(
    sections: list[SectionResult], window: str, total: int, llm: LLM | None, verifier: LLM | None = None,
) -> dict[str, Any]:
    notes = [
        {"label": s.label, "n": len(s.items), "read": s.read, "top_titles": [i["title"] for i in s.items[:2]]}
        for s in sections
    ]
    fallback = {
        "headline": "",
        "lede": f"{total} stories across {len(sections)} sectors this week. Here is what mattered, sector by sector.",
        "themes": [],
    }
    if llm is None:
        return fallback
    source = json.dumps(notes, ensure_ascii=False)
    feedback = ""
    for _ in range(2):
        prompt = _overview_prompt(window, total, notes)
        if feedback:
            prompt += "\n\nFix these problems and return the full JSON again:\n" + feedback
        try:
            data = parse_json(llm(OVERVIEW_SYSTEM, prompt))
        except Exception as exc:  # noqa: BLE001
            feedback = f"- The response was not valid JSON ({type(exc).__name__}). Return only the JSON object."
            continue
        headline = re.sub(r"[\"“”&<>]", "", str(data.get("headline") or "")).replace("'", "’").strip().rstrip(".")
        lede = str(data.get("lede") or "").strip()
        themes = [str(t).strip() for t in (data.get("themes") or []) if str(t).strip()][:3]
        problems = []
        if not headline or _words(headline) > 12:
            problems.append("headline must be 1-12 words")
        problems += check_text(lede, source, max_words=55, field_name="lede")
        if len(themes) != 3:
            problems.append("themes must contain exactly 3 items")
        for index, theme in enumerate(themes, 1):
            problems += check_text(theme, source, max_words=32, field_name=f"theme {index}")
        if not problems:
            written = {"headline": headline, "lede": lede, "themes": themes}
            return written if verifier is None else _verify_overview(written, sections, verifier, fallback)
        feedback = "\n".join(f"- {p}" for p in problems)
    return fallback


def _verify_overview(
    written: dict[str, Any], sections: list[SectionResult], verifier: LLM, fallback: dict[str, Any],
) -> dict[str, Any]:
    """The opening lines may only characterise summaries that already passed the fact-check."""
    from claim_verifier import Item, verify_unquoted

    summaries = " ".join(n["summary"] for s in sections for n in s.notes.values())
    items = [Item(id="h", kind="summary", text=written["headline"]), Item(id="l", kind="summary", text=written["lede"])]
    items += [Item(id=f"t{i}", kind="summary", text=t) for i, t in enumerate(written["themes"], 1)]
    try:
        verify_unquoted(items, summaries, summaries, verifier)
    except Exception:  # noqa: BLE001
        return fallback
    ok = {i.id: i.ok for i in items}
    return {
        "headline": written["headline"] if ok["h"] else "",
        "lede": written["lede"] if ok["l"] else fallback["lede"],
        "themes": [t for n, t in enumerate(written["themes"], 1) if ok[f"t{n}"]],
    }


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------

def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=False)


def render_body(overview: dict[str, Any], sections: list[SectionResult]) -> str:
    parts = [f"<p>{_esc(overview['lede'])}</p>"]
    if overview.get("themes"):
        parts.append("<h2>If you read nothing else</h2>")
        parts.append("<ul>" + "".join(f"<li>{_esc(t)}</li>" for t in overview["themes"]) + "</ul>")
    for section in sections:
        parts.append(f"<h2>{_esc(section.label)}</h2>")
        if section.read:
            parts.append(f"<p><em>{_esc(section.read)}</em></p>")
        bullets = []
        for item in section.items:
            note = section.notes.get(item["_id"], {})
            link = f'<a href="{_esc(item.get("url") or "/insights/" + item["slug"] + ".html")}">{_esc(item["title"])}</a>'
            line = f"<strong>{link}</strong> {_esc(note.get('summary'))}"
            if note.get("take"):
                line += f" <em>Why it matters: {_esc(note['take'])}</em>"
            if item.get("sourceName"):
                line += f" ({_esc(item['sourceName'])})"
            bullets.append(f"<li>{line}</li>")
        parts.append("<ul>" + "".join(bullets) + "</ul>")
    parts.append("<p>Each item links to the full piece. The wrap summarises what we published this week; "
                 "it is analysis of reported facts, not investment advice.</p>")
    return "\n".join(parts)


def _safe_title(text: str) -> str:
    return re.sub(r"[\"“”<>&]", "", text).replace("'", "’").strip()


def build_article(
    friday: date, start: date, overview: dict[str, Any], sections: list[SectionResult], *, now: datetime,
) -> dict[str, Any]:
    label = week_label(start, friday)
    headline = overview.get("headline") or ""
    title = _safe_title(f"Weekly Wrap ({label}): {headline}" if headline else f"Weekly Wrap: {label}")
    total = sum(len(s.items) for s in sections)
    subtitle = first_sentences(overview["lede"], 150)
    meta = first_sentences(f"{overview['lede']} {total} stories across {len(sections)} sectors.", 155)

    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for section in sections:
        for item in section.items:
            url = str(item.get("sourceUrl") or "")
            if url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                sources.append({"name": str(item.get("sourceName") or url), "url": url})

    iso = now if friday == now.astimezone(NEW_YORK).date() else datetime(
        friday.year, friday.month, friday.day, 21, 0, tzinfo=timezone.utc)
    slug = f"weekly-wrap-{friday.isoformat()}"
    return {
        "title": title,
        "slug": slug,
        "subtitle": subtitle,
        "meta_description": meta,
        "category": WRAP_CATEGORY,
        "tags": ["Weekly Wrap", *[s.label for s in sections][:6]],
        "date_iso": iso.replace(microsecond=0).isoformat(),
        "date": f"{iso:%B} {iso.day}, {iso.year}",
        "body_html": render_body(overview, sections),
        "editorial_format": WRAP_FORMAT,
        "editorial_format_label": WRAP_CATEGORY,
        "franchise": None,
        "pipeline_version": PIPELINE_VERSION,
        "event_id": f"weekly-{friday.isoformat()}",
        "must_read_score": 100,
        "selection_tier": "weekly_wrap",
        "source_count": len(sources),
        "source_name": "Light Tower Insights",
        "source_url": f"{SITE_URL}/insights.html",
        "sources": sources or [{"name": "Light Tower Insights", "url": f"{SITE_URL}/insights.html"}],
    }


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def prepare_items(by_section: dict[str, list[dict[str, Any]]], insights_dir: Path = INSIGHTS_DIR) -> None:
    counter = 0
    for items in by_section.values():
        for item in items:
            counter += 1
            item["_id"] = f"m{counter}"
            lead = read_lead(str(item["slug"]), insights_dir=insights_dir)
            item["_context"] = f"{item.get('excerpt') or ''} {lead}".strip()


def build_wrap(
    manifest: list[dict[str, Any]],
    friday: date,
    llm: LLM | None,
    *,
    max_per_section: int = 6,
    min_items: int = 8,
    insights_dir: Path = INSIGHTS_DIR,
    now: datetime | None = None,
    workers: int = 4,
    verifier: LLM | None = None,
) -> dict[str, Any]:
    start, end = week_window(friday)
    window = week_label(start, end)
    pool = load_week_items(manifest, start, end)
    result: dict[str, Any] = {"friday": friday.isoformat(), "window": window,
                              "items_in_window": len(pool), "status": "ok"}
    if len(pool) < min_items:
        result.update(status="insufficient_items",
                      reason=f"only {len(pool)} published items in {window}; need {min_items}")
        return result

    by_section = select_for_wrap(pool, max_per_section=max_per_section)
    prepare_items(by_section, insights_dir)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(write_section, key, items, window, llm, verifier=verifier)
                   for key, items in by_section.items()]
        sections = [f.result() for f in futures]

    total = sum(len(s.items) for s in sections)
    overview = write_overview(sections, window, len(pool), llm, verifier)
    article = build_article(friday, start, overview, sections, now=now or datetime.now(timezone.utc))
    fallbacks = sum(len(s.fallback_ids) for s in sections)
    result.update(
        article=article,
        sections=[{"key": s.key, "label": s.label, "items": len(s.items), "attempts": s.attempts,
                   "fallback_items": len(s.fallback_ids), "problems": s.problems[:6], "error": s.error}
                  for s in sections],
        items_featured=total,
        fallback_items=fallbacks,
        llm_used=llm is not None,
    )
    if llm is not None and total and fallbacks / total > 0.5:
        result.update(status="writer_degraded",
                      reason=f"{fallbacks}/{total} items fell back to plain excerpts")
    return result


def publish(article: dict[str, Any], diagnostics: dict[str, Any], *, force: bool = False) -> list[str]:
    """Write the page and update manifest, feed, sitemap and the deploy manifest."""
    from daily_news_agent import render_html, update_feed_xml, update_manifest, update_sitemap_xml
    from edition_manager import write_generated_files

    slug = article["slug"]
    page = INSIGHTS_DIR / f"{slug}.html"
    if page.exists() and not force:
        print(f"  {slug} already exists; use --force to rewrite")
        return []
    written: list[Path] = []
    try:
        from social_image_generator import generate_article_image

        social = INSIGHTS_DIR / f"{slug}_social.png"
        if generate_article_image(article["title"], article["subtitle"], social):
            article["social_image"] = f"/insights/{social.name}"
            written.append(social)
    except Exception:  # noqa: BLE001
        pass  # a social card may degrade; the page may not

    page.write_text(render_html(article), encoding="utf-8")
    written.append(page)
    update_manifest(article)
    update_feed_xml()
    update_sitemap_xml()
    written += [MANIFEST_PATH, SITE_ROOT / "feed.xml", SITE_ROOT / "sitemap.xml"]
    try:
        from v3_publish import _write_related

        written.append(_write_related(article))
    except Exception:  # noqa: BLE001
        pass

    WRAP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = WRAP_STATE_DIR / f"{article['event_id'].removeprefix('weekly-')}.json"
    slim = {k: v for k, v in diagnostics.items() if k != "article"}
    slim["slug"] = slug
    slim["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record.write_text(json.dumps(slim, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(record)

    # Model calls append to the provider log; declaring it keeps the runner's tree clean
    # so the publish step can rebase onto a newer main.
    provider_log = STATE_DIR / "provider-log.jsonl"
    if provider_log.exists():
        written.append(provider_log)

    manifest_path = write_generated_files([p for p in written if p.exists()])
    return [str(p.relative_to(SITE_ROOT)).replace("\\", "/") for p in [*written, manifest_path] if p.exists()]


def _scheduled_guard(now_et: datetime) -> str:
    """Why a *scheduled* invocation should not run now, or '' to proceed."""
    if now_et.weekday() != 4:
        return f"not Friday in New York ({now_et:%A})"
    if not (16 <= now_et.hour < 19):
        return f"outside the 16:00-19:00 New York publishing window ({now_et:%H:%M})"
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--week-ending", help="Friday to wrap, YYYY-MM-DD (default: latest Friday in New York)")
    parser.add_argument("--mode", choices=("preview", "publish"), default="preview")
    parser.add_argument("--max-per-section", type=int, default=6)
    parser.add_argument("--min-items", type=int, default=8)
    parser.add_argument("--no-llm", action="store_true", help="deterministic excerpts only; no provider calls")
    parser.add_argument("--force", action="store_true", help="rewrite an existing wrap for this week")
    parser.add_argument("--scheduled", action="store_true",
                        help="apply the Friday 16:00-19:00 New York guard (for cron triggers)")
    parser.add_argument("--preview-file", default=str(STATE_DIR / "weekly-wrap-preview.json"))
    args = parser.parse_args(argv)

    now_et = datetime.now(NEW_YORK)
    if args.scheduled:
        reason = _scheduled_guard(now_et)
        if reason:
            print(f"Weekly wrap skipped: {reason}.")
            return 0

    friday = date.fromisoformat(args.week_ending) if args.week_ending else latest_friday(now_et.date())
    if friday.weekday() != 4:
        print(f"--week-ending must be a Friday; {friday} is a {friday:%A}.", file=sys.stderr)
        return 2
    slug = f"weekly-wrap-{friday.isoformat()}"
    if args.mode == "publish" and (INSIGHTS_DIR / f"{slug}.html").exists() and not args.force:
        print(f"Weekly wrap for {friday} is already published ({slug}); nothing to do.")
        return 0

    llm: LLM | None = None
    verifier: LLM | None = None
    if not args.no_llm:
        from model_router import provider_chain, provider_config

        chain = provider_chain(provider_config("deepseek", for_writing=True), for_writing=True)
        if not chain:
            print("No writing provider is configured (set DEEPSEEK_API_KEY or OPENAI_API_KEY), "
                  "or pass --no-llm.", file=sys.stderr)
            return 1
        llm = make_llm(chain)
        # Every sentence the model writes is fact-checked by a second pass before it can be published.
        from v4_generation import _make_verifier

        verifier = _make_verifier(chain[0])

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    outcome = build_wrap(manifest, friday, llm, max_per_section=args.max_per_section,
                         min_items=args.min_items, verifier=verifier)
    status = outcome["status"]
    print(f"Weekly wrap {friday} ({outcome['window']}): {status}; "
          f"{outcome.get('items_featured', 0)} featured of {outcome['items_in_window']} published.")
    if status == "insufficient_items":
        print(f"  {outcome['reason']}")
        return 0
    for section in outcome.get("sections", []):
        flag = f" [{section['fallback_items']} fell back]" if section["fallback_items"] else ""
        print(f"  - {section['label']}: {section['items']} items, {section['attempts']} model call(s){flag}")
    if status == "writer_degraded":
        print(f"  {outcome['reason']}; refusing to publish.", file=sys.stderr)
        return 1

    article = outcome["article"]
    if args.mode == "preview":
        out = Path(args.preview_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  title: {article['title']}")
        print(f"  preview written to {out}")
        return 0

    files = publish(article, outcome, force=args.force)
    print(f"  published {article['slug']} ({len(files)} files declared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
