# Reuses the actual launcher process helpers with a local Python executable.
# No Codex/model/MCP request or real credential lookup is performed.
# The default Python path is this PC's Codex bundled runtime. To find another
# bundled path, use Codex load_workspace_dependencies and pass its python.exe
# as -PythonExecutable. Any working Python needs only its standard library.
[CmdletBinding()]
param(
    [string]$PythonExecutable = 'C:\Users\qkaeh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [switch]$FakeParentWorker
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$launcherPath = Join-Path $PSScriptRoot 'run_codex_live.ps1'
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw 'Set -PythonExecutable to an available local Python interpreter.'
}
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($launcherPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Launcher PowerShell parse failed.' }
foreach ($functionName in @('Quote-NativeArgument', 'Invoke-IsolatedCodex')) {
    $functionAst = $ast.Find({
        param($node)
        $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $functionName
    }, $true)
    if (-not $functionAst) { throw ('Missing real launcher function: ' + $functionName) }
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}

# A separate parent process carries explicit fake human/service credentials.
# This proves their removal even when the calling user's environment has none,
# and does not replace or inspect any credential in the caller's environment.
if (-not $FakeParentWorker) {
    $parentInfo = New-Object Diagnostics.ProcessStartInfo
    $parentInfo.FileName = Join-Path $PSHOME $(if ($PSVersionTable.PSEdition -eq 'Desktop') { 'powershell.exe' } else { 'pwsh.exe' })
    $parentArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath,
        '-FakeParentWorker', '-PythonExecutable', $PythonExecutable)
    $parentInfo.Arguments = (($parentArgs | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $parentInfo.UseShellExecute = $false
    $parentInfo.CreateNoWindow = $true
    $parentInfo.RedirectStandardOutput = $true
    $parentInfo.RedirectStandardError = $true
    $parentInfo.EnvironmentVariables.Clear()
    foreach ($safeName in @('PATH', 'SystemRoot', 'WINDIR', 'SystemDrive', 'COMSPEC',
            'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'TEMP', 'TMP')) {
        $safeValue = [Environment]::GetEnvironmentVariable($safeName)
        if ($null -ne $safeValue) { $parentInfo.EnvironmentVariables[$safeName] = $safeValue }
    }
    $parentInfo.EnvironmentVariables['WITH_HUMAN_STDIN_FAKE_PARENT'] = '1'
    $parentInfo.EnvironmentVariables['HUMAN_USER_TOKEN'] = 'review-fake-human-not-forwarded'
    $parentInfo.EnvironmentVariables['GATEWAY_SERVICE_TOKEN'] = 'review-fake-service-not-forwarded'
    $parentProcess = New-Object Diagnostics.Process
    $parentProcess.StartInfo = $parentInfo
    try {
        [void]$parentProcess.Start()
        $parentOut = $parentProcess.StandardOutput.ReadToEndAsync()
        $parentErr = $parentProcess.StandardError.ReadToEndAsync()
        if (-not $parentProcess.WaitForExit(20000)) { $parentProcess.Kill(); throw 'Fake-parent stdin check timed out.' }
        $safeOut = $parentOut.GetAwaiter().GetResult()
        $safeErr = $parentErr.GetAwaiter().GetResult()
        if ($parentProcess.ExitCode -ne 0) { throw 'Fake-parent stdin check failed. No raw process output retained.' }
        Write-Host $safeOut.Trim()
    } finally { $parentProcess.Dispose() }
    return
}
if ([Environment]::GetEnvironmentVariable('WITH_HUMAN_STDIN_FAKE_PARENT') -ne '1') {
    throw 'Internal worker requires the controlled fake-parent process.'
}
if ([Environment]::GetEnvironmentVariable('HUMAN_USER_TOKEN') -ne 'review-fake-human-not-forwarded' -or
    [Environment]::GetEnvironmentVariable('GATEWAY_SERVICE_TOKEN') -ne 'review-fake-service-not-forwarded') {
    throw 'Controlled fake role credentials are missing.'
}

# These are the helper's captured variables. The controlled child is Python,
# not Codex. Runtime files contain no prompt, role token, or API credentials.
$utf8 = New-Object Text.UTF8Encoding($false)
$codexExecutable = [IO.Path]::GetFullPath($PythonExecutable)
$trialRoot = Join-Path $projectRoot ('tmp/stdin-check-' + [Guid]::NewGuid().ToString('N'))
$trialWorkspace = Join-Path $trialRoot 'workspace'
$trialCodexHome = Join-Path $trialRoot 'codex-home'
foreach ($directory in @($trialWorkspace, $trialCodexHome,
        (Join-Path $trialRoot 'appdata'), (Join-Path $trialRoot 'localappdata'))) {
    [void][IO.Directory]::CreateDirectory($directory)
}

# Codepoints avoid the test source's file encoding deciding the Korean input.
$prompt = -join (@(51060, 49800, 32, 52, 50, 47484, 32, 50836, 50557, 54644, 51480) |
    ForEach-Object { [char]$_ })
$prompt += ' "quoted" & ; line1' + "`n" + 'line2'
$pythonProbe = 'import os,sys,json; p=sys.stdin.buffer.read(); print(json.dumps({"stdin_hex":p.hex(),"human_present":"HUMAN_USER_TOKEN" in os.environ,"service_present":"GATEWAY_SERVICE_TOKEN" in os.environ,"fake_api":os.environ.get("OPENAI_API_KEY")=="review-fake-api","fake_session":os.environ.get("WITH_HUMAN_AGENT_SESSION_TOKEN")=="review-fake-session"}))'
$normal = Invoke-IsolatedCodex -CliArguments @('-c', $pythonProbe) -Prompt $prompt `
    -ApiCredential 'review-fake-api' -AgentCredential 'review-fake-session'
if ($normal.ExitCode -ne 0 -or $normal.TimedOut) { throw 'Controlled Python stdin probe failed.' }
$received = $normal.Stdout | ConvertFrom-Json -ErrorAction Stop
$expectedHex = ([BitConverter]::ToString($utf8.GetBytes($prompt))).Replace('-', '').ToLowerInvariant()
if ($received.stdin_hex -cne $expectedHex -or $received.human_present -or $received.service_present -or
    -not $received.fake_api -or -not $received.fake_session) {
    throw 'Native UTF-8 stdin identity or isolated child environment check failed.'
}

$failed = Invoke-IsolatedCodex -CliArguments @('-c', 'import sys; sys.exit(7)')
if ($failed.ExitCode -ne 7 -or $failed.TimedOut) { throw 'Nonzero child process exit was lost.' }
$timeout = Invoke-IsolatedCodex -CliArguments @('-c', 'import time; time.sleep(5)') -Seconds 1
if (-not $timeout.TimedOut -or $timeout.ExitCode -eq 0) { throw 'Child process timeout was lost.' }

$evidence = [ordered]@{
    scope = 'launcher_native_stdin_checks'
    created_at = [DateTime]::UtcNow.ToString('o')
    powershell_version = $PSVersionTable.PSVersion.ToString()
    controlled_executable = 'local_python'
    cases = @(
        @{ name = 'utf8_multiline_stdin_and_fake_parent_env_split'; result = 'PASS' },
        @{ name = 'child_exit_7_observed'; result = 'PASS' },
        @{ name = 'child_timeout_observed'; result = 'PASS' }
    )
    real_credentials_read = $false
    fake_parent_role_credentials = $true
    live_api = 'NOT_RUN'
    product_tests = 'NOT_RUN'
    note = 'Only the native launcher pipe/environment helper was tested; product AT-15 remains NOT_RUN.'
}
$evidenceDir = Join-Path $projectRoot 'artifacts/codex-launcher'
[void][IO.Directory]::CreateDirectory($evidenceDir)
$evidencePath = Join-Path $evidenceDir 'stdin-checks.json'
[IO.File]::WriteAllText($evidencePath, ($evidence | ConvertTo-Json -Depth 6), $utf8)
Write-Host ('Native launcher stdin checks: 3 PASS; local Python only. Evidence: ' + $evidencePath)
