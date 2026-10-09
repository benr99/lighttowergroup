# Daily dress rehearsal for Light Tower Insights: a full preview day, nothing published.
# Writes to %USERPROFILE%\ltg-rehearsal\<date>\ (digest.html, health.txt, run files).
#
# To run it every weekday at 7:30 am, Ben runs this once in PowerShell (no admin needed):
#   $action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\rehearsal.ps1`""
#   $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 7:30am
#   Register-ScheduledTask -TaskName "LTG Insights Rehearsal" -Action $action -Trigger $trigger -Description "Preview-only Insights day; nothing is published"
# To stop it: Unregister-ScheduledTask -TaskName "LTG Insights Rehearsal" -Confirm:$false

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $env:USERPROFILE "ltg-rehearsal"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("rehearsal-" + (Get-Date -Format "yyyy-MM-dd") + ".log")

Push-Location $repo
try {
    python scripts\rehearsal.py @args *>&1 | Tee-Object -FilePath $log
}
finally {
    Pop-Location
}
