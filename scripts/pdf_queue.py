"""Create the single LinkedIn document PDF for each finished Insight.

The daily workflow intentionally produces an article PDF, rather than a
carousel rewrite: the published prose is the source of truth.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict

from pypdf import PdfReader

from article_pdf_generator import build_article_pdf, extract_article_paragraphs


logger = logging.getLogger(__name__)


def _linkedin_post_text(article_data: Dict) -> str:
    title = str(article_data.get("title") or "Light Tower Insight").strip()
    subtitle = str(article_data.get("subtitle") or article_data.get("excerpt") or "").strip()
    slug = str(article_data.get("slug") or "").strip()
    url = f"https://lighttowergroup.co/insights/{slug}.html" if slug else "https://lighttowergroup.co/insights/"
    lines = [title]
    if subtitle:
        lines.extend(["", subtitle])
    lines.extend(["", "The complete note is attached as a PDF.", "", url])
    return "\n".join(lines)


def _validate_article_pdf(pdf_path: Path) -> int:
    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    if page_count < 2:
        raise ValueError("Article PDF must include a cover and at least one reading page")
    if not reader.pages[1].extract_text().strip():
        raise ValueError("Article PDF body page contains no extractable text")
    return page_count


async def generate_article_pdf_async(article_html: str, article_data: Dict, output_dir: str) -> bool:
    """Generate and validate a clean article PDF plus a LinkedIn caption."""
    slug = str(article_data.get("slug") or "unknown")
    try:
        output = Path(output_dir)
        pdf_path = output / f"{slug}_article.pdf"
        logger.info("[PDF] Rendering article document for: %s", slug)
        build_article_pdf(article_html, article_data, pdf_path)
        page_count = _validate_article_pdf(pdf_path)

        (output / f"linkedin-post-{slug}.txt").write_text(
            _linkedin_post_text(article_data), encoding="utf-8"
        )
        metadata = {
            "artifact": "article_pdf",
            "source_slug": slug,
            "paragraph_count": len(extract_article_paragraphs(article_html, article_data)),
            "page_count": page_count,
            "rewrite_disabled": True,
        }
        (output / f"{slug}_article-data.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        logger.info("[PDF] Complete: %s (%s pages)", pdf_path, page_count)
        return True
    except Exception as exc:
        logger.error("[PDF] Exception for %s: %s", slug, exc, exc_info=True)
        return False


def queue_article_pdf_generation(article_html: str, article_data: Dict, output_dir: str) -> None:
    """Run article PDF creation safely from synchronous or asynchronous callers."""
    coroutine = generate_article_pdf_async(article_html, article_data, output_dir)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coroutine)
        else:
            loop.run_until_complete(coroutine)
    except RuntimeError:
        asyncio.run(coroutine)


# Backward-compatible import for callers outside the daily workflow.
queue_pdf_generation = queue_article_pdf_generation
