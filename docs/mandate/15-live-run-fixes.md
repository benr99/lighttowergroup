# Pipeline Live Run Fixes — Comprehensive Prompt

Today's live run revealed critical issues. Fix EVERY one.

## ISSUES FOUND

### 1. Source Feed URLs Unverified (CRITICAL)
120+ of 159 sources are marked `verified: false`. Their RSS URLs are domain-name estimates that may not work. Only 7 sources returned items. PE, Energy, Banking, and Fed/Macro sectors had ZERO stories. Fix: test every unverified feed URL, find working RSS endpoints, update config/sources.json.

### 2. Source-Sector Mapping Too Narrow (CRITICAL)
56% of real-world stories needed LLM classification (vs 6% in tests). Real feed names like "Gothamist", "The City NYC", "6sqft" don't match the exact names in `_SOURCE_SECTOR_PRIORS`. Fix: expand mapping with fuzzy matching, add all real feed names, normalize source names before lookup.

### 3. Only 3 of 7 Sectors Produced Stories
CRE had 58 items, data centers had 2, local government had 1. PE, Energy, Banking, Fed/Macro had zero. Fix: activate verified feeds for missing sectors.

### 4. Editorial Scorer Thresholds May Be Too Strict
The one generated article scored 7.5/10 but was marked "not publishable" because incentive_analysis and reader_utility were below minimum (both at 5, minimum 6). For a Tier 3 story from a single source, these minimums may be too aggressive. Fix: calibrate thresholds based on article depth and evidence availability.

### 5. Ingestion Performance
Only 10 of 30 verified sources were fetched. The full 159-source fetch timed out. Fix: add per-feed timeout, skip feeds that have been empty for 3+ consecutive runs, limit total fetch time to 5 minutes.

### 6. LLM Classification Rate Too High
56% needing LLM classification means ~34 expensive calls per run. Fix: expand regex patterns and source mappings so more stories classify deterministically.

## INSTRUCTIONS

Read and fix every file that needs changes. For each fix, compile-check and test.

### Fix 1: config/sources.json — verify feed URLs
- Read the current config/sources.json
- For every feed marked `verified: false`, try the URL. If it returns a valid RSS feed, mark as `verified: true`. If it returns HTML (not RSS), try common RSS path variants (/feed/, /rss/, /news/feed/). If nothing works, mark as `active: false` with a note.
- For feeds we can't test locally (network restrictions), leave as `verified: false` but add a `tested_note` field with what we know.
- Prioritize feeds for the 4 missing sectors: PE, Energy, Banking, Fed/Macro.

### Fix 2: scripts/classification.py — expand source mapping
- Add fuzzy matching: strip common suffixes ("News", "Blog", "Media"), lowercase compare, partial substring match
- Add ALL source names from config/sources.json that don't already have entries
- Add a `_normalize_source_name()` function that strips "The ", " Inc", " LLC", " News", etc.
- Make `classify_source_prior()` use the normalized name
- Target: reduce LLM classification rate from 56% to under 20%

### Fix 3: scripts/ingestion.py — performance optimization
- Add `FEED_TIMEOUT_SECONDS = 15` — skip any feed that takes longer
- Add `MAX_TOTAL_FETCH_SECONDS = 300` (5 min) — stop fetching after this limit
- Skip feeds that have been empty for 3+ consecutive runs (check source health)
- Add progress indicator: "Fetching feed X of Y..."
- Set `MAX_ENTRIES_PER_FEED = 200` (down from 500)

### Fix 4: scripts/editorial_scorer.py — tier-aware thresholds
- Brief articles (400-700 words, tier 4): reduce minimums by 1 across all dimensions
- Single-source articles: reduce factual_accuracy minimum from 7 to 6
- Add article depth as a parameter to `score()`: score(article, brief, depth="standard")
- Only enforce strict minimums on flagship/standard depth. Brief gets relaxed thresholds.

### Fix 5: tests/todays_run.py — improve the daily run script
- Fetch from ALL verified sources, not just first 10
- Add timing output for each phase
- Save results to .editorial-state/todays-run.json
- If API key is set, generate articles for ALL stories above threshold, not just top 1 per sector
- Print summary at end: total articles generated, sectors covered, cost estimate

### Fix 6: Run the pipeline again after all fixes
```
uv run python tests/todays_run.py
```

Target: >100 items ingested, >4 sectors covered, >5 articles generated, classification <20% LLM.

## VERIFICATION
After ALL fixes:
- python -m py_compile for every modified file
- Run the pipeline
- Report: items ingested, sectors covered, classification LLM rate, articles generated, cost estimate