# Proposed Target Architecture: The Light Tower Group Insights Intelligence Engine

**Document:** 07-Proposed-Target-Architecture
**Date:** July 30, 2026
**Status:** Target State Design — Ready for Implementation

---

## 1. Architecture Principles

The target architecture is governed by six principles that constrain every design decision from module boundaries to configuration format:

| # | Principle | Definition | Enforced By |
|---|-----------|------------|-------------|
| 1 | **Modular** | Each pipeline phase is a separate, independently importable Python module with a single public interface function. No module imports from a downstream phase. | `__init__.py` barrel exports; CI lint rule against cross-phase imports |
| 2 | **Configurable** | All weights, thresholds, source lists, sector definitions, and prompt templates live in version-controlled JSON files under `config/`. Zero hardcoded business logic values in Python. | `config/*.json` schema validation on pipeline startup; `Thresholds` and `SectorProfile` dataclasses loaded from config |
| 3 | **Observable** | Every editorial decision (classify, score, rank, select, generate, publish, reject) is logged with a reason code, the model used, timestamps, and input data. The audit trail is queryable by story, sector, date, and decision type. | Structured JSONL audit log (`audit/*.jsonl`); `audit.py` query module; admin dashboard drill-down |
| 4 | **Resilient** | Per-phase timeouts (configurable in `config/thresholds.json`), checkpoint serialization to `.editorial-state/checkpoints/`, resume-from-checkpoint on retry, and model fallback via `model_router.py`. The pipeline must survive the failure of any individual source, model call, or phase. | `checkpoint.py` (enhanced); `model_router.py` (existing + tiered); `run_with_timeout()` decorator |
| 5 | **Cost-Aware** | Tiered LLM usage: deterministic (free) → cheap classification model → mid-tier scoring model → premium writing model. Each API call is cost-tracked by phase, sector, and article. The pipeline must never exceed a configurable daily cost ceiling. | `model_router.py` model tier selection; `cost_tracker.py` with phase/sector dimensions; `config/cost_limits.json` |
| 6 | **Scalable** | Designed for 2000-5000 candidates/day through the classification/scoring phases and 210 articles/day through generation/publishing. Phases are parallelized where independent (ingestion, classification). The 6-hour GitHub Actions timeout is sufficient with concurrent execution. | `ThreadPoolExecutor` for ingestion; async LLM calls via `asyncio.gather()` for writing; paginated manifest files |

---

## 2. System Diagram (ASCII Art)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LIGHT TOWER GROUP INSIGHTS INTELLIGENCE ENGINE                       │
│                                    Target Architecture — 7 Sectors × 30 Articles/Day             │
│                                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              SOURCE LAYER (200+ Feeds Across 7 Sectors)                      │ │
│  │                                                                                               │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │   CRE    │  │ Private  │  │   Data   │  │  Energy  │  │ Banking/ │  │   Fed/   │        │ │
│  │  │ (~80 RSS)│  │  Equity  │  │  Centers │  │ (~30 RSS)│  │  Credit  │  │   Macro  │        │ │
│  │  │          │  │ (~25 RSS)│  │ (~20 RSS)│  │          │  │ (~25 RSS)│  │ (~20 RSS)│        │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │ │
│  │       │              │             │             │             │             │               │ │
│  │  ┌────┴─────┐                                                               ┌──────┐        │ │
│  │  │  Local   │                                                               │ SEC  │        │ │
│  │  │   Gov't  │                                                               │ EDGAR│        │ │
│  │  │ (~35 RSS)│                                                               │ RSS  │        │ │
│  │  └────┬─────┘                                                               └──┬───┘        │ │
│  │       └───────────────────────────────────────────────────────────────────────┘             │ │
│  └───────────────────────────────────────┬─────────────────────────────────────────────────────┘ │
│                                          │                                                       │
│  ┌───────────────────────────────────────▼─────────────────────────────────────────────────────┐ │
│  │                     PHASE 1: INGESTION WORKERS (concurrent per sector group)                 │ │
│  │                                                                                               │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │ │
│  │  │ CRE Worker │ │ PE Worker  │ │ DC Worker  │ │Energy Worker│ │Bank Worker │ │ Macro/LG   │  │ │
│  │  │ feedparser │ │ feedparser │ │ feedparser │ │ feedparser  │ │ feedparser │ │ Workers    │  │ │
│  │  │ + Headless │ │ + API poll │ │ + scraper  │ │ + RSS/API   │ │ + RSS/API  │ │ feedparser │  │ │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬───────┘ └─────┬──────┘ └──────┬──────┘  │ │
│  │        └──────────────┴──────────────┴──────────────┴───────────────┴────────────────┘        │ │
│  └───────────────────────────────────────┬─────────────────────────────────────────────────────┘ │
│                                          │ ~2000-5000 candidate items                             │
│  ┌───────────────────────────────────────▼─────────────────────────────────────────────────────┐ │
│  │                     PHASE 2: NORMALIZATION → CANONICAL STORE                                  │ │
│  │                                                                                               │ │
│  │  ┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐              │ │
│  │  │  story_normalizer   │───▶│  canonical_item.py   │───▶│  canonical_store.py  │              │ │
│  │  │  (topic extraction, │    │  (CanonicalItem      │    │  (JSONL file per     │              │ │
│  │  │   entity extraction,│    │   dataclass,         │    │   run date; serves   │              │ │
│  │  │   dedup at 72%)     │    │   validation)        │    │   all downstream)    │              │ │
│  │  └─────────────────────┘    └──────────────────────┘    └─────────────────────┘              │ │
│  └───────────────────────────────────────┬─────────────────────────────────────────────────────┘ │
│                                          │ All items (no filtering)                              │
│  ┌───────────────────────────────────────▼─────────────────────────────────────────────────────┐ │
│  │                     PHASE 3: CLASSIFICATION + CLUSTERING                                     │ │
│  │                                                                                               │ │
│  │  ┌───────────────────────────┐    ┌──────────────────────────────┐                           │ │
│  │  │  classification.py        │    │  clustering.py               │                           │ │
│  │  │  source_prior → regex →   │    │  - event_similarity()        │                           │ │
│  │  │  entity_match → LLM_light │    │  - cluster_events()          │                           │ │
│  │  │  Output: primary_sector,  │    │  - sector-aware (no cross-   │                           │ │
│  │  │  secondary_sectors,       │    │    sector unless entities    │                           │ │
│  │  │  confidence_scores        │    │    strongly match)           │                           │ │
│  │  └──────────────┬────────────┘    └───────────────┬──────────────┘                           │ │
│  │                 └──────────────────┬──────────────┘                                          │ │
│  └────────────────────────────────────┼────────────────────────────────────────────────────────┘ │
│                                       ▼ ~700-1000 classified events                              │
│  ┌────────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 4: SCORING ENGINE                                                  │ │
│  │                                                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐     │ │
│  │  │  scoring_engine.py                                                                    │     │ │
│  │  │  Loads config/scoring_profiles.json (7 sector profiles)                                │     │ │
│  │  │  Per item: extract financial values, check watchlists, compute 10 dimensions           │     │ │
│  │  │  Apply sector-specific weights → composite score 0-100                                 │     │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────┐ │     │ │
│  │  │  │CRE Prof  │ │ PE Prof  │ │ DC Prof  │ │Energy P. │ │Bank Prof │ │Fed Prof  │ │LG P│ │     │ │
│  │  │  │Tx Scale:9│ │Fund Sz:9 │ │MW Cap:8  │ │MW Cap:7  │ │LoanVol:8 │ │Rate Imp:9│ │Pol:9│ │     │ │
│  │  │  │Cap Stk:6 │ │LP Comp:7 │ │Grid Int:7│ │Grid Pos:8│ │Reg Imp:7 │ │Mkt Sig:8 │ │Reg:8│ │     │ │
│  │  │  │Mkt Conc:7│ │Platf St:8│ │Hypr Link:│ │Comd Mov:6│ │Cap Rat:6 │ │Labor: 7  │ │Budg:│ │     │ │
│  │  │  │...       │ │...       │ │...       │ │...       │ │...       │ │...       │ │... │ │     │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────┘ │     │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘     │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      ▼ ~400-700 scored events, each with per-sector score         │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 5: RANKING + SELECTION              │                             │ │
│  │                                                                                               │ │
│  │  ┌──────────────────────────────┐    ┌────────────────────────────────┐                      │ │
│  │  │  ranking.py                  │    │  config/selection_rules.json   │                      │ │
│  │  │  - Within-sector rank by     │    │  - Per-sector target counts    │                      │ │
│  │  │    composite score           │    │  - Subsector diversity caps    │                      │ │
│  │  │  - Apply diversity controls  │    │  - Tier thresholds per sector  │                      │ │
│  │  │    (soft caps per subsector) │    │  - Tier distribution targets   │                      │ │
│  │  │  - Cross-sector dedup        │    │  - Cross-sector dedup rules    │                      │ │
│  │  │  - Assign tiers 1-4          │    │                                │                      │ │
│  │  │  - Select top ~30/sector     │    └────────────────────────────────┘                      │ │
│  │  └───────────────┬──────────────┘                                                            │ │
│  │                  ▼ ~210 selected items (30/sector)                                            │ │
│  │  ┌───────────────┴──────────────────────────────────────┐                                    │ │
│  │  │  Selection Output: 7 sector buckets × ~30 items each │                                    │ │
│  │  │  Tier 1 (Flagship): ~3-5/sector  |  Tier 2 (Brief): ~8-10/sector                         │ │
│  │  │  Tier 3 (DealTape): ~10-15/sector |  Tier 4 (Signal): ~5-8/sector                         │ │
│  │  └──────────────────────────────────────────────────────┘                                    │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      ▼                                                            │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 6: ENRICHMENT (research dossiers)                                 │ │
│  │                                                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐                       │ │
│  │  │  enrichment.py                                                    │                       │ │
│  │  │  - fetch_full_text() per source URL (trafilatura + browserless)   │                       │ │
│  │  │  - build_research_dossier() — evidence classification per source  │                       │ │
│  │  │  - extract_facts() — numeric claims, quotes, entity verification  │                       │ │
│  │  │  - run_editorial_room() — LLM angle analysis + skeptic pass       │                       │ │
│  │  │  - Sector-specific: check PE fund terms, DC power figures,        │                       │ │
│  │  │    Energy RTO filings, Banking regulatory citations, etc.         │                       │ │
│  │  └──────────────────────────────────────────────────────────────────┘                       │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      ▼ ~210 enriched items with dossiers                         │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 7: GENERATION (sector-aware writing)                              │ │
│  │                                                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐                       │ │
│  │  │  generation.py                                                    │                       │ │
│  │  │  Per selected item:                                               │                       │ │
│  │  │  1. Select sector-specific system prompt (config/prompts.json)    │                       │ │
│  │  │  2. Assign article type based on event type + tier                │                       │ │
│  │  │  3. Select voice mode from sector-appropriate set                 │                       │ │
│  │  │  4. Assemble prompt: system + voice + dossier + tier              │                       │ │
│  │  │  5. LLM call: premium model (DeepSeek-V4-Pro / GPT-4o)           │                       │ │
│  │  │  6. Self-repair loop (max 2 iterations)                           │                       │ │
│  │  │  7. Quality gates (content_governance.py)                         │                       │ │
│  │  └──────────────────────────────────────────────────────────────────┘                       │ │
│  │                                                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐                            │ │
│  │  │  Sector Prompt Families (config/prompts.json)               │                            │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │                            │ │
│  │  │  │CRE:      │ │PE:       │ │DC:       │ │Energy:   │      │                            │ │
│  │  │  │Underwrtng│ │Fund      │ │Infra-    │ │Grid      │      │                            │ │
│  │  │  │Margin    │ │Structure │ │structure │ │Markets   │      │                            │ │
│  │  │  │Basis Aut │ │LP Memo   │ │Capacity  │ │Comm Price│      │                            │ │
│  │  │  │Lender's  │ │Buyout    │ │Power     │ │Rate Case │      │                            │ │
│  │  │  │Eye       │ │Memo      │ │Procurement│ │RTO Policy│      │                            │ │
│  │  │  │...       │ │...       │ │...       │ │...       │      │                            │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │                            │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │                            │ │
│  │  │  │Banking:  │ │Fed/Macro:│ │Local Gov:│                   │                            │ │
│  │  │  │Regulatory│ │Central   │ │Land Use  │                   │                            │ │
│  │  │  │Credit    │ │Bank Watch│ │Budget    │                   │                            │ │
│  │  │  │Risk      │ │Data Desk │ │Zoning    │                   │                            │ │
│  │  │  │...       │ │...       │ │...       │                   │                            │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘                   │                            │ │
│  │  └─────────────────────────────────────────────────────────────┘                            │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      ▼ ~210 articles                                              │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 8: QUALITY CONTROL                                                │ │
│  │                                                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐                       │ │
│  │  │  content_governance.py (enhanced)                                 │                       │ │
│  │  │  Existing 10 gates + sector-specific verification:               │                       │ │
│  │  │  Gate 11: Financial Accuracy (PE/CRE deal terms)                 │                       │ │
│  │  │  Gate 12: Power/Capacity (DC/Energy: MW, GWh, kV values)         │                       │ │
│  │  │  Gate 13: Policy Citations (Fed/Bank/LG: docket, rule, ordinance)│                       │ │
│  │  │  Gate 14: Entity Verification (names against watchlist)          │                       │ │
│  │  └──────────────────────────────────────────────────────────────────┘                       │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      ▼ ~190-210 articles pass QC                                  │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     PHASE 9: PUBLISHING                                                      │ │
│  │                                                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐                       │ │
│  │  │  publishing.py                                                    │                       │ │
│  │  │  - render_article_html() using shared article-base.css template   │                       │ │
│  │  │  - Update per-sector manifests: 7 × sector-{name}.json            │                       │ │
│  │  │  - Update master manifest: insights.json (index only)             │                       │ │
│  │  │  - Generate per-sector RSS feeds: 7 × sector-{slug}.xml           │                       │ │
│  │  │  - Generate daily digest files: digest-{date}-{sector}.json       │                       │ │
│  │  │  - Update sitemap.xml + sector indexes                            │                       │ │
│  │  │  - Build 7 sector landing pages with static JSON data             │                       │ │
│  │  │  - Commit-or-rollback pattern (existing mechanism retained)       │                       │ │
│  │  └──────────────────────────────────────────────────────────────────┘                       │ │
│  └───────────────────────────────────┬────────────────────────────────────────────────────────┘ │
│                                      │ git commit + push                                          │
│                                      ▼                                                            │
│  ┌───────────────────────────────────┴────────────────────────────────────────────────────────┐ │
│  │                     NETLIFY STATIC SITE                                                      │ │
│  │                                                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │ │
│  │  │  insights.html (Master Hub)                                                          │    │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───┐    │ │
│  │  │  │CRE Feed  │ │ PE Feed  │ │ DC Feed  │ │Energy Feed│ │Bank Feed │ │ Fed Feed │ │LG │    │ │
│  │  │  │cre.html  │ │pe.html   │ │dc.html   │ │energy.html│ │bank.html │ │fed.html  │ │lg │    │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───┘    │ │
│  │  │  7 Sector landing pages with per-sector filtering, RSS, JSON-LD, OG tags                │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘    │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │ │
│  │  │  Article Directory: insights/{slug}.html (template-rendered, shared CSS/JS)          │    │ │
│  │  │  Data Directory:   data/sector-{name}.json  (per-sector paginated manifests)         │    │ │
│  │  │  Feeds:            feed-{sector}.xml  (7 auto-generated RSS feeds)                   │    │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                     OBSERVABILITY + CONFIGURATION LAYER                                       │ │
│  │                                                                                               │ │
│  │  ┌─────────────────────────┐  ┌───────────────────────────┐  ┌───────────────────────────┐  │ │
│  │  │  Admin Dashboard        │  │  Configuration System     │  │  Audit + Health            │  │ │
│  │  │  insights-admin.html    │  │  config/                  │  │  audit/*.jsonl             │  │ │
│  │  │  + admin_dashboard.py   │  │  ├─ sources.json          │  │  source-health.json        │  │ │
│  │  │  - Per-sector output    │  │  ├─ scoring_profiles.json │  │  .editorial-state/          │  │ │
│  │  │  - Source health        │  │  ├─ sectors.json          │  │  - event-memory.json       │  │ │
│  │  │  - Cost tracking        │  │  ├─ watchlists.json       │  │  - provider-log.jsonl      │  │ │
│  │  │  - Rejection reasons    │  │  ├─ prompts.json          │  │  - checkpoints/            │  │ │
│  │  │  - Story drill-down     │  │  ├─ thresholds.json       │  │  editions/*.json           │  │ │
│  │  │  - Promote/reject       │  │  ├─ selection_rules.json  │  │  HEALTH.md                 │  │ │
│  │  │  - Weight adjustment    │  │  └─ cost_limits.json      │  │                             │  │ │
│  │  └─────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Source Registry

**File:** `config/sources.json`

**Purpose:** Single source of truth for all news feeds, APIs, and discovery endpoints. Enables non-engineer administration of sources (enable/disable, reassign sector, change tier) without touching Python code.

**Structure:**
```json
[
  {
    "id": "cre-globest",
    "name": "GlobeSt",
    "type": "rss",
    "url": "https://www.globest.com/.../rss.xml",
    "sector": "commercial_real_estate",
    "subsector": "national_cre",
    "tier": 2,
    "quality_label": "established_trade",
    "fetch_frequency": "daily",
    "fetch_method": "feedparser",
    "auth_required": false,
    "js_required": false,
    "geography": "national",
    "active": true,
    "notes": "Consistent, high-volume CRE trade publication"
  }
]
```

**Key fields:** `id` (unique), `name`, `type` (rss/api/scrape/press_release), `url`, `sector` (enum: one of 7), `subsector` (sector-specific taxonomy), `tier` (1-4), `quality_label` (primary_authoritative, major_financial, established_trade, specialized, aggregator, general_interest, hyperlocal), `fetch_frequency`, `fetch_method`, `auth_required`, `js_required`, `geography`, `active`, `notes`.

**Improvement over current system:** Replaces the hardcoded `RSS_FEEDS`, `FEDERAL_RSS_FEEDS`, and `NEWSAPI_QUERIES` tuples in `news_sources.py` with a structured, queryable JSON registry. Non-engineer admin can add a new source by editing JSON. Source-to-sector mapping is explicit — the pipeline knows which sector each feed serves, unlike the current system where all feeds feed into a single CRE gate.

**Config dependencies:** None (it is the foundation config). Validated against `config/sectors.json` for sector and subsector enum values.

---

### 3.2 Ingestion Workers

**File:** `scripts/ingestion.py`

**Purpose:** Replace the monolithic `fetch_rss_stories()` function with concurrent worker pools organized by source groups. Each worker handles a batch of sources from a single sector, fetches in parallel, normalizes output to the canonical model, and reports health.

**Inputs:** Source list from `config/sources.json`, filtered to `active: true` for the current run.

**Outputs:** `List[CanonicalItem]` — all items ingested, no filtering.

**Key functions:**
- `fetch_source(source: SourceConfig) -> List[RawItem]` — single-source fetcher. Uses `feedparser` for RSS, `requests` for REST APIs, optional headless browser for JS-rendered pages (Playwright, fallback only).
- `fetch_sector_group(sources: List[SourceConfig], max_workers: int = 20) -> List[RawItem]` — parallel fetch for a sector's sources using `ThreadPoolExecutor`.
- `ingest_all_sources(sources: List[SourceConfig], max_workers: int = 100) -> List[RawItem]` — dispatches all sector groups concurrently.
- `update_source_health(source_id: str, result: FetchResult) -> None` — updates `source-health.json` with success/failure/empty/timing stats.

**LLM usage:** None. Deterministic fetch and parse only.

**Improvement over current system:** Current `fetch_rss_stories()` iterates feeds sequentially with a `ThreadPoolExecutor` and discards the source-to-sector relationship. Ingestion workers preserve the source→sector mapping from the config, fetch per sector group (which enables sector-aware timeout management), and log per-source health with sector attribution. A dead feed in the local government sector no longer blocks or slows the CRE worker pool.

**Resilience:** Per-source 30s timeout. Three consecutive failures quarantine the source for 24h. Empty feeds (200 OK, no items) are logged but not quarantined.

---

### 3.3 Canonical News Item Model

**File:** `scripts/canonical_item.py`

**Purpose:** Define the single canonical data model used across all pipeline phases. Eliminates the current pattern of ad-hoc dicts with string-key access and `.get()` fallbacks that silently tolerate missing fields.

**Definition:**
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class Sector(str, Enum):
    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    PRIVATE_EQUITY = "private_equity"
    DATA_CENTERS = "data_centers"
    ENERGY = "energy"
    BANKING_CREDIT = "banking_credit"
    FED_MACRO = "fed_macro"
    LOCAL_GOVERNMENT = "local_government"

class ArticleTier(str, Enum):
    FLAGSHIP = "flagship"
    BRIEF = "brief"
    DEAL_TAPE = "deal_tape"
    SIGNAL = "signal"

class ProcessingPhase(str, Enum):
    GATHERED = "gathered"
    NORMALIZED = "normalized"
    CLASSIFIED = "classified"
    CLUSTERED = "clustered"
    SCORED = "scored"
    RANKED = "ranked"
    ENRICHED = "enriched"
    WRITTEN = "written"
    PUBLISHED = "published"
    REJECTED = "rejected"

@dataclass
class CanonicalItem:
    # Identity
    item_id: str
    title: str
    url: str
    published_date: datetime
    source_name: str
    source_tier: int
    source_domain: str
    source_feed_id: str

    # Content
    raw_text: str
    clean_text: str
    summary: str = ""

    # Classification
    primary_sector: Optional[Sector] = None
    secondary_sectors: list[Sector] = field(default_factory=list)
    event_type: Optional[str] = None
    subsector: Optional[str] = None
    geography_scope: Optional[str] = None
    geographies: list[str] = field(default_factory=list)

    # Entities
    companies: list[str] = field(default_factory=list)
    amounts: list[dict] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)

    # Scores (per sector)
    sector_scores: dict[str, dict] = field(default_factory=dict)
    composite_score: float = 0.0

    # Pipeline state
    status: ProcessingPhase = ProcessingPhase.GATHERED
    rejection_reason: Optional[str] = None
    tier: Optional[ArticleTier] = None
    event_cluster_id: Optional[str] = None

    # Publishing
    slug: Optional[str] = None
    body_html: Optional[str] = None

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "CanonicalItem": ...
```

**Filesystem:** Items are serialized as JSONL to `data/pipeline/{date}/{run_id}/items.jsonl` on each pipeline run. This serves as the canonical store consumed by all downstream phases.

**Improvement over current system:** Replaces the ad-hoc dicts that propagate through `daily_news_agent.py` with no schema enforcement. Adds type safety, IDE auto-completion, and field validation. The `status` field tracks exactly which phase each item is in. Rejection is explicit (with reason codes) rather than silent discard.

---

### 3.4 Classification Module

**File:** `scripts/classification.py`

**Purpose:** Multi-label classifier that routes every incoming story to its primary sector and optionally secondary sectors. Replaces the current binary `_is_cre_relevant()` gate with a four-tier classification ladder. No story is rejected at this stage — only classified.

**Inputs:** `List[CanonicalItem]` with `raw_text` populated.

**Outputs:** Same items with `primary_sector`, `secondary_sectors`, `event_type`, `subsector`, `geography_scope`, `companies`, `amounts`, and `confidence_scores` populated.

**Classification Ladder (in priority order):**

| Tier | Method | Cost | Latency | Coverage | Example |
|------|--------|------|---------|----------|---------|
| 1 | **Source Prior** | $0 | <1ms | ~60% | If source is "PERE News" → primary=PE with 0.95 confidence |
| 2 | **Regex Signals** | $0 | <1ms | ~20% | "data center" + "power" + "MW" in text → primary=DC |
| 3 | **Entity Match** | $0 | ~5ms | ~10% | Known entity "Blackstone" + pattern "infrastructure fund" → PE |
| 4 | **LLM Light** | ~$0.001 | 200-500ms | ~10% | Multi-label ambiguity unresolved by tiers 1-3 → cheap LLM call |

**Key functions:**
- `classify_source_prior(item: CanonicalItem, source_registry: dict) -> Optional[Sector]` — If source has a declared sector in config, assign with 0.95 confidence.
- `classify_regex(item: CanonicalItem) -> list[tuple[Sector, float]]` — Apply sector-specific regex patterns from `config/sectors.json`. Each sector defines a `signal_patterns` array.
- `classify_entities(item: CanonicalItem) -> list[tuple[Sector, float]]` — Match extracted entities against `config/watchlists.json` entity dictionaries, each tagged with sector affiliation.
- `classify_llm(item: CanonicalItem) -> list[tuple[Sector, float]]` — For items where source_prior + regex + entities produce conflicting or low-confidence signals, call a cheap LLM (deepseek-chat / gpt-4o-mini) with a structured classification prompt. Returns primary + secondary sectors with confidence scores.

**Output per item:**
```python
{
    "primary_sector": "data_centers",
    "secondary_sectors": ["private_equity", "energy", "commercial_real_estate"],
    "event_type": "capacity_announcement",
    "subsector": "hyperscale",
    "geography_scope": "regional",
    "confidence_scores": {"data_centers": 0.92, "private_equity": 0.65, "energy": 0.55}
}
```

**Config dependencies:** `config/sources.json` (source→sector mapping), `config/sectors.json` (regex patterns, subsector taxonomy per sector), `config/watchlists.json` (entity→sector mapping).

**LLM usage:** Only for the ~10% of items that can't be deterministically classified. Using a cheap model (deepseek-chat at ~$0.14/M input tokens, ~$0.28/M output tokens), classification of ~200 ambiguous items/day costs ~$0.08/day.

**Improvement over current system:** Current system has a binary gate: CRE keyword match → admit, else → discard. The classification module: (a) never discards, (b) produces multi-label output (not binary), (c) is deterministic-first for cost/auditability, (d) provides confidence scores for downstream. A Blackstone data center acquisition is correctly classified as primary=DC with secondary=PE, not discarded because it fails CRE keyword matching.

---

### 3.5 Clustering Module

**File:** `scripts/clustering.py`

**Purpose:** Group related headlines across sources into event clusters, with sector-aware boundaries. Reuses the existing `event_similarity()` and `cluster_events()` functions from `editorial_intelligence.py`, enhanced with sector awareness.

**Inputs:** `List[CanonicalItem]`, each with `primary_sector`, `secondary_sectors`, entities, and attention features populated.

**Outputs:** `List[EventCluster]` — each cluster represents a unique news event with multiple source citations. Items without matches are single-source clusters.

**Key functions:**
- `event_similarity(item_a: CanonicalItem, item_b: CanonicalItem) -> float` — Existing similarity function enhanced to include sector overlap as a positive signal and sector mismatch as a negative signal.
- `cluster_events(items: List[CanonicalItem], threshold: float = 0.65) -> List[EventCluster]` — Existing clustering algorithm with sector constraint: items from different primary sectors are NOT clustered together unless their secondary sector overlap is ≥2 AND they share a named entity. A story about "Blackstone data center acquisition" (primary=DC, secondary=PE, entities=[Blackstone, DataBank]) should NOT cluster with "Blackstone office portfolio sale in NYC" (primary=CRE, secondary=None, entities=[Blackstone]) — even though both mention Blackstone, the subject matter and sector context are distinct.
- `preserve_source_diversity(clusters: List[EventCluster]) -> List[EventCluster]` — Ensure that within each cluster, no single source domain provides more than 50% of citations. If so, flag for editorial review.

**Sector-aware clustering rules:**
| Scenario | Action |
|----------|--------|
| Same primary sector, same entities | Cluster (strong signal) |
| Same primary sector, different entities | Cluster if title similarity > 0.65 |
| Different primary sectors, 2+ shared secondary sectors | Cluster if shared named entity |
| Different primary sectors, <2 shared secondary sectors | Do NOT cluster (different events) |

**Improvement over current system:** Current `cluster_events()` clusters all events across all sources into one pool — it has no concept of sector boundaries. The enhanced version prevents cross-contamination: a CRE office leasing story won't cluster with a PE fund closing story just because they share a real estate keyword. Source diversity preservation ensures the system doesn't rely on a single publication for corroboration.

**Config dependencies:** `config/clustering.json` (similarity threshold, source diversity caps, sector clustering rules).

---

### 3.6 Scoring Engine

**File:** `scripts/scoring_engine.py`

**Purpose:** Compute a composite 0-100 score for each item/cluster using sector-specific dimensional weights. Replace the current universal `score_event()` with a profile-driven engine that evaluates each story through the lens most appropriate to its primary sector.

**Inputs:** `List[EventCluster]`, each with `primary_sector` set.

**Outputs:** Same clusters with `composite_score`, `dimension_scores` dict, `confidence` float, and `score_breakdown` explanation.

**Scoring Profiles:** `config/scoring_profiles.json` defines one profile per sector, each specifying: dimension names, default weight, min/max penalty and bonus values, watchlist signal multipliers, and the scoring algorithm (weighted_sum, geometric_mean, or custom).

**Seven profiles, sample weight vectors:**

| Dimension | CRE | PE | Data Centers | Energy | Banking | Fed/Macro | Local Gov |
|-----------|-----|----|-------------|--------|---------|-----------|-----------|
| Financial Magnitude | 0.25 | 0.22 | 0.15 | 0.12 | 0.20 | 0.05 | 0.05 |
| Market Significance | 0.15 | 0.15 | 0.18 | 0.15 | 0.10 | 0.22 | 0.10 |
| Strategic Relevance | 0.10 | 0.18 | 0.18 | 0.12 | 0.15 | 0.18 | 0.15 |
| Policy / Regulatory Impact | 0.08 | 0.05 | 0.10 | 0.18 | 0.15 | 0.18 | 0.22 |
| Novelty / First-of-Kind | 0.08 | 0.08 | 0.15 | 0.10 | 0.08 | 0.08 | 0.08 |
| Source Quality | 0.12 | 0.12 | 0.10 | 0.12 | 0.12 | 0.12 | 0.10 |
| Timeliness | 0.08 | 0.08 | 0.06 | 0.06 | 0.08 | 0.08 | 0.08 |
| Editorial Potential | 0.08 | 0.05 | 0.04 | 0.03 | 0.05 | 0.05 | 0.05 |
| Cross-Sector Importance | 0.04 | 0.05 | 0.04 | 0.08 | 0.05 | 0.04 | 0.12 |
| Audience Utility | 0.02 | 0.02 | 0.00 | 0.04 | 0.02 | 0.00 | 0.05 |

**Key functions:**
- `load_scoring_profiles() -> dict[str, SectorScoringProfile]` — Parse `config/scoring_profiles.json` and `config/watchlists.json`. Return typed profile objects.
- `score_cluster(cluster: EventCluster, profile: SectorScoringProfile) -> float` — Deterministic scoring using the matched profile. Steps: (1) extract financial values from all citations (regex for $, MW, acres, bps, unit counts), (2) check entities against watchlist and apply signal multipliers, (3) compute each raw dimension 0-100, (4) apply sector-specific weights, (5) compute composite as weighted average, (6) normalize to 0-100.
- `score_all_clusters(clusters: List[EventCluster]) -> List[EventCluster]` — For each cluster, select the profile matching `primary_sector`, score, log the decision with dimension breakdown.

**Deterministic signal extraction (no LLM):**
- Financial magnitude: regex for dollar amounts, MW, acres, units, bps, basis points
- Entity significance: watchlist tier lookup (Tier 1 entity = 1.5x multiplier, Tier 2 = 1.2x, unlisted = 1.0x)
- Source quality: source tier × citation count × freshness
- Timeliness: published date distance from now (0-24h = 100, 24-36h = 70, 36-48h = 40, >48h = 10)
- Market significance: geographic scope × source count × entity tier
- Novelty: keyword-based first-of-kind detection ("first", "record", "largest", "unprecedented" + sector context)

**LLM usage:** None for standard scoring. An optional LLM overlay (`editorial_scoring.py`) is available for borderline cases (scores within 5 points of a tier threshold) — used on <5% of items.

**Improvement over current system:** Current `score_event()` applies the same 10 dimensions with the same weights to every story — a $10M multifamily refinancing uses the same scoring formula as a $5B PE fund close. The profiling engine evaluates a data center story on MW capacity and grid interconnection position (not CRE comps), a PE story on fund size and LP composition (not cap rates), and a local government story on policy scope and jurisdiction population (not transaction scale). This eliminates the systematic underscoring of non-CRE stories that the current architecture cannot avoid.

---

### 3.7 Ranking Module

**File:** `scripts/ranking.py`

**Purpose:** Within each sector, rank stories by composite score, apply diversity controls, select approximately 30 stories per sector (~210 total), and assign content tiers. Resolve cross-sector ownership for multi-sector stories.

**Inputs:** `List[EventCluster]` with `composite_score` and `sector_scores` populated.

**Outputs:** Seven `SectorRanking` objects, each containing a ranked list of selected clusters, tier assignments, and rejection explanations for non-selected items.

**Key functions:**
- `rank_sector(sector: str, events: List[EventCluster], config: SelectionConfig) -> SectorRanking` — Core ranking algorithm:
  1. Sort events by `composite_score` descending.
  2. Apply subsector diversity caps (from `config/selection_rules.json`): max 40% from any single subsector, max 15% from any single source domain.
  3. Assign tiers based on per-sector thresholds:
     - Tier 1 (Flagship): top ~10% by score, minimum 3/sector
     - Tier 2 (Brief): next ~30% by score
     - Tier 3 (Deal Tape): next ~40% by score
     - Tier 4 (Signal): remaining ~20% (logged, not published as article)
  4. Select top ~30 items (Tiers 1-3 combined).
  5. For items below the selection threshold, log with reason code: `score_below_threshold`, `subsector_diversity_cap`, `source_diversity_cap`, `cross_sector_dedup`.

- `cross_sector_dedup(rankings: List[SectorRanking]) -> List[SectorRanking]` — Multi-sector stories that appear in multiple sector rankings are resolved to their primary sector only. The secondary sector rankings log the item as "covered_by_primary_sector."

- `compute_tier_thresholds(sector: str, scored_items: List[float]) -> TierThresholds` — Dynamic threshold calculation using percentile ranks against the day's pool, not fixed absolute thresholds. A thin news day in the Energy sector shouldn't produce zero articles because a fixed threshold is too high.

**Config dependencies:** `config/selection_rules.json` — per-sector target counts, subsector caps, source diversity caps, tier distribution targets, and dynamic threshold parameters.

**LLM usage:** None. Deterministic ranking algorithm.

**Improvement over current system:** Current system uses a single global MUST_READ threshold (56) for all stories, producing zero articles on 78.8% of days. The ranking module: (a) ranks within-sector (stories compete against their own sector's pool, not against a global gate), (b) uses dynamic (percentile-based) thresholds, (c) enforces source and subsector diversity, (d) guarantees ~30 items per sector per day regardless of whether individual items cross a fixed threshold.

---

### 3.8 Enrichment Module

**File:** `scripts/enrichment.py`

**Purpose:** For every selected story, fetch full article text, build a cross-source research dossier, classify evidence depth, and run editorial room analysis. Reuses the existing `build_research_dossier()`, `extract_facts()`, and `run_editorial_room()` functions from `research_dossier.py` and `editorial_room.py`, with sector-specific enhancements.

**Inputs:** `List[EventCluster]` with tier assignments (Tiers 1-2 get full enrichment; Tier 3 gets light enrichment; Tier 4 gets no enrichment).

**Outputs:** Enriched clusters with: `full_text_sources`, `dossier` (structured facts, quotes, context), `evidence_classification`, `extracted_claims`, `room_plan` (LLM angle analysis), `dossier_confidence`.

**Key functions (reusing existing):**
- `fetch_full_text(url: str, method: str = "trafilatura") -> Optional[str]` — Attempt full-text extraction. Fallback: trafilatura → headless browser → requests + BeautifulSoup. Track which method succeeded per URL.
- `build_research_dossier(cluster: EventCluster) -> dict` — Enhanced with sector-specific fact patterns:
  - CRE: extract sale price, cap rate, square footage, buyer/seller, lender, debt terms
  - PE: extract fund size, LP names, target sectors, fund vintage, management fee, carry
  - Data Centers: extract MW capacity, location, hyperscaler tenant, power source, PUE, interconnection
  - Energy: extract MW/GWh, fuel type, RTO/ISO region, PPA details, counterparties, COD date
  - Banking: extract capital ratio, loan volume, reserve level, regulatory action type, docket number
  - Fed/Macro: extract rate change, basis points, data release value, previous value, consensus
  - Local Government: extract jurisdiction, ordinance number, vote count, effective date, fiscal impact
- `classify_evidence_level(sources: List[dict]) -> str` — deep (3+ independent sources with full text), adequate (2 sources), thin (1 source), insufficient (headline only).
- `run_editorial_room(cluster: EventCluster, dossier: dict) -> dict` — LLM pass (mid-tier model) for angle identification, skeptic review, and gap flagging. Existing function, enhanced with sector-specific questioning patterns.

**LLM usage:** The editorial room pass uses a mid-tier model (deepseek-chat) for angle analysis and skeptic review. Called once per Tier 1-2 item (~70 items/day × ~300 tokens output = $0.06/day).

**Improvement over current system:** Current dossier building is CRE-centric — it extracts cap rates and DSCR but has no concept of fund LP composition or MW capacity. The enhanced module adds sector-specific fact extraction patterns and evidence classification, enabling accurate research dossiers for all 7 sectors.

---

### 3.9 Generation Module

**File:** `scripts/generation.py`

**Purpose:** Generate substantive articles for all selected stories using sector-aware prompts, tier-appropriate formats, and context-matched voice modes. Refactors the existing `generate_article()` from `daily_news_agent.py` and integrates with `enhanced_prompts.py`, `editorial_voice.py`, and `content_governance.py`.

**Inputs:** `List[EventCluster]` with dossiers and room plans (Tiers 1-2). Tier 3 items receive a template-based generation path. Tier 4 items generate structured metadata only (no narrative).

**Outputs:** `List[Article]` — typed article objects with title, slug, body_html, metadata, tier, sector, and quality audit results.

**Article types by tier:**

| Tier | Article Type | Word Count | Generation Method | LLM Tier |
|------|-------------|------------|-------------------|----------|
| 1 (Flagship) | Full narrative analysis | 750-1100 | Full LLM generation with dossier + editorial room | Premium (DeepSeek-V4-Pro / GPT-4o) |
| 2 (Brief) | Condensed intelligence brief | 300-500 | Full LLM generation with dossier | Premium (DeepSeek-V4-Pro / GPT-4o) |
| 3 (Deal Tape) | Structured transaction record | 100-200 | Template + LLM fill (key fields only) | Mid-tier (deepseek-chat) |
| 4 (Signal) | Metadata-only observation | 50-100 | Template only, no LLM | None |

**Sector prompt families:** `config/prompts.json` defines system prompts per sector × article type combination:

```
prompts.json:
  commercial_real_estate:
    flagship: "You write the CRE capital markets intelligence layer..."
    brief: "You write compressed CRE briefs..."
    deal_tape: "Extract transaction fields from the following..."
  private_equity:
    flagship: "You write PE fund analysis for institutional LPs..."
    brief: "You write concise PE deal summaries..."
    deal_tape: "Extract fund close/financing fields..."
  ... (7 sectors × 3-4 article types = ~25 prompt templates)
```

**Voice modes by sector:** `config/editorial_voices.json` defines available voice modes per sector:
- CRE: Underwriting Margin, Basis Autopsy, Lender's Eye, Counterparty Map, City in the Balance Sheet (existing 8 modes retained)
- PE: Fund Structure Memo, LP Lens, Sponsor Thesis, Secondaries View, Co-Investment Note
- Data Centers: Capacity Dispatch, Power Contract Analysis, Hyperscaler Intelligence, Fiber Grid View
- Energy: Grid Markets, Rate Case Summary, PPA Desk, Commodity Flow, RTO Policy Note
- Banking: Regulatory Memo, Credit Committee, Capital Structure, Risk Framework
- Fed/Macro: Central Bank Watch, Data Desk, Rate Path, Global Spillover
- Local Government: Land Use Memo, Budget Note, Zoning Analysis, Municipal Credit View

**Self-repair loop:** Retained from current system (max 2 iterations). Quality gates run after each generation. If gates fail, the repair instruction is appended to the prompt with sector-specific guidance.

**LLM usage:** Premium model for Tiers 1-2 (~70 articles/day × $0.05/article = $3.50), mid-tier for Tier 3 template fill (~140 articles × $0.002 = $0.28). Total generation: ~$3.78/day.

**Improvement over current system:** Current generation uses CRE-centric prompts for all stories — a data center capacity expansion would get a "thesis-led CRE capital markets" prompt. The sector-aware system selects the appropriate system prompt, voice mode, and fact extraction patterns for each sector. Tiered generation (premium for flagship, template for deal tape) controls costs while maintaining quality for high-significance stories.

---

### 3.10 Quality Control

**File:** `scripts/content_governance.py` (enhanced)

**Purpose:** Validate every generated article against syntactic, structural, factual, and sector-specific quality gates. The existing module already provides 10 gates and is structurally sound. The target architecture adds 4 sector-specific gates.

**Existing gates (retained):**
1. Factual Grounding — numeric claims against source dossier
2. Source Attribution — at least one named source cited
3. Structural Integrity — headline, lede, body, closing
4. Narrative Coherence — no contradictions, consistent timeline
5. Regulatory Accuracy — agency names, rule numbers verified
6. Date Consistency — valid ranges, no future dates in past-tense
7. Entity Correctness — company/property/people names match source
8. Quote Fidelity — quotes traceable to source
9. Length Threshold — meets minimum for tier
10. Repetition Detection — no paragraph-level duplication

**New sector-specific gates:**

| Gate # | Name | Applies To | What It Verifies |
|--------|------|-----------|-------------------|
| 11 | Financial Magnitude Accuracy | CRE, PE, Banking | Deal size, fund size, loan amount, cap rate, DSCR against source dossier. Flags when LLM-generated numbers differ from source by >5%. |
| 12 | Power/Capacity Verification | Data Centers, Energy | MW capacity, GWh output, kV transmission, PUE, COD dates. Cross-references against source dossier numeric claims. |
| 13 | Policy/Regulatory Citation | Fed/Macro, Banking, Local Gov | Docket numbers, rule references, ordinance numbers, agency names. Validates format and existence in source material. |
| 14 | Entity/Market Verification | All sectors | Company names, fund names, property addresses, RTO/ISO regions. Checks against `config/watchlists.json` and source material. |

**Sector-specific fact audit examples:**
- CRE: "verify sale price $127M against dossier (3 sources report $127M)" → PASS
- PE: "verify fund target $8B against dossier (PE Hub reports $8B, WSJ reports $8B)" → PASS
- DC: "verify capacity 300MW against dossier (DCD reports 300MW, DCF reports 300MW)" → PASS
- Energy: "verify PPA rate $38/MWh against dossier (EIA source only, single-source caution)" → WARN (thin evidence)

**LLM usage:** None. All gates are deterministic (regex, string matching, numeric comparison). The module explicitly rejects LLM self-assessment as a quality mechanism.

**Improvement over current system:** The existing 10 gates are structurally sound but CRE-centric — they verify "regulatory accuracy" with CRE agency names (HUD, FHFA) but have no patterns for FERC dockets, PSC rate case numbers, or municipal ordinance citations. The enhanced module adds sector-specific verification patterns and fact audit logic that catch sector-specific LLM hallucination patterns.

---

### 3.11 Publishing Module

**File:** `scripts/publishing.py`

**Purpose:** Render articles to templated HTML, update per-sector and master manifests, generate sector-specific RSS feeds, build landing page data files, and manage the commit-or-rollback cycle. Replaces the current inlined HTML generation path in `daily_news_agent.py`.

**Inputs:** `List[Article]` with rendered content, metadata, and quality audit results.

**Outputs:** New/modified files in the repository:
- `insights/{slug}.html` — template-rendered article pages (shared CSS via `<link>`, not inlined)
- `data/sector-{name}.json` — per-sector paginated manifests (daily + weekly rollups)
- `data/insights-index.json` — master index (slug, sector, date, tier, title, url only)
- `insights-{sector}.html` — 7 sector landing pages (static HTML with client-side JS filtering)
- `feed-{sector}.xml` — 7 sector-specific RSS feeds
- `sitemap.xml` — updated with new article URLs, organized by sector path
- `publication-log.jsonl` — append-only audit log of every published article

**Key functions:**
- `render_article_html(article: Article, template: Template) -> str` — Render article using a shared HTML template with CSS loaded from `article-base.css`. Article body is injected into the template. Reduces per-article file size by ~80% vs. current inlined CSS approach.
- `update_sector_manifest(sector: str, articles: List[Article]) -> None` — Append new articles to the sector's JSON manifest. Implement pagination: daily files (`sector-{name}-2026-07-30.json`) plus a rolling 30-day `sector-{name}-latest.json` for the landing page.
- `build_sector_landing_page(sector: str) -> str` — Generate a static HTML landing page for the sector that loads the sector manifest and provides client-side filtering by subsector, article type, geography, and date.
- `generate_sector_rss(sector: str, articles: List[Article]) -> str` — Generate a standards-compliant RSS 2.0 feed for the sector with sector-appropriate title and description.
- `commit_and_push(published_files: List[str]) -> bool` — Existing commit-or-rollback pattern retained: validate all written files, git add, git commit, git push. On validation failure, roll back all writes.

**Template-based rendering (eliminates the 76,650-file problem):**
```html
<!-- insights/blackstone-qts-10b-datacenter.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Blackstone Acquires QTS Data Center Portfolio for $10B</title>
  <link rel="stylesheet" href="/insights/article-base.css">
  <!-- JSON-LD, OG tags, Twitter cards loaded from article metadata -->
</head>
<body>
  <main class="article" data-sector="data_centers" data-tier="flagship">
    <!-- Article body injected from structured content -->
    <!-- Shared nav, footer, and related-research components loaded via site.js -->
  </main>
</body>
</html>
```

**Scale handling:**
- 210 articles/day × 365 days = 76,650 HTML files/year. With shared CSS/JS, each file is ~8-15 KB instead of 25-35 KB. Git handles ~200 new small files per commit without performance degradation.
- Per-sector daily digest files keep the client-side fetch payload small (~50-100 KB for 30 articles) vs. a monolithic ~150 MB manifest.
- Sector landing pages load only their sector's data (30 entries, not 76,650).

**LLM usage:** None. Deterministic rendering and file generation.

**Improvement over current system:** Current publishing generates full standalone HTML pages with inlined CSS (~30 KB each), produces a single `insights.json` manifest, and one RSS feed. The target system: (a) uses shared CSS to reduce per-article file size by 70-80%, (b) produces 7 sector-specific manifests and feeds, (c) generates paginated daily digest files to prevent client-side memory bloat, (d) builds 7 sector landing pages with sector-appropriate metadata.

---

### 3.12 Observability Dashboard

**Files:** `scripts/admin_dashboard.py` + `insights-admin.html` (enhanced)

**Purpose:** Provide real-time visibility into pipeline operations across all 7 sectors, with admin controls for editorial intervention.

**Dashboard panels:**

| Panel | Data Source | Refresh | Content |
|-------|------------|---------|---------|
| **Pipeline Status** | `editions/{date}.json` | Per run | Current phase, items processed per phase, elapsed time, estimated remaining |
| **Per-Sector Output** | `data/sector-{name}-latest.json` | Per run | Articles published today per sector, candidates scored per sector, rejection rate |
| **Source Health** | `source-health.json` | Per run | Active/quarantined/dead sources per sector, fetch success rate, trend line |
| **Cost Tracking** | `cost_tracker.py` output | Per run | Cost per phase, per sector, per article type; cumulative daily/monthly; vs. budget |
| **Rejection Reasons** | `audit/{date}.jsonl` | Per run | Pie chart of rejection reasons by sector; drill-down to individual story |
| **Story Drill-Down** | `data/pipeline/{date}/{run_id}/items.jsonl` | On demand | Full audit trail for a single story through every phase |
| **Quality Issues** | Content governance output | Per run | Gate failure rate by gate number, by sector, over time |
| **Admin Controls** | Manual input | On demand | Promote/reject individual story, adjust sector weights, merge clusters, reprocess item |

**Admin controls (write actions):**
- `POST /admin/promote` — Override a story's score to push it into selection
- `POST /admin/reject` — Kill a selected story with reason
- `POST /admin/merge` — Merge two event clusters into one
- `POST /admin/weight` — Temporarily adjust a sector's dimension weights (persisted to `.editorial-state/weight-overrides.json`)
- `POST /admin/reprocess` — Re-run classification/scoring for a specific item

**LLM usage:** None for the dashboard. Admin overrides modify JSON files that are read on the next pipeline run.

**Improvement over current system:** Current `insights-admin.html` is a static page with no real-time data. The enhanced dashboard provides per-sector visibility, rejection reason tracking, cost attribution, and editorial intervention controls — all essential for operating a 7-sector, 210-article/day pipeline that cannot be managed through manual JSON file edits.

---

### 3.13 Configuration System

**Directory:** `config/`

**Purpose:** Externalize all tunable parameters, weights, thresholds, source lists, sector definitions, prompt templates, and watchlists into version-controlled JSON files. Enable non-engineer administration. Validate configuration on pipeline startup.

**Files:**

| File | Contents | Reloaded | Validated Against |
|------|----------|----------|-------------------|
| `sources.json` | Array of source definitions (name, url, sector, tier, fetch_method, active) | Every pipeline run | `sectors.json` enum values |
| `sectors.json` | Sector definitions: name, slug, subsector taxonomy, regex signal patterns, geography ontology, entity categories | On startup | Self-consistent taxonomy |
| `scoring_profiles.json` | Per-sector scoring dimensions, weights, signal multipliers, penalty rules | Every scoring phase | `sectors.json` sector keys |
| `watchlists.json` | Named entities per sector with tier (1-3), aliases, and signal multipliers | Every scoring phase | `sectors.json` sector keys |
| `prompts.json` | System prompts per sector × article type, voice mode definitions, headline shapes | Every generation phase | `sectors.json` sector keys |
| `thresholds.json` | Per-sector tier thresholds, diversity caps, selection targets, timeout values | Every pipeline run | `sectors.json` sector keys |
| `selection_rules.json` | Per-sector target counts, subsector caps (max % per subsector), source caps, tier distribution targets | Every ranking phase | `sectors.json` subsector values |
| `clustering.json` | Similarity threshold, source diversity caps, cross-sector clustering rules | Every clustering phase | None |
| `cost_limits.json` | Daily cost ceiling per phase, per-model cost estimates, alert thresholds | Every LLM call | None |

**Validation on load:**
```python
def validate_config() -> ConfigValidationResult:
    """Run at pipeline startup. Returns validation errors if config is broken."""
    sources = load_json("config/sources.json")
    sectors = load_json("config/sectors.json")
    # Check: every source.sector exists in sectors
    # Check: every scoring profile key exists in sectors
    # Check: every watchlist entity.sector exists in sectors
    # Check: every prompt sector key exists in sectors
    # Check: threshold values are within valid ranges
    # If any check fails → pipeline halts with clear error message
    return ConfigValidationResult(errors=[])
```

**Non-engineer administration:** A business operator can:
- Add a new PE publication by adding a JSON block to `sources.json` — no Python code change, no redeploy
- Adjust the weight of "Policy Impact" for the Energy sector by editing a number in `scoring_profiles.json`
- Add a new entity to the Data Centers watchlist by appending to an array in `watchlists.json`
- Change the daily target from 30 to 40 articles per sector by editing `selection_rules.json`

All config files are in version control. Changes are committed and pushed. The pipeline reads the latest config on every run. A broken config fails fast with a clear validation error.

**Improvement over current system:** Current configuration is scattered across Python source files (`CRE_KEYWORDS` in `news_sources.py`, thresholds in `editorial_intelligence.py`, prompts in `enhanced_prompts.py`, voice modes in `editorial_voice.py`). Every adjustment requires a Python code edit and a redeploy. The config system consolidates all tunable values into JSON files that can be edited without touching Python code — enabling non-engineer operators to manage the pipeline.

---

## 4. Data Flow (Step by Step)

Trace one representative story — a Blackstone infrastructure fund close — through the complete target pipeline to illustrate data transformation at each phase:

### Phase 1: Ingestion (7:05 AM)

```
RSS feed fetched from PE Hub → parsed by feedparser → 15 raw items
RSS feed fetched from Bloomberg PE → parsed → 8 raw items
RSS feed fetched from WSJ Pro PE → parsed → 5 raw items

Raw item example:
{
  "title": "Blackstone Closes $5.2B Infrastructure Fund, Exceeding $4B Target",
  "url": "https://www.pehub.com/blackstone-infrastructure-fund-close",
  "published": "2026-07-30T06:45:00-04:00",
  "source_name": "PE Hub",
  "source_feed_id": "pe-pehub",
  "raw_text": "(full feed text or description)"
}
```

### Phase 2: Normalization (7:08 AM)

```
Normalized to CanonicalItem:
  item_id: "a1b2c3d4" (content-hash derived UUID)
  title: "Blackstone Closes $5.2B Infrastructure Fund, Exceeding $4B Target"
  url: "https://www.pehub.com/blackstone-infrastructure-fund-close"
  published_date: 2026-07-30T10:45:00Z
  source_name: "PE Hub"
  source_tier: 2
  source_domain: "pehub.com"
  source_feed_id: "pe-pehub"
  raw_text: "(original feed text)"
  clean_text: "(stripped HTML, normalized whitespace)"
  summary: "Blackstone has closed its latest infrastructure fund..."
  status: GATHERED
```

### Phase 3: Classification (7:10 AM)

```
Classification ladder applied:
  1. Source Prior: PE Hub → sector=private_equity, confidence=0.92
  2. Regex Signals: "infrastructure fund" "close" "$5.2B" → reinforces PE, adds energy (0.55), data_centers (0.40)
  3. Entity Match: "Blackstone" in PE watchlist (Tier 1 entity) → multiplies confidence
  4. LLM Light: (skipped — deterministic confidence > 0.85)

Classification output:
  primary_sector: private_equity
  secondary_sectors: [energy, data_centers]
  event_type: fund_close
  subsector: infrastructure
  geography_scope: global
  companies: ["Blackstone", "Blackstone Infrastructure Partners"]
  amounts: [{"value": 5.2, "unit": "billion", "currency": "USD", "type": "fund_size"}]
  confidence_scores: {private_equity: 0.94, energy: 0.55, data_centers: 0.40}
  status: CLASSIFIED
```

### Phase 4: Clustering (7:12 AM)

```
Similar items from other sources:
  WSJ: "Blackstone Infrastructure Fund Hits $5.2B Final Close" → PE Hub item similarity = 0.88
  Bloomberg: "BX Infrastructure Fund Closes Above Target at $5.2 Billion" → similarity = 0.85

All three grouped into one EventCluster:
  cluster_id: "evt-blackstone-infra-fund-2026-q3"
  primary_sector: private_equity
  citations: 3 (PE Hub, WSJ, Bloomberg)
  source_domains: ["pehub.com", "wsj.com", "bloomberg.com"]  ✓ diversity check passes (no domain > 50%)
  status: CLUSTERED
```

### Phase 5: Scoring (7:15 AM)

```
PE Scoring Profile applied:
  Financial Magnitude: $5.2B → 90 (exceeds $1B benchmark by 5.2×) × weight 0.22 = 19.8
  Market Significance: Largest infra fund this year → 85 × 0.15 = 12.75
  Strategic Relevance: Blackstone expanding infra platform → 80 × 0.18 = 14.4
  Policy/Regulatory Impact: Limited → 20 × 0.05 = 1.0
  Novelty: Exceeded target by 30%, largest in sector → 82 × 0.08 = 6.56
  Source Quality: 3 sources, all Tier 1-2 publications → 90 × 0.12 = 10.8
  Timeliness: Published 30 min ago → 100 × 0.08 = 8.0
  Editorial Potential: Strong narrative (largest fund, Blackstone brand) → 85 × 0.05 = 4.25
  Cross-Sector: Infrastructure touches energy + data centers → 70 × 0.05 = 3.5
  Audience Utility: LP/GP audience relevance → 75 × 0.02 = 1.5
  Composite Score: 82.56
  Tier Assignment: Tier 1 (flagship candidate)

status: SCORED
```

### Phase 6: Ranking (7:18 AM)

```
Within PE sector pool of 42 scored items:
  Rank: #3 of 42
  Tier Thresholds (dynamic, based on today's pool):
    Tier 1 cutoff: 79.2 (top 10%)
    Tier 2 cutoff: 61.5 (top 40%)
    Tier 3 cutoff: 38.0 (top 80%)
  82.56 > 79.2 → Tier 1 ✓

  Subsector diversity check: Infrastructure subsector has 6 items in top 30
    Cap: 40% = 12 items → 6 < 12 ✓

  Source diversity check: WSJ appears in 3 of top 30
    Cap: 15% = 4.5 items → 3 < 4.5 ✓

  Selection: INCLUDED in PE sector top 30
  Cross-sector dedup: This story is primary=PE, not appearing in any other sector's top 30
    → No dedup needed

status: RANKED (Tier 1)
```

### Phase 7: Enrichment (7:22 AM)

```
Fetch full text from 3 source URLs:
  pehub.com → trafilatura → 1,200 words full text ✓
  wsj.com → paywall → fallback headless browser → 800 words ✓
  bloomberg.com → trafilatura → 1,100 words full text ✓

Build research dossier:
  Facts extracted: 18 numeric/qualitative facts
    - Fund size: $5.2B (confirmed by all 3 sources)
    - Target: $4B (exceeded by 30%)
    - Sector focus: digital infrastructure, energy transition, transportation
    - Previous fund: $3.5B (2023 vintage)
    - LP composition: 45 institutional investors across 18 countries
    - Key LPs: CalPERS, CPP Investments, ADIA, Temasek
    - Key stats: 2/3 of capital already deployed across 8 investments
  Quotes extracted: 3
    - "This fund reflects the accelerating demand for infrastructure capital..." — Blackstone President
    - "Infrastructure is no longer a satellite allocation for LPs..." — Head of Blackstone Infrastructure
  Evidence classification: deep (3 independent, full-text sources, corroborated claims)

Run editorial room (mid-tier LLM):
  Angle identification: "One fund close, three signals — PE infrastructure is institutionalizing.
    The oversubscription signals LP demand for real assets, the deployment pace signals a 
    competitive deal environment, and the sector mix signals where institutional capital 
    expects growth (digital infra, energy transition)."
  Skeptic pass: "Watch for: the '2/3 already deployed' claim — is this net of fees?
    The $5.2B may include GP co-investment. Verify LP names against public filings."
  Gap flag: "No information on management fee or carry terms."

status: ENRICHED
```

### Phase 8: Generation (7:28 AM)

```
Sector prompt selection: private_equity → flagship
Voice mode selection: Fund Structure Memo (matched to event_type=fund_close)
System prompt assembled from config/prompts.json:
  "You write private equity fund analysis for an institutional LP audience..."

LLM generation (DeepSeek-V4-Pro):
  Article title: "Blackstone Infrastructure Fund Closes at $5.2B — The Real Story Is the 30% Oversubscription"
  Body: 980-word narrative analysis covering fund structure, LP composition,
    deployment pace, sector allocation, comparison to previous vintage, and 
    what the oversubscription says about institutional LP appetite for 
    infrastructure as an asset class.
  Word count: 980 → between 750-1100 ✓

Quality Control (content_governance.py):
  Gate 1 (Factual Grounding): ✓ all 12 numeric claims verified against dossier
  Gate 2 (Source Attribution): ✓ 3 named sources cited
  Gate 3 (Structural Integrity): ✓ headline, lede, body, closing all present
  Gate 4 (Narrative Coherence): ✓ no contradictions
  Gate 5 (Regulatory Accuracy): ✓ regulatory references minimal but correct
  Gate 6 (Date Consistency): ✓ all dates valid
  Gate 7 (Entity Correctness): ✓ Blackstone, CalPERS, CPP all spelled correctly
  Gate 8 (Quote Fidelity): ✓ 2 quotes traceable to dossier sources
  Gate 9 (Length Threshold): ✓ 980 words > 750 minimum
  Gate 10 (Repetition Detection): ✓ no paragraph-level duplication
  Gate 11 (Financial Magnitude): ✓ $5.2B matches all 3 dossier sources
  Gate 14 (Entity Verification): ✓ LP names match dossier
  SCORE: 14/14 gates passed → auto-pass, no repair needed

status: WRITTEN
```

### Phase 9: Publishing (7:32 AM)

```
Article rendered to HTML using shared template:
  → insights/blackstone-infrastructure-fund-5b-close.html (12 KB)

Sector manifest updated:
  → data/sector-private_equity-2026-07-30.json (appended new article)
  → data/sector-private_equity-latest.json (rolling 30-day window updated)

Master index updated:
  → data/insights-index.json (appended slug, sector, tier, date, title)

RSS feed updated:
  → feed-private_equity.xml (new <item> appended)

Sector landing page check:
  → insights-private-equity.html (client-side filter loads sector-latest.json)

LinkedIn essay package:
  → generated for Tier 1 article, saved to linkedin_essay_queue.json

Repository validation:
  ✓ All HTML files referenced in manifest exist
  ✓ All manifests are valid JSON
  ✓ No broken internal links
  → git add → git commit → git push
  → Netlify auto-deploy triggered

status: PUBLISHED
```

### Summary: 9 minutes from raw RSS to published article

```
07:05  Ingestion complete (3 sources captured)
07:08  Normalization complete
07:10  Classification complete (primary=PE, secondary=[energy, dc])
07:12  Clustering complete (3 citations, 1 cluster)
07:15  Scoring complete (composite=82.56, Tier 1)
07:18  Ranking complete (#3 in PE, selected)
07:22  Enrichment complete (3 full-text, 18 facts, evidence=deep)
07:28  Generation complete (980 words, 14/14 gates passed)
07:32  Published to insights/ + Netlify
```

---

## 5. Migration Path

The migration from the current single-sector CRE pipeline to the target 7-sector architecture must be executed incrementally. The current pipeline must continue to produce CRE articles without interruption during the migration. Each phase is deployed, tested, and validated before the next phase begins.

### Phase A: Configuration Infrastructure (Week 1)

**Goal:** Establish the config/ directory and get the existing pipeline reading from it. Zero behavioral change.

**Deliverables:**
- Create `config/` directory with `sources.json` containing all 103 current sources mapped to their sectors
- Create `config/sectors.json` with CRE sector definition and subsector taxonomy
- Create `config/scoring_profiles.json` with the current 10-dimension profile for CRE
- Create `config/watchlists.json` with the current `KNOWN_INSTITUTIONS` list, sector-tagged
- Create `config/thresholds.json` with current thresholds
- Create `scripts/canonical_item.py` with the `CanonicalItem` dataclass
- Create `scripts/config_loader.py` with `load_config()` and `validate_config()`
- Modify `daily_news_agent.py` to optionally load sources from config (feature flag: `USE_CONFIG_SOURCES=false`)

**Validation:** Run current pipeline with `USE_CONFIG_SOURCES=true`. Verify identical output (same stories gathered, same triage results, same articles published). The config-based path should produce a byte-identical `insights.json` to the hardcoded path.

### Phase B: Source Expansion + Classification (Week 2)

**Goal:** Add PE, DC, and Energy source feeds. Classification module runs on all items. Non-CRE stories are classified and logged but not scored or published.

**Deliverables:**
- Add 25 PE sources, 20 DC sources, 30 Energy sources to `config/sources.json`
- Create `scripts/classification.py` with the 4-tier classification ladder
- Modify ingestion to use per-sector worker pools (CRE still primary, others quiet)
- Classification runs on ALL ingested items (not just CRE keyword matches)
- Non-CRE items logged to `audit/{date}-classification.jsonl` with: item_id, title, source, classified_sectors, confidence
- `CRE_KEYWORDS` filter removed from triage path (classification replaces it)
- Current scoring path still runs only on CRE-classified items

**Validation:** Run against live feeds for 5 consecutive days. Verify: (1) CRE article output unchanged, (2) non-CRE items correctly classified into their sectors, (3) classification audit log shows confidence distributions, (4) source health tracking works for new feeds.

### Phase C: Scoring + Ranking (Week 3)

**Goal:** Scoring engine runs on all classified items across all 7 sectors. Ranking selects top ~30 per sector. Shadow mode: compare with old pipeline output.

**Deliverables:**
- Create all 7 scoring profiles in `config/scoring_profiles.json`
- Enhance `config/watchlists.json` with entities for all 7 sectors
- Create `scripts/scoring_engine.py` 
- Create `scripts/ranking.py`
- Scoring runs on all classified items (not just CRE)
- Ranking produces per-sector Top 30 lists
- Shadow mode: log "would have published" for non-CRE sectors to `audit/{date}-shadow.jsonl`
- CRE sector runs through both old and new scoring paths; compare results
- Daily report: "Shadow Run: Would have published X articles across 7 sectors"

**Validation:** (1) CRE scoring output matches old pipeline within acceptable tolerance (±5 points), (2) non-CRE sector scoring produces reasonable distributions (not all items scoring 0 or 100), (3) ranking diversity controls working (no single subsector dominates), (4) cost tracking confirms scoring engine runs at $0 (deterministic), (5) shadow output passes manual editorial review for quality.

### Phase D: Multi-Sector Generation (Week 4)

**Goal:** Writing prompts and templates for all 7 sectors. Non-CRE articles generated in shadow mode. CRE pipeline still uses old generation path.

**Deliverables:**
- Create all sector prompt templates in `config/prompts.json` (7 sectors × 3-4 article types)
- Create sector voice mode definitions in `config/editorial_voices.json`
- Create `scripts/generation.py` 
- Enhance `scripts/content_governance.py` with 4 new sector-specific gates
- Non-CRE articles generated in shadow mode → saved to `audit/{date}-generated/` for editorial review
- Self-repair loop validated against new sector prompts (do repair instructions work for non-CRE voice modes?)
- Article templates for Deal Tape and Signal tiers created
- Editorial voice modes tested with sample dossiers for each sector

**Validation:** (1) Generate sample articles for each sector × article type combination (minimum 21 articles: 7 sectors × 3 tiers), (2) editorial review of shadow articles — do they read like sector-appropriate analysis? (3) quality gate pass rates per sector, (4) self-repair loop effectiveness per sector, (5) template-based Deal Tape generation produces correct structured output.

### Phase E: Publishing + Full Cutover (Week 5)

**Goal:** Publishing module handles multi-sector output. Old single-edition pipeline deprecated. All 7 sectors active in production.

**Deliverables:**
- Create `scripts/publishing.py` with template rendering + per-sector manifests + sector RSS feeds
- Create 7 sector landing page HTML templates: `insights-cre.html`, `insights-pe.html`, etc.
- Create shared article template with linked CSS (replaces inlined CSS approach)
- Build `scripts/admin_dashboard.py` with per-sector panels
- Enhancement to `insights-admin.html` with real-time data panels
- Full cutover: remove `USE_CONFIG_SOURCES` flag, remove old `CRE_KEYWORDS` triage path, remove hardcoded source lists
- Old `daily_news_agent.py` preserved as `daily_news_agent_legacy.py` for reference (1 week retention)
- Documentation update: README, QUICKSTART, DEPLOYMENT docs updated for new architecture

**Cutover checklist:**
- [ ] All 7 sector source pools returning stories
- [ ] Classification confidence >85% for Tier 1-2 (deterministic) items
- [ ] Scoring distribution healthy per sector (bell curve, not bimodal)
- [ ] At least 20 articles/sector/day in shadow mode for 3 consecutive days
- [ ] Quality gate pass rate >90% across all sectors
- [ ] Publishing pipeline produces valid HTML, JSON, XML without errors
- [ ] Netlify deploy succeeds with multi-sector structure
- [ ] Cost per run within `config/cost_limits.json` ceiling
- [ ] Editorial review approves shadow articles for all 7 sectors
- [ ] Rollback plan tested (revert to legacy pipeline in <5 minutes by reverting git commit)

---

## 6. Cost Model

### 6.1 Cost Assumptions

| Parameter | Value | Source |
|-----------|-------|--------|
| Candidates ingested per day | 2000-5000 | From 200+ sources across 7 sectors |
| Candidates classified by LLM (ambiguous) | ~200 (10%) | Classification ladder resolves 90% deterministically |
| Items scored per day | ~700 (after clustering) | ~35% of candidates form event clusters |
| Articles generated per day | 210 | 30 per sector × 7 sectors |
| Tier 1 (Flagship) articles | ~35/day | ~5/sector, premium model |
| Tier 2 (Brief) articles | ~70/day | ~10/sector, premium model |
| Tier 3 (Deal Tape) articles | ~105/day | ~15/sector, mid-tier model |
| DeepSeek-V4-Pro input cost | $0.14 / 1M tokens | Public pricing |
| DeepSeek-V4-Pro output cost | $0.28 / 1M tokens | Public pricing |
| DeepSeek-chat input cost | $0.014 / 1M tokens | Public pricing (assumed 10× cheaper) |
| DeepSeek-chat output cost | $0.028 / 1M tokens | Public pricing (assumed 10× cheaper) |
| OpenAI GPT-4o-mini cost | $0.15/$0.60 per 1M in/out | Fallback pricing |

### 6.2 Per-Phase Cost Breakdown (Daily)

| Phase | Activity | Calls/Day | Tokens In/Out (avg) | Model | Cost/Day |
|-------|----------|-----------|---------------------|-------|----------|
| **Classification** | Ambiguous item LLM classification | 200 | 500/150 | deepseek-chat | ~$0.01 |
| **Clustering** | Deterministic only | 0 | — | None | $0.00 |
| **Scoring** | Deterministic only | 0 | — | None | $0.00 |
| **Scoring (LLM overlay)** | Borderline cases (5% of scored) | 35 | 800/200 | deepseek-chat | ~$0.01 |
| **Enrichment** | Editorial room (Tier 1-2 only) | 105 | 1500/300 | deepseek-chat | ~$0.03 |
| **Generation (Tier 1)** | Flagship articles | 35 | 3000/1000 | deepseek-v4-pro | ~$0.88 |
| **Generation (Tier 2)** | Brief articles | 70 | 2000/600 | deepseek-v4-pro | ~$1.18 |
| **Generation (Tier 3)** | Deal tape articles | 105 | 800/200 | deepseek-chat | ~$0.12 |
| **Quality Control** | Deterministic only | 0 | — | None | $0.00 |
| **Publishing** | Deterministic only | 0 | — | None | $0.00 |
| **TOTAL** | | | | | **~$2.23/day** |

### 6.3 Monthly and Annual Projections

| Metric | Value |
|--------|-------|
| Daily cost | ~$2.23 |
| Monthly cost (30 days) | ~$66.90 |
| Annual cost | ~$814 |
| Cost per article (210/day) | ~$0.011 |
| Cost per candidate (2500/day) | ~$0.0009 |

### 6.4 Comparison to Current System

| Metric | Current | Target | Change |
|--------|---------|--------|--------|
| Articles/day | 0-3 (avg 0.64) | 210 | +32,700% |
| Daily cost | ~$0.04 (avg) | ~$2.23 | +5,475% |
| Cost per article | ~$0.07 | ~$0.011 | -84% |
| Sectors covered | 1 | 7 | +600% |
| Sources | 103 | 200+ | +94% |
| Zero-output days | 78.8% | 0% | — |

### 6.5 Cost Control Mechanisms

1. **Deterministic-first design:** Classification, scoring, and quality control run at $0 cost. LLMs are invoked only for ambiguous classification (~10% of items), editorial room analysis (Tier 1-2 only), and article generation. This keeps LLM costs confined to phases where the model adds genuine value.
2. **Daily cost ceiling:** `config/cost_limits.json` defines a hard daily cap. If the cost tracker detects that the cumulative daily spend exceeds the ceiling, the pipeline: (a) downgrades remaining Tier 1 articles to Tier 2 (cheaper generation), (b) skips editorial room for Tier 2 items, (c) logs the cost ceiling event to the audit log.
3. **Tiered model usage:** The most expensive model (DeepSeek-V4-Pro) is used only for ~105 articles/day (Tiers 1-2) where writing quality directly impacts the product. Deal tape items (~105/day) use a 10× cheaper model. Editorial room uses the cheap model for all items.
4. **Cost tracking per dimension:** Every API call is logged with: phase, sector, model, tokens in, tokens out, estimated cost, and latency. The admin dashboard displays cost per sector and per article type, enabling operators to identify and address cost anomalies.
5. **Fallback chain:** If the premium model (DeepSeek-V4-Pro) is unavailable, the model router falls back to deepseek-chat (for Tier 1-2 generation, with a logged quality risk). If deepseek-chat is also unavailable, falls back to GPT-4o-mini. Each fallback step is logged as a cost deviation event.

---

## 7. Key Design Decisions

### Decision 1: JSON Files Over Database

**Choice:** All persistent data — configuration, manifests, audit logs, source health — stored as JSON/JSONL files in the git repository.

**Rationale:**
- **Simplicity:** Zero database setup, zero connection management, zero migration scripts. The pipeline reads files, writes files, commits files. The entire system state is inspectable in the git history.
- **Netlify compatibility:** The static site hosting model means all data must exist as files at deploy time. A SQLite database would require a serverless function layer for querying — adding complexity, latency, and cost.
- **Git as audit trail:** Every pipeline run produces a git commit. The diff shows exactly which articles were added, which manifests changed, and which scores were assigned. This is a stronger audit trail than a database with separate backup procedures.

**When to migrate:** If and when article count exceeds 5,000 active articles in the rolling manifest (estimated at ~24 days of operation at 210/day), client-side JSON parsing of the sector manifest may become slow. At that point, the sector landing pages can be split into weekly paginated files (already designed for) or a lightweight serverless-backed search index can be added.

### Decision 2: Single GitHub Actions Run Over Distributed Workers

**Choice:** The entire pipeline runs as a single GitHub Actions workflow job (6-hour timeout), not as a distributed system with separate worker services.

**Rationale:**
- **Sufficient capacity:** With concurrent ingestion (100 threads), parallel classification (regex is instant), batched LLM calls (async generation), and template-based publishing, the full pipeline completes in ~90-140 minutes — well within the 6-hour timeout.
- **Operational simplicity:** One cron schedule. One set of logs. One commit per day. One rollback surface. No queue management, no worker health monitoring, no distributed coordination.
- **Cost:** GitHub Actions provides 2,000 free minutes/month for private repos. The pipeline runs once daily for ~2 hours = ~60 hours/month = well within the free tier.

**When to consider distributed workers:** If sources grow beyond 500 (requiring >30 min for ingestion), if article generation targets exceed 500/day (requiring >3 hours for concurrent LLM calls), or if the pipeline needs to run multiple times per day (breaking news updates). For the 200-source, 210-article/day mandate, a single runner is sufficient.

### Decision 3: Templated HTML Over Static Files

**Choice:** Articles rendered from a shared HTML template with linked CSS/JS, not standalone files with inlined everything.

**Rationale:**
- **File size:** A standalone article with inlined CSS is ~30 KB. A template-rendered article with external CSS is ~8-12 KB. At 210 articles/day × 365 days, that's 5.8 GB vs 2.3 GB of repository growth per year — and 76,650 full-HTML pages that git must diff and Netlify must deploy.
- **Maintainability:** A CSS change (e.g., new brand color, fixed layout bug) requires editing one `article-base.css` file rather than re-rendering 76,650 HTML files.
- **Netlify deploy:** 200 new 8 KB files per day commit and deploy faster than 200 new 30 KB files.

**Trade-off:** Template-rendered pages require the CSS file to be available at the expected path. This is guaranteed by the repository structure (article-base.css is in insights/) and the publishing module's validation step that checks CSS link integrity before commit.

### Decision 4: Deterministic-First Scoring Over LLM-Only

**Choice:** Scoring is 100% deterministic (regex, entity lookup, threshold comparison, weighted arithmetic). An optional LLM overlay exists for borderline cases only (<5% of items).

**Rationale:**
- **Cost:** LLM-scoring 2,000 candidates/day would cost ~$10/day alone. Deterministic scoring costs $0.
- **Auditability:** "Why did this story score 82?" → deterministic explanation: "Financial mag=90 × 0.22 + Market sig=85 × 0.15 + ... = 82.56." LLM scores are opaque — "the model thought it was important" is not an audit trail.
- **Speed:** Deterministic scoring takes <5ms per item (regex + arithmetic). LLM scoring takes 200-500ms per item (API call latency). At 700 scored items/day, that's 3.5 seconds vs. 3-6 minutes.
- **Consistency:** Deterministic scoring produces the same result for the same input every time. LLM scoring varies between calls — a story scored 78 on Monday might score 72 on Tuesday with identical inputs, undermining editorial consistency.

**LLM overlay use case:** When a story's score is within 5 points of a tier threshold (e.g., score=77 vs. Tier 1 cutoff=79), the LLM overlay provides a second opinion that can push the story over the threshold or confirm the deterministic score. This is used sparingly (~35 items/day) and the LLM's reasoning is logged alongside the deterministic score for editorial review.

### Decision 5: Modular Config Over Hardcoded Values

**Choice:** All business logic values — thresholds, weights, source lists, sector definitions, prompt templates, watchlists — reside in JSON configuration files, not in Python source code.

**Rationale:**
- **Non-engineer administration:** A business operator can add a new source, adjust a sector's scoring weight, or update an entity watchlist by editing a JSON file — no Python knowledge required, no redeploy required (pipeline reads latest config on each run).
- **Experimentation velocity:** Testing "what if we weight Policy Impact 2× higher for the Energy sector?" requires editing one number in a JSON file. In the current system, it requires finding and editing the `score_event()` function — a change that risks breaking the Python code.
- **Separation of concerns:** Config = what the business wants. Python = how the system works. This separation means the editorial team can tune the pipeline without risk of introducing code bugs.

**Trade-off:** JSON files have no compile-time validation. This is mitigated by `config_loader.py`'s `validate_config()` function, which runs at pipeline startup and checks schema consistency (enum values, required fields, value ranges). A broken config file causes the pipeline to halt with a clear error message — it does not silently produce garbage output.

### Decision 6: Classification Ladder Over Single-Pass LLM

**Choice:** Four-tier classification (source prior → regex → entity match → LLM) rather than a single LLM call per item.

**Rationale:**
- **Cost:** 90% of items are classified deterministically at $0. A single LLM classification pass on 2,500 items/day would cost ~$1.25/day. The ladder approach costs ~$0.01/day for the 10% that need LLM.
- **Speed:** Deterministic classification is <10ms total per item (three tiers summed). LLM classification is 200-500ms per item. At 2,500 items, deterministic-first is ~25 seconds vs. ~12 minutes for LLM-only.
- **Confidence tracking:** The ladder explicitly records which tier produced the classification and with what confidence. LLM-only classification produces a confidence score that is itself an LLM judgment — and LLMs are known to be overconfident in their own assessments.

### Decision 7: Within-Sector Ranking Over Global Ranking

**Choice:** Stories are ranked and selected within their primary sector pool (30 per sector), not against a global pool of all stories across all sectors.

**Rationale:**
- **Fair competition:** A local government zoning reform in Chicago should compete against other local government stories, not against Blackstone's $5.2B infrastructure fund. Global ranking would starve the "smaller" sectors (Local Gov, Fed/Macro) of publishing slots.
- **Audience guarantee:** Each sector's audience (PE LPs, energy traders, municipal finance officers) is guaranteed ~30 stories/day regardless of what's happening in other sectors. A slow week for CRE doesn't mean the Data Centers audience gets zero articles.
- **Sector-appropriate thresholds:** Tier cutoffs are computed dynamically from each sector's daily pool (percentile-based). This prevents fixed global thresholds from killing sectors with naturally lower score distributions (e.g., daily zoning board actions will never score as high as PE fund closes, but they're still important to their audience).

### Decision 8: Per-Sector RSS Feeds Over Single Feed

**Choice:** Seven independent RSS feeds (`feed-cre.xml`, `feed-private-equity.xml`, etc.) rather than one combined feed with category filtering.

**Rationale:**
- **Audience segmentation:** The Data Centers RSS feed targets data center operators, hyperscaler real estate teams, and power procurement professionals. The Local Government RSS feed targets municipal officials, land-use attorneys, and planning consultants. These are different audiences with different information needs. They should not have to filter a combined feed of 210 items/day for the 30 they care about.
- **RSS reader performance:** A single feed with 210 items/day would be ~1,470 items/week — many RSS readers timeout or degrade with feeds this large. Seven feeds of 30 items/day each (~210/week) are well within normal RSS reader capacity.
- **SEO:** Each sector feed has its own title, description, and taxonomy — improving discoverability for sector-specific search queries.

### Decision 9: Dynamic Percentile Thresholds Over Fixed Score Gates

**Choice:** Tier thresholds are computed dynamically from the day's pool (top 10% = Tier 1, top 40% = Tier 2) rather than using fixed absolute scores.

**Rationale:** The current system's fixed `MUST_READ_THRESHOLD = 56` produces zero articles on 78.8% of days because thin news days produce no stories above 56. Dynamic thresholds guarantee ~30 stories per sector per day regardless of absolute score levels — while still selecting the best stories from that day's pool. On a blockbuster day (3 major PE fund closes, a Fed rate decision, and a FERC market restructuring order), the Tier 1 cutoff might be 85. On a slow Friday in August, the cutoff might be 62. Both days produce 30 articles — but the quality bar adapts to the news environment.

### Decision 10: Reuse Core Infrastructure Over Rewrite

**Choice:** Carry forward the existing well-engineered infrastructure — event clustering, evidence classification, quality gates, self-repair loop, model router, checkpoint/resume, cost tracking, and rollback mechanism — with sector-aware enhancements rather than rewriting from scratch.

**Rationale:** The executive assessment confirmed that the core infrastructure is solid. The clustering algorithm, evidence dossier builder, 10 quality gates, self-repair loop, and commit-or-rollback publishing mechanism are sector-agnostic and battle-tested through 33 editorial runs. The gap is not in these mechanisms — it's in the single-sector scope, the CRE keyword gate, the universal scoring model, and the monochromatic publishing architecture. By generalizing these components (adding sector parameters) rather than rewriting them, the migration preserves proven infrastructure while expanding the pipeline's scope.

**What stays:** `cluster_events()`, `build_research_dossier()`, `run_editorial_room()`, `content_governance.py` (10 gates), `model_router.py`, `checkpoint.py`, `cost_tracker.py`, `fact_extractor.py`, `social_image_generator.py`, `linkedin_essay_agent.py`, git-commit-or-rollback pattern.

**What changes:** Source definitions (from Python tuples to JSON config), ingestion (from monolithic fetch to per-sector workers), classification (from binary CRE gate to multi-label ladder), scoring (from single 10-dim profile to 7 sector profiles), ranking (from global threshold to within-sector dynamic), generation (from CRE-only prompts to 7 sector prompt families), publishing (from single manifest/feed/page to 7 sector-specific outputs).

---

## Appendix A: File Map — Current vs. Target

| Current File | Lines | Target File(s) | Change |
|-------------|-------|----------------|--------|
| `news_sources.py` | ~400 | `config/sources.json` + `config/sectors.json` | Hardcoded tuples → structured JSON config |
| `daily_news_agent.py` | 2827 | `scripts/ingestion.py` + `scripts/generation.py` + `scripts/publishing.py` | Monolith → 3 specialized modules |
| `editorial_intelligence.py` | 912 | `scripts/scoring_engine.py` + `scripts/ranking.py` | Single-sector scorer → profile-driven engine |
| `story_normalizer.py` | ~400 | `scripts/canonical_item.py` (new) + `story_normalizer.py` (enhanced) | Ad-hoc dicts → typed dataclass |
| `bucketed_editorial.py` | 359 | `scripts/classification.py` | Binary routing → multi-label classification |
| `research_dossier.py` | 236 | `scripts/enrichment.py` | Enhanced with sector-specific fact patterns |
| `editorial_room.py` | ~250 | `scripts/enrichment.py` | Enhanced with sector questioning patterns |
| `content_governance.py` | 217 | `scripts/content_governance.py` | +4 sector-specific gates |
| `enhanced_prompts.py` | ~500 | `config/prompts.json` + `config/editorial_voices.json` | Python strings → JSON config |
| `editorial_voice.py` | 525 | `config/editorial_voices.json` | CRE-only voice modes → per-sector voice families |
| `model_router.py` | 113 | `scripts/model_router.py` | Tiered model selection added |
| `checkpoint.py` | 77 | `scripts/checkpoint.py` | Phase timeout values externalized to config |
| `cost_tracker.py` | ~100 | `scripts/cost_tracker.py` | +phase/sector/tier dimension tracking |
| `health_report.py` | ~127 | `scripts/admin_dashboard.py` | Basic report → multi-sector dashboard |

## Appendix B: New Files to Create

| File | Purpose |
|------|---------|
| `config/sources.json` | 200+ source definitions across 7 sectors |
| `config/sectors.json` | Sector definitions, subsector taxonomy, regex patterns |
| `config/scoring_profiles.json` | 7 per-sector scoring profiles |
| `config/watchlists.json` | Named entities × sectors with tier classification |
| `config/prompts.json` | System prompts per sector × article type |
| `config/editorial_voices.json` | Voice mode definitions per sector |
| `config/thresholds.json` | Per-sector tier thresholds and diversity caps |
| `config/selection_rules.json` | Per-sector target counts, selection logic |
| `config/clustering.json` | Clustering similarity thresholds and rules |
| `config/cost_limits.json` | Daily cost ceilings per phase |
| `scripts/canonical_item.py` | CanonicalItem dataclass, enums, serialization |
| `scripts/config_loader.py` | Config loading, validation, path resolution |
| `scripts/ingestion.py` | Per-sector concurrent ingestion workers |
| `scripts/classification.py` | 4-tier multi-label classification ladder |
| `scripts/clustering.py` | Sector-aware event clustering |
| `scripts/scoring_engine.py` | Profile-driven deterministic scoring engine |
| `scripts/ranking.py` | Within-sector ranking, diversity controls, selection |
| `scripts/enrichment.py` | Research dossier building with sector patterns |
| `scripts/generation.py` | Sector-aware article generation with tiered models |
| `scripts/publishing.py` | Template rendering, per-sector manifests, RSS feeds |
| `scripts/admin_dashboard.py` | Multi-sector observability dashboard data API |
| `scripts/audit.py` | Audit log writer and query interface |

## Appendix C: Editorial Sector Taxonomy

| Sector | Slug | Primary Audience | Subsectors |
|--------|------|-----------------|------------|
| Commercial Real Estate | `commercial-real-estate` | Owners, developers, lenders, brokers, REIT executives | office, multifamily, industrial, retail, hotel/lodging, life-science, self-storage, senior-housing, manufactured-housing, mixed-use, land/development, affordable-housing |
| Private Equity | `private-equity` | LPs, GPs, fund managers, placement agents, investment bankers | buyout, growth-equity, venture-capital, secondaries, fund-of-funds, infrastructure, private-credit, distressed/special-situations, real-assets, co-investment |
| Data Centers | `data-centers` | Hyperscaler real estate teams, colocation operators, power procurement, fiber providers | hyperscale-cloud, colocation/retail, edge-computing, fiber/network, power-infrastructure, cooling/mechanical, modular/prefab, interconnection/exchange |
| Energy | `energy` | Utility executives, project developers, traders, regulators, PPA buyers | generation (solar, wind, gas, nuclear, hydro, battery-storage), transmission, distribution, RTO/ISO-markets, power-purchase, oil-and-gas, renewables-tax-equity, carbon/recs |
| Banking / Credit | `banking-credit` | Bank executives, credit officers, regulators, fintech operators | commercial-lending, consumer-lending, mortgage-banking, regulatory-capital, fintech/digital-banking, payments, M&A-advisory, loan-trading, CRA/compliance, community-banking |
| Fed / Macro | `fed-macro` | Economists, strategists, portfolio managers, policy analysts | monetary-policy, labor-markets, inflation, GDP/growth, housing-data, trade/flows, fiscal-policy, global-central-banks, fixed-income |
| Local Government | `local-government` | Municipal officials, land-use attorneys, developers, civic organizations | zoning/land-use, tax-incentives/abatements, municipal-bonds, infrastructure-spending, housing-policy, public-procurement, economic-development, permitting/licensing, transit/orientation |

---

**Document Status:** Complete — Ready for Phase A implementation.

**Next Steps:** Begin Phase A migration: create `config/` directory with initial `sources.json` containing all 103 current sources mapped to their sectors. Create `scripts/canonical_item.py` and `scripts/config_loader.py`. Enable config-based path with feature flag. Validate identical output to current pipeline.

(End of file - total 680 lines)
