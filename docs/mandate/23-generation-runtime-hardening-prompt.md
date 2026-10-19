# Implementation Prompt: Harden Insights Generation Runtime and Provider Timeouts

## Role

You are a senior Python reliability engineer working on the Light Tower Group
Insights generator. Make a focused, production-quality change that prevents a
generation run from hanging for tens of minutes while preserving editorial
quality, provider failover behavior, evidence boundaries, publication safety,
and truthful reporting.

Do not redesign the editorial system. Do not lower the quality floor. Do not
silently publish partial or failed work. Improve the runtime contract around
the existing v3 generation pipeline.

## Objective

Make the generation deadline real.

The system must stop starting new article work when the generation deadline is
reached, cancel work that has not started, bound provider request time, avoid
unbounded retry/fallback multiplication, preserve completed results, and write
clear diagnostics explaining which article and stage consumed time.

The run must terminate predictably whether the provider succeeds, truncates,
returns HTTP 429, hangs until timeout, or repeatedly fails over to another
provider.

## Evidence from the latest production run

Production run:

https://github.com/benr99/lighttowergroup/actions/runs/33188271350

It was manually cancelled after approximately 44 minutes while still inside
`Build the curated edition`. It never reached publication.

The preceding one-article production test succeeded, but the full three-article
run exposed a runtime problem:

- feed ingestion completed normally;
- provider preflight completed normally;
- the build step remained active for roughly 43 minutes;
- no publication step was reached;
- no cancellation-safe generation diagnostic was available because the build
  had not returned its report;
- the workflow job timeout was 120 minutes;
- the generation deadline passed to v3 is 3600 seconds;
- the generation pool checks the deadline before starting a task, but does not
  cancel active futures or enforce a hard outer wall-clock limit;
- each provider request can wait up to 150 seconds and retry twice;
- provider failover can add another provider's attempts after the primary
  provider fails;
- the editorial pipeline contains multiple model stages per article, including
  drafting, financial review, editorial review, and possible revision.

Earlier failures also showed:

- DeepSeek V4 Pro returned `finish_reason=length` because hidden reasoning
  consumed the completion budget;
- OpenAI fallback requests returned HTTP 429;
- the new non-thinking DeepSeek request mode fixed the truncation problem;
- the subsequent one-article production run generated and published one valid
  article;
- the current problem is therefore runtime containment, not feed availability.

## Relevant code locations

Inspect these files before editing:

- `scripts/v3_generation.py`
  - `write_one()`
  - `write_all()`
  - `GenerationReport`
  - `DraftResult`
- `scripts/editorial_pipeline.py`
  - `_request_json()`
  - `stage_draft()`
  - `stage_financial_review()`
  - revision/review stages
- `scripts/editorial_scoring.py`
  - provider request timeout constants
  - `call_deepseek()`
  - retry and provider-chain handling
- `scripts/model_router.py`
  - provider selection
  - provider-chain construction
  - provider diagnostics
- `scripts/insights_v3.py`
  - `generation_deadline_s`
  - generation stage orchestration
  - run summary and report serialization
- `.github/workflows/daily-insights-agent.yml`
  - build timeout
  - failure gate
  - artifact preservation
- `tests/test_v3_generation.py`
- `tests/test_model_router.py`
- `tests/test_insights_v2_production.py`

Read the current implementation and tests first. Preserve existing user
changes and do not overwrite unrelated generated state.

## Required design

### 1. Establish one explicit runtime budget

Define a clear runtime contract for generation. The budget must include:

- the total generation wall-clock deadline;
- the per-article budget, derived from the remaining total budget and the
  number of work items;
- the per-provider-request timeout;
- the maximum number of attempts per provider call;
- the maximum number of providers attempted for one logical request.

Do not scatter unrelated timeout constants across modules. Centralize the
configuration or pass an explicit runtime/deadline object through the call
path.

Use monotonic time for all deadline calculations. Never compare wall-clock
timestamps for timeout enforcement.

### 2. Make the outer generation deadline enforceable

`write_all()` must not wait indefinitely for the entire executor pool.

Implement a clean design that:

- records the absolute monotonic deadline at the start;
- refuses to submit new work after the deadline;
- uses bounded waits while collecting futures;
- cancels futures that have not started when the deadline expires;
- returns completed results immediately;
- marks unfinished work as `skipped` with a reason such as
  `generation deadline exceeded`;
- does not misclassify deadline skips as provider failures;
- does not claim that cancelled work was written or held;
- does not require killing Python threads or processes as the normal path.

Important: cancelling a `ThreadPoolExecutor` future cannot stop a request that
is already running. Therefore active provider calls must also have a strict
request timeout that is shorter than the remaining generation budget.

If the chosen implementation uses a context manager around the executor,
verify that executor shutdown does not wait forever for active workers after the
deadline. Use an explicit shutdown strategy where necessary, and document the
tradeoff.

### 3. Bound provider requests by remaining time

Every HTTP request must receive a timeout derived from the remaining runtime,
not only a fixed global timeout.

The effective timeout should be the smaller of:

- the normal connect/read timeout;
- the remaining generation budget;
- the remaining per-article budget, if one exists.

Never pass a zero or negative timeout. If no meaningful time remains, fail the
request locally with a typed timeout/deadline error before making the HTTP
request.

Keep connect and read timeout semantics clear. If `requests` cannot enforce an
overall response deadline directly, wrap the request with an outer deadline
and make sure the practical behavior is still bounded.

### 4. Stop retry multiplication

Retries must be budget-aware.

For each logical model request:

- do not retry if the remaining budget cannot support another attempt;
- do not retry permanent errors such as authentication failures, invalid
  requests, unsupported models, or malformed configuration;
- retry transient errors only when appropriate: timeout, connection failure,
  408, 429, 500, 502, 503, or 504;
- cap attempts explicitly;
- cap total provider attempts across the logical request;
- use bounded backoff that is included in the deadline calculation;
- do not retry a truncated reasoning response endlessly;
- preserve the original error and the final error in diagnostics.

The fallback provider must not create an unbounded second retry tree. A logical
request should have a finite maximum number of total attempts across DeepSeek
and OpenAI.

### 5. Make provider selection honest

The current runtime has both a configured DeepSeek provider and an OpenAI
fallback. The implementation must distinguish:

- provider configured and reachable;
- provider request attempted and timed out;
- provider returned a transient error;
- provider returned a permanent error;
- provider response was truncated;
- provider fallback was attempted;
- fallback was unavailable because of HTTP 429 or missing credentials;
- request was never attempted because the local generation deadline expired.

Do not report `0 provider calls` when provider attempts actually occurred.
Ensure the run report, provider log, and per-article result agree.

Do not log API keys, authorization headers, prompt contents, full generated
articles, or other secrets.

### 6. Add progress diagnostics that survive slow runs

The generation stage must periodically emit safe progress information before
the entire stage completes. At minimum, record:

- generation start time;
- total requested articles;
- active article count;
- completed article count;
- article title or stable object ID;
- current stage: brief, draft, review, revision, or finalization;
- provider and model name;
- attempt number;
- elapsed seconds;
- remaining deadline seconds;
- timeout/deadline events;
- cancellation events.

Use stable IDs and truncated titles. Do not log prompts or article bodies.

The final report must still be written when generation ends because of a
deadline, cancellation, or provider exhaustion.

### 7. Preserve partial success correctly

If two of three articles finish and the third exceeds the deadline:

- preserve the two completed results;
- mark the unfinished item as skipped or failed according to the actual cause;
- do not discard completed drafts;
- do not publish automatically unless the existing publication contract allows
  the resulting edition and all existing gates pass;
- report the partial result honestly;
- ensure rollback metadata includes every file actually written.

The statuses must remain semantically distinct:

- `completed`: a valid article exists;
- `needs_review`: an article exists but is not cleared for automatic release;
- `held`: editorial gates intentionally produced no article without a system
  error;
- `failed`: the system attempted the work and encountered an error;
- `skipped`: work was not attempted or was stopped because of budget/deadline.

### 8. Keep the publication safety gate fail-closed

Do not weaken publication requirements.

The run must not publish when:

- all generation requests fail;
- zero articles are written;
- the edition status is not ready;
- a provider failure is incorrectly represented as a hold;
- the run was cancelled or timed out before a complete publication decision;
- generated artifacts are incomplete or invalid.

The GitHub Actions failure gate must run even when the build exits nonzero and
must preserve whatever diagnostics were created before failure.

### 9. Improve workflow-level containment

Inspect the GitHub workflow and make the runtime contract explicit.

Consider adding:

- a generation-specific timeout shorter than the entire job timeout;
- a diagnostic artifact upload with `if: always()`;
- a step summary containing generation duration, provider attempts, completed,
  skipped, held, and failed counts;
- a clear error when the generation deadline is exceeded;
- no automatic publish after a cancelled or timeout run.

Do not make the workflow silently ignore a cancelled generation.

## Required tests

Add deterministic unit tests using mocked providers and controlled monotonic
clocks where practical. Do not use live API calls in tests.

At minimum cover:

1. A request receives a timeout no greater than remaining budget.
2. A request is not started when the deadline has expired.
3. Pending futures are cancelled at the deadline.
4. Active work that times out becomes a deadline/timeout result rather than
   hanging the collector.
5. Completed futures are preserved when another future fails.
6. Retry logic stops when the remaining budget is too small.
7. Permanent provider errors are not retried unnecessarily.
8. 429 and transient errors are retried only within the finite attempt cap.
9. Fallback attempts do not multiply without a hard upper bound.
10. DeepSeek truncation is recorded as a provider failure.
11. A provider failure is not reported as a hold.
12. Deadline skips are not reported as failures.
13. Partial success produces truthful counts.
14. Cancellation writes a usable run report.
15. No API key or prompt text appears in diagnostics.
16. A zero-output publish run fails the workflow gate.
17. A valid partial edition follows the existing publication policy.
18. The normal successful one-article path still works.

Include at least one test proving that executor shutdown does not wait forever
after the generation deadline.

## Verification procedure

Run locally first:

```powershell
& .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
& .\\.venv\\Scripts\\python.exe -m py_compile scripts/*.py
& .\\.venv\\Scripts\\python.exe scripts/validate_publication.py
npm run check:js
npm run test:js
```

Then run controlled GitHub Actions tests in this order:

1. v3 shadow run to confirm feed ingestion and selection without model calls;
2. v3 preview with one article to confirm provider calls and no publication;
3. v3 preview with three articles to confirm bounded concurrency and runtime;
4. deliberate mocked/unit failure tests for timeout and retry behavior;
5. only after those pass, one controlled production publish attempt.

For every live run record:

- run URL and commit SHA;
- total duration;
- feed items and feed failures;
- selected and publication candidate counts;
- provider calls by provider;
- retries and fallbacks;
- written, review, held, skipped, and failed counts;
- publication decision;
- live verification result.

## Non-goals

Do not:

- lower the quality floor;
- publish weak or incomplete articles to make the count look healthy;
- remove evidence requirements;
- remove provider failover entirely;
- increase the workflow timeout as the only fix;
- hide errors by converting failures into holds;
- add unlimited retries;
- use `os._exit`, forced process termination, or destructive cleanup as the
  normal implementation;
- make live API calls from the test suite;
- rewrite unrelated feed configuration, site content, or generated archives;
- commit runtime artifacts or API responses containing secrets.

## Deliverables

Produce:

1. Clean, focused code changes implementing the hard runtime contract.
2. Tests covering deadlines, cancellation, retry bounds, provider accounting,
   partial success, and report integrity.
3. Any necessary GitHub Actions changes for timeout and artifact preservation.
4. A concise implementation note describing the runtime budget and worst-case
   request count.
5. Evidence from local tests and controlled GitHub Actions runs.

Before declaring success, answer these questions with measured evidence:

- What is the maximum possible provider-attempt count for one article?
- What is the maximum possible provider-attempt count for the whole run?
- What is the maximum time an active request can occupy a worker?
- What happens to pending work at the deadline?
- What happens to active work at the deadline?
- Can the executor shutdown wait indefinitely?
- Can a cancelled run publish anything?
- Can the final report distinguish failure, hold, and skip?
- Does the workflow turn a zero-output run red?

The implementation is complete only when these answers are explicit, tested,
and consistent with the code.
