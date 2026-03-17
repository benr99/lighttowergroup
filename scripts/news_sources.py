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
