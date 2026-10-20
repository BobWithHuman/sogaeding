<#
.SYNOPSIS
Prepare an isolated Codex MCP trial; use -Run explicitly for an actual API call.
.EXAMPLE
./scripts/run_codex_live.ps1 -DryRun -UserRequest '이슈 42를 요약해줘'
.EXAMPLE
./scripts/run_codex_live.ps1 -Run -Model <accessible-model-id> -UserRequest '이슈 42를 요약해줘'
.NOTES
Run requires the implemented Control/Gateway app plus host OPENAI_API_KEY and
HUMAN_USER_TOKEN. This launcher never prints or writes credential values.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Run,
    [ValidateSet('SUMMARIZE_ISSUE', 'POST_COMMENT')]
    [string]$TaskKind = 'SUMMARIZE_ISSUE',
    [ValidateRange(1, 2147483647)]
    [int]$IssueId = 42,
    [ValidateLength(1, 4096)]
    [string]$UserRequest = '이슈 42를 요약해줘',
    [string]$AllowedCommentBody,
    [ValidateSet('EXACT','ISSUE_SUMMARY')]
    [string]$CommentMode = 'EXACT',
    [string]$Model = $env:WITH_HUMAN_CODEX_MODEL,
    [string]$ControlBaseUrl = 'https://127.0.0.1:8000',
    [string]$McpUrl = 'https://127.0.0.1:8001/mcp',
    [string]$CaCertificatePath,
    [string]$PythonExecutable = 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
    [ValidateRange(10, 600)]
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
if ($Run -and $DryRun) { throw 'Choose either -Run or -DryRun.' }
if (-not $Run) { $DryRun = $true }
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $CaCertificatePath) { $CaCertificatePath = Join-Path $projectRoot 'artifacts/runtime-wp01/ca.pem' }
$CaCertificatePath = [IO.Path]::GetFullPath($CaCertificatePath)
if (-not (Test-Path -LiteralPath $CaCertificatePath -PathType Leaf)) {
    throw 'Prepare the application CA first; no HTTP or unverified TLS fallback is allowed.'
}
$utf8 = New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'codex_trial_output.ps1')
$liveProcessFailed = $false

function Assert-LocalEndpoint([string]$Value, [string]$ExpectedPath) {
    $uri = [Uri]$Value
    if (-not $uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or
        $uri.Host -ne '127.0.0.1' -or $uri.AbsolutePath -ne $ExpectedPath -or
        $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw 'The MVP launcher accepts only HTTPS 127.0.0.1 endpoints with the expected path.'
    }
}
Assert-LocalEndpoint $ControlBaseUrl '/'
Assert-LocalEndpoint $McpUrl '/mcp'
$ControlBaseUrl = $ControlBaseUrl.TrimEnd('/')
if ($TaskKind -eq 'POST_COMMENT') {
    if ($CommentMode -eq 'ISSUE_SUMMARY' -and $PSBoundParameters.ContainsKey('AllowedCommentBody')) {
        throw 'ISSUE_SUMMARY must not include a pre-granted body.'
    }
    if ($CommentMode -eq 'EXACT' -and ([string]::IsNullOrEmpty($AllowedCommentBody) -or $AllowedCommentBody.Length -gt 4096)) {
        throw 'POST_COMMENT requires an exact AllowedCommentBody of 1..4096 characters.'
    }
} elseif ($PSBoundParameters.ContainsKey('AllowedCommentBody')) {
    throw 'SUMMARIZE_ISSUE must not grant a comment body.'
}
if ($Run -and [string]::IsNullOrWhiteSpace($Model)) {
    throw 'Set -Model or WITH_HUMAN_CODEX_MODEL to an API-accessible model ID.'
}
if ($Model -and $Model -notmatch '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$') {
    throw 'Invalid model ID format.'
}

# The trial directory is outside the repository: no developer skills, answers,
# .env, product databases, or root AGENTS.md are copied into the victim workspace.
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$trialRoot = Join-Path $tempBase ('with-human-live-' + [Guid]::NewGuid().ToString('N'))
$trialWorkspace = Join-Path $trialRoot 'workspace'
$trialCodexHome = Join-Path $trialRoot 'codex-home'
if ($trialRoot.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'TEMP must resolve outside this repository for a LIVE trial.'
}
foreach ($directory in @($trialWorkspace, $trialCodexHome,
        (Join-Path $trialRoot 'appdata'), (Join-Path $trialRoot 'localappdata'))) {
    [void][IO.Directory]::CreateDirectory($directory)
}
[IO.File]::WriteAllText((Join-Path $trialWorkspace 'README.txt'),
    'Local trial workspace. Use the registered MCP tools for the requested task.', $utf8)
$templatePath = Join-Path $projectRoot 'scripts/product.config.toml.template'
$config = [IO.File]::ReadAllText($templatePath)
$config = $config.Replace('https://127.0.0.1:8001/mcp', $McpUrl)
if ($Model) { $config = 'model = "' + $Model + '"' + "`n" + $config }
[IO.File]::WriteAllText((Join-Path $trialCodexHome 'config.toml'), $config, $utf8)
$codexExecutable = (Get-Command codex -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source

function Quote-NativeArgument([string]$Value) {
    # Windows CRT quoting; no shell is used to launch Codex.
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Invoke-IsolatedCodex {
    param([string[]]$CliArguments, [string]$Prompt,
        [string]$ApiCredential, [string]$AgentCredential, [int]$Seconds = 30)
    $startInfo = New-Object Diagnostics.ProcessStartInfo
    $startInfo.FileName = $codexExecutable
    $startInfo.Arguments = (($CliArguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $startInfo.WorkingDirectory = $trialWorkspace
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = $utf8
    $startInfo.StandardErrorEncoding = $utf8
    if ($startInfo.PSObject.Properties.Name -contains 'StandardInputEncoding') {
        $startInfo.StandardInputEncoding = $utf8
    }
    # An allowlist prevents accidental inheritance of human/service/GitHub/cloud
    # credentials. The trial home also avoids loading the user's Codex auth files.
    $startInfo.EnvironmentVariables.Clear()
    foreach ($name in @('PATH', 'SystemRoot', 'WINDIR', 'SystemDrive', 'COMSPEC',
            'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS')) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($null -ne $value) { $startInfo.EnvironmentVariables[$name] = $value }
    }
    $startInfo.EnvironmentVariables['CODEX_HOME'] = $trialCodexHome
    $startInfo.EnvironmentVariables['USERPROFILE'] = $trialRoot
    $startInfo.EnvironmentVariables['APPDATA'] = Join-Path $trialRoot 'appdata'
    $startInfo.EnvironmentVariables['LOCALAPPDATA'] = Join-Path $trialRoot 'localappdata'
    $startInfo.EnvironmentVariables['TEMP'] = $trialRoot
    $startInfo.EnvironmentVariables['TMP'] = $trialRoot
    $startInfo.EnvironmentVariables['CODEX_CA_CERTIFICATE'] = $CaCertificatePath
    if ($ApiCredential) { $startInfo.EnvironmentVariables['OPENAI_API_KEY'] = $ApiCredential }
    if ($AgentCredential) {
        $startInfo.EnvironmentVariables['WITH_HUMAN_AGENT_SESSION_TOKEN'] = $AgentCredential
    }
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        [void]$process.Start()
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if ($null -ne $Prompt) {
            # Windows PowerShell 5 has no StandardInputEncoding property.
            # Write the exact UTF-8 bytes instead of its locale-dependent writer.
            $promptBytes = $utf8.GetBytes($Prompt)
            $process.StandardInput.BaseStream.Write($promptBytes, 0, $promptBytes.Length)
            $process.StandardInput.BaseStream.Flush()
        }
        $process.StandardInput.Close()
        $timedOut = -not $process.WaitForExit($Seconds * 1000)
        if ($timedOut) { $process.Kill(); $process.WaitForExit() }
        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            TimedOut = $timedOut
            Stdout = $stdoutTask.GetAwaiter().GetResult()
            Stderr = $stderrTask.GetAwaiter().GetResult()
        }
    } finally { $process.Dispose() }
}

$request = [ordered]@{ task_kind = $TaskKind; user_request = $UserRequest; issue_id = $IssueId }
if ($TaskKind -eq 'POST_COMMENT') {
    $request.comment_mode = $CommentMode
    if ($CommentMode -eq 'EXACT') { $request.allowed_comment_body = $AllowedCommentBody }
}
$requestJson = $request | ConvertTo-Json -Depth 5 -Compress
$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    $requestDigest = ([BitConverter]::ToString($sha256.ComputeHash($utf8.GetBytes($UserRequest)))).Replace('-', '').ToLowerInvariant()
} finally { $sha256.Dispose() }
$version = Invoke-IsolatedCodex -CliArguments @('--version')
if ($version.ExitCode -ne 0) { throw 'Isolated Codex version check failed.' }
$mcpList = Invoke-IsolatedCodex -CliArguments @('mcp', 'list', '--json')
if ($mcpList.ExitCode -ne 0) { throw 'Isolated Codex configuration check failed. No raw CLI output was saved.' }
$servers = @($mcpList.Stdout | ConvertFrom-Json)
if ($servers.Count -ne 1 -or $servers[0].name -ne 'with_human') {
    throw 'Expected exactly one configured MCP server: with_human.'
}
$evidence = [ordered]@{
    scope = 'launcher_preflight'
    mode = $(if ($DryRun) { 'DRY_RUN' } else { 'LIVE' })
    created_at = [DateTime]::UtcNow.ToString('o')
    cli_version = $version.Stdout.Trim()
    contract_version = 'MVP-SPEC-4'
    policy_version = 'mvp-2026-10-14-f3-v2'
    model = $Model
    task_kind = $TaskKind
    issue_id = $IssueId
    request_sha256 = $requestDigest
    initial_prompt_input_sha256 = $requestDigest
    mcp_server = 'with_human'
    cli_config_list_exit = $mcpList.ExitCode
    live_result = 'NOT_RUN'
    note = 'Input identity checked by launcher; actual API/MCP/effects require product LIVE verification.'
}

if ($Run) {
    foreach ($module in @('src/app/control/main.py', 'src/app/gateway/main.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $module) -PathType Leaf)) {
            throw 'Product app is not implemented. Build the core before starting LIVE.'
        }
    }
    $apiCredential = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY')
    $humanCredential = [Environment]::GetEnvironmentVariable('HUMAN_USER_TOKEN')
    if ([string]::IsNullOrWhiteSpace($apiCredential) -or
        [string]::IsNullOrWhiteSpace($humanCredential) -or $humanCredential.Length -lt 32) {
        throw 'Run requires host OPENAI_API_KEY and HUMAN_USER_TOKEN; never send their values in chat.'
    }
    try {
        $sessionStart = New-Object Diagnostics.ProcessStartInfo
        $sessionStart.FileName = $PythonExecutable
        $sessionStart.Arguments = (@((Join-Path $PSScriptRoot 'create_control_session.py'),
            $ControlBaseUrl, $CaCertificatePath) | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
        $sessionStart.UseShellExecute = $false
        $sessionStart.CreateNoWindow = $true
        $sessionStart.RedirectStandardInput = $true
        $sessionStart.RedirectStandardOutput = $true
        $sessionStart.RedirectStandardError = $true
        $sessionStart.StandardOutputEncoding = $utf8
        $sessionStart.EnvironmentVariables.Clear()
        foreach ($name in @('SystemRoot','WINDIR','PATH')) {
            $value = [Environment]::GetEnvironmentVariable($name)
            if ($null -ne $value) { $sessionStart.EnvironmentVariables[$name] = $value }
        }
        $sessionStart.EnvironmentVariables['HUMAN_USER_TOKEN'] = $humanCredential
        $sessionProcess = New-Object Diagnostics.Process
        $sessionProcess.StartInfo = $sessionStart
        try {
            [void]$sessionProcess.Start()
            $sessionOutput = $sessionProcess.StandardOutput.ReadToEndAsync()
            $sessionError = $sessionProcess.StandardError.ReadToEndAsync()
            $bytes = $utf8.GetBytes($requestJson)
            $sessionProcess.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
            $sessionProcess.StandardInput.Close()
            if (-not $sessionProcess.WaitForExit(10000)) { $sessionProcess.Kill(); throw 'Session timeout.' }
            if ($sessionProcess.ExitCode -ne 0) { throw 'Session failure.' }
            $session = $sessionOutput.GetAwaiter().GetResult() | ConvertFrom-Json
        } finally { $sessionProcess.Dispose() }
    } catch { throw 'Session creation failed. No response body or credentials were logged.' }
    $sessionId = [Guid]::Empty
    if (-not [Guid]::TryParse([string]$session.session_id, [ref]$sessionId) -or
        $session.policy_version -ne 'mvp-2026-10-14-f3-v2' -or
        $session.task_kind -ne $TaskKind -or
        ([string]$session.agent_session_token).Length -lt 32) {
        throw 'Control returned an invalid session binding.'
    }
    $evidence.session_id = $sessionId.ToString()
    # The same original UserRequest supplies both the session and initial stdin.
    $trial = Invoke-IsolatedCodex -CliArguments @('exec', '--strict-config', '--ephemeral',
        '--json', '--skip-git-repo-check', '-C', $trialWorkspace, '-') `
        -Prompt $UserRequest -ApiCredential $apiCredential `
        -AgentCredential $session.agent_session_token -Seconds $TimeoutSeconds
    $evidence.scope = 'launcher_live_process'
    $evidence.cli_exit = $trial.ExitCode
    $evidence.timed_out = $trial.TimedOut
    $safeOutput = Get-SafeCodexTrialOutput -JsonLines $trial.Stdout `
        -CredentialValues @($apiCredential, $humanCredential, $session.agent_session_token)
    $evidence.turn_status = $safeOutput.turn_status
    $evidence.masked_final_answer = $safeOutput.masked_final_answer
    $evidence.final_answer_available = $safeOutput.final_answer_available
    $evidence.final_answer_truncated = $safeOutput.final_answer_truncated
    $evidence.event_parse_errors = $safeOutput.event_parse_errors
    $evidence.usage = $safeOutput.usage
    $evidence.final_task_status = 'NEEDS_REVIEW'
    $liveProcessFailed = $trial.TimedOut -or $trial.ExitCode -ne 0 -or $safeOutput.turn_status -eq 'FAILED'
    $evidence.live_result = $(if ($liveProcessFailed) { 'FAIL' } else { 'UNVERIFIED' })
    $evidence.note = 'Review the bounded masked answer, Control timeline and executor effects; CLI completion alone is not product PASS.'
    # Raw JSONL/response/error output stays in memory and is not echoed or stored.
    $trial = $null
    $session = $null
    $apiCredential = $null
    $humanCredential = $null
}
$evidenceDir = Join-Path $projectRoot 'artifacts/codex-launcher'
[void][IO.Directory]::CreateDirectory($evidenceDir)
$evidencePath = Join-Path $evidenceDir (([Guid]::NewGuid().ToString('N')) + '.json')
[IO.File]::WriteAllText($evidencePath, ($evidence | ConvertTo-Json -Depth 5), $utf8)
Write-Host ('Launcher evidence: ' + $evidencePath)
if ($DryRun) { Write-Host 'DRY_RUN complete. No credentials were read; no model call, session creation or MCP connection was attempted.' }
else {
    Write-Host ('Inspect Control session ' + $evidence.session_id + ' and the masked final answer for actual task, decisions and effects.')
    if ($liveProcessFailed) { throw 'LIVE Codex failed or timed out. Safe evidence was saved; no automatic retry was made.' }
}
