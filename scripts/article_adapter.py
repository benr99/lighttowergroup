"""
Transform existing article format into PDF schema.

Input: article data from daily_news_agent.py
Output: structured JSON for PDF generation
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

def extract_pull_quote_from_html(html: str) -> str:
    """
    Extract pull quote from article HTML.

    Convention: Author tags pull quote with <!-- PULL_QUOTE --> markers:
    <!-- PULL_QUOTE -->Most analytical sentence<!-- /PULL_QUOTE -->

    If no tag found: auto-extract most analytical sentence.
    """
    # Try explicit tag first
    match = re.search(r'<!-- PULL_QUOTE -->(.*?)<!-- /PULL_QUOTE -->', html, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: auto-extract most analytical sentence
    analytical_verbs = ['indicates', 'signals', 'suggests', 'means', 'reveals',
                        'shows', 'demonstrates', 'underscores', 'reflects',
                        'drives', 'determines', 'creates', 'establishes']

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', html)
    for sent in sentences:
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', sent).strip()
        word_count = len(clean.split())

        if 15 < word_count < 35:  # 15–35 words
            if any(verb in clean.lower() for verb in analytical_verbs):
                return clean

    # Last resort: first sentence of second paragraph
    paras = re.split(r'</p>', html)
    if len(paras) > 1:
        second_para = paras[1]
        first_sent = re.split(r'(?<=[.!?])\s+', second_para)
        if first_sent:
            clean = re.sub(r'<[^>]+>', '', first_sent[0]).strip()
            if clean:
                return clean

    return "LTG Capital Intelligence"  # Last resort fallback


def extract_key_figures(headline: str, paragraphs: List[str]) -> List[Dict]:
    """
    Extract 1–2 key data points from article.

    Look for:
    - Dollar amounts ($X.XB, $X.XM, $X.XK)
    - Percentages (XX%)
    """
    figures = []

    # Look in headline first for dollar amounts
    dollar_match = re.search(r'\$[\d.]+[BMK]', headline)
    if dollar_match:
        figures.append({
            "number": dollar_match.group(0),
            "label": "Key Metric"
        })

    # Then first two paragraphs for more figures
    text = ' '.join(paragraphs[:2])

    # Dollar amounts
    dollars = re.findall(r'\$[\d.]+[BMK]', text)
    if dollars and len(figures) < 2:
        # Skip if already in headline
        if not dollar_match or dollars[0] != dollar_match.group(0):
            figures.append({
                "number": dollars[0],
                "label": "Amount"
            })

    # Percentages
    percents = re.findall(r'(\d+(?:\.\d+)?%)', text)
    if percents and len(figures) < 2:
        figures.append({
            "number": percents[0],
            "label": "Rate/Margin"
        })

    return figures[:2]  # Max 2


def get_publication_metadata() -> dict:
    """
    Read publication metadata from publication-metadata.json.

    Auto-increments volume if issue_date is > 30 days after last_issue_date.
    """
    metadata_path = Path(__file__).parent.parent / 'publication-metadata.json'

    if not metadata_path.exists():
        # First-time initialization
        initial = {
            "current_volume": 1,
            "last_issue_date": datetime.now().isoformat()[:10],
            "publication_start": "2026-01-01"
        }
        metadata_path.write_text(json.dumps(initial, indent=2))
        return initial

    with open(metadata_path) as f:
        metadata = json.load(f)

    # Check if we should increment volume
    last_date = datetime.fromisoformat(metadata['last_issue_date'])
    today = datetime.now()
    days_since = (today - last_date).days

    if days_since > 30:  # Monthly or more frequent
        metadata['current_volume'] += 1
        metadata['last_issue_date'] = today.isoformat()[:10]
        metadata_path.write_text(json.dumps(metadata, indent=2))
        logger.info(f"Incremented publication volume to {metadata['current_volume']}")

    return metadata


def transform_article_to_pdf_schema(
    article_html: str,
    article_data: dict,
    theme: str = None
) -> dict:
    """
    Transform existing article into PDF schema.

    INPUT: article_data from daily_news_agent.py
    {
        "headline": "...",
        "body": "<p>...</p><p>...</p>...",
        "excerpt": "...",
        "slug": "...",
        "date": "2026-05-26"
    }

    OUTPUT: PDF schema for carousel generation
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(article_data['body'], 'html.parser')

    # Extract paragraphs
    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all('p')
        if p.get_text(strip=True)
    ]

    if not paragraphs:
        raise ValueError(f"No paragraphs found in article: {article_data.get('slug')}")

    # Split 5 stories from the paragraphs
    # NOTE: This assumes the article contains 5 distinct story sections
    # In production, this would be more intelligent parsing
    if len(paragraphs) < 5:
        raise ValueError(f"Article has {len(paragraphs)} paragraphs, need ≥5 stories")

    stories = []
    category_patterns = {
        'Capital Markets': ['REIT', 'equity', 'debt', 'capital', 'fund', 'financing', 'bond'],
        'Policy': ['policy', 'regulation', 'law', 'bill', 'albany', 'senate'],
        'Transactions': ['acquisition', 'sale', 'deal', 'sold', 'purchased', 'merger'],
        'Development': ['development', 'construction', 'built', 'building', 'lease'],
    }

    for i in range(min(5, len(paragraphs))):
        story_text = paragraphs[i]

        # Extract category from headline or first paragraph
        category = "Capital Markets"  # Default
        for cat, keywords in category_patterns.items():
            combined_text = (story_text + ' ' + article_data.get('headline', '')).lower()
            if any(kw in combined_text for kw in keywords):
                category = cat
                break

        # Extract headline from first sentence
        first_sent = story_text.split('.')[0].strip()
        headline = first_sent if len(first_sent) < 80 else first_sent[:77] + "..."

        # Deck: second sentence if available
        sentences = re.split(r'(?<=[.!?])\s+', story_text)
        deck = sentences[1] if len(sentences) > 1 else ''
        if len(deck) > 150:
            deck = deck[:147] + "..."

        stories.append({
            "number": i + 1,
            "category": category,
            "headline": headline,
            "deck": deck,
            "dateline": "NEW YORK",
            "date": article_data.get('date', datetime.now().isoformat()[:10]),
            "source": "Light Tower Group Analysis",
            "key_figures": extract_key_figures(headline, [story_text]),
            "pull_quote": extract_pull_quote_from_html(article_html),
            "paragraphs": [story_text]
        })

    # Get publication metadata
    pub_meta = get_publication_metadata()
    issue_date = datetime.fromisoformat(article_data.get('date', datetime.now().isoformat()[:10]))
    issue_month = issue_date.strftime("%B %Y")

    if not theme:
        # Auto-generate theme from main article headline
        theme = f"{article_data.get('headline', 'Five Stories')} in {issue_month}"

    return {
        "publication": {
            "volume": pub_meta['current_volume'],
            "issue_date": article_data.get('date'),
            "issue_month": issue_month,
            "theme": theme
        },
        "author": {
            "name": "Benjamin Rohr",
            "title": "Principal, Light Tower Group",
            "email": "ben@lighttowergroup.co"
        },
        "stories": stories
    }
