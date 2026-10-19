# Implementation Prompt: Fix Root Cause #3 — Repair the Ranking Measures

## Mission

Repair the insights generator's ranking layer so scores are truthful,
discriminating, and useful for selection. The current system reports that
three ranking measures are dead:

```text
WARNING: dead measures ['precedent', 'novelty', 'evidence']
```

A dead measure is one that returns the same value, nearly the same value, or a
value that is not connected to the actual story data for the current corpus.
Such a measure cannot help rank stories. If it remains in the weighted score,
it gives a false impression of precision and distorts the meaning of the
quality floor.

Do not solve this by lowering the quality floor, adding arbitrary noise, or
promoting weak stories to fill sectors. Determine whether each measure is
broken, genuinely unavailable, or conceptually unsuitable. Repair it when the
underlying data supports a defensible calculation; otherwise retire it and
renormalize the remaining weights.

## Current evidence

The current-state audit observed:

- `precedent`, `novelty`, and `evidence` are reported as dead;
- final scores span only roughly 0–66 rather than using the advertised 0–100
  range;
- the mean score is low and the upper scale is unreachable;
- a quality floor such as 40 therefore does not have an obvious, stable
  interpretation;
- novelty and evidence information exists elsewhere in the pipeline, but the
  ranker may not be consuming it in the correct shape or at the correct stage;
- `_surprise` is already excluded with a documented rationale and should be
  treated as the precedent for an intentional retirement.

The ranking code is not the article-writer runtime problem. Keep this change
focused on scoring, score interpretation, selection diagnostics, and tests.
Do not redesign generation, feeds, publication, or editorial voice here.

## Files to inspect first

Read the current implementations and tests before editing:

- `scripts/importance.py`;
- `scripts/selection.py`;
- `scripts/intelligence_object.py`;
- `scripts/editorial_memory.py`;
- `scripts/insights_v3.py`;
- `tests/test_selection.py`;
- `tests/test_intelligence_object.py`;
- `tests/test_ranker_regression.py`;
- the candidate and score artifacts under `.editorial-state/` when available;
- the current ranking documentation and mandate files.

Trace each measure from its source fields to its final weighted contribution.
Record whether the issue is:

1. a missing input;
2. an incorrect field name or type;
3. a stage-ordering problem;
4. a calculation that collapses all values to a constant;
5. a data distribution that is genuinely uniform;
6. a measure whose concept is not defensible for this product.

Do not infer the cause from the warning alone. Produce a small diagnostic
table for every measure showing sample inputs, raw values, normalized values,
weighted contribution, and the number of distinct values across the current
fixture/corpus.

## Required design principles

### 1. Define the score contract explicitly

Document:

- the measures used;
- each measure's input fields;
- each measure's raw range;
- its normalization method;
- its weight;
- what a high value means;
- what happens when its input is missing;
- whether it is allowed to affect publication selection;
- how the final score is mapped to 0–100.

The final score must have a mathematically clear meaning. If the implementation
does not guarantee a full 0–100 range, do not imply that it does. Either:

- renormalize the active measures so their maximum possible weighted score is
  100; or
- change the documented scale to the actual bounded range and update all
  thresholds and summaries deliberately.

Prefer a 0–100 scale with active weights summing to 1.0, because the selection
floor and reports already speak in that language.

### 2. Diagnose `precedent`

Determine what precedent is intended to measure. It could mean historical
importance of a source/entity/event type, repeat relevance, or prior coverage.
Do not guess.

If it is intended to use editorial memory, ensure the measure receives the
memory state after memory is loaded and before scoring. A story already covered
should not automatically receive a positive importance score; the product may
want a follow-up signal, a novelty penalty, or a material-change adjustment.

Choose and document one defensible policy, for example:

- positive score for a material follow-up to a known event;
- neutral score when there is no reliable precedent data;
- penalty for a duplicate with no material change;
- no invented historical importance when memory is empty.

Write tests for new event, follow-up with material change, duplicate without
change, and empty memory. If the available data cannot support this measure,
retire it rather than manufacturing a score.

### 3. Diagnose `novelty`

Trace the existing `novelty_state`, prior published slugs, material changes,
and memory records. Confirm whether novelty is being computed but discarded,
overwritten, or converted to one constant before importance scoring.

The measure must distinguish at least the meaningful states the product already
recognizes, such as:

- new event;
- new development on a known event;
- previously covered/duplicate;
- unknown because memory is unavailable.

Do not call a story novel merely because its headline differs. Use the existing
event/object identity and material-change evidence. Preserve the existing hard
exclusions for duplicates where applicable; a ranking bonus must never promote
an ineligible or duplicate story into publication.

If novelty is already a gate rather than an importance dimension, make that
boundary explicit and retire it from the weighted score. One fact must not be
counted twice under both a gate and a score without a documented reason.

### 4. Diagnose `evidence`

Use the evidence state already computed by retrieval and the intelligence
object. Inspect at minimum:

- evidence level;
- independent source count;
- primary source count;
- usable full-text count;
- retrieval status;
- corroboration state;
- material fact/source relationships.

Evidence should not reward a story merely because it has many syndicated copies.
Use independent sources as the relevant unit, preserve primary-authority
distinctions, and do not let blocked or summary-only sources inflate evidence.

The evidence score must align with the depth cap used by selection and writing.
It may distinguish support strength, but it must not override eligibility or
allow unsupported content to qualify for a deeper article format.

Add tests for:

- one summary-only source;
- one full-text source;
- two independent corroborating sources;
- multiple syndicated copies;
- blocked retrieval;
- missing sources;
- primary plus secondary evidence.

### 5. Repair or retire each measure deliberately

For each of the three measures, make exactly one documented decision:

- `repaired`: the calculation now consumes valid data and distinguishes real
  cases; or
- `retired`: the measure is removed from the weighted score because its data or
  concept cannot support a reliable contribution.

Do not leave a dead measure in the score with a constant value. Do not silently
replace it with a different concept under the same name.

If a measure is retired:

- remove its weight from the active score;
- renormalize remaining active weights;
- update the dead-measure report so intentional retirements are not emitted as
  unexplained warnings;
- document why it is retired and what data would be required to restore it;
- add a regression test that prevents accidental reintroduction.

If a measure is repaired:

- give it a stable documented range;
- test its minimum, middle, and maximum cases;
- verify it has at least two distinct values on realistic fixtures;
- ensure missing data produces a neutral/explicit result, not an accidental
  maximum or minimum;
- include its contribution in the candidate audit.

## Score normalization and selection behavior

After the measure decisions:

1. Make active weights explicit and verify they sum to 1.0.
2. Ensure the final score is bounded and interpretable.
3. Report minimum, maximum, mean, median, and distinct-score count.
4. Report each active measure's distinct-value count and contribution range.
5. Keep the quality floor unchanged until the score behavior is measured.
6. Re-evaluate whether the existing floor of 40 represents the intended
   publishable band only after comparing before/after fixtures.
7. Do not force selection merely because the new scale makes a sector look
   sparse.

The selection layer must continue to distinguish:

- no discovered stories;
- discovered but ineligible stories;
- eligible but below-floor stories;
- selected stories removed by diversity or global slate limits.

Ranking changes must not erase those explanations.

## Required diagnostics

Extend the score report or candidate audit with safe, reproducible fields:

- score version;
- active measures;
- retired measures and reasons;
- configured weights;
- weight sum;
- raw and normalized value per measure;
- final score;
- missing-input flags;
- distinct-value counts;
- min/max/mean/median;
- whether a score was neutral because data was unavailable.

Do not persist prompts, API keys, or private provider data. Candidate titles,
IDs, statuses, and numeric score diagnostics are acceptable.

The report must not call a measure “dead” when it is intentionally retired. Use
separate statuses such as `active`, `repaired`, `retired`, and `data_missing`.

## Required tests

Add deterministic tests proving:

1. Every active measure has a documented weight and input contract.
2. Active weights sum to exactly 1.0 within a defined tolerance.
3. Each repaired measure produces distinct values for meaningful fixture cases.
4. Retired measures cannot silently contribute to the final score.
5. Missing precedent data is neutral or explicitly flagged.
6. New, follow-up, material-change, and duplicate novelty states differ as
   documented.
7. Summary-only evidence does not score like corroborated full text.
8. Syndicated copies do not count as independent corroboration.
9. Blocked retrieval does not inflate evidence.
10. Evidence scoring cannot override eligibility or depth caps.
11. Final scores remain within the documented range.
12. Score reports include active/retired status and weight diagnostics.
13. The dead-measure warning is emitted only for active measures with no
   variation, not intentional retirements.
14. Candidate audits include the score version and per-measure contributions.
15. Selection still reports below-floor and ineligible reasons accurately.
16. Existing false-positive and genuine-story regression fixtures preserve their
   expected eligibility behavior.
17. Existing generation, publication, and workflow tests remain green.

Add a corpus-level fixture test with at least ten varied stories. Assert that
the active measures are not all constant, the final scores have a meaningful
range, and ordering changes only when the underlying facts justify it.

## Safe rollout sequence

1. Capture the current score distribution and top/bottom candidate ordering.
2. Add the diagnostic table before changing formulas if necessary.
3. Repair or retire the three measures one at a time.
4. Run focused ranking, intelligence-object, and regression tests.
5. Run the full Python suite and publication validation.
6. Run a GitHub Actions shadow pass with the new score version.
7. Compare candidate ordering, score distribution, sector shortfalls, and
   rejection reasons against the baseline.
8. Run a preview without publication and inspect the candidate audit.
9. Do not change the quality floor or scheduled pipeline until the comparison
   is reviewed and documented.

## Non-goals

Do not:

- lower the quality floor to hide a score-scale problem;
- add random jitter to create artificial variation;
- count syndicated copies as independent sources;
- promote ineligible stories because a score is high;
- make provider calls to calculate deterministic ranking measures;
- redesign article generation or provider runtime;
- rewrite feed ingestion;
- change public article formats or editorial voice;
- delete historical score artifacts needed for comparison.

## Completion standard

This work is complete only when:

- every former dead measure is repaired or intentionally retired;
- the decision for each measure is documented in code and the mandate;
- active weights and score normalization are mathematically explicit;
- the final score range and quality floor are honestly described;
- the candidate audit shows per-measure values and contributions;
- ranking tests demonstrate meaningful variation on realistic fixtures;
- evidence and novelty remain aligned with eligibility and depth rules;
- the full test suite passes;
- a shadow run comparison confirms that selection changes are explainable;
- no article is promoted solely to fill a sector quota.

## Final report

Report in plain English:

- what was wrong with `precedent`, `novelty`, and `evidence`;
- whether each was repaired or retired and why;
- the old and new weights;
- the old and new score distributions;
- how the quality floor should be interpreted now;
- examples of stories whose rank changed and the factual reason;
- tests and shadow-run results;
- any remaining data limitation.
