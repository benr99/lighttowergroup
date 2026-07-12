$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$env:PYTHONDONTWRITEBYTECODE = "1"
& $Python -m py_compile scripts\content_governance.py scripts\content_maintenance.py scripts\editorial_voice.py scripts\enhanced_prompts.py scripts\linkedin_essay_agent.py scripts\linkedin_thread_agent.py scripts\carousel_script_agent.py scripts\carousel_script_agent_2026.py scripts\carousel_content_writer.py scripts\article_pdf_generator.py scripts\pdf_queue.py scripts\linkedin_pdf_post.py scripts\linkedin_pdf_scheduler.py scripts\source_health.py scripts\ideas_prompts.py scripts\ideas_quality.py scripts\ideas_daily_agent.py scripts\daily_news_agent.py
& $Python -m unittest discover -s tests -v
& $Python -c "import xml.etree.ElementTree as ET, tomllib; ET.parse('sitemap.xml'); ET.parse('feed.xml'); tomllib.load(open('netlify.toml','rb')); print('public_artifacts_ok')"

Write-Host "Light Tower quality checks passed."
