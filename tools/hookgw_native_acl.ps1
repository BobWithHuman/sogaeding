param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference='Stop'
$resolved=(Resolve-Path -LiteralPath $Path).Path
if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {throw 'Fixture host directory required'}
$artifactRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts'))
if (-not $resolved.StartsWith(($artifactRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetFileName($resolved) -ne 'host') {throw 'Only a new artifact fixture host directory is permitted'}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $resolved /inheritance:r /grant:r "${identity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) {throw 'Fixture host ACL restriction failed'}
Write-Output 'Fixture host ACL restricted to current user and SYSTEM.'
