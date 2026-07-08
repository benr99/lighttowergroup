#!/usr/bin/env python3
"""
Light Tower Group PDF Carousel Generator - REDESIGNED
Creates premium, beautifully-designed carousels for LinkedIn.

DESIGN IMPROVEMENTS:
- Serif fonts (Playfair Display) for headlines
- Centered, larger text (easy to read on mobile)
- Cream gradient background (alive, not flat)
- Ben's headshot + bio on first slide
- No page numbers (cleaner aesthetic)
- Premium luxury feel throughout
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

LTG_COLORS = {
    "bg": "#f5f4f0",           # Warm cream
    "bg_light": "#faf9f6",     # Lighter cream (for gradient)
    "text": "#121212",         # Near black
    "text_light": "#333333",   # Softer text
    "accent": "#c9a84c",       # Champagne gold
    "muted": "#666666",        # Gray
}

PAGE_W = 108
PAGE_H = 135
MARGIN = 8
CONTENT_WIDTH = 80  # Centered content block width


class CarouselPDFGenerator:
    """Premium carousel PDF generator with beautiful design."""

    def __init__(self, headshot_path: str | None = None, output_dir: str | None = None):
        self.headshot_path = Path(headshot_path or ASSETS_DIR / "ben-rohr-headshot.jpg")
        self.output_dir = Path(output_dir) if output_dir else SITE_ROOT
        self.colors = LTG_COLORS
        self.font_body = "Helvetica"
        self.font_display = "Times"

    def create_carousel_pdf(self, carousel_content: dict[str, Any], output_path: str | None = None) -> str:
        """Create PDF carousel."""
        if output_path is None:
            title_slug = carousel_content.get("carousel_title", "carousel").lower().replace(" ", "-")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"carousel_{title_slug}_{timestamp}.pdf"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        slides = carousel_content.get("slides", [])
        self._create_pdf(slides, str(output_path))
        return str(output_path)

    def _create_pdf(self, slides: list[dict[str, Any]], pdf_path: str) -> None:
        """Create PDF with all slides."""
        pdf = FPDF(unit="mm", format=(PAGE_W, PAGE_H))
        pdf.set_auto_page_break(False)
        self._load_fonts(pdf)

        for idx, slide in enumerate(slides):
            slide_type = slide.get("slide_type", "content")
            if slide_type == "cover":
                self._draw_cover(pdf, slide)
            else:
                self._draw_content(pdf, slide)

        pdf.output(pdf_path)

    def _load_fonts(self, pdf: FPDF) -> None:
        """Load Light Tower fonts."""
        try:
            pdf.add_font("SpaceGrotesk", "", str(FONT_DIR / "SpaceGrotesk-Regular.ttf"), uni=True)
            pdf.add_font("SpaceGrotesk", "B", str(FONT_DIR / "SpaceGrotesk-Bold.ttf"), uni=True)
            pdf.add_font("Playfair", "B", str(FONT_DIR / "PlayfairDisplay-Bold.ttf"), uni=True)
            self.font_body = "SpaceGrotesk"
            self.font_display = "Playfair"
        except Exception:
            pass

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex to RGB."""
        color = (hex_color or "#000000").strip().lstrip("#")
        if len(color) != 6:
            color = "000000"
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

    def _sanitize(self, text: str) -> str:
        """Clean problematic characters."""
        replacements = {
            "\u2014": "-",
            "\u2013": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "*",
            "\u2026": "...",
            "\u00a0": " ",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        text = unicodedata.normalize("NFKD", text)
        return text.encode("ascii", errors="ignore").decode("ascii").strip()

    def _gradient_background(self, pdf: FPDF) -> None:
        """Draw cream gradient (warm, alive)."""
        r1, g1, b1 = self._hex_to_rgb(self.colors["bg"])
        r2, g2, b2 = self._hex_to_rgb(self.colors["bg_light"])

        band_height = PAGE_H / 12
        for i in range(12):
            ratio = i / 12
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            pdf.set_fill_color(r, g, b)
            pdf.rect(0, i * band_height, PAGE_W, band_height, "F")

    def _draw_cover(self, pdf: FPDF, slide: dict[str, Any]) -> None:
        """Draw cover slide - headshot LEFT, text RIGHT (side-by-side)."""
        pdf.add_page()
        self._gradient_background(pdf)

        # Calculate centered content block
        content_x = (PAGE_W - CONTENT_WIDTH) / 2
        headshot_size = 18
        headshot_x = content_x
        text_x = content_x + headshot_size + 4  # Headshot + small gap
        text_width = CONTENT_WIDTH - headshot_size - 4

        y = 20

        # Headshot (LEFT side)
        try:
            if self.headshot_path.exists():
                pdf.image(str(self.headshot_path), headshot_x, y, w=headshot_size, h=headshot_size)
        except Exception:
            pass

        # Name (RIGHT side, next to headshot)
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "B", 8)
        pdf.set_xy(text_x, y + 1)
        pdf.multi_cell(text_width, 2.5, "Benjamin Rohr", align="L")

        # Title (RIGHT side, next to headshot)
        pdf.set_font(self.font_body, "", 6)
        r, g, b = self._hex_to_rgb(self.colors["muted"])
        pdf.set_text_color(r, g, b)
        pdf.set_xy(text_x, y + 4)
        pdf.multi_cell(text_width, 2, "Principal, Light Tower Group", align="L")

        # Main headline (large serif, LEFT-ALIGNED WITHIN centered block)
        y = PAGE_H * 0.38
        headline = self._sanitize(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_display, "B", 18)
        pdf.set_xy(content_x, y)
        pdf.multi_cell(CONTENT_WIDTH, 5.8, headline, align="L")

        # Subtitle (gold accent, LEFT-ALIGNED WITHIN centered block)
        y = PAGE_H * 0.70
        body = self._sanitize(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "", 10)
        pdf.set_xy(content_x, y)
        pdf.multi_cell(CONTENT_WIDTH, 4.3, body, align="L")

    def _draw_content(self, pdf: FPDF, slide: dict[str, Any]) -> None:
        """Draw content slide - centered block, left-aligned text inside."""
        pdf.add_page()
        self._gradient_background(pdf)

        # Calculate centered content block position
        content_x = (PAGE_W - CONTENT_WIDTH) / 2

        # Eyebrow (small, left-aligned WITHIN centered block, gold)
        eyebrow = self._sanitize(slide.get("eyebrow", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "B", 7.5)
        pdf.set_xy(content_x, 8)
        pdf.multi_cell(CONTENT_WIDTH, 2.5, eyebrow, align="L")

        # Headline (large serif, left-aligned WITHIN centered block)
        headline = self._sanitize(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_display, "B", 16)
        pdf.set_xy(content_x, 13)
        pdf.multi_cell(CONTENT_WIDTH, 5.2, headline, align="L")

        # Body (readable, left-aligned WITHIN centered block, bigger)
        body = self._sanitize(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "", 11)
        pdf.set_xy(content_x, 37)
        pdf.multi_cell(CONTENT_WIDTH, 4.5, body, align="L")


def main() -> None:
    parser = argparse.ArgumentParser(description="Light Tower PDF Carousel Generator")
    parser.add_argument("--content", required=True, help="Path to carousel content JSON")
    parser.add_argument("--output", help="Output PDF path")
    args = parser.parse_args()

    with open(args.content, encoding="utf-8-sig") as f:
        carousel_content = json.load(f)

    generator = CarouselPDFGenerator()
    pdf_path = generator.create_carousel_pdf(carousel_content, output_path=args.output)
    print(f"PDF created: {pdf_path}")


if __name__ == "__main__":
    main()

