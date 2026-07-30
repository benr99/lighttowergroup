# Current Architecture: The Light Tower Group Insights Intelligence Engine

**Document:** 02-Current-Architecture
**Date:** July 30, 2026
**Status:** Pre-Overhaul Reference Architecture

---

## 1. System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS (cron 7:07 AM NY)                 │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ RSS Feeds│   │ NewsAPI  │   │ SEC EDGAR│   │Discovery │            │
│  │ (~90)    │   │ queries  │   │ (RSS)    │   │Watchlist │            │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘            │
│       └──────────────┴──────────────┴──────────────┘                   │
│                          │ PHASE 1: GATHER                             │
│                          ▼ (1807 raw stories)                          │
│                    ┌─────────────┐                                     │
│                    │  normalize  │  story_normalizer.py                │
│                    │  + dedupe   │  (topics, entities, features)       │
│                    └──────┬──────┘                                     │
│                           │ PHASE 2: TRIAGE                            │
│                           ▼                                            │
│                    ┌─────────────┐                                     │
│                    │ CRE KEYWORD │  ← THE BOTTLENECK                   │
│                    │   FILTER    │  Must match ≥1 CRE_KEYWORDS         │
│                    │             │  Must NOT match EXCLUDE_KEYWORDS    │
│                    │             │  1807→14 on July 26                 │
│                    └──────┬──────┘                                     │
│                           │ PHASE 3: SCORE                             │
│                           ▼ (14 candidates)                            │
│              ┌────────────────────────┐                                │
│              │  select_edition()      │  editorial_intelligence.py     │
│              │  - cluster_events()    │                                │
│              │  - score_event()       │  10 dimensions, 0-100          │
│              │  - assign_franchise()  │                                │
│              │  - select candidates   │  thresholds: 72/56/34/24       │
│              └───────────┬────────────┘                                │
│                          │ PHASE 4: ENRICH                             │
│                          ▼ (0-5 selected stories)                      │
│              ┌────────────────────────┐                                │
│              │  build_research_       │  research_dossier.py           │
│              │  dossier()             │  - fetch full text per source  │
│              │                        │  - extract facts & quotes      │
│              │  run_editorial_room()  │  - classify evidence level     │
│              │                        │  editorial_room.py             │
│              │  extract_facts()       │  - LLM angle/skeptic pass      │
│              │                        │  fact_extractor.py (new)       │
│              └───────────┬────────────┘                                │
│                          │ PHASE 5: WRITE                              │
│                          ▼ (0-3 articles)                              │
│              ┌────────────────────────┐                                │
│              │  generate_article()    │  DeepSeek API                  │
│              │  - assemble prompt     │  enhanced_prompts.py           │
│              │  - LLM call            │  editorial_voice.py            │
│              │  - self-repair loop    │  (max 2 iterations)            │
│              │  - quality gates       │  content_governance.py         │
│              └───────────┬────────────┘                                │
│                          │ PHASE 6: PUBLISH                            │
│                          ▼                                             │
│              ┌────────────────────────┐                                │
│              │  render_html()         │  insights/{slug}.html          │
│              │  update_manifest()     │  insights.json                 │
│              │  update_sitemap()      │  sitemap.xml                   │
│              │  update_feed()         │  feed.xml                      │
│              │  social_image()        │  {slug}_social.png             │
│              │  validate + commit     │  publish_generated.py          │
│              └───────────┬────────────┘                                │
│                          │ PHASE 5b: LINKEDIN                          │
│                          ▼                                             │
│              ┌────────────────────────┐                                │
│              │  generate_essay_       │  linkedin_essay_queue.json     │
│              │  package()             │                                │
│              └────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
                              │ git commit + push
                              ▼
                    ┌─────────────────┐
                    │   NETLIFY CDN   │
                    │  Static HTML    │
                    │  + Netlify Fns  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  insights.html  │
                    │  (client-side   │
                    │   filter/search)│
                    │  331 articles   │
                    │  in flat JSON   │
                    └─────────────────┘
```

---

## 2. Technology Stack

### Frontend
| Component | Technology | Notes |
|-----------|-----------|-------|
| Site pages | Static HTML | Hand-authored HTML files (index.html, insights.html, buildings.html, about.html) |
| Styling | CSS custom properties | `ltg-*` variable system in site.css; article-base.css extracted for shared article styles |
| Client logic | Vanilla JavaScript | site.js (nav toggle, read tracking, related-research loader); insights.html inline JS (filter, search, paginate) |
| Hosting | Netlify CDN | Static site hosting with automatic deploy on git push |
| Serverless | Netlify Functions (Node.js) | Form handling, dynamic data endpoints |
| SEO | Structured data | JSON-LD, Open Graph, Twitter Cards, canonical URLs per article |

### Backend (Pipeline)
| Component | Technology | Notes |
|-----------|-----------|-------|
| Runtime | Python 3.11 | Single process, sequential phases |
| Orchestration | GitHub Actions | Cron schedule (~7:07 AM NY time), 6-hour timeout |
| RSS Parsing | feedparser library | ThreadPoolExecutor for parallel feed fetching |
| Full-Text Extraction | trafilatura | Per-source full article text for dossier building |
| Search API | NewsAPI.org | Free tier, 18 CRE-focused keyword queries |
| LLM Primary | DeepSeek (deepseek-chat) | Article generation, editorial room, scoring assistance |
| LLM Fallback | OpenAI (gpt-4o-mini / gpt-4o) | Via model_router.py when DeepSeek unavailable |

### Data Layer
| Store | Format | Purpose |
|-------|--------|---------|
| Article manifest | `insights.json` (flat JSON array) | All published articles with metadata; consumed by insights.html |
| Editorial runs | `editions/*.json` | Per-run records with stories processed, candidates scored, articles published |
| Editorial state | `.editorial-state/*.json` | Event memory, audience signals, editorial priors, discovery watchlist |
| Source health | `source-health.json` | Per-source fetch statistics (success/failure/empty counts) |
| LinkedIn queue | `linkedin_essay_queue.json` | Generated essay packages awaiting human review |
| Run logs | `daily-news-agent-*.log` | Detailed per-phase logs for each editorial run |

### Infrastructure
| Component | Technology | Notes |
|-----------|-----------|-------|
| Deployment | Git push → Netlify auto-deploy | `netlify.toml` configures CSP, cache headers, redirects |
| Cost tracking | `scripts/cost_tracker.py` | Per-call token usage and cost estimation |
| Checkpoint/Resume | `scripts/checkpoint.py` | Per-phase timeouts with state serialization |
| Monitoring | `scripts/health_report.py` | Generates HEALTH.md with source health, cost summary, run stats |
| Retrospective | Weekly manual review | Editorial run summaries, pipeline performance trends |

### Cost Profile
| Metric | Value | Notes |
|--------|-------|-------|
| Cost per article | ~$0.07 | DeepSeek pricing for generation + scoring |
| Cost on zero-output day | $0.00 | No LLM calls when nothing passes signal gate |
| Zero-output days | 78.8% | 26 of 33 runs produced 0 articles |
| Effective daily cost | ~$0.04 | Weighted average across all runs |
| Estimated monthly cost | ~$1.20 | At current publish rate |

---

## 3. Key Files and Their Roles

### Core Pipeline (`scripts/`)

| File | Lines | Role |
|------|-------|------|
| `daily_news_agent.py` | 2827 | **Main orchestrator.** Contains `main()` with all 8 phases: gather, triage, score, enrich, write, publish, LinkedIn, finalize. Entry point for GitHub Actions workflow. |
| `news_sources.py` | ~400 | **Source definitions.** RSS feed URLs organized by tier, `CRE_KEYWORDS` list, `EXCLUDE_KEYWORDS` list, `NewsAPI_KEYWORD_QUERIES`. The triage gatekeeper. |
| `editorial_intelligence.py` | ~800 | **Scoring engine.** `score_event()` (10 dimensions, 0-100), `cluster_events()` (cross-source grouping), `assign_franchise()`, `select_edition()` candidate selection. |
| `editorial_scoring.py` | ~300 | **LLM scoring.** Calls DeepSeek for editorial scoring with structured output. Provider-aware via `model_router.py`. |
| `story_normalizer.py` | ~400 | **Story normalization.** Topic extraction (regex patterns for 15 CRE topics), entity extraction, deduplication (72% title similarity), CRE anchor checking. |
| `bucketed_editorial.py` | ~250 | **Sub-domain routing.** `route_story()` classifies stories into 5 CRE buckets (real estate, capital markets, policy, architecture, market analysis). |
| `research_dossier.py` | ~400 | **Evidence dossier.** `build_research_dossier()` fetches full text, extracts facts/quotes, classifies evidence level (deep/adequate/thin/insufficient). |
| `editorial_room.py` | ~250 | **Pre-writing analysis.** LLM-driven angle identification and skeptic review before article generation. |
| `content_governance.py` | ~400 | **Quality gates.** 10 independent checks after article generation (not trusting LLM self-assessment). |
| `enhanced_prompts.py` | ~500 | **Prompt templates.** System prompts, user prompt assembly, voice mode integration, headline shape selection. |
| `editorial_voice.py` | ~300 | **Voice configuration.** Voice modes, headline shape definitions, quality check patterns. |
| `model_router.py` | ~200 | **Provider failover.** Health checks for DeepSeek and OpenAI, automatic fallback routing. |
| `checkpoint.py` | ~150 | **Resilience.** Per-phase timeout handling, checkpoint serialization, resume capability. |
| `cost_tracker.py` | ~100 | **Cost monitoring.** Per-call token counting, cost estimation, run-level cost summary. |
| `fact_extractor.py` | ~200 | **Fact verification.** Deterministic extraction of numeric claims, semantic audit against source evidence. |
| `article_variants.py` | ~100 | **A/B testing.** Variant assignment for articles. |
| `rebuild_articles.py` | ~300 | **Template rebuild.** Bulk rebuild of all published articles from source data. |

### Frontend

| File | Role |
|------|------|
| `insights.html` | Client-side article listing. Fetches `insights.json`, renders cards with category filtering, search, and pagination. 331 articles rendered client-side. |
| `buildings.html` | Building profile database with maturity filtering (under construction, recently completed, stabilized). |
| `index.html` | Home page with firm overview, services, team. |
| `about.html` | Firm history, team bios, contact information. |
| `site.js` | Shared JavaScript: mobile nav toggle, read-tracking (localStorage), related-research lazy loader. |
| `site.css` | Shared CSS with `ltg-*` custom property system for consistent theming (gold `#C9A84C`, dark palette). |
| `insights/article-base.css` | Extracted article template styles, shared across all published article HTML files. |
| `netlify.toml` | Netlify configuration: build settings, CSP headers, cache rules, redirects, serverless function routing. |

### Data Files

| File | Role |
|------|------|
| `insights.json` | Flat JSON array of all 331 published articles. Each entry: slug, title, date, category, description, image, tags, url. Consumed by insights.html at page load. |
| `feed.xml` | RSS feed of published articles. Auto-generated during publish phase. |
| `sitemap.xml` | XML sitemap for search engine indexing. Auto-generated during publish phase. |
| `editions/*.json` | Per-run editorial records: input stories, triage results, scored candidates, editorial decisions, published articles, cost summary. |
| `.editorial-state/event-memory.json` | Persistent memory of previously seen events and topics (used for novelty scoring and deduplication across runs). |
| `.editorial-state/editorial-priors.json` | Editorial preferences and learned weights from past runs. |
| `.editorial-state/discovery-watchlist.json` | Configurable watchlist of entities, topics, and queries for proactive story discovery (new, not yet integrated). |
| `source-health.json` | Per-source health statistics: total fetches, successes, failures, empty returns, last fetch timestamp. |
| `linkedin_essay_queue.json` | Essay packages generated for LinkedIn, awaiting human review and posting. |

---

## 4. Data Flow (Step by Step)

### Pre-Flight
1. GitHub Actions cron fires on schedule → checks out `main` branch
2. Sets up Python 3.11 environment → installs dependencies from `requirements.txt`
3. Resolves schedule policy (daily, weekday-only, test mode)

### Phase 1: Gather
4. `main()` initializes → loads known insights from `insights.json`, audience signals, event memory from `.editorial-state/`, editorial priors
5. `fetch_rss_stories()` iterates ~103 RSS feeds via `ThreadPoolExecutor` using `feedparser`
6. `fetch_newsapi_stories()` queries NewsAPI.org with 18 CRE keyword queries
7. `fetch_sec_edgar_rss()` pulls SEC EDGAR filings (RSS format)
8. Total raw yield: ~1807 stories (July 26 baseline)
9. `normalize_stories()` extracts topics (regex), entities, and features; deduplicates at 72% title similarity

### Phase 2: Triage
10. `triage_bucketed_volume()` begins — each normalized story is evaluated:
    - Checked against `EXCLUDE_KEYWORDS` (single-family, celebrity, residential listings, etc.) — match = discard
    - Checked against `CRE_KEYWORDS` — no match = discard (must match at least one keyword)
    - `route_story()` attempts to classify into one of 5 CRE buckets
    - If no bucket matches, story is discarded
    - Survivors: ~14 candidates (0.78% of raw intake)

### Phase 3: Score
11. `pre_enrich_selection_candidates()` — for top candidates, fetch full text to improve event clustering
12. `select_edition()`:
    - `cluster_events()` — group related headlines by cross-source corroboration
    - `score_event()` — compute 10-dimension deterministic score (0-100) for each event cluster
    - `assign_franchise()` — label each event: flagship, brief, data_note, culture_signal
    - Select candidates exceeding thresholds: MUST_READ (56), DEAL_TAPE (34), FLAGSHIP_CANDIDATE (72)
    - Optional: `editorial_scoring.py` provides LLM-assisted scoring overlay
13. Signal gate: stories below MUST_READ_THRESHOLD (56) are not considered for article generation
14. Selected for enrichment: 0-5 stories (0 on July 26)

### Phase 4: Enrich
15. For each selected story:
    - Fetch full article text from each source URL using `trafilatura`
    - `build_research_dossier()` — classify evidence level per source (deep/adequate/thin/insufficient), extract key facts, identify corroborating and conflicting details
    - `extract_facts()` — deterministic extraction of numeric claims (dollar amounts, square footage, unit counts) + semantic audit
    - `run_editorial_room()` — LLM pass: identify narrative angle, surface skepticism, flag gaps
16. Terminal editorial decision per story: write (proceed to Phase 5), kill (insufficient evidence), defer (hold for more sources), deal_tape (log as transaction record only)

### Phase 5: Write
17. For each story marked "write":
    - `generate_article()` assembles prompt: system prompt + user prompt + research dossier + voice mode + franchise + headline shape
    - DeepSeek API call generates article text
    - `content_governance.py` runs 10 independent quality gates
    - If any gate fails → self-repair loop (max 2 iterations):
      - Regenerate with explicit repair instructions
      - Article score resets
      - Re-run all quality gates
    - If both repair attempts fail → kill article, log failure
    - If all gates pass → article proceeds to publish
18. Typical output: 0-3 articles per run

### Phase 6: Publish
19. For each completed article:
    - `render_html()` — generate `insights/{slug}.html` with inlined CSS, JSON-LD, OG tags, article content
    - `generate_social_image()` — create `{slug}_social.png` preview image
20. `update_manifest()` — add article entry to `insights.json`
21. `update_feed()` — add entry to `feed.xml`
22. `update_sitemap()` — add URL to `sitemap.xml`
23. `validate_repository()` — check for broken links, invalid JSON, missing assets
    - On failure: roll back all file writes from this run (atomically, all-or-nothing)
    - On success: `git add` all new/modified files → `git commit` → `git push`
24. Netlify detects push → auto-deploys updated site

### Phase 5b: LinkedIn
25. `generate_essay_package()` — creates LinkedIn-optimized version of flagship articles
26. Saves to `linkedin_essay_queue.json` for human review and posting

### Phase 8: Finalize
27. Write detailed run log to `daily-news-agent-*.log`
28. Save editorial run record to `editions/*.json` (full trace: stories → triage → scored → decisions → published → costs)
29. Update event memory in `.editorial-state/event-memory.json` (persist seen events for deduplication)
30. Save publication decisions
31. Render run summary to stdout (stories gathered, triaged, scored, enriched, written, published; costs; errors)

---

## 5. Scoring Architecture Detail

### Deterministic Scoring: `score_event()` in `editorial_intelligence.py`

The 10 dimensions, each contributing to a 0-100 composite:

| # | Dimension | Weight | What It Measures |
|---|-----------|--------|------------------|
| 1 | Transaction Scale | High | Deal size relative to market comps and historical baselines |
| 2 | Market Significance | High | Concentration in key submarkets, market share implications |
| 3 | Source Quality | Medium | Number of corroborating sources, publication tier, reporter authority |
| 4 | Timeliness | Medium | Recency (within 36-hour window), exclusivity premium |
| 5 | Novelty | Medium | First-of-kind, unusual structure, departure from trend |
| 6 | Capital Stack Complexity | Medium | Debt/equity layers, financing creativity, lender diversity |
| 7 | Policy Impact | Medium-Low | Zoning changes, tax abatements, regulatory actions affecting CRE |
| 8 | Strategic Relevance | Medium-Low | Portfolio fit for major players, market entry/exit signals |
| 9 | Geographic Concentration | Low | NYC-metro premium vs. national vs. international |
| 10 | Narrative Potential | Low | Human interest, visual potential, explainer value |

**Thresholds:**
- `FLAGSHIP_CANDIDATE_THRESHOLD = 72` — top-tier, signals major story
- `MUST_READ_THRESHOLD = 56` — signal gate; stories below this are not considered for articles
- `DEAL_TAPE_THRESHOLD = 34` — logged as transaction record but not a narrative article
- `SIGNAL_THRESHOLD = 24` — tracked for event memory but not published

### LLM Scoring Overlay: `editorial_scoring.py`

Optional LLM-assisted scoring that provides a second opinion on the deterministic score. Used sparingly for borderline cases. Calls DeepSeek (or OpenAI fallback) with structured output format. Provider routing via `model_router.py` with health checks.

---

## 6. Quality Assurance Architecture

### Content Governance (`content_governance.py`)

Ten independent quality gates run after every article generation. These are syntactic and structural checks — they do not evaluate editorial quality (that is the LLM editorial room's job):

1. **Factual Grounding** — Verify numeric claims against source dossier
2. **Source Attribution** — At least one named source cited in article
3. **Structural Integrity** — Has headline, lede, body, closing paragraph
4. **Narrative Coherence** — No contradictory statements, consistent timeline
5. **Regulatory Accuracy** — Agency names, rule numbers, legal citations verified
6. **Date Consistency** — All dates within valid ranges, no future dates in past-tense stories
7. **Entity Correctness** — Company names, people, properties match source material
8. **Quote Fidelity** — Quoted material traceable to source (if claimed as direct quote)
9. **Length Threshold** — Meets minimum word count for franchise type
10. **Repetition Detection** — No paragraph-level duplication within article

### Self-Repair Loop

If any quality gate fails:
1. Failure details are compiled into a repair instruction
2. The article prompt is extended with: "The previous version failed quality check X because Y. Repair the article to address this issue."
3. DeepSeek regenerates the article
4. All 10 gates re-evaluate
5. Max 2 repair attempts; if both fail, article is killed

### Rollback Mechanism

Before git commit, `validate_repository()` checks:
- `insights.json` is valid JSON
- All referenced HTML files exist
- All internal links resolve
- No orphaned files from partial writes

If validation fails, all files written during this publish phase are deleted, and the commit is aborted. The editorial run record still logs the failure.

---

## 7. Source Architecture

### Feed Organization (4 Tiers + Federal)

| Tier | Count | Focus | Example Feeds |
|------|-------|-------|---------------|
| Tier 1 | ~20 | NYC-Focused CRE | The Real Deal, Commercial Observer, Bisnow NY, Crain's NY, NY YIMBY |
| Tier 2 | ~30 | National CRE | GlobeSt, Connect CRE, NREI, Multi-Housing News, HousingWire, 10 Bisnow regional |
| Tier 3 | ~25 | Capital Markets/Finance | PERE News, MBA Newslink, Bloomberg RE, American Banker, Trepp, NAREIT |
| Tier 4 | ~15 | Regional/Context | NY Post, Curbed NY, CoStar, NY Times RE, regional business journals |
| Federal | ~15 | Regulatory/Policy | Federal Reserve (7 feeds), FDIC, OCC (2), SEC (4), FHFA, HUD, CFPB, Treasury |

### Supplementary Sources
- **NewsAPI** — 18 keyword queries for CRE topics (free tier, supplementary)
- **SEC EDGAR RSS** — Real-time filing notifications
- **Discovery Watchlist** — `.editorial-state/discovery-watchlist.json` with 18 NewsAPI queries + EDGAR RSS (newly created, not yet operational)

### Source Health
- 48 of 103 feeds returned empty on most recent fetch (46% failure rate)
- Some major feeds (The Real Deal) have had 3 consecutive empty runs
- Commercial Observer and GlobeSt are healthy and consistent
- Federal feeds mostly healthy; some (Treasury, CFPB) return empty

---

## 8. Publishing Architecture

### Article File Structure
Each published article produces:
```
insights/
  {slug}.html              # Standalone article page with inlined CSS + JSON-LD
  {slug}_social.png        # Generated social preview image
```

Plus manifest updates:
```
insights.json              # New entry appended to flat array
feed.xml                   # New <item> in RSS feed
sitemap.xml                # New <url> entry
```

### Client-Side Rendering
`insights.html` loads `insights.json` at page load (AJAX), then:
- Renders article cards in a grid
- Provides category filter (6 categories: Capital Markets, Deal Intelligence, Debt & Equity, Policy & Regulation, Architecture & Capital Markets, Market Analysis)
- Provides text search across titles and descriptions
- Client-side pagination (show N per page)

### Current Scale
- 331 published articles in `insights.json`
- 6 category filters
- ~1095 articles/year at 3/day max
- Each article: ~15-30 KB HTML file

### Scale Problem at 210 Articles/Day
At 210 articles/day × 365 days = 76,650 articles/year:
- `insights.json` would be ~15-30 MB (unacceptably large for client-side fetch)
- 76,650 HTML files in `insights/` would slow git operations and Netlify deploys
- Sitemap generation would become a bottleneck
- Client-side rendering of 76,650 entries in memory would freeze browsers

---

## 9. Deployment Architecture

### GitHub Actions Workflow
```yaml
on:
  schedule:
    - cron: '7 11 * * *'  # ~7:07 AM NY time (11:07 UTC)
  workflow_dispatch:       # Manual trigger for testing
```

- Runner: Ubuntu latest
- Timeout: 6 hours
- Steps: checkout → setup Python 3.11 → install dependencies → run `main()` → commit + push (if articles generated)

### Netlify Configuration (`netlify.toml`)
- Build command: none (static site, pre-built)
- Publish directory: root
- CSP headers for security
- Cache headers for static assets
- Redirects for legacy URLs

### Netlify Serverless Functions
- Contact form handler
- Newsletter signup
- Dynamic data endpoints (limited)

---

## 10. Monitoring and Observability

### Health Report (`scripts/health_report.py`)
Generates `HEALTH.md` with:
- Source health summary (feed success/failure/empty rates)
- Run statistics (stories gathered, triaged, scored, published)
- Cost summary per run and cumulative
- Error rates and failure modes

### Source Health Tracking (`source-health.json`)
Per-source counters:
- Total fetches
- Successful fetches (returned items)
- Empty fetches (200 OK, no items)
- Failed fetches (connection error, timeout, parse error)
- Last successful fetch timestamp
- Consecutive failure count

### Run Logs
Detailed per-phase logs in `daily-news-agent-*.log`:
- Timestamps per phase
- Story counts at each stage
- Scoring details per event
- Editorial decisions with reasoning
- LLM call details (model, tokens, cost, latency)
- Error traces with full context

### Weekly Retrospective
Manual review process examining:
- Editorial run summaries for the week
- Pipeline performance trends
- Source health degradation alerts
- Cost anomalies
- Content quality spot-checks

---

## 11. Known Constraints and Limits

| Constraint | Current Limit | Impact at 210/Day |
|------------|--------------|--------------------|
| Runner timeout | 6 hours | Phases must be optimized; parallelization may be needed |
| Single-threaded pipeline | Sequential phases | Phase 3-6 for 210 stories would exceed timeout |
| insights.json size | 331 entries (~200 KB) | Would reach ~15 MB at scale — too large for client fetch |
| insights/ directory | ~331 HTML files | Would reach 76,650 files/year — git slowdown |
| RSS feed timeout | 30s per feed | 103 feeds = ~52 min in gather phase alone (with 20 threads) |
| NewsAPI free tier | 100 requests/day | Already near limit with 18 queries |
| DeepSeek API rate limit | Not documented | Needs stress testing at 210 article generation calls/day |
| Category taxonomy | 6 categories | Cannot represent 7 sectors × subsectors |
| Single editorial voice | Voice modes within CRE | Need sector-appropriate voices (PE analyst, policy wonk, etc.) |
| No admin interface | Manual file edits | Cannot promote/reject stories without editing JSON by hand |
| No sector analytics | None | Cannot track output per sector or per event type |
