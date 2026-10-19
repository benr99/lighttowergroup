# Insights Generator Restoration — Execution Plan

**Written:** 27 August 2026  
**Owner:** Codex + Ben  
**Status:** Core restoration implemented; live provider validation pending

## Objective

Restore the Light Tower Insights generator to reliable daily publication, then
restore volume without weakening the editorial quality floor. Every failure must
be distinguishable as one of:

1. discovery/source failure;
2. selection/editorial hold;
3. provider or generation failure; or
4. publication/deployment failure.

The system must never report a successful run when the writer failed to produce
all selected drafts, and it must never silently manufacture stories to meet a
target.

## Evidence baseline

The 26 August production run ingested 810 documents, clustered 747 events,
selected 17 stories, attempted 5 drafts, and wrote 0 articles. The selected
drafts failed because DeepSeek returned output-limit terminations or malformed
JSON, while the OpenAI fallback returned HTTP 429. The run then described the
failed drafts as held and recorded an overall success.

Local validation is not currently clean: the default Windows interpreter lacks
locked Python dependencies, and the full suite reports retrieval/listing
failures in addition to import errors. CI installs `scripts/requirements.lock`,
so local and CI validation must be reported separately.

## Work order and acceptance criteria

### WO-1 — Make generation truncation explicit and recoverable

Files: `scripts/editorial_scoring.py`, `scripts/editorial_pipeline.py`.

- Treat `finish_reason == "length"` as a labelled provider truncation failure,
  whether visible content is empty or non-empty.
- Preserve provider diagnostics: finish reason, reasoning length, visible length,
  token usage, provider, model, and attempt.
- Use depth-aware draft budgets derived from the requested word contract rather
  than one flat 8,000-token value.
- Make a truncation retry materially different: reduce the output contract,
  increase the ceiling where safe, or split the audit ledger from the prose call.
- Keep a hard upper bound to prevent runaway provider cost and latency.

Acceptance: tests prove truncation is rejected, the retry changes its request,
and budgets differ by depth. A live probe across all depth tiers records no
unlabelled length failures.

### WO-2 — Bound the evidence prompt at source boundaries

Files: `scripts/research_dossier.py`, `scripts/editorial_pipeline.py`.

- Render whole source blocks only; never slice through a URL, source header,
  extract, or sentence.
- Rank sources by authority, independence, and evidence richness before dropping
  material.
- Report how many sources/characters were omitted.
- Keep the writer, reviewer, and fact verifier inside the same evidence boundary.

Acceptance: a 40-source dossier stays within the prompt budget, contains no
partial source block, and exposes omission counts in diagnostics.

### WO-3 — Separate provider failure from editorial hold

Files: `scripts/v3_generation.py`, `scripts/v3_publish.py`,
`scripts/insights_v3.py`, `scripts/edition_manager.py`.

- Count statuses such as `draft_failed`, `revision_failed`, and provider errors
  as failures, never as holds.
- A hold means an article exists but a quality or human-review gate withheld it.
- A run with selected stories but zero generated articles must fail visibly or be
  marked `provider_failure`, not `success` or `no_publishable_story`.
- `auto_publish_allowed` must be false when generation failures occurred.
- Preserve partial success: valid articles may publish while failed articles are
  listed separately.

Acceptance: regression tests assert distinct counts and release decisions for
provider failure, editorial hold, and empty selection.

### WO-4 — Restore fallback readiness without creating a paid dependency

Files: provider configuration and workflow diagnostics only.

- Keep OpenAI as an optional configured fallback.
- Do not add a paid provider or change billing without Ben's approval.
- Check the OpenAI account separately because the current key returns 429.
- If fallback remains unavailable, record single-provider operation explicitly.

Acceptance: provider preflight names the available chain without exposing keys;
the live run either uses a working fallback or clearly reports that none exists.

### WO-5 — Validate locally and in CI-equivalent conditions

- Install/use the locked dependencies in an isolated environment.
- Run Python compilation, the full unittest suite, publication validation, JS
  syntax checks, and JS tests.
- Fix test defects that are code defects; do not hide failures by skipping them.
- Keep Windows developer commands separate from Bash/GitHub Actions commands.

Acceptance: the CI command set passes, or every remaining failure is listed with
its cause and owner.

### WO-6 — Remove the hidden volume ceiling safely

Files: `scripts/selection.py`, workflow configuration, budget/timing controls.

- Replace the hard five-article ceiling with a configurable safe maximum.
- Keep the daily target and article limit separate.
- Enforce cost, per-article, phase, and total runtime ceilings.
- Increase publication volume only after WO-1 through WO-3 pass two live runs.

Acceptance: a test proves a requested limit above five reaches generation; a live
run records wall-clock time and spend before any larger target is adopted.

### WO-7 — Diagnose sector shortfalls without lowering standards

Files: source health, eligibility, classification, and selection diagnostics.

- For each sector, distinguish no discovery, ineligible content, below-floor
  content, and selection/diversity effects.
- Sample rejected candidates before changing eligibility rules.
- Repair source/config/classification gaps before lowering quality thresholds.
- Treat a genuinely thin sector as a visible shortfall.

Acceptance: each sector has before/after counts and a reasoned rejection sample;
no weak story is promoted solely to fill a quota.

### WO-8 — Make missed and zero-output runs audible

Files: workflow and a small alert/reporting component.

Alert on zero articles, provider failure above threshold, rollback, and a missed
scheduled run. Use existing free GitHub mechanisms unless Ben approves another
delivery channel. A weekly committed health report is not sufficient for a
daily publication system.

Acceptance: a simulated zero-output run produces an actionable alert artifact;
the workflow exposes it through the configured free channel.

## Execution status

| Work order | Status | Notes |
|---|---|---|
| WO-1 | Implemented | Truncation is labelled; draft budgets are depth-aware; retries change the budget and prompt. |
| WO-2 | Implemented | Dossier prompts keep complete source blocks and report omitted blocks. |
| WO-3 | Implemented | Provider failures are separated from editorial holds and block automatic publication. |
| WO-4 | Blocked externally | OpenAI account/quota must be checked by Ben. |
| WO-5 | Verified locally | 415 Python tests, compilation, publication validation, and 24 JS tests pass in `.venv`/Node. |
| WO-6 | Implemented | Selection and workflow can request up to 30; spend/time budgets remain the safety controls. |
| WO-7 | Pending | Must follow writer restoration. |
| WO-8 | Partially implemented | Zero-output publish runs now fail visibly even when the build step fails, and retain artifacts; same-day external notification still depends on GitHub/account notification settings. |

## Verification record

- Focused restoration tests: **51 passed**.
- Full Python suite in the repository virtual environment: **415 passed**.
- Python compilation for every `scripts/*.py`: **passed**.
- `scripts/validate_publication.py`: **passed**.
- JavaScript syntax checks: **passed**.
- JavaScript tests: **24 passed**.
- Live provider probe: **not run** because it requires the configured provider
  secrets and would incur provider cost.
- Live shadow probe: **attempted** in an isolated state directory; the local
  network returned 164/171 feed failures, so no coverage conclusion was drawn.
- OpenAI fallback restoration: **not possible from repository code**; the
  account behind `OPENAI_API_KEY` must be checked for the observed 429 state.

## Non-negotiable safety rules

- Do not bypass paywalls, bot protection, authentication, or robots.txt.
- Do not print or persist API keys.
- Do not add a paid service without cost/coverage review and approval.
- Do not lower the quality floor merely to hit an article count.
- Do not commit generated diagnostics or unrelated user work as part of the fix.
