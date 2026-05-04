"""
Generate branded social media images for Light Tower Group articles.
Creates 1200x628px images for LinkedIn sharing with title, subtitle, and branding.

Requires: pip install Pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from pathlib import Path
import textwrap

# Brand colors (from index.html :root)
BRAND_BG = "#F5F4F0"        # Light cream background
BRAND_ACCENT = "#C9A84C"    # Gold accent
BRAND_TEXT = "#121212"      # Near-black text
BRAND_DARK = "#0E0E0E"      # Very dark (logo)
BRAND_WHITE = "#FFFFFF"

# LinkedIn image standard: 1200x628px (1.91:1 ratio)
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 628

# Padding and layout
PADDING_H = 60  # Horizontal padding
PADDING_V = 50  # Vertical padding


def get_fonts():
    """Load brand fonts or fall back to system fonts."""
    script_dir = Path(__file__).parent

    # Try to load Google Fonts (if downloaded locally)
    fonts = {
        "title": None,      # Playfair Display Bold for titles
        "subtitle": None,   # Space Grotesk Regular for subtitles
        "branding": None,   # Space Grotesk for branding text
    }

    # Try common font paths on Windows
    font_paths = [
        Path("C:/Windows/Fonts/playfair-display-bold.ttf"),
        Path("C:/Windows/Fonts/PlayfairDisplay-Bold.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]

    # Fall back to default system fonts
    try:
        fonts["title"] = ImageFont.truetype("arial.ttf", 56)
        fonts["subtitle"] = ImageFont.truetype("arial.ttf", 28)
        fonts["branding"] = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        # If TrueType fonts unavailable, use default
        fonts["title"] = ImageFont.load_default()
        fonts["subtitle"] = ImageFont.load_default()
        fonts["branding"] = ImageFont.load_default()

    return fonts


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within a maximum width."""
    lines = []
    for line in text.split('\n'):
        if not line.strip():
            lines.append("")
            continue

        words = line.split()
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

    Args:
        title (str): Article title (max 90 chars, but will be wrapped)
        subtitle (str): Article subtitle (one sentence, max 140 chars)
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

        # Calculate available width for text
        content_width = IMAGE_WIDTH - (2 * PADDING_H)

        # Wrap and draw title
        title_lines = wrap_text(title, fonts["title"], content_width, draw)

        y = PADDING_V
        line_height = 70

        for line in title_lines[:3]:  # Max 3 lines for title
            draw.text(
                (PADDING_H, y),
                line,
                font=fonts["title"],
                fill=BRAND_TEXT
            )
            y += line_height

        # Add accent line separator
        y += 20
        draw.rectangle(
            [(PADDING_H, y), (PADDING_H + 80, y + 4)],
            fill=BRAND_ACCENT
        )

        # Draw subtitle
        y += 25
        subtitle_lines = wrap_text(subtitle, fonts["subtitle"], content_width, draw)

        for line in subtitle_lines[:2]:  # Max 2 lines for subtitle
            draw.text(
                (PADDING_H, y),
                line,
                font=fonts["subtitle"],
                fill=BRAND_TEXT
            )
            y += 45

        # Draw branding at bottom
        branding_text = "Light Tower Group — Capital Markets Advisory"
        branding_bbox = draw.textbbox((0, 0), branding_text, font=fonts["branding"])
        branding_width = branding_bbox[2] - branding_bbox[0]

        # Right-align branding
        branding_x = IMAGE_WIDTH - PADDING_H - branding_width
        branding_y = IMAGE_HEIGHT - PADDING_V - 30

        draw.text(
            (branding_x, branding_y),
            branding_text,
            font=fonts["branding"],
            fill=BRAND_ACCENT
        )

        # Draw small brand accent line at bottom
        draw.rectangle(
            [(branding_x - 10, branding_y - 15), (branding_x, branding_y - 10)],
            fill=BRAND_ACCENT
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
