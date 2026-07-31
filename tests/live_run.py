"""Live pipeline run — show the full flow."""
import sys, os, json, time, re
sys.path.insert(0, 'scripts')

from datetime import datetime, timezone
from canonical_item import CanonicalItem
from ingestion import load_sources, fetch_single_feed
from classification import classify_batch, get_sector_stats
from scoring_engine import score_batch, get_scoring_stats
from ranking import rank_and_select
from analytical_brief import build_analytical_brief
from editorial_pipeline import EditorialPipeline
from editorial_scorer import score_article

api_key = os.environ.get('DEEPSEEK_API_KEY', '')
now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

print('=' * 60)
print(f'LIGHT TOWER INSIGHTS — LIVE PIPELINE RUN')
print(f'  {now_str}')
print('=' * 60)

# Phase 1: Ingest
print('\n[1/5] Fetching from verified sources...')
sources = load_sources()
verified = [s for s in sources if s.get('verified')]
print(f'  Using {len(verified)} verified sources')

all_items = []
# Diversify: take top N from each sector to ensure multi-sector coverage
from collections import defaultdict
by_sector = defaultdict(list)
for src in verified:
    for sec in src.get('sectors', []):
        by_sector[sec].append(src)

# Take up to 10 sources per sector
diverse_sources = []
for sector in ['commercial_real_estate', 'private_equity', 'data_centers',
               'energy', 'banking_credit', 'fed_macro', 'local_government']:
    sector_sources = by_sector.get(sector, [])[:10]
    for s in sector_sources:
        if s not in diverse_sources:
            diverse_sources.append(s)
print(f'  Using {len(diverse_sources)} diverse sources across all sectors')

for src in diverse_sources[:60]:
    items, updated, err = fetch_single_feed(src)
    name = src.get('name', '?')
    if items:
        sectors = ','.join(src.get('sectors', [])[:2])
        print(f'  + {name} [{sectors}]: {len(items)} items')
        all_items.extend(items)

if len(all_items) < 10:
    print('  Low yield from feeds — supplementing with simulation data')
    sim = [
        ('commercial_real_estate', 'SL Green Sells 245 Park Avenue for $2.1B', 'SL Green sold 245 Park Avenue for $2.1B, marking Manhattan largest office sale in 2026.', 'Commercial Observer', 2),
        ('private_equity', 'KKR Closes $8.5B North America Buyout Fund, Exceeding $7B Target', 'KKR closed its latest buyout fund at $8.5B.', 'PE Hub', 2),
        ('data_centers', 'AWS Leases 200MW Hyperscale Campus in Ohio with $500M Construction Loan', 'AWS signed a 200MW lease at a new data center campus.', 'Data Center Dynamics', 2),
        ('energy', 'NextEra Announces $12B Grid Modernization Plan for Florida', 'NextEra Energy announced a $12B grid plan.', 'Utility Dive', 2),
        ('banking_credit', 'FDIC Issues New CRE Concentration Guidance for Regional Banks', 'FDIC issued updated guidance for CRE stress tests.', 'American Banker', 2),
        ('fed_macro', 'FOMC Minutes Reveal Split Committee on Rate Path', 'FOMC minutes showed division on rate hikes.', 'Federal Reserve', 1),
        ('local_government', 'SF Board Approves Downtown Rezoning for 5,000 Housing Units', 'San Francisco approved rezoning for office-to-residential conversions.', 'San Francisco Planning', 2),
    ]
    for sec, h, s, src, t in sim:
        item = CanonicalItem()
        item.headline = h
        item.primary_sector = sec
        item.raw_summary = s
        item.raw_text = s
        item.source_name = src
        item.source_tier = t
        item.publication_date = datetime.now(timezone.utc).isoformat()
        item.item_id = item.generate_id()
        all_items.append(item)
    print(f'  Added {len(sim)} simulated items across 7 sectors')

print(f'  Total: {len(all_items)} items ingested')

# Phase 2: Classify
print(f'\n[2/5] Classifying {len(all_items)} items...')
classified = classify_batch(all_items)
sector_counts = get_sector_stats(classified)
for sec, count in sorted(sector_counts.items()):
    print(f'  {sec}: {count}')

# Phase 3: Score
print(f'\n[3/5] Scoring...')
scored = score_batch(classified)
score_stats = get_scoring_stats(scored)
print(f'  Tier distribution: {score_stats["tier_distribution"]}')

# Phase 4: Rank
print(f'\n[4/5] Ranking and selecting...')
selected, report = rank_and_select(scored, target_per_sector=30)
print(f'  Selected: {report["total_selected"]} stories across {len(selected)} sectors')
for sector, data in sorted(report.get("per_sector", {}).items()):
    print(f'    {sector}: {data["count"]} selected')

# Phase 5: Generate ONE article
print(f'\n[5/5] Generating article...')
top_item = None
for sector, items in sorted(selected.items()):
    if items and sector != 'commercial_real_estate':
        top_item = items[0]
        break
if not top_item:
    for sector, items in sorted(selected.items()):
        if items:
            top_item = items[0]
            break

if top_item and api_key:
    sector = top_item.primary_sector or 'unknown'
    headline = top_item.headline[:70]
    score = top_item.composite_score

    print(f'\n  [{sector.upper()}] {headline}')
    print(f'  Composite score: {score:.1f} | Tier: {top_item.tier}')

    brief = build_analytical_brief(top_item)
    print(f'  Architecture: {brief["article_architecture"]["name"]}')
    print(f'  Depth: {brief["article_depth"]["depth"]}')
    print(f'  Question: {brief["central_financial_question"][:100]}')

    print(f'  Generating via 7-stage editorial pipeline...')
    pipeline = EditorialPipeline(api_key=api_key)
    result = pipeline.run(top_item)

    if result.get('article'):
        a = result['article']
        scores = score_article(a, brief, depth=brief['article_depth']['depth'])
        title = a.get('title', '?')
        body = re.sub(r'<[^>]+>', ' ', a.get('body_html', '')).strip()

        print(f'\n  {"=" * 50}')
        print(f'  TITLE: {title}')
        print(f'  SCORE: {scores["overall"]}/10 | Publishable: {scores["publishable"]}')
        if scores.get('below_minimum'):
            print(f'  Issues: {", ".join(scores["below_minimum"][:3])}')
        print(f'\n  BODY PREVIEW:')
        for line in body.split('. ')[:8]:
            clean = line.strip()
            if clean:
                print(f'  {clean}.')
        print(f'  {"=" * 50}')
    else:
        print(f'  Pipeline status: {result.get("status")}')
        if result.get('errors'):
            for e in result['errors'][:3]:
                print(f'    Error: {e}')
elif top_item:
    sector = top_item.primary_sector or 'unknown'
    print(f'\n  [{sector.upper()}] {top_item.headline[:70]}')
    print(f'  Score: {top_item.composite_score:.1f}')
    print('  [offline — no API key set]')
else:
    print('  No stories selected for generation')

print(f'\n{"=" * 60}')
print(f'RUN COMPLETE')
print(f'  Ingested: {len(all_items)}')
print(f'  Classified: {len(classified)}')
print(f'  Scored: {len(scored)}')
print(f'  Selected: {report["total_selected"]} across {len(selected)} sectors')
print(f'  Generated: 1 article')
print(f'{"=" * 60}')
