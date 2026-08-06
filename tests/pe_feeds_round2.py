"""Deep PE feed discovery round 2."""
import sys
sys.path.insert(0, 'scripts')
from ingestion import fetch_single_feed
from concurrent.futures import ThreadPoolExecutor, as_completed

feeds = [
    ('Real Estate Capital Europe', 'https://www.recapitalnews.com/feed/', 2, ['private_equity']),
    ('Private Funds CFO', 'https://www.privatefundscfo.com/feed/', 2, ['private_equity']),
    ('Crunchbase News', 'https://news.crunchbase.com/feed/', 2, ['private_equity']),
    ('TechCrunch', 'https://techcrunch.com/feed/', 2, ['private_equity']),
    ('NYT DealBook', 'https://rss.nytimes.com/services/xml/rss/nyt/DealBook.xml', 2, ['private_equity']),
    ('Top1000Funds', 'https://www.top1000funds.com/feed/', 2, ['private_equity']),
    ('FundFire', 'https://www.fundfire.com/feed/', 2, ['private_equity']),
    ('PE News', 'https://www.privateequitynews.com/feed/', 2, ['private_equity']),
    ('Family Capital', 'https://www.famcap.com/feed/', 2, ['private_equity']),
    ('Bain PE Insights', 'https://www.bain.com/insights/industry/private-equity/feed/', 2, ['private_equity']),
    ('McKinsey PE', 'https://www.mckinsey.com/industries/private-equity-and-principal-investors/our-insights/feed', 2, ['private_equity']),
    # Financial press
    ('Bloomberg Deals', 'https://feeds.bloomberg.com/markets/deals.rss', 2, ['private_equity']),
    ('WSJ Business', 'https://feeds.content.dowjones.io/wsj/public/rss/wsj-business', 2, ['private_equity', 'banking_credit']),
    # Real estate PE crossover
    ('The Real Deal National', 'https://therealdeal.com/national/feed/', 2, ['private_equity', 'commercial_real_estate']),
    ('Connect CRE', 'https://www.connectcre.com/feed/', 2, ['private_equity', 'commercial_real_estate']),
    ('GlobeSt', 'https://www.globest.com/feed/', 2, ['private_equity', 'commercial_real_estate']),
    # VC
    ('AVCJ', 'https://www.avcj.com/feed/', 2, ['private_equity']),
    ('DealStreetAsia', 'https://www.dealstreetasia.com/feed/', 2, ['private_equity']),
    # Allocators
    ('Allocator Intel', 'https://www.allocatorintel.com/feed/', 2, ['private_equity']),
    ('IREI', 'https://irei.com/feed/', 2, ['private_equity']),
    # More
    ('S&P Global PE', 'https://www.spglobal.com/marketintelligence/en/news-insights/latest-news-headlines/private-equity-rss', 2, ['private_equity']),
    ('StrictlyVC', 'https://www.strictlyvc.com/feed/', 2, ['private_equity']),
    ('Mergermarket', 'https://www.mergermarket.com/feed/', 2, ['private_equity']),
]

print(f'Testing {len(feeds)} PE feeds...')
working = []

def test(name, url, tier, sectors):
    try:
        src = {'name': name, 'url': url, 'tier': tier, 'sectors': sectors}
        items, updated, err = fetch_single_feed(src)
        return name, url, len(items), err
    except Exception as e:
        return name, url, 0, str(e)[:60]

with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(test, *f): f for f in feeds}
    for future in as_completed(futures):
        name, url, count, err = future.result()
        if count > 0:
            working.append((name, url, count))
            print(f'  + {name}: {count} items')

print(f'\nNew PE working feeds: {len(working)}')
for name, url, count in sorted(working, key=lambda x: -x[2]):
    print(f'  {name}: {count} items')
