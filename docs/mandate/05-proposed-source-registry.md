# Proposed Source Registry: Light Tower Group 7-Sector Intelligence Engine

**Document:** 05-Proposed-Source-Registry
**Date:** July 30, 2026
**Status:** Design Specification — Multi-Sector Source Universe

---

## Overview

This document defines the complete source registry for the 7-sector institutional news intelligence engine. The current system operates with approximately 115 RSS feeds covering only Commercial Real Estate. The proposed registry expands to approximately 350 feeds and API endpoints spanning all seven mandated sectors.

**Sectors:** Commercial Real Estate (CRE), Private Equity (PE), Data Centers (DC), Energy (ENG), Banking/Credit (BNK), Federal Reserve/Macro (MAC), Local Government (LOC)

**Verification Status Legend:**
- `[VERIFIED]` — RSS URL confirmed active and producing content
- `[NEEDS VERIFICATION]` — URL format likely correct but not confirmed live
- `[INFERRED]` — Standard feed pattern assumed, requires testing
- `[KEPT]` — Existing feed from current inventory, verified working in production

---

## Layer 1: Federal and Authoritative Sources

These are primary-source, authoritative feeds from federal agencies, regulatory bodies, and government data providers. They carry the highest source quality weight (tier 0) and are the foundation for evidence-based editorial.

### Existing Federal Feeds (Keep All 15)

| # | Agency | Feed | Coverage | Status |
|---|--------|------|----------|--------|
| 1 | Federal Reserve Board | Press Releases | Monetary policy, regulatory actions | [KEPT] |
| 2 | Federal Reserve Board | Monetary Policy | FOMC statements, minutes | [KEPT] |
| 3 | Federal Reserve Board | Banking Regulation | Supervisory actions, rulemaking | [KEPT] |
| 4 | Federal Reserve Board | Enforcement Actions | Bank enforcement orders | [KEPT] |
| 5 | Federal Reserve Board | Speeches | Governor and staff speeches | [KEPT] |
| 6 | Federal Reserve Board | Testimony | Congressional testimony | [KEPT] |
| 7 | Federal Reserve Board | Credit & Liquidity | Credit conditions, liquidity facilities | [KEPT] |
| 8 | Federal Reserve Board | H.8 Data Release | Weekly bank assets/liabilities | [KEPT] |
| 9 | FDIC | Press Releases | Bank supervision, deposit insurance | [KEPT] |
| 10 | OCC | News Releases | National bank supervision | [KEPT] |
| 11 | OCC | Bulletins | Bank regulatory guidance | [KEPT] |
| 12 | SEC | Press Releases | Securities regulation, enforcement | [KEPT] |
| 13 | SEC | Speeches & Statements | SEC leadership speeches | [KEPT] |
| 14 | SEC | Testimony | Congressional testimony | [KEPT] |
| 15 | SEC | Litigation Releases | Enforcement litigation announcements | [KEPT] |
| 16 | FHFA | News Releases | Housing finance regulation | [KEPT] — currently in supplementary list |
| 17 | HUD | Press Releases | Housing and urban development policy | [KEPT] — currently in supplementary list |
| 18 | CFPB | Newsroom | Consumer financial protection | [KEPT] — currently in supplementary list |
| 19 | Treasury | Press Releases | Fiscal policy, financial stability | [KEPT] — currently in supplementary list |

### New Federal Feeds

| # | Agency | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| 20 | Bureau of Labor Statistics (BLS) | `https://www.bls.gov/feed/bls_latest.rss` | Employment Situation, CPI, PPI, JOLTS, productivity | [VERIFIED] |
| 21 | BLS — Regional | `https://www.bls.gov/regions/` | Regional employment, wage data by MSA | [NEEDS VERIFICATION] — may require per-region feeds |
| 22 | Bureau of Economic Analysis (BEA) | `https://www.bea.gov/rss` | GDP, personal income, trade data, industry accounts | [NEEDS VERIFICATION] |
| 23 | Census Bureau — Economic Indicators | `https://www.census.gov/economic-indicators/rss` | Construction spending, housing starts, building permits, new home sales, manufacturing | [VERIFIED] |
| 24 | Census Bureau — Construction | `https://www.census.gov/construction/nrc/rss.html` | Monthly construction put-in-place, residential/nonresidential | [NEEDS VERIFICATION] |
| 25 | FERC | `https://www.ferc.gov/news-events/rss-feeds` | Orders, notices, rulemakings, market oversight | [NEEDS VERIFICATION] |
| 26 | Department of Energy (DOE) | `https://www.energy.gov/rss/press-releases` | Energy policy, funding, research announcements | [VERIFIED] |
| 27 | Energy Information Administration (EIA) | `https://www.eia.gov/rss/todayinenergy.xml` | Today in Energy analysis | [VERIFIED] |
| 28 | EIA — This Week in Petroleum | `https://www.eia.gov/rss/twip.xml` | Weekly petroleum, natural gas data | [VERIFIED] |
| 29 | EIA — Electricity | `https://www.eia.gov/rss/electricity.xml` | Electricity generation, capacity, prices | [VERIFIED] |
| 30 | EIA — Natural Gas | `https://www.eia.gov/rss/naturalgas.xml` | Natural gas storage, production, prices | [VERIFIED] |
| 31 | EIA — Renewables | `https://www.eia.gov/rss/renewable.xml` | Solar, wind, hydro generation data | [NEEDS VERIFICATION] |
| 32 | Congressional Budget Office (CBO) | `https://www.cbo.gov/publications/rss.xml` | Budget projections, economic forecasts, cost estimates | [VERIFIED] |
| 33 | Government Accountability Office (GAO) | `https://www.gao.gov/feed.xml` | Federal program audits, investigations, reports | [VERIFIED] |
| 34 | Treasury Direct | `https://www.treasurydirect.gov/rss/auctions.xml` | Treasury auction announcements, results | [NEEDS VERIFICATION] |
| 35 | EPA — News Releases | `https://www.epa.gov/newsreleases/feed` | Environmental regulatory actions, permits | [VERIFIED] |
| 36 | IRS — Guidance | `https://www.irs.gov/newsroom/rss` | Tax guidance, opportunity zone updates, LIHTC | [VERIFIED] |
| 37 | USDA — Rural Development | `https://www.rd.usda.gov/newsroom/rss-feeds` | Rural housing, utilities, infrastructure programs | [NEEDS VERIFICATION] |
| 38 | USACE — Regulatory | `https://www.usace.army.mil/Media/News/` | Section 404 permits, wetlands, water infrastructure | [NEEDS VERIFICATION] — may require scraping |

### State Utility Commissions (for Energy + Local Government)

| # | Commission | Feed URL / Source | Coverage | Status |
|---|-----------|-------------------|----------|--------|
| 39 | California Public Utilities Commission (CPUC) | `https://www.cpuc.ca.gov/news/` | Energy, water, telecom rate cases in CA | [NEEDS VERIFICATION] — may require scraping |
| 40 | Texas Public Utility Commission (PUCT) | `https://www.puc.texas.gov/news/` | ERCOT market regulation, rate cases | [NEEDS VERIFICATION] |
| 41 | New York Public Service Commission (NYPSC) | `https://www.dps.ny.gov/` | NY energy, utility rate decisions | [NEEDS VERIFICATION] — may require scraping |
| 42 | Florida Public Service Commission | `https://www.floridapsc.com/` | FL energy, utility regulation | [NEEDS VERIFICATION] |
| 43 | Illinois Commerce Commission | `https://www.icc.illinois.gov/news/` | IL energy, telecom, transportation | [NEEDS VERIFICATION] |
| 44 | PJM Interconnection | `https://www.pjm.com/about-pjm/newsroom` | Largest RTO/ISO market announcements | [NEEDS VERIFICATION] — may require parsing |
| 45 | ERCOT | `https://www.ercot.com/news` | Texas grid market notices | [NEEDS VERIFICATION] |
| 46 | CAISO | `https://www.caiso.com/about/Pages/News/Default.aspx` | California ISO market notices | [NEEDS VERIFICATION] |
| 47 | MISO | `https://www.misoenergy.org/about/newsroom/` | Midwest ISO market announcements | [NEEDS VERIFICATION] |
| 48 | NYISO | `https://www.nyiso.com/news` | New York ISO market notices | [NEEDS VERIFICATION] |
| 49 | ISO New England | `https://www.iso-ne.com/about/news/` | New England grid updates | [NEEDS VERIFICATION] |

**Layer 1 Summary:** 49 sources (15 existing + 34 new). Coverage of federal monetary, fiscal, regulatory, economic data, and energy grid operational announcements. Strong primary-source coverage for Fed/Macro, Banking, and Energy sectors.

---

## Layer 2: Industry Publications by Sector

### Sector: Commercial Real Estate (CRE)

The existing CRE feed inventory is the system's strongest asset. The following consolidates and extends the current ~65 CRE feeds to approximately 85 feeds.

#### Core CRE Trade Publications (Existing + Expanded)

| # | Source | Feed URL | Coverage | Status |
|---|--------|----------|----------|--------|
| CRE-01 | The Real Deal (NYC) | `https://therealdeal.com/new-york/feed/` | NYC CRE deals, development, policy | [KEPT] |
| CRE-02 | The Real Deal (National) | `https://therealdeal.com/feed/` | National CRE trends, capital markets | [KEPT] |
| CRE-03 | The Real Deal (Los Angeles) | `https://therealdeal.com/la/feed/` | LA CRE market | [NEEDS VERIFICATION] |
| CRE-04 | The Real Deal (Chicago) | `https://therealdeal.com/chicago/feed/` | Chicago CRE market | [NEEDS VERIFICATION] |
| CRE-05 | The Real Deal (South Florida) | `https://therealdeal.com/miami/feed/` | Miami/South Florida CRE | [NEEDS VERIFICATION] |
| CRE-06 | The Real Deal (Texas) | `https://therealdeal.com/texas/feed/` | Texas CRE markets | [NEEDS VERIFICATION] |
| CRE-07 | Commercial Observer | `https://commercialobserver.com/feed/` | NYC CRE, finance, development | [KEPT] |
| CRE-08 | Bisnow National | `https://www.bisnow.com/national/rss` | National CRE deal coverage | [KEPT] |
| CRE-09 | Bisnow New York | `https://www.bisnow.com/new-york/rss` | NYC CRE | [KEPT] |
| CRE-10 | Bisnow Los Angeles | `https://www.bisnow.com/los-angeles/rss` | LA CRE | [KEPT] |
| CRE-11 | Bisnow Chicago | `https://www.bisnow.com/chicago/rss` | Chicago CRE | [KEPT] |
| CRE-12 | Bisnow Washington DC | `https://www.bisnow.com/washington-dc/rss` | DC metro CRE | [KEPT] |
| CRE-13 | Bisnow Dallas-Fort Worth | `https://www.bisnow.com/dallas-fort-worth/rss` | DFW CRE | [KEPT] |
| CRE-14 | Bisnow Boston | `https://www.bisnow.com/boston/rss` | Boston CRE | [KEPT] |
| CRE-15 | Bisnow Atlanta | `https://www.bisnow.com/atlanta/rss` | Atlanta CRE | [KEPT] |
| CRE-16 | Bisnow Seattle | `https://www.bisnow.com/seattle/rss` | Seattle CRE | [KEPT] |
| CRE-17 | Bisnow Denver | `https://www.bisnow.com/denver/rss` | Denver CRE | [KEPT] |
| CRE-18 | Bisnow Houston | `https://www.bisnow.com/houston/rss` | Houston CRE | [KEPT] |
| CRE-19 | Bisnow San Francisco | `https://www.bisnow.com/san-francisco/rss` | SF Bay Area CRE | [KEPT] |
| CRE-20 | Bisnow Philadelphia | `https://www.bisnow.com/philadelphia/rss` | Philadelphia CRE | [KEPT] |
| CRE-21 | Bisnow Phoenix | `https://www.bisnow.com/phoenix/rss` | Phoenix CRE | [NEEDS VERIFICATION] |
| CRE-22 | GlobeSt | `https://www.globest.com/rss/` | National CRE transactions, trends | [KEPT] |
| CRE-23 | Connect CRE | `https://www.connect.media/feed/` | National CRE deal coverage | [KEPT] |
| CRE-24 | Propmodo | `https://propmodo.com/feed/` | CRE technology, innovation | [KEPT] |
| CRE-25 | National Real Estate Investor (NREI) | `https://www.nreionline.com/rss/all` | Institutional CRE investment | [KEPT] |
| CRE-26 | Multi-Housing News | `https://www.multihousingnews.com/feed/` | Multifamily sector | [KEPT] |
| CRE-27 | CP Executive | `https://www.cpexecutive.com/feed/` | Commercial property executive news | [KEPT] |
| CRE-28 | HousingWire | `https://www.housingwire.com/feed/` | Housing finance, mortgage market | [KEPT] |
| CRE-29 | Construction Dive | `https://www.constructiondive.com/feeds/news/` | Construction industry news | [KEPT] |
| CRE-30 | Urban Land Institute (ULI) | `https://urbanland.uli.org/feed/` | Land use, urban planning, CRE research | [KEPT] |
| CRE-31 | Affordable Housing Finance | `https://www.housingfinance.com/feed/` | Affordable housing development, LIHTC | [KEPT] |
| CRE-32 | Building Design + Construction (BD+C) | `https://www.bdcnetwork.com/rss.xml` | Architecture, engineering, construction | [KEPT] |
| CRE-33 | Shopping Center Business | `https://www.shoppingcenterbusiness.com/feed/` | Retail real estate sector | [KEPT] |
| CRE-34 | RE Business Online | `https://www.rebusinessonline.com/feed/` | National CRE transactions, development | [KEPT] |
| CRE-35 | CoStar News | `https://www.costar.com/rss/news` | National CRE data + news (paywalled) | [KEPT] |
| CRE-36 | Senior Housing News | `https://seniorhousingnews.com/feed/` | Seniors housing sector | [KEPT] — currently in Tier 2 |
| CRE-37 | Student Housing Business | `https://www.studenthousingbusiness.com/feed/` | Student housing sector | [KEPT] — currently intermittent |
| CRE-38 | Multifamily Executive | `https://www.multifamilyexecutive.com/rss/` | Multifamily development + management | [KEPT] |
| CRE-39 | Commercial Property Executive | `https://www.commercialsearch.com/news/rss` | Institutional CRE investment | [KEPT] |
| CRE-40 | RE Journals | `https://rejournals.com/feed/` | Regional CRE markets (Midwest focus) | [KEPT] |
| CRE-41 | New York YIMBY | `https://newyorkyimby.com/feed` | NYC development pipeline, new construction | [KEPT] |
| CRE-42 | Real Estate Weekly | `https://rew-online.com/feed/` | NYC CRE transactions, people moves | [KEPT] |
| CRE-43 | Crain's New York Business | `https://www.crainsnewyork.com/real-estate/rss` | NYC business + CRE | [KEPT] |
| CRE-44 | Observer Real Estate | `https://observer.com/real-estate/feed/` | NYC luxury/high-end CRE | [KEPT] |
| CRE-45 | 6sqft | `https://www.6sqft.com/feed/` | NYC real estate, architecture, urbanism | [KEPT] |
| CRE-46 | CityLand NYC | `https://www.citylandnyc.org/feed/` | NYC land use, zoning, ULURP | [KEPT] |
| CRE-47 | Curbed NY | `https://www.curbed.com/rss/index.xml` | NYC urbanism, development, architecture | [KEPT] |

#### CRE Research, Data, and Brokerage

| # | Source | Feed URL | Coverage | Status |
|---|--------|----------|----------|--------|
| CRE-48 | Colliers Insights | `https://www.colliers.com/en-us/news/rss.xml` | CRE brokerage research, market reports | [KEPT] |
| CRE-49 | Marcus & Millichap | `https://www.marcusmillichap.com/rss.xml` | Investment sales, market research | [KEPT] |
| CRE-50 | Newmark Research | `https://www.nmrk.com/rss/` | Capital markets, leasing research | [KEPT] |
| CRE-51 | VTS Blog | `https://www.vts.com/blog/rss.xml` | Leasing technology, office market data | [KEPT] |
| CRE-52 | NCREIF | `https://www.ncreif.org/rss.xml` | Institutional CRE performance indices | [KEPT] |
| CRE-53 | Green Street Advisors | `https://www.greenstreetadvisors.com/rss.xml` | REIT and property sector research | [KEPT] |
| CRE-54 | ATTOM Data | `https://www.attomdata.com/feed/` | Property data, housing market trends | [KEPT] |
| CRE-55 | NAREIT | `https://www.nareit.com/rss.xml` | REIT industry news and data | [KEPT] |
| CRE-56 | National Multifamily Housing Council (NMHC) | `https://www.nmhc.org/feed/` | Multifamily policy + research | [KEPT] |
| CRE-57 | Institutional Real Estate, Inc. (IREI) | `https://irei.com/news/feed/` | Institutional CRE investment | [KEPT] |
| CRE-58 | RealPage | `https://www.realpage.com/news/feed/` | Multifamily data, analytics | [KEPT] |
| CRE-59 | Yardi Matrix | `https://www.yardi.com/blog/rss/` | CRE data and market reports | [KEPT] |
| CRE-60 | National Association of Realtors (NAR) | `https://www.nar.realtor/news/rss.xml` | Residential + commercial data | [KEPT] |
| CRE-61 | Fannie Mae Perspectives | `https://www.fanniemae.com/rss.xml` | Housing finance, economic research | [KEPT] |
| CRE-62 | Freddie Mac Perspectives | `https://www.freddiemac.com/rss.xml` | Housing finance, multifamily research | [KEPT] |
| CRE-63 | CRE Finance Council (CREFC) | `https://www.crefc.org/rss.xml` | CRE finance industry association | [KEPT] |
| CRE-64 | CCIM Institute | `https://www.ccim.com/news/rss/` | Commercial investment real estate | [KEPT] |
| CRE-65 | Mortgage Bankers Association (MBA) | `https://newslink.mba.org/feed/` | CRE + residential mortgage finance | [KEPT] |
| CRE-66 | Appraisal Institute | `https://www.appraisalinstitute.org/news/rss/` | Commercial real estate appraisal | [KEPT] |
| CRE-67 | Urban Institute | `https://www.urban.org/taxonomy/term/100/feed` | Housing, urban policy research | [KEPT] |
| CRE-68 | Lincoln Institute of Land Policy | `https://www.lincolninst.edu/rss/policy-and-research` | Land policy, property tax research | [KEPT] |
| CRE-69 | JLL Research | `https://www.us.jll.com/en/newsroom` | Brokerage capital markets research | [NEEDS VERIFICATION] — may need scraper |
| CRE-70 | CBRE Research | `https://www.cbre.com/insights` | Global CRE research, data centers coverage | [NEEDS VERIFICATION] — may need scraper |
| CRE-71 | Cushman & Wakefield Research | `https://www.cushmanwakefield.com/en/insights` | CRE market reports | [NEEDS VERIFICATION] |
| CRE-72 | Avison Young | `https://www.avisonyoung.com/insights` | CRE market intelligence | [NEEDS VERIFICATION] |
| CRE-73 | Transwestern | `https://transwestern.com/insights` | CRE research, market reports | [NEEDS VERIFICATION] |
| CRE-74 | Savills US | `https://www.savills.us/insight-and-opinion/` | Global/US CRE research | [NEEDS VERIFICATION] |

**CRE Sector Summary:** 74 sources (65 existing + 9 new/expansion). Broad coverage across asset classes, geographies, and data providers. Strongest source cluster in the registry.

---

### Sector: Private Equity (PE)

All new sources. The current system has only PERE News and IREI, both filtered as CRE-adjacent. This section adds 25 dedicated PE and private capital publications.

#### PE Trade and News Publications

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| PE-01 | PE Hub | `https://www.pehub.com/feed/` | Buyout news, fundraising, deal coverage | [NEEDS VERIFICATION] |
| PE-02 | Buyouts Insider | `https://www.buyoutsinsider.com/feed/` | PE deal coverage, fund closes, LP news | [NEEDS VERIFICATION] |
| PE-03 | PitchBook News | `https://pitchbook.com/news/feed` | Data-driven PE, VC, M&A coverage | [NEEDS VERIFICATION] |
| PE-04 | PEI — Private Equity International | `https://www.privateequityinternational.com/feed/` | Institutional PE, LP/GP relationships | [NEEDS VERIFICATION] |
| PE-05 | WSJ Pro Private Equity | `https://www.wsj.com/pro/privateequity` | Premium PE coverage (paywalled) | [NEEDS VERIFICATION] — limited by paywall |
| PE-06 | Secondaries Investor | `https://www.secondariesinvestor.com/feed/` | GP-led secondaries, continuation vehicles | [NEEDS VERIFICATION] |
| PE-07 | New Private Markets | `https://www.newprivatemarkets.com/feed/` | ESG, impact investing in private markets | [NEEDS VERIFICATION] |
| PE-08 | Infrastructure Investor | `https://www.infrastructureinvestor.com/feed/` | Infrastructure PE, energy, digital infra | [NEEDS VERIFICATION] |
| PE-09 | Agri Investor | `https://www.agriinvestor.com/feed/` | Agriculture, timberland PE | [NEEDS VERIFICATION] |
| PE-10 | Venture Capital Journal | `https://www.venturecapitaljournal.com/feed/` | VC fund news, LP commitments | [NEEDS VERIFICATION] |
| PE-11 | Mergers & Acquisitions | `https://www.themiddlemarket.com/rss/` | Middle-market M&A coverage | [NEEDS VERIFICATION] |
| PE-12 | The Deal | `https://www.thedeal.com/feed/` | Transactional coverage, bankruptcy, activism | [NEEDS VERIFICATION] |
| PE-13 | Axios Pro Rata | `https://www.axios.com/newsletters/axios-pro-rata` | Dan Primack's daily PE/VC newsletter | [NEEDS VERIFICATION] — newsletter, not RSS |
| PE-14 | Term Sheet (Fortune) | `https://fortune.com/newsletter/termsheet` | Daily PE/VC deal newsletter | [NEEDS VERIFICATION] — newsletter, not RSS |
| PE-15 | Institutional Investor | `https://www.institutionalinvestor.com/feed/` | Asset management, institutional allocation | [NEEDS VERIFICATION] |
| PE-16 | Sovereign Wealth Fund Institute | `https://www.swfinstitute.org/feed/` | SWF activity, direct investments | [NEEDS VERIFICATION] |

#### Private Credit and Debt

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| PE-17 | Private Debt Investor | `https://www.privatedebtinvestor.com/feed/` | Private credit, direct lending funds | [NEEDS VERIFICATION] |
| PE-18 | Creditflux | `https://www.creditflux.com/feed/` | CLOs, structured credit, private credit | [NEEDS VERIFICATION] |
| PE-19 | LevFin Insights | `https://www.levfininsights.com/feed` | Leveraged finance, institutional loan market | [NEEDS VERIFICATION] |
| PE-20 | Covenant Review | `https://www.covenantreview.com/rss` | Credit agreement analysis, cov-lite trends | [NEEDS VERIFICATION] |

#### PE Data and Research

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| PE-21 | Preqin Insights | `https://www.preqin.com/insights` | Alternatives data, fundraising trends | [NEEDS VERIFICATION] — API possible |
| PE-22 | Cambridge Associates | `https://www.cambridgeassociates.com/insights/` | Institutional investment research | [NEEDS VERIFICATION] |
| PE-23 | StepStone Group | `https://www.stepstonegroup.com/insights/` | PE/VC/real assets research | [NEEDS VERIFICATION] |
| PE-24 | Hamilton Lane | `https://www.hamiltonlane.com/en-us/insights` | Private markets data, research | [NEEDS VERIFICATION] |
| PE-25 | PERE News | `https://www.perenews.com/rss/` | Private equity real estate | [KEPT] — already in system |

**PE Sector Summary:** 25 sources. Covers buyouts, growth equity, venture capital, infrastructure, private credit, secondaries, and LP/GP dynamics. Note: several are newsletter-based rather than RSS, requiring custom ingestion adapters.

---

### Sector: Data Centers (DC)

All new sources. Zero data center coverage exists in the current system. This section adds 18 dedicated sources.

#### Data Center Trade Publications

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| DC-01 | Data Center Dynamics | `https://www.datacenterdynamics.com/rss/` | Global data center news, capacity, M&A | [VERIFIED] |
| DC-02 | Data Center Frontier | `https://datacenterfrontier.com/feed/` | Data center markets, power, design | [NEEDS VERIFICATION] |
| DC-03 | DatacenterHawk | `https://www.datacenterhawk.com/feed` | Data center market intelligence | [NEEDS VERIFICATION] |
| DC-04 | Data Center Knowledge | `https://www.datacenterknowledge.com/feed` | Data center industry, IT infrastructure | [VERIFIED] |
| DC-05 | Bisnow Data Centers | `https://www.bisnow.com/data-centers/rss` | Data center real estate, development | [NEEDS VERIFICATION] — may have dedicated feed |
| DC-06 | JLL Data Center Research | `https://www.us.jll.com/en/trends-and-insights` | Brokerage data center market reports | [NEEDS VERIFICATION] — requires scraping |
| DC-07 | CBRE Data Center Solutions | `https://www.cbre.com/insights` | CRE + data center investment reports | [NEEDS VERIFICATION] — requires scraping |
| DC-08 | Structure Research | `https://structureresearch.net/feed` | Data center, cloud, hosting markets | [NEEDS VERIFICATION] |
| DC-09 | Cloudscene | `https://cloudscene.com/news` | Data center and connectivity marketplace | [NEEDS VERIFICATION] |
| DC-10 | Uptime Institute | `https://uptimeinstitute.com/blog` | Data center reliability, standards, research | [NEEDS VERIFICATION] |
| DC-11 | AFCOM / Data Center World | `https://www.afcom.com/blog` | Data center operations, facilities | [NEEDS VERIFICATION] |

#### Hyperscaler Infrastructure News (Custom Scraping / Monitoring)

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| DC-12 | AWS Infrastructure | `https://aws.amazon.com/about-aws/global-infrastructure/` | New AWS region and AZ announcements | [NEEDS VERIFICATION] — requires custom scraper |
| DC-13 | Microsoft Azure Infrastructure | `https://azure.microsoft.com/en-us/blog/` | Azure region expansions, capacity investments | [NEEDS VERIFICATION] — blog with RSS |
| DC-14 | Google Cloud Infrastructure | `https://cloud.google.com/blog/products/infrastructure` | GCP region, subsea cable announcements | [NEEDS VERIFICATION] |
| DC-15 | Meta Infrastructure | `https://about.fb.com/news/` | Meta data center build announcements | [NEEDS VERIFICATION] |
| DC-16 | Apple Infrastructure | `https://www.apple.com/newsroom/rss/` | Apple data center, renewable energy commitments | [VERIFIED] — general press RSS |

#### Data Center REIT Investor Relations

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| DC-17 | Equinix — Investor Relations | `https://www.equinix.com/newsroom/` | Press releases on expansions, earnings | [NEEDS VERIFICATION] |
| DC-18 | Digital Realty — Investor Relations | `https://www.digitalrealty.com/news` | Press releases, market commentary | [NEEDS VERIFICATION] |

**DC Sector Summary:** 18 sources. Covers industry trade press, hyperscaler expansion announcements, brokerage research, and REIT investor relations. Requires custom scrapers for some hyperscaler and brokerage content.

---

### Sector: Energy (ENG)

All new sources. Zero energy sector coverage exists in the current system. This section adds 25 dedicated energy industry publications.

#### Energy Trade Publications and News

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| ENG-01 | Utility Dive | `https://www.utilitydive.com/feeds/news/` | Utility industry, regulation, rate cases | [VERIFIED] |
| ENG-02 | E&E News | `https://www.eenews.net/feed/` | Energy and environmental policy | [NEEDS VERIFICATION] — paywalled |
| ENG-03 | S&P Global Commodity Insights | `https://www.spglobal.com/commodityinsights/en/market-insights/latest-news` | Oil, gas, power, renewables markets | [NEEDS VERIFICATION] — likely API-required |
| ENG-04 | Power Magazine | `https://www.powermag.com/feed/` | Power generation, plant operations | [VERIFIED] |
| ENG-05 | Renewable Energy World | `https://www.renewableenergyworld.com/feed/` | Solar, wind, storage, renewable energy | [NEEDS VERIFICATION] |
| ENG-06 | Greentech Media / Wood Mackenzie | `https://www.greentechmedia.com/rss` | Clean energy analysis, markets | [NEEDS VERIFICATION] — merged into WoodMac |
| ENG-07 | Wood Mackenzie | `https://www.woodmac.com/news/` | Energy research, consulting | [NEEDS VERIFICATION] |
| ENG-08 | PV Magazine | `https://www.pv-magazine.com/feed/` | Solar photovoltaic industry | [VERIFIED] |
| ENG-09 | Windpower Monthly | `https://www.windpowermonthly.com/feed` | Wind energy industry | [NEEDS VERIFICATION] |
| ENG-10 | RTO Insider | `https://www.rtoinsider.com/feed` | RTO/ISO markets, FERC, grid policy | [NEEDS VERIFICATION] |
| ENG-11 | Natural Gas Intelligence | `https://www.naturalgasintel.com/feed/` | Natural gas market prices, fundamentals | [NEEDS VERIFICATION] |
| ENG-12 | Energy Storage News | `https://www.energy-storage.news/feed/` | Battery storage, grid-scale storage | [VERIFIED] |
| ENG-13 | Canary Media | `https://www.canarymedia.com/feed/` | Clean energy transition reporting, independent | [NEEDS VERIFICATION] |
| ENG-14 | Heatmap News | `https://heatmap.news/feed` | Climate, energy transformation | [NEEDS VERIFICATION] |
| ENG-15 | Climate Tech VC | `https://climatetechvc.substack.com/feed` | Climate tech investment, energy transition | [NEEDS VERIFICATION] |

#### Energy Industry Associations and Research

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| ENG-16 | American Public Power Association | `https://www.publicpower.org/feed/rss.xml` | Municipal utility industry | [NEEDS VERIFICATION] |
| ENG-17 | Edison Electric Institute | `https://www.eei.org/News/news/Pages/default.aspx` | Investor-owned utility industry | [NEEDS VERIFICATION] |
| ENG-18 | World Nuclear News | `https://www.world-nuclear-news.org/feed` | Nuclear power industry news | [VERIFIED] |
| ENG-19 | Solar Energy Industries Association (SEIA) | `https://www.seia.org/news/rss` | US solar industry policy, market data | [VERIFIED] |
| ENG-20 | American Clean Power Association | `https://cleanpower.org/news/` | Wind, solar, storage industry policy | [NEEDS VERIFICATION] |
| ENG-21 | Nuclear Energy Institute (NEI) | `https://www.nei.org/news/rss` | Nuclear power policy, operations | [NEEDS VERIFICATION] |

#### Energy Data and Analytics

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| ENG-22 | BloombergNEF (BNEF) | `https://about.bnef.com/blog/` | Clean energy, advanced transport, commodities | [NEEDS VERIFICATION] — free blog; full research paywalled |
| ENG-23 | Rystad Energy | `https://www.rystadenergy.com/news` | Upstream, renewables, energy transition | [NEEDS VERIFICATION] |
| ENG-24 | Lazard — Levelized Cost of Energy | `https://www.lazard.com/research-insights/` | Annual LCOE analysis | [NEEDS VERIFICATION] — research reports page |

#### Energy Utility Investor Relations

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| ENG-25 | NextEra Energy — Newsroom | `https://www.nexteraenergy.com/news.html` | Largest US utility/renewables developer | [NEEDS VERIFICATION] |

**ENG Sector Summary:** 25 sources. Covers utility and grid operations, renewable energy, oil and gas, nuclear, storage, and industry associations. RTO/ISO market notices and EIA/DOE feeds (in Layer 1) provide primary-source data.

---

### Sector: Banking/Credit (BNK)

Existing coverage is partial — American Banker, MBA Newslink, Trepp, CREFC, and mortgage publications exist but are filtered for CRE-only relevance. This section expands to 18 dedicated banking and credit sources for general coverage.

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| BNK-01 | American Banker | `https://www.americanbanker.com/feed` | Banking industry, regulation, fintech | [KEPT] |
| BNK-02 | Bank Director | `https://www.bankdirector.com/feed/` | Bank governance, strategy, M&A | [NEEDS VERIFICATION] |
| BNK-03 | S&P Global Market Intelligence | `https://www.spglobal.com/marketintelligence/en/news-insights` | Bank financials, M&A, regulatory filings | [NEEDS VERIFICATION] — likely API-required |
| BNK-04 | The Financial Brand | `https://thefinancialbrand.com/feed/` | Bank marketing, digital, strategy | [NEEDS VERIFICATION] |
| BNK-05 | Banking Dive | `https://www.bankingdive.com/feeds/news/` | Banking industry news | [VERIFIED] |
| BNK-06 | Credit Union Times | `https://www.cutimes.com/feed/` | Credit union industry | [NEEDS VERIFICATION] |
| BNK-07 | ABA Banking Journal | `https://bankingjournal.aba.com/feed/` | American Bankers Association publication | [NEEDS VERIFICATION] |
| BNK-08 | ICBA Independent Banker | `https://independentbanker.org/feed/` | Community banking industry | [NEEDS VERIFICATION] |
| BNK-09 | Risk.net | `https://www.risk.net/feed` | Credit risk, market risk, regulation | [NEEDS VERIFICATION] |
| BNK-10 | GlobalCapital | `https://www.globalcapital.com/feed` | Capital markets, securitization, covered bonds | [NEEDS VERIFICATION] |
| BNK-11 | Asset-Backed Alert | `https://www.abalert.com/feed` | ABS, structured finance market | [NEEDS VERIFICATION] |
| BNK-12 | Structured Finance Association (SFA) | `https://structuredfinance.org/news/` | Securitization industry | [NEEDS VERIFICATION] |
| BNK-13 | Fitch Ratings — Banks | `https://www.fitchratings.com/rss/banks` | Bank credit rating actions | [NEEDS VERIFICATION] |
| BNK-14 | Moody's — Banking | `https://www.moodys.com/rss/banking` | Bank credit research, ratings | [NEEDS VERIFICATION] |
| BNK-15 | S&P Global Ratings — Financial Institutions | `https://www.spglobal.com/ratings/en/sector/financial-institutions` | Bank rating actions | [NEEDS VERIFICATION] |
| BNK-16 | Knowledge@Wharton | `https://knowledge.wharton.upenn.edu/feed/` | Finance, banking, business research | [VERIFIED] |
| BNK-17 | Mortgage Bankers Association (MBA) | `https://newslink.mba.org/feed/` | CRE + residential mortgage finance | [KEPT] |
| BNK-18 | Trepp | `https://www.trepp.com/trepptalk/rss.xml` | CMBS data, CRE finance analytics | [KEPT] |

**BNK Sector Summary:** 18 sources (3 existing + 15 new). Covers banking regulation, credit ratings, structured finance, community banking, and credit union sectors. Layer 1 federal feeds (Fed, OCC, FDIC, SEC) provide primary regulatory news.

---

### Sector: Federal Reserve/Macro (MAC)

Existing coverage is strong (19 federal feeds). This section keeps all existing and adds 10 analytical publications and data aggregators to complement the primary-source Layer 1 feeds.

#### Keep All Existing Federal Feeds (See Layer 1)

All 19 existing federal regulatory feeds (Fed × 8, FDIC, OCC × 2, SEC × 4, FHFA, HUD, CFPB, Treasury) are retained. See Layer 1 for complete listing.

#### New Macro Analysis and Commentary (Layer 2 for this sector)

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| MAC-01 | Calculated Risk | `https://www.calculatedriskblog.com/feeds/posts/default` | Housing, employment, macro data analysis | [VERIFIED] — Bill McBride's blog |
| MAC-02 | Wolf Street | `https://wolfstreet.com/feed/` | Finance, economics, real estate data analysis | [VERIFIED] |
| MAC-03 | The Overshoot (Matt Klein) | `https://theovershoot.co/feed` | Macroeconomics, monetary policy, global finance | [NEEDS VERIFICATION] |
| MAC-04 | Apartment List Research | `https://www.apartmentlist.com/research/feed` | Rental market data, national rent index | [NEEDS VERIFICATION] |
| MAC-05 | Zillow Research | `https://www.zillow.com/research/feed/` | Housing market data, Zillow Home Value Index | [VERIFIED] |
| MAC-06 | Redfin News | `https://www.redfin.com/news/feed/` | Housing market data, real estate brokerage | [VERIFIED] |
| MAC-07 | Fed Guy (Joseph Wang) | `https://fedguy.com/feed/` | Fed operations, monetary plumbing, repo market | [NEEDS VERIFICATION] |
| MAC-08 | BIS (Bank for International Settlements) | `https://www.bis.org/press/rss.htm` | Global banking supervision, financial stability | [VERIFIED] |
| MAC-09 | IMF — Publications | `https://www.imf.org/en/News/RSS` | Global economic outlook, financial stability reports | [NEEDS VERIFICATION] |
| MAC-10 | Congressional Budget Office (CBO) | `https://www.cbo.gov/publications/rss.xml` | Also listed in Layer 1 | [VERIFIED] |

**MAC Sector Summary:** 29 sources (19 Layer 1 federal + 10 new analytical). Strongest primary-source coverage of any sector. Gaps filled from 04-gap-analysis: BLS, BEA, Census Bureau, CBO now included in Layer 1.

---

### Sector: Local Government (LOC)

All new sources. Zero local government coverage exists in the current system. This section adds 38 municipal-level sources across 13 priority MSAs plus state-level feeds for key jurisdictions.

#### New York City / New York State

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-01 | NYC.gov Press Releases | `https://www.nyc.gov/rss/press-office.xml` | Mayoral announcements, city policy | [NEEDS VERIFICATION] |
| LOC-02 | NYC Department of City Planning | `https://www.nyc.gov/site/planning/about/rss.page` | Zoning, land use, area plans, ULURP | [NEEDS VERIFICATION] |
| LOC-03 | NYC Department of Buildings | `https://www.nyc.gov/site/buildings/about/news.page` | Construction permits, code updates, violations | [NEEDS VERIFICATION] — may require scraper |
| LOC-04 | NYC Council | `https://council.nyc.gov/rss/` | Legislation, hearings, land use committee | [NEEDS VERIFICATION] |
| LOC-05 | NYC Comptroller | `https://comptroller.nyc.gov/newsroom/rss/` | Municipal finance, audits, pension investments | [NEEDS VERIFICATION] |
| LOC-06 | NYS Homes and Community Renewal | `https://hcr.ny.gov/rss.xml` | NY state housing finance, affordable housing | [NEEDS VERIFICATION] |

#### Los Angeles / California

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-07 | Los Angeles City Clerk — Council File Management | `https://cityclerk.lacity.org/lacityclerkconnect/` | Council legislation, land use, motions | [NEEDS VERIFICATION] — may require scraper |
| LOC-08 | Los Angeles City Planning | `https://planning.lacity.gov/news` | Zoning, community plans, development | [NEEDS VERIFICATION] |
| LOC-09 | California Department of Housing & Community Development | `https://www.hcd.ca.gov/news/rss` | State housing policy, RHNA, funding | [NEEDS VERIFICATION] |

#### Chicago / Illinois

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-10 | Chicago City Clerk — Legislative | `https://chicityclerkelms.chicago.gov/` | City council legislation, zoning | [NEEDS VERIFICATION] — requires scraper |
| LOC-11 | Chicago Department of Planning & Development | `https://www.chicago.gov/city/en/depts/dcd.html` | Development approvals, TIF districts | [NEEDS VERIFICATION] — requires scraper |

#### San Francisco / Bay Area

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-12 | San Francisco Planning Department | `https://sfplanning.org/rss.xml` | Zoning, environmental review, permits | [NEEDS VERIFICATION] |
| LOC-13 | San Francisco Board of Supervisors | `https://sfbos.org/rss` | Legislation, land use committee | [NEEDS VERIFICATION] |

#### Boston / Massachusetts

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-14 | Boston Planning & Development Agency | `https://www.bostonplans.org/news/rss` | Development review, planning studies | [NEEDS VERIFICATION] |
| LOC-15 | Massachusetts Housing Partnership | `https://www.mhp.net/news/rss` | Affordable housing finance, policy | [NEEDS VERIFICATION] |

#### Washington DC

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-16 | DC Office of Planning | `https://planning.dc.gov/rss.xml` | Comprehensive plan, zoning | [NEEDS VERIFICATION] |
| LOC-17 | DC Council | `https://dccouncil.gov/rss/` | Legislation, hearings, zoning commission | [NEEDS VERIFICATION] |

#### Miami-Dade / South Florida

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-18 | Miami-Dade County — Regulatory & Economic Resources | `https://www.miamidade.gov/global/news/rss.page` | Zoning, building permits, environmental | [NEEDS VERIFICATION] |
| LOC-19 | Miami-Dade County — Legislation | `https://www.miamidade.gov/global/government/rss.page` | County commission, ordinances | [NEEDS VERIFICATION] |

#### Dallas-Fort Worth / Texas

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-20 | Dallas City Council Agendas | `https://dallascityhall.com/Pages/default.aspx` | Council agenda, zoning cases | [NEEDS VERIFICATION] — requires scraper |
| LOC-21 | Texas Department of Housing & Community Affairs | `https://www.tdhca.state.tx.us/rss.xml` | LIHTC allocation, housing programs | [NEEDS VERIFICATION] |

#### Houston / Texas

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-22 | Houston Planning & Development Department | `https://www.houstontx.gov/planning/` | Development regulation, permits | [NEEDS VERIFICATION] — requires scraper |

#### Atlanta / Georgia

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-23 | Atlanta Department of City Planning | `https://www.atlantaga.gov/government/departments/city-planning` | Zoning, development, comprehensive plan | [NEEDS VERIFICATION] — requires scraper |
| LOC-24 | Georgia Department of Community Affairs | `https://www.dca.ga.gov/rss` | Housing, community development | [NEEDS VERIFICATION] |

#### Phoenix / Arizona

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-25 | Phoenix Planning & Development Department | `https://www.phoenix.gov/pdd` | Zoning, building permits, development plans | [NEEDS VERIFICATION] — requires scraper |
| LOC-26 | Arizona Department of Housing | `https://housing.az.gov/news/rss` | State housing policy, funding | [NEEDS VERIFICATION] |

#### Seattle / Washington

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-27 | Seattle Department of Construction & Inspections | `https://www.seattle.gov/sdci` | Building permits, land use, code | [NEEDS VERIFICATION] — requires scraper |
| LOC-28 | Washington State Department of Commerce | `https://www.commerce.wa.gov/news/` | Housing, infrastructure, growth management | [NEEDS VERIFICATION] |

#### Denver / Colorado

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-29 | Denver Community Planning & Development | `https://www.denvergov.org/Government/Agencies-Departments-Offices/Community-Planning-and-Development` | Zoning, building permits, neighborhood plans | [NEEDS VERIFICATION] — requires scraper |
| LOC-30 | Colorado Department of Local Affairs | `https://cdola.colorado.gov/rss.xml` | Housing, land use, local government | [NEEDS VERIFICATION] |

#### State Legislatures (Multi-State)

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| LOC-31 | California Legislative Information | `https://leginfo.legislature.ca.gov/` | CA bills, housing legislation, CEQA | [NEEDS VERIFICATION] — requires API/scraper |
| LOC-32 | Texas Legislature Online | `https://capitol.texas.gov/` | TX bills, property tax, PUC legislation | [NEEDS VERIFICATION] — requires scraper |
| LOC-33 | New York State Senate/Assembly | `https://www.nysenate.gov/rss` | NY legislation, 421-a, rent regulation | [NEEDS VERIFICATION] |
| LOC-34 | Florida Legislature | `https://www.flsenate.gov/RSS/` | FL legislation, housing, insurance | [NEEDS VERIFICATION] |
| LOC-35 | Illinois General Assembly | `https://www.ilga.gov/` | IL bills, property tax, development incentives | [NEEDS VERIFICATION] — requires scraper |
| LOC-36 | Virginia Legislative Information System | `https://lis.virginia.gov/` | VA bills, data center incentives, land use | [NEEDS VERIFICATION] — requires scraper |
| LOC-37 | New Jersey Legislature | `https://www.njleg.state.nj.us/` | NJ bills, PILOT programs, redevelopment | [NEEDS VERIFICATION] — requires scraper |
| LOC-38 | LegiScan (commercial service) | `https://legiscan.com/RSS` | All 50 states legislative tracking | [NEEDS VERIFICATION] — paid RSS service |

**LOC Sector Summary:** 38 sources. The hardest sector to automate — most municipal sources lack standardized RSS feeds and will require custom web scrapers, API integrations, or paid services (LegiScan for state legislatures). City-level sources should be prioritized for the top 10 MSAs defined in `TOP_MSA_GOVERNMENT_LANES`.

---

## Layer 3: National and Financial News

General-interest financial and business news publications that cover stories across all seven sectors. These feeds serve as supplementary discovery for stories that may not appear in trade publications.

| # | Source | Feed URL / Source | Coverage | Status |
|---|--------|-------------------|----------|--------|
| N-01 | Bloomberg Markets | `https://feeds.bloomberg.com/markets/news.rss` | Financial markets, deals, macro | [KEPT] |
| N-02 | Reuters Business | `https://feeds.reuters.com/reuters/businessNews` | Global business, breaking news | [KEPT] |
| N-03 | Reuters Deals | `https://feeds.reuters.com/reuters/USDealsNews` | M&A, PE, capital markets | [NEEDS VERIFICATION] |
| N-04 | Wall Street Journal | `https://feeds.a.dj.com/rss/RSSMarketsMain.xml` | Markets, deals, Fed, finance | [KEPT] |
| N-05 | WSJ Real Estate | `https://feeds.a.dj.com/rss/RSSWSJD.xml` | Real estate section | [NEEDS VERIFICATION] |
| N-06 | CNBC | `https://www.cnbc.com/id/100003114/device/rss/rss.html` | Top news, markets, deals | [VERIFIED] |
| N-07 | CNBC Real Estate | `https://www.cnbc.com/id/10000115/device/rss/rss.html` | Real estate news | [KEPT] |
| N-08 | Financial Times | `https://www.ft.com/?format=rss` | Global business, finance, macro | [NEEDS VERIFICATION] — paywalled |
| N-09 | Barron's | `https://feeds.barrons.com/wsj/barrons/feed` | Markets, investing, economy | [NEEDS VERIFICATION] |
| N-10 | MarketWatch Real Estate | `https://feeds.marketwatch.com/marketwatch/realestate/` | Real estate markets | [KEPT] |
| N-11 | MarketWatch Economy | `https://feeds.marketwatch.com/marketwatch/economy/` | Economic data, macro analysis | [NEEDS VERIFICATION] |
| N-12 | Fortune | `https://fortune.com/feed/` | Business, finance, tech | [NEEDS VERIFICATION] |
| N-13 | Forbes Real Estate | `https://www.forbes.com/real-estate/feed/` | Real estate coverage | [NEEDS VERIFICATION] |
| N-14 | Business Insider | `https://www.businessinsider.com/feed` | Business news, markets, tech | [NEEDS VERIFICATION] |
| N-15 | Axios | `https://www.axios.com/feeds/feed.rss` | Policy, business, technology | [KEPT] |
| N-16 | Axios Pro Rata | Newsletter only | Daily PE/VC deal newsletter | [NEEDS VERIFICATION] — requires email/API |
| N-17 | The Information | No public RSS | Premium tech/finance (paywalled) | [NEEDS VERIFICATION] — no RSS available |
| N-18 | Semafor | `https://www.semafor.com/feed` | Global business, policy, tech | [NEEDS VERIFICATION] |
| N-19 | Punchbowl News | No public RSS | DC policy, Congress, regulation | [NEEDS VERIFICATION] — premium, no RSS |
| N-20 | Bloomberg Businessweek | `https://feeds.bloomberg.com/businessweek/news.rss` | Long-form business journalism | [KEPT] |
| N-21 | New York Times — Business | `https://rss.nytimes.com/services/xml/rss/nyt/Business.xml` | National business news | [NEEDS VERIFICATION] — paywalled |

**Layer 3 Summary:** 21 sources (7 existing + 14 new). General financial press for cross-sector discovery. Note: Bloomberg Terminal content is not accessible via RSS and would require a separate Bloomberg API integration if available.

---

## Layer 4: Regional and Local News

City-specific business journals and major metro newspaper business sections providing geographic depth, primarily for CRE and Local Government sectors.

### American City Business Journals Network (BizJournals)

The BizJournals network (bizjournals.com) operates 40+ city-specific business journals. Many share the same RSS URL pattern. The following represent the priority 15 markets:

| # | Source | Feed URL | Coverage | Status |
|---|--------|----------|----------|--------|
| R-01 | San Francisco Business Times | `https://www.bizjournals.com/sanfrancisco/rss2.xml` | SF/Bay Area business, CRE | [KEPT] |
| R-02 | Los Angeles Business Journal (BizJournals) | `https://www.bizjournals.com/losangeles/rss2.xml` | LA business, CRE, development | [KEPT] |
| R-03 | Chicago (Crain's) | `https://www.chicagobusiness.com/rss/` | Chicago business, CRE | [NEEDS VERIFICATION] — separate from BizJournals |
| R-04 | Dallas Business Journal | `https://www.bizjournals.com/dallas/rss2.xml` | DFW business, CRE | [KEPT] |
| R-05 | Houston Business Journal | `https://www.bizjournals.com/houston/rss2.xml` | Houston business, CRE | [NEEDS VERIFICATION] |
| R-06 | Washington Business Journal | `https://www.bizjournals.com/washington/rss2.xml` | DC metro business, CRE, govcon | [NEEDS VERIFICATION] |
| R-07 | Phoenix Business Journal | `https://www.bizjournals.com/phoenix/rss2.xml` | Phoenix business, CRE | [KEPT] |
| R-08 | Boston Business Journal | `https://www.bizjournals.com/boston/rss2.xml` | Boston business, CRE, life sciences | [NEEDS VERIFICATION] |
| R-09 | Atlanta Business Chronicle | `https://www.bizjournals.com/atlanta/rss2.xml` | Atlanta business, CRE | [NEEDS VERIFICATION] |
| R-10 | South Florida Business Journal | `https://www.bizjournals.com/southflorida/rss2.xml` | Miami/FtL business, CRE | [NEEDS VERIFICATION] |
| R-11 | Denver Business Journal | `https://www.bizjournals.com/denver/rss2.xml` | Denver business, CRE | [NEEDS VERIFICATION] |
| R-12 | Seattle (Puget Sound Business Journal) | `https://www.bizjournals.com/seattle/rss2.xml` | Seattle business, CRE, tech | [NEEDS VERIFICATION] |
| R-13 | Philadelphia Business Journal | `https://www.bizjournals.com/philadelphia/rss2.xml` | Philadelphia business, CRE | [NEEDS VERIFICATION] |
| R-14 | Austin Business Journal | `https://www.bizjournals.com/austin/rss2.xml` | Austin business, CRE, tech | [NEEDS VERIFICATION] |
| R-15 | Charlotte Business Journal | `https://www.bizjournals.com/charlotte/rss2.xml` | Charlotte business, CRE, banking | [NEEDS VERIFICATION] |

### Major Metro Newspaper Business Sections

| # | Source | Feed URL | Coverage | Status |
|---|--------|----------|----------|--------|
| R-16 | Washington Post Business | `https://feeds.washingtonpost.com/rss/business` | DC business, economy, tech | [KEPT] |
| R-17 | Boston Globe Business | `https://feeds.bostonglobe.com/rss/business/` | Boston business, CRE | [KEPT] |
| R-18 | Houston Chronicle Business | `https://www.houstonchronicle.com/business/rss.xml` | Houston business, energy, real estate | [KEPT] |
| R-19 | Los Angeles Times Business | `https://www.latimes.com/business/rss.xml` | LA business, entertainment, CRE | [NEEDS VERIFICATION] |
| R-20 | Chicago Tribune Business | `https://www.chicagotribune.com/business/rss2.xml` | Chicago business, CRE | [KEPT] |
| R-21 | Denver Post Business | `https://www.denverpost.com/feed/` | Denver business, development | [KEPT] |
| R-22 | Seattle Times Business | `https://feeds.seattletimes.com/rss/seattle/business/` | Seattle business, tech, CRE | [KEPT] |
| R-23 | Miami Herald Business | `https://www.miamiherald.com/news/business/rss.xml` | Miami business, CRE, Latin America | [KEPT] |
| R-24 | Philadelphia Inquirer Business | `https://www.inquirer.com/business/rss/` | Philadelphia business, CRE, eds/meds | [KEPT] |
| R-25 | Atlanta Journal-Constitution Business | `https://www.ajc.com/news/business/rss/` | Atlanta business, CRE, logistics | [KEPT] |
| R-26 | Las Vegas Review-Journal Business | `https://www.reviewjournal.com/business/feed/` | Vegas business, hospitality, CRE | [NEEDS VERIFICATION] |
| R-27 | Nashville Business Journal area | `https://www.bizjournals.com/nashville/rss2.xml` | Nashville business, CRE, healthcare | [NEEDS VERIFICATION] |
| R-28 | Portland Business Journal | `https://www.bizjournals.com/portland/rss2.xml` | Portland business, CRE | [NEEDS VERIFICATION] |
| R-29 | San Diego Business Journal area | `https://www.bizjournals.com/sandiego/rss2.xml` | San Diego business, CRE, life sciences | [NEEDS VERIFICATION] |
| R-30 | Minneapolis/St. Paul Business Journal | `https://www.bizjournals.com/twincities/rss2.xml` | Twin Cities business, CRE | [NEEDS VERIFICATION] |

**Layer 4 Summary:** 30 sources (12 existing + 18 new). Broad geographic coverage across top US MSAs. The BizJournals network provides a standardized feed pattern (`bizjournals.com/{city}/rss2.xml`) for 40+ cities, enabling systematic expansion.

---

## Layer 5: Discovery APIs

Programmatic search and discovery services that supplement RSS feeds for surfacing stories not captured by direct feed monitoring. These are cost-tiered services.

| # | Service | URL | Coverage | Cost Tier | Notes |
|---|---------|-----|----------|-----------|-------|
| API-01 | NewsAPI.org | `https://newsapi.org/` | 80,000+ news sources, keyword search | **Free** (100 req/day), Developer ($449/mo), Business ($849/mo) | Currently in use on free tier. Limited to 100 requests/day, 100 results per request. |
| API-02 | GNews API | `https://gnews.io/` | Google News aggregation, 10 languages | **Free** (100 req/day), Basic ($50/mo), Pro ($100/mo), Enterprise ($400/mo) | Good coverage of regional and international news. 30-day article archive. |
| API-03 | EventRegistry | `https://eventregistry.org/` | Event-based news clustering, 150K+ articles/day | **Free** (1,000 req/day), Analyst ($50/mo), Enterprise (custom) | Best-in-class event clustering. Returns events, not just articles. Semantic search. Article archive to 2014. |
| API-04 | NewsCatcher | `https://www.newscatcherapi.com/` | 1M+ articles/day from 100K+ sources | **Free** (50 req/mo), v3 Small ($99/mo, 250K req), Enterprise ($399+/mo) | Strong at discovery across sources. Good for filling gaps in RSS coverage. |
| API-05 | Google News RSS (Unofficial) | `https://news.google.com/rss` | Google News topics and search | **Free** (unofficial) | Can construct topic-specific RSS URLs. No SLA. Used for company watchlist monitoring. |
| API-06 | Bing News Search API | `https://www.microsoft.com/en-us/bing/apis/bing-news-search-api` | Microsoft news aggregation | **Free** (1,000/mo), Tiered ($3+/1,000) | Part of Bing Search APIs. Good for programmatic search. |
| API-07 | SEC EDGAR RSS | `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=100&output=atom` | Real-time SEC filing notifications | **Free** | Already in use. Valuable for PE, REIT, and corporate filings across all sectors. |
| API-08 | FRED API (Federal Reserve Economic Data) | `https://fred.stlouisfed.org/docs/api/fred/` | 816,000+ US and international economic time series | **Free** (120 req/min) | Structured economic data — not news, but supports data points for editorial. |

**Layer 5 Summary:** 8 API services. Recommended priority: (1) Keep NewsAPI free tier + expand to 30+ sector-specific queries, (2) Add GNews API free tier for additional discovery, (3) Evaluate EventRegistry for event clustering (replaces in-house clustering at scale), (4) Use Google News RSS for company watchlist monitoring. Total API budget estimate: $0-500/month at free/low tiers.

---

## Layer 6: Company Watchlists

The following entities are monitored via Google News alerts, NewsAPI queries, and entity recognition patterns. These represent the most significant institutions within each sector — stories mentioning these entities receive a "Party Significance" scoring bonus and are more likely to pass the selection threshold.

### Commercial Real Estate (15 entities)

| # | Entity | Type | Monitoring Priority |
|---|--------|------|---------------------|
| W-CRE-01 | Blackstone | Alternative asset manager / largest CRE owner globally | Critical |
| W-CRE-02 | Brookfield Asset Management | Infrastructure, real estate, PE, credit | Critical |
| W-CRE-03 | Prologis | Largest industrial/logistics REIT globally | High |
| W-CRE-04 | Starwood Capital Group | CRE private equity and debt | High |
| W-CRE-05 | Related Companies | Major US developer (NYC, national) | High |
| W-CRE-06 | SL Green Realty | Largest NYC office landlord | Medium |
| W-CRE-07 | Vornado Realty Trust | Major NYC office/retail REIT | Medium |
| W-CRE-08 | Tishman Speyer | Global developer/operator | High |
| W-CRE-09 | CBRE Group | Largest CRE services firm | High |
| W-CRE-10 | JLL (Jones Lang LaSalle) | Global CRE services | High |
| W-CRE-11 | Cushman & Wakefield | Global CRE services | Medium |
| W-CRE-12 | Boston Properties | Class A office REIT (national) | Medium |
| W-CRE-13 | AvalonBay Communities | Major multifamily REIT | Medium |
| W-CRE-14 | Equity Residential | Major multifamily REIT | Medium |
| W-CRE-15 | Greystar | Largest US multifamily operator/developer | High |

### Private Equity (20 entities)

| # | Entity | Type | Monitoring Priority |
|---|--------|------|---------------------|
| W-PE-01 | Blackstone | PE, real estate, credit, infrastructure | Critical |
| W-PE-02 | Apollo Global Management | PE, credit, insurance, real assets | Critical |
| W-PE-03 | KKR | PE, infrastructure, credit, real estate | Critical |
| W-PE-04 | The Carlyle Group | PE, credit, infrastructure, real estate | Critical |
| W-PE-05 | TPG | PE, impact, real estate, growth | High |
| W-PE-06 | Bain Capital | PE, credit, life sciences, real estate | High |
| W-PE-07 | Ares Management | Credit, PE, real estate, infrastructure | High |
| W-PE-08 | Brookfield Asset Management | Infrastructure, PE, real estate, renewable power | Critical |
| W-PE-09 | Warburg Pincus | Growth PE, energy, financial services | High |
| W-PE-10 | Silver Lake | Technology PE | Medium |
| W-PE-11 | Thoma Bravo | Software PE | Medium |
| W-PE-12 | Vista Equity Partners | Enterprise software PE | Medium |
| W-PE-13 | Cerberus Capital Management | Distressed, PE, real estate | High |
| W-PE-14 | Fortress Investment Group | PE, credit, real estate, infrastructure | Medium |
| W-PE-15 | Oaktree Capital Management | Distressed debt, credit, contrarian | High |
| W-PE-16 | Blue Owl Capital | Direct lending, GP stakes, real estate | Medium |
| W-PE-17 | Sixth Street | Credit, PE, real estate, insurance | Medium |
| W-PE-18 | Hines | Global real estate investor/developer | High |
| W-PE-19 | Lone Star Funds | Distressed, non-performing loans | Medium |
| W-PE-20 | Bridge Investment Group | Real estate, credit, renewables | Medium |

### Data Centers (15 entities)

| # | Entity | Type | Monitoring Priority |
|---|--------|------|---------------------|
| W-DC-01 | Equinix | Largest data center REIT — global colocation | Critical |
| W-DC-02 | Digital Realty | Second-largest data center REIT — wholesale + colocation | Critical |
| W-DC-03 | American Tower | Tower + data center infrastructure (CoreSite) | High |
| W-DC-04 | CyrusOne | Wholesale data center REIT | High |
| W-DC-05 | QTS Realty Trust | Hyperscale + colocation data centers | High |
| W-DC-06 | Vantage Data Centers | Hyperscale campus developer | High |
| W-DC-07 | Stack Infrastructure | Hyperscale + wholesale data centers | High |
| W-DC-08 | DataBank | Enterprise colocation | Medium |
| W-DC-09 | Aligned Data Centers | Hyperscale, sustainable design | Medium |
| W-DC-10 | Compass Datacenters | Hyperscale campus developer | Medium |
| W-DC-11 | Amazon Web Services (AWS) | Largest hyperscaler | Critical |
| W-DC-12 | Microsoft Azure | Second-largest hyperscaler | Critical |
| W-DC-13 | Google Cloud | Third-largest hyperscaler | Critical |
| W-DC-14 | Meta | Social media data center infrastructure | High |
| W-DC-15 | NTT Data Centers | Global data center operator | Medium |

### Energy (15 entities)

| # | Entity | Type | Monitoring Priority |
|---|--------|------|---------------------|
| W-ENG-01 | NextEra Energy | Largest US utility + renewable developer | Critical |
| W-ENG-02 | Duke Energy | Major US utility (Southeast) | High |
| W-ENG-03 | Dominion Energy | Major US utility (Mid-Atlantic, data center hub) | Critical |
| W-ENG-04 | Southern Company | Major US utility (Southeast) | High |
| W-ENG-05 | Exelon | Major US utility (Mid-Atlantic, nuclear) | High |
| W-ENG-06 | Constellation Energy | Largest US nuclear operator | High |
| W-ENG-07 | Vistra Corp | Major power generator, retail electricity | High |
| W-ENG-08 | NRG Energy | Major power generator, retail | Medium |
| W-ENG-09 | Sempra Energy | CA/TX utility, LNG infrastructure | Medium |
| W-ENG-10 | AES Corporation | Global power generator, renewables, data center deals | High |
| W-ENG-11 | Enel North America | Renewables developer | Medium |
| W-ENG-12 | Invenergy | Largest private renewables developer | High |
| W-ENG-13 | Brookfield Renewable Partners | Global renewable power operator | High |
| W-ENG-14 | Pattern Energy | Renewables developer, SunZia transmission | High |
| W-ENG-15 | Energy Transfer | Pipeline, midstream infrastructure | Medium |

### Banking/Credit (15 entities)

| # | Entity | Type | Monitoring Priority |
|---|--------|------|---------------------|
| W-BNK-01 | JPMorgan Chase | Largest US bank | Critical |
| W-BNK-02 | Bank of America | Second-largest US bank | Critical |
| W-BNK-03 | Wells Fargo | Major US bank, CRE lender | Critical |
| W-BNK-04 | Citigroup | Global bank, institutional | High |
| W-BNK-05 | Goldman Sachs | Investment bank, PE, private credit | High |
| W-BNK-06 | Morgan Stanley | Investment bank, wealth, CRE lending | High |
| W-BNK-07 | PNC Financial Services | Super-regional bank | Medium |
| W-BNK-08 | Truist Financial | Super-regional bank (Southeast) | Medium |
| W-BNK-09 | U.S. Bancorp | Super-regional bank | Medium |
| W-BNK-10 | Capital One | Consumer + commercial bank | Medium |
| W-BNK-11 | M&T Bank | Regional bank, CRE lender | Medium |
| W-BNK-12 | KeyBank | Regional bank, CRE lender | Medium |
| W-BNK-13 | Regions Financial | Regional bank (Southeast) | Medium |
| W-BNK-14 | Fifth Third Bank | Regional bank (Midwest) | Medium |
| W-BNK-15 | New York Community Bancorp | CRE-focused regional bank | High |

### Federal Reserve/Macro (no separate entities beyond Fed itself)

The institutions captured in Layers 1-6 are the entities. Fed/Macro sector monitoring focuses on agencies (Fed, Treasury, FDIC, OCC, SEC, BLS, BEA, CBO) already defined in Layer 1, plus key macro commentators (Bill McBride, Wolf Richter, Matt Klein, Joseph Wang) defined in MAC sector feeds.

### Local Government (no separate entities beyond city/state agencies)

Monitoring focuses on the 38 municipal and state-level sources defined in Layer 2 (LOC sector). Entity extraction will flag when any of the 13 tracked MSAs or their constituent counties/cities appear in stories.

**Layer 6 Summary:** 80 monitored entities. Organized by sector with monitoring priority tiers. Used for: (a) Party Significance dimension scoring, (b) Google News Alert and NewsAPI query construction, (c) entity extraction during classification. Critical-tier entities should have dedicated Google News alert feeds checked in every gather cycle.

---

## Summary Source Inventory Table

| Sector | Layer 1 (Auth) | Layer 2 (Industry) | Layer 3 (National) | Layer 4 (Regional) | Layer 5 (API) | Layer 6 (Watchlist) | Total Feed Sources |
|--------|---------------|-------------------|--------------------|--------------------|---------------|---------------------|--------------------|
| CRE | 5 | 74 | 8 | 15 | — | 15 | 102 |
| PE | 1 | 25 | 8 | 0 | — | 20 | 34 |
| Data Centers | 0 | 18 | 5 | 0 | — | 15 | 23 |
| Energy | 4 | 25 | 5 | 5 | — | 15 | 39 |
| Banking/Credit | 8 | 18 | 5 | 0 | — | 15 | 31 |
| Fed/Macro | 12 | 10 | 8 | 0 | — | — | 30 |
| Local Government | 2 | 38 | 2 | 30 | — | — | 72 |
| **Total (Unique)** | **32** | **208** | **41** | **50** | **8** | **80** | **331** |

*Note: Layer 1 sources serve multiple sectors. "Unique" row counts each source once across all sectors. Layer 5 APIs are not assignable to a single sector. Layer 6 entities are monitoring targets, not feed sources. Total unique feed/API sources: approximately 340.*

---

## Feed Count by Sector (How Each Sector Sees the Total Universe)

| Sector | Dedicated Feeds | Layer 1 Overlap | Layer 3 Overlap | Layer 4 Overlap | Total Visible |
|--------|----------------|-----------------|-----------------|-----------------|---------------|
| CRE | 74 | 5 | 8 | 15 | 102 |
| Private Equity | 25 | 1 | 8 | 0 | 34 |
| Data Centers | 18 | 0 | 5 | 0 | 23 |
| Energy | 25 | 4 | 5 | 5 | 39 |
| Banking/Credit | 18 | 8 | 5 | 0 | 31 |
| Fed/Macro | 10 | 12 | 8 | 0 | 30 |
| Local Government | 38 | 2 | 2 | 30 | 72 |

---

## Feed Health and Verification Status Summary

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| [KEPT] | 75 | 22% | Existing feeds verified working in production |
| [VERIFIED] | 28 | 8% | New feeds with confirmed working RSS endpoints |
| [NEEDS VERIFICATION] | 237 | 70% | Inferred feed URLs requiring testing before production |
| **Total** | **340** | **100%** | |

**Note:** 70% of proposed feeds require URL verification. This is the largest operational risk in the source registry. Priority: verify all trade publication feeds first (most likely to follow standard RSS patterns), then municipal/government feeds (most likely to require custom scrapers).

---

## Feed Construction Conventions

For feeds marked [NEEDS VERIFICATION] and [INFERRED], the following URL conventions are assumed:

1. **WordPress sites:** `/feed/` (most common pattern)
2. **Blogger/Blogspot:** `/feeds/posts/default`
3. **Industry Dive publications:** `/feeds/news/` (verified pattern)
4. **BizJournals network:** `/{city}/rss2.xml`
5. **NewsAPI queries:** Constructed from keyword + sector patterns
6. **Google News RSS:** `https://news.google.com/rss/search?q={entity}+{sector}&hl=en-US&gl=US&ceid=US:en`
7. **SEC EDGAR:** Standard Atom feed URL
8. **Government feeds:** Vary widely; many use GovDelivery (`public.govdelivery.com`)

---

## Implementation Priorities

**Phase 1 — Immediate (Week 1-2):** Verify and activate Private Equity + Data Center feeds. These sectors have zero coverage today and the shortest path to initial capability. Approximately 43 new feed URLs to verify.

**Phase 2 (Week 3-4):** Verify and activate Energy + Banking/Credit feeds. Energy requires approximately 25 feed verifications; banking requires approximately 15 new feed verifications. Energy RTO/ISO feeds may require custom parsers.

**Phase 3 (Week 5-6):** Verify and activate Local Government feeds. Highest difficulty — approximately 38 sources, most without standardized RSS. Prioritize top 10 MSA city-level sources; use LegiScan for state legislative tracking.

**Phase 4 (Week 7-8):** Layer 5 API integration. Set up paid tiers as needed. Integrate EventRegistry or GNews API for supplementary discovery. Implement Google News Alert monitoring for watchlist entities.

**Ongoing:** Feed health monitoring, dead feed replacement, new source discovery. The `SourceHealthLedger` (in `source_health.py`) requires per-sector tracking to support the 340-feed inventory.

---

## Feed Redundancy Requirement

Each sector must maintain at least 3 independent, non-overlapping source families to enable cross-source corroboration. The current `cluster_events()` function depends on multiple sources covering the same story — this infrastructure must be preserved and is not optional for editorial quality.

| Sector | Source Families | Redundancy Status |
|--------|----------------|-------------------|
| CRE | Trade press (TRD, CO, Bisnow, GlobeSt), brokerage research (CBRE, JLL, C&W, Colliers, Newmark), data providers (CoStar, RealPage, Yardi, NAREIT, NCREIF), federal (FHFA, HUD, Fannie, Freddie) | Strong — 4+ independent families |
| PE | Trade press (PE Hub, Buyouts, PEI, PitchBook), newsletters (Axios Pro Rata, Term Sheet), data (Preqin, Cambridge), federal (SEC EDGAR) | Adequate — 4 families after verification |
| DC | Trade press (DCD, DCF, DCK), hyperscaler sources (AWS, Azure, GCP, Meta), REIT IR (Equinix, Digital Realty), research (Structure, Uptime) | Adequate — 4 families after verification |
| Energy | Trade press (Utility Dive, E&E, Power Mag, RTO Insider), federal (EIA, FERC, DOE, EPA), RTO/ISO (PJM, ERCOT, CAISO), data (S&P Global, BNEF, WoodMac) | Strong — 4 families after verification |
| Banking | Federal (Fed, OCC, FDIC), trade press (American Banker, Banking Dive, Risk.net), ratings (Fitch, Moody's, S&P), data (S&P Market Intelligence) | Strong — 4 families |
| Fed/Macro | Federal (Fed × 8, Treasury, CBO), economic data (BLS, BEA, Census, FRED), analytical (Calculated Risk, Wolf Street, Fed Guy, Overshoot), international (BIS, IMF) | Strong — 4 families |
| Local Gov | City agencies, state agencies, state legislatures (LegiScan), business journals (BizJournals network) | Adequate — 4 families after verification |

---

## End of Document

**Next Document:** `06-scoring-and-ranking-specification.md` — Complete scoring framework with 10 dimensions, sector-specific weight profiles, composite score calculation, tier assignment, and cross-sector deduplication logic.
