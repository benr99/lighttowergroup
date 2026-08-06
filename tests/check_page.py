"""Check insights page for issues."""
import re

with open('insights.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('site.js', 'r', encoding='utf-8') as f:
    js = f.read()

print('site.js braces:', js.count('{'), 'open,', js.count('}'), 'close')

# Check main inline script
m = re.search(r'const grid = document', html)
print('grid element found:', bool(m))

m = re.search(r'fetch\(\'/insights\.json\'\)', html)
print('insights.json fetch:', bool(m))

m = re.search(r'renderCuratedGrid', html)
print('renderCuratedGrid:', bool(m))

# Check for common issues
if 'FILTERS' in html:
    print('FILTERS object: present')
if 'allPosts' in html:
    print('allPosts variable: present')

# Check the filter buttons match the FILTERS keys
buttons = re.findall(r'data-filter="([^"]+)"', html)
filter_keys = re.findall(r'(\w+):\s*\[', html)
print('Filter buttons:', sorted(buttons))
print('FILTERS keys:', sorted(filter_keys))

# Verify buttons match keys
missing = set(buttons) - set(filter_keys) - {'all'}
extra = set(filter_keys) - set(buttons) - {'all'}
if missing:
    print('MISSING from FILTERS:', missing)
if extra:
    print('MISSING button for:', extra)

print('Done')
