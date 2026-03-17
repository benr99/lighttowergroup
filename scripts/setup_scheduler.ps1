$action  = New-ScheduledTaskAction -Execute "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts\run_agent.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At "07:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "LTG Daily News Agent" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
Write-Host "Task registered. Verify with: Get-ScheduledTask -TaskName 'LTG Daily News Agent'"
