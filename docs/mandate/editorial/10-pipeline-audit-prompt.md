# Editorial Pipeline — Deep Audit & Fix Prompt

You are auditing the newly built multi-stage editorial pipeline for Light Tower Group. Three new modules were created. Find EVERY bug, logic error, integration gap, edge case, and design flaw — then fix them all.

## What Was Built

### scripts/editorial_pipeline.py (~290 lines)
- `EditorialPipeline` class with 7 stages: analytical_brief, assemble_prompt, draft, financial_review, editorial_review, fact_verification, final_revision
- Uses `call_deepseek` from editorial_scoring.py for LLM stages
- Graceful offline fallback when no API key (`_HAS_LLM` flag)
- `run()` method orchestrates all stages
- `_extract_json()` helper for parsing LLM responses

### scripts/editorial_scorer.py (~200 lines)
- `EditorialScorer` class with 14 scoring dimensions
- Per-dimension minimums (factual_accuracy≥9, financial_understanding≥7, etc.)
- Overall minimum 7.0 for publishability
- `score()` method returns scores + publishability verdict
- `_strip_html()` helper for text analysis

### scripts/analytical_brief.py (enhanced)
- `build_analytical_brief()` — deterministic pre-writing reasoning
- `enhance_brief_with_llm()` — LLM-assisted thesis/counterargument generation
- 13 fields: event_summary, parties_and_incentives, transaction_economics, market_context, central_financial_question, core_tension, thesis, counterargument, unknowns, reader_relevance, article_architecture, article_depth, key_numbers

## Audit Instructions

Read ALL three files completely. Then check EVERY item below.

### Category 1: Import and Compilation Errors
1. Does `editorial_pipeline.py` import `call_deepseek` correctly? Does the try/except handle the case where editorial_scoring can't be imported?
2. Does `editorial_pipeline.py` import `build_analytical_brief` from analytical_brief correctly?
3. Does `editorial_pipeline.py` import `get_sector_prompt` from generation correctly?
4. Does `editorial_scorer.py` import `CanonicalItem`? Is it actually used?
5. Does `analytical_brief.py` `enhance_brief_with_llm()` import `call_deepseek` inside a try/except?
6. Compile-check ALL three files

### Category 2: Logic Bugs
7. In `editorial_pipeline.py` `stage_draft()`: what happens when `call_deepseek` succeeds but returns malformed JSON? Does the exception handler catch `json.JSONDecodeError`?
8. In `editorial_pipeline.py` `stage_financial_review()`: the prompt says "Return JSON" but what if the LLM returns non-JSON text?
9. In `editorial_pipeline.py` `stage_editorial_review()`: same JSON parsing concern
10. In `editorial_pipeline.py` `stage_final_revision()`: does it correctly handle the case where `all_issues` is empty? Does it skip the LLM call?
11. In `editorial_pipeline.py` `run()`: what happens if `stage_draft()` returns `status: "skipped"` (no API key)? The code checks for `!= "completed"` — but "skipped" is not "completed".
12. In `editorial_scorer.py` `_score_factual_accuracy()`: what if `article.get("sources")` is None (not just empty list)?
13. In `editorial_scorer.py` `_score_use_of_numbers()`: does the regex correctly match dollar amounts with spaces like "$ 2.1 billion"?
14. In `editorial_scorer.py` `_score_narrative_structure()`: it splits on `'\n'` — but body_html contains `<p>` tags, not newlines. The text split won't find paragraphs.
15. In `editorial_scorer.py` `_score_opening_quality()`: same issue — splits on `'\n'` but HTML has `<p>` tags
16. In `editorial_scorer.py` `_score_conclusion_quality()`: same — splits on `'\n'`
17. In `analytical_brief.py` `_select_depth()`: what threshold values map to which depth? Check if the boundaries are correct (≥70 deep, ≥50 standard, <50 brief)
18. In `analytical_brief.py` `_build_economics()`: if `transaction_value` is 0 but `transaction_value_raw` is "$2.1 billion", the per-unit/per-sf calculations divide by zero

### Category 3: Integration Gaps
19. The `editorial_pipeline.run()` returns `article` from `stage_draft()` but `stage_draft()` returns `{"status": ..., "article": ...}`. Check that `result["article"] = draft_result["article"]` correctly accesses the article dict.
20. The `editorial_pipeline.run()` passes `article` to `stage_financial_review()`, `stage_editorial_review()`, and `stage_fact_verification()`. Does each of these functions access `article.get("body_html")` correctly?
21. The `stage_final_revision()` receives `article`, `prompt_context`, `financial_review`, `editorial_review`, `fact_issues`. Does it correctly extract issues from each review dict?
22. The `stage_assemble_prompt()` calls `get_sector_prompt()` from generation.py. Does generation.py import the correct function name?
23. The `editorial_scorer.score()` takes `article` and `brief`. Is `brief` optional? What happens when it's None?
24. The `enhance_brief_with_llm()` function — is it called anywhere in the pipeline? Or is it orphaned?

### Category 4: Edge Cases
25. What happens when `_extract_json()` is called with an empty string?
26. What happens when `_extract_json()` is called with text that has no `{` character?
27. What happens when `_strip_html()` is called with None?
28. What happens when the scorer's `_score_sentence_quality()` receives text with zero sentences?
29. What happens when `_score_originality()` receives text that is empty or None?
30. What happens in `_build_economics()` when `item.transaction_value > 0` is True but `item.unit_count == 0`? (Division by zero checked above, but also check: does the code guard against this?)
31. What happens when `_select_architecture()` receives an item with composite_score between 50-75 AND sector is "fed_macro"? Which architecture wins — sector-based or score-based?

### Category 5: Performance
32. Does `editorial_scorer` recompile regex patterns on every `score()` call? The `_score_use_of_numbers()` and `_score_sentence_quality()` use inline regex — are they compiled once?
33. Does `stage_assemble_prompt()` call `json.dumps()` multiple times on the same data? Could the brief be pre-serialized?
34. The `get_pipeline_stats()` function iterates results — any O(n) operations that could cause issues at scale?

### Category 6: Design Issues
35. The `EditorialPipeline` class stores `self.errors` but never exposes them to the caller. Should `run()` return errors?
36. The scorer uses hardcoded strings for dimension names that differ from the rubric document names (e.g., "analytical_originality" vs "Analytical Originality"). Is this intentional?
37. `_score_thesis_strength()` checks `len(thesis) > 50` as a proxy for quality. Is character count really a good measure?
38. The pipeline has 7 stages but the modular architecture document specifies 15 stages. Which stages are missing? (Article outline, headline generation, metadata generation, entity extraction, financial analysis, incentive analysis, market context — some are in the analytical brief, others are missing)

## Fix Instructions

For EVERY bug found:
1. State file and line number
2. Explain the bug
3. Apply the fix
4. Verify: `python -m py_compile <file>`

After ALL fixes, run:
```
python tests/test_editorial_pipeline.py
```

Everything must pass with zero errors. Return a complete bug report.
