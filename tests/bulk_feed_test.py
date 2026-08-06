"""Bulk RSS feed tester — find working feeds for all 6 sectors."""
import sys
sys.path.insert(0, 'scripts')
from ingestion import fetch_single_feed
from concurrent.futures import ThreadPoolExecutor, as_completed

# All feeds to test — name, url, tier, sectors
FEEDS = [
    # ── PRIVATE EQUITY ──
    ("PE Hub", "https://www.pehub.com/feed/", 2, ["private_equity"]),
    ("Buyouts Insider", "https://www.buyoutsinsider.com/feed/", 2, ["private_equity"]),
    ("Private Equity International", "https://www.privateequityinternational.com/feed/", 2, ["private_equity"]),
    ("Secondaries Investor", "https://www.secondariesinvestor.com/feed/", 2, ["private_equity"]),
    ("Venture Capital Journal", "https://www.venturecapitaljournal.com/feed/", 2, ["private_equity"]),
    ("Infrastructure Investor", "https://www.infrastructureinvestor.com/feed/", 2, ["private_equity"]),
    ("Private Debt Investor", "https://www.privatedebtinvestor.com/feed/", 2, ["private_equity"]),
    ("Agri Investor", "https://www.agriinvestor.com/feed/", 2, ["private_equity"]),
    ("New Private Markets", "https://www.newprivatemarkets.com/feed/", 2, ["private_equity"]),
    ("Mergers & Acquisitions", "https://www.themiddlemarket.com/feed/", 2, ["private_equity"]),
    ("PitchBook News", "https://pitchbook.com/newsroom/feed/", 2, ["private_equity"]),
    ("Institutional Investor", "https://www.institutionalinvestor.com/feed/", 2, ["private_equity"]),
    ("Fortune Term Sheet", "https://fortune.com/feed/term-sheet/", 2, ["private_equity"]),
    ("WSJ Pro PE", "https://feeds.content.dowjones.io/wsj/public/rss/wsj-pro-private-equity", 2, ["private_equity"]),
    ("Bloomberg PE", "https://feeds.bloomberg.com/markets/private-equity.rss", 2, ["private_equity"]),
    ("Sovereign Wealth Fund Institute", "https://www.swfinstitute.org/feed/", 2, ["private_equity"]),
    ("PERE News", "https://www.perenews.com/feed/", 2, ["private_equity"]),
    
    # ── DATA CENTERS ──
    ("Data Center Dynamics", "https://www.datacenterdynamics.com/rss/", 2, ["data_centers"]),
    ("Data Center Knowledge", "https://www.datacenterknowledge.com/feed/", 2, ["data_centers"]),
    ("Data Center Frontier", "https://datacenterfrontier.com/feed/", 2, ["data_centers"]),
    ("Uptime Institute", "https://uptimeinstitute.com/blog/feed/", 2, ["data_centers"]),
    ("Cloudscene", "https://cloudscene.com/news/feed/", 2, ["data_centers"]),
    ("Structure Research", "https://structureresearch.net/feed/", 2, ["data_centers"]),
    ("Bisnow Data Centers", "https://www.bisnow.com/national/data-centers/rss", 2, ["data_centers"]),
    
    # ── ENERGY ──
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/", 2, ["energy"]),
    ("Power Magazine", "https://www.powermag.com/feed/", 2, ["energy"]),
    ("Renewable Energy World", "https://www.renewableenergyworld.com/feed/", 2, ["energy"]),
    ("Greentech Media", "https://www.greentechmedia.com/feed/", 2, ["energy"]),
    ("PV Magazine", "https://www.pv-magazine.com/feed/", 2, ["energy"]),
    ("Windpower Monthly", "https://www.windpowermonthly.com/feed/", 2, ["energy"]),
    ("Energy Storage News", "https://www.energy-storage.news/feed/", 2, ["energy"]),
    ("Canary Media", "https://www.canarymedia.com/feed/", 2, ["energy"]),
    ("RTO Insider", "https://www.rtoinsider.com/feed/", 2, ["energy"]),
    ("Natural Gas Intelligence", "https://www.naturalgasintel.com/feed/", 2, ["energy"]),
    ("S&P Global Commodities", "https://www.spglobal.com/commodityinsights/en/rss-feed/", 2, ["energy"]),
    ("World Nuclear News", "https://www.world-nuclear-news.org/feed/", 2, ["energy"]),
    ("E&E News", "https://www.eenews.net/feed/", 2, ["energy"]),
    
    # ── BANKING / CREDIT ──
    ("Banking Dive", "https://www.bankingdive.com/feeds/news/", 2, ["banking_credit"]),
    ("American Banker", "https://www.americanbanker.com/arcio/rss/", 2, ["banking_credit"]),
    ("Bank Director", "https://www.bankdirector.com/feed/", 2, ["banking_credit"]),
    ("The Financial Brand", "https://thefinancialbrand.com/feed/", 2, ["banking_credit"]),
    ("Risk.net", "https://www.risk.net/feed/", 2, ["banking_credit"]),
    ("ABA Banking Journal", "https://bankingjournal.aba.com/feed/", 2, ["banking_credit"]),
    ("Credit Union Times", "https://www.cutimes.com/feed/", 2, ["banking_credit"]),
    ("Mortgage Professional America", "https://www.mpamag.com/us/feed/", 2, ["banking_credit"]),
    ("National Mortgage News", "https://www.nationalmortgagenews.com/feed/", 2, ["banking_credit"]),
    
    # ── FED / MACRO ──
    ("Federal Reserve Press", "https://www.federalreserve.gov/feeds/press_all.xml", 1, ["fed_macro"]),
    ("Federal Reserve FOMC", "https://www.federalreserve.gov/feeds/press_monetary.xml", 1, ["fed_macro"]),
    ("Federal Reserve Speeches", "https://www.federalreserve.gov/feeds/speeches.xml", 1, ["fed_macro"]),
    ("Federal Reserve Testimony", "https://www.federalreserve.gov/feeds/testimony.xml", 1, ["fed_macro"]),
    ("FDIC Press", "https://www.fdic.gov/news/rss-feeds/press-releases.xml", 1, ["banking_credit", "fed_macro"]),
    ("OCC News", "https://www.occ.gov/news-issuances/news-releases/index-rss.xml", 1, ["banking_credit"]),
    ("SEC Press", "https://www.sec.gov/news/pressreleases.rss", 1, ["banking_credit", "fed_macro"]),
    ("SEC Litigation", "https://www.sec.gov/litigation/litreleases.rss", 1, ["banking_credit"]),
    ("Treasury Press", "https://home.treasury.gov/news/press-releases/feed", 1, ["fed_macro"]),
    ("FHFA", "https://www.fhfa.gov/Media/Pages/RSS.aspx", 1, ["fed_macro"]),
    ("BLS", "https://www.bls.gov/feed/bls_news.xml", 1, ["fed_macro"]),
    ("BEA", "https://www.bea.gov/feeds/news.xml", 1, ["fed_macro"]),
    ("Census Economic", "https://www.census.gov/economic-indicators/feed.xml", 1, ["fed_macro"]),
    
    # ── LOCAL GOVERNMENT ──
    ("CityLand NYC", "https://www.citylandnyc.org/feed/", 2, ["local_government"]),
    ("NYC Planning", "https://www.nyc.gov/site/planning/about/press-releases.rss", 2, ["local_government"]),
    ("NYC DOB", "https://www.nyc.gov/site/buildings/about/press-releases.rss", 2, ["local_government"]),
    ("NYC Council", "https://council.nyc.gov/press/feed/", 2, ["local_government"]),
    ("SF Planning", "https://sfplanning.org/news/feed", 2, ["local_government"]),
    ("LA Planning", "https://planning.lacity.gov/news/feed", 2, ["local_government"]),
    ("Chicago City Clerk", "https://www.chicago.gov/city/en/rss.html", 2, ["local_government"]),
]

results = {"working": [], "empty": [], "broken": []}

print("Testing", len(FEEDS), "feeds across 6 sectors...\n")

def test_feed(name, url, tier, sectors):
    src = {"name": name, "url": url, "tier": tier, "sectors": sectors}
    items, updated, err = fetch_single_feed(src)
    return name, url, len(items), err, sectors

with ThreadPoolExecutor(max_workers=8) as ex:
    futures = [ex.submit(test_feed, *f) for f in FEEDS]
    for future in as_completed(futures):
        name, url, count, err, sectors = future.result()
        if count > 0:
            results["working"].append((name, url, count, sectors))
            print(f"  OK: {name} — {count} items")
        elif err:
            results["broken"].append((name, url, str(err)[:60]))
            print(f"  BROKEN: {name}")
        else:
            results["empty"].append((name, url))
            # Don't print empty to reduce noise

print(f"\nRESULTS: {len(results['working'])} working, {len(results['empty'])} empty, {len(results['broken'])} broken")

# Print working by sector
from collections import Counter
sector_counts = Counter()
print("\n--- Working Feeds by Sector ---")
for name, url, count, sectors in results["working"]:
    for s in sectors:
        sector_counts[s] += 1
for s, c in sector_counts.most_common():
    print(f"  {s}: {c} feeds")

# Print broken feeds for debugging
if results["broken"]:
    print(f"\n--- Broken ({len(results['broken'])}) ---")
    for name, url, err in results["broken"][:10]:
        print(f"  {name}: {url[:60]}")
