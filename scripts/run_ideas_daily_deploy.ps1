param(
  [int]$Count = 3,
  [int]$MaxFeeds = 20
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

Write-Host "Running Light Tower Ideas publisher..."
& $Python "scripts\ideas_daily_agent.py" --publish --count $Count --max-feeds $MaxFeeds
if ($LASTEXITCODE -ne 0) {
  throw "Ideas publisher failed with exit code $LASTEXITCODE"
}

Write-Host "Validating public Ideas artifacts..."
& $Python -c "import xml.etree.ElementTree as ET, tomllib; ET.parse('sitemap.xml'); ET.parse('ideas/feed.xml'); tomllib.load(open('netlify.toml','rb')); print('xml_toml_ok')"
if ($LASTEXITCODE -ne 0) {
  throw "Public artifact validation failed"
}

$publicScan = & rg -n "noindex|Essay body to be generated|Excerpt to be generated|DEEPSEEK_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY|Bearer " ideas.html ideas sitemap.xml netlify.toml site.css
if ($LASTEXITCODE -eq 0) {
  Write-Host $publicScan
  throw "Public artifact scan found blocked text"
}
if ($LASTEXITCODE -gt 1) {
  throw "Public artifact scan failed with exit code $LASTEXITCODE"
}

$changes = & git status --short ideas ideas.html sitemap.xml
if (-not $changes) {
  Write-Host "No public Ideas changes to deploy."
  exit 0
}

Write-Host "Deploying public Ideas changes..."
git add ideas ideas.html sitemap.xml
$today = Get-Date -Format "yyyy-MM-dd"
git commit -m "Publish Light Tower Ideas daily articles $today"
git push origin main

Write-Host "Light Tower Ideas daily deployment complete."
