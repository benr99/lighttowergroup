# Gap Analysis: The Light Tower Group Insights Intelligence Engine

**Document:** 04-Gap-Analysis
**Date:** July 30, 2026
**Status:** Current vs. Mandated State — Seven-Sector Coverage Gap Assessment

---

## 1. Source Coverage Gap

The current RSS feed inventory (`news_sources.py:7-113` plus `FEDERAL_RSS_FEEDS` at line 119-135) was assembled to serve a single purpose: NYC CRE capital markets intelligence. The mandate requires coverage spanning seven distinct sectors — only one of which (CRE) has adequate feed density. The remaining six sectors are either sparsely represented or entirely absent.

| Sector | Current Feeds | Current Status | Needed Feeds | Key Missing Sources |
|---|---|---|---|---|
| **CRE / Real Estate** | 60+ feeds (The Real Deal, Commercial Observer, Bisnow × 12 markets, GlobeSt, Connect CRE, CoStar, NREI, CP Executive, Multi-Housing News, etc.) | Adequate for current daily volume; ~60 CRE-specific feeds | Maintain existing; add targeted sub-sector feeds for industrial, life-science, data center RE, self-storage | N/A — CRE is the strongest sector |
| **Private Equity** | 3 marginal feeds (PERE News, Institutional Real Estate, IREI News) | Weak — PERE and IREI cover institutional real estate allocation, not PE writ large | 25-35 feeds | PitchBook News, Preqin Insights, Buyouts Insider, PE Hub, The Deal Pipeline, Secondaries Investor, Infrastructure Investor, Private Debt Investor, Mergermarket, Bloomberg PE, WSJ Private Equity, Financial Times Due Diligence, PEI Media network |
| **Data Centers** | 0 dedicated feeds | None — no sector-specific ingestion exists | 15-25 feeds | Data Center Dynamics, Data Center Frontier, Data Center Knowledge, The Register (data center section), Mission Critical Magazine, Bisnow Data Centers, CBRE Data Center Solutions, JLL Data Centers, TPC (Total Data Center), AFCOM, Uptime Institute, Structure Research, Green Street (data center REIT coverage) |
| **Energy** | 0 dedicated feeds | None — no energy sector ingestion exists | 20-30 feeds | S&P Global Commodity Insights, Reuters Energy, BloombergNEF (BNEF), RTO Insider, EIA Today in Energy, FERC news releases, Utility Dive, Power Magazine, Greentech Media, Wood Mackenzie, Rystad Energy, Solar Power World, North American Windpower, Energy Storage News, Hart Energy, Oil & Gas Journal, NERC, PJM, ERCOT, CAISO market notices |
| **Banking / Credit** | 6 feeds (American Banker, MBA Newslink, Mortgage Professional, Mortgage News Daily, Trepp Blog, CREFC) | Narrow — all 6 are CRE-adjacent; no general banking or credit coverage | 20-30 feeds | Bank Director, S&P Global Market Intelligence (banking section), KBW Research, The Financial Brand, Risk.net, GlobalCapital, Asset-Backed Alert, Structured Finance Association, LevFin Insights, Covenant Review, CreditSights, LCD (Leveraged Commentary & Data), Fitch Ratings, Moody's, S&P Ratings |
| **Federal Reserve / Macro** | 15 federal feeds (Fed press releases, monetary policy, banking regulation, enforcement, speeches, testimony, credit & liquidity, H.8 data; OCC; SEC × 4; FDIC) | Good for primary source ingestion; lacks secondary market analysis | 10-15 feeds | Fed Guy (Joseph Wang), Macro Musings (Mercatus), Real Time Economics (WSJ), FT Alphaville, The Overshoot (Matt Klein), Calculated Risk, Bloomberg Economics, Reuters Macro Matters, BIS, IMF, CBO, CFPB |
| **Local Government** | 0 dedicated feeds; 10 MSA keyword aliases defined in `TOP_MSA_GOVERNMENT_LANES` (line 141-152) but only match against existing business journal feeds | None — lane definitions exist but no dedicated ingestion | 25-35 feeds (10 MSAs × 2-3 feeds each) | NYC: CityLand, City Council press, NYC Planning, NYS Homes; LA: LA City Planning, CA Dept of Housing; Chicago: City Clerk legislative, IL Housing Development; Dallas: City Council, TX Dept of Housing; Houston: City Council, TX Comptroller; DC: DC Council, WMATA, NCR; Miami: Miami-Dade County, FL Housing; Atlanta: Invest Atlanta, GA DCA; Boston: Boston Planning, MA Housing; SF: SF Planning, Bay Area Council |

### The Federal Feed Inventory: Quality vs. Purpose Mismatch

The 15 federal RSS feeds (lines 119-135) are high-quality primary sources, but they exist as a parallel lane that feeds into the pipeline's secondary CRE assessment. A Federal Reserve enforcement action or an SEC litigation release arrives at the same CRE keyword gate that filters multifamily transactions — because the current triage cannot distinguish a banking regulatory event from a broker announcement. The feeds exist; the infrastructure to use them independently of the CRE filter does not.

### NewsAPI: CRE-Constrained Queries

The 16 `NEWSAPI_QUERIES` (lines 213-230) are uniformly CRE-shaped. Queries like "NYC commercial real estate mortgage 2026" and "Brooklyn commercial real estate deal" lock the supplementary discovery layer into the same single-sector scope. No queries target data center construction, energy M&A, local government procurement, or PE fundraising — the categories the mandate requires.

---

## 2. Ingestion and Triage Gap

### 2.1 The CRE_KEYWORDS Hard Kill Switch

The primary editorial intake path uses `_is_cre_relevant()` at `daily_news_agent.py:355-359`:

```python
def _is_cre_relevant(story: dict) -> bool:
    text = (story["title"] + " " + story["summary"]).lower()
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text for kw in CRE_KEYWORDS)
```

This is a binary, lossy, sector-specific gate. Every single story — regardless of its source, lane, or potential sector relevance — must contain at least one string from `CRE_KEYWORDS` (defined at `news_sources.py:234-266`). The keyword list is exhaustive of CRE terms: 36 NYC neighborhoods, 18 CRE financing terms, 9 asset classes, 12 transaction types, 7 regulatory codes (421a, 421g, j51, etc.). But it contains zero terms for: data centers, energy generation/transmission, PE fundraising outside of real estate, local government procurement, general banking regulation, or Fed macro policy not explicitly tied to real estate.

The impact is structural, not edge-case. A story with the headline **"Blackstone Raises $8B for Energy Transition Fund"** fails `_is_cre_relevant()` because it contains "private equity" (line 262) but does not reference any real estate asset class or CRE financing term. A story titled **"DataBank Secures $2.1B for Hyperscale Data Center Campus in Northern Virginia"** fails because the only match candidates in `CRE_KEYWORDS` are "industrial" (line 237) and "warehouse" (line 237) — a data center is neither. A story titled **"Fed Raises Capital Buffer Requirements for Regional Banks by 200bp"** fails unless it happens to mention "mortgage," "commercial real estate," or one of the CRE financing terms included in the keyword list.

The `triage()` function at `daily_news_agent.py:385-389` applies this filter sequentially, then logs its own destructive effect:

```python
def triage(stories: list, recent_hours: int = 36) -> list:
    relevant = [s for s in stories if s["url"] and _is_cre_relevant(s) and _is_recent(s, recent_hours)]
    unique   = _deduplicate(relevant)
    print(f"  Triage: {len(stories)} raw → {len(relevant)} relevant → {len(unique)} unique")
    return unique
```

### 2.2 The Bucketed Volume Path: An Improvement, Not a Replacement

The newer `triage_bucketed_volume()` at `daily_news_agent.py:510-528` does not use `_is_cre_relevant()` directly. Instead, it calls `route_story()` (from `bucketed_editorial.py`) and admits any story that maps to at least one editorial bucket. This is a structural improvement — it was designed to let banking, PE, and policy stories through.

However, `route_story()` itself at `bucketed_editorial.py:93-129` maps stories to only 5 CRE sub-domain buckets:

| Bucket Key | Bucket Label |
|---|---|
| `cre_capital_markets` | CRE Capital Markets |
| `cre_transactions_development` | CRE Transactions & Development |
| `banking_credit` | Banking & Credit |
| `private_equity_private_capital` | Private Equity & Private Capital |
| `policy_rates_public_markets` | Policy, Rates & Public Markets |

The bucket matching relies on regex patterns (`_BUCKET_PATTERNS` at lines 40-63) that are CRE-anchored. The `banking_credit` pattern requires terms like "commercial real estate exposure," "loan loss," or "credit standard." The `policy_rates_public_markets` pattern includes general terms (`reit`, `treasury`, `interest rate`, `inflation`) but the function then applies a secondary filter at lines 102-111 that **removes** the policy bucket match unless the story also has `_has_property_context()` or contains a policy authority name. The result: a story about the Fed raising rates because of services inflation, with no real estate angle, gets dropped. A story about municipal zoning reform in Phoenix without an explicit CRE mention gets dropped.

### 2.3 The July 26 Baseline

On July 26, 2026, the pipeline ingested ~1,807 raw stories from RSS feeds, NewsAPI, and SEC EDGAR. After normalization and deduplication, the `triage()` function (`daily_news_agent.py:385-389`) produced:

```
Triage: 1807 raw → 14 relevant → 14 unique
```

That is a 99.2% reduction — not from noise and deduplication (which is healthy), but from a keyword gate that cannot recognize stories from 6 of the 7 mandated sectors. The 14 survivors were all CRE stories. From those 14 candidates, the `select_edition()` function in `editorial_intelligence.py` produced 0 articles that met the MUST_READ threshold — a 0% yield run.

Under the mandate's 210 articles/day target, this pipeline would need to admit at least 2,000 candidates from across all sectors. The current infrastructure kills 99.2% of incoming stories at the first processing stage.

### 2.4 What the Mandate Requires

The triage layer must be replaced with a multi-sector admission layer that:

1. **Routes by sector, not by CRE keyword match.** A data center story should be classified as Data Centers, not forced through a CRE gate.
2. **Logs rejection with reason codes.** The current system silently discards stories. An operator should know why each story was rejected (sector mismatch? source quality? recency? deduplication?).
3. **Applies sector-specific relevance filters, not a universal CRE gate.** A bank regulation story should be assessed against banking relevance criteria. A local government story should be assessed against MSA relevance criteria.
4. **Preserves all sector candidates through the scoring phase.** Current: triage → score → select. Required: ingest → classify by sector → score per sector → select per sector.

---

## 3. Classification Gap

### 3.1 Current: Binary and CRE-Specific

The `story_normalizer.py` module enriches raw stories with topic tags, entity extraction, and attention features. Its `TOPIC_PATTERNS` dictionary (lines 33-62) defines 15 topic categories, all CRE-anchored:

| Pattern Key | Domain |
|---|---|
| `major_sale` | CRE transactions |
| `capital_placement` | CRE debt/equity |
| `mna` | M&A (CRE-adjacent) |
| `fed_rates` | Monetary policy |
| `bank_credit` | Bank CRE exposure |
| `private_credit` | CRE private credit |
| `private_equity` | PE (real estate funds) |
| `distress` | CRE distress |
| `cmbs` | Commercial MBS |
| `policy` | CRE/housing policy |
| `reit_public_markets` | REITs |
| `development_finance` | CRE development |
| `capital_expenditure` | CRE capex |
| `leasing` | CRE leasing |
| `market_fundamentals` | CRE market data |
| `government_action` | Policy/regulatory |

Zero patterns exist for: data center development, energy generation/transmission, power purchase agreements, semiconductor manufacturing, renewable energy tax credits, municipal bond issuance, local zoning without a CRE hook, general banking regulation without CRE transmission, or PE buyouts of operating companies outside real estate.

### 3.2 What the Mandate Requires: Multi-Label Classification

Under the mandate, every candidate story must be classified into one or more of the 7 sectors, with a primary sector assignment for display routing and secondary assignments for cross-referencing. Consider a concrete example:

> **"Blackstone Acquires QTS Data Center Portfolio for $10B Using Private Credit Facility; Texas County Approves $240M in Property Tax Abatements"**

This story should be classified as:

- **Primary:** Data Centers (the subject matter is data center real estate and infrastructure)
- **Secondary:** Private Equity (Blackstone is a PE firm executing a major acquisition), Banking/Credit (private credit facility financing), Energy (data centers are energy infrastructure with power procurement implications), Local Government (property tax abatements from a county authority), CRE (data centers are a real estate asset class)

The current system would classify this story as `major_sale` + `private_equity` + `private_credit` — three topics that fail to capture the data center and energy dimensions entirely, and that route the story into the CRE editorial pipeline where it would be written as a real estate transaction piece.

### 3.3 Entity Extraction: CRE-Institution Bias

The `KNOWN_INSTITUTIONS` list at `story_normalizer.py:24-31` is exclusively CRE, banking, and brokerage firms:

```python
KNOWN_INSTITUTIONS = [
    "blackstone", "brookfield", "apollo", "starwood", "ares", "kkr",
    "carlyle", "tpg", "cerberus", "sl green", "vornado", "related", "tishman",
    "jpmorgan", "jp morgan", "goldman", "morgan stanley", "wells fargo",
    "bank of america", "citigroup", "citi", "deutsche bank", "barclays",
    "federal reserve", "fed", "fdic", "occ", "treasury", "fannie mae",
    "freddie mac", "hud", "cbrem", "cbre", "jll", "cushman",
]
```

Missing institutions needed for multi-sector coverage: NextEra, Dominion, Duke Energy, Exelon, Southern Company, Vistra, Constellation (Energy); Digital Realty, Equinix, CyrusOne, DataBank, Vantage, Stack Infrastructure (Data Centers); KKR Infrastructure, Brookfield Infrastructure, Global Infrastructure Partners, Macquarie, IFM Investors (Infrastructure PE); county governments, city councils, planning commissions, public utility commissions (Local Government).

### 3.4 Asset Class Taxonomy: CRE-Only

The `ASSET_CLASSES` dictionary at `story_normalizer.py:73-100+` recognizes: office, multifamily, industrial/warehouse, retail/hotel, land/development, mixed-use, affordable housing, life science, self-storage, manufactured housing, and senior housing. It does not recognize: data centers, fiber networks, cell towers, renewable energy facilities, battery storage, transmission infrastructure, sports venues, or government facilities — asset classes that the mandate requires the system to cover.

---

## 4. Scoring Gap

### 4.1 Current: Universal 10-Dimension Framework

The `score_event()` function at `editorial_intelligence.py:498-634` produces a `must_read_score` on a 0-100 scale using 12 weighted components (10 positive, 2 penalty):

| Dimension | Max Points | Signal |
|---|---|---|
| `consequence` | 15 | Material transaction, operating signal, big number, distress/policy topics |
| `novelty` | 15 | First/record/historic language, cross-source corroboration |
| `conflict_and_power` | 15 | Distress, lawsuit, dispute, government action |
| `explanatory_value` | 15 | Topic count, causality/pressure/constraint language |
| `cultural_relevance` | 10 | Sports, entertainment, technology, status, cities, climate, politics |
| `human_stakes` | 10 | Jobs, rents, displacement, affordability |
| `evidence_depth` | 10 | Source quality weighted by tier and federal/primary authority |
| `light_tower_right_to_win` | 10 | Capital markets familiarity and topical fit |
| `conversation_potential` | 10 | Derived from conflict, culture, and novelty scores |
| `audience_learning_adjustment` | -5 to +5 | Audience signal weights from config |
| `routine_event_penalty` | -18 | Pattern-matched routine transactions |
| `archive_repetition_penalty` | -18 | Previously covered events |

Every story across every sector is scored against this identical framework. The framework was designed for CRE capital markets — it rewards distress, debt, capital placement, and property context. It provides no mechanism for a data center story to receive elevated scoring because 300MW of new capacity is more significant than a $10M multifamily refinancing. The same 15-point `consequence` ceiling applies to both stories, and the scoring dimensions are agnostic to the sector context that gives a number its meaning.

### 4.2 What the Mandate Requires: Sector-Specific Scoring Profiles

The mandate requires per-sector scoring profiles that weight dimensions differently depending on context:

| Scoring Dimension | CRE Weight | PE Weight | Data Center Weight | Energy Weight | Banking Weight | Fed/Macro Weight | Local Gov Weight |
|---|---|---|---|---|---|---|---|
| **Financial Magnitude** | High | High | Medium | Medium | High | Low | Low |
| **Market Significance** | High | High | High | High | Medium | High | Medium |
| **Strategic Relevance** | Medium | High | High | Medium | High | High | High |
| **Policy Impact** | Medium | Low | Medium | High | High | High | High |
| **Novelty** | Medium | Medium | High | Medium | Medium | Medium | Medium |
| **Source Quality** | High | High | High | High | High | High | High |
| **Timeliness** | High | High | High | High | High | High | High |
| **Audience Utility** | High | High | Medium | Medium | High | High | High |
| **Editorial Potential** | High | Medium | Medium | Low | Medium | Medium | Medium |
| **Cross-Sector Importance** | Medium | High | High | High | High | High | High |

A sector-specific scorer would apply these weights at the dimensional level, producing different composite scores for the same event depending on which sector is evaluating it. A story about a 300MW data center campus would receive high magnitude and infrastructure impact scores under the Data Center profile; the same story under a CRE profile would parse the deal as "warehouse development" and rate it against office and multifamily comparables — fundamentally miscategorizing the asset.

---

## 5. Content Generation Gap

### 5.1 Current: CRE-Centric Prompt Architecture

The content generation layer consists of two primary prompts and a voice control library:

- `SYSTEM_PROMPT_ENHANCED` at `enhanced_prompts.py:10-193` — defines the writer's persona as a CRE capital markets analyst. Opens with: "You write the daily intelligence layer for CRE capital markets: what happened, why it happened now, what the money is really saying, and who should care." Defines the reader as "a CRE owner, developer, lender, broker, PE investor, family office principal, or REIT executive."
- `USER_PROMPT_TEMPLATE` at `enhanced_prompts.py:196-311` — frames every article as a "thesis-led commercial real estate capital markets analysis piece" and requires the writer to explain "the economics: basis, debt, maturity, liquidity, leverage, rates, sponsor quality, or demand."
- `EDITION_SYSTEM_PROMPT` at `enhanced_prompts.py:314-354` — provides similar CRE framing for the curated edition path.

The `VOICE_MODES` tuple at `editorial_voice.py:143-184` defines 8 narrative modes, all tailored to financial deal narrative:

| Voice Mode | Orientation |
|---|---|
| Underwriting margin | CRE deal underwriting |
| Basis autopsy | CRE basis analysis |
| Lender's-eye memorandum | CRE lending |
| Counterparty map | CRE transaction negotiation |
| City in the balance sheet | Physical CRE/urban assets |
| Consensus under cross-examination | Market consensus |
| Time as a cost of capital | CRE debt maturity |
| Operator's field note | CRE operations |

None of these voice modes are appropriate for a data center capacity report, a municipal zoning reform analysis, or a PSC rate case summary. If a Data Center story reached the writing phase, the system would assign it a voice mode based on pattern-matching against CRE topics — likely matching "capital placement" or "major sale" — and instructing the writer to "walk through the underwriting the way an actual sponsor or credit officer would." The generated article would read like a real estate deal memo, not an infrastructure capacity analysis.

### 5.2 Article Type: One Format for All Stories

The current system generates exactly one article format per story: an 800-1,050 word narrative insight with a thesis, narrative ledger, and excellence ledger. Every story — a $2M local zoning change in Boston, a $10B PE buyout, a Fed rate decision, a 500MW solar PPA — would receive identical structural treatment:

- Same length requirement (800-1,050 words)
- Same narrative ledger structure (anchor, tension, cast, mechanism, claim, reader consequence)
- Same excellence ledger structure (why_now, original_inference, counterargument, concrete_detail, human_stakes, reader_value, memorable_line, claim_evidence)
- Same franchise assignment system

The mandate requires article type variety mapped to sector and story magnitude:

| Article Type | Word Count | Evidence Requirement | Examples |
|---|---|---|---|
| **Flagship Analysis** | 800-1,100 | Multi-source dossier, confirmed facts | Major transactions, policy shifts, market inflection points |
| **Transaction Brief** | 300-500 | Single-source with entity extraction | $10M+ deals, fund closes, lease signings |
| **Policy Analysis** | 500-800 | Primary source text + regulatory context | Fed actions, local zoning, energy regulation |
| **Regulatory Note** | 200-400 | Single regulatory filing or order | SEC enforcement, FERC orders, banking bulletins |
| **Data Point / Market Note** | 150-300 | Single data release or survey | H.8 data, employment reports, construction starts |
| **Deal Tape Entry** | 100-200 | Transaction metadata only | Sub-$10M transactions, routine filings |

### 5.3 Franchise Assignment: Misapplied to Non-CRE Stories

The editorial intelligence module (`editorial_intelligence.py`) assigns each story to a franchise based on topic patterns and score thresholds. Franchises — "The Most Expensive Assumption," "The Basis Is the Deal," "The Shadow Book," etc. — are CRE conceptual frameworks. A data center capacity expansion assigned to "The Most Expensive Assumption" would be asked to "identify the premise on which the capital plan quietly depends" — useful framing, but the system would supply CRE comparables (cap rates, DSCR, rent rolls) that are irrelevant to power procurement contracts and interconnection queues.

---

## 6. Publishing and Display Gap

### 6.1 Current: Monolithic Single-Page + Flat Manifest

The current publishing architecture consists of:

- **One listing page:** `insights.html` with 6 category filters (Capital Markets, Market Analysis, Debt & Equity, Policy & Regulation, Deal Intelligence, Architecture & Capital Markets). All 331 published articles share a single landing page with a `data-category` attribute for client-side filtering.
- **One flat manifest:** `insights.json` — a JSON array of article metadata objects. Each entry has: `title`, `slug`, `date`, `publishedAt`, `readTime`, `category` (single-valued, one of 6 CRE categories), `excerpt`, `url`, `tags`, `format`, `franchise`, `mustReadScore`, `sourceCount`, `eventId`.
- **One HTML file per article:** `insights/{slug}.html` — one static HTML page per published article.
- **One RSS feed:** `feed.xml` with the title "Light Tower Group — NYC CRE Capital Markets Insights."

### 6.2 Scale Failure at 210 Articles/Day

At the mandate's target of 210 articles/day, the current approach produces:

- **76,650 HTML files per year** in the `insights/` directory. Netlify's build and deployment latency scales poorly with this file count. Git operations (add, commit, push) on 200+ new files per day would become a bottleneck.
- **A single `insights.json` manifest with 76,650 entries per year** — approximately 150MB of JSON. Client-side parsing of a monolithic manifest on every page load would degrade to seconds of latency. Pagination and filtering on the client-side over 76K items would be unusable.
- **One `insights.html` page listing thousands of articles** with client-side JavaScript filtering — pagination would need to be rewritten to handle 210 daily increments.
- **One `feed.xml` with thousands of entries** — RSS readers would timeout on parse.

### 6.3 Structural Limitations of the Current Manifest

The `insights.json` schema cannot represent the data model the mandate requires:

| Required Field | Current Support | Gap |
|---|---|---|
| Multi-label sector classification | Not supported — `category` is a single string from 6 CRE options | Need `sectors` array, `primary_sector` string |
| Article tier (flagship/brief/deal-tape) | Partially supported — `format` field exists but is inconsistently populated | Need explicit `tier` field with display consequences |
| Sector-specific metadata | None — all metadata is CRE-oriented | Need sector-specific fields: `power_mw`, `deal_size`, `jurisdiction`, `regulatory_docket`, `asset_type` |
| Cross-references | None | Need `related_articles`, `same_event_group`, `follow_up_to` |
| Data points extracted | None in manifest — data points exist in `body_html` only | Need structured `data_points` array per article |
| Geographic scope | None | Need `msa`, `state`, `region`, `national`, `international` |

### 6.4 What the Mandate Requires

- **7 sector landing pages** (one per sector) with sector-specific taxonomy, filtering, and RSS feeds
- **Templated rendering** — articles rendered from a template rather than generating full HTML per article; a shared layout with injected metadata
- **Tiered display logic** — flagship articles get hero treatment on the landing page; briefs get compact cards; deal tape entries appear in a scrollable list or table
- **Multi-label filtering** — readers filter by primary sector, secondary sector, article type, geography, publication date, and source
- **Paginated manifests** — per-sector JSON files, daily digest files, and a master index — rather than one monolithic file
- **Separate RSS feeds per sector** — each sector needs its own feed with sector-appropriate title, description, and taxonomy

---

## 7. Observability and Administration Gap

### 7.1 Current: Basic Health Report

The `health_report.py` module (lines 1-127) generates a single health output with:

- Source health summary from `source-health.json` (healthy count, quarantined count)
- 7-day pipeline stats (total runs, successful runs, total articles, estimated 30-day cost)
- Per-run detail (date, articles, cost, selections, decisions)
- Content governance issues
- Cost model (per-article costs by phase)

The report is rendered to `HEALTH.md` but is not currently being generated (the file does not exist at the workspace root). It provides an aggregate pipeline view with no per-sector breakdown, no per-story drill-down, and no rejection reason tracking.

### 7.2 What's Missing

| Capability | Current State | Required State |
|---|---|---|
| **Per-sector output dashboard** | Single aggregate article count | Articles per sector, per day, per week; candidates vs. published per sector |
| **Rejection reason codes** | Stories silently discarded in triage | Every rejected candidate logged with reason code: `no_sector_match`, `source_quality`, `recency`, `duplicate`, `evidence_insufficient`, `score_below_threshold` |
| **Source health by sector** | Per-feed health only (binary up/down) | Per-feed health with sector tags; feed failure rate by sector; source diversity metrics per sector |
| **Cost tracking per sector** | Per-run total cost only | API cost per sector, per article type, per model tier; cost-per-published-article by sector |
| **Story-level drill-down** | None | Per-story audit trail: which feeds produced it, how it scored in each dimension, which model scored it, why it was published or rejected |
| **Admin interface** | `insights-admin.html` exists but is a static page | Admin ability to: adjust sector weights, promote/reject individual stories, merge story clusters, override model scores, add editorial notes |
| **Alerting** | None beyond health report | Dead feed alerting, zero-article-day alerting, cost anomaly alerting, model failure alerting |
| **SLA tracking** | None | Pipeline completion time, time-to-publish per article, model latency, API error rate |

### 7.3 The Source Health Ledger's Blind Spot

The `SourceHealthLedger` class at `source_health.py:17-120` tracks per-feed operational health but has no concept of sector coverage. A feed can be marked "healthy" (returning stories) while providing zero stories for the sector it's supposed to cover — because the ledger doesn't know which sectors each feed serves. A Data Center feed that only returns enterprise IT stories about server hardware, with no data center real estate or power content, would appear healthy while providing zero sector-relevant stories.

---

## 8. Scale and Cost Gap

### 8.1 Current Economics

The pipeline currently operates at approximately $0.07 per published article, generating 0-5 articles per day. At the mandate's 210 articles/day target, the cost model transforms:

**Current (3 articles/day):**
- Phase 2 (triage): ~1,800 stories pass through classification → ~14 survivors
- Phase 3 (scoring): ~14 candidates scored by LLM
- Phase 5 (writing): ~3 full articles generated by LLM
- Daily cost: ~$0.21

**Mandate (210 articles/day):**
- Phase 2 (triage): ~5,000-8,000 stories ingested (expanded feed inventory) → ~2,000 candidates across all sectors
- Phase 3 (scoring): ~2,000 candidates scored by LLM
- Phase 5 (writing): ~210 full articles generated per day
- Estimated daily cost at current DeepSeek pricing: ~$15-25/day

The dominant cost multiplier is the LLM classification pass on ~2,000 candidates per day. If every candidate passes through the same DeepSeek model used for final article generation, the candidate scoring phase alone could exceed the current per-article cost by 100×.

### 8.2 Tiered Model Strategy Required

The mandate requires a tiered model deployment:

| Pipeline Phase | Model Strategy | Rationale |
|---|---|---|
| **Sector classification** | Cheap model (e.g., DeepSeek-V3-Lite, GPT-4o-mini) | Binary/multi-label classification on title + summary only. Does not require reasoning. |
| **Deterministic scoring** | No model (regex + heuristic) | Sector-specific deterministic scoring using extracted entities, amounts, topics. Runs in milliseconds per candidate. |
| **Candidate ranking per sector** | Mid-tier model (DeepSeek-V3) | Scores the top ~100 candidates per sector on sector-specific dimensions. Requires reasoning and domain knowledge. |
| **Full article generation** | Premium model (DeepSeek-V4-Pro / Claude 4) | Only for articles that clear the writing threshold. Writing quality is the product — do not compromise on prose quality. |
| **SEO/social metadata** | Cheap model or deterministic | Tags, slugs, excerpts, LinkedIn hooks — lightweight generation tasks. |

### 8.3 The 6-Hour GitHub Actions Window

The current pipeline runs in a 6-hour GitHub Actions timeout window (`timeout-minutes: 360`). At 210 articles/day with parallelized phases, this window is adequate:

- **Phase 1 (ingestion):** 5-8 minutes (parallel RSS fetch, 100 worker threads)
- **Phase 2 (classification):** 2-4 minutes (regex + cheap LLM on 2,000 candidates)
- **Phase 3 (scoring):** 8-12 minutes (mid-tier LLM on ~700 sector candidates, batched)
- **Phase 4 (writing):** 60-90 minutes (210 articles × 15-25 seconds each, 8-10 concurrent LLM calls)
- **Phase 5 (publishing):** 5-10 minutes (template rendering, manifest generation, git operations)
- **Phase 6 (LinkedIn/social):** 5-15 minutes (optional, can run as separate workflow)

Total: ~90-140 minutes per run, well within the 360-minute window.

### 8.4 Cost-Efficiency Through Candidate Filtering

The key cost lever is the candidate filtering ratio: 2,000 ingested → ~700 sector-classified → ~400 deterministic-scored → ~250 mid-tier-model-scored → 210 published. Each filtering stage should reduce the candidate pool by 30-50% using progressively more expensive methods. The most expensive model (article writer) is applied only after 4 preceding filtering stages.

---

## 9. Data Model Gap

### 9.1 Current: Ad-Hoc Dictionary Structures

The system passes story data through each pipeline phase as Python dictionaries with no enforced schema. Fields are added, modified, and sometimes dropped across phases:

**Phase 1 (gather):** `{"title": str, "summary": str, "url": str, "source": str, "published": str}`

**Phase 2 (normalize):** Adds `topics` (list of strings), `entities` (dict with keys like `companies`, `amounts`, `markets`, `asset_classes`, `policy_triggers`, etc.), `attention_features` (dict with bool flags like `has_big_number`, `has_known_institution`, `has_material_transaction`, etc.), and source metadata like `source_tier` and `source_lane`.

**Phase 3 (score):** Adds `must_read_score`, score breakdown dicts, `decision`, `reason`, and `franchise` assignment.

**Phase 4 (enrich):** Adds `research_dossier` (nested dict), `room_plan` (LLM output), `facts` (extracted claims).

**Phase 5 (write):** Returns a flat dict with `title`, `slug`, `body_html`, `tags`, `linkedin_hook`, `narrative_ledger`, `excellence_ledger` — a different shape than any upstream phase.

**Phase 6 (publish):** Writes `insights.json` entries with a subset of the writing phase fields, discarding the editorial ledgers and research materials.

There is no single data class, TypedDict, or Pydantic model that defines the canonical shape of a story/article across all pipeline phases. Field access is by string key with `.get()` fallbacks throughout — a pattern that silently tolerates missing fields rather than surfacing schema violations.

### 9.2 What the Mandate Requires

A structured canonical news item model with typed fields:

```python
@dataclass
class NewsItem:
    # Identity
    id: str  # content-hash derived UUID
    title: str
    summary: str
    url: str
    published_at: datetime
    
    # Source
    source_name: str
    source_tier: int
    source_domain: str  # e.g., "cre", "banking", "energy"
    source_feed: str  # The specific RSS feed that yielded this item
    
    # Classification
    primary_sector: Sector  # enum: CRE, PRIVATE_EQUITY, DATA_CENTERS, ENERGY, BANKING_CREDIT, FED_MACRO, LOCAL_GOVERNMENT
    secondary_sectors: list[Sector]
    topics: list[str]
    asset_classes: list[str]
    
    # Entities
    companies: list[str]
    amounts: list[Amount]  # typed amount with value, currency, unit
    markets: list[str]
    geographies: list[GeoRef]  # typed geo with MSA, state, country
    regulatory_bodies: list[str]
    
    # Attention signals
    has_material_transaction: bool
    has_big_number: bool
    has_known_institution: bool
    has_policy_impact: bool
    
    # Scoring (per sector — a story can have multiple sector scores)
    sector_scores: dict[Sector, SectorScore]
    
    # Pipeline state
    triage_decision: TriageDecision  # enum: ADMIT, REJECT, NEEDS_REVIEW
    triage_reason: str
    processing_phase: Phase  # enum: GATHERED, NORMALIZED, SCORED, ENRICHED, WRITTEN, PUBLISHED
    
    # Publishing
    article_tier: ArticleTier  # enum: FLAGSHIP, BRIEF, DEAL_TAPE, DATA_POINT
    slug: str | None
    body_html: str | None
    published_at: datetime | None
```

This single canonical model would be used across all pipeline phases, with each phase adding to or validating specific fields rather than constructing new ad-hoc dicts.

---

## 10. Source Health and Resilience Gap

### 10.1 Current: Passive, Binary Health Tracking

The `SourceHealthLedger` at `source_health.py:17-120` tracks each feed on a simple circuit-breaker model:

- **Consecutive failures:** If a feed fails 3 consecutive times, it's "quarantined" for 24 hours (cooldown period)
- **Empty feeds:** Feeds that return zero stories are marked "empty" (diagnostic only, never blocks future reads)
- **Transient outages:** Run-level connectivity issues are noted but not counted against individual sources

On the most recent pipeline execution, approximately 48 of 103 feeds returned empty — a 46% failure rate that the system records but does not act on. The `record_empty()` method at line 55 explicitly states that empty feeds "must not quarantine the source for the next daily run." This is a deliberate design choice that prioritizes availability over reliability, assuming that empty feeds are transient publisher behavior rather than permanently dead endpoints.

### 10.2 What's Missing

| Capability | Current State | Impact |
|---|---|---|
| **Dead feed detection** | None — empty feeds are retried indefinitely | The system continues to hit dead RSS endpoints every day, consuming bandwidth and worker threads with guaranteed zero yield |
| **Feed replacement / discovery** | None — feeds are manually curated in `news_sources.py` | When a publication changes its RSS URL or discontinues its feed, the source disappears from coverage with no automated recovery |
| **Sector coverage monitoring** | None — no concept of sectors in the health ledger | Even if a feed is "healthy," it could be returning zero stories for the sector it's supposed to cover |
| **Feed freshness scoring** | Not tracked | A feed that returns stories but only from 3+ days ago is technically "healthy" but useless for daily editorial |
| **Source diversity metrics** | Not tracked | The system doesn't know if 80% of articles are coming from 3 feeds |
| **Alerting** | None beyond the health report file | Operators must proactively read the health report rather than being notified of coverage gaps or dead sources |
| **Graceful degradation** | Circuit breaker only — binary up/down | A feed returning 2 stories instead of 20 is "healthy" and receives no attention. There is no concept of degraded performance. |
| **Multi-source corroboration tracking** | In `editorial_intelligence.py` for scoring but not in health monitoring | The system knows when sources corroborate but doesn't use this to assess source reliability or coverage completeness |

### 10.3 Feed Inventory Staleness

The current RSS feed list has not been audited for freshness in weeks. Business journal feeds (lines 88-100) from Bizjournals.com domains are known to have unstable RSS endpoints. Several feeds in the list use HTTP URLs that should be HTTPS. The NewsAPI queries (lines 213-230) reference "2026" in query strings — a hardcoded year that will need updating within months.

The mandate's 7-sector coverage requires approximately 140-195 feeds (up from ~103), increasing the surface area for feed failures proportionally. Without automated feed health management, the operational burden of maintaining feed currency would scale linearly with feed count — an unsustainable manual process.

---

## Summary: Cumulative Gap Severity

| Gap Area | Current State | Severity | Mandate Impact |
|---|---|---|---|
| Source Coverage | 1 of 7 sectors adequately covered | **Critical** | Cannot produce articles for 6 sectors without new feeds |
| Ingestion/Triage | CRE keyword gate kills non-CRE stories | **Critical** | 99.2% of incoming stories from non-CRE sectors would be discarded |
| Classification | Binary CRE-relevant or not; no multi-label | **Critical** | Cannot route stories to correct sectors; cross-sector stories are impossible |
| Scoring | Single universal framework; CRE-weighted | **High** | Non-CRE stories scored against irrelevant criteria; data center MW would score below small CRE deals |
| Content Generation | CRE-centric prompts, voice modes, and formats | **High** | Non-CRE stories would generate misapplied CRE narrative frames |
| Publishing/Display | Single page, flat manifest, one file per article | **Critical** | Unsustainable at 210 articles/day (76K HTML files/year); no sector navigation |
| Observability | Basic health report only; no sector tracking | **High** | No visibility into 7-sector pipeline performance; cannot debug sector-specific failures |
| Scale/Cost | ~$0.07/article at 3/day | **Medium** | Need tiered model strategy; cost manageable with proper candidate filtering |
| Data Model | Ad-hoc dicts; no canonical schema | **High** | Field inconsistency causes silent failures; adds friction to every pipeline modification |
| Source Health | Passive tracking; 46% empty feed rate; no replacement | **High** | Will compound with 2× larger feed inventory; manual maintenance doesn't scale |

**Priority Order for Remediation:**

1. Triage/Ingestion overhaul (blocks everything downstream)
2. Source coverage expansion (enables content for 6 uncovered sectors)
3. Classification system (enables correct routing)
4. Data model standardization (foundation for all other changes)
5. Scoring system (ensures editorial quality per sector)
6. Content generation (ensures appropriate voice and format per sector)
7. Publishing infrastructure (supports 210 articles/day)
8. Observability (enables ongoing operations)
9. Source health management (prevents degradation over time)
