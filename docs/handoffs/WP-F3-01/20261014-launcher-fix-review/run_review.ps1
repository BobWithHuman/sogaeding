param([Parameter(Mandatory)][string]$Label,[Parameter(Mandatory)][string]$ShellPath)
$ErrorActionPreference='Stop'
$target='C:/sogaeding/artifacts/20261014-f3-launcher-fix-review'
$snapshot=Join-Path $target ($Label+'-snapshot')
New-Item -ItemType Directory -Path $snapshot -ErrorAction Stop | Out-Null
$records=@()
foreach($source in @('C:/sogaeding/tools/f3_evidence.ps1','C:/sogaeding/scripts/f3_verify.ps1',(Join-Path $PSScriptRoot 'check.ps1'),(Join-Path $PSScriptRoot 'run_review.ps1'))) {
    $name=Split-Path $source -Leaf
    Copy-Item -LiteralPath $source -Destination (Join-Path $snapshot $name)
    $records+=@{path=$source;sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()}
}
@{captured_at=[DateTime]::UtcNow.ToString('o');files=$records}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $snapshot 'manifest.json') -Encoding utf8
$started=[DateTime]::UtcNow.ToString('o')
$beforePreference=$ErrorActionPreference
try {$ErrorActionPreference='Continue';$PSNativeCommandUseErrorActionPreference=$false
    $output=& $ShellPath -NoProfile -File (Join-Path $PSScriptRoot 'check.ps1') -Label $Label 2>&1 | ForEach-Object {$_.ToString()}
    $code=$LASTEXITCODE
}finally {$ErrorActionPreference=$beforePreference}
$output|Set-Content -LiteralPath (Join-Path $target ($Label+'.txt')) -Encoding utf8
@{started_at=$started;completed_at=[DateTime]::UtcNow.ToString('o');command=@($ShellPath,'-NoProfile','-File',(Join-Path $PSScriptRoot 'check.ps1'),'-Label',$Label);exit_code=$code;source_fixture_manifest=$Label+'-snapshot/manifest.json'} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $target ($Label+'-command.json')) -Encoding utf8
$output|Select-Object -Last 12
exit $code
