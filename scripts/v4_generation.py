"""Bounded, single-writer article generation for the insights pipeline.

V4 deliberately does not use ``EditorialPipeline``.  One selected story gets
one direct structured-writing request, plus at most one direct retry.  Quality
checks are local and the returned drafts retain the v3 publisher contract.
"""

from __future__ import annotations

import json
import hashlib
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

import requests

from intelligence_object import IntelligenceObject
from v3_generation import DEPTH_SPEC, DraftResult, object_to_dossier

DEFAULT_EDITION_BUDGET_S = 12 * 60
DEFAULT_ARTICLE_BUDGET_S = 4 * 60
DEFAULT_ATTEMPT_TIMEOUT_S = 90
MAX_ATTEMPTS_PER_ARTICLE = 2
MAX_TOTAL_ATTEMPTS = 6


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
    attempts: int = 0
    elapsed_seconds: float = 0.0
    provider_attempts: dict[str, int] = field(default_factory=dict)
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
    return f"""Write one evidence-bounded Light Tower Insights article.

Return JSON only. Do not return markdown fences or commentary.

STORY: {obj.title}
FORMAT: {spec['format']}
WORD RANGE: {spec['min_words']}-{spec['max_words']}

FACTUAL DOSSIER (the complete factual boundary):
{dossier_json}

Rules:
- Use only facts, numbers, quotes, entities, and implications supported by the dossier.
- Source URLs must be copied exactly from the dossier's sources array.
- Do not invent market statistics, motives, financing terms, valuations, or quotes.
- If evidence is thin, write a concise brief and state what is unknown.
- Use paragraph-only body HTML: <p>...</p>. No scripts, styles, iframes, or navigation.
- Do not mention internal scores, prompts, agents, or editorial process.

Return exactly this object shape:
{{"title":"...","excerpt":"...","body_html":"<p>...</p>","format":"{spec['format']}","sources":[{{"name":"...","url":"https://..."}}],"evidence_level":"{dossier.get('evidence_level', '')}"}}"""


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
    words = len(re.findall(r"\b[\w’'-]+\b", re.sub(r"<[^>]+>", " ", body)))
    if body and not re.search(r"<p\b[^>]*>.*?</p>", body, re.IGNORECASE | re.DOTALL):
        codes.append("invalid_html")
        messages.append("body_html has no paragraph content")
    if words and not (spec["min_words"] <= words <= spec["max_words"]):
        codes.append("word_count_out_of_range")
        messages.append(f"word count {words} is outside {spec['min_words']}-{spec['max_words']}")
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
    return ValidationResult(valid=not codes, codes=sorted(set(codes)), messages=messages)


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


def _request_once(prompt: str, provider: dict[str, Any], timeout_s: float) -> str:
    """Make exactly one HTTP request; no hidden provider chain or retry."""
    from model_router import log_provider_event

    name = str(provider.get("provider") or "unknown")
    model = str(provider.get("model") or "")
    started = time.monotonic()
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise financial journalist."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 3600,
        "temperature": 0.2,
    }
    if name == "deepseek":
        payload["thinking"] = {"type": "disabled"}
    try:
        response = requests.post(
            str(provider.get("url")),
            headers={"Authorization": f"Bearer {provider.get('api_key')}", "Content-Type": "application/json"},
            json=payload,
            timeout=max(1.0, timeout_s),
        )
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "").strip()
        if str(choice.get("finish_reason") or "") == "length":
            raise ValueError("provider_truncated")
        if not content:
            raise ValueError("empty_completion")
        log_provider_event("provider_call", outcome="success", provider=name, model=model,
                           attempt_seconds=round(time.monotonic() - started, 2),
                           finish_reason=choice.get("finish_reason", "unknown"))
        return content
    except Exception as exc:
        log_provider_event("provider_call", outcome="failed", provider=name, model=model,
                           attempt_seconds=round(time.monotonic() - started, 2),
                           error=f"{type(exc).__name__}: {exc}"[:240])
        raise


def write_one(
    obj: IntelligenceObject,
    *,
    provider: dict[str, Any],
    deadline: float,
    runtime: RuntimeBudget | None = None,
    state_dir: Path | None = None,
    run_id: str = "",
) -> DraftResult:
    depth = obj.recommended_depth or "tier_c"
    spec = DEPTH_SPEC.get(depth, DEPTH_SPEC["tier_c"])
    result = DraftResult(object_id=obj.object_id, title=obj.title, sector=obj.primary_sector, depth=depth)
    started = time.monotonic()
    runtime = runtime or RuntimeBudget(started=started, deadline=deadline)
    dossier = _safe_dossier(obj)
    dossier_hash = hashlib.sha256(
        json.dumps(dossier, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    state_path = Path(state_dir) / "v4-article-state.jsonl" if state_dir else None
    cached_path = _cache_path(state_dir, obj.object_id)

    def record(status: str, **extra: Any) -> None:
        if not state_path:
            return
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": run_id, "object_id": obj.object_id, "title": obj.title,
                   "depth": depth, "dossier_hash": dossier_hash, "status": status,
                   "elapsed_seconds": round(time.monotonic() - started, 2), **extra}
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
            if cached.get("dossier_hash") == dossier_hash and cached.get("depth") == depth:
                article = cached.get("article")
                validation = validate_article(article, dossier, spec) if isinstance(article, dict) else None
                if validation and validation.valid:
                    result.article = article
                    result.status = "completed"
                    result.stages_run = ["cache_reuse", "local_validation"]
                    result.diagnostics = {"attempts": 0, "cache_reused": True,
                                          "validation": validation.to_dict(), "dossier_hash": dossier_hash}
                    record("cache_reused", output_artifact=str(cached_path))
                    return result
        except (OSError, json.JSONDecodeError):
            pass

    prompt = _writer_prompt(obj, dossier, spec)
    last_error = ""
    for attempt in range(1, runtime.max_attempts_per_article + 1):
        result.diagnostics["attempts"] = attempt
        remaining = runtime.request_timeout(deadline)
        if remaining <= 0:
            result.status = "skipped"
            result.skipped_reason = "article deadline exceeded"
            record(result.status, attempt=attempt, reason=result.skipped_reason)
            return result
        record("attempt_started", attempt=attempt, provider=provider.get("provider"), model=provider.get("model"))
        try:
            raw = _request_once(prompt if attempt == 1 else prompt + "\nReturn a shorter complete article.", provider, remaining)
            article = _parse_json(raw)
            validation = validate_article(article, dossier, spec)
            result.diagnostics = {"attempts": attempt, "validation": validation.to_dict(), "dossier_hash": dossier_hash}
            if validation.valid:
                article.setdefault("event_id", obj.object_id)
                article.setdefault("research_evidence_level", obj.evidence_level)
                article.setdefault("format", spec["format"])
                result.article = article
                result.status = "completed"
                result.stages_run = ["bounded_writer", "local_validation"]
                if cached_path:
                    cached_path.parent.mkdir(parents=True, exist_ok=True)
                    cached_path.write_text(json.dumps({
                        "object_id": obj.object_id,
                        "depth": depth,
                        "dossier_hash": dossier_hash,
                        "article": article,
                    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                record("completed", attempt=attempt, validation=validation.to_dict(),
                       output_artifact=str(cached_path) if cached_path else "")
                result.seconds = round(time.monotonic() - started, 1)
                return result
            last_error = "; ".join(validation.codes)
            record("validation_failed", attempt=attempt, codes=validation.codes)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"[:240]
            record("attempt_failed", attempt=attempt, error=last_error)
            if attempt >= runtime.max_attempts_per_article or not _retryable_error(exc):
                break
    result.status = "failed"
    result.errors = [last_error or "generation failed"]
    result.stages_run = ["bounded_writer", "local_validation"]
    result.seconds = round(time.monotonic() - started, 1)
    return result


def write_all(
    objects: Sequence[IntelligenceObject],
    *,
    provider: dict[str, Any] | None = None,
    budget: Any = None,
    deadline_s: float = DEFAULT_EDITION_BUDGET_S,
    article_budget_s: float = DEFAULT_ARTICLE_BUDGET_S,
    verbose: bool = True,
    state_dir: Path | None = None,
    run_id: str = "",
) -> tuple[list[DraftResult], GenerationReport]:
    started = time.monotonic()
    report = GenerationReport(requested=len(objects))
    results: list[DraftResult] = []
    if not provider or not provider.get("api_key"):
        report.failed = len(objects)
        report.results = [DraftResult(object_id=o.object_id, title=o.title, status="failed",
                                      errors=["no writing provider configured"]).to_dict() for o in objects]
        return results, report

    runtime = RuntimeBudget.start(deadline_s, article_budget_s=article_budget_s)
    deadline = runtime.deadline
    for index, obj in enumerate(objects, start=1):
        remaining = runtime.remaining()
        if remaining <= 0 or remaining < min(runtime.article_budget_s, runtime.attempt_timeout_s):
            result = DraftResult(object_id=obj.object_id, title=obj.title, sector=obj.primary_sector,
                                 depth=obj.recommended_depth, status="skipped",
                                 skipped_reason="edition generation window closed")
        else:
            article_deadline = runtime.article_deadline()
            result = write_one(obj, provider=provider,
                               deadline=article_deadline,
                               runtime=RuntimeBudget(
                                   started=time.monotonic(), deadline=article_deadline,
                                   article_budget_s=runtime.article_budget_s,
                                   attempt_timeout_s=runtime.attempt_timeout_s,
                                   max_attempts_per_article=runtime.max_attempts_per_article,
                                   max_total_attempts=runtime.max_total_attempts,
                               ),
                               state_dir=state_dir, run_id=run_id)
        results.append(result)
        if verbose:
            print(f"    [v4 {index}/{len(objects)}] {result.status}: {result.title[:58]} ({result.seconds:.1f}s)", flush=True)
        if result.status == "completed":
            report.written += 1
        elif result.status == "skipped":
            report.skipped += 1
        else:
            report.failed += 1
        attempts = int(result.diagnostics.get("attempts", 0))
        report.attempts += attempts
        name = str(provider.get("provider") or "unknown")
        report.provider_attempts[name] = report.provider_attempts.get(name, 0) + attempts
        if report.attempts >= MAX_TOTAL_ATTEMPTS:
            break
    report.elapsed_seconds = round(time.monotonic() - started, 2)
    report.results = [r.to_dict() for r in results]
    return results, report


def summarise(report: GenerationReport) -> str:
    return (f"  v4 wrote {report.written}/{report.requested} in {report.elapsed_seconds:.0f}s "
            f"({report.attempts} bounded provider attempts; {report.failed} failed; "
            f"{report.skipped} skipped)")
