# Light Tower Insights Generator: Current-State Model

## Purpose

This document describes how the generator works today, at the production
`main` commit inspected on 2026-08-28. It is an as-is model, not a proposal.
It separates:

1. what the code is designed to do;
2. what GitHub Actions actually invokes;
3. what recent production runs prove;
4. what remains uncertain or misleading.

The purpose is to establish a reliable baseline before replacing the current
generation architecture.

## Production reference

Current production commit:

```text
4e72d7815b1680403998e46cba1516ebf0016554
Disable DeepSeek thinking for article JSON
```

The working tree also contains unrelated untracked audit and artifact files.
They are not treated as part of the production program unless referenced by the
workflow or code.

## One-sentence description

GitHub Actions starts a Python process that fetches configured feeds and a small
number of listing pages, classifies and clusters the resulting documents into
events, rejects weak or previously covered events, fetches full text for
eligible candidates, scores and selects a global publication slate, makes many
nested AI calls per selected article, validates the resulting drafts, optionally
writes the edition to git, and finally verifies the live website.

The feed and research side is operational. The expensive nested article-writing
side is the current reliability and runtime risk.

## System map

```text
GitHub cron or manual dispatch
              |
              v
daily-insights-agent.yml
  - checkout selected ref
  - resolve schedule policy
  - install locked Python dependencies
  - run full baseline tests
  - preflight DeepSeek/OpenAI
  - run scripts/insights_v3.py
              |
              v
        v3 run(mode)
              |
   +----------+-----------+
   |                      |
   v                      v
feed ingestion       HTML listing intake
   |                      |
   +----------+-----------+
              v
       CanonicalItem documents
              |
              v
       sector classification
              |
              v
       event clustering
              |
              v
       eligibility/type gates
              |
              v
       editorial memory/novelty
              |
              v
       full-text retrieval/enrichment
              |
              v
       importance scoring
              |
              v
       sector slates + global publication slate
              |
              v
       v3_generation.write_all()
              |
              +--> one EditorialPipeline per article
              |       |
              |       +--> analytical brief (LLM)
              |       +--> prompt assembly
              |       +--> draft (LLM)
              |       +--> financial review (LLM)
              |       +--> editorial review (LLM)
              |       +--> fact verification
              |       +--> revision (LLM if needed)
              |       +--> post-revision reviews
              |       +--> possible second revision/reviews
              |
              v
       generation report + draft artifacts
              |
              v
       publication decision
              |
              +--> review branch, or
              +--> publish_generated.py -> git push main
                                      |
                                      v
                          Netlify deploy + live verification
```

## Stage-by-stage flow

### 1. Trigger and checkout

The workflow is [`daily-insights-agent.yml`](../../.github/workflows/daily-insights-agent.yml).

It has two schedules:

- `7 11 * * *` UTC;
- `7 12 * * *` UTC.

Both exist to preserve a 07:07 New York run across daylight-saving changes.
`resolve_schedule_policy.py` uses the cron expression that fired, converts it
to New York time, and runs only if the resulting local time is between 07:05
and 07:15. A manual dispatch always runs and takes its selected mode.

The workflow checks out `main` for scheduled runs and the selected branch for
manual runs. It installs `scripts/requirements.lock`, runs Python compilation,
the complete Python test suite, publication validation, JavaScript syntax checks,
and JavaScript tests before any live provider work.

### 2. Provider preflight

The workflow exports:

- `DEEPSEEK_API_KEY`;
- `DEEPSEEK_MODEL=deepseek-v4-pro`;
- `OPENAI_API_KEY`;
- `NEWSAPI_KEY`.

`model_router.select_provider(for_writing=True)` performs a minimal `ping`
request to DeepSeek. If it is not healthy, it pings OpenAI and selects it if
healthy. The preflight proves that a provider answers a tiny request; it does
not prove that the provider can complete the much larger article contract.

The production writing chain is normally DeepSeek first, then OpenAI. A failed
DeepSeek article request can switch to OpenAI. Provider events are appended to
`.editorial-state/provider-log.jsonl` without keys or authorization headers.

### 3. Feed ingestion

`ingestion.fetch_all_sources()` loads active entries from
`config/sources.json`. The registry currently contains 255 configured sources,
171 active at the time of inspection.

It skips sources quarantined by `SourceHealthLedger`, then submits the remaining
feeds to a thread pool with eight workers. Each feed uses:

- connect timeout: 8 seconds;
- read timeout: 15 seconds;
- redirects enabled;
- an application User-Agent;
- feedparser over the returned bytes;
- a 36-hour recency window;
- at most 500 entries per feed.

Each feed returns normalized `CanonicalItem` objects. Non-200 responses are
currently recorded as an empty result rather than a distinct HTTP failure in
the ingestion path. Exceptions are recorded as failures. If at least half of
the attempted feeds fail, the ledger treats the event as a shared outage and
releases quarantines rather than blaming individual publishers.

The separate `source_health_probe.py` gives better feed classifications than
the production ingester. The GitHub probe found 125 of 255 usable sources and
710 recent items, confirming that the source universe is capable of supplying
the pipeline.

### 4. HTML listing intake

After RSS ingestion, v3 reads up to 12 active sources whose `source_type` is
`html_listing`. Each listing is limited to 15 items. These items are converted
to the same `CanonicalItem` shape and appended to the feed documents.

This means the pipeline is not RSS-only. A run's total input is:

```text
documents_from_feeds + documents_from_listings
```

### 5. Classification

`classification.classify_batch()` assigns sector information to the incoming
documents. Classification failures are accumulated in the run report; the v3
process generally continues rather than aborting the entire run.

An item without a usable primary sector can be dropped later. This is visible
in validation output as a warning that an item was dropped because classification
failed.

### 6. Event clustering

`event_clustering.cluster_to_objects()` groups multiple documents reporting the
same event into an `IntelligenceObject`. This is the main deduplication boundary.
The run records:

- objects after clustering;
- documents consolidated;
- the source references retained on each object.

The object—not an individual feed entry—is the unit that proceeds toward
selection and writing.

### 7. Type and eligibility gates

`eligibility.apply(obj)` assigns event-family/type decisions and determines
whether an object is eligible. Eligibility is not simply a keyword filter; it
is intended to reject material that cannot support the editorial product.

Failures in the eligibility function mark the object ineligible and append an
error to the run report, while the rest of the run continues.

### 8. Editorial memory and novelty

`EditorialMemory` loads `.editorial-state/editorial-memory.json`. If empty, it
seeds itself from the published manifest. It compares current objects against
prior coverage before enrichment, so already-published or duplicate material is
not supposed to consume retrieval budget.

It tracks states such as:

- new;
- minor follow-up;
- material update;
- duplicate;
- already published.

At the end of the run it observes the objects and saves memory. This is a
durable side effect even when no article is published.

### 9. Full-text retrieval and enrichment

Eligible, non-stale, non-duplicate objects are sorted by source tier and passed
to `retrieval.enrich_objects()`.

Current v3 defaults:

- enrichment candidate limit: 250;
- enrichment budget: 420 seconds;
- robots-aware retrieval;
- per-domain throttling;
- cached retrieval results;
- full, partial, blocked, failed, and skipped statuses.

The retriever uses source URLs from the object, checks robots rules, requests
article pages, extracts readable text, canonical URLs, and publication dates,
and records retrieval results. The dossier later exposes only the evidence the
object actually holds.

The 420-second enrichment budget is separate from the later generation budget.
It is not the source of the cancelled 2026-08-28 run; that run reached the
generation build step after ingestion, retrieval, and selection.

### 10. Importance scoring

`importance.score_all(objects)` calculates the editorial scoring dimensions and
produces a score distribution. The run warns when a measure has no
discriminating power. Recent runs reported `evidence` as a degenerate measure,
which means that dimension did not help distinguish candidates even though it
did not necessarily stop publication.

Scoring is deterministic/local at this stage. It does not consume the provider
writing calls used later.

### 11. Sector slates and global publication slate

`selection.build_slates()` creates two related outputs:

1. per-sector scouting slates, which explain coverage and shortfalls;
2. one bounded global publication slate, which is the only list sent to article
   generation.

The run may select many stories for diagnostics while generating only the global
publication candidates. The workflow passes:

- daily target: 3;
- article limit: manual input, normally 1, 3, 5, or 10;
- quality floor: 40;
- generation workers: 3.

The selection code now allows a larger system maximum, but the workflow still
requests three articles for the normal daily target. A sector shortfall does
not automatically mean a feed failure; it can mean the candidates did not
clear the quality floor.

### 12. Article generation entry point

`insights_v3.run()` calls `v3_generation.write_all()` when mode is `preview` or
`publish`. Shadow mode never calls the provider.

`write_all()` sorts selected objects by recommended depth, creates a
`ThreadPoolExecutor(max_workers=3)` in the production workflow, and submits one
`write_one()` task per selected publication object.

The deadline argument defaults to 3600 seconds. It is checked only before a
task begins. It does not currently create a hard outer deadline around the
executor and does not cancel active network calls.

This is the critical runtime boundary.

### 13. Per-article pipeline

`write_one()` converts the object into:

- a `CanonicalItem` for the editorial pipeline;
- a dossier containing source names, URLs, retrieved text, facts, evidence
  level, novelty, material claims, gaps, and allowed depth.

Then it calls `editorial_pipeline.run_editorial_pipeline()`.

The current pipeline is not one model call. It is a conditional multi-stage
workflow:

#### Stage A: analytical brief

The model creates an analytical brief from the item and dossier.

#### Stage B: prompt assembly

The system constructs a large article-writing prompt, including the dossier,
format, requested word range, evidence rules, and excellence ledger contract.

#### Stage C: draft

The model must return a complete JSON article. The request uses a large token
budget and DeepSeek non-thinking mode for long JSON responses. The response is
parsed and checked for required fields.

#### Stage D: financial review

The draft is sent to another model review asking whether financial mechanisms,
claims, and conclusions are supported.

#### Stage E: editorial review

The draft is sent to another model review for editorial quality.

#### Stage F: fact verification

The draft is checked against the brief and dossier.

#### Stage G: final revision

If issues exist, the model is asked to rewrite the complete article. The revised
article is reviewed again.

In some cases a second revision and second round of reviews occur. Therefore
the number of provider calls per article is data-dependent and can be much
larger than one.

### 14. Provider request behavior

`editorial_scoring.call_deepseek()` currently uses:

- a 90-second timeout for short JSON calls;
- a 150-second timeout for long calls;
- two attempts per provider;
- retry on selected transient HTTP errors;
- provider-chain fallback after the preferred provider is exhausted;
- JSON parsing and required-field validation after the response;
- explicit rejection of `finish_reason=length`;
- non-thinking mode for long DeepSeek JSON requests.

The non-thinking change fixed the original DeepSeek truncation pattern. The
prior production failure showed DeepSeek reasoning consuming the completion
budget and OpenAI fallback returning HTTP 429. The later one-article run proved
that non-thinking DeepSeek can complete an article.

The remaining issue is that the call tree is still large and each call is
allowed to consume a long timeout. The outer generation loop waits for submitted
futures to finish.

### 15. Generation result accounting

Each `DraftResult` records:

- object ID;
- title;
- sector;
- depth;
- status;
- article if present;
- stages run;
- errors;
- diagnostics;
- seconds;
- estimated spend.

`GenerationReport` counts:

- requested;
- written;
- needs review;
- held;
- skipped on budget/time;
- failed;
- spend;
- elapsed time;
- per-article results.

The newer status accounting distinguishes provider failures from editorial holds.
However, if the Python process is cancelled while `write_all()` is waiting in
the executor, the final report may never be created.

### 16. Publication decision

In publish mode, `v3_publish.publish()` accepts the completed drafts and object
map. It:

- skips or holds incomplete/review-required work according to policy;
- renders article pages and related files;
- updates edition/manifest structures;
- records publication results;
- updates memory and budget state.

`finalize_publication()` creates `.editorial-state/publication-decision.json`.
The workflow's zero-output gate requires:

- a decision file;
- `edition_status == ready`;
- article count greater than zero;
- failed count equal to zero.

If the decision is review-required, the workflow pushes a review branch and opens
a pull request instead of publishing directly to `main`.

### 17. Git publication and deployment

If automatic publication is allowed, `scripts/publish_generated.py` adds the
generated files, commits them, pushes to `main`, and verifies that the remote
commit matches.

Netlify then deploys the repository. The workflow calls
`verify_deployment.py` against `https://lighttowergroup.co`. If the live
edition does not match the expected release, it calls `rollback_release.py`.

Preview mode does not enter this path. Shadow mode does not generate or publish.

## State and artifact ownership

| File or directory | Purpose | Written by | Durable side effect? |
|---|---|---|---|
| `config/sources.json` | configured source universe | manual/config work | yes |
| `.editorial-state/source-health.json` | source circuit-breaker health | ingestion | yes |
| `.editorial-state/editorial-memory.json` | seen/published coverage memory | v3 run | yes |
| `.editorial-state/event-memory.json` | event memory | pipeline components | yes |
| `.editorial-state/provider-log.jsonl` | secret-free provider attempts | model router | yes |
| `.editorial-state/spend-ledger.json` | estimated provider spend | budget tracker | yes |
| `.editorial-state/v3-candidates.json` | all candidate objects | v3 artifact writer | run artifact |
| `.editorial-state/v3-slates.json` | sector/global slate decisions | v3 artifact writer | run artifact |
| `.editorial-state/v3-drafts.json` | generated draft results | v3 artifact writer | run artifact |
| `.editorial-state/v3-run.json` | complete v3 report | v3 artifact writer | run artifact |
| `.editorial-state/run-summary.md` | human-readable summary | publication finalizer/workflow | yes |
| `.editorial-state/publication-decision.json` | publish/review decision | v3 publisher | yes |
| `editions/YYYY-MM-DD.json` | edition package | publisher | public/repository |
| `insights/*.html` | article pages | publisher | public/repository |
| `insights.json` | article manifest | publisher | public/repository |
| `latest-edition.json` | latest edition pointer | publisher | public/repository |
| `feed.xml`, `sitemap.xml` | discovery outputs | publisher/build | public/repository |

## Modes and what they really mean

| Mode | Ingest | Select | Model generate | Validate generated edition | Publish site |
|---|---:|---:|---:|---:|---:|
| `shadow` | yes | yes | no | no | no |
| `preview` | yes | yes | yes | no publication validation step | no |
| `publish` | yes | yes | yes | yes | yes if decision allows |

The name “preview” can be misleading: it performs real provider calls and can
consume money. It only prevents public publication.

## What recent runs prove

### Feed probe

GitHub feed probe run [33124088641](https://github.com/benr99/lighttowergroup/actions/runs/33124088641):

- 255 sources tested;
- 125 usable;
- 710 items in 36 hours;
- 49.0% usable coverage.

Conclusion: feed connectivity is sufficient for a daily run.

### Shadow run after restoration

GitHub run [33124868495](https://github.com/benr99/lighttowergroup/actions/runs/33124868495):

- 731 items from 170 feeds;
- 0 feed failures;
- 19 selected stories;
- 3 publication candidates;
- no provider calls because shadow mode intentionally does not generate.

Conclusion: feed ingestion, classification, enrichment, scoring, and slate
selection completed successfully.

### Preview before the DeepSeek mode fix

GitHub run [33125360546](https://github.com/benr99/lighttowergroup/actions/runs/33125360546):

- 690 feed items from 170 feeds;
- 3 publication candidates;
- 0 of 3 written;
- all three draft attempts failed;
- DeepSeek returned `finish_reason=length`;
- OpenAI fallback returned HTTP 429;
- the workflow correctly failed.

Conclusion: the old failure was a provider/output-contract problem.

### Preview after the DeepSeek mode fix

The following preview succeeded on the restoration branch:

- 633 feed items from 170 feeds;
- 3 candidates processed;
- 24 provider calls;
- 0 fallback calls;
- 1 article fully written;
- 2 articles written but flagged for review;
- no public files changed.

Conclusion: the non-thinking DeepSeek request fixed the catastrophic truncation
failure, but the pipeline still used many provider calls.

### One-article production publish

GitHub run [33187438880](https://github.com/benr99/lighttowergroup/actions/runs/33187438880):

- 670 feed items from 170 feeds;
- 1 feed failure and 62 empty feeds;
- 1 article written;
- DeepSeek used successfully;
- publication validation passed;
- one article was published and live verification passed.

Conclusion: the repaired path can publish a valid article end-to-end.

### Three-article daily run that was cancelled

GitHub run [33188271350](https://github.com/benr99/lighttowergroup/actions/runs/33188271350):

- manual production publish request for three articles;
- baseline tests passed;
- provider preflight passed;
- build step remained active for approximately 44 minutes;
- no publication step was reached;
- run was manually cancelled;
- no final build diagnostics were available because cancellation occurred inside
  generation.

Conclusion: the current multi-stage, multi-call writer is not bounded enough for
the normal three-article run.

## Current failure boundaries

### Confirmed working

- GitHub scheduling and manual dispatch;
- source fetching from GitHub Actions;
- feed probe classification;
- classification and clustering;
- eligibility and novelty checks;
- full-text retrieval;
- slate selection;
- provider preflight;
- DeepSeek non-thinking article generation for at least one article;
- publication validation;
- git publication;
- live verification;
- zero-output publication gate on completed runs.

### Confirmed fragile

- nested model-call count per article is data-dependent;
- article stages can launch additional review and revision calls;
- provider retries and fallback add latency;
- `write_all()` waits for the executor to finish all submitted futures;
- generation deadline is checked before tasks but is not a hard outer deadline;
- active HTTP calls cannot be cancelled by cancelling a future;
- cancellation during generation may lose the final run report;
- preview mode consumes real provider spend;
- provider preflight checks only a tiny ping, not the real article contract;
- `evidence` scoring currently has no discriminating power;
- source ingestion still conflates some non-200/empty conditions;
- `audience-signals-live write error: fs is not defined` appears as a non-blocking
  validation warning.

### Misleading or stale documentation

- workflow comments still say scheduled runs retain a five-candidate ceiling,
  while current workflow input and selection behavior allow more;
- the v3 module header says production remains on v2, while the workflow invokes
  v3 by default;
- older notes refer to `verified` feed flags, while the current registry uses
  health records and the probe tool;
- a green scheduled run can be an intentional DST guard skip;
- a green historical publish run can still have reported zero live articles if
  it predates the current gate or followed a different path.

## Runtime model of the current writer

The important relationship is:

```text
one selected article
  -> one EditorialPipeline
  -> 1 analytical brief call
  -> 1 draft request, potentially 2 attempts
  -> 1 financial review call, potentially 2 attempts
  -> 1 editorial review call, potentially 2 attempts
  -> 1 fact-verification call or local check, depending on implementation
  -> 0–2 revision calls, potentially retried
  -> additional post-revision reviews
```

The exact path varies by evidence depth and review findings. Consequently, the
workflow's `--workers 3` limits concurrent articles, not total provider calls.
Three concurrent articles can each have several sequential model stages. Each
stage may wait on two attempts and a fallback chain. This is why the runtime is
not proportional to “three articles × one call.”

## Current publication truth

The generator is not simply “on” or “off.” The accurate status is:

```text
The source and research pipeline works.
The provider can generate at least some valid articles after the DeepSeek fix.
The publication path works for a one-article run.
The normal three-article run is still operationally too slow and can be cancelled
before it produces a final report.
```

This is the baseline the lean rewrite must improve.

## Questions the rewrite must answer against this model

Before replacing v3, the implementation should demonstrate:

1. How many provider calls are made per article?
2. What is the maximum call count for a three-article run?
3. Which stages are genuinely necessary for publication quality?
4. Which checks can be deterministic/local instead of model-based?
5. What is the maximum elapsed time for one article?
6. What is the maximum elapsed time for the run?
7. What happens if one article stalls while two finish?
8. What artifacts survive cancellation?
9. What exact state is safe to reuse on a rerun?
10. What conditions permit publication of a partial edition?

Until those answers are explicit and tested, the system should not be described
as reliably working for the normal three-article production target.
