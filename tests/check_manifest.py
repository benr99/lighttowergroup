import json, os

with open('insights.json', encoding='utf-8') as f:
    m = json.load(f)

print(f'Entries: {len(m)}')
size = os.path.getsize('insights.json')
print(f'File size: {size:,} bytes ({size/1024:.0f} KB)')

# Check for entries with missing fields
bad = []
for i, e in enumerate(m):
    title = e.get('title', '?')[:40]
    if not e.get('date'):
        bad.append(f'Entry {i}: missing date - {title}')
    if not e.get('category'):
        bad.append(f'Entry {i}: missing category - {title}')
    if not e.get('url'):
        bad.append(f'Entry {i}: missing url')

if bad:
    for b in bad[:10]:
        print(b)
    print(f'Total bad entries: {len(bad)}')
else:
    print('All entries have required fields')

# Check duplicate slugs
slugs = [e.get('slug','') for e in m]
dupes = set()
seen = set()
for s in slugs:
    if s in seen:
        dupes.add(s)
    seen.add(s)
if dupes:
    print(f'Duplicate slugs: {len(dupes)}')
    for d in list(dupes)[:5]:
        print(f'  {d}')
else:
    print('No duplicate slugs')
