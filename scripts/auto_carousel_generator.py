#!/usr/bin/env python3
"""
Automatic PDF Carousel Generator - Post-Article Integration

This script is called automatically after each article is generated.

It creates the carousel PDF and saves it to insights/{slug}_carousel.pdf
so the LinkedIn share button can access it immediately.

Usage:
  python auto_carousel_generator.py --slug ARTICLE_SLUG

Integrated into article generation workflow:
  1. Article generated (enhanced_prompts.py)
  2. This script runs automatically
  3. Carousel content created (Ben Rohr voice)
  4. PDF generated and saved
  5. LinkedIn share button ready to go
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_JSON = SITE_ROOT / "insights.json"
INSIGHTS_DIR = SITE_ROOT / "insights"

# Import pipeline components
sys.path.insert(0, str(SCRIPT_DIR))
from carousel_content_writer import generate_carousel_content
from pdf_carousel_generator import CarouselPDFGenerator

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

_env = SCRIPT_DIR / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)


def load_article_text(slug: str, article_data: dict[str, Any]) -> str:
    """Load article text from HTML file or article data."""
    html_path = INSIGHTS_DIR / f"{slug}.html"
    if html_path.exists():
        import re
        html = html_path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&apos;", "'", text)
        text = re.sub(r"&amp;", "&", text)
        return text

    return article_data.get("body_text", "")


def generate_carousel_for_article(slug: str, dry_run: bool = False) -> str | None:
    """
    Generate PDF carousel for an article.

    Returns: Path to generated PDF, or None if failed
    """
    # Load article from insights.json
    if not INSIGHTS_JSON.exists():
        logger.error("insights.json not found")
        return None

    manifest = json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))
    article = None

    for item in manifest:
        if item.get("slug") == slug:
            article = item
            break

    if not article:
        logger.error(f"Article with slug '{slug}' not found in insights.json")
        return None

    logger.info(f"✓ Article found: {article.get('title', 'Untitled')[:60]}")

    # Step 1: Load article text
    article_text = load_article_text(slug, article)
    if not article_text:
        article_text = article.get("excerpt", "") or article.get("subtitle", "")

    if not article_text:
        logger.error("Could not load article text")
        return None

    # Step 2: Generate carousel content
    logger.info("Generating carousel content...")
    try:
        if not DEEPSEEK_API_KEY:
            logger.warning("DEEPSEEK_API_KEY not set. Cannot generate carousel content.")
            return None

        carousel_content = generate_carousel_content(
            article,
            article_text=article_text,
            api_key=DEEPSEEK_API_KEY,
        )
        num_slides = len(carousel_content.get("slides", []))
        logger.info(f"✓ Generated {num_slides} slides")

    except Exception as e:
        logger.error(f"Carousel content generation failed: {e}")
        return None

    # Step 3: Generate PDF
    logger.info("Generating PDF...")
    try:
        generator = CarouselPDFGenerator(output_dir=str(INSIGHTS_DIR))

        # Generate PDF with the naming convention: {slug}_carousel.pdf
        pdf_filename = f"{slug}_carousel.pdf"
        pdf_path = INSIGHTS_DIR / pdf_filename

        pdf_full_path = generator.create_carousel_pdf(carousel_content, output_path=str(pdf_path))
        logger.info(f"✓ PDF saved: {pdf_filename}")

        if dry_run:
            logger.info("[DRY RUN] Would have saved PDF. File not actually created.")
            return None

        return pdf_full_path

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically generate PDF carousel for an article",
        epilog="This script is called automatically after article generation.",
    )
    parser.add_argument("--slug", required=True, help="Article slug")
    parser.add_argument("--dry-run", action="store_true", help="Show output without saving")

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("AUTO CAROUSEL GENERATOR")
    logger.info("=" * 80)
    logger.info("")

    pdf_path = generate_carousel_for_article(args.slug, dry_run=args.dry_run)

    logger.info("")
    if pdf_path:
        logger.info("✓ Carousel PDF ready for LinkedIn share button")
        logger.info("=" * 80)
        logger.info("")
        return 0
    else:
        logger.error("Failed to generate carousel PDF")
        logger.info("=" * 80)
        logger.info("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
