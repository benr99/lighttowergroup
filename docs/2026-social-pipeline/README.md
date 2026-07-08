# 2026 Social Pipeline

This folder is the working documentation for the Light Tower Group 2026 LinkedIn and carousel workflow.

The archived files in `archive/` are preserved for context, but they should not be treated as the source of truth. Some of them were implementation notes, some used optimistic "complete" language, and some contain encoding artifacts from an earlier export.

## Current Source Of Truth

- `README.md`: What the system is and what is safe to use.
- `RUNBOOK.md`: How to run the pipeline, including offline/no-AI tests.
- `VOICE_GUIDE.md`: The writing standard for thread and carousel output.
- `GO_LIVE_CHECKLIST.md`: Review checklist before commit, deploy, or posting.
- `ARCHIVE_INDEX.md`: What the archived docs contain.

## Active Scripts

- `scripts/run_social_pipeline_2026.py`: Runs strategy, thread, and carousel schema generation.
- `scripts/run_pdf_carousel_pipeline.py`: Generates a LinkedIn-ready carousel PDF.
- `scripts/social_strategy_selector.py`: Chooses the likely best format.
- `scripts/linkedin_thread_agent.py`: Creates LinkedIn thread packages.
- `scripts/carousel_script_agent_2026.py`: Creates the 2026 carousel schema.
- `scripts/carousel_content_writer.py`: Creates PDF slide copy and has a deterministic offline fallback.
- `scripts/pdf_carousel_generator.py`: Renders PDF carousel content.

## Safety Rules

Use `--offline` or `--no-ai` when testing structure, dependencies, PDF generation, and article extraction. This mode intentionally avoids external AI calls.

Only run AI-backed generation when you are intentionally ready to send article content to the configured model provider.

Generated PDFs belong in `carousel_pdfs/`, which is ignored by Git.

The current publication tracker is `publication-metadata.json` and is intentionally kept at volume 2.

