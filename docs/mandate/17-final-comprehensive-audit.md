# Light Tower Group Insights — Final Comprehensive Audit Prompt

You have full access to the repository. The system has been through extensive development. Your job is to find EVERY remaining bug, integration gap, design flaw, performance issue, or operational risk. Leave no stone unturned.

## Audit Scope

### 1. GitHub Actions Workflows (`.github/workflows/`)
- `daily-insights-agent.yml` — daily pipeline at 7:07 AM NY
- `quality.yml` — PR/PR validation
- `weekly-assignment-desk.yml` and `weekly-health-check.yml` — scheduled maintenance
- Check: cron triggers, environment vars, permissions, timeouts, conditional execution logic, concurrency groups, artifact retention

### 2. Core Pipeline Code (`scripts/`)
- `daily_news_agent.py` — main orchestrator, argument parsing, mode handling
- `pipeline_v2.py` — multi-sector pipeline orchestrator
- `editorial_pipeline.py` — 7-stage pipeline (brief → prompt → draft → financial review → editorial review → fact verification → final revision)
- `analytical_brief.py` — structured pre-writing reasoning
- `classification.py` — multi-label classification with source priors + regex
- `scoring_engine.py` — 10-dimension deterministic scoring + LLM scoring
- `ranking.py` — within-sector ranking, diversity controls, cross-sector dedup
- `editorial_scorer.py` — 14-dimension rubric with publishability thresholds
- `ingestion.py` — RSS feed fetching, source health, deduplication
- `editorial_scorer.py` — 14-dimension automated scoring
- `ranking.py` — within-sector ranking, diversity controls, cross-sector dedup
- `generation.py` — sector-aware article routing
- `sector_prompts.py` — sector-specific prompts and headline shapes
- `editorial_voice.py` — voice modes, headline shapes, narrative finance addendum
- `editorial_scoring.py` — LLM scoring call
- `editorial_room.py` — editorial room simulation
- `editorial_intelligence.py` — event clustering, scoring, archive matching
- `editorial_scoring.py` — LLM scoring call
- `editorial_room.py` — editorial room simulation
- `enhanced_prompts.py` — system/user prompts for article generation
- `editorial_intelligence.py` — event clustering, scoring, edition selection
- `editorial_store.py` — durable editorial records
- `edition_manager.py` — edition document builder
- `research_dossier.py` — pre-writing research dossiers
- `story_normalizer.py` — feed item normalization, CRE anchor detection
- `editorial_store.py`, `edition_manager.py` — persistence layer
- `bucketed_editorial.py` — legacy path, should be deprecated or removed
- `daily_news_agent.py` — legacy entry point, must not conflict with pipeline-v2
- `validate_publication.py` — article validation
- `publish_generated.py` — git commit/push logic
- `validate_publication.py` — article validation logic

### 3. Configuration Files
- `config/sources.json` — 198 sources, 158 verified, all 7 sectors covered
- `config/sectors.json` — sector taxonomy
- `config/scoring_profiles.json` — 7 sector-specific weight profiles
- `config/thresholds.json` — article targets, tier boundaries, diversity controls
- `config/watchlists.json` — entity watchlists for scoring
- `config/thresholds.json` — article targets, tier boundaries, diversity controls
- `netlify.toml` — CSP headers, redirects, cache headers, CDN config

### 3. Frontend
- `insights.html` — main listing page with 7-sector filter, search, pagination
- `buildings.html` — building profiles page
- `site.js` — client-side logic
- `edition.js` — edition-specific rendering
- `site.css`, `experience-2026.css`, `article-base.css`, `edition.css` — stylesheets
- `chat-widget.js` — chat widget
- `netlify/functions/` — serverless functions

### 4. Tests
- `tests/` — all test files, coverage, edge cases
- `tests/test_comprehensive.py` — comprehensive integration tests
- `tests/test_editorial_pipeline.py` — editorial pipeline tests
- `tests/test_pass5_audit.py` — audit tests
- `tests/test_phase2_3_integration.py` — phase 2/3 integration
- `tests/test_generation.py` — generation tests
- `tests/test_editorial_pipeline.py` — pipeline tests
- `tests/test_generation.py` — generation tests
- `tests/test_editorial_voice.py` — voice tests
- `tests/test_comprehensive.py` — comprehensive tests

### 4. Content & Content Generation
- `insights.html` — main listing page with 7-sector filter, search, pagination
- `insights.json` — article manifest (878 entries)
- `latest-edition.json` — current edition metadata
- `editions/` — daily edition JSON files
- Article HTML generation via `render_html()` in `daily_news_agent.py`

### 5. Configuration & Secrets
- GitHub Actions secrets: `DEEPSEEK_API_KEY`, `NEWSAPI_KEY`
- Netlify functions environment
- Netlify CSP headers, redirects, cache rules

## AUDIT TASKS

### 1. GitHub Actions Workflows
- [ ] `daily-insights-agent.yml` — cron triggers, schedule policy resolution, baseline validation, pipeline execution, publish logic, artifact upload
- [ ] `quality.yml` — PR/PR validation, test matrix, node/python versions, caching
- [ ] `weekly-assignment-desk.yml` — cron, assignment desk logic
- [ ] `weekly-health-check.yml` — cron, health report generation

### 2. Pipeline Execution Flow
- [ ] Cron trigger → schedule policy → baseline validation → pipeline-v2 ingestion → classification → scoring → ranking → analytical brief → LLM drafting → multi-stage review → fact verification → final revision → publish
- [ ] Verify `daily_news_agent.py --pipeline-v2` entry point works end-to-end
- [ ] Shadow mode (`--shadow`), dry-run (`--dry-run`), publish mode behavior
- [ ] Schedule policy resolution (`resolve_schedule_policy.py`) — exact time matching, skip logic
- [ ] Pipeline v2 stages: ingestion → classification → scoring → ranking → analytical brief → LLM drafting → review loops → final revision → publish
- [ ] Article generation: sector-aware prompts, voice modes, franchise assignment, headline shapes
- [ ] Multi-stage editorial review: financial, editorial, fact verification
- [ ] Final revision incorporating review feedback
- [ ] Publishing: `render_html`, manifest update, sitemap/feed rebuild, git commit/push

### 3. Configuration Consistency
- [ ] `config/sources.json` — all feeds have valid URLs, correct sectors, verified flags
- [ ] `config/sectors.json` — sector taxonomy complete
- [ ] `config/scoring_profiles.json` — 7 sector profiles, 10 dimensions each, weights sum correctly
- [ ] `config/thresholds.json` — article targets, tier boundaries, diversity controls
- [ ] `config/watchlists.json` — entity watchlists for scoring
- [ ] `config/thresholds.json` — tier boundaries, diversity controls
- [ ] All JSON files valid syntax, no trailing commas

### 5. HTML Output Quality
- [ ] `render_html()` produces complete valid HTML5
- [ ] Open Graph, Twitter Card, JSON-LD schema.org markup
- [ ] Share buttons, CTA block, source attribution
- [ ] Related research section, tags, categories
- [ ] SEO metadata (canonical, Open Graph, Twitter Card, JSON-LD)
- [ ] Responsive design, no layout shifts
- [ ] Proper escaping, no XSS vectors
- [ ] `insights.html` — filter buttons, search, sort, pagination, edition section
- [ ] `buildings.html` — maturity filter, search, sector-appropriate display
- [ ] No duplicate IDs, no invalid HTML nesting, valid HTML5

### 6. Article Generation Quality
- [ ] Analytical brief produced before drafting
- [ ] Sector-specific prompts (7 sectors) with correct voice modes
- [ ] Narrative finance addendum included in prompts
- [ ] Article types: flagship, brief, culture_signal, data_note, deal_tape
- [ ] Narrative ledger fields populated (anchor, tension, cast, mechanism, claim, reader_consequence, scene)
- [ ] Financial analysis: capital structure, incentives, risk transfer
- [ ] Incentive analysis explicit
- [ ] Counterargument presented
- [ ] Numbers interpreted, not just listed
- [ ] Thesis stated early, supported by evidence
- [ ] Conclusions actionable for capital decision-makers
- [ ] No "signals/reveals/underscores" crutch language
- [ ] No AI tell phrases ("the real story is", "in this cycle", etc.)
- [ ] Human-like voice, authoritative but not arrogant
- [ ] Specific numbers with units, sources cited
- [ ] Counterargument / counterfactual presented
- [ ] Conclusion identifies what to watch next

### 6. Multi-Sector Coverage
- [ ] CRE: 30+ articles/day target, 87 feeds
- [ ] Private Equity: 17 feeds → 15-20 articles/day
- [ ] Data Centers: 4 feeds + NewsAPI, ~15/day
- [ ] Energy: 20 feeds, 15-20 articles/day
- [ ] Banking/Credit: 35 feeds
- [ ] Fed/Macro: 21 feeds
- [ ] Local Gov: 8 feeds + NewsAPI
- [ ] Data Centers: 4 feeds + NewsAPI
- NewsAPI queries configured for each sector as fallback

### 6. Netlify Configuration
- [ ] `netlify.toml` — redirects, headers, CSP, cache rules
- [ ] CSP allows inline scripts on `/insights.html` and `/buildings.html`
- [ ] `/insights.html` CSP: `script-src 'self' 'unsafe-inline'`
- [ ] `/buildings.html` CSP: `script-src 'self' 'unsafe-inline'`
- [ ] `insights.html` CSP override configured
- [ ] Functions deployed: `newsletter-subscribe`, `editorial-feedback`, `chat`, `mandate-submit`, `deal-notify`, `linkedin-essay`, `track-read`

### 7. Netlify Functions
- [ ] `chat.js` — chat widget
- [ ] `editorial-feedback.js` — editorial feedback endpoint
- [ ] `chat-widget.js` — widget loading
- [ ] `mandate-submit.js` — deal review submission
- [ ] `newsletter-subscribe.js` — newsletter signup
- [ ] `deal-notify.js` — deal notification
- [ ] `linkedin-essay.js` — LinkedIn essay queue
- [ ] All functions have rate limiting, CORS, input validation
- [ ] Environment variables configured in Netlify dashboard

### 7. Test Suite Completeness
- `python -m py_compile scripts/*.py` — all clean
- `python -m unittest discover -s tests -v` — OK (90 tests, 2 skipped)
- `python -m py_compile scripts/*.py` — all 13 modules clean
- `python tests/test_comprehensive.py` — 149 passed
- `tests/test_generation.py` — passes
- `tests/test_editorial_pipeline.py` — passes
- `tests/test_pass5_audit.py` — passes
- `tests/test_phase2_3_integration.py` — passes
- `tests/test_generation.py` — passes
- `tests/test_editorial_voice.py` — passes
- `tests/test_phase2_3_integration.py` — passes
- `tests/test_phase1_smoke.py` — passes
- `tests/test_comprehensive.py` — passes
- `tests/test_editorial_voice.py` — passes
- `tests/test_phase2_3_integration.py` — passes
- `tests/test_generation.py` — passes
- `tests/test_comprehensive.py` — 149 passed
- `tests/test_editorial_voice.py` — passes
- `tests/test_generation.py` — passes
- `tests/test_editorial_pipeline.py` — passes
- `tests/test_editorial_voice.py` — passes
- `tests/test_pass5_audit.py` — passes
- `tests/test_phase2_3_integration.py` — passes
- `tests/test_generation.py` — passes
- `tests/test_phase1_smoke.py` — passes

### 9. Cost & Performance
- [ ] Per-article cost ~$0.007 (DeepSeek)
- [ ] Daily cost at 210 articles: ~$2.10/day (~$63/month)
- [ ] LLM calls per article: ~3-4 (draft + financial review + editorial review + conditional revision)
- [ ] Classification: 94% deterministic, 6% LLM
- [ ] Article generation latency: ~30-60s/article
- [ ] Daily pipeline runtime: <10 minutes end-to-end

### 8. Live Site Verification
- [ ] https://lighttowergroup.co/insights.html loads without JS errors
- [ ] 7 sector tabs filter correctly
- [ ] Search works
- [ ] Pagination works (18 per page)
- [ ] Sort dropdown works (newest, flagship)
- [ ] Article pages load with full template (OG tags, JSON-LD, share bar, CTA, related research, sources)
- [ ] Article pages have: OG tags, JSON-LD, share buttons, CTA block, related research, source list
- [ ] SEO meta tags present (canonical, OG, Twitter, JSON-LD)
- [ ] No console errors on load
- [ ] Mobile responsive

### 9. Edge Cases & Error Handling
- [ ] Feed fetch timeout / failure handling
- [ ] LLM API rate limit / error handling
- [ ] Empty feed handling
- [ ] Duplicate detection
- [ ] Archive deduplication
- [ ] Schedule policy grace window (07:05-07:15)
- [ ] Skip logic for thin news days
- [ ] LLM rate limit / error handling / retry
- [ ] Netlify function cold start latency
- [ ] Git push retry on conflict

### 10. Operational Readiness
- [ ] Runbook documented for manual intervention
- [ ] Rollback procedure documented
- [ ] Cost monitoring alert threshold
- [ ] Failed run alerting
- [ ] Manual override procedure documented

## EXECUTION INSTRUCTIONS

For each item above:
1. Verify it works
2. If broken, fix it
3. Document what was fixed
3. Update todo list

Report format:
```
## AUDIT REPORT
### PASSED: [list]
### FAILED: [list with details]
### FIXED: [list]
### BLOCKED: [list with reason]
### RECOMMENDATIONS: [list]
```

Do NOT modify code yet. Just audit and report. I will execute fixes after your report.