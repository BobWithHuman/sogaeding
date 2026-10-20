<# Separate trusted HUMAN terminal. Never passes a human credential to Codex/MCP. #>
param([switch]$Watch, [string]$PythonPath='', [ValidateSet('','behavior-v5-1')][string]$Revision='')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $PythonPath) {
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
$previousConsole=[Console]::OutputEncoding
$previousOutput=$OutputEncoding
try {
    [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
    $OutputEncoding=[Text.UTF8Encoding]::new($false)
    $arguments=@()
    if ($Watch) { $arguments+='--watch' }
    if ($Revision) { $arguments+=@('--host',(Join-Path $project 'artifacts/runtime-mvp-demo/revisions/behavior-v5-1/host')) }
    & $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_confirm.py') @arguments
    $nativeExit=$LASTEXITCODE
    if ($nativeExit -ne 0) { throw 'HUMAN_CONFIRM_FAILED; no automatic approval or retry.' }
} finally {
    [Console]::OutputEncoding=$previousConsole
    $OutputEncoding=$previousOutput
}
