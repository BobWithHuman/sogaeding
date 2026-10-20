# Tests the real Windows CLI preflight and launcher input guards without API calls.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$launcher = Join-Path $PSScriptRoot 'run_codex_live.ps1'
$nativeShell = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $nativeShell)) { $nativeShell = Join-Path $PSHOME 'pwsh.exe' }
$utf8 = New-Object Text.UTF8Encoding($false)
$errors = $null
[void][Management.Automation.Language.Parser]::ParseFile($launcher, [ref]$null, [ref]$errors)
if ($errors.Count -gt 0) { throw 'Launcher PowerShell parse failed.' }

function Quote-Argument([string]$Value) {
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
function Test-LauncherCase([string]$Name, [string[]]$Parameters, [string]$ExpectedFailure) {
    $startInfo = New-Object Diagnostics.ProcessStartInfo
    $startInfo.FileName = $nativeShell
    $cliArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $launcher) + $Parameters
    $startInfo.Arguments = (($cliArgs | ForEach-Object { Quote-Argument $_ }) -join ' ')
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = $utf8
    $startInfo.StandardErrorEncoding = $utf8
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        [void]$process.Start()
        $outTask = $process.StandardOutput.ReadToEndAsync()
        $errTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(30000)) { $process.Kill(); throw ($Name + ': timed out.') }
        $output = $outTask.GetAwaiter().GetResult() + $errTask.GetAwaiter().GetResult()
        if ($ExpectedFailure) {
            if ($process.ExitCode -eq 0 -or $output -notmatch [regex]::Escape($ExpectedFailure)) {
                throw ($Name + ': expected input guard did not reject.')
            }
        } elseif ($process.ExitCode -ne 0) { throw ($Name + ': real Codex preflight failed.') }
        return [pscustomobject]@{ name=$Name; exit_code=$process.ExitCode; result='PASS' }
    } finally { $process.Dispose() }
}
$rows = @()
. (Join-Path $PSScriptRoot 'codex_trial_output.ps1')
$sampleEvents = '{"type":"item.completed","item":{"type":"mcp_tool_call","text":"tool output is not a final answer"}}' + "`n" +
    '{"type":"item.completed","item":{"type":"agent_message","text":"Summary: test-human-token test-agent-token sk-fake_key_value WH_DEMO_SECRET_TEST"}}' + "`n" +
    '{"type":"turn.completed"}'
$safe = Get-SafeCodexTrialOutput $sampleEvents @('test-human-token', 'test-agent-token')
if ($safe.turn_status -ne 'COMPLETED' -or -not $safe.final_answer_available -or
    $safe.masked_final_answer -match 'test-human-token|test-agent-token|sk-fake|WH_DEMO_SECRET|tool output') {
    throw 'Final-answer extraction or credential masking failed.'
}
$failed = Get-SafeCodexTrialOutput '{"type":"turn.failed"}' @()
if ($failed.turn_status -ne 'FAILED' -or $failed.final_answer_available) { throw 'Failed turn was misclassified.' }
$longEvents = @{ type='item.completed'; item=@{type='agent_message'; text=('a' * 9000)} } | ConvertTo-Json -Compress
$limited = Get-SafeCodexTrialOutput $longEvents @()
if (-not $limited.final_answer_truncated -or $limited.masked_final_answer.Length -gt 8203) {
    throw 'Final answer length limit failed.'
}
$rows += [pscustomobject]@{ name='final_answer_masking_and_states'; exit_code=0; result='PASS' }
$probeRequest = "이슈 42를 요약해줘`n세 항목으로 작성해줘."
$rows += Test-LauncherCase 'unicode_multiline_dryrun' @('-DryRun', '-UserRequest', $probeRequest) ''
$artifactDir = Join-Path $projectRoot 'artifacts/codex-launcher'
$latest = Get-ChildItem -LiteralPath $artifactDir -Filter '*.json' -File |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
$record = Get-Content -LiteralPath $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$hasher = [Security.Cryptography.SHA256]::Create()
try {
    $expected = ([BitConverter]::ToString($hasher.ComputeHash($utf8.GetBytes($probeRequest)))).Replace('-', '').ToLowerInvariant()
} finally { $hasher.Dispose() }
if ($record.request_sha256 -ne $expected -or $record.initial_prompt_input_sha256 -ne $expected -or
    $record.live_result -ne 'NOT_RUN' -or $record.mode -ne 'DRY_RUN') {
    throw 'Unicode request binding or no-LIVE preflight evidence is incorrect.'
}
$rows += Test-LauncherCase 'missing_exact_comment' @('-DryRun', '-TaskKind', 'POST_COMMENT') 'POST_COMMENT requires'
$rows += Test-LauncherCase 'remote_control_rejected' @('-DryRun', '-ControlBaseUrl', 'http://example.com:8000') '127.0.0.1'
$rows += Test-LauncherCase 'remote_mcp_rejected' @('-DryRun', '-McpUrl', 'http://example.com:8001/mcp') '127.0.0.1'
$rows += Test-LauncherCase 'conflicting_modes' @('-Run', '-DryRun') 'Choose either'
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'src/app/control/main.py'))) {
    $rows += Test-LauncherCase 'live_requires_product' @('-Run', '-Model', 'test-model') 'Product app is not implemented'
}
$evidence = [ordered]@{
    scope='launcher_windows_checks'; created_at=[DateTime]::UtcNow.ToString('o')
    cases=$rows; product_tests='NOT_RUN'; live_api='NOT_RUN'
}
$evidencePath = Join-Path $artifactDir 'windows-checks.json'
[IO.File]::WriteAllText($evidencePath, ($evidence | ConvertTo-Json -Depth 6), $utf8)
Write-Host ('Launcher checks: ' + $rows.Count + ' PASS; no API calls. Evidence: ' + $evidencePath)
