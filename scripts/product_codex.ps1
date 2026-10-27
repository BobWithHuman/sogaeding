param(
    [ValidateSet('build','prepare','up','check','start','history','security','down')][string]$Mode='check',
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
$productClient=Join-Path $env:LOCALAPPDATA ('WithHuman/Codex/'+$productRootId+'/'+$RuntimeName)
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
    if($Mode -eq 'prepare'){
        if(-not $JevKeyFile){throw 'prepare requires -JevKeyFile. No key is printed or copied.'}
        if(($null -eq $ApproveJevRequests) -ne ($null -eq $ApproveJevInputTokens)){throw 'Supply both optional legacy limits or omit both for unlimited usage.'}
        if((Test-Path -LiteralPath $productRuntime) -or (Test-Path -LiteralPath $productClient)){throw 'Existing runtime preserved; choose a new RuntimeName.'}
        $productKey=(Get-Item -LiteralPath $JevKeyFile -ErrorAction Stop)
        if($productKey.PSIsContainer -or ($productKey.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'A regular external Jev key file is required.'}
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
        @{key_file=$productKey.FullName;control_port=$ControlPort;gateway_port=$GatewayPort;workspace=$productRoot} | ConvertTo-Json | Set-Content -LiteralPath $productSettings -Encoding utf8
        Assert-PrivateClient
        Write-Host 'Prepared new Codex connector; model requests 0. Use up, check, then start.'
        return
    }
    if(-not (Test-Path -LiteralPath $productSettings)){throw 'Run product_codex.ps1 -Mode prepare first.'}
    if($Mode -ne 'down'){Assert-PrivateClient}
    $productConnection=Get-Content -LiteralPath $productSettings -Raw | ConvertFrom-Json
    $env:SOGAEDING_JEV_KEY_FILE=$productConnection.key_file
    $env:SOGAEDING_JEV_POLICY_FILE=$productPolicyFile
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
