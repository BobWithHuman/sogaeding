<#
.SYNOPSIS
Prepare Docker tools and run harness checks before product implementation.
.DESCRIPTION
check validates only the harness and contracts. Once product tests exist, run:
docker compose run --rm --no-deps dev python -m pytest tests/backend tests/gateway -q -p no:cacheprovider
The dev service mounts source, tools and tests read-only; product DB tests use temp paths.
#>
param(
    [ValidateSet('up', 'check', 'down', 'app', 'lock', 'audit', 'tls', 'test')]
    [string]$Mode = 'up'
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot

function Invoke-Docker {
    # Keep this a simple function: advanced-function common switches would consume
    # native flags such as docker's -d or pytest's -p before Docker receives them.
    & docker @args
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed (exit $LASTEXITCODE)."
    }
}

switch ($Mode) {
    'up' {
        Invoke-Docker compose up -d --build dev
        Write-Host 'Development tools container ready. App code and endpoints are not running.'
    }
    'check' {
        Invoke-Docker compose run --rm --no-deps dev python tools/check_contracts.py
        Invoke-Docker compose run --rm --no-deps dev python -m pytest tests/harness -q -p no:cacheprovider
        Invoke-Docker compose run --rm --no-deps dev python -m ruff check tools/check_contracts.py tests/harness
        Invoke-Docker compose run --rm --no-deps dev python -m bandit -q tools/check_contracts.py
        Invoke-Docker compose run --rm --no-deps dev python -m pip check
    }
    'down' {
        # Deliberately preserve control/effects volumes.
        Invoke-Docker compose --profile app down
    }
    'app' {
        foreach ($modulePath in @('src/app/control/main.py', 'src/app/gateway/main.py')) {
            if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $modulePath) -PathType Leaf)) {
                throw "App source is not implemented: $modulePath. Run -Mode up / -Mode check for preparation only."
            }
        }
        foreach ($file in @('control/control.pem','control/control.key','control/human.token',
            'control/service.token','control/storage.key','gateway/gateway.pem','gateway/gateway.key',
            'gateway/gateway-client.pem','gateway/gateway-client.key','gateway/service.token',
            'gateway/storage.key','ca.pem')) {
            if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ('artifacts/runtime-wp01/' + $file)))) {
                throw 'Prepare app-specific PKI with -Mode tls first. No HTTP fallback.'
            }
        }
        Invoke-Docker compose --profile app up -d --build control gateway
        Write-Host 'App processes started. Run the real authenticated MCP smoke before claiming integration.'
    }
    'tls' {
        $runtimePath = Join-Path $projectRoot 'artifacts/runtime-wp01'
        if (Test-Path -LiteralPath $runtimePath) { throw 'Runtime exists; preserve its keys/DB bindings. Reissue into a separate reviewed runtime.' }
        [void][IO.Directory]::CreateDirectory((Join-Path $projectRoot 'artifacts'))
        Invoke-Docker run --rm --user 10001:10001 --mount "type=bind,source=$projectRoot/tools,target=/tools,readonly" --mount "type=bind,source=$projectRoot/artifacts,target=/output" with-human-dev:local python /tools/prepare_tls.py /output/runtime-wp01
        foreach ($role in @('control','gateway')) { [void][IO.Directory]::CreateDirectory((Join-Path $runtimePath $role)) }
        foreach ($file in @('ca.pem','control.pem','control.key','human.token','service.token','storage.key')) {
            Copy-Item -LiteralPath (Join-Path $runtimePath $file) -Destination (Join-Path $runtimePath ('control/' + $file))
        }
        foreach ($file in @('ca.pem','gateway.pem','gateway.key','gateway-client.pem','gateway-client.key','service.token')) {
            Copy-Item -LiteralPath (Join-Path $runtimePath $file) -Destination (Join-Path $runtimePath ('gateway/' + $file))
        }
        Copy-Item -LiteralPath (Join-Path $runtimePath 'effects-storage.key') -Destination (Join-Path $runtimePath 'gateway/storage.key')
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        & icacls $runtimePath /inheritance:r /grant:r ($identity + ':F') 'SYSTEM:F' /T /Q
        if ($LASTEXITCODE -ne 0) { throw 'Runtime file ACL configuration failed.' }
        & icacls $runtimePath /grant:r ($identity + ':(OI)(CI)F') 'SYSTEM:(OI)(CI)F' /Q
        if ($LASTEXITCODE -ne 0) { throw 'Runtime ACL configuration failed.' }
    }
    'test' {
        Invoke-Docker compose run --rm --no-deps dev python -m pytest tests/backend tests/transport tests/web tests/acceptance -q -p no:cacheprovider
    }
    'lock' {
        Invoke-Docker build --target resolver -f Dockerfile.dev -t with-human-resolver:local .
        Invoke-Docker run --rm --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,source=$projectRoot,target=/workspace" with-human-resolver:local --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --quiet --output-file requirements-dev.lock requirements-dev.in
        Write-Host 'Review the lock diff, rebuild, and run checks after changing dependencies.'
    }
    'audit' {
        # Public vulnerability lookup only; no workspace credentials or API keys.
        Invoke-Docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,mode=1777 with-human-dev:local python -m pip_audit --cache-dir /tmp/pip-audit --progress-spinner off --no-deps --disable-pip -r /opt/requirements-dev.lock --format json
    }
}
