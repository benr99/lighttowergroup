# Intelligence readability audit: report and rollout

Run 2026-10-08. Prompt: `docs/audits/INSIGHTS_LINKEDIN_READABILITY_AUDIT_PROMPT.md`.

## Verdict

Ben is right. The published pages read at a college-graduate level because of **density, not vocabulary**:
about 100 words per paragraph and 26 per sentence. The same facts, written for LinkedIn by this repo's own
essay agent, come out at grade 8. The cause is the production writer prompt, not the model. A new writer prompt
and a set of readability checks, now in the working tree, take the same stories from grade 15.5 to grade 9 in a
10-story A/B test. The main new risk is that the punchier voice invents figures, and the checks below target that.

## Evidence (Workstream B)

198 published articles from Sep 1 to Oct 6, plus the pre-April archive and 60 of Light Tower's own LinkedIn essays.
Re-run with `python outputs/readability/measure.py <insights.json> <insights_dir>`.

| Measure | Published pages | Own LinkedIn essays | Target now enforced |
|---|---|---|---|
| Words per paragraph | 100 | 38 | at most 60 |
| Words per sentence | 26 (27% over 30) | 13 (2% over 30) | mean at most 22, none over 35 |
| Flesch reading ease / grade | 29 / 15.4 | 58.5 / 8.2 | about 60 / 9 (A/B result) |
| Sentences starting "The" | 43% | n/a | at most 35% |
| Closing on "what remains unknown" | 46% (86% of briefs) | 2% | none |
| Excerpt cut mid-sentence | 39% | 0% | none |
| Insider jargon per 100 words | 0.1 | 0.1 | n/a |

Jargon is rare. The problem is long sentences and walls of text. The Chase RMBS article was an outlier, not the norm.
Briefs are worst on the template closer (86%); the "fed_rates" and "policy" sectors open most often with "The".

## Root causes (Workstream D)

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | v4 writes with only "precise financial journalist" | **Confirmed** | `v4_generation.py` at HEAD |
| H2 | The voice stack is unused by v4 | **Confirmed** | only legacy, LinkedIn, carousel and ideas code imports `VOICE_SYSTEM_ADDENDUM` |
| H3 | Word floors force padding | **Confirmed** | old prompt: "Do not stop early… reach the minimum"; old briefs ran 180-380 words, analyses 400-800 |
| H4 | Wire-copy structure, no hook | **Confirmed** | old structure was event, mechanics, evidence, implications, limitations; hooks rarely carried a number or tension |
| H5 | Template closer | **Confirmed** | 46% overall, 86% of briefs |
| H6 | Source jargon pasted through | **Partly refuted** | jargon density is low; density of prose is the issue |
| H7 | Validation ignores readability | **Confirmed** | only word, paragraph, HTML and URL checks existed |
| H8 | Excerpts truncated | **Confirmed**, root cause found | `v3_publish._article_payload` did `excerpt[:160]` and `[:200]` |
| H9 | Off-topic stories | **Confirmed, not fixed here** | e.g. ship-fuel startup, Fifth Wall profile; a selection issue, so prose cannot rescue it |
| H10 | Low temperature flattens voice | **Unproven** | not isolated; raised 0.2 to 0.35 together with the prompt |
| H11 | Filter buckets inconsistent | **Confirmed, minor** | `insights.html` FILTERS; left alone |

## What changed

- `scripts/v4_generation.py`: new system prompt and writer prompt (hook, what happened, the number that matters,
  why it matters, "My read", one thing to check; short sentences and paragraphs; no padding).
  New length ranges: brief 110-300, analysis 200-520, flagship 380-850 words (were 180-380, 400-800, 750-1400).
  After a valid draft, readability and fact checks run. If any trip, **one corrective rewrite** is requested,
  with the specific problems quoted back. If the rewrite fails or never arrives, the earlier valid draft ships.
  As a last resort, sentences carrying numbers no source gave are cut.
  Drafts cached under the old prompt are no longer reused (`WRITER_PROMPT_VERSION`).
- `scripts/readability.py` (new): the shared checks (sentence and paragraph length, "The" openings, banned
  phrases, template closers, excerpt completeness) and the fact tripwires (numbers allowing rescale and rounding,
  and capitalised names the source never gave).
- `scripts/v3_publish.py`: subtitle and meta description now trim at a sentence or word boundary.
- `scripts/weekly_wrap.py` shares the banned-phrase and number checks, so the daily pieces and the Friday wrap
  use one voice and one guard.
- Tests: `tests/test_readability.py` (new), `tests/test_v4_generation.py` (fixture made readable, 5 new cases),
  `tests/test_weekly_wrap.py`. Full suite on a clean `origin/main` plus these changes: **459 tests pass.**

## A/B result (Workstream F)

10 stories from cached source text (2 of 12 planned were not in the cache), same dossier, same provider
(DeepSeek v4 pro). Arm A is the prompt at HEAD; arm B is the new writer, one request, no retry.
Re-run with `python outputs/readability/ab_harness.py`. Side by side text is in `ab_samples.md`.

| Measure | A (current) | B (new) |
|---|---|---|
| Words per article | 547 | 245 |
| Words per paragraph | 106 | 41 |
| Words per sentence | 27.8 | 16.8 |
| Sentences over 30 words | 36% | 6% |
| Flesch reading ease / grade | 31.8 / 15.5 | 59.2 / 9.0 |
| Sentences starting "The" | 39% | 18% |
| Template closer | 2 of 10 | 0 of 10 |
| Articles with a figure not in the sources | 0 | 2 |
| Blind judge prefers | 0 | 10 of 10 |
| Judge scores (1-5): hook / plain / skim / useful / trust | 2.6 / 3.2 / 2.8 / 3.4 / 4.2 | 4.5 / 4.4 / 4.6 / 4.3 / 3.7 |

Reading the table honestly:

- **The readability win is large and consistent across all 10 stories.**
- **Trust went down.** B's voice offers a view and sometimes reaches for a derived figure (e.g. "$149 million
  of equity" computed from a purchase price and a loan; "76 percent of the purchase price"; hypothetical
  "25-basis-point hike" scenarios). The guard caught all of these. In run 1 of three, five of ten first drafts
  carried such a figure; after the guard and prompt tweaks it was two of ten. One corrective rewrite cleaned
  one of four flagged drafts fully, so the last-resort sentence cut matters.
- **Limits of this test:** 10 stories, one run per arm, a single judge that is the same model family as the
  writer, and run-to-run variance (warnings ranged 4 to 8 of 10 across runs). Treat the direction as solid and
  the exact percentages as approximate. The judge is no substitute for Ben reading ten pieces.
- The judge also rewarded B's opinionated "My read" paragraphs. For a publication that must stay inside its
  sources, that paragraph is the one to watch in review.

## Benchmark notes (Workstream C)

Internal evidence is the strongest: the essay agent's output on the same facts is the bar (grade 8, 13-word
sentences). No engagement data exists in the repo for pages or posts. External evidence is thin and mostly from vendors;
treat it as directional. Two findings carried weight: the hook should land in roughly the first 140-210
characters (mobile vs desktop "see more" cutoffs, sources disagree), and Edelman/LinkedIn's survey of
3,484 executives rates strong data, help with the reader's own challenges and concrete guidance as the traits
of valued B2B content. Claims that one length or paragraph style wins did not hold up across sources.
Out of bounds by design: engagement bait, emoji, manufactured first-hand access, one-line-per-paragraph overuse.

Sources:
- https://www.edelman.com/news-awards/new-research-edelman-linkedin-thought-leadership-influences-b2b-sales
- https://ligosocial.com/research/linkedin-post-length (same-author comparison; vendor)
- https://www.tryordinal.com/blog/linkedin-post-size (248k posts; vendor; conflicts with the above on length)
- https://www.agorapulse.com/social-media-lab/post-length-linkedin (vendor)

## Rollout and what to watch

Nothing is committed or pushed. Suggested path:

1. **Read ten before anything ships.** Run the daily workflow with `pipeline=v4`, `mode=preview`,
   `article_count=10`. Read the artifact, focusing on "My read" and the closing line. Look for any figure or
   name you cannot find in the linked source.
2. Commit, fix or revert the broken `update_manifest` edit in your local `daily_news_agent.py`, rebase onto
   `origin/main`, and publish a normal day.
3. After two weeks compare, using the existing `/api/track-read` events: share of readers reaching
   `scroll_50` and `scroll_100`, click-through from Intelligence cards, LinkedIn impressions and saves for posts
   built from these pieces, and unsubscribes. Also track the share of articles that needed a retry or a sentence
   cut (in each article's diagnostics: `readability_warnings`, `sentences_removed_for_unsupported_numbers`).
4. **Kill switch:** revert `scripts/v4_generation.py` to HEAD. The v3 and v2 pipelines are untouched.

Expected cost: articles are about 55% shorter, so output tokens fall sharply; the corrective retry is the offset
(roughly 40% of articles in this sample would trigger one).

## Not done

- The 12-story A/B ran on 10; two stories were not in the cache.
- Story selection (H9) and the Intelligence page's category filters (H11) are untouched.
- `INSIGHTS_GENERATOR` mandate docs and `editorial_voice.py` were not changed. The persona there is still used
  only by the LinkedIn, carousel and ideas agents.
