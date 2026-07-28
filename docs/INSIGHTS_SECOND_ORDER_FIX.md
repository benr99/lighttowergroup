# Light Tower Insights — Second-Order Fix Plan
# Address all 23 critical issues from two audit passes

## Fix categories

### P0 — BROKEN INFRASTRUCTURE (prevents pipeline from working correctly)
- #2: Model router sends OpenAI key to DeepSeek URL — fallback is a lie
- #14: HTML sanitizer strips h2/h3 — quality gate requires them, viewer sees wall of text
- #5: Signal gate threshold 34 catches nothing — must be 56
- #16: Cost tracker double-called — crashes if import failed
- #3/#19: Checkpoint module exists but never imported — no phase timeouts

### P1 — DATA INTEGRITY (corrupts or loses data)
- #13: Files written to disk before validation — corrupt state on failure
- #12: Self-repair loop accepts broken articles silently — no escape hatch
- #15: LinkedIn PDF queue overwrites previous entries — data loss

### P2 — TEMPLATE & FRONTEND (affects all 331 articles)
- #11/#23: Two incompatible article templates — rebuild would corrupt half the site
- #20: Inline CSS duplicated 331 times — uncacheable bandwidth waste
- #6: Read tracking not injected into article pages — blind feedback loop
- #18: CSP unsafe-inline required by inline scripts — XSS attack surface

### P3 — ACCURACY & VERIFICATION
- #1: Cost tracker never called during pipeline — always reports $0.00
- #21: Mojibake detection misses common artifacts — corrupted text passes
- #22: validate_publication only checks first 10 by position, not by recency

### P4 — OPTIMIZATION & FEATURES
- #4: Article variants module exists but never called — A/B testing is dead
- #9: Fact audit only checks amounts/names, not semantic truth
- #8: No article recommendations — reader bounces after one article

### P5 — EDGE CASES & CONFIG
- #7: Buildings page has comment-only upgrade plan, zero implementation
- #10: System cannot confidently publish nothing — gate too weak
- #17: Netlify cache rules don't match subdirectory files

---

## Execution order (by dependency)

### P0 (immediate — fix broken infrastructure)

**Fix #2: Model router URL switching**
- File: scripts/model_router.py
- Change: Return `url` field from `select_provider()` with the correct API endpoint
- File: scripts/editorial_scoring.py  
- Change: `call_deepseek()` accepts optional `provider` param, uses provider's URL
- File: scripts/daily_news_agent.py
- Change: Pass provider dict through to all API call sites (lines 2253, 2328, 2412, 2578)
- Also: Fix inline API calls at lines 571, 807, 835 to use provider-aware URL
- Verify: Run `python -m py_compile` on all modified files

**Fix #14: HTML sanitizer strips h2/h3**
- File: scripts/daily_news_agent.py, line 942
- Change: `_SAFE_TAGS = {'p', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'blockquote', 'br', 'a', 'span', 'h2', 'h3', 'h4', 'h5', 'h6'}`
- One-line change. Headings have no interactive capability and are safe.

**Fix #5: Signal gate threshold**
- File: scripts/daily_news_agent.py, line ~2226
- Change: `(item.get("must_read_score") or 0) >= 34` → `(item.get("must_read_score") or 0) >= 56`
- Import MUST_READ_THRESHOLD from editorial_intelligence, use the constant

**Fix #16: Cost tracker double-call**
- File: scripts/daily_news_agent.py, near line 2784
- Change: Delete the unconditional `get_costs()` at line 2784. Keep only the try/except block at 2787-2791.

**Fix #3: Import checkpoint module**
- File: scripts/daily_news_agent.py
- Change: Add `from checkpoint import run_with_timeout, clear_checkpoints, PHASE_TIMEOUTS` at top
- Change: At start of main(), call `clear_checkpoints()` 
- Change: Wrap the triage call: `candidates = run_with_timeout("triage", triage_bucketed_volume, all_stories, LOOKBACK_HOURS)`
- Change: At end of successful main(), call `clear_checkpoints()`
- Also wrap: Phase 3 scoring, Phase 4 dossier building (the for loop can't be easily wrapped — use per-iteration timeout via the editorial room call's existing timeout)

### P1 (next — fix data integrity)

**Fix #13: Validate before write**
- File: scripts/daily_news_agent.py, publish phase (lines 2639-2717)
- Change: Move `validate_repository()` call BEFORE all file writes
- Change: Write article HTML to temp paths first
- Pattern:
```python
# Phase 6a: Generate artifacts (no disk writes yet)
rendered_articles = []
for article in articles:
    html = render_html(article)
    assert_no_mojibake(f"html {article['slug']}", html)
    rendered_articles.append((article, html))
# Phase 6b: Write to temp
temp_manifest = update_manifest_temp(rendered_articles)
# Phase 6c: Validate the staged artifacts
# Phase 6d: Commit to disk (rename temp → final)
```

**Fix #12: Self-repair exhaustion handler**
- File: scripts/daily_news_agent.py, generate_article(), after line 856
- Change: Add `else:` clause on the `for _ in range(2)` loop
```python
else:
    # Exhausted repair attempts — still has issues
    unresolved = '; '.join(control_findings[:3])
    print(f"  [WARN] Self-repair exhausted: {unresolved}")
    raise ValueError(f"Article quality issues unresolved: {unresolved}")
```

**Fix #15: LinkedIn PDF queue append, not overwrite**
- File: scripts/daily_news_agent.py, near line 2680
- Change: Load existing queue first, append, deduplicate by slug, then write

### P2 (template — affects all 331 articles)

**Fix #11/#23: Migrate to single article template**
- Identify which template is current/newer (Template B: Georgia + system sans, CSS custom properties)
- File: scripts/daily_news_agent.py, render_html()
- Change: Always use Template B. Remove Template A code path.
- Run rebuild_articles.py to regenerate all 331 pages with consistent template

**Fix #20: Extract inline CSS**
- Extract the common article CSS from an article's inline `<style>` block
- Save to site.css (or create article.css)
- File: scripts/daily_news_agent.py, render_html()
- Change: Replace inline `<style>...</style>` with `<link rel="stylesheet" href="/article.css">`
- Run rebuild to apply to all 331 articles

**Fix #6: Inject tracking into site.js**
- File: site.js
- Change: Add read-tracking function (adapted from the inline script in insights.html)
- The tracking fires on: page load (view), 50% scroll, 95% scroll, share button click
- This automatically applies to ALL 331 articles since they all load site.js
- File: insights.html — remove the inline tracking script (now redundant, site.js handles it)

**Fix #18: CSP unsafe-inline**
- Move remaining inline scripts to site.js or to dedicated .js files
- The nav toggle — already in site.js
- The JSON-LD — can be injected by site.js reading a data attribute
- The Google Analytics — already commented out
- File: netlify.toml
- Change: Remove 'unsafe-inline' from script-src CSP
- Add specific hashes for any remaining inline scripts that can't be extracted

### P3 (accuracy)

**Fix #1: Wire cost tracker into call_deepseek**
- File: scripts/editorial_scoring.py, call_deepseek()
- Change: After successful response, extract usage data and call track_llm_cost
```python
data = resp.json()
usage = data.get("usage", {})
total_tokens = usage.get("total_tokens", 1000)
from cost_tracker import track_llm_cost
track_llm_cost("scoring", total_tokens)
return data["choices"][0]["message"]["content"].strip()
```
- Also add to daily_news_agent.py's inline API calls at lines 571, 807, 835

**Fix #21: Complete mojibake detection**
- File: scripts/validate_publication.py, line 59
- Change: Replace limited regex with broader pattern covering all common UTF-8 double-encoding artifacts
- Also: Add replacement character check `\ufffd`
- Also check editorial_voice.py's MOJIBAKE_RE for same issue

**Fix #22: Validate latest N by date, not position**
- File: scripts/validate_publication.py, line 78
- Change: `sorted(manifest, key=lambda r: r.get("date", ""), reverse=True)[:10]` instead of `manifest[:10]`

### P4 (optimization)

**Fix #4: Wire article variants**
- File: scripts/daily_news_agent.py, generate_article()
- Change: Import and call save_variant_record after article generation
- Change: Inject get_variant_instruction into the writing prompt's headline instructions
- File: scripts/daily_news_agent.py, render_html()
- Change: Use CTA variant to conditionally include different CTA markup

**Fix #9: Semantic fact audit**
- File: scripts/fact_extractor.py
- Change: Add `audit_claim_semantic()` function that checks if the article's central claim assertions appear in source text (keyword + proximity search)
- File: scripts/content_governance.py
- Change: Call the semantic audit in the quality gate

**Fix #8: Article recommendations**
- File: scripts/daily_news_agent.py, publish phase
- Change: At publish time, compute 3 related articles by tag overlap from insights.json
- Write `insights/{slug}_related.json`
- File: Article template (render_html)
- Change: Include "Related Research" section that reads `{slug}_related.json`

### P5 (remaining)

**Fix #7: Buildings page implementation**
- File: buildings.html
- Changes: maturity date filter, search, sort by maturity, highlight imminent maturities
- Parse maturity dates from building profile article content/tags

**Fix #10: Publish-nothing confidence**
- File: scripts/daily_news_agent.py
- Change: Signal gate at threshold 56 (already in P0). If no candidates pass, edition status = "thin_news_skip"
- Don't generate deal tape HTML pages for thin days

**Fix #17: Netlify cache rules**
- File: netlify.toml
- Change: Add explicit cache rules for /insights/*.png and /insights/*.jpg
