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
