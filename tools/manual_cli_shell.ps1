# Loaded only in the dedicated, allowlisted interactive child shell.
$ErrorActionPreference='Stop'
[Console]::InputEncoding = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding=[Console]::OutputEncoding
Set-Location -LiteralPath $env:WITH_HUMAN_MANUAL_WORKSPACE
function global:codex {
    if ($args.Count -gt 0) { throw 'Type codex alone; enter the request directly in the TUI.' }
    & $env:WITH_HUMAN_MANUAL_PYTHON -X utf8 $env:WITH_HUMAN_MANUAL_HELPER start $env:WITH_HUMAN_MANUAL_CONNECTION
    if ($LASTEXITCODE -ne 0) { Write-Host 'Stopped. Collect diagnostics; do not retry the model automatically.' }
}
function global:prompt { 'With Human manual> ' }
Write-Host 'Dedicated product shell ready. Type codex yourself. No model has been started.'
Write-Host 'Enter exactly the original dashboard request in Codex. Stop at the first analysis failure.'
Write-Host 'Each codex start consumes one of two actor episodes; 180 seconds maximum.'
Write-Host 'Type exit after Codex exits to return to your original terminal.'
