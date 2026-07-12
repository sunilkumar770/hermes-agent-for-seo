# GoRentls SEO Automation - Master Windows Task Scheduler Setup & Configuration
# Run this script as Administrator (Right-click PowerShell -> Run as Administrator)

$ErrorActionPreference = "Stop"

# 1. Check for Admin privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges. Please run PowerShell as Administrator."
    exit 1
}

# 2. Get current username (without domain/machine prefix if local)
$Username = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($Username -like "*\*") {
    $Username = $Username.Split("\")[1]
}

Write-Host "--------------------------------------------------------"
Write-Host "Configuring GoRentls SEO Tasks for User: $Username"
Write-Host "--------------------------------------------------------"

# 3. Prompt for password securely and convert to plain text
$passwordSecure = Read-Host -AsSecureString "Enter Windows password for user '$Username' (required for background tasks)"
if (-not $passwordSecure) {
    Write-Error "Password cannot be empty."
    exit 1
}
$Password = [System.Net.NetworkCredential]::new("", $passwordSecure).Password

# 4. Determine Python Path (prioritize global python with dependencies)
$PythonPath = "C:\Users\sunil\AppData\Local\Programs\Python\Python313\python.exe"
if (-not (Test-Path $PythonPath)) {
    $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    Write-Error "Python executable not found. Please verify python path."
    exit 1
}

# 5. Define Working Directory
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $ScriptDir) {
    $ScriptDir = "C:\Users\sunil\OneDrive\Desktop\hermes agent for SEO\seo\scripts"
}

Write-Host "Using Python Path: $PythonPath"
Write-Host "Using Working Directory: $ScriptDir"
Write-Host "--------------------------------------------------------"

# Task list to create
$TaskDefs = @(
    @{
        Name = "GoRentls_Daily_SEO_Scan"
        Desc = "Daily GoRentls SEO rank tracking and competitor crawl pipeline"
        Args = "seo_coordinator.py --full"
        Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
        Limit = New-TimeSpan -Minutes 30
    },
    @{
        Name = "GoRentls_Weekly_Deep_SEO"
        Desc = "Weekly GoRentls deep SEO audit and optimization draft"
        Args = "seo_coordinator.py --full"
        Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:00AM
        Limit = New-TimeSpan -Hours 1
    },
    @{
        Name = "GoRentls_Boot_SEO_Sync"
        Desc = "At logon GoRentls SEO position sync"
        Args = "seo_coordinator.py --scan-only"
        Trigger = New-ScheduledTaskTrigger -AtLogOn
        Limit = $null
    }
)

foreach ($taskDef in $TaskDefs) {
    $name = $taskDef.Name
    Write-Host "Processing task: $name..."

    try {
        # Create action
        $action = New-ScheduledTaskAction -Execute $PythonPath -Argument $taskDef.Args -WorkingDirectory $ScriptDir

        # Create settings
        if ($taskDef.Limit) {
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit $taskDef.Limit -RunOnlyIfNetworkAvailable
        } else {
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
        }

        # Create Principal (Run whether logged on or not + Highest Privileges)
        $principal = New-ScheduledTaskPrincipal -UserId $Username -LogonType Password -RunLevel Highest

        # Create Task Definition object
        $task = New-ScheduledTask -Action $action -Trigger $taskDef.Trigger -Settings $settings -Principal $principal

        # Register Task with Password
        Register-ScheduledTask -TaskName $name -InputObject $task -User $Username -Password $Password -Force | Out-Null
        
        Write-Host "✓ Successfully registered and configured: $name" -ForegroundColor Green
    }
    catch {
        Write-Error "✗ Failed to register task $name: $_"
    }
}

Write-Host "--------------------------------------------------------"
Write-Host "Verification of Registered GoRentls Tasks:"
Write-Host "--------------------------------------------------------"
Get-ScheduledTask -TaskName "GoRentls*" | Format-Table TaskName, State, @{Name='RunLevel'; Expression={$_.Principal.RunLevel}}, @{Name='LogonType'; Expression={$_.Principal.LogonType}}
