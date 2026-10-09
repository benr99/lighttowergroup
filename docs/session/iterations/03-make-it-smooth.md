> **Status (2026-10-09): done.** See LOG.md, Iteration 03.

# Iteration 03: Make it smooth (everything before the rehearsal week)

Milestones: M1 (writer), M2 (protect the reader), M4 (part), M5 (part), M6 (part)
Plan: `../ZOOM_OUT_PLAN.md` steps 1–5, plus the tooling for step 6. Backlog items 2–7.

## Why now
Ben paused go-live and asked for the whole system to be made smooth before anything is turned on. He wants one run of work, done step by step without stopping, then a plain report. Everything here stays on the local branch `codex/phase-0-accurate-writer` (worktree `C:\Users\Ben\Downloads\ltg-phase0`). Nothing is pushed or published.

## Ben's standing decisions (2026-10-09)
- DeepSeek only. OpenAI is removed from every live chain (D12).
- Do not push or publish. No schedule is switched on by the Engineer.
- Plan step 2 says "one failed story must not block the rest of the day"; Ben read and approved it, so D4 is taken at its recommended default (publish the verified subset; send everything to a review PR only above a failure threshold).
- D11 (opinion sentences) is taken at its default: built and **on in previews**, behind a switch that is **off for production** until Ben reads the rehearsal.

## Ground truth (verified before starting)
- Branch is clean at `26001da`; 502 tests pass (`python -m unittest discover -s tests`).
- `scripts/v4_generation.py:_make_verifier` tries OpenAI first and DeepSeek second.
- `scripts/model_router.py:select_provider` falls back to OpenAI.
- `write_all(budget=...)` ignores the budget; spend reads $0 (F5).
- `v3_publish.py:404` sets `auto_publish_allowed` only when zero stories failed **and** zero were skipped (F16).
- `v3_publish.py:208` imports four renderer functions from the 2,872-line `daily_news_agent.py` (F1).
- The voice engine (`ben_voice.py`, `voice_gate.py`, `docs/voice/prompts/`) is proven in `outputs/voice/prototype.py` and is not wired into v4 (F9).
- An administrative Fed notice reached the writer (F17); `precedent` and `novelty` do not vary (F18); previews still write `source-health.json` and the retrieval cache into the repo (F19).

## Objective
After this run, one command produces a full preview day that is DeepSeek-only, spend-capped, voice-written where the story earns it, fact-checked sentence by sentence, unblocked by single failures, and summarised in a one-page digest Ben can read. Every claim here is proved by a test or a live run.

## Scope
**In**
- A. DeepSeek-only reliability (items 1.4, 1.5, 1.6, F5, F11, F16).
- B. Story picking (F17, F18; administrative and off-topic items).
- C. One writer: the voice engine wired into v4 as the writer for flagships and analyses, merged with the best of Codex's July voice work; briefs keep the fast facts-only path (items 7.1, 7.3; F9, F10).
- D. Oversight: daily digest page, daily health note, wrap preview switch (items 0.6a, 5.1, 5.2).
- E. Clean house: renderer out of `daily_news_agent.py`; previews stop writing into the repo; sector shown in the manifest (items 3.1, 1.3; F1, F19, F14 where safe).
- F. Rehearsal kit: one script that runs a full preview day into a folder outside the repo and builds the digest, plus the one command Ben runs to schedule it.
- G. Verify everything, run one live preview day, audit it, record and report.

**Out**
- Pushing, publishing, PRs, switching on any schedule, touching secrets.
- Ben's work in progress (`index.html`, `scripts/editorial_voice.py`, the `daily_news_agent.py` edit in the main checkout). Codex's persona text may be **read** for ideas; the file is never edited or committed.
- Archive triage (D3), NewsAPI (D8), the feedback loop (D9), LinkedIn derivatives: later iterations.
- Moving legacy code into `scripts/legacy/` (too many importers to do safely in this run; recorded as next).

## Steps

### A. DeepSeek only, dependable
1. `model_router.select_provider`: DeepSeek only. If its health check fails, retry it twice with pauses, then raise a clear "DeepSeek unavailable" error. No OpenAI anywhere in the live chain. `provider_chain` is DeepSeek-only.
2. `_make_verifier`: DeepSeek only (reasoning on), with patient retries for 429, 5xx and network errors.
3. Writer requests (`_request_once` and the voice path) retry 429, 5xx and network errors with backoff, inside the article deadline.
4. Spend: every writer and verifier call reports its token usage to a shared `Budget`; `Budget.allow()` is asked before each call; a refused call ends that story as "skipped: daily budget reached". `write_all` uses the budget it is given. The run report shows real spend.
5. Provider outage: if DeepSeek fails on its first several calls in a row, stop starting new stories and report "DeepSeek unavailable", so the day ends cleanly instead of grinding.
6. Partial-day publishing: `auto_publish_allowed` is true when at least one story published and failures plus skips are no more than a set share of the day (default 20%). Reasons are written into `publication-decision.json`.

### B. Story picking
7. Administrative notices (release notices, "notice to users", schedule changes, data revisions, website or system notices) are typed as never-eligible. Test with the H.8 title.
8. Investigate `precedent` and `novelty` on the saved candidate file from the last live preview. Fix the cause if it is a defect. If a measure cannot vary in practice, give its weight to the measures that do, and say so in the code. Tests prove both vary on realistic input.

### C. One writer
9. Merge the strongest ideas from Codex's July voice guide (`docs/mandate/editorial/06`) and the persona draft (read-only) into `docs/voice/prompts/system.txt`. Check them against the accuracy rules: nothing that invites invented facts, motives or experiences.
10. Add the voice path to `v4_generation.write_one`: for `tier_a` and `tier_b` when voice is on, make a brief call, then an article call, then `voice_gate.verify_voice_draft`, then one retry with the rejection notes, then the same publish contract. Briefs (`tier_c`) keep the facts-only writer. If the voice path fails to produce enough verified facts, fall back once to the facts-only writer before withholding.
11. Voice switch: `INSIGHTS_VOICE` = `on` | `off`. Previews default to on; the production workflow sets off until Ben says otherwise.
12. One `DEPTH_SPEC` (F10): v4 owns it; the old writer imports from v4 or keeps its own private copy for the legacy path only.
13. Evidence files record the kind of every kept sentence and the rejection reasons, for the digest.

### D. Oversight
14. `scripts/daily_digest.py`: reads a run folder (run report plus `v4-evidence/`) and writes a single readable HTML page: the day in numbers, then each story with every sentence beside its source quote, its kind (fact, take, voice), and what was cut and why. Fully offline.
15. Daily health note: a short text summary (stories written, withheld, skipped, failed, spend, time, warnings) written beside the digest and printed at the end of every run.
16. Weekly wrap: the scheduled run only publishes when the repo variable `WEEKLY_WRAP_PUBLISH` is `true`; otherwise it builds a preview artifact.

### E. Clean house
17. Move `render_html`, `update_manifest`, `update_feed_xml`, `update_sitemap_xml` and what they need into `scripts/site_renderer.py`. `daily_news_agent.py` imports them from there, so its behaviour is unchanged. `v3_publish.py` imports only `site_renderer`. A test proves `v3_publish` no longer loads `daily_news_agent`.
18. F19: `source-health.json` and the retrieval cache follow `--state-dir`.
19. Sector in the manifest and filters (F14): store each article's sector in the manifest; make the Intelligence page filters match it. Only if it can be done without touching `index.html` and with a test; otherwise record it.

### F. Rehearsal kit
20. `scripts/rehearsal.py` (and a `.ps1` wrapper): runs `insights_v3.py --pipeline v4 --mode preview` with voice on, into `%USERPROFILE%\ltg-rehearsal\<date>\`, then builds the digest and health note there. It never writes into the repo.
21. Write the single Task Scheduler command for Ben to switch on a daily rehearsal. The Engineer does not run it.

### G. Verify, review, record
22. Standard checks on the worktree (compile, all tests, `validate_publication.py`, JS checks, map validate and build).
23. Update the system map (`docs/system-map/data.js`): close the fixed flags, add any new nodes; plan ticks in `docs/SYSTEM_CLEANUP_PLAN.md`.
24. One live preview day with the rehearsal script (spend cap $3 for this iteration via `LTG_MAX_DAILY_USD`). Then the accuracy audit on every kept fact sentence, and a read of every kept take and voice line.
25. Reviewer pass: re-read the full diff; try one input meant to break each new rule; confirm nothing in section 2 of the operating prompt was bent.
26. One commit per theme. Update `STATE.md`, `LOG.md`, and the plan. Write the plain-English report for Ben.

## Acceptance criteria
- `grep -n openai scripts/v4_generation.py scripts/model_router.py` shows no live use (constants for legacy reporting only, if any).
- Tests: a 429 then success is retried; an exhausted budget skips stories and reports spend; three straight provider failures stop new stories; one failed story out of ten still allows auto-publish; three out of ten does not; the H.8 title is never-eligible; voice path with a fake model keeps facts, keeps a fair take, deletes an unfounded take; `v3_publish` imports without loading `daily_news_agent`; preview state stays in `--state-dir`.
- All tests pass on the worktree; publication validation passes; map validates.
- Live preview: zero unsupported fact sentences in the audit; every kept take reads as opinion and rests on kept facts; spend reported and under the cap; a digest page exists and opens.

## Stop conditions
- A change would require pushing, publishing, a schedule, or a secret: stop that step, record it, continue with the rest.
- The live audit finds an unsupported fact: fix the gate before anything else; never report around it.
- DeepSeek is down for the live run: finish everything else, report it, and leave the live run for the rehearsal.

## Needs Ben (after the run, at most three)
1. Switch on the daily rehearsal (one command).
2. Disable the old "LTG Daily News Agent" task (admin step, unchanged).
3. After a week of digests: voice on in production, then go live.

## Budget
Model spend up to $3 for the live preview. Time: as long as it takes, without stopping.

## Report
Plain English, friendly, short: what was done, what was proved, what is left, the few things Ben needs to do. Technical detail lives in `LOG.md` and `STATE.md`.
