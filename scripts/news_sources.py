"""
Light Tower Group — News Agent Source Configuration
"""

# ── RSS Feeds ──────────────────────────────────────────────────────────────────
# (display_name, feed_url)
RSS_FEEDS = [
    # Tier 1: NYC-focused CRE — highest priority
    ("The Real Deal",           "https://therealdeal.com/new-york/feed/"),
    ("Commercial Observer",     "https://commercialobserver.com/feed/"),
    ("Bisnow New York",         "https://www.bisnow.com/new-york/rss"),
    ("Real Estate Weekly",      "https://rew-online.com/feed/"),
    ("Crain's NY Business",     "https://www.crainsnewyork.com/real-estate/rss"),

    # Tier 2: National CRE — broad market coverage
    ("GlobeSt",                 "https://www.globest.com/rss/"),
    ("Connect CRE",             "https://www.connect.media/feed/"),
    ("Propmodo",                "https://propmodo.com/feed/"),
    ("NREI",                    "https://www.nreionline.com/rss/all"),
    ("Multi-Housing News",      "https://www.multihousingnews.com/feed/"),
    ("CP Executive",            "https://www.cpexecutive.com/feed/"),

    # Tier 3: Capital markets & finance
    ("PERE News",               "https://www.perenews.com/rss/"),
    ("Mortgage Professional",   "https://www.mpamag.com/us/rss"),
    ("MBA Newslink",            "https://newslink.mba.org/feed/"),

    # Tier 4: Broader business context
    ("NY Post Real Estate",     "https://nypost.com/real-estate/feed/"),
    ("Curbed NY",               "https://www.curbed.com/rss/index.xml"),
    ("Bloomberg Business",      "https://feeds.bloomberg.com/businessweek/news.rss"),
    ("Axios Cities",            "https://www.axios.com/feeds/feed.rss"),
    ("CoStar News",             "https://www.costar.com/rss/news"),
    ("NY Times Real Estate",    "https://rss.nytimes.com/services/xml/rss/nyt/RealEstate.xml"),

    # Tier 1 additions — NYC-specific CRE
    ("New York YIMBY",          "https://newyorkyimby.com/feed"),
    ("Observer Real Estate",    "https://observer.com/real-estate/feed/"),
    ("The City NYC",            "https://thecity.nyc/feed"),
    ("6sqft",                   "https://www.6sqft.com/feed/"),
    ("Gothamist",               "https://gothamist.com/feed/"),
    ("CityLand NYC",            "https://www.citylandnyc.org/feed/"),
    ("NY Daily News RE",        "https://www.nydailynews.com/real-estate/rss.xml"),
    ("The Real Deal National",  "https://therealdeal.com/feed/"),

    # Tier 2 additions — National CRE + Regional Bisnow
    ("Bisnow National",         "https://www.bisnow.com/national/rss"),
    ("Bisnow Los Angeles",      "https://www.bisnow.com/los-angeles/rss"),
    ("Bisnow Chicago",          "https://www.bisnow.com/chicago/rss"),
    ("Bisnow DC",               "https://www.bisnow.com/washington-dc/rss"),
    ("Bisnow Miami",            "https://www.bisnow.com/miami/rss"),
    ("Bisnow Dallas",           "https://www.bisnow.com/dallas-fort-worth/rss"),
    ("Bisnow Boston",           "https://www.bisnow.com/boston/rss"),
    ("Bisnow Atlanta",          "https://www.bisnow.com/atlanta/rss"),
    ("Bisnow Philadelphia",     "https://www.bisnow.com/philadelphia/rss"),
    ("Bisnow Seattle",          "https://www.bisnow.com/seattle/rss"),
    ("Bisnow Denver",           "https://www.bisnow.com/denver/rss"),
    ("HousingWire",             "https://www.housingwire.com/feed/"),
    ("Construction Dive",       "https://www.constructiondive.com/feeds/news/"),
    ("Urban Land Institute",    "https://urbanland.uli.org/feed/"),
    ("Affordable Housing Finance", "https://www.housingfinance.com/feed/"),
    ("Building Design+Construction", "https://www.bdcnetwork.com/rss.xml"),
    ("Shopping Center Business", "https://www.shoppingcenterbusiness.com/feed/"),
    ("RE Business Online",      "https://www.rebusinessonline.com/feed/"),

    # Tier 3 additions — Capital Markets & Finance
    ("Bloomberg Real Estate",   "https://feeds.bloomberg.com/markets/news.rss"),
    ("Reuters Business",        "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC Real Estate",        "https://www.cnbc.com/id/10000115/device/rss/rss.html"),
    ("Wall Street Journal",     "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("MarketWatch Real Estate", "https://feeds.marketwatch.com/marketwatch/realestate/"),
    ("American Banker",         "https://www.americanbanker.com/feed"),
    ("Mortgage News Daily",     "https://www.mortgagenewsdaily.com/rss/"),
    ("Trepp Blog",              "https://www.trepp.com/trepptalk/rss.xml"),
    ("HUD Exchange",            "https://www.hudexchange.info/news/rss/"),
    ("ATTOM Data",              "https://www.attomdata.com/feed/"),
    ("NAREIT",                  "https://www.nareit.com/rss.xml"),
    ("NMHC",                    "https://www.nmhc.org/feed/"),
    ("Institutional Real Estate", "https://irei.com/news/feed/"),
    ("RealPage",                "https://www.realpage.com/news/feed/"),
    ("Yardi Matrix",            "https://www.yardi.com/blog/rss/"),
    ("National Association of Realtors", "https://www.nar.realtor/news/rss.xml"),
    ("Fannie Mae Perspectives",  "https://www.fanniemae.com/rss.xml"),
    ("Freddie Mac Perspectives", "https://www.freddiemac.com/rss.xml"),
    ("CREFC",                   "https://www.crefc.org/rss.xml"),

    # Tier 4 additions — Regional business journals
    ("San Francisco Business Times", "https://www.bizjournals.com/sanfrancisco/rss2.xml"),
    ("LA Business Journal",     "https://www.bizjournals.com/losangeles/rss2.xml"),
    ("Chicago Tribune Business", "https://www.chicagotribune.com/business/rss2.xml"),
    ("Dallas Business Journal",  "https://www.bizjournals.com/dallas/rss2.xml"),
    ("Washington Post Business", "https://feeds.washingtonpost.com/rss/business"),
    ("Boston Globe Business",    "https://feeds.bostonglobe.com/rss/business/"),
    ("Houston Chronicle Business", "https://www.houstonchronicle.com/business/rss.xml"),
    ("Denver Post Business",     "https://www.denverpost.com/feed/"),
    ("Seattle Times Business",   "https://feeds.seattletimes.com/rss/seattle/business/"),
    ("Miami Herald Business",    "https://www.miamiherald.com/news/business/rss.xml"),
    ("Philadelphia Inquirer Business", "https://www.inquirer.com/business/rss/"),
    ("Atlanta Journal-Constitution", "https://www.ajc.com/news/business/rss/"),
    ("Phoenix Business Journal", "https://www.bizjournals.com/phoenix/rss2.xml"),

    # Tier 5 (new) — Research and analytics
    ("Colliers Insights",       "https://www.colliers.com/en-us/news/rss.xml"),
    ("Marcus & Millichap",      "https://www.marcusmillichap.com/rss.xml"),
    ("Newmark Research",        "https://www.nmrk.com/rss/"),
    ("VTS Blog",                "https://www.vts.com/blog/rss.xml"),
    ("NCREIF",                  "https://www.ncreif.org/rss.xml"),
    ("Green Street Advisors",   "https://www.greenstreetadvisors.com/rss.xml"),
    ("Urban Institute",         "https://www.urban.org/taxonomy/term/100/feed"),
    ("IREI News",               "https://irei.com/news/feed/"),
    ("Lincoln Institute",       "https://www.lincolninst.edu/rss/policy-and-research"),
    ("National Law Review",     "https://www.natlawreview.com/rss/real-estate-law"),
]

# ── NewsAPI Keyword Queries ────────────────────────────────────────────────────
# Used with NewsAPI.org free tier (100 req/day).
# We run the first 3 only to stay well within limits.
NEWSAPI_QUERIES = [
    "NYC commercial real estate mortgage 2026",
    "Manhattan multifamily loan maturity",
    "Brooklyn commercial real estate deal",
    "New York CMBS office distress",
    "NYC apartment building refinance",
]

# ── CRE Relevance Filter ───────────────────────────────────────────────────────
# A story must contain at least one of these keywords to pass triage.
CRE_KEYWORDS = [
    # Asset classes
    "commercial real estate", "multifamily", "apartment building", "residential tower",
    "office building", "retail space", "industrial", "warehouse", "mixed-use",
    "condo tower", "co-op", "rental building", "affordable housing",

    # Finance / debt
    "mortgage", "refinanc", "bridge loan", "construction loan", "mezzanine",
    "cmbs", "mbs", "agency debt", "fannie", "freddie", "fha ", "hud ",
    "loan maturity", "default", "distress", "foreclosure", "note sale",
    "cap rate", "noi", "debt service", "dscr", "ltv ", "interest rate",
    "sofr", "10-year treasury", "credit spread", "capital stack",

    # Transactions
    "acquisition", "disposition", "sale-leaseback", "ground lease",
    "joint venture", "recapitalization", "equity raise", "fund",

    # NYC-specific
    "421a", "421g", "j51", "tax abatement", "opportunity zone",
    "upzoning", "rezoning", "air rights", "transferable development rights",
    "brooklyn", "manhattan", "queens", "bronx", "fidi", "midtown",
    "hudson yards", "long island city", "williamsburg", "bushwick",
    "downtown brooklyn", "dumbo", "red hook", "gowanus", "harlem",
    "upper east side", "upper west side", "hells kitchen", "chelsea",

    # Industry roles
    "landlord", "developer", "sponsor", "lender", "borrower",
    "reit", "private equity", "investment sales", "brokerage",

    # Regulation
    "rent stabilization", "housing court", "hpd ", "dob permit",
    "certificate of occupancy", "landmark", "lpc ",
]

# ── Exclusion Filter ───────────────────────────────────────────────────────────
# Stories containing any of these are discarded as noise.
EXCLUDE_KEYWORDS = [
    "single-family home", "single family home", "open house", "home sale",
    "interior design", "renovation tips", "diy home", "celebrity home",
    "home decor", "celebrity buys", "reality tv", "sports arena naming",
    "political campaign", "immigration", "weather forecast",
]

# ── Site Configuration ─────────────────────────────────────────────────────────
SITE_URL         = "https://lighttowergroup.co"
SITE_NAME        = "Light Tower Group"
FEED_TITLE       = "Light Tower Group \u2014 NYC CRE Capital Markets Insights"
FEED_DESCRIPTION = (
    "Data-driven capital markets analysis and building intelligence "
    "for NYC commercial real estate professionals."
)

# LinkedIn hashtags appended to every post
LINKEDIN_HASHTAGS = [
    "#CREFinance",
    "#CapitalMarkets",
    "#NYCRealEstate",
    "#CommercialRealEstate",
    "#RealEstateInvesting",
]
