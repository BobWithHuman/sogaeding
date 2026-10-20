<# Native Windows PS5.1 fixture: no real key, Docker, actor or provider. #>
param([Parameter(Mandatory)][string]$OutputPath,[string]$PythonPath='')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$output=[IO.Path]::GetFullPath($OutputPath)
if (-not $output.StartsWith((Join-Path $project 'artifacts')+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Evidence path must be under workspace artifacts' }
if (Test-Path -LiteralPath $output) { throw 'Preserve previous evidence' }
if (-not $PythonPath) { $PythonPath=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
$fixture=Join-Path (Split-Path $output) 'native-fixture'
if (Test-Path -LiteralPath $fixture) { throw 'Use a new evidence directory' }
New-Item -ItemType Directory -Force (Join-Path $fixture 'scripts'),(Join-Path $fixture 'tools') | Out-Null
$script=Join-Path $fixture 'scripts/jev_eval.ps1'
Copy-Item -LiteralPath (Join-Path $project 'scripts/jev_eval.ps1') -Destination $script
$fake=@'
import json,locale,pathlib,sys
case=pathlib.Path(__file__).with_name('case.txt').read_text(encoding='ascii')
if case=='nonzero':
 print('PRIVATE_STDERR_CANARY',file=sys.stderr)
 print('PRIVATE_STDOUT_CANARY')
 raise SystemExit(2)
if case=='empty':raise SystemExit(0)
if case=='malformed':
 print('PRIVATE_STDOUT_CANARY')
 raise SystemExit(0)
text=sys.stdin.read() if sys.argv[1]=='store-key' else ''
print(json.dumps(dict(mode=sys.argv[1],isolated=sys.flags.isolated,utf8_mode=sys.flags.utf8_mode,
 encoding=locale.getpreferredencoding(False),sample='\ud55c\uad6d\uc5b4 \u6f22 \U0001f600 e\u0301',
 ascii_stdin=(text.strip()=='PUBLIC-FAKE-ASCII-key') if sys.argv[1]=='store-key' else None),ensure_ascii=False))
'@
[IO.File]::WriteAllText((Join-Path $fixture 'tools/jev_eval.py'),$fake,[Text.UTF8Encoding]::new($false))
$control=Join-Path $fixture 'tools/case.txt'
$checks=New-Object Collections.Generic.List[object]
function Check([string]$Name,[bool]$Value) {
    $checks.Add(@{name=$Name;pass=$Value})
    if(-not $Value){throw "Fixture check failed: $Name"}
}
$originalConsole=[Console]::OutputEncoding
$originalOutput=$OutputEncoding
try {
    [Console]::OutputEncoding=[Text.Encoding]::GetEncoding(949)
    $OutputEncoding=[Text.Encoding]::ASCII
    foreach($mode in @('inspect','preflight','collect')) {
        [IO.File]::WriteAllText($control,'ok')
        $lines=@(& $script -Mode $mode -PythonPath $PythonPath)
        $value=($lines -join "`n") | ConvertFrom-Json
        Check "$mode-isolated-utf8" ($value.isolated -eq 1 -and $value.utf8_mode -eq 1 -and $value.encoding -eq 'utf-8')
        $expected=([string][char]0xD55C)+([string][char]0xAD6D)+([string][char]0xC5B4)+' '+([string][char]0x6F22)+' '+[char]::ConvertFromUtf32(0x1F600)+' e'+([string][char]0x0301)
        Check "$mode-unicode-json" ($value.sample -ceq $expected)
        Check "$mode-console-restored" ([Console]::OutputEncoding.CodePage -eq 949 -and $OutputEncoding.CodePage -eq 20127)
    }
    foreach($item in @(@('nonzero','HELPER_NONZERO_EXIT'),@('malformed','HELPER_JSON_INVALID'),@('empty','HELPER_EMPTY_OUTPUT'))) {
        [IO.File]::WriteAllText($control,$item[0])
        $message=''
        try { $null=@(& $script -Mode inspect -PythonPath $PythonPath) } catch { $message=$_.Exception.Message }
        Check ($item[0]+'-fixed-diagnostic') ($message.Contains('stage=INSPECT code='+$item[1]) -and -not $message.Contains('PRIVATE_'))
        Check ($item[0]+'-console-restored') ([Console]::OutputEncoding.CodePage -eq 949 -and $OutputEncoding.CodePage -eq 20127)
    }
    [IO.File]::WriteAllText($control,'ok')
    function Read-Host {
        param([string]$Prompt,[switch]$AsSecureString)
        $secure=[Security.SecureString]::new()
        foreach($character in 'PUBLIC-FAKE-ASCII-key'.ToCharArray()){$secure.AppendChar($character)}
        return $secure
    }
    $keyOutput=@(& $script -Mode key -PythonPath $PythonPath)
    $stored=$keyOutput[-1] | ConvertFrom-Json
    Check 'fake-hidden-ascii-stdin' ($stored.ascii_stdin -eq $true -and $stored.isolated -eq 1 -and $stored.utf8_mode -eq 1)
    function Read-Host { throw 'PRIVATE_CANCEL_CANARY' }
    $message=''
    try { $null=@(& $script -Mode key -PythonPath $PythonPath) } catch { $message=$_.Exception.Message }
    Check 'hidden-cancel-fixed-diagnostic' ($message -ceq 'WITH_HUMAN_JEV_FAILURE stage=KEY_INPUT code=HIDDEN_INPUT_FAILED')
    Check 'hidden-cancel-console-restored' ([Console]::OutputEncoding.CodePage -eq 949 -and $OutputEncoding.CodePage -eq 20127)
    $message=''
    try { $null=@(& $script -Mode inspect -PythonPath (Join-Path $fixture 'absent.exe')) } catch { $message=$_.Exception.Message }
    Check 'launch-failure-fixed-diagnostic' ($message -ceq 'WITH_HUMAN_JEV_FAILURE stage=INSPECT code=PYTHON_START_FAILED')
    $message=''
    try { $null=@(& $script -Mode evaluate -PythonPath $PythonPath) } catch { $message=$_.Exception.Message }
    Check 'evaluate-without-approval-denied' ($message.StartsWith('Review exact inspect data and price first;'))
    Check 'final-console-restored' ([Console]::OutputEncoding.CodePage -eq 949 -and $OutputEncoding.CodePage -eq 20127)
    $report=@{powershell=$PSVersionTable.PSVersion.ToString();checks=@($checks.ToArray());count=$checks.Count;paid_requests=0;real_key_body_read=$false;sample=$expected}
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $output -Encoding utf8
    @{checks=$checks.Count;passed=@($checks | Where-Object pass).Count;paid_requests=0;actual_key_reads=0} | ConvertTo-Json -Compress
} finally {
    [Console]::OutputEncoding=$originalConsole
    $OutputEncoding=$originalOutput
}
