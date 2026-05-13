#!/usr/bin/env python3
"""
Regenerate all Light Tower Group insight social images with new WSJ-inspired design.
Also updates og:image meta tags on HTML pages with proper width/height attributes.

Reads from insights.json and generates PNG images for all articles, then updates
the corresponding HTML files with complete Open Graph meta tags.
"""

import json
import re
from pathlib import Path
from social_image_generator import generate_article_image

ROOT = Path(__file__).parent.parent
INSIGHTS_DIR = ROOT / "insights"


def load_articles():
    """Load all articles from insights.json."""
    try:
        with open(ROOT / "insights.json", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load insights.json: {e}")
        return []


def get_html_path(slug):
    """Get the HTML file path for an article slug."""
    return INSIGHTS_DIR / f"{slug}.html"


def read_html(path):
    """Read HTML file with proper encoding."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def write_html(path, content):
    """Write HTML file with proper encoding."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"    [ERROR] Failed to write {path}: {e}")
        return False


def insert_social_image(html_content, slug):
    """
    Insert the social image into the article after the header section.
    Looks for the article-rule (hr) and inserts the image after it.
    """
    image_url = f"/insights/{slug}_social.png"
    image_html = (
        f'\n      <figure class="article-image">\n'
        f'        <img src="{image_url}" alt="Article summary image" '
        f'style="width: 100%; height: auto; display: block; margin: 2rem 0; border-radius: 2px;">\n'
        f'      </figure>\n'
    )

    # Find the article-rule (hr) and insert the image after it
    # Pattern: <hr class="article-rule"> ... <div class="article-body"
    pattern = r'(<hr class="article-rule">)\s*(?=<div class="article-body")'
    html_content = re.sub(pattern, r'\1' + image_html, html_content, count=1)

    return html_content


def update_og_tags(html_content, slug, title, subtitle):
    """
    Update Open Graph meta tags in HTML with proper format for LinkedIn sharing.

    Replaces or adds:
    - og:title
    - og:description
    - og:image
    - og:image:width
    - og:image:height
    - og:image:type
    - og:url
    """
    image_url = f"https://lighttowergroup.co/insights/{slug}_social.png"

    # Meta tag patterns to match and replace
    og_patterns = {
        'og:title': (
            r'<meta\s+property="og:title"\s+content="[^"]*"',
            f'<meta property="og:title" content="{title.replace('"', '&quot;')}"'
        ),
        'og:description': (
            r'<meta\s+property="og:description"\s+content="[^"]*"',
            f'<meta property="og:description" content="{subtitle.replace('"', '&quot;')}"'
        ),
        'og:image': (
            r'<meta\s+property="og:image"\s+content="[^"]*"',
            f'<meta property="og:image" content="{image_url}"'
        ),
        'og:url': (
            r'<meta\s+property="og:url"\s+content="[^"]*"',
            f'<meta property="og:url" content="{image_url.replace("_social.png", ".html")}"'
        ),
    }

    # Replace existing og: tags
    for tag, (pattern, replacement) in og_patterns.items():
        html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)

    # Clean up any duplicate og:image tags (keep only the first set)
    # Remove duplicate og:image:width and og:image:height lines
    lines = html_content.split('\n')
    seen_og_image_width = False
    seen_og_image_height = False
    seen_og_image_type = False
    cleaned_lines = []

    for line in lines:
        skip = False
        if 'og:image:width' in line:
            if seen_og_image_width:
                skip = True
            seen_og_image_width = True
        elif 'og:image:height' in line:
            if seen_og_image_height:
                skip = True
            seen_og_image_height = True
        elif 'og:image:type' in line:
            if seen_og_image_type:
                skip = True
            seen_og_image_type = True

        if not skip:
            cleaned_lines.append(line)

    html_content = '\n'.join(cleaned_lines)

    # Add og:image dimension and type tags if they don't exist
    if 'og:image:width' not in html_content:
        og_image_pattern = r'(<meta\s+property="og:image"\s+content="[^"]*">)'
        insert_text = (
            r'\1\n  <meta property="og:image:width" content="1200">'
            r'\n  <meta property="og:image:height" content="628">'
            r'\n  <meta property="og:image:type" content="image/png">'
        )
        html_content = re.sub(og_image_pattern, insert_text, html_content, count=1)

    return html_content


def main():
    print("Light Tower Group - Backfill Social Images")
    print("=" * 60)

    articles = load_articles()
    if not articles:
        print("[ERROR] No articles found in insights.json")
        return 1

    print(f"\nFound {len(articles)} articles in insights.json")
    print(f"Regenerating social images in: {INSIGHTS_DIR}")
    print()

    success_count = 0
    updated_html_count = 0
    skipped_count = 0

    for i, article in enumerate(articles, 1):
        slug = article.get('slug')
        title = article.get('title', 'Untitled')
        subtitle = article.get('excerpt', '')

        if not slug:
            print(f"  [{i}/{len(articles)}] [SKIP] No slug found")
            skipped_count += 1
            continue

        # Generate image
        img_path = INSIGHTS_DIR / f"{slug}_social.png"
        ok = generate_article_image(title, subtitle, img_path)

        if ok:
            success_count += 1
            status = "[OK]"
        else:
            status = "[FAIL]"

        # Update HTML page with og: meta tags and insert social image
        html_path = get_html_path(slug)
        if html_path.exists():
            html_content = read_html(html_path)
            if html_content:
                # Update og: meta tags
                updated_html = update_og_tags(html_content, slug, title, subtitle)
                # Insert the social image into the article
                updated_html = insert_social_image(updated_html, slug)

                if write_html(html_path, updated_html):
                    updated_html_count += 1
                    print(f"  [{i}/{len(articles)}] {status} {slug[:50]}")
                else:
                    print(f"  [{i}/{len(articles)}] {status} {slug[:50]} (HTML update failed)")
            else:
                print(f"  [{i}/{len(articles)}] {status} {slug[:50]} (couldn't read HTML)")
        else:
            print(f"  [{i}/{len(articles)}] {status} {slug[:50]} (HTML not found)")

    print()
    print("=" * 60)
    print(f"Generated images: {success_count}/{len(articles)}")
    print(f"Updated HTML pages: {updated_html_count}/{len(articles)}")
    print(f"Skipped: {skipped_count}/{len(articles)}")

    if success_count == len(articles):
        print("\n[OK] All social images regenerated successfully!")
        return 0
    else:
        print(f"\n[WARNING] {len(articles) - success_count} images failed to generate")
        return 1


if __name__ == "__main__":
    exit(main())
