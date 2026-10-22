param(
    [ValidateSet('build','prepare','up','check','test','down','export')]
    [string]$Mode = 'check',
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,47}$')]
    [string]$RuntimeName = 'default',
    [ValidateRange(1024,65535)][int]$ControlPort = 8130,
    [ValidateRange(1024,65535)][int]$GatewayPort = 8140,
    [string]$ExportPath = ''
)
$ErrorActionPreference = 'Stop'
$teamRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$teamRuntime = Join-Path $teamRoot ('artifacts/team-dev/' + $RuntimeName)
$teamImage = 'sogaeding-team-dev:local'
$teamHash = [Security.Cryptography.SHA256]::Create()
try { $teamRootId = ([BitConverter]::ToString($teamHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($teamRoot.ToLowerInvariant())))).Replace('-','').Substring(0,8).ToLowerInvariant() } finally { $teamHash.Dispose() }
$teamProject = 'sogaeding-team-' + $teamRootId + '-' + $RuntimeName
$teamVolume = $teamProject + '-runtime'
if ($ControlPort -eq $GatewayPort) { throw 'Control and gateway ports must differ.' }
function Invoke-TeamDocker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Team Docker command failed (exit $LASTEXITCODE). Existing evidence is preserved." }
}
$teamNames = @('SOGAEDING_TEAM_RUNTIME','SOGAEDING_CONTROL_PORT','SOGAEDING_GATEWAY_PORT','SOGAEDING_PROTECTED_SUBNET','SOGAEDING_INGRESS_SUBNET','SOGAEDING_TEAM_VOLUME','SOGAEDING_RUNTIME_NAME')
$teamPrevious = @{}
foreach ($teamName in $teamNames) { $teamPrevious[$teamName] = [Environment]::GetEnvironmentVariable($teamName, 'Process') }
Push-Location -LiteralPath $teamRoot
try {
    $env:SOGAEDING_TEAM_RUNTIME = $teamRuntime.Replace('\','/')
    $env:SOGAEDING_CONTROL_PORT = [string]$ControlPort
    $env:SOGAEDING_GATEWAY_PORT = [string]$GatewayPort
    $env:SOGAEDING_TEAM_VOLUME = $teamVolume
    $env:SOGAEDING_RUNTIME_NAME = $RuntimeName
    if ($Mode -eq 'up' -and -not (Test-Path -LiteralPath (Join-Path $teamRuntime 'prepared.json'))) { throw 'Run -Mode prepare with this RuntimeName first.' }
    $teamNetworkFile = Join-Path $teamRuntime 'networks.json'
    if ($Mode -eq 'up' -and -not (Test-Path -LiteralPath $teamNetworkFile)) {
        $teamNetworkIds = @(& docker network ls -q)
        if ($LASTEXITCODE -ne 0) { throw 'Docker network inventory unavailable.' }
        $teamNetworkInventory = '[]'
        if ($teamNetworkIds.Count) {
            $teamNetworkInventory = (& docker network inspect @teamNetworkIds) -join "`n"
            if ($LASTEXITCODE -ne 0) { throw 'Docker network inspection unavailable.' }
        }
        $teamSelectedNetworks = $teamNetworkInventory | & docker run --rm -i --read-only --cap-drop ALL --network none --tmpfs /tmp `
            --mount "type=bind,source=$teamRoot/tools,target=/tools,readonly" $teamImage python /tools/team_runtime.py networks
        if ($LASTEXITCODE -ne 0) { throw 'No non-overlapping team subnets selected; existing networks preserved.' }
        $teamSelectedNetworks | ConvertFrom-Json | ConvertTo-Json | Set-Content -LiteralPath $teamNetworkFile -Encoding utf8
    }
    if (Test-Path -LiteralPath $teamNetworkFile) {
        $teamNetworkSettings = Get-Content -LiteralPath $teamNetworkFile -Raw | ConvertFrom-Json
        $env:SOGAEDING_PROTECTED_SUBNET = $teamNetworkSettings.protected
        $env:SOGAEDING_INGRESS_SUBNET = $teamNetworkSettings.ingress
    }
    switch ($Mode) {
        'build' { Invoke-TeamDocker build --target dev -f Dockerfile.dev -t $teamImage . }
        'prepare' {
            if (Test-Path -LiteralPath $teamRuntime) { throw 'Existing team runtime preserved. Choose a new RuntimeName.' }
            $teamExisting = @(& docker volume ls --format '{{.Name}}')
            if ($LASTEXITCODE -ne 0 -or $teamExisting -contains $teamVolume) { throw 'Existing/unavailable volume preserved. Choose a new RuntimeName.' }
            Invoke-TeamDocker volume create --label ('sogaeding.team=' + $teamProject) $teamVolume
            Invoke-TeamDocker run --rm --read-only --user 0:0 --cap-drop ALL --cap-add CHOWN --network none `
                --mount "type=volume,source=$teamVolume,target=/team" $teamImage python -c "import os; os.chown('/team',10001,10001)"
            Invoke-TeamDocker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --network none --tmpfs /tmp `
                --mount "type=bind,source=$teamRoot/tools,target=/tools,readonly" --mount "type=volume,source=$teamVolume,target=/team" `
                $teamImage python /tools/team_runtime.py prepare /team --name $RuntimeName
            New-Item -ItemType Directory -Path $teamRuntime -Force | Out-Null
            @{volume=$teamVolume;root_id=$teamRootId;provider='disabled'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $teamRuntime 'prepared.json') -Encoding utf8
        }
        'up' {
            Invoke-TeamDocker compose -p $teamProject -f compose.team.yaml up -d control upstream gateway
        }
        'check' { Invoke-TeamDocker compose -p $teamProject -f compose.team.yaml run --rm --no-deps check }
        'test' {
            Invoke-TeamDocker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --network none --tmpfs /tmp `
                --mount "type=bind,source=$teamRoot,target=/workspace,readonly" -w /workspace `
                -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/workspace/src:/workspace/tests/hookgw:/workspace/tools `
                -e CONTRACT_DIR=/workspace/docs/mvp/contracts $teamImage python -m pytest -q -p no:cacheprovider `
                tests/hookgw/test_engine.py tests/hookgw/test_jev_policy.py tests/hookgw/test_jev_response_contract.py `
                tests/hookgw/test_demo_confirm_adapter.py tests/hookgw/test_core_auth_audit.py tests/hookgw/test_team_share.py `
                tests/hookgw/test_default_candidate_policy.py
        }
        'down' { Invoke-TeamDocker compose -p $teamProject -f compose.team.yaml down }
        'export' {
            if (-not $ExportPath) { throw '-ExportPath must name a new directory.' }
            $teamPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
            if (-not $teamPython) { throw 'Export requires Python 3 on PATH; runtime build/check/test use Docker only.' }
            & $teamPython.Source -X utf8 tools/repository_export.py --root $teamRoot --output $ExportPath
            if ($LASTEXITCODE -ne 0) { throw 'Source export rejected; inspect its path-only diagnostics.' }
        }
    }
} finally {
    foreach ($teamName in $teamNames) { [Environment]::SetEnvironmentVariable($teamName, $teamPrevious[$teamName], 'Process') }
    Pop-Location
}
