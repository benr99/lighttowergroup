> **ON HOLD (2026-10-09).** Ben paused go-live until the system is smooth end to end. This prompt becomes backlog item 8. See `../ZOOM_OUT_PLAN.md`.

# Iteration 02: Go live, supervised                                     Milestone: M1   Plan items: 0.4–0.7

## Why now
The gated writer is proven locally on live feeds (46 kept sentences, 0 unsupported) but production still publishes with the old writer every morning, which the audit found states unsupported things in 14 of 16 articles. Every day of delay adds pages to the archive we will later have to triage. Nothing in M2–M6 should build on a writer that is not yet in production.

## Ground truth (verified, see STATE.md and LOG.md)
- Branch `codex/phase-0-accurate-writer`: five commits on `origin/main`, 502 tests pass on a clean tree, not pushed.
- `quality.yml` runs automatically on pushes to `codex/**`, so pushing the branch runs CI.
- Today is Friday 2026-10-09. `weekly-wrap.yml` is scheduled for 16:30 ET Fridays in **publish** mode. If the branch merges before 19:00 ET today, the first wrap publishes unsupervised tonight.
- A full production day selects about 26 stories (live preview), and writing takes about 2 minutes per story with 6 in parallel, so the 45-minute window has room. Withheld stories do not block a day; one failed or skipped story does (flag F16).
- `workflow_dispatch` needs a workflow file on the default branch, so `weekly-wrap.yml` cannot be dispatched until merged.

## Objective
The gated writer and Friday wrap run in production from `main`, after a full-slate preview on GitHub that Ben has read, with the first scheduled wrap held to preview until Ben says otherwise.

## Scope
In:
- **Wrap safety switch (build first).** Scheduled wrap runs publish only when the repository variable `WEEKLY_WRAP_PUBLISH` is `true`; otherwise a scheduled run is a preview. Manual dispatch is unchanged.
- **Evidence digest.** `outputs/readability/evidence_digest.py` turns a run's `v4-evidence/` into one readable HTML page: each article's sentences beside their quotes and source links, plus everything the gate deleted and why. This is what Ben reads instead of raw JSON.
- After Ben's yes: push the branch; confirm CI is green; open a PR to `main` whose body summarises the evidence.
- Dispatch the daily workflow on the branch: `pipeline=v4`, `mode=preview`, `article_count=70`. Download the artifact; run `audit_preview.py` and the digest on it.
- After Ben reads the digest and says go: merge; leave the cron to publish the next morning (or dispatch `mode=publish` on `main` if Ben prefers today).
- Verify the first production run: the deployment check passes, and every published sentence in that run appears in an evidence file.
- Update STATE, LOG, the plan's checkboxes and the map; write Iteration 03.

Out:
- Spend cap, filters, partial-day publishing (Iterations 3 and 4).
- Fixing eligibility for administrative notices (F17) or the degenerate measures (F18), beyond recording them.
- Merging any of Ben's work in progress.

## Steps
1. Build the wrap safety switch in `weekly-wrap.yml` and the evidence digest; add tests for the digest; commit `0.6a` on the branch; re-run the verification standard.
2. **Stop and ask Ben** for: push and PR (with the digest from the local preview attached).
3. `git push -u origin codex/phase-0-accurate-writer`; watch `quality.yml`.
4. `gh pr create --base main --head codex/phase-0-accurate-writer`, with a body covering evidence, the five commits, the safety switch, and how to roll back.
5. `gh workflow run daily-insights-agent.yml --ref codex/phase-0-accurate-writer -f mode=preview -f pipeline=v4 -f article_count=70`; wait; `gh run download` the artifact.
6. Run `audit_preview.py` and `evidence_digest.py` on the artifact's `.editorial-state/`; send Ben the digest.
7. **Stop and ask Ben** to read the digest and approve the merge, choosing between "publish tomorrow at 07:07" and "publish now".
8. Merge (squash off; keep the individual commits). If "now": `gh workflow run daily-insights-agent.yml -f mode=publish -f pipeline=v4 -f article_count=70`.
9. After the first production run: `gh run view` for the deployment check; compare the published pages' sentences against the run's evidence files.
10. Record and direct the next iteration.

## Acceptance criteria
- CI green on the branch; the PR exists and links the evidence.
- GitHub full-slate preview: the run completes; 0 failed; the withheld count and reasons are listed; audit of all kept fact sentences finds **0 unsupported**; total writing time under 30 minutes.
- Ben has read the digest and approved, recorded in LOG.md with the date.
- `main` contains the branch commits (0.3a–0.3e, the session record, 0.6a). A scheduled wrap without `WEEKLY_WRAP_PUBLISH=true` produced a preview, not a page.
- First production run: deployment verification passed; 100% of published body sentences found in that run's evidence files.

## Stop conditions
- CI fails on the branch for a reason not caused by this work: stop and report.
- The GitHub preview has any failed story (which would route a real day to review): stop; decide whether to pull partial-day publishing (1.5) forward.
- The audit flags any kept fact sentence that is not an audit artifact: stop; no merge.
- Any sign the old writer is still being used after merge: stop and roll back.

## Needs Ben
1. **Push the branch, open the PR, run a GitHub preview?** Recommendation: yes. Default if unanswered: nothing is pushed.
2. **D12: add OpenAI credit** so the second fact-check pass is a different model family? Recommendation: yes, about $20 covers months. Default: both passes stay on DeepSeek, which is proven but less independent.
3. **D13: the two Windows tasks on this PC.** Recommendation: disable "LTG Daily News Agent" (it only exits now); keep "Light Tower Ideas Daily" until it has its own review. Default: leave both.

## Budget
Model spend under $3 (one full-slate GitHub preview of about 26 stories plus the audit). The preview takes about 15 to 25 minutes; Ben's reading time about 15 minutes.

## Report
CI result, PR link, preview numbers (selected, completed, withheld with reasons, failed, minutes), audit result, the digest link, Ben's decision, and (after the merge) the first production run's verification.
