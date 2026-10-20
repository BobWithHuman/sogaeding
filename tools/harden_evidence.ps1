param([Parameter(Mandatory)][string]$RunId,
      [Parameter(Mandatory)][string]$Label,
      [Parameter(Mandatory)][string[]]$DockerArgs)
$ErrorActionPreference = 'Stop'
$target = Join-Path (Join-Path $PSScriptRoot '../artifacts') $RunId
New-Item -ItemType Directory -Force -Path $target | Out-Null
$started = [DateTime]::UtcNow.ToString('o')
$output = & docker @DockerArgs 2>&1
$code = $LASTEXITCODE
$output | Set-Content -LiteralPath (Join-Path $target "$Label.txt") -Encoding utf8
@{command = @('docker') + $DockerArgs; started_at = $started;
  completed_at = [DateTime]::UtcNow.ToString('o'); exit_code = $code;
  safe_output_path = "artifacts/$RunId/$Label.txt"} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $target "$Label-command.json") -Encoding utf8
$output | Select-Object -Last 12
exit $code
