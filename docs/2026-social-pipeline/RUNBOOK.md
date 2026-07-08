# Runbook

Run these commands from the repo root:

```powershell
cd C:\Users\Ben\Downloads\Lighttowergroupsite
```

## Offline Tests

Use these first. They do not call external AI.

```powershell
.venv\Scripts\python scripts\run_social_pipeline_2026.py --latest --dry-run --offline
.venv\Scripts\python scripts\run_pdf_carousel_pipeline.py --latest --offline --verbose
.venv\Scripts\python scripts\verify_carousel_agent.py
```

Expected result:

- Strategy uses `method: heuristic`.
- Thread output uses `fallback: true`.
- Carousel output uses `fallback: true`.
- PDF is created under `carousel_pdfs/`.
- `verify_carousel_agent.py` prints `carousel agent verification passed`.

## AI-Backed Runs

Run these only when it is acceptable to send article content to the configured AI provider:

```powershell
.venv\Scripts\python scripts\run_social_pipeline_2026.py --latest --dry-run
.venv\Scripts\python scripts\run_pdf_carousel_pipeline.py --latest --verbose
```

Before publishing any AI-generated text, review it for:

- Unsupported dollar amounts or percentages.
- Claims that are not in the article.
- Framing that contradicts the article.
- Tone that sounds too promotional, too certain, or too generic.

The 2026 carousel agent now rejects unsupported dollar and percentage figures, but narrative judgment still needs review.

## Output Files

- `social_pipeline_output.json`: Saved social pipeline history when not using dry run.
- `linkedin_thread_queue.json`: Saved thread packages.
- `carousel_pdfs/`: Generated PDF files. This folder is ignored by Git.

## Dependency Notes

Dependencies are installed into `.venv/`, which is ignored by Git.

The important packages are:

- `requests` for model/API calls.
- `beautifulsoup4` and related parsers for HTML/text extraction.
- `Pillow` for preview/image work.
- `fpdf2` and `pypdf` for PDF generation and validation.
- `feedparser` and `trafilatura` for the broader article/news workflow.

