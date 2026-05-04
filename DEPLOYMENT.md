# Light Tower Group News Agent — Deployment Guide

## Production Status: ✓ LIVE

**Deployment Date:** May 3, 2026  
**Integration:** DeepSeek API (article ranking & generation)  
**Schedule:** Daily at 7:00 AM (Windows Task Scheduler)  
**Commit:** `9a6f77e` (main branch)

---

## Architecture Overview

### Daily Pipeline (8 Phases)

```
GATHER (Phase 1)
  └─ 88 RSS feeds + NewsAPI
     └─ 80+ raw stories/day

TRIAGE (Phase 2)
  └─ Filter: CRE-relevant, last 36h, deduplicate
     └─ 20-30 qualified candidates

SCORE (Phase 3)
  └─ DeepSeek ranks by: capital markets impact (30 pts),
     NYC relevance (25 pts), deal scale (20 pts),
     originality (15 pts), timeliness (10 pts)
     └─ Ranked 1-20

ENRICH (Phase 4)
  └─ Fetch full text (Trafilatura)
  └─ Extract NYC addresses
     └─ Top 5 enriched stories

WRITE (Phase 5)
  └─ DeepSeek generates 5 editorial pieces
  └─ System prompt: SYSTEM_PROMPT_ENHANCED (sophisticated CRE voice)
  └─ User template: USER_PROMPT_TEMPLATE (consistent structure)
  └─ Output: 750-950 words each, institutional-grade
     └─ JSON: title, subtitle, slug, category, meta_description,
       tags, body_html, sources, linkedin_hook, twitter_hook

PUBLISH (Phase 6)
  └─ Save 5 .html files to /insights/
  └─ Update insights.json manifest (5 new entries)
  └─ Rebuild feed.xml (RSS feed)
  └─ Rebuild sitemap.xml
  └─ Git commit + push to origin/main
     └─ Triggers Netlify build & deploy

LINKEDIN (Phase 7)
  └─ Post top-ranked article link + hook
     └─ 30,000-follower CRE capital markets audience

LOG (Phase 8)
  └─ Append run record to agent_log.json
     └─ Metrics: elapsed_seconds, articles_count, status, etc.
```

---

## Configuration

### API Keys (scripts/.env)

```
ANTHROPIC_API_KEY=sk-ant-api03-...         [unused, kept for reference]
DEEPSEEK_API_KEY=sk-5515636d3d0c4f5e...   [active — article ranking & writing]
NEWSAPI_KEY=f1e6e15b400f484c...            [story gathering]
LINKEDIN_ACCESS_TOKEN=AQXOl2jGsSXF2n...   [LinkedIn posting]
```

### DeepSeek Integration

| Component | Value |
|-----------|-------|
| **Endpoint** | `https://api.deepseek.com/v1/chat/completions` |
| **Model** | `deepseek-chat` |
| **Temperature** | 0.2 (focused, deterministic) |
| **Ranking** | max_tokens=3500, timeout=60s |
| **Writing** | max_tokens=4500, timeout=120s |
| **System Message** | SYSTEM_PROMPT_ENHANCED (250+ lines, sophisticated CRE editorial voice) |
| **User Template** | USER_PROMPT_TEMPLATE (explicit examples, format specs) |

### Scheduled Task

```
Task Name:    LTG Daily News Agent
Schedule:     Daily at 07:00 (7:00 AM)
Program:      C:\Users\Ben\Downloads\Lighttowergroupsite\scripts\run_agent.bat
Working Dir:  C:\Users\Ben\Downloads\Lighttowergroupsite\scripts
State:        Ready ✓
```

**To verify:**
```powershell
Get-ScheduledTask -TaskName "LTG Daily News Agent"
```

---

## Monitoring & Logs

### Run Metrics (agent_log.json)

After each run, check `scripts/agent_log.json`:

```json
{
  "timestamp": "2026-05-03T07:15:23Z",
  "elapsed_seconds": 187,
  "status": "success",
  "articles_count": 5,
  "articles": [
    { "title": "...", "slug": "...", "source": "..." },
    ...
  ],
  "top_story": { "title": "...", "source": "...", "score": 92 }
}
```

**Key Metrics:**
- `status`: `success`, `error`, or `already_published`
- `articles_count`: Number of articles generated (1-10)
- `elapsed_seconds`: Total pipeline duration
- `top_story`: Highest-ranked story details

### Raw Output Log (agent_run.log)

For debugging, check `scripts/agent_run.log`:

```
[1/8] PHASE 1: GATHER
  Fetching 88 RSS feeds + NewsAPI...
  Collected 87 stories in 12.5s

[2/8] PHASE 2: TRIAGE
  Filtering to CRE-relevant...
  Passed: 24 stories

[3/8] PHASE 3: SCORE
  Ranking with DeepSeek...
  Top 3: [92] ..., [87] ..., [83] ...

...
```

### Article Quality

After each run, check `insights.html`:
- Browse the published articles (5 most recent)
- Review date formatting (should be "May 3, 2026", not timestamps)
- Verify JSON structure (no "undefined min read" errors)
- Check RSS feed at `feed.xml` (proper publication dates)

---

## Maintenance

### Daily Checklist

1. **After 7:15 AM:** Check `agent_log.json` for `"status": "success"`
2. **By 8:00 AM:** Verify 5 new articles in `insights.html`
3. **Check dates:** Confirm no microseconds or timezone issues
4. **Review scores:** Top article should be 85+ (capital markets relevance)
5. **Monitor LinkedIn:** Post should appear on Light Tower Group profile

### Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| **API quota exceeded** | `[ERROR] DeepSeek API rate limit` | Wait 1 hour, retry manually |
| **Missing .env key** | `[ERROR] DEEPSEEK_API_KEY not found` | Verify `.env` file, reload Task Scheduler |
| **Network timeout** | `[WARN] Request timeout after 120s` | Check internet, increase timeout (if consistent) |
| **Duplicate detection** | `[WARN] Article already published` | Expected if same story appears twice in 36h |
| **RSS feed error** | `[ERROR] Feed XML generation failed` | Check feed.xml syntax (likely JSON→XML conversion issue) |

---

## Testing & Validation

### Manual Test Run

```bash
cd scripts
python daily_news_agent.py --dry-run
```

**Output:**
- `[dry-run]` tag in all logs
- Articles generated in memory only (no files saved)
- No git push or LinkedIn post
- Useful for: verifying API keys, checking article quality, debugging

### Force Publish (Skip Duplicate Check)

```bash
cd scripts
python daily_news_agent.py --force
```

**Use when:**
- Re-publishing a previous story manually
- Testing with the same feeds
- Overriding duplicate detection

### Full Production Run

```bash
cd scripts
python daily_news_agent.py
```

**Flow:**
1. Gather stories
2. Score & rank
3. Enrich top 5
4. Generate articles
5. Publish to git + Netlify
6. Post to LinkedIn
7. Log metrics

---

## Performance Targets

| Phase | Target | Typical |
|-------|--------|---------|
| GATHER | <20s | 12-18s |
| TRIAGE | <5s | 2-4s |
| SCORE (DeepSeek) | <60s | 45-58s |
| ENRICH | <10s | 5-8s |
| WRITE (5× articles) | <300s | 200-280s |
| PUBLISH | <30s | 15-25s |
| LINKEDIN | <10s | 3-7s |
| LOG | <5s | 1-2s |
| **TOTAL** | **<450s** | **280-370s** |

**Typical full run:** ~5–6 minutes

---

## Editorial Quality Standards

### Voice & Tone
- **Target:** WSJ "Heard on the Street" grade
- **Audience:** Institutional investors, lenders, REIT analysts, hedge fund managers
- **Tone:** Incisive, forensic, analytically sharp, never promotional

### Structure (3-Act)
1. **ACT I (Paras 1–2):** The Trigger — vivid, specific scene (named person, dollar amount, court decision)
2. **ACT II (Paras 3–8):** Evidence & Analysis — causal chains, 4 sentences max per paragraph
3. **ACT III (Paras 9–Final):** Reckoning & Implication — connect to systemic market forces, forward-looking kicker

### Content Requirements
- **Word count:** 750–950 words
- **Sentences per paragraph:** Max 4 (enforce split if cramped)
- **Numbers:** Always named (not "many", "several", "significant")
- **Attribution:** Forensic specific — "per ACRIS records", "court filings allege", "Trepp data shows"
- **Banned phrases:** "in recent years", "going forward", "stakeholders", "paradigm", "ecosystem"

### JSON Output Validation
- **title:** ≤90 chars, specific not vague
- **subtitle:** ≤140 chars, delivers "so what"
- **slug:** kebab-case, max 6 words, lowercase letters + hyphens
- **body_html:** Only `<p>` tags, no `<h1>`, `<strong>`, etc.
- **linkedin_hook:** 100–160 words, no hashtags, no emojis
- **twitter_hook:** ≤240 chars, sharp and specific

---

## Rollback Procedure

If something breaks:

```bash
# See recent commits
git log --oneline -10

# Revert to last known-good state
git revert HEAD
git push origin main

# Or rollback entirely
git reset --hard [commit-hash]
git push origin main --force
```

**After rollback:**
1. Fix the issue locally
2. Test with `--dry-run`
3. Commit & push to redeploy

---

## Next Enhancements

- [ ] A/B test scoring weights (capital markets impact vs. NYC relevance)
- [ ] Add backtesting: score last 30 days of stories, measure predictive accuracy
- [ ] Expand LinkedIn posting: include all 5 articles (not just top 1)
- [ ] Add article versioning: keep prior versions, show update history
- [ ] Implement dynamic prompts: adjust voice based on story category
- [ ] Add analytics: track read times, shares, engagement per article

---

## Support & Documentation

| Resource | Path |
|----------|------|
| **Agent Code** | `scripts/daily_news_agent.py` (1,300+ lines) |
| **Enhanced Prompts** | `scripts/enhanced_prompts.py` (250+ lines) |
| **RSS Sources** | `scripts/news_sources.py` (88 feeds, 5 tiers) |
| **Run Logs** | `scripts/agent_log.json` (metrics) |
| **Output Log** | `scripts/agent_run.log` (detailed) |
| **Published Articles** | `insights/` (HTML) + `insights.json` (manifest) |
| **Feeds** | `feed.xml` (RSS) + `sitemap.xml` (search) |

**Contact:** For issues or feature requests, check commit messages (git log) for decision rationale.

---

**Status:** Production-ready ✓ Deployed ✓ Scheduled ✓
