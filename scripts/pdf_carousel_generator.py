#!/usr/bin/env python3
"""
Light Tower Group PDF Carousel Generator (FPDF-based)

Creates premium, luxury-style PDF carousels for LinkedIn distribution.
Uses FPDF library (compatible with existing codebase).

Format: 108mm × 135mm portrait (mobile-optimized)
Style: Warm capital markets intelligence briefing
Brand: Light Tower Group visual identity
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = SITE_ROOT / "assets"
FONT_DIR = SCRIPT_DIR / "fonts"

# Light Tower Group Brand Colors
LTG_COLORS = {
    "bg": "#f5f4f0",           # Warm ivory background
    "surface": "#ffffff",      # White
    "text": "#121212",         # Near black
    "muted": "#555555",        # Gray
    "soft": "#777777",         # Lighter gray
    "accent": "#c9a84c",       # Champagne gold
    "accent_hover": "#d9b85c", # Lighter gold
    "dark": "#0e0e0e",         # Very dark
}

# FPDF page dimensions (in mm)
PAGE_W = 108  # ~1080px at 254 DPI
PAGE_H = 135  # ~1350px at 254 DPI
MARGIN = 9    # ~90px margins


class CarouselPDFGenerator:
    """Generates premium PDF carousels from slide content using FPDF."""

    def __init__(self, headshot_path: str | None = None, output_dir: str | None = None):
        """Initialize PDF generator."""
        self.headshot_path = headshot_path or ASSETS_DIR / "ben-rohr-headshot.jpg"
        self.output_dir = Path(output_dir) if output_dir else SITE_ROOT
        self.colors = LTG_COLORS

    def create_carousel_pdf(self, carousel_content: dict[str, Any], output_path: str | None = None) -> str:
        """Create a PDF carousel from slide content."""
        if output_path is None:
            title_slug = carousel_content.get("carousel_title", "carousel").lower().replace(" ", "-")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"carousel_{title_slug}_{timestamp}.pdf"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        slides = carousel_content.get("slides", [])
        self._create_pdf_from_slides(slides, str(output_path))
        return str(output_path)

    def _create_pdf_from_slides(self, slides: list[dict[str, Any]], pdf_path: str) -> None:
        """Create PDF with multiple slides using FPDF."""
        pdf = FPDF(unit="mm", format=(PAGE_W, PAGE_H))
        pdf.set_auto_page_break(False)
        self._load_fonts(pdf)

        for slide_num, slide in enumerate(slides, 1):
            self._draw_slide(pdf, slide, slide_num, len(slides))

        pdf.output(pdf_path)

    def _load_fonts(self, pdf: FPDF) -> None:
        """Load Light Tower fonts if available."""
        try:
            pdf.add_font("SpaceGrotesk", "", str(FONT_DIR / "SpaceGrotesk-Regular.ttf"), uni=True)
            pdf.add_font("SpaceGrotesk", "B", str(FONT_DIR / "SpaceGrotesk-Bold.ttf"), uni=True)
            pdf.add_font("Playfair", "B", str(FONT_DIR / "PlayfairDisplay-Bold.ttf"), uni=True)
            self.font_body = "SpaceGrotesk"
            self.font_display = "Playfair"
        except Exception:
            self.font_body = "Helvetica"
            self.font_display = "Times"

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        color = (hex_color or "#000000").strip().lstrip("#")
        if len(color) != 6:
            color = "000000"
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _sanitize_text(self, text: str) -> str:
        """Clean text of problematic Unicode characters for PDF rendering."""
        # Replace smart quotes and dashes
        replacements = {
            "—": "-",      # em dash
            "–": "-",      # en dash
            "‘": "'",      # left single quote
            "’": "'",      # right single quote
            "“": '"',      # left double quote
            "”": '"',      # right double quote
            "•": "*",      # bullet
            "…": "...",    # ellipsis
            " ": " ",      # non-breaking space
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        # Normalize and remove other problematic chars
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", errors="ignore").decode("ascii")
        return text.strip()

    def _draw_slide(self, pdf: FPDF, slide: dict[str, Any], slide_num: int, total_slides: int) -> None:
        """Draw a single slide."""
        pdf.add_page()
        slide_type = slide.get("slide_type", "content")

        if slide_type == "cover":
            self._draw_cover_slide(pdf, slide)
        else:
            self._draw_content_slide(pdf, slide, slide_num, total_slides)

    def _draw_cover_slide(self, pdf: FPDF, slide: dict[str, Any]) -> None:
        """Draw cover slide with dark background."""
        # Dark background
        r, g, b = self._hex_to_rgb(self.colors["dark"])
        pdf.set_fill_color(r, g, b)
        pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

        # Title
        headline = self._sanitize_text(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb("#ffffff")
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_xy(MARGIN, PAGE_H * 0.4)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 8, headline, align="L")

        # Subtitle
        body = self._sanitize_text(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 5, body, align="L")

    def _draw_content_slide(self, pdf: FPDF, slide: dict[str, Any], slide_num: int, total_slides: int) -> None:
        """Draw standard content slide."""
        # Light background
        r, g, b = self._hex_to_rgb(self.colors["bg"])
        pdf.set_fill_color(r, g, b)
        pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

        # Eyebrow label
        eyebrow = self._sanitize_text(slide.get("eyebrow", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(MARGIN, MARGIN)
        pdf.cell(0, 4, eyebrow)

        # Headline
        headline = self._sanitize_text(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(MARGIN, MARGIN + 8)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 6, headline, align="L")

        # Body
        body = self._sanitize_text(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["muted"])
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(MARGIN, MARGIN + 28)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 4, body, align="L")

        # Footer
        r, g, b = self._hex_to_rgb(self.colors["muted"])
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(MARGIN, PAGE_H - MARGIN - 2)
        pdf.cell(0, 3, f"Light Tower Group  *  {slide_num}/{total_slides}", align="L")


def main() -> None:
    parser = argparse.ArgumentParser(description="Light Tower PDF Carousel Generator")
    parser.add_argument("--content", required=True, help="Path to carousel content JSON")
    parser.add_argument("--output", help="Output PDF path")

    args = parser.parse_args()

    # Load carousel content
    with open(args.content) as f:
        carousel_content = json.load(f)

    # Generate PDF
    generator = CarouselPDFGenerator()
    pdf_path = generator.create_carousel_pdf(carousel_content, output_path=args.output)

    print(f"✓ PDF created: {pdf_path}")


if __name__ == "__main__":
    main()
