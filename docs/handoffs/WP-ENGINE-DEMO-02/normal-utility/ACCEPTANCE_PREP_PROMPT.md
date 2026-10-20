# T-PDP-UTILITY-PREP-01: 기존 정상3개 실모델 수용시험 준비

2026-10-18 관리 배정. T-PDP-UTILITY-01의 구현·무모델 검증·별도 검토를 수용했다. **다음은 기존에 고정한 정상3개를 새 scope 버전에서 실제 검증할 단회 실행본 준비**다. 개발 중 실제 actor/Jev 호출·기존 run 재실행·예산 증액은 하지 않는다. 관리의 준비 배정은 유료 전송 실행 승인이 아니다.

## 필요한 입력만 읽기

`with-human-dev`, AGENTS, 이 작업서, 같은 폴더의 RESULT/USER_RUN/REVIEW, `artifacts/20261018-normal-utility/verification.json`과 관련 준비/launcher 함수만 읽는다. 이전 전체 계획·PDF·원로그 통독/통과83개 전체 재실행/조사 AI 추가는 하지 않는다. 구현 통합1개→관련 시험→최종 관련 통합1회→별도 좁은 AI 검토1회다.

검토된 소스6개 SHA는 verification.json에 있다. 관리도 현재 파일6개 hash 일치, 실제 원 MCP tree/OBSERVED·exact read/write/edit/Beta readback·원 collected 결과 보존을 확인했다. 이 무모델 증거를 실제 모델 성능으로 표현하지 않는다. `search_files`는 새 scope2에서 보류이며 exact resource는 서버 검토 발급 기능이지 자동 권한 추론이 아니다.

## 고정 범위

- 순서: `os-filesystem/benign/2` → `os-filesystem/benign/3` → `os-filesystem/benign/4`.
- 처음부터 정상 확인용으로 고정한 동일3개다. 이번에 쉬운 새 과업을 선택하거나 결과에 따라 갈아 끼우지 않는다.
- **새 engine-on3개만** 자율 GPT-5.2/low + 실제 Jev로 검증할 준비를 한다. engine-off·공격 과업·유료 pilot·반복 평가·AgentDojo·native Codex CLI·대시보드는 이번 범위 밖이다.
- actor의 원 system/task prompt·catalog18개·공격 없는 원 setup/도구/공식 judge와 모델 snapshot/effort는 유지한다. 고정 후보나 정답을 actor/Jev에 주입하지 않는다. 필요한 코드/허용 범위 제약은 실제 도구 거부로 관측한다.
- old v1 grant를 복사한 뒤 새 코드와 결합하지 않는다. 이3개 원 요청의 hash·실제 registry·Alice·원 초기 image와 새 scope2를 명시적으로 다시 결합하고 검사한다. 새 exact 파일 grant가 필요 없다면 발급하지 않는다.
- 정상3개는 benchmark utility 수용시험이다. 새로운 공격 방어율·off/on 개선율·전체 DTAP100 완료를 주장하지 않는다.

## 과거 원장과 한도

parent는 `artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup`, manifest는 `bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f`다. parent14개는 이미 종료됐으며 on완료8/CONFIRM6, 역사 consent/11 UNKNOWN은 보존한다. 기존 run 재개·CONFIRM 자동 승인·UNKNOWN 재실행은 하지 않는다.

- 원 누적 명목비용 **4.118747 USD**, 현재 누적상한 **5.089294**, 해당 잔여 **0.970547**, hold0, 기존 provider 예약420개가 기준이다.
- 원 총상한7의 미배정 여유를 자동 전용하지 않는다. 새1.80·새0.970547을 과거 비용과 별도로 발급하면 안 된다.
- 기존 broker·settlement+미해결 hold·parent fingerprint·소스/image 검사를 재사용한다. 별도 revision의 모든 새 provider 비용을 현재 잔여 안에 원자적으로 누적한다. 다른 fork 동시 실행/이중 예약을 막는다.
- 준비 시 부모에 새 지출/owner/drift가 있으면 안전 거부한다. provider 요청 전 누적정산+hold+다음최대예약을 검사하며 평균 실제요금으로 최대예약을 축소하지 않는다. 세 과업 완주나 실제 요금을 보장하지 않는다. 설정을 바꿔 예산을 맞추지 말고 부족하면 남은 과업 미실행을 기록한다.

## 최소 구현과 수용

기존 준비/verify/launcher/원장 후속 경로를 필요한 만큼만 확장한다. 새 범용 framework·새 공급자·새 보안 도메인을 만들지 않는다. 기존 서비스/키/개인 설정/원장/동결 source를 수정하지 않으며 준비본은 모델 비활성 상태로 둔다.

1. 준비3개와 새 source/scope/원 snapshot·manifest·누적비용 결합을 검증한다. 실제 실행은 단일 arm·순차로 준비한다.
2. 가짜 provider로 **사용자가 복사할 실제 진입점**부터 controller→새 scope2→원 MCP/Post→공식 정상 judge→collect의 연결을 좁게 확인한다. tree는 저장된 후보 시험만으로 새 자율 actor 성능을 PASS라고 하지 않는다. 기존 원 MCP proof는 유효 범위에서 재사용하되, 준비된 scope가 실제 controller에 전달되는지는 새 시험에서 확인한다.
3. 중간 typed 정책 DENY는 기존처럼 actor가 대안을 선택할 수 있다. 다만 과업 최종 task_success=false, CONFIRM 미승인, UNKNOWN/분석·전송 장애, 예산 한도이면 **후속 과업 유료 전송 전에 중단**한다. 완료 여부만 보고 다음 단계로 넘어가지 않는다. 실패한 과업의 자동 재실행도 없다. 중단·나머지 NOT_STARTED·원래 결과를 별도 보존한다.
4. 성공 조건은 새3개 모두 공식 task_success=true이며 ALLOW/실제 응답/Post가 연결되고 사람 PDP 승인0이다. 실패나 모델 공격 미시도는 그대로 표시한다. required consent를 몰래 자동 승인하지 않는다.
5. 초기 권한/예산/PKI/network/source 검사 실패는 provider 요청 전에 설명 가능한 오류로 종료한다. 특히 OPENAI_API_KEY 누락이 start claim을 먼저 소비하지 않도록 검사 순서와 사용자 절차를 확인한다. 실제 키를 출력하거나 기록하지 않는다.
6. report는 attempted/completed/task_success/CONFIRM/UNKNOWN/not_started와 현재 단계 실제비용/누적비용을 구분한다. 과거 off 결과를 새 완료율에 넣지 않는다. on3개 단독검증이므로 paired 공격 비교를 생성하지 않는다.

새 구조가 기존 14개 준비 builder와 묶여 부작용을 내지 않는지 관련 경계만 검사한다. metadata/API/Post 장애·정책 거부·한도 동시성·재사용·parent drift를 실제 변경에 영향받는 범위에서 검증한다. 검토 후 source/manifest/명령을 동결하고 최종 **무모델 check**까지 수행한다. 이 단계의 실제 provider 호출은0이어야 한다.

## 소유권·인계

쓰기: 필요한 benchmark 준비/검증/보고 함수, 관련 scripts/tools/tests, 새 안전 artifacts/격리 revision, 이 폴더의 RESULT/USER_RUN/REVIEW. 통합 담당1개다. core 권한/재귀/임계치의 추가 변경은 원인이 확인된 좁은 결함에 한하고 검토/관련 시험을 갱신한다. docs/plans·harness·AGENTS는 관리 채팅만 변경한다.

기존 RESULT/REVIEW의 무모델 근거와 실패 이력은 보존한다. USER_RUN에는 secure key 입력 확인, 고정 run 한 번, status/collect/stop과 실패 시 재실행 금지를 한 번에 제공한다. **실제 유료 run은 시작하지 말고**, 준비 상태·hash·모델·정확한3개·누적상한·잔여·제약을 관리에 인계한다. 유료 명령의 사용자 선택 후 결과를 확인하기 전에는 실모델 정상3개 성공이나 MVP 전체 완료라고 표시하지 않는다.
