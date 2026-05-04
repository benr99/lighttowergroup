# Daily Monitoring Checklist — Light Tower Group News Agent

## Quick Status Check (5 minutes)

**Time:** Check each morning after 7:15 AM

### ✓ Run Completed Successfully?

```bash
# Check last run status
cat scripts/agent_log.json | jq '.[-1] | {timestamp, status, articles_count}'
```

**Expected output:**
```json
{
  "timestamp": "2026-05-03T07:15:23Z",
  "status": "success",
  "articles_count": 5
}
```

✓ **If successful:** Skip to "Article Quality Check"  
✗ **If error:** See "Troubleshooting" section below

---

## Article Quality Check (3 minutes)

### Step 1: Verify Article Count

```bash
# Count new articles from today
ls -lt insights/*.html | head -5
```

**Expected:** 5 new `.html` files with today's date timestamp

### Step 2: Open insights.html in Browser

1. Go to: `file:///C:/Users/Ben/Downloads/Lighttowergroupsite/insights.html`
2. **Verify:**
   - ✓ Top 5 articles show today's date
   - ✓ No articles display "Invalid Date" or "undefined min read"
   - ✓ "Read time" shows 7–15 min (not blank or "undefined")
   - ✓ Each article has category tag (Capital Markets, Debt & Equity, etc.)
   - ✓ Links to full articles are clickable

### Step 3: Check RSS Feed

```bash
# Verify feed.xml is valid XML
python3 -c "import xml.etree.ElementTree as ET; ET.parse('feed.xml'); print('✓ Feed is valid XML')"

# Check latest entries
head -100 feed.xml | grep -A2 "<item>"
```

**Expected:**
- ✓ 5 newest `<item>` entries have today's publication date
- ✓ No entries show "2026-05-03T00:00:00.123456Z" (no microseconds)
- ✓ Feed validates as proper RSS 2.0

### Step 4: Spot-Check Article Quality

**Open one full article:** `insights/[latest-slug].html`

**Read through and verify:**
- ✓ Title is specific, under 90 chars (not vague like "Major Deal in Manhattan")
- ✓ Opening paragraph has vivid detail: named person, company, dollar amount, date
- ✓ Article is 750–950 words
- ✓ Paragraphs are 2–4 sentences max (not dense blocks)
- ✓ No banned phrases: "going forward", "in recent years", "stakeholders", "paradigm", "ecosystem"
- ✓ Numbers are always named: "$2.1B CMBS funding" not "significant capital deployment"
- ✓ Attribution is forensic: "per ACRIS records", "court filings allege", "Trepp data shows"
- ✓ Final paragraph circles back to opening with forward-looking insight

---

## LinkedIn Posting Check (2 minutes)

1. Go to: https://www.linkedin.com/company/light-tower-group/posts/
2. **Verify:**
   - ✓ Most recent post is from today
   - ✓ Post includes top-ranked article title + link
   - ✓ Post has punchy hook with specific detail (e.g., "$132M judgment", company name)
   - ✓ 4 separate lines (LinkedIn formats line breaks nicely)
   - ✓ Engagement starting: reactions, comments visible

**If no post:** Check Phase 7 errors in `agent_run.log`

---

## Troubleshooting

### Issue: `"status": "error"` in agent_log.json

**Check the full error:**
```bash
tail -50 scripts/agent_run.log
```

**Common errors & fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `[ERROR] DEEPSEEK_API_KEY not found` | Key not in .env | Verify `.env` has key, restart Task Scheduler |
| `[ERROR] 401 Unauthorized` | API key invalid/expired | Regenerate DeepSeek API key, update `.env` |
| `[ERROR] 429 Too Many Requests` | Rate limit exceeded | Wait 1 hour, retry manually |
| `[ERROR] Network timeout` | API unreachable | Check internet, DeepSeek status page |
| `[ERROR] No JSON found in response` | DeepSeek response malformed | Likely prompt too long; check `SYSTEM_PROMPT_ENHANCED` |

### Issue: Articles show "Invalid Date" in Browser

**Cause:** Date format issue (legacy vs new format mismatch)

**Fix:**
```bash
# Check insights.json date format
grep '"date"' insights.json | head -3

# Should show: "date": "2026-05-03" (ISO format, not "May 3, 2026")
# If showing "May 3, 2026", the browser formatDate() function is failing
```

**If dates are wrong:** Run `--dry-run` test first, check enhanced_prompts.py imports

### Issue: Task Scheduled but Not Running

**Verify task:**
```powershell
Get-ScheduledTask -TaskName "LTG Daily News Agent" | Select-Object TaskName, State
```

**If State = "Ready" but not running at 7 AM:**
1. Check Windows Task Scheduler (Win+R → `taskschd.msc`)
2. Right-click task → "Run" to test
3. Check `agent_run.log` for output

**If task is missing:** Re-run setup:
```powershell
# Requires Administrator
& "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts\setup_scheduler.ps1"
```

### Issue: Only 1–3 Articles Instead of 5

**Check agent_log.json:**
```bash
jq '.[-1].articles | length' scripts/agent_log.json
```

**Causes:**
- `"error_reason": "already_published"` — Top candidates were recently published
- Feed quality low — Fewer than 20 qualified candidates after triage
- DeepSeek timeout — Tried to generate 5 but one failed; continues with remainder

**Fix:** Use `--force` flag to skip duplicate detection:
```bash
cd scripts && python daily_news_agent.py --force
```

---

## Weekly Review (Friday, 5 PM)

### Metrics Over Last 5 Days

```bash
jq '.[] | select(.timestamp >= "2026-04-29") | {timestamp, status, articles_count, elapsed_seconds}' scripts/agent_log.json
```

**Look for:**
- ✓ All 5 runs succeeded (no errors)
- ✓ Consistent article count (5 per day)
- ✓ Elapsed time stable (250–370 seconds typical)

### Article Performance

1. **Click** into 2–3 random articles
2. **Skim** for quality issues:
   - Sentences too long (max 4 per paragraph)
   - Jargon without explanation (CMBS, DSCR, cap rates all assumed known — OK)
   - Rehashed press release (should feel like original reporting)
3. **Note** any consistent patterns to mention in next refinement

---

## Manual Run Procedure

### Dry Run (No Publishing)

```bash
cd C:\Users\Ben\Downloads\Lighttowergroupsite\scripts
python daily_news_agent.py --dry-run
```

**Output:** Generates articles in memory, shows scores & editorial samples, does NOT publish

### Force Publish (Skip Duplicates)

```bash
cd C:\Users\Ben\Downloads\Lighttowergroupsite\scripts
python daily_news_agent.py --force
```

**Use:** When manually re-running same story or testing with same feeds

### Full Production Run

```bash
cd C:\Users\Ben\Downloads\Lighttowergroupsite\scripts
python daily_news_agent.py
```

**Flow:**
1. Gathers 80+ stories
2. Triages to 20–30
3. Scores with DeepSeek
4. Enriches top 5
5. Generates 5 articles
6. Publishes to git + Netlify
7. Posts to LinkedIn
8. Logs metrics

**After run:** Monitor `insights.html` and agent_log.json (3–4 minutes for full run)

---

## Alert Conditions

**Email/Notify if:**

| Condition | Action |
|-----------|--------|
| No run in `agent_log.json` after 8 AM | Check Task Scheduler, manually run `run_agent.bat` |
| `"status": "error"` | Check `agent_run.log`, fix issue, re-run `--dry-run` |
| Articles with "Invalid Date" | Force re-run with current date, rebuild `insights.html` |
| Fewer than 3 articles published | Expected occasionally (duplicate detection); check if OK |
| LinkedIn post missing | Verify LINKEDIN_ACCESS_TOKEN in .env, check Phase 7 in logs |
| Feed.xml malformed | Check `insights.json` date format, rebuild feed |

---

## Monthly Refinement

1. **Scoring weights:** Are top 5 articles truly the most significant? Adjust `score_stories()` criteria if needed
2. **Prompt quality:** Review 10 random articles from last month. Any patterns (e.g., too wordy, missing data)?
3. **RSS feeds:** Check `news_sources.py` — add/remove feeds based on relevance
4. **Performance:** If elapsed time >400s, profile slow phases (usually WRITE phase)

---

**Last Updated:** May 3, 2026  
**Next Review:** May 10, 2026  
**Status:** ✓ LIVE & MONITORED
