$runtimeScripts = "C:\Users\Ben\Downloads\Lighttowergroupsite\.agent-runtime\scripts"
if (-not (Test-Path (Join-Path $runtimeScripts "run_agent_runtime.bat"))) {
    throw "Isolated agent runtime is missing. Run setup_agent_runtime.ps1 first."
}
$action  = New-ScheduledTaskAction -Execute (Join-Path $runtimeScripts "run_agent_runtime.bat") -WorkingDirectory $runtimeScripts
$trigger = New-ScheduledTaskTrigger -Daily -At "07:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 4)
Register-ScheduledTask -TaskName "LTG Daily News Agent" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
Get-ScheduledTask -TaskName "LTG Daily News Agent" | Select-Object TaskName, State
Write-Host "Task registered: daily at 07:00, isolated runtime, IgnoreNew overlap protection, 4-hour limit."
