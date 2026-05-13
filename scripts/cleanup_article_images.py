#!/usr/bin/env python3
"""
Remove <figure class="article-image"> elements from all insight pages.
One-time cleanup of the accidentally-inserted image figures from the previous backfill run.
"""

import re
from pathlib import Path

INSIGHTS_DIR = Path(__file__).parent.parent / "insights"
figure_pattern = re.compile(
    r'\s*<figure class="article-image">.*?</figure>\s*',
    re.DOTALL
)

print("Light Tower Group - Article Image Cleanup")
print("=" * 50)
print(f"Processing: {INSIGHTS_DIR}\n")

count = 0
for html_file in sorted(INSIGHTS_DIR.glob("*.html")):
    content = html_file.read_text(encoding='utf-8')
    cleaned = figure_pattern.sub('\n', content)

    if cleaned != content:
        html_file.write_text(cleaned, encoding='utf-8')
        count += 1
        print(f"  Cleaned: {html_file.name}")

print(f"\n{'=' * 50}")
print(f"Cleaned {count} files")
