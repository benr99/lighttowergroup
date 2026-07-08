# 2026 Social Pipeline: Go-Live Checklist

**Ready to deploy the new system? Use this checklist.**

---

## Pre-Deployment (Do These First)

- [ ] Read `README_2026_IMPLEMENTATION.md` (5 min)
- [ ] Read `PIPELINE_TEST_RESULTS.md` to see example output (5 min)
- [ ] Verify DEEPSEEK_API_KEY is set in `.env`
- [ ] Run test: `python run_social_pipeline_2026.py --latest --dry-run` ✓ Works?

## Verify Article Generation Still Works

- [ ] Run old article generation (enhanced_prompts.py) on a test article
- [ ] Confirm 750-950 word article is generated
- [ ] Confirm article is saved to insights/ folder
- [ ] Confirm insights.json is updated
- [ ] ✅ **Article generation unchanged?** If yes, proceed.

## Test Complete Pipeline

- [ ] Run: `python run_social_pipeline_2026.py --slug tuscan-village-mixed-use-capital`
- [ ] Check output appears in `linkedin_thread_queue.json`
- [ ] Check output appears in `social_pipeline_output.json`
- [ ] Review thread posts (are they conversational? debate-ready?)
- [ ] Review carousel slides (are they punchy? scannable?)
- [ ] Review strategy recommendation (makes sense for this article?)

## Review Outputs

**Thread Quality Checks:**
- [ ] Posts are 150-250 characters (not dense)
- [ ] Tone is peer-to-peer ("Here's what I'm seeing...")
- [ ] No generic phrases ("game changer", "robust demand")
- [ ] Each post stands alone but builds narrative
- [ ] Final post has specific CTA/question

**Carousel Quality Checks:**
- [ ] Exactly 9 slides (not 8, not 10)
- [ ] Slide 1 (hero) has punchy, specific headline
- [ ] Slide 2 has data/figures
- [ ] Slides 3-8 have one clear idea each
- [ ] Slide 9 closes with specific question
- [ ] No generic headlines ("The Deal", "The Market")
- [ ] All text under 30 words/slide

**Strategy Quality Checks:**
- [ ] Primary format makes sense (carousel vs. thread)
- [ ] Rationale explains why
- [ ] Key hooks are specific (not generic)
- [ ] CTA recommendation is actionable

## Prepare First Publication

- [ ] Decide format: Carousel only? Thread only? Both?
- [ ] Download carousel schema from `social_pipeline_output.json`
- [ ] Open Canva / design tool
- [ ] Create 9-slide carousel matching schema
- [ ] Export as PDF (< 8MB)
- [ ] Write caption (use strategy recommendation or thread first post)
- [ ] Prepare first comment (link to article)

## Go Live

- [ ] Post carousel to LinkedIn
- [ ] Add caption
- [ ] Add first comment with article link
- [ ] Set reminder to monitor engagement (30 min, 1 hr, 3 hrs)

## Monitor First 24 Hours

- [ ] Carousel completion rate (screenshot at 4-6 hrs)
- [ ] Comment quality (deep technical? or generic?)
- [ ] Save rate (if available via LinkedIn Analytics)
- [ ] Share rate
- [ ] Time until first comment
- [ ] Document in spreadsheet

## Post Analysis (After 3-5 Posts)

- [ ] Compare metrics across posts
- [ ] Which format is winning? (Carousel vs. Thread)
- [ ] Which topics get best completion rate?
- [ ] Which hooks work best?
- [ ] Did any generate leads? (Track inquiries)
- [ ] Any feedback from audience? (Comments)

## Iterate (If Needed)

If performance is below target (70% completion, 6%+ engagement):
- [ ] Review thread posts — too institutional?
- [ ] Review carousel design — too text-heavy?
- [ ] Review strategy — wrong format chosen?
- [ ] Adjust prompts (I'll help)
- [ ] Re-test with 2-3 more articles
- [ ] Then assess if ready for production scaling

## Full Production (If Performance Meets Target)

- [ ] Add to daily workflow: `python run_social_pipeline_2026.py --latest`
- [ ] Set publishing cadence (e.g., 1-2 pieces per week)
- [ ] Establish content mix:
  - 60% Carousels
  - 25% Threads
  - 10% Polls
  - 5% Reports
- [ ] Track metrics continuously
- [ ] Monthly review of what's working

---

## Quick Reference

**Before you run anything:**
```bash
cd C:\Users\Ben\Downloads\Lighttowergroupsite\scripts
python run_social_pipeline_2026.py --latest --dry-run
```

**If output looks good:**
```bash
python run_social_pipeline_2026.py --latest
# Check outputs in linkedin_thread_queue.json and social_pipeline_output.json
```

**If you want to test specific article:**
```bash
python run_social_pipeline_2026.py --slug <article-slug-here>
```

---

## Success Criteria

✅ **You're ready for production if:**
- First carousel hits 70%+ completion rate
- Comments include technical CRE discussion (not just emojis)
- Thread posts generate debate
- 1+ lead attributed to social post within 30 days

❌ **Pause and iterate if:**
- Completion rate < 60%
- Comments are generic ("Great post!", emojis)
- No debate or technical discussion
- No leads after 20+ posts

---

## Rollback Plan (If Something's Wrong)

If you need to revert to old system:
1. Stop running `run_social_pipeline_2026.py`
2. Revert to using `linkedin_essay_agent.py` + old carousel
3. Article generation (`enhanced_prompts.py`) is untouched - keeps working
4. No data lost, no articles broken

**This is a low-risk deployment** because articles are untouched.

---

## Support

**Questions?** 
- Read `README_2026_IMPLEMENTATION.md` (comprehensive guide)
- Check `DEPLOYMENT_GUIDE_2026.md` (troubleshooting section)
- Review `PIPELINE_TEST_RESULTS.md` (real example output)

**Performance not as expected?**
- Share 2-3 carousel/thread outputs
- I'll review and refine prompts
- We iterate until it matches 2026 best practices

---

## Checklist Summary

**Pre-Deploy:**
- [ ] Tests pass
- [ ] Articles still generating correctly
- [ ] Understand outputs

**First Publication:**
- [ ] Design carousel in Canva
- [ ] Post to LinkedIn
- [ ] Monitor for 24 hours

**After 5 Posts:**
- [ ] Review metrics
- [ ] Iterate if needed OR go full production

**Full Production:**
- [ ] Add to daily workflow
- [ ] Track continuously
- [ ] Celebrate 3.4x engagement improvement 🚀

---

**You're ready. Let's go live.**
