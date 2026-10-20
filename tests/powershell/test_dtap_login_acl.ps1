param([Parameter(Mandatory=$true)][string]$EvidenceDirectory)
$ErrorActionPreference='Stop'
$aclProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$aclEvidence=[IO.Path]::GetFullPath($EvidenceDirectory)
$aclAllowedRoot=Join-Path $aclProject 'artifacts/20261020-siwc-acl-fix'
if(-not $aclEvidence.StartsWith($aclAllowedRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Synthetic ACL test must stay within its evidence directory.'
}
$aclTokens=$null; $aclErrors=$null
$aclAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $aclProject 'scripts/dtap_chatgpt_login.ps1'),[ref]$aclTokens,[ref]$aclErrors)
if($aclErrors.Count){throw 'Launcher parse failed.'}
$aclFunction=$aclAst.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Protect-LoginFolder'},$true)
if(-not $aclFunction){throw 'Protection function missing.'}
# Load only the reviewed ACL function; never invoke login, Docker or credentials.
Invoke-Expression $aclFunction.Extent.Text
$aclFixture=Join-Path $aclEvidence 'public-fixture'
Protect-LoginFolder $aclFixture
$aclChild=Join-Path $aclFixture 'nested'
[IO.Directory]::CreateDirectory($aclChild) | Out-Null
$aclFile=Join-Path $aclChild 'public.txt'
[IO.File]::WriteAllText($aclFile,'PUBLIC SYNTHETIC ONLY')
$aclHash=(Get-FileHash -LiteralPath $aclFile -Algorithm SHA256).Hash
$aclWorld=[Security.Principal.SecurityIdentifier]::new('S-1-1-0')
$aclFileSecurity=Get-Acl -LiteralPath $aclFile
$aclFileSecurity.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($aclWorld,'Read','Allow'))
if($PSVersionTable.PSEdition -eq 'Core'){
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($aclFile),$aclFileSecurity)
}else{
    [IO.File]::SetAccessControl($aclFile,$aclFileSecurity)
}
# Repeated protection must work without SeSecurityPrivilege and remove broad ACEs.
Protect-LoginFolder $aclFixture
Protect-LoginFolder $aclFixture
$aclAllowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18')
foreach($aclEntry in @($aclFixture,$aclChild,$aclFile)){
    $aclInfo=Get-Item -LiteralPath $aclEntry
    $aclSaved=Get-Acl -LiteralPath $aclInfo.FullName
    if(-not $aclSaved.AreAccessRulesProtected){throw 'Inheritance unexpectedly enabled.'}
    $aclRules=@($aclSaved.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    if($aclRules.Count -ne 2){throw 'Unexpected access rule count.'}
    foreach($aclRule in $aclRules){
        if($aclRule.IdentityReference.Value -notin $aclAllowed -or $aclRule.AccessControlType -ne 'Allow' -or $aclRule.FileSystemRights -ne 'FullControl'){
            throw 'Credential protection broadened or changed rights.'
        }
    }
}
if((Get-FileHash -LiteralPath $aclFile -Algorithm SHA256).Hash -ne $aclHash){throw 'Synthetic contents changed.'}
[pscustomobject]@{
    result='PASS';powershell=$PSVersionTable.PSVersion.ToString();protection_passes=3;
    checked_entries=3;broad_rule_removed=$true;contents_preserved=$true;
    elevated=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} | ConvertTo-Json -Compress
