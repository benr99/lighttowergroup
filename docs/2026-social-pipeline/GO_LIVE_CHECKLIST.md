# Go Live Checklist

Do not commit, deploy, or post until these are checked.

## Repo Checks

- `git status --short --branch` reviewed.
- No secrets are tracked.
- `.venv/` is ignored.
- `carousel_pdfs/` is ignored.
- `scripts/.env` remains ignored.
- `publication-metadata.json` is intentionally volume 2.

## Pipeline Checks

```powershell
.venv\Scripts\python scripts\run_social_pipeline_2026.py --latest --dry-run --offline
.venv\Scripts\python scripts\run_pdf_carousel_pipeline.py --latest --offline --verbose
.venv\Scripts\python scripts\verify_carousel_agent.py
```

Required:

- No syntax errors.
- Offline mode shows deterministic fallback behavior.
- PDF generation succeeds.
- Carousel verifier passes.

## Content Review

For any AI-backed run, review before publishing:

- Every dollar amount.
- Every percentage.
- Every named party.
- Any sentence that sounds like a market-wide claim.
- Whether the carousel framing matches the article.
- Whether the LinkedIn caption mentions the attached carousel.

## Deploy Readiness

- Decide which untracked 2026 scripts/docs should be added.
- Review generated `git diff`.
- Commit only after the Downloads version is finalized and the useful features from the other version have been evaluated.
- Push/deploy only after explicit approval.

## Ideas Publishing Checks

```powershell
python -m py_compile scripts\ideas_daily_agent.py scripts\ideas_prompts.py scripts\ideas_quality.py scripts\ideas_renderer.py
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --dry-run --offline --no-ai --count 1 --force
.venv\Scripts\python.exe scripts\ideas_daily_agent.py --dry-run --no-ai --count 1 --max-feeds 6 --force
python -c "import xml.etree.ElementTree as ET, tomllib; ET.parse('sitemap.xml'); ET.parse('ideas/feed.xml'); tomllib.load(open('netlify.toml','rb')); print('xml_toml_ok')"
```

Required:

- `ideas.html` renders the approved launch Ideas article.
- `ideas/feed.xml` contains only approved public Ideas URLs.
- `sitemap.xml` contains only approved public Ideas URLs.
- Public Ideas files contain no placeholders, `noindex`, stale generated test articles, or secret-looking strings.
- Live AI failures are held under `data/ideas/held/`; they are not fallback-published.
- Scheduler starts in first-week mode: up to 3 Ideas articles/day from 20 feeds.
- Scheduler uses `scripts\run_ideas_daily.bat`, which calls `scripts\run_ideas_daily_deploy.ps1`.
- Daily deploy wrapper commits only public Ideas files and pushes `main` to trigger Netlify.
