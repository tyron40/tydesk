$ErrorActionPreference = 'Stop'
Unregister-ScheduledTask -TaskName 'TyDesk Remote Access Companion' -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'Sign-in startup removed. Close the companion to stop the current session; Forget saved enrollment to erase its credential.'
