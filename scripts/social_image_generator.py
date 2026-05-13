"""
Generate branded social media images for Light Tower Group articles.
Creates 1200x628px images for LinkedIn sharing with WSJ-inspired design:
- Large serif headline (Playfair Display Bold)
- Gold separator rule
- Clean sans-serif subtitle (Space Grotesk Regular)
- Brand name at bottom (Space Grotesk Bold)

Requires: pip install Pillow
          python scripts/setup_fonts.py (to download brand fonts)
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from pathlib import Path

# Brand colors (from index.html :root)
BRAND_BG = "#F5F4F0"        # Light cream background
BRAND_ACCENT = "#C9A84C"    # Gold accent
BRAND_TEXT = "#121212"      # Near-black text
BRAND_MUTED = "#555555"     # Muted gray for subtitle

# LinkedIn image standard: 1200x628px (1.91:1 ratio)
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 628

# Layout constants
TOP_PADDING = 52
BOTTOM_PADDING = 48
SIDE_PADDING = 60
RULE_WIDTH = 60
RULE_HEIGHT = 3
RULE_GAP = 20


def get_fonts():
    """Load brand fonts from scripts/fonts/ directory with Arial fallback."""
    script_dir = Path(__file__).parent
    fonts_dir = script_dir / "fonts"

    fonts = {
        "title": None,      # Playfair Display Bold for titles (72px)
        "subtitle": None,   # Space Grotesk Regular for subtitles (34px)
        "branding": None,   # Space Grotesk Bold for brand name (40px)
    }

    try:
        # Try to load from local fonts directory (downloaded by setup_fonts.py)
        fonts["title"] = ImageFont.truetype(
            str(fonts_dir / "PlayfairDisplay-Bold.ttf"), 72
        )
        fonts["subtitle"] = ImageFont.truetype(
            str(fonts_dir / "SpaceGrotesk-Regular.ttf"), 34
        )
        fonts["branding"] = ImageFont.truetype(
            str(fonts_dir / "SpaceGrotesk-Bold.ttf"), 40
        )
        return fonts
    except Exception:
        pass

    # Fallback to system fonts
    try:
        fonts["title"] = ImageFont.truetype("arial.ttf", 72)
        fonts["subtitle"] = ImageFont.truetype("arial.ttf", 34)
        fonts["branding"] = ImageFont.truetype("arial.ttf", 40)
        return fonts
    except Exception:
        # Last resort: system default
        default_font = ImageFont.load_default()
        fonts["title"] = default_font
        fonts["subtitle"] = default_font
        fonts["branding"] = default_font
        return fonts


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within a maximum width, respecting line breaks."""
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append("")
            continue

        words = paragraph.split()
        current = []

        for word in words:
            test_line = ' '.join(current + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]

        if current:
            lines.append(' '.join(current))

    return lines


def generate_article_image(title, subtitle, output_path):
    """
    Generate a branded social media image for a Light Tower Group article.
    WSJ-inspired design: large serif title, gold rule, sans-serif subtitle, branding at bottom.

    Args:
        title (str): Article title (will be wrapped to max ~3 lines)
        subtitle (str): Article subtitle (will be wrapped to max ~2 lines)
        output_path (str|Path): Where to save the PNG image

    Returns:
        bool: True if successful, False otherwise
    """
    if not PILLOW_AVAILABLE:
        print(f"    [SKIP] Pillow not installed (pip install Pillow)")
        return False

    try:
        # Create image with brand background
        img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color=BRAND_BG)
        draw = ImageDraw.Draw(img)

        fonts = get_fonts()

        # Content width (both sides)
        content_width = IMAGE_WIDTH - (2 * SIDE_PADDING)

        # ===== TITLE (Playfair Display Bold, 72px) =====
        title_lines = wrap_text(title, fonts["title"], content_width, draw)
        title_lines = title_lines[:3]  # Max 3 lines

        y = TOP_PADDING
        title_line_height = 80  # Tight leading (72px font + 8px gap)

        for line in title_lines:
            draw.text(
                (SIDE_PADDING, y),
                line,
                font=fonts["title"],
                fill=BRAND_TEXT
            )
            y += title_line_height

        # ===== GOLD SEPARATOR RULE =====
        y += RULE_GAP
        rule_y = y
        draw.rectangle(
            [(SIDE_PADDING, rule_y), (SIDE_PADDING + RULE_WIDTH, rule_y + RULE_HEIGHT)],
            fill=BRAND_ACCENT
        )

        # ===== SUBTITLE (Space Grotesk Regular, 34px, muted) =====
        y = rule_y + RULE_GAP + RULE_HEIGHT
        subtitle_lines = wrap_text(subtitle, fonts["subtitle"], content_width, draw)
        subtitle_lines = subtitle_lines[:2]  # Max 2 lines

        subtitle_line_height = 50  # 34px font + gap

        for line in subtitle_lines:
            draw.text(
                (SIDE_PADDING, y),
                line,
                font=fonts["subtitle"],
                fill=BRAND_MUTED
            )
            y += subtitle_line_height

        # ===== BRANDING (Space Grotesk Bold, 40px, bottom-left) =====
        # "LIGHT TOWER GROUP." with uppercase letter-spacing matching nav logo
        branding_text = "LIGHT TOWER GROUP."
        branding_y = IMAGE_HEIGHT - BOTTOM_PADDING

        draw.text(
            (SIDE_PADDING, branding_y),
            branding_text,
            font=fonts["branding"],
            fill=BRAND_TEXT
        )

        # Save the image
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, 'PNG', quality=95)

        return True

    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        return False


if __name__ == "__main__":
    # Test the image generator
    test_title = "Meyer Chetrit's Four-Decade Empire Faces $171M in Court Judgments"
    test_subtitle = "When cheap debt and speed meet a rate cycle, judges redistribute capital."
    test_output = Path("test_social_image.png")

    if generate_article_image(test_title, test_subtitle, test_output):
        print(f"✓ Test image generated: {test_output}")
    else:
        print("✗ Test image generation failed")
