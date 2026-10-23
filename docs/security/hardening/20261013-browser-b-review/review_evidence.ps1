param([Parameter(Mandatory)][string]$Label,
      [Parameter(Mandatory)][string]$Program,
      [Parameter(Mandatory)][string[]]$CommandArgs)
$ErrorActionPreference = 'Stop'
$reviewRoot = 'C:/sogaeding/docs/handoffs/WP-HARDEN-01/20261013-browser-b-review'
$artifactRoot = 'C:/sogaeding/artifacts/20261013-browser-b-review'
$fixtureTarget = Join-Path $artifactRoot "$Label-review-fixtures"
if (Test-Path -LiteralPath $fixtureTarget) { throw 'Preserve old fixture snapshots.' }
New-Item -ItemType Directory -Path $fixtureTarget | Out-Null
$fixtureManifest = @(Get-ChildItem -LiteralPath $reviewRoot -File | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $fixtureTarget $_.Name)
  @{path = $_.FullName; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
})
@{captured_at = [DateTime]::UtcNow.ToString('o'); files = $fixtureManifest} | ConvertTo-Json -Depth 5 |
  Set-Content -LiteralPath (Join-Path $fixtureTarget 'manifest.json') -Encoding utf8
& 'C:/sogaeding/tools/browser_evidence.ps1' -RunId 20261013-browser-b-review -Label $Label -Program $Program -CommandArgs $CommandArgs
exit $LASTEXITCODE
