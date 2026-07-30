"""Smoke test for Phase 1 modules: canonical_item, classification, scoring_engine."""
import sys
sys.path.insert(0, 'scripts')

from canonical_item import CanonicalItem
from classification import classify_item, classify_batch, get_sector_stats
from scoring_engine import score_item, score_batch, get_scoring_stats

# Test 1: PE story
print("=== Test 1: Private Equity Story ===")
item = CanonicalItem()
item.headline = 'Blackstone Closes $5B Infrastructure Fund'
item.raw_summary = 'Blackstone has closed its latest infrastructure fund at $5 billion, exceeding its $4 billion target.'
item.raw_text = item.raw_summary
item.source_name = 'PE Hub'
item.source_tier = 2
item.publication_date = '2026-07-30T10:00:00+00:00'

classified = classify_item(item)
print(f"  Primary sector: {classified.primary_sector}")
print(f"  Secondary sectors: {classified.secondary_sectors}")
print(f"  Method: {classified.classification_method}, Confidence: {classified.classification_confidence}")

scored = score_item(classified)
print(f"  Composite score: {scored.composite_score}")
print(f"  Tier: {scored.tier}")
print(f"  Profile: {scored.scoring_profile}")

# Test 2: Data Center story
print("\n=== Test 2: Data Center Story ===")
dc = CanonicalItem()
dc.headline = 'AWS Announces 300MW Data Center Campus in Northern Virginia'
dc.raw_summary = 'Amazon Web Services plans a new 300-megawatt hyperscale data center campus in Loudoun County with $3.5 billion in planned investment.'
dc.raw_text = dc.raw_summary
dc.source_name = 'Data Center Dynamics'
dc.source_tier = 2
dc.publication_date = '2026-07-30T08:00:00+00:00'

dc_classified = classify_item(dc)
dc_scored = score_item(dc_classified)
print(f"  Primary sector: {dc_classified.primary_sector}")
print(f"  Composite score: {dc_scored.composite_score}")
print(f"  Tier: {dc_scored.tier}")
print(f"  Financial magnitude: {dc_scored.financial_magnitude_score}")
print(f"  MW detected: {dc_scored.megawatts}")

# Test 3: Fed story
print("\n=== Test 3: Federal Reserve Story ===")
fed = CanonicalItem()
fed.headline = 'Fed Raises Rates by 25 Basis Points, Signals Possible Pause'
fed.raw_summary = 'The Federal Reserve raised its benchmark rate by 25 bps. Chair Powell signaled data-dependent future decisions.'
fed.raw_text = fed.raw_summary
fed.source_name = 'Federal Reserve'
fed.source_tier = 1
fed.source_authority = 'primary'
fed.publication_date = '2026-07-30T14:00:00+00:00'

fed_classified = classify_item(fed)
fed_scored = score_item(fed_classified)
print(f"  Primary sector: {fed_classified.primary_sector}")
print(f"  Composite score: {fed_scored.composite_score}")
print(f"  Tier: {fed_scored.tier}")
print(f"  Source quality: {fed_scored.source_quality_score}")
print(f"  Policy impact: {fed_scored.policy_impact_score}")

# Test 4: Local Government story
print("\n=== Test 4: Local Government Story ===")
gov = CanonicalItem()
gov.headline = 'NYC Council Approves Mixed-Use Rezoning for Gowanus Development'
gov.raw_summary = 'The New York City Council approved a rezoning for the Gowanus neighborhood that enables 8,500 new apartments including 3,000 affordable units and mixed-use development with retail and community space.'
gov.raw_text = gov.raw_summary
gov.source_name = 'CityLand NYC'
gov.source_tier = 2
gov.publication_date = '2026-07-29T16:00:00+00:00'

gov_classified = classify_item(gov)
gov_scored = score_item(gov_classified)
print(f"  Primary sector: {gov_classified.primary_sector}")
print(f"  Secondary sectors: {gov_classified.secondary_sectors}")
print(f"  Composite score: {gov_scored.composite_score}")
print(f"  Tier: {gov_scored.tier}")

# Test 5: Batch processing
print("\n=== Test 5: Batch Processing ===")
items = [item, dc, fed, gov]
batch = classify_batch(items)
scored_batch = score_batch(batch)
stats = get_scoring_stats(scored_batch)
sector_stats = get_sector_stats(batch)
print(f"  Items classified: {stats['total_items']}")
print(f"  Sector distribution: {sector_stats}")
print(f"  Tier distribution: {stats['tier_distribution']}")
for s, d in sorted(stats['sector_stats'].items()):
    print(f"  {s}: {d['count']} items, avg composite {d['avg_composite']}")

print("\n=== ALL TESTS PASSED ===")
