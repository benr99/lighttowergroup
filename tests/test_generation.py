"""Test generation module and sector prompts."""
import sys
sys.path.insert(0, 'scripts')

from sector_prompts import (
    PE_SYSTEM_PROMPT, DC_SYSTEM_PROMPT, ENERGY_SYSTEM_PROMPT,
    BANKING_SYSTEM_PROMPT, FED_SYSTEM_PROMPT, LOCALGOV_SYSTEM_PROMPT,
)
from generation import get_sector_prompt, get_generation_stats, build_generation_context
from canonical_item import CanonicalItem

# Test prompt loading
print("=== Sector Prompts ===")
prompts = {
    "PE": PE_SYSTEM_PROMPT,
    "DC": DC_SYSTEM_PROMPT,
    "Energy": ENERGY_SYSTEM_PROMPT,
    "Banking": BANKING_SYSTEM_PROMPT,
    "Fed/Macro": FED_SYSTEM_PROMPT,
    "LocalGov": LOCALGOV_SYSTEM_PROMPT,
}
for name, prompt in prompts.items():
    words = len(prompt.split())
    print(f"  {name}: {words} words, starts with: {prompt[:60].strip()}...")

# Test routing
print("\n=== Prompt Routing ===")
for sector in ['commercial_real_estate', 'private_equity', 'data_centers', 
               'energy', 'banking_credit', 'fed_macro', 'local_government', 'unknown']:
    prompt = get_sector_prompt(sector)
    words = len(prompt.split())
    print(f"  {sector}: {words} words")

# Test generation stats
print("\n=== Generation Stats ===")
items = {}
for sector in ['commercial_real_estate', 'private_equity', 'data_centers', 
               'energy', 'banking_credit', 'fed_macro', 'local_government']:
    items[sector] = []
    for i in range(3):
        item = CanonicalItem()
        item.primary_sector = sector
        item.headline = f'Test story {i} for {sector}'
        items[sector].append(item)

stats = get_generation_stats(items)
for sector, data in sorted(stats.items()):
    if sector == "total":
        print(f"  TOTAL: {data['articles']} articles, ~{data['estimated_words']} words")
        continue
    if isinstance(data, dict):
        print(f"  {sector}: {data['articles']} articles, ~{data['estimated_words']} words")

# Test build context
print("\n=== Build Context ===")
item = CanonicalItem()
item.headline = "KKR Closes $8.5B North America Buyout Fund"
item.primary_sector = "private_equity"
item.event_type = "fund_close"
item.source_name = "PE Hub"
item.source_tier = 2
item.composite_score = 56.5
item.tier = "tier_3_useful_coverage"
item.raw_summary = "KKR closed its latest buyout fund at $8.5B, exceeding target."
item.companies = ["KKR"]
ctx = build_generation_context(item)
for k, v in ctx.items():
    print(f"  {k}: {v}")

print("\n=== ALL GENERATION TESTS PASSED ===")
