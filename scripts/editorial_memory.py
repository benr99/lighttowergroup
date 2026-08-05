"""What we have already seen, chosen and published.

Novelty was a hardcoded 7 for every story, because nothing in v3 remembered
yesterday. That was harmless while the system published nothing. The day it
starts publishing on its own it becomes serious: it will re-run stories it
already covered, and rank follow-ups above genuinely new events.

`.editorial-state/event-memory.json` held 262 entries and stopped being written
on 2026-07-30 -- the day v2 replaced the path that maintained it. This replaces
that with a store the v3 pipeline reads and writes, and which answers one
question per story:

    new              never seen
    new_stage        same parties, materially different figure or status
    material_update  we covered this and something substantive changed
    minor_follow_up  we covered this and little has changed
    duplicate        we saw this today or yesterday and did not run it
    already_published we published this

Matching deliberately reuses the same signals as same-day clustering -- shared
amounts, entity overlap, headline tokens -- so "the same story" means the same
thing within a day and across weeks.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from event_clustering import _Signature, _jaccard
from intelligence_object import IntelligenceObject, NoveltyState

SITE_ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = SITE_ROOT / ".editorial-state" / "editorial-memory.json"
MANIFEST_PATH = SITE_ROOT / "insights.json"

#: How far back a story can match. Beyond this a recurring theme is legitimately
#: news again -- CMBS distress in August is not the same story as in March.
LOOKBACK_DAYS = 45

#: Same-story confidence. Above this two records describe one event.
MATCH_THRESHOLD = 0.58

#: A figure moving by more than this is a new stage, not a repeat.
MATERIAL_CHANGE = 0.15

RETENTION_DAYS = 120

_MONEY = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|bn|b|million|mm|m|trillion|tn|k)?\b", re.I
)
_MULT = {"trillion": 1e12, "tn": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9,
         "million": 1e6, "mm": 1e6, "m": 1e6, "k": 1e3, None: 1.0, "": 1.0}

_STATUS = (
    ("closed", re.compile(r"\b(?:closed|completed|finaliz\w+|sealed)\b", re.I)),
    ("agreed", re.compile(r"\b(?:agrees?|agreed|accepts?|accepted|signs?|signed)\b", re.I)),
    ("launched", re.compile(r"\b(?:launch\w+|opens?|begins?|breaks? ground)\b", re.I)),
    ("proposed", re.compile(r"\b(?:propos\w+|plans?|explor\w+|in talks|considering)\b", re.I)),
)


def _amounts(text: str) -> list[float]:
    out = []
    for raw, unit in _MONEY.findall(text or ""):
        try:
            out.append(float(raw.replace(",", "")) * _MULT.get((unit or "").lower(), 1.0))
        except ValueError:
            continue
    return out


def _status_of(text: str) -> str:
    for name, pattern in _STATUS:
        if pattern.search(text or ""):
            return name
    return ""


@dataclass
class MemoryRecord:
    """One event we have encountered, and what became of it."""

    event_key: str = ""
    title: str = ""
    primary_sector: str = ""
    first_seen: str = ""
    last_seen: str = ""
    times_seen: int = 0
    selected: bool = False
    published: bool = False
    published_slug: str = ""
    published_at: str = ""
    largest_amount: float = 0.0
    status: str = ""
    source_urls: list[str] = field(default_factory=list)
    angles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NoveltyVerdict:
    state: str = NoveltyState.NEW
    score: float = 9.0
    matched_key: str = ""
    reason: str = ""
    changes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EditorialMemory:
    """Reads and writes what the desk has already covered."""

    def __init__(self, path: Path | None = None, *, lookback_days: int = LOOKBACK_DAYS) -> None:
        self.path = path or MEMORY_PATH
        self.lookback_days = lookback_days
        self.records: dict[str, MemoryRecord] = {}
        self._load()

    # ── persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for raw in payload.get("events", []):
            known = set(MemoryRecord.__dataclass_fields__)
            record = MemoryRecord(**{k: v for k, v in raw.items() if k in known})
            if record.event_key:
                self.records[record.event_key] = record

    def save(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
        kept = [r for r in self.records.values() if (r.last_seen or "") >= cutoff or r.published]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "count": len(kept),
                        "events": [r.to_dict() for r in sorted(kept, key=lambda x: x.last_seen, reverse=True)],
                    },
                    indent=1,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def seed_from_manifest(self, manifest_path: Path | None = None, *, limit: int = 400) -> int:
        """Treat already-published articles as covered, so day one has memory."""
        path = manifest_path or MANIFEST_PATH
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        added = 0
        for entry in records[:limit]:
            title = str(entry.get("title") or "")
            if not title:
                continue
            key = self._key(title, entry.get("category", ""))
            if key in self.records:
                continue
            self.records[key] = MemoryRecord(
                event_key=key,
                title=title,
                primary_sector=str(entry.get("category") or ""),
                first_seen=str(entry.get("date") or ""),
                last_seen=str(entry.get("date") or ""),
                times_seen=1,
                selected=True,
                published=True,
                published_slug=str(entry.get("slug") or ""),
                published_at=str(entry.get("date") or ""),
                largest_amount=max(_amounts(title), default=0.0),
                status=_status_of(title),
            )
            added += 1
        return added

    # ── matching ───────────────────────────────────────────────────────────

    @staticmethod
    def _key(title: str, sector: str = "") -> str:
        import hashlib

        basis = re.sub(r"[^a-z0-9 ]", " ", f"{sector} {title}".lower())
        basis = " ".join(sorted(w for w in basis.split() if len(w) > 3))
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    def _recent(self) -> list[MemoryRecord]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.lookback_days)).isoformat()
        return [r for r in self.records.values() if (r.last_seen or "") >= cutoff or r.published]

    @staticmethod
    def _across_time(a: _Signature, b: _Signature) -> float:
        """Same-event similarity for records days apart.

        Deliberately NOT `event_clustering.similarity`. That penalises
        conflicting monetary amounts by nearly half, which is right within one
        day -- two different figures mean two different deals. Across time it is
        exactly backwards: a loan that moved from $2.5bn to $3.3bn is the same
        event reaching a new stage, and that is the case we most need to catch.
        Matching therefore rests on parties and wording, and the amount is read
        afterwards as evidence of movement rather than of difference.
        """
        token_sim = _jaccard(a.tokens, b.tokens)
        entity_sim = _jaccard(a.entities, b.entities)
        score = 0.6 * token_sim + 0.4 * entity_sim
        if a.sector and b.sector and a.sector != b.sector:
            score *= 0.85
        return min(1.0, score)

    def _best_match(self, obj: IntelligenceObject) -> tuple[MemoryRecord | None, float]:
        probe = _Signature.build(
            type("D", (), {
                "headline": obj.title,
                "raw_summary": obj.what_happened,
                "primary_sector": obj.primary_sector,
            })()
        )
        best, best_score = None, 0.0
        for record in self._recent():
            candidate = _Signature.build(
                type("D", (), {
                    "headline": record.title,
                    "raw_summary": "",
                    "primary_sector": record.primary_sector,
                })()
            )
            score = self._across_time(probe, candidate)
            if score > best_score:
                best, best_score = record, score
        return best, best_score

    def assess(self, obj: IntelligenceObject) -> NoveltyVerdict:
        """How new is this, given what we have already covered?"""
        match, score = self._best_match(obj)
        if match is None or score < MATCH_THRESHOLD:
            return NoveltyVerdict(NoveltyState.NEW, 9.0, "", "not previously seen")

        changes: list[str] = []
        amount_now = max(_amounts(f"{obj.title} {obj.what_happened}"), default=0.0)
        status_now = _status_of(f"{obj.title} {obj.what_happened}")

        if amount_now and match.largest_amount:
            delta = abs(amount_now - match.largest_amount) / max(match.largest_amount, 1.0)
            if delta > MATERIAL_CHANGE:
                changes.append(
                    f"figure moved from ${match.largest_amount:,.0f} to ${amount_now:,.0f}"
                )
        elif amount_now and not match.largest_amount:
            changes.append(f"a figure is now disclosed (${amount_now:,.0f})")

        if status_now and match.status and status_now != match.status:
            changes.append(f"status moved from {match.status} to {status_now}")

        if match.published:
            if changes:
                return NoveltyVerdict(
                    NoveltyState.NEW_STAGE, 7.0, match.event_key,
                    "we published this and it has moved on", changes,
                )
            return NoveltyVerdict(
                NoveltyState.ALREADY_PUBLISHED, 1.0, match.event_key,
                f"already published as {match.published_slug or 'an earlier article'}",
            )

        if changes:
            return NoveltyVerdict(
                NoveltyState.MATERIAL_UPDATE, 6.0, match.event_key,
                "seen before, and something substantive changed", changes,
            )
        if match.times_seen >= 2:
            return NoveltyVerdict(
                NoveltyState.DUPLICATE, 1.0, match.event_key,
                f"seen {match.times_seen} times without changing",
            )
        return NoveltyVerdict(
            NoveltyState.MINOR_FOLLOW_UP, 3.0, match.event_key,
            "seen before with nothing substantive added",
        )

    def apply(self, objects: Iterable[IntelligenceObject]) -> dict[str, int]:
        """Set novelty on each object and return a tally of the verdicts."""
        tally: dict[str, int] = {}
        for obj in objects:
            verdict = self.assess(obj)
            obj.novelty_state = verdict.state
            obj.novelty_score = verdict.score
            obj.material_changes = list(verdict.changes)
            if verdict.matched_key:
                obj.prior_object_ids = [verdict.matched_key]
                prior = self.records.get(verdict.matched_key)
                if prior and prior.published_slug:
                    obj.prior_published_slugs = [prior.published_slug]
            tally[verdict.state] = tally.get(verdict.state, 0) + 1
        return tally

    # ── recording ──────────────────────────────────────────────────────────

    def observe(self, objects: Sequence[IntelligenceObject]) -> None:
        """Record that we saw these today, and which we chose."""
        now = datetime.now(timezone.utc).isoformat()
        for obj in objects:
            key = obj.prior_object_ids[0] if obj.prior_object_ids else self._key(
                obj.title, obj.primary_sector
            )
            record = self.records.get(key)
            if record is None:
                record = MemoryRecord(
                    event_key=key, title=obj.title,
                    primary_sector=obj.primary_sector, first_seen=now,
                )
                self.records[key] = record
            record.last_seen = now
            record.times_seen += 1
            record.selected = record.selected or bool(obj.selected)
            amount = max(_amounts(f"{obj.title} {obj.what_happened}"), default=0.0)
            if amount:
                record.largest_amount = max(record.largest_amount, amount)
            status = _status_of(f"{obj.title} {obj.what_happened}")
            if status:
                record.status = status
            for source in obj.sources[:3]:
                url = source.canonical_url or source.source_url
                if url and url not in record.source_urls:
                    record.source_urls.append(url)
            record.source_urls = record.source_urls[:8]

    def mark_published(self, obj: IntelligenceObject, slug: str) -> None:
        key = obj.prior_object_ids[0] if obj.prior_object_ids else self._key(
            obj.title, obj.primary_sector
        )
        record = self.records.setdefault(
            key, MemoryRecord(event_key=key, title=obj.title, primary_sector=obj.primary_sector)
        )
        record.published = True
        record.published_slug = slug
        record.published_at = datetime.now(timezone.utc).isoformat()
        record.selected = True
        record.last_seen = record.last_seen or record.published_at
        # Without these, re-seeing the identical story reads as "a figure is now
        # disclosed" and comes back as a new stage instead of already published.
        amount = max(_amounts(f"{obj.title} {obj.what_happened}"), default=0.0)
        if amount:
            record.largest_amount = max(record.largest_amount, amount)
        status = _status_of(f"{obj.title} {obj.what_happened}")
        if status:
            record.status = status

    def report(self) -> dict[str, Any]:
        published = sum(1 for r in self.records.values() if r.published)
        return {
            "events_remembered": len(self.records),
            "published": published,
            "seen_but_not_run": len(self.records) - published,
            "lookback_days": self.lookback_days,
        }
