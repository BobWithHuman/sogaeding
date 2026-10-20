param([string]$Label='browser-b-regression')
$ErrorActionPreference='Stop'
$env:WITH_HUMAN_BROWSER_RUNTIME='artifacts/runtime-f3-01'
$env:WITH_HUMAN_BROWSER_BASE_URL='https://127.0.0.1:8020'
$env:WITH_HUMAN_BROWSER_PROFILE='artifacts/profile-f3-01'
$env:WITH_HUMAN_BROWSER_COMPOSE='compose.f3.yaml'
$env:WITH_HUMAN_BROWSER_DRIVER='tools/f3_driver.py'
$env:WITH_HUMAN_BROWSER_EVIDENCE_ROOT='artifacts/20261014-f3-01'
& 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/web/browser_acceptance.mjs $Label
exit $LASTEXITCODE
