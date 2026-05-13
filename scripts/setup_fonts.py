#!/usr/bin/env python3
"""
Download brand fonts from Google Fonts for use in social image generation.

This script downloads:
- Playfair Display Bold (700)
- Space Grotesk Regular (400)
- Space Grotesk Bold (700)

Usage:
  python setup_fonts.py
"""

import requests
import re
import sys
from pathlib import Path

FONTS_DIR = Path(__file__).parent / "fonts"

FONTS_TO_DOWNLOAD = [
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
        print("[OK] All fonts ready for social_image_generator.py")
        return 0
    else:
        print("[ERROR] Some fonts failed to download")
        return 1


if __name__ == "__main__":
    exit(main())
