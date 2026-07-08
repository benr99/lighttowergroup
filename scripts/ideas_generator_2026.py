#!/usr/bin/env python3
"""Light Tower Ideas generator.

Review-first editorial workflow for the /ideas section:
- scouts CRE/built-world stories from the existing source list
- scores them against the Light Tower Ideas rubric
- writes private Daily Ten and draft JSON artifacts
- optionally renders draft HTML pages for local review

The default mode is offline/no-AI safe. Nothing commits, pushes, or posts.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import feedparser
except ImportError:  # pragma: no cover - dependency status is reported by status.
    feedparser = None

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
DATA_ROOT = SITE_ROOT / "data" / "ideas"
IDEAS_DIR = SITE_ROOT / "ideas"
SITE_URL = "https://lighttowergroup.co"

try:
    from news_sources import RSS_FEEDS
except Exception:
    RSS_FEEDS = []


@dataclass
class Story:
    story_id: str
    title: str
    source: str
    url: str
    published: str = ""
    summary: str = ""


@dataclass
class IdeaScore:
    story_id: str
    title: str
    source: str
    url: str
    total_score: float
    built_world_specificity: float
    human_drama: float
    power_politics: float
    capital_relevance: float
    aesthetic_design: float
    psychological_depth: float
    narrative_potential: float
    originality: float
    business_relevance: float
    timeliness: float
    evergreen_potential: float
    risk_score: float
    recommendation: str
    best_angle: str
    why_it_matters: str


@dataclass
class IdeaDraft:
    slug: str
    title: str
    subtitle: str
    date: str
    status: str
    source_title: str
    source_name: str
    source_url: str
    idea_score: float
    risk_score: float
    excerpt: str
    body_html: str
    tags: list[str] = field(default_factory=list)
    generated_at: str = ""
    review_notes: list[str] = field(default_factory=list)


SAMPLE_STORIES = [
    Story(
        story_id="offline-office-reset",
        title="Office owners rethink lobbies as leasing becomes a confidence game",
        source="Offline Review Fixture",
        url="https://example.com/offline-office-reset",
        published="2026-07-07T08:00:00Z",
        summary=(
            "A review fixture about office landlords investing in hospitality, "
            "security, and amenity space as tenants scrutinize attendance and value."
        ),
    ),
    Story(
        story_id="offline-housing-capital",
        title="Affordable housing capital stacks grow more complex as subsidies lag costs",
        source="Offline Review Fixture",
        url="https://example.com/offline-housing-capital",
        published="2026-07-07T08:00:00Z",
        summary=(
            "A review fixture about layered financing, public approvals, and the "
            "gap between civic ambition and construction math."
        ),
    ),
    Story(
        story_id="offline-retail-place",
        title="Neighborhood retail survives by becoming social infrastructure",
        source="Offline Review Fixture",
        url="https://example.com/offline-retail-place",
        published="2026-07-07T08:00:00Z",
        summary=(
            "A review fixture about storefronts, foot traffic, local memory, and "
            "why small-format retail can matter beyond rent rolls."
        ),
    ),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def slugify(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:90].strip("-") or "idea"


def text_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def load_stories(*, offline: bool, limit: int) -> list[Story]:
    if offline:
        return SAMPLE_STORIES[:limit]

    if feedparser is None:
        raise RuntimeError("feedparser is not installed. Run with --offline or install scripts/requirements.txt.")

    stories: list[Story] = []
    for source_name, feed_url in RSS_FEEDS[:40]:
        if len(stories) >= limit:
            break
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:5]:
            title = clean_text(entry.get("title", ""))
            url = entry.get("link", "")
            if not title or not url:
                continue
            stories.append(
                Story(
                    story_id=f"{source_name.lower()}-{text_hash(url)}",
                    title=title,
                    source=source_name,
                    url=url,
                    published=entry.get("published", entry.get("updated", "")),
                    summary=clean_text(entry.get("summary", "")),
                )
            )
            if len(stories) >= limit:
                break
    return stories


def keyword_score(text: str, words: list[str], base: float = 4.0, bump: float = 0.8) -> float:
    text_l = text.lower()
    hits = sum(1 for word in words if word in text_l)
    return min(10.0, base + hits * bump)


def score_story(story: Story) -> IdeaScore:
    text = f"{story.title} {story.summary}"
    built = keyword_score(text, ["building", "office", "housing", "retail", "tower", "street", "neighborhood", "construction", "lobby", "space"], 4.5, 0.7)
    human = keyword_score(text, ["tenant", "resident", "community", "worker", "family", "neighborhood", "confidence", "safety", "belonging"], 4.0, 0.7)
    power = keyword_score(text, ["zoning", "subsidy", "approval", "policy", "regulation", "public", "city", "institution"], 3.5, 0.8)
    capital = keyword_score(text, ["loan", "debt", "equity", "capital", "financing", "rent", "cost", "refi", "lender", "subsidy"], 4.0, 0.8)
    design = keyword_score(text, ["design", "architecture", "lobby", "amenity", "interior", "street", "storefront", "hospitality"], 3.5, 0.8)
    psych = keyword_score(text, ["confidence", "status", "trust", "fear", "belonging", "memory", "desire", "anxiety", "social"], 4.0, 0.75)
    narrative = min(10.0, (built + human + capital + psych) / 4 + 0.8)
    originality = keyword_score(text, ["rethink", "survives", "complex", "hidden", "forgot", "new", "lag"], 4.5, 0.6)
    business = min(10.0, (capital + built) / 2 + 0.6)
    timeliness = 7.0 if story.published else 5.5
    evergreen = min(10.0, (human + psych + design) / 3 + 0.9)
    risk = keyword_score(text, ["lawsuit", "fraud", "criminal", "alleged", "investigation"], 1.0, 1.2)

    weights = {
        "built": 0.12,
        "human": 0.10,
        "power": 0.10,
        "capital": 0.10,
        "design": 0.10,
        "psych": 0.10,
        "narrative": 0.10,
        "originality": 0.10,
        "business": 0.08,
        "timeliness": 0.05,
        "evergreen": 0.05,
    }
    total = (
        built * weights["built"]
        + human * weights["human"]
        + power * weights["power"]
        + capital * weights["capital"]
        + design * weights["design"]
        + psych * weights["psych"]
        + narrative * weights["narrative"]
        + originality * weights["originality"]
        + business * weights["business"]
        + timeliness * weights["timeliness"]
        + evergreen * weights["evergreen"]
    )
    recommendation = "develop" if total >= 6.4 and risk <= 4 else "hold"
    return IdeaScore(
        story_id=story.story_id,
        title=f"{story.title} - Ideas Brief",
        source=story.source,
        url=story.url,
        total_score=round(total, 2),
        built_world_specificity=round(built, 1),
        human_drama=round(human, 1),
        power_politics=round(power, 1),
        capital_relevance=round(capital, 1),
        aesthetic_design=round(design, 1),
        psychological_depth=round(psych, 1),
        narrative_potential=round(narrative, 1),
        originality=round(originality, 1),
        business_relevance=round(business, 1),
        timeliness=round(timeliness, 1),
        evergreen_potential=round(evergreen, 1),
        risk_score=round(risk, 1),
        recommendation=recommendation,
        best_angle=make_angle(story),
        why_it_matters=make_why_it_matters(story),
    )


def make_angle(story: Story) -> str:
    title = story.title.rstrip(".")
    return (
        f"Use '{title}' as the visible event, then ask what it reveals about how "
        "capital, design, and human trust become physical space."
    )


def make_why_it_matters(story: Story) -> str:
    return (
        "This belongs in Ideas if the final essay moves beyond the transaction and "
        "shows readers a hidden system in the built world."
    )


def daily_menu(args: argparse.Namespace) -> dict[str, Any]:
    stories = load_stories(offline=args.offline, limit=args.limit)
    scored = sorted((score_story(story) for story in stories), key=lambda item: item.total_score, reverse=True)
    top = scored[: args.count]
    payload = {
        "date": today(),
        "generated_at": now_iso(),
        "mode": "offline-no-ai" if args.offline else "rss-no-ai",
        "candidate_count": len(stories),
        "ranked_ideas": [asdict(item) for item in top],
    }
    out = DATA_ROOT / "internal" / "daily-ten" / f"{today()}.json"
    write_json(out, payload)
    print(f"Daily Ten saved: {out.relative_to(SITE_ROOT)}")
    for idx, idea in enumerate(top, 1):
        print(f"{idx}. [{idea.total_score}/10] {idea.title}")
    return payload


def draft_from_idea(idea: dict[str, Any]) -> IdeaDraft:
    base_title = idea["title"].replace(" - Ideas Brief", "")
    title = base_title
    slug = slugify(title)
    escaped_title = html.escape(title)
    source = html.escape(idea.get("source", ""))
    url = html.escape(idea.get("url", ""))
    body = f"""
<p><strong>Editorial frame:</strong> {html.escape(idea.get("best_angle", ""))}</p>
<h2>The Surface Event</h2>
<p>{escaped_title} is the starting point, not the whole story. The finished essay should use the reported item as the door into a larger argument about place.</p>
<h2>The Hidden System</h2>
<p>Develop the connection between the physical asset, the capital stack behind it, and the psychological promise the place is trying to make to tenants, residents, lenders, or neighbors.</p>
<h2>Questions For Reporting</h2>
<ul>
  <li>What specific building, room, street, or design choice makes the idea visible?</li>
  <li>Who supplies the capital, who carries the risk, and who experiences the space?</li>
  <li>What fact would make the interpretation stronger or force it to change?</li>
</ul>
<h2>Source To Review</h2>
<p><a href="{url}" rel="nofollow noopener">{source}</a></p>
""".strip()
    return IdeaDraft(
        slug=slug,
        title=title,
        subtitle="A review-ready Light Tower Ideas brief",
        date=today(),
        status="draft_review",
        source_title=title,
        source_name=idea.get("source", ""),
        source_url=idea.get("url", ""),
        idea_score=float(idea.get("total_score", 0)),
        risk_score=float(idea.get("risk_score", 0)),
        excerpt=idea.get("why_it_matters", ""),
        body_html=body,
        tags=["Ideas", "Built World", "Capital", "Place"],
        generated_at=now_iso(),
        review_notes=[
            "Draft artifact only. Do not publish without human review.",
            "Verify source facts and add real reporting/detail before converting to a public essay.",
        ],
    )


def draft(args: argparse.Namespace) -> list[IdeaDraft]:
    menu_path = DATA_ROOT / "internal" / "daily-ten" / f"{args.date or today()}.json"
    if not menu_path.exists():
        payload = daily_menu(args)
    else:
        payload = json.loads(menu_path.read_text(encoding="utf-8"))
    drafts = [draft_from_idea(item) for item in payload.get("ranked_ideas", [])[: args.count]]
    for item in drafts:
        write_json(DATA_ROOT / "drafts" / f"{item.slug}.json", asdict(item))
        if args.render:
            render_draft(item, draft=True)
    print(f"Drafts saved: {len(drafts)}")
    return drafts


def render_draft(draft_item: IdeaDraft, *, draft: bool) -> Path:
    label = "Draft Review" if draft else "Light Tower Ideas"
    noindex = '<meta name="robots" content="noindex, nofollow">' if draft else '<meta name="robots" content="index, follow">'
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(draft_item.title)} | Light Tower Ideas</title>
  <meta name="description" content="{html.escape(draft_item.excerpt)}">
  {noindex}
  <link rel="canonical" href="{SITE_URL}/ideas/{draft_item.slug}.html">
  <link rel="stylesheet" href="/site.css">
</head>
<body>
  <nav class="nav">
    <a href="/" class="nav-logo">Light Tower Group</a>
    <div class="nav-links">
      <a href="/insights.html">Insights</a>
      <a href="/ideas.html">Ideas</a>
      <a href="/buildings.html">Buildings</a>
      <a href="/services.html">Services</a>
      <a href="/about.html">About</a>
    </div>
  </nav>
  <main class="article-page">
    <article class="article-shell">
      <p class="eyebrow">{label}</p>
      <h1>{html.escape(draft_item.title)}</h1>
      <p class="article-subtitle">{html.escape(draft_item.subtitle)}</p>
      <p class="article-meta">{html.escape(draft_item.date)} - Score {draft_item.idea_score}/10 - Risk {draft_item.risk_score}/10</p>
      <div class="article-content">
        {draft_item.body_html}
      </div>
    </article>
  </main>
</body>
</html>
"""
    out_dir = IDEAS_DIR / "_drafts" if draft else IDEAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{draft_item.slug}.html"
    out.write_text(html_doc, encoding="utf-8")
    return out


def status(_: argparse.Namespace) -> None:
    print("Light Tower Ideas Generator")
    print(f"Site root: {SITE_ROOT}")
    print(f"Data root: {DATA_ROOT.relative_to(SITE_ROOT)}")
    print(f"RSS sources available: {len(RSS_FEEDS)}")
    print(f"feedparser installed: {'yes' if feedparser else 'no'}")
    print("Default behavior: no AI, no auto-publish, no commit, no push")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Light Tower Ideas review-first generator")
    sub = parser.add_subparsers(dest="command", required=False)

    status_parser = sub.add_parser("status", help="Show generator status")
    status_parser.set_defaults(func=status)

    menu = sub.add_parser("daily-menu", help="Create a private Daily Ten idea ranking")
    menu.add_argument("--offline", action="store_true", help="Use built-in fixture stories; no network")
    menu.add_argument("--limit", type=int, default=60, help="Maximum stories to scout")
    menu.add_argument("--count", type=int, default=10, help="Number of ideas to keep")
    menu.set_defaults(func=daily_menu)

    draft_parser = sub.add_parser("draft", help="Create review drafts from a Daily Ten")
    draft_parser.add_argument("--offline", action="store_true", help="Use fixtures if no Daily Ten exists")
    draft_parser.add_argument("--limit", type=int, default=60, help="Maximum stories to scout if creating menu")
    draft_parser.add_argument("--count", type=int, default=3, help="Number of draft briefs to create")
    draft_parser.add_argument("--date", default="", help="Daily Ten date, defaults to today")
    draft_parser.add_argument("--render", action="store_true", help="Render noindex draft HTML under ideas/_drafts/")
    draft_parser.set_defaults(func=draft)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["status"])
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
