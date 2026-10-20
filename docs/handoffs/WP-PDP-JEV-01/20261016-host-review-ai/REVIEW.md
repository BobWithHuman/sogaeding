# 호스트 수동 reviewer 준비: 별도 AI 검토

2026-10-16. 작성자와 분리된 AI 검토이며 사람 개발자는 사용자1명이다. 공식 독립 보안 진단이 아니다. 상태: **배정된 launcher·무모델 준비 범위 수용 가능 / 미해결 차단 finding0**. 실제 호스트 승인/사용자 읽기 완료는 수용하지 않는다.

## 승인 범위와 구현 대조

HOST_REVIEW_START_PROMPT 전체, 최신 AGENTS, 관리의 WP-PDP-JEV-01 검토, with-human-dev 역할/검증 reference 및 현재 코드를 읽었다. 사용자가 승인한 범위는 이번 테스트 CLI1회의 호스트 수동 reviewer와 공개 `fixtures/hookgw/notes.txt` 읽기1회다. 개발 AI 실제 모델 호출·TypeSafe 활성화·쓰기/임의 명령 승인은 아니다.

launcher의 정확한 단일 `--manual-review`는 `--api --jev-rules`에서만 유효하고 그 자식 CLI argv에 `approvals_reviewer="user"`/`approval_policy="on-request"` 두 값만 더한다. sandbox/권한·PDP·TLS·hook permissionDecision을 바꾸지 않는다. 축약·중복·다른 임의 config/profile/sandbox/yolo·추가 명령을 거부한다. PowerShell 전역 상태나 개인 config/auth에 reviewer 값을 저장하지 않고 다음 일반 `codex`는 기존 설정을 상속한다.

로컬 requirements의 reviewer/approval allowlist와 managed-hooks-only를 보수적으로 검사한다. CLI config 거부 또는 수동 경로에서 stderr 경고가 있으면 고정 issue로 readiness를 실패시킨다. cloud/기타 managed 제약은 CLI에 계속 맡기며 경고를 무시하거나 정책을 수정하지 않는다. stderr/config/개인 transcript 원문을 보고서에 넣지 않는다.

preflight는 actor API 인증/모델 접근, Jev 규칙 전용 model0, 호스트 reviewer 요청을 구분한다. CLI config accepted와 실제 사람 승인 완료는 별개다. TypeSafe 키/원장/유료 한도가 없고 의미 쓰기는 계속 NOT_AUTHORIZED다.

## 독립 검증

독립 [시험 코드](../../../../artifacts/20261016-host-review-ai/test_independent_host_review.py)와 관련 API/Jev preflight·MCP startup·manual 시험을 network-none/RO/일반 UID/cap-drop Docker에서 실행했다. 결과 **99 PASS/5.66초**, 증거 `artifacts/20261016-host-review-ai/independent-final.json`. 그중 검토자 별도21개가 정확 두 override, 허용 모드, 축약/중복/임의 인자 거부, 두 번 실행할 때 reviewer 미상속, config/auth byte 불변, PS state 미저장, managed 허용/거부·타입·hooks-only, exit0+managed fallback warning 실패를 확인했다. 실제 actor/judge/Jev 호출0·production DB/키/원장 볼륨 미마운트다.

HOST-R01: 첫 신규 preflight는 CLI exit0만으로 수동 reviewer 설정 준비를 판단했다. [공식 관리 문서](https://learn.chatgpt.com/docs/enterprise/managed-configuration)는 제약에 맞는 값으로 fallback하고 알릴 수 있음을 설명한다. 작성자가 수동 경로의 stderr를 고정 코드 `HOST_MANUAL_REVIEW_CLI_WARNING`으로 거부하도록 보완했고 독립21개 중 해당 재진단이 PASS다. 초기 source-only 지적·수정·재진단을 `findings.jsonl`에 보존했다. 이 검토에서는 실제 managed layer의 완전 집행을 주장하지 않는다.

[공식 설정](https://learn.chatgpt.com/docs/config-file/config-reference)과 [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review)를 직접 조회했다. reviewer는 승인 주체를 고르는 설정이며 sandbox 확장이 아니다. 관리 제약이 CLI override보다 우선하고 `on-request`는 승인 요청을 자동 허용하는 값이 아니다. 출처와 확인 내용은 `official-reference-check.json`에 기록했다.

## 작성자 native/실제 준비 증거 검토

`tests/hookgw/manual_review_cli_fixture.py` 및 `artifacts/20261016-host-review-fixture/native-manual-review-r3.json`을 읽었다. 실제 설치 CLI SHA=`be96b992178b1e467c225800da0d65f2c86d5eba1ef0b14632f65db381cbdfde`에서 수동 reviewer enum 수용(exit0), 잘못된 enum 거부(exit1), loopback fake Responses POST1/metadata GET2, 생성 config/auth 불변과 기본 auto_review/on-request/read-only 보존을 확인했다. 고정 가짜키·격리 CODEX_HOME/USERPROFILE/ProgramData만 사용하고 실제 키/개인 인증은 사용하지 않는다. 실제 provider 추론·제품 tool 호출0이다.

이 fixture의 수용 범위는 **NATIVE_OPTIONS_FAKE_ACTOR_AND_GENERATED_FILE_PRESERVATION_ONLY**다. 격리 ProgramData requirements는 native에서 로드됐다는 증거가 없어 **NOT_VERIFIED**, 비대화형 exec의 on-request 실효는 **NOT_PROVEN**, 실제 사람 승인은 **NOT_RUN**이다. r2의 실패를 보존하고 r3에서 이 한계를 제외한 좁은 시험 범위를 명시한 것이며 managed/사람 승인 PASS로 확대하지 않는다. 격리 fixture의 PATH 경고와 실제 host preflight의 stderr 없는 config accepted도 구분한다.

`artifacts/20261016-host-review/actual-manual-preflight.txt`는 실제 Windows PowerShell5.1에서 CLI0.154.0/TLS8032·8042/stdIO initialize→initialized→tools-list/임시 연결 정리, ready=true/issues=[]를 기록한다. reviewer user/on-request 요청 범위는 THIS_CLI_INVOCATION이고 sandbox는 상속한다. human_tool_approval=NOT_RUN_USER_NEXT, model access 미검증, semantic_write_ready=false, Jev NOT_AUTHORIZED/실제 key·ledger 없음, tools/call/turn/candidate/paid0을 확인했다. 이는 사용자 공개 notes 과업 완료 증거가 아니다.

## 가이드와 잔여 경계

이번 변경은 기존191파일의 PDP/provider·원자 예약·암호화·TLS를 교체하지 않는 launcher 범위다. 이전 세션에서 원 PDF SHA를 확인해 읽은 G4 PDF38/G3 PDF164·171·511의 권한/예외/세션 통제, G2 PDF133·135·137의 오류 최소기록/실패 처리와 연결해 검토했다. 수동 reviewer가 보안 정책을 해제하지 않도록 고정 argv·호출 한정·managed 보수 거부·warning fail-closed·비영속 저장을 확인했다. 설계20/약점49 전체 PASS나 공식 점수·조치율을 선언하지 않는다.

사용자 실제 새 CLI의 승인창·notes1회 ALLOW→OBSERVED·내용 일치는 아직 NOT_RUN이다. 사용자 절차는 한 번 승인 후 CLI 종료, 추가/다른 도구 거절, 이전 READY/UNKNOWN 미해제, TypeSafe 미활성화를 유지해야 한다. 일반 native 지원·hook 사망/timeout/malformed fail-open·개인 bob MCP·공급망 및 실제 Jev 정확도는 이번 수용 범위 밖의 미완료 항목으로 남는다.

## 최종 인계 대조와 판단

`../20261016-host-review/RESULT.md`와 `artifacts/20261016-host-review/final-index.json`을 전체 읽고 실제 명령/출력·native helper·원문4페이지·보존 기록을 대조했다. 작성자 관련 회귀285 PASS/72.01초와 Ruff PASS를 확인했다. Bandit은 오류0/High0/Medium0/Low5이며 기존 subprocess import/고정 argv 경고다. source→sink에서 shell=False 기본·신뢰된 launcher/helper·허용된 인자 경계를 확인했고 억제하지 않았다. 이를 보안49 전수 PASS로 보지 않는다.

최종193파일 fingerprint=`bdc7df912c9d2c815b9c2928814004b4afc83310fe66e6686084a0f367daa999`를 독립 재계산했으며 현재 SHA 불일치0·독립 시험 입력10파일 변경0이다. 기준선 대비 변경은 launcher/preflight/PS/관련2시험/사용 설명의6파일뿐이고 src/contract/Compose/bundle35파일 변경0이다. 새 native helper의 보고 보완은 최신 r3가 별도로 실행됐으며 실제 interactive 수동 승인 증거로 확대하지 않는다.

baseline-runtime과 final-runtime의 두 history5+5·보호 파일 hash·OpenAI 원장 count/hash가 동일했다. OpenAI22/24·남은2, 기존 GPT/Jev READY/UNKNOWN·개인 config/auth·키/CA/token/profile·notes를 보존했다. 최종4페이지 원문 PDF3문서 SHA도 다시 계산해 불일치0이다. `artifacts/20261016-host-review-ai/final-handoff-verification.json`에 대조 결과를 남겼다. 임시 metadata 연결 생성/정리와 실제 tool/turn 실행을 구분한다.

사용자 절차가 `codex --manual-review --preflight`와 이어지는 명시적 `codex --manual-review`를 분리하고, 정확한 공개 notes 한 건만 이번 요청에 한해 승인·내용/새 call의 ALLOW→OBSERVED 대조·CLI 종료를 요구함을 확인했다. 세션/서버 전체 승인·다른 도구·추가 요청·TypeSafe 활성화를 허용하지 않으며 경고/403/UNKNOWN이면 중단한다. 다음 평소 CLI는 기본 reviewer를 상속한다.

따라서 **사용자가 명시 승인한 테스트 CLI1회를 위한 옵션 구현·오프라인 준비 인계는 수용 가능**하다. 이것은 자동 검토403의 실제 복구 완료, 실제 managed 계층 전수 집행, 대화형 승인창/공개 읽기 성공, Jev 성능 또는 전체 MVP 완료 판정이 아니다. 실제 결과는 사용자 새 CLI1회에서 확인하고 관리가 후속 수용을 판단해야 한다.
