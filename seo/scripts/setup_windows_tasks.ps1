# GoRentls SEO Automation - Windows Task Scheduler Setup
# Run this script as Administrator

$ErrorActionPreference = "Stop"

# Check for admin privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges. Please run PowerShell as Administrator."
    exit 1
}

# Find python path
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    $PythonPath = "C:\Users\sunil\AppData\Local\Programs\Python\Python313\python.exe"
}

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

Write-Host "Using Python path: $PythonPath"
Write-Host "Script Directory: $ScriptDir"

# Verify paths exist
if (-not (Test-Path $PythonPath)) {
    Write-Error "Python not found at: $PythonPath"
    exit 1
}

# 1. Daily Scan Task at 9:00 AM
$ActionDaily = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --full" -WorkingDirectory $ScriptDir
$TriggerDaily = New-ScheduledTaskTrigger -Daily -At 9:00AM
$SettingsDaily = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "GoRentls_Daily_SEO_Scan" -Action $ActionDaily -Trigger $TriggerDaily -Settings $SettingsDaily -Description "Daily GoRentls SEO rank tracking and competitor crawl pipeline" -Force

# 2. Weekly Deep SEO Monday at 8:00 AM
$ActionWeekly = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --full" -WorkingDirectory $ScriptDir
$TriggerWeekly = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:00AM
$SettingsWeekly = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "GoRentls_Weekly_Deep_SEO" -Action $ActionWeekly -Trigger $TriggerWeekly -Settings $SettingsWeekly -Description "Weekly GoRentls deep SEO audit and optimization draft" -Force

# 3. Boot Logon Sync Task
$ActionLogon = New-ScheduledTaskAction -Execute $PythonPath -Argument "seo_coordinator.py --scan-only" -WorkingDirectory $ScriptDir
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
$SettingsLogon = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "GoRentls_Boot_SEO_Sync" -Action $ActionLogon -Trigger $TriggerLogon -Settings $SettingsLogon -Description "At logon GoRentls SEO position sync" -Force

Write-Host "--------------------------------------------------------"
Write-Host "Successfully registered all 3 Scheduled Tasks in Windows!"
Write-Host "--------------------------------------------------------"
Get-ScheduledTask -TaskName "GoRentls*" | Format-Table TaskName, State
