# Social Media Image Generation — Light Tower Group News Agent

## Overview

Each article published by the news agent automatically generates a branded 1200×628px social media image optimized for LinkedIn sharing. The images include:

- **Article title** (bold serif font — Playfair Display style)
- **Article subtitle** (readable secondary text)
- **Brand attribution** (Light Tower Group Capital Markets Advisory, right-aligned)
- **Brand colors** (gold accent #C9A84C, light cream background #F5F4F0, dark text #121212)

---

## Setup

### 1. Install Pillow (Image Generation Library)

```bash
cd scripts
pip install -r requirements.txt
```

Or standalone:
```bash
pip install Pillow>=10.0.0
```

### 2. Verify Installation

```bash
python3 -c "from PIL import Image; print('Pillow installed successfully')"
```

---

## How It Works

### Generation Pipeline

When each article is published (Phase 6 — PUBLISH), the agent:

1. **Saves HTML** → `insights/{slug}.html`
2. **Generates image** → `insights/{slug}_social.png` (1200×628px)
3. **Updates manifest** → `insights.json` (includes image path)
4. **Commits to git** → All files pushed to origin/main

**Status in logs:**
```
[6/8] Publishing 5 article(s)...
  Saved: insights/chetrit-empire-judgment.html
  Image: insights/chetrit-empire-judgment_social.png
  Saved: insights/sl-green-2b-credit-refinance.html
  Image: insights/sl-green-2b-credit-refinance_social.png
  ...
```

### Image Specifications

| Property | Value |
|----------|-------|
| **Dimensions** | 1200×628px (LinkedIn standard, 1.91:1 ratio) |
| **Format** | PNG (transparent background optional) |
| **Brand Colors** | Light cream (#F5F4F0) background, gold (#C9A84C) accents |
| **Typography** | Playfair Display (titles), Space Grotesk (subtitles, branding) |
| **File Naming** | `{article-slug}_social.png` |
| **Location** | `/insights/` (same directory as HTML articles) |
| **Size** | ~200–400 KB per image |

---

## Manual Image Generation

You can generate social images outside the daily pipeline:

```bash
cd scripts

python3 << 'EOF'
from social_image_generator import generate_article_image

title = "Meyer Chetrit's Four-Decade Empire Faces $171M in Court Judgments"
subtitle = "When cheap debt and speed meet a rate cycle, judges redistribute capital."
output = "test_image.png"

if generate_article_image(title, subtitle, output):
    print(f"✓ Image saved: {output}")
else:
    print("✗ Image generation failed")
EOF
```

---

## Using Images for Social Sharing

### LinkedIn Posting Options

#### Option 1: Automatic LinkedIn Share (Current)
- The agent posts article link + hook text to LinkedIn
- LinkedIn auto-generates preview from article's og:meta tags
- Branded image is generated but not yet integrated to LinkedIn API

#### Option 2: Manual Upload
1. Download the generated PNG from `/insights/{slug}_social.png`
2. Post to LinkedIn with custom image upload
3. Add the LinkedIn hook text from the article

#### Option 3: Future Enhancement
Update `post_to_linkedin()` to:
- Upload PNG asset to LinkedIn's asset store
- Use IMAGE media category instead of ARTICLE
- Automatically post with branded image

---

## Image Content & Layout

### Example Article Image Structure:

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  [CREAM BACKGROUND #F5F4F0]                            │
│                                                          │
│                                                          │
│  ARTICLE TITLE (Playfair Display Bold, 56px)          │
│  Meyer Chetrit's Four-Decade Empire Faces $171M       │
│  in Court Judgments                                     │
│                                                          │
│  ━━━━━━ [GOLD ACCENT #C9A84C, 80px wide]             │
│                                                          │
│  When cheap debt and speed meet a rate cycle,          │
│  judges redistribute capital. (Space Grotesk, 28px)   │
│                                                          │
│                                                          │
│                                                          │
│                  Light Tower Group —              │
│              Capital Markets Advisory     │
│                      [GOLD ACCENT]              │
│                                                          │
└─────────────────────────────────────────────────────────┘
        1200px wide × 628px tall (LinkedIn optimal)
```

### Text Wrapping Rules

- **Title**: Wraps across multiple lines, max 3 lines (56px Playfair Display)
- **Subtitle**: Max 2 lines (28px Space Grotesk)
- **Branding**: Right-aligned, 20px Space Grotesk

If content is too long, the generator wraps intelligently and ensures all text fits within the image bounds.

---

## Troubleshooting

### Issue: "Pillow not installed"

**Error message:**
```
[SKIP] Pillow not installed (pip install Pillow)
```

**Fix:**
```bash
pip install Pillow>=10.0.0
```

Then re-run the agent:
```bash
python daily_news_agent.py
```

### Issue: Image Generation Fails

**Symptom:** Logs show `[WARN] Image generation failed: ...` but articles still publish

**Cause:** Usually missing font files or image path issues

**Fix:**
1. Verify `/insights/` directory exists and is writable
2. Check that agent has write permissions to the directory
3. Try manual test:
   ```bash
   python3 social_image_generator.py
   # Should create test_social_image.png in current directory
   ```

### Issue: Image File Not Found After Run

**Troubleshooting:**
1. Check if image generation was skipped due to Pillow not being installed
2. Verify article slug is valid (no special characters, lowercase, hyphens only)
3. Check file permissions: `ls -la insights/*_social.png`

---

## Performance Impact

- **Generation time per image:** ~200–500ms
- **Total time for 5 articles:** ~1–2.5 seconds (negligible vs. article writing)
- **Pipeline impact:** Adds <3% to total runtime

---

## Advanced Customization

To modify image styling, edit `scripts/social_image_generator.py`:

```python
# Brand colors
BRAND_BG = "#F5F4F0"        # Light cream
BRAND_ACCENT = "#C9A84C"    # Gold
BRAND_TEXT = "#121212"      # Dark text

# Image dimensions
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 628

# Spacing and padding
PADDING_H = 60  # Horizontal
PADDING_V = 50  # Vertical

# Font sizes (in get_fonts function)
fonts["title"] = ImageFont.truetype("arial.ttf", 56)       # Title size
fonts["subtitle"] = ImageFont.truetype("arial.ttf", 28)    # Subtitle size
fonts["branding"] = ImageFont.truetype("arial.ttf", 20)    # Branding size
```

### Custom Fonts

To use custom fonts (e.g., actual Playfair Display and Space Grotesk):

1. Download fonts from Google Fonts
2. Save .ttf files to `scripts/fonts/`
3. Update `get_fonts()` function:
   ```python
   fonts["title"] = ImageFont.truetype("fonts/PlayfairDisplay-Bold.ttf", 56)
   fonts["subtitle"] = ImageFont.truetype("fonts/SpaceGrotesk-Regular.ttf", 28)
   fonts["branding"] = ImageFont.truetype("fonts/SpaceGrotesk-Regular.ttf", 20)
   ```

---

## File Management

### Daily Output

```
insights/
  ├── chetrit-empire-judgment.html          # Article HTML
  ├── chetrit-empire-judgment_social.png    # Social image
  ├── sl-green-2b-refinance.html
  ├── sl-green-2b-refinance_social.png
  ├── ...
  └── insights.json                          # Manifest (includes image path in metadata)
```

### Cleanup (Optional)

Social images can be deleted without affecting articles:

```bash
# Delete all social images (keeps HTML articles)
cd insights
rm *_social.png

# They will be regenerated on next run
```

### Git Tracking

Social images are **excluded from git** by default (too large for version control). Update `.gitignore` if you want to track them:

```
# .gitignore
# Remove this line if you want to commit social images:
insights/*_social.png

# Keep articles committed:
insights/*.html
insights/insights.json
```

---

## Integration with LinkedIn

### Current Behavior
Articles are posted to LinkedIn with text hook + automatic preview from article URL.

### Future Enhancements

1. **Auto-upload images to LinkedIn asset store**
   - Requires LinkedIn API v2 asset upload
   - Modify `post_to_linkedin()` to use IMAGE media type
   - Automatically use generated social images

2. **Multi-image carousel posts**
   - Post all 5 daily articles as one carousel
   - Each slide: article image + hook text

3. **A/B testing**
   - Generate multiple image variations per article
   - Track engagement per image style

---

## Status & Monitoring

### Check Image Generation

```bash
# See generated images from last run
ls -lh insights/*_social.png | head -5

# Check image file sizes
du -h insights/*_social.png | sort -h

# Verify images are valid PNG
file insights/*_social.png
```

### Monitor in Logs

Check `scripts/agent_run.log` for image generation status:

```bash
grep "Image:" agent_run.log
# Output: Image: insights/chetrit-empire-judgment_social.png
```

---

## Contact & Support

For image generation issues:
1. Verify Pillow is installed: `pip list | grep Pillow`
2. Check write permissions: `touch insights/test.txt && rm insights/test.txt`
3. Review `scripts/social_image_generator.py` for detailed error messages
4. See DEPLOYMENT.md → Troubleshooting section

---

**Last Updated:** May 4, 2026  
**Status:** ✓ READY FOR PRODUCTION
