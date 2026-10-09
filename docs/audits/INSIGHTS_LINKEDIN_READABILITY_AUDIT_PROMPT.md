# Insights Readability Audit: Light Tower Intelligence vs. LinkedIn-Native Writing

> Paste this whole file into a fresh Claude Code session opened in this repository.
> It is written to be run end to end by one agent with read access to the repo and web search.
> It is an **audit and proposal** task. Do not change production prompts, push, or publish.

---

## 0. Your role

You are a senior editorial-systems auditor with two skills most auditors lack:
you can read a Python content pipeline down to the prompt string, **and** you can
judge prose the way a busy CRE sponsor, lender, or LP scrolling LinkedIn at 7:40 a.m. would.

Ben Rohr (Light Tower Group, Brooklyn CRE capital advisory) reports the Intelligence
page (`insights.html`, fed by `insights.json`) "works" but the stories read as
**"almost too sophisticated and unreadable."** He wants to know whether adopting the
writing style that is familiar and well-liked on LinkedIn would make the stories
better received, and exactly what to change in the process to get there.

Your job: **find out whether he is right, prove it with measurements, and design the fix.**

## 1. Hard constraints (do not violate)

1. **Read-only on production behavior.** Work on a new branch. Never push to `main`, never
   trigger the GitHub workflow, never run a command that publishes, posts to LinkedIn, or sends email.
2. **Do not weaken the factual boundary.** Every proposal must keep the rule that an article
   may use only facts, numbers, quotes, and entities supported by its dossier, and that source
   URLs come from the dossier. Readability is achieved by *better translation and structure*,
   never by invention, false first-hand access ("I toured the building"), or manufactured drama.
3. **No secrets in output.** `scripts/.env` and any memory file may contain live keys. Never print,
   copy, or commit them. Use env vars if you need a provider; if none is available, say so and
   use the stored drafts/dossiers only.
4. **Known working-tree hazard.** `scripts/daily_news_agent.py` currently has an *uncommitted,
   half-applied edit* in `update_manifest()` (a `try:` whose body is not indented, followed by
   `finally:`), so `python -m py_compile scripts/daily_news_agent.py` fails locally. Production runs
   the committed version and is unaffected. Do not "fix" it as part of this audit. Report it, and
   when you need the renderer, test against `git show HEAD:scripts/daily_news_agent.py` or a clean
   `git worktree`.
5. Everything you claim must cite `path:line` or a stored artifact. Mark each claim
   **Confirmed / Refuted / Unproven**. No vibes.

## 2. What I already know (verify each; these are hypotheses, not facts)

Recon done before you started. Treat as leads and try to **refute** them.

| # | Hypothesis | Where to look |
|---|-----------|---------------|
| H1 | The live production writer is `v4_generation.py` (workflow `daily-insights-agent.yml` → `insights_v3.py --pipeline v4`). Its only voice instruction is the system prompt `"You are a precise financial journalist."` plus a user prompt of rules and a generic paragraph structure. | `scripts/v4_generation.py` `_writer_prompt`, `_request_once` |
| H2 | The carefully built voice stack, `VOICE_SYSTEM_ADDENDUM`, `NARRATIVE_FINANCE_ADDENDUM`, `VOICE_MODES`, `HEADLINE_SHAPES`, `editorial_quality_issues` (AI-tell blocklist), is **not used by v4 at all.** It only reaches the legacy v2 path, carousels, LinkedIn essay/thread agents, and ideas. The latest rewrite of the voice file (uncommitted) is therefore aimed at paths that do not produce the Intelligence page. | `grep -rn VOICE_SYSTEM_ADDENDUM scripts/`; `git diff scripts/editorial_voice.py` |
| H3 | v4 imposes hard word floors per tier (`DEPTH_SPEC`: brief 180-380, analysis 400-800, flagship 750-1400) and tells the model "Do not stop early because the dossier is short. Reach the minimum using supported context, mechanics, implications, source comparison, limitations, and explicit unknowns." That instruction **manufactures padding and abstraction**, which reads as "sophisticated and unreadable." | `v4_generation.py:149-176`, `v3_generation.py:48-52` |
| H4 | The structure instruction is wire-copy, not LinkedIn: (1) what happened, (2) facts and mechanics, (3) evidence and source context, (4) implications, (5) limitations. Result: no hook, no stance, no "so what" in the first screen. | `v4_generation.py:133-148` |
| H5 | Output has a near-template closer: a paragraph beginning "What remains unknown…" / "Whether … remains to be seen." One of the AI-tell patterns that `editorial_voice.py` itself bans ("remains to be seen"). | sample 30+ stored articles |
| H6 | The dossier is a "complete factual boundary" with up to 5,000 chars per source and `material_claims`/`facts`. The model paraphrases source jargon verbatim (e.g. Chase RMBS piece: "QM safe harbor", "Pentalpha Surveillance", tranche-by-tranche enhancement percentages) instead of translating it. | `_safe_dossier`; article `chase-rmbs-deal-pairs-prime-collateral-with-a-two-year-r-w-sunset.html` |
| H7 | Validation checks structure only (word/paragraph count, HTML tags, source URLs, repeated paragraphs). **Nothing measures readability** (sentence length, jargon density, hook, headline quality). | `v4_generation.py:189-267` |
| H8 | Excerpts/meta descriptions are mechanically truncated: in the 127 items published 2026-09-28 → 2026-10-06 (from `origin/main:insights.json`), ~57 (45%) of excerpts end mid-sentence. These are the exact text shown on the Intelligence cards and in LinkedIn link previews. | `insights.json`, `render_html`, `update_manifest` |
| H9 | Low reader-value inputs reach the page: e.g. a ship-fuel-reformer seed round filed under "Market Commentary", a Fifth Wall founder profile filed under "Policy & Regulation". Readability fixes cannot rescue irrelevance. Quantify how common this is. | `config/sectors.json`, `v3_publish._CATEGORY`, selection gates |
| H10 | `temperature: 0.2` and DeepSeek `thinking: disabled` bias toward flat, conservative paraphrase. Test whether a higher temperature or a short planning step improves voice without hurting accuracy. | `_request_once` |
| H11 | `insights.html` category filters are inconsistent with what v3/v4 publish (e.g. everything not named maps into the "CRE" bucket). Note only if it affects readability/discoverability. | `insights.html` `FILTERS` |

## 3. Workstreams

### A. Map the writing path end to end
Produce a one-page diagram + table of **every place text is authored or rewritten** between a raw
feed item and the pixels on `insights.html` and the article page: ingestion summaries, dossier
construction (`object_to_dossier`), writer prompt, retry prompt, validators, `article_adapter.py`,
excerpt / `meta_description` / subtitle creation, headline selection, `render_html`, the CTA blocks,
and downstream LinkedIn derivatives (`linkedin_essay_agent.py`, `linkedin_thread_agent.py`,
`carousel_*`). For each: file:line, model/temperature, who owns the instruction, and whether it
carries voice guidance. Explicitly answer: **which production code path wrote each of the last 20
published pages?** (use `pipelineVersion` in `insights.json`, `.editorial-state/v3-run.json`,
`.editorial-state/runs/`).

### B. Measure the corpus (replace opinion with numbers)
Write a small read-only script (save to `outputs/readability/measure.py`) and run it on a stratified
sample of **at least 40 published articles**: both eras (`v2/v3/v4` where available), all three depth
tiers, and every sector bucket (multifamily, industrial, office, retail, hospitality, CMBS/lending,
Fed/macro, PE, data centers, energy, policy).
Extract paragraphs from the body `<p>` elements only (exclude CTA/footer). Report per-article and
aggregate:

- words, paragraphs, words/paragraph (mean, p90), sentences, **words/sentence (mean, p90, % over 30)**
- Flesch Reading Ease and Flesch-Kincaid grade (state the formula you used)
- acronym/jargon density per 100 words (build and publish your jargon list; separate *ordinary CRE
  vocabulary the audience knows* (cap rate, NOI, DSCR, SOFR) from *insider-of-insider jargon* that
  needs a gloss (R&W sunset, QM safe harbor, Pentalpha, tranche letters))
- numbers per 100 words, and **numbers with no plain-English translation** next to them
- passive-voice rate; "the" sentence-starter rate; hedge-word rate
- **first 210 characters**: does it contain a person/company, a number, and a tension? (LinkedIn
  truncates around there behind "see more", and so do the Intelligence cards.)
- headline: length, shape, numeric content, verb strength; repeated-pattern count across the sample
- closer type: is the last paragraph a "what remains unknown" template? count repeats
- excerpt: truncated mid-sentence? duplicates the first sentence of the body?
- compare against the **LinkedIn benchmark in section C** and against 6-8 of Light Tower's *own*
  LinkedIn-format outputs (`linkedin_essay_queue.json`, `scripts/linkedin_essay_agent.py` outputs, any
  stored thread/carousel text) so the comparison is apples to apples.

Output a table and 3-5 charts or ASCII distributions. State the sample and how it was drawn.

### C. Define the LinkedIn benchmark, with evidence
"Well-liked on LinkedIn" is folklore until sourced. Build the benchmark from two evidence streams and
label which is which:

1. **Internal evidence.** Mine whatever Light Tower already knows about its audience:
   `scripts/linkedin_engagement_scraper.py` and any stored engagement data,
   `.editorial-state/audience-signals.json`, `linkedin_essay_queue.json`, `data/`, `reports/`,
   analytics (`analytics-dashboard.*`, `visitor-analytics.js`, the `/api/track-read` scroll-depth
   events: what share of readers reach `scroll_50` / `scroll_100` on long vs short pieces if data
   exists). If real engagement data exists, it outranks everything below. Say plainly if none does.
2. **External evidence.** Use WebSearch/WebFetch to research what demonstrably performs for
   professional/finance/CRE audiences on LinkedIn: hook length and "see more" cutoff, paragraph
   length, reading level, use of first person, contrarian-but-supported takes, numbers in line one,
   list/scan structure, question or checkable takeaway at the end, and optimal length by format (post vs
   newsletter/essay). Prefer primary sources (LinkedIn's own creator/Marketing Solutions guidance,
   published large-scale analyses) over listicles; **cite each URL; do not reproduce their text.**
   Separate *what is measured* from *what is folk wisdom*.

Then write the benchmark as a **testable rubric** (each criterion measurable or checkable), e.g.:
hook in first ~200 chars; one idea per paragraph; paragraphs ≤ 3 sentences; mean sentence length target
and ceiling; jargon is glossed on first use; every number is translated into a consequence; a stated
view the reader can disagree with; a checkable close; scannable skeleton for pieces > 250 words.
Include the **counter-risk**: this audience is professional. Identify where "LinkedIn style" would
*hurt* (over-simplification, engagement bait, fake vulnerability, emoji, one-line-per-paragraph
overuse, "Agree?" closers) and mark those as **out of bounds**. The target is *plain words, expert
content*: a smart analyst explaining the deal to a colleague, not an influencer.

### D. Gap analysis
Score the current Intelligence output 1-5 against each rubric criterion, with the measured evidence
from B beside each score. Then trace **each gap to a root cause** in the code or prompt (file:line)
and classify it:

- *Instruction gap*: the prompt never asks for it
- *Instruction conflict*: the prompt asks for it and then demands something that defeats it (e.g. padding to a word floor)
- *Input gap*: the dossier does not contain what is needed
- *Validation gap*: nothing would catch the failure
- *Selection gap*: wrong story, so no prose could save it
- *Presentation gap*: headline/excerpt/card/rendering

Give a clear verdict on Ben's claim: **Is the writing too sophisticated for its audience? For which
tiers/sectors is it worst? What fraction of the problem is prose vs. story selection vs. presentation?**

### E. Design the improvement
Deliver concrete, drop-in proposals, not advice.

1. **Replacement writer prompt(s)** for tiers A, B, C (full text), including: a *plain-English
   translation layer* (jargon glossed in the same sentence; every number given a consequence), a
   *first-screen contract* (hook that carries the who, the number, and the tension), a
   *structure per tier* (e.g. Hook → What happened in two sentences → Why it matters → The number that
   matters → My read → What to check this week), *headline rules and 3 candidate headlines* with the
   selection logic, a *real excerpt* (a complete sentence, ≤ 160 chars, not a truncation), and a
   *closing that is checkable* but not a template.
2. **Remove or retarget the word-floor padding pressure.** Propose new `DEPTH_SPEC` ranges (shorter, with
   a *ceiling that matters more than the floor*), and the exact edits to the "do not stop early" rules.
   Show what happens to read time, token cost, and the tests that assert the current ranges.
3. **New validators** (deterministic, cheap): sentence-length cap, paragraph cap, jargon-gloss check,
   blocked-crutch list (reuse `_AI_TELLS`, extend deliberately), hook check, closer-diversity check
   across the last N published articles, excerpt completeness. Specify thresholds from your B data.
   Decide for each whether failure → retry-with-feedback, soft flag, or hard block.
4. **Decide the fate of the existing voice stack.** Either wire the *useful* parts into v4 (which
   parts, in what size: the full 5-conviction persona is probably too heavy for a 180-word brief) or
   retire them. Reconcile with the uncommitted rewrite of `editorial_voice.py` so the work is not lost.
5. **Selection and presentation fixes** that readability depends on (relevance gate for off-topic
   stories; excerpt generation; card layout; category mapping).
6. **Sequencing**: which change delivers most per hour of effort, and what to measure after rollout.

### F. Prove it with a bounded A/B
Using stored dossiers (check `.editorial-state/v4-drafts/`, `.editorial-state/retrieval-cache/`,
`v3-candidates.json`; if none, rebuild a dossier from a published article's sources), run **current prompt
vs. your proposed prompt on 12 stories** (at least 2 per depth tier, at least 6 different sectors).
- Use the production provider settings (DeepSeek via `model_router.provider_config`) if a key is in the
  environment; otherwise do not fake results. Report that the A/B could not be run and why, and supply the
  harness (`outputs/readability/ab_harness.py`) ready to run.
- Score blind: run the section-B metrics on both arms, add an LLM-judge pass using the section-C rubric
  (hide which arm is which), and include **3 side-by-side excerpts** in the report.
- **Fact-preservation check is mandatory:** every number, name, and quote in the new output must appear in
  the dossier. Report any violation; a readability gain that adds one invented fact is a failure.
- Report latency and token cost per article and the projected daily cost at 70 articles/day.

### G. Cross-check the new Friday weekly wrap
A weekly wrap feature (`scripts/weekly_wrap.py`) is being built in parallel. Read it. Verify its prompt follows your
benchmark, and note any place the daily-article fixes should be shared with it (one voice across both).

## 4. Deliverables (write to `outputs/readability/`)

1. `REPORT.md`: executive verdict first (5 sentences max), then A-G. Use the Confirmed/Refuted/Unproven tags.
2. `scorecard.md`: rubric × current × proposed table with evidence.
3. `measure.py`, `ab_harness.py`, raw metrics JSON/CSV: re-runnable by me.
4. `PROPOSED_PROMPTS.md`: the exact replacement prompt text, plus a unified diff against
   `scripts/v4_generation.py` (and any other file) on the branch `audit/readability-proposal`. **Do not merge.**
5. `ROLLOUT.md`: staged plan (shadow run → 10-article preview → full), kill-switch, and the 5 metrics that
   will tell us in two weeks whether readers prefer it (e.g. scroll_50 rate, click-through from
   Intelligence cards, LinkedIn impressions per post, saves/forwards, unsubscribe rate).
6. A final chat message: the verdict, the top 5 changes in priority order with effort (S/M/L) and risk,
   and the single decision you need from Ben.

## 5. Quality bar

- A claim without a path, number, or URL is a failure.
- If the data say the writing is **fine** and the real problem is story selection or presentation, say so, even if
  it deflates the premise.
- If a proposal increases hallucination risk, say so and add the guard.
- Prefer deleting instructions to adding them: the prompt that produced this output is already long.
- Keep the whole report skimmable. Use plain words. **Practice what you propose:** the report itself
  should pass the benchmark in section C.
