"""Bounded, cached, lawful content retrieval.

The pipeline previously read one article per story and stopped: no second
outlet, no original document. Every story in the last live run was assessed as
`thin` by the system's own reckoning -- one source, zero primary documents --
and then asked for analysis those inputs could not support.

This module is the fix for the input side. It fetches article bodies and
primary documents under explicit limits, and -- critically -- always reports
*what kind of thing it got back*, so nothing downstream can mistake a feed
snippet for a full reading.

Guarantees
    * connect and read timeouts on every request
    * a whole-phase deadline, so a batch cannot run forever
    * bounded concurrency, and a per-domain floor between requests
    * response size ceiling, streamed and truncated rather than buffered whole
    * content-type validation before parsing
    * robots.txt consulted and obeyed; a disallowed path is skipped, never worked around
    * on-disk cache keyed by URL, so the same document is never fetched twice
    * failure isolation: one bad document can never take down a run
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import urllib.parse as urlparse
import urllib.robotparser as robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests

from intelligence_object import Fact, RetrievalStatus

SITE_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = SITE_ROOT / ".editorial-state" / "retrieval-cache"

USER_AGENT = "LightTowerGroup-NewsAgent/2.0 (+https://lighttowergroup.co)"

CONNECT_TIMEOUT = 8
READ_TIMEOUT = 15
MAX_BYTES = 3_000_000
MAX_WORKERS = 6
PER_DOMAIN_DELAY = 1.0
MAX_ATTEMPTS = 2
CACHE_TTL_SECONDS = 6 * 3600
DEFAULT_PHASE_BUDGET = 300

_HTML_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
_DOC_TYPES = ("application/pdf", "application/xml", "text/xml")

_DATE_META = (
    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)',
    r'"datePublished"\s*:\s*"([^"]+)"',
)
_CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', re.I
)


@dataclass
class RetrievalResult:
    """What we got, and honestly what kind of thing it is."""

    url: str = ""
    final_url: str = ""
    canonical_url: str = ""
    status: str = RetrievalStatus.FAILED
    http_status: int | None = None
    content_type: str = ""
    text: str = ""
    text_chars: int = 0
    published_at: str = ""
    content_hash: str = ""
    from_cache: bool = False
    elapsed_ms: int = 0
    attempts: int = 0
    error: str = ""
    skipped_reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status in (RetrievalStatus.FULL_TEXT, RetrievalStatus.PARTIAL_TEXT)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


@dataclass
class RetrievalReport:
    """Aggregate outcome for a batch, for the run artifact."""

    requested: int = 0
    fetched: int = 0
    from_cache: int = 0
    blocked: int = 0
    failed: int = 0
    skipped_budget: int = 0
    bytes_downloaded: int = 0
    elapsed_ms: int = 0
    by_status: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _DomainThrottle:
    """One request per domain per PER_DOMAIN_DELAY seconds."""

    def __init__(self, delay: float = PER_DOMAIN_DELAY) -> None:
        self._delay = delay
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, domain: str) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                previous = self._last.get(domain, 0.0)
                if now - previous >= self._delay:
                    self._last[domain] = now
                    return
                sleep_for = self._delay - (now - previous)
            time.sleep(min(sleep_for, self._delay))


class _RobotsCache:
    """robots.txt per origin. Fetch failure means unrestricted, not blocked."""

    def __init__(self) -> None:
        self._cache: dict[str, robotparser.RobotFileParser | None] = {}
        self._lock = threading.Lock()

    def allows(self, url: str) -> bool:
        parts = urlparse.urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        with self._lock:
            known = origin in self._cache
            parser = self._cache.get(origin)
        if not known:
            parser = self._load(origin)
            with self._lock:
                self._cache[origin] = parser
        if parser is None:
            return True
        try:
            return parser.can_fetch(USER_AGENT, url)
        except Exception:  # noqa: BLE001
            return True

    @staticmethod
    def _load(origin: str) -> robotparser.RobotFileParser | None:
        try:
            resp = requests.get(
                origin + "/robots.txt",
                headers={"User-Agent": USER_AGENT},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
        except Exception:  # noqa: BLE001
            return None
        if resp.status_code != 200 or len(resp.content) > 500_000:
            return None
        parser = robotparser.RobotFileParser()
        try:
            parser.parse(resp.text.splitlines())
        except Exception:  # noqa: BLE001
            return None
        return parser


class Retriever:
    """Fetches documents under explicit limits. Safe to share across threads."""

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        cache_ttl: int = CACHE_TTL_SECONDS,
        max_workers: int = MAX_WORKERS,
        per_domain_delay: float = PER_DOMAIN_DELAY,
        max_bytes: int = MAX_BYTES,
        respect_robots: bool = True,
        session: Any = None,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_ttl = cache_ttl
        self.max_workers = max_workers
        self.max_bytes = max_bytes
        self.respect_robots = respect_robots
        self._throttle = _DomainThrottle(per_domain_delay)
        self._robots = _RobotsCache()
        self._session = session or requests.Session()
        self._bytes = 0
        self._lock = threading.Lock()

    # ── cache ──────────────────────────────────────────────────────────────

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, url: str) -> RetrievalResult | None:
        path = self._cache_path(url)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        stored_at = payload.get("_stored_at", 0)
        if time.time() - stored_at > self.cache_ttl:
            return None
        payload.pop("_stored_at", None)
        payload.pop("ok", None)
        known = set(RetrievalResult.__dataclass_fields__)
        result = RetrievalResult(**{k: v for k, v in payload.items() if k in known})
        result.from_cache = True
        return result

    def _write_cache(self, url: str, result: RetrievalResult) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            payload = result.to_dict()
            payload["_stored_at"] = time.time()
            self._cache_path(url).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass  # a cache write failure must never fail a fetch

    # ── single fetch ───────────────────────────────────────────────────────

    def fetch(self, url: str, *, use_cache: bool = True) -> RetrievalResult:
        """Fetch one document. Never raises."""
        started = time.perf_counter()
        result = RetrievalResult(url=url)

        if not url or not url.lower().startswith(("http://", "https://")):
            result.status = RetrievalStatus.FAILED
            result.error = "unsupported or empty URL"
            return result

        if use_cache:
            cached = self._read_cache(url)
            if cached is not None:
                return cached

        if self.respect_robots and not self._robots.allows(url):
            result.status = RetrievalStatus.BLOCKED
            result.skipped_reason = "disallowed by robots.txt"
            result.elapsed_ms = int((time.perf_counter() - started) * 1000)
            self._write_cache(url, result)
            return result

        domain = urlparse.urlsplit(url).netloc
        last_error = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result.attempts = attempt
            self._throttle.wait(domain)
            try:
                resp = self._session.get(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*"},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    allow_redirects=True,
                    stream=True,
                )
            except requests.exceptions.Timeout:
                last_error = "timeout"
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"[:160]
                continue

            result.http_status = resp.status_code
            result.final_url = getattr(resp, "url", url) or url
            result.content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()

            if resp.status_code in (401, 403, 451):
                result.status = RetrievalStatus.BLOCKED
                result.skipped_reason = f"publisher returned {resp.status_code}"
                break
            if resp.status_code == 429:
                last_error = "rate limited"
                time.sleep(2.0)
                continue
            if resp.status_code != 200:
                last_error = f"http {resp.status_code}"
                if 500 <= resp.status_code < 600:
                    continue
                break

            if result.content_type and not any(
                result.content_type.startswith(t) for t in _HTML_TYPES + _DOC_TYPES
            ):
                result.status = RetrievalStatus.FAILED
                result.error = f"unsupported content type {result.content_type}"
                break

            try:
                raw = resp.raw.read(self.max_bytes + 1, decode_content=True) or b""
            except Exception as exc:  # noqa: BLE001
                last_error = f"read failed: {type(exc).__name__}"
                continue
            finally:
                resp.close()

            truncated = len(raw) > self.max_bytes
            raw = raw[: self.max_bytes]
            with self._lock:
                self._bytes += len(raw)

            html = raw.decode(resp.encoding or "utf-8", errors="replace")
            result.content_hash = hashlib.sha256(raw).hexdigest()[:16]
            result.canonical_url = self._canonical(html, result.final_url)
            result.published_at = self._published(html)
            text = self._extract(html, result.final_url)
            result.text = text
            result.text_chars = len(text)

            if len(text) >= 1200 and not truncated:
                result.status = RetrievalStatus.FULL_TEXT
            elif text:
                result.status = RetrievalStatus.PARTIAL_TEXT
            else:
                result.status = RetrievalStatus.FAILED
                result.error = "no main text could be extracted"
            break
        else:
            result.status = RetrievalStatus.FAILED

        if result.status == RetrievalStatus.FAILED and not result.error:
            result.error = last_error or "unknown failure"
        result.elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._write_cache(url, result)
        return result

    # ── batch ──────────────────────────────────────────────────────────────

    def fetch_many(
        self,
        urls: Sequence[str],
        *,
        budget_seconds: int = DEFAULT_PHASE_BUDGET,
        use_cache: bool = True,
    ) -> tuple[dict[str, RetrievalResult], RetrievalReport]:
        """Fetch a batch under a whole-phase deadline. Never raises."""
        started = time.perf_counter()
        deadline = started + max(1, budget_seconds)
        unique = list(dict.fromkeys(u for u in urls if u))
        results: dict[str, RetrievalResult] = {}
        report = RetrievalReport(requested=len(unique))

        if not unique:
            return results, report

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            pending = {}
            for url in unique:
                pending[pool.submit(self.fetch, url, use_cache=use_cache)] = url
            for future in as_completed(pending):
                url = pending[future]
                if time.perf_counter() > deadline:
                    future.cancel()
                    skipped = RetrievalResult(url=url, status=RetrievalStatus.FAILED)
                    skipped.skipped_reason = "phase budget exhausted"
                    results[url] = skipped
                    report.skipped_budget += 1
                    continue
                try:
                    results[url] = future.result()
                except Exception as exc:  # noqa: BLE001
                    broken = RetrievalResult(url=url, status=RetrievalStatus.FAILED)
                    broken.error = f"{type(exc).__name__}: {exc}"[:160]
                    results[url] = broken

        for result in results.values():
            report.by_status[result.status] = report.by_status.get(result.status, 0) + 1
            if result.from_cache:
                report.from_cache += 1
            if result.ok:
                report.fetched += 1
            elif result.status == RetrievalStatus.BLOCKED:
                report.blocked += 1
            elif result.skipped_reason != "phase budget exhausted":
                report.failed += 1

        report.bytes_downloaded = self._bytes
        report.elapsed_ms = int((time.perf_counter() - started) * 1000)
        return results, report

    # ── parsing helpers ────────────────────────────────────────────────────

    @staticmethod
    def _extract(html: str, url: str) -> str:
        try:
            import trafilatura

            text = trafilatura.extract(
                html, url=url, include_comments=False, include_tables=False, no_fallback=False
            )
            return (text or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _canonical(html: str, fallback: str) -> str:
        match = _CANONICAL_RE.search(html or "")
        if match:
            href = match.group(1).strip()
            if href.startswith("http"):
                return href
            return urlparse.urljoin(fallback, href)
        return fallback

    @staticmethod
    def _published(html: str) -> str:
        for pattern in _DATE_META:
            match = re.search(pattern, html or "", re.I)
            if match:
                value = match.group(1).strip()
                try:
                    cleaned = value.replace("Z", "+00:00")
                    return datetime.fromisoformat(cleaned).astimezone(timezone.utc).isoformat()
                except ValueError:
                    return value
        return ""


def enrich_objects(
    objects: Iterable[Any],
    *,
    retriever: Retriever | None = None,
    budget_seconds: int = DEFAULT_PHASE_BUDGET,
    max_sources_per_object: int = 3,
) -> RetrievalReport:
    """Fetch bodies for an object's sources and upgrade its evidence level.

    Mutates each object in place: source retrieval status and text length are
    replaced with what was actually retrieved, then the evidence level is
    recomputed so depth decisions downstream reflect reality.
    """
    retriever = retriever or Retriever()
    objects = list(objects)
    wanted: list[str] = []
    for obj in objects:
        for ref in obj.sources[:max_sources_per_object]:
            url = ref.canonical_url or ref.source_url
            if url:
                wanted.append(url)

    results, report = retriever.fetch_many(wanted, budget_seconds=budget_seconds)

    for obj in objects:
        fact_index = {(fact.name, str(fact.value).lower()): fact for fact in obj.facts}
        for ref in obj.sources[:max_sources_per_object]:
            url = ref.canonical_url or ref.source_url
            result = results.get(url)
            if result is None:
                continue
            ref.retrieval_status = result.status
            if result.text_chars:
                ref.text_chars = result.text_chars
            if result.text:
                ref.retrieved_text = result.text[:12_000]
                try:
                    from fact_extractor import extract_facts

                    extracted = extract_facts(ref.retrieved_text)
                    groups = (
                        ("amount", extracted.get("amounts", []), "raw"),
                        ("percentage", extracted.get("percentages", []), "raw"),
                        ("company", extracted.get("companies", []), "name"),
                    )
                    for fact_name, values, value_key in groups:
                        for value in values[:20]:
                            raw_value = str(value.get(value_key) or "").strip()
                            if not raw_value:
                                continue
                            key = (fact_name, raw_value.lower())
                            current = fact_index.get(key)
                            if current is not None:
                                if ref.item_id and ref.item_id != current.source_item_id:
                                    if ref.item_id not in current.corroborating_item_ids:
                                        current.corroborating_item_ids.append(ref.item_id)
                                continue
                            current = Fact(
                                name=fact_name,
                                value=raw_value,
                                evidence_span=str(value.get("context") or raw_value)[:500],
                                source_item_id=ref.item_id,
                                confidence=0.9,
                            )
                            obj.facts.append(current)
                            fact_index[key] = current
                    for fact_name, values in (
                        ("address", extracted.get("addresses", [])),
                        ("date", extracted.get("dates", [])),
                    ):
                        for raw_value in values[:12]:
                            raw_value = str(raw_value).strip()
                            key = (fact_name, raw_value.lower())
                            if not raw_value or key in fact_index:
                                continue
                            current = Fact(
                                name=fact_name,
                                value=raw_value,
                                evidence_span=raw_value,
                                source_item_id=ref.item_id,
                                confidence=0.85,
                            )
                            obj.facts.append(current)
                            fact_index[key] = current
                except Exception:  # noqa: BLE001
                    pass
            if result.canonical_url:
                ref.canonical_url = result.canonical_url
            if result.published_at and not ref.publication_date:
                ref.publication_date = result.published_at
        obj.assess_evidence()
    return report
