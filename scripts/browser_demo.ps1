param([switch]$Normal)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath 'artifacts/runtime-browser-b/control/human.token')) { throw 'Prepare the dedicated browser runtime first; never replace the old runtime.' }
if (-not (Test-Path -LiteralPath 'artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe')) { throw 'The fixed browser tool is missing; see stage B TOOLING.md.' }
& docker compose -f compose.browser.yaml up -d control gateway
if ($LASTEXITCODE -ne 0) { throw 'Dedicated browser product could not start.' }
& 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tools/browser_prepare_profile.mjs artifacts/profile-browser-b-firefox
if ($LASTEXITCODE -ne 0) { throw 'Dedicated browser profile initialization failed.' }
& 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 tools/browser_profile_ca.py artifacts/profile-browser-b-firefox
if ($LASTEXITCODE -ne 0) { throw 'Application-only browser CA preparation failed; no TLS bypass.' }
if ($Normal) {
    & 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tools/browser_demo.mjs --normal
} else {
    & 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tools/browser_demo.mjs
}
exit $LASTEXITCODE
