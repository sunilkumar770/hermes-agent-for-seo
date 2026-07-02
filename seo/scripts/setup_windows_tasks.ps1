# Find python path
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    $PythonPath = "C:\Users\sunil\AppData\Local\Programs\Python\Python313\python.exe"
}

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = "C:\Users\sunil\OneDrive\Desktop\hermes agent for SEO\seo\scripts"
}

Write-Host "Using Python path: $PythonPath"
Write-Host "Script Directory: $ScriptDir"

# 1. Daily Scan Task at 9:00 AM
$ActionDaily = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --full" -WorkingDirectory $ScriptDir
$TriggerDaily = New-ScheduledTaskTrigger -Daily -At 9:00AM
Register-ScheduledTask -TaskName "GoRentls_Daily_SEO_Scan" -Action $ActionDaily -Trigger $TriggerDaily -Description "Daily GoRentls SEO rank tracking and competitor crawl pipeline" -Force

# 2. Weekly Deep SEO Monday at 8:00 AM
$ActionWeekly = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --full" -WorkingDirectory $ScriptDir
$TriggerWeekly = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:00AM
Register-ScheduledTask -TaskName "GoRentls_Weekly_Deep_SEO" -Action $ActionWeekly -Trigger $TriggerWeekly -Description "Weekly GoRentls deep SEO audit and optimization draft" -Force

# 3. Boot Logon Sync Task
$ActionLogon = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --scan-only" -WorkingDirectory $ScriptDir
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "GoRentls_Boot_SEO_Sync" -Action $ActionLogon -Trigger $TriggerLogon -Description "At logon GoRentls SEO position sync" -Force

Write-Host "--------------------------------------------------------"
Write-Host "Successfully registered all 3 Scheduled Tasks in Windows!"
Write-Host "--------------------------------------------------------"
Get-ScheduledTask -TaskName "GoRentls*" | Format-Table TaskName, State
