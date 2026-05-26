#!/usr/bin/env python3
"""
Download brand fonts from Google Fonts for social images and PDF carousel generation.

Fonts for social images:
- Playfair Display Bold (700)
- Space Grotesk Regular (400)
- Space Grotesk Bold (700)

Fonts for PDF carousel:
- Cormorant Garamond: 400, 600, 700, 400i, 600i
- EB Garamond: 400, 500, 400i
- Inter: 400, 500

Usage:
  python setup_fonts.py
"""

import requests
import re
import sys
from pathlib import Path

FONTS_DIR = Path(__file__).parent / "fonts"

FONTS_TO_DOWNLOAD = [
    # Social image fonts
    {
        "family": "Playfair+Display",
        "weight": 700,
        "output": "PlayfairDisplay-Bold.ttf",
    },
    {
        "family": "Space+Grotesk",
        "weight": 400,
        "output": "SpaceGrotesk-Regular.ttf",
    },
    {
        "family": "Space+Grotesk",
        "weight": 700,
        "output": "SpaceGrotesk-Bold.ttf",
    },
    # PDF carousel fonts
    {
        "family": "Cormorant+Garamond",
        "weight": 400,
        "output": "CormorantGaramond-Regular.ttf",
    },
    {
        "family": "Cormorant+Garamond",
        "weight": 600,
        "output": "CormorantGaramond-SemiBold.ttf",
    },
    {
        "family": "Cormorant+Garamond",
        "weight": 700,
        "output": "CormorantGaramond-Bold.ttf",
    },
    {
        "family": "EB+Garamond",
        "weight": 400,
        "output": "EBGaramond-Regular.ttf",
    },
    {
        "family": "EB+Garamond",
        "weight": 500,
        "output": "EBGaramond-SemiBold.ttf",
    },
    {
        "family": "Inter",
        "weight": 400,
        "output": "Inter-Regular.ttf",
    },
    {
        "family": "Inter",
        "weight": 500,
        "output": "Inter-SemiBold.ttf",
    },
]


def download_font(family_css_name, weight, output_filename):
    """Download a font from Google Fonts API."""
    output_path = FONTS_DIR / output_filename

    if output_path.exists():
        print(f"  [OK] {output_filename} already exists, skipping")
        return True

    try:
        # Try with classic user-agent first to get TTF
        url = f"https://fonts.googleapis.com/css2?family={family_css_name}:wght@{weight}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        print(f"  Downloading {output_filename}...")
        css_response = requests.get(url, headers=headers, timeout=10)
        css_response.raise_for_status()

        # Parse the CSS response to find the font URL
        # Format: src: url(https://...);
        match = re.search(r'src:\s*url\(([^)]+)\)', css_response.text)
        if not match:
            print(f"  [ERROR] Could not parse font URL from CSS response")
            return False

        font_url = match.group(1)
        print(f"    Fetching: {font_url[:80]}...")

        # Download the font file
        font_response = requests.get(font_url, timeout=10)
        font_response.raise_for_status()

        # Save to disk (accept any font format)
        output_path.write_bytes(font_response.content)
        print(f"  [OK] {output_filename} ({len(font_response.content)} bytes)")
        return True

    except Exception as e:
        print(f"  [ERROR] {output_filename}: {e}")
        return False


def main():
    print("Light Tower Group - Font Setup")
    print("=" * 50)

    # Create fonts directory
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nFonts directory: {FONTS_DIR}")

    success_count = 0
    for font in FONTS_TO_DOWNLOAD:
        if download_font(font["family"], font["weight"], font["output"]):
            success_count += 1

    print(f"\n{'=' * 50}")
    print(f"Downloaded {success_count}/{len(FONTS_TO_DOWNLOAD)} fonts")

    if success_count == len(FONTS_TO_DOWNLOAD):
        print("[OK] All fonts ready for social_image_generator.py and PDF carousel")
        return 0
    else:
        print("[ERROR] Some fonts failed to download")
        return 1


if __name__ == "__main__":
    exit(main())
