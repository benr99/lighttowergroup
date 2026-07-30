# 12 — Operational Documentation

Practical operational documentation for administrators of the Light Tower Group Insights Intelligence Engine. This document assumes the target multi-sector architecture is built and running in production.

---

## System Overview

The Insights engine runs as a GitHub Actions workflow triggered on a schedule (currently daily at 06:00 UTC). It fetches from 200+ RSS/Atom feeds across 7 sectors, classifies every story, scores and ranks candidates, generates articles using DeepSeek LLM, and publishes to Netlify. The admin dashboard at `insights-admin.html` provides visibility and manual controls.

**Key files and locations:**
- Configuration: `config/` — sources.json, scoring_profiles.json, sectors.json, watchlists.json, thresholds.json
- Scripts: `scripts/` — ingestion.py, classification.py, scoring_engine.py, ranking.py, generation.py, publishing.py, admin_dashboard.py
- Output: `insights/` — published articles organized by sector
- Logs: `logs/` — run logs, source health, cost reports
- Pipeline runner: `.github/workflows/insights-pipeline.yml`

**Key operational metrics (targets):**
- Articles per day: 210 (30 per sector × 7 sectors)
- Pipeline runtime: <2 hours (target), <6 hours (hard limit via GitHub Actions)
- Source failure rate: <35%
- Generation success rate: >95%
- Daily cost: <$3.00 USD
- Classification accuracy: >85%

---

## How to Add a Source

1. Open `config/sources.json`.
2. Add a new entry following the schema:

```json
{
  "id": "pe-hub-deals",
  "name": "PE Hub Deal News",
  "url": "https://www.pehub.com/feed",
  "sector": "private_equity",
  "sector_weight": 1.0,
  "tier": "tier_1",
  "fetch_frequency": "every_run",
  "auth_required": false,
  "active": true,
  "content_type": "rss",
  "language": "en",
  "needs_verification": true,
  "notes": "PE Hub deal announcements",
  "last_validated": null,
  "consecutive_failures": 0,
  "added_date": "2026-07-30"
}
```

3. Run validation:

```bash
python scripts/validate_sources.py --source pe-hub-deals
```

The validator checks:
- The URL is reachable (HTTP 200).
- The response is parseable as RSS/Atom.
- At least one entry is produced.
- The feed does not return a redirect to a paywall or login page.

4. If validation passes, set `"needs_verification": false` and `"last_validated": "<today's date>"`.
5. If validation fails, investigate the URL. Common issues: paywalled content, incorrect RSS endpoint, site uses Atom not RSS (try the Atom URL), site requires user-agent header.
6. The next pipeline run picks up the new source automatically. No restart required.
7. Monitor the source for the first 3 runs to confirm it's producing usable items.

**Adding a batch of sources:**
Create a JSON array file with the new entries, then run:

```bash
python scripts/validate_sources.py --batch new_sources_batch.json
```

The batch validator checks all sources and outputs a report of which passed and which failed.

**Disabling a source:**
Set `"active": false`. The source will be skipped on the next run. Do not delete the entry — preserve the source history.

---

## How to Change Scoring Weights

1. Open `config/scoring_profiles.json`.
2. Find the sector profile you want to adjust. For example, `"private_equity"`:

```json
"private_equity": {
  "weights": {
    "transaction_significance": 1.8,
    "market_movement": 0.9,
    "policy_impact": 0.7,
    "entity_prominence": 1.5,
    ...
  }
}
```

3. Adjust weight values. Each dimension has a multiplier from 0.0 to 2.0:
   - 0.0 = dimension is ignored for this sector.
   - 1.0 = dimension contributes at its raw value.
   - 2.0 = dimension is doubled in importance.
   - Values above 2.0 are clamped to 2.0.
   - Negative values are not allowed.

4. Example use case: During a period of heavy regulatory activity, increase `"policy_impact"` for the `"banking_credit"` sector from 1.4 to 1.8. This boosts stories about regulatory changes.

5. After editing, run validation:

```bash
python scripts/validate_config.py
```

The validator checks:
- All 10 dimensions are present for every sector.
- All weight values are in range [0.0, 2.0].
- No sector is missing.
- Article targets sum correctly.
- Subsector lists are non-empty.

6. Weights take effect on the next pipeline run. No restart required.

7. **Important:** After changing weights, run the pipeline in shadow mode for one day to verify the new weightings produce intuitively correct rankings before enabling full publishing.

**Best practices for weight tuning:**
- Change one weight at a time. Changing multiple simultaneously makes it impossible to know which change caused an effect.
- Document the rationale in `config/weight_change_log.json`.
- Review the impact after 3-5 production runs before making further adjustments.
- High-volatility sectors (PE, Banking) may need more frequent tuning than stable sectors (Federal Policy).

---

## How to Change Output Targets

1. Open `config/thresholds.json`.
2. Adjust `"per_sector_targets"`:

```json
"per_sector_targets": {
  "articles_per_sector": 30,
  "minimum_articles_per_sector": 15,
  "maximum_articles_per_sector": 45
}
```

- `articles_per_sector`: The target number of articles per sector per run.
- `minimum_articles_per_sector`: The system will flag a warning if a sector produces fewer than this.
- `maximum_articles_per_sector`: The hard cap. No sector will exceed this regardless of candidate quality.

3. Adjust tier boundaries:

```json
"tier_definitions": {
  "must_cover": {"min_score": 85, "per_sector_max": 5, ...},
  "strongly_recommended": {"min_score": 70, "per_sector_max": 10, ...},
  "brief_format": {"min_score": 55, "per_sector_max": 15, ...},
  "deal_tape": {"min_score": 40, "per_sector_max": 30, ...}
}
```

Changing tier boundaries affects which stories are selected. Raising `must_cover.min_score` from 85 to 90 will reduce the number of flagship articles. Lowering `deal_tape.min_score` from 40 to 35 will include more low-signal items.

4. Targets take effect on the next pipeline run.

**Warning:** Setting `articles_per_sector` above 45 will increase cost proportionally. Each additional article beyond the 210 baseline costs approximately $0.008–$0.015 in LLM generation and enrichment.

---

## How to Review Failures

### Pipeline-Level Failures

1. Open the admin dashboard (`insights-admin.html`).
2. Click "Pipeline Runs" in the navigation.
3. The dashboard shows recent runs with status (success, partial, failed), duration, articles produced, and cost.
4. Click any run with "status: failed" to see the drill-down.

The drill-down shows:
- **Phase**: Which phase failed (ingestion, classification, scoring, ranking, generation, publishing).
- **Item**: Which specific story was being processed when the failure occurred.
- **Error**: The exact error message and stack trace.
- **Context**: The item ID, title, source, and sector at the time of failure.
- **Recovery**: Suggested action (retry, skip, manual intervention).

### Ingestion Failures

When a specific source fails:
1. Navigate to "Source Health" in the admin dashboard.
2. Sources with red status have failed the most recent run.
3. Click a failed source to see its error history: last 10 runs, failure patterns, error types.
4. Common causes:
   - **HTTP 4xx/5xx**: The feed URL is broken or the server is down. Verify the URL manually.
   - **Timeout**: The feed server is slow. Increase `REQUEST_TIMEOUT` in ingestion.py or mark the source for reduced fetch frequency.
   - **Parse error**: The feed is not valid RSS/Atom. The site may have changed its feed format. Investigate manually.
   - **Empty feed**: The source returned HTTP 200 but no entries. This may be normal for low-frequency sources. Check source history to see if this source typically produces entries.

5. If a source fails 3 consecutive runs, it is auto-disabled by the circuit breaker. You can manually re-enable it by setting `"active": true` in sources.json and resetting `"consecutive_failures": 0`.

### Generation Failures

When an article fails to generate:
1. In the admin dashboard, find the article under "Failed Generations".
2. The failure details show the LLM error. Common causes:
   - **Token limit exceeded**: The dossier was too large for the model context window. Reduce full-text enrichment or truncate input.
   - **Model unavailable**: DeepSeek API returned a 5xx. The OpenAI fallback should have kicked in. Check if both are down.
   - **Content policy rejection**: The model refused to generate content. This happens with sensitive topics (lawsuits, criminal allegations). The story is flagged for human review.
   - **Prompt error**: The prompt or dossier caused a malformed response. Regenerate with an updated prompt.

3. Click "Reprocess" to retry generation. The system uses an exponential backoff: 1st retry after 2 minutes, 2nd after 5 minutes, 3rd after 15 minutes. After 3 retries, the item is marked "failed: permanent" and requires manual intervention.

### Classification Failures

When classification produces no sector or low confidence:
1. In the admin dashboard, filter by "classification_confidence < 0.6".
2. Review these items manually. Assign a sector if obvious (the item is reclassified on save).
3. If many items from a particular source are failing classification, the source's `sector` tag may be wrong — check sources.json.

---

## How to Regenerate an Article

1. In the admin dashboard, navigate to "Published Articles".
2. Find the article you want to regenerate. Use the search bar (search by title, entity, or article ID).
3. Click "Regenerate". A confirmation dialog appears:
   - "This will archive the current version and generate a new version using the latest prompts. Continue?"
4. Confirm. The system:
   - Archives the old article (moves to `insights/<sector>/archive/<article_id>_v1.html`).
   - Increments the item's `version` field.
   - Re-runs generation.py with the same dossier but current prompts.
   - Writes the new article to the original URL.
   - Updates the manifest with the new version number.
5. Compare old and new versions side-by-side in the admin dashboard before deciding.
6. If the new version is worse, click "Restore Previous Version". This reverses the archive swap.

**Bulk regeneration:** If you've updated a system prompt and want to regenerate all articles in a sector from the past week, use the admin dashboard's "Bulk Regenerate" tool. This is cost-intensive — it will regenerate potentially 210 articles per day × 7 days = 1470 articles. Confirm the cost estimate before proceeding.

---

## How to Manually Promote or Reject a Story

### From the Candidate Pool

1. In the admin dashboard, go to "Candidate Pool" (stories that were classified but not yet selected/rejected).
2. Browse or search for the story you want to override.
3. **To promote:**
   - Click "Promote" next to the story.
   - Select the target tier (must_cover, strongly_recommended, brief_format).
   - Add an optional note.
   - The story is force-selected and will appear in the sector output regardless of its composite score.
4. **To reject:**
   - Click "Reject" next to the story.
   - Select a rejection reason code from the dropdown: "low_relevance", "duplicate_coverage", "low_quality_source", "editorial_discretion", "other".
   - Add an optional note.
   - The story will not be published regardless of its score.

### Effects of Manual Actions

- Promoted stories appear at the top of their sector feed (above even higher-scored items).
- Promoted stories get a "Editor's Pick" badge in the UI.
- Rejected stories go to the rejection log with the operator's reason code.
- All manual actions are logged with timestamp, operator identifier, action type, and reason.
- The action log is viewable in the admin dashboard under "Audit Log".

### Bulk Promote/Reject

- Use the checkboxes in the Candidate Pool to select multiple items.
- Click "Bulk Promote" or "Bulk Reject".
- Useful for quickly clearing out an entire subsector that you know is not relevant today.

---

## How to Monitor Cost

### Daily Monitoring

1. Open `logs/HEALTH.md` — this file is auto-generated by `scripts/health_report.py` at the end of every pipeline run.
2. It shows:

```
## Cost Summary — 2026-07-30

| Category | Amount |
|----------|--------|
| Classification (LLM) | $0.12 |
| Enrichment (LLM) | $0.08 |
| Generation (LLM) | $1.68 |
| **Daily Total** | **$1.88** |
| **Monthly Projection** | **$56.40** |
| YTD Total | $412.30 |

## Per-Sector Cost

| Sector | Articles | LLM Calls | Cost |
|--------|----------|-----------|------|
| Commercial Real Estate | 32 | 32 | $0.27 |
| Private Equity | 30 | 30 | $0.25 |
| Data Centers | 28 | 28 | $0.24 |
| Energy & Infrastructure | 26 | 26 | $0.22 |
| Banking & Credit | 30 | 30 | $0.25 |
| Federal Policy | 24 | 24 | $0.20 |
| Local Government | 18 | 18 | $0.15 |
| **Total** | **188** | **188** | **$1.58** |

## Cost Drivers

| Phase | Cost | % of Total |
|-------|------|-----------|
| Classification (LLM fallback) | $0.12 | 6.4% |
| Enrichment (full-text + entity extraction) | $0.08 | 4.3% |
| Article Generation | $1.68 | 89.4% |
```

### Cost Alerts

Cost alerts are configured in `config/cost_limits.json`:

```json
{
  "alerts": {
    "daily_warning_usd": 2.50,
    "daily_critical_usd": 3.00,
    "monthly_warning_usd": 75.00,
    "monthly_critical_usd": 90.00,
    "per_article_warning_usd": 0.015
  }
}
```

- **Warning threshold**: The admin dashboard shows a yellow banner. The pipeline continues but the operator is notified.
- **Critical threshold**: The admin dashboard shows a red banner. The pipeline may be paused (configurable). An alert is written to `logs/ALERTS.md`.

### Cost Optimization Tips

- If classification LLM cost is high: Tighten regex patterns to reduce LLM fallback rate. Add more entity aliases to watchlists.json.
- If enrichment cost is high: Reduce full-text enrichment to Tier 1 and Tier 2 stories only.
- If generation cost is high: Reduce per-sector article targets. Switch some sectors from flagship to brief format.
- If total cost is high: Check if the OpenAI fallback is being used heavily (OpenAI is more expensive than DeepSeek). Investigate why DeepSeek is unavailable.

---

## How to Troubleshoot Common Issues

### "Pipeline produced 0 articles today"

**Symptom:** The pipeline ran successfully (no errors) but output 0 articles across all sectors.

**Diagnosis steps:**
1. Check the signal gate in `config/thresholds.json`. If `minimum_source_tier` is set too high, no candidates pass the initial filter.
2. Check `source_health.json` to see if all sources are down. This can happen if there's a widespread RSS outage or DNS issue.
3. Check the GitHub Actions run log for any silent failures (exceptions caught and logged but not surfaced as failures).
4. Check if the ingestion produced any items at all: look at `item_count` in the run summary.

**Resolution:**
- Temporarily lower `minimum_source_tier` to `tier_4` to allow more candidates through.
- Investigate source failures — if a critical mass of sources is down, the day's edition may be unrecoverable. Accept a "no edition" day and fix sources for tomorrow.
- Check if the workflow schedule changed or was disabled.

### "Classification is wrong for X stories"

**Symptom:** Stories are being assigned to the wrong sector. For example, a data center power procurement story is classified as energy_infrastructure instead of data_centers.

**Diagnosis steps:**
1. Check the `classification_method` field on the misclassified items. If "source_prior", the source's sector tag in sources.json may be wrong.
2. If "regex_signals", the classification patterns may have false matches. Check the matched patterns in the classification log.
3. If "entity_match", the entity mentioned may be associated with the wrong sector in watchlists.json.
4. If "llm", the LLM may be misclassifying. Review the LLM's reasoning (stored in classification log).

**Resolution:**
- For source-based errors: Correct the source's sector tag in sources.json. If the source covers multiple sectors, lower sector_weight to force regex/entity/LLM classification.
- For regex errors: Add exclusion patterns to the sector's `classification_signals.exclusion_patterns`. Tune regex to be more specific.
- For entity errors: Update the entity's `primary_sectors` in watchlists.json. Add aliases if the entity is mentioned under different names.
- For LLM errors: Review the classification prompt. It may need additional examples for confusing sector boundaries.
- Long-term: Add the misclassified item as a test case to tests/test_classification.py.

### "Generated articles are low quality"

**Symptom:** Published articles are factually accurate but stylistically weak, repetitive, or lack insight.

**Diagnosis steps:**
1. Check the `evidence_level` for low-quality articles. If evidence_level is "low" or "none", the LLM has insufficient source material to write a good article. The article should have been flagged for deal tape only.
2. Check which system prompt was used. The prompt may need revision.
3. Check the article's `word_count`. If unusually short (<200 words), the LLM may have been truncated or produced a minimal response.
4. Review a sample of low-quality articles against their source dossiers. Is the LLM missing key facts? Are the facts available in the source material?

**Resolution:**
- If evidence is thin: Lower the tier for those stories. Thin evidence should produce brief or deal tape format, not flagship.
- If prompt is weak: Update the sector's system prompt in config/prompts.json. Add better examples. Regenerate a sample and review.
- If generation is truncated: Check token limits. Increase max_tokens in the LLM call. Ensure the dossier is properly truncated before generation.
- If generation is repetitive: Add a "avoid clichés" instruction to the prompt. Add variety requirements (vary headline structure, vary opening sentence).

### "Pipeline is taking too long"

**Symptom:** Pipeline runtime exceeds 2 hours and approaches or exceeds the 6-hour GitHub Actions timeout.

**Diagnosis steps:**
1. Check source health for slow feeds. Sort by `fetch_time_ms` descending.
2. Check how many items are being enriched with full-text (trafilatura). Each web request adds 1-5 seconds.
3. Check LLM latency. Is the model responding slowly? Is the fallback to OpenAI happening frequently (OpenAI is often slower)?
4. Check the number of items — are there unexpectedly many candidates (e.g., a major news day)?

**Resolution:**
- Disable slow sources that produce few usable items. If a feed takes 30 seconds and produces 2 items, it may not be worth it.
- Reduce full-text enrichment scope. Only enrich Tier 1 and Tier 2 stories. Skip enrichment for Tier 3 and deal tape (evidence from RSS description only).
- Increase concurrency in ingestion.py (MAX_WORKERS). Default is 10. Can go up to 20 if the GitHub Actions runner has sufficient resources.
- Reduce per-sector article targets. Generating 210 articles takes longer than generating 140.
- Check if `editorial_intelligence.py` is making unnecessary API calls. The existing pipeline may be doing enrichment that's now handled elsewhere.
- Split into separate workflow jobs (see Phase 6 migration plan in 08-implementation-plan.md).

### "Cost spiked unexpectedly"

**Symptom:** Daily cost is 2-3x normal.

**Diagnosis steps:**
1. Check the cost breakdown by phase. Which phase's cost spiked?
2. If classification cost spiked: Check what percentage of items required LLM classification (>20% is unusual). Check if the regex patterns are failing.
3. If generation cost spiked: Check if article count is higher than normal. Check if per-article token usage is higher (longer articles, more verbose LLM).
4. If OpenAI fallback cost spiked: Check DeepSeek availability. If DeepSeek is down, all calls go to OpenAI at higher cost.

**Resolution:**
- For classification spikes: Improve regex patterns to reduce LLM fallback. Temporarily increase `max_llm_calls_per_classification` threshold if source quality has degraded.
- For generation spikes: Reduce article targets temporarily. Add token budget per article type (flagship max 800 tokens, brief max 400 tokens, deal tape max 200 tokens).
- For OpenAI spikes: Investigate DeepSeek availability. Contact DeepSeek support if persistent. Consider reducing pipeline frequency until DeepSeek is stable.
- Set cost caps in cost_limits.json. The pipeline will refuse to exceed the daily cap.

---

## Administrative Tasks

### Weekly Review Checklist

Every Monday (or after each weekend's automatic runs):

- [ ] Spot-check 5 articles per sector for quality.
- [ ] Review source health report. Investigate any source with >2 consecutive failures.
- [ ] Review cost for the past week. Is it on track for the monthly budget?
- [ ] Check the admin dashboard "Flagged for Review" queue. Review any items with legal/allegation flags.
- [ ] Review rejection report. Are any sectors being over-rejected? Under-rejected?
- [ ] Check pipeline runtime trend. Is it increasing week over week?
- [ ] If any sector produced <minimum_articles_per_sector for 3+ days, investigate source coverage for that sector.

### Monthly Review Checklist

First of each month:

- [ ] Run full pipeline in shadow mode for one day. Review output before returning to production.
- [ ] Review scoring weights. Are they still appropriate given current market conditions?
- [ ] Review watchlist. Any entities to add? Any to remove?
- [ ] Review all system prompts. Have model versions changed? Does output need prompt adjustments?
- [ ] Full cost reconciliation. Compare actual vs. projected.
- [ ] Check for new potential sources. Is there a new RSS feed available for a weak sector?
- [ ] Review reader engagement metrics (if analytics available). Which sectors and article types perform best?
- [ ] Decide whether to adjust per-sector article targets for the coming month.

### Emergency Procedures

**Pipeline is producing factually incorrect articles:**
1. Immediately disable the GitHub Actions workflow.
2. Take down the affected articles from Netlify (use Netlify admin or delete the output files and redeploy).
3. Investigate the root cause: bad source data, LLM hallucination, prompt error.
4. Fix the issue. Run in preview mode to verify.
5. Re-enable publishing only after verification.
6. If readers were affected, consider a correction notice on the Insights page.

**DeepSeek API is down for >2 hours:**
1. The OpenAI fallback should kick in automatically. Monitor cost — it will be higher.
2. If OpenAI is also down or costs are too high: consider running with reduced article targets (or skipping a day).
3. Check `config/cost_limits.json` — if the fallback cost would exceed the daily cap, the pipeline may refuse to run. You can temporarily raise the cap.

**Netlify deployment fails:**
1. Check the Netlify build log. The Insights site is static HTML — deployments rarely fail.
2. If a build error, check if any article HTML files are malformed.
3. If a deploy error (not build), retry the deploy from Netlify admin.
4. If Netlify is down entirely, the articles are generated but not published. They will be published on the next successful deploy (the manifest includes all pending articles).

---

## Configuration Reference

### files Requiring Restart After Changes

| File | Restart Required? | Notes |
|------|-------------------|-------|
| `config/sources.json` | No | Next run picks up changes |
| `config/scoring_profiles.json` | No | Next run picks up changes |
| `config/thresholds.json` | No | Next run picks up changes |
| `config/sectors.json` | No | Next run picks up changes |
| `config/watchlists.json` | No | Next run picks up changes |
| `config/cost_limits.json` | No | Next run picks up changes |
| `config/prompts.json` | No | Next generation uses new prompts |
| `.github/workflows/insights-pipeline.yml` | Yes | GitHub Actions workflow changes require the updated workflow file to be pushed to the repository |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API authentication | Required |
| `DEEPSEEK_MODEL` | Model ID | `deepseek-chat` |
| `OPENAI_API_KEY` | OpenAI fallback authentication | Required |
| `OPENAI_MODEL` | Fallback model ID | `gpt-4o-mini` |
| `NEWSAPI_KEY` | NewsAPI key for supplemental queries | Optional |
| `MAX_WORKERS` | Concurrency for ingestion | `10` |
| `REQUEST_TIMEOUT` | HTTP timeout per feed (seconds) | `15` |
| `RUN_MODE` | `production`, `preview`, `shadow` | `production` |

---

## Support Escalation

For issues that cannot be resolved using this document:

1. Check `logs/` for detailed error logs.
2. Review the pipeline's GitHub Actions run logs (complete with timestamps).
3. Check if the issue is environmental (GitHub Actions outage, Netlify outage, DeepSeek outage).
4. For persistent issues: open a GitHub issue in the repository with the run ID, error messages, and steps to reproduce.

---

*Last updated: July 30, 2026. This document should be reviewed and updated after each phase of implementation (see 08-implementation-plan.md).*
