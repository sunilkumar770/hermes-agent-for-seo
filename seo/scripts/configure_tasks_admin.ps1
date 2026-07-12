# GoRentls SEO Tasks - Configure for "Run whether user is logged on or not" + "Run with highest privileges"
# Run this script as Administrator (Right-click PowerShell -> Run as Administrator)

$ErrorActionPreference = "Stop"

# Prompt for password securely
$password = Read-Host -AsSecureString "Enter your Windows password for user 'sunil'"

$tasks = @(
    "GoRentls_Daily_SEO_Scan",
    "GoRentls_Weekly_Deep_SEO", 
    "GoRentls_Boot_SEO_Sync"
)

foreach ($taskName in $tasks) {
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        
        # Set to run whether user is logged on or not (Password logon type)
        $task.Principal.LogonType = "Password"
        # Set to run with highest privileges
        $task.Principal.RunLevel = "Highest"
        # Allow running on batteries
        $task.Settings.AllowStartIfOnBatteries = $true
        $task.Settings.DontStopIfGoingOnBatteries = $true
        $task.Settings.StartWhenAvailable = $true
        $task.Settings.RunOnlyIfNetworkAvailable = $true
        
        # Apply changes with credentials
        Set-ScheduledTask -InputObject $task -User "sunil" -Password $password
        
        Write-Host "✓ Updated: $taskName" -ForegroundColor Green
    }
    catch {
        Write-Error "✗ Failed to update $taskName: $_"
    }
}

Write-Host "`nDone! Verifying..."
Get-ScheduledTask -TaskName "GoRentls*" | Format-Table TaskName, State, @{Name='RunLevel'; Expression={$_.Principal.RunLevel}}, @{Name='LogonType'; Expression={$_.Principal.LogonType}}