Set-Location $PSScriptRoot
if (!(Test-Path .venv)) { py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements-server.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$secure = Read-Host 'Choose server password (at least 16 characters)' -AsSecureString
$env:TYDESK_PASSWORD = [System.Net.NetworkCredential]::new('', $secure).Password
try { & .\.venv\Scripts\python.exe server.py } finally { Remove-Item Env:TYDESK_PASSWORD -ErrorAction SilentlyContinue }
