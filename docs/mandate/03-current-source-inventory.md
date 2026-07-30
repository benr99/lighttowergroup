# Current Source Inventory: The Light Tower Group Insights Intelligence Engine

**Document:** 03-Current-Source-Inventory
**Date:** July 30, 2026
**Status:** Pre-Overhaul Baseline — Source Universe Catalog

---

## 1. Overview

The current source universe consists of approximately 103 RSS feed sources plus supplementary NewsAPI queries and an SEC EDGAR RSS feed. Sources are organized into four tiers based on geographic focus and editorial purpose, plus a separate federal/regulatory tier.

**Total feeds:** ~103 (approx. 90 CRE-focused + 13 federal/regulatory)
**Sectors covered:** 1 of 7 mandated (Commercial Real Estate only)
**Feed health:** 48 of 103 (46%) returned empty on most recent fetch
**Supplementary:** 18 NewsAPI keyword queries (free tier) + SEC EDGAR RSS

### Sector Coverage Summary

| Sector | Feeds | Coverage Quality | Notes |
|--------|-------|-----------------|-------|
| Commercial Real Estate | ~65 | Comprehensive (for CRE) | Tiers 1-4 cover NYC, national, finance, and regional CRE |
| Private Equity | 1-2 | Incidental only | PERE News and Bloomberg pass through but are filtered for CRE relevance |
| Data Centers | 0 | None | No data center trade publications or hyperscaler sources |
| Energy | 0 | None | No utility, grid, or energy market publications |
| Banking/Credit | 5-10 | Partial, CRE-filtered | American Banker, MBA Newslink, Trepp — only CRE-adjacent stories survive |
| Fed/Macro | 10-15 | Strong for CRE-relevant stories | Federal Reserve, FDIC, OCC, SEC, FHFA, HUD, CFPB, Treasury — but triage filters for CRE relevance |
| Local Government | 0 | None | No municipal, planning board, or city council feeds |

---

## 2. Tier 1: NYC-Focused CRE (~20 feeds)

These feeds are the core of the system's editorial coverage. They produce the majority of scored and published stories.

| # | Source Name | Feed URL / Source | Coverage | Quality Tier | Health Status |
|---|-------------|-------------------|----------|-------------|---------------|
| 1 | The Real Deal | RSS feed | NYC CRE (sales, leasing, development, policy) | 2 — Established Trade | BROKEN — 3 consecutive empty runs |
| 2 | Commercial Observer | RSS feed | NYC CRE (leasing, finance, development) | 2 — Established Trade | Healthy |
| 3 | Bisnow New York | RSS feed | NYC CRE (events-driven, deal coverage) | 3 — Aggregator/Trade | Mixed |
| 4 | Real Estate Weekly | RSS feed | NYC CRE (transactions, people moves) | 2 — Established Trade | Mixed |
| 5 | Crain's New York Business | RSS feed | NYC business + CRE | 2 — Established Business | Healthy |
| 6 | New York YIMBY | RSS feed | NYC development pipeline, new construction | 2 — Established Trade | Healthy |
| 7 | Observer Real Estate | RSS feed | NYC luxury/ high-end CRE | 3 — General Interest | Mixed |
| 8 | The City | RSS feed | NYC local news incl. real estate | 3 — General Interest | Mixed |
| 9 | 6sqft | RSS feed | NYC real estate, architecture, urbanism | 3 — Trade/Aggregator | Healthy |
| 10 | Gothamist | RSS feed | NYC local news | 3 — General Interest | Mixed |
| 11 | CityLand | RSS feed | NYC land use, zoning, ULURP | 2 — Specialized | Healthy |
| 12 | NY Daily News — Real Estate | RSS feed | NYC real estate section | 3 — General Interest | Mixed |
| 13 | NY Post — Real Estate | RSS feed | NYC real estate section | 3 — General Interest | Mixed |
| 14 | Patch NYC | RSS feed | NYC neighborhood news | 4 — Hyperlocal | Empty frequently |
| 15 | Brownstoner | RSS feed | Brooklyn real estate | 3 — Trade | Mixed |
| 16 | Queens Post | RSS feed | Queens real estate + development | 4 — Hyperlocal | Empty frequently |
| 17 | Brooklyn Paper | RSS feed | Brooklyn news incl. development | 4 — Hyperlocal | Empty frequently |
| 18 | amNewYork | RSS feed | NYC general news | 4 — General Interest | Empty frequently |
| 19 | StreetEasy Blog | RSS feed | NYC residential/rental market data | 3 — Data Provider | Mixed |
| 20 | NYC DCP Updates | RSS feed | NYC Dept. of City Planning announcements | 1 — Government | Intermittent |

**Sector coverage:** Commercial Real Estate (NYC metro only)
**Geography:** New York City and immediate metro area
**Known gaps within tier:** Missing some hyperlocal outer-borough sources; no Staten Island-specific feeds

---

## 3. Tier 2: National CRE (~30 feeds)

National CRE trade publications covering transactions, development, financing, and policy across all US markets.

| # | Source Name | Feed URL / Source | Coverage | Quality Tier | Health Status |
|---|-------------|-------------------|----------|-------------|---------------|
| 1 | GlobeSt | RSS feed | National CRE (transactions, trends, people) | 2 — Established Trade | Healthy |
| 2 | Connect CRE | RSS feed | National CRE (deal coverage, market reports) | 2 — Established Trade | Healthy |
| 3 | Propmodo | RSS feed | CRE technology, innovation, future of real estate | 2 — Established Trade | Mixed |
| 4 | National Real Estate Investor (NREI) | RSS feed | Institutional CRE investment | 2 — Established Trade | Mixed |
| 5 | Multi-Housing News | RSS feed | Multifamily sector (development, investment, operations) | 2 — Established Trade | Healthy |
| 6 | CP Executive | RSS feed | Commercial property executive news | 3 — Trade | Mixed |
| 7 | HousingWire | RSS feed | Residential mortgage + housing (CRE crossover) | 2 — Established Trade | Healthy |
| 8 | Construction Dive | RSS feed | Construction industry (CRE-adjacent) | 2 — Industry Dive | Healthy |
| 9 | Urban Land Institute (ULI) | RSS feed | Land use, urban planning, CRE research | 1 — Industry Authority | Mixed |
| 10 | Affordable Housing Finance | RSS feed | Affordable housing development, LIHTC, policy | 2 — Specialized | Mixed |
| 11 | Building Design + Construction (BD+C) | RSS feed | Architecture, engineering, construction | 2 — Established Trade | Mixed |
| 12 | Shopping Center Business | RSS feed | Retail real estate sector | 2 — Established Trade | Mixed |
| 13 | RE Business Online | RSS feed | National CRE transactions and development | 3 — Trade | Mixed |
| 14 | Bisnow Atlanta | RSS feed | Atlanta CRE | 3 — Aggregator/Trade | Mixed |
| 15 | Bisnow Austin | RSS feed | Austin CRE | 3 — Aggregator/Trade | Mixed |
| 16 | Bisnow Boston | RSS feed | Boston CRE | 3 — Aggregator/Trade | Mixed |
| 17 | Bisnow Chicago | RSS feed | Chicago CRE | 3 — Aggregator/Trade | Mixed |
| 18 | Bisnow Dallas-Fort Worth | RSS feed | DFW CRE | 3 — Aggregator/Trade | Mixed |
| 19 | Bisnow Denver | RSS feed | Denver CRE | 3 — Aggregator/Trade | Mixed |
| 20 | Bisnow Houston | RSS feed | Houston CRE | 3 — Aggregator/Trade | Mixed |
| 21 | Bisnow Los Angeles | RSS feed | LA CRE | 3 — Aggregator/Trade | Mixed |
| 22 | Bisnow San Francisco | RSS feed | SF Bay Area CRE | 3 — Aggregator/Trade | Mixed |
| 23 | Bisnow Seattle | RSS feed | Seattle CRE | 3 — Aggregator/Trade | Mixed |
| 24 | Bisnow Washington DC | RSS feed | DC metro CRE | 3 — Aggregator/Trade | Mixed |
| 25 | Senior Housing News | RSS feed | Seniors housing sector | 2 — Specialized | Mixed |
| 26 | Student Housing Business | RSS feed | Student housing sector | 3 — Trade | Empty frequently |
| 27 | Hotel Business | RSS feed | Hospitality real estate | 3 — Trade | Empty frequently |
| 28 | Multifamily Executive | RSS feed | Multifamily development + management | 3 — Trade | Mixed |
| 29 | Commercial Property Executive | RSS feed | Institutional CRE investment | 3 — Trade | Mixed |
| 30 | RE Journals | RSS feed | Regional CRE markets (Midwest focus) | 3 — Trade | Mixed |

**Sector coverage:** Commercial Real Estate (national scope)
**Geography:** All US markets, with regional depth via 10 Bisnow city feeds
**Known gaps within tier:** Light on industrial/logistics (no dedicated industrial feed); no life sciences/biotech CRE feed; no self-storage sector feed; no manufactured housing feed

---

## 4. Tier 3: Capital Markets / Finance (~25 feeds)

Financial press and capital markets sources that carry CRE-adjacent content.

| # | Source Name | Feed URL / Source | Coverage | Quality Tier | Health Status |
|---|-------------|-------------------|----------|-------------|---------------|
| 1 | PERE News | RSS feed | Private equity real estate (fundraising, deals, LPs) | 2 — Established Trade | Mixed |
| 2 | Mortgage Professional America | RSS feed | Mortgage industry (residential + commercial) | 3 — Trade | Mixed |
| 3 | MBA Newslink | RSS feed | Mortgage Bankers Association (CRE + resi finance) | 2 — Trade/Industry | Intermittent |
| 4 | Bloomberg Real Estate | RSS feed | Global real estate (broad coverage) | 2 — Major Financial | Healthy |
| 5 | Reuters | RSS feed | Global financial news (general) | 2 — Major Newswire | Healthy |
| 6 | CNBC Real Estate | RSS feed | Consumer + commercial real estate news | 3 — Financial Media | Mixed |
| 7 | Wall Street Journal | RSS feed | National/international business (general) | 2 — Major Financial | Requires subscription |
| 8 | MarketWatch | RSS feed | Financial markets news | 3 — Financial Media | Mixed |
| 9 | American Banker | RSS feed | Banking industry (CRE lending, regulation) | 2 — Specialized Financial | Mixed |
| 10 | Mortgage News Daily | RSS feed | Mortgage rates, MBS, housing finance | 3 — Specialized | Mixed |
| 11 | Trepp | RSS feed | CMBS data, CRE finance analytics | 1 — Data/ Analytics | Intermittent |
| 12 | HUD Exchange | RSS feed | HUD programs, funding notices, policy | 1 — Government | Intermittent |
| 13 | ATTOM Data Solutions | RSS feed | Property data, housing market trends | 2 — Data Provider | Mixed |
| 14 | NAREIT | RSS feed | REIT industry news and data | 1 — Industry Association | Intermittent |
| 15 | National Multifamily Housing Council (NMHC) | RSS feed | Multifamily industry policy + research | 1 — Industry Association | Intermittent |
| 16 | Institutional Real Estate, Inc. | RSS feed | Institutional CRE investment | 2 — Specialized | Mixed |
| 17 | RealPage | RSS feed | Multifamily data, analytics, market reports | 2 — Data Provider | Mixed |
| 18 | Yardi Matrix | RSS feed | CRE data and market reports | 2 — Data Provider | Mixed |
| 19 | National Association of Realtors (NAR) | RSS feed | Residential + commercial Realtor data | 1 — Industry Association | Intermittent |
| 20 | Fannie Mae | RSS feed | Housing finance, economic research | 1 — GSE | Intermittent |
| 21 | Freddie Mac | RSS feed | Housing finance, multifamily research | 1 — GSE | Intermittent |
| 22 | CRE Finance Council (CREFC) | RSS feed | CRE finance industry association | 1 — Industry Association | Intermittent |
| 23 | CCIM Institute | RSS feed | Commercial investment real estate | 2 — Industry Association | Mixed |
| 24 | SIOR | RSS feed | Industrial/office brokerage association | 2 — Industry Association | Empty frequently |
| 25 | Appraisal Institute | RSS feed | Commercial real estate appraisal | 3 — Professional | Empty frequently |

**Sector coverage:** CRE capital markets, banking (CRE-adjacent only), housing finance
**Known gaps within tier:** Light on pure capital markets (no Dealogic, no Preqin, no Refinitiv); no dedicated CMBS new issuance tracker beyond Trepp; no direct access to bank call reports or Fed H.8 data outside RSS headlines

---

## 5. Tier 4: Regional / Context (~15 feeds)

Regional business journals and general-interest publications providing geographic and economic context for CRE stories.

| # | Source Name | Feed URL / Source | Coverage | Quality Tier | Health Status |
|---|-------------|-------------------|----------|-------------|---------------|
| 1 | NY Post | RSS feed | NYC general news (tabloid) | 3 — General Interest | Healthy |
| 2 | Curbed NY | RSS feed | NYC urbanism, development, architecture | 3 — Niche Media | Mixed |
| 3 | Bloomberg Businessweek | RSS feed | General business, long-form | 2 — Major Financial | Requires subscription |
| 4 | Axios | RSS feed | National news, policy, business (short-form) | 2 — Digital Media | Healthy |
| 5 | CoStar News | RSS feed | National CRE data + news (paywalled) | 2 — Data Provider | Intermittent (paywall) |
| 6 | New York Times — Real Estate | RSS feed | Residential + CRE coverage | 2 — Major Newspaper | Requires subscription |
| 7 | Crain's Chicago Business | RSS feed | Chicago business (incl. CRE) | 2 — Regional Business | Mixed |
| 8 | Crain's Detroit Business | RSS feed | Detroit business (incl. CRE) | 3 — Regional Business | Mixed |
| 9 | Boston Business Journal | RSS feed | Boston business (incl. CRE) | 3 — Regional Business | Mixed |
| 10 | Philadelphia Business Journal | RSS feed | Philadelphia business (incl. CRE) | 3 — Regional Business | Mixed |
| 11 | Dallas Business Journal | RSS feed | Dallas business (incl. CRE) | 3 — Regional Business | Mixed |
| 12 | Houston Business Journal | RSS feed | Houston business (incl. CRE) | 3 — Regional Business | Mixed |
| 13 | San Francisco Business Times | RSS feed | SF/Bay Area business (incl. CRE) | 3 — Regional Business | Mixed |
| 14 | Washington Business Journal | RSS feed | DC metro business (incl. CRE) | 3 — Regional Business | Mixed |
| 15 | Los Angeles Business Journal | RSS feed | LA business (incl. CRE) | 3 — Regional Business | Mixed |

**Sector coverage:** Regional business + CRE context
**Known gaps within tier:** Only 10 regional business journals covered; no Southeast (Miami, Atlanta, Charlotte), no Mountain West beyond Denver (Salt Lake, Phoenix), no Pacific Northwest beyond Seattle (Portland)

---

## 6. Federal / Regulatory Feeds (~15 feeds)

Primary-source federal agency feeds providing policy, regulatory, and economic data relevant to commercial real estate and financial markets.

| # | Agency | Feed Type | Coverage | Quality Tier | Health Status |
|---|--------|-----------|----------|-------------|---------------|
| 1 | Federal Reserve Board | Press Releases | Monetary policy, regulatory actions | 1 — Primary/Authoritative | Healthy |
| 2 | Federal Reserve Board | Speeches | Governor and staff speeches | 1 — Primary/Authoritative | Mixed |
| 3 | Federal Reserve Board | Testimony | Congressional testimony | 1 — Primary/Authoritative | Intermittent |
| 4 | Federal Reserve Board | Monetary Policy | FOMC statements, minutes | 1 — Primary/Authoritative | Event-driven |
| 5 | Federal Reserve Board | Banking Regulation | Supervisory actions, rulemaking | 1 — Primary/Authoritative | Intermittent |
| 6 | Federal Reserve Board | Credit & Liquidity | Credit conditions, liquidity facilities | 1 — Primary/Authoritative | Mixed |
| 7 | Federal Reserve Board | Enforcement Actions | Bank enforcement orders | 1 — Primary/Authoritative | Intermittent |
| 8 | Federal Reserve — H.8 | H.8 Data Release | Weekly bank assets/liabilities | 1 — Primary/Authoritative | Weekly |
| 9 | FDIC | Press Releases | Bank supervision, deposit insurance | 1 — Primary/Authoritative | Intermittent |
| 10 | OCC — News Releases | Press Releases | National bank supervision | 1 — Primary/Authoritative | Intermittent |
| 11 | OCC — Bulletins | Regulatory Bulletins | Bank regulatory guidance | 1 — Primary/Authoritative | Intermittent |
| 12 | SEC — Press Releases | Press Releases | Securities regulation, enforcement | 1 — Primary/Authoritative | Healthy |
| 13 | SEC — Rulemaking | Proposed + Final Rules | Securities rulemaking activity | 1 — Primary/Authoritative | Event-driven |
| 14 | SEC — Investor Alerts | Investor Education | Investor protection notices | 1 — Primary/Authoritative | Mixed |
| 15 | SEC — Speeches | Commissioner Speeches | SEC leadership speeches | 1 — Primary/Authoritative | Event-driven |
| 16 | FHFA | News Releases | Housing finance regulation (Fannie/Freddie) | 1 — Primary/Authoritative | Intermittent |
| 17 | HUD | Press Releases | Housing and urban development policy | 1 — Primary/Authoritative | Intermittent |
| 18 | CFPB | Newsroom | Consumer financial protection | 1 — Primary/Authoritative | Empty frequently |
| 19 | Treasury | Press Releases | Fiscal policy, financial stability | 1 — Primary/Authoritative | Empty frequently |

**Sector coverage:** Federal policy, banking regulation, housing finance
**Known gaps within tier:** No BLS (Bureau of Labor Statistics) data releases; no BEA (Bureau of Economic Analysis) GDP/economic data; no Census Bureau construction/housing data; no CBO (Congressional Budget Office) reports; no FERC (Federal Energy Regulatory Commission) orders or announcements — critical for energy sector; no DOE (Department of Energy) announcements; no EPA environmental regulatory actions

---

## 7. Supplementary Sources

### NewsAPI

18 keyword-based queries to NewsAPI.org (free tier, 100 requests/day):

| Query Theme | Description |
|-------------|-------------|
| CRE transactions | "commercial real estate" + "sale" / "acquisition" / "deal" |
| NYC development | "New York" + "real estate" + "development" / "construction" |
| CRE finance | "commercial mortgage" / "CMBS" / "CRE lending" |
| Multifamily | "multifamily" + "acquisition" / "development" / "sale" |
| Industrial CRE | "industrial real estate" + "warehouse" / "logistics" |
| Office market | "office market" + "leasing" / "vacancy" |
| Retail CRE | "retail real estate" + "shopping center" |
| Hotel CRE | "hotel" + "acquisition" / "sale" |
| CRE capital markets | "real estate" + "fund" / "investment" / "REIT" |
| CRE distress | "distressed" + "commercial real estate" / "foreclosure" |
| CRE policy | "zoning" + "real estate" / "property tax" / "rent control" |
| Fed + real estate | "Federal Reserve" + "real estate" / "commercial property" |

**Performance:** Returned 0 results on July 26 run. Generally low yield due to free tier limitations. Supplementary only — no editorial dependency.

### SEC EDGAR RSS

Real-time SEC filing notifications via EDGAR RSS feed. Captures:
- 8-K (material events — acquisitions, dispositions, financings)
- 10-K / 10-Q (annual/quarterly reports)
- S-11 (REIT registration statements)
- SC 13D / 13G (beneficial ownership — activist and institutional positions)
- Form D (private placement notices — real estate fund offerings)

**Performance:** Low signal-to-noise ratio on individual filings, but valuable for REIT and fund-level intelligence. Not yet integrated into the main triage-to-score pipeline.

### Discovery Watchlist

A newly created configuration file at `.editorial-state/discovery-watchlist.json` containing:
- 18 NewsAPI queries (mirroring the production queries)
- SEC EDGAR RSS configuration
- Entity watchlist (companies, REITs, funds to monitor)
- Topic watchlist (themes to proactively search for)

**Status:** Not yet operational in production runs. Created as infrastructure for future multi-sector discovery.

---

## 8. Source Health Summary

### Aggregate Health

| Metric | Value |
|--------|-------|
| Total feeds configured | ~103 |
| Feeds returning content (last run) | ~55 (53%) |
| Feeds returning empty (last run) | 48 (47%) |
| Feeds with 3+ consecutive empty runs | ~8-12 |
| Healthiest feeds | GlobeSt, Connect CRE, Commercial Observer, Construction Dive, HousingWire, Bloomberg RE |
| Unhealthiest feeds | The Real Deal (3 consecutive empty), Student Housing Business, SIOR, Appraisal Institute, CFPB, Treasury, Patch NYC, Queens Post, Brooklyn Paper |

### Feed Failure Patterns

| Pattern | Count | Examples | Likely Cause |
|---------|-------|----------|-------------|
| 3+ consecutive empty runs | ~8 | The Real Deal, SIOR, Appraisal Institute | Feed URL changed, paywall gate, site restructure |
| Intermittent empty (some runs OK) | ~25 | NAREIT, NMHC, Fannie Mae, SEC testimony feeds | Low-frequency sources (weekly/monthly), event-driven content |
| Always healthy | ~15 | GlobeSt, Connect CRE, Bloomberg RE, Reuters, Crain's NY, Construction Dive | High-frequency trade publications, major newswires |
| Free tier / paywall degraded | ~10 | WSJ, NYT, Bloomberg Businessweek, CoStar | Paywall blocking feedparser/full-text extraction |
| Infrequent source (expected) | ~5 | Fed testimony, SEC speeches, FHFA | Fed speeches and SEC actions are event-driven by nature |

---

## 9. Critical Gaps by Mandated Sector

### Gap Statement

The current source universe was built for one purpose: covering commercial real estate capital markets with a New York City emphasis. It performs adequately for that purpose. But the system mandate now requires coverage of 7 sectors, and the source universe covers only 1.

The gaps are most acute for sectors where the pipeline has **zero dedicated sources:**

| Sector Gap | Severity | Feeds Today | Feeds Needed | Primary Missing Sources |
|------------|----------|-------------|--------------|------------------------|
| Private Equity | **Critical** | 1-2 incidental | 20-30 | PE Hub, Buyouts, PitchBook News, PEI, WSJ Pro PE, Secondaries Investor, affiliate titles, Preqin, Dealogic |
| Data Centers | **Critical** | 0 | 15-20 | Data Center Dynamics, Data Center Frontier, DatacenterHawk, Data Center Knowledge, hyperscaler press release pages (AWS, Azure, GCP), utility interconnection filings |
| Energy | **Critical** | 0 | 25-30 | Utility Dive, E&E News, S&P Global Platts, RTO/ISO market announcements (PJM, ERCOT, CAISO, MISO, NYISO, ISO-NE, SPP), EIA data releases, FERC orders, DOE announcements |
| Local Government | **Critical** | 0 | 30-50 | Major city planning department RSS feeds, city council legislative trackers, state-level development agency announcements, county property records portals, municipal bond offering statements |
| Banking/Credit | **High** | 5-10 partial | 20-25 | Bank Director, S&P Global Market Intelligence, Fed direct supervisory releases (already partially covered), OCC/FDIC enforcement action databases, bank call report data, ratings agency actions (Moody's, S&P, Fitch for banks) |
| Fed/Macro | **Moderate** | 10-15 | 15-20 | BLS data releases (Employment Situation, CPI, PPI), BEA (GDP, personal income), Census Bureau (construction spending, housing starts, building permits), CBO reports, Treasury auction results, OFR (Office of Financial Research) |
| Commercial Real Estate | **Low** | ~65 | 80-100 | Some specialty subsectors missing (life sciences, self-storage, manufactured housing, data center REITs — though these cross over to DC sector); more regional depth needed |

### Source Diversity Problem

Beyond sector gaps, the source universe has a diversity problem:

- **95% trade press and aggregators:** Almost all news enters through secondary sources (journalists writing about events) rather than primary sources (the events themselves — SEC filings, court records, agency announcements, company press releases).
- **No company-level monitoring:** Zero feeds from individual company press rooms, investor relations pages, or regulatory filing monitors beyond SEC EDGAR.
- **No structured data feeds:** No API-based structured data ingestion (no FRED for economic data, no EIA API for energy data, no Census API for construction data).
- **No search-based discovery layer:** Beyond the free tier of NewsAPI (100 requests/day), there is no programmatic search capability for surfacing stories not in RSS feeds. Google News API, Bing News Search, or commercial news APIs would be required for adequate coverage.

---

## 10. Implications for the Overhaul

The source universe requires a near-total rebuild for 6 of 7 mandated sectors. This is the single largest deliverable in the overhaul — larger than the classification system redesign, larger than the scoring framework update, and larger than the publishing infrastructure changes.

**Estimated new feeds needed:** ~150-200 additional RSS/API sources beyond the current ~103.

**Priority order for source acquisition:**
1. **Tier 1 (Week 1-2):** Private Equity + Data Centers — these sectors have zero coverage today and the shortest path to initial capability (PE has established trade press; DCs have 3-4 established publications)
2. **Tier 2 (Week 3-4):** Energy + Banking/Credit — energy requires more sources (utility and grid coverage is fragmented); banking needs more systematic regulatory coverage
3. **Tier 3 (Week 5-6):** Local Government — the hardest sector, requiring bespoke scraping for municipal sources with no standardized RSS presence; likely needs a hybrid of RSS, API, and web scraping
4. **Tier 4 (Week 7-8):** Fed/Macro gap fill + CRE gap fill — lower urgency since existing coverage is partially adequate for these sectors

**Source redundancy requirement:** Each sector should have at least 3 independent, non-overlapping source families to enable cross-source corroboration (the current system's event clustering depends on multiple sources covering the same story — this is essential infrastructure that must carry forward).

**Source health monitoring:** The 46% feed failure rate must be addressed either through better feed management (automated health checks with alerting, feed URL rotation, fallback scraping) or through aggressive source pruning (dropping consistently dead feeds to reduce noise in the gather phase).
