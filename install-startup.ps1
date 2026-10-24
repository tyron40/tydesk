# Opt-in current-user startup. The TyDesk companion remains visible.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
$agent = Join-Path $PSScriptRoot 'agent.py'
if (!(Test-Path $python)) { throw 'Run start-agent.ps1 and pair this computer first.' }
if (!(Test-Path (Join-Path $env:LOCALAPPDATA 'TyDesk\enrollment.dat'))) { throw 'Enable Remember this device in the companion first.' }
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $agent + '" --autostart') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName 'TyDesk Remote Access Companion' -Description 'Visible, owner-enabled remote desktop companion. Remove with uninstall-startup.ps1.' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host 'TyDesk will reconnect at sign-in for this Windows user. Keep this project folder in place.'
