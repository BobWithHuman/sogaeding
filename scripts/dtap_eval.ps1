param(
    [ValidateSet('check','run','status','collect','stop','recover','resume')][string]$Mode = 'check',
    [ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
    [switch]$OfficialRuntime,
    [ValidateSet('engine-off','engine-on')][string]$Arm,
    [string]$Experiment='artifacts/20261018-dtap-os100/user-usd7-context-2',
    [decimal]$MaxTotalUsd=0,
    [switch]$PaidOptIn,
    [switch]$AcknowledgeIncompleteCoverage
)
$ErrorActionPreference='Stop'
if($MaxTotalUsd -gt 7){throw 'USER_BUDGET_MAX_USD_7: both arms combined; no provider call was started.'}
$dtapRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($OfficialRuntime) {
    & (Join-Path $PSScriptRoot 'dtap_official_runtime.ps1') @PSBoundParameters
    exit $LASTEXITCODE
}
if (-not $ManifestSha256 -or $Mode -notin @('check','run')) { throw 'Legacy preparation requires check/run and its original manifest hash.' }
# Preparation-only entry point has no network and never mounts any user key.
& docker run --rm --network none --read-only --cap-drop ALL --tmpfs /tmp:rw `
  --mount "type=bind,source=$dtapRoot/tools/dtap_eval.py,target=/workspace/tools/dtap_eval.py,readonly" `
  --mount "type=bind,source=$dtapRoot/artifacts/20261017-dtap-prepare/inventory-final,target=/workspace/artifacts/20261017-dtap-prepare/inventory-final,readonly" `
  --mount "type=bind,source=$dtapRoot/artifacts/20261017-dtap-prepare/prepared,target=/workspace/artifacts/20261017-dtap-prepare/prepared,readonly" `
  -w /workspace with-human-dev:local python tools/dtap_eval.py $Mode --manifest-sha256 $ManifestSha256
if ($LASTEXITCODE -ne 0) { throw "DTAP gate stopped (exit $LASTEXITCODE). Read the listed compatibility/cost gaps." }



