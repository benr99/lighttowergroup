# Build Prompt: Replace the Slow Insights Generation Path with a Lean, Reliable Pipeline

## Mission

The current v3 generation design is too complicated and too slow to operate
reliably. Do not keep adding timeout patches around it. Replace the critical
generation path with a smaller, bounded architecture that can consistently
produce a useful edition or fail quickly with an honest explanation.

The goal is not to force three articles every day. The goal is to publish only
valid, evidence-supported work within a predictable runtime.

## Evidence that the current approach is failing

The production run on 2026-08-28 was cancelled after approximately 44 minutes
while still inside `Build the curated edition`:

https://github.com/benr99/lighttowergroup/actions/runs/33188271350

The current pipeline performs multiple model calls per article: analytical
brief, draft, financial review, editorial review, and possible revision. Each
call can retry and can fall through to another provider. The result is a large
and unpredictable call tree.

The previous one-article test proved that the provider and publisher can work,
but the three-article run showed that the system cannot reliably complete the
full critical path in a reasonable time.

## Required architectural change

Implement a new lean generation path, preferably named `v4`, rather than
continuing to expand v3. Keep v3 available as a rollback path until v4 passes
the production tests.

The new path must have these stages:

```text
Ingest → normalize → select → retrieve evidence →
one bounded writer call per article → local validation → publish
```

Do not put model-based review, revision, scoring, or multiple editorial agents
inside the normal publication critical path.

## Design rules

### 1. One writer call per article

For each selected story, assemble one compact, evidence-bounded prompt and make
one model call that returns the complete article contract.

The call must return:

- title;
- excerpt;
- body HTML;
- source URLs drawn only from the dossier;
- the required evidence/analysis fields;
- article format and word count metadata.

The prompt must explicitly tell the model to use non-thinking mode for DeepSeek
structured writing. The request must have a finite output limit and a finite
wall-clock timeout.

Do not make a separate AI call for an analytical brief, financial review,
editorial review, revision, or self-score before publication.

### 2. Move quality checks into deterministic code

Replace critical-path model reviewers with local validators wherever possible.
Validate in Python:

- valid JSON;
- required fields;
- non-empty body;
- word-count range;
- required sections/format;
- source URLs are present in the dossier;
- no invented source URLs;
- no missing evidence for material claims;
- no duplicate article identity;
- no forbidden claims or empty placeholders;
- HTML safety and renderer compatibility;
- article is not a homepage or navigation page;
- evidence level matches the allowed article depth.

If validation fails, mark the article `needs_review` or `failed` with a precise
reason. Do not automatically launch another chain of model calls.

### 3. Use one bounded retry only

Allow at most one retry for a transient or structurally recoverable failure.

The retry must:

- use a shorter prompt if the original was too large;
- use the same article dossier;
- have its own strict timeout;
- be skipped for authentication, quota, unsupported-model, or permanent 4xx
  errors;
- never invoke a second review/revision tree.

Provider fallback is optional and must be one direct fallback attempt, not a
second set of retries. If the fallback is unavailable or returns 429, stop that
article immediately.

### 4. Bound the whole run

Set a practical generation budget for the complete edition, for example:

- 12 minutes for generation;
- 3–4 minutes maximum per article;
- 90 seconds maximum per provider attempt;
- at most two total attempts per article;
- at most six total provider attempts for a three-article run.

Choose values that fit the existing GitHub Actions environment, but make them
explicit and testable.

The entire run must return before the workflow timeout. Do not rely on the
120-minute job timeout as a design feature.

If time is running out, stop starting new articles. Preserve completed drafts
and report skipped work. A smaller successful edition is preferable to a hung
run.

### 5. Adaptive article count

Treat the daily target as a maximum, not a guaranteed workload.

Select up to the requested number of stories, then process only as many as the
remaining budget permits. If the first article consumes most of the budget,
stop cleanly rather than starting work that cannot finish.

Never lower the quality floor just to hit the target.

### 6. Make the run resumable

Persist a compact per-article state record before and after each attempt:

- object ID;
- title;
- selected rank;
- dossier hash;
- attempt number;
- provider/model;
- start/end time;
- status;
- failure category;
- validator results;
- output artifact path.

On rerun, reuse completed valid drafts from the same run or dossier hash. Do
not pay for and regenerate an article that already passed validation.

Do not persist secrets, prompts, or full model reasoning traces.

### 7. Separate publication from generation

Generation should create a release candidate package. Publication should only
consume that package after all local checks pass.

The publication decision must distinguish:

- `ready`: at least one valid article and no blocking failures;
- `partial`: valid articles exist but some requested work was skipped;
- `needs_review`: article exists but requires human approval;
- `provider_failure`: model work failed;
- `no_publishable_story`: no valid article exists;
- `cancelled` or `deadline_exceeded`.

The workflow must not publish a package with zero valid articles, incomplete
state, provider failure mislabeled as a hold, or a cancelled run.

### 8. Instrument the actual critical path

Emit one concise progress line per article and stage:

```text
[2/3] story title — writer attempt 1/2 — deepseek-v4-pro — 42s elapsed
```

At completion, report:

- feed items;
- selected stories;
- article attempts;
- provider attempts by provider;
- completed/partial/review/failed/skipped counts;
- total generation seconds;
- per-article seconds;
- publication decision.

The numbers must reconcile. Do not report zero provider calls when requests
were made.

## Implementation guidance

Inspect the existing code before editing:

- `scripts/insights_v3.py`
- `scripts/v3_generation.py`
- `scripts/editorial_pipeline.py`
- `scripts/editorial_scoring.py`
- `scripts/model_router.py`
- `scripts/v3_publish.py`
- `.github/workflows/daily-insights-agent.yml`

Reuse the existing ingestion, selection, dossier, renderer, and publication
contracts where they are sound. Replace the multi-agent article-writing chain,
not the feed and evidence system.

Prefer a small new module such as `scripts/v4_generation.py` with clear
interfaces over further conditional branching inside v3.

The writer interface should look conceptually like:

```python
result = write_article_once(
    dossier=dossier,
    provider=provider,
    deadline=article_deadline,
)
```

It should return a typed result, never hang, and never raise an uncaught
provider exception into the whole edition.

## Required tests

Add deterministic tests proving:

1. A valid article can be created with one model call.
2. The writer makes no hidden review/revision calls.
3. A provider timeout returns a bounded failure.
4. One retry is the maximum for an article.
5. Fallback cannot multiply retries.
6. A three-article run has a finite maximum provider-attempt count.
7. The run stops starting new work when its deadline is reached.
8. Completed articles survive a later article failure.
9. Local validators reject malformed JSON and missing evidence.
10. Source URLs must come from the dossier.
11. A partial edition is reported as partial, not success or failure incorrectly.
12. A zero-article run cannot publish.
13. A cancelled/deadline-exceeded run cannot publish.
14. Completed drafts are reused on rerun.
15. Diagnostics contain no API keys, prompts, or hidden reasoning.
16. The provider call count in the report equals the actual request count.

## Deployment sequence

1. Build v4 behind an explicit pipeline switch.
2. Run local unit tests and publication validation.
3. Run GitHub Actions shadow mode to confirm ingestion and selection.
4. Run one-article preview mode and verify one bounded writer call.
5. Run three-article preview mode and verify it finishes within the chosen
   generation budget.
6. Review the generated article package and diagnostics.
7. Run one controlled publish mode.
8. Verify the live edition and article count.
9. Only then make v4 the scheduled production path.

## Non-goals

Do not:

- add more nested AI reviewers;
- increase timeouts to hide the problem;
- increase the article target to compensate for failures;
- lower the quality floor;
- publish incomplete drafts;
- treat provider failure as editorial hold;
- make live API calls in unit tests;
- delete v3 until v4 has passed the controlled production sequence.

## Completion standard

The rewrite is complete only when a three-article preview:

- finishes within the stated runtime budget;
- makes a measured, finite number of provider attempts;
- produces honest per-article results;
- preserves partial success;
- produces a valid release package;
- never hangs waiting for nested reviewers;
- and does not publish unless the release gate passes.

Report the measured runtime, provider call count, article results, and live
verification URL.
