# Light Tower Insights: System Cleanup and Improvement Plan

Written 2026-10-09. Companion to the system map (`docs/intelligence-system-map.html`) and the accuracy findings
(`outputs/readability/ACCURACY.md`). Every item below comes from a verified finding, not a guess.
Where something is suspected rather than verified, it says so.

---

## 1. Principles for the whole effort

1. **Accuracy beats everything.** No change may make a published sentence less traceable to a source. Factual checks block; they never warn.
2. **Ship small, reversible steps.** One theme per commit. Every step has a test, a rollback and an acceptance check. Production runs daily at 07:07 ET; nothing lands untested.
3. **Make the code say what it does.** If a config key, workflow, or file does not affect the live system, either wire it in or delete it. Misleading controls are worse than none.
4. **Measure before and after.** Accuracy audit, reader-visible checks, and run reports are the evidence. "It looks better" does not close an item.
5. **Decisions are yours; execution is ours.** Items that need a product call are listed in section 6. We do not guess on those.

## 2. Where we are (evidence)

| Fact | Value | Source |
|---|---|---|
| Unsupported sentences in the old writer's output | **23.6%** (74 of 314), 14 of 16 articles | accuracy audit, 2026-10-08 |
| Same measure for the new fact-gated writer | 0 genuine (1 audit artifact) of 143, 0 of 16 articles | same audit |
| Live pages written before any gate | ~1,450 | `insights.json` on origin |
| Scripts | 105 files, ~36,800 lines | `scripts/` |
| Of which live path / weekly wrap / satellites / legacy | ~9,400 / ~900 / ~4,500 / ~6,000 lines (rest are maintenance and one-off scripts) | system map |
| Local checkout vs origin | **36 commits behind**, 0 ahead; every commit since Sep 1 is a bot (27 desk, 5 health) | `git rev-list` |
| Uncommitted work in this checkout | 10 modified files, 32 untracked, including the new writer, verifier, readability module, weekly wrap, workflow, tests | `git status` |
| Tests | 480 pass on a clean tree with all changes | CI-equivalent run |
| Intelligence-page filters that match recent content | 2 of 6 sector buttons (Private Equity, Data Centers) | 535 articles since Sep 1 |

The two biggest risks are not code quality. They are (a) **the new accurate writer exists only on this machine**, while production still runs the old writer, and (b) **the archive was never verified**.

## 3. Issue register

Severity: **H** harms readers or the business now · **M** wastes effort or hides problems · **L** tidiness. Effort: S under 2 h · M half a day · L one to two days.

| ID | Issue | Sev | Phase | Effort | Flag |
|---|---|---|---|---|---|
| A1 | Accurate writer + verifier not committed or deployed; production still uses the old writer | H | 0 | M | n/a |
| A2 | Local `daily_news_agent.py` has an unfinished edit that does not compile | H | 0 | S | F1 |
| A3 | Local checkout 36 commits behind origin; unrelated WIP mixed in one tree | M | 0 | S | n/a |
| A4 | OpenAI account has no credit, so the second fact-check pass is the same model family | H | 0 | S | F6 |
| A5 | Earlier memory note contained live API keys (scrubbed); keys may need rotating | H | 0 | S | n/a |
| B1 | ~1,450 archive pages unverified; sample shows ~24% of sentences unsupported | H | 1 | L | F12 |
| B2 | Four Intelligence filters match nothing; manifest has no `sector` field | H | 1 | M | F14 |
| B3 | Spend cap not enforced on the v4 writer; spend reports read $0 | H | 1 | M | F5 |
| B4 | One skipped or failed story sends the whole day to a review PR | M | 1 | M | F16 |
| B5 | Writer has no provider fallback | M | 1 | M | F11 |
| C1 | Seven "active" NewsAPI sources are skipped; `NEWSAPI_KEY` unused | L | 2 | S | F7 |
| C2 | Index-page sources tried as RSS; only 12 of 16 read | L | 2 | S | F8 |
| C3 | `thresholds.json` does not control live selection | M | 2 | M | F2 |
| C4 | Sunday assignment desk feeds nothing live | M | 2 | S | F3 |
| C5 | `latest-edition.json` written daily, displayed nowhere | M | 2 | M | F4 |
| C6 | Audience feedback loop is open | M | 2 | M | F13 |
| D1 | 2,872-line legacy monolith on the publish path | H | 3 | L | F1 |
| D2 | `DEPTH_SPEC` duplicated; v4 imports the v3 writer module for three symbols | L | 3 | S | F10 |
| D3 | Voice persona (`editorial_voice.py`) does not shape daily articles | M | 3 | M | F9 |
| D4 | Legacy v2/v3 code (~6,000 lines) mixed with live code | M | 3 | L | n/a |
| E1 | Repo clutter: 86 root files, stray audit/prompt docs, two old blueprint pages, `outputs/`, `.codex-artifacts/` | L | 4 | M | n/a |
| E2 | No pipeline README; 25 mandate docs of mixed accuracy | M | 4 | M | n/a |
| E3 | Line-ending warnings (CRLF/LF) on many files | L | 4 | S | n/a |
| E4 | Local scheduler remnants (`agent_runtime`, `.bat`, `setup_scheduler.ps1`) | L | 4 | S | F15 |
| F1 | No alerting on withheld/failed/rejection rates; no routine for reading evidence files | M | 5 | M | n/a |
| F2 | Daily and weekly jobs both rewrite `generated-files.json` and `provider-log.jsonl` | L | 5 | S | n/a |
| F3 | No integration test that runs a whole day on recorded fixtures | M | 5 | L | n/a |
| G1 | Off-topic stories still reach the page (for example a ship-fuel startup) | M | 6 | M | n/a |
| G2 | Voice and readability tuning on real reader data | M | 6 | M | n/a |
| F17 | Administrative notices pass eligibility (H.8 notice selected; gate withheld it) | M | 6 | S | F17 |
| F18 | `precedent` and `novelty` measures degenerate on live data; nothing reaches tier_a | M | 6 | M | F18 |
| F19 | Previews with `--state-dir` still write source health and the retrieval cache into the repo | L | 5 | S | F19 |
| H1 | Writing is accurate but flat: no hooks, point of view or cultural meaning, so reach and deal flow suffer | H | 7 | L | n/a |

## 4. The plan, phase by phase

Each phase ends with a checkpoint: all tests green, a preview run read by a human, and a decision to proceed.

### Phase 0. Stabilise and ship what we built (do this first)

**Goal:** the accurate writer is in production, behind a safe rollout, on a clean branch.

- [ ] **0.1 Decide the fate of the local `daily_news_agent.py` edit (A2).** It adds a lock around `update_manifest` and a Google Analytics tag but is half-applied. Either finish the lock correctly (a proper `try/finally`) or revert. *Acceptance:* `python -m py_compile scripts/*.py` passes locally.
- [x] **0.2 Create a working branch and sync (A3).** Done 2026-10-09: `codex/phase-0-accurate-writer` from `origin/main`, in worktree `../ltg-phase0`. `git switch -c cleanup/phase-0`, rebase onto `origin/main` (36 bot commits touch content only, so conflicts are unlikely). *Acceptance:* `git rev-list --left-right --count HEAD...origin/main` shows 0 behind.
- [x] **0.3 Split the uncommitted work into reviewable commits.** Done 2026-10-09: commits 0.3a–0.3e; a live preview found and fixed one defect (0.3e). (a) readability + claim verifier + v4 writer + tests; (b) weekly wrap + workflow + tests + `insights.html` feature band; (c) system map + plan + audit scripts under `docs/` and `outputs/`; (d) the unrelated `index.html` and `editorial_voice.py` changes, each as its own commit or deferred. *Acceptance:* every commit passes `python -m unittest discover -s tests`.
- [ ] **0.4 Restore a genuinely independent second checker (A4).** Add OpenAI credit, or supply another provider key. Then re-run `outputs/readability/accuracy_audit.py` once so the report says which model checked which. *Acceptance:* the evidence file shows verifier ≠ writer provider.
- [ ] **0.5 Rotate any key that was ever in a memory or notes file (A5).** DeepSeek and NewsAPI at minimum. Update the GitHub secrets.
- [ ] **0.6 Supervised rollout.** Dispatch the daily workflow with `pipeline=v4`, `mode=preview`. Read 10 evidence files in `.editorial-state/v4-evidence/` and spot-check 5 sentences each against the source. Then one manual `mode=publish`, then enable the cron. *Acceptance:* zero unsupported sentences found in the spot check; withheld rate under 25%.
- [ ] **0.7 Weekly wrap preview.** Dispatch `weekly-wrap.yml` in preview for the latest Friday; read it.

**Rollback:** the workflow can still run `pipeline=v3` or `v2`; reverting one commit restores the old writer.

### Phase 1. Protect the reader

**Goal:** nothing wrong stays live, and the page behaves as it claims.

- [ ] **1.1 Audit and triage the archive (B1).** Re-fetch each page's source (the retrieval cache is not committed, so this needs live fetches; some will be dead or paywalled), run the claim verifier over every sentence, and write `outputs/archive-audit.json`. Three buckets: *verified*, *has flagged sentences*, *cannot verify*. *Acceptance:* a ranked list, worst first.
- [ ] **1.2 Apply a policy to the archive (decision D3).** Options: unpublish the worst N; add a "not independently verified" note to the pages that cannot be checked; regenerate flagged pages through the new writer; leave the rest. Whatever we choose, record it in the manifest (`verified: true|false|null`).
- [ ] **1.3 Store sector in the manifest and fix the filters (B2).** Add `sector` and `subsector` to each `insights.json` entry at publish time (and backfill from tags for existing entries). Make `insights.html` filter on `sector`, not category names. *Acceptance:* all six sector buttons return items for the last 30 days; a test asserts every manifest entry has a sector.
- [ ] **1.4 Enforce the spend cap in v4 (B3).** `budget.allow()` before every writer and verifier call; `budget.record()` after; the run report shows real spend. *Acceptance:* a unit test with a $0.01 cap stops generation and the run reports "stopped by budget" rather than failing.
- [ ] **1.5 Publish the completed subset (B4, decision D4).** Replace "any failed or skipped story blocks everything" with: publish verified stories, list the rest in the run summary, and open a review PR only for a zero-article day or an error rate above a threshold. *Acceptance:* a test where 3 of 70 fail still publishes 67 and exits 0 with a warning.
- [ ] **1.6 Decide the writer fallback (B5, decision D5).** Either leave single-provider (stories fail when DeepSeek is down) or add a bounded fallback to the second provider with the same gate. *Acceptance:* a provider-outage test matches the chosen behaviour.

**Rollback:** each item is a separate commit; manifest additions are backward compatible.

### Phase 2. Make the flow honest

**Goal:** every config key, workflow and file either does something live or is gone.

- [ ] **2.1 Make selection read its config (C3).** `selection.py` takes floor, sector target, per-source and per-company caps and tier cutoffs from `config/thresholds.json` (one source of truth); remove the keys only the legacy ranker used. *Acceptance:* changing the floor in config changes the slate in a test; a test fails if a config key is unused.
- [ ] **2.2 Fix the source list (C1, C2).** Deactivate the seven NewsAPI entries (or implement the fetch, decision D8); stop `ingestion.py` fetching `html_listing` sources as RSS; raise `--listing-limit` to cover all 16. *Acceptance:* the ingest report lists feeds attempted, succeeded, skipped (with reason), and the numbers on the system map match it.
- [ ] **2.3 Resolve the assignment desk (C4).** Wire `assignment-queue.json` and `structured-candidates.json` into the live selection (as candidates with a bonus), or retire the Sunday workflow. *Acceptance:* either an end-to-end test shows a queued item reaching the slate, or the workflow is deleted.
- [ ] **2.4 Resolve the edition record (C5, decision D7).** Either render `latest-edition.json` on the site (include `edition.js`), or shrink the record to what `verify_deployment.py` needs and delete the unused fields. Keep a deployment check either way. *Acceptance:* no field is written that nothing reads.
- [ ] **2.5 Resolve the feedback loop (C6, decision D9).** Persist reader signals somewhere durable and feed them into scoring (an `audience` measure with a documented weight), or remove the pretence. *Acceptance:* a measure that varies, documented in `importance.py`, with the distribution report passing.

### Phase 3. Untangle the code

**Goal:** the live path is small, importable on its own, and separate from legacy.

- [ ] **3.1 Extract the renderer (D1).** Move `render_html`, `sanitize_html`, `update_manifest`, `update_feed_xml`, `update_sitemap_xml`, `calculate_read_time` into `scripts/site_render.py` and `scripts/manifest.py` with their tests. `v3_publish.py` and `weekly_wrap.py` import from there. `daily_news_agent.py` imports from there too, so v2 keeps working. *Acceptance:* the publish path no longer imports `daily_news_agent`; a test asserts that.
- [ ] **3.2 Extract shared types (D2).** `DraftResult`, `object_to_dossier`, `DEPTH_SPEC` move to `scripts/dossier.py`; delete the stale `DEPTH_SPEC` copy in the v3 writer. *Acceptance:* `import v4_generation` no longer loads `editorial_pipeline`.
- [ ] **3.3 One house style (D3, decision D2).** Decide whether the facts-only voice also governs LinkedIn. Either retire the persona in `editorial_voice.py` or make the satellite agents use `readability.py` and the same verifier. *Acceptance:* one document, `docs/HOUSE_STYLE.md`, and tests that enforce it.
- [ ] **3.4 Quarantine legacy (D4).** Move v2/v3 modules to `scripts/legacy/` behind import shims, add a smoke test per rollback path, and set a deletion date (decision D6, suggest 60 days of clean v4 runs). *Acceptance:* the live import graph contains no legacy module; the system map's "live" group matches it.
- [ ] **3.5 (Optional) Package the live path.** Group into `sources / events / gate / evidence / rank / write / publish / weekly`. Do this only after 3.1–3.4, with shims, because workflows reference `scripts/*.py` paths. See target layout below.

### Phase 4. Repo hygiene

**Goal:** a new person can find what matters in five minutes.

- [ ] **4.1 Clear the root (E1).** Move the audit prompts and reports (`COPY_DESIGN_*`, `FUNNEL_*`, `INSIGHTS_GENERATOR_*`, `compass_artifact_*`, `ENHANCEMENT_PLAN.md`) to `docs/archive/`; remove or relocate `insights-blueprint.html` and `repo-blueprint.html` (superseded by the new map); decide on `outputs/` and `.codex-artifacts/` (gitignore or commit). *Acceptance:* under 40 root files, all explained in the README.
- [ ] **4.2 Write the README and architecture doc (E2).** One `docs/ARCHITECTURE.md` generated from the system map data (so it cannot drift), plus a `README` section: how a day runs, how to preview, how to roll back, how to read an evidence file. Mark each file in `docs/mandate/` as current, historical, or superseded.
- [ ] **4.3 Normalise line endings (E3).** `.gitattributes` with `* text=auto`; one commit that renormalises. *Acceptance:* no CRLF warnings on `git add`.
- [ ] **4.4 Retire the local scheduler (E4).** Delete `agent_runtime.py`, the `.bat` wrappers, `setup_scheduler.ps1` and the scheduler lease logic once Phase 0 has run clean for two weeks.
- [ ] **4.5 Size check.** `insights/` is 120 MB and the git pack 108 MB; confirm Netlify build time is unaffected and decide whether social PNGs and PDFs belong in git.

### Phase 5. Operate it

**Goal:** problems are noticed by the system, not by readers.

- [ ] **5.1 Daily health summary (F1).** One page per run: stories selected, written, withheld, failed; fact-check rejection rate; spend; time; sources dead. Post it as the run summary and flag thresholds (withheld above 25%, rejection rate above 40%, any provider down).
- [ ] **5.2 Evidence spot-check routine.** A weekly script that picks 5 random published sentences and shows the quote and source side by side, for a two-minute human check. Record the result.
- [ ] **5.3 Stop the two workflows colliding (F2).** Give the daily and weekly jobs separate generated-files manifests and separate provider logs, or serialise them explicitly.
- [ ] **5.4 Integration test on recorded fixtures (F3).** Freeze one real day (feeds, pages, model responses) and replay the whole pipeline offline, asserting the slate, the published files and the verifier verdicts. *Acceptance:* runs in CI under two minutes.
- [ ] **5.5 Runbooks.** One page each: provider outage, rollback, a bad article reported by a reader (find the evidence file, unpublish, correct), and a feed going dark.

### Phase 6. Raise the quality bar (after the foundation is solid)

- [ ] **6.1 Relevance gate (G1).** Tighten the beat anchor in `eligibility.py` so adjacent news (ship fuel, a fintech charter) stops reaching a capital-markets page; measure with a labelled sample of 100 stories.
- [ ] **6.2 Readability on real readers (G2).** Use scroll depth and click-through from the Intelligence cards (the `track-read` events) to compare the old and new writer; tune hooks within the facts-only constraint.
- [ ] **6.3 Weekly wrap polish.** Review which sections fall back most; improve the source-stated "why it matters" extraction; consider a LinkedIn-ready version built from the verified lines only.
- [ ] **6.4 Source coverage.** Re-probe blocked feeds; add primary-source feeds in sectors with the thinnest slates (see the shortfall reasons in the run report).

### Phase 7. The voice engine (the writing evolution)

**Goal:** pieces people actually read, like and share, in Ben Rohr's voice, with the same accuracy guarantee. Full design: `docs/voice/WRITING_GUIDE.md`. Prompts: `docs/voice/prompts/`. Prototype and samples: `outputs/voice/`, `docs/voice/SAMPLES.md`.

Depends on Phase 0 (the fact gate in production) and 1.4 (spend cap), because it adds one to two model calls per story.

- [ ] **7.1 Settle the voice policy (decisions V1 to V6).** Opinion sentences allowed under the strict rules? How much first person? Who verifies the Context Bank? *Acceptance:* a one-page policy committed as `docs/voice/POLICY.md`.
- [ ] **7.2 Seed the two banks.** Ben writes 10 to 15 real notes (`ben-notes.json`); we research and verify 20 context entries with primary-source links (`context-bank.json`). *Acceptance:* every entry has a source URL, a date and a verifier.
- [ ] **7.3 Productionise the engine.** Wire `ben_voice.py` and `voice_gate.py` into `v4_generation.py` behind a flag (`VOICE_ENGINE=on`): brief call, draft call with paragraph roles and sentence kinds, existing fact gate, new voice gate, one retry, assembly from kept sentences. Keep the old writer as the flag-off path. *Acceptance:* unit tests for every deterministic rule; an end-to-end test on recorded fixtures; the accuracy audit still shows zero unsupported fact sentences.
- [ ] **7.4 Editor pass.** A scorecard call (0 to 5 on ten criteria); under 3.5 average triggers one rewrite that may rearrange and add voice but never add facts; re-gated. *Acceptance:* median scorecard at or above 3.5 on 20 stories.
- [ ] **7.5 LinkedIn derivative.** Post and first comment built only from kept sentences; hook under 210 characters. *Acceptance:* every sentence in a post exists in its source article's evidence file.
- [ ] **7.6 Preview and A/B.** Ten-story preview read by Ben; then two weeks of LinkedIn posts alternating old and new voice; compare impressions, saves, shares, comments from target accounts, inbound messages. *Acceptance:* a written read-out with a go or no-go.
- [ ] **7.7 Tune from evidence.** Adjust shapes, lenses, hook formulas and humour level from the A/B and from which takes the gate rejects most.

**Rollback:** the engine is behind a flag; turning it off restores the fact-only writer unchanged.

## 5. Target shape of the live path

```
Trigger (workflow, policy, lease)
  → sources/   ingest · index pages · source health · canonical item
  → events/    classify · cluster · intelligence object
  → gate/      content typing · eligibility · editorial memory
  → evidence/  retrieval · fact extraction
  → rank/      importance · selection   (all numbers read from config/)
  → write/     dossier · writer · claim verifier · readability     (fail-closed)
  → publish/   site_render · manifest · edition · validate · release
  → weekly/    wrap (same verifier, same publish path)
scripts/legacy/   v2 + v3 (frozen, with a deletion date)
satellites/       linkedin · pdf · carousel · ideas · buildings (own workflows)
```

Rules for the new shape: the live path imports nothing from `legacy/` or `satellites/`; every stage has one input type and one output type; every threshold lives in `config/`; no stage imports the renderer except `publish/`.

## 6. Decisions needed from you

| # | Decision | Our recommendation |
|---|---|---|
| D1 | Local `daily_news_agent.py` edit: finish the lock or revert | Finish it properly as part of 3.1, revert for now |
| D2 | Facts-only voice: also for LinkedIn and Ideas? | Yes, one style, one verifier |
| D3 | Archive policy: unpublish, annotate, regenerate, or leave | Triage first (1.1); regenerate the top-traffic flagged pages; annotate the unverifiable |
| D4 | Publish the verified subset when a few stories fail | Yes, with a warning and a review PR only above a failure threshold |
| D5 | Writer fallback to a second provider | Yes, bounded, with the same gate |
| D6 | When to delete legacy code | After 60 days of clean v4 runs |
| D7 | Display or drop `latest-edition.json` | Drop the unused fields, keep a deployment check |
| D8 | NewsAPI: implement or drop | Drop, unless coverage gaps appear |
| D9 | Reader-feedback loop: build or drop | Build only after Phase 1; start with scroll depth |
| D10 | Weekly wrap "why it matters" lines: keep (source-stated only) or remove | Keep; they only appear when the article itself says it |
| D11 | Voice engine: allow opinion `take` sentences under strict rules (guide decisions V1 to V6) | Yes, behind a flag, previewed before launch |

## 7. How we will work through it

1. **One phase per session.** Start with the checklist, finish with the checkpoint.
2. **Each item:** write the acceptance test first, make the change, run the full suite on a clean tree, run the accuracy audit if anything touched writing or publishing, then commit with the item id in the message (for example `1.3 store sector in manifest`).
3. **Keep a decision log** at the bottom of this file: date, decision, reason.
4. **Never mix themes in a commit,** and never push to `main` without a preview run for anything in the daily path.
5. **Update the system map** (`docs/system-map/data.js`, then `build.py`) in the same commit as any structural change, so the map stays true.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Refactor breaks the daily publish | Phase 3 moves code behind shims; the integration test (5.4) should land before the big moves, or run a preview before every merge |
| The fact gate withholds too many stories | Track the withheld rate in 5.1; tune quote length and chunk size before loosening any rule |
| Archive audit is slow or hits dead links | Tiered buckets; "cannot verify" is a legitimate outcome |
| Same-family checker blind spots | Phase 0.4, plus the weekly human spot check (5.2) |
| Config consolidation changes the slate silently | Snapshot the slate before and after 2.1 on the same day's data and diff it |

## 9. Success measures

- Zero unsupported sentences in a weekly 50-sentence random audit of new articles.
- Withheld rate under 25%; failed rate under 2%.
- All six Intelligence filters return results; every manifest entry has a sector.
- The live import graph contains no legacy module; the publish path does not import `daily_news_agent`.
- Every config key is read by live code (a test enforces it); every workflow produces something the live system uses.
- Root directory under 40 files; a new person can run a preview from the README alone.

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-10-09 | Plan written | Starting point |
