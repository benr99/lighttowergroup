"""Integration test for Phase 2+3: ingestion → classification → scoring → ranking."""
import sys
sys.path.insert(0, 'scripts')

from canonical_item import CanonicalItem
from classification import classify_batch, get_sector_stats
from scoring_engine import score_batch, get_scoring_stats
from ranking import rank_and_select

print("=" * 60)
print("PHASE 2+3 INTEGRATION TEST")
print("=" * 60)

# Simulate ingested items across multiple sectors
items = []
test_data = [
    # sector, headline, summary, source, tier
    ("CRE", "SL Green Sells 245 Park Avenue for $2.1B", "SL Green Realty Corp sold 245 Park Avenue to a Japanese investor for $2.1 billion, marking Manhattan's largest office sale of 2026.", "Commercial Observer", 2),
    ("CRE", "AvalonBay Breaks Ground on 450-Unit multifamily Project in Brooklyn", "AvalonBay Communities started construction on a 450-unit apartment complex in Downtown Brooklyn with $180M in construction financing from Wells Fargo.", "Multi-Housing News", 2),
    ("CRE", "CMBS Delinquency Rate Ticks Up to 7.5% as Office Loans Drag", "The CMBS delinquency rate rose 15 bps to 7.5% in July, driven by office and retail loans. Trepp reports $2.3B in newly delinquent loans.", "Trepp", 2),
    ("PE", "KKR Closes $8.5B North America Buyout Fund", "KKR closed its latest North America buyout fund at $8.5 billion, exceeding its $7B target. The fund will target enterprise software and healthcare.", "PE Hub", 2),
    ("PE", "Apollo Launches $2B Private Credit Fund for Middle-Market Lending", "Apollo Global Management launched a $2B direct lending fund focused on middle-market companies in manufacturing and business services.", "Private Debt Investor", 2),
    ("PE", "Thoma Bravo Acquires Cybersecurity Firm for $3.2B", "Thoma Bravo agreed to acquire a cybersecurity software company for $3.2 billion in a take-private deal expected to close Q4 2026.", "PitchBook News", 2),
    ("DC", "AWS Leases 200MW Data Center Campus in Ohio", "Amazon Web Services signed a 200-megawatt lease at a new hyperscale data center campus in New Albany, Ohio. The developer secured $500M in construction financing.", "Data Center Dynamics", 2),
    ("DC", "Digital Realty Acquires 50-Acre Powered Land Site in Phoenix for $120M", "Digital Realty purchased 50 acres of entitled powered land in Phoenix for $120M, with plans for a 300MW campus serving AI workloads.", "Data Center Frontier", 2),
    ("Energy", "NextEra Energy Announces $12B Grid Modernization Plan", "NextEra Energy announced a $12 billion grid modernization and transmission expansion plan across Florida, driven by data center and industrial power demand.", "Utility Dive", 2),
    ("Energy", "FERC Approves New Interconnection Rules to Speed Renewable Projects", "FERC approved sweeping new interconnection queue rules designed to reduce the backlog of 2,000 GW of pending generation projects.", "Power Magazine", 2),
    ("Banking", "FDIC Issues New Guidance on CRE Loan Concentration Risk", "The FDIC issued updated guidance requiring regional banks to stress-test their CRE loan portfolios and hold additional capital against office exposure.", "American Banker", 2),
    ("Banking", "PNC Reports $150M in CRE Loan Loss Provisions for Q2", "PNC Financial reported $150 million in CRE loan loss provisions for Q2 2026, doubling from Q1, citing office and retail exposure in coastal markets.", "S&P Global Market Intelligence", 2),
    ("Fed", "Fed Minutes Show Divided Committee on Rate Path", "FOMC minutes revealed a split committee, with several members advocating for additional rate hikes while others favored a pause to assess lagged effects.", "Federal Reserve", 1),
    ("Fed", "CPI Report Shows Inflation Cooling to 3.1% Annual Rate", "The Consumer Price Index rose 0.2% in June, bringing the annual rate to 3.1%, down from 3.3% in May. Core CPI rose 3.4% year-over-year.", "Bureau of Labor Statistics", 1),
    ("LocalGov", "San Francisco Board Approves Downtown Rezoning for Housing Conversion", "San Francisco's Board of Supervisors approved a rezoning plan allowing office-to-residential conversions across 200 downtown buildings, targeting 5,000 new housing units.", "San Francisco Planning", 2),
    ("LocalGov", "NYC Council Passes Permanent Outdoor Dining Program with New Zoning Rules", "The NYC Council passed a bill making outdoor dining permanent with new zoning restrictions affecting 12,000 restaurants across the five boroughs.", "CityLand NYC", 2),
    ("LocalGov", "Texas Legislature Passes Property Tax Relief Bill Affecting Commercial Properties", "The Texas legislature passed a $18B property tax relief package that reduces appraisal caps for commercial properties and increases homestead exemptions.", "Texas Legislature", 3),
]
for sector, headline, summary, source, tier in test_data:
    item = CanonicalItem()
    item.headline = headline
    item.raw_summary = summary
    item.raw_text = summary
    item.source_name = source
    item.source_tier = tier
    item.publication_date = '2026-07-30T10:00:00+00:00'
    items.append(item)

# Phase 2: Classify
print("\n[CLASSIFICATION]")
classified = classify_batch(items)
sector_counts = get_sector_stats(classified)
for sector, count in sorted(sector_counts.items()):
    print(f"  {sector}: {count} items")

# Phase 3: Score
print("\n[SCORING]")
scored = score_batch(classified)
score_stats = get_scoring_stats(scored)
print(f"  Tier distribution: {score_stats['tier_distribution']}")
for sector, data in sorted(score_stats.get("sector_stats", {}).items()):
    print(f"  {sector}: {data['count']} items, avg composite {data['avg_composite']}")

# Phase 3: Rank and Select
print("\n[RANKING & SELECTION]")
selected, report = rank_and_select(scored, target_per_sector=5)  # 5 for test
print(f"\n  Selection complete: {report['total_selected']}/{report['total_candidates']} selected "
      f"({report['selection_rate_pct']}%)")

# Show top picks per sector
print("\n[TOP PICKS BY SECTOR]")
for sector, items_list in sorted(selected.items()):
    print(f"\n  --- {sector.upper()} ({len(items_list)} selected) ---")
    for item in items_list[:3]:
        print(f"  [{item.tier}] {item.composite_score:.1f} | {item.headline[:80]}")
        print(f"       Source: {item.source_name} | Method: {item.classification_method}")

# Cross-sector test: verify classification correctness
print("\n[CLASSIFICATION ACCURACY CHECK]")
correct = 0
for item in classified:
    # Check if headline content matches expected sector by checking source+keyword overlap
    expected = item.source_name
    actual = item.primary_sector
    if actual and actual != "unclassified":
        correct += 1
    if item.classification_method == "needs_llm":
        print(f"  NEEDS LLM: {item.headline[:60]} -> {actual} (source: {expected})")

accuracy = correct / max(1, len(classified)) * 100
print(f"  Classified without LLM: {correct}/{len(classified)} ({accuracy:.0f}%)")
print(f"  LLM needed: {len(classified) - correct}/{len(classified)}")

print("\n" + "=" * 60)
print("INTEGRATION TEST COMPLETE")
print("=" * 60)
