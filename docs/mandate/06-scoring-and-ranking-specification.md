# Scoring and Ranking Specification: Light Tower Group 7-Sector Intelligence Engine

**Document:** 06-Scoring-and-Ranking-Specification
**Date:** July 30, 2026
**Status:** Design Specification — Authoritative Scoring Framework

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [The Classification Layer (Pre-Scoring)](#2-the-classification-layer-pre-scoring)
3. [The 10 Scoring Dimensions](#3-the-10-scoring-dimensions)
4. [Sector-Specific Weight Profiles](#4-sector-specific-weight-profiles)
5. [Composite Score Calculation](#5-composite-score-calculation)
6. [Tier Assignment](#6-tier-assignment)
7. [Within-Sector Ranking and Selection](#7-within-sector-ranking-and-selection)
8. [Selection Quotas and Volume Management](#8-selection-quotas-and-volume-management)
9. [Diversity Controls](#9-diversity-controls)
10. [Cross-Sector Deduplication](#10-cross-sector-deduplication)
11. [Cross-Sector Story Promotion](#11-cross-sector-story-promotion)
12. [Rejection Reason Codes and Audit Trail](#12-rejection-reason-codes-and-audit-trail)
13. [Configurability and Runtime Overrides](#13-configurability-and-runtime-overrides)
14. [Deterministic vs. LLM-Assisted Scoring](#14-deterministic-vs-llm-assisted-scoring)
15. [Scoring Edge Cases and Calibration Rules](#15-scoring-edge-cases-and-calibration-rules)
16. [Implementation Checklist and Testing](#16-implementation-checklist-and-testing)

---

## 1. Philosophy

### 1.1 The Core Principle

The scoring system must understand stories — not just check whether their title contains keywords. Every ingested story is classified by sector and event type, then scored on ten dimensions that reflect its actual significance within that sector's context. The system is capable of recognizing that a $200M data center deal with 300MW of power procurement is more significant than a $10M multifamily refinancing in a tertiary market, even though the latter matches CRE keywords and the former does not. Sector context determines significance, not universal keyword lists.

### 1.2 Design Principles

1. **Sector Context Determines Everything.** The same number — $100M — means something different in CRE (a significant single-asset deal), PE (a mid-market buyout fund), energy (a modest solar portfolio), and banking (one branch of a regional bank). Dimensions are scored relative to sector norms, not absolute thresholds.

2. **Deterministic Where Possible, LLM-Assisted Where Necessary.** Dimensions that can be scored from structured data (financial magnitude from extracted dollar amounts, source quality from the source tier map, timeliness from publication timestamp, entity significance from the watchlist) are scored deterministically. Dimensions requiring context, judgment, or forward-looking assessment (market impact, strategic relevance, editorial potential) may use an LLM call — but with the LLM's reasoning captured in the audit trail.

3. **Cross-Sector Comparability Is Optional, Not Required.** The system does not need to compare a CRE story to a data center story — they compete within their own sectors for selection slots. Cross-sector comparison only occurs during deduplication (when the same story is classified under multiple sectors) and during cross-sector promotion.

4. **Transparency Is Non-Negotiable.** Every dimensional score, every weight applied, every selection decision, and every rejection must be logged with an audit trail that includes the reasoning, the model used (if any), the timestamp, and the input data.

5. **Configurable Without Code Changes.** All weights, thresholds, tier boundaries, sector profiles, and selection quotas live in `config/scoring_profiles.json`. The scoring spec is the source of truth — implementation must match it exactly, and any deviation is a bug.

---

## 2. The Classification Layer (Pre-Scoring)

Before scoring, every ingested story passes through a multi-label classification step. Classification determines which sector profile(s) are applied during scoring.

### 2a. Sector Classification

**Output:** `primary_sector` (single enum value) + `secondary_sectors` (list of 0-6 enum values)

**Enum Values:**
- `COMMERCIAL_REAL_ESTATE` (CRE)
- `PRIVATE_EQUITY` (PE)
- `DATA_CENTERS` (DC)
- `ENERGY` (ENG)
- `BANKING_CREDIT` (BNK)
- `FEDERAL_MACRO` (MAC)
- `LOCAL_GOVERNMENT` (LOC)

**Classification Methods (Applied in Order):**

1. **Source-Based Prior (Deterministic).** Every feed in the source registry has a sector domain tag. A story from `pehub.com` has a prior probability of `PRIVATE_EQUITY: 0.85`. A story from `datacenterdynamics.com` has a prior of `DATA_CENTERS: 0.90`. This prior is the starting point but is not dispositive — a PE Hub story about a real estate fund gets CRE as primary, PE as secondary.

   ```python
   SOURCE_SECTOR_BIAS = {
       "pehub.com": {"PRIVATE_EQUITY": 0.85, "COMMERCIAL_REAL_ESTATE": 0.10, "BANKING_CREDIT": 0.05},
       "datacenterdynamics.com": {"DATA_CENTERS": 0.90, "ENERGY": 0.05, "COMMERCIAL_REAL_ESTATE": 0.05},
       "utilitydive.com": {"ENERGY": 0.80, "LOCAL_GOVERNMENT": 0.10, "BANKING_CREDIT": 0.05, "FEDERAL_MACRO": 0.05},
       "americanbanker.com": {"BANKING_CREDIT": 0.80, "FEDERAL_MACRO": 0.10, "COMMERCIAL_REAL_ESTATE": 0.10},
       # ... full map in config/scoring_profiles.json
   }
   ```

2. **Expanded Topic Regex Patterns per Sector (Deterministic).** Each sector has a set of regex patterns that indicate sector relevance. These replace the current `CRE_KEYWORDS` / `EXCLUDE_KEYWORDS` filter — they are used for probabilistic classification, not binary elimination.

   **CRE Topic Patterns (partial list — full list in config):**
   ```
   commercial real estate, multifamily, apartment building, office building, retail space,
   industrial warehouse, mixed-use, condo tower, rental building, affordable housing,
   mortgage refinanc, bridge loan, construction loan, CMBS, agency debt,
   acquisition, disposition, sale-leaseback, ground lease, joint venture, recapitalization,
   cap rate, NOI, debt service, DSCR, LTV, interest rate, SOFR,
   REIT, landlord, developer, sponsor, lender, borrower, investment sales,
   rent stabilization, housing court, zoning, building permit, certificate of occupancy,
   opportunity zone, upzoning, rezoning, air rights, tax abatement,
   421a, 421g, j51, ULURP, landmark preservation,
   brooklyn, manhattan, queens, bronx, fidi, midtown, hudson yards,
   long island city, williamsburg, bushwick, dumbo, harlem
   ```

   **PE Topic Patterns:**
   ```
   private equity, buyout, growth equity, venture capital, take-private,
   fundrais(e|ing), fund clos(e|ing), limited partner, general partner, LP commitment,
   secondaries, continuation vehicle, GP-led, co-investment,
   leveraged buyout, management buyout, carve-out, add-on acquisition,
   private capital, institutional investor, pension fund, endowment, sovereign wealth fund,
   dry powder, capital deployment, fund vintage, IRR, MOIC, DPI, TVPI,
   private credit, direct lending, mezzanine debt, unitranche,
   portco|portfolio company, platform investment
   ```

   **Data Center Topic Patterns:**
   ```
   data center, datacenter, colocation, hyperscale, cloud region, availability zone,
   megawatt|MW capacity, critical load, power usage effectiveness|PUE,
   fiber network, cross-connect, interconnection, peering,
   server rack, raised floor, cooling system, liquid cooling,
   cage, cabinet, wholesale data center, powered shell,
   edge data center, modular data center, micro data center,
   dark fiber, lit building, carrier hotel, meet-me room,
   Tier III, Tier IV, Uptime Institute, LEED data center
   ```

   **Energy Topic Patterns:**
   ```
   power plant, generating station, solar farm, wind farm, battery storage,
   megawatt|MW|gigawatt|GW, kilowatt-hour|MWh|GWh, capacity factor, levelized cost|LCOE,
   power purchase agreement|PPA, renewable portfolio standard|RPS, renewable energy credit|REC,
   transmission line, substation, interconnection, grid, RTO, ISO,
   natural gas, LNG, crude oil, refinery, pipeline, midstream, upstream,
   nuclear reactor, nuclear plant, NRC, FERC, PURPA,
   utility commission, rate case, rate base, decoupling, net metering,
   carbon capture, hydrogen, clean energy standard, energy transition,
   distributed generation, microgrid, demand response, virtual power plant,
   PJM, ERCOT, CAISO, MISO, NYISO, ISO-NE, SPP
   ```

   **Banking/Credit Topic Patterns:**
   ```
   bank, banking, credit union, thrift, savings bank, community bank,
   loan loss, non-performing loan|NPL, charge-off, allowance for credit losses|CECL,
   tier 1 capital, CET1, risk-weighted asset, leverage ratio, stress test|CCAR|DFAST,
   deposit, deposit beta, deposit flight, brokered deposit,
   net interest margin|NIM, loan-to-deposit ratio, yield curve,
   Basel III, capital buffer, GSIB surcharge, TLAC, resolution plan,
   mortgage lending, commercial lending, construction lending, C&I loan,
   credit risk, counterparty risk, concentration risk, loan portfolio,
   FDIC insurance, bank failure, receivership, bridge bank
   ```

   **Federal Reserve/Macro Topic Patterns:**
   ```
   federal reserve, Fed chair, FOMC, federal funds rate, interest rate decision,
   monetary policy, quantitative easing, balance sheet runoff, open market operations,
   inflation, CPI, PCE, core inflation, deflation, disinflation,
   GDP growth, recession, economic expansion, leading indicators, consumer confidence,
   unemployment, nonfarm payroll, JOLTS, labor force participation, wage growth,
   Treasury yield, yield curve, 2-year, 10-year, 30-year, spread,
   fiscal policy, deficit, debt ceiling, budget, appropriation,
   CBO score, GAO report, BLS release, BEA estimate, Census survey
   ```

   **Local Government Topic Patterns:**
   ```
   city council, county commission, board of supervisors, mayor, planning commission,
   zoning, rezoning, variance, conditional use permit, special exception,
   comprehensive plan, area plan, neighborhood plan, master plan,
   building permit, certificate of occupancy, site plan, subdivision plat,
   tax abatement, TIF, PILOT, tax increment financing, property tax,
   affordable housing, inclusionary zoning, mandatory inclusionary housing|MIH,
   community benefits agreement, environmental impact statement|EIS, CEQA, SEQRA,
   procurement, RFP, request for proposals, public-private partnership|P3,
   municipal bond, GO bond, revenue bond, bond rating,
   annexation, incorporation, eminent domain, condemnation,
   housing element, RHNA, fair share, growth management
   ```

3. **Entity Recognition Against Company Watchlists (Deterministic).** If a story mentions entities from Layer 6 watchlists, those entity-to-sector mappings provide sector classification signals. A story mentioning "Equinix" has a `DATA_CENTERS: 0.70` signal. A story mentioning both "Blackstone" and "QTS" has strong dual classification signals for PE and Data Centers.

4. **Optional LLM Classification Call (For Ambiguous Cases).** If deterministic methods produce low confidence (< 0.60 for the highest-scoring sector) or conflicting signals (two sectors both above 0.40), dispatch a cheap LLM call (e.g., DeepSeek-V3-Lite or gpt-4o-mini) with the story title + summary and ask for sector classification. The LLM returns `{"primary": "DATA_CENTERS", "secondary": ["PRIVATE_EQUITY", "ENERGY"], "confidence": 0.85}`.

**Classification Confidence Score:** Each classification produces a confidence score (0.0-1.0). Stories with confidence below the `MIN_CLASSIFICATION_CONFIDENCE` threshold (default: 0.50) are admitted to the scoring phase with a `classification_confidence` metadata flag but are more likely to be filtered at the tier assignment stage.

**Rejection Reason Codes from Classification:**
- `CLASS_INSUFFICIENT_TEXT` — Title + summary too short (< 20 chars) to classify
- `CLASS_NO_SECTOR_MATCH` — No sector pattern matched (confidence < 0.20 for all sectors)
- `CLASS_AMBIGUOUS` — Multiple sectors matched but LLM call failed or was not configured
- `CLASS_EXCLUDED` — Matched exclusion patterns (single-family home, celebrity gossip, etc.)

### 2b. Event Type Classification

Each story is mapped to one of the following standard event types. Event type influences which dimensions are most relevant and which editorial formats are applicable.

**Standardized Event Types:**

| Code | Event Type | Description | Typical Sectors |
|------|-----------|-------------|-----------------|
| `ACQ` | Acquisition | Company or asset purchase | All |
| `DIS` | Disposition / Divestiture | Asset or division sale | CRE, PE, DC, ENG |
| `REFI` | Refinancing | Debt refinancing or restructuring | CRE, PE, BNK |
| `DEV_APPR` | Development Approval | Zoning, permit, or planning approval | CRE, DC, ENG, LOC |
| `CONSTR_START` | Construction Start | Groundbreaking or construction commencement | CRE, DC, ENG, LOC |
| `FUND_CLOSE` | Fund Closing | PE/VC/credit/real estate fund final close | PE, CRE |
| `REG_ACTION` | Regulatory Action | Rulemaking, enforcement, guidance, or order | BNK, MAC, ENG, LOC |
| `POLICY_CHANGE` | Policy Change | Legislation, executive action, regulatory change | MAC, LOC, ENG, BNK |
| `EARNINGS` | Earnings Report | Quarterly/annual financial results | All |
| `EXEC_CHANGE` | Executive Change | CEO, CFO, key personnel moves | All |
| `MKT_REPORT` | Market Report | Industry data, research, survey release | All |
| `LEASE` | Lease Transaction | Significant lease signing or renewal | CRE, DC |
| `DEBT_ISS` | Debt Issuance | Bond issuance, loan syndication, note placement | BNK, CRE, PE, MAC |
| `DISTRESS` | Distress Event | Default, foreclosure, bankruptcy, workout | CRE, PE, BNK |
| `RESTRUCTURE` | Restructuring | Corporate or debt restructuring | PE, BNK |
| `JV` | Joint Venture | Partnership formation or structuring | CRE, DC, ENG, PE |
| `IPO` | Initial Public Offering | Company going public | PE, DC, ENG, BNK |
| `DELISTING` | Delisting / Take-Private | Going private transaction | PE |
| `LEGISLATION` | Legislation | Bill introduction, committee action, passage | LOC, MAC |
| `ZONING` | Zoning Decision | Rezoning, variance, land-use decision | CRE, LOC |
| `TAX_INC` | Tax Incentive | Tax abatement, TIF, PILOT approval | CRE, DC, LOC |
| `ENV_PERMIT` | Environmental Permitting | EIS, environmental review, NEPA | CRE, DC, ENG, LOC |
| `UTIL_APPR` | Utility Approval | Rate case decision, interconnection approval | ENG, DC |
| `PWR_AGMT` | Power Agreement | PPA signing, energy procurement contract | DC, ENG |
| `INTERCONNECT` | Interconnection Filing | Generator or load interconnection request | ENG, DC |

**Implementation:** Deterministic regex matching against normalized topic tags. If no match, default to `OTHER` which receives no event-type-specific weighting.

### 2c. Entity Extraction

Extract from title + summary using regex + watchlist lookup:

1. **Buyers / Acquirers** — entities followed by "acquired", "bought", "purchased", "closed on"
2. **Sellers / Divesting Parties** — entities followed by "sold", "divested", "disposed of"
3. **Lenders / Financiers** — entities followed by "financed", "provided debt", "arranged financing"
4. **Developers** — entities followed by "developing", "building", "constructing"
5. **Government Bodies** — match against Layer 1 and LOC source names
6. **Advisors / Brokers** — entities followed by "advised", "brokered", "arranged"
7. **Properties / Projects** — named developments, addresses, facility names
8. **Funds** — named investment vehicles (e.g., "Blackstone Real Estate Partners X")

**Scoring Impact:** Whether an entity is on the Tier-1 watchlist (Critical priority) determines the `party_significance` dimension score. See Section 3, D2.

### 2d. Geography Extraction

Extract city, state, MSA, and country from story text. Match against the priority markets list:

**Priority Markets (Score Bonus = +1 to +2 on Market Impact dimension):**
- Tier A: New York City, San Francisco Bay Area, Los Angeles, Chicago, Washington DC
- Tier B: Miami, Dallas-Fort Worth, Houston, Atlanta, Boston, Phoenix, Seattle, Denver, Northern Virginia
- Tier C: Austin, Nashville, Charlotte, Raleigh-Durham, Portland, San Diego, Las Vegas, Minneapolis

**Implementation:** Deterministic matching against a gazetteer of MSA names, city names, county names, and neighborhood names. Stories matching Tier A markets receive an automatic +1 to the Market Impact dimension. Tier B matches add +1 but cannot push the score above 9 unless independently justified.

### 2e. Financial Extraction

Extract structured financial values from text using regex patterns:

```python
FINANCIAL_PATTERNS = {
    "dollar_amount": r"\$(\d+(?:\.\d+)?)\s*(million|billion|trillion|M|B|T|mn|bn|tn)",
    "unit_count": r"(\d+)[- ](unit|apartment|home|house|bed|key|door)",
    "square_footage": r"(\d+(?:,\d+)?)\s*(square feet|sq ft|SF|sq\.\s*ft\.|sf)",
    "acreage": r"(\d+(?:\.\d+)?)\s*(acre|ac)",
    "megawatts": r"(\d+(?:\.\d+)?)\s*(MW|megawatt|gigawatt|GW)",
    "fund_size": r"\$(\d+(?:\.\d+)?)\s*(million|billion)\s*(fund|vehicle|raise|close)",
    "interest_rate": r"(\d+(?:\.\d+)?)\s*%\s*(interest|rate|coupon|coupon rate)",
    "cap_rate": r"(\d+(?:\.\d+)?)\s*%\s*(cap rate|capitalization rate|caps)",
}
```

All extracted amounts are normalized to USD millions for comparability. Square footage, megawatts, and unit counts are normalized to their base unit.

---

## 3. The 10 Scoring Dimensions

Each dimension is scored 1-10 (integer). A score of 1 means the story has minimal presence on this dimension. A score of 10 means exceptional presence on this dimension relative to its sector's norms.

### D1: Financial Magnitude (1-10)

**What it measures:** The monetary scale of the event relative to sector norms. A $500M deal is significant in any sector. A $20M deal might be significant in a small market or niche sector. A $2B deal scores 10 in most sectors.

**Scoring Logic (Deterministic Where Possible):**

| Extracted Value | CRE | PE | Data Centers | Energy | Banking | Fed/Macro |
|----------------|-----|-----|-------------|--------|---------|-----------|
| < $1M | 1 | 1 | 1 | 1 | 1 | N/A (use policy impact instead) |
| $1M - $5M | 2-3 | 2 | 2 | 2 | 2 | N/A |
| $5M - $25M | 3-4 | 3 | 2-3 | 2-3 | 3 | N/A |
| $25M - $100M | 5-6 | 4-5 | 3-4 | 3-4 | 4-5 | N/A |
| $100M - $500M | 7-8 | 6-7 | 5-7 | 4-6 | 6-7 | N/A |
| $500M - $1B | 8-9 | 7-8 | 7-8 | 6-7 | 7-8 | N/A |
| $1B - $5B | 9-10 | 8-9 | 8-9 | 7-8 | 8-9 | N/A |
| > $5B | 10 | 9-10 | 9-10 | 8-9 | 9-10 | N/A |

For non-dollar financial extractions: 100 units = 1-2, 500 units = 3-4, 2,000 units = 5-6, 10,000 units = 7-8, 50,000+ units = 9-10.

**Edge Cases:**
- Story with no extractable financial value: default score = 3 (may still be significant for other reasons)
- Story about a 300MW data center with no dollar figure: score as 6-7 based on implied capital (300MW × ~$8M/MW build cost ≈ $2.4B implied project value)
- Macro/Fed stories: Financial Magnitude defaults to 3 unless a specific dollar figure is present (e.g., "$500B balance sheet reduction")

### D2: Party Significance (1-10)

**What it measures:** Are the entities involved major players in the sector? How significant is their participation or action?

**Scoring Logic:**

| Entity Tier | Score Range | Description |
|-------------|-------------|-------------|
| Tier 1 / Critical watchlist | 9-10 | Blackstone, Brookfield, Apollo, JPMorgan, Fed, AWS, NextEra, Equinix, etc. |
| Tier 2 / High watchlist | 7-8 | Major but not dominant players in the sector |
| Tier 3 / Medium watchlist | 5-6 | Recognizable institution within the sector |
| Known but not on watchlist | 3-4 | Established firm but not spotlight entity |
| Unknown entity | 1-2 | Entity with no sector recognition |

**Tiebreaking:** If multiple entities appear, use the highest-tier entity to set the base score, then add +1 if multiple Tier 1 entities appear.

**Edge Cases:**
- Federal Reserve action story with no other named entities: score = 10 (Fed itself is Tier 1)
- Local developer with only local recognition: score = 3
- Anonymous sources or "a group of investors" with no named entities: score = 1

### D3: Market Impact (1-10)

**What it measures:** Does this event change pricing, expectations, or behavior in its market? Is this a market-moving event or a routine transaction?

**Scoring Logic:**

| Impact Level | Score | Examples |
|-------------|-------|----------|
| Systemic / market-wide impact | 10 | Fed rate hike, FERC capacity market redesign, regulatory rule that changes an entire industry |
| Reshapes subsector pricing | 8-9 | Distress sale that resets cap rate expectations, major PPA that sets new benchmark price |
| Material deal with market signaling | 6-7 | Record-setting price per unit, first-of-kind deal structure, largest deal in a submarket |
| Notable but routine transaction | 4-5 | Large deal without unusual structure, quarterly earnings in-line with expectations |
| Routine event, no market signal | 2-3 | Standard lease renewal, routine refinancing, minor regulatory filing |
| Trivial / irrelevant | 1 | Press release with no market substance |

**Deterministic Signals:**
- `has_record_language` flag (words like "record", "largest", "first", "unprecedented", "historic"): +2 to base
- `has_distress` flag (foreclosure, default, bankruptcy): +2 to base
- `has_policy_change` flag (legislation, regulation, rule change): +2 to base

**LLM-Assisted Assessment:** When deterministic signals are insufficient, prompt an LLM: "Given the story [title + summary], rate the market impact on a 1-10 scale in the [sector] sector. Explain your reasoning."

### D4: Strategic Relevance (1-10)

**What it measures:** How relevant is this story to Light Tower's core audience — CRE sponsors, lenders, PE investors, developers, family office principals? This dimension is weighted differently per sector based on audience persona match.

**Scoring Logic:**

| Relevance Level | Score | Description |
|----------------|-------|-------------|
| Directly addresses core audience decisions | 9-10 | Story about capital flows, investment strategy, lending conditions, development economics |
| Relevant to audience investment/operating context | 7-8 | Market data report, policy change affecting investments, sector trend with capital implications |
| Provides useful context for decision-makers | 5-6 | Industry trend piece, competitor analysis, regulatory development with indirect impact |
| Adjacent but not directly actionable | 3-4 | General industry news, consumer-facing story, technical detail without capital angle |
| Peripheral interest only | 1-2 | Story with only passing relevance to Light Tower audience personas |

**Audience Personas (Configurable):**
- Primary: CRE sponsor, institutional lender, PE investor, developer
- Secondary: REIT analyst, private credit fund, family office, banker, broker
- Tertiary: energy trader, data center operator, municipal official, policy analyst

**Implementation:** LLM-assisted scoring with audience persona alignment check.

### D5: Policy/Regulatory Impact (1-10)

**What it measures:** Does this story involve a policy or regulatory action that changes what is legally or financially possible? What is the scope and consequence of the policy change?

**Scoring Logic:**

| Impact Level | Score | Examples |
|-------------|-------|----------|
| Federal rule/law with national scope and major consequence | 10 | Federal Reserve interest rate decision, Basel III endgame, major tax legislation |
| Federal regulatory action with sector-wide impact | 8-9 | SEC rulemaking on private funds, FERC transmission planning order, Treasury guidance |
| State/local action with major market impact | 7-8 | State housing legislation, major city zoning overhaul, PUC rate case decision |
| Meaningful regulatory development affecting subsector | 5-6 | Agency guidance, proposed rule, legislative committee action |
| Minor regulatory/administrative action | 3-4 | Routine regulatory filing, administrative update, technical correction |
| No policy/regulatory dimension | 1-2 | Pure market transaction, earnings report, personnel move with no regulatory angle |

**Deterministic Signals:**
- Source is a federal agency (Layer 1): +3 to base (scored from minimum 4)
- Source is a state/local government source: +2 to base
- Topic includes regulatory patterns: +2 to base
- Has `has_government_action` or `has_regulatory_trigger` flag: +2 to base

### D6: Novelty (1-10)

**What it measures:** Is this new information? First report of a major deal? Or is it recycled coverage of already-circulated news?

**Scoring Logic:**

| Novelty Level | Score | Description |
|--------------|-------|-------------|
| First report of significant deal/event | 10 | Exclusive or first-to-publish coverage |
| Early coverage with new details | 7-8 | Second source confirming deal + adds new facts |
| Coverage from new angle or with new analysis | 5-6 | Story adds analyst commentary or market context |
| Syndication / rewrite of earlier coverage | 3-4 | Third+ source covering same event, no new facts |
| Straight syndication, no new information | 1-2 | Press release reprint, wire service syndication |

**Implementation:** Scored against the event memory archive. If an event (clustered by URL, title similarity, extracted entities) already appears in the archive, novelty score decreases by 2 points per prior sighting (minimum 1).

**Deterministic Signals:**
- First time an entity + event type combination appears today: auto base of 7
- Within 1 hour of the earliest known report: +1 bonus
- Source tier 0 (primary/federal): auto minimum of 6 (even if not first, primary-source value)

### D7: Source Quality (1-10)

**What it measures:** The authority, reliability, and depth of the publishing source. Based on the source tier hierarchy defined in the source registry.

**Scoring Logic:**

| Source Tier | Score | Description | Examples |
|-------------|-------|-------------|----------|
| Tier 0 — Primary/Authoritative | 9-10 | Government filing, regulatory order, court document, official data release | SEC EDGAR filing, Federal Reserve announcement, FERC order, BLS data release |
| Tier 1 — Major Financial / Top Trade | 7-8 | Established financial publication, leading trade journal | WSJ, Bloomberg, Reuters, The Real Deal, PERE, DCD |
| Tier 2 — Established Trade / Regional | 5-6 | Recognized trade publication, regional business journal | GlobeSt, Connect CRE, BizJournals, Utility Dive |
| Tier 3 — Aggregator / General Interest | 3-4 | News aggregator, general-interest publication with sector coverage | Press release wire, consumer news site |
| Tier 4 — Unverified / Low Authority | 1-2 | Unknown blog, unverified aggregator, anonymous source | Spammy aggregator, content farm |

**Edge Cases:**
- Company press release: score = 3 (self-interested source)
- Multiple sources corroborating the same event: primary source score +1 per corroborating source (max 10)
- Federal agency primary source: auto minimum of 9

### D8: Timeliness (1-10)

**What it measures:** How recent is this story? Fresher information has higher editorial value.

**Scoring Logic:**

| Publication Age | Score |
|----------------|-------|
| < 1 hour | 10 |
| 1-3 hours | 9 |
| 3-6 hours | 8 |
| 6-12 hours | 7 |
| 12-24 hours (same day) | 6 |
| Yesterday | 5 |
| 2 days ago | 4 |
| 3 days ago | 3 |
| 4-5 days ago | 2 |
| > 5 days or unknown | 1 |

**Special Rules:**
- SEC filings: publication timestamp may be days after event date; score based on filing publication time, not underlying event date
- Weekend stories evaluated on Monday: score as if published Monday morning (same-day relative to next business day's editorial cycle)
- Data releases with known schedules (BLS Employment Situation, FOMC statement, etc.): auto score = 10 in the hour after release

### D9: Editorial Potential (1-10)

**What it measures:** Do we have enough source material to write a substantive article? Can we produce something worth reading?

Evidence levels from the research dossier:

| Evidence Level | Score | Description |
|---------------|-------|-------------|
| Deep (3+ sources, 2+ full text articles, corroborated facts) | 10 | Multiple independent sources with full article text, cross-verified claims, multiple data points |
| Strong (2+ sources, at least 1 full text, corroborated key facts) | 8-9 | At least two independent sources, one with full text, key facts verified |
| Adequate (2+ sources, partial text, plausible narrative) | 6-7 | Multiple sources but limited to titles/summaries; can write an adequate brief |
| Thin (1 source, limited text, single-source story) | 4-5 | One source only; can write a brief but risks single-source bias |
| Insufficient (1 source, summary-only, no factual depth) | 1-3 | Cannot write anything with editorial confidence |

**Deterministic Signals:**
- `evidence_depth` field from `build_research_dossier()` output
- Number of corroborating sources from `cluster_events()`
- Whether full-text fetching succeeded for at least one source
- Word count of available text

### D10: Cross-Sector Impact (1-10)

**What it measures:** How many sectors does this story touch? A story classified under multiple sectors has higher cross-sector importance than a single-sector story.

**Scoring Logic:**

| Sectors Affected | Score | Examples |
|-----------------|-------|----------|
| 5+ sectors | 10 | Federal Reserve rate decision (affects CRE, PE, DC, ENG, BNK, MAC, LOC through municipal rates) |
| 4 sectors | 8-9 | Major tax legislation, infrastructure bill spending |
| 3 sectors | 6-7 | PE acquisition of a data center platform with power procurement (DC + PE + ENG) |
| 2 sectors | 4-5 | Bank CRE loan portfolio sale (BNK + CRE) |
| 1 sector | 2-3 | Pure single-sector story |
| Niche subsector within one sector | 1 | Narrow sub-specialty news with no spillover |

**Implementation:** Determined from the multi-label sector classification output. The count of secondary sectors plus the primary sector yields the raw count, which maps to the score table above.

---

## 4. Sector-Specific Weight Profiles

Each sector applies different multipliers to each of the 10 dimensions. These weights reflect what matters most in editorial assessment within each sector. For example, Policy Impact matters enormously in the Energy sector (where FERC orders and PUC rate cases drive investment) but less so in CRE (where market transactions are the primary editorial driver).

The weight profiles below are stored in `config/scoring_profiles.json` and are editable without code changes.

### 4a. CRE Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×1.5** | Deal size is the primary signal in CRE — larger deals create more market impact, attract more attention, and set comparables |
| D2: Party Significance | **×1.2** | Brand-name sponsors and lenders matter; a Blackstone acquisition is inherently newsier than a local buyer |
| D3: Market Impact | **×1.2** | Pricing signals, cap rate movements, and market share shifts are editorial drivers |
| D4: Strategic Relevance | **×1.3** | High audience persona match — CRE is the core audience's primary interest |
| D5: Policy/Regulatory Impact | **×0.8** | Important but secondary to transaction news; zoning stories score lower unless tied to a specific deal |
| D6: Novelty | **×1.0** | Standard importance; breaking CRE news carries value |
| D7: Source Quality | **×1.0** | Standard importance; trade press is adequate for CRE coverage |
| D8: Timeliness | **×1.0** | Standard importance; CRE news cycle is daily |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×0.7** | Reduced importance — CRE stories typically stay within sector; cross-sector spillover is less common |

**Total weighted points possible:** D1(15) + D2(12) + D3(12) + D4(13) + D5(8) + D6(10) + D7(10) + D8(10) + D9(10) + D10(7) = **107**

**Normalization divisor for 100-point scale:** 107 / 10 = **10.7** raw weighted points per 1 scaled point

### 4b. PE Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×1.4** | Fund sizes, deal values, and dry powder amounts are primary editorial signals |
| D2: Party Significance | **×1.4** | Who is doing the deal matters enormously — Apollo/KKR deals demand coverage |
| D3: Market Impact | **×1.4** | PE deal activity signals capital allocation trends, pricing benchmarks, and LP sentiment |
| D4: Strategic Relevance | **×1.2** | PE stories are directly relevant to sponsor/GP/LP audience |
| D5: Policy/Regulatory Impact | **×0.6** | PE is less policy-driven than other sectors (except for carried interest, SEC private fund rules) |
| D6: Novelty | **×1.2** | First reports of fund closes and deal announcements carry premium value |
| D7: Source Quality | **×1.0** | Standard importance |
| D8: Timeliness | **×0.9** | Slightly lower — PE deals develop over longer timeframes; a day's delay is less critical |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.0** | PE deals often span sectors (real estate funds, infra funds, credit funds) |

**Total weighted points possible:** D1(14) + D2(14) + D3(14) + D4(12) + D5(6) + D6(12) + D7(10) + D8(9) + D9(10) + D10(10) = **111**

**Normalization divisor for 100-point scale:** 111 / 10 = **11.1**

### 4c. Data Centers Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×1.3** | Deal values and capital investment amounts are significant |
| D2: Party Significance | **×1.2** | Hyperscaler and major REIT involvement carries weight |
| D3: Market Impact | **×1.2** | Capacity additions, market pricing, and vacancy rates signal trends |
| D4: Strategic Relevance | **×1.5** | High relevance — data center stories are direct capital allocation signals for the CRE+PE audience |
| D5: Policy/Regulatory Impact | **×1.0** | Tax incentives, energy regulation, and zoning decisions materially affect data center development |
| D6: Novelty | **×1.1** | Slight premium on new project announcements and capacity reports |
| D7: Source Quality | **×1.0** | Standard importance |
| D8: Timeliness | **×1.0** | Standard importance |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.3** | Data centers always intersect energy (power), CRE (real estate), and often PE (investment) |

**Total weighted points possible:** D1(13) + D2(12) + D3(12) + D4(15) + D5(10) + D6(11) + D7(10) + D8(10) + D9(10) + D10(13) = **116**

**Normalization divisor for 100-point scale:** 116 / 10 = **11.6**

### 4d. Energy Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×1.2** | Project costs and PPA values matter, but policy often matters more |
| D2: Party Significance | **×1.2** | Major utilities and developers carry weight |
| D3: Market Impact | **×1.2** | Capacity market outcomes, fuel price shifts, and renewable penetration rates |
| D4: Strategic Relevance | **×1.3** | Energy infrastructure is investment infrastructure — directly relevant to PE/infra audience |
| D5: Policy/Regulatory Impact | **×1.4** | Energy is the most regulated sector; FERC, PUC, EPA decisions dominate editorial importance |
| D6: Novelty | **×1.0** | Standard importance |
| D7: Source Quality | **×1.0** | Standard importance |
| D8: Timeliness | **×1.0** | Standard importance |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.1** | Energy touches DC, CRE, PE, and LOC |

**Total weighted points possible:** D1(12) + D2(12) + D3(12) + D4(13) + D5(14) + D6(10) + D7(10) + D8(10) + D9(10) + D10(11) = **114**

**Normalization divisor for 100-point scale:** 114 / 10 = **11.4**

### 4e. Banking/Credit Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×1.1** | Loan portfolio sizes and deal values are significant |
| D2: Party Significance | **×1.3** | Which bank matters — JPMorgan actions carry more weight than a community bank |
| D3: Market Impact | **×1.3** | Credit conditions, lending standards, and rate moves directly affect all sectors |
| D4: Strategic Relevance | **×1.3** | Banking and credit conditions are directly relevant to every Light Tower audience persona |
| D5: Policy/Regulatory Impact | **×1.4** | Banking is highly regulated — Fed, OCC, FDIC, CFPB, SEC actions are primary editorial material |
| D6: Novelty | **×1.0** | Standard importance |
| D7: Source Quality | **×1.2** | Banking stories require high-quality sources; regulatory filings and official data are preferred |
| D8: Timeliness | **×1.1** | Slight premium — regulatory actions and rate changes have immediate market impact |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.2** | Banking conditions affect CRE (lending), PE (financing), DC (project finance), energy (capital) |

**Total weighted points possible:** D1(11) + D2(13) + D3(13) + D4(13) + D5(14) + D6(10) + D7(12) + D8(11) + D9(10) + D10(12) = **119**

**Normalization divisor for 100-point scale:** 119 / 10 = **11.9**

### 4f. Fed/Macro Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×0.8** | Dollar values are secondary — macro stories are about rates, policy, and expectations, not specific dollar amounts |
| D2: Party Significance | **×1.5** | The institution acting matters enormously — Fed vs. CBO vs. BLS vs. a forecaster |
| D3: Market Impact | **×1.5** | Market impact is THE primary dimension for macro stories — does this move markets? |
| D4: Strategic Relevance | **×1.2** | Macro conditions affect all investment decisions and capital allocation |
| D5: Policy/Regulatory Impact | **×1.5** | Macro stories are inherently about policy and its transmission to the economy |
| D6: Novelty | **×1.1** | Slight premium — new data releases and policy announcements are time-sensitive |
| D7: Source Quality | **×1.3** | High premium on authoritative sources (Fed, BLS, BEA, CBO) vs. secondary commentary |
| D8: Timeliness | **×1.2** | Fed statements and data releases are time-critical; same-hour coverage is expected |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.4** | Fed/macro stories affect ALL sectors — the most cross-sector-relevant category |

**Total weighted points possible:** D1(8) + D2(15) + D3(15) + D4(12) + D5(15) + D6(11) + D7(13) + D8(12) + D9(10) + D10(14) = **125**

**Normalization divisor for 100-point scale:** 125 / 10 = **12.5**

### 4g. Local Government Weight Profile

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **×0.7** | Dollar values are small relative to other sectors — a $5M tax abatement is locally significant but small in absolute terms |
| D2: Party Significance | **×1.0** | Standard importance — the jurisdiction matters (NYC vs. a small town) |
| D3: Market Impact | **×1.0** | Standard importance — local actions can have outsized impact on specific submarkets |
| D4: Strategic Relevance | **×1.4** | High relevance — local government actions directly affect development, investment, and property values |
| D5: Policy/Regulatory Impact | **×1.5** | Policy impact is the primary editorial driver in local government — zoning, permits, tax incentives |
| D6: Novelty | **×1.1** | Slight premium — zoning and permit decisions are time-sensitive for deal teams |
| D7: Source Quality | **×1.0** | Standard importance — municipal sources are authoritative but can be thin on detail |
| D8: Timeliness | **×1.0** | Standard importance |
| D9: Editorial Potential | **×1.0** | Standard importance |
| D10: Cross-Sector Impact | **×1.0** | Standard — local government actions primarily affect CRE and Data Centers |

**Total weighted points possible:** D1(7) + D2(10) + D3(10) + D4(14) + D5(15) + D6(11) + D7(10) + D8(10) + D9(10) + D10(10) = **107**

**Normalization divisor for 100-point scale:** 107 / 10 = **10.7**

---

### 4h. Weight Profile Summary Table

| Dimension | CRE | PE | DC | Energy | Banking | Fed/Macro | Local Gov |
|-----------|-----|-----|-----|--------|---------|-----------|-----------|
| D1: Financial Magnitude | 1.5 | 1.4 | 1.3 | 1.2 | 1.1 | 0.8 | 0.7 |
| D2: Party Significance | 1.2 | 1.4 | 1.2 | 1.2 | 1.3 | 1.5 | 1.0 |
| D3: Market Impact | 1.2 | 1.4 | 1.2 | 1.2 | 1.3 | 1.5 | 1.0 |
| D4: Strategic Relevance | 1.3 | 1.2 | 1.5 | 1.3 | 1.3 | 1.2 | 1.4 |
| D5: Policy/Regulatory Impact | 0.8 | 0.6 | 1.0 | 1.4 | 1.4 | 1.5 | 1.5 |
| D6: Novelty | 1.0 | 1.2 | 1.1 | 1.0 | 1.0 | 1.1 | 1.1 |
| D7: Source Quality | 1.0 | 1.0 | 1.0 | 1.0 | 1.2 | 1.3 | 1.0 |
| D8: Timeliness | 1.0 | 0.9 | 1.0 | 1.0 | 1.1 | 1.2 | 1.0 |
| D9: Editorial Potential | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| D10: Cross-Sector Impact | 0.7 | 1.0 | 1.3 | 1.1 | 1.2 | 1.4 | 1.0 |
| **Sum of Weights** | **10.7** | **11.1** | **11.6** | **11.4** | **11.9** | **12.5** | **10.7** |
| **Normalization Divisor** | 1.07 | 1.11 | 1.16 | 1.14 | 1.19 | 1.25 | 1.07 |

---

## 5. Composite Score Calculation

### 5a. Formula

For each sector that a story is classified under (primary sector, and optionally secondary sectors), compute:

```
weighted_sum = Σ (dimension_score[d] × sector_weight[sector][d]) for d in [D1..D10]
composite = (weighted_sum / sum_of_weights[sector]) × 10
```

The result is a 0-100 composite score for the story under a given sector's profile.

**Example: CRE story — $150M multifamily portfolio sale by Blackstone in NYC**

| Dimension | Raw Score | CRE Weight | Weighted |
|-----------|-----------|------------|----------|
| D1: Financial Magnitude | 7 | 1.5 | 10.5 |
| D2: Party Significance | 9 | 1.2 | 10.8 |
| D3: Market Impact | 6 | 1.2 | 7.2 |
| D4: Strategic Relevance | 9 | 1.3 | 11.7 |
| D5: Policy Impact | 3 | 0.8 | 2.4 |
| D6: Novelty | 8 | 1.0 | 8.0 |
| D7: Source Quality | 7 | 1.0 | 7.0 |
| D8: Timeliness | 8 | 1.0 | 8.0 |
| D9: Editorial Potential | 8 | 1.0 | 8.0 |
| D10: Cross-Sector | 4 | 0.7 | 2.8 |
| **Weighted Sum** | | | **76.4** |
| **Composite** | | | **76.4 / 10.7 × 10 = 71.4** |

This story would be Tier 2 (Strongly Recommended) under the CRE profile.

**Same story scored under the PE profile:**

| Dimension | Raw Score | PE Weight | Weighted |
|-----------|-----------|-----------|----------|
| D1: Financial Magnitude | 6 | 1.4 | 8.4 |
| D2: Party Significance | 9 | 1.4 | 12.6 |
| D3: Market Impact | 5 | 1.4 | 7.0 |
| D4: Strategic Relevance | 6 | 1.2 | 7.2 |
| D5: Policy Impact | 3 | 0.6 | 1.8 |
| D6: Novelty | 8 | 1.2 | 9.6 |
| D7: Source Quality | 7 | 1.0 | 7.0 |
| D8: Timeliness | 8 | 0.9 | 7.2 |
| D9: Editorial Potential | 8 | 1.0 | 8.0 |
| D10: Cross-Sector | 4 | 1.0 | 4.0 |
| **Weighted Sum** | | | **72.8** |
| **Composite** | | | **72.8 / 11.1 × 10 = 65.6** |

Under PE profile: 65.6 — a lower score because the story is primarily a CRE transaction, not a PE platform acquisition. This is correct behavior.

### 5b. Multi-Sector Score Storage

A single story may have multiple composite scores — one per sector it's classified under. Store as:

```json
{
  "sector_scores": {
    "COMMERCIAL_REAL_ESTATE": {
      "composite": 71.4,
      "dimensions": { "D1": 7, "D2": 9, ... },
      "weights": { "D1": 1.5, "D2": 1.2, ... },
      "tier": "TIER_2"
    },
    "PRIVATE_EQUITY": {
      "composite": 65.6,
      "dimensions": { "D1": 6, "D2": 9, ... },
      "weights": { "D1": 1.4, "D2": 1.4, ... },
      "tier": "TIER_2"
    }
  },
  "primary_sector": "COMMERCIAL_REAL_ESTATE",
  "highest_composite": 71.4,
  "highest_composite_sector": "COMMERCIAL_REAL_ESTATE"
}
```

For selection purposes, a story's primary sector is the one with the highest composite score across all classified sectors.

---

## 6. Tier Assignment

After composite scores are computed, each story is assigned to a tier within each sector it's classified under.

### 6a. Tier Thresholds

| Tier | Label | Composite Range | Editorial Meaning |
|------|-------|-----------------|-------------------|
| **Tier 1** | Must Cover | composite ≥ 80 | Significant story that demands editorial coverage. Missing a Tier 1 story is a coverage gap. |
| **Tier 2** | Strongly Recommended | 65 ≤ composite < 80 | Solid story with clear editorial merit. Should be covered unless quota already filled by stronger stories. |
| **Tier 3** | Useful Coverage | 50 ≤ composite < 65 | Story worth covering if quota space exists. May be routine but still informative. |
| **Tier 4** | Reserve | 35 ≤ composite < 50 | Story with marginal editorial value. Only selected if significant quota shortfall exists. |
| **Rejected** | Not Selected | composite < 35 | Does not meet minimum threshold for editorial coverage. Logged with rejection reason. |

### 6b. Tier Assignment Logic

```python
def assign_tier(composite: float) -> str:
    if composite >= 80:
        return "TIER_1"
    elif composite >= 65:
        return "TIER_2"
    elif composite >= 50:
        return "TIER_3"
    elif composite >= 35:
        return "TIER_4"
    else:
        return "REJECTED"
```

### 6c. Tier Threshold Calibration

The thresholds above are initial values. They should be calibrated after 2-4 weeks of production data to achieve:

- Tier 1: approximately 10-15% of scored candidates per sector
- Tier 2: approximately 20-25% of scored candidates per sector
- Tier 3: approximately 30-35% of scored candidates per sector
- Tier 4: approximately 20-25% of scored candidates per sector
- Rejected: approximately 10-15% of scored candidates per sector

If actual distributions deviate significantly, thresholds should be recalibrated in `config/scoring_profiles.json`. The scoring spec document should be updated to reflect calibrated thresholds.

---

## 7. Within-Sector Ranking and Selection

### 7a. Ranking

Within each sector, all candidates are ranked by their composite score (descending). The resulting list is the within-sector editorial priority order.

### 7b. Selection Algorithm

```
For each sector:
  1. Sort all admitted candidates by composite score (descending)
  2. Select candidates in priority order:
     a. All Tier 1 (Must Cover) candidates — no quota limit on Tier 1
     b. Tier 2 (Strongly Recommended) candidates — select up to quota fill
     c. Tier 3 (Useful Coverage) candidates — select only if quota not yet filled
     d. Tier 4 (Reserve) candidates — select only if significant quota shortfall
  3. Stop when the sector quota is reached
  4. If fewer than MIN_ARTICLES_PER_SECTOR are selected:
     a. Log INFO: "Sector [name] shortfall: selected [N], target [T]"
     b. Note shortfall reasons in the daily editorial run log
  5. If MORE than MAX_ARTICLES_PER_SECTOR + BOOST are selected:
     a. Trim lowest-scoring stories above the boost threshold
     b. Log INFO: "Sector [name] overflow: trimming [N] stories to [T]"
```

### 7c. Quota Parameters (Configurable)

| Sector | MIN_ARTICLES_PER_SECTOR | TARGET_ARTICLES_PER_SECTOR | MAX_ARTICLES_PER_SECTOR | BOOST_TOLERANCE |
|--------|------------------------|---------------------------|------------------------|-----------------|
| CRE | 10 | 30 | 40 | +10 (allow 50 if strong day) |
| Private Equity | 10 | 30 | 40 | +10 |
| Data Centers | 8 | 30 | 40 | +10 |
| Energy | 10 | 30 | 40 | +10 |
| Banking/Credit | 10 | 30 | 40 | +10 |
| Fed/Macro | 8 | 30 | 40 | +10 |
| Local Government | 10 | 30 | 40 | +10 |
| **Total** | **66** | **210** | **280** | — |

The system target is 210 articles per day. Under heavy news days, the system can boost up to 280 articles across sectors with the `BOOST_TOLERANCE`. Under light news days, the system should not fill quota with low-quality stories — it is better to publish fewer than the target than to publish weak content.

---

## 8. Selection Quotas and Volume Management

### 8a. Volume Floor and Ceiling

- **Absolute minimum per day**: 50 articles (across all sectors). If fewer than 50 stories clear the `composite ≥ 50` threshold, the system should:
  1. Log WARN: "Low volume day: only [N] stories above useful coverage threshold"
  2. Select all stories above threshold (including Tier 3)
  3. Do NOT lower thresholds to fill quota — this degrades editorial quality

- **Absolute maximum per day**: 280 articles (across all sectors). If more than 280 stories clear Tier 2+:
  1. Select top 280 by composite score across all sectors
  2. Log INFO: "High volume day: [N] Tier 2+ stories, selected top 280"
  3. Remaining Tier 2+ stories logged as "near misses" with their composite scores

### 8b. Per-Sector Minimum Guardrails

Each sector has a `MIN_ARTICLES_PER_SECTOR` guardrail (see table above). If a sector produces fewer stories than its minimum:

1. **Shortfall ≤ 3**: Accept the shortfall. Log "Sector [name] light day: [N] stories selected."
2. **Shortfall > 3**: Investigate. Log WARN with detailed diagnostics:
   - Raw story count from that sector's feeds
   - Classification confidence distribution
   - Average composite score
   - Number of stories above each tier threshold
   - Feed health for that sector's sources

### 8c. The Zero-Article Scenario

If a sector produces zero stories above Tier 4 (composite ≥ 35):

1. Log CRITICAL: "Sector [name] produced zero publishable candidates"
2. Trigger source health audit for that sector's feeds
3. Check if sector feeds returned any content at all
4. If feeds returned content but all stories were rejected: log rejection reason distribution
5. Flag for human review in the daily editorial summary

---

## 9. Diversity Controls

### 9a. Subsector Diversity

Within each sector, enforce soft targets for subsector diversity. The rule: within any single sector, no single subsector should account for more than 40% of selected stories, unless the dominant news cycle justifies it.

**CRE Subsectors (examples):**
- Office, Multifamily, Industrial, Retail, Hospitality, Development/Construction, Capital Markets/Debt, Policy, Distress/Workouts, Affordable Housing, Seniors/Student Housing

**PE Subsectors:**
- Buyouts, Growth Equity, Venture Capital, Secondaries, Fundraising, Private Credit, Infrastructure, Real Estate, Distressed, LP/GP Relations

**Data Center Subsectors:**
- Hyperscale, Colocation, Edge, Power/Energy, Fiber/Connectivity, REIT/M&A, Cloud Provider, Construction/Development

**Energy Subsectors:**
- Utility/Grid, Solar, Wind, Storage, Nuclear, Natural Gas, Oil/Midstream, Transmission, Policy/Regulation, Hydrogen/Emerging

**Banking Subsectors:**
- Commercial Banking, Investment Banking, Regulation, Credit Risk, Fintech, Community Banking, Ratings, Structured Finance, Mortgage

### 9b. Diversity Enforcement Logic

```python
def check_subsector_diversity(selected: list[Story], sector: Sector) -> list[str]:
    subsector_counts = Counter(s.subsector for s in selected)
    total = len(selected)
    violations = []
    for subsector, count in subsector_counts.items():
        pct = count / total * 100 if total > 0 else 0
        if pct > MAX_SUBSECTOR_PCT:  # default 40%
            violations.append(f"Subsector {subsector}: {count}/{total} ({pct:.1f}%) exceeds {MAX_SUBSECTOR_PCT}% cap")
    return violations
```

When a violation is detected:

1. Log WARN with the violation details
2. If the violation is attributable to a dominant news cycle (e.g., 60% of CRE stories are about office distress during a major downturn), document the justification and bypass the cap
3. If no dominant news cycle justifies the concentration, trim the lowest-scoring stories from the overrepresented subsector until balance is restored
4. Diversity metrics are included in the daily editorial run summary

### 9c. Geographic Diversity (CRE and Local Government Only)

For CRE and Local Government sectors, no single MSA should exceed 50% of selections unless it's NYC (the system's home market) or the dominant news cycle justifies it.

---

## 10. Cross-Sector Deduplication

After within-sector selection is complete for all seven sectors, run a cross-sector deduplication pass.

### 10a. Duplicate Detection

Two stories from different sectors are considered duplicates if:

1. **Same URL:** Exact URL match (strongest signal)
2. **Same Event Cluster ID:** Both stories were clustered into the same event by `cluster_events()` during scoring
3. **High Title Similarity + Entity Overlap:** Fuzzy title similarity > 0.85 AND at least two shared extracted entities
4. **Same SEC Filing:** Both reference the same SEC filing accession number or CIK

### 10b. Deduplication Logic

When a duplicate pair is found across sectors:

1. Compare composite scores for the story under each sector's profile
2. **Keep:** The sector under which the story scored highest
3. **Remove:** The sector under which the story scored lower
4. **Cross-link:** The removed sector's daily edition adds a cross-reference: "See also: [story title] under [sector name]"
5. **Log:** The deduplication decision with both composite scores and the rationale

### 10c. Deduplication Tolerance for Cross-Sector Stories

Some stories genuinely belong in multiple sectors and should not be deduplicated. The rule: if a story's composite score in the secondary sector is ≥ 75% of its composite score in the primary sector, the story is NOT deduplicated — it appears in both sector editions as a "cross-sector story" with appropriate sector-specific framing.

**Example:** A Blackstone acquisition of a portfolio of data center assets with 800MW of power capacity might score:
- CRE: 68 (framed as real estate transaction)
- PE: 72 (framed as PE platform acquisition)
- DC: 85 (framed as data center capacity expansion)

The highest score is DC (85). PE's score (72) is 84.7% of DC's score (≥ 75%), so the story also appears in the PE edition. CRE's score (68) is 80% of DC's score (≥ 75%), so the story also appears in the CRE edition. Result: story published in DC (primary, with DC framing), PE (cross-sector, with PE framing), and CRE (cross-sector, with CRE framing).

---

## 11. Cross-Sector Story Promotion

### 11a. The Promotion Mechanism

A story classified under one sector may be promoted into a different sector's selection list if the cross-sector score mechanism (Section 10c) applies. Promotion is always from the highest-scoring sector ("home sector") to lower-scoring sectors ("guest sectors").

### 11b. Promotion Logic

```
For each story with multi-sector classifications:
  1. Identify home sector = argmax(sector_scores[].composite)
  2. For each guest sector (any other sector with a composite score):
     a. If guest_composite / home_composite ≥ PROMOTION_THRESHOLD (default 0.75):
        - Add story to guest sector's selection list
        - Set story.tier in guest sector = story.tier in home sector (or one tier lower, if desired)
        - Set story.cross_sector_source = home_sector
     b. If guest_composite / home_composite < PROMOTION_THRESHOLD:
        - Story stays only in home sector
        - Guest sector gets a cross-reference link
```

---

## 12. Rejection Reason Codes and Audit Trail

### 12a. Rejection Reason Codes

Every story that is scored but not selected receives a rejection reason code. These codes enable systematic analysis of pipeline performance.

| Code | Category | Description |
|------|----------|-------------|
| `SCORE_BELOW_TIER_1` | Scoring | Composite score below Tier 1 threshold for all classified sectors |
| `SCORE_BELOW_TIER_2` | Scoring | Composite score below Tier 2 threshold; story had merit but not enough to make the cut |
| `SCORE_BELOW_MIN` | Scoring | Composite score below REJECTED threshold (35) |
| `QUOTA_FULL` | Selection | Story scored high enough but sector quota was already filled by higher-scoring stories |
| `DIVERSITY_CAP` | Selection | Story excluded due to subsector or geographic diversity constraints |
| `DUPLICATE` | Deduplication | Story was a duplicate of a higher-scoring story in another sector |
| `CLASS_CONFIDENCE_LOW` | Classification | Classification confidence below minimum threshold |
| `CLASS_NO_SECTOR` | Classification | Could not classify into any sector |
| `CLASS_EXCLUDED` | Classification | Matched exclusion patterns (consumer real estate, celebrity, etc.) |
| `EVIDENCE_INSUFFICIENT` | Editorial | Story scored well but had insufficient source material to write an article |
| `RECENCY_FAIL` | Timeliness | Story older than `MAX_AGE_HOURS` (default 72 hours) |
| `SOURCE_BLOCKLIST` | Source | Source is on the blocklist (known spam, duplicate aggregator) |
| `EDITORIAL_OVERRIDE` | Manual | Human editor explicitly rejected this story |

### 12b. Audit Trail Requirements

For every story that passes through the scoring pipeline, the following must be logged:

```json
{
  "story_id": "hash-derived-uuid",
  "title": "story title",
  "url": "source URL",
  "source": "source name",
  "published_at": "ISO 8601 timestamp",
  "ingested_at": "ISO 8601 timestamp",
  "classification": {
    "primary_sector": "COMMERCIAL_REAL_ESTATE",
    "secondary_sectors": ["PRIVATE_EQUITY"],
    "confidence": 0.85,
    "method": "source_prior_regex",  // or "llm" or "source_prior_regex_llm"
    "llm_model": null  // if LLM was used
  },
  "event_type": "ACQ",
  "extracted_entities": {
    "companies": ["Blackstone", "Related Companies"],
    "amounts": [{"value": 150, "unit": "USD", "scale": "million"}],
    "geographies": [{"city": "New York", "state": "NY", "msa": "New York-Newark-Jersey City"}]
  },
  "sector_scores": {
    "COMMERCIAL_REAL_ESTATE": {
      "composite": 71.4,
      "dimensions": { "D1": 7, "D2": 9, "D3": 6, "D4": 9, "D5": 3, "D6": 8, "D7": 7, "D8": 8, "D9": 8, "D10": 4 },
      "weights": { "D1": 1.5, "D2": 1.2, "D3": 1.2, "D4": 1.3, "D5": 0.8, "D6": 1.0, "D7": 1.0, "D8": 1.0, "D9": 1.0, "D10": 0.7 },
      "tier": "TIER_2"
    }
  },
  "selection": {
    "selected": true,
    "selected_sector": "COMMERCIAL_REAL_ESTATE",
    "rank_in_sector": 12,
    "selection_timestamp": "ISO 8601",
    "selection_method": "within_sector_quota"
  },
  "rejection": null  // or { "code": "QUOTA_FULL", "reason": "..." }
}
```

The audit trail must be queryable by story ID, sector, date, rejection code, and selection status.

---

## 13. Configurability and Runtime Overrides

### 13a. Configuration File: `config/scoring_profiles.json`

All configurable parameters live in a single JSON file:

```json
{
  "version": "2.0.0",
  "description": "Light Tower Group 7-Sector Scoring Configuration",
  "last_updated": "2026-07-30",
  "global": {
    "tier_thresholds": {
      "TIER_1": 80,
      "TIER_2": 65,
      "TIER_3": 50,
      "TIER_4": 35
    },
    "min_classification_confidence": 0.50,
    "max_article_age_hours": 72,
    "cross_sector_promotion_threshold": 0.75,
    "subsector_diversity_cap_pct": 40,
    "msa_concentration_cap_pct": 50
  },
  "sectors": {
    "COMMERCIAL_REAL_ESTATE": {
      "weights": {
        "D1_financial_magnitude": 1.5,
        "D2_party_significance": 1.2,
        "D3_market_impact": 1.2,
        "D4_strategic_relevance": 1.3,
        "D5_policy_impact": 0.8,
        "D6_novelty": 1.0,
        "D7_source_quality": 1.0,
        "D8_timeliness": 1.0,
        "D9_editorial_potential": 1.0,
        "D10_cross_sector": 0.7
      },
      "quota": {
        "min_articles": 10,
        "target_articles": 30,
        "max_articles": 40,
        "boost_tolerance": 10
      },
      "subsectors": ["office", "multifamily", "industrial", "retail", "hospitality", "development", "capital_markets", "policy", "distress", "affordable_housing", "seniors_housing", "student_housing"]
    }
    // ... full entries for all 7 sectors
  },
  "source_quality_tiers": {
    "0": { "label": "primary_authoritative", "min_score": 9, "max_score": 10 },
    "1": { "label": "major_financial_top_trade", "min_score": 7, "max_score": 8 },
    "2": { "label": "established_trade_regional", "min_score": 5, "max_score": 6 },
    "3": { "label": "aggregator_general_interest", "min_score": 3, "max_score": 4 },
    "4": { "label": "unverified_low_authority", "min_score": 1, "max_score": 2 }
  },
  "financial_magnitude_scale": {
    "thresholds": [
      {"min": 0, "max": 1, "score": 1, "label": "under_1m"},
      {"min": 1, "max": 5, "score": 2, "label": "1m_to_5m"},
      {"min": 5, "max": 25, "score": 3, "label": "5m_to_25m"},
      {"min": 25, "max": 100, "score": 5, "label": "25m_to_100m"},
      {"min": 100, "max": 500, "score": 7, "label": "100m_to_500m"},
      {"min": 500, "max": 1000, "score": 8, "label": "500m_to_1b"},
      {"min": 1000, "max": 5000, "score": 9, "label": "1b_to_5b"},
      {"min": 5000, "max": 999999, "score": 10, "label": "over_5b"}
    ]
  },
  "watchlist_entity_tiers": {
    "critical": { "party_significance_score": 10, "label": "Tier 1 / Critical" },
    "high": { "party_significance_score": 8, "label": "Tier 2 / High" },
    "medium": { "party_significance_score": 6, "label": "Tier 3 / Medium" },
    "known": { "party_significance_score": 4, "label": "Known but not on watchlist" },
    "unknown": { "party_significance_score": 2, "label": "Unknown entity" }
  }
}
```

### 13b. Runtime Override Mechanism

The scoring system must support runtime overrides for:

1. **Per-run weight adjustments:** If an editor wants to emphasize policy stories on a heavy regulatory day, weights can be adjusted for a single run via a command-line flag or environment variable
2. **Per-sector quota adjustments:** If a sector has an unusually heavy or light news day, quota parameters can be adjusted
3. **Manual story promotion:** An editor can promote a specific story by URL or story ID to Tier 1 regardless of composite score
4. **Manual story rejection:** An editor can reject a specific story regardless of composite score

Overrides are logged with the editor's identity (or "system" if automated), timestamp, and reason.

---

## 14. Deterministic vs. LLM-Assisted Scoring

### 14a. Scoring Method Assignment

| Dimension | Method | Rationale |
|-----------|--------|-----------|
| D1: Financial Magnitude | **Deterministic** | Extracted dollar amounts map directly to score table |
| D2: Party Significance | **Deterministic** | Entity tier lookup from watchlist |
| D3: Market Impact | **Hybrid** | Deterministic signals (has_record, has_distress, has_policy_change) provide base; LLM refines for ambiguous cases |
| D4: Strategic Relevance | **LLM-Assisted** | Requires audience persona judgment; LLM with structured output |
| D5: Policy/Regulatory Impact | **Hybrid** | Source tier + topic patterns provide base; LLM refines scope/consequence |
| D6: Novelty | **Deterministic** | Event memory archive lookup by title similarity and entity overlap |
| D7: Source Quality | **Deterministic** | Direct lookup from source tier map |
| D8: Timeliness | **Deterministic** | Publication timestamp minus current time |
| D9: Editorial Potential | **Hybrid** | Evidence depth is deterministic; LLM assesses narrative richness |
| D10: Cross-Sector Impact | **Deterministic** | Count of classified sectors from multi-label classification output |

### 14b. LLM Fallback Protocol

When an LLM call fails (timeout, API error, rate limit):

1. Dimensions with deterministic scoring: use deterministic score only
2. Dimensions that require LLM: use the deterministic base score. If no deterministic base is available, default to the median score (5)
3. Log the fallback with the specific error
4. Flag the story as `scoring_method: "deterministic_fallback"` with the failed dimensions listed

### 14c. Scoring Cost Budget

| Phase | Stories/Day | Model | Est. Tokens/Call | Est. Cost/Day |
|-------|------------|-------|-----------------|---------------|
| Classification (LLM) | ~200 (ambiguous only) | DeepSeek-V3-Lite | 200 | $0.01 |
| Scoring (LLM) | ~600 (D3, D4, D5, D9) | DeepSeek-V3 | 500 | $0.30 |
| **Total Scoring Cost** | | | | **~$0.31/day** |

At estimated DeepSeek pricing ($0.07-0.14/1M tokens), the scoring phase is approximately 1.5% of the total pipeline cost (dominated by article generation at ~210 articles/day).

---

## 15. Scoring Edge Cases and Calibration Rules

### 15a. Stories With No Extractable Financial Value

- Default D1 (Financial Magnitude): 3
- D3 (Market Impact) and D4 (Strategic Relevance) carry the editorial weight
- Example: "Fed Chair Powell Signals Patience on Rate Cuts" — no dollar amount, but D3 might be 9 and D4 might be 8

### 15b. Stories Referencing Multiple Deals/Actions

- Score each dimension based on the most significant deal/action, not the aggregate
- Example: "Three Data Center Deals Close This Week: $50M, $75M, $400M" — D1 = 7 (based on the $400M deal, not the sum)

### 15c. Stories With Conflicting Signals

- If a story has BOTH distress language AND positive growth language, score D3 (Market Impact) based on the dominant signal
- The LLM refinement pass (for hybrid dimensions) should resolve ambiguities

### 15d. Press Releases Disguised as News

- Source is a company's own newsroom AND the tone is promotional: reduce D7 (Source Quality) by 2 points
- If the same event is covered by a trade publication: use the trade publication's version for scoring, not the press release

### 15e. Earnings Reports

- Earnings that beat/miss estimates significantly receive D3 (Market Impact) bonus: +2 if beat/miss > 10%, +1 if > 5%
- Routine in-line earnings: D3 = 3, D6 (Novelty) = 2 (highly anticipated, no surprise)

### 15f. Mergers and Acquisitions

- D1 (Financial Magnitude): use deal value
- D2 (Party Significance): use the highest-tier entity involved (acquirer OR target)
- D3 (Market Impact): +2 bonus if deal is sector-consolidating (reduces competitor count), +1 if creates new market leader

### 15g. Data Releases (BLS, BEA, Census, EIA)

- D1 (Financial Magnitude): default 3 (unless specific dollar value present)
- D2 (Party Significance): 9 (authoritative source)
- D3 (Market Impact): scored based on deviation from consensus expectations
- D6 (Novelty): 10 in the hour after release, decreasing by schedule
- D7 (Source Quality): 9-10 (primary source)
- D8 (Timeliness): 10 if just released

### 15h. Anonymous / Unattributed Stories

- D7 (Source Quality): automatic -3 penalty if source is anonymous
- D9 (Editorial Potential): automatic -2 penalty (cannot verify facts without attribution)

---

## 16. Implementation Checklist and Testing

### 16a. Implementation Phases

**Phase 1 — Deterministic Scoring Engine (Week 1-2):**
- [ ] Implement D1 (Financial Magnitude) deterministic scorer
- [ ] Implement D2 (Party Significance) with watchlist lookup
- [ ] Implement D6 (Novelty) with event memory archive
- [ ] Implement D7 (Source Quality) with source tier map
- [ ] Implement D8 (Timeliness) with timestamp comparison
- [ ] Implement D10 (Cross-Sector Impact) from classification output
- [ ] Implement sector weight profile loading from `scoring_profiles.json`
- [ ] Implement composite score calculation
- [ ] Implement tier assignment
- [ ] Implement within-sector ranking and selection with quota logic

**Phase 2 — Hybrid and LLM Scoring (Week 3-4):**
- [ ] Implement D3 (Market Impact) hybrid scorer (deterministic base + LLM refinement)
- [ ] Implement D4 (Strategic Relevance) LLM-assisted scorer
- [ ] Implement D5 (Policy/Regulatory Impact) hybrid scorer
- [ ] Implement D9 (Editorial Potential) hybrid scorer
- [ ] Implement LLM fallback protocol
- [ ] Implement classification LLM call for ambiguous stories

**Phase 3 — Cross-Sector Logic (Week 5-6):**
- [ ] Implement cross-sector deduplication
- [ ] Implement cross-sector story promotion
- [ ] Implement diversity controls (subsector, geographic)
- [ ] Implement rejection reason code logging
- [ ] Implement full audit trail

**Phase 4 — Calibration and Tuning (Week 7-8):**
- [ ] Run scoring on 2 weeks of historical data
- [ ] Compare score distributions against human editor judgments (sample of 50 stories per sector)
- [ ] Calibrate tier thresholds to achieve target distributions
- [ ] Calibrate dimension weights based on false positive / false negative analysis
- [ ] Document calibrated parameters and update `scoring_profiles.json`

### 16b. Testing Requirements

**Unit Tests:**
- Test each deterministic scorer with known inputs and expected outputs
- Test composite score calculation with known dimension scores and weight profiles
- Test tier assignment for boundary values (exactly 80, 65, 50, 35, 80.1, 64.9, etc.)
- Test quota selection with varying story counts (0, 5, 20, 30, 50, 100 candidates)
- Test cross-sector deduplication with duplicate examples
- Test diversity cap enforcement

**Integration Tests:**
- End-to-end scoring of a batch of 20 stories per sector (140 total)
- Verify that a $200M data center deal (DC primary) outscores a $10M multifamily deal (CRE primary) within their respective sectors
- Verify that a Fed rate hike story receives high cross-sector impact (D10)
- Verify that same-day news receives higher timeliness (D8) than 3-day-old news
- Verify that rejection reason codes are correctly assigned

**Calibration Tests:**
- Score 500 historical stories (mix across sectors) with the new framework
- Compare against the old `score_event()` output for CRE stories (should be directionally similar but not identical)
- Compare top-30 selections per sector against human editorial judgment
- Measure inter-sector score distribution overlap (too much overlap = dimensions not discriminating)

---

## Appendix A: Dimension Scoring Quick Reference Card

| Dimension | 1-2 (Minimal) | 3-4 (Low) | 5-6 (Moderate) | 7-8 (High) | 9-10 (Exceptional) |
|-----------|--------------|-----------|----------------|------------|-------------------|
| **D1: Financial Magnitude** | < $1M deal | $1M-$25M | $25M-$500M | $500M-$5B | > $5B |
| **D2: Party Significance** | Unknown entity | Known, not listed | Tier 3 watchlist | Tier 2 watchlist | Tier 1 / Critical watchlist |
| **D3: Market Impact** | Trivial | Routine | Notable deal | Reshapes pricing | Systemic market event |
| **D4: Strategic Relevance** | Peripheral | Adjacent | Useful context | Relevant to audience | Directly addresses decisions |
| **D5: Policy Impact** | None | Minor admin action | Meaningful development | Major agency action | Federal law/rule, national scope |
| **D6: Novelty** | Syndication | 3rd+ coverage | New angle/analysis | 2nd source w/ new facts | First report, exclusive |
| **D7: Source Quality** | Unverified blog | Aggregator | Established trade | Major financial | Government filing, court order |
| **D8: Timeliness** | > 5 days old | 3-5 days | Yesterday | Same day | < 1 hour |
| **D9: Editorial Potential** | Insufficient | Thin (1 source) | Adequate (2 sources) | Strong (2+ w/ full text) | Deep (3+ corroborated) |
| **D10: Cross-Sector** | 1 sector, niche | 1 sector | 2 sectors | 3 sectors | 5+ sectors |

---

## End of Document

This scoring specification is the authoritative definition of how the Light Tower Group 7-Sector Intelligence Engine evaluates, ranks, and selects stories for editorial coverage. All implementation must conform to this specification. Any deviation must be documented and approved as a spec amendment.
