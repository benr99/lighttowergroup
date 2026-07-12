"""Render a finished Light Tower Insight as a simple LinkedIn document PDF.

This deliberately preserves the approved article rather than rewriting it as a
carousel.  It uses fpdf2, which is already part of the agent runtime.
"""

from __future__ import annotations

import html
import unicodedata
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from fpdf import FPDF


PAGE_WIDTH_MM = 190.5   # 7.5in
PAGE_HEIGHT_MM = 238.125  # 9.375in (4:5)
MARGIN_MM = 15.75
CREAM = "F5F4F0"
INK = "121212"
MUTED = "5A5A54"
GOLD = "C9A84C"


def _ascii_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    replacements = {
        "â€”": "-", "â€“": "-", "â€™": "'", "â€˜": "'", "â€œ": '"',
        "â€": '"', "â€¦": "...", "â€¢": "-", "\u00a0": " ",
        "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
        "…": "...", "•": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", errors="ignore").decode("ascii").strip()


def extract_article_paragraphs(article_html: str, article_data: dict[str, Any]) -> list[str]:
    body_html = article_data.get("body_html") or article_data.get("body") or article_html or ""
    soup = BeautifulSoup(body_html, "html.parser")
    root = soup.select_one('[itemprop="articleBody"], .article-body') or soup
    paragraphs = [_ascii_text(node.get_text(" ", strip=True)) for node in root.find_all("p")]
    return [paragraph for paragraph in paragraphs if paragraph]


class ArticlePDF(FPDF):
    def _frame(self, label: str, page_number: int | None = None) -> None:
        self.set_fill_color(int(CREAM[:2], 16), int(CREAM[2:4], 16), int(CREAM[4:], 16))
        self.rect(0, 0, PAGE_WIDTH_MM, PAGE_HEIGHT_MM, style="F")
        self.set_text_color(int(GOLD[:2], 16), int(GOLD[2:4], 16), int(GOLD[4:], 16))
        self.set_font("Helvetica", "B", 7.5)
        self.text(MARGIN_MM, 11.4, label)
        self.set_draw_color(int(GOLD[:2], 16), int(GOLD[2:4], 16), int(GOLD[4:], 16))
        self.line(MARGIN_MM, 14.5, PAGE_WIDTH_MM - MARGIN_MM, 14.5)
        self.set_text_color(int(MUTED[:2], 16), int(MUTED[2:4], 16), int(MUTED[4:], 16))
        self.set_font("Helvetica", "", 7.5)
        self.text(MARGIN_MM, PAGE_HEIGHT_MM - 10.5, "lighttowergroup.co")
        if page_number is not None:
            self.text(PAGE_WIDTH_MM - MARGIN_MM - 3, PAGE_HEIGHT_MM - 10.5, str(page_number))

    def header(self) -> None:
        if self.page_no() > 1:
            self._frame("LIGHT TOWER GROUP  |  INSIGHT", self.page_no())


def build_article_pdf(article_html: str, article_data: dict[str, Any], output_path: Path) -> Path:
    """Create a branded PDF containing approved Insight text in reading order."""
    paragraphs = extract_article_paragraphs(article_html, article_data)
    if len(paragraphs) < 2:
        raise ValueError("Article PDF needs at least two readable article paragraphs")

    title = _ascii_text(article_data.get("title") or "Light Tower Insight")
    subtitle = _ascii_text(article_data.get("subtitle") or article_data.get("excerpt") or "")
    category = _ascii_text(article_data.get("category") or "Capital Markets")
    date = _ascii_text(article_data.get("date") or article_data.get("date_iso") or "")
    source = _ascii_text(article_data.get("source_name") or "Light Tower Group Analysis")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = ArticlePDF(orientation="P", unit="mm", format=(PAGE_WIDTH_MM, PAGE_HEIGHT_MM))
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_title(title)
    pdf.set_author("Light Tower Group")

    pdf.add_page()
    pdf._frame("LIGHT TOWER GROUP  |  CAPITAL MARKETS NOTE")
    pdf.set_xy(MARGIN_MM, 50)
    pdf.set_text_color(int(GOLD[:2], 16), int(GOLD[2:4], 16), int(GOLD[4:], 16))
    pdf.set_font("Helvetica", "B", 8)
    pdf.multi_cell(0, 5, category.upper())
    pdf.ln(4)
    pdf.set_text_color(int(INK[:2], 16), int(INK[2:4], 16), int(INK[4:], 16))
    pdf.set_font("Times", "B", 24)
    pdf.multi_cell(0, 10, title)
    if subtitle:
        pdf.ln(4)
        pdf.set_text_color(int(MUTED[:2], 16), int(MUTED[2:4], 16), int(MUTED[4:], 16))
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 7, subtitle)
    pdf.set_y(PAGE_HEIGHT_MM - 42)
    pdf.set_text_color(int(MUTED[:2], 16), int(MUTED[2:4], 16), int(MUTED[4:], 16))
    pdf.set_font("Helvetica", "B", 8)
    pdf.multi_cell(0, 5, " | ".join(item for item in (date, source) if item))
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 5, "A source-grounded Light Tower Insight.")

    pdf.add_page()
    pdf.set_xy(MARGIN_MM, 23)
    pdf.set_text_color(int(INK[:2], 16), int(INK[2:4], 16), int(INK[4:], 16))
    pdf.set_font("Helvetica", "", 11.4)
    for paragraph in paragraphs:
        pdf.multi_cell(0, 7.1, paragraph)
        pdf.ln(4)

    pdf.output(str(output_path))
    return output_path
