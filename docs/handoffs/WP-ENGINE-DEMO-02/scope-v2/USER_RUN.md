# 서버 작업 범위 .50 v2 실행 인계

> 실제 첫 실행 후 중단된 역사 명령이다. 이 run을 재실행하지 않는다. 미시작14개·동일누적상한의 최신 명령은 [runtime-deny-followup/USER_RUN.md](runtime-deny-followup/USER_RUN.md)를 사용한다. 아래 최초 준비 기록은 보존한다.

기존 `7562007f...` v1 명령은 사용하지 않는다. 새 root는 `C:\sogaeding\artifacts\20261018-dtap-os100\user-engine-demo-02-scope-v2`다. 원 준비본은 보존했다. 프로필은 `dtap-demo-allow50-scope-v2`, allow .50/risk .90이다. Actor GPT-5.2 low·실제 Jev 설정은 유지한다.

실제 준비 설정으로 exact grant가 없는 조건부 과업에서 B LEGITIMATE .60 + A raw WITHIN_TASK → 의미 ALLOW → 원 MCP 쓰기1·재사용0을 확인했다. 증거: `artifacts/20261018-engine-demo-02-scope-v2/prepared-reachability.json`. Jev 응답은 합성이며 실제 분류 성능이나 DTAP 완료를 입증한 것은 아니다.

추가 지출 상한 $1.80, 기소비 포함 누적상한 $5.089294 ≤ 원상한 $7. 미확정 hold/UNKNOWN은 보존한다. 기존 run/다른 fork와 동시에 실행하지 않는다. 400k/8192 최대예약 $0.814688을 평균값으로 낮추지 않았다. 정상15개 완주는 보장하지 않는다.

최종 manifest는 `338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8`이다. `final-bindings.json`에서 동결 source81·scope15·실제 Engine DB7의 grant/policy configuration·broker config·원장 binding을 대조했다. 미열거 쓰기는 원 MCP로 다시 읽어 `Annual summary` 내용까지 확인했다. 유료 broker/actor/Jev는 아직 시작하지 않았다.

PowerShell에서 준비 확인(무모델):

```powershell
Set-Location C:\sogaeding
$scopeManifest = '338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8'
if ((Get-Content -Raw .\artifacts\20261018-dtap-os100\user-engine-demo-02-scope-v2\manifest.sha256).Trim() -ne $scopeManifest) { throw 'Reviewed manifest mismatch' }
& .\scripts\dtap_official_runtime.ps1 -Mode check -DemoMode -MaxTotalUsd 7 -ManifestSha256 $scopeManifest
```

사용자가 실제 실행을 선택할 때만 아래 명령을 실행한다. 같은 PowerShell의 기존 `OPENAI_API_KEY`와 기존 보호된 Jev key 참조가 필요하며 키를 화면/문서에 출력하지 않는다. 키·로그인·모델 설정을 변경하지 않았다.

```powershell
Set-Location C:\sogaeding
& .\scripts\dtap_official_runtime.ps1 -Mode run -DemoMode -OfficialRuntime -Arm engine-on -PaidOptIn -MaxTotalUsd 5.089294 -ManifestSha256 338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8
```

별도 PowerShell에서 상태·수집:

```powershell
Set-Location C:\sogaeding
$scopeManifest = '338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8'
& .\scripts\dtap_official_runtime.ps1 -Mode status -DemoMode -ManifestSha256 $scopeManifest
& .\scripts\dtap_official_runtime.ps1 -Mode collect -DemoMode -ManifestSha256 $scopeManifest
```

중단이 필요하면 `-Mode stop -DemoMode -ManifestSha256 $scopeManifest`를 사용한다. 이 프로필은 resume을 허용하지 않는다. UNKNOWN/중단 호출을 재시도하거나 비용을 환불 처리하지 말고 원장과 증거를 보존한다. 현재 준비본의 PKI leaf 유효기간은 생성 후 2일이다. 만료/환경 drift로 검사가 실패하면 임의 재생성·동결본 덮어쓰기를 하지 않고 새 준비·검토가 필요하다.

관련73·최종 통합121 통과 후 경로 한도와 실제 readback 반영에 대한 좁은32 통과를 확인했다. 별도 AI 검토는 `REVIEW.md`에 기록했다. 실제 모델 정확도·전체 DTAP 완료·전체 ASR은 NOT_RUN이다. AgentDojo는 제외했다.
