"""Realistic cost analysis for the multi-sector pipeline."""
# DeepSeek pricing: ~$0.27/1M input tokens, ~$1.10/1M output tokens
INPUT_COST = 0.27 / 1_000_000
OUTPUT_COST = 1.10 / 1_000_000

# Per-article LLM calls in the editorial pipeline:
calls = [
    ("Draft (5200 max)",          5000, 2000),
    ("Financial Review (1K)",     2000, 500),
    ("Editorial Review (1K)",     2000, 500),
    ("Revision (5200, conditional)", 5000, 2000),
]

print("PER-ARTICLE LLM COST (DeepSeek pricing)")
print("=" * 50)
total_in = 0
total_out = 0
for name, inp, out in calls:
    cost = (inp * INPUT_COST) + (out * OUTPUT_COST)
    print(f"  {name}: ${cost:.4f}")
    total_in += inp
    total_out += out

full_cost = (total_in * INPUT_COST) + (total_out * OUTPUT_COST)
no_revision = full_cost - (5000 * INPUT_COST + 2000 * OUTPUT_COST)
print(f"  {'-' * 40}")
print(f"  Full pipeline (4 calls): ${full_cost:.4f}")
print(f"  No revision (3 calls):  ${no_revision:.4f}")
print()

# Classification cost
print("CLASSIFICATION COST")
print("=" * 50)
print(f"  94% deterministic = FREE")
print(f"  6% need LLM: 2000 candidates x 6% = 120 calls")
print(f"  Cheap call (~500 tokens in, ~100 out): ${500 * INPUT_COST + 100 * OUTPUT_COST:.4f}")
print(f"  Daily classification: ${120 * (500 * INPUT_COST + 100 * OUTPUT_COST):.2f}")
print()

# Realistic daily scenarios
print("DAILY SCENARIOS")
print("=" * 50)
for n in [3, 5, 10, 15, 20, 30]:
    cost = n * no_revision
    cost_w_rev = n * (no_revision + full_cost - no_revision) * 0.5  # 50% need revision
    total = n * (no_revision + (full_cost - no_revision) * 0.5)
    monthly = total * 30
    print(f"  {n:>2} articles: ${total:.2f}/day = ${monthly:.2f}/month")

print()
print("THE $12.50 FIGURE CAME FROM: 210 articles x $0.05 (wrong model pricing)")
print("REAL COST: ~10-15 articles/day with mixed revision = ~$0.07-0.11/day")
print("MONTHLY: ~$2-$3/month for 10-15 articles/day across all 7 sectors")
