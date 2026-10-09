# Iteration 01: Ship-ready branch and a live end-to-end preview          Milestone: M1   Plan items: 0.1, 0.2, 0.3

## Why now
Everything built so far exists only as uncommitted files on one PC, mixed with older work in progress. Production still runs the writer that the audit showed states unsupported things in 14 of 16 articles. Nothing downstream (GitHub preview, supervised publish, every later milestone) can start until the work sits on a clean, tested branch. The new writer has also never run on live feeds end to end, only on cached stories; that is the biggest unknown left before shipping.

## Ground truth (verified, see STATE.md)
- Local `main` is 36 commits behind `origin/main` and 0 ahead; no upstream commit touches the code we changed.
- Groups A–D are ready to ship; E is Ben's untouchable work in progress; F is run noise.
- `.gitignore` would silently drop `docs/system-map/build.py` and `outputs/**/*.py`.
- 496 tests passed on a clean worktree with A–D on 2026-10-09.

## Objective
A local branch `codex/phase-0-accurate-writer`, cut from `origin/main`, holding groups A–D as four themed commits, verified on a clean tree, plus evidence from one live end-to-end preview of the real pipeline (live feeds, live models, five stories) showing the gate behaves on today's news. The main checkout, Ben's work in progress, production and `main` are untouched.

## Scope
In:
- Preserve group E as a patch file, without changing the working copy.
- Create the branch in a separate worktree (`../ltg-phase0`) so the main checkout is not disturbed.
- Copy groups A–D in; fix `.gitignore` so the session's tooling is tracked; four commits (A accuracy gate, B weekly wrap, C voice prototype, D docs and tooling).
- Full verification standard on the worktree.
- One live preview: `insights_v3.py --pipeline v4 --mode preview` limited to five stories, state written to a temporary directory.
- An independent audit of the preview's kept sentences against their sources.
- Update STATE.md and LOG.md; write the Iteration 02 prompt.

Out:
- Pushing anything (that is Iteration 02, with Ben's yes).
- Group E, group G, and any refactor.
- Wiring the voice engine into production.
- Fixing issues the preview reveals beyond a one-line obvious bug; record them instead.

## Steps
1. `git diff -- index.html scripts/editorial_voice.py scripts/daily_news_agent.py > docs/session/wip/ben-wip-2026-10-09.patch`. Confirm the working copy is unchanged afterwards.
2. `git worktree add ../ltg-phase0 -b codex/phase-0-accurate-writer origin/main`.
3. Copy group A files; commit `0.3a accuracy gate: quoted-fact writer, claim verifier, readability`.
4. Copy group B; commit `0.3b Friday weekly wrap with fact-checked lines`.
5. Copy group C; commit `0.3c voice engine prototype (not wired into production)`.
6. Add `!docs/**/*.py` and `!outputs/**/*.py` to `.gitignore`; copy group D (excluding run noise and the superseded `samples_run2.json`); commit `0.3d system map, plan, writing guide, session protocol, audit tooling`.
7. Run the verification standard on the worktree.
8. Live preview from the worktree, with keys taken from the environment:
   `python scripts/insights_v3.py --pipeline v4 --mode preview --daily-target 5 --article-limit 5 --state-dir <tmp>`
9. From `<tmp>`: count completed, withheld and failed; read every evidence file; run an independent audit of every kept fact sentence against its source text.
10. Reviewer pass: re-read the four commit diffs; confirm no group E or F file is in any commit; confirm `git -C ../ltg-phase0 log origin/main..HEAD` shows exactly four commits.

## Acceptance criteria
- `docs/session/wip/ben-wip-2026-10-09.patch` exists and `git diff --stat` in the main checkout is unchanged by this iteration.
- The branch has exactly four commits on top of `origin/main`; none contains `index.html`, `editorial_voice.py`, `daily_news_agent.py` or `provider-log.jsonl`.
- On the worktree: compile clean; all tests pass; `validate_publication.py` passes; the map validates and builds.
- The preview completes without a pipeline error. Each of the five slate stories is completed, withheld, or failed with a stated reason.
- The independent audit finds **zero** unsupported kept fact sentences; any flag is investigated and explained.
- STATE.md and LOG.md are updated, and `iterations/02-*.md` exists.

## Stop conditions
- Any test fails on the clean tree and the cause is not inside this iteration's files: stop and report.
- The preview fails in ingestion, provider or verifier setup: stop, report the error, do not work around it.
- The audit finds an unsupported kept fact sentence that is not an audit artifact: stop; this blocks shipping.

## Needs Ben
Nothing during this iteration. The closing report will ask about pushing the branch, D12 (second fact-check provider) and D13 (local Windows tasks).

## Budget
Model spend under $3 (five stories, each with a writer call, at most one retry and fact-check passes, plus the audit). About 30 to 45 minutes, most of it the preview's feed reading and fact checks.

## Report
Outcome; branch and commit list; test count; preview numbers (selected, completed, withheld, failed, facts kept and rejected, time); audit result; anything surprising; the three decisions; link to Iteration 02.
