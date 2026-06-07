"""
Generate ready-to-paste LinkedIn post text from carousel data.

The PDF is the delivery vehicle, so this post intentionally does not include a
separate article link.
"""

from pathlib import Path


def build_linkedin_post_text(article_data: dict) -> str:
    """Generate concise LinkedIn copy to accompany a single-article carousel."""
    slides = article_data.get("slides", [])
    hero = slides[0] if slides else {}

    hook = (hero.get("headline") or article_data.get("publication", {}).get("theme") or "").strip()
    if len(hook) > 210:
        hook = hook[:207].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."

    article_slides = [slide for slide in slides if slide.get("system") == "article"]
    opening = (article_slides[0].get("subhead") if article_slides else hero.get("subhead") or "").strip()
    if len(opening) > 280:
        opening = opening[:277].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."

    body = "Full Light Tower Group capital markets note attached as a PDF carousel."
    if opening:
        body = opening.rstrip(".") + ".\n\n" + body

    closing = "\n\n#CRE #CapitalMarkets #RealEstateFinance"
    return hook + "\n\n" + body + closing


def save_linkedin_post(text: str, output_path: str) -> None:
    """Save post text to file for copy-paste."""
    Path(output_path).write_text(text, encoding="utf-8")
