# V5 최소 실제 관측 준비 — 기존 평가 도구 재사용

관리 배정 2026-10-17. with-human-dev를 적용한다. **이번 작업은 구현·무모델 검증·별도 검토·실행 가능한 준비까지다. 실제 TypeSafe/actor 요청, 서비스 교체, CLI 시작은 하지 않는다.** 관리 정본/장부는 수정하지 않는다.

## 수용한 기준과 목적

- ADR-P03 및 `20261017-decision-attribution/RESULT.md`/별도 REVIEW의 V5 내부 후보를 오프라인 구현 범위로 수용했다. 현재 V3 서비스와 사람 승인 쓰기 성공은 보존한다.
- 원 V4 정상·공격은 모두 CONFIRM이다. 기존 위험 관측에서 정밀 귀속 조건만 분리한 반사실 공격 DENY는 새 Jev 답이 아니다. V5 실제 `behavior` 응답을 확인해야 한다.
- 새 정상/공격 자료를 만들지 않는다. `artifacts/runtime-jev-followups/followup-auto-v4/plan/requests.json`의 **정확한 두 snapshot**을 사용해 비교한다. 질문/정책만 V5 `build/compose_view/combine_behavior`로 교체한다. 과거 확률/typed 답을 새 질문의 답으로 승격하지 않는다.

## 작은 변경으로 완성할 범위

1. 기존 `scripts/jev_eval.ps1`/`tools/jev_eval.py`의 준비·inspect·preflight·evaluate·collect·ledger/실패/usage 경로를 재사용해 고정 run ID **`followup-behavior-v5`**를 연결한다. 프로필별 build/compose·고정 입력/한도만 분리하고, V4 runner를 통째로 복제하거나 새 ps1/CLI/UI/예산 DB 체계를 만들지 않는다. 필요한 함수와 관련 시험부터 읽는다.
2. 동결된 같은 정상 A→B, 공격 A→B의 **최대4요청**이다. 오류 시 뒤 요청은 중단하고 자동 재시도하지 않는다. 성공 여부/기대값은 로컬 비교에만 쓰며 모델 wire에 case ID·정답/평가 지시를 추가하지 않는다. V5 원래 wire의 catalog short key/원문과 A/B 격리는 유지한다.
3. **표준 JevClient**와 현 TLS/응답계약2/사용량 기록/.90 경계/민감값 guard를 쓴다. V5는 hash를 서버 inventory에만 두므로 V4 전용 `FixedPublicDigestClient` 예외를 새 경로에 확장하지 않는다. 기존 키를 역할별 RO로 참조하고 재입력·복사·출력하지 않는다.
4. 준비 시 후보4개, 실제 worker 소스·schema/프로필·원 snapshot/요청 wire·image를 manifest에 결합한다. inspect는 전송될 정확 자료/목적지/질문/제안 한도, preflight는 무모델 검증과 NOT_VERIFIED_NO_REQUEST를 표시한다. `ready`를 실제 모델 성공으로 표시하지 않는다.
5. 기존 ledger는 읽기 전용 부모 근거로 묶는다. 기존 실패·usage UNKNOWN·예약 소비·result·manifest는 그대로다. 새 별도 allowance는 **사용자가 evaluate에서 선택하기 전에는 미승인·disabled**다. prepare는 지출권한/원장 초기화가 아니다.

제안 한도(승인이 아님): 새4요청/입력예약256000, 전체 역사17+4=**21요청**, 예약1088000+256000=**1344000**. demo8+V4평가4+이번4를 함께 추적하는 누적 필드가 필요하면 **16요청/1024000**이며, 이를 기존 demo ledger8/8의 증액으로 구현하지 않는다. 추가 actor/CLI는0, 기존3/3은 재개하지 않는다. 금액은 실제 provider 요율 확인 없이 보장하지 않는다.

## 허용 파일과 보존

- `tools/jev_eval.py`, `scripts/jev_eval.ps1`, 관련 `tests/hookgw/`의 필요한 시험, 해당 평가 설명 문단만 수정한다. V5/schema 후보는 원칙적으로 유지하며 연결 결함으로 수정이 필요하면 이유·새 hash·관련 반례를 명시한다. Engine/server/승인/DB 상태/compose/일반 native는 이번 범위 밖이다.
- 기존 V4 동결54파일과 원 결과는 변경 전 대조한다. 이번에 변경을 허용한 평가 소스는 원본 snapshot을 안전한 증거 폴더에 먼저 보존한다. 원 manifest를 덮어쓰거나 source mismatch를 숨기지 않는다. 과거 collect는 역사 결과·실제 source 일치 여부를 정직하게 유지한다.
- 새 run은 기존 run과 분리한다. 기존 준비 폴더를 재활용/덮어쓰기하지 않는다. 원 데이터는 합성 고정 자료만 사용하고 키/암호화 업무본문을 읽지 않는다.

## 검증과 인계

관련 fake transport/worker로 정확 wire 4개·표준 guard·typed 결과를 확인한다. 정상 높은 행동확신 ALLOW, 확정 외부추가행동 DENY와 낮은 행동확신 CONFIRM, 입력/ref 변조 차단, 첫 오류 중단/추가 비용0, 유효 usage 보존, 한도/parent binding·재실행 거부·오래된 소스 차단을 확인한다. 기존 평가 모드와 collect의 관련 회귀 및 실제 PowerShell5.1 무모델 점검을 수행한다. 최종 필요한 통합은 한 번, 최종 후보의 별도 AI 검토는 한 번이다. 이미 통과한 제품 전체 시험을 문서/hash 기록 때문에 반복하지 않는다. 필수 PDF/P0 연결은 해당 변경 페이지·기존 근거를 재사용한다.

`docs/handoffs/WP-MVP-DEMO-01/20261017-v5-eval/RESULT.md`, `USER_RUN.md`, 별도 review 폴더와 안전한 원증거를 인계한다. **사용자에게 준비를 다시 시키지 말고**, 준비가 실제로 완료된 뒤 고정 manifest hash와 필요한 한도가 모두 들어간 **복사 가능한 evaluate 한 명령**, 이어 collect 한 명령을 제공한다. 가격·자료·추가 한도를 짧게 설명한다. 실제 호출은 관리 확인 및 사용자의 해당 명령 실행 전까지0이다.

실제 평가의 통과 관측은 정상 ALLOW/공격 DENY이며 두 예제의 연결·판정 관측일 뿐 정확도/전체 IPI 보호 증명이 아니다. 결과가 뒷받침되면 다음 작업은 기존 gateway/CLI의 한정 파일 효과 통합이다. 다시 CONFIRM/불일치면 결과를 보존하고 모델 적합성/실제 질문별 관측을 검토한다. **자동 재시도·임계치 임의 하향·같은 예제에 맞춘 새 질문 버전/새 유료 run을 연속 생성하지 않는다.**
