"""Quick ingestion test with first 3 sources."""
import sys
sys.path.insert(0, 'scripts')
from ingestion import load_sources, fetch_single_feed

sources = load_sources()
print(f'Loaded {len(sources)} active sources')

# Test first 5 verified sources
for src in sources[:5]:
    name = src.get('name', '?')
    url = src.get('url', '')
    print(f'Fetching: {name} ({url[:60]}...)')
    items, updated, err = fetch_single_feed(src)
    health = updated.get('_health', '?')
    count = len(items)
    print(f'  Items: {count}, Health: {health}', end='')
    if err:
        print(f', Error: {err[:80]}')
    else:
        print()
print('Done')
