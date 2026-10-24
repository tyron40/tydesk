# Run from the extracted project in VS Code. Requires Git and GitHub CLI.
# Publishes a NEW PRIVATE source repository; never uploads enrollment or server data.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Install GitHub CLI: winget install --id GitHub.cli -e, then restart VS Code.' }
if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git: winget install --id Git.Git -e, then restart VS Code.' }
gh auth status
if ($LASTEXITCODE -ne 0) { gh auth login; if ($LASTEXITCODE -ne 0) { throw 'GitHub sign-in failed.' } }
if (Test-Path .git) { throw 'This folder already has Git metadata. Review it before creating a new repository.' }
git init -b main
if ($LASTEXITCODE -ne 0) { throw 'Git initialization failed.' }
git add .
git commit -m 'Add TyDesk Windows companion and persistent relay server'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed. Set your Git name and email and retry manually.' }
gh repo create tydesk --private --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'Repository creation/push failed. Review the error above; no repository will be overwritten.' }
gh repo view --json url --jq .url
Write-Host 'Source pushed. Tell ChatGPT the repository URL so Render deployment can continue.'
