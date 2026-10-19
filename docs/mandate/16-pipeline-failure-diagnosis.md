# Daily Pipeline Failure — Comprehensive Diagnosis & Fix

## WHAT HAPPENED

The Curated Insights edition workflow at `.github/workflows/daily-insights-agent.yml` is triggered by cron at 11:07 UTC (7:07 AM EDT). It runs `python scripts/resolve_schedule_policy.py` to determine whether to proceed, then validates the codebase (`py_compile` + `unittest discover` + `validate_publication.py` + node checks), then builds the edition.

The pipeline did NOT produce articles today. The most likely cause: **the baseline validation step failed** because our test files (`test_editorial_pipeline.py`, `test_pass5_audit.py`) used `sys.exit(0)` which unittest treats as an error, and `test_agent_runtime.py` / `test_article_pdf_generator.py` failed from missing pip packages. These were fixed AFTER the cron fired this morning but the cron ran with the old code.

## SECONDARY CONCERN

Even if validation passes, there may be additional issues in the CI environment that prevent the pipeline from completing. We must verify every step works end-to-end.

## AUDIT CHECKLIST — Execute every item

### 1. Verify schedule policy resolves correctly
- Read `scripts/resolve_schedule_policy.py`
- Simulate the cron trigger: `python scripts/resolve_schedule_policy.py --event-name schedule --trigger-cron "7 11 * * *"`
- Confirm it outputs `skip=false` and `mode=publish`
- If not, fix the policy

### 2. Verify baseline validation passes on CI
Read `.github/workflows/daily-insights-agent.yml` lines 72-82. The baseline validation runs:
```
python -m py_compile scripts/*.py
python -m unittest discover -s tests -v
python scripts/validate_publication.py
node --check site.js
node --check edition.js
node --check netlify/functions/newsletter-subscribe.js
node --check netlify/functions/editorial-feedback.js
node --test tests/netlify-functions.test.js
```
- Run `python -m py_compile scripts/*.py` — MUST pass for ALL files
- Run `python -m unittest discover -s tests -v` — MUST show "OK" (any failures = pipeline stops)
- Run `python scripts/validate_publication.py` — MUST print "Publication artifacts validated"
- Run `node --check site.js` — MUST pass
- Run `node --test tests/netlify-functions.test.js` — MUST pass
- If anything fails, fix it

### 3. Verify the pipeline imports work in CI
The Build step (line 90-113) runs `python daily_news_agent.py --selection-mode edition --articles 5 --daily-target 3 --pipeline-v2 --skip-git --run-origin github-actions`.
- Check that `daily_news_agent.py` can be imported without errors (it imports feedparser which is installed via pip)
- Check that `pipeline_v2.py` can be imported (it imports ingestion.py which imports feedparser)
- Simulate a shadow run: `python daily_news_agent.py --selection-mode edition --articles 3 --daily-target 1 --pipeline-v2 --shadow --skip-git --run-origin github-actions`
- This MUST complete without crashing

### 4. Check for any remaining sys.exit() calls in our test files
- Search ALL files in tests/ for `sys.exit(`
- Remove any remaining calls — they break unittest discover
- Already fixed: test_editorial_pipeline.py, test_pass5_audit.py
- Check if test_comprehensive.py, test_phase2_3_integration.py, test_generation.py, test_phase1_smoke.py have sys.exit()

### 5. Check the quality.yml workflow for the same test issues
- Read `.github/workflows/quality.yml`
- The quality workflow runs the same unittest discover step
- Verify it uses the same test skip logic (already fixed for agent_runtime and article_pdf_generator)
- Check if quality.yml also fails on node --check for track-read.js (our new Netlify function) — the node --check command lists specific files but doesn't include track-read.js. This is NOT a problem since it only checks listed files.

### 6. Verify validate_publication.py handles our new article format
- Our CVC PE article has category "Private Equity" — a new category
- Read `scripts/validate_publication.py`
- Check if it validates category names against a hardcoded list that would reject "Private Equity"
- If so, fix by adding the new categories or making the validation permissive

### 7. Check for config file issues in CI
- `config/sources.json` was modified heavily — verify it's valid JSON
- `config/sectors.json`, `config/scoring_profiles.json`, `config/watchlists.json`, `config/thresholds.json` — verify all valid
- Any module that loads these files at import time could crash the pipeline

### 8. Fix the schedule policy to be more robust
- Currently, `resolve_schedule_policy.py` line 59: `"skip": "false" if local_time == "07:07" else "true"` 
- This is a STRICT equality check. If the cron fires even 1 minute late and the local time rounds differently, it skips.
- Consider: what if the cron fires at 7:08 due to GitHub Actions queue delay? The local_time would be "07:08" and the run would be skipped.
- Fix: change to allow a window (e.g., 07:05-07:15) instead of exact 07:07 match.

### 9. Test the full pipeline end-to-end
After all fixes, simulate the exact CI flow:
1. Resolve schedule policy
2. Install pip deps (if needed)
3. Run baseline validation
4. Run `python daily_news_agent.py --selection-mode edition --articles 3 --daily-target 1 --pipeline-v2 --shadow --skip-git --run-origin github-actions`
5. Verify: no crashes, no import errors, pipeline completes with status report

### 10. Commit and push all fixes
After every fix is verified, commit with a clear message and push to main.

## VERIFICATION
- `python -m py_compile scripts/*.py` — all 70+ files clean
- `python -m unittest discover -s tests -v` — OK with 0 failures
- `python scripts/validate_publication.py` — artifacts validated
- Shadow pipeline run completes without errors
- Schedule policy window widened to prevent false skips
