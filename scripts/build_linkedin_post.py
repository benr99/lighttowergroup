"""
Generate ready-to-paste LinkedIn post text from article data.

Does NOT include a link — the PDF is the delivery vehicle.
"""

def build_linkedin_post_text(article_data: dict) -> str:
    """
    Generate LinkedIn post text.

    Formula:
    1. Hook (210 chars max): Analytical opening statement
    2. Body (1 paragraph): Summary of the week's themes
    3. Closing: Question for engagement + hashtags

    Does NOT link to article (PDF carousel is the delivery mechanism)
    """
    pub = article_data['publication']
    stories = article_data['stories']

    # HOOK — analytical statement, not a teaser
    # Aim for 180-210 characters
    hook = (
        f"Five institutional capital developments shaping CRE allocation this week. "
        f"What structural shifts are you tracking?"
    )

    if len(hook) > 210:
        hook = hook[:207] + "..."

    # BODY — synthesize all 5 stories into one flowing paragraph
    story_insights = []
    for story in stories[:5]:
        # Pull from deck
        if story['deck']:
            story_insights.append(story['deck'].rstrip('.') + '.')

    body = ' '.join(story_insights[:3])  # First 3 stories in main body

    # CLOSING — invitation + hashtags
    # Note: LinkedIn limits ~2950 characters, we're well under
    closing = (
        "\nFull analysis attached — swipe through the PDF carousel above for all five stories."
        "\n\n#CRE #CapitalMarkets #RealEstateFinance"
    )

    return hook + '\n\n' + body + closing


def save_linkedin_post(text: str, output_path: str):
    """Save post text to file for copy-paste."""
    from pathlib import Path
    Path(output_path).write_text(text, encoding='utf-8')
