"""Render a finished Light Tower Insight as a branded LinkedIn document PDF.

This deliberately preserves the approved article in full rather than rewriting
it as a carousel or summary: the published prose is the source of truth. The
renderer keeps the article's structure (sub-headings, lists, block quotes and
inline emphasis) and sets it in the Light Tower brand typefaces with full
Unicode support, so real punctuation, accents and symbols survive intact.

It uses fpdf2 (already part of the agent runtime) and the TTF faces bundled in
scripts/fonts.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag
from fpdf import FPDF
from fpdf.enums import XPos, YPos


FONTS_DIR = Path(__file__).parent / "fonts"

# ── Page geometry — 4:5 LinkedIn document ratio ──────────────────────────────
PAGE_W = 190.5      # 7.5in
PAGE_H = 238.125    # 9.375in
MARGIN = 17.0
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Palette (warm institutional) ─────────────────────────────────────────────
CREAM = (246, 244, 239)   # page ground
INK = (26, 22, 18)        # warm near-black body text
MUTED = (108, 101, 90)    # secondary text
GOLD = (176, 143, 58)     # accent
HAIR = (214, 205, 190)    # hairline rules
QUOTE_BG = (240, 237, 229)

# ── Type scale (pt) ──────────────────────────────────────────────────────────
BODY_SIZE = 11.3
BODY_LEAD = 6.8           # line height in mm
LEAD_SIZE = 12.8          # opening paragraph
SUBHEAD_SIZE = 12.5
PARA_GAP = 3.4

_MOJIBAKE = {
    "â€”": "—", "â€“": "–", "â€™": "’", "â€˜": "‘",
    "â€œ": "“", "â€\x9d": "”", "â€¦": "…", "â€¢": "•",
    "Â\xa0": " ", " ": " ", "Â": "",
}


def _clean_run(value: Any) -> str:
    """Unescape entities and repair mojibake without trimming edge whitespace.

    Edge whitespace matters inside inline flow: the space that separates a word
    from an adjacent <strong> run lives at a text-run boundary, so stripping it
    would weld the words together ("a shift toward" + <b>X</b> -> "towardX").
    """
    text = html.unescape(str(value or ""))
    for bad, good in _MOJIBAKE.items():
        text = text.replace(bad, good)
    return text


def _clean(value: Any) -> str:
    """Unescape entities and repair common mojibake, trimming the ends."""
    return _clean_run(value).strip()


def _inline(node: Tag | NavigableString) -> str:
    """Flatten a node's inline content to text, marking bold as **markdown**."""
    if isinstance(node, NavigableString):
        return _clean_run(str(node))
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(_clean_run(str(child)))
        elif isinstance(child, Tag):
            if child.name == "br":
                parts.append(" ")
            elif child.name in ("strong", "b", "em", "i"):
                inner = _inline(child).strip()
                parts.append(f"**{inner}**" if inner else "")
            else:
                parts.append(_inline(child))
    return "".join(parts)


def _inline_text(node: Tag | NavigableString) -> str:
    """Collapsed inline string (whitespace normalised, emphasis preserved)."""
    return re.sub(r"\s+", " ", _inline(node)).strip()


def extract_article_paragraphs(article_html: str, article_data: dict[str, Any]) -> list[str]:
    """Backward-compatible helper: plain paragraph strings in reading order."""
    body_html = article_data.get("body_html") or article_data.get("body") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    root = soup.select_one('[itemprop="articleBody"], .article-body') or soup
    paragraphs = [re.sub(r"\s+", " ", _clean(node.get_text(" ", strip=True))) for node in root.find_all("p")]
    return [p for p in paragraphs if p]


def _reading_minutes(root: Tag) -> int:
    words = len(root.get_text(" ", strip=True).split())
    return max(1, round(words / 220))


class InsightPDF(FPDF):
    short_title = ""

    def header(self) -> None:
        # Cream ground on every page (covers auto-break pages too).
        self.set_fill_color(*CREAM)
        self.rect(0, 0, PAGE_W, PAGE_H, style="F")
        if self.page_no() == 1:
            return
        self.set_xy(MARGIN, 11.5)
        self.set_text_color(*GOLD)
        self.set_font("Inter", "B", 7)
        self.set_char_spacing(1.1)
        self.cell(CONTENT_W / 2, 4, "LIGHT TOWER GROUP")
        self.set_char_spacing(0)
        self.set_xy(MARGIN + CONTENT_W / 2, 11.5)
        self.set_text_color(*MUTED)
        self.set_font("Inter", "", 7)
        self.cell(CONTENT_W / 2, 4, self.short_title, align="R")
        self.set_draw_color(*HAIR)
        self.set_line_width(0.25)
        self.line(MARGIN, 17.2, PAGE_W - MARGIN, 17.2)
        # Reset the cursor to the content origin so the first body block on the
        # page starts at the left margin (fpdf keeps whatever header() left).
        self.set_xy(MARGIN, 23)

    def footer(self) -> None:
        self.set_draw_color(*HAIR)
        self.set_line_width(0.25)
        self.line(MARGIN, PAGE_H - 13, PAGE_W - MARGIN, PAGE_H - 13)
        self.set_xy(MARGIN, PAGE_H - 11)
        self.set_text_color(*MUTED)
        self.set_font("Inter", "", 7)
        self.cell(CONTENT_W / 2, 4, "lighttowergroup.co")
        self.set_xy(MARGIN + CONTENT_W / 2, PAGE_H - 11)
        self.cell(CONTENT_W / 2, 4, str(self.page_no()), align="R")


def _register_fonts(pdf: FPDF) -> None:
    pdf.add_font("Inter", "", str(FONTS_DIR / "Inter-Regular.ttf"))
    pdf.add_font("Inter", "B", str(FONTS_DIR / "Inter-SemiBold.ttf"))
    pdf.add_font("Cormorant", "B", str(FONTS_DIR / "CormorantGaramond-Bold.ttf"))
    pdf.add_font("EBGaramond", "", str(FONTS_DIR / "EBGaramond-Regular.ttf"))
    pdf.add_font("EBGaramond", "B", str(FONTS_DIR / "EBGaramond-SemiBold.ttf"))


def _label(pdf: InsightPDF, text: str, size: float = 8.0, color=GOLD, spacing: float = 1.6) -> None:
    pdf.set_font("Inter", "B", size)
    pdf.set_text_color(*color)
    pdf.set_char_spacing(spacing)
    pdf.multi_cell(CONTENT_W, size * 0.52, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_char_spacing(0)


def _title_size(title: str) -> float:
    n = len(title)
    if n <= 34:
        return 40
    if n <= 55:
        return 34
    if n <= 80:
        return 29
    if n <= 110:
        return 25
    return 21


def _render_cover(pdf: InsightPDF, *, category: str, title: str, subtitle: str,
                  date: str, source: str, minutes: int) -> None:
    pdf.add_page()
    # top kicker row
    pdf.set_xy(MARGIN, 20)
    pdf.set_font("Inter", "B", 7.5)
    pdf.set_text_color(*GOLD)
    pdf.set_char_spacing(1.6)
    pdf.cell(CONTENT_W / 2, 5, "LIGHT TOWER GROUP")
    pdf.set_char_spacing(0.8)
    pdf.set_text_color(*MUTED)
    pdf.set_font("Inter", "", 7.5)
    pdf.set_xy(MARGIN + CONTENT_W / 2, 20)
    pdf.cell(CONTENT_W / 2, 5, "CAPITAL MARKETS NOTE", align="R")
    pdf.set_char_spacing(0)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.4)
    pdf.line(MARGIN, 28, PAGE_W - MARGIN, 28)

    # headline block, vertically centred in the upper two-thirds
    pdf.set_xy(MARGIN, 66)
    if category:
        _label(pdf, category, size=8.5, color=GOLD, spacing=1.8)
        pdf.ln(4)
    pdf.set_text_color(*INK)
    size = _title_size(title)
    pdf.set_font("Cormorant", "B", size)
    pdf.multi_cell(CONTENT_W, size * 0.40, title, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if subtitle:
        pdf.ln(5)
        pdf.set_text_color(*MUTED)
        pdf.set_font("EBGaramond", "", 13.5)
        pdf.multi_cell(CONTENT_W, 6.6, subtitle, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # meta footer block
    pdf.set_xy(MARGIN, PAGE_H - 52)
    pdf.set_draw_color(*HAIR)
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, PAGE_H - 52, PAGE_W - MARGIN, PAGE_H - 52)
    pdf.ln(4)
    meta_bits = [b for b in (date, source, f"{minutes} min read") if b]
    pdf.set_font("Inter", "B", 8)
    pdf.set_text_color(*INK)
    pdf.set_char_spacing(0.4)
    pdf.multi_cell(CONTENT_W, 5, "   ·   ".join(meta_bits), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_char_spacing(0)
    pdf.ln(1.5)
    pdf.set_font("EBGaramond", "", 10.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(CONTENT_W, 5, "A source-grounded Light Tower Insight. The complete note follows.",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _para(pdf: InsightPDF, text: str, *, size: float = BODY_SIZE, lead: float = BODY_LEAD,
          color=INK) -> None:
    if not text:
        return
    pdf.set_font("EBGaramond", "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(CONTENT_W, lead, text, markdown=True,
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(PARA_GAP)


def _subhead(pdf: InsightPDF, text: str) -> None:
    if not text:
        return
    if pdf.will_page_break(18):
        pdf.add_page()
    pdf.ln(2.5)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.5)
    pdf.line(MARGIN, pdf.get_y(), MARGIN + 12, pdf.get_y())
    pdf.ln(2.5)
    pdf.set_font("Inter", "B", SUBHEAD_SIZE)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W, 6, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)


def _list_item(pdf: InsightPDF, text: str, marker: str) -> None:
    if not text:
        return
    y0 = pdf.get_y()
    pdf.set_font("Inter", "B", BODY_SIZE)
    pdf.set_text_color(*GOLD)
    pdf.set_xy(MARGIN + 1.5, y0)
    pdf.cell(6.5, BODY_LEAD, marker)
    pdf.set_xy(MARGIN + 8, y0)
    pdf.set_font("EBGaramond", "", BODY_SIZE)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W - 8, BODY_LEAD, text, markdown=True, align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(PARA_GAP * 0.5)


def _blockquote(pdf: InsightPDF, text: str) -> None:
    if not text:
        return
    pdf.ln(1)
    y0 = pdf.get_y()
    pdf.set_font("EBGaramond", "", BODY_SIZE + 0.5)
    pdf.set_text_color(*MUTED)
    pdf.set_x(MARGIN + 8)
    pdf.multi_cell(CONTENT_W - 12, BODY_LEAD, text, markdown=True, align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    y1 = pdf.get_y()
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(1.0)
    pdf.line(MARGIN + 2, y0 + 0.5, MARGIN + 2, y1 - 1)
    pdf.ln(PARA_GAP)


def _render_body(pdf: InsightPDF, root: Tag) -> None:
    lead_done = False

    def walk(node: Tag) -> None:
        nonlocal lead_done
        for child in node.children:
            if isinstance(child, NavigableString):
                continue
            if not isinstance(child, Tag):
                continue
            name = child.name.lower()
            if name == "p":
                text = _inline_text(child)
                if not text:
                    continue
                if not lead_done:
                    _para(pdf, text, size=LEAD_SIZE, lead=BODY_LEAD + 0.7)
                    lead_done = True
                else:
                    _para(pdf, text)
            elif name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                _subhead(pdf, _inline_text(child))
            elif name in ("ul", "ol"):
                ordered = name == "ol"
                for i, li in enumerate(child.find_all("li", recursive=False), start=1):
                    marker = f"{i}." if ordered else "—"
                    _list_item(pdf, _inline_text(li), marker)
                pdf.ln(PARA_GAP * 0.6)
            elif name == "blockquote":
                _blockquote(pdf, _inline_text(child))
            elif name in ("hr",):
                pdf.ln(2)
            else:
                # Container (div/section/figure…): recurse into it.
                walk(child)

    walk(root)


def _render_sources(pdf: InsightPDF, sources: list) -> None:
    items: list[str] = []
    for s in sources:
        if isinstance(s, dict):
            label = s.get("name") or s.get("title") or s.get("url") or ""
            url = s.get("url") or ""
            if label and url and url not in label:
                items.append(f"{_clean(label)} — {_clean(url)}")
            elif label:
                items.append(_clean(label))
        elif s:
            items.append(_clean(s))
    items = [i for i in items if i]
    if not items:
        return
    if pdf.will_page_break(30):
        pdf.add_page()
    pdf.ln(4)
    pdf.set_draw_color(*HAIR)
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
    pdf.ln(3)
    _label(pdf, "Sources", size=8, color=GOLD, spacing=1.6)
    pdf.ln(2)
    pdf.set_font("Inter", "", 8.8)
    for item in items:
        y0 = pdf.get_y()
        pdf.set_text_color(*GOLD)
        pdf.set_xy(MARGIN + 1.5, y0)
        pdf.cell(6, 4.8, "—")
        pdf.set_xy(MARGIN + 7, y0)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(CONTENT_W - 7, 4.8, item, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.2)


def _render_endmark(pdf: InsightPDF) -> None:
    if pdf.will_page_break(16):
        return
    pdf.ln(4)
    pdf.set_font("Inter", "B", 8)
    pdf.set_text_color(*GOLD)
    pdf.set_char_spacing(2)
    pdf.cell(CONTENT_W, 5, "LIGHT TOWER GROUP", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_char_spacing(0)


def build_article_pdf(article_html: str, article_data: dict[str, Any], output_path: Path) -> Path:
    """Create a branded PDF containing the approved Insight in full reading order."""
    body_html = article_data.get("body_html") or article_data.get("body") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    root = soup.select_one('[itemprop="articleBody"], .article-body') or soup

    paragraphs = extract_article_paragraphs(article_html, article_data)
    if len(paragraphs) < 2:
        raise ValueError("Article PDF needs at least two readable article paragraphs")

    title = _clean(article_data.get("title") or "Light Tower Insight")
    subtitle = _clean(article_data.get("subtitle") or article_data.get("excerpt") or "")
    category = _clean(article_data.get("category") or "Capital Markets")
    date = _clean(article_data.get("date") or article_data.get("date_iso") or "")
    source = _clean(article_data.get("source_name") or "Light Tower Group Analysis")
    sources = article_data.get("sources") or []
    minutes = _reading_minutes(root)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = InsightPDF(orientation="P", unit="mm", format=(PAGE_W, PAGE_H))
    _register_fonts(pdf)
    pdf.set_title(title)
    pdf.set_author("Light Tower Group")
    pdf.set_creator("Light Tower Group Insight Engine")
    pdf.short_title = title if len(title) <= 60 else title[:57] + "…"
    pdf.set_margins(MARGIN, 23, MARGIN)
    pdf.set_auto_page_break(auto=True, margin=18)

    _render_cover(pdf, category=category, title=title, subtitle=subtitle,
                  date=date, source=source, minutes=minutes)

    pdf.add_page()
    _render_body(pdf, root)
    if isinstance(sources, list):
        _render_sources(pdf, sources)
    _render_endmark(pdf)

    pdf.output(str(output_path))
    return output_path
