"""
Validate generated PDF carousels for quality and completeness.
"""

import logging
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def validate_generated_pdf(pdf_path: str, expected_data: dict) -> list:
    """
    Validate generated PDF against expectations.
    Returns list of errors (empty if valid).
    """
    errors = []

    if not Path(pdf_path).exists():
        return ["PDF file does not exist"]

    try:
        pdf = PdfReader(pdf_path)

        # Check page count (rough estimate: 1 cover + 5 stories + transitions + closing)
        # Minimum: 14, Maximum: 20 is ideal
        page_count = len(pdf.pages)
        if page_count < 12:
            errors.append(f"PDF has only {page_count} pages (expected 14–20)")
        elif page_count > 25:
            errors.append(f"PDF has {page_count} pages (expected max ~20)")

        # Check metadata stripped (Creator field should be minimal)
        if pdf.metadata:
            creator = pdf.metadata.get('/Creator', '')
            if creator and len(creator) > 50:
                errors.append(f"PDF metadata not properly stripped (Creator: {creator[:30]}...)")

        # Check file size
        file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        if file_size_mb > 15:
            errors.append(f"PDF is {file_size_mb:.1f}MB (max 15MB)")
        elif file_size_mb < 0.5:
            errors.append(f"PDF is very small ({file_size_mb:.2f}MB), may be empty")

        # Check all pages have content
        empty_pages = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text or len(text.strip()) < 50:
                empty_pages.append(i + 1)

        if empty_pages:
            errors.append(f"Pages {empty_pages} appear empty or mostly blank")

        # Check for key content on first page
        first_page_text = pdf.pages[0].extract_text().lower()
        if 'ltg capital intelligence' not in first_page_text:
            errors.append("Cover page missing publication masthead")

        # Check for closing page
        last_page_text = pdf.pages[-1].extract_text().lower()
        if 'light tower group' not in last_page_text:
            errors.append("Closing page missing publication colophon")

    except Exception as e:
        errors.append(f"Failed to read PDF: {str(e)}")

    return errors


def run_validation_report(pdf_path: str, article_data: dict = None) -> dict:
    """
    Run comprehensive validation and return report.
    """
    errors = validate_generated_pdf(pdf_path, article_data or {})

    report = {
        "valid": len(errors) == 0,
        "errors": errors,
        "file_path": str(pdf_path),
        "file_size_mb": Path(pdf_path).stat().st_size / (1024 * 1024) if Path(pdf_path).exists() else 0,
    }

    if Path(pdf_path).exists():
        try:
            pdf = PdfReader(pdf_path)
            report['page_count'] = len(pdf.pages)
        except:
            pass

    return report
