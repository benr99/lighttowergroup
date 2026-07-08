# Automatic PDF Carousel Integration
## Seamless: Article → Carousel PDF (No Manual Steps)

**Status:** Ready to integrate  
**Flow:** Article generated → Carousel automatically created → LinkedIn button ready

---

## How It Works

When an article is published to `insights.json`:

```
enhanced_prompts.py generates article
           ↓
insights.json is updated with new article
           ↓
auto_carousel_generator.py runs automatically
           ↓
Carousel content generated (Ben Rohr voice)
           ↓
PDF created: insights/{slug}_carousel.pdf
           ↓
LinkedIn share button is ready to go
           ↓
No manual steps needed
```

---

## Integration Points

### Option 1: Hook Into daily_news_agent.py (Recommended)

Your `daily_news_agent.py` likely calls article generation. Add this after article generation:

```python
# In daily_news_agent.py, after articles are generated:

import subprocess
import sys

# After article generation loop
for article_slug in new_article_slugs:
    # Generate carousel PDF automatically
    result = subprocess.run(
        [sys.executable, "scripts/auto_carousel_generator.py", "--slug", article_slug],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"✓ Carousel PDF created for {article_slug}")
    else:
        print(f"✗ Carousel PDF failed for {article_slug}: {result.stderr}")
```

### Option 2: Hook Into enhanced_prompts.py (Alternative)

After the article is written to JSON:

```python
# In enhanced_prompts.py, at the end of article generation:

from pathlib import Path
import subprocess
import sys

# After saving article to insights.json
article_slug = article.get("slug")

subprocess.run(
    [sys.executable, str(Path(__file__).parent / "auto_carousel_generator.py"), "--slug", article_slug],
    capture_output=True,
)
```

### Option 3: Standalone Batch Job

Run after all daily articles are generated:

```bash
# After your daily article generation completes
python scripts/auto_carousel_generator.py --slug tuscan-village-mixed-use-capital
python scripts/auto_carousel_generator.py --slug bryant-park-grill-eviction-lease-value
# ... etc for each new article
```

---

## File Structure After Integration

```
insights/
  ├── tuscan-village-mixed-use-capital.html         [Article HTML]
  ├── tuscan-village-mixed-use-capital_carousel.pdf [PDF Carousel] ← NEW
  ├── bryant-park-grill-eviction-lease-value.html
  ├── bryant-park-grill-eviction-lease-value_carousel.pdf ← NEW
  └── ... (all articles now have matching carousels)

insights.json                                        [Updated with new articles]

scripts/
  ├── enhanced_prompts.py                           [Article generation]
  ├── auto_carousel_generator.py                    [NEW] Carousel generation
  ├── carousel_content_writer.py                    [Content in Ben's voice]
  ├── pdf_carousel_generator.py                     [PDF creation]
  └── linkedin_pdf_post.py                          [LinkedIn publishing]
```

---

## What Happens Automatically

### Step 1: Article is Generated
```
Article added to insights.json with metadata:
- slug
- title
- category
- body_html
- etc.
```

### Step 2: Carousel Content Created
- Reads article text
- Generates 8-10 slides in Ben Rohr warm, teaching voice
- Each slide formatted for PDF presentation
- Output: JSON with slide structure

### Step 3: PDF Generated
- Carousel content → beautiful PDF
- 1080×1350px portrait (mobile optimized)
- Light Tower brand colors and fonts
- Ben's headshot in identity cluster
- Professional, institutional appearance

### Step 4: PDF Saved
- Saved to: `insights/{slug}_carousel.pdf`
- Immediately accessible via LinkedIn share button
- No additional processing needed

---

## For LinkedIn Share Button

The carousel PDF is now automatically available at:

```
/insights/{slug}_carousel.pdf
```

Your LinkedIn share button can link directly to this file. No manual uploads needed.

Example:
```html
<a href="/insights/tuscan-village-mixed-use-capital_carousel.pdf" class="linkedin-share-btn">
  Share on LinkedIn
</a>
```

---

## Testing Integration

### Test 1: Manual Test
```bash
python scripts/auto_carousel_generator.py --slug tuscan-village-mixed-use-capital
```

Expected output:
```
================================================================================
AUTO CAROUSEL GENERATOR
================================================================================

✓ Article found: Tuscan Village Leasing Shows Mixed-Use Capital...
Generating carousel content...
✓ Generated 9 slides
Generating PDF...
✓ PDF saved: tuscan-village-mixed-use-capital_carousel.pdf

✓ Carousel PDF ready for LinkedIn share button
================================================================================
```

### Test 2: Verify File Created
```bash
ls -lh insights/tuscan-village-mixed-use-capital_carousel.pdf
```

Should show the PDF file with a reasonable size (typically 500KB-2MB).

### Test 3: Verify PDF Content
- Open the PDF on your phone
- Verify readability
- Check slide progression
- Confirm brand aesthetic

---

## Environment Requirements

The script needs:
- ✅ `DEEPSEEK_API_KEY` set in `scripts/.env`
- ✅ Ben's headshot at `assets/ben-rohr-headshot.jpg`
- ✅ Article must exist in `insights.json`

If any are missing, the script will fail gracefully with clear error messages.

---

## Dry Run Mode (Safety)

To test without creating files:

```bash
python scripts/auto_carousel_generator.py --slug test-article --dry-run
```

This shows what would happen without actually creating the PDF.

---

## Integration Checklist

- [ ] Add `auto_carousel_generator.py` to scripts directory (already created)
- [ ] Add carousel generation to article generation workflow (daily_news_agent.py or similar)
- [ ] Add Ben's headshot to assets/ben-rohr-headshot.jpg
- [ ] Set DEEPSEEK_API_KEY in scripts/.env
- [ ] Test with one article manually
- [ ] Verify PDF appears in insights/ directory
- [ ] Verify LinkedIn button links work
- [ ] Deploy to production

---

## How the LinkedIn Button Works

When someone views an article on your website:

1. **Current state:** LinkedIn button exists (probably links to LinkedIn share flow)
2. **After integration:** LinkedIn button can optionally link to the carousel PDF

Options:
- **Option A:** Direct link to PDF in insights/ (simplest)
- **Option B:** LinkedIn document post (requires API, handled by linkedin_pdf_post.py)
- **Option C:** Both (PDF available locally + posted to LinkedIn)

---

## No More Manual Steps

After integration:

- ❌ No manual carousel generation
- ❌ No manual PDF creation
- ❌ No manual uploads
- ✅ Fully automatic when article publishes
- ✅ PDF ready immediately for LinkedIn share
- ✅ Consistent quality every time

---

## Performance

Each carousel generation:
- Content creation: ~5-10 seconds (API call to DeepSeek)
- PDF generation: ~2-3 seconds
- Total: ~10-15 seconds per article
- Safe to run for 10+ articles daily without delay

---

## Troubleshooting

### PDF not created?
- Check DEEPSEEK_API_KEY is set
- Check article slug exists in insights.json
- Run with manual command to see error messages

### PDF looks wrong?
- Check Ben's headshot is at assets/ben-rohr-headshot.jpg
- Verify PDF opens on your phone
- Check brand colors match site.css

### Want to regenerate?
```bash
# Remove old PDF
rm insights/{slug}_carousel.pdf

# Generate new one
python scripts/auto_carousel_generator.py --slug {slug}
```

---

## One-Line Summary

**After integration, every article automatically gets a beautiful, branded PDF carousel saved to `insights/{slug}_carousel.pdf` — ready for LinkedIn sharing with zero manual steps.**

🚀
