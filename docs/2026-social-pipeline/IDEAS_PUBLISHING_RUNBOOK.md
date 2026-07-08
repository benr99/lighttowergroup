# Light Tower Ideas Publishing Runbook

The Ideas daily agent publishes essay-style articles to the public `/ideas/` section.

Main script:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py
```

## Product Difference

Insights explains CRE capital markets news.

Ideas explains what built-world events reveal about buildings, money, power, design, psychology, and culture.

## Safe Test Commands

Offline dry run:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --dry-run --offline --no-ai --count 2
```

Live RSS dry run without AI:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --dry-run --no-ai --count 1 --max-feeds 8
```

Live RSS dry run with AI:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --dry-run --count 1 --max-feeds 6 --force
```

Local publish test:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --publish --offline --no-ai --count 1 --force
```

Future daily target after reviewed first-week performance:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --publish --count 10 --max-feeds 40
```

First-week recommended production command:

```powershell
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --publish --count 3 --max-feeds 20
```

## What The Agent Does

1. Reads RSS stories from the existing source list.
2. Filters for Ideas candidates with place, capital, power, design, and psychology signals.
3. Scores candidates using the recovered Light Tower Ideas rubric.
4. Saves a private Daily Ten audit file under `data/ideas/internal/daily-ten/`.
5. Builds a research dossier for each selected story.
6. Generates a full Ideas essay.
7. Runs quality, fact, risk, SEO, placeholder, mojibake, and secret checks.
8. Publishes approved HTML pages to `ideas/*.html`.
9. Updates `ideas.html`.
10. Updates `ideas/feed.xml`.
11. Adds approved Ideas URLs to `sitemap.xml` and removes stale generated Ideas URLs.
12. Saves social draft packages under `data/ideas/social/`.

## Safety Rules

- No git commit.
- No git push.
- No LinkedIn posting.
- `--publish` is required to write public pages.
- Dry-run previews stay under `data/ideas/previews/`.
- Failed articles go to `data/ideas/held/`.
- Private artifacts remain under `data/ideas/`, which is ignored and blocked.
- Intentional `--offline --no-ai` runs may create fallback previews for testing.
- Live production AI failures are held for manual review; they are not silently fallback-published.

## Quality Gates

Publishing fails if an article has:

- placeholder text
- mojibake
- secret-looking tokens
- missing source URL
- missing title/subtitle/excerpt/meta description
- body below the minimum word count
- unsupported dollar or percentage figures
- quote attribution patterns requiring review
- site-visit language requiring review
- high-risk allegation language
- unsupported speculative or imagined-scene language
- name-wordplay essays built around branding details
- generic meta headings such as `A Resonant Ending`
- AI-generation failure fallback in live production mode
- low quality score
- high risk score
- missing SEO/schema markers in generated HTML
- `noindex` in a public page

## Files Produced

Public:

- `ideas/[slug].html`
- `ideas.html`
- `ideas/feed.xml`
- `sitemap.xml`

Private:

- `data/ideas/ideas.json`
- `data/ideas/published/[slug].json`
- `data/ideas/internal/dossiers/[slug].json`
- `data/ideas/internal/daily-ten/YYYY-MM-DD.json`
- `data/ideas/internal/logs/*.json`
- `data/ideas/social/[slug].json`

## Before Scheduling 10/Day

1. Run a live RSS dry run with `--no-ai`.
2. Run a live AI dry run for one article.
3. Review the preview HTML.
4. Publish one live article locally.
5. Visually inspect desktop and mobile.
6. Only then schedule `--publish --count 10`.

## Scheduling

Batch runner:

```powershell
scripts\run_ideas_daily.bat
```

Preview the Windows scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_ideas_daily.ps1
```

Register the Windows scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_ideas_daily.ps1 -Register
```

Default schedule:

- Task name: `Light Tower Ideas Daily`
- Time: `06:30`
- Command: `scripts\run_ideas_daily.bat`
- First-week behavior: publishes up to 3 Ideas articles/day from 20 feeds

To change the time:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_ideas_daily.ps1 -Register -RunAt "07:15"
```

## Removing A Bad Ideas Article

1. Delete the public page:

```powershell
Remove-Item ideas\[slug].html
```

2. Remove the entry from `data/ideas/ideas.json`.
3. Regenerate `ideas.html` and `ideas/feed.xml`.
4. Remove the URL from `sitemap.xml`.
5. Re-run XML validation:

```powershell
python -c "import xml.etree.ElementTree as ET; ET.parse('sitemap.xml'); ET.parse('ideas/feed.xml'); print('xml_ok')"
```

Do not remove source logs/dossiers until after review. They explain what happened.

## Rollback

Until auto-push is intentionally added, rollback is manual:

- remove the bad public `ideas/[slug].html`
- restore `ideas.html`, `ideas/feed.xml`, and `sitemap.xml`
- commit the correction
- push to Netlify

The Ideas agent does not currently commit or push.
