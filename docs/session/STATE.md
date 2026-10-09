# Ground truth

Facts only, each with how it was established. Updated at the end of every iteration.
Last updated: 2026-10-09, after Iteration 03 ("make it smooth").

## Branch

| Fact | Proof |
|---|---|
| All work is on `codex/phase-0-accurate-writer` in worktree `C:\Users\Ben\Downloads\ltg-phase0`, cut from `origin/main` (`ef65d89`); **not pushed** (Ben: "lets not load it yet") | `git -C ../ltg-phase0 log --oneline origin/main..HEAD` (21 commits) |
| 542 tests pass; all scripts compile; publication validation passes; `site.js`/`edition.js` check; map validates (118 nodes, 0 problems) | Iteration 03 verification |
| Ben's work in progress is untouched in the main checkout and preserved at `docs/session/wip/ben-wip-2026-10-09.patch` | main checkout `git status` |

## What the system does now (branch)

| Fact | Proof |
|---|---|
| DeepSeek is the only provider: router, writer, fact-checker; no workflow passes an OpenAI key | `model_router.allowed_providers()`; `test_model_router`, `test_v4_voice_and_spend.test_verifier_is_deepseek_only`, `test_insights_v2_production` |
| Every model call retries rate limits, server errors and dropped connections (0/4/12 s); 3 exhausted calls or one refused key stop new stories, reported as "DeepSeek unavailable" | `v4_generation._chat`, `ProviderHealth`; tests |
| Spend is checked before and recorded after every call; the run reports it; a reached cap skips stories | live runs report $0.34–0.37 per 10 stories |
| The verified subset of a day publishes unless more than 20% failed or was skipped | `v3_publish.publication_decision`; tests |
| Flagships and analyses are written in Ben's voice when `INSIGHTS_VOICE=on` (default on for preview, **off** for production via the repo variable) | `v4_generation.voice_enabled`; daily workflow env |
| Every run builds `digest.html` (every sentence beside its quote) and `health.txt` | `scripts/daily_digest.py` |
| Publishing no longer loads `daily_news_agent.py`; pages are byte-identical | `test_site_renderer` |
| Previews keep all state in `--state-dir` | `test_insights_v3.PreviewStateStaysInItsFolder` |
| Friday wrap only publishes when the repo variable `WEEKLY_WRAP_PUBLISH` is `true` | `weekly-wrap.yml` |
| `scripts/rehearsal.py` runs a full preview day into `%USERPROFILE%\ltg-rehearsal\<date>\` | `test_rehearsal` |

## Live evidence (2026-10-09, three 10-story preview days)

| Run | Written | In Ben's voice | Withheld / failed | Spend | Time writing | Independent audit of kept facts |
|---|---|---|---|---|---|---|
| 1 | 10/10 | 9 | 0 / 0 | $0.36 | 484 s | 0 of 81 flagged; human read found 3 opinion problems and 1 encoding problem → fixed |
| 2 | 10/10 | 9 | 0 / 0 | $0.34 | 303 s | **1 of 76 flagged** ("add" for "offer") plus 2 opinion problems → fixed; sentence re-checked live: now cut |
| 3 | 10/10 | 9 | 0 / 0 | $0.37 | 331 s | **0 of 94 flagged**; opinion lines within the rules |

Folders: `C:\Users\Ben\ltg-rehearsal\2026-10-09\`, `...\second-run\2026-10-09\`, `...\third-run\2026-10-09\` (each with `digest.html`, `health.txt`, `audit.json`).

## Production (unchanged)

| Fact | Proof |
|---|---|
| GitHub Actions still publishes daily at 07:07 ET with the **old** v4 writer (no quote gate) | `origin/main:scripts/v4_generation.py` |
| Windows task "LTG Daily News Agent" is still enabled; disabling it needs administrator rights (Ben) | `Disable-ScheduledTask` → Access is denied |

## Still open

| Item | Note |
|---|---|
| Thin sectors | Run 1: 6 of 7 sectors short of 10 (only CRE full); plan 6.4 |
| tier_a (flagship) almost never happens | needs 3 independent sources and 2 full texts; 174 of 180 eligible stories have one source |
| Opinion lines are the judgement-call layer | rules hold, but some takes still generalise from one deal; Ben's rehearsal read decides |
| Titles are checked for names and numbers, not tone | e.g. "Braemar Pays $480M to Fire Its Manager" (source: terminates its management agreement) |
| Classification uses a model for ~90 items a day outside the spend ledger | `classification.classify_batch` |
| Backfill sector for existing manifest entries; legacy quarantine (3.4); shared types (3.2) | plan |
