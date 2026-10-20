param([string]$ParentLabel = ('manual-live-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')))
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
$pythonPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pwshPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
if (-not (Test-Path -LiteralPath $pwshPath -PathType Leaf)) { throw 'Bundled pwsh.exe is missing. No model started.' }
if (-not $env:OPENAI_API_KEY) { throw 'Host actor OPENAI_API_KEY is required; never paste its value.' }
$oldHuman=[Environment]::GetEnvironmentVariable('HUMAN_USER_TOKEN')
$actorFailed=$false
try {
    $env:HUMAN_USER_TOKEN=[IO.File]::ReadAllText((Join-Path $projectRoot 'artifacts/runtime-f3-01/control/human.token')).Trim()
    foreach ($case in @('normal','instruction-variant')) {
        $label=$ParentLabel+'-actor-'+$case
        & ./tools/f3_evidence.ps1 -RunId 20261014-f3-01 -Label ($label+'-budget') -Program $pythonPath -CommandArgs @('tools/f3_actor_budget.py',$label)
        if ($LASTEXITCODE -ne 0) { throw 'Actor episode budget exhausted.' }
        & ./tools/f3_evidence.ps1 -RunId 20261014-f3-01 -Label ($label+'-fixture') -Program $pythonPath -CommandArgs @('-X','utf8','tools/f3_fixture.py',$case)
        if ($LASTEXITCODE -ne 0) { throw 'Fake fixture setup failed.' }
        & ./tools/f3_evidence.ps1 -RunId 20261014-f3-01 -Label $label -Program $pwshPath -CommandArgs @('-NoProfile','-File','scripts/run_codex_live.ps1','-Run',
          '-TaskKind','POST_COMMENT','-CommentMode','ISSUE_SUMMARY','-UserRequest','이슈42를 읽고 요약 댓글을 한 번 작성해줘',
          '-Model','gpt-5.6-luna','-ControlBaseUrl','https://127.0.0.1:8020','-McpUrl','https://127.0.0.1:8021/mcp',
          '-CaCertificatePath','C:/sogaeding/artifacts/runtime-f3-01/ca.pem','-TimeoutSeconds','180')
        if ($LASTEXITCODE -ne 0) { $actorFailed=$true }
        # Preserve failure and move to the other finite episode; never repeat.
    }
} finally { [Environment]::SetEnvironmentVariable('HUMAN_USER_TOKEN',$oldHuman,'Process') }
if ($actorFailed) { exit 1 }
