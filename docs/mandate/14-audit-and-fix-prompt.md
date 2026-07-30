# Multi-Sector Pipeline — Comprehensive Audit & Fix Prompt

You are auditing a newly built multi-sector news intelligence pipeline for Light Tower Group. The system was built over 5 phases and consists of 9 new Python modules, 5 config files, and several modified existing files. Your job is to find EVERY bug, integration gap, logic error, edge case, performance issue, and inconsistency — then fix all of them.

## What Was Built

### New Python Modules (all in scripts/)
- `canonical_item.py` — Typed dataclass for all news items (~200 lines)
- `classification.py` — Multi-label sector classifier using source priors + regex signals (~261 lines)
- `scoring_engine.py` — 10-dimension deterministic scoring with 7 sector weight profiles (~380 lines)
- `ingestion.py` — Config-driven RSS feed fetcher, ThreadPoolExecutor, source health (~286 lines)
- `ranking.py` — Within-sector ranking, diversity controls, top-N selection, cross-sector dedup (~203 lines)
- `pipeline_v2.py` — Complete pipeline: ingest → classify → score → rank → report (~260 lines)
- `sector_prompts.py` — 6 sector-specific LLM writing prompts (~431 lines)
- `generation.py` — Sector-aware article routing and context building (~438 lines)

### Config Files (all in config/)
- `sources.json` — 159 feeds across 7 sectors
- `sectors.json` — Taxonomy: sectors, subsectors, event types
- `scoring_profiles.json` — 10 dimensions × 7 sector weight profiles
- `watchlists.json` — 95 tracked entities in 3 tiers
- `thresholds.json` — Article targets, tier boundaries, cost limits

### Modified Files
- `insights.html` — 7-sector navigation tabs
- `scripts/daily_news_agent.py` — `--pipeline-v2` flag added
- `.github/workflows/daily-insights-agent.yml` — pipeline-v2 flag added

## Audit Instructions

Read EVERY file listed above completely. For each file, identify:

### Category 1: Import Errors and Missing Dependencies
- Does every import resolve? Are there circular imports?
- Do the existing files in the project have the functions/classes that the new modules try to import?
- Are there imports of modules that don't exist yet?
- Does `classification.py` correctly import from `canonical_item`? Does `scoring_engine.py`? Does `ranking.py`?

### Category 2: Logic Bugs
- Does the scoring engine correctly extract financial values from text?
- Does the classification module correctly apply source priors before regex signals?
- Does the ranking module handle edge cases (empty sectors, all-rejected items, single-item sectors)?
- Are the diversity controls correctly enforcing percentage caps?
- Does the ingestion module correctly handle feedparser responses (bozo flag, empty feeds, missing fields)?
- Are there off-by-one errors in tier assignment thresholds?
- Does the generation module correctly route unknown sectors?

### Category 3: Data Flow and Integration
- Does pipeline_v2.py correctly chain together ingestion → classification → scoring → ranking?
- Are the CanonicalItem fields properly populated at each stage?
- Does the scoring engine read from the correct item fields (e.g., does it use item.raw_summary or item.raw_text)?
- Are CompositeScore and Tier being set correctly by the scoring engine?
- Does the ranking module correctly read the tier field from scored items?

### Category 4: Config File Consistency
- Do the sector names in sources.json match the sector keys in sectors.json, scoring_profiles.json, and thresholds.json?
- Are there config values referenced in code that don't exist in the config files?
- Are there config values in the files that are never read by any code?
- Do the watchlist entity names overlap with the source-sector mapping names?

### Category 5: Edge Cases and Error Handling
- What happens when classification receives an item with empty headline and summary?
- What happens when scoring receives an item with no primary_sector set?
- What happens when ranking receives zero items for a sector?
- What happens when ingestion encounters a feed that returns a 500 error?
- What happens when pipeline_v2 receives zero ingested items?
- Are there any potential division-by-zero errors?
- Are there any potential NoneType errors from dict.get() calls?

### Category 6: Performance Issues
- Does the scoring engine load config files from disk on every call to score_item()?
- Does the classification module recompile regex patterns on every call?
- Are there any O(n²) operations that could be O(n)?
- Is the ingestion ThreadPoolExecutor properly bounded?

### Category 7: Security Issues
- Are any API keys or secrets exposed in config files?
- Is user-supplied text (RSS feed content) properly sanitized before use?
- Are there any eval() or exec() calls?

### Category 8: Cross-Module Inconsistencies
- Do the field names in CanonicalItem match what classification.py writes and scoring_engine.py reads?
- Does pipeline_v2.py use the same function signatures that the modules export?
- Are there duplicate function names across modules that could cause import shadowing?
- Do the config file structures match what the code expects?

## Fix Instructions

For EVERY bug found:
1. Identify the file and exact line number
2. Explain what's wrong and why it matters
3. Apply the fix using the Edit tool
4. Verify with `python -m py_compile <file>`

After all fixes are applied, run the full integration test:
```
python tests/test_phase2_3_integration.py
python tests/test_generation.py
```

Everything must pass with zero errors.

## Priority
Focus on Category 1-3 issues first (imports, logic, data flow) as these break the pipeline. Then Category 4-5 (config, edge cases). Then Category 6-8.

Return a complete audit report listing every bug found and every fix applied, organized by category.
