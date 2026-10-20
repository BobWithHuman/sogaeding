<# Isolated demo entrypoint. Only human start with exact approvals opens a model. #>
param(
    [ValidateSet('prepare','revise','inspect','check','start','verify-block','history')][string]$Mode='check',
    [string]$PythonPath='', [string]$CodexPath='', [string]$Model='',
    [switch]$ConfirmSend, [string]$ManifestSha256='', [string]$ResumeManifestSha256='',
    [string]$RiskAttempt='', [string]$AttemptManifestSha256='',
    [Nullable[int]]$ApproveRequestLimit, [Nullable[int]]$ApproveInputReservationLimit,
    [Nullable[int]]$ApproveActorEpisodes, [string]$Revision='', [switch]$ConfirmRevision,
    [Nullable[int]]$ApproveInteractiveWallSeconds,
    [Nullable[int]]$ApproveTotalActorStarts, [Nullable[int]]$ApproveCumulativeRequests,
    [Nullable[int]]$ApproveCumulativeInputReservation, [Nullable[int]]$ApproveDemoCumulativeRequests,
    [Nullable[int]]$ApproveDemoCumulativeInputReservation
)
$ErrorActionPreference='Stop'
if ($Revision -in @('hands-on-1','frozen-demo-1') -and $Mode -notin @('history','check','inspect')) { throw 'Use the matching hookgw_connect.ps1 fixed demo selection then direct codex.' }
if (($RiskAttempt -or $AttemptManifestSha256) -and ($Mode -ne 'verify-block' -or $Revision -ne 'core-auto-v5p1' -or $RiskAttempt -ne 'post-complete-1' -or $AttemptManifestSha256 -notmatch '^[a-f0-9]{64}$' -or $ResumeManifestSha256)) { throw 'Separate post attempt requires core verify-block, exact attempt hash and no original retry.' }
if ($ResumeManifestSha256 -and ($Mode -ne 'verify-block' -or $Revision -ne 'core-auto-v5p1' -or $ResumeManifestSha256 -notmatch '^[a-f0-9]{64}$')) { throw 'Resume manifest is core verify-block only.' }
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $PythonPath) {
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath=(Get-Command python -CommandType Application -ErrorAction Stop).Source }
}
if ($Mode -in @('check','start') -and -not $CodexPath) { $CodexPath=(Get-Command codex -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source }
if ($Mode -notin @('start','verify-block') -and ($ConfirmSend -or $ManifestSha256 -or $null -ne $ApproveRequestLimit -or $null -ne $ApproveInputReservationLimit -or $null -ne $ApproveActorEpisodes -or $null -ne $ApproveInteractiveWallSeconds)) { throw 'Paid transmission approval arguments are start-only.' }
if ($Revision -and $Revision -notin @('host-wait-1','behavior-v5-1','core-auto-v5p1','hands-on-1','frozen-demo-1')) { throw 'Only assigned revisions are supported.' }
if ($ConfirmRevision -and $Mode -ne 'revise') { throw 'ConfirmRevision is only valid for model-free revise.' }
if ($Mode -eq 'revise' -and ($Revision -notin @('host-wait-1','behavior-v5-1','core-auto-v5p1') -or -not $ConfirmRevision)) { throw 'Revision preparation requires assigned -Revision and -ConfirmRevision; no paid execution.' }
$hasExtra=$null -ne $ApproveTotalActorStarts -or $null -ne $ApproveCumulativeRequests -or $null -ne $ApproveCumulativeInputReservation -or $null -ne $ApproveDemoCumulativeRequests -or $null -ne $ApproveDemoCumulativeInputReservation
if ($hasExtra -and ($Mode -notin @('start','verify-block') -or $Revision -notin @('behavior-v5-1','core-auto-v5p1'))) { throw 'V5 additional approvals are start-only.' }
$requestLimit=8; $inputLimit=512000; $actorLimit=2
if ($Revision -in @('behavior-v5-1','core-auto-v5p1')) { $requestLimit=4; $inputLimit=256000; $actorLimit=1 }
if ($Mode -in @('start','verify-block') -and (-not $ConfirmSend -or $ManifestSha256 -notmatch '^[a-f0-9]{64}$' -or $ApproveRequestLimit -ne $requestLimit -or $ApproveInputReservationLimit -ne $inputLimit -or $ApproveActorEpisodes -ne $actorLimit -or ($Mode -eq 'start' -and -not $Model))) { throw 'Inspect first; start requires exact manifest, ConfirmSend, fixed revision limits and explicit Model.' }
if ($Mode -eq 'verify-block' -and $Revision -ne 'core-auto-v5p1') { throw 'verify-block requires core-auto-v5p1.' }
if ($Mode -in @('start','verify-block') -and $Revision -eq 'core-auto-v5p1' -and ($ApproveTotalActorStarts -ne 5 -or $ApproveCumulativeRequests -ne 29 -or $ApproveCumulativeInputReservation -ne 1856000 -or $ApproveDemoCumulativeRequests -ne 24 -or $ApproveDemoCumulativeInputReservation -ne 1536000 -or $ApproveInteractiveWallSeconds -ne 1800)) { throw 'Core requires new4/256000, CLI1/total5, history29/1856000, demo24/1536000, wall1800.' }
if ($Mode -eq 'start' -and $Revision -eq 'behavior-v5-1' -and ($ApproveTotalActorStarts -ne 4 -or $ApproveCumulativeRequests -ne 25 -or $ApproveCumulativeInputReservation -ne 1600000 -or $ApproveDemoCumulativeRequests -ne 20 -or $ApproveDemoCumulativeInputReservation -ne 1280000 -or $ApproveInteractiveWallSeconds -ne 1800)) { throw 'V5 requires additional CLI1/total4, new Jev4/256000, total25/1600000, demo20/1280000, wall1800.' }
if ($Mode -eq 'start' -and $Revision -eq 'host-wait-1' -and $ApproveInteractiveWallSeconds -ne 1800) { throw 'This revision requires explicit -ApproveInteractiveWallSeconds 1800, including human wait; original180 is not silently extended.' }
if ($Mode -eq 'start' -and -not $Revision -and $null -ne $ApproveInteractiveWallSeconds -and $ApproveInteractiveWallSeconds -ne 180) { throw 'Legacy wall remains180; new wall requires explicit assigned revision.' }
$arguments=@($Mode)
if ($CodexPath) { $arguments+=@('--exe',$CodexPath) }
if ($Model) { $arguments+=@('--model',$Model) }
if ($Revision) { $arguments+=@('--revision',$Revision) }
if ($ResumeManifestSha256) { $arguments+=@('--resume-manifest-sha256',$ResumeManifestSha256) }
if ($RiskAttempt) { $arguments+=@('--risk-attempt',$RiskAttempt,'--attempt-manifest-sha256',$AttemptManifestSha256) }
if ($ConfirmRevision) { $arguments+='--confirm-revision' }
if ($null -ne $ApproveInteractiveWallSeconds) { $arguments+=@('--approve-interactive-wall-seconds',"$ApproveInteractiveWallSeconds") }
if ($Revision -in @('behavior-v5-1','core-auto-v5p1') -and $Mode -in @('start','verify-block')) { $arguments+=@('--approve-total-actor-starts',"$ApproveTotalActorStarts",'--approve-cumulative-requests',"$ApproveCumulativeRequests",'--approve-cumulative-input-reservation',"$ApproveCumulativeInputReservation",'--approve-demo-cumulative-requests',"$ApproveDemoCumulativeRequests",'--approve-demo-cumulative-input-reservation',"$ApproveDemoCumulativeInputReservation") }
if ($Mode -in @('start','verify-block')) { $arguments+=@('--confirm-send','--manifest-sha256',$ManifestSha256,'--approve-request-limit',"$ApproveRequestLimit",'--approve-input-reservation-limit',"$ApproveInputReservationLimit",'--approve-actor-episodes',"$ApproveActorEpisodes") }
$previousConsole=[Console]::OutputEncoding
$previousOutput=$OutputEncoding
try {
    [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
    $OutputEncoding=[Text.UTF8Encoding]::new($false)
    # Interactive start inherits terminal streams; do not capture user/model traffic.
    $ErrorActionPreference='Continue'
    if ($Mode -eq 'start') {
        & $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_demo.py') @arguments
    } else {
        & $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_demo.py') @arguments 2>$null
    }
    $nativeExit=$LASTEXITCODE
    if ($nativeExit -ne 0) { throw 'WITH_HUMAN_MVP_DEMO_FAILURE; no implicit retry; use history/check.' }
} finally {
    [Console]::OutputEncoding=$previousConsole
    $OutputEncoding=$previousOutput
    $ErrorActionPreference='Stop'
}
