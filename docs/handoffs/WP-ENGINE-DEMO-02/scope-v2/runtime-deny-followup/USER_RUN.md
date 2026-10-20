# 미시작 14개 후속 실행 명령

기존 scope-v2 run은 재실행하지 않는다. UNKNOWN인 consent/11은 제외했다. 새 준비본은 `C:\sogaeding\artifacts\20261018-dtap-os100\user-engine-demo-02-deny-followup`이며 PREPARED_NOT_STARTED다. 새 유료 호출0, AgentDojo 제외다.

누적 지출 **$3.332794**, 기존 누적상한 **$5.089294**, 잔여 **$1.756500**이다. 원 총상한 $7은 유지하며 새 $1.80을 더하지 않았다. 원장·UNKNOWN·기존 run의 source/키/서비스는 보존했다. 기존 fork와 동시 실행하지 않는다.

준비 확인만 수행하는 무모델 명령:

```powershell
Set-Location C:\sogaeding
$denyManifest = 'bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f'
if ((Get-Content -Raw .\artifacts\20261018-dtap-os100\user-engine-demo-02-deny-followup\manifest.sha256).Trim() -ne $denyManifest) { throw 'Reviewed manifest mismatch' }
& .\scripts\dtap_official_runtime.ps1 -Mode check -DenyFollowup -MaxTotalUsd 5.089294 -ManifestSha256 $denyManifest
```

사용자가 실제 유료 실행을 선택할 때만 아래 명령을 실행한다. 이 작업에서는 실행하지 않았다. 같은 PowerShell에 기존 `OPENAI_API_KEY`가 이미 설정되어 있어야 하며 런처는 기존 보호된 Jev key 참조를 사용한다. 키를 출력하거나 로그인/개인 설정을 변경하지 않는다.

```powershell
Set-Location C:\sogaeding
& .\scripts\dtap_official_runtime.ps1 -Mode run -DenyFollowup -OfficialRuntime -Arm engine-on -PaidOptIn -MaxTotalUsd 5.089294 -ManifestSha256 bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f
```

별도 PowerShell에서 상태·증거 수집:

```powershell
Set-Location C:\sogaeding
$denyManifest = 'bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f'
& .\scripts\dtap_official_runtime.ps1 -Mode status -DenyFollowup -ManifestSha256 $denyManifest
& .\scripts\dtap_official_runtime.ps1 -Mode collect -DenyFollowup -ManifestSha256 $denyManifest
```

중단이 필요할 때:

```powershell
& .\scripts\dtap_official_runtime.ps1 -Mode stop -DenyFollowup -ManifestSha256 $denyManifest
```

status의 `demo_progress.new_on_*`를 사용한다. 준비 시 새 on은0/14 완료·시도0·미시작14, 재사용 off11이다. 원 parent의 off12/새 on완료0·시도1·UNKNOWN1 기록은 별도 보존했다. 재사용 off가 포함된 both-arm 비율을 새 완료율로 읽지 않는다.

resume/UNKNOWN 재시도·임의 환불은 금지한다. parent 상태 drift나 준비 검사 실패 시 새로 시작하지 말고 원장/증거를 보존한다. 새 PKI leaf 유효기간은 준비 후2일이며, 만료 시 동결본을 덮어쓰지 말고 새 검토된 준비가 필요하다. 정확 사유의 정책 DENY 뒤 대안 선택 경로는 무모델 연결검증을 통과했지만 실제 모델 정확도·14개 완주·전체 ASR은 미검증이다. 근거: [RESULT](RESULT.md), [별도 AI 검토](REVIEW.md), `artifacts/20261018-engine-demo-02-deny-followup/final-bindings.json`.
