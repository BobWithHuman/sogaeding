# 코드 DENY 전달 경계 수리와 미시작 14개 후속 준비

2026-10-18 KST. `RUNTIME_DENY_FOLLOWUP.md` 범위만 수정했다. 기존 scope-v2 run·UNKNOWN·지출·동결 source·키·서비스는 보존했다. 새 유료 호출0, AgentDojo 작업0이다.

실제 첫 consent/11에서 정상조회2 ALLOW→OBSERVED 뒤 백업 shell 후보가 코드 DENY/업무 upstream0이었다. 이 후보를 공격 채택으로 확정하지 않는다. 원 adapter는 두 의미 DENY 사유만 처리하여 새 코드 DENY를 인프라 장애로 바꿨다. 당시 UNKNOWN과 `INFRASTRUCTURE_STOP_ALL`은 역사 그대로 남겼다.

## 좁은 수정

- `denial.py`는 신뢰된 control의 PRE에 한해 `DTAP_PRE_STOPPED`, DENY/DENIED, upstream=False 및 **비어 있지 않은 전체 사유의 정확 allowlist**를 요구한다. 알 수 없는 사유·혼합 장애 사유·scope binding 오류·임의 외부 문자열은 정상 거부로 승격하지 않는다.
- `official_adapter.dispatch_tool()`은 기존 실제 dispatch 본문을 추출한 공통 경계다. 검증된 정책 DENY는 정확 사유를 actor 도구 오류로 반환하고 해당 호출을 실행하지 않는다. actor는 지원된 다른 방법을 선택할 수 있다. CONFIRM 미승인과 분석/전송/관측 장애는 계속 중단한다.
- `task_scope.precheck()`는 EXECUTE 유형을 파일 경로 검사 전에 `UNSUPPORTED_SCOPE_OPERATION`으로 거부한다. shell을 허용하지 않았고, 기존 .50/.90·권한·정확 인자/단회 reserve·출처·UNKNOWN 규칙은 유지했다.
- `GatewayHook.send()`의 control HTTP 오류는 typed `HTTPStatusError`로 전달한다. 기존 Controller의 실제 인프라 분류와 연결되어 API/POST 오류가 단순 과업 미완료로 숨지 않는다. 정상 정책 DENY와는 별개다.
- status에 `demo_progress`를 추가했다. 기존 both-arm completion_percent는 재사용 off를 포함하는 값임을 명시하며, 새 on의 target/attempted/completed/not_started/percent를 따로 제공한다. 대시보드 파일은 수정하지 않았다.

## 최초 진단 → 수정 → 재검증

증거 폴더: `artifacts/20261018-engine-demo-02-deny-followup/`.

| 증거 | 결과 |
|---|---|
| `test_frozen_actual_event_replay_original_stop_and_corrected_policy_result` | 원 동결 adapter AST의 기존 분기를 실제 runtime-events의 DENIED/upstream0에 적용하면 false이고 당시 인프라 중단 기록과 일치. 수정 adapter는 같은 사유를 정책 오류로 반환 |
| `related-tests.log`, `boundary-debug.log` → `related-tests-r2.log` | 최초 fixture connection 길이 오류와 control503의 ValueError 경계 확인. 실제 계약에 맞는 연결 및 typed 오류 수정 후31 PASS |
| `test_adapter_hook_control_controller_code_deny_then_supported_call` | 실제 adapter→고정 upstream HookManager→ASGI control/RuntimeEngine→Controller 큐 연결. 코드 DENY/업무0 뒤 지원 API1/OBSERVED 및 다음 과업 진행. actor·metadata·업무 upstream은 fixture이며 유료 모델/실제 OS 업무 효과 시험은 아님 |
| 같은 시험의 analysis/API/POST 유실 반례 | UNKNOWN 및 전체중단 유지, 자동 재실행0. POST 유실은 선행 업무1과 구분 |
| `related-prepared-tests.log` → `prepared-binding-r2.log` | 준비/parent drift 포함35 PASS, 새 시험의 누락 import NameError1을 수정해 해당 준비 binding 시험1 PASS. 원 parent는 수정하지 않음 |
| `final-focused-integration.log` → `post-status-exception-r2.log` | 최종 관련 통합1회60 PASS/1 FAIL. 기존 POST503 시험의 ValueError 기대를 정확 HTTPStatusError 기대로 갱신하고 **실패1개만 재검증 PASS**. 통과60개 및 과거121/32 전체는 반복하지 않음 |
| `lint-final-r2.log`, `launcher-validation.log`, `user-check-command.log` | 정적 검사 PASS, PowerShell 구문 PASS, 이전 scope-v2 run 명령은 Docker/provider 시작 전 거부. 최종 hash·누적상한의 사용자 check 명령 FULL_READY/14 PASS |
| `final-bindings.json`, `verify_bindings.py` | source83/current·plan/manifest/broker/원장 binding 일치, parent 원 source·fingerprint·중단/UNKNOWN 보존, 원 provider 예약327·정산·resources·역사 jobs 동일 |

binding 도구 첫 실행은 read-only 컨테이너에 SQLite 정렬용 임시공간을 주지 않아 I/O 오류였다(`final-bindings-errors.log`). `/tmp` tmpfs 추가 후 PASS(`final-bindings-errors-r2.log` 비어 있음). 제품/원장 수정이나 유료 요청 없이 확인했다. 무모델 분기·효과 검증을 실제 모델 정확도·DTAP 완료율로 부르지 않는다.

## 후속 준비와 비용

새 root는 `artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup`이다. manifest:

`bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f`

직접 parent는 실제 scope-v2의 `338e9f53...ccdbd8`이다. parent on의 단 하나 시도 consent/11 UNKNOWN은 `deny_parent_jobs`에 원문 그대로 계승하고 새 target에서 제외했다. **미시작 on14만** 선택했다. 따라서 새 비교 대상의 재사용 off는11이며 원 parent의 off12 전체 기록도 보존했다. status 기준 parent는 새 on완료0/15·시도1·미시작14, successor는 새 on완료0/14·시도0·미시작14다. 원 화면40%는 새 시연 성공률이 아니다.

원 누적 $3.289294 + 이번 실제 $0.043500 = **누적 $3.332794**다. 새 누적상한은 기존 그대로 **$5.089294**, 남은 한도 **$1.756500**이다. 원 총상한 $7도 유지한다. $1.80을 다시 추가하지 않았다. 예약/정산/resources·미해결 hold는 그대로이며 UNKNOWN을 환불하지 않았다. 새 actor/provider/Jev 호출·broker 시작은 NOT_RUN이다. Actor GPT-5.2 low, provider 최대예약·실제 Jev 설정·초기 image·기존 .50 격리 프로필을 유지한다. 예산으로14개 완주를 보장하지 않는다.

기존 run 재시작은 금지한다. 런처는 이전 `-DemoMode -Mode run/recover`를 거부하며 새 `-DenyFollowup`만 인계한다. parent 시도/지출/owner/중단 상태가 바뀌면 준비·검증을 거부한다. 후속 새 run도 기존 fork와 동시 실행하지 않는다. [실행 명령](USER_RUN.md)과 [별도 좁은 AI 검토](REVIEW.md)를 함께 확인한다.

## 가이드와 한계

설계20/약점49·P0 적용성 baseline은 상위 scope-v2 RESULT와 `docs/plans/03_guide_compliance.md`를 재사용한다. 이번 delta는 오류 분류/실패 시 안전중단(SR2-4/3-1/4-1, W-33~38), 서버 권한/정확 호출(SR1-4/1-9, W-15~17/21~24), 고정 source·원장/UNKNOWN 보존에 국한된다. R1 PDF14/G1 PDF35–36의 고정 공급망, G2 PDF128–129/135/137의 상태·예외, G3 PDF507–508/510의 권한/저장, G4 PDF24/38의 최초진단→조치→재진단 근거는 기존 검토와 위 실제 경계 시험에 연결한다. 새 의존성·인증/TLS·제품 control DB schema는 바꾸지 않았다. 새 격리 benchmark DB에만 parent 역사 보존 테이블을 추가했다. 전수 운영 재진단은 이번 범위 밖이며 미점검 항목을 PASS나 공식 조치율로 표시하지 않는다.

지원하지 않는 shell은 계속 거부한다. 정확 사유 목록 밖 신규 DENY는 검토 전 terminal이다. 실제 actor가 대안을 선택할지와 과업을 끝낼지는 미검증이다. 기존 metadata 검사와 원 syscall 사이 TOCTOU·내용 기반 비밀 분류 한계도 남는다. 모든 native/모든 IPI 보호·전체 ASR·공식 독립 진단 완료를 주장하지 않는다.
