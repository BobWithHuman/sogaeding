param(
    [ValidateSet('start','stop','status')][string]$Mode='start',
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,47}$')][string]$RuntimeName='try-gate6',
    [ValidateRange(1024,65535)][int]$Port=8150
)
$ErrorActionPreference='Stop'
$dashboardRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dashboardHash=[Security.Cryptography.SHA256]::Create()
try{$dashboardId=([BitConverter]::ToString($dashboardHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($dashboardRoot.ToLowerInvariant())))).Replace('-','').Substring(0,8).ToLowerInvariant()}finally{$dashboardHash.Dispose()}
$dashboardRuntime=Join-Path $dashboardRoot ('artifacts/team-dev/'+$RuntimeName)
$dashboardNetworks=Get-Content -LiteralPath (Join-Path $dashboardRuntime 'networks.json') -Raw | ConvertFrom-Json
$dashboardVars=@('SOGAEDING_TEAM_VOLUME','SOGAEDING_TEAM_IMAGE','SOGAEDING_RUNTIME_NAME','SOGAEDING_DASHBOARD_PORT','SOGAEDING_PROTECTED_SUBNET','SOGAEDING_INGRESS_SUBNET')
$dashboardPrior=@{}
foreach($name in $dashboardVars){$dashboardPrior[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try{
    $env:SOGAEDING_TEAM_VOLUME='sogaeding-team-'+$dashboardId+'-'+$RuntimeName+'-runtime'
    $env:SOGAEDING_TEAM_IMAGE='with-human-engine:local'
    $env:SOGAEDING_RUNTIME_NAME=$RuntimeName
    $env:SOGAEDING_DASHBOARD_PORT=[string]$Port
    $env:SOGAEDING_PROTECTED_SUBNET=$dashboardNetworks.protected
    $env:SOGAEDING_INGRESS_SUBNET=$dashboardNetworks.ingress
    $dashboardArgs=@('compose','-p',('sogaeding-team-'+$dashboardId+'-'+$RuntimeName),'-f',(Join-Path $dashboardRoot 'compose.yaml'))
    if($Mode -eq 'start'){& docker @dashboardArgs up -d --no-deps dashboard}
    elseif($Mode -eq 'stop'){& docker @dashboardArgs stop dashboard}
    else{& docker @dashboardArgs ps dashboard}
    if($LASTEXITCODE -ne 0){throw 'Local dashboard command failed.'}
    if($Mode -eq 'start'){Write-Host ('Local dashboard: http://127.0.0.1:'+$Port)}
}finally{foreach($name in $dashboardVars){[Environment]::SetEnvironmentVariable($name,$dashboardPrior[$name],'Process')}}
