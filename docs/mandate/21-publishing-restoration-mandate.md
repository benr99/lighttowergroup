# Mandate 21 — Restore Publishing, Then Restore Volume

**Written:** 27 August 2026
**Status:** open, unstarted
**Predecessors:** [18 — ranker redesign](18-ranker-redesign-phase1.md), [19 — source health audit](19-source-health-audit.md), [20 — completion status](20-completion-status.md)

---

## 0. How to use this document

This is an executable mandate, not a discussion. Work the sections in order. Each
work order states the verified problem, the evidence behind it, the change
required, and the condition that proves it done. Do not begin a later order until
the earlier one meets its acceptance criteria, because the later ones are
unmeasurable while the writer is broken.

Where this document asserts a fact, that fact was verified against run logs or
source on 27 August 2026, and the evidence is quoted inline. Where it states a
hypothesis, it says so and tells you how to test it. **Do not treat the hypothesis
in Work Order 1 as established.** Prove it first.

---

## 1. Situation

The Light Tower editorial pipeline has not stopped. It ingests, clusters, scores
and selects every morning without error. It published 27 articles between 10 and
25 August. What failed is a single stage — the writer — and it failed gradually
enough that no alarm fired.

```
articles written per run     24 Aug   4 of 5
                             25 Aug   1 of 5
                             26 Aug   0 of 5
                             27 Aug   run never fired
```

The proximate cause is that every draft request on 26 August terminated against
its output ceiling:

```
26 Aug — every draft call, from .editorial-state/provider-log.jsonl

  success  deepseek  in 2,676  out 8000    (= max_tokens, truncated)
  success  deepseek  in 2,702  out 8000    (= max_tokens, truncated)
  success  deepseek  in 3,247  out 8000    (= max_tokens, truncated)
  success  deepseek  in 3,273  out 8000    (= max_tokens, truncated)
  success  deepseek  in 5,233  out 8000    (= max_tokens, truncated)
  failed   deepseek  empty completion (finish_reason=length, reasoning_chars=34128)
  failed   deepseek  empty completion (finish_reason=length, reasoning_chars=33736)
```

Truncated JSON cannot be parsed, so `stage_draft` returns `failed`, the pipeline
records `draft_failed`, and the article is discarded. Five selected stories, zero
articles.

This began when source coverage improved. Items ingested went 324 → 721 → 810
across 24, 25 and 26 August; articles written went 4 → 1 → 0 across the same three
days. **The source repair is what broke the writing.** Nothing regressed; a fixed
ceiling stopped being large enough.

Two conditions removed every safeguard that should have caught this:

- The OpenAI fallback refuses every request (`429`, 19 times on 26 August, each
  returning in under three seconds on both attempts — an account state, not a
  transient rate limit). There is no second writer.
- The failure is reported as `"5 held by the quality gates"`, because
  `draft_failed` is not the literal string `failed` and falls through to the
  leftover bucket. The outage was legible as editorial strictness for days.

---

## 2. Governing objective

> Return the site to publishing every weekday, at ten stories per sector, without
> a person in the loop — and make any future stoppage impossible to mistake for a
> quiet news day.

Two clauses, ranked. Publishing correctly at low volume beats publishing nothing
at high volume. Do not pursue volume until Work Orders 1–4 hold for two
consecutive live runs.

---

## 3. Standing constraints

These carry forward and are not negotiable.

1. **Never print secrets.** Identify environment variables by name and by where
   they are used. Never emit a value of `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`,
   `NEWSAPI_KEY`, or any token.
2. **No access-control circumvention.** Do not bypass paywalls, bot protection,
   authentication, or `robots.txt`. If a source is blocked, find a lawful
   alternative or drop it.
3. **No new paid service** without first reporting cost, expected coverage, and
   alternatives, and receiving approval.
4. **No destructive git.** No `reset --hard`, no force-push, no discarding
   uncommitted work without first explaining exactly what would be lost.
5. **Report faithfully.** If tests fail, quote the failure. If a step is skipped,
   say so. Never report a fix as verified on the strength of the code reading
   correct — verification means a run.
6. **Full test suite before and after every change.** `python -m unittest
   discover -s tests` plus `python scripts/validate_publication.py`. Read the
   output before committing.

---

## 4. Work orders

### WO-1 — Give the writer room, and stop discarding truncated work

**Severity:** blocks all publishing.
**Files:** `scripts/editorial_pipeline.py`, `scripts/editorial_scoring.py`

**Hypothesis to test first.** DeepSeek's reasoning models are believed to charge
`reasoning_content` against the same `max_tokens` allowance as the visible answer,
so a long reasoning trace starves the article. The evidence is strong — completions
landing on exactly 8,000 tokens, and empty completions carrying 34k characters of
reasoning — but it is inferred, not confirmed.

Before changing anything, confirm it with one cheap probe: issue a single draft-
shaped request at a known `max_tokens`, and record `usage.completion_tokens`,
`usage.completion_tokens_details` if present, `finish_reason`, and
`len(reasoning_content)`. Establish whether reasoning tokens are inside or outside
the cap. **Write the finding down in this file before proceeding.** If the
hypothesis is wrong, the remedy below changes and you must say so rather than
apply it anyway.

**Required changes.**

1. **Detect truncation on success.** `call_deepseek` in `editorial_scoring.py`
   currently raises only when `content` is empty. A response with non-empty but
   truncated content is logged as `outcome: success` and passed upward to fail
   silently at the JSON parser. Treat `finish_reason == "length"` as a failure in
   its own right, with its own log field, whether or not content came back. This
   single change would have made the outage self-evident on day one.

2. **Size the budget to the work.** `editorial_pipeline.py:248` sets a flat
   `"max_tokens": 8000` for every article regardless of depth — the same
   allowance for a `tier_c` brief of 180 words as for a `tier_a` flagship of
   1,400. Derive the allowance from `DEPTH_SPEC` (`scripts/v3_generation.py:48`)
   plus a reasoning headroom term. Headroom must be sized from the measured
   reasoning distribution, not guessed; the observed range is roughly 3,700 to
   36,000 characters.

3. **Make the retry change something.** `_request_json`
   (`editorial_pipeline.py:36`) retries a malformed response by re-sending the
   same prompt at the same `max_tokens`. A truncation failure retried identically
   truncates identically, at full cost and full latency — this is why individual
   drafts took 290 to 630 seconds. On a length failure specifically, the retry
   must raise the ceiling, or reduce the demanded output, or both.

4. **Consider splitting the audit ledgers out of the draft call.** The draft is
   required to return `body_html`, `title`, `excerpt`, `sources`,
   `excellence_ledger` and `claim_evidence` as one JSON object, so truncation
   anywhere destroys a finished article. Emitting the ledgers in a second call
   would make a good article survivable. Evaluate this and either implement it or
   record why not.

**Acceptance criteria.**

- A probe run of at least 10 draft calls across all three depth tiers produces
  zero `finish_reason == "length"` outcomes.
- A deliberately over-long prompt produces a clean, logged, *labelled*
  length-failure rather than a JSON parse error.
- New tests cover: a truncated-but-non-empty completion is rejected; a length
  failure retries with a changed budget; per-depth budgets are derived, not
  hardcoded.

---

### WO-2 — Bound the prompt so richer sources cannot re-break the writer

**Severity:** prevents recurrence.
**Files:** `scripts/research_dossier.py`, `scripts/editorial_pipeline.py`

Source growth is the trigger and it will continue. `dossier_prompt_payload`
(`research_dossier.py:186`) truncates at `max_chars` with a bare slice — it can cut
mid-source, mid-URL, mid-sentence, and the model then reasons over a mangled tail.
The financial-review stage requests 24,000 characters of dossier.

Give the dossier a real budget: rank sources by authority and independence, keep
whole sources rather than truncating one mid-way, and drop the weakest first.
Log how much was dropped so shrinkage is visible instead of silent.

**Acceptance criteria.** A dossier of 40 sources renders under budget with no
partial source block; the number dropped appears in the run summary; a test pins
that no source is ever emitted half-written.

---

### WO-3 — Restore the fallback writer *(requires Ben — cannot proceed without)*

**Severity:** no safety net until resolved.

Every OpenAI call is refused with `429`. Both attempts return in 1.4–2.7 seconds,
which is characteristic of an account-level refusal rather than server pressure.
The likely cause is an exhausted prepaid balance or a reached spend cap on the
account behind `OPENAI_API_KEY`.

**This is the one item the executor cannot do.** Ben must check billing and usage
on that account. Report the finding here.

If OpenAI is not to be restored, say so explicitly and treat single-provider
operation as a deliberate architectural decision — which then makes WO-1 and WO-7
load-bearing rather than merely important, and that should be stated plainly
rather than left implied.

---

### WO-4 — Never let an outage read as an editorial decision

**Severity:** cost several days of diagnosis.
**File:** `scripts/v3_generation.py`

At line 354 the tally reads `elif item.status == "failed"`. The pipeline emits
`draft_failed`, which does not match, so it lands in the `else` bucket printed as
`"N held by the quality gates"`. A total writer outage was reported in the same
words the system uses for stories it deliberately declined.

Fix the classification, and separate the two ideas permanently in the summary
output: *the model failed to produce an article* and *we chose not to publish this*
must never share a line. A story held on editorial grounds and a story lost to a
broken provider are different events and should read differently.

**Acceptance criteria.** A test asserts that a `draft_failed` result increments the
failure count and never the held count, and that the printed summary names the
provider failure explicitly.

---

### WO-5 — Lift the real cap

**Severity:** caps volume at 5 regardless of configuration.
**File:** `scripts/selection.py`

This one is not where it appears to be, and the obvious change does nothing.

```python
# scripts/selection.py:40
MAX_DAILY_ARTICLES = 5

# scripts/selection.py:290-291
publication_target = max(0, min(int(publication_target), MAX_DAILY_ARTICLES))
article_limit     = max(publication_target, min(int(article_limit), MAX_DAILY_ARTICLES))
```

Both knobs are clamped to 5. `--daily-target` is clamped on line 290; `--article-limit`
is clamped on line 291 and then floored by the already-clamped target. **No command
line argument can produce more than five articles.** Raising `--daily-target` and
`--article-limit` in the workflow — the change that looks like the fix — would have
changed nothing at all and would have been reported as a fix that did not work.

The constant is the cap. Raise it, and only then raise the workflow flags in
`.github/workflows/daily-insights-agent.yml:141-146` (`--daily-target`,
`--article-limit`, `--workers`) and the `article_count` dispatch choices, which
currently offer only 1, 3 and 5.

Before raising it, size the consequences honestly and write the numbers here:
generation is parallel, so wall-clock is roughly `ceil(articles / workers) ×
per-article seconds` against the job's `timeout-minutes: 120`. At 26 August's
observed 130–315 seconds per article, thirty articles at six workers is a
plausible 65–105 minutes and uncomfortably close to the ceiling. Cost is not the
constraint — 26 August spent $0.35 against a $25 ceiling — but time is. Either
raise the timeout with justification, raise worker count, or stage the increase.

**Acceptance criteria.** A test pins that a requested target above the old ceiling
actually reaches generation. One live run publishes more than five articles. Wall
clock and spend are recorded here.

---

### WO-6 — Fill the six starving sectors

**Severity:** limits supply beneath the cap.
**Files:** `scripts/eligibility.py`, `scripts/content_typing.py`

Even unclamped, selection found only 17 publishable stories on 26 August, not 70.
One sector of seven filled its slate.

```
26 Aug — slate fill by sector

  commercial_real_estate   10/10    eligible  54 of 382
  data_centers              4/10    eligible   8 of  85
  banking_credit            2/10    eligible   6 of  44
  private_equity            1/10    eligible   4 of  73
  energy                    0/10    eligible   9 of 131
  fed_macro                 0/10    eligible   1 of  27
  local_government          0/10    eligible   4 of   5
```

Energy is the sharpest case: 131 items in, 9 eligible, 0 selected. `local_government`
is a different failure — only 5 items reached eligibility at all, which is a
sourcing gap, not a rules gap. Diagnose each sector before touching any rule, and
say which of the two problems it has.

Sample at least 20 rejected items per starving sector, classify each rejection as
correct or incorrect, and only then change rules. Report the before/after
eligibility rate per sector.

**Constraint.** Do not lower the quality floor to manufacture volume. If a sector
genuinely lacks ten publishable events on a given day, publishing fewer is the
correct outcome and must be reported as such.

---

### WO-7 — Make silence audible

**Severity:** every failure above was invisible.
**Files:** `.github/workflows/daily-insights-agent.yml`, new alerting script

Three distinct silent-failure modes are now confirmed:

- **Zero articles written** while the run reports success (26 August).
- **A scheduled run that never fires.** 27 August produced no run of any workflow
  against an 11:07 UTC cron, checked at 19:08 UTC. The repository is public, so
  Actions minutes are not the cause, and the workflow is enabled. GitHub's
  scheduled triggers are best-effort and are dropped under load. There is no
  catch-up and no alert.
- **A release rolled back after publishing.** From 18 to 23 August the run
  published, waited ten minutes for the change to appear live, decided it had not,
  and reverted itself — which is what erased 23 August:

  ```
  NOT VERIFIED: latest edition edition_date has not reached the live site
  Rolled back failed release with verified revert commit 2a5e13b5...
  ```

  This has not recurred since 24 August and live currently matches the repository
  exactly, so treat it as watch-and-instrument rather than fix-blind. Note that
  `verify_deployment.py`'s 600-second window has no tolerance for a slow Netlify
  build; record actual observed deploy latency before deciding whether to widen it.

Build alerting that reaches Ben the same day for: zero articles published, a
missed scheduled run, a rollback, and a provider whose failure rate exceeds a
threshold. The existing `weekly-health-check.yml` commits a report and notifies
nobody; weekly is too slow for a daily publication regardless.

Choose a delivery channel and **report the cost before building it** if it is not
free.

---

### WO-8 — Repair or retire the three dead ranking measures

**Severity:** degrades ordering, blocks nothing.
**File:** `scripts/importance.py`

Every run prints its own diagnosis:

```
WARNING: dead measures ['precedent', 'novelty', 'evidence']
```

Three of eight measures return the same value for every story and cannot separate
anything. Scores span 0 to 66 with a mean of 21 — the top of the 0–100 scale is
unreachable, which makes the quality floor of 40 mean something other than what it
appears to mean.

For each measure: determine whether it is mis-computed or genuinely
non-discriminating on this corpus. Repair it, or remove it and re-normalise the
remaining weights. A measure that cannot discriminate must not silently contribute
a constant. Note that `_surprise` is already deliberately excluded with a
documented rationale — follow that precedent and document whatever you decide.

---

## 5. Out of scope

Do not undertake these under this mandate:

- Redesigning the ranker beyond WO-8.
- Adding data providers or paid subscriptions.
- Reworking the public site, templates, or `insights.json` client-side loading
  (a known issue at ~560KB, tracked separately).
- Resolving `stash@{0}` (local v3 publish wiring, likely superseded).
- Changing editorial voice, format specifications, or article length targets.

---

## 6. Definition of done

The mandate closes when all of the following hold:

1. Three consecutive scheduled runs publish articles, none reporting a
   length-truncation failure.
2. A day with zero published articles produces an alert that reaches Ben.
3. At least one run publishes more than five articles.
4. No sector reports `0/10` for reasons of rules rather than genuine absence of news.
5. The daily summary distinguishes provider failure from editorial hold.
6. The full test suite passes, and the run output proving it is quoted in the
   closing report.

Report progress against these six by number. State plainly what is done, what is
partial, and what is untouched.

---

## 7. First action

Do not start with the code. Start with the probe in WO-1: establish empirically
whether reasoning tokens are charged against `max_tokens` on `deepseek-v4-pro`.
Every remedy in this document assumes an answer to that question, and the answer
has not been measured.
