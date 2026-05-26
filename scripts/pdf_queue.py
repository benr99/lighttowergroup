"""
Async PDF generation queue.

Generates PDFs in the background after articles are published.
Does not block article publishing.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict

from fetch_brand_colors import fetch_brand_colors
from article_adapter import transform_article_to_pdf_schema
from generate_carousel_pdf import CarouselPDFGenerator
from build_linkedin_post import build_linkedin_post_text, save_linkedin_post
from validate_pdf import run_validation_report

logger = logging.getLogger(__name__)


async def generate_pdf_async(article_html: str, article_data: Dict, output_dir: str) -> bool:
    """
    Generate PDF in background (async, non-blocking).

    This function is called AFTER the article is already published to /insights/
    It does not block article publishing and failures are logged but not fatal.

    Args:
        article_html: Full HTML of the published article
        article_data: Article metadata (headline, slug, date, body, etc.)
        output_dir: Directory to save PDF and post text

    Returns:
        bool: True if successful, False otherwise
    """
    slug = article_data.get('slug', 'unknown')

    try:
        logger.info(f"[PDF] Starting carousel generation for: {slug}")

        # 1. Transform article to PDF schema
        pdf_schema = transform_article_to_pdf_schema(
            article_html,
            article_data
        )

        # 2. Fetch live brand colors
        colors = fetch_brand_colors()

        # 3. Generate PDF
        generator = CarouselPDFGenerator(colors)
        pdf_path = f"{output_dir}/{slug}_carousel.pdf"

        success = await generator.generate_pdf(pdf_schema, pdf_path)

        if not success:
            logger.error(f"[PDF] Generation failed for {slug}")
            return False

        # 4. Validate PDF
        validation = run_validation_report(pdf_path, pdf_schema)
        if not validation['valid']:
            logger.warning(f"[PDF] Validation warnings for {slug}: {validation['errors']}")

        # 5. Generate LinkedIn post text
        post_text = build_linkedin_post_text(pdf_schema)
        post_path = f"{output_dir}/linkedin-post-{slug}.txt"
        save_linkedin_post(post_text, post_path)

        # 6. Save the PDF schema for reference
        schema_path = f"{output_dir}/{slug}_carousel-data.json"
        Path(schema_path).write_text(json.dumps(pdf_schema, indent=2))

        logger.info(f"[PDF] ✓ Complete: {pdf_path}")
        logger.info(f"[PDF] ✓ Post: {post_path}")

        return True

    except Exception as e:
        logger.error(f"[PDF] Exception for {slug}: {str(e)}", exc_info=True)
        return False


def queue_pdf_generation(article_html: str, article_data: Dict, output_dir: str):
    """
    Queue a PDF for generation in the background.

    Safe to call immediately after publishing an article.
    The PDF will be generated asynchronously without blocking the caller.

    Args:
        article_html: Full HTML of the published article
        article_data: Article metadata
        output_dir: Directory to save outputs
    """
    # Create task to run in background
    # This requires being called from within an async context or event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create task
            loop.create_task(
                generate_pdf_async(article_html, article_data, output_dir)
            )
        else:
            # Not in async context, schedule on event loop
            asyncio.ensure_future(
                generate_pdf_async(article_html, article_data, output_dir)
            )
    except RuntimeError:
        # No event loop exists, create one (for sync context)
        logger.info(f"[PDF] Creating event loop for {article_data.get('slug')}")
        asyncio.run(
            generate_pdf_async(article_html, article_data, output_dir)
        )


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python pdf_queue.py <article_html> <article_data.json> <output_dir>")
        sys.exit(1)

    html_path = sys.argv[1]
    data_path = sys.argv[2]
    output_dir = sys.argv[3]

    with open(html_path) as f:
        html = f.read()

    with open(data_path) as f:
        data = json.load(f)

    success = asyncio.run(generate_pdf_async(html, data, output_dir))
    sys.exit(0 if success else 1)
