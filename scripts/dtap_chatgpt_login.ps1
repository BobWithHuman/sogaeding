param(
    [ValidateSet('login','account-check','logout','prepare','check','run','status','collect','stop')][string]$Mode='check',
    [ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
    [ValidateSet('engine-off','engine-on')][string]$Arm,
    [ValidatePattern('^[a-z0-9-]{1,32}$')][string]$Account='main',
    [decimal]$MaxTotalUsd=5.089294,
    [switch]$StartEvaluation
)
$ErrorActionPreference='Stop'
$loginProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).Replace('\','/')
$loginRoot="$loginProject/artifacts/20261018-dtap-os100/user-chatgpt-login-luna-stream1"
$loginParent="$loginProject/artifacts/20261018-dtap-os100/user-query-utility"
$loginCredentials="$loginProject/artifacts/runtime-dtap-chatgpt-login"
$loginWorker='sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d'
if($MaxTotalUsd -ne [decimal]5.089294){throw 'Exact cumulative USD5.089294 cap required; no budget increase.'}
function Protect-LoginFolder([string]$Path){
    if(-not(Test-Path -LiteralPath $Path)){New-Item -ItemType Directory -Path $Path | Out-Null}
    if((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse directory rejected.'}
    $loginAcl=New-Object Security.AccessControl.DirectorySecurity
    $loginAcl.SetAccessRuleProtection($true,$false)
    foreach($loginSid in @([Security.Principal.WindowsIdentity]::GetCurrent().User,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))){
        $loginAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($loginSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    # Persist modified DACL entries only. Set-Acl can request SACL privileges on
    # an already protected directory, even when no audit rules were requested.
    if($PSVersionTable.PSEdition -eq 'Core'){
        [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($Path),$loginAcl)
    }else{
        [IO.Directory]::SetAccessControl($Path,$loginAcl)
    }
    foreach($loginChild in @(Get-ChildItem -LiteralPath $Path -Force -Recurse)){
        if($loginChild.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Credential/artifact reparse child rejected.'}
        if($loginChild.PSIsContainer){$loginChildAcl=New-Object Security.AccessControl.DirectorySecurity}else{$loginChildAcl=New-Object Security.AccessControl.FileSecurity}
        $loginChildAcl.SetAccessRuleProtection($true,$false)
        foreach($loginSid in @([Security.Principal.WindowsIdentity]::GetCurrent().User,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))){
            $loginRule=if($loginChild.PSIsContainer){New-Object Security.AccessControl.FileSystemAccessRule($loginSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')}else{New-Object Security.AccessControl.FileSystemAccessRule($loginSid,'FullControl','Allow')}
            $loginChildAcl.AddAccessRule($loginRule)
        }
        if($loginChild.PSIsContainer){
            if($PSVersionTable.PSEdition -eq 'Core'){
                [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]$loginChild,$loginChildAcl)
            }else{
                [IO.Directory]::SetAccessControl($loginChild.FullName,$loginChildAcl)
            }
        }else{
            if($PSVersionTable.PSEdition -eq 'Core'){
                [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]$loginChild,$loginChildAcl)
            }else{
                [IO.File]::SetAccessControl($loginChild.FullName,$loginChildAcl)
            }
        }
    }
}
function Invoke-Account([string]$Operation){
    Protect-LoginFolder $loginCredentials
    $loginSource=if(Test-Path -LiteralPath "$loginRoot/plan.json"){"$loginRoot/source"}else{$loginProject}
    $loginArgs=@('run','--rm','--read-only','--cap-drop','ALL','--tmpfs','/tmp:rw',
        '--mount',"type=bind,source=$loginSource,target=/project,readonly",'--mount',"type=bind,source=$loginCredentials,target=/credentials",
        '-e','PYTHONPATH=/project/src:/benchdeps:/vendor','-e','CONTRACT_DIR=/project/docs/mvp/contracts','-e','PYTHONDONTWRITEBYTECODE=1','-e','DTAP_WINDOWS_HOST_ACL=1')
    if($Operation -eq 'login'){
        $loginArgs=@('run','-d','--name','with-human-dtap-siwc-login','--read-only','--cap-drop','ALL','--tmpfs','/tmp:rw','-p','127.0.0.1:1459:1459')+$loginArgs[7..($loginArgs.Length-1)]
    }
    $loginArgs+=@($loginWorker,'python','/project/tools/dtap_chatgpt_login.py',$Operation,'--account',$Account)
    if($Operation -ne 'login'){
        & docker @loginArgs
        if($LASTEXITCODE -ne 0){throw 'SIWC account/model unavailable; no inference or API fallback.'}
        return
    }
    if(Test-Path -LiteralPath "$loginCredentials/authorization-url.json"){throw 'Pending authorization preserved; inspect the existing login helper.'}
    $loginId=& docker @loginArgs
    if($LASTEXITCODE -ne 0){throw 'Login helper unavailable; no account settings changed.'}
    try{
        $loginDeadline=(Get-Date).AddSeconds(30)
        while(-not(Test-Path -LiteralPath "$loginCredentials/authorization-url.json")){
            if((Get-Date) -gt $loginDeadline){throw 'Login listener did not become ready.'}
            Start-Sleep -Milliseconds 250
        }
        $loginUrl=(Get-Content -Raw -LiteralPath "$loginCredentials/authorization-url.json" | ConvertFrom-Json).url
        if(-not $loginUrl.StartsWith('https://auth.openai.com/api/accounts/authorize?',[StringComparison]::Ordinal)){throw 'Official authorization URL required.'}
        Start-Process $loginUrl
        Write-Host 'Continue with ChatGPT: sign in and review plan usage consent in the official browser. No inference will start.'
        $loginExit=& docker wait $loginId
        & docker logs $loginId
        if($loginExit -ne '0'){throw 'SIWC login not completed; API fallback disabled.'}
    }finally{& docker rm -f $loginId | Out-Null}
}
function Invoke-LoginRuntime([string]$Operation,[switch]$Initial,[switch]$Socket,[string]$Network='none'){
    $loginSource=if($Initial){$loginProject}else{"$loginRoot/source"}
    $loginUser=if($Initial){'0:10001'}else{'10001:10001'}
    $loginDocker=@('run','--rm','--user',$loginUser,'--read-only','--cap-drop','ALL','--tmpfs','/tmp:rw','--network',$Network,
        '--mount',"type=bind,source=$loginSource,target=/project,readonly",'--mount',"type=bind,source=$loginRoot,target=/experiment",
        '--mount',"type=bind,source=$loginParent,target=/parent,readonly",'-e','PYTHONPATH=/project/src:/benchdeps:/vendor','-e','CONTRACT_DIR=/project/docs/mvp/contracts','-e','PYTHONDONTWRITEBYTECODE=1','-e','DTAP_WINDOWS_HOST_ACL=1')
    if($Socket -and -not $Initial){$loginDocker+=@('--group-add','0')}
    if($Socket){$loginDocker+=@('--mount','type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock')}
    $loginDocker+=@($loginWorker,'python','/project/tools/dtap_runtime.py',$Operation,'--host-root',$loginRoot,'--project-root',$loginProject,'--broker-port','18670','--credentials-host-root',$loginCredentials)
    if($Operation -eq 'init'){$loginDocker+=@('--chatgpt-plan','--parent-host-root',$loginParent)}
    if($ManifestSha256){$loginDocker+=@('--expected-manifest-sha256',$ManifestSha256)}
    if($Arm){$loginDocker+=@('--arm',$Arm)}
    & docker @loginDocker
    if($LASTEXITCODE -ne 0){throw "SIWC runtime $Operation stopped. Preserve ledger/claims; no automatic retry or API fallback."}
}
if($Mode -in @('login','account-check','logout')){
    if($Mode -eq 'logout' -and (Test-Path -LiteralPath "$loginRoot/broker-container.json")){
        Invoke-LoginRuntime 'stop'
        Write-Host 'Both arms stopped before sign-out; an in-flight request may still complete.'
    }
    Invoke-Account $Mode
    exit 0
}
if($Mode -eq 'prepare'){
    if(Test-Path -LiteralPath $loginRoot){throw 'Preparation directory exists; preserve it and use check.'}
    Protect-LoginFolder $loginRoot
    Invoke-LoginRuntime 'init' -Initial -Socket
    exit 0
}
if(-not(Test-Path -LiteralPath "$loginRoot/plan.json")){throw 'Run prepare first; no inference started.'}
$loginPlan=Get-Content -Raw -LiteralPath "$loginRoot/plan.json" | ConvertFrom-Json
if($Mode -eq 'check'){
    Invoke-LoginRuntime 'verify'
    if(Test-Path -LiteralPath "$loginCredentials/$Account.json"){Invoke-Account 'account-check'}else{Write-Host 'ACCOUNT_MODEL_CHECK_PENDING: no dedicated SIWC login; inference NOT_RUN.'}
    exit 0
}
if(-not $ManifestSha256){throw 'Explicit reviewed frozen manifest required.'}
if($Mode -eq 'run'){
    if(-not $StartEvaluation -or -not $Arm -or $Account -ne 'main'){throw 'run requires explicit -StartEvaluation, arm, reviewed main account and manifest.'}
    Invoke-LoginRuntime 'verify'
    Invoke-Account 'account-check'
    foreach($loginImage in $loginPlan.manifest.images.psobject.Properties){
        $loginActualImage=& docker image inspect $loginImage.Value --format '{{.Id}}'
        if($LASTEXITCODE -ne 0 -or ($loginImage.Value -match '^sha256:' -and $loginActualImage -ne $loginImage.Value)){throw 'Frozen image unavailable; no start claim made.'}
    }
    $loginJev="$loginProject/artifacts/runtime-jev-eval/key/jev.api-key"
    if(-not(Test-Path -LiteralPath $loginJev -PathType Leaf) -or ((Get-Item -LiteralPath $loginJev).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Existing Jev key reference required before any claim.'}
    if(Test-Path -LiteralPath "$loginRoot/keys/openai.api-key"){throw 'OpenAI API key forbidden for SIWC.'}
    if(Test-Path -LiteralPath "$loginRoot/$Arm-start.lock"){throw 'Arm already started; no replay.'}
    $loginLock=$null
    try{
        try{$loginLock=[IO.File]::Open("$loginRoot/broker-start.lock",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)}catch [IO.IOException]{}
        if($loginLock){
            Protect-LoginFolder "$loginRoot/keys"
            Copy-Item -LiteralPath $loginJev -Destination "$loginRoot/keys/jev.api-key"
            @{manifest_sha256=$ManifestSha256;max_total_micro_usd=5089294;authorized_by='EXPLICIT_USER_SIWC_COMMAND'} | ConvertTo-Json -Compress | Set-Content -Encoding ascii -LiteralPath "$loginRoot/broker-data/paid-opt-in.json"
            Invoke-LoginRuntime 'broker' -Socket
        }else{
            $loginWait=0
            while(-not(Test-Path -LiteralPath "$loginRoot/broker-container.json")){
                if($loginWait++ -ge 60){throw 'Broker start incomplete; preserve claim and inspect.'}
                Start-Sleep -Milliseconds 500
            }
        }
    }finally{if($loginLock){$loginLock.Dispose()}}
    $loginArmClaim=[IO.File]::Open("$loginRoot/$Arm-start.lock",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $loginArmClaim.Dispose()
    Invoke-LoginRuntime 'run' -Socket -Network $loginPlan.networks.$Arm.name
    exit 0
}
Invoke-LoginRuntime $Mode
