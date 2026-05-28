"""
Generate LTG Capital Intelligence PDF carousels.

The renderer intentionally uses a single fpdf2 document end to end. Older
versions built one PDF per page and merged them with pypdf, which made carousel
generation fragile and dependent on an optional package.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from fpdf import FPDF


logger = logging.getLogger(__name__)

PAGE_W = 210
PAGE_H = 297
MARGIN = 16
CONTENT_W = PAGE_W - (MARGIN * 2)


class CarouselPDFGenerator:
    """Generate a polished vertical PDF carousel from structured article data."""

    def __init__(self, colors: dict[str, str]):
        self.colors = colors
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(False)
        self.page_count = 0

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        color = (hex_color or "#000000").strip().lstrip("#")
        if len(color) != 6:
            color = "000000"
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _color(self, key: str, fallback: str = "#000000") -> tuple[int, int, int]:
        return self._hex_to_rgb(self.colors.get(key, fallback))

    def _sanitize_text(self, text: Any) -> str:
        """Normalize text to the core-font encoding fpdf uses reliably."""
        value = str(text or "")
        replacements = {
            "\u2014": "-",
            "\u2013": "-",
            "\u2022": "*",
            "\u2026": "...",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u00a0": " ",
            "\u00b7": "-",
        }
        for src, dst in replacements.items():
            value = value.replace(src, dst)
        value = unicodedata.normalize("NFKD", value)
        value = value.encode("latin-1", errors="ignore").decode("latin-1")
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _add_page(self, bg_key: str = "bg_primary") -> None:
        self.pdf.add_page()
        self.page_count += 1
        self.pdf.set_fill_color(*self._color(bg_key, "#0A0A0A"))
        self.pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

    def _line(self, x1: float, y: float, x2: float, color_key: str = "accent_gold") -> None:
        self.pdf.set_draw_color(*self._color(color_key, "#C9A84C"))
        self.pdf.set_line_width(0.25)
        self.pdf.line(x1, y, x2, y)

    def _cell_text(
        self,
        text: str,
        *,
        x: float,
        y: float,
        w: float,
        h: float,
        font: str = "Helvetica",
        style: str = "",
        size: int = 10,
        color_key: str = "text_primary",
        fallback: str = "#F5F5F0",
        align: str = "L",
    ) -> float:
        self.pdf.set_xy(x, y)
        self.pdf.set_font(font, style, size)
        self.pdf.set_text_color(*self._color(color_key, fallback))
        self.pdf.multi_cell(w, h, self._sanitize_text(text), align=align)
        return self.pdf.get_y()

    def _footer(self, label: str, dark: bool = True) -> None:
        color_key = "text_muted_dark" if dark else "text_muted_light"
        self.pdf.set_font("Helvetica", "", 7)
        self.pdf.set_text_color(*self._color(color_key, "#8A8A80"))
        self.pdf.set_xy(MARGIN, 282)
        self.pdf.cell(40, 5, self._sanitize_text(label))
        self.pdf.cell(105, 5, "LTG Capital Intelligence", align="C")
        self.pdf.cell(40, 5, "lighttowergroup.co", align="R")

    def _cover_page(self, data: dict[str, Any]) -> None:
        pub = data["publication"]
        self._add_page("bg_primary")
        self._cell_text("LTG CAPITAL INTELLIGENCE", x=MARGIN, y=16, w=120, h=5, font="Helvetica",
                        style="B", size=10, color_key="accent_gold", fallback="#C9A84C")
        self._cell_text("Institutional Perspectives on CRE & Capital Markets", x=MARGIN, y=23,
                        w=120, h=4, size=8, color_key="text_muted_dark", fallback="#8A8A80")
        self._cell_text(f"Vol. {pub.get('volume', 1)}\n{pub.get('issue_month', '')}", x=150, y=16,
                        w=44, h=4, size=8, color_key="text_muted_dark", fallback="#8A8A80", align="R")

        self._line(MARGIN, 40, PAGE_W - MARGIN, "accent_gold")
        self._cell_text(pub.get("theme", "Capital Markets Intelligence"), x=22, y=68, w=166, h=9,
                        font="Times", style="B", size=22, color_key="text_primary",
                        fallback="#F5F5F0", align="C")

        self._cell_text("INSIDE THIS CAROUSEL", x=MARGIN, y=132, w=CONTENT_W, h=4,
                        style="B", size=8, color_key="accent_gold", fallback="#C9A84C")
        y = 143
        for i, story in enumerate(data.get("stories", [])[:5], 1):
            self.pdf.set_xy(MARGIN, y)
            self.pdf.set_font("Helvetica", "B", 8)
            self.pdf.set_text_color(*self._color("accent_gold", "#C9A84C"))
            self.pdf.cell(12, 5, f"{i:02d}")
            self.pdf.set_font("Helvetica", "", 8)
            self.pdf.set_text_color(*self._color("text_muted_dark", "#8A8A80"))
            self.pdf.cell(155, 5, self._sanitize_text(story.get("headline", ""))[:88])
            y += 9

        self._footer("Cover")

    def _transition_page(self, story: dict[str, Any], num: int) -> None:
        self._add_page("bg_primary")
        self._cell_text("*", x=78, y=82, w=54, h=24, font="Helvetica", style="B", size=52,
                        color_key="accent_gold", fallback="#C9A84C", align="C")
        self._cell_text("NEXT", x=MARGIN, y=140, w=CONTENT_W, h=5, style="B", size=8,
                        color_key="accent_gold", fallback="#C9A84C", align="C")
        self._cell_text(story.get("headline", ""), x=24, y=152, w=162, h=7, font="Times",
                        style="B", size=17, color_key="text_primary", fallback="#F5F5F0", align="C")
        self._cell_text(story.get("category", ""), x=24, y=188, w=162, h=4, size=8,
                        color_key="text_muted_dark", fallback="#8A8A80", align="C")
        self._footer(f"Transition {num}")

    def _story_opening_page(self, story: dict[str, Any], num: int, dark: bool) -> None:
        bg_key = "bg_page" if dark else "bg_light"
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        rule_key = "rule_dark" if dark else "rule_light"
        self._add_page(bg_key)

        self._cell_text(f"STORY {num:02d} OF 05 - {story.get('category', 'Capital Markets').upper()}",
                        x=MARGIN, y=16, w=CONTENT_W, h=4, style="B", size=8,
                        color_key="accent_gold", fallback="#C9A84C")
        self._line(MARGIN, 24, PAGE_W - MARGIN, rule_key)

        self._cell_text(story.get("headline", ""), x=MARGIN, y=35, w=112, h=7, font="Times",
                        style="B", size=18, color_key=text_key, fallback="#F5F5F0")
        y = self._cell_text(story.get("deck", ""), x=MARGIN, y=82, w=112, h=5,
                            font="Times", style="I", size=11, color_key=muted_key, fallback="#8A8A80")
        paragraphs = story.get("paragraphs", [])
        if paragraphs:
            self._cell_text(paragraphs[0], x=MARGIN, y=min(y + 6, 116), w=112, h=4.2,
                            size=9, color_key=text_key, fallback="#F5F5F0")

        x = 138
        y = 42
        for fig in story.get("key_figures", [])[:3]:
            self._cell_text(fig.get("number", ""), x=x, y=y, w=54, h=8, font="Times", style="B",
                            size=22, color_key="accent_gold", fallback="#C9A84C")
            y += 10
            self._cell_text(fig.get("label", "Key metric"), x=x, y=y, w=54, h=4, size=8,
                            color_key=muted_key, fallback="#8A8A80")
            y += 15

        self._cell_text(f"{story.get('dateline', 'NEW YORK')} - {story.get('date', '')}",
                        x=138, y=206, w=54, h=4, style="B", size=8,
                        color_key=muted_key, fallback="#8A8A80")
        self._cell_text(story.get("source", "Light Tower Group Analysis"), x=138, y=212,
                        w=54, h=4, size=7, color_key=muted_key, fallback="#8A8A80")
        self._footer(f"A-{num:02d}", dark=dark)

    def _story_continuation_page(self, story: dict[str, Any], num: int, dark: bool) -> None:
        bg_key = "bg_page" if dark else "bg_light"
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        rule_key = "rule_dark" if dark else "rule_light"
        self._add_page(bg_key)

        short_headline = self._sanitize_text(story.get("headline", ""))[:54].upper()
        self._cell_text(f"{short_headline} (CONT'D)", x=MARGIN, y=16, w=CONTENT_W, h=4,
                        style="B", size=8, color_key="accent_gold", fallback="#C9A84C")
        self._line(MARGIN, 24, PAGE_W - MARGIN, rule_key)

        paragraphs = story.get("paragraphs", [])[1:] or story.get("paragraphs", [])
        text = " ".join(paragraphs)
        text = self._sanitize_text(text)
        if len(text) > 1850:
            text = text[:1847].rsplit(" ", 1)[0] + "..."
        y = self._cell_text(text, x=MARGIN, y=36, w=CONTENT_W, h=4.5, size=10,
                            color_key=text_key, fallback="#F5F5F0")

        quote = self._sanitize_text(story.get("pull_quote", ""))
        if quote and y < 222:
            self._line(30, y + 10, 180, "accent_gold")
            self._cell_text(f'"{quote}"', x=30, y=y + 16, w=150, h=5, font="Times",
                            style="I", size=13, color_key=muted_key, fallback="#8A8A80", align="C")
        self._footer(f"A-{num:02d}A", dark=dark)

    def _closing_page(self, data: dict[str, Any]) -> None:
        self._add_page("bg_primary")
        self._line(MARGIN, 24, PAGE_W - MARGIN, "accent_gold")
        self._cell_text("LIGHT TOWER GROUP", x=MARGIN, y=54, w=CONTENT_W, h=8, font="Times",
                        style="B", size=24, color_key="text_primary", fallback="#F5F5F0", align="C")
        self._cell_text("INSTITUTIONAL CAPITAL ADVISORY", x=MARGIN, y=66, w=CONTENT_W, h=4,
                        style="B", size=9, color_key="accent_gold", fallback="#C9A84C", align="C")

        self._cell_text("ABOUT", x=MARGIN, y=106, w=80, h=4, style="B", size=8,
                        color_key="accent_gold", fallback="#C9A84C")
        self._cell_text(
            "Benjamin Rohr is the Principal of Light Tower Group, a New York-based "
            "institutional capital advisory firm specializing in debt and equity "
            "placement for complex commercial real estate transactions.",
            x=MARGIN, y=113, w=82, h=4, size=8, color_key="text_muted_dark", fallback="#8A8A80",
        )

        self._cell_text("ENGAGE", x=112, y=106, w=82, h=4, style="B", size=8,
                        color_key="accent_gold", fallback="#C9A84C")
        self._cell_text(
            "Principal-led execution. Debt placement, equity structuring, and "
            "investment advisory for complex commercial real estate mandates.",
            x=112, y=113, w=82, h=4, size=8, color_key="text_muted_dark", fallback="#8A8A80",
        )
        self._cell_text("ben@lighttowergroup.co\n(347) 554-0093\nlighttowergroup.co",
                        x=112, y=146, w=82, h=5, style="B", size=10,
                        color_key="accent_gold", fallback="#C9A84C")

        self._cell_text(
            "This publication is for informational purposes only and does not constitute investment advice.",
            x=MARGIN, y=264, w=CONTENT_W, h=3, size=7, color_key="text_muted_dark",
            fallback="#8A8A80", align="C",
        )
        self._footer("Closing")

    def render(self, data: dict[str, Any]) -> FPDF:
        self._cover_page(data)
        for i, story in enumerate(data.get("stories", [])[:5], 1):
            dark = i % 2 == 1
            if i > 1:
                self._transition_page(story, i)
            self._story_opening_page(story, i, dark)
            self._story_continuation_page(story, i, dark)
        self._closing_page(data)
        return self.pdf

    async def generate_pdf(self, data: dict[str, Any], output_path: str) -> bool:
        try:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            pdf = self.render(data)
            pdf.set_title("LTG Capital Intelligence")
            pdf.set_author("Light Tower Group")
            pdf.set_creator("Light Tower Group")
            pdf.output(str(output))
            logger.info("LTG Capital Intelligence PDF: %s (%s pages)", output, self.page_count)
            return True
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc, exc_info=True)
            return False


if __name__ == "__main__":
    import sys
    from fetch_brand_colors import fetch_brand_colors

    if len(sys.argv) < 2:
        print("Usage: python generate_carousel_pdf.py <pdf_schema.json> [output.pdf]")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        schema = json.load(f)

    out = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"
    generator = CarouselPDFGenerator(fetch_brand_colors())
    ok = asyncio.run(generator.generate_pdf(schema, out))
    sys.exit(0 if ok else 1)
