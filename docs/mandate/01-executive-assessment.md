# Executive Assessment: The Light Tower Group Insights Intelligence Engine

**Document:** 01-Executive-Assessment
**Date:** July 30, 2026
**Status:** Current State Analysis — Pre-Overhaul Baseline

---

## 1. What the Current System Is

The Light Tower Group Insights Intelligence Engine is a single-purpose Commercial Real Estate (CRE) capital markets daily editorial pipeline. It is not a general intelligence platform. It is not a multi-sector newsroom. It is a CRE editorial machine — and within that narrow domain, it is meticulously engineered.

The pipeline operates on a GitHub Actions cron trigger each morning (~7:07 AM NY time). It runs through eight distinct phases:

1. **Gather** — Pulls stories from ~90 RSS feeds (CRE trade publications, financial press, federal agencies) plus supplementary NewsAPI queries and SEC EDGAR RSS. Normalizes and deduplicates the raw stream (~1807 stories on July 26).

2. **Triage** — Filters all raw stories through a CRE keyword gate (must match at least one `CRE_KEYWORD`, must NOT match any `EXCLUDE_KEYWORD`). Routes survivors into five CRE sub-domain buckets (real estate, capital markets, policy, architecture, market analysis). Everything else is discarded.

3. **Score** — Clusters related headlines into events, then deterministically scores each event on 10 named dimensions (0-100 scale). Assigns a franchise label (flagship, brief, data note, culture signal). Selects candidates above thresholds: MUST_READ (56), DEAL_TAPE (34), FLAGSHIP_CANDIDATE (72).

4. **Enrich** — Fetches full article text for each selected story's sources. Builds research dossiers with evidence classification (deep/adequate/thin/insufficient). Extracts facts and claims with source verification. Runs an editorial room simulation (LLM angle analysis + skeptic pass). Makes a terminal editorial decision: write, kill, defer, or handle as deal tape.

5. **Write** — Generates narrative articles via the DeepSeek API using recently rewritten prompts designed for a 90s/2000s financial journalism voice. Each article passes through a self-repair loop (max 2 iterations) with 10 independent quality gates. Articles that fail both repair attempts are killed.

6. **Publish** — Renders standalone HTML pages (`insights/{slug}.html`), generates social preview images, updates the flat JSON manifest (`insights.json`), rebuilds `feed.xml` and `sitemap.xml`, validates the repository state, commits to git, and pushes — triggering a Netlify deploy.

7. **LinkedIn** — Generates an essay package variant and saves to a LinkedIn queue for later publishing.

8. **Finalize** — Writes the run log, saves editorial record, updates event memory, renders a run summary.

The system has published 331 articles across 6 categories: Capital Markets, Deal Intelligence, Debt & Equity, Policy & Regulation, Architecture & Capital Markets, and Market Analysis. The public-facing site (`insights.html`) provides client-side filtering, search, and pagination over this flat catalog.

---

## 2. What It Does Well

The pipeline excels at depth, rigor, and transparency within its narrow scope.

**Deterministic Event Clustering.** The `cluster_events()` function groups related headlines by cross-source corroboration before scoring — so a single deal reported by GlobeSt, Commercial Observer, and Connect CRE becomes one event with multiple evidence sources, rather than three competing stories.

**Transparent, Inspectable Scoring.** The deterministic `score_event()` function exposes 10 named dimensions (transaction scale, market significance, source quality, timeliness, novelty, capital stack complexity, policy impact, strategic relevance, geographic concentration, narrative potential). Every score is traceable. No opaque LLM judgment without audit trail.

**Multi-Source Research Dossier Building.** When a story is selected for writing, the system fetches full text from every contributing source, extracts facts, classifies evidence depth, and builds a structured dossier. The editorial room then runs an LLM pass to identify angles and surface skepticism — so the writer prompt receives curated, cross-referenced material, not raw scraped text.

**Independent Quality Gates.** The content governance module runs 10 checks (factual grounding, source attribution, structural integrity, narrative coherence, regulatory accuracy, date consistency, entity correctness, quote fidelity, length threshold, repetition detection) after every article generation. These are independent assessments — they do not trust the LLM's own self-evaluation, which is a known failure mode in LLM-generated content systems.

**Self-Repair Loop.** If an article fails quality gates, the system regenerates with explicit repair instructions. Article scoring resets each cycle. This gives each story two chances to meet standards before being killed — a pattern that catches transient LLM failure modes (hallucinated numbers, dropped paragraphs, wrong byline formats) without escalating to full manual intervention.

**Clean Rollback on Validation Failure.** If the post-publish repository validation fails (broken links, invalid JSON, missing assets), every file written during that publish cycle is rolled back atomically. The system publishes all-or-nothing per editorial run.

**Strong SEO Foundation.** Every published article includes JSON-LD structured data, Open Graph tags, Twitter card metadata, canonical URLs, and properly structured headings. The site maintains a complete sitemap and RSS feed.

**Fact Extraction and Claim-to-Source Verification.** The `fact_extractor.py` module extracts numeric claims (dollar amounts, square footage, unit counts, interest rates) from the article text and verifies them against source evidence in the dossier. Discrepancies trigger quality gate failures.

**Resilient Infrastructure.** The system has model fallback (DeepSeek primary → OpenAI secondary via `model_router.py`), per-phase checkpointing with timeout handling, and cost tracking per API call. It can run for 6 hours inside a GitHub Actions runner and resume from checkpoints on retry.

**Writing Quality.** The recently rewritten prompt system (`enhanced_prompts.py`, `editorial_voice.py`) produces narrative financial prose that reads like human-written market commentary — with proper voice modes, headline shapes, and structural variety that avoid the detectable patterns of AI-generated content.

---

## 3. What It Fails to Do

These are not bugs. They are architectural limitations — the system was never designed to do these things. But the mandate now requires them.

**It discovers virtually nothing outside CRE.** The triage phase (`triage_bucketed_volume()` → `route_story()`) is a hard keyword gate against `CRE_KEYWORDS`. Stories that don't match at least one CRE keyword are discarded before scoring. On July 26, 1807 raw stories were reduced to 14 candidates. The 1793 discarded stories include private equity platform acquisitions, data center developments, energy infrastructure announcements, banking regulatory changes, Fed policy shifts, and local government land-use decisions — all of which are now mandatory coverage areas.

**It has zero coverage of six mandated sectors.** The system currently covers 1 of the 7 required sectors:
- Commercial Real Estate: yes (the only sector with source feeds, keywords, classification, and scoring)
- Private Equity: no (PERE News is in the feed list but filtered as CRE-adjacent only; PE platform acquisitions are discarded)
- Data Centers: no (zero feeds, zero keywords, zero scoring dimensions)
- Energy: no (zero feeds, zero keywords, zero scoring dimensions)
- Banking/Credit: partial (a few banking feeds exist but coverage is incidental, not systematic)
- Fed/Macro: partial (federal feeds exist but stories are filtered for CRE relevance only)
- Local Government: no (zero feeds, zero keywords, zero scoring dimensions)

**It produces near-zero output 78.8% of the time.** Across 33 completed editorial runs, 26 (78.8%) produced zero articles. The `MUST_READ_THRESHOLD` signal gate at 56 blocks everything on thin news days — and in a single-sector pipeline, most days are thin. The system was calibrated for a "publish only when there's something worth saying" philosophy, which made sense for a boutique CRE commentary operation but is incompatible with a 210-article/day mandate.

**It cannot scale to multi-sector coverage.** The architecture assumes:
- One daily edition with 3 articles
- One scoring rubric applied to all stories
- One set of keywords filtering the firehose
- One insights page with 6 category filters
- One HTML file per published article

None of these assumptions hold at 7 sectors × 30 articles/day.

**The source universe is 95% CRE trade publications.** Of ~103 total feed sources, approximately 90 are CRE-focused trade publications, 13 are federal/regulatory, and 0 are dedicated PE, energy, data center, or local government sources. The pipeline cannot cover what it cannot see.

**There is no multi-label classification.** The `route_story()` function in `bucketed_editorial.py` assigns each surviving story to exactly one CRE sub-domain bucket. A story that touches both private equity and real estate (e.g., a Blackstone platform acquisition) is classified as "real estate" — the private equity dimension is invisible to the system.

**Scoring is CRE-centric by design.** The 10 dimensions in `score_event()` are tuned for CRE capital markets. A $50M data center development with 200MW of power capacity and strategic significance for a hyperscaler would score lower than a $10M multifamily refinancing — because the data center story would score near zero on "capital stack complexity," "market concentration," and "transaction scale" (no comps in the CRE universe).

**The insights.json manifest cannot represent multi-sector taxonomy.** The current manifest is a flat JSON array of article objects with a single `category` field drawn from 6 CRE-specific values. There is no structure for sectors, subsectors, event types, or cross-sector tagging. The client-side rendering in `insights.html` assumes this flat structure.

**The HTML-per-article publishing model doesn't scale.** At 210 articles/day across 7 sectors, the system would produce 76,650 HTML files per year — each a standalone page with inlined CSS, social images, and JSON-LD. This is manageable at 3/day (1095/year) but becomes a repository and build-time problem at 70x volume. Git operations, Netlify deploys, and sitemap generation would choke.

---

## 4. Why It Underperforms

The system does not "underperform" in an absolute sense — it performs exactly as designed for a single-sector CRE pipeline. It underperforms relative to the new multi-sector mandate. Three root causes drive the gap, in order of impact:

### Root Cause 1: The CRE Keyword Filter at Triage (99%+ Elimination Rate)

This is the single biggest bottleneck. The `CRE_KEYWORDS` list in `news_sources.py` (plus the `EXCLUDE_KEYWORDS` list) acts as a hard gate that deletes every story that doesn't match at least one CRE keyword. The list was designed for a single-sector pipeline and is fundamentally incompatible with multi-sector coverage.

The math is damning. On July 26:
- 1807 raw stories gathered
- 14 survived triage (0.78% survival rate)
- 0 scored above MUST_READ threshold
- 0 articles published
- 1 deal tape item produced

The 1793 discarded stories almost certainly contained material relevant to private equity, energy, data centers, banking, and government — but the system never saw them. No scoring algorithm, no matter how sophisticated, can evaluate stories it never receives.

The keyword filter must either be removed entirely (replaced with a light classification pass that routes stories to their appropriate sector pipeline) or expanded to include keyword sets for all 7 sectors. The former approach is architecturally cleaner for the new mandate.

### Root Cause 2: No Sector-Specific Classification or Scoring

Every story that survives triage is scored by the same 10-dimension rubric, regardless of what the story is about. The dimensions were designed for CRE capital markets:

| Dimension | What It Measures (CRE Context) | What It Misses (Non-CRE Context) |
|-----------|-------------------------------|----------------------------------|
| Transaction Scale | Deal size in CRE comps | Megawatt capacity, acreage, fund size, regulatory scope |
| Market Significance | CRE submarket concentration | Grid interconnection queue position, basin-wide energy impact, national banking concentration |
| Capital Stack Complexity | Debt/equity structure | Fund structure, LP composition, regulatory capital ratios |
| Policy Impact | Zoning, tax abatements | FERC orders, Basel III rules, Fed rate path signals |
| Strategic Relevance | Portfolio fit for REITs | Hyperscaler cloud region strategy, PE platform roll-up logic |
| Novelty | First-of-kind in CRE | First-of-kind in any of 7 sectors (different baseline per sector) |
| Source Quality | Trade publication tier | Different source hierarchy per sector (SEC filing > trade press for PE; FERC filing > trade press for energy) |
| Timeliness | Universal | Universal (works across sectors) |
| Geographic Concentration | NYC-metro vs national | Different geographic ontologies per sector (grid regions for energy, cloud regions for DC, MSAs for CRE) |
| Narrative Potential | CRE audience appeal | Seven different audience personas with different information needs |

A major private equity platform acquisition, a 200MW data center campus announcement, a FERC order restructuring capacity markets, and a multifamily refinancing all get the same rubric. The rubric was built for one of those four story types. The other three are scored incorrectly by construction.

### Root Cause 3: The Publishing Ceiling

The 3-article daily target, single-edition architecture, and HTML-per-article publishing model were designed for a boutique CRE commentary shop — not an institutional intelligence desk producing 210 articles/day across 7 sectors.

The constraints compound:
- **Volume ceiling**: `MUST_READ_THRESHOLD = 56` gates to ~3 articles/day for CRE. At 7 sectors, even with 30 scored candidates per sector, a sector-agnostic 56-point gate would kill most of them.
- **Format ceiling**: Every published article is a full narrative — there is no concept of a deal tape item, a brief, or a data note at the publishing layer. All 331 articles use the same template.
- **Build-time ceiling**: One `git commit` per editorial run works at 0-3 files changed. At 210 files changed per run, git operations, Netlify deploy time, and sitemap generation become bottlenecks.

---

## 5. What the New System Must Accomplish

The overhauled system must transform from a single-sector CRE editorial pipeline into a multi-sector intelligence engine capable of sustained, high-volume publishing across 7 distinct sectors.

### Core Requirements

1. **Universal Story Acceptance.** Accept stories from all 7 mandated sectors — CRE, Private Equity, Data Centers, Energy, Banking/Credit, Fed/Macro, and Local Government — without prejudicial filtering at intake. Classification replaces elimination.

2. **Multi-Label Classification.** Classify every story by at minimum:
   - Primary sector (1 of 7)
   - Secondary sectors (0-n)
   - Event type (transaction, regulatory, market development, policy action, financing, personnel, data release, litigation)
   - Subsector (sector-specific taxonomy — e.g., "industrial" within CRE, "buyout" within PE, "hyperscale" within data centers)
   - Geographic scope (local, metro, regional, national, global) and named locations
   - Named entities (companies, people, agencies, funds, properties)
   - Classification confidence score

3. **Sector-Specific Scoring.** Score every story using a framework appropriate to its primary sector:
   - Financial magnitude (deal size, fund size, budget, AUM, megawatts, acreage — in sector-appropriate units)
   - Market significance (market share, concentration, strategic position — in sector context)
   - Strategic/policy relevance (regulatory impact, precedent value, signaling effect)
   - Novelty (first-of-kind, unusual structure, departure from trend)
   - Source quality (sector-specific source hierarchy)
   - Timeliness (recency, exclusivity, ahead-of-cycle)
   - Editorial potential (narrative richness, audience interest, explanatory value)

4. **Cross-Sector Ranking and Selection.** Select approximately the 30 most significant stories per sector per day (~210 total). Stories compete within their sector for slots — not across sectors. Each sector has its own ranking and its own thresholds. Editors (human or LLM-as-editor) can promote, demote, or merge stories across the pipeline.

5. **Tiered Content Generation.** Generate articles at varying depths based on information availability and editorial significance:
   - **Flagship** (800-1200 words): Major stories with deep evidence, multiple sources, strategic significance. Full narrative with context, analysis, and forward-looking implications.
   - **Brief** (300-500 words): Solid stories with adequate evidence. Concise analysis with key facts and context.
   - **Deal Tape / Data Note** (100-200 words): Transaction records, data releases, minor regulatory updates. Structured format with standardized fields.
   - **Signal** (50-100 words): Early indicators, rumors, filings that merit tracking but not full coverage.

6. **Sector-Specific Publishing.** Publish to properly separated sector feeds — each with its own landing page on the Insights site, its own RSS feed, and its own metadata schema. Article cards show sector, event type, and key metrics appropriate to the sector (deal size for CRE/PE, MW for data centers/energy, basis points for Fed/macro, etc.).

7. **Template-Based Rendering.** Replace the one-HTML-file-per-article model with a template-based rendering system that produces articles from structured data + a shared template. Article HTML should be build-time rendered but share CSS, JS, and template logic — reducing per-article file size by 80-90%.

8. **Sustainable Cost Model.** Tiered LLM usage:
   - Classification/routing: light/cheap model (e.g., deepseek-chat, gpt-4o-mini)
   - Scoring assistance: light model with structured output
   - Writing: premium model (deepseek-chat or gpt-4o) for flagship articles only
   - Brief/deal tape writing: light model
   - Editorial oversight (promotion/merge decisions): premium model, limited calls

9. **Complete Audit Trails.** Every editorial decision — classification, scoring, ranking, selection, editorial action (write/kill/defer/promote) — must be logged with the reasoning, the model used, the timestamp, and the input data. The audit trail must be queryable by story, by sector, by date, and by decision type.

10. **Observability Dashboard.** Real-time visibility into:
    - Stories gathered per sector per run
    - Classification distribution
    - Scoring distribution per sector
    - Selection/ rejection counts with reason codes
    - Source health by sector
    - Cost per sector and per article
    - Publishing throughput and backlog

---

## 6. Summary Assessment

The current system is a well-engineered CRE editorial pipeline that has outgrown its architecture. It was built for one sector, one audience, one daily edition of 3 articles. The mandate now requires seven sectors, seven audiences, and 210 articles per day.

The three root causes — the CRE keyword filter, the single-sector scoring model, and the publishing ceiling — are not bugs to fix. They are architectural assumptions to unwind. The keyword filter must become a classification router. The scoring model must become a family of seven sector-specific frameworks. The publishing model must graduate from handmade HTML files to a template-based rendering system.

The good news: the core infrastructure is solid. The pipeline's gather → classify → score → enrich → write → publish architecture is fundamentally correct — it just needs to be generalized from one sector to seven. The deterministic clustering, evidence classification, quality gates, self-repair loop, and rollback mechanism are sector-agnostic and will carry forward with minimal modification. The LLM integration layer (model router, cost tracking, checkpoint/timeout) already supports the multi-model tiered strategy required for cost control at 70x volume.

The bad news: the source universe must be rebuilt almost from scratch for 6 of 7 sectors. This is the largest single piece of work in the overhaul — and the one that cannot be shortcut by prompt engineering or architectural changes. The system cannot cover what it cannot see.

**Overall readiness for the mandated overhaul: the engine is sound, but the fuel system and the dashboard need a complete rebuild.**
