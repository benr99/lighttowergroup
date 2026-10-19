# Light Tower Insights Generator — Complete Systems Documentation

**Autonomous Editorial Intelligence Pipeline — Step-by-Step Technical Reference**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Complete Data Flow](#2-complete-data-flow)
3. [daily_news_agent.py — The Orchestrator](#3-daily_news_agentpy--the-orchestrator-2842-lines)
4. [Pipeline v2: The Modern Multi-Sector Pipeline](#4-pipeline-v2-the-modern-multi-sector-pipeline)
5. [editorial_intelligence.py — Deterministic Editorial Brain](#5-editorial_intelligencepy--deterministic-editorial-brain-912-lines)
6. [editorial_room.py — The Assigning Editor & Skeptic](#6-editorial_roompy--the-assigning-editor--skeptic-352-lines)
7. [editorial_pipeline.py — The 7-Stage Article Generator](#7-editorial_pipelinepy--the-7-stage-article-generator-916-lines)
8. [research_dossier.py — Multi-Source Evidence Ledger](#8-research_dossierpy--multi-source-evidence-ledger-236-lines)
9. [generation.py — Sector-Aware Prompt Routing](#9-generationpy--sector-aware-prompt-routing-439-lines)
10. [content_governance.py — The Safeguards](#10-content_governancepy--the-safeguards-217-lines)
11. [fact_extractor.py — Deterministic Fact Verification](#11-fact_extractorpy--deterministic-fact-verification-264-lines)
12. [v2_editorial.py — Pipeline Bridge](#12-v2_editorialpy--pipeline-bridge-401-lines)
13. [edition_manager.py — Daily Edition Builder](#13-edition_managerpy--daily-edition-builder-293-lines)
14. [Supporting Modules](#14-supporting-modules)
15. [Configuration Layer](#15-configuration-layer)
16. [CI/CD & Deployment](#16-cicd--deployment)

---

## 1. System Overview

**Light Tower Group** is a commercial real estate capital advisory firm. The Insights pipeline is a fully autonomous AI newsroom that discovers, scores, writes, and publishes institutional-grade commercial real estate intelligence daily.

### What It Produces

- 450+ published articles in `insights/*.html` with matching `_social.png` images
- Daily structured editions in `editions/YYYY-MM-DD.json` and `latest-edition.json`
- Auto-rebuilt `feed.xml` (RSS), `sitemap.xml`, `insights.json`
- LinkedIn essays, PDF carousels, threaded posts
- Durable editorial audit trail in `.editorial-state/`

### Pipeline at a Glance (13 Stages)

| Stage | Module | What Happens |
|-------|--------|-------------|
| 1 | `resolve_schedule_policy.py` | DST-aware schedule guard — permits only 07:07 NY time trigger |
| 2 | `model_router.py` | Provider preflight — verifies DeepSeek API is reachable |
| 3 | `ingestion.py` | Fetches 150+ RSS feeds + NewsAPI, normalizes to `CanonicalItem` objects |
| 4 | `classification.py` | Multi-label sector/event classification using regex + entity matching |
| 5 | `scoring_engine.py` | 10-dimension deterministic scoring per item |
| 6 | `ranking.py` | Within-sector ranking with diversity controls |
| 7 | `editorial_intelligence.py` | Event clustering, archive matching, must-read scoring, edition selection |
| 8 | `research_dossier.py` | Multi-source evidence dossier with full text, facts, quotes |
| 9 | `editorial_room.py` | LLM assigning editor — format, angle, kill/defer/shorten decisions |
| 10 | `editorial_pipeline.py` | 7-stage article generation (Brief → Prompt → Draft → Financial Review → Editorial Review → Fact Verification → Final Revision) |
| 11 | `content_governance.py` | Deterministic quality gates (NEVER calls LLM) |
| 12 | `edition_manager.py` + `daily_news_agent.py` (Phase 6) | Render HTML, social images, feeds, sitemaps, edition JSONs |
| 13 | `publish_generated.py` | Git commit + push to main or open editorial review PR |

### The 7 Sectors

```
commercial_real_estate  → Capital Markets
private_equity          → Deal Intelligence
data_centers            → Market Analysis
energy                  → Market Analysis
banking_credit          → Debt & Equity
fed_macro              → Policy & Regulation
local_government        → Policy & Regulation
```

### The 5 Editorial Formats

| Format | Words | Min Sources | Purpose |
|--------|-------|-------------|---------|
| **Flagship Analysis** | 750–1050 | 3 | Thesis-led analysis that changes how reader understands the event |
| **Intelligence Brief** | 240–430 | 1 | Compressed explanation of what changed and what to watch next |
| **Culture of Capital** | 300–550 | 2 | Where money, status, place, policy, and human behavior collide |
| **Data Note** | 200–400 | 1 | One primary data release → one bounded, legible argument |
| **Deal Tape** | ≤80 | 1 | Structured facts + one bounded implication; never a padded essay |

---

## 2. Complete Data Flow

```
═══════════════════════════════════════════════════════════════════════════
                    LIGHT TOWER INSIGHTS — COMPLETE DATA FLOW
═══════════════════════════════════════════════════════════════════════════

GitHub Actions triggers at 07:07 NY time (11:07/12:07 UTC, DST-aware)
│
├─▶ SCHEDULE GUARD  resolve_schedule_policy.py
│   Checks event_name, trigger_cron, dispatch_mode
│   Permits only the correct DST-time cron trigger
│   Sets RUN_MODE: shadow | preview | publish
│
├─▶ VALIDATE BASELINE
│   python -m py_compile scripts/*.py     ← all Python syntax valid
│   python -m unittest discover -s tests  ← 30+ unit tests pass
│   node --check site.js edition.js ...   ← JS syntax valid
│   python validate_publication.py        ← all public assets valid
│
├─▶ PROVIDER PREFLIGHT  model_router.py
│   Pings DeepSeek API with DEEPSEEK_API_KEY
│   Confirms model deepseek-v4-pro is available
│
├─▶ INGESTION  ingestion.py → feedparser → canonical_item.py
│   │
│   │  config/sources.json (5094 lines, 150+ sources, 7 sectors)
│   │  ─────────────────────────────────────────────────────────
│   │  ThreadPoolExecutor(max_workers=8)
│   │  ├─ Commercial Observer → Tier 1 CRE → fetch RSS
│   │  ├─ Bisnow → Tier 1 CRE → fetch RSS
│   │  ├─ Bloomberg → Tier 1 CRE → fetch RSS
│   │  ├─ PE Hub → Tier 1 PE → fetch RSS
│   │  ├─ Data Center Dynamics → Tier 1 DC → fetch RSS
│   │  ├─ Utility Dive → Tier 1 Energy → fetch RSS
│   │  ├─ American Banker → Tier 1 Banking → fetch RSS
│   │  ├─ Federal Reserve → Tier 1 Fed → fetch RSS
│   │  ├─ NY YIMBY → Tier 2 CRE → fetch RSS
│   │  └─ ... 140+ more
│   │
│   │  Per feed:
│   │  ├─ feedparser.parse(url, User-Agent header)
│   │  ├─ skip if quarantined (SourceHealthLedger)
│   │  ├─ for each entry: extract title, url, summary (strip HTML),
│   │  │   published date (ISO 8601), source name
│   │  ├─ apply 36-hour recency filter
│   │  ├─ create CanonicalItem.from_rss_entry()
│   │  └─ track health: ok / empty / error
│   │
│   │  Shared outage detection:
│   │  ├─ if ≥8 sources attempted AND ≥50% fail
│   │  └─ → release ALL quarantines (network outage, not publisher failure)
│   │
│   └─▶ Output: ~80–150 CanonicalItem objects
│
├─▶ CLASSIFICATION  classification.py
│   │
│   │  CLASSIFY EVERY ITEM — NEVER REJECT AT THIS STAGE
│   │
│   │  Layer 1: Source-based prior
│   │  ├─ _SOURCE_SECTOR_PRIORS: 70+ known source→sector mappings
│   │  │  "Commercial Observer" → commercial_real_estate
│   │  │  "PE Hub" → private_equity
│   │  │  "Data Center Dynamics" → data_centers
│   │  │  "Utility Dive" → energy
│   │  │  "American Banker" → banking_credit
│   │  │  "Federal Reserve" → fed_macro
│   │  │  "NYC Department of City Planning" → local_government
│   │  └─ return sector or None
│   │
│   │  Layer 2: Regex signal scoring
│   │  ├─ _SECTOR_SIGNALS_COMPILED: 7 pattern sets
│   │  │  CRE: multifamily|office building|cap rate|occupancy|cmbs|noi|dscr|ltv...
│   │  │  PE: buyout|take.private|leveraged buyout|growth equity|fund close...
│   │  │  DC: data center|hyperscale|colocation|gpu cluster|pue...
│   │  │  Energy: power plant|solar farm|battery storage|ppa|ferc...
│   │  │  Banking: bank failure|loan.loss reserve|charge.off|fdic...
│   │  │  Fed/Macro: federal reserve|fomc|federal funds rate|sofr|cpi...
│   │  │  LocalGov: city council|planning board|zoning variance|tax abatement...
│   │  └─ score per sector = matched_patterns / total_patterns (density 0–1)
│   │
│   │  Layer 3: Entity recognition
│   │  └─ match extracted entities against config/watchlists.json
│   │
│   │  Final assignment:
│   │  ├─ primary_sector = highest-score sector
│   │  ├─ secondary_sectors = all sectors with significant signal
│   │  ├─ classification_confidence = density score of winning sector
│   │  └─ classification_method = source_config_prior | regex | entity_match
│   │
│   └─▶ Output: classified CanonicalItem objects
│
├─▶ SCORING  scoring_engine.py  (DETERMINISTIC — ZERO LLM CALLS)
│   │
│   │  10 DIMENSIONS, EACH SCORED 1–10:
│   │
│   │  1. financial_magnitude
│   │     ├─ Extract $ amounts: regex \$\s*([\d,.]+)\s*(million|billion|trillion|mm|bn|m|b)?
│   │     ├─ Sector-specific threshold buckets:
│   │     │  CRE:   $1M→$10M→$50M→$100M→$500M→$1B→$5B
│   │     │  PE:    $10M→$50M→$100M→$500M→$1B→$5B→$10B
│   │     │  DC:    $5M→$25M→$100M→$250M→$500M→$1B→$5B
│   │     │  Energy:$10M→$50M→$100M→$500M→$1B→$5B→$10B
│   │     │  Fed:   FOMC/rate decision→6, else→3 (not $-driven)
│   │     └─ DC bonus: ≥500MW +3, ≥200MW +2, ≥50MW +1
│   │
│   │  2. party_significance
│   │     ├─ Match entities against config/watchlists.json
│   │     │  tier_1_institutions → 10, tier_2_companies → 7,
│   │     │  tier_3_firms → 4, unknown → 1
│   │     └─ Searches headline+summary text if no entities extracted
│   │
│   │  3. market_impact
│   │     ├─ Base: 3
│   │     ├─ "record/largest/first/historic/unprecedented" +3
│   │     ├─ "repric*/reset*/shift*/signal*/trend" +2
│   │     ├─ "ripple/spillover/contagion/systemic" +3
│   │     ├─ "federal reserve/fomc/rate hike/rate cut" +4
│   │     ├─ "bankruptcy/default/insolven*" +3
│   │     └─ "industry.wide/market.wide/across the sector" +2
│   │
│   │  4. strategic_relevance
│   │     ├─ Base: 3
│   │     ├─ CRE stakeholder terms (sponsor, developer, lender...) → each +1
│   │     ├─ Capital terms (debt, equity, fund, investment, yield...) → each +1
│   │     └─ Sector bonus: CRE +2, PE/Banking/Fed/LocalGov +1, DC/Energy +0
│   │
│   │  5. policy_impact
│   │     ├─ Base: 2
│   │     ├─ Fed/FOMC +4, Congress/legislation +4
│   │     ├─ FDIC/OCC/SEC/CFPB +4, regulation/regulatory +3
│   │     ├─ zoning/rezoning/land use +3
│   │     ├─ tax change/tariff/subsidy +2
│   │     └─ Supreme/federal court/ruling +3
│   │
│   │  6. novelty  → default 7 (updated by editorial_intelligence via event memory)
│   │
│   │  7. source_quality
│   │     ├─ tier 1→10, tier 2→7, tier 3→5, tier 4→3, tier 5→1
│   │     └─ primary authority → +2
│   │
│   │  8. timeliness
│   │     ├─ hours = item.age_hours() (now – publication_date)
│   │     └─ ≤1hr→10, ≤6hr→9, ≤12hr→8, ≤24hr→7, ≤48hr→5, ≤72hr→3, >72hr→1
│   │
│   │  9. editorial_potential
│   │     ├─ available text words: >2000→10, >1000→8, >500→6, >200→4, else 2
│   │     └─ entity count: ≥5 +2, ≥2 +1
│   │
│   │  10. cross_sector_impact
│   │      └─ 1(primary) + len(secondary): ≥5→10, ≥4→8, ≥3→6, ≥2→4, else 2
│   │
│   │  COMPOSITE SCORE:
│   │  ├─ Load sector weight profile from config/scoring_profiles.json
│   │  ├─ composite = (weighted_sum / weight_sum) × 10  →  0–100
│   │  └─ Tier assignment:
│   │     ≥80 → tier_1_must_cover
│   │     ≥65 → tier_2_strongly_recommended
│   │     ≥50 → tier_3_useful_coverage
│   │     ≥35 → tier_4_reserve
│   │     <35 → rejected
│   │
│   └─▶ Output: scored CanonicalItem objects with composite + tier
│
├─▶ RANKING  ranking.py
│   │
│   │  rank_within_sector(items, sector):
│   │  ├─ Filter: primary_sector matches AND tier ≠ 'rejected'
│   │  └─ Sort: composite_score descending
│   │
│   │  apply_diversity_controls(ranked, sector):
│   │  ├─ No single subsector > 40%
│   │  ├─ No single source > 25%
│   │  ├─ No single company > 20%
│   │  ├─ Minimum 3 distinct subsectors
│   │  └─ When constraint violated: replace excess with lower-ranked diverse items
│   │
│   └─▶ Output: per-sector ranked slates (~30 stories each)
│
├─▶ EDITION MODE  editorial_intelligence.py
│   │
│   │  EVENT CLUSTERING:
│   │  cluster_events(candidates, threshold=0.61)
│   │  ├─ For each candidate, find best-matching existing cluster
│   │  │  event_similarity(left, right) computes:
│   │  │  ├─ Exact URL match → 1.0
│   │  │  ├─ Title token overlap (stopwords removed) → weight 0.55
│   │  │  ├─ Company entity overlap → weight 0.20
│   │  │  ├─ Amount overlap → weight 0.15
│   │  │  ├─ Market overlap → weight 0.05
│   │  │  ├─ Asset class overlap → weight 0.05
│   │  │  └─ Boosted mode: if amounts match AND title ≥ 0.15
│   │  │     → 0.64 + 0.22×title + 0.09×company + 0.03×market + 0.02×asset
│   │  └─ Create new cluster if best score < 0.61
│   │
│   │  event_fingerprint(members):
│   │  ├─ Collect: title tokens (appearing in ≥50% of members), companies,
│   │  │   amounts, markets, asset classes
│   │  ├─ Concatenate with | delimiter
│   │  └─ SHA-256 → first 20 hex chars (stable event ID)
│   │
│   │  attach_corroborating_sources(events, wider_pool, threshold=0.61):
│   │  ├─ For each event: find matching stories from wider feed pool
│   │  ├─ Filter: different URL, different domain
│   │  ├─ Sort: similarity descending, source tier ascending
│   │  └─ Cap: 5 sources per event
│   │
│   │  ARCHIVE MATCHING:
│   │  archive_matches(event, archive_records, threshold=0.38)
│   │  ├─ Compare candidate against published Light Tower articles
│   │  ├─ Same-event detection via multi-dimensional signals:
│   │  │  ├─ Title token overlap ≥ 0.57
│   │  │  ├─ Amount overlap + context ≥ 0.16
│   │  │  ├─ Address overlap + context ≥ 0.14
│   │  │  ├─ Entity overlap + context ≥ 0.24
│   │  │  └─ Context score ≥ 0.38
│   │  ├─ _dollar_amount_values(): parse $X (million|billion|trillion) → int
│   │  ├─ _street_addresses(): regex \d{1,5} ... street|st|avenue|ave...
│   │  ├─ _archive_is_recent(): candidate date within 7 days of record date
│   │  └─ Returns top 5 matches with similarity, same_event, recent flags
│   │
│   │  MUST-READ SCORING  score_event() — 9 dimensions:
│   │  ┌─────────────────────────┬──────────────────────────────────────┐
│   │  │ 1. Consequence   (max15)│ material_transaction+5, operating_signal+4│
│   │  │                      │ big_number+3, distress/policy topics+5   │
│   │  │                      │ billion-scale language+3                 │
│   │  │ 2. Novelty       (max15)│ "first/largest/record/historic" patterns │
│   │  │                      │ cross-source bonus+3                     │
│   │  │ 3. Conflict      (max15)│ "default/foreclosure/lawsuit" patterns  │
│   │  │                      │ distress/gov_action topics+4             │
│   │  │ 4. Explanatory   (max15)│ 3+topics×2, "because/pressure"+3       │
│   │  │ 5. Cultural      (max10)│ sports/entertainment/tech/status ×3    │
│   │  │ 6. Human Stakes  (max10)│ tenant/resident/worker patterns→8, +2  │
│   │  │ 7. Evidence      (max10)│ source tier + primary bonus + count     │
│   │  │ 8. Right to Win  (max10)│ LTG topic alignment (capital markets,   │
│   │  │                      │ CMBS, private credit, distress+5)        │
│   │  │ 9. Conversation  (max10)│ conflict/3 + cultural/2 + novelty/4     │
│   │  └─────────────────────────┴──────────────────────────────────────┘
│   │  PENALTIES:
│   │  ├─ Routine penalty (–18): formulaic "$X million loan", "X sq ft lease",
│   │  │   "acquires Y for $Z" — unless distress/policy/gov topics present
│   │  ├─ Archive penalty (–18 max): recent same-event → –18,
│   │  │   9 × published_priors + 3 × recent_memory_matches
│   │  └─ Audience adjustment (±5): learned weights from audience_signals.json
│   │
│   │  SELECTION  select_edition():
│   │  ├─ Filter: must_read_score ≥ MUST_READ_THRESHOLD (56)
│   │  ├─ Separate into tiers: must-cover, strongly-recommended, useful
│   │  ├─ Apply editorial diversity (no single topic dominance)
│   │  ├─ Assign formats based on score and evidence level
│   │  ├─ Target: DEFAULT_DAILY_ARTICLE_TARGET = 3 publishable pieces
│   │  ├─ Research: up to 5 candidates (extra capacity absorbs failures)
│   │  ├─ Deal Tape: separate compact entries, never padded into articles
│   │  ├─ Flagship threshold: ≥ 72
│   │  ├─ Auto-publish brief floor: ≥ 24
│   │  └─ Daily-depth research floor: ≥ 24
│   │
│   │  PRE-ENRICHMENT:
│   │  ├─ Fetch full text via trafilatura.fetch_url() for top CRE candidates
│   │  ├─ This lets a generic headline recover material facts:
│   │  │  project cost, square footage, occupancy, rent, capex, redevelopment scope
│   │  └─ The wider feed pool can then corroborate without admitting low-quality stories
│   │
│   └─▶ Output: editorial_selection dict with events, scores, formats, assignments
│
├─▶ RESEARCH DOSSIER  research_dossier.py
│   │
│   │  build_research_dossier(editorial_event, fetched_text_by_url, archive_records)
│   │  │
│   │  │  FOR EACH SOURCE in event:
│   │  │  ├─ Fetch full text from fetched_text_by_url cache
│   │  │  ├─ sanitize_untrusted_source(): remove prompt-injection text
│   │  │  ├─ _fact_candidates(): extract fact-bearing sentences
│   │  │  │  └─ Must contain: $X, X%, 20XX year, said/reported/announced/
│   │  │  │     filed/approved/acquired/sold/borrowed/lent/matures/
│   │  │  │     occupancy/units/square feet
│   │  │  ├─ _quotes(): extract quoted text (20-280 chars, curly + straight quotes)
│   │  │  └─ Build source entry: name, url, domain, published, authority,
│   │  │     tier, summary, full_text_excerpt (first 6,500 chars),
│   │  │     reported_facts (up to 8), quotes (up to 3)
│   │  │
│   │  │  COMPUTE:
│   │  │  ├─ independent_source_count: unique domains
│   │  │  ├─ usable_full_text_count: sources with non-empty full_text_excerpt
│   │  │  ├─ evidence_level:
│   │  │  │  "deep"      = ≥3 independent + ≥2 full text
│   │  │  │  "adequate"  = ≥2 independent OR have primary source
│   │  │  │  "thin"      = ≥1 source
│   │  │  │  "insufficient" = no usable sources
│   │  │  ├─ longform_allowed = evidence_level in {deep, adequate}
│   │  │  └─ reporting_gaps: missing financial figures, party identities, market context
│   │  │
│   │  └─ Return: complete dossier dict with source_facts, quote_ledger,
│   │     evidence_level, independent_source_count, reporting_gaps
│   │
│   └─▶ Output: research dossier per selected event
│
├─▶ EDITORIAL ROOM  editorial_room.py
│   │
│   │  run_editorial_room(editorial_event, dossier, api_key, editorial_priors)
│   │  │
│   │  │  Step 1: deterministic_room_plan()
│   │  │  ├─ Downgrade flagship→brief if longform not allowed
│   │  │  ├─ Downgrade culture_signal→brief if <2 independent sources
│   │  │  ├─ Force deal_tape if evidence_level == "insufficient"
│   │  │  └─ Set default angle, skeptic objections, reporting gaps
│   │  │
│   │  │  Step 2: If deal_tape → return deterministic plan immediately
│   │  │
│   │  │  Step 3: LLM EDITORIAL ROOM CALL (DeepSeek)
│   │  │  ├─ System prompt: EDITORIAL_CONSTITUTION
│   │  │  │  "Light Tower publishes only when it can make a smart reader
│   │  │  │   see a capital decision differently. Accuracy is the floor..."
│   │  │  ├─ Context: current slate, editorial priors, dossier summary
│   │  │  └─ Returns: decision (write/shorten/kill/deal_tape),
│   │  │     final_format, angle, why_now, skeptic_objections,
│   │  │     reporting_gaps, human_stakes, concrete_detail, kill_reason
│   │  │
│   │  │  Step 4: DAILY-DEPTH BRIEF OVERRIDE GUARD
│   │  │  ├─ IF selection_tier == "daily_depth"
│   │  │  ├─ AND no legal/allegation risk
│   │  │  ├─ AND evidence_level ≠ "insufficient"
│   │  │  ├─ AND ≥1 usable full text
│   │  │  ├─ AND ≥3 reported facts
│   │  │  ├─ AND no hard-stop patterns (allegations, lawsuits, criminal,
│   │  │  │   fraud, indicted, source authenticity, fabricate, cannot verify,
│   │  │  │   unsupported claims, duplicate)
│   │  │  └─ THEN: deterministic plan OVERRIDES LLM kill decision
│   │  │     "The editorial-room model cannot turn single-source status or
│   │  │      missing human stakes into an automatic veto when the
│   │  │      deterministic record contains ≥1 full text and ≥3 facts."
│   │  │
│   │  └─▶ Output: editorial plan (format, angle, kill/defer/shorten decision)
│
├─▶ 7-STAGE ARTICLE GENERATION  editorial_pipeline.py
│   │
│   │  EditorialPipeline.run(item, dossier, api_key, article_format)
│   │  │
│   │  │  STAGE 1: Analytical Brief (deterministic + optional LLM enhancement)
│   │  │  ├─ build_analytical_brief(item, dossier) → structured pre-writing analysis
│   │  │  │  Output: central_financial_question, core_tension, thesis,
│   │  │  │  article_architecture, article_depth, parties_and_incentives,
│   │  │  │  transaction_economics, key_numbers, unknowns
│   │  │  └─ Optional: enhance_brief_with_llm() deepens analytical framing
│   │  │
│   │  │  STAGE 2: Assemble Writing Prompt
│   │  │  ├─ get_sector_prompt(primary_sector) → sector-specific system prompt
│   │  │  ├─ Build user prompt with: story, source tier, sector, summary,
│   │  │  │  dossier text (24,000 chars), analytical brief, article structure,
│   │  │  │  editorial format, word contract
│   │  │  └─ 12 WRITING RULES:
│   │  │     1. Open with the most revealing fact, number, or tension
│   │  │     2. Build around the central question and thesis
│   │  │     3. Interpret key numbers — don't just list them
│   │  │     4. Name the parties and explain gains/risks
│   │  │     5. Distinguish reported facts, reasonable inferences, unknowns
│   │  │     6. Vary sentence rhythm; avoid formulaic openings
│   │  │     7. End with unresolved question or next signal to watch
│   │  │     8. DO NOT use "signals," "highlights," "underscores,"
│   │  │        "showcases" as analytical verbs
│   │  │     9. Every claim must be supported by the source dossier
│   │  │     10. Label calculations and inferences explicitly
│   │  │     11. Sources array = canonical dossier URLs only
│   │  │     12. NEVER mention internal scores in public copy
│   │  │
│   │  │  STAGE 3: Draft (LLM call)
│   │  │  ├─ DeepSeek API: json_mode=True, temperature=0.2, max_tokens=8000
│   │  │  ├─ Required fields: body_html, title, excerpt, sources, excellence_ledger
│   │  │  └─ Non-empty sources array validation
│   │  │
│   │  │  STAGE 4: Financial Review (separate LLM call)
│   │  │  ├─ Checks: are financial figures correct? supported?
│   │  │  │  Does article explain what numbers MEAN?
│   │  │  │  Are return/valuation/market claims supported?
│   │  │  │  Does it distinguish facts from calculated metrics?
│   │  │  ├─ CALIBRATION RULES:
│   │  │  │  "Judge against what the dossier actually discloses, not an
│   │  │  │   imagined underwriting file."
│   │  │  │  "For a 240–430 word brief, one credible source can support
│   │  │  │   a bounded article when every claim is attributed."
│   │  │  │  "Do NOT fail for undisclosed loan pricing, returns, or
│   │  │  │   valuations. Fail if the article invents them."
│   │  │  └─ Returns: issues[], passed (bool), score_1_10, summary
│   │  │
│   │  │  STAGE 5: Editorial Review (separate LLM call)
│   │  │  ├─ Checks: opening quality, logical flow, sentence variety,
│   │  │  │  AI language detection, conclusion quality, voice
│   │  │  └─ Returns: issues[], passed, score_1_10, opening_quality,
│   │  │     worst_sentence, summary
│   │  │
│   │  │  STAGE 6: Fact Verification (DETERMINISTIC — NO LLM)
│   │  │  ├─ Check: dossier has canonical source URLs
│   │  │  ├─ Check: every article source URL is present in dossier URLs
│   │  │  ├─ Check: key numbers from brief appear in article body
│   │  │  ├─ Scan for unsupported claims: "is expected to", "analysts
│   │  │  │  predict", "sources say", "widely viewed as", "market believes"
│   │  │  └─ audit_article_facts(): cross-reference article amounts,
│   │  │     companies, addresses against dossier source_facts
│   │  │     └─ Flags: unmatched amounts, unmatched companies,
│   │  │        unmatched addresses with surrounding context
│   │  │
│   │  │  STAGE 7: Final Revision (LLM call — only if issues exist)
│   │  │  ├─ Compiles ALL issues from financial + editorial + fact reviews
│   │  │  ├─ Sends to DeepSeek: original article JSON + issues + dossier
│   │  │  ├─ Instructions: fix every issue, keep source-grounded facts,
│   │  │  │  delete unsupported claims (no valid replacement),
│   │  │  │  don't introduce new claims, maintain word contract
│   │  │  └─ Returns: revised article (merged with original for missing fields)
│   │  │
│   │  └─▶ Output: complete article dict with all public fields + control ledgers
│
├─▶ QUALITY GOVERNANCE  content_governance.py  (NEVER CALLS LLM)
│   │
│   │  independent_quality_issues(article, require_sections, article_format)
│   │  │
│   │  │  1. FALLBACK CHECK: if generation ends with "fallback" → hold
│   │  │
│   │  │  2. WORD COUNT: format-specific min/max
│   │  │     flagship  725–1100 words
│   │  │     brief     215–475  words
│   │  │     culture   275–625  words
│   │  │     data_note 175–450  words
│   │  │
│   │  │  3. STRUCTURE: ≥2 <h2> sections (for full articles)
│   │  │
│   │  │  4. BOILERPLATE DETECTION:
│   │  │     "the headline is therefore a doorway"
│   │  │     "buildings are where private capital"
│   │  │     "the capital question is simple and difficult"
│   │  │     "the built world is not merely the background"
│   │  │
│   │  │  5. VOICE QUALITY: editorial_quality_issues() checks
│   │  │
│   │  │  6. SOURCE VALIDATION:
│   │  │     ├─ sources array must be non-empty
│   │  │     ├─ must have valid https:// or http:// URLs
│   │  │     └─ REJECT example.com (fixture/test sources)
│   │  │
│   │  │  7. PARAGRAPH REPETITION:
│   │  │     └─ if ≥4 paragraphs and unique/total < 0.9 → flag
│   │  │
│   │  │  8. FACT AUDIT (if dossier has source_facts):
│   │  │     ├─ audit_article_facts(body_html, source_facts, source_tier)
│   │  │     ├─ Matches article amounts, companies, addresses against sources
│   │  │     └─ Flags: unmatched amounts/companies/addresses
│   │  │        → sets article["_fact_audit"]
│   │  │
│   │  │  9. SEMANTIC CLAIM AUDIT (if narrative_ledger has claim + sources):
│   │  │     ├─ audit_claim_semantic(claim, source_texts)
│   │  │     ├─ Breaks claim into assertions, checks each against sources
│   │  │     ├─ Returns: claim_supported, confidence, assertions_missing
│   │  │     └─ If unsupported → "central claim not supported by sources"
│   │  │
│   │  │  10. NEAR-DUPLICATE DETECTION:
│   │  │      ├─ near_duplicate_matches(title, known_insights, threshold=0.86)
│   │  │      ├─ SequenceMatcher.ratio() on normalized titles
│   │  │      ├─ Jaccard token similarity (threshold 0.82)
│   │  │      └─ Returns warning messages for editorial review
│   │  │
│   │  └─▶ Returns: list of error strings (empty = passed all gates)
│
├─▶ RENDER & PUBLISH  daily_news_agent.py Phase 6 + edition_manager.py
│   │
│   │  FOR EACH APPROVED ARTICLE:
│   │  ├─ render_html(article) → complete HTML page with site design
│   │  ├─ Mojiabake check on rendered HTML
│   │  ├─ Save: insights/{slug}.html
│   │  ├─ generate_article_image() → insights/{slug}_social.png
│   │  ├─ update_manifest() → append to insights.json
│   │  ├─ Related articles: compute tag overlap (≥2 shared tags)
│   │  │  → write insights/{slug}_related.json
│   │  └─ LinkedIn PDF carousel generation (non-brief articles)
│   │
│   │  REBUILD DISTRIBUTION FILES:
│   │  ├─ update_feed_xml() → feed.xml (RSS)
│   │  └─ update_sitemap_xml() → sitemap.xml (16 static pages + all insights)
│   │
│   │  BUILD EDITION (edition mode):
│   │  ├─ build_edition_document(date, selection, articles, status)
│   │  │  ├─ Article summaries with read_time, source_count, format
│   │  │  ├─ Deal Tape entries
│   │  │  └─ Editorial metadata
│   │  ├─ save_public_edition() → editions/YYYY-MM-DD.json + latest-edition.json
│   │  ├─ update_event_memory() → .editorial-state/event-memory.json
│   │  ├─ save_publication_decision() → auto-publish vs review
│   │  └─ save_run_record() → .editorial-state/runs/YYYY-MM-DD.json
│   │
│   │  LINKEDIN ESSAY DESK:
│   │  ├─ generate_essay_package(article, length_mode, api_key)
│   │  ├─ Length modes: standard (flagship), edge (culture), compressed (brief)
│   │  ├─ Quality check: publish_ready + editorial_review.status == "ready_for_review"
│   │  └─ save_to_queue() → linkedin_essay_queue.json
│   │
│   └─▶ Output: all public + audit files written to disk
│
├─▶ GIT PUBLICATION  publish_generated.py
│   │
│   │  load_files() from .editorial-state/generated-files.json:
│   │  ├─ Validate: no absolute paths, no .. traversal, no .git/ paths
│   │  ├─ Resolve all paths relative to SITE_ROOT
│   │  ├─ Verify every declared file exists
│   │  ├─ Deduplicate paths
│   │  └─ Add generated-files.json itself
│   │
│   │  PUBLICATION DECISION from publication-decision.json:
│   │  ├─ AUTO-PUBLISH (briefs, data notes, routine coverage):
│   │  │  git add {all manifest files}
│   │  │  git commit -m "Publish curated Insights edition {run_id}"
│   │  │  git push origin main
│   │  │
│   │  └─ EDITORIAL REVIEW (flagships, Culture of Capital, legal risk,
│   │     insufficient evidence, fact-poor):
│   │     git push origin codex/editorial-review-{run_id}
│   │     gh pr create --base main --head {branch} --title "Editorial review"
│   │        --body-file .editorial-state/run-summary.md
│   │
│   └─▶ Netlify detects push → builds site → deploys to CDN
│       └─ CSP headers, cache policies applied from netlify.toml
│
═══════════════════════════════════════════════════════════════════════════
                            END OF DATA FLOW
═══════════════════════════════════════════════════════════════════════════
```

---

## 3. daily_news_agent.py — The Orchestrator (2842 lines)

**Role**: The central nervous system. The `main()` entry point that coordinates every stage of the pipeline. This is the file invoked by GitHub Actions or the local scheduler.

### Imports & Setup (lines 1–171)

```
Import 20+ sub-modules covering:
  - Feeds:      news_sources (RSS_FEEDS, FEDERAL_RSS_FEEDS, CRE_KEYWORDS...)
  - Prompts:    enhanced_prompts (SYSTEM_PROMPT_ENHANCED, USER_PROMPT_TEMPLATE)
  - Scoring:    editorial_scoring (call_deepseek, daily_top_news_selection)
  - Governance: content_governance (independent_quality_issues, near_duplicate_matches)
  - Editorial:  editorial_intelligence (select_edition, score_event, cluster_events)
  - Research:   research_dossier (build_research_dossier)
  - Room:       editorial_room (run_editorial_room, excellence_issues)
  - Publishing: edition_manager (build_edition_document, save_public_edition...)
  - LinkedIn:   linkedin_essay_agent (generate_essay_package, save_to_queue)
  - Images:     social_image_generator (generate_article_image)
  - Health:     source_health (SourceHealthLedger)
  - Validation: validate_publication
  - Costs:      cost_tracker
  - Checkpoints: checkpoint (run_with_timeout)
```

**`.env` loading** (lines 36–41):
```python
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
```
Crucially uses `setdefault` — existing environment variables (e.g., from GitHub Actions secrets) take precedence over `.env` file values.

**LLM Configuration** (lines 159–170):
```python
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
_LLM_URL = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
_LLM_PROVIDER = {
    "provider": "deepseek",
    "model": _LLM_MODEL,
    "url": _LLM_URL,
    "fallback": False,
}
```

**Redaction** (lines 173–184):
`redact_secret_text()` strips API keys, bearer tokens, and `sk-` prefixed keys from log output using regex:
```python
re.sub(r"([?&](?:apiKey|key|token|access_token)=)[^&\s)]+", r"\1[REDACTED]", text)
re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text)
re.sub(r"\bsk-[A-Za-z0-9._-]+", "sk-[REDACTED]", text)
```

**Mojiabake Detection** (lines 187–198):
`assert_no_mojibake()` scans for the Unicode replacement character (`\ufffd`) and two common mojibake patterns (â, Ã). If found, raises `ValueError` with the surrounding context — preventing corrupted text from reaching publication.

### Phase 1: GATHER — `fetch_rss_stories()` (lines 205–279)

This is the legacy ingestion function. The modern pipeline uses `ingestion.py`. But it's still present and works as follows:

1. **Initialize**: `SourceHealthLedger(SOURCE_HEALTH_FILE)` — loads quarantined sources
2. **Iterate ALL_RSS_FEEDS** (CRE + Federal feeds fused together):
   - Skip quarantined sources (print `[SKIP]` message)
   - Call `feedparser.parse(feed_url, User-Agent="LightTowerGroup-NewsAgent/1.0")`
   - If bozo (malformed) AND no entries → record empty, continue
   - For each entry: extract `title`, `url` (link or id), `summary` (strip HTML), `published` (ISO 8601)
   - Append story dict: `{title, url, summary, source, published}`
   - Record `health.record_success()` with story count and elapsed ms
   - On exception: record failure with redacted error message
   - Sleep 50ms between feeds (rate limiting)
3. **Shared outage detection** (lines 275–279):
   ```python
   shared_outage = attempted_feeds >= 8 and len(failures) >= max(4, attempted_feeds // 2)
   if shared_outage:
       released = health.release_quarantines()
   ```
   If ≥8 feeds attempted and ≥50% fail, this is a network-wide outage, not per-publisher failures. All quarantines are released so every feed gets a fresh chance on the next run.

### Phase 2: TRIAGE

Filters stories using `story_normalizer.py` functions:
- `has_cre_editorial_anchor()` — must have enough CRE-specific content
- `has_reported_amount_at_least_ten_million()` — minimum $10M deal threshold
- Sanitizes user-submitted text (removes instruction-like strings)
- Deduplicates: 36-hour recency filter, URL dedup

### Phase 3: SCORE (legacy paths)

- `daily_top_news_selection()` — DeepSeek ranks stories by: capital markets impact (30pts), NYC relevance (25pts), deal scale (20pts), originality (15pts), timeliness (10pts)
- `bucketed_volume_selection()` — alternative: volume-oriented routing to 5 editorial lanes
- `generate_weekly_market_review()` — Friday-only: synthesizes a week of runs

### Phase 3-EDITION: Edition Mode Pipeline (current production)

This is triggered by `--selection-mode edition` and uses the modern pipeline:

1. **Event Clustering**: `cluster_events()` groups same-event coverage
2. **Corroboration**: `attach_corroborating_sources()` adds matching stories from wider pool
3. **Archive Check**: `archive_matches()` prevents re-covering published transactions
4. **Pre-enrichment**: Fetches full text via `trafilatura` for top CRE candidates
5. **Must-Read Scoring**: `score_event()` computes 9-dimension editorial value
6. **Selection**: `select_edition()` builds scarce daily portfolio
7. **Research Dossier**: `build_research_dossier()` — multi-source evidence ledger
8. **Editorial Room**: `run_editorial_room()` — LLM format/angle/kill assignment
9. **Excellence Check**: `excellence_issues()` — positive-quality ledger validation

### Phase 4: ENRICH

- Fetches full article text via `trafilatura.fetch_url()` for each candidate
- Extracts NYC addresses from enriched stories
- Pre-enrichment gives the pipeline more material facts for scoring and writing

### Phase 5: WRITE — Article Generation (lines 2412–2502)

```python
for i, candidate in enumerate(enriched_candidates, 1):
    if len(articles) >= MAX_ARTICLES: break
    
    if args.pipeline_v2:
        article = generate_v2_article(candidate, api_key=DEEPSEEK_API_KEY, provider=_llm_provider)
    else:
        article = generate_article(candidate, recent_titles_window)
```

**Post-generation checks** (lines 2447–2478):
1. **Mojiabake check**: `assert_no_mojibake()` on the article
2. **Independent quality gate**: `_article_control_findings()` — word count, sections, sources, boilerplate, paragraph repetition, fact audit, semantic claim audit
3. **Near-duplicate detection**: `near_duplicate_matches()` against `known_insights`
4. **Slug collision**: `already_published()` check
5. **Ledger stripping**: `article["_editorial_control"]` stores narrative_ledger and excellence_ledger (for the audit trail only, never in public HTML)

### Phase 5b: LinkedIn Essay Desk (lines 2515–2561)

For each approved article:
```python
package = generate_essay_package(article, length_mode=native_length, api_key=DEEPSEEK_API_KEY)
approved = bool(package.get("publish_ready")) and review.get("status") == "ready_for_review"
if approved:
    article["linkedin_essay"] = package.get("linkedin_essay", "")
    save_to_queue(package)
```

Length mode selection:
- `flagship` → `"standard"`
- `culture_signal` → `"edge"`
- `brief` / `data_note` → `"compressed"`

### Phase 6: PUBLISH (lines 2588–2750)

For each article:
1. `render_html(article)` → produces a complete HTML page
2. Mojiabake check on rendered HTML
3. Write `insights/{slug}.html`
4. `generate_article_image(title, subtitle, img_path)` → `insights/{slug}_social.png`
5. `update_manifest(article)` → append to `insights.json`
6. Related articles: tag overlap computation → `insights/{slug}_related.json`
7. Rebuild `feed.xml` and `sitemap.xml`
8. LinkedIn PDF carousel generation (non-brief articles)
9. Edition mode: `build_edition_document()` → `save_public_edition()` → `update_event_memory()` → `save_publication_decision()` → `save_run_record()`

### Phase 7: DEPLOY & Phase 8: MONITOR

- Git publication via `publish_generated.py`
- Editorial review PR for flagships/legal-sensitive work
- Write `agent_log.json`
- Generate `run-summary.md`

### CLI Interface

```
--selection-mode edition   ← current production mode
--articles 4               ← max articles to generate
--daily-target 3           ← target publishable pieces
--pipeline-v2              ← use modern multi-sector pipeline
--shadow                   ← score only, no generation, no publish
--dry-run                  ← generate but don't write files or git
--skip-git                 ← skip git operations
--run-origin github-actions ← scheduler lease identity
```

---

## 4. Pipeline v2: The Modern Multi-Sector Pipeline

### 4a. pipeline_v2.py (395 lines)

The modern orchestrator that runs alongside (not instead of) `daily_news_agent.py`. Can run in shadow mode.

**`write_candidate_audit()`** — the audit trail function:
```python
def write_candidate_audit(scored, selected=None, output_path=None) -> Path:
    """Persist every scored candidate with all ten raw dimensions."""
    rows = []
    for item in scored:
        rows.append({
            "id": item.item_id,
            "headline": item.headline,
            "source_name": item.source_name,
            "source_tier": item.source_tier,
            "primary_sector": item.primary_sector,
            "scores": {dim: getattr(item, f"{dim}_score", None) for dim in SCORING_DIMENSIONS},
            "composite": item.composite_score,
            "tier": item.tier,
            "selected_for_sector_slate": item_id in selected_ids,
        })
    rows.sort(key=lambda row: row["composite"], reverse=True)
    # Writes to .editorial-state/candidate-audit.json
    # Newest run overwrites previous — but workflow artifact upload preserves history
```

This is critical for debugging scoring behavior — without it, only the few selected stories survive, making ranking behavior impossible to audit after the fact.

### 4b. ingestion.py (326 lines)

Replaces the monolithic `fetch_rss_stories()` with a config-driven approach.

**`load_sources()`** (lines 36–64):
- Reads `config/sources.json`
- Supports both `{"schema_version": 1, "sources": [...]}` and bare `[...]` shapes
- Filters to active sources only (`active: true`)
- Returns flat list of source dicts

**`fetch_single_feed()`** (lines 114–179):
```python
def fetch_single_feed(source) -> tuple[list[CanonicalItem], dict, str | None]:
    name = source.get("name", "unknown")
    url = source.get("url", "")
    feed = feedparser.parse(url, request_headers={"User-Agent": "LightTowerGroup-NewsAgent/2.0"})
    for entry in feed.entries:
        if len(items) >= MAX_ENTRIES_PER_FEED: break  # 500 cap
        title = (entry.get("title") or "").strip()
        link = entry.get("link") or entry.get("id") or ""
        if not title or not link: continue
        published = _parse_entry_date(entry)
        if not _is_recent(published): continue  # 36-hour window
        summary = _truncate_summary(raw_summary)  # strip HTML, max 600 chars
        item = CanonicalItem.from_rss_entry(
            {"title": title, "link": link, "summary": summary, "published": published},
            source
        )
        items.append(item)
    return items, source, None
```

**`fetch_all_sources()`** (lines 182–326):
```python
def fetch_all_sources(sources=None, max_workers=MAX_WORKERS) -> list[CanonicalItem]:
    health = SourceHealthLedger(SOURCE_HEALTH_FILE)
    active_sources = [s for s in sources if not health.is_quarantined(s.get("name", ""))]
    
    all_items = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(active_sources))) as executor:
        futures = {executor.submit(fetch_single_feed, src): src for src in active_sources}
        for future in as_completed(futures):
            items, updated_source, error = future.result()
            all_items.extend(items)
    return all_items
```

Threaded via `ThreadPoolExecutor` with 8 workers. Since all calls are I/O-bound (HTTP requests to RSS feeds), threading provides excellent parallelism without GIL interference.

### 4c. canonical_item.py (233 lines)

The unified data model. Every story in the pipeline is a `@dataclass` with 40+ fields.

**Key fields**:
```python
@dataclass
class CanonicalItem:
    # Identity
    item_id: str = ""
    source_name: str = ""
    source_url: str = ""
    headline: str = ""
    publication_date: str = ""
    
    # Classification
    primary_sector: str = ""       # commercial_real_estate, private_equity, etc.
    secondary_sectors: list[str]   # multiple sectors possible
    event_type: str = ""           # property_acquisition, buyout, fomc_decision...
    subsector: str = ""            # multifamily, buyouts, hyperscale...
    classification_confidence: float = 0.0
    classification_method: str = "" # source_prior, regex, entity_match
    
    # Entities
    companies: list[str] = []
    buyers: list[str] = []
    sellers: list[str] = []
    lenders: list[str] = []
    developers: list[str] = []
    
    # Financial
    amounts: list[float] = []
    square_feet: float = 0.0
    units: int = 0
    megawatts: float = 0.0
    
    # Source metadata
    source_tier: int = 3           # 1=primary/authoritative, 5=aggregator
    source_authority: str = "secondary"  # primary or secondary
    
    # Scoring (10 dimensions)
    financial_magnitude_score: float = 0.0
    party_significance_score: float = 0.0
    # ... all 10 scores
    composite_score: float = 0.0
    tier: str = ""                 # tier_1_must_cover through rejected
```

**`age_hours()` method**:
```python
def age_hours(self) -> float:
    try:
        pub = datetime.fromisoformat(self.publication_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - pub).total_seconds() / 3600
    except Exception:
        return 999.0
```

**`from_rss_entry()` factory**: Creates a `CanonicalItem` from a feedparser entry dict + source config dict. Sets source_tier, source_authority, primary_sector from config. Standardizes dates and URLs.

### 4d. intelligence_object.py (498 lines)

Groups multiple articles about the same event into one IntelligenceObject. This is the critical innovation — without it, 3 outlets covering the same $500M acquisition would consume 3 slots in a 10-story slate.

**Controlled vocabularies**:
```python
class ObjectClass:
    DISCRETE_EVENT = "discrete_event"    # Single transaction or decision
    EVENT_UPDATE = "event_update"        # New development on known event
    DATA_RELEASE = "data_release"        # Statistical or economic data
    MARKET_MOVEMENT = "market_movement"  # Price/rate movement
    TREND = "trend"                      # Emerging pattern
    DISCLOSURE = "disclosure"            # Filing or regulatory disclosure
    ANALYTICAL_FINDING = "analytical_finding"  # Research conclusion
```

**Schema versioning**: `SCHEMA_VERSION = 1` — must be incremented when the meaning of any existing field changes, so persisted objects remain readable.

**Key operations**:
- `normalize_amount(value)`: Standardizes dollar amounts — removes spaces, normalizes "million"/"mm" → "m", "billion"/"bn" → "b"
- `extract_entities(text)`: Pulls companies, people, locations using entity recognition
- `merge_into_object(items)`: Collapses multiple articles into one IntelligenceObject — combines entities, deduplicates sources, computes corroboration metadata, counts independent domains

### 4e. classification.py (295 lines)

**Source-based priors** (`_SOURCE_SECTOR_PRIORS`, 70+ entries):
```
"The Real Deal" → commercial_real_estate
"PE Hub" → private_equity
"Data Center Dynamics" → data_centers
"Utility Dive" → energy
"American Banker" → banking_credit
"Federal Reserve" → fed_macro
"NYC Department of City Planning" → local_government
... and 60+ more
```

**Regex signal patterns** (`_SECTOR_SIGNALS`, compiled into `_SECTOR_SIGNALS_COMPILED`):

Each sector has a single combined regex pattern with alternation (`|`). For instance, the CRE pattern (line 42-47):
```python
r"\b(?:multifamily|apartment building|office building|retail center|industrial property|warehouse|"
r"mixed.use|commercial real estate|cap rate|occupancy|tenant|landlord|lease|sq.?ft|"
r"square feet|cmbs|noi|dscr|ltv|refinanc\w*|bridge loan|construction loan|"
r"ground lease|sale.leaseback|joint venture.*real estate)\b"
```

The PE pattern (line 48-52):
```python
r"\b(?:buyout|take.private|leveraged buyout|growth equity|platform acquisition|"
r"add.on acquisition|sponsor.*exit|continuation (?:fund|vehicle)|secondary sale|"
r"gp.led|fund close|fundraising|private credit|direct lending|nav financing|"
r"subscription facility|structured equity|portfolio company|carried interest)\b"
```

**`_score_signal_matches()`**: Counts pattern matches per sector, returns density (0.0–1.0) = `matches / total_patterns`.

**`classify_item()`** — the full classification pipeline:
1. Check if item already has a primary_sector from source config prior
2. Run `classify_source_prior()` — match source name against known mappings
3. Run `classify_regex_signals()` — score all 7 sectors by pattern density
4. Primary sector = highest-scoring sector
5. Secondary sectors = all sectors with significant signal
6. Classification confidence = density score of winning sector
7. Classification method = which layer determined the result

### 4f. scoring_engine.py (416 lines) — FULLY COVERED IN DATA FLOW SECTION 5 ABOVE

See the scoring section in the Complete Data Flow. All 10 dimensions, their formulas, threshold buckets, and weight application are documented there.

### 4g. ranking.py (296 lines)

**`rank_within_sector(items, sector)`** (lines 36–46):
```python
sector_items = [
    item for item in items
    if item.primary_sector == sector and item.tier != "rejected"
]
sector_items.sort(key=lambda x: x.composite_score, reverse=True)
return sector_items
```

**`apply_diversity_controls()`** (lines 49–156):
Enforces editorial diversity with configurable thresholds:
- `max_single_subsector_pct` (default 40%): No single subsector should dominate
- `max_single_source_pct` (default 25%): Prevent one publication from filling the slate
- `max_single_company_pct` (default 20%): Prevent one entity from dominating
- `min_subsectors` (default 3): Ensure breadth of coverage

When a constraint would be violated, the algorithm replaces the lowest-ranked excess items with the highest-ranked items from diverse subsectors/sources.

---

## 5. editorial_intelligence.py — Deterministic Editorial Brain (912 lines)

### Editorial Constitution

The scorer is intentionally inspectable. It rewards: consequence, novelty, conflict, explanatory value, culture, human stakes, evidence, and Light Tower's right to add value. Routine transactions are penalized even when they contain a large dollar amount.

### Key Constants

```
MUST_READ_THRESHOLD           = 56   ← minimum editorial score for consideration
FLAGSHIP_CANDIDATE_THRESHOLD  = 72   ← qualifies for Flagship Analysis
DEAL_TAPE_THRESHOLD           = 34   ← minimum for Deal Tape entry
DAILY_RESEARCH_FLOOR          = 24   ← minimum for daily-depth research queue
AUTO_PUBLISH_BRIEF_FLOOR      = 24   ← minimum for auto-publishable briefs
DEFAULT_DAILY_ARTICLE_TARGET  = 3    ← target publishable pieces per day
```

### The 6 Franchises (Recurring Analytical Frames)

1. **Credit Committee Theater** — "What the structure reveals about the lender's real risk test."
2. **Five Minutes Before Maturity** — "How time, extensions, and refinancing pressure redistribute bargaining power."
3. **Who Got Paid / Who Got Stuck** — "Follow the economics through every party rather than repeating the transaction headline."
4. **What the Press Release Left Out** — "Separate the announcement from the constraints, incentives, and unanswered questions."
5. **Capital After Dark** — "Where finance meets status, culture, politics, entertainment, and the life of a city."
6. **The Most Expensive Assumption** — "Identify the premise on which the capital plan quietly depends."

### Event Similarity Algorithm

```python
def event_similarity(left, right) -> float:
    # Exact URL match → 1.0
    if left_url == right_url: return 1.0

    # Tokenize titles (remove stopwords, min 3 chars)
    title_score = jaccard(tokens(left["title"]), tokens(right["title"]))
    company_score = jaccard(entities(left, "companies"), entities(right, "companies"))
    amount_score = jaccard(entities(left, "amounts"), entities(right, "amounts"))
    market_score = jaccard(entities(left, "markets"), entities(right, "markets"))
    asset_score = jaccard(entities(left, "asset_classes"), entities(right, "asset_classes"))

    # Boosted mode: shared amount + minimal title overlap → likely same event
    if amount_score and title_score >= 0.15:
        return min(1.0, 0.64 + 0.22*title_score + 0.09*company_score
                         + 0.03*market_score + 0.02*asset_score)
    
    # Standard mode
    return 0.55*title_score + 0.20*company_score + 0.15*amount_score
           + 0.05*market_score + 0.05*asset_score
```

**`event_fingerprint(members)`** — creates a stable event ID:
1. Collect title tokens appearing in ≥50% of member articles (up to 12)
2. Collect companies (up to 5), amounts (up to 4), markets (up to 3), assets (up to 3)
3. Concatenate with `|` delimiters
4. `SHA-256(key.encode("utf-8")).hexdigest()[:20]` → 20-char stable ID

**Greedy clustering** (`cluster_events`, threshold=0.61):
- For each candidate, find the best-matching existing cluster
- If best score ≥ 0.61, add to that cluster
- Otherwise, create a new cluster
- Each cluster becomes one *event*

### Archive Matching

`archive_matches(event, archive_records, threshold=0.38)`:

Multi-dimensional same-event detection against published Light Tower articles:

```
Same-event signals (ANY of these match):
├─ Title token overlap ≥ 0.57
├─ Dollar amount overlap + context score ≥ 0.16
├─ Street address overlap + context score ≥ 0.14
├─ Entity overlap + context score ≥ 0.24
└─ Context score alone ≥ 0.38
```

- `_dollar_amount_values()`: Extracts `$X (million|billion|trillion)` normalized to integer dollars
- `_street_addresses()`: Regex for `\d{1,5} ... street|st|avenue|ave|road|rd|boulevard|blvd...`
- `_archive_is_recent()`: Checks candidate date within 7 days of record date

### Must-Read Scoring

`score_event()` computes 9 dimensions. See the detailed breakdown in the Data Flow section. Summary:

| Dimension | Max | What Drives It |
|-----------|-----|----------------|
| Consequence | 15 | Material transactions, big numbers, distress/policy topics |
| Novelty | 15 | "First/largest/record" patterns, cross-source corroboration |
| Conflict & Power | 15 | Default/foreclosure/bankruptcy/lawsuit patterns |
| Explanatory Value | 15 | Topic breadth, causal language ("because", "pressure") |
| Cultural Relevance | 10 | Sports, entertainment, tech, status, cities, climate, politics |
| Human Stakes | 10 | Tenant/resident/worker language |
| Evidence Depth | 10 | Source tiers, primary sources, source count |
| Right to Win | 10 | LTG topic alignment (capital markets, CMBS, distress) |
| Conversation | 10 | Derived from conflict + culture + novelty |

**Penalties**:
- **Routine** (–18): Formulaic language ("provides $X million loan", "signs X sq ft lease") — unless countervailing signals
- **Archive repeat** (up to –18): Recent same-event coverage → –18, or 9 × published_priors + 3 × recent_memory_matches
- **Audience adjustment** (±5): Learned weights from `audience-signals.json`

---

## 6. editorial_room.py — The Assigning Editor & Skeptic (352 lines)

### The Editorial Constitution (lines 14–19)

```
Light Tower publishes only when it can make a smart reader see a capital
decision differently. Accuracy is the floor. The work must add consequence,
mechanism, human or institutional stakes, candor, and a bounded point of
view. Routine facts belong in the deal tape. Wit must be earned by a true
observation. A valid editorial outcome is to kill, shorten, or defer a story.
```

### Deterministic Room Plan (lines 42–84)

The safe plan used when an LLM critique is unavailable or inappropriate:

```python
def deterministic_room_plan(editorial_event, dossier) -> dict:
    desired = editorial_event.get("provisional_format", "brief")
    final_format = desired
    
    # Downgrade rules
    if desired == "flagship" and not dossier.get("longform_allowed"):
        final_format = "brief"
    elif desired == "culture_signal" and dossier.get("independent_source_count", 0) < 2:
        final_format = "brief"
    
    # Hard evidence floor
    if dossier.get("evidence_level") == "insufficient":
        final_format = "deal_tape"
    
    return {
        "decision": "write" if final_format != "deal_tape" else "deal_tape",
        "final_format": final_format,
        "angle": "Explain the decision, constraint, and consequence beneath the event.",
        "skeptic_objections": [
            "Do not claim a market-wide shift from one transaction.",
            "Do not infer unreported motives or private negotiations.",
        ],
        ...
    }
```

### LLM Editorial Room Call (lines 110–352)

```python
def run_editorial_room(editorial_event, dossier, *, api_key, editorial_priors, provider):
    fallback = deterministic_room_plan(editorial_event, dossier)
    if not api_key or fallback["decision"] == "deal_tape":
        return fallback
    
    # Call DeepSeek with editorial constitution + current slate context
    result = call_deepseek(prompt, api_key, ...)
    
    # Extract: decision, final_format, angle, why_now, skeptic_objections,
    #          reporting_gaps, human_stakes, concrete_detail, kill_reason
    
    return result
```

### The Daily-Depth Brief Override Guard (lines 86–107)

This is one of the most important safeguards in the entire system:

```python
def _daily_depth_brief_is_supported(editorial_event, dossier, result) -> bool:
    if editorial_event.get("selection_tier") != "daily_depth":
        return False
    if editorial_event.get("legal_or_allegation_risk"):
        return False
    if dossier.get("evidence_level") == "insufficient":
        return False
    if int(dossier.get("usable_full_text_count") or 0) < 1:
        return False
    if len(dossier.get("reported_facts") or []) < 3:
        return False
    
    # Check that the LLM's objections don't contain hard-stop patterns
    risk_text = json.dumps({
        "kill_reason": result.get("kill_reason"),
        "reporting_gaps": result.get("reporting_gaps"),
        "skeptic_objections": result.get("skeptic_objections"),
    })
    return not _DAILY_DEPTH_HARD_STOP.search(risk_text)
```

The `_DAILY_DEPTH_HARD_STOP` regex blocks:
```
allegation, alleged, lawsuit, litigation, criminal, fraud, indicted, charged,
legal risk, conflicting facts, contradiction, source authenticity, fabricate,
cannot verify, unsupported number/claim, duplicate, already covered
```

**The override logic**: If the deterministic contract says "supported" (≥1 full text, ≥3 facts, no legal risk, no hard-stop patterns) but the LLM says "kill", the deterministic plan **overrides the LLM**. The rationale: "The editorial-room model cannot turn single-source status or missing human stakes into an automatic veto when the deterministic record contains retrieved full text and at least three source-mapped facts."

---

## 7. editorial_pipeline.py — The 7-Stage Article Generator (916 lines)

### The `EditorialPipeline` Class

```python
class EditorialPipeline:
    def __init__(self, api_key="", provider=None):
        self.api_key = api_key
        self.provider = dict(provider or {})
        self.stages_run = []
        self.errors = []
```

### Stage 1: Analytical Brief

```python
def stage_analytical_brief(self, item, dossier=None) -> dict:
    brief = build_analytical_brief(item, dossier)
    # Returns: central_financial_question, core_tension, thesis,
    #          article_architecture, article_depth, parties_and_incentives,
    #          transaction_economics, key_numbers, unknowns
    
    # Optional LLM enhancement
    if _HAS_LLM and self.api_key:
        brief = enhance_brief_with_llm(brief, item, self.api_key)
    return brief
```

### Stage 2: Assemble Writing Prompt

This stage builds the complete LLM prompt. It's heavily detailed because it controls the entire article output:

**System prompt**: From `get_sector_prompt(item.primary_sector)` — sector-specific journalistic voice.

**User prompt** (constructed in lines 113–204): Contains:
1. **STORY**: headline, source name, source tier, sector, summary
2. **SOURCE DOSSIER**: the complete factual boundary (24,000 chars from `dossier_prompt_payload()`)
3. **ANALYTICAL BRIEF**: central question, core tension, thesis, parties+incentives (1,500 chars), transaction economics (1,000 chars), key numbers (800 chars), unknowns (500 chars)
4. **ARTICLE STRUCTURE**: from `article_architecture`
5. **EDITORIAL FORMAT**: label + "HARD LENGTH CONTRACT: X-Y words"
6. **12 WRITING RULES** (reproduced verbatim here):

```
1. Open with the most revealing fact, number, or tension from the brief
   — not a generic announcement.
2. Build the article around the central question and thesis.
3. Interpret the key numbers — don't just list them. Explain what they mean.
4. Name the parties. Explain what each gains and risks.
5. Distinguish clearly between reported facts, reasonable inferences, and unknowns.
6. Vary sentence rhythm. Avoid formulaic openings like
   "The most important X is not Y."
7. End with the unresolved question or next signal to watch.
8. Do not use "signals," "highlights," "underscores," or "showcases"
   as analytical verbs.
9. Every factual and numerical claim must be supported by the source dossier.
10. Label calculations and reasonable inferences explicitly.
    Never invent a market statistic, return target, tenant, financing term,
    motive, quote, or source.
11. The sources array must contain only the canonical article URLs provided
    in the dossier. Do not substitute publication homepages.
12. Never mention an internal editorial, ranking, composite, or significance
    score in public copy.
```

**Required JSON output fields** (lines 164–201):
```json
{
  "title": "Specific headline under 90 characters",
  "subtitle": "One-sentence consequence under 150 characters",
  "slug": "lowercase-kebab-case-max-six-words",
  "category": "Capital Markets | Market Analysis | Debt & Equity | ...",
  "meta_description": "Specific description under 160 characters",
  "tags": ["three", "to", "five", "specific", "tags"],
  "body_html": "<p>Complete article using paragraph tags only.</p>",
  "data_points": [{"label": "...", "value": "...", "source_url": "..."}],
  "sources": [{"name": "Exact source name", "url": "Exact dossier URL"}],
  "excerpt": "One- or two-sentence preview",
  "narrative_ledger": {
    "anchor": "Reported anchor",
    "tension": "Economic tension",
    "cast": ["Party: documented constraint or clock"],
    "mechanism": "Supported financial or operating mechanism",
    "claim": "Bounded interpretation",
    "reader_consequence": "What a market participant should test",
    "reported_facts": ["Reported fact"],
    "interpretations": ["Clearly labeled inference"],
    "open_questions": ["Material unknown"],
    "scene": {"used": false, "detail": "", "source_basis": ""}
  },
  "excellence_ledger": {
    "why_now": "Why this deserves attention now",
    "original_inference": "The article's one bounded added insight",
    "counterargument": "Strongest plausible alternative explanation",
    "concrete_detail": "A detail supported by a named source",
    "human_stakes": "The supported human, institutional, or physical consequence",
    "reader_value": "What the reader understands or can test after reading",
    "memorable_line": "One exact sentence that appears verbatim in body_html",
    "claim_evidence": [{"claim": "Factual claim", "source_url": "Exact dossier URL"}]
  }
}
```

The ledgers are **internal audit evidence** and are stripped from public HTML (stored in `article["_editorial_control"]`) — but they remain in the run audit record.

### Stage 3: Draft

```python
def stage_draft(self, prompt_context) -> dict:
    raw = call_deepseek(
        prompt_context["user_prompt"],
        self.api_key,
        max_tokens=8000,
        temperature=0.2,
        json_mode=True,
        system=prompt_context["system_prompt"],
        provider=self.provider or None,
    )
    article = _extract_json(raw, required_fields=["body_html", "title", "excerpt", "sources", "excellence_ledger"])
    # Must have non-empty sources array
    if not isinstance(article.get("sources"), list) or not article["sources"]:
        raise ValueError("LLM response did not include a non-empty sources array")
    return {"status": "completed", "article": article}
```

**Critical**: `_extract_json()` finds the first `{...}` in the response. This handles cases where DeepSeek wraps the JSON in explanatory text (despite `json_mode=True`). Uses a simple regex `r"\{[\s\S]*\}"` then `json.loads()`. Returns empty dict on failure.

### Stage 4: Financial Review

```python
def stage_financial_review(self, article, brief, dossier=None, article_format=None) -> dict:
    prompt = f"""You are a financial editor reviewing an article for accuracy.
    
    ARTICLE: {body_clean[:8000]}
    EVIDENCE: {evidence_text}
    BRIEF: {brief_summary}
    
    Check for:
    1. Are any financial figures incorrect or unsupported?
    2. Does the article explain what the numbers MEAN?
    3. Are any claims about returns, valuations, or market conditions unsupported?
    4. Does the article distinguish reported facts from calculated metrics?
    5. Is the incentive analysis clear?
    
    CALIBRATION RULES:
    - Judge against what the dossier actually discloses
    - For a 240-430 word brief, one credible source can support a bounded article
    - Do NOT fail for undisclosed loan pricing, returns, valuations
    - Fail if the article invents them, hides the gap, or makes unsupported conclusions
    - Do NOT require financial figures when the source contains none
    - A reported claim may be attributed to its named publication
    - Set passed=true when there is no specific factual defect
    
    Return JSON: {{issues, passed, score_1_10, summary}}
    """
    raw = call_deepseek(prompt, self.api_key, max_tokens=4000, temperature=0.1, json_mode=True)
    result = _extract_json(raw)
    result["passed"] = result.get("passed") is True
    return result
```

The calibration rules (lines 292–308) are the most important part — they prevent the financial reviewer from demanding information that legitimate financial journalism doesn't always have, while still catching invented numbers.

### Stage 5: Editorial Review

```python
def stage_editorial_review(self, article) -> dict:
    prompt = f"""You are an editorial reviewer. Score this article on writing quality.
    
    ARTICLE: {body_clean[:8000]}
    
    Check for:
    1. Opening quality: Hook with something specific?
    2. Structure: Logical flow or formulaic template?
    3. Sentence quality: Varied length/structure? Repetitive patterns?
    4. AI language: "signals," "highlights," "underscores," "showcases"?
    5. Conclusion: Right implication, not vague forward look?
    6. Voice: Knowledgeable professional, not institution?
    
    Return JSON: {{issues, passed, score_1_10, opening_quality, worst_sentence, summary}}
    """
    raw = call_deepseek(prompt, self.api_key, max_tokens=4000, temperature=0.1, json_mode=True)
    result = _extract_json(raw)
    result["passed"] = result.get("passed") is True
    return result
```

### Stage 6: Fact Verification (DETERMINISTIC)

```python
def stage_fact_verification(self, article, brief, dossier=None) -> dict:
    # 1. Validate source URLs: every article source must be in dossier
    for source in generated_sources:
        url = str(source.get("url", "")).strip()
        if url not in canonical_urls:
            issues.append(f"Article source not in dossier: {url}")
    
    # 2. Check key numbers from brief appear in article
    for kn in brief.get("key_numbers", [])[:3]:
        if kn.get("number", "") and num not in body:
            issues.append(f"Key number '{num}' from brief not found")
    
    # 3. Scan for unsupported claim phrases
    UNSUPPORTED = ["is expected to", "analysts predict", "sources say",
                    "widely viewed as", "market believes"]
    for phrase in UNSUPPORTED:
        if phrase in body.lower():
            issues.append(f"Potentially unsupported claim: '{phrase}'")
    
    # 4. Deterministic fact audit via fact_extractor
    audit = audit_article_facts(body, dossier["source_facts"], source_tier=source_tier)
    if audit.get("hold_for_review"):
        issues.append(f"Unverified claims: {len(unmatched_amounts)} amounts, "
                      f"{len(unmatched_companies)} companies, {len(unmatched_addresses)} addresses")
    
    passed = len(issues) == 0
    return {"issues": issues, "passed": passed, "score_1_10": 10 if passed else 6}
```

### Stage 7: Final Revision

Only runs if there are issues to fix:

```python
def stage_final_revision(self, article, prompt_context, financial_review, editorial_review, fact_issues):
    all_issues = (financial_review.get("issues", []) +
                  editorial_review.get("issues", []) +
                  fact_issues.get("issues", []))
    if not all_issues:
        return {"status": "no_issues", "article": article}  # Skip — article is clean
    
    prompt = f"""REVISE this article to fix the following issues.
    
    CURRENT ARTICLE JSON: {original_json}
    SOURCE DOSSIER: {dossier_text}
    ISSUES TO FIX: {all_issues}
    
    Rewrite the COMPLETE article as JSON. Fix every issue.
    Delete unsupported claims when the dossier supplies no valid replacement.
    Do not introduce new unsupported claims, numbers, names, or motives.
    Maintain the evidence-bounded thesis and word contract.
    """
    raw = call_deepseek(prompt, self.api_key, max_tokens=10000, temperature=0.15, json_mode=True)
    revised = _extract_json(raw, required_fields=["body_html", "title", "excerpt", "sources", "excellence_ledger"])
    revised = {**article, **revised}  # Merge with original for any missing fields
    return {"status": "revised", "article": revised}
```

### Full Pipeline — `run()` Method (lines 556–700)

```python
def run(self, item, dossier=None, api_key="", article_format=None) -> dict:
    if api_key:
        self.api_key = api_key
    
    # Stage 1
    brief = self.stage_analytical_brief(item, dossier)
    
    # Stage 2
    prompt_ctx = self.stage_assemble_prompt(item, brief, dossier, article_format)
    prompt_ctx["dossier"] = dossier
    
    # Stage 3
    draft_result = self.stage_draft(prompt_ctx)
    if draft_result.get("status") == "skipped":
        return {"status": "no_llm", "article": None}
    
    article = draft_result["article"]
    
    # Stage 4
    fin_review = self.stage_financial_review(article, brief, dossier, article_format)
    
    # Stage 5
    ed_review = self.stage_editorial_review(article)
    
    # Stage 6
    fact_issues = self.stage_fact_verification(article, brief, dossier)
    
    # Stage 7
    revision = self.stage_final_revision(article, prompt_ctx, fin_review, ed_review, fact_issues)
    
    article = revision.get("article", article)
    
    return {
        "item_id": item.item_id,
        "headline": item.headline,
        "article": article,
        "stages": self.stages_run,
        "errors": self.errors,
        "status": "completed"
    }
```

---

## 8. research_dossier.py — Multi-Source Evidence Ledger (236 lines)

### Fact Extraction

**`_fact_candidates(value)`** (lines 23–33):
```python
def _fact_candidates(value) -> list[str]:
    facts = []
    for sentence in _sentences(value):  # 7-55 word sentences
        if re.search(
            r"(?:\$[\d,.]+|\b\d+(?:\.\d+)?%|\b\d{4}\b|\b(?:said|reported|announced|filed|"
            r"approved|acquired|sold|borrowed|lent|matures?|occupancy|units?|square feet)\b)",
            sentence, re.IGNORECASE,
        ):
            facts.append(sentence)
    return facts
```

A sentence is a "fact candidate" if it contains ANY of:
- Dollar amounts (`$X`)
- Percentages (`X%`)
- Years (`20XX`)
- Attribution verbs (`said`, `reported`, `announced`, `filed`)
- Transaction verbs (`approved`, `acquired`, `sold`, `borrowed`, `lent`)
- Real estate metrics (`matures`, `occupancy`, `units`, `square feet`)

### Quote Extraction

**`_quotes(value)`** (lines 36–38):
```python
def _quotes(value) -> list[str]:
    found = re.findall(r'["\u201c]([^"\u201d]{20,280})["\u201d]', str(value or ""))
    return [re.sub(r"\s+", " ", quote).strip() for quote in found[:3]]
```

Matches both straight quotes (`"`) and curly quotes (`\u201c`/`\u201d`). Filters to 20–280 character quotes. Returns at most 3.

### The Main Function — `build_research_dossier()`

```python
def build_research_dossier(editorial_event, *, fetched_text_by_url=None, archive_records=()) -> dict:
    sources = []
    reported_facts = []
    quote_ledger = []
    seen_domains = set()
    
    for source in editorial_event.get("sources", []):
        url = str(source.get("url", ""))
        domain = str(source.get("domain") or _independent_domain(url))
        full_text = sanitize_untrusted_source(fetched.get(url, ""))
        summary = sanitize_untrusted_source(source.get("summary", ""))
        
        source_facts = _fact_candidates(f"{summary} {full_text}")[:8]
        source_quotes = _quotes(full_text)
        
        sources.append({
            "name": source.get("source") or domain,
            "url": url,
            "domain": domain,
            "published": source.get("published"),
            "authority": source.get("source_authority", "secondary"),
            "tier": int(source.get("source_tier", 3) or 3),
            "summary": summary,
            "full_text_excerpt": full_text[:6500],
            "reported_facts": source_facts,
            "quotes": source_quotes,
        })
        
        seen_domains.add(domain)
        reported_facts.extend(
            {"fact": fact, "source_url": url, "source_name": domain}
            for fact in source_facts
        )
    
    # Compute evidence metrics
    independent_source_count = len({d for d in seen_domains if d})
    usable_full_text_count = sum(bool(s["full_text_excerpt"]) for s in sources)
    
    if independent_source_count >= 3 and usable_full_text_count >= 2:
        evidence_level = "deep"
    elif independent_source_count >= 2 or [s for s in sources if s["authority"] == "primary"]:
        evidence_level = "adequate"
    elif independent_source_count >= 1:
        evidence_level = "thin"
    else:
        evidence_level = "insufficient"
    
    return {
        "sources": sources,
        "reported_facts": reported_facts,
        "quote_ledger": quote_ledger,
        "source_facts": reported_facts,  # alias for fact verification
        "independent_source_count": independent_source_count,
        "usable_full_text_count": usable_full_text_count,
        "evidence_level": evidence_level,
        "longform_allowed": evidence_level in ("deep", "adequate"),
        "reporting_gaps": [...],
    }
```

---

## 9. generation.py — Sector-Aware Prompt Routing (439 lines)

### Sector-to-Prompt Mapping

```python
SECTOR_PROMPTS = {
    "private_equity": PE_SYSTEM_PROMPT,      # from sector_prompts.py
    "data_centers": DC_SYSTEM_PROMPT,
    "energy": ENERGY_SYSTEM_PROMPT,
    "banking_credit": BANKING_SYSTEM_PROMPT,
    "fed_macro": FED_SYSTEM_PROMPT,
    "local_government": LOCALGOV_SYSTEM_PROMPT,
    # commercial_real_estate → SYSTEM_PROMPT_ENHANCED (from enhanced_prompts.py)
}
```

### Sector-to-Category Mapping

```python
SECTOR_CATEGORIES = {
    "private_equity": "Deal Intelligence",
    "data_centers": "Market Analysis",
    "energy": "Market Analysis",
    "banking_credit": "Debt & Equity",
    "fed_macro": "Policy & Regulation",
    "local_government": "Policy & Regulation",
    "commercial_real_estate": "Capital Markets",
}
```

### Article Type Routing (60+ mappings)

The `ARTICLE_TYPES` dict maps `event_type` → `article_format`:

| Sector | Event Type | Article Format |
|--------|-----------|----------------|
| PE | fund_close, fund_launch | fundraising_analysis |
| PE | buyout, dividend_recap, gp_stake_sale, take_private, growth_equity | transaction_brief |
| PE | exit_sale | exit_analysis |
| PE | add_on_acquisition, sponsor_acquisition | deal_analysis |
| Data Centers | dc_development | development_brief |
| Data Centers | dc_lease | lease_analysis |
| Data Centers | dc_acquisition | deal_analysis |
| Data Centers | dc_power_agreement | energy_brief |
| Energy | power_agreement, ppa_signing, interconnection_approval | energy_brief |
| Energy | project_finance, plant_acquisition, loan_sale | deal_analysis |
| Energy | regulatory_decision, rate_case | policy_analysis |
| Banking | bank_earnings | data_note |
| Banking | loan_origination, private_credit_deal | transaction_brief |
| Banking | regulatory_action, enforcement_action | policy_analysis |
| Banking | loan_sale, credit_event | deal_analysis |
| Fed/Macro | fomc_decision, fomc_minutes | macro_brief |
| Fed/Macro | inflation_report, employment_report, gdp_report | data_note |
| CRE | property_acquisition, portfolio_acquisition | deal_analysis |
| CRE | refinancing, note_sale | transaction_brief |
| CRE | construction_financing, development_financing | development_brief |
| CRE | foreclosure, receivership | distress_brief |
| CRE | major_lease | lease_analysis |
| CRE | rezoning | policy_analysis |

---

## 10. content_governance.py — The Safeguards (217 lines)

**This module deliberately does not call an LLM.** It is the independent control layer around model output.

### Prompt Injection Defense

```python
PROMPT_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?"
    r"|disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|forget\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|system\s+prompt|developer\s+message|reveal\s+(?:your|the)\s+instructions?"
    r"|act\s+as\s+(?:a\s+)?(?:different|new)\s+(?:assistant|system))",
    re.IGNORECASE,
)
```

`sanitize_untrusted_source()` applies this regex to ALL source material before it's included in prompts. Matched text is replaced with `"[editorial instruction removed]"`.

### Boilerplate Detection

```python
GENERIC_EDITORIAL_RE = re.compile(
    r"(?:the headline is therefore a doorway|buildings are where private capital|"
    r"the capital question is simple and difficult|the built world is not merely the background)",
    re.IGNORECASE,
)
```

These are known generational artifacts — phrases the LLM over-uses. Any article containing them is flagged.

### Near-Duplicate Detection

```python
def near_duplicate_matches(title, records, *, threshold=0.86) -> list[str]:
    title_key = normalise_title(title)
    for record in records:
        existing_key = normalise_title(str(record.get("title", "")))
        sequence = SequenceMatcher(None, title_key, existing_key).ratio()
        token = _token_similarity(title, existing)  # Jaccard index
        if title_key == existing_key or sequence >= threshold or token >= 0.82:
            matches.append(f"near-duplicate of {slug} ({max(sequence, token):.0%} similarity)")
    return matches
```

Three detection methods:
1. **Exact match** of normalized titles
2. **Sequence similarity** ≥ 0.86 (Python's `difflib.SequenceMatcher`)
3. **Token similarity** ≥ 0.82 (Jaccard index of word sets, stopwords removed)

### The Complete Quality Gate — `independent_quality_issues()`

This function runs all 10 checks and returns a list of error strings. An empty list means the article passes every independent quality gate.

```
Check 1:  Fallback writing → hold for review
Check 2:  Word count within format-specific bounds
Check 3:  ≥2 <h2> sections (full articles)
Check 4:  No boilerplate language
Check 5:  Voice quality (editorial_quality_issues)
Check 6:  Valid source URLs (https:// required, no example.com)
Check 7:  No repeated paragraph structure (≥4 paras, <90% unique)
Check 8:  Fact audit (amounts, companies, addresses match dossier)
Check 9:  Semantic claim audit (central claim supported by sources)
Check 10: (Handled separately) near_duplicate_matches against published archive
```

---

## 11. fact_extractor.py — Deterministic Fact Verification (264 lines)

### Amount Extraction

```python
def extract_amounts(text) -> list[dict]:
    for match in re.finditer(
        r'\$\s*([\d,.]+(?:\.\d+)?)\s*(million|billion|trillion|mm|bn|m|b)?\b',
        str(text or ""), re.IGNORECASE
    ):
        amounts.append({
            "raw": match.group(0).strip(),
            "number": match.group(1),
            "unit": (match.group(2) or "").lower(),
            "context": text[max(0, match.start()-60) : min(len(text), match.end()+60)].strip(),
        })
    return amounts
```

Captures dollar amounts with 60 characters of surrounding context for each match.

### Company Extraction

Uses a hardcoded list of 60+ known CRE/finance institutions:

```python
_KNOWN_INSTITUTIONS = [
    "blackstone", "brookfield", "apollo", "starwood", "ares", "kkr",
    "carlyle", "tpg", "cerberus", "sl green", "vornado", "related", "tishman",
    "jpmorgan", "jp morgan", "goldman", "morgan stanley", "wells fargo",
    "bank of america", "citigroup", "deutsche bank", "barclays",
    "federal reserve", "fdic", "occ", "treasury", "fannie mae", "freddie mac",
    "hud", "cbre", "jll", "cushman", "eastdil", "newmark", "meridian",
    "walker & dunlop", "berkadia", "northmarq", "greystone", "keybank",
    "pnc", "m&t bank", "signature bank", "new york community bank",
    "connectone", "oceanfirst", "flushing financial", "valley national",
]
```

Case-insensitive matching. Each match includes 30 characters of surrounding context.

### Address Extraction

```python
def extract_addresses(text) -> list[str]:
    for match in re.finditer(
        r"\b\d{1,5}\s+(?:(?:west|east|north|south|w|e)\s+)?"
        r"[a-z0-9'-]+(?:\s+[a-z0-9'-]+){0,2}\s+"
        r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|terrace|place)\b",
        str(text or ""), re.IGNORECASE,
    ):
        addresses.append(match.group(0).strip())
    return addresses
```

### Fact Audit — `audit_article_facts()`

Cross-references article body against dossier source facts:

```python
def audit_article_facts(body_html, source_facts, source_tier=3) -> dict:
    article_amounts = extract_amounts(body_text)
    article_companies = extract_companies(body_text)
    article_addresses = extract_addresses(body_text)
    
    # Match against source facts
    source_amounts = set()
    source_company_names = set()
    source_addresses = set()
    
    for fact in source_facts:
        source_amounts.update(normalize_amount(a["number"]) for a in extract_amounts(fact["fact"]))
        source_companies.update(c["name"] for c in extract_companies(fact["fact"]))
        source_addresses.update(extract_addresses(fact["fact"]))
    
    # Find unmatched
    unmatched_amounts = [a for a in article_amounts if not any(
        normalize_amount(a["number"]) in sa for sa in source_amounts
    )]
    unmatched_companies = [c for c in article_companies if c["name"] not in source_companies]
    unmatched_addresses = [a for a in article_addresses if a not in source_addresses]
    
    # Lower tiers get more leniency
    hold_thresholds = {1: 1, 2: 1, 3: 2, 4: 3, 5: 5}
    hold = len(unmatched_amounts) + len(unmatched_companies) >= hold_thresholds.get(source_tier, 2)
    
    return {
        "article_amounts": article_amounts,
        "unmatched_amounts": unmatched_amounts,
        "unmatched_companies": unmatched_companies,
        "unmatched_addresses": unmatched_addresses,
        "hold_for_review": hold,
    }
```

### Semantic Claim Audit — `audit_claim_semantic()`

Breaks the article's central claim into individual assertions and checks each against source texts:

```python
def audit_claim_semantic(claim, source_texts) -> dict:
    assertions = [a.strip() for a in re.split(r'[;,]|\band\b', claim) if len(a.strip()) > 10]
    
    assertions_found = []
    assertions_missing = []
    
    for assertion in assertions:
        keywords = set(re.findall(r'\b[a-z]{4,}\b', assertion.lower()))
        found = any(
            all(kw in text.lower() for kw in keywords)
            for text in source_texts
        )
        if found:
            assertions_found.append(assertion)
        else:
            assertions_missing.append(assertion)
    
    confidence = len(assertions_found) / len(assertions) if assertions else 0.0
    return {
        "claim_supported": len(assertions_missing) == 0,
        "confidence": confidence,
        "assertions_found": assertions_found,
        "assertions_missing": assertions_missing,
    }
```

---

## 12. v2_editorial.py — Pipeline Bridge (401 lines)

Bridges the typed v2 multi-sector pipeline output into the editorial publishing pipeline.

### Legal Risk Detection

```python
_LEGAL_RISK = re.compile(
    r"\b(?:alleg(?:ation|ed|edly)|lawsuit|litigation|fraud|indict(?:ed|ment)?|"
    r"criminal|charged|investigation|sanction)\b",
    re.IGNORECASE,
)
```

Articles with legal risk are always routed to editorial review.

### Non-Editorial Format Rejection

```python
_NON_EDITORIAL_FORMAT = re.compile(
    r"\b(?:test drive|hands[ -]on|product review|car review|unboxing|buyer(?:'s)? guide|"
    r"how to|podcast|webinar|photo gallery|sponsored content)\b",
    re.IGNORECASE,
)
```

Consumer/tech content patterns — these stories are not financial editorial and are rejected.

### Capital or Policy Anchor Verification

```python
_CAPITAL_OR_POLICY_ANCHOR = re.compile(
    r"\b(?:acquir\w*|buyout|bought|sold|sale|merger|loan|lender|debt|credit|equity|"
    r"financ\w*|fund\w*|capital|invest\w*|bank\w*|refinanc\w*|development|developer|"
    r"construction|project|proposal|approval|permit|zoning|lease|rent|property|housing|"
    r"units?|data cent(?:er|re)|power|grid|infrastructure|federal reserve|"
    r"interest rates?|inflation|regulat\w*|policy|subsid\w*|tax|tariff)\b",
    re.IGNORECASE,
)
```

A story must contain at least one capital or policy anchor term to be eligible. This prevents non-financial stories from entering the pipeline.

### Sector Article Anchors

Per-sector regexes verify the story is actually about that sector. For example:

```python
_SECTOR_ARTICLE_ANCHORS = {
    "commercial_real_estate": re.compile(
        r"\b(?:commercial real estate|real estate|property|properties|office|retail "
        r"(?:property|space|center)|industrial|warehouse|multifamily|apartment|housing|"
        r"units?|hotel|hospitality|development|developer|construction|zoning|land use|"
        r"building|tenant|lease|rent|mortgage|reit)\b", re.IGNORECASE,
    ),
    "private_equity": re.compile(
        r"\b(?:private equity|buyout|portfolio compan(?:y|ies)|take-private|"
        r"growth equity|limited partners?|general partner|fund close|sponsor-backed)\b",
        re.IGNORECASE,
    ),
    "fed_macro": re.compile(
        r"\b(?:federal reserve|\bfed\b|interest rates?|treasur(?:y|ies)|"
        r"bond yields?|inflation|monetary policy|fomc|basis points?)\b", re.IGNORECASE,
    ),
    # ... etc for data_centers, energy
}
```

### `generate_v2_article()` — The Main Bridge Function

```python
def generate_v2_article(candidate, api_key, provider=None) -> dict:
    # Convert candidate to CanonicalItem
    item = candidate_to_canonical(candidate)
    
    # Build dossier if not already present
    dossier = candidate.get("research_dossier") or build_research_dossier(candidate)
    
    # Run the 7-stage editorial pipeline
    pipeline = EditorialPipeline(api_key=api_key, provider=provider)
    result = pipeline.run(
        item,
        dossier=dossier,
        api_key=api_key,
        article_format=candidate.get("editorial_format"),
    )
    
    # Extract article from pipeline result
    article = result.get("article")
    if article is None:
        return None
    
    # Add editorial metadata
    article["editorial_format"] = candidate.get("editorial_format")
    article["must_read_score"] = candidate.get("must_read_score")
    article["selection_tier"] = candidate.get("selection_tier")
    article["franchise"] = candidate.get("franchise", {})
    article["source_name"] = item.source_name
    article["source_url"] = item.source_url
    
    return article
```

---

## 13. edition_manager.py — Daily Edition Builder (293 lines)

### Read Time Calculation

```python
def calculate_read_time(body_html: str) -> int:
    words = len(html_to_text(body_html).split())
    return max(1, round(words / 225))
```

Standard adult reading speed of 225 words per minute.

### Article Summary

```python
def _article_summary(article) -> dict:
    return {
        "event_id": article.get("event_id"),
        "title": article.get("title"),
        "subtitle": article.get("subtitle"),
        "slug": article.get("slug"),
        "url": f"/insights/{article.get('slug')}.html",
        "category": article.get("category"),
        "format": article.get("editorial_format", "brief"),
        "format_label": article.get("editorial_format_label", "Intelligence Brief"),
        "franchise": article.get("franchise"),
        "must_read_score": article.get("must_read_score"),
        "selection_tier": article.get("selection_tier"),
        "read_time": calculate_read_time(str(article.get("body_html", ""))),
        "source_count": len({
            source_url.split("/")[2].lower().removeprefix("www.")
            for source in article.get("sources", [])
        }),
    }
```

`source_count` is computed as unique *domains* (not URLs), removing `www.` prefix.

### Build Edition Document

```python
def build_edition_document(edition_date, selection, articles, run_status) -> dict:
    return {
        "schema_version": 1,
        "type": "insights_edition",
        "date": edition_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": run_status,  # "ready" | "no_publishable_story"
        "articles": [_article_summary(a) for a in articles],
        "deal_tape": [_deal_tape_summary(item) for item in selection.get("deal_tape", [])],
        "editorial_metadata": {
            "edition_date": edition_date.isoformat(),
            "selection_thresholds": {
                "must_read": MUST_READ_THRESHOLD,
                "flagship_candidate": FLAGSHIP_CANDIDATE_THRESHOLD,
                "deal_tape": DEAL_TAPE_THRESHOLD,
            },
            "production_window": f"{edition_date.isoformat()}T07:07:00-04:00/{edition_date.isoformat()}T23:59:59-04:00",
        },
    }
```

This edition document is written to:
- `editions/YYYY-MM-DD.json` — the durable public record
- `latest-edition.json` — always points to today's edition

### Other Output Functions

- `save_publication_decision()`: Writes whether this run requires editorial review (auto-publish vs PR)
- `update_event_memory()`: Appends new event fingerprints to the persistent ledger
- `render_run_summary()`: Generates human-readable Markdown for the GitHub Actions summary
- `write_generated_files()`: Creates the manifest of all generated file paths

---

## 14. Supporting Modules

### 14a. editorial_store.py (57 lines)

Minimal persistence layer for editorial runs and weekly reviews:

```python
def save_editorial_run(payload, run_date=None) -> Path:
    run_date = run_date or datetime.now(timezone.utc).date()
    path = EDITORIAL_RUNS_DIR / f"{run_date.isoformat()}.json"
    path.write_text(_json_safe(payload), encoding="utf-8")
    return path

def load_weekly_editorial_runs(anchor=None) -> list[dict]:
    anchor = anchor or datetime.now(timezone.utc).date()
    monday = anchor - timedelta(days=anchor.weekday())
    runs = []
    for offset in range(5):
        path = EDITORIAL_RUNS_DIR / f"{(monday + timedelta(days=offset)).isoformat()}.json"
        if path.exists():
            runs.append(load_editorial_run(path))
    return runs
```

### 14b. bucketed_editorial.py (359 lines)

Volume-oriented editorial routing to 5 lanes:
- `cre_capital_markets` — refinancing, bridge loans, mortgage, CMBS, defaults
- `cre_transactions_development` — acquisitions, sales, leasing, development, permits
- `banking_credit` — banks, loan losses, charge-offs, FDIC, OCC
- `private_equity_private_capital` — PE, fundraising, institutional allocators, JVs
- `policy_rates_public_markets` — Fed, Treasury, rates, SOFR, FOMC, GDP

Constants: PUBLISH_SCORE = 65, REVIEW_SCORE = 55.

### 14c. story_normalizer.py

- `normalize_stories()`: Strips HTML, extracts entities, standardizes formatting
- `enrich_normalized_story()`: Fetches full text via `trafilatura`, extracts addresses, amounts, parties
- `has_cre_editorial_anchor()`: Validates minimum CRE content for coverage
- `has_reported_amount_at_least_ten_million()`: Minimum deal size gate

### 14d. publish_generated.py (93 lines)

Safe Git publication — ONLY publishes files declared in the generation manifest:

```python
def load_files() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = payload.get("files")
    
    safe = []
    for value in files:
        relative = Path(str(value))
        # Security: no absolute paths, no .. traversal, no .git/ paths
        if relative.is_absolute() or ".." in relative.parts or relative.parts[0] == ".git":
            raise RuntimeError(f"unsafe generated path: {value}")
        # Resolve to verify it's within SITE_ROOT
        resolved = (SITE_ROOT / relative).resolve()
        resolved.relative_to(root)  # Raises ValueError if outside root
        safe.append(normalized)
    
    safe.append(".editorial-state/generated-files.json")  # Always include manifest itself
    return safe
```

### 14e. agent_runtime.py (146 lines)

Local scheduler that enforces the scheduler lease:

```python
def local_scheduler_enabled() -> bool:
    payload = json.loads(SCHEDULER_CONTROL.read_text(encoding="utf-8"))
    return payload.get("active_scheduler") == "local-scheduler"

def preflight() -> dict:
    # 1. Working tree must be clean
    if git_text("status", "--porcelain"):
        raise RuntimeError("runtime worktree is not clean")
    
    # 2. Fetch origin/main
    git("fetch", "origin", "main")
    
    # 3. Compare HEAD with origin/main
    head = git_text("rev-parse", "HEAD")
    remote_main = git_text("rev-parse", "origin/main")
    
    if head == remote_main:
        action = "current"
    elif merge_base_is_ancestor("origin/main", "HEAD"):
        action = "recover_push"    # HEAD ahead → push local commits
    elif merge_base_is_ancestor("HEAD", "origin/main"):
        action = "fast_forward"    # HEAD behind → merge
    else:
        raise RuntimeError("diverged — manual review required")
    
    # 4. Verify HEAD == origin/main after sync
    assert head == remote_main
    return {"head": head, "sync_action": action}
```

### 14f. LinkedIn Distribution Suite

- `linkedin_essay_agent.py`: Generates LinkedIn essays with voice modes (standard/edge/compressed), quality scoring, editorial review. Fallback template-based generation when no API key.
- `linkedin_thread_agent.py`: Multi-post LinkedIn threads
- `linkedin_pdf_scheduler.py` / `linkedin_pdf_post.py`: Schedules/posts PDF carousels
- `linkedin_auth.py`: OAuth token management
- `linkedin_engagement_scraper.py`: Post engagement analytics
- `build_linkedin_post.py`: Templates and formatting
- `article_adapter.py` (862 lines): HTML→Carousel transformation with sentence extraction, tension/analysis word scoring, compact formatting

### 14g. social_image_generator.py

Generates `_social.png` for each article: branded navy/gold background, wrapped title and subtitle text rendered with Pillow, Light Tower mark. Called by Phase 6 of `daily_news_agent.py`.

### 14h. validate_publication.py

Pre-deployment validation of ALL public assets:
- Validates HTML files (well-formed, no broken images, no placeholder text)
- Validates `insights.json` (valid JSON, all required fields)
- Validates `feed.xml` (valid RSS/Atom, required elements)
- Validates `sitemap.xml` (valid XML, all URLs resolve)
- Validates `latest-edition.json` and `editions/` files
- Ensures no internal secrets in public files

### 14i. model_router.py

Provider preflight — pings DeepSeek API, validates key format, confirms model availability. Used by GitHub Actions before the editorial run.

### 14j. cost_tracker.py

Tracks API costs: DeepSeek tokens in/out, NewsAPI calls, estimated dollar costs. `get_costs()` returns cumulative session costs, `reset_costs()` clears tracking.

### 14k. checkpoint.py

Timeout-protected pipeline phases:
```python
PHASE_TIMEOUTS = {
    "gather": 300,     # 5 minutes
    "classify": 120,   # 2 minutes
    "score": 120,
    "enrich": 600,     # 10 minutes (fetching full text)
    "generate": 1800,  # 30 minutes (LLM calls)
    "publish": 300,
}
```

### 14l. Ideas Pipeline

The parallel Ideas pipeline (`/ideas` section) uses a different rubric:
- `ideas_generator_2026.py` (449 lines): 10-dimension Ideas scoring (built_world_specificity, human_drama, power_politics, capital_relevance, aesthetic_design, psychological_depth, narrative_potential, originality, business_relevance, timeliness, evergreen_potential, risk_score)
- `ideas_daily_agent.py`: Daily orchestrator
- `ideas_prompts.py`, `ideas_quality.py`, `ideas_renderer.py`: Writing, quality, rendering

---

## 15. Configuration Layer

### config/sources.json (5094 lines)

150+ news sources across 7 sectors. Each source:

```json
{
  "name": "Commercial Observer",
  "url": "https://commercialobserver.com/feed/",
  "sectors": ["commercial_real_estate", "private_equity"],
  "tier": 1,
  "fetch_frequency_hours": 6,
  "auth_required": false,
  "js_required": false,
  "full_text_available": true,
  "geographic_scope": "nyc",
  "source_type": "industry_publication",
  "active": true,
  "health": {
    "state": "ok",
    "checked_at": "2026-08-03T20:28:43.944335+00:00",
    "http_status": 200,
    "items_in_window": 12,
    "newest_age_hours": 2.3
  }
}
```

Source tiers:
- **Tier 1**: Primary/authoritative (Commercial Observer, Bloomberg, WSJ, Federal Reserve, SEC)
- **Tier 2**: Established publications (Bisnow, Crain's, PEI, Data Center Frontier)
- **Tier 3**: Trade publications (GlobeSt, Multi-Housing News, RE Business)
- **Tier 4**: Regional/local (patch.com, neighborhood news)
- **Tier 5**: Aggregators (Yahoo Finance, Google News)

### config/sectors.json (40 lines)

7 sectors with their subsectors and event types. Example:

```json
{
  "commercial_real_estate": {
    "label": "Commercial Real Estate",
    "subsectors": ["multifamily", "industrial_logistics", "office", "retail",
                   "hospitality", "self_storage", "student_housing", "senior_housing",
                   "manufactured_housing", "medical_office", "life_sciences",
                   "mixed_use", "affordable_housing", "single_family_rental",
                   "land_development", "data_center_real_estate",
                   "infrastructure_real_estate", "distressed_real_estate"],
    "event_types": ["property_acquisition", "portfolio_acquisition", "asset_sale",
                    "recapitalization", "refinancing", "construction_financing",
                    "development_financing", "loan_origination", "cmbs_activity",
                    "foreclosure", "receivership", "note_sale", "distressed_sale",
                    "rescue_capital", "preferred_equity", "joint_venture",
                    "fund_launch", "major_lease", "development_approval",
                    "rezoning", "entitlement_change", "tax_incentive",
                    "public_subsidy", "construction_start", "project_completion",
                    "ownership_change", "firm_acquisition", "executive_change",
                    "bank_exposure", "market_report"]
  }
  // ... 6 more sectors
}
```

### config/scoring_profiles.json

Per-sector weight profiles for the 10 scoring dimensions. Different sectors weight dimensions differently — e.g., CRE weights financial_magnitude heavily while fed_macro weights policy_impact.

### config/thresholds.json

```json
{
  "tier_boundaries": {
    "tier_1_must_cover": 80,
    "tier_2_strongly_recommended": 65,
    "tier_3_useful_coverage": 50,
    "tier_4_reserve": 35
  }
}
```

### config/watchlists.json

Entity recognition lists organized by tier:
- `tier_1_institutions`: Top-tier banks, PE firms, REITs, government bodies
- `tier_2_companies`: Mid-tier firms, regional players
- `tier_3_firms`: Niche/specialist firms

---

## 16. CI/CD & Deployment

### .github/workflows/daily-insights-agent.yml (212 lines)

```yaml
name: Curated Insights edition

on:
  schedule:
    - cron: "7 11 * * *"   # 11:07 UTC → 07:07 EDT
    - cron: "7 12 * * *"   # 12:07 UTC → 07:07 EST
  workflow_dispatch:
    inputs:
      mode: [shadow, preview, publish]
      article_count: ["1", "3", "5"]

concurrency:
  group: curated-insights-edition
  cancel-in-progress: false   # Never cancel a running edition

permissions:
  contents: write
  pull-requests: write

jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    
    steps:
      - checkout (ref: main for schedule, selected ref for manual)
      - resolve_schedule_policy.py → DST guard
      - setup-python 3.11 + install deps
      - validate baseline (py_compile + unit tests + JS check + validate_publication)
      - model_router.py → provider preflight
      - daily_news_agent.py → build curated edition
      - validate generated edition
      - upload artifacts (30-day retention)
      - resolve publication: auto-publish main OR review branch PR
```

Two cron triggers handle both EDT (UTC-4) and EST (UTC-5) without manual changes. The schedule guard in `resolve_schedule_policy.py` ensures only the correct trigger fires.

### netlify.toml (285 lines)

Production CDN configuration:
- **CSP headers**: Content-Security-Policy with nuanced per-path overrides (insights article pages allow legacy inline scripts; dashboard pages have stricter policies)
- **Redirects**: Blocks internal paths (`.editorial-state/*`, `scripts/*`, `config/*`, `data/*`, `agent/*`, `memory/*`) with 404; canonicalizes duplicate article URLs; forces HTTPS
- **Cache policies**: Static assets (images, CSS) cached aggressively; dynamic files (insights.json, feed.xml, sitemap.xml) with short TTL + stale-while-revalidate; functions never cached
- **Security headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Strict-Transport-Security

### Netlify Serverless Functions (11 functions)

- `newsletter-subscribe.js`: Email signup via Resend API with segment routing
- `editorial-feedback.js`: Reader feedback collection — Resend or webhook sink
- `analytics-dashboard.js` + `analytics-retention.js`: Analytics API + scheduled retention (Netlify Blobs)
- `visitor-track.js` + `track-read.js`: Page view and article read tracking
- `capital-diagnostic.js`: Capital diagnostic tool backend
- `mandate-submit.js`: Lead/mandate form processing
- `deal-notify.js`: Deal alert notifications
- `chat.js`: AI chat endpoint
- `linkedin-essay.js`: LinkedIn essay queue endpoint

---

## Summary: The System's Key Design Principles

1. **Deterministic Where Possible**: Classification, scoring (10 dims), fact verification, source URL validation, boilerplate detection, duplicate detection — all deterministic. LLMs are used only where judgment is required (writing, financial review, editorial review).

2. **Independent Verification**: The quality layer (`content_governance.py`) NEVER calls an LLM. It is the independent control layer that checks the LLM's output. A model cannot self-assess its own writing.

3. **Fail Closed**: Every review stage defaults to "fail" if unavailable. The financial reviewer, editorial reviewer, and fact verifier all return `passed: false` on error. An article only publishes when it passes every gate.

4. **Event Memory**: The system remembers what it has published. Event fingerprints prevent covering the same transaction multiple times. Archive matching catches same-event coverage across different wording.

5. **Scarce Edition**: The system targets 3 publishable pieces, researches up to 5. The extra capacity absorbs source failure, duplication, and editorial kills. Deal Tape entries never become padded articles.

6. **Evidence-Bounded Writing**: Every claim must be traceable to a source URL in the dossier. The 12 writing rules enforce this contract. The fact audit and semantic claim audit verify it.

7. **Scheduler Lease**: Only one publisher can run at a time. The `.editorial-state/scheduler.json` lease prevents duplicate daily runs from GitHub Actions and any local scheduler.

8. **Editorial Constitution**: "Light Tower publishes only when it can make a smart reader see a capital decision differently." This principle governs every editorial decision — the desk can and does publish nothing when no story clears the bar.
