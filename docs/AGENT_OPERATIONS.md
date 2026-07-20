# Insights Agent Operations

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
