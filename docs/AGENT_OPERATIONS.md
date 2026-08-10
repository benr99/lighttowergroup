# Insights Generator v3 operations

This is the production runbook for Light Tower Insights. The active scheduler is
`.github/workflows/daily-insights-agent.yml`; the active engine is
`scripts/insights_v3.py`. The older v2 engine remains available only as an
explicit manual rollback choice in the workflow.

## Production contract

- Publish at approximately 07:07 New York time every day.
- Target three publishable articles; never publish more than five.
- Never fill the slate below the global quality floor merely to hit volume.
- Long-form treatment requires at least three independent sources and two
  usable full texts. Thinner evidence is shortened to analysis or a brief.
- A draft that fails financial, editorial, source, or deterministic fact review
  is withheld. A cleared subset may still publish.
- `shadow` cannot generate or publish. `preview` can generate drafts but cannot
  alter public files. Only `publish` can build a release package.
- Public writes are limited to the generated-files allowlist.
- A main-branch release is not successful until the live edition and every new
  article are reachable and match the local release.

## Schedule and workflow

GitHub Actions registers `11:07` and `12:07` UTC schedules. The schedule-policy
guard permits only the trigger that maps to 07:07 in `America/New_York`, so one
run occurs through both daylight and standard time. Scheduled runs use
`mode=publish`, `pipeline=v3`, a daily target of three, and a five-candidate
ceiling.

Manual workflow inputs:

- `mode`: `shadow`, `preview`, or `publish`;
- `article_count`: `1`, `3`, or `5`;
- `pipeline`: `v3` by default, or `v2` for emergency rollback.

The workflow validates the committed baseline, checks the provider, builds the
edition, validates it again, uploads a 30-day evidence artifact, publishes only
the allowlist, and verifies the live deployment. Work held by editorial gates
remains in the artifact; it is not silently forced into the public edition.

## Required repository configuration

Repository secrets:

- `DEEPSEEK_API_KEY` — primary classification, writing, and review provider;
- `OPENAI_API_KEY` — per-call alternate provider;
- `NEWSAPI_KEY` — optional supplemental discovery.

Actions workflow permissions must be `read and write`. Enable **Allow GitHub
Actions to create and approve pull requests** so an operator-selected review
release can open its pull request. The workflow itself declares:

```yaml
permissions:
  contents: write
  pull-requests: write
```

Netlify must continue deploying `main` to `https://lighttowergroup.co`.

## Pipeline stages

1. Fetch active RSS/Atom sources and lawful index-page replacements.
2. Normalize titles, repair encoding, and classify sectors.
3. Cluster duplicate coverage into one intelligence object.
4. Reject marketing, digests, administrative notices, consumer/lifestyle
   housing, and items without a real beat anchor.
5. Compare against durable editorial memory and the published archive.
6. Retrieve article text and transfer actual source authority and evidence.
7. Score importance and build sector scouting slates.
8. Choose one bounded global slate: target three, maximum five, floor 40.
9. Build a dossier whose retrieved source text is the writer's factual boundary.
10. Draft in parallel at the maximum depth the evidence supports.
11. Run financial review, editorial review, deterministic fact verification,
    revision when needed, and post-revision re-review.
12. Render cleared pages, social images, related metadata, `insights.json`, RSS,
    sitemap, edition documents, run audit, decision, and deployment manifest.
13. Commit and push only the generated allowlist.
14. Poll the live edition and every new article for up to ten minutes.
15. If verification fails, revert only when local `HEAD` and `origin/main` still
    equal the exact failed release; otherwise stop without touching newer work.

## Provider behavior

DeepSeek is preferred. Each provider gets two bounded transport attempts. If
the primary still fails, that individual call switches to OpenAI; the rest of
the article does not become permanently pinned to the fallback. A syntactically
invalid JSON contract receives one separate bounded retry. Two invalid
contracts fail closed.

Secret-free diagnostics record provider, model, outcome, attempts, latency,
token counts when available, fallback use, and switches. Prompts, API keys, and
authorization headers are never logged. The provider log compacts after 512 KB.

## Evidence and fact controls

The writer and reviewers receive the same dossier window. Every public source
URL must be an exact dossier URL. The deterministic audit checks monetary
amounts, known institutions, addresses, key brief numbers, and unsupported
claim phrases. Equivalent representations such as `$1,567 million` and
`$1.567 billion` compare in base dollars, while genuinely different magnitudes
remain a hold.

Review-required draft artifacts include the exact stage decisions, scores,
issues, summaries, and errors without duplicating full articles inside every
stage record.

## Durable and retained state

Tracked operating state lives in `.editorial-state/` and is denied from public
web access by `netlify.toml`.

- `editorial-memory.json`: observed and published event memory;
- `spend-ledger.json`: shared daily spend history, retained for 60 days;
- `provider-log.jsonl`: compact secret-free provider diagnostics;
- `source-health.json`: measured feed health and quarantine state;
- `runs/YYYY-MM-DD.json`: compact daily audit record;
- `publication-decision.json`: automatic-publication decision;
- `generated-files.json`: exact release allowlist;
- `run-summary.md`: human-readable Actions summary.

Large candidate, slate, run, and draft diagnostics are ignored by Git and kept
in the workflow artifact. Retrieved article bodies are not added to durable Git
history. An operator-supplied `--state-dir` redirects memory, spend, artifacts,
and provider diagnostics together, which keeps canaries and tests isolated.

## Spend and runtime limits

`config/thresholds.json` supplies the default `$25` daily LLM ceiling and
per-article ceiling. All runs on the same UTC date share the durable spend
ledger. `LTG_MAX_DAILY_USD` may lower or raise the daily ceiling for an operator
run without editing the repository. Budget refusal is a normal shorter-edition
outcome and is reported explicitly.

The workflow job has a 120-minute ceiling. Generation is concurrent and each
individual result is isolated, so one failed article does not discard cleared
work.

## Local commands

Run from the repository root with the repository virtual environment.

Full validation:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile scripts\*.py
python -m unittest discover -s tests -v
python scripts\validate_publication.py
npm.cmd run check:js
npm.cmd run test:js
```

Selection-only canary:

```powershell
python scripts\insights_v3.py --mode shadow `
  --daily-target 3 --article-limit 5 --quality-floor 40 --workers 3 `
  --state-dir .editorial-state\canary\shadow
```

Real no-public-write canary:

```powershell
python scripts\insights_v3.py --mode preview `
  --daily-target 3 --article-limit 3 --quality-floor 40 --workers 3 `
  --state-dir .editorial-state\canary\preview
```

Do not use `--include-review` in automation. It is a deliberate manual override
for a human who has inspected the exact held drafts and sources.

## Reading a run

Start with `.editorial-state/v3-run.json` or the isolated run directory.

Healthy production-equivalent indicators:

- `daily_target_met: true` when at least three candidates cleared selection;
- `generation.written` near three, with every hold explained in `results`;
- `provider.successful_calls` greater than zero and provider failures visible;
- `spend.exhausted: false` unless an intentional ceiling stopped work;
- `publication.failed: 0`;
- publication decision `auto_publish_allowed: true` before main publication;
- live verification reports the expected edition and article count.

`no_publishable_story` is safe but not a healthy volume result. Investigate
selection, retrieval, and holds before the next schedule.

## Troubleshooting

### Feed outage or zero documents

Check `source-health.json` and the ingestion line in the run report. A broad
network/DNS failure is not evidence that 170 feeds broke simultaneously. Retry
with confirmed outbound access. Do not lower relevance gates in response to a
transport outage.

### Fewer than three publication candidates

Inspect `v3-candidates.json`, `v3-slates.json`, eligibility reasons, score
distribution, and the runner-up. Confirm the input supply is real before
changing the floor. Never promote digests, administrative notices, marketing,
consumer housing, or unrelated finance to fill the number.

### Draft held for review

Read `v3-drafts.json` and the draft's `diagnostics` in this order:

1. post-revision fact verification;
2. post-revision financial review;
3. post-revision editorial review;
4. provider/JSON errors;
5. original reviews and revision result.

Fix false equivalence, dossier truncation, or contract parsing in code. Do not
convert a failed gate to a pass merely to meet the target.

### Provider failure

Inspect `provider-log.jsonl` and the run's provider summary. If DeepSeek failed
and OpenAI succeeded, the system operated as designed. If both failed, confirm
both secrets and provider status. A provider preflight failure stops generation
before public files are changed.

### Review pull request fails to open

Verify the repository setting allowing Actions to create pull requests. The
`contents: write` and `pull-requests: write` declarations alone are not enough.
The generated review branch and artifact remain recoverable even if PR creation
fails.

### Live verification fails

Check Netlify build/deploy status and request
`latest-edition.json?release=<sha>`. The workflow automatically invokes the
safe rollback script only if nobody has advanced `main`. If `main` moved, the
script refuses to revert and requires an operator to inspect the newer state.

## Emergency rollback

Preferred rollback is the workflow input `pipeline=v2`, which leaves v3 code in
place while running the previous production engine. Use it only while a v3
incident is being diagnosed.

For an exact failed publication commit, the workflow uses:

```powershell
python scripts\rollback_release.py --expected-sha <failed-release-sha>
```

This command is intentionally strict: it refuses unless local `HEAD` and
`origin/main` both still equal that exact SHA. It creates a normal revert commit
and verifies the remote push; it never force-pushes or resets history.

## Release acceptance checklist

- Full Python and JavaScript suites pass.
- A real preview writes three cleared articles with no public changes.
- Workflow syntax and manual v3 path are present; v2 rollback remains present.
- Required Actions permissions and secrets are configured.
- The cutover commit reaches `main` through a reviewed branch/PR.
- A manual `mode=publish`, `pipeline=v3` run completes.
- `latest-edition.json` and every new article verify on the live domain.
- A second production-equivalent run completes without duplication, state loss,
  unbounded spend, or unexplained holds.
