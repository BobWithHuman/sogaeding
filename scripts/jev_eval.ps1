<# User-only bounded Jev smoke. Preparation never authorizes transmission. #>
param(
    [ValidateSet('prepare','key','inspect','preflight','evaluate','collect','followup-plan','followup-prepare')][string]$Mode='preflight',
    [string]$PythonPath='', [switch]$ConfirmSend, [string]$ManifestSha256='',
    [Nullable[int]]$ApproveRequestLimit, [Nullable[int]]$ApproveInputReservationLimit,
    [string]$NewRunId='', [switch]$ConfirmNewPlan, [string]$RunId='',
    [Nullable[int]]$ApproveCumulativeRequestLimit, [Nullable[int]]$ApproveCumulativeInputReservationLimit,
    [Nullable[int]]$ApproveAdditionalRequestLimit, [Nullable[int]]$ApproveAdditionalInputReservationLimit,
    [Nullable[int]]$ApproveDemoCumulativeRequestLimit, [Nullable[int]]$ApproveDemoCumulativeInputReservationLimit
)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $PythonPath) {
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath=(Get-Command python -CommandType Application -ErrorAction Stop).Source }
}
$helper=Join-Path $project 'tools/jev_eval.py'
if ($Mode -ne 'evaluate' -and ($ConfirmSend -or $ManifestSha256 -or $null -ne $ApproveRequestLimit -or $null -ne $ApproveInputReservationLimit -or $null -ne $ApproveCumulativeRequestLimit -or $null -ne $ApproveCumulativeInputReservationLimit -or $null -ne $ApproveAdditionalRequestLimit -or $null -ne $ApproveAdditionalInputReservationLimit -or $null -ne $ApproveDemoCumulativeRequestLimit -or $null -ne $ApproveDemoCumulativeInputReservationLimit)) { throw 'Transmission approval arguments are only valid for evaluate.' }
if (($NewRunId -and $Mode -ne 'followup-plan') -or ($ConfirmNewPlan -and $Mode -notin @('followup-plan','followup-prepare'))) { throw 'New plan arguments are only valid for a plan preparation mode; no budget or transmission is authorized.' }
if ($RunId -and ($RunId -notin @('followup-response-v2','followup-auto-v4','followup-behavior-v5') -or $Mode -notin @('followup-prepare','inspect','preflight','evaluate','collect'))) { throw 'Only an assigned fixed followup run can be selected.' }
function Invoke-JevPython {
    param([string]$Stage,[string[]]$CommandArgs,[string]$InputText,[switch]$HasInput)
    $previousPreference=$ErrorActionPreference
    try {
        # PS5.1 wraps native stderr as ErrorRecord. Keep raw tracebacks off all
        # output streams and classify only the trusted process exit/stage.
        $ErrorActionPreference='Continue'
        $global:LASTEXITCODE=$null
        if ($HasInput) { $lines=@($InputText | & $PythonPath -X utf8 -I $helper @CommandArgs 2>$null) }
        else { $lines=@(& $PythonPath -X utf8 -I $helper @CommandArgs 2>$null) }
        $nativeExit=$global:LASTEXITCODE
    } catch {
        throw "WITH_HUMAN_JEV_FAILURE stage=$Stage code=PYTHON_START_FAILED"
    } finally {
        $ErrorActionPreference=$previousPreference
    }
    if ($null -eq $nativeExit) { throw "WITH_HUMAN_JEV_FAILURE stage=$Stage code=PYTHON_START_FAILED" }
    if ($nativeExit -ne 0) { throw "WITH_HUMAN_JEV_FAILURE stage=$Stage code=HELPER_NONZERO_EXIT; no implicit retry" }
    $jsonText=($lines -join "`n").Trim()
    if (-not $jsonText) { throw "WITH_HUMAN_JEV_FAILURE stage=$Stage code=HELPER_EMPTY_OUTPUT" }
    try {
        if (-not $jsonText.StartsWith('{') -or -not $jsonText.EndsWith('}')) { throw 'Invalid object' }
        $null=$jsonText | ConvertFrom-Json -ErrorAction Stop
    } catch { throw "WITH_HUMAN_JEV_FAILURE stage=$Stage code=HELPER_JSON_INVALID" }
    $lines
}
$previousConsoleEncoding=[Console]::OutputEncoding
$previousOutputEncoding=$OutputEncoding
try {
    try {
        # Explicit -X survives -I; these encodings control PS5.1 native capture
        # and the existing ASCII key stdin pipe, not a persistent user setting.
        [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
        $OutputEncoding=[Text.UTF8Encoding]::new($false)
    } catch { throw 'WITH_HUMAN_JEV_FAILURE stage=ENCODING code=UTF8_SETUP_FAILED' }
    if ($Mode -in @('prepare','key')) {
        # Failed preparation: no key input or model request is started.
        if ($Mode -eq 'prepare') { Invoke-JevPython -Stage PREPARE -CommandArgs @('prepare') }
        else { Invoke-JevPython -Stage STORAGE_CHECK -CommandArgs @('storage-check') }
        Write-Host 'Owner-only ACL and ignored path are required. Key preparation is not permission to call TypeSafe.'
        try { $secure=Read-Host 'TypeSafe role key (hidden; no model request)' -AsSecureString }
        catch { throw 'WITH_HUMAN_JEV_FAILURE stage=KEY_INPUT code=HIDDEN_INPUT_FAILED' }
        $pointer=[IntPtr]::Zero
        try {
            $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
            $plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
            Invoke-JevPython -Stage STORE_KEY -CommandArgs @('store-key') -InputText $plain -HasInput
        } finally {
            $plain=$null
            if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
            if ($secure) { $secure.Dispose() }
        }
    } elseif ($Mode -eq 'evaluate') {
        if (-not $ConfirmSend -or $ManifestSha256 -notmatch '^[0-9a-f]{64}$' -or $ApproveRequestLimit -ne 4 -or $ApproveInputReservationLimit -ne 256000) { throw 'Review exact inspect data and price first; evaluate requires -ConfirmSend -ManifestSha256 <hash> -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000.' }
        $evaluateArgs=@('evaluate','--confirm-send','--manifest-sha256',$ManifestSha256,'--approve-request-limit',"$ApproveRequestLimit",'--approve-input-reservation-limit',"$ApproveInputReservationLimit")
        if ($RunId) {
            if ($RunId -in @('followup-auto-v4','followup-behavior-v5')) {
                $totalRequests=17; $totalInput=1088000; $demoRequests=12; $demoInput=768000
                if ($RunId -eq 'followup-behavior-v5') { $totalRequests=21; $totalInput=1344000; $demoRequests=16; $demoInput=1024000 }
                if ($ApproveCumulativeRequestLimit -ne $totalRequests -or $ApproveCumulativeInputReservationLimit -ne $totalInput -or $ApproveAdditionalRequestLimit -ne 4 -or $ApproveAdditionalInputReservationLimit -ne 256000 -or $ApproveDemoCumulativeRequestLimit -ne $demoRequests -or $ApproveDemoCumulativeInputReservationLimit -ne $demoInput) { throw 'V4 requires its fixed limits; V5 requires new4/256000, demo cumulative16/1024000 and all historical cumulative21/1344000; CLI0, no refund/reset.' }
                $evaluateArgs+=@('--approve-demo-cumulative-request-limit',"$ApproveDemoCumulativeRequestLimit",'--approve-demo-cumulative-input-reservation-limit',"$ApproveDemoCumulativeInputReservationLimit")
            } elseif ($ApproveCumulativeRequestLimit -ne 5 -or $ApproveCumulativeInputReservationLimit -ne 320000 -or $ApproveAdditionalRequestLimit -ne 1 -or $ApproveAdditionalInputReservationLimit -ne 64000 -or $null -ne $ApproveDemoCumulativeRequestLimit -or $null -ne $ApproveDemoCumulativeInputReservationLimit) { throw 'Followup requires explicit cumulative5/320000 and additional1/64000 approval; previous1/64000 is not refunded.' }
            $evaluateArgs+=@('--run-id',$RunId,'--approve-cumulative-request-limit',"$ApproveCumulativeRequestLimit",'--approve-cumulative-input-reservation-limit',"$ApproveCumulativeInputReservationLimit",'--approve-additional-request-limit',"$ApproveAdditionalRequestLimit",'--approve-additional-input-reservation-limit',"$ApproveAdditionalInputReservationLimit")
        } elseif ($null -ne $ApproveCumulativeRequestLimit -or $null -ne $ApproveCumulativeInputReservationLimit -or $null -ne $ApproveAdditionalRequestLimit -or $null -ne $ApproveAdditionalInputReservationLimit -or $null -ne $ApproveDemoCumulativeRequestLimit -or $null -ne $ApproveDemoCumulativeInputReservationLimit) { throw 'Followup total/additional approval requires the assigned RunId.' }
        Invoke-JevPython -Stage EVALUATE -CommandArgs $evaluateArgs
    } elseif ($Mode -eq 'followup-prepare') {
        if ($RunId -notin @('followup-response-v2','followup-auto-v4','followup-behavior-v5') -or -not $ConfirmNewPlan) { throw 'Explicit assigned -RunId and -ConfirmNewPlan required; no provider call is authorized.' }
        Invoke-JevPython -Stage FOLLOWUP_PREPARE -CommandArgs @('followup-prepare','--run-id',$RunId,'--confirm-new-plan')
    } elseif ($Mode -eq 'followup-plan') {
        if (-not $ConfirmNewPlan -or $NewRunId -notmatch '^followup-[a-z0-9][a-z0-9-]{0,39}$') { throw 'Followup proposal requires -NewRunId followup-<safe-id> -ConfirmNewPlan; it remains disabled and cannot execute.' }
        Invoke-JevPython -Stage FOLLOWUP_PLAN -CommandArgs @('followup-plan','--new-run-id',$NewRunId,'--confirm-new-plan')
    } else {
        $modeArgs=@($Mode)
        if ($RunId) { $modeArgs+=@('--run-id',$RunId) }
        Invoke-JevPython -Stage $Mode.ToUpperInvariant() -CommandArgs $modeArgs
    }
} finally {
    [Console]::OutputEncoding=$previousConsoleEncoding
    $OutputEncoding=$previousOutputEncoding
}
