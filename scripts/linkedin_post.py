#!/usr/bin/env python3
"""Build the day's LinkedIn post: a bulleted story roundup in Ben's voice.

One post per day, built only from what that day's articles already proved:

    hook (two lines that stop the scroll)
    N stories from today's capital markets tape 👇
    <emoji> headline
    → one or two short lines per story
    💬 Ben's read (only where the article kept one)
    ... closing question for comments
    "Full stories in the first comment" + hashtags

plus the first comment with the links. The writer may only restate sentences that passed
the article fact gate; every line of the post is then checked again against that story's
verified sentences (numbers and names deterministically, meaning by two reasoning passes),
and Ben's reads and the closing question pass the voice gate. Anything that fails is
deleted, never softened; one rewrite sees the deletions and their reasons. Nothing is
posted: the text is written for Ben to paste.

    python linkedin_post.py <run folder>   # writes linkedin-post.txt, linkedin-comment.txt, linkedin-post.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SITE = "https://lighttowergroup.co"
MAX_CHARS = 2900  # LinkedIn allows 3,000; leave room for an edit
MAX_STORIES = 8
MIN_STORIES = 2
POST_VERSION = "linkedin-roundup-1"

LLM = Callable[[str, str], str]

EMOJI = {
    "commercial_real_estate": "🏢", "banking_credit": "🏦", "fed_macro": "🏛️", "energy": "⚡",
    "data_centers": "🖥️", "private_equity": "💼", "local_government": "🏙️",
}
HASHTAGS = {
    "commercial_real_estate": "#CommercialRealEstate", "banking_credit": "#Lending", "fed_macro": "#FederalReserve",
    "energy": "#Energy", "data_centers": "#DataCenters", "private_equity": "#PrivateEquity",
    "local_government": "#RealEstatePolicy",
}

SYSTEM = (
    "You are Ben Rohr, a commercial real estate capital advisor in Brooklyn, writing your daily LinkedIn "
    "roundup of the capital markets stories your desk verified today. Your followers are sponsors, lenders, "
    "brokers and investors. You write like a sharp, funny, generous colleague: plain words, short lines, "
    "one point of view, never a press release. You never state a fact that is not in the verified sentences "
    "you are given."
)

PROMPT = """Write today's LinkedIn roundup post from the verified stories below. Return JSON only.

VERIFIED STORIES (each sentence already passed a fact check; these are the only facts you may use):
{stories}

THE FORMAT (a proven LinkedIn roundup template)
- "hook": two short lines (each under 110 characters). Line 1 is the single most surprising fact of the day, plainly stated, with its number. Line 2 is a short reaction that makes people click "see more" (no facts in line 2: no numbers, no names). Set "hook_story" to the id the line-1 fact comes from.
- "stories": one entry per story you include, in the order a reader would find most gripping (lead with the strongest). Include at least {min_stories} and at most {max_stories}. For each:
  - "id": the story id.
  - "headline": under 60 characters, specific, with the key number when there is one. Not a label like "X announces Y".
  - "lines": one or two lines, each under 120 characters: the facts that make the story matter, restated more tightly than the source sentence. Every number, name, place and relationship must appear in that story's verified sentences. No new totals, rankings, causes or comparisons.
  - "read": optional. Use only when the story lists a READ: you may shorten it, but keep it first person and keep its meaning. Otherwise "".
- KEEP EVERY QUALIFIER AND ATTRIBUTION, in headlines and lines alike: "about $589 per square foot" stays "about $589"; "valued at $1 billion, according to The Wall Street Journal" keeps "per the WSJ"; "agreed to acquire" stays "agreed to acquire"; "about $525.3 million" stays "about $525M". "$1 billion" may be written "$1B" and "more than 25 years" may become "25+ years". Each line is checked again by machine and deleted if it drops one of these.
- "close": one line that asks the reader a genuine question about their own deals or market, to start the comments. No facts, no numbers, no names.
- Never use: "landscape", "navigating", "game-changer", "unlock", "delve", "in today's market", "buckle up", "let's dive in", "here's the thing", "the real story". No hashtags in the text (they are added for you). No links.

Return exactly:
{{"hook":["...","..."],"hook_story":"s1","stories":[{{"id":"s1","headline":"...","lines":["...","..."],"read":""}}],"close":"..."}}"""


@dataclass
class Story:
    id: str
    object_id: str
    title: str
    sector: str
    score: float
    url: str
    facts: list[str]
    reads: list[str]


@dataclass
class Post:
    text: str = ""
    comment: str = ""
    stories: list[dict[str, Any]] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    total_stories: int = 0
    status: str = "ok"


def load_stories(run_dir: Path) -> list[Story]:
    """Published (or, in preview, completed) stories with their verified sentences, best first."""
    run_dir = Path(run_dir)
    run_file = run_dir / "v3-run.json"
    report = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
    urls = {a.get("event_id"): SITE + str(a.get("url") or "")
            for a in (report.get("publication") or {}).get("articles") or [] if a.get("event_id")}
    scores: dict[str, float] = {}
    candidates = run_dir / "v3-candidates.json"
    if candidates.exists():
        for c in json.loads(candidates.read_text(encoding="utf-8")).get("candidates", []):
            scores[c.get("object_id")] = float(c.get("final_score") or 0)
    published_only = bool(urls)
    stories: list[Story] = []
    for path in sorted((run_dir / "v4-evidence").glob("*.json")):
        ev = json.loads(path.read_text(encoding="utf-8"))
        oid = ev.get("object_id", "")
        if published_only and oid not in urls:
            continue  # written but not published today (held for review, or already live)
        items = [i for para in ev.get("paragraphs") or [] for i in para]
        facts = [i["text"] for i in items if i.get("kind") == "fact"]
        if not facts:
            continue
        stories.append(Story(id="", object_id=oid, title=ev.get("title", ""), sector=ev.get("sector", ""),
                             score=scores.get(oid, 0.0), url=urls.get(oid, ""), facts=facts,
                             reads=[i["text"] for i in items if i.get("kind") == "take"]))
    stories.sort(key=lambda s: -s.score)
    for n, story in enumerate(stories, 1):
        story.id = f"s{n}"
    return stories


def _stories_block(stories: list[Story]) -> str:
    out = []
    for s in stories:
        lines = [f"[{s.id}] {s.title} (sector: {s.sector.replace('_', ' ')})"]
        lines += [f"  FACT: {f}" for f in s.facts]
        lines += [f"  READ: {r}" for r in s.reads]
        out.append("\n".join(lines))
    return "\n\n".join(out)


def _parse(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("invalid_json_object")
    return value


def _clean(text: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip().strip('"')
    return text if len(text) <= limit else ""


def _check(llm: LLM, story: Story, lines: list[str]) -> list[tuple[bool, str]]:
    """Each line must be supported by the story's verified sentences (fail closed)."""
    from claim_verifier import FACT, Item, verify_unquoted

    if not lines:
        return []
    source = f"{story.title}\n" + "\n".join(story.facts)
    items = [Item(id=f"l{i}", kind=FACT, text=t) for i, t in enumerate(lines)]
    try:
        verify_unquoted(items, source, " ".join(story.facts), llm)
    except Exception as exc:  # noqa: BLE001
        return [(False, f"fact check unavailable: {type(exc).__name__}")] * len(lines)
    return [(i.ok, "" if i.ok else i.reason) for i in items]


def _voice_ok(text: str, kind: str, story: Story | None, llm: LLM) -> bool:
    from voice_gate import VoiceItem, check_voice_item, run_rubric

    facts = {f"f{i}": f for i, f in enumerate(story.facts)} if story else {}
    item = VoiceItem(id="v", kind=kind, text=text, because=list(facts))
    check_voice_item(item, facts, [], [])
    if item.problems:
        return False
    try:
        run_rubric(llm, facts, [item])
    except Exception:  # noqa: BLE001
        return False
    return item.ok


def _render(post: Post, hook: list[str], entries: list[tuple[Story, str, list[str], str]], close: str) -> str:
    parts = [line for line in hook if line] + [""]
    parts += [f"{len(entries)} stories from today's capital markets tape 👇", ""]
    for story, headline, lines, read in entries:
        parts.append(f"{EMOJI.get(story.sector, '📌')} {headline}")
        parts += [f"→ {line}" for line in lines]
        if read:
            parts.append(f"💬 {read}")
        parts.append("")
    more = post.total_stories - len(entries)
    if more > 0:
        parts += [f"+ {more} more stor{'y' if more == 1 else 'ies'} on the site today.", ""]
    if close:
        parts += [close, ""]
    parts += ["Every story in full, each fact checked against its source: link in the first comment.", ""]
    tags: list[str] = []
    for story, *_ in entries:
        tag = HASHTAGS.get(story.sector)
        if tag and tag not in tags:
            tags.append(tag)
    parts.append(" ".join((["#CRE"] + tags + ["#CapitalMarkets"])[:5]))
    return "\n".join(parts).strip() + "\n"


def _attempt(stories: list[Story], writer: LLM, checker: LLM, feedback: str) -> Post:
    post = Post(total_stories=len(stories))
    pool = stories[:MAX_STORIES + 4]  # a few spares in case some lines fail
    try:
        draft = _parse(writer(SYSTEM, PROMPT.format(stories=_stories_block(pool), min_stories=MIN_STORIES,
                                                    max_stories=MAX_STORIES) + feedback))
    except Exception as exc:  # noqa: BLE001
        post.status = f"skipped: the writer failed ({type(exc).__name__})"
        return post
    by_id = {s.id: s for s in pool}

    kept: list[tuple[Story, str, list[str], str]] = []
    for entry in draft.get("stories") or []:
        story = by_id.get(str(entry.get("id")))
        if story is None or any(k[0] is story for k in kept):
            continue
        headline = _clean(entry.get("headline"), 70)
        lines = [x for x in (_clean(y, 140) for y in (entry.get("lines") or [])[:2]) if x]
        verdicts = _check(checker, story, ([headline] if headline else []) + lines)
        head_v, line_v = (verdicts[0], verdicts[1:]) if headline else ((False, "empty"), verdicts)
        if not head_v[0]:
            post.dropped.append(f"[{story.id} headline] {headline or '(empty)'} <- {head_v[1]}")
            headline = story.title if len(story.title) <= 70 else ""
        good_lines = [x for x, (ok, _) in zip(lines, line_v) if ok]
        post.dropped += [f"[{story.id} line] {x} <- {why}" for x, (ok, why) in zip(lines, line_v) if not ok]
        if not headline or not good_lines:
            continue
        read = _clean(entry.get("read"), 200)
        if read and not _voice_ok(read, "take", story, checker):
            post.dropped.append(f"[{story.id} read] {read} <- failed the opinion rules")
            read = ""
        kept.append((story, headline, good_lines, read))
        if len(kept) >= MAX_STORIES:
            break

    if len(kept) < MIN_STORIES:
        post.status = "skipped: too few stories survived the check"
        return post

    hook = [_clean(x, 130) for x in (draft.get("hook") or [])[:2]]
    hook_story = by_id.get(str(draft.get("hook_story")))
    hook_v = _check(checker, hook_story, [hook[0]]) if (hook and hook[0] and hook_story) else [(False, "missing")]
    if not hook_v[0][0]:
        post.dropped.append(f"[hook] {hook[0] if hook else '(empty)'} <- {hook_v[0][1]}")
        hook = [kept[0][1]]
    elif len(hook) > 1 and hook[1] and not _voice_ok(hook[1], "voice", None, checker):
        post.dropped.append(f"[hook line 2] {hook[1]} <- a reaction line may state no fact, number or name")
        hook = hook[:1]
    close = _clean(draft.get("close"), 200)
    if close and not _voice_ok(close, "voice", None, checker):
        post.dropped.append(f"[close] {close} <- a question may state no fact, number or name")
        close = ""

    while len(_render(post, hook, kept, close)) > MAX_CHARS and len(kept) > MIN_STORIES:
        kept.pop()
    post.text = _render(post, hook, kept, close)
    post.stories = [{"id": s.id, "object_id": s.object_id, "headline": h, "lines": ls, "read": r, "url": s.url}
                    for s, h, ls, r in kept]
    links = [f"• {h}: {s.url}" for s, h, _, _ in kept if s.url][:5]
    post.comment = "\n".join([f"Read every story from today, in full: {SITE}/insights.html"]
                             + ([""] + links if links else [])) + "\n"
    return post


def build(stories: list[Story], writer: LLM, checker: LLM) -> Post:
    """Two attempts at most: the second sees every line the check deleted and why."""
    if len(stories) < MIN_STORIES:
        post = Post(total_stories=len(stories))
        post.status = f"skipped: only {len(stories)} stor{'y' if len(stories) == 1 else 'ies'} today"
        return post
    feedback = ""
    best: Post | None = None
    for _ in range(2):
        post = _attempt(stories, writer, checker, feedback)
        if best is None or (len(post.stories), -len(post.dropped)) > (len(best.stories), -len(best.dropped)):
            best = post
        if not post.dropped and post.stories:
            break
        feedback = ("\n\nYour previous draft was checked. These were deleted, with the reason. Write a complete "
                    "replacement in the same JSON shape, keeping every qualifier and attribution:\n"
                    + "\n".join(f"- {d}" for d in post.dropped[:30]))
    return best


def _writer(provider: dict[str, Any], budget: Any = None) -> LLM:
    from v4_generation import _chat

    def call(system: str, user: str) -> str:
        return _chat(provider, system=system, user=user, temperature=0.7, max_tokens=4000, timeout_s=120,
                     json_mode=True, budget=budget, stage="linkedin_post")
    return call


def write(run_dir: Path, *, budget: Any = None) -> Post:
    """Build the post for a run folder and write it beside the run's other files."""
    from model_router import provider_config
    from v4_generation import _make_verifier

    run_dir = Path(run_dir)
    provider = provider_config("deepseek", for_writing=True)
    if not provider:
        post = Post(status="skipped: DEEPSEEK_API_KEY is not set")
    else:
        post = build(load_stories(run_dir), _writer(provider, budget), _make_verifier(provider, budget=budget))
    (run_dir / "linkedin-post.txt").write_text(post.text, encoding="utf-8")
    (run_dir / "linkedin-comment.txt").write_text(post.comment, encoding="utf-8")
    (run_dir / "linkedin-post.json").write_text(json.dumps({
        "version": POST_VERSION, "status": post.status, "total_stories": post.total_stories,
        "stories": post.stories, "dropped_by_check": post.dropped, "characters": len(post.text),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return post


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the day's LinkedIn roundup post from a run folder.")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    from model_router import configure_state_dir
    configure_state_dir(args.run_dir)
    post = write(args.run_dir)
    print(f"{post.status}: {len(post.stories)} stories, {len(post.text)} characters, "
          f"{len(post.dropped)} lines deleted by the check. See linkedin-post.txt in {args.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
