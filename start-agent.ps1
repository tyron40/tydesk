param([switch]$TerminalSetup, [switch]$RememberPairing, [switch]$AllSharing, [switch]$StartInTray, [switch]$Console)

$ErrorActionPreference = 'Stop'
if ($Console -and $StartInTray) { throw 'Choose Console or StartInTray, not both.' }
if ($RememberPairing -or $AllSharing -or $StartInTray -or $Console) { $TerminalSetup = $true }
if ($TerminalSetup) {
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Use a regular PowerShell window for ZDesk terminal setup.'
    }
}
Push-Location $PSScriptRoot
try {
    if (!(Test-Path .venv)) {
        py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($TerminalSetup) {
        $launchArgs = @('agent.py', '--terminal-setup')
        if ($RememberPairing) { $launchArgs += '--remember-pairing' }
        if ($AllSharing) { $launchArgs += '--all-sharing' }
        if ($StartInTray) { $launchArgs += '--start-in-tray' }
        if ($Console) { $launchArgs += '--console' }
        & .\.venv\Scripts\python.exe @launchArgs
    } else {
        & .\.venv\Scripts\python.exe agent.py
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
