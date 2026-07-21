# Insights Agent Operations

## Scheduler: GitHub Actions (primary)

`.github/workflows/daily-insights-agent.yml` runs the agent daily at 07:07 America/New_York (cron is UTC; see the note in the workflow file about the DST shift) on GitHub's own runners. It checks out `main` fresh, installs `scripts/requirements.lock`, and runs `daily_news_agent.py --selection-mode bucketed-volume --no-limit` from a clean clone — so there's no local worktree to keep in sync and no dependency on any machine being powered on.

It needs three repository secrets set under Settings → Secrets and variables → Actions: `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `NEWSAPI_KEY` (the same values as `scripts/.env`). LinkedIn credentials are not needed here since the scheduled run doesn't pass `--auto-post-linkedin`. The workflow also needs "Read and write permissions" for the default `GITHUB_TOKEN` (Settings → Actions → General → Workflow permissions) so it can push the generated articles back to `main`. Trigger it manually anytime from the Actions tab (`workflow_dispatch`) to test without waiting for 7 AM.

Do not run this alongside the Windows Task Scheduler job below — both will try to publish and push around the same time and can race. Disable the Windows task once the GitHub Actions run has been verified.

## Scheduler: Windows Task Scheduler (legacy/backup)

Windows Task Scheduler starts `LTG Daily News Agent` at 7:00 AM local time. It runs from the isolated `.agent-runtime` Git worktree, not the editable development folder. The job uses bucketed-volume selection with no article cap: every non-duplicate story that clears its bucket's publication threshold is eligible to be written.

Before writing, the runtime verifies it is clean, fetches `origin/main`, fast-forwards when behind, and stops on a divergent history. If the previous run made a commit but could not push it, the next preflight attempts that recovery push before collecting new stories.

The current secret-free status is `.agent-runtime/tmp/agent_status.json`. The runtime log is `.agent-runtime/scripts/agent_run.log`; the per-run editorial record is `.agent-runtime/scripts/agent_log.json`. A failed push produces `deployment_failed` in the agent log, exits non-zero, and leaves the runtime status as `failed`; it never prints a successful completion.

Each source is retried every day. A feed with no entries is not quarantined. After seven consecutive empty runs it is marked `needs_review` in `.agent-runtime/tmp/source_health.json` so an operator can investigate its URL, but it remains eligible for future retrieval. Repeated source-specific exceptions can temporarily quarantine a source; a shared connectivity outage releases those quarantines.

To rebuild the isolated runtime and task configuration after a move or repair, run PowerShell as the task owner:

```powershell
& "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts\setup_agent_runtime.ps1"
& "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts\setup_scheduler.ps1"
```

The task allows a four-hour run and ignores overlapping starts. Do not edit `.agent-runtime` by hand; make code changes in the primary repository, deploy them to `main`, then let the runtime fast-forward safely.
