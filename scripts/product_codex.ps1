param(
    [ValidateSet('build','prepare','attach','up','check','start','history','security','down')][string]$Mode='check',
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,47}$')][string]$RuntimeName='codex-gate6',
    [string]$JevKeyFile='',
    [ValidateRange(1,1000)][Nullable[int]]$ApproveJevRequests,
    [ValidateRange(64000,64000000)][Nullable[int]]$ApproveJevInputTokens,
    [string]$PythonPath='', [string]$CodexPath='',
    [ValidateRange(1024,65535)][int]$ControlPort=8130,
    [ValidateRange(1024,65535)][int]$GatewayPort=8140
)
$ErrorActionPreference='Stop'
$productRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$productRuntime=Join-Path $productRoot ('artifacts/team-dev/'+$RuntimeName)
$productHash=[Security.Cryptography.SHA256]::Create()
try{$productRootId=([BitConverter]::ToString($productHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($productRoot.ToLowerInvariant())))).Replace('-','').Substring(0,8).ToLowerInvariant()}finally{$productHash.Dispose()}
$productClientRelative='WithHuman/Codex/'+$productRootId+'/'+$RuntimeName
$productClient=Join-Path $env:LOCALAPPDATA $productClientRelative
# Packaged/isolated terminals can redirect LOCALAPPDATA even for this same user.
# Reuse an existing normal-user connector; never copy credentials or re-prepare
# a running engine merely because this process has a different environment.
$productUserProfile=[Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
if($productUserProfile -and $Mode -notin @('build','attach')){
    $productUserClient=Join-Path (Join-Path $productUserProfile 'AppData/Local') $productClientRelative
    if(-not (Test-Path -LiteralPath (Join-Path $productClient 'connection.json')) -and
       (Test-Path -LiteralPath (Join-Path $productUserClient 'connection.json'))){
        $productClient=$productUserClient
    }
}
$productHost=Join-Path $productClient 'host'
$productSettings=Join-Path $productClient 'connection.json'
$productPolicyFile=Join-Path $productRuntime 'jev-policy.json'
function Assert-ProductPath([string]$Path){
    $productAncestor=[IO.DirectoryInfo]::new([IO.Path]::GetFullPath($Path))
    while($null -ne $productAncestor){
        if($productAncestor.Exists -and ($productAncestor.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Client path cannot traverse a link.'}
        $productAncestor=$productAncestor.Parent
    }
}
Assert-ProductPath $productClient
function Protect-ProductDirectory([string]$Path){
    if((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Private client directory cannot be a link.'}
    $productOwner=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $productAcl=[Security.AccessControl.DirectorySecurity]::new()
    $productAcl.SetOwner($productOwner)
    $productAcl.SetAccessRuleProtection($true,$false)
    foreach($productSidValue in @($productOwner.Value,'S-1-5-18','S-1-5-32-544') | Select-Object -Unique){
        $productSid=[Security.Principal.SecurityIdentifier]::new($productSidValue)
        $productRule=[Security.AccessControl.FileSystemAccessRule]::new($productSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $productAcl.AddAccessRule($productRule)
    }
    Set-Acl -LiteralPath $Path -AclObject $productAcl
    $productVerified=Get-Acl -LiteralPath $Path
    $productAllowed=@($productOwner.Value,'S-1-5-18','S-1-5-32-544')
    if(-not $productVerified.AreAccessRulesProtected){throw 'Private directory ACL inheritance remains enabled.'}
    foreach($productRule in $productVerified.Access){
        if($productRule.AccessControlType -eq 'Allow' -and $productAllowed -notcontains $productRule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value){throw 'Unexpected client credential access rule.'}
    }
}
function Assert-PrivateProviderKey([string]$Path){
    Assert-ProductPath ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Path)))
    $productKeyItem=Get-Item -LiteralPath $Path -ErrorAction Stop
    if($productKeyItem.PSIsContainer -or ($productKeyItem.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'A regular external Jev key file is required.'}
    $productAllowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
    $productParentAcl=Get-Acl -LiteralPath $productKeyItem.DirectoryName
    if($productAllowed -notcontains $productParentAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value){throw 'External Jev key directory has an untrusted owner.'}
    $productWriteRights=[Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
    foreach($productRule in $productParentAcl.Access){
        if($productRule.AccessControlType -eq 'Allow' -and ($productRule.FileSystemRights -band $productWriteRights) -and $productAllowed -notcontains $productRule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value){throw 'External Jev key directory permits changes by another principal.'}
    }
    $productKeyAcl=Get-Acl -LiteralPath $productKeyItem.FullName
    if($productAllowed -notcontains $productKeyAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value){throw 'External Jev key owner must be the current user, SYSTEM or Administrators.'}
    foreach($productRule in $productKeyAcl.Access){
        if($productRule.AccessControlType -eq 'Allow' -and $productAllowed -notcontains $productRule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value){throw 'External Jev key ACL grants access to another principal; restrict its ACL before continuing.'}
    }
}
function Assert-PrivateClient {
    $productAllowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
    foreach($productItem in @((Get-Item -LiteralPath $productClient)) + @(Get-ChildItem -LiteralPath $productClient -Recurse -Force)){
        if($productItem.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Private client cannot contain links.'}
        $productItemAcl=Get-Acl -LiteralPath $productItem.FullName
        foreach($productItemRule in $productItemAcl.Access){
            if($productItemRule.AccessControlType -eq 'Allow' -and $productAllowed -notcontains $productItemRule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value){throw 'Client credential ACL verification failed.'}
        }
    }
}
if(-not $PythonPath){
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if(-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)){$PythonPath=(Get-Command python -CommandType Application -ErrorAction Stop).Source}
}
function Invoke-ProductPython {
    & $PythonPath -X utf8 -I (Join-Path $productRoot 'tools/product_codex.py') @args
    if($LASTEXITCODE -ne 0){throw 'Product connection failed. No implicit retry.'}
}
$productEnvNames=@('SOGAEDING_JEV_KEY_FILE','SOGAEDING_JEV_POLICY_FILE','SOGAEDING_TEAM_IMAGE')
$productPrior=@{}
foreach($productEnvName in $productEnvNames){$productPrior[$productEnvName]=[Environment]::GetEnvironmentVariable($productEnvName,'Process')}
Push-Location -LiteralPath $productRoot
try {
    $env:SOGAEDING_TEAM_IMAGE='with-human-engine:local'
    if($Mode -eq 'build'){
        & (Join-Path $PSScriptRoot 'team_dev.ps1') -Mode build
        if($LASTEXITCODE -ne 0){throw 'Product image build failed.'}
        return
    }
    if($Mode -eq 'attach'){
        # Reconstruct this terminal's connector only. Never recreate/alter the
        # existing volume, grant, certificates, tokens, policy or usage ledger.
        if(Test-Path -LiteralPath $productClient){throw "Existing connector directory preserved at '$productClient'. Use check, or inspect access from this terminal."}
        $productPrepared=Get-Content -LiteralPath (Join-Path $productRuntime 'prepared.json') -Raw -ErrorAction Stop | ConvertFrom-Json
        $productProject='sogaeding-team-'+$productRootId+'-'+$RuntimeName
        if($productPrepared.volume -ne ($productProject+'-runtime') -or $productPrepared.root_id -ne $productRootId){throw 'Prepared runtime identity mismatch.'}
        $productRunning=@{}
        foreach($productRole in @('control','gateway')){
            $productInspectText=@(& docker inspect ($productProject+'-'+$productRole+'-1'))
            if($LASTEXITCODE -ne 0){throw 'Running product services not visible to this terminal. Check Docker context; no runtime was changed.'}
            $productInspect=@(($productInspectText -join "`n") | ConvertFrom-Json)[0]
            if($productInspect.Config.Labels.'com.docker.compose.project' -ne $productProject -or -not $productInspect.State.Running){throw 'Running product identity mismatch.'}
            $productMountedRuntime=@($productInspect.Mounts | Where-Object {$_.Destination -eq '/runtime'})
            if($productMountedRuntime.Count -ne 1 -or $productMountedRuntime[0].Name -ne $productPrepared.volume){throw 'Running volume identity mismatch.'}
            $productRunning[$productRole]=$productInspect
        }
        $productControlBindings=@($productRunning.control.NetworkSettings.Ports.'8030/tcp')
        $productGatewayBindings=@($productRunning.gateway.NetworkSettings.Ports.'8040/tcp')
        if($productControlBindings.Count -ne 1 -or $productGatewayBindings.Count -ne 1 -or
           $productControlBindings[0].HostIp -ne '127.0.0.1' -or $productGatewayBindings[0].HostIp -ne '127.0.0.1'){
            throw 'Exactly one loopback port is required for each service.'
        }
        $ControlPort=[int]$productControlBindings[0].HostPort
        $GatewayPort=[int]$productGatewayBindings[0].HostPort
        if($ControlPort -lt 1024 -or $GatewayPort -lt 1024 -or $ControlPort -eq $GatewayPort){throw 'Invalid running ports.'}
        if(-not $JevKeyFile){
            $productKeyMount=@($productRunning.control.Mounts | Where-Object {$_.Destination -eq '/jev-key/jev.api-key'})
            if($productKeyMount.Count -ne 1 -or $productKeyMount[0].Type -ne 'bind'){throw 'External key mount not found. Supply -JevKeyFile for this existing runtime.'}
            $JevKeyFile=$productKeyMount[0].Source
            if($JevKeyFile -match '^/(?:run/desktop/mnt/host|host_mnt)/([a-z])/(.+)$'){$JevKeyFile=$Matches[1]+':/'+$Matches[2]}
        }
        $productKey=Get-Item -LiteralPath $JevKeyFile -ErrorAction Stop
        Assert-PrivateProviderKey $productKey.FullName
        if(-not (Test-Path -LiteralPath $productPolicyFile -PathType Leaf)){throw 'Existing Jev policy file not visible. No policy or usage was reset.'}
        $productBundleText=@(& docker run --rm --log-driver none --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp `
            -e PYTHONDONTWRITEBYTECODE=1 --mount "type=bind,source=$productRoot/tools,target=/tools,readonly" `
            --mount "type=volume,source=$($productPrepared.volume),target=/team,readonly" `
            with-human-engine:local python /tools/product_codex.py export-bundle --include-metadata --runtime ('/team/artifacts/team-dev/'+$RuntimeName))
        if($LASTEXITCODE -ne 0){throw 'Existing connector export failed; runtime unchanged.'}
        $productBundle=($productBundleText -join '') | ConvertFrom-Json
        if($productBundle.format -ne 'product-connector-bundle-1' -or @($productBundle.roles.PSObject.Properties).Count -ne 4){throw 'Invalid connector bundle.'}
        if($null -ne $productBundle.adapter){throw 'This deployment supports the enrolled file adapter only.'}
        New-Item -ItemType Directory -Path $productClient -ErrorAction Stop | Out-Null
        Protect-ProductDirectory $productClient
        New-Item -ItemType Directory -Path $productHost -ErrorAction Stop | Out-Null
        foreach($productRoleName in @('ca.pem','machine.id','machine.token','human.token')){
            $productRoleBytes=[Convert]::FromBase64String($productBundle.roles.$productRoleName)
            if($productRoleBytes.Length -lt 1 -or $productRoleBytes.Length -gt 8192){throw 'Invalid client role.'}
            [IO.File]::WriteAllBytes((Join-Path $productHost $productRoleName),$productRoleBytes)
        }
        $productProfile=@{format='product-codex-1';workspace=$productRoot;engine_workspace='/files';mcp_only=$true;control_url=('https://127.0.0.1:'+$ControlPort);gateway_url=('https://127.0.0.1:'+$GatewayPort+'/mcp')}
        $productConnectionSettings=@{key_file=$productKey.FullName;control_port=$ControlPort;gateway_port=$GatewayPort;workspace=$productRoot}
        [IO.File]::WriteAllText((Join-Path $productHost 'profile.json'),($productProfile | ConvertTo-Json))
        $productConnectionSettings | ConvertTo-Json | Set-Content -LiteralPath $productSettings -Encoding utf8
        Assert-PrivateClient
        $productBundle=$null; $productBundleText=$null; $productRoleBytes=$null
        Invoke-ProductPython check --host $productHost
        Write-Host 'Attached this terminal to the existing runtime; no engine restart, token rotation, policy change or model request.'
        return
    }
    if($Mode -eq 'prepare'){
        if(-not $JevKeyFile){throw 'prepare requires -JevKeyFile. No key is printed or copied.'}
        if(($null -eq $ApproveJevRequests) -ne ($null -eq $ApproveJevInputTokens)){throw 'Supply both optional legacy limits or omit both for unlimited usage.'}
        if((Test-Path -LiteralPath $productRuntime) -or (Test-Path -LiteralPath $productClient)){throw 'Existing runtime preserved; choose a new RuntimeName.'}
        $productKey=(Get-Item -LiteralPath $JevKeyFile -ErrorAction Stop)
        Assert-PrivateProviderKey $productKey.FullName
        & (Join-Path $PSScriptRoot 'team_dev.ps1') -Mode build
        if($LASTEXITCODE -ne 0){throw 'Product image build failed.'}
        & (Join-Path $PSScriptRoot 'team_dev.ps1') -Mode prepare -RuntimeName $RuntimeName -ControlPort $ControlPort -GatewayPort $GatewayPort
        if($LASTEXITCODE -ne 0){throw 'Runtime preparation failed.'}
        $productPrepared=Get-Content -LiteralPath (Join-Path $productRuntime 'prepared.json') -Raw | ConvertFrom-Json
        if($productPrepared.volume -ne ('sogaeding-team-'+$productRootId+'-'+$RuntimeName+'-runtime') -or $productPrepared.root_id -ne $productRootId){throw 'Prepared runtime identity mismatch.'}
        New-Item -ItemType Directory -Path $productClient | Out-Null
        Protect-ProductDirectory $productClient
        $productPolicy=@{enabled=$true;model='jev-1.13.0';request_limit=$ApproveJevRequests;input_token_limit=$ApproveJevInputTokens;policy_id=('codex-gate6-'+$RuntimeName)}
        if($null -eq $ApproveJevRequests){$productPolicy.unlimited=$true}
        [IO.File]::WriteAllText($productPolicyFile,($productPolicy | ConvertTo-Json))
        # Capture only in memory. Windows creates files under the private DACL;
        # Docker Desktop file creation does not preserve Windows ACL inheritance.
        $productBundleText=@(& docker run --rm --log-driver none --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp `
            -e PYTHONDONTWRITEBYTECODE=1 --mount "type=bind,source=$productRoot/tools,target=/tools,readonly" `
            --mount "type=volume,source=$($productPrepared.volume),target=/team,readonly" `
            with-human-engine:local python /tools/product_codex.py export-bundle --runtime ('/team/artifacts/team-dev/'+$RuntimeName))
        if($LASTEXITCODE -ne 0){throw 'Client credential export failed; runtime preserved.'}
        $productBundle=($productBundleText -join '') | ConvertFrom-Json
        $productRoleNames=@('ca.pem','machine.id','machine.token','human.token')
        if(@($productBundle.PSObject.Properties).Count -ne 4){throw 'Invalid client bundle.'}
        New-Item -ItemType Directory -Path $productHost | Out-Null
        foreach($productRoleName in $productRoleNames){
            $productRoleBytes=[Convert]::FromBase64String($productBundle.$productRoleName)
            if($productRoleBytes.Length -lt 1 -or $productRoleBytes.Length -gt 8192){throw 'Invalid client bundle.'}
            [IO.File]::WriteAllBytes((Join-Path $productHost $productRoleName),$productRoleBytes)
        }
        $productBundle=$null; $productBundleText=$null; $productRoleBytes=$null
        $productProfile=@{format='product-codex-1';workspace=$productRoot;engine_workspace='/files';mcp_only=$true;control_url=('https://127.0.0.1:'+$ControlPort);gateway_url=('https://127.0.0.1:'+$GatewayPort+'/mcp')}
        [IO.File]::WriteAllText((Join-Path $productHost 'profile.json'),($productProfile | ConvertTo-Json))
        $productConnectionSettings=@{key_file=$productKey.FullName;control_port=$ControlPort;gateway_port=$GatewayPort;workspace=$productRoot}
        $productConnectionSettings | ConvertTo-Json | Set-Content -LiteralPath $productSettings -Encoding utf8
        Assert-PrivateClient
        Write-Host 'Prepared new Codex connector; model requests 0. Use up, check, then start.'
        return
    }
    if(-not (Test-Path -LiteralPath $productSettings)){
        if(Test-Path -LiteralPath (Join-Path $productRuntime 'prepared.json')){
            throw "Engine runtime exists, but connector settings were not found at '$productSettings'. In this PowerShell, run: powershell.exe -NoProfile -File .\scripts\product_codex.ps1 -Mode attach -RuntimeName $RuntimeName . Existing runtime preserved; do not prepare it again."
        }
        throw "Connector settings not found at '$productSettings'. Run product_codex.ps1 -Mode prepare first."
    }
    if($Mode -ne 'down'){Assert-PrivateClient}
    $productConnection=Get-Content -LiteralPath $productSettings -Raw | ConvertFrom-Json
    if($Mode -eq 'up'){Assert-PrivateProviderKey $productConnection.key_file}
    $env:SOGAEDING_JEV_KEY_FILE=$productConnection.key_file
    $env:SOGAEDING_JEV_POLICY_FILE=$productPolicyFile
    if($productConnection.adapter){throw 'This deployment supports the enrolled file adapter only.'}
    if($Mode -in @('up','down')){
        & (Join-Path $PSScriptRoot 'team_dev.ps1') -Mode $Mode -RuntimeName $RuntimeName -ControlPort $productConnection.control_port -GatewayPort $productConnection.gateway_port
        if($LASTEXITCODE -ne 0){throw 'Product services command failed.'}
    } elseif($Mode -eq 'start') {
        if(-not $CodexPath){$CodexPath=(Get-Command codex.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source}
        Invoke-ProductPython start --host $productHost --exe $CodexPath
    } else {
        if($Mode -eq 'check'){
            if(-not $CodexPath){$CodexPath=(Get-Command codex.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source}
            Invoke-ProductPython cli-check --host $productHost --exe $CodexPath
        }
        Invoke-ProductPython $Mode --host $productHost
    }
} finally {
    Pop-Location
    foreach($productEnvName in $productEnvNames){[Environment]::SetEnvironmentVariable($productEnvName,$productPrior[$productEnvName],'Process')}
}
