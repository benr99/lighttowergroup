"""Comprehensive test suite covering edge cases for all pipeline modules."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from canonical_item import CanonicalItem
from classification import (
    classify_item, classify_batch, get_sector_stats,
    classify_source_prior, classify_regex_signals,
)
from scoring_engine import (
    score_item, score_batch, get_scoring_stats,
    _get_entity_tier, _extract_amounts, _extract_megawatts, _clear_caches,
)
from ranking import (
    rank_and_select, rank_within_sector, apply_diversity_controls,
    select_top_n, deduplicate_across_sectors, get_rejection_report,
)
from generation import (
    get_sector_prompt, get_sector_label, get_sector_category,
    get_article_type, get_article_type_label, get_word_count,
    get_category_word_range, build_generation_context,
    get_primary_prompt_for_item, get_secondary_prompts,
    get_generation_stats, print_generation_summary,
    validate_item_for_generation, filter_ready_items,
)

PASSED = 0
FAILED = 0


def check(description, condition):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS: {description}")
    else:
        FAILED += 1
        print(f"  FAIL: {description}")


def check_no_exception(description, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  PASS: {description}")
    except Exception as e:
        FAILED += 1
        print(f"  FAIL: {description} -> {type(e).__name__}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# MODULE 1: canonical_item – Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 1: canonical_item Edge Cases")
print("=" * 60)

print("\n1.1 Empty defaults")
item = CanonicalItem()
check("headline defaults to ''", item.headline == "")
check("composite_score defaults to 0.0", item.composite_score == 0.0)
check("secondary_sectors defaults to []", item.secondary_sectors == [])
check("status defaults to 'ingested'", item.status == "ingested")
check("source_tier defaults to 3", item.source_tier == 3)

print("\n1.2 generate_id")
item2 = CanonicalItem()
item2.source_url = "https://example.com/article"
item2.headline = "Test Headline"
item_id = item2.generate_id()
check("generate_id returns non-empty string", len(item_id) == 16)
check("generate_id is hex string", all(c in "0123456789abcdef" for c in item_id))

print("\n1.3 generate_id with unicode")
item3 = CanonicalItem()
item3.source_url = "https://example.com/artículo"
item3.headline = "Créeme – Test €100M"
uid = item3.generate_id()
check("generate_id handles unicode", len(uid) == 16)

print("\n1.4 age_hours with invalid date")
item4 = CanonicalItem()
item4.publication_date = "not-a-date"
check("age_hours returns 999 for invalid date", item4.age_hours() == 999)

print("\n1.5 age_hours with empty date")
item5 = CanonicalItem()
item5.publication_date = ""
check("age_hours returns 999 for empty date", item5.age_hours() == 999)

print("\n1.6 is_publishable without scoring")
item6 = CanonicalItem()
check("is_publishable False when not scored", not item6.is_publishable())

print("\n1.7 is_publishable with high score")
item7 = CanonicalItem()
item7.composite_score = 80.0
item7.status = "scored"
check("is_publishable True when scored above threshold", item7.is_publishable())

print("\n1.8 from_rss_entry with None values")
none_entry = {"title": None, "summary": None, "link": None, "published": None}
none_source = {"name": None}
check_no_exception("from_rss_entry handles None values", lambda: CanonicalItem.from_rss_entry(none_entry, none_source))

print("\n1.9 from_dict filters unknown fields")
data = {"headline": "Test", "primary_sector": "private_equity", "not_a_field": 999}
item8 = CanonicalItem.from_dict(data)
check("from_dict includes known fields", item8.headline == "Test")
check("from_dict excludes unknown fields", not hasattr(item8, "not_a_field"))

print("\n1.10 from_dict with empty dict")
check_no_exception("from_dict({}) works", lambda: CanonicalItem.from_dict({}))

print("\n1.11 to_json produces valid JSON")
item9 = CanonicalItem()
item9.headline = "Test with unicode: \u2014 em dash"
json_str = item9.to_json()
check_no_exception("to_json parses back", lambda: json.loads(json_str))

print("\n1.12 reject() method")
item10 = CanonicalItem()
item10.reject("Test reason", "R001")
check("reject sets status", item10.status == "rejected")
check("reject sets reason", item10.rejection_reason == "Test reason")
check("reject sets code", item10.rejection_code == "R001")

print("\n1.13 record_error() method")
item11 = CanonicalItem()
item11.record_error("Error 1")
item11.record_error("Error 2")
check("record_error increments retry_count", item11.retry_count == 2)
check("record_error appends to error_history", len(item11.error_history) == 2)

print("\n1.14 set_classification updates all fields")
item12 = CanonicalItem()
item12.set_classification("private_equity", ["data_centers"], "buyout", "tech_buyout", 0.85, "source_prior_and_regex")
check("set_classification sets primary", item12.primary_sector == "private_equity")
check("set_classification sets secondary", item12.secondary_sectors == ["data_centers"])
check("set_classification sets event_type", item12.event_type == "buyout")
check("set_classification sets confidence", item12.classification_confidence == 0.85)
check("set_classification sets method", item12.classification_method == "source_prior_and_regex")
check("set_classification sets status", item12.status == "classified")

print("\n1.15 set_scoring updates all score fields")
item13 = CanonicalItem()
scores = {
    "financial_magnitude": 7, "party_significance": 5, "market_impact": 4,
    "strategic_relevance": 6, "policy_impact": 3, "novelty": 7,
    "source_quality": 5, "timeliness": 8, "editorial_potential": 4,
    "cross_sector_impact": 2,
}
item13.set_scoring(scores, 56.5, "private_equity", "tier_3_useful_coverage")
check("set_scoring composite", item13.composite_score == 56.5)
check("set_scoring profile", item13.scoring_profile == "private_equity")
check("set_scoring tier", item13.tier == "tier_3_useful_coverage")
check("set_scoring status", item13.status == "scored")
check("set_scoring financial_magnitude", item13.financial_magnitude_score == 7)

# ═══════════════════════════════════════════════════════════════════════
# MODULE 2: Classification – Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 2: Classification Edge Cases")
print("=" * 60)

print("\n2.1 classify_batch with empty list")
check("classify_batch([]) returns []", classify_batch([]) == [])

print("\n2.2 classify_item with empty fields")
empty_item = CanonicalItem()
empty_item.source_name = ""
classified_empty = classify_item(empty_item)
check("empty item gets needs_llm", classified_empty.classification_method == "needs_llm")
check("empty item falls back to CRE", classified_empty.primary_sector == "commercial_real_estate")

print("\n2.3 classify_item with unknown source")
unknown = CanonicalItem()
unknown.headline = "Some random news about nothing in particular"
unknown.raw_summary = "Generic content without sector signals"
unknown.source_name = "Unknown Blog"
classified_unknown = classify_item(unknown)
check("unknown source falls to regex/llm", classified_unknown.classification_method in ("needs_llm", "regex_signals"))

print("\n2.4 classify_source_prior with empty source")
check("classify_source_prior empty source returns None", classify_source_prior(CanonicalItem()) is None)

print("\n2.5 classify_source_prior with known source")
known = CanonicalItem()
known.source_name = "PE Hub - Private Equity News"
check("classify_source_prior matches PE Hub", classify_source_prior(known) == "private_equity")

print("\n2.6 classify_regex_signals with empty text")
empty_signals = classify_regex_signals(CanonicalItem())
check("empty text returns all-zeroish scores", all(v < 0.01 for v in empty_signals.values()))

print("\n2.7 get_sector_stats with empty list")
check("get_sector_stats([]) returns {}", get_sector_stats([]) == {})

print("\n2.8 get_sector_stats with mixed items")
mixed = [
    CanonicalItem.from_dict({"headline": "a", "primary_sector": "private_equity"}),
    CanonicalItem.from_dict({"headline": "b", "primary_sector": "private_equity"}),
    CanonicalItem.from_dict({"headline": "c", "primary_sector": "data_centers"}),
]
stats = get_sector_stats(mixed)
check("get_sector_stats counts correctly", stats == {"private_equity": 2, "data_centers": 1})

print("\n2.9 classify_item with strong CRE signals")
cre_item = CanonicalItem()
cre_item.headline = "Blackstone Acquires 245 Park Avenue for $2.1B"
cre_item.raw_summary = "Blackstone acquired the office building at 245 Park Avenue for $2.1 billion, marking Manhattan's largest office sale."
cre_item.source_name = "Commercial Observer"
cre_classified = classify_item(cre_item)
check("CRE source gets CRE sector", cre_classified.primary_sector == "commercial_real_estate")

print("\n2.10 classify_item with PE fund close signals")
pe_item = CanonicalItem()
pe_item.headline = "KKR Closes $8.5 Billion Buyout Fund"
pe_item.raw_summary = "KKR closed its latest buyout fund at $8.5 billion, exceeding its $7 billion target with strong LP demand."
pe_item.source_name = "PE Hub"
pe_classified = classify_item(pe_item)
check("PE source+signals gets higher confidence", pe_classified.classification_confidence > 0.8)

print("\n2.11 classify_batch returns same count as input")
batch_items = [CanonicalItem() for _ in range(5)]
for i, bi in enumerate(batch_items):
    bi.source_name = f"Test{i}"
    bi.headline = f"Headline {i}"
check("classify_batch preserves count", len(classify_batch(batch_items)) == 5)

# ═══════════════════════════════════════════════════════════════════════
# MODULE 3: Scoring Engine – Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 3: Scoring Engine Edge Cases")
print("=" * 60)

_clear_caches()  # Reset before testing

print("\n3.1 score_batch with empty list")
check("score_batch([]) returns []", score_batch([]) == [])

print("\n3.2 score_item with missing primary_sector")
nosector = CanonicalItem()
nosector.headline = "Test"
nosector.primary_sector = ""
nosector.publication_date = "2026-07-30T10:00:00+00:00"
scored_nosector = score_item(nosector)
check("no-sector item gets scored (fallback to CRE)", scored_nosector.composite_score > 0)

print("\n3.3 _get_entity_tier with empty name")
check("_get_entity_tier('') returns 5", _get_entity_tier("", {"tier_1_institutions": {"companies": ["Blackstone"]}}) == 5)
check("_get_entity_tier(' ') returns 5", _get_entity_tier("   ", {}) == 5)

print("\n3.4 _get_entity_tier with unknown name")
check("_get_entity_tier unknown returns 5", _get_entity_tier("SomeRandomUnknownCo", {}) == 5)

print("\n3.5 _get_entity_tier with known tier-1 entity")
watchlists = {"tier_1_institutions": {"companies": ["Blackstone", "Apollo"]}}
check("_get_entity_tier finds Blackstone as tier 1", _get_entity_tier("Blackstone Group", watchlists) == 1)

print("\n3.6 _extract_amounts with empty text")
check("_extract_amounts('') returns []", _extract_amounts("") == [])

print("\n3.7 _extract_amounts with dollar amounts")
amounts = _extract_amounts("The deal is worth $5.5 million and involved a $2 billion fund")
check("_extract_amounts finds amounts", len(amounts) >= 2)

print("\n3.8 _extract_megawatts with empty text")
check("_extract_megawatts('') returns 0.0", _extract_megawatts("") == 0.0)

print("\n3.9 _extract_megawatts finds MW values")
mw = _extract_megawatts("A 300 MW data center campus was announced")
check("_extract_megawatts finds 300 MW", mw == 300.0)

print("\n3.10 score_item with zero amounts")
zero_item = CanonicalItem()
zero_item.headline = "Minor update"
zero_item.raw_summary = "Nothing of financial significance"
zero_item.publication_date = "2026-07-30T10:00:00+00:00"
zero_item.primary_sector = "commercial_real_estate"
scored_zero = score_item(zero_item)
check("zero-amount item still gets a score", scored_zero.composite_score > 0)
check("zero-amount item gets tier", scored_zero.tier != "")

print("\n3.11 score_item with fed_macro sector")
fed_item = CanonicalItem()
fed_item.headline = "Fed Raises Rates by 25 bps"
fed_item.raw_summary = "The FOMC raised rates in a rate decision today"
fed_item.publication_date = "2026-07-30T10:00:00+00:00"
fed_item.primary_sector = "fed_macro"
fed_item.source_tier = 1
fed_item.source_authority = "primary"
fed_scored = score_item(fed_item)
check("fed_macro item scores non-zero", fed_scored.composite_score > 0)

print("\n3.12 score_item with data_centers and MW")
dc_item = CanonicalItem()
dc_item.headline = "300MW Data Center Campus Announced"
dc_item.raw_summary = "A new 300 megawatt hyperscale data center campus"
dc_item.publication_date = "2026-07-30T10:00:00+00:00"
dc_item.primary_sector = "data_centers"
dc_item.megawatts = 300.0
dc_scored = score_item(dc_item)
check("DC item with MW gets financial magnitude boost", dc_scored.financial_magnitude_score >= 3)

print("\n3.13 get_scoring_stats with empty list")
empty_stats = get_scoring_stats([])
check("get_scoring_stats([]) total=0", empty_stats["total_items"] == 0)
check("get_scoring_stats([]) empty tiers", empty_stats["tier_distribution"] == {})

print("\n3.14 score_item on already-scored item (idempotency)")
item_re = CanonicalItem()
item_re.headline = "Test"
item_re.primary_sector = "commercial_real_estate"
item_re.publication_date = "2026-07-30T10:00:00+00:00"
scored1 = score_item(item_re)
score1 = scored1.composite_score
scored2 = score_item(scored1)
check("re-scoring same item gives same composite", scored2.composite_score == score1)

# ═══════════════════════════════════════════════════════════════════════
# MODULE 4: Ranking – Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 4: Ranking Edge Cases")
print("=" * 60)

print("\n4.1 rank_and_select with empty list")
selected_empty, report_empty = rank_and_select([])
check("rank_and_select([]) returns empty dict", selected_empty == {})
check("rank_and_select([]) total_candidates=0", report_empty["total_candidates"] == 0)
check("rank_and_select([]) total_selected=0", report_empty["total_selected"] == 0)
check("rank_and_select([]) selection_rate=0", report_empty["selection_rate_pct"] == 0.0)
check("rank_and_select([]) rejection total=0", report_empty["rejection"]["total_rejected"] == 0)

print("\n4.2 rank_and_select with single scored item")
single = CanonicalItem()
single.headline = "Single Story"
single.primary_sector = "commercial_real_estate"
single.composite_score = 75.0
single.tier = "tier_2_strongly_recommended"
single.status = "scored"
single.publication_date = "2026-07-30T10:00:00+00:00"
selected_single, report_single = rank_and_select([single], target_per_sector=5)
check("single item selected", report_single["total_selected"] == 1)
check("single item in correct sector", "commercial_real_estate" in selected_single)

print("\n4.3 rank_and_select with all rejected items")
rejected = CanonicalItem()
rejected.headline = "Rejected Story"
rejected.primary_sector = "commercial_real_estate"
rejected.composite_score = 10.0
rejected.tier = "rejected"
rejected.status = "scored"
selected_rej, report_rej = rank_and_select([rejected], target_per_sector=5)
check("all-rejected selects nothing", report_rej["total_selected"] == 0)
check("all-rejected reports correctly", report_rej["rejection"]["total_rejected"] == 1)

print("\n4.4 rank_within_sector with empty list")
check("rank_within_sector empty", rank_within_sector([], "any_sector") == [])

print("\n4.5 rank_within_sector filters non-matching sector")
multi_sector = [
    CanonicalItem.from_dict({"headline": "a", "primary_sector": "private_equity", "composite_score": 70, "tier": "tier_2_strongly_recommended"}),
    CanonicalItem.from_dict({"headline": "b", "primary_sector": "data_centers", "composite_score": 60, "tier": "tier_3_useful_coverage"}),
]
ranked_pe = rank_within_sector(multi_sector, "private_equity")
check("rank_within_sector filters by sector", len(ranked_pe) == 1 and ranked_pe[0].headline == "a")

print("\n4.6 rank_within_sector excludes rejected tier")
mixed_tier = [
    CanonicalItem.from_dict({"headline": "good", "primary_sector": "energy", "composite_score": 60, "tier": "tier_3_useful_coverage"}),
    CanonicalItem.from_dict({"headline": "bad", "primary_sector": "energy", "composite_score": 20, "tier": "rejected"}),
]
ranked_energy = rank_within_sector(mixed_tier, "energy")
check("rank_within_sector excludes rejected", len(ranked_energy) == 1 and ranked_energy[0].headline == "good")

print("\n4.7 apply_diversity_controls with < 5 items")
few_items = [
    CanonicalItem.from_dict({"headline": f"h{i}", "source_name": f"src{i}", "subsector": f"sub{i}",
                              "primary_sector": "cre", "composite_score": 90-i, "tier": "tier_1"})
    for i in range(3)
]
result_few = apply_diversity_controls(few_items, "cre")
check("apply_diversity_controls returns all for <5", len(result_few) == 3)

print("\n4.8 select_top_n with empty list")
check("select_top_n([]) returns {}", select_top_n([]) == {})

print("\n4.9 deduplicate_across_sectors with empty dict")
check("deduplicate_across_sectors({}) returns {}", deduplicate_across_sectors({}) == {})

print("\n4.10 deduplicate_across_sectors preserves unique items")
sector_dict = {
    "private_equity": [CanonicalItem.from_dict({"headline": "a", "item_id": "id1"})],
    "data_centers": [CanonicalItem.from_dict({"headline": "b", "item_id": "id2"})],
}
deduped = deduplicate_across_sectors(sector_dict)
total = sum(len(v) for v in deduped.values())
check("dedup preserves unique items", total == 2)

print("\n4.11 deduplicate_across_sectors removes duplicates")
dupe_item = CanonicalItem.from_dict({"headline": "shared", "item_id": "shared_id"})
dup_sector_dict = {
    "private_equity": [dupe_item],
    "data_centers": [CanonicalItem.from_dict({"headline": "shared", "item_id": "shared_id"})],
}
deduped_dup = deduplicate_across_sectors(dup_sector_dict)
total_after = sum(len(v) for v in deduped_dup.values())
check("dedup removes duplicate by item_id", total_after == 1)

print("\n4.12 get_rejection_report with empty list")
rej_report = get_rejection_report([])
check("get_rejection_report empty total=0", rej_report["total_rejected"] == 0)
check("get_rejection_report empty reasons={}", rej_report["reasons"] == {})

print("\n4.13 rank_and_select with items missing primary_sector")
nosector_item = CanonicalItem()
nosector_item.headline = "No Sector"
nosector_item.primary_sector = ""
nosector_item.composite_score = 50.0
nosector_item.tier = "tier_3_useful_coverage"
nosector_item.status = "scored"
selected_ns, report_ns = rank_and_select([nosector_item], target_per_sector=5)
check("no-sector item not selected", report_ns["total_selected"] == 0)

# ═══════════════════════════════════════════════════════════════════════
# MODULE 5: Generation – Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 5: Generation Edge Cases")
print("=" * 60)

print("\n5.1 get_sector_prompt with empty string")
prompt_empty = get_sector_prompt("")
check("get_sector_prompt('') returns a prompt", len(prompt_empty) > 100)

print("\n5.2 get_sector_prompt with unknown sector")
prompt_unknown = get_sector_prompt("nonexistent_sector_xyz")
check("get_sector_prompt unknown returns PE fallback", len(prompt_unknown) > 100)

print("\n5.3 get_sector_prompt with known sector")
prompt_pe = get_sector_prompt("private_equity")
check("get_sector_prompt('private_equity') has expected content", "PRIVATE EQUITY" in prompt_pe)

print("\n5.4 get_sector_label with unknown sector")
label = get_sector_label("some_new_sector")
check("get_sector_label unknown returns title-case", label == "Some New Sector")

print("\n5.5 get_sector_label with empty string")
label_empty = get_sector_label("")
check("get_sector_label empty returns empty title", label_empty == "")

print("\n5.6 get_sector_category with unknown sector")
cat = get_sector_category("unknown")
check("get_sector_category unknown returns Capital Markets", cat == "Capital Markets")

print("\n5.7 get_article_type with no event_type")
item_noevent = CanonicalItem()
check("get_article_type empty event returns 'general'", get_article_type(item_noevent) == "general")

print("\n5.8 get_article_type with known event_type")
item_fund = CanonicalItem()
item_fund.event_type = "fund_close"
check("get_article_type fund_close -> fundraising_analysis", get_article_type(item_fund) == "fundraising_analysis")

print("\n5.9 get_article_type_label with unknown type")
lbl = get_article_type_label("some_future_type")
check("get_article_type_label unknown title-cases", lbl == "Some Future Type")

print("\n5.10 get_word_count with unknown type")
wc = get_word_count("nonexistent")
check("get_word_count unknown returns general word count", wc == get_word_count("general"))

print("\n5.11 get_category_word_range with unknown category")
cwr = get_category_word_range("unknown_category")
check("get_category_word_range unknown returns Capital Markets range", cwr == get_category_word_range("Capital Markets"))

print("\n5.12 build_generation_context with blank item")
blank = CanonicalItem()
ctx = build_generation_context(blank)
check("build_generation_context has headline", "headline" in ctx)
check("build_generation_context has sector", "sector" in ctx)
check("build_generation_context has word count", "word_count_min" in ctx)

print("\n5.13 get_primary_prompt_for_item")
item_prompt = CanonicalItem()
item_prompt.primary_sector = "energy"
prompt = get_primary_prompt_for_item(item_prompt)
check("get_primary_prompt_for_item returns energy prompt", "energy" in prompt.lower())

print("\n5.14 get_secondary_prompts with no secondaries")
item_nosec = CanonicalItem()
check("get_secondary_prompts empty returns []", get_secondary_prompts(item_nosec) == [])

print("\n5.15 get_generation_stats with empty dict")
check_no_exception("get_generation_stats({}) works", lambda: get_generation_stats({}))

print("\n5.16 get_generation_stats with data")
mock_data = {
    "private_equity": [CanonicalItem.from_dict({"headline": "h", "primary_sector": "private_equity", "event_type": "fund_close"})],
}
gen_stats = get_generation_stats(mock_data)
check("get_generation_stats has total", "total" in gen_stats)
check("get_generation_stats PE has articles", gen_stats["private_equity"]["articles"] == 1)
check("get_generation_stats total articles", gen_stats["total"]["articles"] == 1)

print("\n5.17 print_generation_summary does not crash")
check_no_exception("print_generation_summary works", lambda: print_generation_summary(gen_stats))

print("\n5.18 validate_item_for_generation -- all failures")
bad_item = CanonicalItem()
issues = validate_item_for_generation(bad_item)
check("bad item has headline issue", "Missing headline" in issues)
check("bad item has content issue", any("source content" in i for i in issues))
check("bad item has source URL issue", "Missing source URL" in issues)
check("bad item has sector issue", any("primary sector" in i for i in issues))
check("bad item has scoring issue", any("not been scored" in i for i in issues))

print("\n5.19 validate_item_for_generation – valid item")
good_item = CanonicalItem()
good_item.headline = "Test Article"
good_item.raw_summary = "Content here"
good_item.source_url = "https://example.com/article"
good_item.primary_sector = "commercial_real_estate"
good_item.composite_score = 56.5
good_issues = validate_item_for_generation(good_item)
check("valid item has no issues", good_issues == [])

print("\n5.20 filter_ready_items with empty list")
ready, blocked = filter_ready_items([])
check("filter_ready_items empty: ready=[]", ready == [])
check("filter_ready_items empty: blocked=[]", blocked == [])

print("\n5.21 filter_ready_items splits correctly")
mixed_items = [bad_item, good_item]
ready2, blocked2 = filter_ready_items(mixed_items)
check("filter_ready_items ready count", len(ready2) == 1)
check("filter_ready_items blocked count", len(blocked2) == 1)
check("filter_ready_items good item is ready", ready2[0] is good_item)

# ═══════════════════════════════════════════════════════════════════════
# MODULE 6: Cross-Module Integration Smoke Test
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 6: Cross-Module Integration")
print("=" * 60)

print("\n6.1 Empty pipeline: ingest-like empty batch -> classify -> score -> rank")
pipeline_empty = []
check_no_exception("empty pipeline classify", lambda: classify_batch(pipeline_empty))
classified_empty = classify_batch(pipeline_empty)
check("empty pipeline: classify returns []", classified_empty == [])
check_no_exception("empty pipeline score", lambda: score_batch(classified_empty))
check_no_exception("empty pipeline rank_and_select", lambda: rank_and_select(score_batch(classified_empty)))

print("\n6.2 Full pipeline with mixed sectors (simulated)")
items_full = []
for src_name, headline, summary in [
    ("PE Hub", "KKR Closes $8.5B Fund", "KKR closed its buyout fund at $8.5 billion exceeding target."),
    ("Data Center Dynamics", "AWS 200MW Campus", "AWS signed a 200 megawatt data center lease in Ohio."),
    ("American Banker", "FDIC Issues CRE Guidance", "The FDIC issued guidance requiring stress tests for CRE portfolios."),
    ("Federal Reserve", "FOMC Raises Rates 25bps", "The Federal Reserve raised rates by 25 basis points."),
    ("CityLand NYC", "NYC Rezoning Approved", "The NYC Council approved a mixed-use rezoning for Gowanus."),
    ("Utility Dive", "NextEra $12B Grid Plan", "NextEra announced a $12 billion grid modernization plan."),
]:
    it = CanonicalItem()
    it.headline = headline
    it.raw_summary = summary
    it.raw_text = summary
    it.source_name = src_name
    it.source_tier = 2
    it.publication_date = "2026-07-30T10:00:00+00:00"
    items_full.append(it)

classified_full = classify_batch(items_full)
check("full pipeline: all classified", len(classified_full) == 6)
check("full pipeline: no needs_llm", not any(c.classification_method == "needs_llm" for c in classified_full))

scored_full = score_batch(classified_full)
check("full pipeline: all scored", len(scored_full) == 6)
check("full pipeline: all have tiers", all(s.tier != "" for s in scored_full))
check("full pipeline: all have composite > 0", all(s.composite_score > 0 for s in scored_full))

selected_full, report_full = rank_and_select(scored_full, target_per_sector=3)
check("full pipeline: selection report has candidates", report_full["total_candidates"] == 6)
check("full pipeline: selection report has selected items", report_full["total_selected"] > 0)
check("full pipeline: report has rejection data", "rejection" in report_full)
check("full pipeline: report has per_sector data", "per_sector" in report_full)

print("\n6.3 Pipeline with single-sector focus")
focused = [it for it in items_full if it.source_name in ("PE Hub",)]
cf = classify_batch(focused)
sf = score_batch(cf)
selected_f, report_f = rank_and_select(sf, target_per_sector=5)
check("single-sector: item selected", report_f["total_selected"] == 1)

print("\n6.4 Pipeline return type verification")
check("rank_and_select returns tuple", isinstance(rank_and_select(scored_full), tuple))
sel, rep = rank_and_select(scored_full)
check("first element is dict", isinstance(sel, dict))
check("second element is dict", isinstance(rep, dict))
check("report has expected keys", all(k in rep for k in ("total_candidates", "total_selected", "selection_rate_pct", "rejection", "per_sector")))

# ═══════════════════════════════════════════════════════════════════════
# MODULE 7: UTF-8 / String Encoding Verification
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MODULE 7: String/Encoding Verification")
print("=" * 60)

print("\n7.1 generate_id with unicode produces stable output")
item_enc1 = CanonicalItem()
item_enc1.source_url = "https://test.com/résumé"
item_enc1.headline = "Crème de la crème"
id1 = item_enc1.generate_id()
id2 = item_enc1.generate_id()
check("unicode generate_id is deterministic", id1 == id2)

print("\n7.2 to_json handles unicode")
item_enc2 = CanonicalItem()
item_enc2.headline = "Test – The Market\u2019s Reaction"
json_str2 = item_enc2.to_json()
check("to_json preserves unicode", "Market" in json_str2)
parsed = json.loads(json_str2)
check("to_json roundtrips headline", parsed["headline"] == item_enc2.headline)

print("\n7.3 SECTOR_SIGNALS patterns are valid regex")
from classification import _SECTOR_SIGNALS_COMPILED
for sector, patterns in _SECTOR_SIGNALS_COMPILED.items():
    for p in patterns:
        check_no_exception(f"compiled pattern for {sector}: {p.pattern[:50]}",
                           lambda _p=p: _p.search("test"))
check("SECTOR_SIGNALS_COMPILED has all 7 sectors", len(_SECTOR_SIGNALS_COMPILED) == 7)

print("\n7.4 sector_prompts contain valid unicode literals")
from sector_prompts import (
    PE_SYSTEM_PROMPT, DC_SYSTEM_PROMPT, ENERGY_SYSTEM_PROMPT,
    BANKING_SYSTEM_PROMPT, FED_SYSTEM_PROMPT, LOCALGOV_SYSTEM_PROMPT,
)
for name, prompt in [("PE", PE_SYSTEM_PROMPT), ("DC", DC_SYSTEM_PROMPT),
                      ("Energy", ENERGY_SYSTEM_PROMPT), ("Banking", BANKING_SYSTEM_PROMPT),
                      ("Fed", FED_SYSTEM_PROMPT), ("LocalGov", LOCALGOV_SYSTEM_PROMPT)]:
    check(f"{name} prompt is non-empty string", isinstance(prompt, str) and len(prompt) > 200)

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"  RESULTS: {PASSED} passed, {FAILED} failed")
print("=" * 60)

if FAILED > 0:
    sys.exit(1)
