#!/usr/bin/env python3
"""
Backfill og:image and twitter:image meta tags into all existing article HTML files.
Run once after updating render_html() to inject image meta tags.
"""

from pathlib import Path
import re

INSIGHTS_DIR = Path(__file__).parent.parent / "insights"
SITE_URL = "https://lighttowergroup.co"

print("Backfilling og:image and twitter:image tags into existing articles...\n")

patched_count = 0
skipped_count = 0

for html_file in sorted(INSIGHTS_DIR.glob("*.html")):
    # Skip the main insights index page
    if html_file.name in ("index.html", "insights.html"):
        continue

    slug = html_file.stem
    social_url = f"{SITE_URL}/insights/{slug}_social.png"

    content = html_file.read_text(encoding="utf-8")

    # Check if already has og:image
    if "og:image" in content:
        print(f"  SKIP: {html_file.name} (already has og:image)")
        skipped_count += 1
        continue

    # Patch 1: Insert og:image* tags after og:site_name
    og_image_block = (
        f'  <meta property="og:image"        content="{social_url}">\n'
        f'  <meta property="og:image:width"  content="1200">\n'
        f'  <meta property="og:image:height" content="628">\n'
        f'  <meta property="og:image:alt"    content="{slug.replace("-", " ").title()}">\n'
    )

    # Find the og:site_name line and insert after it
    content = re.sub(
        r'(<meta property="og:site_name"[^>]*>\n)',
        r'\1' + og_image_block,
        content,
        count=1
    )

    # Patch 2: Add twitter:image after twitter:description
    tw_image_tag = f'  <meta name="twitter:image"       content="{social_url}">\n'

    # Find twitter:description line and insert twitter:image after it
    content = re.sub(
        r'(<meta name="twitter:description"[^>]*>\n)',
        r'\1' + tw_image_tag,
        content,
        count=1
    )

    # Write the patched content back
    html_file.write_text(content, encoding="utf-8")
    print(f"  PATCHED: {html_file.name}")
    patched_count += 1

print(f"\n✓ Backfill complete!")
print(f"  Patched: {patched_count}")
print(f"  Skipped (already updated): {skipped_count}")
