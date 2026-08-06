"""Deep feed discovery — test 100+ URLs across all 6 non-CRE sectors."""
import sys
sys.path.insert(0, 'scripts')
from ingestion import fetch_single_feed
from concurrent.futures import ThreadPoolExecutor, as_completed

FEEDS = [
    # ═══ PRIVATE EQUITY — need 20 more ═══
    # PE Hub network (already have 7, test the rest)
    ("PE Hub", "https://www.pehub.com/feed/", 2, ["private_equity"]),
    ("Buyouts", "https://www.buyoutsinsider.com/feed/", 2, ["private_equity"]),
    ("VC Journal", "https://www.venturecapitaljournal.com/feed/", 2, ["private_equity"]),
    ("PEI", "https://www.privateequityinternational.com/feed/", 2, ["private_equity"]),
    ("Secondaries Investor", "https://www.secondariesinvestor.com/feed/", 2, ["private_equity"]),
    ("PDI", "https://www.privatedebtinvestor.com/feed/", 2, ["private_equity"]),
    ("Infra Investor", "https://www.infrastructureinvestor.com/feed/", 2, ["private_equity"]),
    ("Agri Investor", "https://www.agriinvestor.com/feed/", 2, ["private_equity"]),
    ("New Private Mkts", "https://www.newprivatemarkets.com/feed/", 2, ["private_equity"]),
    # Other PE publications
    ("PitchBook", "https://pitchbook.com/newsroom/feed/", 2, ["private_equity"]),
    ("The Deal", "https://www.thedeal.com/feed/", 2, ["private_equity"]),
    ("Institutional Investor", "https://www.institutionalinvestor.com/feed/", 2, ["private_equity"]),
    ("SWFI", "https://www.swfinstitute.org/feed/", 2, ["private_equity"]),
    ("PERE News", "https://www.perenews.com/feed/", 2, ["private_equity"]),
    ("Real Deals", "https://realdeals.eu.com/feed/", 2, ["private_equity"]),
    ("Alt Assets", "https://www.altassets.net/feed/", 2, ["private_equity"]),
    ("Pensions & Investments", "https://www.pionline.com/feed/", 2, ["private_equity"]),
    ("Chief Investment Officer", "https://www.ai-cio.com/feed/", 2, ["private_equity"]),
    ("Funds Europe", "https://www.funds-europe.com/feed/", 2, ["private_equity"]),
    ("IPE Real Assets", "https://realassets.ipe.com/feed/", 2, ["private_equity"]),
    ("Axios Pro Rata", "https://www.axios.com/feeds/newsletters/pro-rata.rss", 2, ["private_equity"]),
    
    # ═══ DATA CENTERS — need 13 more ═══
    ("DCD", "https://www.datacenterdynamics.com/rss/", 2, ["data_centers"]),
    ("Data Center Knowledge", "https://www.datacenterknowledge.com/feed/", 2, ["data_centers"]),
    ("Data Center Frontier", "https://datacenterfrontier.com/feed/", 2, ["data_centers"]),
    ("Uptime Institute", "https://uptimeinstitute.com/blog/feed/", 2, ["data_centers"]),
    ("Cloudscene", "https://cloudscene.com/news/feed/", 2, ["data_centers"]),
    ("Structure Research", "https://structureresearch.net/feed/", 2, ["data_centers"]),
    ("Bisnow Data Centers", "https://www.bisnow.com/national/data-centers/rss", 2, ["data_centers"]),
    ("Mission Critical Mag", "https://www.missioncriticalmagazine.com/rss", 2, ["data_centers"]),
    ("Data Center POST", "https://datacenterpost.com/feed/", 2, ["data_centers"]),
    ("InterGlobix", "https://interglobixmagazine.com/feed/", 2, ["data_centers"]),
    ("JLL Data Centers", "https://www.us.jll.com/en/views/tag/data-centers/rss", 2, ["data_centers"]),
    ("CBRE Data Centers", "https://www.cbre.com/insights/feed?tag=data-centers", 2, ["data_centers"]),
    
    # ═══ ENERGY — need 22 more ═══
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/", 2, ["energy"]),
    ("Power Magazine", "https://www.powermag.com/feed/", 2, ["energy"]),
    ("Renewable Energy World", "https://www.renewableenergyworld.com/feed/", 2, ["energy"]),
    ("PV Magazine", "https://www.pv-magazine.com/feed/", 2, ["energy"]),
    ("Energy Storage News", "https://www.energy-storage.news/feed/", 2, ["energy"]),
    ("Canary Media", "https://www.canarymedia.com/feed/", 2, ["energy"]),
    ("NGI", "https://www.naturalgasintel.com/feed/", 2, ["energy"]),
    ("RTO Insider", "https://www.rtoinsider.com/feed/", 2, ["energy"]),
    ("Windpower Monthly", "https://www.windpowermonthly.com/feed/", 2, ["energy"]),
    ("Greentech Media", "https://www.greentechmedia.com/feed/", 2, ["energy"]),
    ("World Nuclear News", "https://www.world-nuclear-news.org/feed/", 2, ["energy"]),
    ("E&E News", "https://www.eenews.net/feed/", 2, ["energy"]),
    ("S&P Global Platts", "https://www.spglobal.com/commodityinsights/en/rss-feed/", 2, ["energy"]),
    ("Solar Power World", "https://www.solarpowerworldonline.com/feed/", 2, ["energy"]),
    ("CleanTechnica", "https://cleantechnica.com/feed/", 2, ["energy"]),
    ("Utility Week", "https://utilityweek.co.uk/feed/", 2, ["energy"]),
    ("Transmission & Distribution World", "https://www.tdworld.com/rss", 2, ["energy"]),
    ("Hydrogen Fuel News", "https://www.hydrogenfuelnews.com/feed/", 2, ["energy"]),
    ("Offshore Wind", "https://www.offshorewind.biz/feed/", 2, ["energy"]),
    ("Energy Central", "https://energycentral.com/rss", 2, ["energy"]),
    ("Smart Electric Power Alliance", "https://sepapower.org/feed/", 2, ["energy"]),
    ("American Public Power", "https://www.publicpower.org/feed/", 2, ["energy"]),
    
    # ═══ BANKING / CREDIT — need more industry ═══
    ("Banking Dive", "https://www.bankingdive.com/feeds/news/", 2, ["banking_credit"]),
    ("ABA Banking Journal", "https://bankingjournal.aba.com/feed/", 2, ["banking_credit"]),
    ("American Banker", "https://www.americanbanker.com/arcio/rss/", 2, ["banking_credit"]),
    ("Bank Director", "https://www.bankdirector.com/feed/", 2, ["banking_credit"]),
    ("Financial Brand", "https://thefinancialbrand.com/feed/", 2, ["banking_credit"]),
    ("Risk.net", "https://www.risk.net/feed/", 2, ["banking_credit"]),
    ("CU Times", "https://www.cutimes.com/feed/", 2, ["banking_credit"]),
    ("National Mortgage News", "https://www.nationalmortgagenews.com/feed/", 2, ["banking_credit"]),
    ("MPA Magazine", "https://www.mpamag.com/us/feed/", 2, ["banking_credit"]),
    ("HousingWire", "https://www.housingwire.com/feed/", 2, ["banking_credit"]),
    ("Bank Automation News", "https://bankautomationnews.com/feed/", 2, ["banking_credit"]),
    ("Payments Dive", "https://www.paymentsdive.com/feeds/news/", 2, ["banking_credit"]),
    ("CFO Dive", "https://www.cfodive.com/feeds/news/", 2, ["banking_credit"]),
    ("Treasury & Risk", "https://www.treasuryandrisk.com/feed/", 2, ["banking_credit"]),
    
    # ═══ FED / MACRO ═══
    ("Fed Press", "https://www.federalreserve.gov/feeds/press_all.xml", 1, ["fed_macro"]),
    ("Fed FOMC", "https://www.federalreserve.gov/feeds/press_monetary.xml", 1, ["fed_macro"]),
    ("Fed Speeches", "https://www.federalreserve.gov/feeds/speeches.xml", 1, ["fed_macro"]),
    ("Fed Testimony", "https://www.federalreserve.gov/feeds/testimony.xml", 1, ["fed_macro"]),
    ("FDIC Press", "https://www.fdic.gov/news/rss-feeds/press-releases.xml", 1, ["banking_credit", "fed_macro"]),
    ("OCC News", "https://www.occ.gov/news-issuances/news-releases/index-rss.xml", 1, ["banking_credit"]),
    ("SEC Press", "https://www.sec.gov/news/pressreleases.rss", 1, ["banking_credit", "fed_macro"]),
    ("SEC Litigation", "https://www.sec.gov/litigation/litreleases.rss", 1, ["banking_credit"]),
    ("Treasury Press", "https://home.treasury.gov/news/press-releases/feed", 1, ["fed_macro"]),
    ("FHFA", "https://www.fhfa.gov/Media/Pages/RSS.aspx", 1, ["fed_macro"]),
    ("BLS News", "https://www.bls.gov/feed/bls_news.xml", 1, ["fed_macro"]),
    ("BEA News", "https://www.bea.gov/feeds/news.xml", 1, ["fed_macro"]),
    ("Census Economic", "https://www.census.gov/economic-indicators/feed.xml", 1, ["fed_macro"]),
    ("IMF News", "https://www.imf.org/en/News/RSS", 1, ["fed_macro"]),
    ("World Bank News", "https://www.worldbank.org/en/news/rss", 1, ["fed_macro"]),
    ("CBO", "https://www.cbo.gov/rss/latest10.xml", 1, ["fed_macro"]),
    ("GAO Reports", "https://www.gao.gov/feeds/reports.xml", 1, ["fed_macro"]),
    
    # ═══ LOCAL GOVERNMENT ═══
    ("CityLand NYC", "https://www.citylandnyc.org/feed/", 2, ["local_government"]),
    ("NYC Council", "https://council.nyc.gov/press/feed/", 2, ["local_government"]),
    ("SF Planning", "https://sfplanning.org/news/feed", 2, ["local_government"]),
    ("LA Planning", "https://planning.lacity.gov/news/feed", 2, ["local_government"]),
    ("Chicago City Clerk", "https://www.chicago.gov/city/en/rss.html", 2, ["local_government"]),
    ("NYC Planning", "https://www.nyc.gov/site/planning/about/press-releases.rss", 2, ["local_government"]),
    ("NYC DOB", "https://www.nyc.gov/site/buildings/about/press-releases.rss", 2, ["local_government"]),
    ("Boston Planning", "https://www.bostonplans.org/news/feed/", 2, ["local_government"]),
    ("DC Planning", "https://planning.dc.gov/rss.xml", 2, ["local_government"]),
    ("Seattle DP", "https://www.seattle.gov/sdci/news/feed", 2, ["local_government"]),
    ("Miami Dade", "https://www.miamidade.gov/global/rss.page", 2, ["local_government"]),
    ("NACo", "https://www.naco.org/news/rss.xml", 2, ["local_government"]),
    ("NLC", "https://www.nlc.org/feed/", 2, ["local_government"]),
    ("Route Fifty", "https://www.route-fifty.com/feed/", 2, ["local_government"]),
    ("Governing", "https://www.governing.com/feed/", 2, ["local_government"]),
]

print(f"Testing {len(FEEDS)} feeds across 6 sectors...\n")

working = {}
empty = []
broken = []

def test(name, url, tier, sectors):
    src = {"name": name, "url": url, "tier": tier, "sectors": sectors}
    items, updated, err = fetch_single_feed(src)
    return name, url, len(items), bool(items), err, sectors

with ThreadPoolExecutor(max_workers=12) as ex:
    futures = {ex.submit(test, *f): f for f in FEEDS}
    for future in as_completed(futures):
        name, url, count, is_working, err, sectors = future.result()
        for s in sectors:
            working.setdefault(s, []).append((name, url, count))
        if is_working:
            print(f"  + {name}: {count} items")
        elif err:
            broken.append(name)
        else:
            empty.append(name)

print(f"\n{'='*50}")
from collections import Counter
sc = Counter()
for s, feeds in working.items():
    total = sum(f[2] for f in feeds)
    sc[s] = len(feeds)
    print(f"  {s}: {len(feeds)} feeds, ~{total} items")

print(f"\nWorking: {sum(sc.values())} feeds total | Empty: {len(empty)} | Broken: {len(broken)}")
