# Implementation Prompt: Fix Root Cause #1 — Replace the Multi-Call Article Generator

## Role

Act as a senior Python engineer responsible for making the insights generator
reliable in GitHub Actions. Work from the current repository, preserve the
existing ingestion, selection, evidence, rendering, and publication contracts
where they are sound, and replace only the article-generation critical path.

Do not treat this as a timeout-tuning exercise. The existing failure is
architectural: one article can trigger a chain of model calls and retries, and
the edition waits on that unbounded call tree. Build a smaller, measurable
generation path that either produces a valid release candidate or stops with
an honest, actionable result.

## Problem to solve

The current v3 path performs several dependent AI operations for each article:
analytical brief, draft, financial review, editorial review, fact verification,
possible revision, and additional reviews. Provider retries and fallback can
multiply those calls. The workflow can remain in `Build the curated edition`
for tens of minutes and cancellation can occur before a final report is
written.

The target design is:

```text
feeds → normalize → select → retrieve dossier → one writer call → local validation → release gate → publish
```

The model writes the complete article once. Python owns the deterministic
quality and release decisions.

## Required implementation

### 1. Add a separate v4 generation module

Create a small module, preferably `scripts/v4_generation.py`, with explicit
typed result objects. Do not bury v4 behind increasingly complex conditionals
in v3.

The module must expose an edition-level function with behavior equivalent to:

```python
generate_edition_v4(
    dossiers,
    requested_count,
    run_deadline,
    provider_config,
    output_dir,
) -> GenerationReport
```

And an article-level function equivalent to:

```python
write_article_once(
    dossier,
    provider,
    attempt_deadline,
) -> ArticleAttemptResult
```

The result must be ordinary serializable data. A provider exception must become
a categorized article result, not an uncaught exception that loses the whole
edition report.

Keep v3 available behind the existing pipeline switch until v4 completes the
rollout gates.

### 2. Define the article contract before calling the model

Use one strict structured response contract. At minimum it must contain:

- stable article/object ID;
- title;
- excerpt/dek;
- article format;
- body HTML or the repository's accepted body representation;
- source URLs;
- evidence level;
- material claims or claim notes required by the existing publisher;
- word count metadata.

Do not accept an opaque prose response and attempt to infer the contract later.
If the project already has a canonical article schema, reuse it and add only
the fields needed for v4 diagnostics.

The prompt must state that:

- every material factual claim must be supported by the supplied dossier;
- source URLs must be selected from the dossier only;
- no unsupported numbers, quotes, entities, or events may be invented;
- the response must contain JSON only;
- the response must fit within the configured output limit;
- DeepSeek structured writing must disable thinking mode when configured for
  JSON output.

Keep the dossier compact. Include the selected evidence and relevant source
metadata, not the entire feed archive or unbounded article text.

### 3. Remove model reviewers from the normal path

For v4, do not call the existing multi-stage editorial pipeline. Do not invoke
analytical brief, financial review, editorial review, fact review, revision,
self-scoring, or post-revision review as hidden substeps.

The complete model interaction for one article is:

1. Build a bounded dossier prompt.
2. Make one writer request.
3. Parse the response.
4. Run local validators.
5. Optionally make exactly one controlled retry if the failure is retryable.

If a retry occurs, shorten the prompt or correct the structural instruction;
do not start a review/revision chain. Permanent failures must stop immediately.

### 4. Implement strict timeout and retry policy

Make all limits configuration values with safe defaults. The defaults should
fit comfortably inside GitHub Actions, for example:

- edition generation budget: 12 minutes;
- per-article budget: 4 minutes;
- individual HTTP attempt: 90 seconds;
- maximum attempts per article: 2 total;
- maximum provider attempts for a three-article edition: 6 total;
- maximum concurrent article writers: 1 or 2, unless measurement proves a
  higher value safe.

Use monotonic time. Every request must receive a timeout derived from the
remaining deadline; never pass an unbounded timeout.

Classify failures before deciding whether to retry:

- retryable: network reset, read timeout, 5xx, transient provider failure;
- structurally retryable: truncated JSON or recoverable parse failure, using a
  shorter prompt;
- permanent: authentication, invalid configuration, unsupported model,
  malformed request, quota/429 unless the provider explicitly supplies a safe
  retry window;
- validation failure: invalid article content after a successful response.

Do not retry permanent errors or validation failures by launching another
review tree. Do not allow provider fallback to create another retry budget.
If fallback is enabled, it is one direct attempt and consumes the same global
attempt budget.

### 5. Make the edition deadline real

The edition loop must check the deadline before starting each article and before
each attempt. It must stop starting new work when the remaining time cannot
support the configured per-article budget.

Do not submit an unlimited set of futures and then wait for all of them. If
concurrency is used, track each future explicitly, cancel pending futures at
deadline, and ensure the worker's HTTP request has its own finite timeout.
The function must return a report even when one article times out or fails.

The requested article count is a maximum, not a promise. A two-article or
one-article result is valid if the remaining budget does not support more.

### 6. Add deterministic validators

Implement or reuse local validators for:

- strict JSON parsing;
- required fields and types;
- non-empty body;
- permitted article format;
- minimum and maximum word count;
- required sections for the selected format;
- valid/safe HTML compatible with the renderer;
- source URLs present and syntactically valid;
- every source URL belongs to the dossier;
- no homepage/navigation-only source;
- evidence level compatible with the dossier;
- duplicate identity/title detection;
- no placeholder text, empty citations, or forbidden unsupported claims;
- renderer/publication schema compatibility.

Return a list of stable validation codes, for example:
`missing_field`, `invalid_json`, `source_not_in_dossier`, `too_short`,
`unsafe_html`, and `duplicate_story`. The report must include codes and safe
human-readable messages.

### 7. Persist resumable, secret-free state

Before and after each attempt, write a compact state record containing:

- run ID;
- object ID;
- selected rank;
- dossier hash;
- attempt number;
- provider/model name;
- start and end timestamps;
- elapsed seconds;
- status;
- failure category;
- validator codes;
- output artifact path, when present.

Do not persist API keys, full prompts, model reasoning, or sensitive headers.
On rerun, reuse a completed valid article when its object ID and dossier hash
match. Never regenerate a valid result solely because the workflow restarted.

### 8. Separate release candidate from publication

V4 must write a release-candidate package first. Publication must consume only
that package after the release gate passes.

Use explicit statuses:

- `ready`: valid article(s) exist and no blocking condition exists;
- `partial`: valid article(s) exist, but requested work was skipped or failed;
- `needs_review`: output exists but local policy requires human review;
- `provider_failure`: provider work failed;
- `no_publishable_story`: no valid article exists;
- `deadline_exceeded`: the budget ended before all requested work finished;
- `cancelled`: the run was interrupted.

The release gate must reject publication when:

- zero valid articles exist;
- the run is cancelled or deadline-exceeded without a valid release package;
- any article is incomplete or schema-invalid;
- the report claims success while provider failures are present;
- the package contains unvalidated or duplicate content.

Partial success may publish only the validated articles, according to the
existing publication policy. It must never be mislabeled as a full success.

### 9. Instrument the real work

Emit one concise line when each stage changes state, such as:

```text
[2/3] story title — writer attempt 1/2 — deepseek — 42s elapsed
```

At completion, write a report whose counters reconcile exactly:

- feed items received;
- selected dossiers;
- requested articles;
- attempts started/completed;
- provider requests by provider;
- completed, partial, needs-review, failed, skipped counts;
- total generation seconds;
- per-article elapsed seconds;
- release decision;
- publication decision.

The provider request counter must be incremented at the actual request
boundary, not inferred from a later summary. Never report zero calls after
requests were made.

## Integration points to inspect

Before editing, read and map the current contracts in:

- `scripts/insights_v3.py`;
- `scripts/v3_generation.py`;
- `scripts/editorial_pipeline.py`;
- `scripts/editorial_scoring.py`;
- `scripts/model_router.py`;
- `scripts/v3_publish.py`;
- `.github/workflows/daily-insights-agent.yml`;
- the existing tests for generation, routing, validation, and publishing.

Reuse sound ingestion, story selection, dossier construction, rendering, and
publication code. Do not rewrite feed collection as part of this change. Do
not change live publication behavior until the v4 release package has passed
the existing publisher validation.

Add an explicit workflow/CLI selection such as `--pipeline v4` or the
repository's equivalent. The default should remain v3 until rollout is
complete, unless the deployment owner explicitly changes it after the gates.

## Tests required before deployment

Add deterministic tests with mocked providers proving:

1. A valid article requires exactly one provider call.
2. No hidden reviewer or revision call occurs.
3. A timeout returns within the configured bound.
4. An article performs at most two total attempts.
5. Fallback cannot multiply the retry budget.
6. Three requested articles have a finite maximum of six provider attempts.
7. No new article starts after the edition deadline.
8. A completed article survives another article's failure.
9. Malformed JSON is rejected locally.
10. A source URL outside the dossier is rejected locally.
11. Duplicate story identity is rejected.
12. Partial output is reported as `partial`.
13. Zero valid articles cannot publish.
14. Cancelled/deadline-exceeded output cannot publish improperly.
15. Matching completed state is reused on rerun.
16. Diagnostics contain no secrets, prompts, or reasoning traces.
17. Reported provider calls equal actual mocked request calls.
18. Existing v3 tests and publisher tests still pass.

Also add one integration-style test that runs the complete v4 path with three
mocked dossiers and asserts that it terminates, returns a reconciled report,
and produces a release-candidate package without making network calls.

## Execution and rollout sequence

Follow this sequence and record the evidence in the implementation PR or
mandate document:

1. Implement v4 behind an explicit switch.
2. Run focused unit tests for the writer, validators, deadline, retry, state,
   and release gate.
3. Run the complete test suite and publication validation.
4. Run GitHub Actions shadow mode to verify feed ingestion and selection.
5. Run one-article v4 preview and inspect the package and call count.
6. Run three-article v4 preview and verify completion within the generation
   budget.
7. Confirm partial, timeout, and provider-failure diagnostics using mocked or
   preview-safe paths.
8. Run one controlled one-article publish.
9. Verify the live edition, article count, commit, and release report.
10. Only after all gates pass, switch the scheduled workflow to v4.
11. Keep the v3 switch and rollback instructions documented until v4 has
    demonstrated stable scheduled runs.

## Completion criteria

The work is complete only when all of the following are true:

- v4 no longer calls the multi-agent editorial pipeline in its normal path;
- one article has at most one writer call plus one bounded retry;
- a three-article preview finishes inside the declared budget;
- provider attempts are finite and reported accurately;
- partial success is preserved;
- deadline and cancellation cannot accidentally publish incomplete content;
- a release-candidate package is produced before publication;
- existing publisher validation passes;
- one controlled production publish is verified;
- measured runtime, provider calls, article outcomes, and live verification are
  recorded.

## Explicit non-goals

Do not solve this by:

- increasing the GitHub Actions timeout;
- adding more AI reviewers;
- lowering evidence or quality requirements;
- forcing the requested article count;
- silently dropping provider failures;
- publishing unvalidated drafts;
- making live provider calls from unit tests;
- deleting v3 before v4 has passed controlled production verification.

## Final implementation report

At the end, report in plain English:

- what files changed;
- how the old call tree was removed or bypassed;
- the exact retry and timeout limits;
- the test results;
- the measured one-article and three-article runtimes;
- actual provider request counts;
- release/publication outcomes;
- rollback instructions;
- any remaining known limitation.
