param([Parameter(Mandatory)][string]$RunId,
      [Parameter(Mandatory)][string]$Label,
      [Parameter(Mandatory)][string]$Program,
      [Parameter(Mandatory)][string[]]$CommandArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$target = Join-Path (Join-Path $projectRoot 'artifacts') $RunId
New-Item -ItemType Directory -Force -Path $target | Out-Null
if (Test-Path -LiteralPath (Join-Path $target "$Label-command.json")) { throw 'Use a new command label; preserve previous evidence.' }
$pythonPath = 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$snapshot = & $pythonPath -X utf8 (Join-Path $PSScriptRoot 'f3_snapshot.py') $RunId $Label
if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed; command was not started.' }
$summary = $snapshot | ConvertFrom-Json
$application = Get-Command -Name $Program -CommandType Application -ErrorAction Stop | Select-Object -First 1
$started = [DateTime]::UtcNow.ToString('o')
$previousErrorAction = $ErrorActionPreference
try {
    # Windows PowerShell 5.1 wraps redirected native stderr as ErrorRecord.
    # Docker progress on stderr is normal; only the process exit code decides.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    $output = & $application.Path @CommandArgs 2>&1 | ForEach-Object { $_.ToString() }
    $code = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorAction
}
$output | Set-Content -LiteralPath (Join-Path $target "$Label.txt") -Encoding utf8
@{command = @($Program) + $CommandArgs; started_at = $started;
  completed_at = [DateTime]::UtcNow.ToString('o'); exit_code = $code;
  source_fingerprint = $summary.fingerprint; source_manifest = "artifacts/$RunId/$Label-source/manifest.json";
  safe_output_path = "artifacts/$RunId/$Label.txt"} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $target "$Label-command.json") -Encoding utf8
$output | Select-Object -Last 10
exit $code

