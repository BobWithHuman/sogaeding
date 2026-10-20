param([Parameter(Mandatory)][string]$Label, [Parameter(Mandatory)][string]$Program,
      [Parameter(Mandatory)][string[]]$CommandArgs)
$ErrorActionPreference='Stop'
$rootPath='C:/sogaeding'
$targetPath=Join-Path $rootPath 'artifacts/20261014-f3-review'
$fixturePath=Join-Path $targetPath ($Label+'-review-fixtures')
New-Item -ItemType Directory -Path $fixturePath -ErrorAction Stop | Out-Null
$items=@()
foreach ($file in Get-ChildItem -LiteralPath $PSScriptRoot -File) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $fixturePath $file.Name)
    $items+=@{path=$file.Name;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
@{captured_at=[DateTime]::UtcNow.ToString('o');files=$items} | ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath (Join-Path $fixturePath 'manifest.json') -Encoding utf8
& (Join-Path $rootPath 'tools/f3_evidence.ps1') -RunId '20261014-f3-review' -Label $Label -Program $Program -CommandArgs $CommandArgs
exit $LASTEXITCODE
