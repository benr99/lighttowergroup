# Iteration log

## Iteration 01: Ship-ready branch and a live end-to-end preview (2026-10-09)

**Outcome: done.** Branch `codex/phase-0-accurate-writer` (local only, not pushed) holds the session's work as five commits on top of `origin/main`, verified on a clean worktree. The new writer ran end to end on live feeds for the first time, exposed one real accuracy defect, which was fixed and re-proved.

**Commits** (`git log origin/main..codex/phase-0-accurate-writer`):
- `15812a1` 0.3a accuracy gate: quoted-fact writer, claim verifier, readability
- `4fe3a5e` 0.3b Friday weekly wrap with fact-checked lines
- `38effd1` 0.3c voice engine prototype (not wired into production)
- `1689cb6` 0.3d system map, plan, writing guide, session protocol, audit tooling
- `81eb2a0` 0.3e gate: names from a quote's surroundings; delete sentences that point back to a deleted one

**Deviation from the prompt:** the prompt said four commits. The Reviewer pass found an accuracy defect during the live preview, and the Director pulled the fix into this iteration because it blocks M1. It is a separate fifth commit so its reasoning is visible.

**Evidence**
- Ben's work in progress preserved at `docs/session/wip/ben-wip-2026-10-09.patch` (241 lines); main checkout's `git diff --stat` unchanged; none of `index.html`, `editorial_voice.py`, `daily_news_agent.py`, `provider-log.jsonl` in any commit.
- Clean worktree: compile clean; **502 tests pass**; `validate_publication.py` passes; map validates (25 groups, 115 nodes, 0 problems).
- Live preview 1 (five stories): 877 documents → 843 events → 112 eligible → 250 read → 26 selected; 4 completed, 1 withheld, 0 failed; writing took 140 s in parallel; whole pipeline 4.3 min. Audit: 42 kept fact sentences, 0 flagged.
- **Defect found by the Reviewer, not the audit:** in the Hines article the name check deleted the sentences introducing each property ("99 West Paces in Atlanta…") because the city sat one line above the quote. The surviving "It is 96% leased… The REIT paid $117 million" then read as the Atlanta tower, though the source says it is the Columbus portfolio. Each sentence was true alone, so the per-sentence audit passed it; in context it was wrong.
- Fix (`0.3e`): names may come from 300 characters around the quote or a standard alias; numbers stay bound to the quote; a back-referencing sentence is deleted with its antecedent; the writer must name each sentence's subject.
- Live preview 2: same slate, name false-rejections 5 → 0, the Hines article now introduces each property before describing it; audit: **46 kept fact sentences, 0 flagged**.

**Other findings (recorded, not fixed)**
- The withheld story was "Notice to Users of the H.8 Release", an administrative Fed notice. Eligibility let it through; the gate stopped it. (Plan: new F17.)
- `precedent` and `novelty` scoring measures are degenerate on live data (no variation). Top score 64.4, so no story reached tier_a. (F18.)
- Spend reported as $0.000: the cap is not enforced on v4 (confirms F5).
- A preview with `--state-dir` still rewrites `.editorial-state/source-health.json` and the retrieval cache in the repo. (F19.)
- Six of seven sectors were short of their target of 10 (only commercial real estate filled).

**Decisions requested:** push and PR, D12, D13 (see Iteration 02).

## Between iterations: Ben zooms out (2026-10-09)

Ben asked where Codex's writing work went, paused go-live, chose DeepSeek only, and approved turning off the old "LTG Daily News Agent" task. Disabling it failed with "Access is denied" (it needs administrator rights), so Ben will do that one step. Codex's writing history and the zoomed-out plan are in `ZOOM_OUT_PLAN.md`; the backlog is reordered; Iteration 02 is on hold.

## Iteration 03: Make it smooth (2026-10-09)

**Outcome: done, except the parts that need Ben** (push, switching on the rehearsal schedule, the admin step for the old Windows task, and voice in production). Prompt: `iterations/03-make-it-smooth.md`.

**Commits** (on `codex/phase-0-accurate-writer`, not pushed): session prompt; 1.4–1.6 DeepSeek only, retries, spend cap, verified subset publishes; 7.1 one writer with Ben's voice; 7.3 Codex's voice work merged; 6.1 story picking (F17, F18); oversight (digest, health note, wrap switch); 3.1 renderer extracted (F1); F19 state isolation; 1.3 sector filters (F14); 0.6 rehearsal kit; map and plan; two rounds of rehearsal fixes.

**Evidence**
- 542 tests pass; compile, publication validation, JS checks and map validation pass.
- Rendered page byte-identical before and after the renderer move.
- Three live 10-story preview days, DeepSeek only, $0.34–0.37 each, 10/10 written every time, 9 in Ben's voice.
- Independent audits: run 1, 0 of 81; run 2, **1 of 76** ("will add updated apartments" where the source says "offer"); run 3, 0 of 94. The run-2 sentence was re-checked with the updated checker and is now cut.
- A human read of every opinion line found: an intent claim ("the mayor is trying to... without another tax hike"), a motive claim ("betting that"), stock deadline lines ("the clock is ticking"), a take adopting one side's allegation (Cook hearing), a reading stated as a finding with a prediction about other cities. All are now rejected by rules, with tests that replay the exact sentences.
- Encoding damage from one source (U+FFFD) would have failed the publisher's mojibake check and sent the whole day to review; the source text is now repaired before writing.
- Found in passing: two backspace characters in the retired `_surprise` regex on `origin/main`; fixed.

**Deviations from the prompt**
- Moving legacy code to `scripts/legacy/` and extracting shared types were left out (too many importers to do safely in one run).
- The prompt planned one live run; there were three, because each read found something to fix.

**Decisions requested:** see the report to Ben (switch on the rehearsal, disable the old task, push when ready).

## Go-live and the LinkedIn roundup (2026-10-11)

Ben: "Push it, voice on, and build the LinkedIn post as a bulleted story post."
- Built `scripts/linkedin_post.py` (plan 7.5): a daily bulleted roundup in Ben's voice from the published stories' verified sentences, every line re-checked, one rewrite with the deletions quoted back; shown on the digest page (copy buttons) and the Actions run summary. On the Oct 9 rehearsal stories: 7 stories, 2,130 characters; the check deleted 3 lines (e.g. "$98M" for "$97.8 million", a name not in the facts).
- Pushed to `main` (`cd89386`), set repo variable `INSIGHTS_VOICE=on`. Site quality CI passed.
- First Actions preview (run 38171000498) found that production wrote no evidence files (no `--state-dir`), so the digest and post would have been empty; fixed and pushed (`39215d3`). A second preview had a single (withheld) candidate, so the post path on Actions is proven by tests and local runs; the first real proof is the 07:07 ET run.
