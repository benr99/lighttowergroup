# Deployment Guide: Light Tower 2026 Social Pipeline
## Complete Implementation & Testing

---

## What You Just Got

**Four new Python scripts** that replace your LinkedIn output generation:

1. **`linkedin_thread_agent.py`** (NEW)
   - Converts articles to 5-8 punchy LinkedIn posts
   - Tweet-first mindset (one idea per post)
   - Conversational, peer-to-peer tone
   - Output: JSON with individual posts + thread structure

2. **`carousel_script_agent_2026.py`** (NEW/UPDATED)
   - Optimized for 2026 LinkedIn standards
   - 9-slide format, max 30 words/slide
   - Scannable, whitespace-heavy design
   - Output: 9-slide carousel schema ready for PDF

3. **`social_strategy_selector.py`** (NEW)
   - Analyzes each article
   - Recommends optimal format(s)
   - Decision logic: high data → carousel, high debate → thread
   - Output: Strategy recommendation + rationale

4. **`run_social_pipeline_2026.py`** (MASTER ORCHESTRATION)
   - Runs complete pipeline end-to-end
   - Takes article → generates strategy → thread → carousel
   - Single command: `python run_social_pipeline_2026.py --slug <article-slug>`
   - Output: Thread + Carousel + Strategy all in one

**Article generation (`enhanced_prompts.py`):** COMPLETELY UNTOUCHED ✓

---

## Installation (5 minutes)

### Step 1: Copy Files to Scripts Directory
The four files are already created:
```
scripts/linkedin_thread_agent.py
scripts/carousel_script_agent_2026.py
scripts/social_strategy_selector.py
scripts/run_social_pipeline_2026.py
```

### Step 2: Verify Dependencies
Make sure you have:
```bash
pip install requests beautifulsoup4
```

(These should already be installed if you're running the existing agents)

### Step 3: Test Environment Variables
Make sure your `.env` file has:
```
DEEPSEEK_API_KEY=sk-xxxxx
SITE_URL=https://lighttowergroup.co
```

### Step 4: Ready to Test
That's it. You're ready to run the pipeline.

---

## Quick Test (10 minutes)

### Test 1: Dry Run (No Saving)
```bash
cd scripts/
python run_social_pipeline_2026.py --slug tuscan-village-mixed-use-capital --dry-run
```

**What you'll see:**
- Strategy analysis (format recommendation)
- Thread posts being generated (5-8 posts)
- Carousel slides being generated (9 slides)
- JSON output showing what would be saved

### Test 2: Full Run (With Saving)
```bash
cd scripts/
python run_social_pipeline_2026.py --slug tuscan-village-mixed-use-capital
```

**What gets created:**
- `linkedin_thread_queue.json` - Thread posts saved here
- `social_pipeline_output.json` - Complete pipeline output (thread + carousel + strategy)

**Output files location:**
- Thread posts: `./linkedin_thread_queue.json` (top of queue)
- Full pipeline log: `./social_pipeline_output.json` (last 100 runs)

### Test 3: Latest Article
```bash
python run_social_pipeline_2026.py --latest
```

Runs on your newest article without specifying slug.

---

## What the Output Looks Like

### Thread Output (linkedin_thread_queue.json)
```json
{
  "thread_title": "Tuscan Village and the Return of Selective Capital",
  "posts": [
    {
      "post_number": 1,
      "post_text": "The most important number in Tuscan Village is not the leased sq ft.\n\nIt's the 170 acres and what that reveals about capital markets in 2026.",
      "format": "hook",
      "character_count": 145
    },
    {
      "post_number": 2,
      "post_text": "In this cycle, capital is selective. It's not asking 'Should we build?' It's asking 'Who gets financed to build?'\n\nTuscan Village got financed.",
      "format": "narrative",
      "character_count": 142
    },
    ...
  ],
  "thread_summary": "Market structure and capital selectivity.",
  "final_cta": "How is your lender underwriting development debt in this market?",
  "suitable_for_carousel": true,
  "format_recommendation": "carousel_primary"
}
```

### Carousel Output (social_pipeline_output.json - snippet)
```json
{
  "slides": [
    {
      "system": "hero",
      "eyebrow": "CAPITAL INTELLIGENCE",
      "headline": "Tuscan Village's Whole Foods Lease Shows Capital Is Betting on Demand Density",
      "subhead": "170 acres of mixed-use development in a Boston suburb just locked down major tenants. Here's what that reveals about where capital moves in 2026.",
      "figures": [
        {"number": "$170 acres", "label": "Total development scale"}
      ]
    },
    {
      "system": "data",
      "eyebrow": "THE FIGURES",
      "headline": "Four Major Tenants Just Committed",
      "figures": [
        {"number": "4", "label": "New tenants signed"},
        {"number": "170 acres", "label": "Total mixed-use scale"}
      ]
    },
    {
      "system": "story",
      "eyebrow": "STORY 01",
      "headline": "The Market Is Not Short of Capital. It's Short of Conviction.",
      "subhead": "Whole Foods, Free People, SWTHZ, Festa Studio. The brands matter less than what they signal: demand density."
    },
    ...
  ]
}
```

### Strategy Output (social_pipeline_output.json)
```json
{
  "primary_format": "carousel",
  "engagement_potential": "high",
  "lead_potential": "high",
  "rationale": "High data density with specific deal details and framework (demand density as underwriting standard). Carousel maximizes clarity and completion rate.",
  "key_hooks": [
    "170-acre scale reveals capital commitment requirement",
    "Demand density is now the underwriting prerequisite",
    "Sponsors without pre-leasing lose access to development debt"
  ]
}
```

---

## How to Use the Output

### Option 1: Publish Thread (5-8 Separate LinkedIn Posts)
```
1. Go to linkedin_thread_queue.json
2. Copy Post 1 (with professional photo/visual)
3. Reply with Post 2 (threaded)
4. Reply with Post 3, etc.
5. On Post 8: Include CTA + link to article

Timeline: Post over 2-3 hours for maximum reach
```

### Option 2: Publish Carousel (9-Slide PDF)
```
1. Take carousel schema from social_pipeline_output.json
2. Open Canva or design tool
3. Create 9 slides matching the schema
4. Export as PDF (under 8MB)
5. Upload to LinkedIn as carousel
6. Use caption from thread_package["first_comment"] or strategy recommendation

Timeline: Post immediately or schedule for optimal time
```

### Option 3: Both (Recommended)
```
1. Post carousel + caption (gets 6.60% engagement, high completion)
2. In first comment: Link to full article
3. Create follow-up thread 24 hours later (spark debate from carousel viewers)

Timeline:
- Day 1, 9am: Post carousel + caption
- Day 1, 6pm: Reply to top comments
- Day 2, 10am: Post debate thread (optional, if article has contrarian angle)
```

---

## Integration with Existing Workflow

### Current Flow (Before 2026 Update)
```
1. Run daily_news_agent.py → Gets CRE news
2. Run [your article generation] → Writes 750-word article
3. Run linkedin_essay_agent.py → Generates 2400+ char essay
4. Run carousel_script_agent.py → Generates carousel from essay
5. Manually post to LinkedIn
```

### New Flow (2026 Optimized)
```
1. Run daily_news_agent.py → Gets CRE news (SAME)
2. Run [your article generation] → Writes 750-word article (SAME, UNTOUCHED)
3. Run run_social_pipeline_2026.py → Generates strategy + thread + carousel (REPLACES 3-4)
4. Manually post thread or carousel to LinkedIn (SIMPLER)
```

**Result:** Fewer steps, better output, optimized for 2026 engagement.

---

## Adding to Daily Automation

### Option A: Manual (What to Do First)
```bash
# After you publish an article
cd scripts/
python run_social_pipeline_2026.py --slug <article-slug>

# Check output
cat ../social_pipeline_output.json | head -100

# Publish manually to LinkedIn
```

### Option B: Automated (Future)
Add to your daily script after article generation:
```bash
#!/bin/bash
# daily_workflow.sh

# Generate article (existing)
python daily_news_agent.py
ARTICLE_SLUG=$(cat insights.json | jq -r '.[0].slug')

# Generate thread + carousel (NEW)
python run_social_pipeline_2026.py --slug $ARTICLE_SLUG

# (Optional) Auto-upload carousel to LinkedIn via API
# (Optional) Post thread via scheduling tool
```

---

## Testing Checklist

Before going live, verify:

- [ ] Can run `python run_social_pipeline_2026.py --latest` without errors
- [ ] Thread posts look conversational (not institutional)
- [ ] Thread posts don't exceed ~280 characters each
- [ ] Carousel has exactly 9 slides
- [ ] Carousel headlines are specific (not generic)
- [ ] Carousel max 30 words per slide (check manually)
- [ ] Strategy recommendation makes sense for the article
- [ ] No article generation changed (enhanced_prompts.py still works)
- [ ] Output files created in correct locations

---

## Metrics to Track (After Publishing)

### For Thread Posts:
- Reply/engagement rate (target: 3%+)
- Comment quality (are sponsors asking technical questions?)
- Thread completion rate (did people read all 8 posts?)

### For Carousels:
- Completion rate (target: 70%+)
- Dwell time (target: 30-60 seconds)
- Saves (indicates reference value)
- Share rate (indicates team forwarding)

### Overall:
- Which format drives more engagement? (Thread vs. Carousel)
- Which generates leads? (Track from post to inquiry)
- Any pattern in hooks that work best?

**After 10-15 posts:** You'll have clear data on what works for YOUR audience.

---

## Troubleshooting

### Issue: "No JSON object found in response"
**Cause:** API returned non-JSON  
**Fix:** Check DEEPSEEK_API_KEY is valid, or run with `--dry-run` to see what's being generated

### Issue: "No insights.json entries found"
**Cause:** Missing insights.json file  
**Fix:** Make sure you're running from `scripts/` directory and insights.json is in parent

### Issue: Carousel has only 6 slides instead of 9
**Cause:** Article text is too short to generate full carousel  
**Fix:** Use `--no-api` flag to generate fallback (or try different article)

### Issue: Thread posts all say same thing
**Cause:** API response was low quality  
**Fix:** Increase `temperature` in prompt (currently 0.42) or check article text

### Issue: "DEEPSEEK_API_KEY not set"
**Cause:** Environment variable not loaded  
**Fix:** 
```bash
export DEEPSEEK_API_KEY=sk-xxxxx
python run_social_pipeline_2026.py --slug xxx
```

---

## Next Steps

1. **Run Test 1 (Dry Run)** — See output without saving
2. **Review Thread & Carousel Output** — Does it look right?
3. **Run Test 2 (Full Run)** — Save to queues
4. **Publish One Carousel or Thread** — See real engagement
5. **Track Metrics** — Completion rate, comments, leads
6. **Iterate** — Adjust prompts based on what works

---

## Files Reference

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| linkedin_thread_agent.py | Convert article to thread | Article text | 5-8 posts (JSON) |
| carousel_script_agent_2026.py | Convert to carousel | Article HTML | 9-slide schema (JSON) |
| social_strategy_selector.py | Recommend format | Article text | Strategy (JSON) |
| run_social_pipeline_2026.py | Orchestrate all 3 | Article slug | Thread + Carousel + Strategy |

| Output File | Location | Contents |
|-------------|----------|----------|
| linkedin_thread_queue.json | `./` | Thread posts (top of queue) |
| social_pipeline_output.json | `./` | Complete pipeline log (last 100) |

---

## Support

If you hit issues:
1. Check article has text/content (not just metadata)
2. Verify DEEPSEEK_API_KEY is valid
3. Run with `--dry-run --verbose` for detailed output
4. Check that `enhanced_prompts.py` still generates articles correctly (it should)

---

**Ready to test?**

```bash
cd scripts/
python run_social_pipeline_2026.py --latest --dry-run
```

Go. 🚀
