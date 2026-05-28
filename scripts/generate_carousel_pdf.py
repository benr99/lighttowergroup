"""
Generate LTG LinkedIn-native PDF carousels.

Format: 4:5 portrait document pages, designed for mobile feed reading.
Slide systems: hero, briefing, data, analysis, kicker.
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

PAGE_W = 108
PAGE_H = 135
MARGIN = 9
CONTENT_W = PAGE_W - (MARGIN * 2)


class CarouselPDFGenerator:
    """Render carousel scripts into polished PDF documents."""

    def __init__(self, colors: dict[str, str]):
        self.colors = colors
        self.pdf = FPDF(unit="mm", format=(PAGE_W, PAGE_H))
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

    def _fit_font_size(self, text: str, width: float, base_size: int, min_size: int = 10) -> int:
        text = self._sanitize_text(text)
        size = base_size
        self.pdf.set_font("Helvetica", "B", size)
        while size > min_size:
            words = max(1, len(text.split()))
            lines = max(1, self.pdf.get_string_width(text) / max(width, 1))
            if words < 10 or lines < 3.2:
                break
            size -= 1
            self.pdf.set_font("Helvetica", "B", size)
        return size

    def _add_page(self, bg_key: str = "bg_primary") -> None:
        self.pdf.add_page()
        self.page_count += 1
        self.pdf.set_fill_color(*self._color(bg_key, "#0A0A0A"))
        self.pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

    def _text(
        self,
        text: str,
        *,
        x: float,
        y: float,
        w: float,
        h: float,
        size: int,
        color_key: str,
        style: str = "",
        font: str = "Helvetica",
        align: str = "L",
        fallback: str = "#F5F5F0",
    ) -> float:
        self.pdf.set_xy(x, y)
        self.pdf.set_font(font, style, size)
        self.pdf.set_text_color(*self._color(color_key, fallback))
        self.pdf.multi_cell(w, h, self._sanitize_text(text), align=align)
        return self.pdf.get_y()

    def _label(self, text: str, slide_no: int, dark: bool = True) -> None:
        self._text(text.upper(), x=MARGIN, y=8, w=64, h=3.2, size=6, style="B",
                   color_key="accent_gold", fallback="#C9A84C")
        self._text(f"{slide_no:02d}", x=92, y=8, w=7, h=3.2, size=6, style="B",
                   color_key="accent_gold", fallback="#C9A84C", align="R")
        rule = "rule_dark" if dark else "rule_light"
        self.pdf.set_draw_color(*self._color(rule, "#2C2C28"))
        self.pdf.set_line_width(0.2)
        self.pdf.line(MARGIN, 15, PAGE_W - MARGIN, 15)

    def _footer(self, dark: bool = True) -> None:
        color_key = "text_muted_dark" if dark else "text_muted_light"
        self._text("LTG Capital Intelligence", x=MARGIN, y=126, w=55, h=3, size=5.5,
                   color_key=color_key, fallback="#8A8A80")
        self._text("lighttowergroup.co", x=72, y=126, w=27, h=3, size=5.5,
                   color_key=color_key, fallback="#8A8A80", align="R")

    def _bullet_list(self, bullets: list[str], *, x: float, y: float, w: float, dark: bool, size: int = 10) -> float:
        text_key = "text_primary" if dark else "text_on_light"
        gold = self._color("accent_gold", "#C9A84C")
        for bullet in bullets[:4]:
            self.pdf.set_fill_color(*gold)
            self.pdf.circle(x + 1.4, y + 1.9, 1.1, "F")
            y = self._text(bullet, x=x + 5, y=y, w=w - 5, h=4.2, size=size,
                           color_key=text_key, fallback="#F5F5F0")
            y += 3
        return y

    def _render_hero(self, slide: dict[str, Any], slide_no: int) -> None:
        self._add_page("bg_primary")
        self._label(slide.get("eyebrow", "MARKET MOVES"), slide_no)
        headline = slide.get("headline", "")
        size = self._fit_font_size(headline, 88, 21, 15)
        self._text(headline, x=MARGIN, y=28, w=90, h=7.5, size=size, style="B",
                   font="Helvetica", color_key="text_primary")
        if slide.get("figures"):
            fig = slide["figures"][0]
            self._text(fig.get("number", ""), x=MARGIN, y=72, w=90, h=10, size=26,
                       style="B", font="Helvetica", color_key="accent_gold", fallback="#C9A84C")
            self._text(fig.get("label", ""), x=MARGIN, y=84, w=70, h=4, size=7,
                       color_key="text_muted_dark", fallback="#8A8A80")
        self._text(slide.get("subhead", ""), x=MARGIN, y=94, w=88, h=4.4, size=10,
                   color_key="text_muted_dark", fallback="#8A8A80")
        self._footer()

    def _render_briefing(self, slide: dict[str, Any], slide_no: int, dark: bool) -> None:
        self._add_page("bg_page" if dark else "bg_light")
        self._label(slide.get("eyebrow", "BRIEFING"), slide_no, dark)
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        self._text(slide.get("headline", ""), x=MARGIN, y=25, w=88, h=6.5, size=19,
                   style="B", color_key=text_key, fallback="#F5F5F0")
        if slide.get("subhead"):
            self._text(slide["subhead"], x=MARGIN, y=43, w=86, h=4, size=9,
                       color_key=muted_key, fallback="#8A8A80")
        self._bullet_list(slide.get("bullets", []), x=MARGIN, y=55, w=88, dark=dark, size=10)
        self._footer(dark)

    def _render_story(self, slide: dict[str, Any], slide_no: int, dark: bool) -> None:
        self._add_page("bg_page" if dark else "bg_light")
        self._label(slide.get("eyebrow", "STORY"), slide_no, dark)
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        headline = slide.get("headline", "")
        size = self._fit_font_size(headline, 88, 18, 13)
        y = self._text(headline, x=MARGIN, y=23, w=88, h=6, size=size,
                       style="B", color_key=text_key, fallback="#F5F5F0")
        subhead = slide.get("subhead", "")
        if subhead:
            y = self._text(subhead, x=MARGIN, y=max(y + 8, 48), w=88, h=4.7, size=10.5,
                           color_key=text_key, fallback="#F5F5F0")
        # Add supporting bullets only when there is room; the prose is the core.
        if slide.get("bullets") and y < 96:
            self._bullet_list(slide["bullets"][:2], x=MARGIN, y=y + 7, w=88, dark=dark, size=7.8)
        self._footer(dark)

    def _render_data(self, slide: dict[str, Any], slide_no: int, dark: bool) -> None:
        self._add_page("bg_primary" if dark else "bg_light")
        self._label(slide.get("eyebrow", "THE MONEY"), slide_no, dark)
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        self._text(slide.get("headline", ""), x=MARGIN, y=23, w=88, h=6, size=17,
                   style="B", color_key=text_key, fallback="#F5F5F0")
        y = 42
        figures = slide.get("figures", [])[:3]
        for fig in figures:
            self._text(fig.get("number", ""), x=MARGIN, y=y, w=88, h=9, size=24,
                       style="B", color_key="accent_gold", fallback="#C9A84C")
            y += 10
            self._text(fig.get("label", ""), x=MARGIN, y=y, w=80, h=3.5, size=7,
                       color_key=muted_key, fallback="#8A8A80")
            y += 13
        if slide.get("bullets") and len(figures) < 3:
            self._bullet_list(slide["bullets"], x=MARGIN, y=max(y, 92), w=88, dark=dark, size=8)
        self._footer(dark)

    def _render_analysis(self, slide: dict[str, Any], slide_no: int, dark: bool) -> None:
        self._add_page("bg_page" if dark else "bg_light")
        self._label(slide.get("eyebrow", "ANALYSIS"), slide_no, dark)
        text_key = "text_primary" if dark else "text_on_light"
        muted_key = "text_muted_dark" if dark else "text_muted_light"
        self._text(slide.get("headline", ""), x=MARGIN, y=25, w=88, h=6.2, size=18,
                   style="B", color_key=text_key, fallback="#F5F5F0")
        y = 46
        if slide.get("subhead"):
            y = self._text(slide["subhead"], x=MARGIN, y=y, w=88, h=5, size=11,
                           color_key=text_key, fallback="#F5F5F0")
            y += 5
        if slide.get("quote"):
            self.pdf.set_draw_color(*self._color("accent_gold", "#C9A84C"))
            self.pdf.set_line_width(0.35)
            self.pdf.line(MARGIN, y + 2, PAGE_W - MARGIN, y + 2)
            y = self._text(f'"{slide["quote"]}"', x=13, y=y + 9, w=82, h=5,
                           size=12, font="Times", style="I", color_key=muted_key,
                           fallback="#8A8A80", align="C")
        if slide.get("bullets"):
            self._bullet_list(slide["bullets"], x=MARGIN, y=max(y + 6, 78), w=88, dark=dark, size=9)
        self._footer(dark)

    def _render_kicker(self, slide: dict[str, Any], slide_no: int) -> None:
        self._add_page("bg_primary")
        self._label(slide.get("eyebrow", "LTG READ"), slide_no)
        self._text(slide.get("headline", ""), x=MARGIN, y=28, w=88, h=7.5, size=21,
                   style="B", font="Helvetica", color_key="text_primary")
        self._text(slide.get("subhead", ""), x=MARGIN, y=66, w=88, h=4.5, size=10,
                   color_key="text_muted_dark", fallback="#8A8A80")
        self._text(slide.get("kicker", ""), x=MARGIN, y=91, w=88, h=5.5, size=13,
                   style="B", color_key="accent_gold", fallback="#C9A84C", align="C")
        self._text("LIGHT TOWER GROUP", x=MARGIN, y=112, w=88, h=4, size=9,
                   style="B", color_key="text_primary", align="C")
        self._footer()

    def render(self, data: dict[str, Any]) -> FPDF:
        slides = data.get("slides") or []
        if not slides:
            slides = self._slides_from_legacy_stories(data)
        for i, slide in enumerate(slides, 1):
            system = slide.get("system", "analysis")
            dark = i % 2 == 1
            if system == "hero":
                self._render_hero(slide, i)
            elif system == "briefing":
                self._render_briefing(slide, i, dark)
            elif system == "story":
                self._render_story(slide, i, dark)
            elif system == "data":
                self._render_data(slide, i, dark)
            elif system == "kicker":
                self._render_kicker(slide, i)
            else:
                self._render_analysis(slide, i, dark)
        return self.pdf

    def _slides_from_legacy_stories(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        stories = data.get("stories", [])
        slides = [{
            "system": "hero",
            "eyebrow": "CAPITAL INTELLIGENCE",
            "headline": data.get("publication", {}).get("theme", "Capital Markets Intelligence"),
            "subhead": "A Light Tower Group carousel brief.",
            "figures": [],
        }]
        for story in stories[:7]:
            slides.append({
                "system": "briefing",
                "eyebrow": story.get("category", "Briefing"),
                "headline": story.get("headline", ""),
                "bullets": story.get("paragraphs", [])[:3],
                "figures": story.get("key_figures", []),
            })
        slides.append({
            "system": "kicker",
            "eyebrow": "LTG READ",
            "headline": "The headline is the transaction. The story is the structure.",
            "subhead": "Capital markets reward clarity, basis, and timing.",
            "kicker": "Structure decides what survives the cycle.",
        })
        return slides

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
