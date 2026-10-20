# T-PDP-QUERY-01 최신 단회 실행 인계

2026-10-20 KST. **아래 QueryRouting 명령만 최신 실행 후보**다. 이전 b95c0992 준비본·원 run·실패/검토 기록은 보존했고 실행하지 않았다.

새 root: `C:\sogaeding\artifacts\20261018-dtap-os100\user-query-utility`.
고정 manifest: `4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770`.
benign/2 → 3 → 4, engine-on만3개. 원 GPT-5.2/low·18도구·prompt/setup/image/judge·실제 Jev 설정·A/B 질문·.50/.90를 유지했다. 검토한 tree(depth1~3), 정확한 존재 확인, 정확한 파일 정보만 CODE_ALLOW 후보이며 다른 조회·내용 쓰기는 기존 의미/동의 경로다. tree 외 재귀 search_files는 열지 않았다.

무모델 연결: CODE_ALLOW3/모두 실제 원 MCP 응답·Post OBSERVED, Jev 요청0. shell CODE_DENY1/실행0. 가짜 actor7요청이며 실제 모델 성능은 NOT_RUN이다. 실제 유료 요청0, 원420예약·UNKNOWN/stop 이력 유지. 누적 **$4.118747 / 상한$5.089294 / 기록상 잔여$0.970547 / hold0**. 평균가격으로 최대예약을 낮추지 않았으며3개 완주를 보장하지 않는다.

관련72건 검증·별도 AI 검토(확정 수정 지적 없음) 후 동일 hash의 최종 무모델 check FULL_READY3 PASS. 원증거는 `artifacts/20261020-query-routing/final-reviewed-check.log`다.

이전 준비본 인증서는 점검시 유효하나 leaf5종이 **2026-10-20 19:44:20 KST** 만료된다. 새 준비본은 별도 PKI로 leaf **2026-10-22 11:07:12 KST**, CA **2026-10-27 11:07:12 KST**까지다. 전역 신뢰/기존 PKI를 바꾸지 않았다. 만료 뒤에는 아래 check가 실패하며 실행 claim/유료 전송 전에 중단한다. 임의 갱신·old 준비본 실행·검사 우회는 하지 않는다.

실행 직전 무모델 검사:

```powershell
Set-Location C:\sogaeding
& .\scripts\dtap_official_runtime.ps1 -Mode check -QueryRouting -MaxTotalUsd 5.089294 -ManifestSha256 4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770
```

실제 실행은 아직 시작하지 않았다. 사용자가 실행을 선택하면 기존 아래의 secure key 입력 절차로 현재 PowerShell의 `OPENAI_API_KEY`를 준비한다. 기존 Jev 키 참조 `artifacts/runtime-jev-eval/key/jev.api-key`도 필요하다. CODE_ALLOW 외 후보는 Jev가 필요하므로 키 검사를 제거하지 않는다. 키 값은 명령문/로그/채팅에 넣지 않는다.

**한 번 실행할 고정 명령:**

```powershell
Set-Location C:\sogaeding
& .\scripts\dtap_official_runtime.ps1 -Mode run -QueryRouting -OfficialRuntime -Arm engine-on -PaidOptIn -MaxTotalUsd 5.089294 -ManifestSha256 4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770
```

현재 launcher는 이전 UtilityAcceptance 유료 실행을 거부한다. fork 시작 흔적을 점검하고 공통 `artifacts/20261018-dtap-os100/utility-cumulative-start.lock`을 원자적으로 단회 발급한 뒤 새 revision의 start lock·키·opt-in을 만든다. 기존 동결 launcher를 직접 실행하거나 다른 fork에서 잔여를 중복 사용하지 않는다. 공통/개별 lock·키·원장·stop/UNKNOWN을 삭제해 재실행하지 않는다. 검사/키 누락은 claim 전에 거부한다. 시작 후 실패·최종CONFIRM/UNKNOWN·과업실패·예산중단은 뒤 과업 전송을 중단하며 자동 resume/재시도/환불은 없다.

```powershell
& .\scripts\dtap_official_runtime.ps1 -Mode status -QueryRouting -ManifestSha256 4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770
& .\scripts\dtap_official_runtime.ps1 -Mode collect -QueryRouting -ManifestSha256 4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770
& .\scripts\dtap_official_runtime.ps1 -Mode stop -QueryRouting -ManifestSha256 4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770
```

`summary.json.query_routing`에 실제 CODE_ALLOW/CODE_DENY/CONSENT_REQUIRED/SEMANTIC과 사유·session/turn·인자/권한/요청 binding 및 신규 provider 요청수가 기록된다. `utility_progress`는 이번3개와 비용만 별도로 보여준다. 차단 건수를 정상 과업 성공이나 분석 생략 성공으로 합산하지 않는다. AgentDojo·전체 IPI/native/인과 증명 완료는 이번 결과가 아니다.

---

# 이전 T-PDP-UTILITY-PREP-01 준비 인계 기록

당시 배정은 **T-PDP-UTILITY-PREP-01**이었다. 아래 명령은 역사 기록이며 최신 실행 후보는 문서 맨 위 QueryRouting이다. 당시 실제 유료 전송은0이었다.

새 root: `C:\sogaeding\artifacts\20261018-dtap-os100\user-normal-utility-acceptance`.
고정 manifest: `b95c0992e67790350eb9e91e6512b1b3422da5b06ecc72ac661d463b3056a77a`.

순서는 benign/2 → benign/3 → benign/4, **새 engine-on만3개**다. scope2를 원 요청·Alice·실제18도구·원 초기 image에 다시 발급했다. Actor GPT-5.2/low·원 system/task prompt·catalog·setup·공식 judge와 실제 Jev 설정은 유지했다. 새 exact resource grant는 없다. 기존 run을 재개하는 명령이 아니다.

누적 지출 **$4.118747**, 누적상한 **$5.089294**, 잔여 **$0.970547**, hold0이다. 이전420 provider 예약과 정산·역사 UNKNOWN/CONFIRM을 계승했다. 원 총상한7의 여유를 전용하지 않는다. 최대 actor 예약 $0.814688을 평균요금으로 줄이지 않았으므로3개 완주/가격은 보장하지 않는다. 다른 fork와 동시에 실행하지 않는다.

무모델 사전 확인(기존 이미지·PKI·parent/source/scope/원장 검증만):

```powershell
Set-Location C:\sogaeding
$utilityManifest = 'b95c0992e67790350eb9e91e6512b1b3422da5b06ecc72ac661d463b3056a77a'
if ((Get-Content -Raw .\artifacts\20261018-dtap-os100\user-normal-utility-acceptance\manifest.sha256).Trim() -ne $utilityManifest) { throw 'Reviewed manifest mismatch' }
& .\scripts\dtap_official_runtime.ps1 -Mode check -UtilityAcceptance -MaxTotalUsd 5.089294 -ManifestSha256 $utilityManifest
```

실제 실행을 사용자가 선택할 때만 키 존재를 확인한다. 이미 process 환경에 있으면 다시 입력하지 않는다. 아래 입력은 화면에 키를 출력하지 않으며 파일/로그에 직접 붙여 넣지 않는다. 기존 Jev 키는 보호된 참조를 그대로 사용한다. 로그인/개인 모델 설정은 바꾸지 않는다. 키의 실제 유효성은 유료 API 없이 검증하지 않았다.

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    $utilitySecureKey = Read-Host 'OPENAI_API_KEY' -AsSecureString
    $utilityKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($utilitySecureKey)
    try { $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($utilityKeyPointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($utilityKeyPointer) }
}
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) { throw 'Key missing; do not start' }
if (-not (Test-Path -LiteralPath C:\sogaeding\artifacts\runtime-jev-eval\key\jev.api-key -PathType Leaf)) { throw 'Existing Jev key reference missing' }
```

**단 한 번의 고정 유료 실행 명령**이다. 이 개발 작업에서는 실행하지 않았다:

```powershell
Set-Location C:\sogaeding
& .\scripts\dtap_official_runtime.ps1 -Mode run -UtilityAcceptance -OfficialRuntime -Arm engine-on -PaidOptIn -MaxTotalUsd 5.089294 -ManifestSha256 b95c0992e67790350eb9e91e6512b1b3422da5b06ecc72ac661d463b3056a77a
```

별도 PowerShell에서 상태·수집·필요 시 중단:

```powershell
Set-Location C:\sogaeding
$utilityManifest = 'b95c0992e67790350eb9e91e6512b1b3422da5b06ecc72ac661d463b3056a77a'
& .\scripts\dtap_official_runtime.ps1 -Mode status -UtilityAcceptance -ManifestSha256 $utilityManifest
& .\scripts\dtap_official_runtime.ps1 -Mode collect -UtilityAcceptance -ManifestSha256 $utilityManifest
# 중단이 필요할 때만:
& .\scripts\dtap_official_runtime.ps1 -Mode stop -UtilityAcceptance -ManifestSha256 $utilityManifest
```

`utility_progress`의 attempted/completed/task_success/accepted/confirm/unknown/not_started와 stage_actual·stage_hold·cumulative 비용을 구분한다. 준비 시 새 시도0·미시작3·이번 비용0이다. 과거 off를 새 완료율에 넣지 않고 paired 공격 비교도 만들지 않는다.

각 과업은 공식 task_success=true, 실제 ALLOW→응답/Post, PDP 승인0이어야 다음으로 진행한다. 중간 typed 정책 DENY는 대안을 선택할 수 있지만, 최종 과업실패·미승인CONFIRM·UNKNOWN/분석/전송 장애·한도는 다음 과업의 유료 전송 전에 중단한다. **실패한 과업·남은 과업을 자동 재실행하지 않는다.** resume 금지이며 lock/키/원장을 지우거나 비용을 환불하지 않는다. 키 누락은 시작 claim 전에 거부됨을 확인했다. 사전검사 실패 시 기록을 보존하고 원인을 먼저 확인한다. PKI leaf는 준비 후2일이며 만료/parent drift이면 유료 시작 전에 거부한다.

무모델 전체 연결은 별도 OFFLINE 복사본에서 같은 진입점·실제 Controller/TLS/gateway/MCP/Post/공식 judge/collect까지 통과했다. 이는 가짜 provider의 연결시험으로, 실제 GPT/Jev utility 성공이 아니다. 최종 관련47 PASS와 별도 검토, 고정 binding은 [RESULT](RESULT.md), [REVIEW](REVIEW.md), `artifacts/20261018-normal-utility-acceptance/final-bindings.json`에 기록했다. 실모델3개 성공/MVP 전체 완료는 실제 사용자 실행 결과 확인 전 NOT_RUN이다.

---

# 이전 T-PDP-UTILITY-01 무모델 인계 기록

이번 인계에는 **새 유료 실행 명령이 없다**. 현재 parent14개는 이미 시도됐으며 완료8/미승인CONFIRM6이다. 기존 run 재실행·CONFIRM 자동 승인·역사 UNKNOWN 재시도를 하지 않는다. 새 cohort를 임의로 선정하지 않았고 실제 actor/Jev utility는 NOT_RUN이다.

새 코드의 `dtap-server-task-scope-2`는 bounded directory_tree와 서버가 검토한 정확 파일/도구 발급을 지원한다. 기존 run의 version1 grant·frozen source·키·서비스를 수정하거나 재배포하지 않았다. 경로 언급·actor 설명·모델 LEGITIMATE·ask_for_permission=True는 동의나 권한이 아니다. 추가 파일 권한은 새 서버 scope를 발급할 때 원 요청·principal·registry·PUBLIC 파일·필요한 tools를 별도로 검토해 `issue_scope(..., reviewed_resources=...)`로 결합한다. 이 발급 seam은 자동 요청 해석/자동 동의 기능이 아니다.

누적 지출 **$4.118747**, 현재 누적상한 **$5.089294**, 해당 잔여 **$0.970547**을 유지했다. 원 총상한7의 여유를 쓰거나 새 예산을 더하지 않았다. 원 CONFIRM/UNKNOWN/정산/hold/모든 결과는 보존했다.

기존 로컬 검증 이미지에서 새 관련 시험만 다시 확인하는 PowerShell 명령(네트워크/모델 호출 없음):

```powershell
Set-Location C:\sogaeding
docker run --rm --read-only --cap-drop ALL --network none --tmpfs /tmp --mount type=bind,source=C:/sogaeding,target=/workspace,readonly -w /workspace -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/workspace/src:/workspace/tools:/workspace/tests/hookgw -e CONTRACT_DIR=/workspace/docs/mvp/contracts with-human-dev:local python -m pytest -q -p no:cacheprovider tests/hookgw/test_normal_utility.py
```

수행된 최종 통합은 `artifacts/20261018-normal-utility/final-focused-integration.log`의83 PASS다. 위 명령은 새 관련62개만 재확인하며 당시 원 MCP를 새로 띄우는 명령이 아니다. 실제 원 MCP 폴더 구조·Post/OBSERVED는 `real-os-r1/`, 정확 파일 read/write/edit/Beta readback은 `real-os-exact-r3/`에 저장했다. 두 검증 모두 별도 새 컨테이너에서 합성 Jev로 수행했고 검증 컨테이너/network는 정리했다.

새 보고 `artifacts/20261018-normal-utility/report-v2.json`은 의미 DENY1/코드28과11+3 분모, benign off 미시작3/on 미시작0을 구분한다. 완료8을 task_success8로 읽거나 조건부6pair의 공격 결과를 전체 ASR로 확대하지 않는다. 구 결과를 덮어쓰지 않았다.

새 paid 비교를 준비하려면 사용자가 cohort를 명시적으로 선택하고 새 scope/source revision과 **현재 잔여 안의** 누적 원장 binding을 검토해야 한다. 현재 문서의 무모델 성공은 실제 모델 utility 성공이나 재실행 승인이 아니다. [결과와 남은 제한](RESULT.md), [별도 좁은 AI 검토](REVIEW.md), `artifacts/20261018-normal-utility/verification.json`을 함께 확인한다.
