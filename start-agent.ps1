param([switch]$TerminalSetup)

$ErrorActionPreference = 'Stop'
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
        & .\.venv\Scripts\python.exe agent.py --terminal-setup
    } else {
        & .\.venv\Scripts\python.exe agent.py
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
