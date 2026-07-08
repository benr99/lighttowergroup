#!/usr/bin/env python3
"""Light Tower Ideas daily publishing agent.

Runs:
news intake -> Ideas ranking -> research dossier -> essay generation ->
quality gates -> public Ideas pages -> hub/feed/sitemap updates.

No git commit, push, scheduling, or LinkedIn posting is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import requests
except ImportError:
    requests = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
IDEAS_DIR = SITE_ROOT / "ideas"
DATA_ROOT = SITE_ROOT / "data" / "ideas"
MANIFEST = DATA_ROOT / "ideas.json"
SITE_URL = "https://lighttowergroup.co"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_env = SCRIPT_DIR / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            key, value = _line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from ideas_prompts import (
    IDEAS_SYSTEM_PROMPT,
    article_json_prompt,
    fallback_article_from_dossier,
    prose_edit_prompt,
)
from ideas_quality import assert_no_mojibake, validate_article, validate_html
from ideas_renderer import (
    render_article,
    render_hub,
    render_ideas_feed,
    update_manifest,
    update_sitemap,
    write_json,
)
from story_normalizer import normalize_stories

try:
    from news_sources import RSS_FEEDS, CRE_KEYWORDS, EXCLUDE_KEYWORDS
except Exception:
    RSS_FEEDS, CRE_KEYWORDS, EXCLUDE_KEYWORDS = [], [], []


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


OFFLINE_STORIES = [
    {
        "title": "Office owners rethink lobbies as leasing becomes a confidence game",
        "source": "Offline Review Fixture",
        "url": "https://example.com/offline-office-lobbies",
        "published": datetime.now(timezone.utc).isoformat(),
        "summary": "Landlords are investing in hospitality, security, and amenity space as companies reassess why employees come to the office.",
    },
    {
        "title": "Affordable housing capital stacks grow more complex as subsidies lag costs",
        "source": "Offline Review Fixture",
        "url": "https://example.com/offline-affordable-housing",
        "published": datetime.now(timezone.utc).isoformat(),
        "summary": "Developers are layering public subsidies, private debt, tax credits, and local approvals to keep housing projects feasible.",
    },
    {
        "title": "Neighborhood retail survives by becoming social infrastructure",
        "source": "Offline Review Fixture",
        "url": "https://example.com/offline-neighborhood-retail",
        "published": datetime.now(timezone.utc).isoformat(),
        "summary": "Storefronts that act as community anchors are proving more durable than commodity retail space in some urban corridors.",
    },
]


IDEAS_KEYWORDS = [
    "building", "tower", "office", "housing", "apartment", "multifamily", "retail",
    "street", "neighborhood", "architecture", "design", "zoning", "planning",
    "development", "construction", "lobby", "tenant", "public space", "adaptive reuse",
    "affordable housing", "landmark", "campus", "hotel", "warehouse", "data center",
]

CAPITAL_KEYWORDS = [
    "loan", "debt", "equity", "capital", "financing", "mortgage", "refinance",
    "lender", "sponsor", "lease", "rent", "valuation", "fund", "credit",
    "subsidy", "tax credit", "cost", "distress", "default",
]

POWER_KEYWORDS = [
    "zoning", "policy", "approval", "regulation", "city", "public", "institution",
    "agency", "board", "community", "tax", "subsidy", "land use", "politics",
]

DESIGN_KEYWORDS = [
    "design", "architecture", "interior", "facade", "lobby", "amenity", "street",
    "storefront", "public realm", "adaptive reuse", "historic", "beauty", "taste",
]

PSYCH_KEYWORDS = [
    "confidence", "trust", "status", "belonging", "safety", "memory", "anxiety",
    "community", "identity", "loneliness", "desire", "work", "home",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Light Tower Ideas daily publishing agent")
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate without writing public pages")
    parser.add_argument("--publish", action="store_true", help="Write public Ideas pages and update hub/feed/sitemap")
    parser.add_argument("--count", type=int, default=10, help="Number of Ideas articles to generate, max 10")
    parser.add_argument("--offline", action="store_true", help="Use built-in fixture stories; no network")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic fallback writing")
    parser.add_argument("--force", action="store_true", help="Allow regenerating existing slugs")
    parser.add_argument("--lookback-hours", type=int, default=72)
    parser.add_argument("--max-feeds", type=int, default=35, help="Maximum RSS feeds to scan in live mode")
    args = parser.parse_args()

    if not args.publish:
        args.dry_run = True
    count = max(1, min(args.count, 10))
    start = datetime.now(timezone.utc)
    print("=" * 64)
    print("Light Tower Ideas Daily Agent")
    print(f"{start.strftime('%Y-%m-%d %H:%M UTC')} | count={count} | {'PUBLISH' if args.publish else 'DRY-RUN'}")
    print("=" * 64)

    stories = gather_stories(args)
    print(f"[1/7] Gathered {len(stories)} raw stories")
    candidates = filter_ideas_candidates(stories, args.lookback_hours)
    print(f"[2/7] Ideas candidates: {len(candidates)}")
    if not candidates:
        print("No Ideas candidates found.")
        return 0

    ranked = rank_candidates(candidates)
    save_daily_ten(ranked, start)
    attempt_target = min(max(count * 3, count + 5), 20)
    selected = fresh_selection(ranked, attempt_target, force=args.force)
    print(f"[3/7] Selected {len(selected)} article candidate(s) to fill {count} slot(s)")

    articles = []
    held = []
    for idx, idea in enumerate(selected, 1):
        if len(articles) >= count:
            break
        print(f"[4/7] Writing {idx}/{len(selected)}: {idea['title'][:74]}")
        dossier = create_dossier(idea)
        article = generate_article(dossier, no_ai=args.no_ai or args.offline)
        article = normalize_article(article, idea, dossier)
        errors = validate_article(article, dossier)
        if errors:
            held.append({"idea": idea, "article": article, "dossier": dossier, "errors": errors})
            write_json(DATA_ROOT / "held" / f"{article.get('slug','held')}.json", held[-1])
            print(f"  HELD: {', '.join(errors[:3])}")
            continue
        html_doc = render_article(article)
        html_errors = validate_html(html_doc)
        if html_errors:
            held.append({"idea": idea, "article": article, "dossier": dossier, "errors": html_errors})
            write_json(DATA_ROOT / "held" / f"{article.get('slug','held')}.json", held[-1])
            print(f"  HELD HTML: {', '.join(html_errors[:3])}")
            continue
        article["_html"] = html_doc
        article["_dossier"] = dossier
        articles.append(article)
        print(f"  OK: {article['slug']}")

    print(f"[5/7] Publishable: {len(articles)} | held: {len(held)}")
    if args.publish and articles:
        publish_articles(articles)
    else:
        for article in articles:
            preview_path = DATA_ROOT / "previews" / f"{article['slug']}.html"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_text(article["_html"], encoding="utf-8")
            write_json(DATA_ROOT / "drafts" / f"{article['slug']}.json", public_article(article))
            print(f"  [DRY-RUN] Preview: {preview_path.relative_to(SITE_ROOT)}")

    save_run_log(start, args, stories, candidates, ranked, articles, held)
    print("[7/7] Complete")
    if args.publish:
        for article in articles:
            print(f"  {SITE_URL}/ideas/{article['slug']}.html")
    return 0


def gather_stories(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.offline:
        return OFFLINE_STORIES
    if feedparser is None:
        print("feedparser unavailable; use --offline or install dependencies")
        return []
    stories: list[dict[str, Any]] = []
    for source, url in RSS_FEEDS[: max(1, args.max_feeds)]:
        try:
            if requests is not None:
                response = requests.get(url, headers={"User-Agent": "LightTowerIdeas/1.0"}, timeout=8)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            else:
                feed = feedparser.parse(url, request_headers={"User-Agent": "LightTowerIdeas/1.0"})
            for entry in feed.entries[:15]:
                title = clean_text(entry.get("title"))
                link = entry.get("link") or entry.get("id") or ""
                summary = clean_text(entry.get("summary") or entry.get("description"))
                if title and link:
                    stories.append({
                        "title": title,
                        "url": link,
                        "summary": summary,
                        "source": source,
                        "published": parse_entry_date(entry),
                    })
        except Exception as exc:
            print(f"  [WARN] {source}: {redact(exc)}")
        time.sleep(0.03)
    return stories


def filter_ideas_candidates(stories: list[dict[str, Any]], lookback_hours: int) -> list[dict[str, Any]]:
    normalized = normalize_stories(stories)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    filtered = []
    seen_urls = set()
    for item in normalized:
        text = f"{item['title']} {item.get('summary','')}".lower()
        if item["url"] in seen_urls:
            continue
        if EXCLUDE_KEYWORDS and any(word.lower() in text for word in EXCLUDE_KEYWORDS):
            continue
        if not any(word in text for word in IDEAS_KEYWORDS):
            continue
        try:
            published = datetime.fromisoformat(str(item.get("published", "")).replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue
        except Exception:
            published = datetime.now(timezone.utc)
        item["published_dt"] = published.isoformat()
        seen_urls.add(item["url"])
        filtered.append(item)
    return filtered


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for item in candidates:
        text = f"{item['title']} {item.get('summary','')}"
        built = keyword_score(text, IDEAS_KEYWORDS, 4.0, 0.45)
        capital = keyword_score(text, CAPITAL_KEYWORDS, 3.5, 0.55)
        power = keyword_score(text, POWER_KEYWORDS, 3.2, 0.55)
        design = keyword_score(text, DESIGN_KEYWORDS, 3.0, 0.55)
        psych = keyword_score(text, PSYCH_KEYWORDS, 3.2, 0.55)
        human = min(10.0, (psych + keyword_score(text, ["tenant", "resident", "worker", "family", "community"], 3.5, 0.5)) / 2 + 1.0)
        narrative = min(10.0, (built + capital + human + design + psych) / 5 + 1.0)
        originality = keyword_score(text, ["rethink", "shift", "new", "return", "survive", "transform", "conversion", "adaptive"], 4.2, 0.45)
        business = min(10.0, (capital + built) / 2 + 0.8)
        timeliness = 7.0
        evergreen = min(10.0, (human + psych + design) / 3 + 1.0)
        risk = keyword_score(text, ["fraud", "criminal", "lawsuit", "alleged", "investigation"], 1.0, 0.9)
        total = (
            built * 0.12 + human * 0.10 + power * 0.10 + capital * 0.10 +
            design * 0.10 + psych * 0.10 + narrative * 0.10 + originality * 0.10 +
            business * 0.08 + timeliness * 0.05 + evergreen * 0.05
        )
        row = dict(item)
        row["ideas_score"] = {
            "total_score": round(total, 2),
            "built_world_specificity": round(built, 1),
            "human_drama": round(human, 1),
            "power_politics": round(power, 1),
            "capital_relevance": round(capital, 1),
            "aesthetic_design": round(design, 1),
            "psychological_depth": round(psych, 1),
            "narrative_potential": round(narrative, 1),
            "originality": round(originality, 1),
            "business_relevance": round(business, 1),
            "timeliness": round(timeliness, 1),
            "evergreen_potential": round(evergreen, 1),
            "risk_score": round(risk, 1),
            "recommendation": "publish" if total >= 4.5 and risk <= 4.5 else "hold",
        }
        ranked.append(row)
    return sorted(ranked, key=lambda item: item["ideas_score"]["total_score"], reverse=True)


def fresh_selection(ranked: list[dict[str, Any]], count: int, *, force: bool) -> list[dict[str, Any]]:
    selected = []
    for item in ranked:
        if item["ideas_score"]["recommendation"] == "hold":
            continue
        slug = slugify(item["title"])
        if not force and (IDEAS_DIR / f"{slug}.html").exists():
            continue
        selected.append(item)
        if len(selected) >= count:
            break
    return selected


def create_dossier(idea: dict[str, Any]) -> dict[str, Any]:
    text = f"{idea['title']} {idea.get('summary','')}"
    source_text = fetch_article_text(idea.get("url", ""))
    facts = [idea["title"]]
    if idea.get("summary"):
        facts.append(idea["summary"])
    if source_text:
        facts.append(source_text[:1200])
    facts.extend(idea.get("entities", {}).get("amounts", []))
    markets = idea.get("entities", {}).get("markets", [])
    assets = idea.get("entities", {}).get("asset_classes", [])
    score = idea.get("ideas_score", {})
    return {
        "source_story": {
            "title": idea["title"],
            "source": idea.get("source"),
            "url": idea.get("url"),
            "published": idea.get("published"),
            "summary": idea.get("summary"),
        },
        "reported_facts": list(dict.fromkeys(facts)),
        "source_urls": [idea.get("url")],
        "source_excerpt": source_text[:4000],
        "known_entities": idea.get("entities", {}).get("companies", []),
        "physical_place_details": markets + assets,
        "capital_context": infer_phrase(text, CAPITAL_KEYWORDS, "capital, financing, or rent pressure visible in the story"),
        "power_or_policy_context": infer_phrase(text, POWER_KEYWORDS, "public rules, institutional decisions, or local power around the place"),
        "design_or_aesthetic_context": infer_phrase(text, DESIGN_KEYWORDS, "the design and spatial choices implied by the built-world event"),
        "psychological_or_social_theme": infer_phrase(text, PSYCH_KEYWORDS, "how people trust, use, remember, or belong to places"),
        "claims_not_to_make": ["Do not invent quotes.", "Do not claim site visits.", "Do not add figures not in the source material."],
        "questions_unanswered": ["What additional reporting would sharpen the place-specific detail?"],
        "idea_score": score.get("total_score", 0),
        "risk_score": score.get("risk_score", 2),
    }


def generate_article(dossier: dict[str, Any], *, no_ai: bool) -> dict[str, Any]:
    if no_ai:
        article = fallback_article_from_dossier(dossier)
        article["generation_mode"] = "no_ai_fallback"
        return article
    if DEEPSEEK_API_KEY and requests is not None:
        try:
            raw = call_deepseek(article_json_prompt(dossier), IDEAS_SYSTEM_PROMPT, max_tokens=6500)
            article = parse_json_object(raw)
            raw_edit = call_deepseek(prose_edit_prompt(article), IDEAS_SYSTEM_PROMPT, max_tokens=6500)
            article = parse_json_object(raw_edit)
            article["generation_mode"] = "ai"
            return article
        except Exception as exc:
            print(f"  [WARN] AI generation failed, using fallback: {redact(exc)}")
    article = fallback_article_from_dossier(dossier)
    article["generation_mode"] = "ai_failed_fallback"
    return article


def fetch_article_text(url: str) -> str:
    if not url or requests is None:
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": "LightTowerIdeas/1.0"}, timeout=10)
        response.raise_for_status()
        if trafilatura is not None:
            extracted = trafilatura.extract(response.text, include_comments=False, include_tables=False)
            if extracted:
                return clean_text(extracted)[:6000]
        return clean_text(response.text)[:4000]
    except Exception as exc:
        print(f"  [WARN] Source fetch failed: {redact(exc)}")
        return ""


def call_deepseek(prompt: str, system: str, *, max_tokens: int) -> str:
    if requests is None:
        raise RuntimeError("requests unavailable")
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.35,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def normalize_article(article: dict[str, Any], idea: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    date_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    title = clean_text(article.get("title") or idea["title"])
    slug = slugify(title)
    body = article.get("body_html", "")
    sources = [{"name": idea.get("source", "Source"), "url": idea.get("url", "#")}]
    normalized = {
        **article,
        "slug": slug,
        "title": title,
        "subtitle": clean_text(article.get("subtitle") or "A Light Tower Ideas essay."),
        "excerpt": clean_text(article.get("excerpt") or article.get("meta_description") or title),
        "meta_description": truncate_clean(clean_text(article.get("meta_description") or article.get("excerpt") or title), 155),
        "seo_title": truncate_clean(clean_text(article.get("seo_title") or title), 65),
        "body_html": body,
        "tags": article.get("tags") or ["Ideas", "Built World", "Capital", "Place"],
        "sources": sources,
        "date_iso": date_iso,
        "date": datetime.now().strftime("%B %d, %Y"),
        "reading_time": max(5, round(len(strip_html(body).split()) / 220)),
        "idea_score": dossier.get("idea_score", idea.get("ideas_score", {}).get("total_score", 0)),
        "quality_score": float(article.get("quality_score", 7.0)),
        "risk_score": float(article.get("risk_score", dossier.get("risk_score", 2.0))),
        "status": "published",
        "generated_at": date_iso,
    }
    assert_no_mojibake("article", normalized)
    return normalized


def publish_articles(articles: list[dict[str, Any]]) -> None:
    IDEAS_DIR.mkdir(parents=True, exist_ok=True)
    (IDEAS_DIR / "feed.xml").parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    for article in articles:
        html_doc = article.pop("_html")
        dossier = article.pop("_dossier")
        out = IDEAS_DIR / f"{article['slug']}.html"
        out.write_text(html_doc, encoding="utf-8")
        write_json(DATA_ROOT / "published" / f"{article['slug']}.json", public_article(article))
        write_json(DATA_ROOT / "internal" / "dossiers" / f"{article['slug']}.json", dossier)
        write_social_package(article)
        manifest = update_manifest(article, MANIFEST)
        print(f"  Saved: {out.relative_to(SITE_ROOT)}")
    if not manifest:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    (SITE_ROOT / "ideas.html").write_text(render_hub(manifest), encoding="utf-8")
    (IDEAS_DIR / "feed.xml").write_text(render_ideas_feed(manifest), encoding="utf-8")
    update_sitemap(SITE_ROOT / "sitemap.xml", manifest)
    print("  Updated: ideas.html, ideas/feed.xml, sitemap.xml")


def write_social_package(article: dict[str, Any]) -> None:
    package = {
        "slug": article["slug"],
        "title": article["title"],
        "url": f"{SITE_URL}/ideas/{article['slug']}.html",
        "linkedin_hook": article["excerpt"],
        "linkedin_post": f"{article['title']}\n\n{article['excerpt']}\n\nRead: {SITE_URL}/ideas/{article['slug']}.html",
        "first_comment": "Buildings are not just assets. They are arguments about how people should live.",
        "pull_quotes": extract_pull_quotes(article.get("body_html", "")),
        "carousel_concept": "Scene to system: visible building, capital logic, power structure, design argument, human meaning.",
    }
    write_json(DATA_ROOT / "social" / f"{article['slug']}.json", package)


def save_daily_ten(ranked: list[dict[str, Any]], start: datetime) -> None:
    payload = {
        "date": start.date().isoformat(),
        "generated_at": start.isoformat(),
        "candidate_count": len(ranked),
        "ranked_ideas": ranked[:25],
    }
    write_json(DATA_ROOT / "internal" / "daily-ten" / f"{start.date().isoformat()}.json", payload)


def save_run_log(start: datetime, args: argparse.Namespace, stories: list, candidates: list, ranked: list, articles: list, held: list) -> None:
    payload = {
        "run_at": start.isoformat(),
        "mode": "publish" if args.publish else "dry-run",
        "offline": args.offline,
        "no_ai": args.no_ai,
        "raw_count": len(stories),
        "candidate_count": len(candidates),
        "ranked_count": len(ranked),
        "published_count": len(articles) if args.publish else 0,
        "preview_count": len(articles) if not args.publish else 0,
        "held_count": len(held),
        "articles": [{"title": item["title"], "slug": item["slug"]} for item in articles],
    }
    write_json(DATA_ROOT / "internal" / "logs" / f"{start.strftime('%Y-%m-%d-%H%M%S')}.json", payload)


def public_article(article: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in article.items() if not k.startswith("_")}


def clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def truncate_clean(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if len(value) <= limit:
        return value
    clipped = value[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return clipped or value[:limit].rstrip()


def parse_entry_date(entry: Any) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def keyword_score(text: str, words: list[str], base: float, bump: float) -> float:
    text_l = text.lower()
    hits = sum(1 for word in words if word.lower() in text_l)
    return min(10.0, base + hits * bump)


def slugify(text: str) -> str:
    slug = text.lower().replace("&", " and ")
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    if len(slug) > 90:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        slug = slug[:80].strip("-") + "-" + digest
    return slug or "idea"


def infer_phrase(text: str, words: list[str], fallback: str) -> str:
    matches = [word for word in words if word.lower() in text.lower()]
    if not matches:
        return fallback
    return ", ".join(matches[:4])


def parse_json_object(raw: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group())


def redact(value: object) -> str:
    text = str(value)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text, flags=re.I)
    text = re.sub(r"\bsk-[A-Za-z0-9._-]+", "sk-[REDACTED]", text)
    text = re.sub(r"([?&](?:apiKey|key|token)=)[^&\s]+", r"\1[REDACTED]", text, flags=re.I)
    return text


def extract_pull_quotes(body_html: str) -> list[str]:
    text = strip_html(body_html)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sentences if 80 <= len(s) <= 180][:4]


if __name__ == "__main__":
    raise SystemExit(main())
