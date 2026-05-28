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
    close = slides[-1] if slides else {}

    hook = (hero.get("headline") or article_data.get("publication", {}).get("theme") or "").strip()
    if len(hook) > 210:
        hook = hook[:207].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."

    implication = (close.get("subhead") or hero.get("subhead") or "").strip()
    if len(implication) > 260:
        implication = implication[:257].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."

    body = (
        "The attached carousel breaks down the transaction, the numbers, "
        "and why it matters for capital markets."
    )
    if implication:
        body = implication.rstrip(".") + ".\n\n" + body

    closing = "\n\n#CRE #CapitalMarkets #RealEstateFinance"
    return hook + "\n\n" + body + closing


def save_linkedin_post(text: str, output_path: str) -> None:
    """Save post text to file for copy-paste."""
    Path(output_path).write_text(text, encoding="utf-8")
