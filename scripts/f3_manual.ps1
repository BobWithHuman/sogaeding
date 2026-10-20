[CmdletBinding()]
param(
    [ValidateSet('prepare','connect','collect')][string]$Mode='prepare',
    [string]$SessionId,
    [string]$ConnectionId,
    [ValidateSet('normal','instruction-variant')][string]$Fixture='normal'
)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw 'Bundled python.exe is missing.' }
Set-Location -LiteralPath $projectRoot
$previousConsoleInput=[Console]::InputEncoding
$previousConsoleOutput=[Console]::OutputEncoding
$previousPipelineEncoding=$OutputEncoding
try {
[Console]::InputEncoding=New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$OutputEncoding=[Console]::OutputEncoding
if ($Mode -eq 'connect') {
    if (-not $SessionId) { throw 'Use the dashboard session ID with -SessionId.' }
    $secureToken=Read-Host 'Paste the dashboard agent token (hidden; never paste it in chat)' -AsSecureString
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    try {
        $agentToken=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $payload=@{agent_session_token=$agentToken} | ConvertTo-Json -Compress
        $payload | & $pythonPath -X utf8 tools/manual_cli.py connect $SessionId
        $code=$LASTEXITCODE
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $agentToken=$null; $payload=$null; $secureToken.Dispose()
    }
} elseif ($Mode -eq 'collect') {
    if (-not $ConnectionId) { throw 'Use the printed connection ID with -ConnectionId.' }
    & $pythonPath -X utf8 tools/manual_cli.py collect $ConnectionId
    $code=$LASTEXITCODE
} else {
    & $pythonPath -X utf8 tools/manual_cli.py prepare $Fixture
    $code=$LASTEXITCODE
}
} finally {
    [Console]::InputEncoding=$previousConsoleInput
    [Console]::OutputEncoding=$previousConsoleOutput
    $OutputEncoding=$previousPipelineEncoding
}
if ($code -ne 0) { throw 'Manual CLI helper stopped. No automatic model retry.' }
