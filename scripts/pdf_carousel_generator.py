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
            "—": "-", "–": "-", "'": "'", "'": "'",
            """: '"', """: '"', "•": "*", "…": "...", " ": " ",
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
        """Draw cover slide with headshot and bio."""
        pdf.add_page()
        self._gradient_background(pdf)

        y = 6

        # Headshot (centered, small circle)
        headshot_size = 14
        try:
            if self.headshot_path.exists():
                x_pos = (PAGE_W - headshot_size) / 2
                pdf.image(str(self.headshot_path), x_pos, y, w=headshot_size, h=headshot_size)
                y += headshot_size + 2
        except Exception:
            y += 16

        # Name (centered)
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(PAGE_W - (MARGIN * 2), 3, "Benjamin Rohr", align="C")
        y += 4

        # Title (centered, smaller)
        pdf.set_font(self.font_body, "", 6)
        r, g, b = self._hex_to_rgb(self.colors["muted"])
        pdf.set_text_color(r, g, b)
        pdf.set_xy(MARGIN, y)
        pdf.cell(PAGE_W - (MARGIN * 2), 2.5, "Principal, Light Tower Group", align="C")

        # Main headline (large, serif, centered)
        y = PAGE_H * 0.42
        headline = self._sanitize(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_display, "B", 20)
        pdf.set_xy(MARGIN, y)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 6.5, headline, align="C")

        # Subtitle (gold accent)
        y = PAGE_H * 0.75
        body = self._sanitize(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "", 9)
        pdf.set_xy(MARGIN, y)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 4, body, align="C")

    def _draw_content(self, pdf: FPDF, slide: dict[str, Any]) -> None:
        """Draw content slide (centered, large text)."""
        pdf.add_page()
        self._gradient_background(pdf)

        # Eyebrow (small, centered, gold)
        eyebrow = self._sanitize(slide.get("eyebrow", ""))
        r, g, b = self._hex_to_rgb(self.colors["accent"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "B", 7)
        pdf.set_xy(MARGIN, 8)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 2.5, eyebrow, align="C")

        # Headline (large serif, centered)
        headline = self._sanitize(slide.get("headline", ""))
        r, g, b = self._hex_to_rgb(self.colors["text"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_display, "B", 17)
        pdf.set_xy(MARGIN, 14)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 5.5, headline, align="C")

        # Body (readable, centered)
        body = self._sanitize(slide.get("body", ""))
        r, g, b = self._hex_to_rgb(self.colors["text_light"])
        pdf.set_text_color(r, g, b)
        pdf.set_font(self.font_body, "", 10.5)
        pdf.set_xy(MARGIN, 38)
        pdf.multi_cell(PAGE_W - (MARGIN * 2), 4.5, body, align="C")


def main() -> None:
    parser = argparse.ArgumentParser(description="Light Tower PDF Carousel Generator")
    parser.add_argument("--content", required=True, help="Path to carousel content JSON")
    parser.add_argument("--output", help="Output PDF path")
    args = parser.parse_args()

    with open(args.content) as f:
        carousel_content = json.load(f)

    generator = CarouselPDFGenerator()
    pdf_path = generator.create_carousel_pdf(carousel_content, output_path=args.output)
    print(f"✓ PDF created: {pdf_path}")


if __name__ == "__main__":
    main()
