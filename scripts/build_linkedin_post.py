"""
Generate ready-to-paste LinkedIn post text from carousel data.

The PDF is the delivery vehicle, so this post intentionally does not include a
separate article link.
"""

from pathlib import Path


def build_linkedin_post_text(article_data: dict) -> str:
    """Generate concise LinkedIn copy to accompany a PDF carousel."""
    stories = article_data["stories"]

    hook = (
        "Five institutional capital developments shaping CRE allocation this week. "
        "What structural shifts are you tracking?"
    )
    if len(hook) > 210:
        hook = hook[:207] + "..."

    story_insights = []
    for story in stories[:5]:
        deck = (story.get("deck") or "").strip()
        if deck:
            story_insights.append(deck.rstrip(".") + ".")
    body = " ".join(story_insights[:3])

    closing = (
        "\nFull analysis attached - swipe through the PDF carousel above for all five stories."
        "\n\n#CRE #CapitalMarkets #RealEstateFinance"
    )
    return hook + "\n\n" + body + closing


def save_linkedin_post(text: str, output_path: str) -> None:
    """Save post text to file for copy-paste."""
    Path(output_path).write_text(text, encoding="utf-8")
