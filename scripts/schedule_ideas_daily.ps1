param(
  [string]$TaskName = "Light Tower Ideas Daily",
  [string]$RunAt = "06:30",
  [switch]$Register
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runner = Join-Path $PSScriptRoot "run_ideas_daily.bat"

if (-not (Test-Path $Runner)) {
  throw "Missing runner: $Runner"
}

if ($Register) {
  $Action = New-ScheduledTaskAction -Execute $Runner -WorkingDirectory $RepoRoot
  $Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
  $Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

  Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Publishes Light Tower Ideas articles using scripts\ideas_daily_agent.py" `
    -Force | Out-Null

  Write-Host "Registered scheduled task: $TaskName at $RunAt"
} else {
  Write-Host "Preview only. To register:"
  Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\schedule_ideas_daily.ps1 -Register"
  Write-Host ""
  Write-Host "Task name: $TaskName"
  Write-Host "Run time:  $RunAt"
  Write-Host "Runner:    $Runner"
}
