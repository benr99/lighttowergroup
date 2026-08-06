"""Quick feed verification for missing sectors."""
import sys
sys.path.insert(0, 'scripts')
from ingestion import fetch_single_feed

# Test feeds for missing sectors
test_feeds = [
    # Fed/Macro
    {"name": "Federal Reserve Press Releases", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "tier": 1, "sectors": ["fed_macro"]},
    {"name": "Federal Reserve FOMC", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "tier": 1, "sectors": ["fed_macro"]},
    {"name": "BLS Economic News", "url": "https://www.bls.gov/feed/bls_news.xml", "tier": 1, "sectors": ["fed_macro"]},
    {"name": "Treasury Press Releases", "url": "https://home.treasury.gov/news/press-releases/feed", "tier": 1, "sectors": ["fed_macro"]},
    # Banking
    {"name": "American Banker", "url": "https://www.americanbanker.com/arcio/rss/", "tier": 2, "sectors": ["banking_credit"]},
    {"name": "Banking Dive", "url": "https://www.bankingdive.com/feeds/news/", "tier": 2, "sectors": ["banking_credit"]},
    # Energy
    {"name": "Utility Dive", "url": "https://www.utilitydive.com/feeds/news/", "tier": 2, "sectors": ["energy"]},
    {"name": "Power Magazine", "url": "https://www.powermag.com/feed/", "tier": 2, "sectors": ["energy"]},
    # Data Centers
    {"name": "Data Center Dynamics", "url": "https://www.datacenterdynamics.com/feed/", "tier": 2, "sectors": ["data_centers"]},
    {"name": "Data Center Frontier", "url": "https://datacenterfrontier.com/feed/", "tier": 2, "sectors": ["data_centers"]},
]

print("Testing feeds for missing sectors...\n")
for src in test_feeds:
    items, updated, err = fetch_single_feed(src)
    name = src['name']
    count = len(items)
    health = updated.get('_health', '?')
    if items:
        print(f"  OK: {name} — {count} items")
    elif err:
        print(f"  FAIL: {name} — {str(err)[:80]}")
    else:
        print(f"  EMPTY: {name} — no entries found")
