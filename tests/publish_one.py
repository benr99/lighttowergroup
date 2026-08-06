"""Generate and publish the CyrusOne data center article."""
import sys, os, json, re
sys.path.insert(0, 'scripts')

from datetime import datetime, timezone
from canonical_item import CanonicalItem
from analytical_brief import build_analytical_brief
from editorial_pipeline import EditorialPipeline
from editorial_scorer import score_article

api_key = os.environ.get('DEEPSEEK_API_KEY', '')
if not api_key:
    print("No API key. Cannot generate.")
    sys.exit(1)

# Build the item from the live run
item = CanonicalItem()
item.headline = "CyrusOne files to develop three buildings for $1.5bn data center campu"
item.primary_sector = "data_centers"
item.raw_summary = "CyrusOne filed permits to develop three buildings for a $1.5 billion data center campus in Fairfield, Texas, roughly halfway between Dallas and Houston. Construction on two buildings has started; the third breaks ground next month. No tenant has been publicly named, suggesting CyrusOne is building speculatively or under an NDA with a hyperscaler."
item.raw_text = item.raw_summary
item.source_name = "Data Center Dynamics"
item.source_url = "https://www.datacenterdynamics.com/"
item.source_tier = 2
item.composite_score = 51.7
item.tier = "tier_3_useful_coverage"
item.publication_date = datetime.now(timezone.utc).isoformat()
item.item_id = item.generate_id()
item.companies = ["CyrusOne"]
item.megawatts = 0.0
item.transaction_value = 1.5e9
item.transaction_value_raw = "$1.5 billion"

print("Building analytical brief...")
brief = build_analytical_brief(item)
print(f"  Architecture: {brief['article_architecture']['name']}")
print(f"  Depth: {brief['article_depth']['depth']}")

print("Generating via 7-stage editorial pipeline...")
pipeline = EditorialPipeline(api_key=api_key)
result = pipeline.run(item)

if not result.get('article'):
    print('FAILED:', result.get('errors', []))
    sys.exit(1)

llm_article = result['article']
print(f"  Title: {llm_article.get('title', '?')[:80]}")

# Build complete article dict for render_html
now = datetime.now(timezone.utc)
title = llm_article.get('title', 'Untitled')
slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:60].strip('-')

article = {
    'title': title,
    'subtitle': llm_article.get('subtitle', ''),
    'slug': slug,
    'category': 'Data Centers',
    'meta_description': llm_article.get('excerpt', llm_article.get('meta_description', ''))[:160],
    'excerpt': llm_article.get('excerpt', '')[:200],
    'body_html': llm_article.get('body_html', ''),
    'sources': llm_article.get('sources', [{'url': item.source_url, 'name': item.source_name}]),
    'tags': llm_article.get('tags', ['CyrusOne', 'data centers', 'Texas', 'hyperscale', 'speculative development']),
    'date': now.strftime('%Y-%m-%d'),
    'date_iso': now.isoformat(),
    'read_time': max(1, round(len(re.sub(r'<[^>]+>', ' ', llm_article.get('body_html', '')).split()) / 225)),
    'source_name': item.source_name,
    'source_url': item.source_url,
    'social_image': '',
    'editorial_format': 'brief',
    'editorial_format_label': 'Data Center Intelligence',
    'franchise': {'name': 'Data Centers', 'promise': ''},
    'data_points': [],
}

# Render full HTML
from daily_news_agent import render_html
html = render_html(article)

# Write to disk
out_path = f'insights/{slug}.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  Written: {out_path} ({len(html)} bytes)")

# Update manifest
manifest = json.load(open('insights.json', encoding='utf-8'))
existing = {e.get('slug', '') for e in manifest}
if slug not in existing:
    manifest.insert(0, {
        'title': title, 'slug': slug,
        'date': now.strftime('%Y-%m-%d'),
        'readTime': article['read_time'],
        'category': 'Data Centers',
        'excerpt': article['excerpt'],
        'url': f'/insights/{slug}.html',
        'tags': article['tags'],
    })
    json.dump(manifest, open('insights.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"  Manifest: {len(manifest)} entries (+1)")
else:
    print(f"  Already in manifest — updating")
    for e in manifest:
        if e.get('slug') == slug:
            e['title'] = title
            e['excerpt'] = article['excerpt']
            e['tags'] = article['tags']
            break
    json.dump(manifest, open('insights.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

# Score
scores = score_article(article, brief, depth='standard')
print(f"  Score: {scores['overall']}/10 | Publishable: {scores['publishable']}")

# Body preview
body_text = re.sub(r'<[^>]+>', ' ', llm_article.get('body_html', '')).strip()
print(f"\n{'=' * 60}")
print(f"PUBLISHED: {title}")
print(f"URL: /insights/{slug}.html")
print(f"{'=' * 60}")
for line in body_text.split('. ')[:6]:
    print(f"  {line.strip()}.")
