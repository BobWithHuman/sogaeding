<# User-run actual model verification. root agent never launches paid calls. #>
[CmdletBinding()]
param([switch]$IncludeActor)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
$nodePath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$pythonPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pwshPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
if ($IncludeActor -and -not (Test-Path -LiteralPath $pwshPath -PathType Leaf)) { throw 'Bundled pwsh.exe is missing. No model started.' }
$label='manual-real-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$runId='20261014-f3-01'
if (-not (Test-Path -LiteralPath artifacts/runtime-f3-01/control/judge.api-key)) {
    if (-not $env:OPENAI_API_KEY) { throw 'Prepare OPENAI_API_KEY on this host; do not paste its value into chat.' }
    [IO.File]::WriteAllText((Join-Path $projectRoot 'artifacts/runtime-f3-01/control/judge.api-key'),$env:OPENAI_API_KEY)
}
& ./tools/f3_evidence.ps1 -RunId $runId -Label ($label+'-restart') -Program docker -CommandArgs @('compose','-f','compose.f3.yaml','up','-d','control','gateway')
if ($LASTEXITCODE -ne 0) { throw 'Product startup failed.' }
& ./tools/f3_evidence.ps1 -RunId $runId -Label ($label+'-candidate-restart') -Program docker -CommandArgs @('compose','-f','compose.f3.yaml','restart','control','gateway')
if ($LASTEXITCODE -ne 0) { throw 'Product candidate restart failed.' }
& $nodePath tools/browser_prepare_profile.mjs artifacts/profile-f3-01
if ($LASTEXITCODE -ne 0) { throw 'Browser profile initialization failed.' }
& $pythonPath -X utf8 tools/browser_profile_ca.py artifacts/profile-f3-01 artifacts/runtime-f3-01/ca.pem
if ($LASTEXITCODE -ne 0) { throw 'Application-only CA trust failed. No TLS bypass.' }
& ./tools/f3_evidence.ps1 -RunId $runId -Label $label -Program $nodePath -CommandArgs @('tools/f3_browser.mjs',$label)
$judgeExit=$LASTEXITCODE
Write-Host ('Actual judge/browser evidence: artifacts/'+$runId+'/'+$label+'/cases.json and usage.json')
if ($judgeExit -ne 0) { throw 'Actual judge/browser verification has failures; stop and diagnose before actor. Original evidence retained.' }
if ($IncludeActor) {
    # Actor request literals are UTF-8; PS 7 reads them consistently from PS 5.1.
    & $pwshPath -NoProfile -File ./scripts/f3_actor_verify.ps1 -ParentLabel $label
    if ($LASTEXITCODE -ne 0) { throw 'Actor verification has failures; original evidence retained.' }
}
if ($judgeExit -ne 0) { throw 'Actual judge/browser verification has failures; original evidence retained.' }
Write-Host 'Inspect PASS/FAIL and actual effects. Fake tests and model accuracy remain separate.'
