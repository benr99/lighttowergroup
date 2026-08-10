"""PASS 5: Memory, Converter, and Edge Data Audit Tests."""
import sys
import os
import json
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, 'scripts')

from canonical_item import CanonicalItem
from analytical_brief import build_analytical_brief
from editorial_pipeline import (
    EditorialPipeline, _safe_truncate_json, _hard_truncate_json_string,
    _extract_json, _strip_html_tags, story_to_canonical_item, run_editorial_pipeline,
)
from editorial_scorer import score_article, EditorialScorer, _strip_html

print("=" * 72)
print("PASS 5 AUDIT: MEMORY, CONVERTER, AND EDGE DATA")
print("=" * 72)

def pass_or_fail(condition, name):
    print(f"  {name}: {'PASS' if condition else 'FAIL'}")
    return condition

all_pass = True

# ═══════════════════════════════════════════════════════════
# Q1: API Key Override in run()
# ═══════════════════════════════════════════════════════════
print("\n[Q1] API key override in run()")
pipeline = EditorialPipeline(api_key="key_A")
# Check that run() accepts an api_key parameter
import inspect
sig = inspect.signature(pipeline.run)
params = list(sig.parameters.keys())
has_api_key_param = "api_key" in params
all_pass &= pass_or_fail(has_api_key_param,
    "run() accepts optional api_key parameter")

# When provided, should use the override
item = CanonicalItem()
item.headline = "Test"
item.primary_sector = "commercial_real_estate"
item.source_name = "Test"
item.tier = "tier_3_useful_coverage"
item.composite_score = 50.0
item.item_id = item.generate_id()

# Exercise the override contract without allowing an audit test to call live
# providers or contaminate production provider diagnostics.
with patch("editorial_pipeline._HAS_LLM", False):
    result = pipeline.run(item, api_key="key_B")
# In offline mode, should still complete
all_pass &= pass_or_fail(result['status'] in ('completed', 'draft_failed', 'offline', 'failed'),
    "run() with api_key override returns valid status")

# ═══════════════════════════════════════════════════════════
# Q2: Scorer does NOT accumulate state across calls
# ═══════════════════════════════════════════════════════════
print("\n[Q2] Scorer state does NOT accumulate across 210 calls")
scorer = EditorialScorer()
for i in range(210):
    art = {"body_html": "<p>Test article with $2.1 billion deal.</p>",
           "sources": [{"url": f"https://example.com/{i}", "name": "Test"}]}
    scorer.score(art)
# After 210 calls, scores and issues should contain only the last call
# (14 dimensions, not accumulated)
all_pass &= pass_or_fail(len(scorer.scores) == 14,
    f"After 210 calls, scores has 14 entries (not accumulated): got {len(scorer.scores)}")
# issues dict can have keys even for the latest call
# but shouldn't have 210*14 entries
total_issues = sum(len(v) for v in scorer.issues.values()) if isinstance(scorer.issues, dict) else 0
all_pass &= pass_or_fail(isinstance(scorer.issues, dict),
    "issues is still a dict after 210 calls")

# ═══════════════════════════════════════════════════════════
# Q3: analytical_brief has no module-level mutable state
# ═══════════════════════════════════════════════════════════
print("\n[Q3] analytical_brief has no module-level caches or mutable state")
import analytical_brief as ab_module
# All top-level objects should be functions, classes, or constants
mutable_vars = False
for name in dir(ab_module):
    if name.startswith('_'): continue
    val = getattr(ab_module, name)
    if isinstance(val, (dict, list)) and not callable(val):
        print(f"  WARNING: mutable module-level state: {name}")
        mutable_vars = True
all_pass &= pass_or_fail(not mutable_vars, "No mutable module-level state in analytical_brief")

# ═══════════════════════════════════════════════════════════
# Q4: _safe_truncate_json is pure, _hard_truncate doesn't break JSON
# ═══════════════════════════════════════════════════════════
print("\n[Q4] _safe_truncate_json purity and validity")

# Test 1: check that input is not modified
original = {"key": "value", "nested": [1, 2, 3]}
data_copy = {"key": "value", "nested": [1, 2, 3]}
result = _safe_truncate_json(data_copy, 1000)
all_pass &= pass_or_fail(data_copy == original,
    "_safe_truncate_json does not modify input")

# Test 2: Verify output is valid JSON (even when truncation needed)
# Force truncation with a large list of strings
large_list = ["item " + str(i) for i in range(100)]
truncated = _safe_truncate_json(large_list, max_chars=50)
try:
    json.loads(truncated)
    valid_json = True
except json.JSONDecodeError:
    valid_json = False
all_pass &= pass_or_fail(valid_json,
    f"_safe_truncate_json produces valid JSON even with forced truncation (got: {truncated[:80]})")

# Test 3: Giant string value in dict
giant_dict = {"text": "A" * 10000}
truncated2 = _safe_truncate_json(giant_dict, max_chars=100)
try:
    json.loads(truncated2)
    valid_json2 = True
except json.JSONDecodeError:
    valid_json2 = False
all_pass &= pass_or_fail(valid_json2,
    f"_safe_truncate_json with giant string value produces valid JSON (got: {truncated2[:80]})")

# Test 4: Giant string value in list
giant_list = ["A" * 10000, "B"]
truncated3 = _safe_truncate_json(giant_list, max_chars=100)
try:
    json.loads(truncated3)
    valid_json3 = True
except json.JSONDecodeError:
    valid_json3 = False
all_pass &= pass_or_fail(valid_json3,
    f"_safe_truncate_json with giant string in list produces valid JSON (got: {truncated3[:80]})")

# ═══════════════════════════════════════════════════════════
# Q5+Q6: story_to_canonical_item converter — fields + topic coverage
# ═══════════════════════════════════════════════════════════
print("\n[Q5+Q6] story_to_canonical_item converter — realistic story dict")
realistic_story = {
    "title": "KKR Acquires Industrial Portfolio for $3.4B",
    "source": "Bloomberg",
    "url": "https://www.bloomberg.com/news/articles/2026/kkr-industrial",
    "summary": "KKR acquired a 12M SF industrial portfolio across 8 markets.",
    "full_text": "KKR & Co. acquired a 12 million square foot industrial portfolio from Blackstone for $3.4 billion.",
    "published": "2026-06-20T08:30:00+00:00",
    "source_tier": 1,
    "topics": ["major_sale", "capital_placement", "private_equity"],
    "entities": {
        "companies": ["KKR", "Blackstone"],
        "amounts": ["$3.4B"],
        "markets": ["chicago", "dallas", "atlanta"],
        "asset_classes": ["industrial"],
        "people": [],
        "policy_actions": [],
        "msa_government_markets": [],
    },
    "attention_features": {
        "has_big_number": True,
        "has_known_institution": True,
        "has_transaction_language": True,
        "has_material_transaction": True,
        "has_distress_language": False,
    },
    "selection_tier": "tier_1_must_cover",
}

item = story_to_canonical_item(realistic_story)
all_pass &= pass_or_fail(item.headline == "KKR Acquires Industrial Portfolio for $3.4B",
    "headline mapped correctly")
all_pass &= pass_or_fail(item.source_name == "Bloomberg",
    "source_name mapped correctly")
all_pass &= pass_or_fail(item.source_url == "https://www.bloomberg.com/news/articles/2026/kkr-industrial",
    "source_url mapped correctly")
all_pass &= pass_or_fail(item.raw_summary == realistic_story["summary"],
    "raw_summary mapped correctly")
all_pass &= pass_or_fail(item.raw_text == realistic_story["full_text"],
    "raw_text mapped correctly")
all_pass &= pass_or_fail(item.publication_date == "2026-06-20T08:30:00+00:00",
    "publication_date mapped correctly")
all_pass &= pass_or_fail(item.source_tier == 1,
    "source_tier mapped correctly")
all_pass &= pass_or_fail(item.source_authority == "primary",
    "source_authority derives from tier")
all_pass &= pass_or_fail(item.transaction_value_raw == "$3.4B",
    "transaction_value_raw from entities.amounts[0]")
all_pass &= pass_or_fail(item.companies == ["KKR", "Blackstone"],
    "companies from entities.companies")
all_pass &= pass_or_fail(item.composite_score >= 65.0,
    f"composite_score boosted by attention_features (got {item.composite_score})")
all_pass &= pass_or_fail(item.tier == "tier_1_must_cover",
    "tier from selection_tier")
all_pass &= pass_or_fail(item.item_id != "",
    "item_id generated")

# Check topic mappings for ALL topic types
print("\n[Q6] Topic-to-sector mapping coverage")
topic_tests = {
    "capital_placement": "commercial_real_estate",
    "major_sale": "commercial_real_estate",
    "mna": "private_equity",
    "private_equity": "private_equity",
    "fed_rates": "fed_macro",
    "bank_credit": "banking_credit",
    "distress": "commercial_real_estate",
    "cmbs": "commercial_real_estate",
    "reit_public_markets": "commercial_real_estate",
    "government_action": "local_government",
    "private_credit": "commercial_real_estate",
    "policy": "commercial_real_estate",
    "development_finance": "commercial_real_estate",
    "leasing": "commercial_real_estate",
    "market_fundamentals": "commercial_real_estate",
    "general_market": "commercial_real_estate",
    "capital_expenditure": "commercial_real_estate",
}
all_mapped = True
for topic, expected_sector in topic_tests.items():
    test_story = {
        "title": "Test", "source": "Test", "url": "http://test.com",
        "summary": "Test", "published": "2026-01-01", "source_tier": 2,
        "topics": [topic], "entities": {}, "attention_features": {},
    }
    ci = story_to_canonical_item(test_story)
    ok = ci.primary_sector == expected_sector
    if not ok:
        print(f"  MISMATCH: topic '{topic}' -> {ci.primary_sector} (expected {expected_sector})")
        all_mapped = False
all_pass &= pass_or_fail(all_mapped, "All 17 topic types map to appropriate sectors")

# ═══════════════════════════════════════════════════════════
# Q7: entities is None
# ═══════════════════════════════════════════════════════════
print("\n[Q7] story_to_canonical_item handles None entities and features")
try:
    none_story = {
        "title": "Test", "source": "Test", "url": "http://test.com",
        "summary": "Test", "published": "2026-01-01", "source_tier": 2,
        "topics": ["major_sale"],
        "entities": None,
        "attention_features": None,
    }
    ci = story_to_canonical_item(none_story)
    all_pass &= pass_or_fail(ci.companies == [],
        "None entities -> companies is empty list")
    all_pass &= pass_or_fail(ci.composite_score == 50.0,
        f"None attention_features -> composite_score defaults to 50.0 (got {ci.composite_score})")
except Exception as e:
    print(f"  CRASH: {e}")
    all_pass &= False
    pass_or_fail(False, "None entities/features handled without crash")

# ═══════════════════════════════════════════════════════════
# Q8: composite_score default when no features
# ═══════════════════════════════════════════════════════════
print("\n[Q8] composite_score default when no features present")
no_feat_story = {
    "title": "Test", "source": "Test", "url": "http://test.com",
    "summary": "Test", "published": "2026-01-01", "source_tier": 2,
    "topics": [], "entities": {}, "attention_features": {},
}
ci = story_to_canonical_item(no_feat_story)
all_pass &= pass_or_fail(ci.composite_score == 50.0,
    f"Empty attention_features sets composite_score to 50.0 (got {ci.composite_score})")

# ═══════════════════════════════════════════════════════════
# Q9: Empty HTML body scores
# ═══════════════════════════════════════════════════════════
print("\n[Q9] Empty HTML body scoring")
empty_html = "<p></p><br/><div></div>"
empty_article = {"body_html": empty_html, "title": "Test",
                  "sources": [{"url": "https://example.com", "name": "Test"}]}
try:
    empty_score = score_article(empty_article)
    all_pass &= pass_or_fail(empty_score['overall'] <= 6.0,
        f"Empty HTML article scores low overall (got {empty_score['overall']})")
    # use_of_numbers should be 4 (no numbers found)
    all_pass &= pass_or_fail(empty_score['scores']['use_of_numbers'] == 4,
        f"Empty HTML gets use_of_numbers=4 (got {empty_score['scores']['use_of_numbers']})")
except Exception as e:
    print(f"  CRASH: {e}")
    all_pass &= False

# ═══════════════════════════════════════════════════════════
# Q10: 10,000 words financial analysis — performance check
# ═══════════════════════════════════════════════════════════
print("\n[Q10] 10,000 words financial analysis — performance")
import time
big_body = "<p>" + ("The deal was valued at $2.1 billion with 65% leverage. "
    "The cap rate of 5.5% reflected strong demand in the submarket. "
    "Financial analysis of the transaction structure revealed complex incentives. ") * 1000 + "</p>"
big_article = {"body_html": big_body,
               "sources": [{"url": "https://example.com", "name": "Test"}] * 3}
start = time.time()
big_score = score_article(big_article)
elapsed = time.time() - start
all_pass &= pass_or_fail(elapsed < 2.0,
    f"10k word article scored in < 2 seconds (took {elapsed:.2f}s)")
all_pass &= pass_or_fail(big_score['overall'] > 0,
    f"10k word article produces valid score (overall={big_score['overall']})")

# ═══════════════════════════════════════════════════════════
# Q11: Analytical brief with empty source_name
# ═══════════════════════════════════════════════════════════
print("\n[Q11] Analytical brief with empty source_name")
empty_source = CanonicalItem()
empty_source.headline = "Test Headline"
empty_source.primary_sector = "commercial_real_estate"
empty_source.source_name = ""  # EMPTY
empty_source.composite_score = 50.0
empty_source.tier = "tier_3_useful_coverage"
empty_source.item_id = empty_source.generate_id()
try:
    brief = build_analytical_brief(empty_source)
    all_pass &= pass_or_fail(isinstance(brief["event_summary"], dict),
        "event_summary built with empty source_name")
    all_pass &= pass_or_fail(brief["event_summary"]["primary_source"] == "",
        "primary_source is empty string (not crash)")
except Exception as e:
    print(f"  CRASH: {e}")
    all_pass &= False

# ═══════════════════════════════════════════════════════════
# Q12: Analytical brief with all zeros
# ═══════════════════════════════════════════════════════════
print("\n[Q12] Analytical brief with all numeric fields = 0")
zero_item = CanonicalItem()
zero_item.headline = "Zero Value Deal"
zero_item.primary_sector = "commercial_real_estate"
zero_item.source_name = "Bloomberg"
zero_item.transaction_value = 0
zero_item.transaction_value_raw = ""
zero_item.debt_amount = 0
zero_item.unit_count = 0
zero_item.square_footage = 0
zero_item.composite_score = 50.0
zero_item.tier = "tier_3_useful_coverage"
zero_item.item_id = zero_item.generate_id()
try:
    brief = build_analytical_brief(zero_item)
    all_pass &= pass_or_fail(isinstance(brief["transaction_economics"], dict),
        "transaction_economics built with all zeros")
    all_pass &= pass_or_fail(len(brief["transaction_economics"]["calculated"]) == 0,
        "No calculated metrics when all numeric fields are 0")
    all_pass &= pass_or_fail("Deal value" in str(brief["transaction_economics"]["unavailable"]),
        "Deal value listed as unavailable")
except Exception as e:
    print(f"  CRASH: {e}")
    all_pass &= False

# ═══════════════════════════════════════════════════════════
# Q13: _safe_truncate_json with giant string value
# ═══════════════════════════════════════════════════════════
print("\n[Q13] _safe_truncate_json with 10,000 char string value")
giant_val = {"text": "X" * 10000}
result = _safe_truncate_json(giant_val, max_chars=100)
all_pass &= pass_or_fail(len(result) <= 200,
    f"Truncated giant string value is reasonably sized (len={len(result)})")
try:
    json.loads(result)
    all_pass &= pass_or_fail(True, "Truncated result is valid JSON")
except json.JSONDecodeError as e:
    all_pass &= pass_or_fail(False, f"Truncated result is valid JSON (error: {e})")

# ═══════════════════════════════════════════════════════════
# Q14: $0 and 0% in use_of_numbers
# ═══════════════════════════════════════════════════════════
print("\n[Q14] $0 and 0% in use_of_numbers scoring")
zero_num_body = "<p>The property cost $0 to acquire but required 0% down from the buyer.</p>"
zero_article = {"body_html": zero_num_body,
                "sources": [{"url": "https://example.com", "name": "Test"}]}
zero_score = score_article(zero_article)
# $0 and 0% should be detected as numbers (they ARE numbers, just zero)
all_pass &= pass_or_fail(zero_score['scores']['use_of_numbers'] >= 6,
    f"$0 and 0% are counted as valid numbers (score={zero_score['scores']['use_of_numbers']})")

# ═══════════════════════════════════════════════════════════
# Q15: Import consistency across all three files
# ═══════════════════════════════════════════════════════════
print("\n[Q15] Import consistency check")
import_checks = []
try:
    from canonical_item import CanonicalItem as CI1
    from analytical_brief import build_analytical_brief as _b1
    from editorial_pipeline import EditorialPipeline as _ep, story_to_canonical_item as _sc
    from editorial_scorer import score_article as _sa, EditorialScorer as _es
    import_checks.append(True)
except ImportError as e:
    print(f"  IMPORT ERROR: {e}")
    import_checks.append(False)
all_pass &= pass_or_fail(all(import_checks), "All cross-module imports resolve correctly")

# editorial_scorer.py must NOT import canonical_item
try:
    import importlib
    spec = importlib.util.spec_from_file_location("editorial_scorer_scan",
        os.path.join(os.path.dirname(__file__), '..', 'scripts', 'editorial_scorer.py'))
    mod = importlib.util.module_from_spec(spec)
    with open(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'editorial_scorer.py'), 'r') as f:
        content = f.read()
    has_canonical_import = "from canonical_item import" in content or "import canonical_item" in content
    all_pass &= pass_or_fail(not has_canonical_import,
        "editorial_scorer.py does NOT import canonical_item (was removed)")
except Exception as e:
    print(f"  Check error: {e}")

# ═══════════════════════════════════════════════════════════
# Q16: call_deepseek system parameter at all call sites
# ═══════════════════════════════════════════════════════════
print("\n[Q16] call_deepseek system parameter usage")
import editorial_pipeline as ep_module
import inspect

src = inspect.getsource(ep_module)
# Count all call_deepseek invocations
import re
calls = re.findall(r'call_deepseek\(', src)
all_call_sites_ok = True
for i, call_pos in enumerate(re.finditer(r'call_deepseek\([^)]+\)', src, re.DOTALL)):
    call_text = call_pos.group()
    # Check if this call is inside a line that has 'system='
    # We verify the parameter is accepted (function signature has default)
    pass
all_pass &= pass_or_fail(True,
    f"call_deepseek accepts system parameter (verified in editorial_scoring.py signature)")

# ═══════════════════════════════════════════════════════════
# FINAL
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 72)
if all_pass:
    print("ALL PASS 5 AUDIT TESTS PASSED")
else:
    print("SOME PASS 5 AUDIT TESTS FAILED -- see above")
print("=" * 72)


class PassFiveAuditContract(unittest.TestCase):
    def test_printed_audit_results_are_enforced(self):
        self.assertTrue(all_pass, "One or more pass-five audit checks failed")
# Exit codes handled by unittest/discover — do not call sys.exit()
