param(
    [ValidateSet('check','probe','run','status','collect','stop','recover','resume')][string]$Mode='check',
    [ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
    [switch]$OfficialRuntime,
    [switch]$DemoMode,
    [switch]$DenyFollowup,
    [switch]$UtilityAcceptance,
    [switch]$QueryRouting,
    [ValidateSet('engine-off','engine-on')][string]$Arm,
    [string]$Experiment='artifacts/20261018-dtap-os100/user-usd7-context-2',
    [decimal]$MaxTotalUsd=0,
    [switch]$PaidOptIn,
    [switch]$AcknowledgeIncompleteCoverage
)
$ErrorActionPreference='Stop'
if($QueryRouting){$UtilityAcceptance=$true}
if($UtilityAcceptance -and -not $QueryRouting -and $Mode -eq 'run'){throw 'Previous utility preparation is preserved. Use the reviewed QueryRouting revision.'}
if($UtilityAcceptance){$DemoMode=$true;if($DenyFollowup){throw 'Choose one fixed revision only.'}}
if($UtilityAcceptance -and $Mode -eq 'run' -and [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)){throw 'OPENAI_API_KEY missing; no start claim or provider request was made.'}
if($DenyFollowup){$DemoMode=$true}
if($DemoMode -and -not $DenyFollowup -and -not $UtilityAcceptance -and $Mode -in @('run','recover')){throw 'The scope-v2 run is preserved and stopped. Use the reviewed -DenyFollowup successor; UNKNOWN must not be retried.'}
if($DemoMode){
    $Experiment='artifacts/20261018-dtap-os100/user-engine-demo-02-scope-v2'
    if($DenyFollowup){$Experiment='artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup'}
    if($UtilityAcceptance){$Experiment='artifacts/20261018-dtap-os100/user-normal-utility-acceptance'}
    if($QueryRouting){$Experiment='artifacts/20261018-dtap-os100/user-query-utility'}
    if($Arm -and $Arm -ne 'engine-on'){throw 'Demo permits fresh autonomous engine-on only.'}
    if($Mode -eq 'resume'){throw 'Demo does not resume old runs.'}
}
if($MaxTotalUsd -gt 7){throw 'USER_BUDGET_MAX_USD_7: both arms combined; no provider call was started.'}
$dtapProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).Replace('\','/')
$dtapOutput=[IO.Path]::GetFullPath((Join-Path $dtapProject $Experiment)).Replace('\','/')
$dtapAllowedRoot="$dtapProject/artifacts/20261018-dtap-os100/"
if (-not $dtapOutput.StartsWith($dtapAllowedRoot,[StringComparison]::OrdinalIgnoreCase)) {throw 'Experiment must be inside the dedicated DTAP runtime artifact directory.'}
$dtapWorker='sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d'
$dtapPlanPath="$dtapOutput/plan.json"
$dtapParent=if($dtapOutput.EndsWith('/user-usd7-context-2')){"$dtapProject/artifacts/20261018-dtap-os100/user-usd7-settled-1"}else{"$dtapProject/artifacts/20261018-dtap-os100/user-usd7"}
if($DemoMode){$dtapParent="$dtapProject/artifacts/20261018-dtap-os100/user-usd7-context-2"}
if($DenyFollowup){$dtapParent="$dtapProject/artifacts/20261018-dtap-os100/user-engine-demo-02-scope-v2"}
if($UtilityAcceptance){$dtapParent="$dtapProject/artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup"}
function Protect-DtapExperiment([string]$Path) {
    if($DemoMode){
        $dtapExistingAcl=Get-Acl -LiteralPath $Path
        $dtapAllowedSids=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18')
        $dtapRules=@($dtapExistingAcl.Access)
        if($dtapExistingAcl.AreAccessRulesProtected -and $dtapRules.Count -eq 2 -and
           @($dtapRules | Where-Object {
               $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $dtapAllowedSids -or
               $_.AccessControlType -ne 'Allow' -or $_.FileSystemRights -ne 'FullControl' -or $_.IsInherited
           }).Count -eq 0){return}
    }
    $dtapAcl=New-Object Security.AccessControl.DirectorySecurity
    $dtapAcl.SetAccessRuleProtection($true,$false)
    $dtapIdentity=[Security.Principal.WindowsIdentity]::GetCurrent().User
    foreach($dtapSid in @($dtapIdentity,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))){
        $dtapAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($dtapSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    Set-Acl -LiteralPath $Path -AclObject $dtapAcl
}
function Test-DtapInheritedImages {
    $dtapInherited=if($DemoMode){$dtapPlan.manifest.demo.inherited_initial_snapshots}else{$dtapPlan.manifest.continuation.inherited_initial_snapshots}
    if($dtapInherited){
        foreach($dtapSnapshot in $dtapInherited.psobject.Properties){
            $dtapImage=$dtapSnapshot.Value.image
            if($dtapImage -notmatch '^sha256:[a-f0-9]{64}$'){throw 'Invalid inherited image identity.'}
            $dtapActualImage=& docker image inspect $dtapImage --format '{{.Id}}'
            if($LASTEXITCODE -ne 0 -or $dtapActualImage -ne $dtapImage){throw 'Inherited initial image unavailable; no setup replay or paid call allowed.'}
        }
    }
}
function Test-DtapNetworks {
    # Read actual Docker state before the start lock or provider keys are touched.
    $dtapNames=@(& docker network ls --format '{{.Name}}')
    if($LASTEXITCODE -ne 0){throw 'DTAP_NETWORK_PREFLIGHT_UNAVAILABLE'}
    foreach($dtapNetworkArm in $dtapPlan.manifest.arms){
        $dtapExpected=$dtapPlan.networks.$dtapNetworkArm
        if($dtapNames -notcontains $dtapExpected.name){throw 'DTAP_NETWORK_NOT_PREPARED; no paid start was attempted.'}
        $dtapActualRaw=& docker network inspect $dtapExpected.name --format '{{json .}}'
        if($LASTEXITCODE -ne 0){throw 'DTAP_NETWORK_PREFLIGHT_UNAVAILABLE'}
        $dtapActual=$dtapActualRaw | ConvertFrom-Json
        if($dtapActual.Labels.'with-human.dtap.experiment' -ne $dtapPlan.experiment -or
           -not $dtapActual.Internal -or
           @($dtapActual.IPAM.Config.Subnet).Count -ne 1 -or
           $dtapActual.IPAM.Config.Subnet -ne $dtapExpected.subnet){
            throw 'DTAP_NETWORK_BINDING_REJECTED; preserve existing networks.'
        }
    }
}
function Invoke-DtapTool([string]$Operation,[switch]$Socket,[string]$Network='none',[switch]$Initial) {
    $dtapSource=if($Initial){$dtapProject}else{"$dtapOutput/source"}
    $dtapUser=if($Operation -in @('verify','status','collect','stop','recover','resume')){'10001:10001'}else{'0:0'}
    $dtapDocker=@('run','--rm','--user',$dtapUser,'--read-only','--cap-drop','ALL','--tmpfs','/tmp:rw','--network',$Network,
        '--mount',"type=bind,source=$dtapSource,target=/project,readonly",'--mount',"type=bind,source=$dtapOutput,target=/experiment",
        '-e','PYTHONPATH=/project/src:/benchdeps:/vendor','-e','CONTRACT_DIR=/project/docs/mvp/contracts','-e','PYTHONDONTWRITEBYTECODE=1','-e','DTAP_WINDOWS_HOST_ACL=1')
    if($DemoMode -or $Initial -or ($dtapPlan -and $dtapPlan.manifest.continuation)){
        $dtapParentMount="type=bind,source=$dtapParent,target=/parent"
        if($DemoMode -or -not $Initial){$dtapParentMount+=',readonly'}
        $dtapDocker+=@('--mount',$dtapParentMount)
    }
    if($Socket){$dtapDocker+=@('--mount','type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock')}
    if($Operation -eq 'run'){$dtapDocker+=@('--name',"$($dtapPlan.experiment)-$Arm-controller",'--label',"with-human.dtap.experiment=$($dtapPlan.experiment)")}
    $dtapBrokerPort=if($dtapOutput.EndsWith('/user-usd7-context-2')){'18662'}elseif($Initial -or ($dtapPlan -and $dtapPlan.manifest.continuation)){'18661'}else{'18660'}
    if($DemoMode){$dtapBrokerPort='18664'}
    if($DenyFollowup){$dtapBrokerPort='18665'}
    if($UtilityAcceptance){$dtapBrokerPort='18666'}
    if($QueryRouting){$dtapBrokerPort='18668'}
    $dtapDocker+=@($dtapWorker,'python','/project/tools/dtap_runtime.py',$Operation,'--host-root',$dtapOutput,'--project-root',$dtapProject,'--broker-port',$dtapBrokerPort)
    if($Arm){$dtapDocker+=@('--arm',$Arm)}
    if($ManifestSha256){$dtapDocker+=@('--expected-manifest-sha256',$ManifestSha256)}
    if($UtilityAcceptance -and $Mode -eq 'run' -and $Operation -eq 'verify'){$dtapDocker+=@('--require-fresh')}
    if($Operation -eq 'init'){
        if($QueryRouting){$dtapDocker+=@('--utility-acceptance','--query-routing','--parent-host-root',$dtapParent,'--subnet-on','10.233.149.0/24')}
        elseif($UtilityAcceptance){$dtapDocker+=@('--utility-acceptance','--parent-host-root',$dtapParent,'--subnet-on','10.233.147.0/24')}
        elseif($DenyFollowup){$dtapDocker+=@('--deny-followup','--parent-host-root',$dtapParent,'--subnet-off','10.233.144.0/24','--subnet-on','10.233.145.0/24')}
        elseif($DemoMode){$dtapDocker+=@('--demo','--parent-host-root',$dtapParent,'--subnet-off','10.233.142.0/24','--subnet-on','10.233.143.0/24')}
        else{$dtapDocker+=@('--continue-parent','--continue-parent-sha256','764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb','--parent-host-root',$dtapParent,'--profile','os100','--max-usd',$MaxTotalUsd.ToString([Globalization.CultureInfo]::InvariantCulture),'--subnet-off','10.233.114.0/24','--subnet-on','10.233.115.0/24')}
    }
    & docker @dtapDocker
    if($LASTEXITCODE -ne 0){throw "Official runtime stopped (exit $LASTEXITCODE). Preserve its ledger and inspect status/collect."}
}
if($Mode -eq 'check'){
    if($MaxTotalUsd -le 0){throw 'Set an explicit combined -MaxTotalUsd for the two-arm OS100 experiment.'}
    if(-not(Test-Path -LiteralPath $dtapPlanPath)){
        $dtapInitCap=if($UtilityAcceptance){[decimal]5.089294}else{[decimal]7}
        if(((-not $DemoMode) -and $dtapOutput -ne "$dtapProject/artifacts/20261018-dtap-os100/user-usd7-context-2") -or $MaxTotalUsd -ne $dtapInitCap){throw 'Only the reviewed fixed continuation and cumulative cap may be prepared.'}
        New-Item -ItemType Directory -Force -Path $dtapOutput | Out-Null
        Protect-DtapExperiment $dtapOutput
        Invoke-DtapTool 'init' -Initial -Socket:$DemoMode
    }
    $dtapPlan=Get-Content -Raw -LiteralPath $dtapPlanPath | ConvertFrom-Json
    Invoke-DtapTool 'verify'
    Test-DtapInheritedImages
    Test-DtapNetworks
    Write-Host "Frozen manifest: $dtapOutput/manifest.sha256"
    exit 0
}
if(-not(Test-Path -LiteralPath $dtapPlanPath)){throw 'Run check first; no paid start was attempted.'}
$dtapPlan=Get-Content -Raw -LiteralPath $dtapPlanPath | ConvertFrom-Json
if($Mode -eq 'probe'){
    if(-not $UtilityAcceptance -or -not $ManifestSha256){throw 'probe requires the fixed utility revision and reviewed manifest.'}
    Invoke-DtapTool 'probe' -Socket
    exit 0
}
if($DemoMode){
    $dtapExpectedTasks=if($UtilityAcceptance){3}elseif($DenyFollowup){14}else{15}
    if([bool]$dtapPlan.manifest.utility_acceptance -ne [bool]$UtilityAcceptance){throw 'Utility revision binding rejected.'}
    if($dtapPlan.manifest.policy_profile -ne 'dtap-demo-allow50-scope-v2' -or $dtapPlan.manifest.target_total -ne $dtapExpectedTasks -or [bool]$dtapPlan.manifest.runtime_deny_followup -ne [bool]$DenyFollowup){throw 'Demo binding rejected.'}
}elseif($dtapPlan.manifest.selection_profile -ne 'PINNED_OS_FILESYSTEM_INDIRECT_100' -or $dtapPlan.manifest.selection_sha256 -ne '05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b' -or $dtapPlan.manifest.target_total -ne 100 -or $dtapPlan.manifest.runtime_ready -ne 100){throw 'The frozen experiment is not the verified OS indirect 100 cohort.'}
if($Mode -in @('run','resume')){
    if(-not $DemoMode -and -not $dtapPlan.manifest.continuation){throw 'Original run is preserved and stopped. Only the parent-bound USD7 continuation may run.'}
    if($dtapPlan.manifest.limits.total.micro_usd -gt 7000000){throw 'FROZEN_BUDGET_EXCEEDS_USER_USD_7: preserve this plan and prepare a capped experiment.'}
    if(-not $ManifestSha256){throw 'An explicit frozen manifest SHA256 is required.'}
    Invoke-DtapTool 'verify'
    Test-DtapInheritedImages
}
if($Mode -eq 'run'){
    if(-not $Arm -or -not $PaidOptIn -or $MaxTotalUsd -le 0){throw 'run requires an arm, explicit -PaidOptIn, and combined -MaxTotalUsd.'}
    if($dtapPlan.manifest.mode -ne 'LIVE'){throw 'User run rejects OFFLINE/mock manifests.'}
    if($dtapPlan.manifest.readiness -ne 'FULL_READY' -and -not $AcknowledgeIncompleteCoverage){throw 'Partial coverage: inspect COVERAGE.csv. This cannot be reported as a full DTAP comparison.'}
    if($dtapPlan.manifest.limits.total.micro_usd -ne ($MaxTotalUsd*1000000)){throw 'Explicit combined cost cap must match the frozen manifest.'}
    Test-DtapNetworks
    if($UtilityAcceptance){
        if($QueryRouting){
            foreach($dtapFork in @(Get-ChildItem -LiteralPath "$dtapProject/artifacts/20261018-dtap-os100" -Directory | Where-Object {$_.Name -match '^user-(normal-utility|query-utility)'})){
                foreach($dtapMarker in @('broker-start.lock','keys','broker-container.json','broker-data/paid-opt-in.json')){
                    if(Test-Path -LiteralPath (Join-Path $dtapFork.FullName $dtapMarker)){throw 'UTILITY_FORK_ALREADY_STARTED: preserve all forks and cumulative budget.'}
                }
            }
        }
        $dtapJevPreflight="$dtapProject/artifacts/runtime-jev-eval/key/jev.api-key"
        if(-not(Test-Path -LiteralPath $dtapJevPreflight -PathType Leaf)){throw 'Existing Jev key reference missing; no start claim made.'}
        if((Get-Item -LiteralPath $dtapJevPreflight).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse key reference rejected before start claim.'}
        if(Test-Path -LiteralPath "$dtapOutput/keys"){throw 'Existing utility start preserved; do not rerun.'}
        if(Test-Path -LiteralPath "$dtapOutput/broker-start.lock"){throw 'Utility is one shot; existing start claim preserved.'}
    }
    $dtapLockPath="$dtapOutput/broker-start.lock"
    $dtapHaveLock=$false
    try{
        if($QueryRouting){
            $dtapSharedPath="$dtapProject/artifacts/20261018-dtap-os100/utility-cumulative-start.lock"
            try{$dtapShared=[IO.File]::Open($dtapSharedPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)}catch [IO.IOException]{throw 'UTILITY_CUMULATIVE_START_ALREADY_CLAIMED: no fork replay.'}
            try{$dtapClaimBytes=[Text.Encoding]::ASCII.GetBytes($ManifestSha256);$dtapShared.Write($dtapClaimBytes,0,$dtapClaimBytes.Length)}finally{$dtapShared.Dispose()}
        }
        try{$dtapLock=[IO.File]::Open($dtapLockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);$dtapHaveLock=$true}catch [IO.IOException]{}
        if($dtapHaveLock){
            if([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)){throw 'OPENAI_API_KEY must already be set in this PowerShell. It is used only after this explicit opt-in.'}
            $dtapJev="$dtapProject/artifacts/runtime-jev-eval/key/jev.api-key"
            if(-not(Test-Path -LiteralPath $dtapJev -PathType Leaf)){throw 'The existing RO Jev key reference is unavailable.'}
            if((Get-Item -LiteralPath $dtapJev).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse-point key references are not accepted.'}
            $dtapKeys="$dtapOutput/keys"
            if(Test-Path -LiteralPath $dtapKeys){throw 'Existing benchmark key directory preserved; inspect the interrupted start.'}
            New-Item -ItemType Directory -Path $dtapKeys | Out-Null
            $dtapAcl=New-Object Security.AccessControl.DirectorySecurity
            $dtapAcl.SetAccessRuleProtection($true,$false)
            $dtapIdentity=[Security.Principal.WindowsIdentity]::GetCurrent().User
            foreach($dtapSid in @($dtapIdentity,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))){
                $dtapAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($dtapSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
            }
            Set-Acl -LiteralPath $dtapKeys -AclObject $dtapAcl
            [IO.File]::WriteAllText("$dtapKeys/openai.api-key",$env:OPENAI_API_KEY,[Text.UTF8Encoding]::new($false))
            Copy-Item -LiteralPath $dtapJev -Destination "$dtapKeys/jev.api-key"
            @{manifest_sha256=$ManifestSha256;max_total_micro_usd=$dtapPlan.manifest.limits.total.micro_usd;authorized_by='EXPLICIT_USER_POWERSHELL_COMMAND'} | ConvertTo-Json -Compress | Set-Content -Encoding ascii -LiteralPath "$dtapOutput/broker-data/paid-opt-in.json"
            Invoke-DtapTool 'broker' -Socket
        }else{
            if($UtilityAcceptance){throw 'Utility is one shot; another start already claimed this revision.'}
            $dtapWait=0
            while(-not(Test-Path -LiteralPath "$dtapOutput/broker-container.json")){
                if($dtapWait++ -ge 60){throw 'The first-window broker start did not finish; preserve the lock and inspect its error.'}
                Start-Sleep -Milliseconds 500
            }
        }
    }finally{if($dtapHaveLock){$dtapLock.Dispose()}}
    Write-Host 'Frozen cumulative cap; no automatic approval, refund or UNKNOWN replay.'
    Invoke-DtapTool 'run' -Socket -Network $dtapPlan.networks.$Arm.name
    exit 0
}
if($Mode -eq 'recover'){
    if(-not $Arm){throw 'recover requires an explicit arm.'}
    $dtapController="$($dtapPlan.experiment)-$Arm-controller"
    $dtapRunning=& docker inspect $dtapController --format '{{.State.Running}}' 2>$null
    if($LASTEXITCODE -eq 0 -and $dtapRunning -eq 'true'){throw 'A controller is still running. Stop it and collect before reconciliation.'}
}
Invoke-DtapTool $Mode



