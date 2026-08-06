"""Full pipeline v2 simulation with analytical briefs and editorial pipeline."""
import sys
sys.path.insert(0, 'scripts')

from canonical_item import CanonicalItem
from classification import classify_batch, get_sector_stats
from scoring_engine import score_batch
from ranking import rank_and_select
from analytical_brief import build_analytical_brief
from editorial_pipeline import EditorialPipeline

print('=' * 60)
print('FULL PIPELINE V2 SIMULATION')
print('=' * 60)

# Create diverse stories across 6 non-CRE sectors
stories = [
    ('private_equity', 'KKR Closes $8.5B North America Buyout Fund', 'KKR closed its latest buyout fund at $8.5B, exceeding its $7B target.', 'PE Hub', 2, 8.5e9),
    ('data_centers', 'AWS Leases 200MW Data Center Campus in Ohio', 'AWS signed a 200MW lease at a new hyperscale campus with $500M in construction financing.', 'Data Center Dynamics', 2, 5e8),
    ('energy', 'NextEra Announces $12B Grid Modernization Plan', 'NextEra Energy announced a $12B grid modernization and transmission plan across Florida.', 'Utility Dive', 2, 1.2e10),
    ('banking_credit', 'FDIC Issues New CRE Loan Concentration Guidance', 'The FDIC issued updated guidance requiring regional banks to stress-test CRE portfolios.', 'American Banker', 2, 0),
    ('fed_macro', 'FOMC Minutes Show Divided Committee on Rate Path', 'FOMC minutes revealed a split committee with several members advocating for additional hikes.', 'Federal Reserve', 1, 0),
    ('local_government', 'SF Board Approves Downtown Rezoning for Housing Conversion', 'SF Board of Supervisors approved rezoning allowing office-to-residential conversions.', 'San Francisco Planning', 2, 0),
]
items = []
for sector, headline, summary, source, tier, val in stories:
    item = CanonicalItem()
    item.headline = headline
    item.primary_sector = sector
    item.raw_summary = summary
    item.raw_text = summary
    item.source_name = source
    item.source_tier = tier
    item.transaction_value = val
    item.publication_date = '2026-07-31T10:00:00+00:00'
    items.append(item)

# Classify and score
classified = classify_batch(items)
scored = score_batch(classified)
selected, report = rank_and_select(scored, target_per_sector=5)

print(f'\nSelection: {report["total_selected"]}/{report["total_candidates"]} selected')
for sector, data in sorted(report['per_sector'].items()):
    print(f'  {sector}: {data["count"]} items')

# For each selected story, build analytical brief
print('\n--- Analytical Briefs ---')
for item in scored[:4]:
    brief = build_analytical_brief(item)
    print(f'\n  [{item.primary_sector}] {item.headline[:60]}')
    print(f'    Question: {brief["central_financial_question"][:80]}')
    print(f'    Architecture: {brief["article_architecture"]["name"]}')
    print(f'    Depth: {brief["article_depth"]["depth"]} ({brief["article_depth"]["words"]})')

# Simulate editorial pipeline (offline mode)
print('\n--- Editorial Pipeline (offline, no API key) ---')
for item in scored[:3]:
    pipeline = EditorialPipeline(api_key='')
    result = pipeline.run(item)
    print(f'  {item.headline[:50]}... -> {result["status"]} ({len(result["stages_run"])} stages)')

print(f'\nReady. {len(scored)} stories across {len(set(i.primary_sector for i in scored))} sectors.')
print('With API key, these would be drafted, reviewed, and published.')
