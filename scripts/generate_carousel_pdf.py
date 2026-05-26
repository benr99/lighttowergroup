"""
Generate LTG Capital Intelligence PDF carousels from article data.

Renders beautiful, editorially-rigorous multi-page PDFs optimized for LinkedIn.
Uses fpdf2 for pure-Python PDF generation (no system dependencies).
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from fpdf import FPDF

logger = logging.getLogger(__name__)

CANVAS_WIDTH = 210  # mm (A4 width, will scale to display size)
CANVAS_HEIGHT = 297  # mm (A4 height)

class LTGPDFCarousel(FPDF):
    """Custom PDF class for LTG Capital Intelligence carousel."""

    def __init__(self, colors: Dict[str, str]):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.colors = colors
        # Register fonts (fpdf2 can use system fonts via name)
        self.set_auto_page_break(False)

    def set_brand_colors(self):
        """Configure drawing colors from brand palette."""
        pass

    def draw_page_header(self, section_label: str, accent_color: str = None):
        """Draw standard page header with section label and rule."""
        if accent_color is None:
            accent_color = self.colors['accent_gold']

        # Section label
        self.set_font("Courier", "B", 8)
        self.set_text_color(int(accent_color[1:3], 16), int(accent_color[3:5], 16), int(accent_color[5:7], 16))
        self.cell(0, 4, section_label.upper(), ln=True)

        # Thin rule
        self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
        self.ln(4)

    def draw_page_footer(self, page_num: str):
        """Draw standard page footer with pagination."""
        self.set_y(-15)
        self.set_font("Courier", "", 7)
        self.set_text_color(100, 100, 100)
        self.cell(30, 10, page_num)
        self.cell(135, 10, "* LTG Capital Intelligence", align="C")
        self.cell(30, 10, "", align="R")


class CarouselPDFGenerator:
    """Generate PDF carousel from article data."""

    def __init__(self, colors: Dict[str, str]):
        self.colors = colors

    def _sanitize_text(self, text: str) -> str:
        """Convert Unicode characters to ASCII equivalents for fpdf2 compatibility."""
        if not text:
            return text
        replacements = {
            '—': '-', '–': '-', '•': '*', '"': '"', '"': '"',
            ''': "'", ''': "'", '…': '...', '"': '"',
        }
        for uni, ascii_char in replacements.items():
            text = text.replace(uni, ascii_char)
        try:
            return text.encode('latin-1', errors='ignore').decode('latin-1')
        except:
            return text

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def build_pages(self, data: Dict) -> List[FPDF]:
        """Build all PDF pages from article data."""
        pages = []

        # Page 1: Cover
        pages.append(self._build_cover_page(data))

        # Pages 2+: Stories
        for i, story in enumerate(data['stories'], 1):
            is_dark_bg = i % 2 == 1

            # Transition page (not before first story)
            if i > 1:
                pages.append(self._build_transition_page(story, i))

            # Story opening page
            pages.append(self._build_story_opening_page(story, i, is_dark_bg))

            # Continuation page
            cont_page = self._build_continuation_page(story, i, is_dark_bg)
            if cont_page:
                pages.append(cont_page)

        # Final page: Closing
        pages.append(self._build_closing_page(data))

        return pages

    def _build_cover_page(self, data: Dict) -> FPDF:
        """Build masthead/cover page (PAGE TYPE A)."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        # Colors
        bg_rgb = self._hex_to_rgb(self.colors['bg_primary'])
        text_rgb = self._hex_to_rgb(self.colors['text_primary'])
        gold_rgb = self._hex_to_rgb(self.colors['accent_gold'])
        muted_rgb = self._hex_to_rgb(self.colors['text_muted_dark'])

        pdf.set_fill_color(*bg_rgb)
        pdf.rect(0, 0, 210, 297, 'F')

        # Header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(15, 15)
        pdf.cell(0, 5, "* LTG CAPITAL INTELLIGENCE", ln=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*muted_rgb)
        pdf.cell(0, 4, "Institutional Perspectives on CRE & Capital Markets", ln=True)

        # Right side: Volume info
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(150, 15)
        pdf.cell(45, 5, f"Vol. {data['publication']['volume']}", align="R")
        pdf.set_xy(150, 20)
        pdf.cell(45, 4, data['publication']['issue_month'], align="R")

        # Theme section
        pdf.set_font("Times", "B", 18)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, 60)
        theme_text = self._sanitize_text(data['publication']['theme'])
        pdf.multi_cell(180, 8, theme_text, align="C")

        # Table of contents
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(15, 130)

        for i, story in enumerate(data['stories'], 1):
            headline = self._sanitize_text(story['headline'][:45])
            pdf.cell(10, 6, f"{i:02d}", ln=False)
            pdf.cell(170, 6, headline, ln=True)

        # Footer
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(15, 280)
        pdf.cell(0, 5, "lighttowergroup.co  ·  ben@lighttowergroup.co", align="C")

        return pdf

    def _build_story_opening_page(self, story: Dict, num: int, is_dark_bg: bool) -> FPDF:
        """Build story opening page (PAGE TYPE B)."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        bg = self.colors['bg_page'] if is_dark_bg else self.colors['bg_light']
        text_color = self.colors['text_primary'] if is_dark_bg else self.colors['text_on_light']
        muted_color = self.colors['text_muted_dark'] if is_dark_bg else self.colors['text_muted_light']

        bg_rgb = self._hex_to_rgb(bg)
        text_rgb = self._hex_to_rgb(text_color)
        muted_rgb = self._hex_to_rgb(muted_color)
        gold_rgb = self._hex_to_rgb(self.colors['accent_gold'])

        # Background
        pdf.set_fill_color(*bg_rgb)
        pdf.rect(0, 0, 210, 297, 'F')

        # Header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(15, 15)
        pdf.cell(0, 4, f"STORY {num:02d} OF 05 · {story['category'].upper()}", ln=True)

        # Rule
        pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
        pdf.ln(3)

        # Headline
        pdf.set_font("Times", "B", 16)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, 25)
        pdf.multi_cell(100, 6, self._sanitize_text(story['headline']))

        # Deck
        pdf.set_font("Times", "I", 10)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(15, pdf.get_y() + 3)
        pdf.multi_cell(100, 5, self._sanitize_text(story['deck']))

        # Opening paragraph
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, pdf.get_y() + 4)
        if story['paragraphs']:
            pdf.multi_cell(100, 4, self._sanitize_text(story['paragraphs'][0]))

        # Right column: Key figures
        pdf.set_font("Times", "B", 20)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(120, 30)

        if story.get('key_figures'):
            for fig in story['key_figures'][:2]:
                pdf.cell(0, 8, self._sanitize_text(fig['number']), ln=True)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*muted_rgb)
                pdf.cell(0, 3, self._sanitize_text(fig['label']), ln=True)
                pdf.ln(2)
                pdf.set_font("Times", "B", 20)
                pdf.set_text_color(*gold_rgb)

        # Dateline
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(120, 180)
        pdf.cell(0, 4, f"{self._sanitize_text(story['dateline'])} - {self._sanitize_text(story['date'])}", ln=True)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(0, 4, self._sanitize_text(story['source']), ln=True)

        # Footer
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(15, 280)
        pdf.cell(30, 5, f"A-{num:02d}")
        pdf.cell(135, 5, "* LTG Capital Intelligence", align="C")

        return pdf

    def _build_transition_page(self, story: Dict, num: int) -> FPDF:
        """Build transition page (PAGE TYPE D)."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        bg_rgb = self._hex_to_rgb(self.colors['bg_primary'])
        text_rgb = self._hex_to_rgb(self.colors['text_primary'])
        gold_rgb = self._hex_to_rgb(self.colors['accent_gold'])

        # Background
        pdf.set_fill_color(*bg_rgb)
        pdf.rect(0, 0, 210, 297, 'F')

        # Symbol
        pdf.set_font("Helvetica", "B", 60)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(80, 80)
        pdf.cell(50, 40, "*", align="C", ln=True)

        # Next label
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(15, 140)
        pdf.cell(180, 4, "NEXT", align="C", ln=True)

        # Next headline
        pdf.set_font("Times", "B", 14)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, 150)
        pdf.multi_cell(180, 6, self._sanitize_text(story['headline'][:60]), align="C")

        # Category
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*self._hex_to_rgb(self.colors['text_muted_dark']))
        pdf.set_xy(15, pdf.get_y() + 5)
        pdf.cell(0, 4, self._sanitize_text(story['category']), align="C", ln=True)

        return pdf

    def _build_continuation_page(self, story: Dict, num: int, is_dark: bool) -> FPDF:
        """Build continuation page (PAGE TYPE C)."""
        if len(story['paragraphs']) < 2:
            return None

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        bg = self.colors['bg_page'] if is_dark else self.colors['bg_light']
        text_color = self.colors['text_primary'] if is_dark else self.colors['text_on_light']
        muted_color = self.colors['text_muted_dark'] if is_dark else self.colors['text_muted_light']

        bg_rgb = self._hex_to_rgb(bg)
        text_rgb = self._hex_to_rgb(text_color)
        muted_rgb = self._hex_to_rgb(muted_color)
        gold_rgb = self._hex_to_rgb(self.colors['accent_gold'])

        # Background
        pdf.set_fill_color(*bg_rgb)
        pdf.rect(0, 0, 210, 297, 'F')

        # Header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(15, 15)
        pdf.cell(0, 4, f"{self._sanitize_text(story['headline'][:30]).upper()} (CONT'D)", ln=True)

        pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
        pdf.ln(3)

        # Body text
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, 25)

        remaining_text = ' '.join(story['paragraphs'][1:])
        pdf.multi_cell(180, 4, self._sanitize_text(remaining_text))

        # Pull quote
        if story.get('pull_quote'):
            pdf.ln(5)
            pdf.set_font("Times", "I", 11)
            pdf.set_text_color(*muted_rgb)
            pdf.set_xy(25, pdf.get_y())
            pdf.multi_cell(160, 5, f'"{self._sanitize_text(story["pull_quote"])}"')
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*muted_rgb)
            pdf.cell(0, 3, "- LTG Capital Intelligence", ln=True)

        # Footer
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(15, 280)
        pdf.cell(30, 5, f"A-{num:02d}A")
        pdf.cell(135, 5, "* LTG Capital Intelligence", align="C")

        return pdf

    def _build_closing_page(self, data: Dict) -> FPDF:
        """Build closing page (PAGE TYPE E)."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        bg_rgb = self._hex_to_rgb(self.colors['bg_primary'])
        text_rgb = self._hex_to_rgb(self.colors['text_primary'])
        gold_rgb = self._hex_to_rgb(self.colors['accent_gold'])
        muted_rgb = self._hex_to_rgb(self.colors['text_muted_dark'])

        # Background
        pdf.set_fill_color(*bg_rgb)
        pdf.rect(0, 0, 210, 297, 'F')

        # Header rule
        pdf.line(15, 15, 195, 15)

        # Masthead
        pdf.set_font("Times", "B", 18)
        pdf.set_text_color(*text_rgb)
        pdf.set_xy(15, 30)
        pdf.cell(0, 8, "* LIGHT TOWER GROUP", align="C", ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*gold_rgb)
        pdf.cell(0, 4, "INSTITUTIONAL CAPITAL ADVISORY", align="C", ln=True)

        pdf.ln(5)

        # Two-column layout
        # Left column: About
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(15, 85)
        pdf.cell(90, 4, "ABOUT THE AUTHOR", ln=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(15, 90)
        pdf.multi_cell(85, 3,
            "Benjamin Rohr is the Principal of Light Tower Group, a New York-based institutional capital advisory firm specializing in debt and equity placement for complex commercial real estate transactions.")

        # Right column: Engage
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(110, 85)
        pdf.cell(85, 4, "ENGAGE WITH LTG", ln=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(110, 90)
        pdf.multi_cell(85, 3,
            "We work on a success-only basis. No retainers. Direct principal engagement on every mandate.")

        # Contact
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*gold_rgb)
        pdf.set_xy(110, 120)
        pdf.cell(0, 5, "ben@lighttowergroup.co", ln=True)
        pdf.cell(0, 5, "(347) 554-0093", ln=True)
        pdf.cell(0, 5, "lighttowergroup.co", ln=True)

        # Footer
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*muted_rgb)
        pdf.set_xy(15, 265)
        pdf.multi_cell(180, 2,
            "© 2026 Light Tower Group · LTG Capital Intelligence · All rights reserved. This publication is for informational purposes only and does not constitute investment advice.",
            align="C")

        return pdf

    async def generate_pdf(self, data: Dict, output_path: str) -> bool:
        """Generate complete multi-page PDF from article data."""
        try:
            pages = self.build_pages(data)

            if not pages:
                logger.error("No pages generated")
                return False

            # Create output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Merge all pages into one PDF
            pdf = pages[0]

            if len(pages) == 1:
                pdf.output(str(output_path))
            else:
                # Create combined PDF using pypdf
                from pypdf import PdfWriter, PdfReader
                from io import BytesIO

                writer = PdfWriter()

                for page_pdf in pages:
                    # Output each page to bytes
                    pdf_bytes = BytesIO()
                    page_pdf.output(pdf_bytes)
                    pdf_bytes.seek(0)

                    # Read and add to writer
                    reader = PdfReader(pdf_bytes)
                    for page in reader.pages:
                        writer.add_page(page)

                # Write final PDF
                with open(output_path, 'wb') as f:
                    writer.write(f)

            # Strip metadata
            writer = PdfWriter()
            reader = PdfReader(output_path)
            for page in reader.pages:
                writer.add_page(page)

            writer.metadata = {
                "/Title": "LTG Capital Intelligence",
                "/Author": "Light Tower Group",
            }

            with open(output_path, 'wb') as f:
                writer.write(f)

            logger.info(f"* LTG Capital Intelligence PDF: {output_path} ({len(pages)} pages)")
            return True

        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            return False


if __name__ == '__main__':
    import asyncio
    import sys
    from fetch_brand_colors import fetch_brand_colors
    from article_adapter import transform_article_to_pdf_schema

    if len(sys.argv) < 2:
        print("Usage: python generate_carousel_pdf.py <article_data.json> [output.pdf]")
        sys.exit(1)

    article_json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"

    with open(article_json_path) as f:
        data = json.load(f)

    colors = fetch_brand_colors()
    generator = CarouselPDFGenerator(colors)

    success = asyncio.run(generator.generate_pdf(data, output_path))
    sys.exit(0 if success else 1)
