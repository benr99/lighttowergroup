#!/usr/bin/env python3
"""
Light Tower Group Social Media Pipeline (2026)

Master orchestration script that:
1. Takes a finished article insight
2. Analyzes optimal format(s) via Social Strategy Selector
3. Generates LinkedIn Thread (5-8 punchy posts)
4. Generates optimized Carousel (9-slide PDF)
5. Outputs both formats ready for publishing

ARTICLE GENERATION (enhanced_prompts.py) → UNTOUCHED
                    ↓
SOCIAL STRATEGY SELECTOR (social_strategy_selector.py) → Recommends format(s)
                    ↓
THREAD AGENT (linkedin_thread_agent.py) → 5-8 punchy posts
                    ↓
CAROUSEL AGENT (carousel_script_agent_2026.py) → 9-slide optimized carousel
                    ↓
PUBLISH → Thread posts + Carousel PDF ready to go
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import agents
sys.path.insert(0, str(Path(__file__).parent))

from linkedin_thread_agent import generate_thread_package, save_thread_to_queue
from carousel_script_agent_2026 import generate_carousel_script
from social_strategy_selector import recommend_format
from article_adapter import transform_article_to_pdf_schema

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"
PIPELINE_OUTPUT = SITE_ROOT / "social_pipeline_output.json"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def load_manifest() -> list[dict[str, Any]]:
    """Load insights manifest."""
    if not INSIGHTS_JSON.exists():
        return []
    return json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))


def select_article(slug: str | None = None) -> dict[str, Any]:
    """Select an article from manifest."""
    manifest = load_manifest()
    if not manifest:
        raise FileNotFoundError("No insights.json entries")
    if slug:
        for article in manifest:
            if article.get("slug") == slug:
                return article
        raise ValueError(f"Slug not found: {slug}")
    return manifest[0]


def load_article_html(slug: str) -> str:
    """Load article HTML."""
    path = INSIGHTS_DIR / f"{slug}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def load_article_text(slug: str, article_data: dict[str, Any]) -> str:
    """Extract article text for strategy analysis."""
    html = load_article_html(slug)
    if html:
        match = re.search(
            r'<div\s+class="article-body"[^>]*>([\s\S]*?)</div>',
            html,
            flags=re.IGNORECASE,
        )
        article_html = match.group(1) if match else html
        article_html = re.sub(r"<script[\s\S]*?</script>", " ", article_html, flags=re.IGNORECASE)
        article_html = re.sub(r"<style[\s\S]*?</style>", " ", article_html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", article_html)
        text = html_lib.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    return article_data.get("body_text", "")


def build_fallback_carousel_schema(article_data: dict[str, Any]) -> dict[str, Any]:
    """Build fallback carousel schema for validation."""
    html = load_article_html(article_data.get("slug", ""))
    if html:
        try:
            return transform_article_to_pdf_schema(html, article_data)
        except Exception as exc:
            print(f"  [WARN] Rich fallback carousel failed: {exc}")

    return transform_article_to_pdf_schema(
        article_data.get("excerpt") or article_data.get("subtitle") or article_data.get("title", ""),
        article_data,
    )


def run_social_pipeline(
    slug: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    offline: bool = False,
) -> dict[str, Any]:
    """
    Run the complete 2026 social media pipeline for an insight.

    Returns: Dict with thread package, carousel schema, and strategy recommendation.
    """
    # Step 1: Load article
    print("\n" + "=" * 80)
    print("LIGHT TOWER GROUP SOCIAL PIPELINE 2026")
    print("=" * 80)
    api_key = "" if offline else DEEPSEEK_API_KEY
    if offline:
        print("\nOffline/no-AI mode enabled. Using deterministic fallbacks only.")

    article = select_article(slug)
    slug = article.get("slug", "unknown")
    print(f"\n✓ Loaded article: {article.get('title', 'Untitled')}")
    print(f"  Slug: {slug}")
    print(f"  Category: {article.get('category', 'N/A')}")

    # Step 2: Analyze strategy
    print("\n[1/4] ANALYZING STRATEGY...")
    article_text = load_article_text(slug, article)
    if not article_text:
        article_text = article.get("excerpt", "") or article.get("subtitle", "")

    try:
        strategy = recommend_format(article_text, article, api_key=api_key)
        print(f"  → Primary format: {strategy.get('primary_format', 'unknown').upper()}")
        print(f"  → Engagement potential: {strategy.get('engagement_potential', 'medium')}")
        print(f"  → Lead potential: {strategy.get('lead_potential', 'medium')}")
        print(f"  → Rationale: {strategy.get('rationale', 'N/A')}")
    except Exception as e:
        print(f"  [WARN] Strategy analysis failed: {e}")
        strategy = {"primary_format": "carousel", "method": "fallback"}

    # Step 3: Generate thread
    print("\n[2/4] GENERATING THREAD (5-8 posts)...")
    try:
        thread_package = generate_thread_package(article, api_key=api_key)
        num_posts = len(thread_package.get("posts", []))
        print(f"  ✓ Generated {num_posts} thread posts")
        print(f"    Posts generated:")
        for i, post in enumerate(thread_package.get("posts", [])[:3], 1):
            preview = post.get("post_text", "")[:60].replace("\n", " ") + "..."
            print(f"      [{i}] {preview}")
        if num_posts > 3:
            print(f"      ... and {num_posts - 3} more posts")
    except Exception as e:
        print(f"  [ERROR] Thread generation failed: {e}")
        thread_package = None

    # Step 4: Generate carousel
    print("\n[3/4] GENERATING CAROUSEL (9 slides)...")
    try:
        html = load_article_html(slug)
        fallback_schema = build_fallback_carousel_schema(article)

        carousel_schema = generate_carousel_script(
            html,
            article,
            fallback_schema,
            api_key=api_key,
        )

        num_slides = len(carousel_schema.get("slides", []))
        print(f"  ✓ Generated {num_slides}-slide carousel")

        # Show carousel structure
        slides_info = carousel_schema.get("slides", [])
        for slide in slides_info[:3]:
            headline = slide.get("headline", "")[:50]
            print(f"      [{slide.get('system', 'unknown')}] {headline}")
        if num_slides > 3:
            print(f"      ... and {num_slides - 3} more slides")

    except Exception as e:
        print(f"  [ERROR] Carousel generation failed: {e}")
        carousel_schema = None

    # Step 5: Compile results
    print("\n[4/4] COMPILING OUTPUT...")

    pipeline_result = {
        "article": {
            "slug": slug,
            "title": article.get("title", ""),
            "category": article.get("category", ""),
            "date": article.get("date", ""),
        },
        "strategy": strategy,
        "thread": thread_package if thread_package else {"error": "Generation failed"},
        "carousel": carousel_schema if carousel_schema else {"error": "Generation failed"},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "2026_v1",
        "offline": offline,
    }

    # Step 6: Save and display
    if not dry_run:
        output_path = PIPELINE_OUTPUT
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to pipeline output log
        pipeline_log = []
        if output_path.exists():
            try:
                pipeline_log = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception:
                pipeline_log = []

        pipeline_log.insert(0, pipeline_result)
        pipeline_log = pipeline_log[:100]  # Keep last 100

        output_path.write_text(json.dumps(pipeline_log, indent=2, ensure_ascii=False), encoding="utf-8")

        # Also save individual packages to queues
        if thread_package and "error" not in thread_package and thread_package.get("publish_ready"):
            try:
                save_thread_to_queue(thread_package)
                print(f"  ✓ Saved thread package to linkedin_thread_queue.json")
            except Exception as e:
                print(f"  [WARN] Could not save thread queue: {e}")

        elif thread_package and "error" not in thread_package:
            print("  [HOLD] Thread needs editorial revision; it was not added to the publishing queue.")

        print(f"  ✓ Pipeline output saved to {output_path.name}")

    # Step 7: Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Article: {article.get('title', 'Untitled')}")
    print(f"Strategy: {strategy.get('primary_format', 'unknown').upper()}")

    if thread_package and "error" not in thread_package and thread_package.get("publish_ready"):
        thread_posts = len(thread_package.get("posts", []))
        print(f"Thread: {thread_posts} posts ready")
    elif thread_package and "error" not in thread_package:
        print("Thread: held for editorial revision")
    else:
        print(f"Thread: ✗ Failed")

    if carousel_schema and "error" not in carousel_schema and carousel_schema.get("publish_ready"):
        carousel_slides = len(carousel_schema.get("slides", []))
        print(f"Carousel: {carousel_slides} slides ready")
    elif carousel_schema and "error" not in carousel_schema:
        print("Carousel: held for editorial revision")
    else:
        print(f"Carousel: ✗ Failed")

    print("\n✓ Pipeline complete. Ready for publishing.")
    print("=" * 80 + "\n")

    return pipeline_result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Light Tower Group Social Media Pipeline (2026)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_social_pipeline_2026.py                          # Run on latest insight
  python run_social_pipeline_2026.py --slug tuscan-village    # Run on specific insight
  python run_social_pipeline_2026.py --slug tuscan-village --dry-run
  python run_social_pipeline_2026.py --latest --verbose
        """,
    )
    parser.add_argument("--slug", help="Process specific insight (default: latest)")
    parser.add_argument("--latest", action="store_true", help="Process latest insight")
    parser.add_argument("--dry-run", action="store_true", help="Print output without saving")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--offline", "--no-ai", action="store_true", help="Use deterministic fallbacks without calling external AI")

    args = parser.parse_args()

    try:
        result = run_social_pipeline(slug=args.slug, dry_run=args.dry_run, verbose=args.verbose, offline=args.offline)

        if args.dry_run:
            print("\n[DRY RUN OUTPUT]")
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
