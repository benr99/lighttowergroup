# Light Tower Insights Generator — Complete Systems Documentation Prompt

You are a senior systems architect writing a complete, step-by-step technical write-up of the **Light Tower Insights autonomous editorial intelligence pipeline**. This is a Python pipeline that runs daily via GitHub Actions, discovers commercial real estate and multi-sector financial news from 150+ sources, scores editorial value, generates institutional-grade articles via DeepSeek LLM, validates output deterministically, and publishes to a Netlify-hosted website.

Your output must be a single comprehensive markdown document that anyone can read to understand EXACTLY what every file does, step by step, as if reading the source code of a factory.

---

## THE SYSTEM AT A GLANCE

**Light Tower Group** is a commercial real estate capital advisory firm. The Insights pipeline is an autonomous AI newsroom that:

1. **Discovers** news from 150+ RSS feeds + NewsAPI across 7 sectors (CRE, Private Equity, Data Centers, Energy, Banking/Credit, Fed/Macro, Local Government)
2. **Classifies** every story into sector, event type, subsector using regex + entity matching
3. **Groups** duplicate coverage into distinct events (prevents 3 outlets covering the same $500M deal from consuming 3 article slots)
4. **Scores** editorial value across 10 deterministic dimensions + LLM must-read scoring
5. **Selects** a scarce daily portfolio targeting 3 publishable pieces
6. **Researches** — builds multi-source dossiers with full text, facts, quotes, evidence level
7. **Assigns** — an editorial room LLM decides format (Flagship Analysis, Intelligence Brief, Culture of Capital, Data Note, or Deal Tape), kill/defer/shorten
8. **Generates** articles through a 7-stage pipeline (Analytical Brief → Prompt Assembly → Drafting → Financial Review → Editorial Review → Fact Verification → Final Revision)
9. **Validates** — deterministic content governance layer (NEVER calls LLM) checks word count, structure, sources, boilerplate, prompt injection, fact-audit, semantic claim audit, duplicate detection
10. **Publishes** — writes HTML articles, social images, edition JSON, RSS feed, sitemap, LinkedIn essays, PDF carousels
11. **Git commits** and pushes to main (or opens PR for flagship/legal-sensitive work)
12. **Deploys** via Netlify CDN with CSP security headers

The pipeline produces ~450+ published articles in `insights/`, tracked in `insights.json`.

---

## FILE-BY-FILE DEEP DIVE

For each file below, you must write:

- The file's role in the pipeline
- Every major function, what it does, how it works, what inputs it takes, what outputs it produces
- The exact algorithms and logic (e.g., how regex patterns match, how scores are computed, how JSON is parsed)
- Error handling, edge cases, safeguards
- How it connects to other files (imports, data passed between them)
- The line count and notable design decisions

---

### 1. `scripts/daily_news_agent.py` — THE ORCHESTRATOR (2842 lines)

**Role**: The central nervous system. The main entry point that coordinates every stage of the pipeline from ingestion through publication. This is the file invoked by GitHub Actions or the local scheduler.

**Imports and Setup (lines 1-171)**:
- Imports 20+ sub-modules covering feeds, prompts, scoring, governance, editorial, research, publishing, social images, LinkedIn, source health, checkpoints, cost tracking
- Loads `.env` for API keys (lines 36-41): reads DEEPSEEK_API_KEY, NEWSAPI_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN
- Defines paths: SITE_ROOT, INSIGHTS_DIR, INSIGHTS_JSON, FEED_XML, SITEMAP_XML, LOG_FILE
- Defines static sitemap pages (lines 132-149): 16 pages with priority/frequency hints
- Fuses RSS_FEEDS + FEDERAL_RSS_FEEDS into ALL_RSS_FEEDS (line 157)
- Configures DeepSeek LLM (lines 159-170): model deepseek-v4-pro, URL https://api.deepseek.com/v1/chat/completions
- `redact_secret_text()`: Strips API keys and bearer tokens from logs
- `assert_no_mojibake()`: Fails fast if generated content has encoding damage (detects � characters)

**Phase 1: GATHER (lines 201-279)** — `fetch_rss_stories()`
- Iterates through ALL_RSS_FEEDS tuple
- Skips quarantined sources (source health ledger)
- Calls `feedparser.parse()` with User-Agent header
- For each feed entry: extracts title, url, summary (strips HTML), published date
- Records source health (success, empty, failure) via `SourceHealthLedger`
- Shared outage detection: if ≥8 sources attempted and ≥50% fail, releases quarantines (network-wide outage, not per-publisher failure)
- Returns list of story dicts: {title, url, summary, source, published}

**Phase 2: TRIAGE (approx lines 280-500)**
- Filters stories: last 36 hours, CRE-relevant, deduplicates
- Uses `story_normalizer.py` functions: `has_cre_editorial_anchor()`, `has_reported_amount_at_least_ten_million()`
- Sanitizes user-submitted text (removes instruction-like strings, prevents prompt injection)

**Phase 3: SCORE (approx lines 500-800)**
- Calls `daily_top_news_selection()` from `editorial_scoring.py` — LLM-based must-read ranking
- Legacy scoring modes: `bucketed_volume_selection()` from `bucketed_editorial.py`
- Weekly market review generation if it's Friday

**Phase 3-EDITION: Edition Mode Pipeline (the current production mode)**
- Event clustering: `cluster_events()` from `editorial_intelligence.py` — groups same-event coverage
- Corroborating source attachment: `attach_corroborating_sources()`
- Archive check: `archive_matches()` — prevents re-covering already-published transactions
- Pre-enrichment: Fetches full text via `trafilatura` for bounded CRE candidates
- Must-read scoring: `score_event()` — 9-dimension editorial value score
- Selection: `select_edition()` — builds scarce daily portfolio
- Research dossier: `build_research_dossier()` — multi-source evidence ledger
- Editorial room: `run_editorial_room()` — LLM decides format, angle, kill/defer
- Excellence check: `excellence_issues()` — positive-quality ledger validation
- Daily-depth brief contract: ensures full text retrieved, 3+ source-mapped facts, no legal risk

**Phase 4: ENRICH (approx lines 800-1200)**
- Fetches full article text via `trafilatura.fetch_url()` for top candidates
- Extracts NYC addresses
- Enriches normalized stories with additional data

**Phase 5: WRITE (approx lines 1200-2500)**
- `generate_article()`: Makes LLM call to DeepSeek to write the article
  - Uses SYSTEM_PROMPT_ENHANCED and USER_PROMPT_TEMPLATE from `enhanced_prompts.py`
  - Or uses v2 pipeline: `generate_v2_article()` from `v2_editorial.py` (when --pipeline-v2 flag)
  - Calls DeepSeek API with json_mode=True, temperature=0.2, max_tokens dependent on format
  - Requires JSON response with: title, subtitle, slug, category, meta_description, tags, body_html, data_points, sources, excerpt, narrative_ledger, excellence_ledger
  - Internal retry loop: if generation fails or has mechanical headline repetition, retries once
  - Mojiabake check on output
  - Independent quality gate: `_article_control_findings()` checks word count, sections, source validity, boilerplate, paragraph repetition, fact audit, semantic claim audit
  - Near-duplicate detection against `insights.json` (0.86 title similarity threshold)
  - Strips internal ledgers (narrative_ledger, excellence_ledger) from public output — keeps them in `_editorial_control` for the run audit only
  - Slug collision check

**Phase 5b: LINKEDIN ESSAY DESK**
- For each approved article, calls `generate_essay_package()` from `linkedin_essay_agent.py`
- Selects length mode based on editorial format: flagships get "standard", culture_signal gets "edge", brief/data_note get "compressed"
- Quality check: editorial_review status must be "ready_for_review" and publish_ready must be True
- If approved, saves to essay queue via `save_to_queue()`
- Fallback if LLM call fails: generates without API key (template-based)

**Phase 6: PUBLISH (lines 2500-2750)**
- Creates insights/ directory if missing
- For each article:
  - Calls `render_html(article)` to produce the HTML page
  - Mojiabake check on rendered HTML
  - Writes `.html` file to `insights/{slug}.html`
  - Calls `generate_article_image()` for `_social.png` social sharing image
  - Calls `update_manifest(article)` to update `insights.json`
  - Computes related articles by tag overlap (min 2 shared tags), writes `_related.json`
- Rebuilds `feed.xml` (RSS) and `sitemap.xml`
- Generates LinkedIn PDF carousels for non-brief articles
- In edition mode: calls `build_edition_document()`, `save_public_edition()`, `update_event_memory()`, `save_publication_decision()`
- Saves run record to `.editorial-state/runs/YYYY-MM-DD.json`

**Phase 7: DEPLOY & Phase 8: MONITOR**
- Git add + commit + push via `publish_generated.py`
- Or: create editorial review PR for flagship/legal-sensitive work
- Write agent_log.json
- Generate run-summary.md

**Main function flow**:
1. Parse CLI args (--selection-mode, --articles, --daily-target, --shadow, --dry-run, --pipeline-v2, --skip-git, --run-origin)
2. Validate production baseline (py_compile, unit tests, validate_publication.py)
3. Provider preflight via `model_router.py`
4. Schedule guard (only publish if scheduler lease matches)
5. Execute phases 1-8 with checkpoint/wraparound via `run_with_timeout()`
6. If --shadow: score only, no generation, no publication
7. If --dry-run: generate articles but don't write files or git commit
8. Normal mode: full publish pipeline

---

### 2. Pipeline v2 Files — The Modern Multi-Sector Pipeline

#### 2a. `scripts/pipeline_v2.py` (395 lines)
**Role**: The modern multi-sector pipeline entry point. Runs alongside the legacy `daily_news_agent.py` — does not modify it. Can run in shadow mode (no publishing) or preview mode.

**Key Functions**:
- `_now_iso()`: Returns UTC now as ISO string
- `write_candidate_audit()`: Persists every scored candidate with all 10 raw dimension scores to `.editorial-state/candidate-audit.json`. This enables post-hoc auditing of ranking behavior. Selected items are tagged.
- `run_pipeline_v2()`: Orchestrates the full v2 flow:
  1. `fetch_all_sources()` from `ingestion.py` — parallel fetch from all active sources
  2. `classify_batch()` from `classification.py` — multi-label classification
  3. `score_batch()` from `scoring_engine.py` — 10-dimension scoring
  4. `rank_and_select()` from `ranking.py` — per-sector ranking with diversity controls
  5. Writes candidate audit
  6. Returns selected stories per sector

#### 2b. `scripts/ingestion.py` (326 lines)
**Role**: Multi-sector news ingestion. Replaces the monolithic `fetch_rss_stories()` in `daily_news_agent.py` with a config-driven, multi-sector approach.

**Key Functions**:
- `load_sources()`: Loads from `config/sources.json`. Supports both `{"sources": [...]}` and bare `[...]` shapes. Filters active sources only.
- `load_sources_by_sector()`: Groups sources by their primary sector from their config `sectors` list.
- `_parse_entry_date()`: Best-effort ISO 8601 from feedparser entry (tries published_parsed, updated_parsed, falls back to now)
- `_is_recent()`: Checks if published date is within LOOKBACK_HOURS (36 hours). Parses ISO format, handles `Z` suffix.
- `_strip_html()`: Removes HTML tags via regex `<[^>]+>`
- `_truncate_summary()`: Strips HTML, truncates to max_chars (600) at nearest word boundary
- `fetch_single_feed()`: Fetches one RSS feed. Creates `CanonicalItem.from_rss_entry()` for each recent entry. Marks source health as 'ok', 'empty', or 'error'. Returns (items, updated_source, error_string).
- `fetch_all_sources()`: Concurrent fetching via ThreadPoolExecutor (MAX_WORKERS=8 threads). Skips quarantined sources (SourceHealthLedger). Calls `fetch_single_feed()` per source. Returns flat list of CanonicalItem objects.

**Constants**:
- MAX_WORKERS = 8
- LOOKBACK_HOURS = 36
- MAX_ENTRIES_PER_FEED = 500 (not a daily cap — the 36-hour recency filter, not a per-feed limit, determines the candidate universe)

#### 2c. `scripts/canonical_item.py` (233 lines)
**Role**: The unified data model — every story in the pipeline is a typed `@dataclass` with 40+ fields.

**Fields**:
- Identity: item_id, source_name, source_url, canonical_url, headline, publication_date, discovery_date, author
- Content: raw_summary, raw_text, clean_text
- Source metadata: source_type, source_tier (1-5), source_authority (primary/secondary)
- Classification: primary_sector, secondary_sectors, event_type, subsector, classification_confidence, classification_method
- Geography: city, state, country, market, property_address
- Entities: companies, people, buyers, sellers, lenders, developers, government_bodies
- Financial: amounts, square_feet, units, megawatts, percentages
- Scoring: all 10 dimension scores (financial_magnitude_score through cross_sector_impact_score), composite_score, tier
- Timeliness: age_hours() method computes hours since publication_date

**Key Methods**:
- `from_rss_entry()`: Factory that creates a CanonicalItem from a feedparser entry + source config. Sets source tier from config, uses primary sector from source config as prior.
- `generate_id()`: Hashes canonical_url or source_url for unique identity
- `set_scoring()`: Records raw dimension scores, composite, profile, tier
- `set_classification()`: Records sector, event type, subsector, confidence, method

#### 2d. `scripts/intelligence_object.py` (498 lines)
**Role**: Groups multiple articles about the same event into one IntelligenceObject. This is the critical innovation — prevents 3 outlets covering the same $500M acquisition from occupying 3 slots in a 10-story slate.

**Controlled Vocabularies**:
- `ObjectClass`: DISCRETE_EVENT, EVENT_UPDATE, DATA_RELEASE, MARKET_MOVEMENT, TREND, DISCLOSURE, ANALYTICAL_FINDING
- `ContentType`: NEWS_REPORT, PRESS_RELEASE, PRIMARY_DOCUMENT, REGULATORY_FILING, EARNINGS_MATERIAL, DATA_PUBLICATION, RESEARCH_REPORT, INTERVIEW, OPINION

**Key Functions**:
- `normalize_amount()`: Standardizes dollar amounts (removes spaces, normalizes units)
- `extract_entities()`: Pulls companies, people, locations from text
- Event similarity computation using multi-dimensional matching of titles, entities, amounts, markets, asset classes
- `merge_into_object()`: Collapses multiple articles into one IntelligenceObject with source cluster, combined entities, corroboration metadata
- `SCHEMA_VERSION = 1`: Versioned for forward compatibility of persisted objects

#### 2e. `scripts/classification.py` (295 lines)
**Role**: Multi-label sector and event type classification. Assigns primary_sector, secondary_sectors, event_type, subsector, and geography.

**Classification Strategy (3 layers)**:
1. **Source-based priors** (lines 97-167): `_SOURCE_SECTOR_PRIORS` — 70+ source names mapped to primary sectors. E.g., "Commercial Observer" → commercial_real_estate, "PE Hub" → private_equity, "Data Center Dynamics" → data_centers, "Federal Reserve" → fed_macro.

2. **Regex pattern matching** (lines 42-96): `_SECTOR_SIGNALS` — for each sector, a list of compiled regex patterns. Reads both headline and raw_summary. Patterns include:
   - CRE: `multifamily|apartment building|office building|cap rate|occupancy|cmbs|noi|dscr|ltv|refinanc*|bridge loan|construction loan`
   - PE: `buyout|take.private|leveraged buyout|growth equity|sponsor.*exit|fund close|fundraising`
   - Data Centers: `data center|hyperscale|colocation|gpu cluster|power usage effectiveness|pue`
   - Energy: `power plant|solar farm|battery storage|transmission line|ppa|rate base|ferc`
   - Banking: `bank failure|loan.loss reserve|charge.off|fdic.*insured|cease.and.desist|basel|ccar`
   - Fed/Macro: `federal reserve|fomc|federal funds rate|quantitative tightening|sofr|cpi|pce|nonfarm payroll`
   - Local Gov: `city council|planning board|zoning variance|entitlement|tax abatement|pilot agreement|rent control`

3. **Entity recognition** against watchlists (`config/watchlists.json`)

**Scoring**: `_score_signal_matches()` counts pattern matches per sector, returns density (matches / total patterns). Higher density = stronger sector signal.

**Key Functions**:
- `classify_source_prior()`: Returns primary sector based on source name matching (case-insensitive substring match against `_SOURCE_SECTOR_PRIORS`)
- `classify_regex_signals()`: Scores each sector by keyword density in `headline + raw_summary + raw_text`
- `classify_item()`: Full classification pipeline — combines source prior, regex scores, entity matches, and watchlist hits. Assigns primary_sector (highest-score sector), secondary_sectors (other sectors with significant signal), classification_confidence (0.0-1.0), classification_method (source_config_prior, regex, entity_match).
- `classify_batch()`: Classifies a list of items using fallback to LLM for ambiguous cases.
- `get_sector_stats()`: Computes classification statistics per sector.

#### 2f. `scripts/scoring_engine.py` (416 lines)
**Role**: Deterministic scoring on 10 dimensions. NO LLM CALLS. Uses extracted financial values, entity recognition, source quality tiers, timeliness, and cross-sector impact. All scores are 1-10.

**10 Scoring Dimensions**:

1. **financial_magnitude** (lines 147-185): `_score_financial_magnitude()`
   - Extracts dollar amounts from headline + summary via regex `\$\s*([\d,.]+)\s*(million|billion|trillion|mm|bn|m|b)?`
   - Normalizes to actual dollars (million → ×1,000,000; billion → ×1,000,000,000)
   - Sector-specific thresholds: CRE buckets differ from PE/Energy/Data Center buckets
   - For `fed_macro`: scores 6 for FOMC/rate news, 3 otherwise
   - For `data_centers`: bonus points by megawatt scale (≥500MW: +3, ≥200MW: +2, ≥50MW: +1)
   - Extracts megawatts from text via `_extract_megawatts()` using regex

2. **party_significance** (lines 188-207): `_score_party_significance()`
   - Checks if extracted entities (companies + buyers + sellers + lenders + developers) appear in watchlists
   - If no entities found, searches headline + summary text for watchlist companies
   - Watchlist tiers: tier_1_institutions → score 10, tier_2_companies → 7, tier_3_firms → 4, unknown → 1
   - Uses `_get_entity_tier()` which does case-insensitive substring matching against watchlists

3. **market_impact** (lines 210-219): `_score_market_impact()`
   - Base score: 3
   - Pattern bonuses: "record/largest/first/historic/unprecedented" +3, "repric*/reset*/shift*/signal*/trend" +2, "ripple/spillover/contagion/systemic" +3, "federal reserve/fomc/rate hike/rate cut" +4, "bankruptcy/default/insolven*" +3, "industry.wide/market.wide" +2

4. **strategic_relevance** (lines 222-247): `_score_strategic_relevance()`
   - Base score: 3
   - Checks for CRE stakeholder terms (sponsor, developer, lender, borrower, investor, development, construction, refinanc, acquisition) — each +1
   - Checks for capital terms (debt, equity, capital, fund, investment, financing, return, yield, cap rate, valuation, pricing) — each +1
   - Sector bonus: CRE +2, PE/Banking/Fed/LocalGov +1, Data Centers/Energy +0

5. **policy_impact** (lines 250-259): `_score_policy_impact()`
   - Base score: 2
   - Pattern bonuses: Federal Reserve/FOMC +4, Congress/legislation +4, FDIC/OCC/SEC/CFPB +4, regulation/regulatory/compliance +3, zoning/rezoning/land use/entitlement/building code +3, tax change/tariff/subsidy/tax credit +2, Supreme Court/federal court/appeals court/ruling +3

6. **novelty**: Default 7 (requires event memory for real novelty scoring — updated by editorial_intelligence)

7. **source_quality** (lines 262-274): `_score_source_quality()`
   - Maps source_tier to score: tier 1 → 10, tier 2 → 7, tier 3 → 5, tier 4 → 3, tier 5 → 1
   - +2 bonus if source_authority is "primary"

8. **timeliness** (lines 277-293): `_score_timeliness()`
   - Computes story age in hours via `item.age_hours()`
   - Scoring: ≤1hr → 10, ≤6hr → 9, ≤12hr → 8, ≤24hr → 7, ≤48hr → 5, ≤72hr → 3, >72hr → 1

9. **editorial_potential** (lines 296-313): `_score_editorial_potential()`
   - Word count of available text: >2000 words → 10, >1000 → 8, >500 → 6, >200 → 4, else 2
   - Named entity bonus: ≥5 entities +2, ≥2 entities +1

10. **cross_sector_impact** (lines 316-325): `_score_cross_sector_impact()`
    - Count = 1 (primary) + len(secondary_sectors)
    - ≥5 sectors → 10, ≥4 → 8, ≥3 → 6, ≥2 → 4, else 2

**Composite Score** (lines 328-378): `score_item()`
- Applies sector-specific weight multipliers from `config/scoring_profiles.json`
- Weighted average: composite = (weighted_sum / weight_sum) * 10
- Tier assignment:
  - composite ≥ tier_1_must_cover threshold (default 80) → "tier_1_must_cover"
  - composite ≥ tier_2_strongly_recommended (default 65) → "tier_2_strongly_recommended"
  - composite ≥ tier_3_useful_coverage (default 50) → "tier_3_useful_coverage"
  - composite ≥ tier_4_reserve (default 35) → "tier_4_reserve"
  - else → "rejected"

**Batch Processing**:
- `score_batch()`: Clears caches, scores each item, returns scored list
- `get_scoring_stats()`: Computes tier distribution and per-sector average composite

**Caching**: Uses thread-safe cached JSON loading for profiles, thresholds, and watchlists. `_clear_caches()` resets between runs.

#### 2g. `scripts/ranking.py` (296 lines)
**Role**: Within-sector ranking and selection with editorial diversity controls.

**Key Functions**:
- `rank_within_sector()`: Filters items to matching primary_sector and tier != 'rejected'. Sorts by composite_score descending.
- `apply_diversity_controls()`: Enforces editorial diversity:
  - No single subsector exceeds `max_single_subsector_pct` (40%)
  - No single source exceeds `max_single_source_pct` (25%)
  - No single company exceeds `max_single_company_pct` (20%)
  - Minimum `min_subsectors` (3) distinct subsectors
  - When constraints would be violated, lower-ranked items from diverse subsectors/sources replace the excess
- `rank_and_select()`: Full selection pipeline — ranks within each sector, applies diversity, selects top ~30 per sector, handles cross-sector deduplication

---

### 3. `scripts/editorial_intelligence.py` (912 lines)
**Role**: The deterministic editorial brain. Decides whether a reported event deserves attention before an LLM writes about it. Clusters headlines, compares with the published archive, scores editorial value, builds scarce daily portfolios.

**Key Constants**:
- MUST_READ_THRESHOLD = 56 — minimum editorial score for consideration
- FLAGSHIP_CANDIDATE_THRESHOLD = 72 — qualifies for Flagship Analysis
- DEAL_TAPE_THRESHOLD = 34 — minimum for Deal Tape entry
- DAILY_RESEARCH_FLOOR = 24 — minimum for daily-depth research queue
- AUTO_PUBLISH_BRIEF_FLOOR = 24 — minimum for auto-publishable briefs

**FORMAT_SPECS** (lines 40-76): Defines 5 editorial formats:
- `flagship`: Flagship Analysis, 750-1050 words, min 3 independent sources, thesis-led analysis that changes how reader understands the event
- `brief`: Intelligence Brief, 240-430 words, min 1 source, compressed explanation of what changed and what to watch next
- `culture_signal`: Culture of Capital, 300-550 words, min 2 sources, reported look at where money, status, place, policy, and human behavior collide
- `data_note`: One Chart One Argument, 200-400 words, min 1 source, uses primary data release to make one bounded argument
- `deal_tape`: Deal Tape, max 80 words, min 1 source, structured facts and one bounded implication — never a padded standalone essay

**FRANCHISES** (lines 78-103): 6 recurring analytical frames:
- "Credit Committee Theater" — what the structure reveals about the lender's real risk test
- "Five Minutes Before Maturity" — how time, extensions, and refinancing pressure redistribute bargaining power
- "Who Got Paid / Who Got Stuck" — follow the economics through every party
- "What the Press Release Left Out" — separate announcement from constraints and unanswered questions
- "Capital After Dark" — where finance meets status, culture, politics, and city life
- "The Most Expensive Assumption" — identify the premise on which the capital plan quietly depends

**Event Clustering** (lines 150-264):
- `event_similarity()`: Computes 0-1 similarity between two stories using:
  - Title token overlap (stopwords removed, min token length > 2) — weight 0.55
  - Company overlap — weight 0.20
  - Amount overlap — weight 0.15
  - Market overlap — weight 0.05
  - Asset class overlap — weight 0.05
  - Special case: if amounts match AND title similarity ≥ 0.15, uses boosted formula
  - Exact URL match = 1.0 similarity
- `event_fingerprint()`: Creates SHA-256 hash from persistent event features (title tokens appearing in ≥50% of members, companies, amounts, markets, assets) — 20-char hex digest
- `_event_from_members()`: Orders members by source tier, authority, summary length. Picks best candidate as primary. Counts independent domains.
- `cluster_events()`: Greedy clustering with threshold=0.61. For each candidate, finds best-matching existing cluster or creates new one.
- `attach_corroborating_sources()`: Attaches matching stories from the wider feed pool without admitting new events. Filters by domain uniqueness, caps at 5 sources. Sorts by similarity and source tier.

**Archive Matching** (lines 344-443):
- `archive_matches()`: Finds earlier Light Tower stories covering the same event or arc.
  - Compares title tokens, context tokens, dollar amounts, street addresses, company entities
  - Same-event detection: title token overlap ≥ 0.57, or amount overlap + context ≥ 0.16, or address overlap + context ≥ 0.14, or entity overlap + context ≥ 0.24, or context only ≥ threshold
  - Multi-dimensional scoring combining title, context, amount, address, and entity signals
  - `_archive_is_recent()`: Checks if candidate and archive record dates are within 7 days
  - Returns top 5 matches sorted by similarity with recent/published flags

**Event Scoring** (lines 498-599): `score_event()` — 9 dimensions:
1. **Consequence** (max 15): Material transaction +5, material operating signal +4, big number +3, distress/bank_credit/fed_rates/policy topics +5, billion-scale language +3
2. **Novelty** (max 15): Regex patterns for "first/largest/record/historic/rare/unexpected/reverses/collapse/bankruptcy", cross-source bonus +3
3. **Conflict and Power** (max 15): Default/foreclosure/bankruptcy/lawsuit/litigation patterns, distress/government_action topics +4
4. **Explanatory Value** (max 15): Base 3 + topics×2, bonus for "because/pressure/maturity/liquidity/insurance/power/constraint" +3
5. **Cultural Relevance** (max 10): culture_dimensions×3 (sports, entertainment, technology, status, cities, climate, politics)
6. **Human Stakes** (max 10): Human pattern match → 8, +2 if also policy/government/distress topics
7. **Evidence Depth** (max 10): Source quality scoring from tiers, primary sources, source count
8. **Light Tower Right to Win** (max 10): Topic alignment with LTG expertise (capital placement, CMBS, private credit, bank credit, distress +5; markets, asset classes +2/+3)
9. **Conversation** (max 10): Derived from conflict + cultural relevance + novelty

**Penalties**:
- **Routine penalty** (18 points): Deducted for formulaic transaction announcements (e.g., "provides $X million loan", "signs X sq ft lease", "acquires Y for $Z") unless they have distress/policy/government topics or cultural dimensions
- **Archive repeat penalty** (up to 18): Recent same-event match → 18; otherwise 9 per published prior + 3 per recent memory match

**Selection** (lines 600-912):
- `select_edition()`: Builds a deliberately scarce daily portfolio
  - Filters by MUST_READ_THRESHOLD
  - Separates into tiers: must-cover, strongly recommended, useful
  - Applies editorial diversity (no single topic dominance)
  - Assigns formats based on score and evidence
  - Targets DEFAULT_DAILY_ARTICLE_TARGET = 3 publishable pieces, researches up to 5
  - Extra research capacity absorbs source failure, duplication, editorial kills
  - Deal Tape entries never become padded article pages
- `print_edition_report()`: Human-readable summary of selections, scores, formats, evidence levels

---

### 4. `scripts/editorial_room.py` (352 lines)
**Role**: The assigning editor and skeptic. Uses LLM to decide format, angle, kill/defer/shorten each candidate. Has a deterministic fallback.

**EDITORIAL_CONSTITUTION** (line 14-19): The guiding principle — "Light Tower publishes only when it can make a smart reader see a capital decision differently. Accuracy is the floor. The work must add consequence, mechanism, human or institutional stakes, candor, and a bounded point of view."

**`deterministic_room_plan()`** (lines 42-84):
- Used when LLM is unavailable or format is Deal Tape
- Downgrades flagship to brief if longform not allowed
- Downgrades culture_signal to brief if <2 independent sources
- Forces deal_tape if evidence_level is "insufficient"
- Sets default angle from franchise promise or generic constraint-focused angle
- Sets skeptic objections: don't claim market-wide shift from one transaction, don't infer unreported motives

**`_daily_depth_brief_is_supported()`** (lines 86-107):
- Validates daily-depth brief contract requirements:
  - selection_tier must be "daily_depth"
  - No legal or allegation risk
  - Evidence level not "insufficient"
  - At least 1 usable full text
  - At least 3 reported facts
  - No hard-stop patterns in kill_reason/reporting_gaps/skeptic_objections (allegations, lawsuits, criminal, fraud, indicted, legal risk, conflicting facts, source authenticity, fabricate, cannot verify, unsupported claims, duplicate)

**`run_editorial_room()`** (lines 110-352):
- First tries deterministic plan; if deal_tape, returns it immediately
- Calls DeepSeek LLM with the editorial room system prompt + current slate context
- Returns: decision (write/shorten/kill/deal_tape), final_format, angle, why_now, skeptic_objections, reporting_gaps, human_stakes, concrete_detail, kill_reason, generation_mode
- CRITICAL GUARD: For daily-depth briefs, checks `_daily_depth_brief_is_supported()` — if LLM says "kill" but deterministic contract says "supported", the deterministic plan overrides. "The editorial-room model cannot turn single-source status or missing human stakes into an automatic veto when the deterministic record contains ≥1 full text and ≥3 source-mapped facts."

**`excellence_issues()`**: Positive-quality ledger checks — validates the excellence_ledger has all required fields (why_now, original_inference, counterargument, concrete_detail, human_stakes, reader_value, memorable_line, claim_evidence).

---

### 5. `scripts/editorial_pipeline.py` (916 lines)
**Role**: The 7-stage article generation pipeline. Mixes deterministic and LLM stages. Each stage produces verifiable output.

**`EditorialPipeline` class**:
- `__init__()`: Stores api_key, provider dict, stages_run list, errors list

**Stage 1: Analytical Brief** (`stage_analytical_brief()`, lines 36-56):
- **Deterministic**: Calls `build_analytical_brief()` from `analytical_brief.py` — structured pre-writing analysis from the dossier
- **LLM Enhancement** (optional): If api_key is available, calls `enhance_brief_with_llm()` — adds deeper analytical framing, identifies unasked questions, sharpens the thesis

**Stage 2: Assemble Writing Prompt** (`stage_assemble_prompt()`, lines 58-213):
- Loads sector-specific system prompt via `get_sector_prompt()` from `generation.py`
- Builds a rich user prompt containing:
  - STORY: headline, source name, source tier, sector
  - SOURCE DOSSIER: the complete evidence boundary (truncated to 24,000 chars)
  - ANALYTICAL BRIEF: central question, core tension, thesis, parties and incentives, transaction economics, key numbers, important unknowns
  - ARTICLE STRUCTURE: from `article_architecture`
  - EDITORIAL FORMAT: format label
  - HARD LENGTH CONTRACT: e.g., "240-430 words"
  - WRITING INSTRUCTIONS: 12 rules — open with most revealing fact, build around central question/thesis, interpret numbers (don't list), name parties and incentives, distinguish facts from inferences from unknowns, vary sentence rhythm, don't use "signals/highlights/underscores/showcases", every claim must be supported by dossier, label calculations and inferences, sources array must contain canonical dossier URLs only, never mention internal scores in public copy
  - OUTPUT FORMAT: Exact JSON schema with public fields + internal control ledgers (narrative_ledger, excellence_ledger)

**Stage 3: Draft** (`stage_draft()`, lines 215-243):
- Calls DeepSeek with max_tokens=8000, temperature=0.2, json_mode=True
- Extracts JSON from response via `_extract_json()` with required_fields check: body_html, title, excerpt, sources, excellence_ledger
- Validates sources array is non-empty

**Stage 4: Financial Review** (`stage_financial_review()`, lines 245-336):
- Opens a NEW LLM call (not self-review — a separate prompt)
- Checks: are financial figures correct? Does article explain what numbers MEAN? Are return/valuation claims supported? Does it distinguish facts from calculated metrics? Is incentive analysis clear?
- CALIBRATION RULES (lines 292-308): Judge against what the dossier actually discloses, not an imagined underwriting file. For briefs, one credible source can support a bounded article. Don't fail for undisclosed loan pricing, returns, or valuations — fail if the article invents them. A reported claim may be attributed to its named publication.
- Returns: issues list, passed (boolean), score_1_10, summary

**Stage 5: Editorial Review** (`stage_editorial_review()`, lines 338-385):
- Another independent LLM call
- Checks: opening quality (specific hook vs generic), logical flow (not formulaic template), sentence variety, AI language detection ("signals", "highlights", "underscores", "showcases"), conclusion quality (implication, not vague forward look), voice (knowledgeable professional, not institution)
- Returns: issues, passed, score_1_10, opening_quality, worst_sentence, summary

**Stage 6: Fact Verification** (`stage_fact_verification()`, lines 387-477):
- DETERMINISTIC — no LLM. The independent verification layer.
- Checks: research dossier has canonical source URLs, article sources all present in dossier URLs, key numbers from brief appear in article
- Scans for unsupported claim phrases: "is expected to", "analysts predict", "sources say", "widely viewed as", "market believes"
- Calls `audit_article_facts()` from `fact_extractor.py` — extracts amounts, companies, addresses from article body and cross-references against source facts from the dossier
- Flags: unmatched amounts, unmatched companies, unmatched addresses — all with surrounding context

**Stage 7: Final Revision** (`stage_final_revision()`, lines 479-554):
- Only runs if there are issues from financial review, editorial review, or fact verification
- Calls DeepSeek with ALL issue lists + original article JSON + source dossier
- Instructions: fix every issue, keep source-grounded facts, delete unsupported claims when no valid replacement, don't introduce new unsupported claims, maintain evidence-bounded thesis and word contract
- Returns revised article (merged with original for any missing fields)

**`run()`** (lines 556-700):
- The full pipeline execution: runs all 7 stages in sequence
- Handles skipped stages (no LLM available), failed stages
- Status tracking: each stage records status in result["stages"]
- Final article stored in result["article"]
- If any required stage fails, marks status accordingly

---

### 6. `scripts/research_dossier.py` (236 lines)
**Role**: Builds source-grounded research dossiers before any article is written. Creates an evidence ledger from every independent source in an event.

**Key Functions**:
- `_sentences()`: Splits text into sentences, filters to 7-55 word sentences (meaningful units)
- `_fact_candidates()`: Extracts fact-bearing sentences — those containing dollar amounts, percentages, years, reported/said/announced/filed/approved/acquired/sold/borrowed/lent/matures/occupancy/units/square feet
- `_quotes()`: Extracts quoted text (between curly or straight quotes, 20-280 chars)
- `_independent_domain()`: Extracts netloc from URL, strips "www."
- `_archive_context()`: Finds related prior coverage from the published archive by title token overlap and tag overlap
- `build_research_dossier()`: THE MAIN FUNCTION
  1. Iterates editorial_event["sources"]
  2. For each source: fetches full text (from fetched_text_by_url cache), sanitizes (removes instruction-like text via `sanitize_untrusted_source()`), extracts facts (up to 8) and quotes (up to 3)
  3. Builds source entry with: name, url, domain, published date, authority, tier, summary, full_text_excerpt (first 6500 chars), reported_facts, quotes
  4. Compiles global arrays: reported_facts, quote_ledger
  5. Computes:
     - `independent_source_count`: unique domains
     - `primary_sources`: authority="primary" sources
     - `usable_full_text_count`: sources with non-empty full_text_excerpt
     - `evidence_level`: "deep" (≥3 independent + ≥2 full text), "adequate" (≥2 independent or have primary source), "thin" (≥1 source), "insufficient" (none)
  6. Checks `longform_allowed`: requires "deep" or "adequate" evidence level
  7. Computes `reporting_gaps`: missing financial figures, missing party identities, missing market context
- `dossier_prompt_payload()`: Serializes the dossier for inclusion in LLM prompts, with max_chars truncation
- `dossier_audit_payload()`: Serializes for audit/verification purposes

---

### 7. `scripts/editorial_scoring.py`
**Role**: LLM-based must-read scoring and weekly market review. Uses DeepSeek to evaluate editorial quality.

**Key Functions**:
- `call_deepseek()`: The central LLM call function — sends prompt to DeepSeek API, handles retries, parses response
- `daily_top_news_selection()`: Legacy mode — LLM ranks stories by capital markets impact (30 pts), NYC relevance (25 pts), deal scale (20 pts), originality (15 pts), timeliness (10 pts)
- `generate_weekly_market_review()`: Synthesizes a week of editorial runs into a market review

---

### 8. `scripts/v2_editorial.py` (401 lines)
**Role**: Production bridge from v2 multi-sector selection to the editorial publishing pipeline. Converts typed v2 candidates into the research-dossier contract and invokes the 7-stage editorial pipeline.

**Key Functions**:
- `canonical_source_url()`: Returns the best canonical article URL from a CanonicalItem
- Legal risk detection: regex for "allegation/alleged/lawsuit/litigation/fraud/indicted/criminal/charged/investigation/sanction"
- Non-editorial format rejection: regex for "test drive, hands-on, product review, car review, unboxing, buyer's guide, how to, podcast, webinar, photo gallery, sponsored content" — these are consumer/tech content, not financial editorial
- Capital or policy anchor verification: regex checks that the story contains financial/policy terms (acquired, buyout, loan, debt, credit, equity, financing, development, construction, project, federal reserve, interest rates, inflation, regulation, policy, subsidy, tax, tariff)
- Sector article anchors: per-sector regex to verify story is actually about that sector
- `generate_v2_article()`: THE MAIN FUNCTION
  1. Creates `EditorialPipeline` instance
  2. Calls `pipeline.run(item, dossier=dossier, api_key=api_key)`
  3. Extracts article from the pipeline result
  4. Returns article dict compatible with the existing renderer in `daily_news_agent.py`
  5. Handles all error cases, returns None on failure

---

### 9. `scripts/generation.py` (439 lines)
**Role**: Sector-aware article generation routing. Maps classified/scored stories to the appropriate writing prompt based on primary sector.

**SECTOR_PROMPTS** (lines 27-35): Maps sector keys to system prompt variables:
- private_equity → PE_SYSTEM_PROMPT
- data_centers → DC_SYSTEM_PROMPT
- energy → ENERGY_SYSTEM_PROMPT
- banking_credit → BANKING_SYSTEM_PROMPT
- fed_macro → FED_SYSTEM_PROMPT
- local_government → LOCALGOV_SYSTEM_PROMPT
- commercial_real_estate → SYSTEM_PROMPT_ENHANCED (from enhanced_prompts.py)

**SECTOR_LABELS** (lines 37-45): Human-readable names for each sector.

**SECTOR_CATEGORIES** (lines 47-55): Maps sectors to article categories:
- private_equity → "Deal Intelligence"
- data_centers → "Market Analysis"
- energy → "Market Analysis"
- banking_credit → "Debt & Equity"
- fed_macro → "Policy & Regulation"
- local_government → "Policy & Regulation"
- commercial_real_estate → "Capital Markets"

**ARTICLE_TYPES** (lines 59-100): 60+ event_type → article_format mappings:
- PE: fund_close → fundraising_analysis, buyout → transaction_brief, exit_sale → exit_analysis, continuation_vehicle → transaction_brief, gp_stake_sale → transaction_brief, take_private → transaction_brief, growth_equity → transaction_brief, add_on_acquisition → deal_analysis
- Data Centers: dc_development → development_brief, dc_lease → lease_analysis, dc_acquisition → deal_analysis, dc_power_agreement → energy_brief
- Energy: power_agreement → energy_brief, project_finance → deal_analysis, ppa_signing → energy_brief, plant_development → development_brief, regulatory_decision → policy_analysis, rate_case → policy_analysis, interconnection_approval → energy_brief
- Banking: bank_earnings → data_note, loan_origination → transaction_brief, loan_sale → deal_analysis, credit_event → deal_analysis, regulatory_action → policy_analysis, enforcement_action → policy_analysis, private_credit_deal → transaction_brief
- Fed/Macro: fomc_decision → macro_brief, fomc_minutes → macro_brief, inflation_report → data_note, employment_report → data_note, gdp_report → data_note
- CRE-specific: property_acquisition → deal_analysis, refinancing → transaction_brief, construction_financing → development_brief, development_financing → development_brief, foreclosure → distress_brief, receivership → distress_brief, note_sale → transaction_brief, major_lease → lease_analysis, rezoning → policy_analysis

**Key Functions**:
- `get_sector_prompt()`: Returns the appropriate system prompt for a given sector key
- `get_sector_label()`: Returns human-readable sector name
- `get_sector_category()`: Returns the category for a given sector
- `get_article_type()`: Maps event_type → article_format
- Full generation statistics tracking

---

### 10. `scripts/content_governance.py` (217 lines)
**Role**: THE SAFEGUARDS. Deterministic controls that NEVER call an LLM. The independent control layer around model output — source material is treated as untrusted, repetitive stories are caught, generic fallback writing cannot pass as finished editorial work.

**Key Functions**:
- `html_to_text()`: Custom HTMLParser that extracts readable text, collapses whitespace
- `sanitize_untrusted_source()`: Removes instruction-like text from retrieved articles before prompting. Uses PROMPT_INJECTION_RE patterns:
  - "ignore all previous instructions"
  - "disregard prior instructions"
  - "forget previous instructions"
  - "system prompt", "developer message"
  - "reveal your instructions"
  - "act as a different assistant"
- `normalise_title()`: Strips non-alphanumeric, lowercases, collapses whitespace
- `_token_similarity()`: Jaccard similarity of normalized title tokens
- `near_duplicate_matches()`: Checks new title against existing records using SequenceMatcher ratio and token similarity. Threshold 0.86 for sequence, 0.82 for tokens.
- `load_json_records()`: Parses JSON records from files, handling both array and object shapes
- `load_insight_records()`: Loads `insights.json` as list of published article records
- `load_idea_records()`: Loads published Ideas from `data/ideas/published/*.json`

**`independent_quality_issues()`** (lines 117-217): THE MAIN QUALITY GATE
- **Fallback writing check**: If generation_mode ends with "fallback" or source_notes mentions "deterministic fallback" → hold for review
- **Word count checks**: Format-specific minimums (flagship: 725, brief: 215, culture_signal: 275, data_note: 175) and maximums (flagship: 1100, brief: 475, culture_signal: 625, data_note: 450)
- **Section structure**: Requires at least 2 `<h2>` sections (for full articles)
- **Boilerplate detection**: Checks for GENERIC_EDITORIAL_RE patterns — "the headline is therefore a doorway", "buildings are where private capital", "the capital question is simple and difficult", "the built world is not merely the background"
- **Voice quality**: Calls `editorial_quality_issues()` from `editorial_voice.py`
- **Source validation**: Article must have non-empty sources array with valid https:// URLs. Rejects "example.com" fixture sources.
- **Paragraph repetition detection**: If ≥4 paragraphs and unique paragraphs / total paragraphs < 0.9 → flag repeated structure
- **Fact audit** (lines 180-195): If research_dossier has source_facts, calls `audit_article_facts()` from `fact_extractor.py`. Flags unmatched amounts, companies, addresses. Sets `_fact_audit` on article.
- **Semantic claim audit** (lines 197-215): If narrative_ledger has a `claim` field AND dossier has source texts, calls `audit_claim_semantic()` from `fact_extractor.py`. Checks that article's central claim is semantically supported by source texts. Flags unsupported assertions with confidence scores.

---

### 11. `scripts/fact_extractor.py` (264 lines)
**Role**: Deterministic fact extraction for editorial verification. Extracts structured facts from source text and generated articles so claims can be traced to specific source sentences. ZERO LLM calls.

**Key Functions**:
- `extract_amounts()`: Regex `\$\s*([\d,.]+)\s*(million|billion|trillion|mm|bn|m|b)?` — extracts dollar amounts with 60-char surrounding context
- `extract_percentages()`: Regex `([\d,.]+)\s*(%|percent|bps|basis points)` — extracts percentages and basis points with 40-char context
- `extract_companies()`: Matches against `_KNOWN_INSTITUTIONS` — a hardcoded list of 60+ CRE/finance institutions (Blackstone, Brookfield, Apollo, Starwood, Ares, KKR, Carlyle, TPG, SL Green, Vornado, Related, Tishman, JPMorgan, Goldman, CBRE, JLL, Cushman, Eastdil, Newmark, Meridian, Walker & Dunlop, Berkadia, Northmarq, Greystone, KeyBank, PNC, M&T Bank, etc.). Case-insensitive matching.
- `extract_addresses()`: Regex for US street addresses — `\d{1,5}\s+(?:west|east|north|south|w|e\s+)?[a-z0-9'-]+(?:\s+[a-z0-9'-]+){0,2}\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|terrace|place)`
- `audit_article_facts()`: Cross-references article body against source facts:
  1. Extracts amounts, companies, addresses from article body
  2. Compares against source facts from the dossier
  3. Flags unmatched amounts (article claims dollar figures not in sources)
  4. Flags unmatched companies (article mentions companies not in sources)
  5. Flags unmatched addresses (article references addresses not in sources)
  6. Generates `hold_for_review` flag based on source_tier thresholds
  7. Returns structured audit result with matched/unmatched lists and context
- `audit_claim_semantic()`: Verifies that article's central claim is semantically supported by source texts:
  1. Breaks claim into individual assertions
  2. Checks each assertion against source texts using keyword matching and semantic indices
  3. Returns: claim_supported (boolean), confidence (0-1), assertions_missing (list), assertions_found (list)

---

### 12. `scripts/editorial_store.py` (57 lines)
**Role**: Persistence for editorial scoring audits and weekly reviews. All stored in `.editorial-state/`.

**Key Functions**:
- `save_editorial_run()`: Writes run payload to `.editorial-state/runs/YYYY-MM-DD.json`
- `load_editorial_run()`: Reads a single run file
- `load_weekly_editorial_runs()`: Loads 5 runs (Monday-Friday) for the given week
- `save_weekly_review()`: Writes weekly review to `.editorial-state/weekly-reviews/YYYY-MM-DD.json`

---

### 13. `scripts/edition_manager.py` (293 lines)
**Role**: Creates the public daily edition and durable editorial operating record. Manages `editions/`, `latest-edition.json`, event memory, generated files manifest, and publication decisions.

**Key Functions**:
- `calculate_read_time()`: Words / 225 (average reading speed), min 1 minute
- `_article_summary()`: Creates compact article summary for edition JSON — event_id, title, subtitle, slug, url, category, format, format_label, franchise, must_read_score, selection_tier, read_time, source_count (unique domains)
- `_deal_tape_summary()`: Creates Deal Tape entry from editorial selection data
- `build_edition_document()`: THE MAIN FUNCTION — constructs the full edition document:
  1. Article summaries from generated articles
  2. Deal Tape entries from editorial selection
  3. Editorial metadata (date, status, thresholds, production window)
  4. Distribution readiness flags
- `save_public_edition()`: Writes edition to `editions/YYYY-MM-DD.json` and `latest-edition.json`
- `update_event_memory()`: Updates `.editorial-state/event-memory.json` with events from this run
- `save_publication_decision()`: Writes `.editorial-state/publication-decision.json` — whether auto-publish or review required
- `render_run_summary()`: Generates `.editorial-state/run-summary.md` — human-readable markdown summary
- `save_run_record()`: Writes full run record to `.editorial-state/runs/`
- `write_generated_files()`: Creates `.editorial-state/generated-files.json` manifest — lists every file path created by this run

---

### 14. `scripts/bucketed_editorial.py` (359 lines)
**Role**: Volume-oriented editorial routing. Every distinct, relevant story is routed to its proper editorial lane. Deliberately has no category quota or final ranking cap.

**BUCKETS** (5 lanes):
- `cre_capital_markets`: Refinancing, bridge loans, construction loans, mortgages, debt funds, CMBS, special servicing, defaults, workouts
- `cre_transactions_development`: Acquisitions, purchases, sales, leasing, development, groundbreaking, approvals, permits, conversions, rezoning
- `banking_credit`: Banks, loan losses, charge-offs, credit standards, capital ratios, CRE exposure, FDIC, OCC
- `private_equity_private_capital`: PE, private capital, fundraising, fund closes, institutional allocators, pension funds, sovereign wealth, family offices, JVs
- `policy_rates_public_markets`: Federal Reserve, Treasury, rate cuts/hikes, SOFR, FOMC, CPI, GDP, fiscal policy

**Key Functions**:
- `bucketed_volume_selection()`: Routes every qualifying story to its bucket, scores per bucket
- `route_story()`: Pattern-matches a story against bucket patterns
- `print_bucketed_volume_report()`: Reports per-bucket selection counts and scores

**Constants**:
- PUBLISH_SCORE = 65 (minimum for auto-publish)
- REVIEW_SCORE = 55 (minimum for editorial review)

---

### 15. `scripts/story_normalizer.py`
**Role**: Story normalization, CRE relevance validation, financial amount threshold checking.

**Key Functions**:
- `normalize_stories()`: Normalizes raw story dicts — strips HTML, extracts entities, standardizes formatting
- `enrich_normalized_story()`: Fetches full text via trafilatura, extracts additional data (addresses, amounts, parties)
- `has_cre_editorial_anchor()`: Checks if story has enough CRE-specific content to warrant coverage
- `has_reported_amount_at_least_ten_million()`: Validates minimum deal size threshold

---

### 16. `scripts/agent_runtime.py` (146 lines)
**Role**: Local scheduler that reads the `scheduler.json` lease and only publishes if the lease matches.

**Key Functions**:
- `local_scheduler_enabled()`: Reads `.editorial-state/scheduler.json`, checks if `active_scheduler` == "local-scheduler"
- `preflight()`: Git preflight checks:
  1. Working tree must be clean (`git status --porcelain`)
  2. Fetch origin/main
  3. Compare HEAD with origin/main
  4. Actions: "current" (equal), "recover_push" (HEAD ahead — push), "fast_forward" (HEAD behind — merge), "diverged" (raise error)
  5. After sync, verify HEAD matches origin/main
- `git()`, `git_text()`: Subprocess wrappers for git commands
- `write_status()`: Writes operational metadata to `tmp/agent_status.json` (NEVER includes command output or secrets)
- `main()`: Runs preflight, checks scheduler lease, executes `daily_news_agent.py` with AGENT_ARGS, writes status

---

### 17. `scripts/publish_generated.py` (93 lines)
**Role**: Safely publishes only files declared by the generation manifest.

**Key Functions**:
- `load_files()`: Reads `.editorial-state/generated-files.json`:
  1. Validates manifest structure
  2. Security check: no absolute paths, no `..` traversal, no `.git/` paths
  3. Resolves paths relative to SITE_ROOT
  4. Verifies every declared file exists
  5. Deduplicates paths
  6. Adds `generated-files.json` itself to the list
- `main()`:
  1. Loads manifest
  2. Dry run: prints files list, exits
  3. `git add --` all declared files
  4. `git commit -m "Publish curated Insights edition"`
  5. `git push origin {branch}` (default: main)
  6. Error handling: if push fails, attempts pull --rebase and retry

---

### 18. `scripts/social_image_generator.py`
**Role**: Generates branded social sharing images for every article.

**Key Functions**:
- `generate_article_image()`: Creates a `_social.png` image with:
  1. Branded background (navy/gold)
  2. Article title text (wrapped to fit)
  3. Subtitle text
  4. Light Tower Group logo/mark
  5. PyTorch/Pillow-based image composition

---

### 19. LinkedIn Distribution Suite

#### `scripts/linkedin_essay_agent.py`
**Role**: Generates LinkedIn essay packages from articles. Produces: linkedin_essay (full post), first_comment (expanded context), voice_mode, quality_score, editorial_review.

**Key Functions**:
- `generate_essay_package()`: Calls DeepSeek to create LinkedIn-native content:
  1. Length modes: "standard" (flagship), "edge" (culture_signal), "compressed" (brief/data_note)
  2. Returns structured package with publish_ready flag
  3. Fallback (no API key): template-based package generation
- `save_to_queue()`: Appends package to `linkedin_essay_queue.json`

#### Other LinkedIn files:
- `build_linkedin_post.py`: Formats article data into LinkedIn post templates
- `linkedin_thread_agent.py`: Creates multi-post LinkedIn threads
- `linkedin_pdf_scheduler.py` / `linkedin_pdf_post.py`: Schedules and posts PDF carousels
- `linkedin_auth.py`: OAuth token management
- `linkedin_engagement_scraper.py`: Collects post engagement metrics

---

### 20. `scripts/article_adapter.py` (862 lines)
**Role**: Transforms article HTML into LinkedIn-native carousel card decks.

**Key Functions**:
- `clean_text()`: HTML unescape, strip tags, collapse whitespace
- `sentences_from_paragraphs()`: Splits paragraphs into sentences (8-42 words), filters short/long
- `compact()`: Truncates text to char limit at word boundary
- TENSION_WORDS: "debt", "risk", "pressure", "default", "foreclosure", "distress" — used to score sentences for carousel prominence
- ANALYSIS_WORDS: "signals", "reveals", "means", "shows", "demonstrates" — used to score analytical depth
- Produces: slide deck JSON with title slide, tension slides, analysis slides, conclusion slide

---

### 21. `scripts/validate_publication.py`
**Role**: Pre-deployment validation of ALL public assets before Git push.

**Key Functions**:
- Validates HTML files: well-formed, no broken images, no placeholder text
- Validates `insights.json`: valid JSON, all entries have required fields
- Validates `feed.xml`: valid RSS/Atom, all entries have required elements
- Validates `sitemap.xml`: valid XML, all URLs resolve
- Validates `latest-edition.json` and `editions/` files: valid JSON, correct schema
- Validates no internal secrets in public files

---

### 22. `scripts/model_router.py`
**Role**: Provider preflight — verifies the configured LLM provider is reachable before generation.

**Key Functions**:
- Tests API connectivity to DeepSeek
- Validates API key format
- Reports model availability and token limits
- Used by GitHub Actions before the editorial run

---

### 23. `scripts/cost_tracker.py`
**Role**: Tracks API costs across runs.

**Key Functions**:
- `get_costs()`: Returns cumulative costs for current session
- `reset_costs()`: Resets cost tracking
- Tracks: DeepSeek API tokens in/out, NewsAPI calls, estimated dollar costs

---

### 24. `scripts/checkpoint.py`
**Role**: Checkpoint save/validate for resumable long pipeline runs.

**Key Functions**:
- `run_with_timeout()`: Wraps pipeline phases with timeout protection
- `clear_checkpoints()`: Removes stale checkpoint data
- `PHASE_TIMEOUTS`: Per-phase timeout configurations

---

### 25. Ideas Pipeline Files
- `ideas_generator_2026.py` (449 lines): Scouts CRE/built-world stories, scores against 10-dimension Ideas rubric, produces Daily Ten drafts
- `ideas_daily_agent.py`: Daily orchestrator
- `ideas_prompts.py`: Writing prompts
- `ideas_quality.py`: Quality gates
- `ideas_renderer.py`: HTML page rendering

---

### 26. `config/sources.json` (5094 lines)
150+ news sources across 7 sectors. Each source has: name, url, sectors[], tier (1-5), fetch_frequency_hours, auth_required, js_required, full_text_available, geographic_scope, source_type, active status, health tracking.

### 27. `config/sectors.json` (40 lines)
7 sectors with subsectors and event types. CRE has 30 subsectors (multifamily, industrial_logistics, office, retail, hospitality, etc.) and 30 event types.

### 28. `.github/workflows/daily-insights-agent.yml` (212 lines)
Production workflow: schedule guard → Python 3.11 setup → dependency install → validate baseline (compile + unit tests + JS checks) → provider preflight → build curated edition → validate → write run summary → upload artifacts (30-day retention) → resolve auto-publish vs review → push to main or open PR.

---

## THE COMPLETE DATA FLOW (Step by Step)

```
START: GitHub Actions triggers at 07:07 NY time
│
├─1. SCHEDULE GUARD: resolve_schedule_policy.py checks DST-correct time
│
├─2. PREFLIGHT: validate baseline (py_compile all .py, unit tests, JS syntax, validate_publication)
│
├─3. PROVIDER CHECK: model_router.py pings DeepSeek API
│
├─4. INGESTION:
│   ├─ load sources.json → 150+ active sources
│   ├─ fetch_all_sources() → parallel feedparser (8 threads)
│   ├─ Each entry → CanonicalItem (typed dataclass)
│   ├─ Source health tracking → .editorial-state/source-health.json
│   └─ Output: ~80-150 CanonicalItem objects
│
├─5. PIPELINE V2 (when --pipeline-v2):
│   ├─ classify_batch() → classification.py
│   │   ├─ Source-based prior (70+ known source→sector mappings)
│   │   ├─ Regex signal scoring (7 sector pattern sets)
│   │   └─ Entity recognition via watchlists
│   ├─ score_batch() → scoring_engine.py
│   │   ├─ 10 dimension scores (financial_magnitude through cross_sector_impact)
│   │   ├─ Sector-specific weight profiles applied
│   │   ├─ Composite score (0-100) computed
│   │   └─ Tier assignment (tier_1 through rejected)
│   └─ rank_and_select() → ranking.py
│       ├─ Within-sector ranking by composite
│       ├─ Diversity controls (subsector≤40%, source≤25%, company≤20%)
│       └─ Per-sector slates (~30 stories each)
│
├─6. EDITION MODE (current production):
│   ├─ cluster_events() → group duplicate coverage into distinct events
│   ├─ attach_corroborating_sources() → add matching stories from wider pool
│   ├─ archive_matches() → check against published archive (prevent repeats)
│   ├─ Pre-enrichment → fetch full text via trafilatura for top CRE candidates
│   ├─ score_event() → 9-dimension editorial value score
│   ├─ select_edition() → build scarce daily portfolio (target 3 pieces)
│   ├─ build_research_dossier() → multi-source evidence ledger per event
│   │   ├─ Fetch full text for every independent source
│   │   ├─ Extract fact sentences ($ amounts, %, reported/said/announced)
│   │   ├─ Extract quotes (curly+straight quotes, 20-280 chars)
│   │   ├─ Compute evidence_level (deep/adequate/thin/insufficient)
│   │   └─ Compile source_facts array for fact verification
│   ├─ run_editorial_room() → LLM assigns format/angle/kill/defer
│   │   ├─ Deterministic fallback plan
│   │   ├─ LLM editorial plan (format, angle, why_now)
│   │   └─ Daily-depth brief override guard (deterministic wins if supported)
│   └─ excellence_issues() → positive-quality ledger validation
│
├─7. ARTICLE GENERATION (per selected event):
│   ├─ generate_v2_article() → v2_editorial.py
│   │   └─ EditorialPipeline.run()
│   │       ├─ Stage 1: Analytical Brief (deterministic + LLM-enhanced)
│   │       ├─ Stage 2: Assemble Writing Prompt (sector-specific system prompt + dossier + brief)
│   │       ├─ Stage 3: Draft (LLM: DeepSeek, json_mode, temp 0.2, max_tokens 8000)
│   │       ├─ Stage 4: Financial Review (LLM: separate prompt, checks figures/claims)
│   │       ├─ Stage 5: Editorial Review (LLM: separate prompt, checks writing quality)
│   │       ├─ Stage 6: Fact Verification (DETERMINISTIC: cross-ref article vs dossier)
│   │       │   ├─ Source URL validation (article sources must match dossier URLs)
│   │       │   ├─ Key number checking (brief numbers appear in article)
│   │       │   ├─ Unsupported claim detection ("analysts predict", "sources say")
│   │       │   └─ audit_article_facts() → match amounts, companies, addresses
│   │       └─ Stage 7: Final Revision (LLM: incorporates all review feedback)
│   │
│   ├─ independent_quality_issues() → content_governance.py
│   │   ├─ Fallback writing hold
│   │   ├─ Word count checks (format-specific min/max)
│   │   ├─ Section structure (≥2 h2)
│   │   ├─ Boilerplate detection
│   │   ├─ Source validation (no example.com, must have https://)
│   │   ├─ Paragraph repetition (<0.9 unique ratio)
│   │   ├─ Fact audit (cross-ref against dossier source_facts)
│   │   └─ Semantic claim audit (central claim vs source texts)
│   │
│   ├─ near_duplicate_matches() → check against published articles (86% threshold)
│   └─ Mojiabake check → assert no encoding damage
│
├─8. RENDER & PUBLISH:
│   ├─ render_html(article) → HTML page with site design
│   ├─ Save: insights/{slug}.html
│   ├─ generate_article_image() → insights/{slug}_social.png
│   ├─ update_manifest() → insights.json
│   ├─ Related articles computation (tag overlap)
│   ├─ Rebuild: feed.xml, sitemap.xml
│   ├─ LinkedIn PDF carousel generation
│   ├─ LinkedIn essay package generation
│   ├─ build_edition_document() → editions/YYYY-MM-DD.json + latest-edition.json
│   ├─ update_event_memory() → .editorial-state/event-memory.json
│   ├─ save_publication_decision() → auto-publish vs review
│   └─ save_run_record() → .editorial-state/runs/YYYY-MM-DD.json
│
├─9. GIT PUBLICATION:
│   ├─ write_generated_files() → manifest of all created files
│   ├─ load_files() → validate manifest (no path traversal, all files exist)
│   ├─ git add -- {all manifest files}
│   ├─ git commit + push origin main ← AUTO-PUBLISH (briefs, data notes)
│   └─ OR: git push origin codex/editorial-review-{run_id} → gh pr create ← REVIEW (flagships, legal risk)
│
└─10. DEPLOYMENT:
    └─ Netlify detects git push → builds site → deploys to CDN
        └─ CSP headers, cache policies applied from netlify.toml
```

---

## FORMAT THIS AS:

A comprehensive, deeply detailed, single Markdown document. Each file section should be readable as a standalone reference. Use proper headings, bullet points, and code blocks. Include the complete data flow diagram above. Write in clear, technical English. Every function should be named and explained. Every regex pattern should be documented. Every scoring dimension should have its formula explained. Every safeguard should be stated clearly with its trigger conditions.

The goal: someone who has never seen this repo should be able to read this document and understand EVERYTHING the Insights pipeline does, file by file, function by function, decision by decision.

**Length**: This should be a very long document — aim for 8000-12000 words covering every detail.
