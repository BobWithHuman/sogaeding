$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$target = Join-Path $projectRoot 'artifacts/browser-tools-b'
if (Test-Path -LiteralPath $target) { throw 'Tool directory exists; preserve the first download.' }
New-Item -ItemType Directory -Path $target | Out-Null
$url = 'https://cdn.playwright.dev/dbazure/download/playwright/builds/firefox/1538/firefox-win64.zip'
$archive = Join-Path $target 'firefox-1538.zip'
Invoke-WebRequest -Uri $url -OutFile $archive
Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $target 'firefox-1538')
$exe = Join-Path $target 'firefox-1538/firefox/firefox.exe'
$signature = Get-AuthenticodeSignature -FilePath $exe
@{url=$url; downloaded_at=[DateTime]::UtcNow.ToString('o'); revision='1538';
  archive_sha256=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower();
  executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLower();
  signature_status=[string]$signature.Status;
  signature_subject=if($signature.SignerCertificate){$signature.SignerCertificate.Subject}else{$null};
  publisher_expected_zip_digest='NOT_PUBLISHED_IN_INSTALLED_REGISTRY';
  integrity_scope='TLS download plus local reproducibility hashes; signature is recorded, not fabricated'} |
  ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $target 'download-manifest.json') -Encoding utf8
Write-Output 'Fixed development Firefox downloaded; integrity metadata recorded, no product dependencies changed.'
