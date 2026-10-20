param([ValidateSet('prepare','install','start','status','history','approve','reject')][string]$Mode='status', [string]$Call='')
$ErrorActionPreference='Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $project
$python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python=(Get-Command python -CommandType Application -ErrorAction Stop).Source }
$hostPath=Join-Path $project 'artifacts/runtime-hookgw/host'
function Invoke-HookgwDocker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $LASTEXITCODE" }
}
function Install-HookgwRuntime {
    foreach ($role in @('control','gateway','upstream','product')) {
        Invoke-HookgwDocker volume create ('with-human-hookgw-runtime-' + $role)
    }
    $runtimePath=Join-Path $project 'artifacts/runtime-hookgw'
    $toolPath=Join-Path $project 'tools/hookgw_install.py'
    Invoke-HookgwDocker run --rm --network none --user 0:0 --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE --cap-add FOWNER `
        --mount "type=bind,source=$runtimePath,target=/new-runtime,readonly" `
        --mount "type=bind,source=$toolPath,target=/install.py,readonly" `
        --mount 'type=volume,source=with-human-hookgw-runtime-control,target=/installed/control' `
        --mount 'type=volume,source=with-human-hookgw-runtime-gateway,target=/installed/gateway' `
        --mount 'type=volume,source=with-human-hookgw-runtime-upstream,target=/installed/upstream' `
        --mount 'type=volume,source=with-human-hookgw-runtime-product,target=/installed/product' `
        with-human-dev:local python /install.py
}
switch ($Mode) {
    'prepare' {
        & $python -I tools/hookgw_prepare.py $project
        if ($LASTEXITCODE -ne 0) { throw 'Prepare refused/failed; existing runtime preserved.' }
        & $python -I tools/hookgw_bundle.py $project
        if ($LASTEXITCODE -ne 0) { throw 'Frozen product bundle preparation failed.' }
        Install-HookgwRuntime
        @{workspace=$project;control_url='https://127.0.0.1:8030';gateway_url='https://127.0.0.1:8040/mcp'} |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $hostPath 'profile.json') -Encoding utf8
        # Restrict NEW host credentials only; no old runtime/global permissions change.
        if ($env:OS -eq 'Windows_NT') {
            $identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
            $runtimePath=Join-Path $project 'artifacts/runtime-hookgw'
            & icacls $runtimePath /inheritance:r /grant:r "${identity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Host credential ACL failed.' }
        }
    }
    'install' { Install-HookgwRuntime }
    'start' {
        & $python -I tools/hookgw_bundle.py $project --verify
        if ($LASTEXITCODE -ne 0) { throw 'Frozen product bundle check failed; no service started.' }
        Invoke-HookgwDocker compose -f compose.hookgw.yaml up -d
        Write-Host 'TLS control https://127.0.0.1:8030/health ; gateway https://127.0.0.1:8040/mcp'
        Write-Host 'Default judge is unavailable: no paid calls. See the user LIVE procedure.'
    }
    'status' { Invoke-HookgwDocker compose -f compose.hookgw.yaml ps }
    'history' { & $python -I tools/hookgw_hook.py $hostPath history }
    'approve' { if (-not $Call) { throw '-Call is required.' }; & $python -I tools/hookgw_hook.py $hostPath approve --call $Call }
    'reject' { if (-not $Call) { throw '-Call is required.' }; & $python -I tools/hookgw_hook.py $hostPath reject --call $Call }
}
if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" }
