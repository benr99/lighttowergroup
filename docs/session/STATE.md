# Ground truth

Facts only, each with how it was established. Updated at the end of every iteration.
Last updated: 2026-10-09, after Iteration 01.

## Repository

| Fact | Proof |
|---|---|
| Local `main` is 36 commits behind `origin/main`, 0 ahead | `git rev-list --left-right --count origin/main...HEAD` |
| Every upstream commit since Sep 1 is a bot (LTG Editorial Desk, LTG Health Monitor); none touch code we changed | `git log origin/main --since=2026-09-01 --format=%an`; `git diff --stat HEAD origin/main -- scripts tests insights.html .github config` is empty |
| No Codex work after Aug 28; `codex/*` branches end Aug 28; `.codex-artifacts/` holds two Aug 28 preview runs and an Aug 15 workbook script | `git for-each-ref --sort=-committerdate` |
| `.gitignore` ignores `*.py` except `scripts/*.py` and `tests/*.py`, so `docs/system-map/build.py` and `outputs/**/*.py` would not be committed by default | `.gitignore` lines 6–8 |
| `quality.yml` CI runs on pushes to `main` and `codex/**`, and on pull requests | `.github/workflows/quality.yml` |

## Branch

| Fact | Proof |
|---|---|
| `codex/phase-0-accurate-writer` exists locally in worktree `../ltg-phase0`, cut from `origin/main` (`ef65d89`); **not pushed** | `git -C ../ltg-phase0 log --oneline origin/main..HEAD` |
| It holds groups A–D as commits 0.3a–0.3d, the gate fix 0.3e, and the session record | same |
| 502 tests pass on that worktree; publication validation passes; map validates | Iteration 01 verification |
| Ben's work in progress is preserved, uncommitted, at `docs/session/wip/ben-wip-2026-10-09.patch` | file exists; main checkout unchanged |

## Uncommitted work in the main checkout (unchanged by Iteration 01; groups A–D now also live on the branch)

| Group | Files | Status |
|---|---|---|
| A. Accuracy gate (ship) | `scripts/readability.py`, `scripts/claim_verifier.py`, `scripts/v4_generation.py`, `scripts/v3_publish.py`, `scripts/insights_v3.py`, `tests/test_readability.py`, `tests/test_claim_verifier.py`, `tests/test_v4_generation.py` | new or modified |
| B. Friday weekly wrap (ship) | `scripts/weekly_wrap.py`, `.github/workflows/weekly-wrap.yml`, `tests/test_weekly_wrap.py`, `insights.html`, `insights/article-base.css` | new or modified |
| C. Voice engine prototype (ship, inert) | `scripts/ben_voice.py`, `scripts/voice_gate.py`, `tests/test_voice_gate.py`, `docs/voice/prompts/*.txt`, `docs/voice/*.json` | new; nothing imports it from the live path |
| D. Docs and tooling (ship) | `docs/intelligence-system-map.html`, `docs/system-map/`, `docs/SYSTEM_CLEANUP_PLAN.md`, `docs/voice/*.md`, `docs/session/`, `INSIGHTS_LINKEDIN_READABILITY_AUDIT_PROMPT.md`, `outputs/readability/`, `outputs/voice/` | new |
| E. Ben's earlier work in progress (do not touch) | `index.html`, `scripts/editorial_voice.py`, `scripts/daily_news_agent.py` (half-finished edit; does not compile) | modified before these sessions |
| F. Local run noise (do not commit) | `.editorial-state/provider-log.jsonl`, `.editorial-state/todays-run.json`, `outputs/voice/samples_run2.json` | |
| G. Older untracked docs (later, Iteration 8) | `COPY_DESIGN_AUDIT_*`, `FUNNEL_CONVERSION_AUDIT_*`, `ENHANCEMENT_PLAN.md`, `INSIGHTS_GENERATOR_*`, `compass_artifact_*`, `insights-blueprint.html`, `repo-blueprint.html`, `docs/mandate/15–27`, `.codex-artifacts/` | untracked |

## Production

| Fact | Proof |
|---|---|
| GitHub Actions publishes daily at 07:07 ET with the **old** v4 writer (no quote gate) | `origin/main:scripts/v4_generation.py` has no `claim_verifier` import |
| Latest published edition: 2026-10-08 | `git log origin/main -1` |
| OpenAI key returns `insufficient_quota`; both fact-check passes currently use DeepSeek | live probe 2026-10-08 |
| Windows Task Scheduler on this PC: "LTG Daily News Agent" 07:00 (lease makes it exit) and "Light Tower Ideas Daily" 06:30 (wrote `data/ideas/` files this morning) | `schtasks /Query` |

## Quality evidence so far

| Fact | Proof |
|---|---|
| 502 tests pass on a clean `origin/main` worktree plus the branch (496 before the 0.3e fix) | Iteration 01 |
| Old writer: 74 of 314 audited fact sentences unsupported (23.6%), 14 of 16 articles | `outputs/readability/ACCURACY.md` |
| New gated writer: 0 genuine unsupported of 143, 0 of 16 articles (one audit artifact explained) | same |
| Weekly wrap, week of Sep 26: 0 of 52 published lines unsupported | same |
| Voice engine prototype: accurate and readable (grade 9–11) but takes generic; 100–290 s per story | `docs/voice/SAMPLES.md` |
| The gated writer ran end to end on live feeds (two local previews, five stories each): 4 completed, 1 withheld, 0 failed; whole pipeline about 3 to 4 minutes | `docs/session/LOG.md` |
| Independent audit of the second preview: 46 kept fact sentences, 0 unsupported | `outputs/readability/audit_preview.py` |
| A day selects about 26 stories; writing takes about 85 to 140 s per story, 6 in parallel | preview logs |

## Open findings from the live preview

| ID | Finding |
|---|---|
| F17 | An administrative notice ("Notice to Users of the H.8 Release") passed eligibility; the gate withheld it |
| F18 | `precedent` and `novelty` measures did not vary on live data; top score 64.4, so nothing reached tier_a |
| F19 | A preview with `--state-dir` still rewrites `.editorial-state/source-health.json` and the retrieval cache in the repo |
