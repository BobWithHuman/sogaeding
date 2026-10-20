<# Fixed semantic-confirm-1 proposal. prepare/check never starts models/services. #>
param(
    [ValidateSet('prepare','inspect','check','start','history')][string]$Mode='check',
    [string]$PythonPath='', [string]$CodexPath='', [string]$Model='',
    [switch]$ConfirmSend, [string]$ManifestSha256='',
    [Nullable[int]]$ApproveAdditionalStarts, [Nullable[int]]$ApproveTotalStartLimit,
    [Nullable[int]]$ApproveRequestLimit, [Nullable[int]]$ApproveInputReservationLimit,
    [Nullable[int]]$ApproveInteractiveWallSeconds
)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $PythonPath) {
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath=(Get-Command python -CommandType Application -ErrorAction Stop).Source }
}
if ($Mode -in @('check','start') -and -not $CodexPath) { $CodexPath=(Get-Command codex -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source }
if ($Mode -ne 'start' -and ($ConfirmSend -or $ManifestSha256 -or $null -ne $ApproveAdditionalStarts -or $null -ne $ApproveTotalStartLimit -or $null -ne $ApproveRequestLimit -or $null -ne $ApproveInputReservationLimit -or $null -ne $ApproveInteractiveWallSeconds)) { throw 'Paid approvals are start-only; prepare/check have no paid requests.' }
if ($Mode -eq 'start' -and (-not $ConfirmSend -or $ManifestSha256 -notmatch '^[a-f0-9]{64}$' -or $ApproveAdditionalStarts -ne 1 -or $ApproveTotalStartLimit -ne 3 -or $ApproveRequestLimit -ne 8 -or $ApproveInputReservationLimit -ne 512000 -or $ApproveInteractiveWallSeconds -ne 1800 -or -not $Model)) { throw 'Inspect proposal; start requires exact manifest, ConfirmSend, AdditionalStarts1, TotalStartLimit3, Requests8, Input512000, Wall1800 and explicit Model.' }
$arguments=@($Mode)
if ($CodexPath) { $arguments+=@('--exe',$CodexPath) }
if ($Model) { $arguments+=@('--model',$Model) }
if ($Mode -eq 'start') { $arguments+=@('--confirm-send','--manifest-sha256',$ManifestSha256,'--approve-additional-starts',"$ApproveAdditionalStarts",'--approve-total-start-limit',"$ApproveTotalStartLimit",'--approve-request-limit',"$ApproveRequestLimit",'--approve-input-reservation-limit',"$ApproveInputReservationLimit",'--approve-interactive-wall-seconds',"$ApproveInteractiveWallSeconds") }
$previousConsole=[Console]::OutputEncoding
$previousOutput=$OutputEncoding
try {
    [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
    $OutputEncoding=[Text.UTF8Encoding]::new($false)
    $ErrorActionPreference='Continue'
    if ($Mode -eq 'start') {
        & $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_semantic_followup.py') @arguments
    } else {
        & $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_semantic_followup.py') @arguments 2>$null
    }
    $nativeExit=$LASTEXITCODE
    if ($nativeExit -ne 0) { throw 'FOLLOWUP_FAILED_NO_RETRY; use history/check; reservations are retained.' }
} finally {
    [Console]::OutputEncoding=$previousConsole
    $OutputEncoding=$previousOutput
    $ErrorActionPreference='Stop'
}
