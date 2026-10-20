param([string]$EvidenceLabel)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
$env:WITH_HUMAN_BROWSER_RUNTIME='artifacts/runtime-f3-01'
$env:WITH_HUMAN_BROWSER_BASE_URL='https://127.0.0.1:8020'
$env:WITH_HUMAN_BROWSER_PROFILE='artifacts/profile-f3-demo'
$nodePath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$pythonPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $nodePath tools/browser_prepare_profile.mjs artifacts/profile-f3-demo
if ($LASTEXITCODE -ne 0) { throw 'Profile initialization failed.' }
& $pythonPath -X utf8 tools/browser_profile_ca.py artifacts/profile-f3-demo artifacts/runtime-f3-01/ca.pem
if ($LASTEXITCODE -ne 0) { throw 'Application CA trust failed. No TLS bypass.' }
if ($EvidenceLabel) { & $nodePath tools/f3_demo.mjs $EvidenceLabel }
else { & $nodePath tools/f3_demo.mjs }
exit $LASTEXITCODE
