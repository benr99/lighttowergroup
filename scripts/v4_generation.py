"""Bounded, single-writer article generation for the insights pipeline.

V4 deliberately does not use ``EditorialPipeline``.  One selected story gets
one direct structured-writing request, plus at most one direct retry.  Quality
checks are local and the returned drafts retain the v3 publisher contract.
"""

from __future__ import annotations

import json
import hashlib
import html
import os
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

import requests

from claim_verifier import (
    LLM,
    VerifiedDraft,
    assemble_paragraphs,
    source_text_from_dossier,
    verify_draft,
)
from intelligence_object import IntelligenceObject
from readability import (
    paragraph_texts,
    readability_warnings,
    trim_to_sentence,
    unsupported_names,
    unsupported_numbers,
)
from v3_generation import DraftResult, object_to_dossier

DEFAULT_EDITION_BUDGET_S = 45 * 60
DEFAULT_ARTICLE_BUDGET_S = 4 * 60
DEFAULT_ATTEMPT_TIMEOUT_S = 90
MAX_ATTEMPTS_PER_ARTICLE = 2
MAX_TOTAL_ATTEMPTS = 6
DEFAULT_WORKERS = 6
_STATE_LOCK = threading.Lock()

# Each logical model call retries rate limits, server errors and dropped connections
# after these pauses (seconds), always inside the story's own deadline.
REQUEST_RETRY_PAUSES = (0, 4, 12)
# This many calls in a row that exhaust their retries means DeepSeek is down for now.
OUTAGE_THRESHOLD = 3
# Estimate asked of the spending cap before each call; the real cost is recorded after.
EST_CALL_USD = 0.02
# Stories written in Ben's voice when INSIGHTS_VOICE=on. Briefs keep the fast facts-only writer.
VOICE_TIERS = ("tier_a", "tier_b")
VOICE_ARTICLE_BUDGET_S = 540

# Lengths are for readers on a phone. The floors only guard against an empty or
# truncated answer; the writer is told to stop when the facts run out rather than
# pad to a minimum (padding was the main source of abstract, hard-to-read copy).
DEPTH_SPEC = {
    "tier_a": {"format": "flagship", "min_words": 220, "max_words": 850},
    "tier_b": {"format": "analysis", "min_words": 100, "max_words": 520},
    "tier_c": {"format": "brief", "min_words": 60, "max_words": 300},
}
MIN_PARAGRAPHS = {"tier_a": 5, "tier_b": 3, "tier_c": 2}
WRITER_TEMPERATURE = 0.35
# Ben's voice needs room to choose a shape and a hook; facts are still gated sentence by sentence.
VOICE_TEMPERATURE = 0.7
# Bump when the writer prompt changes so drafts cached under an older prompt are not reused.
WRITER_PROMPT_VERSION = "v4.3-verified-sentences"

WRITER_SYSTEM = (
    "You write Light Tower Insights, a commercial real estate capital markets publication. "
    "Readers are sponsors, lenders, brokers and investors. They know the business and read on "
    "their phones between meetings. Write like a sharp colleague explaining a deal over coffee: "
    "plain words, short sentences, a point of view. Be an expert who is easy to read, never a "
    "professor and never a press release."
)


@dataclass(frozen=True)
class RuntimeBudget:
    """One explicit monotonic runtime contract for an edition."""

    started: float
    deadline: float
    article_budget_s: float = DEFAULT_ARTICLE_BUDGET_S
    attempt_timeout_s: float = DEFAULT_ATTEMPT_TIMEOUT_S
    max_attempts_per_article: int = MAX_ATTEMPTS_PER_ARTICLE
    max_total_attempts: int = MAX_TOTAL_ATTEMPTS

    @classmethod
    def start(cls, total_seconds: float, *, article_budget_s: float = DEFAULT_ARTICLE_BUDGET_S) -> "RuntimeBudget":
        started = time.monotonic()
        return cls(started=started, deadline=started + max(0.1, total_seconds), article_budget_s=article_budget_s)

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def article_deadline(self) -> float:
        return min(self.deadline, time.monotonic() + self.article_budget_s)

    def request_timeout(self, article_deadline: float) -> float:
        return max(0.0, min(self.attempt_timeout_s, article_deadline - time.monotonic()))


@dataclass
class ValidationResult:
    valid: bool
    codes: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    word_count: int = 0
    paragraph_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationReport:
    pipeline: str = "v4"
    requested: int = 0
    written: int = 0
    needs_review: int = 0
    failed: int = 0
    skipped: int = 0
    withheld: int = 0  # written but not verifiable against sources; never a pipeline failure
    voiced: int = 0  # completed in Ben's voice (the rest are facts-only)
    voice: bool = False
    stop_reason: str = ""  # set when the day stopped early: budget reached or DeepSeek unavailable
    spend_usd: float = 0.0
    attempts: int = 0
    elapsed_seconds: float = 0.0
    provider_attempts: dict[str, int] = field(default_factory=dict)
    provider_failures: int = 0
    parse_failures: int = 0
    validation_failures: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_dossier(obj: IntelligenceObject, max_chars: int = 18000) -> dict[str, Any]:
    """Keep the factual boundary while preventing an unbounded prompt."""
    dossier = object_to_dossier(obj)
    sources = []
    for source in dossier.get("sources", []):
        item = dict(source)
        text = str(item.get("text") or item.get("summary") or "")
        item["text"] = text[:5000]
        item.pop("full_text_excerpt", None)
        item.pop("reported_facts", None)
        sources.append(item)
    compact = {
        "event_id": dossier.get("event_id"),
        "title": dossier.get("title"),
        "what_happened": dossier.get("what_happened"),
        "sector": dossier.get("sector"),
        "event_type": dossier.get("event_type"),
        "evidence_level": dossier.get("evidence_level"),
        "evidence_level_note": dossier.get("evidence_level_note"),
        "material_claims": dossier.get("material_claims", []),
        "missing_information": dossier.get("missing_information", []),
        "facts": dossier.get("facts", []),
        "sources": sources,
    }
    encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) <= max_chars:
        return compact
    # Preserve source identity and URLs even when retrieved text is unusually large.
    for source in compact["sources"]:
        source["text"] = str(source.get("text") or "")[:1800]
    return compact


def _writer_prompt(obj: IntelligenceObject, dossier: dict[str, Any], spec: dict[str, Any]) -> str:
    dossier_json = json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
    depth = next((name for name, value in DEPTH_SPEC.items() if value is spec), "tier_c")
    target_words = (spec["min_words"] + spec["max_words"]) // 2
    if depth == "tier_c":
        structure = (
            "3-5 short paragraphs: the hook, what happened, and why it matters, each only as the source states it."
        )
    elif depth == "tier_b":
        structure = (
            "4-7 short paragraphs: the hook, what happened, the number that matters, and why it matters, "
            "each only as the source states it."
        )
    else:
        structure = (
            "6-10 short paragraphs: the hook, what happened, the number that matters, why it matters, "
            "the strongest point on the other side, and who gains and who loses, each only as the source states it."
        )
    return f"""Write one Light Tower Insights article from the source text below. Return JSON only. No markdown fences, no commentary.

STORY: {obj.title}
FORMAT: {spec['format']}
LENGTH: about {target_words} words in total across the body ({spec['min_words']}-{spec['max_words']} allowed). Short and true beats long. When the sources run out, stop.
STRUCTURE: {structure}

SOURCES (the complete factual boundary; quotes must be copied from the "text" fields):
{dossier_json}

EVERY SENTENCE IS CHECKED BY MACHINE. How it works:
- Every sentence is a "fact" and must carry quotes. There are no opinion sentences, no predictions, no evaluation, no "this signals", and no closing advice or "what to check" line: all of those are deleted.
- A "fact" states only what its "quotes" support. "quotes" is a list of one or two passages copied character for character from a source "text" (at least 4 words each, at most 240 characters). Quote only the tight passage that carries the claim, and keep its qualifiers (most, about, plans to, expects, could) and who said it. Do not fix, shorten inside, or paraphrase a quote. Copy it.
- You may restate the quoted passage in plainer words, but EVERY number, name, date, amount and relationship in your sentence must appear in its quotes. Spelled-out numbers count too: do not write "three" if the quote says "two".
- A fact must not add a total, difference, ratio or percentage the source does not state; a ranking such as "largest", "first" or "only"; a cause the source does not state; a time the source does not give; or any claim about what someone thinks, wants or fears. If you cannot quote it, do not write it. Plans, requests and allegations stay plans, requests and allegations.
- If a quote says someone said, expects, plans or claims something, your sentence says so too. Never turn a statement, plan, forecast or opinion into plain fact, and never drop "most", "about", "plans to" or "according to".
- Anything that fails a check is deleted from the article, and so is the article if too little survives. A shorter article that is all true is the goal.
- Each sentence is checked and may be deleted on its own, so each must stand on its own: name its subject ("99 West Paces", "Hines Global Income Trust") instead of opening with "It", "They" or "The property". A sentence that points back to a deleted one is deleted too.

HOW TO WRITE IT
- Hook: the first paragraph is one or two short fact sentences with the who, the number and why it matters. Lead with the most interesting quoted fact, not "X announced".
- "Why it matters" is a fact paragraph too: state what the quoted terms mean for the people involved in plain words, using only what the quotes say. If the sources do not say, leave it out.
- Plain English. Sentences average about 15 words and never top 30. Paragraphs are 1-3 sentences. Active voice. Vary how sentences start.
- Explain an insider term in a few words only when the source itself explains it.
- Never use "landscape", "navigating", "highlights", "underscores", "dynamic", "arguably", "essentially", "transformative", "unprecedented", "going forward", "it's worth noting", "the real story is". Never close on what is unknown or "remains to be seen".
- Title: under 80 characters, plain, specific. Its "title_quote" must support every name and number in it. Not a label like "X announces Y".
- Excerpt: one complete sentence of 80-180 characters ending with a period, supported by "excerpt_quote". It must not repeat the title.
- Never claim to have visited, called or seen anything. Do not mention scores, prompts or the editorial process.

Return exactly this shape:
{{"title":"...","title_quote":"...","excerpt":"...","excerpt_quote":"...","paragraphs":[[{{"text":"...","kind":"fact","quotes":["..."]}},{{"text":"...","kind":"fact","quotes":["...","..."]}}]]}}"""


def _parse_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("invalid_json_object")
    return value


def validate_article(article: dict[str, Any], dossier: dict[str, Any], spec: dict[str, Any]) -> ValidationResult:
    codes: list[str] = []
    messages: list[str] = []

    required = ("title", "excerpt", "body_html", "sources")
    for field_name in required:
        if not article.get(field_name):
            codes.append("missing_field")
            messages.append(f"missing required field: {field_name}")
    body = str(article.get("body_html") or "")
    tags = [tag.lower() for tag in re.findall(r"</?([A-Za-z][\w-]*)\b", body)]
    if any(tag != "p" for tag in tags):
        codes.append("invalid_html")
        messages.append("body_html may contain only paragraph tags")
    paragraphs = [
        re.sub(r"<[^>]+>", " ", value).strip()
        for value in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.IGNORECASE | re.DOTALL)
    ]
    paragraphs = [re.sub(r"\s+", " ", value) for value in paragraphs if value]
    words = len(re.findall(r"\b[\w’'-]+\b", re.sub(r"<[^>]+>", " ", body)))
    if body and not re.search(r"<p\b[^>]*>.*?</p>", body, re.IGNORECASE | re.DOTALL):
        codes.append("invalid_html")
        messages.append("body_html has no paragraph content")
    if not (spec["min_words"] <= words <= spec["max_words"]):
        codes.append("word_count_out_of_range")
        messages.append(f"word count {words} is outside {spec['min_words']}-{spec['max_words']}")
    depth = next((name for name, value in DEPTH_SPEC.items() if value is spec), "tier_c")
    minimum_paragraphs = MIN_PARAGRAPHS.get(depth, 3)
    if paragraphs and len(paragraphs) < minimum_paragraphs:
        codes.append("paragraph_count_out_of_range")
        messages.append(
            f"paragraph count {len(paragraphs)} is below minimum {minimum_paragraphs} for {depth}"
        )
    normalized = [re.sub(r"\s+", " ", paragraph).lower() for paragraph in paragraphs]
    if len(normalized) >= 4 and len(set(normalized)) / len(normalized) < 0.9:
        codes.append("repeated_paragraphs")
        messages.append("body_html contains repeated paragraph content")
    if re.search(r"<\s*(script|style|iframe|object|form)\b", body, re.IGNORECASE):
        codes.append("unsafe_html")
        messages.append("body_html contains a forbidden HTML element")

    dossier_urls = {
        str(source.get("url") or "").strip().lower()
        for source in dossier.get("sources", [])
        if source.get("url")
    }
    article_sources = article.get("sources")
    if not isinstance(article_sources, list) or not article_sources:
        codes.append("missing_sources")
        messages.append("sources must be a non-empty list")
    else:
        for source in article_sources:
            if not isinstance(source, dict):
                codes.append("invalid_source")
                messages.append("each source must be an object")
                continue
            url = str(source.get("url") or "").strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                codes.append("invalid_source_url")
                messages.append("source URL is not an absolute HTTP(S) URL")
            elif url.lower() not in dossier_urls:
                codes.append("source_not_in_dossier")
                messages.append("article source URL is outside the dossier")

    if str(article.get("format") or spec["format"]) != spec["format"]:
        codes.append("wrong_format")
        messages.append("article format does not match the selected depth")
    title = str(article.get("title") or "").strip()
    if title and ("placeholder" in title.lower() or "todo" in title.lower()):
        codes.append("placeholder_content")
        messages.append("title contains placeholder content")
    warnings: list[str] = []
    if paragraphs:
        warnings = readability_warnings(paragraphs, excerpt=str(article.get("excerpt") or ""))
        # Fact preservation: a number the sources never gave is the likeliest invented fact.
        invented = unsupported_numbers(
            " ".join([title, str(article.get("excerpt") or ""), " ".join(paragraphs)]),
            json.dumps(dossier, ensure_ascii=False),
        )
        if invented:
            warnings.append(
                "These numbers are not in the dossier; remove them or restate using only dossier figures: "
                + ", ".join(invented[:8])
            )
        invented_names = unsupported_names(" ".join(paragraphs), json.dumps(dossier, ensure_ascii=False))
        if invented_names:
            warnings.append(
                "These names do not appear in the dossier; remove them or use only names the sources gave: "
                + ", ".join(invented_names[:8])
            )
    return ValidationResult(
        valid=not codes,
        codes=sorted(set(codes)),
        messages=messages,
        word_count=words,
        paragraph_count=len(paragraphs),
        warnings=warnings,
    )


def _retryable_error(exc: Exception) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        return bool(response is not None and response.status_code >= 500)
    return isinstance(exc, (json.JSONDecodeError, ValueError))


def _cache_path(state_dir: Path | None, object_id: str) -> Path | None:
    if not state_dir:
        return None
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", object_id)[:120]
    return Path(state_dir) / "v4-drafts" / f"{safe_id}.json"


class BudgetRefused(RuntimeError):
    """The daily (or per-article) spending cap refused a model call."""


class ProviderDown(RuntimeError):
    """DeepSeek is failing persistently; stop starting new work."""


class ProviderHealth:
    """Shared across one edition. Several calls in a row that exhaust their retries, or one
    authorisation failure, mean the provider is down: the day stops cleanly and says so."""

    def __init__(self, threshold: int = OUTAGE_THRESHOLD) -> None:
        self.threshold = threshold
        self.consecutive = 0
        self.down = False
        self.reason = ""
        self._lock = threading.Lock()

    def ok(self) -> None:
        with self._lock:
            self.consecutive = 0

    def failed(self, reason: str, *, permanent: bool = False) -> None:
        with self._lock:
            self.consecutive += 1
            if permanent or self.consecutive >= self.threshold:
                self.down = True
                self.reason = reason


# Which story a worker thread is writing, so verifier calls are charged to it.
_CURRENT = threading.local()


def voice_enabled(explicit: bool | None = None) -> bool:
    """INSIGHTS_VOICE=on writes flagships and analyses in Ben's voice. Off by default."""
    if explicit is not None:
        return explicit
    return os.environ.get("INSIGHTS_VOICE", "off").strip().lower() in {"on", "1", "true", "yes"}


def _chat(
    provider: dict[str, Any], *, system: str, user: str, temperature: float, max_tokens: int,
    timeout_s: float, thinking: bool = False, json_mode: bool = False, deadline: float | None = None,
    budget: Any = None, stage: str = "v4_write", article_id: str = "",
    health: ProviderHealth | None = None, event: str = "provider_call",
) -> str:
    """One logical model call: patient retries for rate limits, server errors and dropped
    connections; spend checked before and recorded after; persistent failure reported to
    ``health`` so the edition can stop cleanly."""
    from model_router import log_provider_event

    if health is not None and health.down:
        raise ProviderDown(health.reason or "provider unavailable")
    if budget is not None and not budget.allow(stage, estimated_usd=EST_CALL_USD, article_id=article_id):
        raise BudgetRefused("daily model budget reached")
    name = str(provider.get("provider") or "unknown")
    model = str(provider.get("model") or "")
    payload: dict[str, Any] = {
        "model": model, "temperature": temperature, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if name == "deepseek":
        payload["thinking"] = {"type": "enabled" if thinking else "disabled"}
    last: Exception | None = None
    for pause in REQUEST_RETRY_PAUSES:
        if pause:
            if deadline is not None and time.monotonic() + pause >= deadline:
                break
            time.sleep(pause)
        limit = timeout_s if deadline is None else min(timeout_s, deadline - time.monotonic())
        if limit <= 1:
            break
        started = time.monotonic()
        try:
            response = requests.post(
                str(provider.get("url")),
                headers={"Authorization": f"Bearer {provider.get('api_key')}", "Content-Type": "application/json"},
                json=payload, timeout=max(1.0, limit),
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            last = exc
            log_provider_event(event, outcome="failed", provider=name, model=model,
                               attempt_seconds=round(time.monotonic() - started, 2),
                               error=f"{type(exc).__name__}: {exc}"[:240])
            continue
        status = int(getattr(response, "status_code", 200))
        text = str(getattr(response, "text", "") or "")
        if status in (401, 403) or (status == 429 and "insufficient" in text.lower()):
            if health is not None:
                health.failed(f"{name} refused the key or has no credit (HTTP {status})", permanent=True)
            log_provider_event(event, outcome="failed", provider=name, model=model, error=f"HTTP {status}")
            response.raise_for_status()
            raise requests.HTTPError(f"HTTP {status}", response=response)
        if status == 429 or status >= 500:
            last = requests.HTTPError(f"HTTP {status}", response=response)
            log_provider_event(event, outcome="failed", provider=name, model=model,
                               attempt_seconds=round(time.monotonic() - started, 2), error=f"HTTP {status}")
            continue
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        if budget is not None:
            budget.record(stage, model=model, input_tokens=int(usage.get("prompt_tokens") or 0),
                          output_tokens=int(usage.get("completion_tokens") or 0),
                          seconds=time.monotonic() - started, article_id=article_id)
        if health is not None:
            health.ok()
        choice = (data.get("choices") or [{}])[0]
        content = str((choice.get("message") or {}).get("content") or "").strip()
        log_provider_event(event, outcome="success", provider=name, model=model,
                           attempt_seconds=round(time.monotonic() - started, 2),
                           finish_reason=choice.get("finish_reason", "unknown"))
        if str(choice.get("finish_reason") or "") == "length":
            raise ValueError("provider_truncated")
        if not content:
            raise ValueError("empty_completion")
        return content
    if health is not None:
        health.failed(f"{name} did not answer after {len(REQUEST_RETRY_PAUSES)} tries: {last}"[:200])
    raise last or RuntimeError("provider unavailable")


def _request_once(prompt: str, provider: dict[str, Any], timeout_s: float, **kwargs: Any) -> str:
    """The facts-only writer request (with the shared retry, spend and health handling)."""
    return _chat(provider, system=WRITER_SYSTEM, user=prompt, temperature=WRITER_TEMPERATURE,
                 max_tokens=3600, timeout_s=timeout_s, **kwargs)


def _make_verifier(
    writer: dict[str, Any] | None = None, *, timeout_s: float = 120.0, budget: Any = None,
    health: ProviderHealth | None = None,
) -> LLM:
    """The fact-checking model: DeepSeek in reasoning mode, at temperature 0.

    DeepSeek is the only provider (Ben's decision, 2026-10-09). Reasoning mode is slower
    but checks each claim against the source more carefully than the writer's fast mode.
    """
    from model_router import provider_config

    provider = provider_config("deepseek", for_writing=True)
    if provider is None and writer and writer.get("provider") == "deepseek":
        provider = dict(writer)
    if provider is None:
        raise RuntimeError("fact-check unavailable: DEEPSEEK_API_KEY is not set")

    def call(system: str, user: str) -> str:
        try:
            content = _chat(provider, system=system, user=user, temperature=0.0, max_tokens=16000,
                            timeout_s=timeout_s, thinking=True, json_mode=True, budget=budget,
                            stage="v4_verify", article_id=getattr(_CURRENT, "article_id", ""),
                            health=health, event="fact_check")
        except (BudgetRefused, ProviderDown):
            raise
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"fact-check unavailable: {type(exc).__name__}: {exc}"[:240]) from exc
        call.used = f"{provider.get('provider')}/{provider.get('model')}"  # type: ignore[attr-defined]
        return content

    call.used = ""  # type: ignore[attr-defined]
    return call


# A story must keep at least this many verified fact sentences to be published.
MIN_FACT_SENTENCES = {"tier_a": 8, "tier_b": 5, "tier_c": 3}


def _assemble(
    paragraphs: list[str], *, title: str, title_ok: bool, excerpt: str, excerpt_ok: bool, first_fact: str,
    dossier: dict[str, Any], spec: dict[str, Any], story_title: str, voice: bool = False,
) -> dict[str, Any]:
    """The page, built from verified sentences only."""
    title = title if title_ok and title else story_title
    if not (excerpt_ok and 40 <= len(excerpt) <= 200 and excerpt.rstrip()[-1:] in ".!?"):
        excerpt = trim_to_sentence(first_fact, 200) if first_fact else ""
    sources = [
        {"name": str(s.get("name") or s.get("source") or ""), "url": str(s.get("url") or "")}
        for s in dossier.get("sources", []) if s.get("url")
    ]
    return {
        "title": title,
        "excerpt": excerpt,
        "body_html": "".join(f"<p>{html.escape(text, quote=False)}</p>" for text in paragraphs),
        "format": spec["format"],
        "sources": sources,
        "evidence_level": dossier.get("evidence_level", ""),
        "fact_checked": True,
        "voice": "ben" if voice else "facts",
    }


def _build_article(
    verified: VerifiedDraft, dossier: dict[str, Any], spec: dict[str, Any], story_title: str,
) -> dict[str, Any]:
    """Assemble the facts-only page from verified sentences."""
    facts = [i.text for p in verified.paragraphs for i in p if i.kind == "fact"]
    return _assemble(assemble_paragraphs(verified), title=verified.title, title_ok=verified.title_ok,
                     excerpt=verified.excerpt, excerpt_ok=verified.excerpt_ok,
                     first_fact=facts[0] if facts else "", dossier=dossier, spec=spec, story_title=story_title)


def _voice_evidence(vd: Any) -> dict[str, Any]:
    def dump(i: Any) -> dict[str, Any]:
        return {"kind": i.kind, "text": i.text, "quotes": i.quotes, "because": i.because}
    return {
        "title": vd.title, "excerpt": vd.excerpt,
        "paragraphs": [[{**dump(i), "role": role} for i in items] for role, items in vd.paragraphs],
        "rejected": [{**dump(i), "reason": i.reason} for i in vd.rejected],
    }


@dataclass
class _Candidate:
    article: dict[str, Any]
    validation: ValidationResult
    evidence: dict[str, Any]
    facts: int
    takes: int
    rejected: list[str]
    attempt: int
    mode: str  # "voice" or "facts"


def _facts_attempts(
    obj: IntelligenceObject, dossier: dict[str, Any], spec: dict[str, Any], depth: str, source_text: str,
    provider: dict[str, Any], check: LLM, runtime: RuntimeBudget, deadline: float,
    call_kw: dict[str, Any], record: Any, diagnostics: dict[str, Any],
) -> list[_Candidate]:
    """The fast facts-only writer: one request, the fact gate, and at most one rewrite."""
    prompt = _writer_prompt(obj, dossier, spec)
    min_facts = MIN_FACT_SENTENCES.get(depth, 3)
    candidates: list[_Candidate] = []
    feedback = ""
    for attempt in range(1, runtime.max_attempts_per_article + 1):
        remaining = runtime.request_timeout(deadline)
        if remaining <= 0:
            break
        diagnostics["attempts"] = diagnostics.get("attempts", 0) + 1
        record("attempt_started", attempt=attempt, mode="facts", provider=provider.get("provider"))
        request_started = time.monotonic()
        try:
            attempt_prompt = prompt
            if feedback:
                attempt_prompt += (
                    "\n\nYour previous draft was fact-checked. The sentences and notes below were rejected "
                    "and deleted. Write a complete replacement in the same JSON shape. Copy quotes exactly "
                    "from the source text, and leave out any claim you cannot quote.\n" + feedback
                )
            raw = _request_once(attempt_prompt, provider, remaining, deadline=deadline, **call_kw)
            diagnostics["request_seconds"] = round(time.monotonic() - request_started, 2)
            draft = _parse_json(raw)
            verified = verify_draft(draft, source_text, check)
        except (BudgetRefused, ProviderDown):
            raise
        except Exception as exc:  # noqa: BLE001
            _note_error(diagnostics, exc, request_started)
            record("attempt_failed", attempt=attempt, mode="facts", error_kind=diagnostics["error_kind"],
                   error=diagnostics["error"])
            if diagnostics["error_kind"] in ("parse",) and attempt < runtime.max_attempts_per_article:
                continue
            break
        article = _build_article(verified, dossier, spec, obj.title)
        validation = validate_article(article, dossier, spec)
        enough = verified.fact_count >= min_facts
        diagnostics.update({"error_kind": "validation", "validation": validation.to_dict(),
                            "fact_check": {"checked": verified.items_checked, "rejected": len(verified.rejected),
                                           "kept_facts": verified.fact_count, "kept_views": verified.view_count,
                                           "verifier": getattr(check, "used", "")}})
        record("fact_checked", attempt=attempt, mode="facts", checked=verified.items_checked,
               rejected=len(verified.rejected), kept_facts=verified.fact_count,
               hard_valid=validation.valid, warnings=validation.warnings[:5])
        if validation.valid and enough:
            candidates.append(_Candidate(article, validation, verified.to_evidence(), verified.fact_count, 0,
                                         [i.reason for i in verified.rejected], attempt, "facts"))
        if validation.valid and enough and not verified.rejected and not validation.warnings:
            break
        notes = verified.rejected_report()
        notes += [f"readability: {w}" for w in validation.warnings]
        if not enough:
            notes.append(f"too few verified facts survived ({verified.fact_count}); "
                         f"write at least {min_facts} quoted fact sentences")
        notes += [f"structure: {m}" for m in validation.messages]
        feedback = "\n".join(f"- {n}" for n in notes)
    return candidates


def _voice_attempts(
    obj: IntelligenceObject, dossier: dict[str, Any], spec: dict[str, Any], depth: str, source_text: str,
    provider: dict[str, Any], check: LLM, runtime: RuntimeBudget, deadline: float,
    call_kw: dict[str, Any], record: Any, diagnostics: dict[str, Any],
) -> list[_Candidate]:
    """Ben's voice: a brief (find the story), the piece, then the fact gate and the voice gate.

    Facts are proved exactly as in the facts-only writer; opinion ("take") and connective
    ("voice") sentences must rest on surviving facts and pass their own rules and an
    independent review, or they are deleted.
    """
    import ben_voice as bv
    import voice_gate as vg

    sources_json = json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
    system = bv.system_prompt()
    context, notes = bv.load_bank("context-bank.json"), bv.load_bank("ben-notes.json")
    min_facts = MIN_FACT_SENTENCES.get(depth, 3)
    candidates: list[_Candidate] = []
    started = time.monotonic()

    def ask(user: str, max_tokens: int) -> dict[str, Any]:
        remaining = runtime.request_timeout(deadline)
        if remaining <= 0:
            raise TimeoutError("article deadline exceeded")
        return _parse_json(_chat(provider, system=system, user=user, temperature=VOICE_TEMPERATURE,
                                 max_tokens=max_tokens, timeout_s=max(remaining, 1.0), json_mode=True,
                                 deadline=deadline, **call_kw))

    try:
        diagnostics["attempts"] = diagnostics.get("attempts", 0) + 1
        record("attempt_started", attempt=0, mode="voice_brief", provider=provider.get("provider"))
        brief = ask(bv.brief_prompt(obj.title, depth, sources_json), 2500)
    except (BudgetRefused, ProviderDown):
        raise
    except Exception as exc:  # noqa: BLE001
        _note_error(diagnostics, exc, started)
        record("attempt_failed", attempt=0, mode="voice_brief", error=diagnostics["error"])
        return candidates
    diagnostics["brief"] = {k: brief.get(k) for k in ("shape", "lens", "protagonist", "tension") if k in brief}
    base = bv.article_prompt(story=obj.title, fmt=spec["format"], min_words=spec["min_words"],
                             max_words=spec["max_words"], brief=brief, sources_json=sources_json,
                             context=context, notes=notes)
    feedback = ""
    for attempt in range(1, runtime.max_attempts_per_article + 1):
        diagnostics["attempts"] = diagnostics.get("attempts", 0) + 1
        record("attempt_started", attempt=attempt, mode="voice", provider=provider.get("provider"))
        request_started = time.monotonic()
        note = ("\n\nYour previous draft was checked. These sentences were rejected and deleted. Write a complete "
                "replacement in the same JSON shape. Keep every fact plain and single-claim, put all colour in "
                "separate take/voice sentences, and copy quotes exactly.\n" + feedback) if feedback else ""
        try:
            draft = ask(base + note, 6000)
            vd = vg.verify_voice_draft(draft, source_text, check, context=context, notes=notes)
        except (BudgetRefused, ProviderDown):
            raise
        except Exception as exc:  # noqa: BLE001
            _note_error(diagnostics, exc, request_started)
            record("attempt_failed", attempt=attempt, mode="voice", error_kind=diagnostics["error_kind"],
                   error=diagnostics["error"])
            if diagnostics["error_kind"] == "parse" and attempt < runtime.max_attempts_per_article:
                continue
            break
        first_fact = next((i.text for _, items in vd.paragraphs for i in items if i.kind == "fact"), "")
        article = _assemble(vd.text_paragraphs(), title=vd.title, title_ok=vd.title_ok, excerpt=vd.excerpt,
                            excerpt_ok=vd.excerpt_ok, first_fact=first_fact, dossier=dossier, spec=spec,
                            story_title=obj.title, voice=True)
        validation = validate_article(article, dossier, spec)
        enough = vd.fact_count >= min_facts
        total = len(vd.rejected) + vd.fact_count + vd.take_count + vd.voice_count
        diagnostics.update({"error_kind": "validation", "validation": validation.to_dict(),
                            "fact_check": {"checked": total, "rejected": len(vd.rejected),
                                           "kept_facts": vd.fact_count, "kept_takes": vd.take_count,
                                           "kept_voice": vd.voice_count, "verifier": getattr(check, "used", "")}})
        record("fact_checked", attempt=attempt, mode="voice", checked=total, rejected=len(vd.rejected),
               kept_facts=vd.fact_count, kept_takes=vd.take_count, hard_valid=validation.valid,
               warnings=validation.warnings[:5])
        if validation.valid and enough:
            candidates.append(_Candidate(article, validation, _voice_evidence(vd), vd.fact_count, vd.take_count,
                                         [i.reason for i in vd.rejected], attempt, "voice"))
        if validation.valid and enough and len(vd.rejected) <= max(2, 0.2 * total) and vd.take_count >= 1:
            break
        lines = [f"[{i.kind}] {i.text[:140]} <- {i.reason[:140]}" for i in vd.rejected[:14]]
        lines += [f"readability: {w}" for w in validation.warnings]
        if not enough:
            lines.append(f"too few verified facts survived ({vd.fact_count}); write at least {min_facts} quoted fact sentences")
        lines += [f"structure: {m}" for m in validation.messages]
        feedback = "\n".join(f"- {n}" for n in lines)
    return candidates


def _note_error(diagnostics: dict[str, Any], exc: Exception, started: float) -> None:
    error = f"{type(exc).__name__}: {exc}"[:240]
    if isinstance(exc, json.JSONDecodeError) or str(exc) == "invalid_json_object":
        kind = "parse"
    elif "fact-check" in str(exc) or "verifier" in str(exc) or "rubric" in str(exc):
        kind = "verifier"
    elif isinstance(exc, ValueError) and str(exc) in {"provider_truncated", "empty_completion"}:
        kind = "parse"
    else:
        kind = "provider"
    diagnostics.update({"error_kind": kind, "error": error,
                        "request_seconds": round(time.monotonic() - started, 2)})


def write_one(
    obj: IntelligenceObject,
    *,
    provider: dict[str, Any],
    deadline: float,
    runtime: RuntimeBudget | None = None,
    state_dir: Path | None = None,
    run_id: str = "",
    verifier: LLM | None = None,
    budget: Any = None,
    health: ProviderHealth | None = None,
    voice: bool | None = None,
) -> DraftResult:
    depth = obj.recommended_depth or "tier_c"
    spec = DEPTH_SPEC.get(depth, DEPTH_SPEC["tier_c"])
    result = DraftResult(object_id=obj.object_id, title=obj.title, sector=obj.primary_sector, depth=depth)
    started = time.monotonic()
    runtime = runtime or RuntimeBudget(started=started, deadline=deadline)
    use_voice = voice_enabled(voice) and depth in VOICE_TIERS
    dossier = _safe_dossier(obj)
    dossier_hash = hashlib.sha256(
        json.dumps(dossier, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    state_path = Path(state_dir) / "v4-article-state.jsonl" if state_dir else None
    cached_path = _cache_path(state_dir, obj.object_id)
    source_text = source_text_from_dossier(dossier)
    prompt_version = WRITER_PROMPT_VERSION
    if use_voice:
        import ben_voice
        prompt_version += "+" + ben_voice.VOICE_PROMPT_VERSION

    def record(status: str, **extra: Any) -> None:
        if not state_path:
            return
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": run_id, "object_id": obj.object_id, "title": obj.title,
                   "depth": depth, "dossier_hash": dossier_hash, "status": status,
                   "elapsed_seconds": round(time.monotonic() - started, 2), **extra}
        with _STATE_LOCK:
            with state_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    if depth == "none":
        result.status = "skipped"
        result.skipped_reason = "evidence does not support any coverage"
        record(result.status, reason=result.skipped_reason)
        return result

    if cached_path and cached_path.exists():
        try:
            cached = json.loads(cached_path.read_text(encoding="utf-8"))
            if (cached.get("dossier_hash") == dossier_hash and cached.get("depth") == depth
                    and cached.get("prompt_version") == prompt_version):
                article = cached.get("article")
                validation = validate_article(article, dossier, spec) if isinstance(article, dict) else None
                # Only drafts that already passed the fact gate are ever cached.
                if validation and validation.valid and article.get("fact_checked"):
                    result.article = article
                    result.status = "completed"
                    result.stages_run = ["cache_reuse", "local_validation"]
                    result.diagnostics = {"attempts": 0, "cache_reused": True,
                                          "error_kind": "none", "validation": validation.to_dict(),
                                          "dossier_hash": dossier_hash}
                    record("cache_reused", output_artifact=str(cached_path))
                    return result
        except (OSError, json.JSONDecodeError):
            pass

    provider_name = str(provider.get("provider") or "unknown")
    provider_model = str(provider.get("model") or "")
    diagnostics: dict[str, Any] = {"attempts": 0, "provider": provider_name, "model": provider_model,
                                   "dossier_hash": dossier_hash, "mode": "voice" if use_voice else "facts"}
    try:
        check = verifier or _make_verifier(provider, budget=budget, health=health)
    except Exception as exc:  # noqa: BLE001
        check = None
        diagnostics.update({"error_kind": "verifier", "error": f"{type(exc).__name__}: {exc}"[:200]})

    _CURRENT.article_id = obj.object_id
    call_kw = {"budget": budget, "stage": "v4_write", "article_id": obj.object_id, "health": health}
    candidates: list[_Candidate] = []
    stop_reason = ""
    try:
        if check is not None and use_voice:
            candidates = _voice_attempts(obj, dossier, spec, depth, source_text, provider, check, runtime,
                                         deadline, call_kw, record, diagnostics)
            if not candidates:
                diagnostics["voice_fallback"] = True
        if check is not None and not candidates and runtime.request_timeout(deadline) > 0:
            candidates = _facts_attempts(obj, dossier, spec, depth, source_text, provider, check, runtime,
                                         deadline, call_kw, record, diagnostics)
    except BudgetRefused as exc:
        stop_reason = f"skipped: {exc}"
    except ProviderDown as exc:
        stop_reason = f"skipped: DeepSeek unavailable ({exc})"[:200]
    finally:
        _CURRENT.article_id = ""
    result.diagnostics = diagnostics

    if candidates:
        # Best verified draft: Ben's voice over facts-only, then no warnings, then the most verified facts.
        best = max(candidates, key=lambda c: (c.mode == "voice" and c.takes > 0, not c.validation.warnings,
                                              c.facts, c.attempt))
        article = best.article
        result.article = article
        result.status = "completed"
        result.stages_run = (["voice_brief", "voice_writer", "fact_check", "voice_gate", "local_validation"]
                             if best.mode == "voice" else ["bounded_writer", "fact_check", "local_validation"])
        result.diagnostics = {**diagnostics, "mode": best.mode, "validation": best.validation.to_dict(),
                              "readability_warnings": best.validation.warnings,
                              "sentences_rejected_by_fact_check": best.rejected[:20]}
        if cached_path:
            cached_path.parent.mkdir(parents=True, exist_ok=True)
            cached_path.write_text(json.dumps({
                "object_id": obj.object_id, "depth": depth, "dossier_hash": dossier_hash,
                "prompt_version": prompt_version, "article": article,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if state_dir:
            evidence = Path(state_dir) / "v4-evidence" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', obj.object_id)[:120]}.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(json.dumps({
                "object_id": obj.object_id, "title": article["title"], "run_id": run_id,
                "sector": obj.primary_sector, "depth": depth, "mode": best.mode,
                "writer": f"{provider_name}/{provider_model}", "verifier": getattr(check, "used", ""),
                "sources": [s["url"] for s in article["sources"]], **best.evidence,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record("completed", attempt=best.attempt, mode=best.mode, validation=best.validation.to_dict(),
               output_artifact=str(cached_path) if cached_path else "")
        result.seconds = round(time.monotonic() - started, 1)
        return result

    result.seconds = round(time.monotonic() - started, 1)
    if stop_reason:
        result.status = "skipped"
        result.skipped_reason = stop_reason
        record("skipped", reason=stop_reason)
        return result
    if diagnostics.get("fact_check") and diagnostics.get("error_kind") == "validation":
        # The story was written but too little of it survived verification. Withholding is the
        # correct outcome, not a pipeline failure: the other stories still publish.
        result.status = "withheld"
        result.skipped_reason = "could not be verified against its sources"
        result.stages_run = ["bounded_writer", "fact_check"]
        record("withheld", reason=result.skipped_reason, fact_check=diagnostics.get("fact_check"))
        return result
    if diagnostics.get("attempts", 0) == 0 and check is not None:
        result.status = "skipped"
        result.skipped_reason = "article deadline exceeded"
        record("skipped", reason=result.skipped_reason)
        return result
    result.status = "failed"
    result.errors = [diagnostics.get("error") or "generation failed"]
    result.stages_run = ["bounded_writer", "fact_check"]
    return result


def write_all(
    objects: Sequence[IntelligenceObject],
    *,
    provider: dict[str, Any] | None = None,
    budget: Any = None,
    deadline_s: float = DEFAULT_EDITION_BUDGET_S,
    article_budget_s: float = DEFAULT_ARTICLE_BUDGET_S,
    voice_article_budget_s: float = VOICE_ARTICLE_BUDGET_S,
    workers: int = DEFAULT_WORKERS,
    verbose: bool = True,
    state_dir: Path | None = None,
    run_id: str = "",
    verifier: LLM | None = None,
    voice: bool | None = None,
    health: ProviderHealth | None = None,
) -> tuple[list[DraftResult], GenerationReport]:
    started = time.monotonic()
    report = GenerationReport(requested=len(objects))
    results: list[DraftResult] = []
    if not provider or not provider.get("api_key"):
        report.failed = len(objects)
        report.provider_failures = len(objects)
        report.results = [DraftResult(
            object_id=o.object_id, title=o.title, status="failed",
            errors=["no writing provider configured"],
            diagnostics={"attempts": 0, "error_kind": "provider"},
        ).to_dict() for o in objects]
        return results, report

    use_voice = voice_enabled(voice)
    report.voice = use_voice
    health = health or ProviderHealth()
    runtime = RuntimeBudget.start(deadline_s, article_budget_s=article_budget_s)
    if verifier is None:
        try:
            verifier = _make_verifier(provider, budget=budget, health=health)
        except Exception:  # noqa: BLE001
            verifier = None  # write_one fails closed without a fact-checker
    indexed = list(enumerate(objects))
    next_index = 0
    futures: dict[Any, tuple[int, IntelligenceObject]] = {}
    pool = ThreadPoolExecutor(max_workers=max(1, min(int(workers), DEFAULT_WORKERS)))
    stop_reason = ""

    def stopped() -> str:
        if health.down:
            return f"DeepSeek unavailable ({health.reason})"[:200]
        if budget is not None and getattr(budget, "remaining", 1.0) < EST_CALL_USD:
            return "daily model budget reached"
        return ""

    def submit_one(index: int, obj: IntelligenceObject) -> None:
        voiced = use_voice and (obj.recommended_depth or "tier_c") in VOICE_TIERS
        allowance = voice_article_budget_s if voiced else runtime.article_budget_s
        article_deadline = min(runtime.deadline, time.monotonic() + allowance)
        article_runtime = RuntimeBudget(
            started=time.monotonic(), deadline=article_deadline,
            article_budget_s=allowance,
            attempt_timeout_s=runtime.attempt_timeout_s,
            max_attempts_per_article=runtime.max_attempts_per_article,
            max_total_attempts=runtime.max_total_attempts,
        )
        future = pool.submit(write_one, obj, provider=provider,
                             deadline=article_deadline, runtime=article_runtime,
                             state_dir=state_dir, run_id=run_id, verifier=verifier,
                             budget=budget, health=health, voice=use_voice)
        futures[future] = (index, obj)

    def can_start() -> bool:
        nonlocal stop_reason
        stop_reason = stop_reason or stopped()
        return not stop_reason and runtime.remaining() >= min(runtime.article_budget_s, runtime.attempt_timeout_s)

    try:
        while next_index < len(indexed) and len(futures) < max(1, min(int(workers), DEFAULT_WORKERS)):
            if not can_start():
                break
            index, obj = indexed[next_index]
            submit_one(index, obj)
            next_index += 1

        while futures:
            if runtime.remaining() <= 0:
                for future in futures:
                    future.cancel()
                break
            done, _ = wait(futures, timeout=min(runtime.remaining(), 1.0),
                           return_when=FIRST_COMPLETED)
            if not done:
                continue
            for future in done:
                index, obj = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    result = DraftResult(object_id=obj.object_id, title=obj.title,
                                         sector=obj.primary_sector, depth=obj.recommended_depth,
                                         status="failed", errors=[f"{type(exc).__name__}: {exc}"[:240]])
                results.append((index, result))
                if verbose:
                    print(f"    [v4 {index + 1}/{len(objects)}] {result.status}: {result.title[:58]} ({result.seconds:.1f}s)", flush=True)
                if next_index < len(indexed) and can_start():
                    new_index, new_obj = indexed[next_index]
                    submit_one(new_index, new_obj)
                    next_index += 1
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Active requests have finite HTTP timeouts; mark work not returned by the
    # deadline as skipped rather than pretending it failed or completed.
    returned = {index for index, _ in results}
    for future, (index, obj) in list(futures.items()):
        if future.done() and not future.cancelled():
            try:
                results.append((index, future.result()))
                returned.add(index)
            except Exception:
                pass
    stop_reason = stop_reason or stopped()
    report.stop_reason = stop_reason
    for index, obj in indexed:
        if index not in returned:
            results.append((index, DraftResult(object_id=obj.object_id, title=obj.title,
                                               sector=obj.primary_sector, depth=obj.recommended_depth,
                                               status="skipped",
                                               skipped_reason=stop_reason or "edition generation window closed")))
    results.sort(key=lambda pair: pair[0])
    results = [result for _, result in results]
    for result in results:
        if result.status == "completed":
            report.written += 1
            if (result.article or {}).get("voice") == "ben":
                report.voiced += 1
        elif result.status == "skipped":
            report.skipped += 1
        elif result.status == "withheld":
            report.withheld += 1
        else:
            report.failed += 1
            error_kind = result.diagnostics.get("error_kind")
            if error_kind == "validation":
                report.validation_failures += 1
            elif error_kind == "parse":
                report.parse_failures += 1
            else:
                report.provider_failures += 1
        attempts = int(result.diagnostics.get("attempts", 0))
        report.attempts += attempts
        name = str(provider.get("provider") or "unknown")
        report.provider_attempts[name] = report.provider_attempts.get(name, 0) + attempts
    if budget is not None:
        try:
            report.spend_usd = round(float(budget.session_usd), 4)
        except Exception:  # noqa: BLE001
            pass
    report.elapsed_seconds = round(time.monotonic() - started, 2)
    report.results = [r.to_dict() for r in results]
    return results, report


def summarise(report: GenerationReport) -> str:
    line = (f"  v4 wrote {report.written}/{report.requested} in {report.elapsed_seconds:.0f}s "
            f"({report.voiced} in Ben's voice; {report.attempts} model attempts; {report.failed} failed; "
            f"{report.skipped} skipped; {report.withheld} withheld as unverifiable; "
            f"${report.spend_usd:.2f} spent)")
    if report.stop_reason:
        line += f"\n  stopped early: {report.stop_reason}"
    return line
