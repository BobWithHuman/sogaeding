<# Dot-source once; normal codex then receives free human input interactively. #>
param([string]$PythonPath='', [switch]$Api, [string]$Model='', [switch]$Preflight, [switch]$PrepareJudgeMountpoint, [switch]$JevRules,
      [switch]$HandsOn, [switch]$FrozenDemo, [switch]$ConfirmSend, [string]$ManifestSha256='', [switch]$ApproveHandsOnLimits, [switch]$ApproveFrozenLimits)
$previousConnectErrorAction=$ErrorActionPreference
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $PythonPath) {
    $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath=(Get-Command python -CommandType Application -ErrorAction Stop).Source }
}
$native=Get-Command codex.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($native) { $nativePath=$native.Source }
else { $nativePath=Join-Path $env:LOCALAPPDATA 'Programs/OpenAI/Codex/bin/codex.exe' }
if (-not (Test-Path -LiteralPath $nativePath)) { throw 'Installed native codex.exe not found.' }
if ($HandsOn -or $FrozenDemo) {
    try {
        $ErrorActionPreference='Stop'
        if ($Api -or $Model -or $Preflight -or $PrepareJudgeMountpoint -or $JevRules -or ($HandsOn -and $FrozenDemo) -or ($HandsOn -and (-not $ApproveHandsOnLimits -or $ApproveFrozenLimits)) -or ($FrozenDemo -and (-not $ApproveFrozenLimits -or $ApproveHandsOnLimits)) -or -not $ConfirmSend -or $ManifestSha256 -notmatch '^[a-f0-9]{64}$') { throw 'Select one prepared demo with its exact manifest, ConfirmSend and matching fixed-limit switch; do not combine modes.' }
        $selectedDemoRevision=if ($FrozenDemo) {'frozen-demo-1'} else {'hands-on-1'}
        if (Test-Path Variable:global:WithHumanHandsOn) { throw 'A hands-on wrapper is already installed in this terminal.' }
        $priorAlias=Get-Alias codex -ErrorAction SilentlyContinue
        $priorFunction=Get-Item Function:codex -ErrorAction SilentlyContinue
        if (($priorAlias -and "$($priorAlias.Options)" -match 'Constant|ReadOnly') -or ($priorFunction -and "$($priorFunction.Options)" -match 'Constant|ReadOnly')) { throw 'Existing codex command is protected; it was not replaced.' }
        # FunctionInfo/AliasInfo refer to mutable session entries; snapshot before replacement.
        $savedFunction=if ($priorFunction) { @{ScriptBlock=$priorFunction.ScriptBlock;Options=$priorFunction.Options;Description=$priorFunction.Description} } else { $null }
        $savedAlias=if ($priorAlias) { @{Definition=$priorAlias.Definition;Options=$priorAlias.Options;Description=$priorAlias.Description} } else { $null }
        $preflightOutput=@(& $PythonPath -X utf8 -I (Join-Path $project 'tools/mvp_demo.py') check --revision $selectedDemoRevision --exe $nativePath --model gpt-5.6-luna)
        $preflightExit=$LASTEXITCODE
        if ($preflightExit -ne 0) { $preflightOutput|Write-Host; throw 'Hands-on model-free preflight failed; no wrapper/model started.' }
        $ready=($preflightOutput -join "`n")|ConvertFrom-Json
        if (-not $ready.ready -or $ready.manifest_sha256 -ne $ManifestSha256) { throw 'Prepared hands-on binding changed; no wrapper installed.' }
        if ($priorAlias) { Remove-Item Alias:codex -ErrorAction Stop }
        $global:WithHumanHandsOn=@{Root=$project;Python=$PythonPath;Native=$nativePath;Manifest=$ManifestSha256;Revision=$selectedDemoRevision;PriorAlias=$savedAlias;PriorFunction=$savedFunction}
        function global:codex {
            if ($args.Count -ne 0) { throw 'Enter plain codex, then type requests interactively. Command-line overrides are not part of this selection.' }
            $currentHands=$global:WithHumanHandsOn
            try {
                & $currentHands.Python -X utf8 -I (Join-Path $currentHands.Root 'tools/mvp_demo.py') start --revision $currentHands.Revision --exe $currentHands.Native --model gpt-5.6-luna --confirm-send --manifest-sha256 $currentHands.Manifest --select-hands-on-limits
            } finally {
                Remove-Item Function:global:codex -ErrorAction SilentlyContinue
                if ($currentHands.PriorFunction) { Set-Item Function:global:codex -Value $currentHands.PriorFunction.ScriptBlock -Options $currentHands.PriorFunction.Options; (Get-Item Function:codex).Description=$currentHands.PriorFunction.Description }
                if ($currentHands.PriorAlias) { Set-Alias -Name codex -Value $currentHands.PriorAlias.Definition -Option $currentHands.PriorAlias.Options -Description $currentHands.PriorAlias.Description -Scope Global }
                Remove-Variable WithHumanHandsOn -Scope Global -ErrorAction SilentlyContinue
                Write-Host 'Hands-on CLI finished. Original terminal command restored; next codex uses your previous settings.'
            }
        }
        Write-Host 'Connected in this PowerShell only. Now enter: codex'
        Write-Host ('Workspace: '+$ready.workspace)
        if ($FrozenDemo) { Write-Host 'Selected: original remaining Jev4/input reservation256000 in shared cap8/512000, CLI1/1800s, historical37/2368000, totalCLI7. Actor costs separate.' }
        else { Write-Host 'Selected cap: Jev8/input reservation512000, CLI1/1800s, historical37/2368000, totalCLI6. Actor costs separate.' }
        Write-Host 'Your typed requests and synthetic files/candidates go to OpenAI actor API and TypeSafe Jev API after you run codex.'
        Write-Host 'Existing human hook review is reused; no automatic trust change. Host Allow and PDP decision are separate.'
        Write-Host 'Protected scope: enrolled synthetic file MCP only. CONFIRM is not auto-approved; native/hook failure boundary remains.'
    } finally { $ErrorActionPreference=$previousConnectErrorAction }
    return
}
$ErrorActionPreference='Stop'
if ($ConfirmSend -or $ManifestSha256 -or $ApproveHandsOnLimits -or $ApproveFrozenLimits) { throw 'Fixed selection arguments require matching demo mode.' }
if (($Api -and -not $Model) -or (($Model -or $Preflight -or $PrepareJudgeMountpoint) -and -not $Api)) { throw 'Use -Api -Model <exact-model-id>; preparation/preflight also requires API mode.' }
if ($JevRules -and (-not $Api -or $PrepareJudgeMountpoint)) { throw '-JevRules requires -Api -Model and does not prepare the historical OpenAI judge mountpoint.' }
if ($PrepareJudgeMountpoint -and $Preflight) { throw 'Run explicit mountpoint preparation separately; preflight remains read-only.' }
if ($PrepareJudgeMountpoint) {
    $dockerExe=(Get-Command docker -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $helper=Join-Path $project 'tools/hookgw_key_mountpoint.py'
    & $dockerExe run --rm --network none --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges:true --read-only `
        --mount 'type=volume,source=with-human-hookgw-runtime-control,target=/runtime' `
        --mount "type=bind,source=$helper,target=/prepare.py,readonly" `
        with-human-dev:local python /prepare.py /runtime
    if ($LASTEXITCODE -ne 0) { throw 'Judge mountpoint preparation failed; no model started.' }
}
$global:WithHumanHookgwLaunch=@{Root=$project;Python=$PythonPath;Native=$nativePath;Api=[bool]$Api;Model=$Model;JevRules=[bool]$JevRules}
function global:codex {
    $launch=$global:WithHumanHookgwLaunch
    $modeArgs=@()
    if ($launch.Api) { $modeArgs=@('--api','--model',$launch.Model) }
    if ($launch.JevRules) { $modeArgs+=@('--jev-rules') }
    & $launch.Python -I (Join-Path $launch.Root 'tools/hookgw_launch.py') --root $launch.Root --exe $launch.Native @modeArgs @args
}
Write-Host 'This terminal now connects normal codex through With Human. Review /hooks on first use.'
Write-Host 'Authorized one-off host review: codex --manual-review (API + JevRules only); next codex inherits your defaults.'
Write-Host 'Protected: enrolled file MCP via actual gateway; supported native hook subset. Hook process failure can fail open.'
if ($Api) { Write-Host "Actor API mode: model=$Model ; env=OPENAI_API_KEY ; https://api.openai.com/v1/responses. Personal login unchanged." }
if ($JevRules) { Write-Host 'Jev rules-only: isolated host profile/ports8032,8042; semantic writes NOT_AUTHORIZED. Actual Jev accuracy NOT_RUN.' }
if ($Preflight) {
    codex --preflight
    if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. No model started; inspect safe issue codes above.' }
}
