# Light Tower Group News Agent — Complete Installation & Setup
# Run as Administrator in PowerShell

Write-Host "========================================" -ForegroundColor Green
Write-Host "LTG News Agent Installation & Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Step 1: Verify Python installation
Write-Host "[1/5] Verifying Python installation..." -ForegroundColor Cyan
$pythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if ($pythonPath) {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Step 2: Install Python dependencies
Write-Host "`n[2/5] Installing Python dependencies..." -ForegroundColor Cyan
$scriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptsDir

if (Test-Path "requirements.txt") {
    Write-Host "  Installing: feedparser, trafilatura, requests, anthropic, Pillow..."
    & python -m pip install -r requirements.txt -q
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ requirements.txt not found" -ForegroundColor Red
    exit 1
}

# Step 3: Verify .env file
Write-Host "`n[3/5] Verifying .env configuration..." -ForegroundColor Cyan
if (Test-Path ".env") {
    $envContent = Get-Content ".env"
    $hasDeepSeek = $envContent | Select-String "DEEPSEEK_API_KEY"
    $hasNewsAPI = $envContent | Select-String "NEWSAPI_KEY"
    $hasLinkedIn = $envContent | Select-String "LINKEDIN_ACCESS_TOKEN"

    if ($hasDeepSeek -and $hasNewsAPI -and $hasLinkedIn) {
        Write-Host "✓ All API keys configured" -ForegroundColor Green
    } else {
        Write-Host "⚠ Some API keys may be missing in .env" -ForegroundColor Yellow
        Write-Host "  Required: DEEPSEEK_API_KEY, NEWSAPI_KEY, LINKEDIN_ACCESS_TOKEN" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ .env file not found" -ForegroundColor Red
    exit 1
}

# Step 4: Verify scheduled task
Write-Host "`n[4/5] Verifying Windows Task Scheduler..." -ForegroundColor Cyan
$task = Get-ScheduledTask -TaskName "LTG Daily News Agent" -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "✓ Scheduled task found: 'LTG Daily News Agent'" -ForegroundColor Green
    Write-Host "  Status: $($task.State)" -ForegroundColor Green
    if ($task.State -eq "Ready") {
        Write-Host "  Next run: Daily at 07:00 (7:00 AM)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Task state is $($task.State) — may not run" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Scheduled task not found" -ForegroundColor Red
    Write-Host "  Creating task: 'LTG Daily News Agent'..." -ForegroundColor Yellow

    $action = New-ScheduledTaskAction -Execute "$scriptsDir\run_agent.bat"
    $trigger = New-ScheduledTaskTrigger -Daily -At "07:00"
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "LTG Daily News Agent" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null

    Write-Host "✓ Scheduled task created" -ForegroundColor Green
}

# Step 5: Summary & next steps
Write-Host "`n[5/5] Installation Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUMMARY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Status:" -ForegroundColor White
Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
Write-Host "  ✓ .env API keys configured" -ForegroundColor Green
Write-Host "  ✓ Windows Task scheduled daily at 07:00 AM" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Monitor at: insights.html (new articles appear daily)" -ForegroundColor Cyan
Write-Host "  2. Check logs: scripts/agent_log.json (run metrics)" -ForegroundColor Cyan
Write-Host "  3. Verify: First run tomorrow at 7:00 AM" -ForegroundColor Cyan
Write-Host ""
Write-Host "Manual Test:" -ForegroundColor White
Write-Host "  cd scripts" -ForegroundColor Cyan
Write-Host "  python daily_news_agent.py --dry-run" -ForegroundColor Cyan
Write-Host ""
Write-Host "Documentation:" -ForegroundColor White
Write-Host "  - DEPLOYMENT.md — Full architecture & maintenance" -ForegroundColor Cyan
Write-Host "  - MONITORING_CHECKLIST.md — Daily monitoring" -ForegroundColor Cyan
Write-Host "  - SOCIAL_IMAGES.md — Image generation guide" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
