param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
    [switch]$SendOneRequest,
    [switch]$CheckLogin
)
$ErrorActionPreference='Stop'
$probeProject='C:\sogaeding'
$probeBase=Join-Path $probeProject 'artifacts/20261020-siwc-protocol-probe-v3'
$probeBundle=Join-Path $probeBase 'bundle'
$probeEvidence=Join-Path $probeBase 'user-one-request-3'
$probeCredentials=Join-Path $probeProject 'artifacts/runtime-dtap-chatgpt-login'
$probeManifestPath=Join-Path $probeBundle 'manifest.json'
if([IO.Path]::GetFullPath($PSCommandPath) -ne [IO.Path]::GetFullPath((Join-Path $probeBundle 'scripts/siwc_protocol_probe.ps1'))){throw 'Use the protected frozen probe launcher only; no request.'}
if((Get-FileHash -LiteralPath $probeManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ManifestSha256){throw 'Probe manifest mismatch; no request.'}
$probeManifest=Get-Content -LiteralPath $probeManifestPath -Raw | ConvertFrom-Json
if((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $probeManifest.sources.'scripts/siwc_protocol_probe.ps1'){throw 'Probe launcher changed; no request.'}
$probeAllowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18')
foreach($probePath in @($probeBase,$probeBundle,$probeEvidence,$probeCredentials)){
    if(-not(Test-Path -LiteralPath $probePath -PathType Container) -or ((Get-Item -LiteralPath $probePath).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Required probe directory missing or reparse point; no request.'}
}
# Protect code and claim against changes by other local users before mounting
# credentials or importing any Python. Manifest paths are pinned by its hash.
$probePrivatePaths=@((Get-Item -LiteralPath $probeBase))+@(Get-ChildItem -LiteralPath $probeBase -Force -Recurse)
foreach($probePrivatePath in $probePrivatePaths){
    if($probePrivatePath.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Probe reparse child rejected; no request.'}
    $probeAccess=(Get-Acl -LiteralPath $probePrivatePath.FullName).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
    foreach($probeRule in $probeAccess){if($probeRule.AccessControlType -eq 'Allow' -and $probeRule.IdentityReference.Value -notin $probeAllowed){throw 'Probe code/evidence ACL broader than user/SYSTEM; no request.'}}
}
foreach($probeSource in $probeManifest.sources.psobject.Properties){
    $probeSourcePath=[IO.Path]::GetFullPath((Join-Path $probeBundle $probeSource.Name))
    if(-not $probeSourcePath.StartsWith($probeBundle+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Probe source outside bundle; no request.'}
    if((Get-FileHash -LiteralPath $probeSourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $probeSource.Value){throw 'Probe source changed before interpreter startup; no request.'}
}
if($SendOneRequest -and $CheckLogin){throw 'Choose auth-only check or one inference request.'}
$probeNetwork=if($SendOneRequest -or $CheckLogin){'bridge'}else{'none'}
$probeDocker=@('run','--rm','--read-only','--cap-drop','ALL','--user','10001:10001','--tmpfs','/tmp:rw','--network',$probeNetwork,
    '--mount',"type=bind,source=$probeBundle,target=/project,readonly",'--mount',"type=bind,source=$probeEvidence,target=/evidence",
    '-e','PYTHONPATH=/project/src:/benchdeps','-e','CONTRACT_DIR=/project/docs/mvp/contracts','-e','PYTHONDONTWRITEBYTECODE=1','-e','DTAP_WINDOWS_HOST_ACL=1')
if($SendOneRequest -or $CheckLogin){
    if($SendOneRequest -and (Test-Path -LiteralPath (Join-Path $probeEvidence 'one-request.claim'))){throw 'Probe already claimed; inspect result.json; no retry.'}
    # Existing protected SIWC store only. No OpenAI/TypeSafe API key or Docker socket mount.
    $probeAclPaths=@((Get-Item -LiteralPath $probeCredentials))+@(Get-ChildItem -LiteralPath $probeCredentials -Force -Recurse)
    foreach($probeAclPath in $probeAclPaths){
        if($probeAclPath.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'SIWC credential reparse child rejected; no request.'}
        $probeAccess=(Get-Acl -LiteralPath $probeAclPath.FullName).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
        foreach($probeRule in $probeAccess){if($probeRule.AccessControlType -eq 'Allow' -and $probeRule.IdentityReference.Value -notin $probeAllowed){throw 'Existing SIWC credential ACL is broader than user/SYSTEM; no request.'}}
    }
    $probeDocker+=@('--mount',"type=bind,source=$probeCredentials,target=/credentials")
}
$probeDocker+=@('sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d','python','/project/tools/siwc_protocol_probe.py','--manifest-sha256',$ManifestSha256)
if($SendOneRequest){$probeDocker+='--send-one-request'}
if($CheckLogin){$probeDocker+='--check-login'}
& docker @probeDocker
if($LASTEXITCODE -ne 0){throw 'Diagnostic stopped; preserve claim and result; no automatic retry.'}
