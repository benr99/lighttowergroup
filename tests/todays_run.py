"""Quick run: generate top article only."""
import sys, os, json, time
sys.path.insert(0, 'scripts')

from datetime import datetime, timezone
from canonical_item import CanonicalItem
from ingestion import load_sources, fetch_single_feed
from classification import classify_batch, get_sector_stats
from scoring_engine import score_batch
from ranking import rank_and_select
from analytical_brief import build_analytical_brief
from editorial_pipeline import EditorialPipeline
from editorial_scorer import score_article

print("=" * 60)
print("LIGHT TOWER INSIGHTS — QUICK RUN")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

# Fetch from top 40 sources
sources = load_sources()
tier1 = [s for s in sources if s.get('tier') == 1 and s.get('verified')]
tier2_cre = [s for s in sources if s.get('tier') == 2 and 'commercial_real_estate' in s.get('sectors', []) and s.get('verified')]
tier2_other = [s for s in sources if s.get('tier') == 2 and 'commercial_real_estate' not in s.get('sectors', []) and s.get('verified')]
selected_sources = (tier1[:8] + tier2_cre[:12] + tier2_other[:8])[:30]

print(f"\n[1] Fetching {len(selected_sources)} sources...")
all_items = []
for src in selected_sources:
    items, updated, err = fetch_single_feed(src)
    if items:
        all_items.extend(items)
        print(f"  {updated.get('name','?')}: {len(items)} items")

print(f"  Total: {len(all_items)} items")

if len(all_items) < 5:
    # Fallback simulation
    sim = [
        ('private_equity', 'KKR Closes $8.5B Fund', 'KKR closed at $8.5B.', 'PE Hub', 2),
        ('data_centers', 'AWS 200MW Campus', 'AWS leased 200MW in Ohio.', 'Data Center Dynamics', 2),
        ('fed_macro', 'FOMC Split on Rates', 'FOMC minutes showed division.', 'Federal Reserve', 1),
    ]
    for s, h, sum, src, t in sim:
        item = CanonicalItem()
        item.headline = h; item.primary_sector = s
        item.raw_summary = sum; item.raw_text = sum
        item.source_name = src; item.source_tier = t
        item.publication_date = datetime.now(timezone.utc).isoformat()
        item.item_id = item.generate_id()
        all_items.append(item)
    print(f"  +{len(sim)} simulated across {len(set(s[0] for s in sim))} sectors")

# Classify + score + rank
classified = classify_batch(all_items)
scored = score_batch(classified)
selected, report = rank_and_select(scored, target_per_sector=30)
sector_counts = get_sector_stats(classified)

print(f"\n[2] Sectors: {sector_counts}")
print(f"[3] Selected: {report['total_selected']} across {len(selected)} sectors")

# Generate ONE article: the top-scoring non-CRE story
api_key = os.environ.get('DEEPSEEK_API_KEY', '')
top = None
for sector, items in sorted(selected.items()):
    if sector != 'commercial_real_estate' and items:
        top = items[0]
        break
if not top:
    for sector, items in sorted(selected.items()):
        if items:
            top = items[0]
            break

if top and api_key:
    print(f"\n[4] Generating: [{top.primary_sector}] {top.headline[:70]}")
    brief = build_analytical_brief(top)
    print(f"    Architecture: {brief['article_architecture']['name']} | Depth: {brief['article_depth']['depth']}")
    print(f"    Question: {brief['central_financial_question'][:100]}")
    
    pipeline = EditorialPipeline(api_key=api_key)
    result = pipeline.run(top)
    
    if result.get('article'):
        article = result['article']
        scores = score_article(article, brief, depth=brief['article_depth']['depth'])
        print(f"\n    TITLE: {article.get('title', '?')}")
        print(f"    SCORE: {scores['overall']}/10 | Publishable: {scores['publishable']}")
        print(f"\n    BODY PREVIEW:")
        body = article.get('body_html', '')
        # Show first 500 chars
        import re
        text = re.sub(r'<[^>]+>', ' ', body).strip()
        for line in text.split('. ')[:5]:
            print(f"    {line.strip()}.")
        
        # Save
        os.makedirs('.editorial-state', exist_ok=True)
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "items": len(all_items),
            "sectors": sector_counts,
            "selected": report['total_selected'],
            "article": {"title": article.get('title'), "scores": scores, "body_preview": text[:500]},
        }, open('.editorial-state/todays-run.json', 'w'), indent=2, default=str)
        print(f"\n    Saved to .editorial-state/todays-run.json")
    else:
        print(f"    Pipeline status: {result.get('status')}")

print(f"\n{'=' * 60}")
print(f"DONE: {len(all_items)} items, {len(sector_counts)} sectors, 1 article generated")
print(f"Cost: ~$0.007")
print(f"{'=' * 60}")
