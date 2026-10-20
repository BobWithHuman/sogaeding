param([Parameter(Mandatory)][string]$Label)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
Set-Location -LiteralPath C:/sogaeding
$runId='20261014-f3-launcher-fix-review'
$target='C:/sogaeding/artifacts/'+$runId
$pythonPath='C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$checks=@()
foreach($expected in @(0,37)) {
    $caseLabel=$Label+'-exit-'+$expected
    $nativeCode="import sys; print('review-safe-stdout'); print('review-safe-stderr',file=sys.stderr); sys.exit("+$expected+')'
    $output=@(& ./tools/f3_evidence.ps1 -RunId $runId -Label $caseLabel -Program $pythonPath -CommandArgs @('-c',$nativeCode))
    $actual=$LASTEXITCODE
    $record=Get-Content -Raw -LiteralPath ($target+'/'+$caseLabel+'-command.json') | ConvertFrom-Json
    $log=Get-Content -Raw -LiteralPath ($target+'/'+$caseLabel+'.txt')
    if($actual -ne $expected -or $record.exit_code -ne $expected){throw 'Native exit code mismatch'}
    if($log -notmatch 'review-safe-stdout' -or $log -notmatch 'review-safe-stderr'){throw 'Native output missing'}
    if($ErrorActionPreference -ne 'Stop' -or $PSNativeCommandUseErrorActionPreference -ne $true){throw 'Caller preferences changed'}
    if(@($output | Where-Object {$_ -is [Management.Automation.ErrorRecord]}).Count){throw 'ErrorRecord leaked'}
    $checks+=@{case='native-stderr';expected_exit=$expected;actual_exit=$actual;recorded_exit=$record.exit_code;caller_preferences_preserved=$true;output_as_text=$true}
}
$successLabel=$Label+'-exit-0'
$beforeHash=(Get-FileHash -LiteralPath ($target+'/'+$successLabel+'-command.json') -Algorithm SHA256).Hash
$sentinel=$target+'/'+$Label+'-unexpected-execution.txt'
$duplicate=$false
try{& ./tools/f3_evidence.ps1 -RunId $runId -Label $successLabel -Program $pythonPath -CommandArgs @('-c',"print('unexpected invocation')")}catch{$duplicate=$true}
if(-not $duplicate -or (Get-FileHash -LiteralPath ($target+'/'+$successLabel+'-command.json') -Algorithm SHA256).Hash -ne $beforeHash){throw 'Duplicate evidence replaced'}
$checks+=@{case='duplicate';rejected=$true;old_record_unchanged=$true}
$missing=$false
try{& ./tools/f3_evidence.ps1 -RunId $runId -Label ($Label+'-missing') -Program 'with-human-review-missing-application' -CommandArgs @('unused')}catch{$missing=$true}
if(-not $missing -or (Test-Path -LiteralPath ($target+'/'+$Label+'-missing-command.json'))){throw 'Missing application did not fail before start'}
$checks+=@{case='missing-application';rejected_before_start=$true}
$dockerCandidates=@(Get-Command docker -CommandType Application)
& ./tools/f3_evidence.ps1 -RunId $runId -Label ($Label+'-docker-client') -Program docker -CommandArgs @('--version')
if($LASTEXITCODE -ne 0){throw 'Docker client name resolution failed'}
$dockerRecord=Get-Content -Raw -LiteralPath ($target+'/'+$Label+'-docker-client-command.json') | ConvertFrom-Json
if($dockerRecord.exit_code -ne 0){throw 'Docker version exit lost'}
$checks+=@{case='application-name-resolution';candidate_count=$dockerCandidates.Count;first_path=$dockerCandidates[0].Path;actual_exit=$dockerRecord.exit_code;docker_daemon_operations=0}
$parseTokens=$null;$parseErrors=$null
$parsed=[Management.Automation.Language.Parser]::ParseFile('C:/sogaeding/scripts/f3_verify.ps1',[ref]$parseTokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Launcher syntax failed'}
$dockerDirect=$parsed.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'docker'},$true)
if($dockerDirect.Count){throw 'A direct Docker invocation remains in the launcher'}
$checks+=@{case='launcher-static';syntax_errors=0;direct_docker_invocations=0;model_launcher_executed=$false}
@{recorded_at=[DateTime]::UtcNow.ToString('o');powershell=$PSVersionTable.PSVersion.ToString();checks=$checks;result='PASS';model_requests=0;actor_episodes=0;product_effects=0} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath ($target+'/'+$Label+'-review.json') -Encoding utf8
Write-Output ('PASS '+$PSVersionTable.PSVersion.ToString()+' independent native and offline launcher checks')
