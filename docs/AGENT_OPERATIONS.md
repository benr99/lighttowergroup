# Curated Insights operations

The production publisher is `.github/workflows/daily-insights-agent.yml`. It is
the only scheduler authorized by `.editorial-state/scheduler.json`.

The legacy Windows task may remain registered as a recovery mechanism, but
`scripts/agent_runtime.py` reads the scheduler lease before doing any Git or
editorial work. While the lease belongs to `github-actions`, the local task
exits successfully without publishing. This prevents duplicate same-day runs.

## Schedule

GitHub Actions triggers at both `11:07` and `12:07` UTC. A New York local-time
guard permits only the trigger that maps to `07:07 America/New_York`. This
handles EDT and EST without manual cron changes.

The workflow may also be started manually from the Actions tab.

## Required GitHub configuration

Repository secrets:

- `DEEPSEEK_API_KEY`: editorial-room planning, writing, revision, and social copy.
- `NEWSAPI_KEY`: supplemental discovery, including Culture of Capital queries.

Workflow permissions must permit contents and pull-request writes.

Anthropic is not used by the Insights workflow.

## Required Netlify configuration

- `RESEND_API_KEY`: newsletter contacts and reader-feedback email.
- `RESEND_SEGMENT_ID`: Resend segment receiving edition subscribers.
- `RESEND_AUDIENCE_ID`: optional backward-compatible alias for the segment ID.
- `NOTIFY_EMAIL`: reader-feedback destination; defaults to `ben@lighttowergroup.co`.
- `FROM_EMAIL`: verified Resend sender; defaults to `noreply@lighttowergroup.co`.
- `EDITORIAL_FEEDBACK_WEBHOOK_URL`: optional durable feedback sink.
- `EDITORIAL_FEEDBACK_WEBHOOK_TOKEN`: optional bearer token for that sink.

If neither the webhook nor Resend is configured, the feedback endpoint returns
an explicit service-unavailable response. It never pretends to save a response.

## Production sequence

1. Verify the current repository and test suite.
2. Gather RSS, federal, NewsAPI, and watchlist discovery.
3. Cluster headlines into distinct events.
4. Score must-read value and build a scarce edition.
5. Fetch every independent source in each selected event.
6. Build a source/claim dossier.
7. Let the assigning editor and skeptic kill, defer, shorten, or assign format.
8. Generate and independently validate the writing.
9. Render articles, edition JSON, social assets, RSS, and sitemap.
10. Validate generated artifacts.
11. Upload the audit artifact and GitHub run summary.
12. Resolve publication:
    - supported routine briefs may publish to `main`;
    - flagships, Culture of Capital pieces, thin evidence, and borderline
      must-read scores publish to a review branch and open a pull request.

Netlify production deployment begins only after the same validation suite has
passed. Review pull requests receive a Netlify Deploy Preview when the
repository's normal Netlify Git integration is active.

## Durable state

Tracked operating state lives in `.editorial-state/` and is blocked from public
web access by `netlify.toml`.

- `scheduler.json`: single-scheduler lease.
- `audience-signals.json`: bounded learning weights.
- `discovery-watchlist.json`: editable culture and original-reporting radar.
- `source-health.json`: feed reliability across cloud runs.
- `event-memory.json`: event IDs and past decisions.
- `runs/YYYY-MM-DD.json`: compact selection, dossier, and decision audit.
- `publication-decision.json`: auto-publish versus editorial-review decision.
- `generated-files.json`: exact safe allowlist for the publish commit.
- `run-summary.md`: human-readable Actions summary and pull-request body.

Retrieved article bodies and captured quotations are excluded from durable Git
history. The audit retains source URLs, evidence counts, reported-fact controls,
reporting gaps, decisions, and scores.

GitHub Actions also uploads state and edition output as a 30-day artifact.

## Public edition files

- `latest-edition.json`: current public edition.
- `editions/YYYY-MM-DD.json`: immutable historical edition.
- `insights.json`: article archive manifest.
- `feed.xml`: RSS and Google News-compatible feed.
- `sitemap.xml`: site index.

An edition can contain no article. `no_publishable_story` is a successful,
intentional outcome.

## Manual validation

From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\validate_publication.py
node --check edition.js
node --check netlify\functions\newsletter-subscribe.js
node --check netlify\functions\editorial-feedback.js
```

Run a no-write editorial simulation:

```powershell
.\.venv\Scripts\python.exe scripts\daily_news_agent.py `
  --selection-mode edition `
  --articles 4 `
  --dry-run `
  --run-origin manual
```

Run selection only:

```powershell
.\.venv\Scripts\python.exe scripts\daily_news_agent.py `
  --selection-mode edition `
  --articles 4 `
  --shadow `
  --run-origin manual
```

## Review checklist

Before merging an editorial-review pull request:

- Confirm the event is new relative to linked archive matches.
- Open every source URL.
- Verify quotes, numbers, parties, dates, and causality.
- Read the skeptic objections and reporting gaps.
- Confirm the headline does not overstate one transaction as a market.
- Confirm any physical or human detail appears in a cited source.
- Read aloud for repeated abstractions or generated rhythm.
- Confirm the article deserves its assigned format.
- Prefer shortening or killing to repairing weak source material with prose.

## Switching back to the local scheduler

Only change `.editorial-state/scheduler.json` to
`"active_scheduler": "local-scheduler"` after disabling the GitHub schedule or
otherwise ensuring it cannot publish. Never authorize both.

The local runtime uses curated edition mode and no longer supports unlimited
bucketed publication.
