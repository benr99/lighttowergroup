"""
Validate generated PDF carousels for quality and completeness.

Deep validation uses pypdf when installed. If pypdf is unavailable, this module
still performs basic checks and never prevents article publishing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_reader():
    try:
        from pypdf import PdfReader
        return PdfReader
    except Exception:
        return None


def validate_generated_pdf(pdf_path: str, expected_data: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    path = Path(pdf_path)
    if not path.exists():
        return ["PDF file does not exist"]
    if path.stat().st_size < 15_000:
        errors.append(f"PDF is very small ({path.stat().st_size} bytes), may be incomplete")

    PdfReader = _load_reader()
    if PdfReader is None:
        return errors

    try:
        pdf = PdfReader(str(path))
        page_count = len(pdf.pages)
        if page_count < 10:
            errors.append(f"PDF has only {page_count} pages (expected at least 10)")
        elif page_count > 20:
            errors.append(f"PDF has {page_count} pages (expected max 20)")

        empty_pages = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if len(text.strip()) < 25:
                empty_pages.append(i + 1)
        if empty_pages:
            errors.append(f"Pages {empty_pages} appear empty or mostly blank")

        first_text = (pdf.pages[0].extract_text() or "").lower()
        if "ltg capital intelligence" not in first_text:
            errors.append("Cover page missing publication masthead")

        last_text = (pdf.pages[-1].extract_text() or "").lower()
        if "light tower group" not in last_text:
            errors.append("Closing page missing publication colophon")
    except Exception as exc:
        errors.append(f"Failed to read PDF: {exc}")

    return errors


def run_validation_report(pdf_path: str, article_data: dict[str, Any] | None = None) -> dict[str, Any]:
    path = Path(pdf_path)
    errors = validate_generated_pdf(pdf_path, article_data or {})
    report: dict[str, Any] = {
        "valid": len(errors) == 0,
        "errors": errors,
        "file_path": str(path),
        "file_size_mb": path.stat().st_size / (1024 * 1024) if path.exists() else 0,
        "deep_validation": False,
    }

    PdfReader = _load_reader()
    if path.exists() and PdfReader is not None:
        try:
            pdf = PdfReader(str(path))
            report["page_count"] = len(pdf.pages)
            report["deep_validation"] = True
        except Exception:
            pass
    return report
