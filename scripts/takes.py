#!/usr/bin/env python3
"""Quick Takes: a five-line, link-free LinkedIn post for every story worth one.

For each published story the writer drafts three candidate takes, each built on a
different formula, from that story's verified sentences only. Every line is checked:

    fact lines    against the story's verified sentences (figures and names by code,
                  meaning by both reasoning passes), so nothing is added, rounded or
                  stripped of its qualifier or attribution
    Ben's read    the opinion rules (first person or framed, rests on the facts, no
                  motives, no predictions as fact, no sides) plus the independent review
    the kicker    a reaction line: no facts, numbers or names, no implied claims

A failed line is deleted. A candidate survives with its hook (a fact) and at least two
lines; the best survivor is the take, the others are alternate angles. Takes go to the
public feed file ``takes.json`` (newest first) that the Intelligence page reads and the
morning email draws from. Nothing is posted anywhere: Ben copies and posts.

    python takes.py <run folder>    # writes takes.json into the run folder (preview)
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from linkedin_post import SITE, Story, load_stories

LLM = Callable[[str, str], str]

TAKES_VERSION = "takes-1"
MAX_LINES = 5
MAX_CHARS = 450
MIN_FACTS = 3          # a story needs this many verified sentences to carry a take
KEEP_DAYS = 90         # the feed keeps this much history
MAX_FEED = 800
WORKERS = 6

FORMULAS = {
    "The Number That Doesn't Fit": "a figure that contradicts the obvious reading",
    "Follow the Money": "who lends, who pays, who carries the risk",
    "The Clock": "a maturity, deadline or vote that drives everything (only if the facts give the date)",
    "The Second-Order Effect": "the obvious winner, then the less obvious consequence",
    "History Rhymes": "today's story next to a pattern a seasoned reader recognises, offered as a reading",
    "Translate the Jargon": "a Fed, banking or capital-stack term turned into what it means for a borrower",
    "The Quiet Signal": "a small deal that may be an early sign, offered carefully",
    "Two Numbers, One Story": "two figures side by side that tell the story with little commentary",
}

SYSTEM = (
    "You are Ben Rohr, a New York commercial real estate capital advisor, writing short LinkedIn takes. "
    "You read like the smartest person at the table who is also the funniest: an economist's eye, a "
    "dealmaker's instincts, a historian's memory, and the restraint to say it in five lines. Wise, not loud. "
    "Dry wit, used sparingly. Generous: the reader learns something. Always a point of view. Never a press "
    "release. You never state a fact that is not in the verified sentences you are given."
)

PROMPT = """Write three candidate LinkedIn takes about ONE story, each built on a DIFFERENT formula. Return JSON only.

STORY: {title}
VERIFIED SENTENCES (the only facts you may use; each already passed a fact check):
{facts}
{reads}
FORMULAS (pick three that fit this story):
{formulas}

EACH TAKE: at most 5 lines and about 450 characters in total. Each line is one or two short sentences. Every line has a "kind":
- "fact": restates verified sentences, tighter. Every number, name, place, date and relationship must be in them. Keep every qualifier and attribution ("about", "per the WSJ", "agreed to", "expects"). No arithmetic: no differences, ratios, totals or paybacks the sentences do not state. No causes or rankings they do not state.
- "read": Ben's view, in the first person or plainly framed ("I read this as", "my guess", "may be"). It rests on the facts in this take. Never a motive ("wants", "is trying to", "betting that"), never a prediction stated as fact, never a side in a dispute, never "the market is..." as fact.
- "kicker": a short closing line that sticks: dry wit, a question for the reader's own deals, or a callback. It states no fact: no numbers, no names, no implied deadline or outcome. Never at anyone's expense.

SHAPE: line 1 is the hook, a "fact" with the most surprising number. Then facts that make it matter, then at most one "read", then at most one "kicker". Three lines that land beat five that sag.
NEVER: links, hashtags, emoji, "Here's why", "Let that sink in", "Read that again", "Hot take", "unpopular opinion", "game-changer", "landscape", "navigating", "buckle up".

Return exactly:
{{"takes":[{{"formula":"...","lines":[{{"kind":"fact","text":"..."}},{{"kind":"read","text":"..."}},{{"kind":"kicker","text":"..."}}]}}]}}"""


@dataclass
class Take:
    id: str
    object_id: str
    date: str
    published_at: str
    sector: str
    title: str
    article_url: str
    formula: str
    text: str
    lines: list[dict[str, str]]
    alternates: list[dict[str, Any]] = field(default_factory=list)
    rank: int = 0
    score: float = 0.0  # the story's importance score; ranks takes across a day's runs
    dropped: list[str] = field(default_factory=list)

    def to_feed(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("dropped")
        data["chars"] = len(self.text)
        return data


def new_york_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:  # noqa: BLE001  (no tz database; a 7 am Eastern run is the same date either way)
        return datetime.now(timezone.utc) - timedelta(hours=4)


def _parse(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("invalid_json_object")
    return value


def _clean(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().strip('"')


_BANNED = re.compile(r"(https?://|www\.|#\w|let that sink in|read that again|hot take|unpopular opinion|"
                     r"game[- ]changer|landscape|navigating|buckle up|here's why)", re.I)


def _check_lines(story: Story, candidates: list[list[dict[str, str]]], checker: LLM) -> list[list[tuple[bool, str]]]:
    """Verdicts for every line of every candidate, in two batched passes (facts, then views)."""
    from claim_verifier import FACT, Item, verify_unquoted
    from voice_gate import TAKE, VOICE, VoiceItem, check_voice_item, run_rubric

    verdicts: list[list[tuple[bool, str]]] = [[(False, "unchecked")] * len(c) for c in candidates]
    facts_by_id = {f"f{i}": f for i, f in enumerate(story.facts)}
    fact_items, fact_pos, view_items, view_pos = [], [], [], []
    for ci, lines in enumerate(candidates):
        for li, line in enumerate(lines):
            text, kind = line["text"], line["kind"]
            if _BANNED.search(text):
                verdicts[ci][li] = (False, "banned phrase, link or hashtag")
            elif kind == "fact":
                fact_items.append(Item(id=f"c{ci}l{li}", kind=FACT, text=text))
                fact_pos.append((ci, li))
            elif kind in ("read", "kicker"):
                item = VoiceItem(id=f"c{ci}l{li}", kind=TAKE if kind == "read" else VOICE, text=text,
                                 because=list(facts_by_id))
                check_voice_item(item, facts_by_id, [], [])
                if item.problems:
                    verdicts[ci][li] = (False, "; ".join(item.problems))
                else:
                    view_items.append(item)
                    view_pos.append((ci, li))
            else:
                verdicts[ci][li] = (False, f"unknown line kind {kind!r}")
    source = f"{story.title}\n" + "\n".join(story.facts)
    try:
        verify_unquoted(fact_items, source, " ".join(story.facts), checker)
        for item, (ci, li) in zip(fact_items, fact_pos):
            verdicts[ci][li] = (item.ok, "" if item.ok else item.reason)
    except Exception as exc:  # noqa: BLE001  (fail closed)
        for ci, li in fact_pos:
            verdicts[ci][li] = (False, f"fact check unavailable: {type(exc).__name__}")
    try:
        run_rubric(checker, facts_by_id, view_items)
        for item, (ci, li) in zip(view_items, view_pos):
            verdicts[ci][li] = (item.ok, "" if item.ok else item.reason)
    except Exception as exc:  # noqa: BLE001
        for ci, li in view_pos:
            verdicts[ci][li] = (False, f"opinion review unavailable: {type(exc).__name__}")
    return verdicts


def _assemble(lines: list[dict[str, str]], verdicts: list[tuple[bool, str]]) -> tuple[list[dict[str, str]], list[str]]:
    kept, dropped = [], []
    for line, (ok, why) in zip(lines, verdicts):
        if ok:
            kept.append(line)
        else:
            dropped.append(f"[{line['kind']}] {line['text']} <- {why}")
    reads = [l for l in kept if l["kind"] == "read"][:1]
    kickers = [l for l in kept if l["kind"] == "kicker"][:1]
    facts = [l for l in kept if l["kind"] == "fact"]
    # Facts first (the hook leads), then one read, then one kicker; at most five lines.
    ordered = [l for l in kept if l in facts or l in reads or l in kickers]
    while len(ordered) > MAX_LINES:
        extra_fact = next((l for l in reversed(ordered) if l["kind"] == "fact" and l is not facts[0]), None)
        ordered.remove(extra_fact if extra_fact else ordered[-1])
    while len("\n".join(l["text"] for l in ordered)) > MAX_CHARS and len(ordered) > 2:
        removable = next((l for l in reversed(ordered) if l["kind"] == "fact" and l is not ordered[0]), ordered[-1])
        ordered.remove(removable)
    return ordered, dropped


def _score(lines: list[dict[str, str]]) -> float:
    if len(lines) < 2 or lines[0]["kind"] != "fact":
        return -1.0
    score = len(lines)
    score += 1.5 if any(l["kind"] == "read" for l in lines) else 0
    score += 1.0 if any(l["kind"] == "kicker" for l in lines) else 0
    score += 1.0 if re.search(r"\d", lines[0]["text"]) else 0
    return score


def take_for(story: Story, writer: LLM, checker: LLM, *, today: str, published_at: str) -> Take | None:
    """The best verified take for one story, with the other survivors as alternates."""
    if len(story.facts) < MIN_FACTS:
        return None
    formulas = "\n".join(f"- {name}: {when}" for name, when in FORMULAS.items())
    reads = ("BEN'S READS ALREADY APPROVED IN THE ARTICLE (you may reuse one, tightened):\n"
             + "\n".join(f"- {r}" for r in story.reads) + "\n") if story.reads else ""
    try:
        draft = _parse(writer(SYSTEM, PROMPT.format(title=story.title, facts="\n".join(f"- {f}" for f in story.facts),
                                                     reads=reads, formulas=formulas)))
    except Exception:  # noqa: BLE001
        return None
    candidates, formulas_used = [], []
    for entry in (draft.get("takes") or [])[:3]:
        lines = [{"kind": str(l.get("kind") or "").lower(), "text": _clean(l.get("text"))}
                 for l in (entry.get("lines") or [])[:6] if isinstance(l, dict) and _clean(l.get("text"))]
        if lines:
            candidates.append(lines)
            formulas_used.append(_clean(entry.get("formula")) or "")
    if not candidates:
        return None
    verdicts = _check_lines(story, candidates, checker)
    built = []
    all_dropped: list[str] = []
    for lines, verdict, formula in zip(candidates, verdicts, formulas_used):
        kept, dropped = _assemble(lines, verdict)
        all_dropped += dropped
        score = _score(kept)
        if score >= 0:
            built.append((score, formula, kept))
    if not built:
        return None
    built.sort(key=lambda b: -b[0])
    score, formula, lines = built[0]
    take = Take(
        id=f"take-{story.object_id}", object_id=story.object_id, date=today, published_at=published_at,
        sector=story.sector, title=story.title, article_url=story.url, formula=formula,
        text="\n".join(l["text"] for l in lines), lines=lines,
        alternates=[{"formula": f, "text": "\n".join(l["text"] for l in ls)} for _, f, ls in built[1:]],
        dropped=all_dropped, score=float(story.score or 0.0),
    )
    return take


def build_takes(stories: list[Story], writer: LLM, checker: LLM, *, workers: int = WORKERS) -> list[Take]:
    """Takes for every story that can carry one, best stories first (rank 1 = the lead)."""
    now = new_york_now()
    today, published_at = now.strftime("%Y-%m-%d"), datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(lambda s: take_for(s, writer, checker, today=today, published_at=published_at), stories))
    takes = [t for t in results if t is not None]
    for rank, take in enumerate(takes, 1):  # stories arrive best first (load_stories sorts by score)
        take.rank = rank
    return takes


def merge_feed(path: Path, takes: list[Take], *, now: datetime | None = None) -> list[dict[str, Any]]:
    """Add today's takes to the public feed, newest first; replace a story's earlier take; trim old ones."""
    try:
        existing = json.loads(path.read_text(encoding="utf-8")).get("takes", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        existing = []
    fresh_ids = {t.id for t in takes}
    cutoff = ((now or new_york_now()) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    kept = [e for e in existing if e.get("id") not in fresh_ids and str(e.get("date") or "") >= cutoff]
    feed = [t.to_feed() for t in takes] + kept
    # Rank each day's takes together, so a midday story can outrank a morning one.
    for day in {str(t.date) for t in takes}:
        same_day = sorted((e for e in feed if e.get("date") == day), key=lambda e: -float(e.get("score") or 0))
        for rank, entry in enumerate(same_day, 1):
            entry["rank"] = rank
    feed.sort(key=lambda e: (str(e.get("date") or ""), -int(e.get("rank") or 999)), reverse=True)
    feed = feed[:MAX_FEED]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": TAKES_VERSION, "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                                "takes": feed}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return feed


def write_takes(run_dir: Path, feed_path: Path, *, budget: Any = None,
                published: list[dict[str, Any]] | None = None) -> list[Take]:
    """Build today's takes from a run folder and merge them into the feed at ``feed_path``."""
    from linkedin_post import _writer
    from model_router import provider_config
    from v4_generation import _make_verifier

    provider = provider_config("deepseek", for_writing=True)
    if not provider:
        return []
    stories = load_stories(run_dir, published)
    takes = build_takes(stories, _writer(provider, budget), _make_verifier(provider, budget=budget))
    merge_feed(feed_path, takes)
    (Path(run_dir) / "takes-report.json").write_text(json.dumps({
        "stories": len(stories), "takes": len(takes),
        "dropped_lines": {t.id: t.dropped for t in takes if t.dropped},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return takes


def summary_markdown(feed_path: Path, count: int = 5) -> str:
    """The latest day's best takes as Markdown code blocks (for the GitHub run summary)."""
    try:
        feed = json.loads(Path(feed_path).read_text(encoding="utf-8")).get("takes", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return "No takes found.\n"
    if not feed:
        return "No takes found.\n"
    latest = max(str(t.get("date") or "") for t in feed)
    best = sorted((t for t in feed if t.get("date") == latest), key=lambda t: t.get("rank") or 999)[:count]
    fence = "`" * 3
    return "".join(f"{fence}text\n{t.get('text', '')}\n{fence}\n" for t in best)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write Quick Takes for a run folder (preview).")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--summary", action="store_true", help="print the latest day's best takes from a feed file")
    args = parser.parse_args()
    if args.summary:
        print(summary_markdown(args.run_dir), end="")
        return 0
    from model_router import configure_state_dir
    configure_state_dir(args.run_dir)
    takes = write_takes(args.run_dir, args.run_dir / "takes.json")
    print(f"{len(takes)} takes written to {args.run_dir / 'takes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
