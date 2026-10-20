> **WP-HOOK-GW-01 / SPEC5 연결 개정 (2026-10-16)**: 평소 Codex hooks·실제 agentgateway 경로의 계약은 [SPEC5](08_transparent_hook_gateway_spec5.md)와 [별도 schema](contracts/spec5.schema.json)다. 아래 SPEC4 고정3도구 내용은 기존 실험·회귀 경로에 유지한다. 새 경로 수용/미지원/사용자 LIVE 상태는 WP-HOOK-GW-01 RESULT/REVIEW를 따른다.



## WP-F3-01 / SPEC-4 동기화

2026-10-14 관리 작업팩10의 명시 위임. 현재 **MVP-SPEC-4**, 정책은 `mvp-2026-10-14-f3-v2`다. 이 상단 계약과 기계 schema가 현재 정본이며 실측 PASS/FAIL/NOT_RUN은 새로운 WP-F3-01 RESULT에서 확인한다. 뒤의 SPEC-3/v1 역사 기록은 당시 기준으로 보존하고 현재 개정과 충돌하는 과거 규칙을 현재 실행 규칙으로 쓰지 않는다.

POST_COMMENT에 `comment_mode: EXACT | ISSUE_SUMMARY`를 추가했다. 생략하면 EXACT, 정확 본문 필수. ISSUE_SUMMARY는 사용자가 이슈 요약 댓글1회를 직접 선택하고 본문을 사전 발급하지 않는다. SUMMARIZE_ISSUE는 읽기만 허용한다. 공개 MCP 세 도구의 입력은 유지하고 agent의 source/approved/judge 자가 선언은 권한이 아니다. 이전 정책 세션/승인은 POLICY_CHANGED로 거부하며 기록 버전은 유지한다.

판정 순서: hard 권한/민감정보/대상/예산 → 서버 성공 읽기 출처 대조 → 필요한 후보의 독립 A(사용자/권한/후보), B(같은 입력+출처) 의미 관측 → 서버 합성. 정상 외부 데이터/제목/URL/공격 문구 보고는 데이터로 사용할 수 있다. 문서의 추가 명령을 따르는 행동은 DENY, 모호한 비민감 후보만 CONFIRM. API/필수 문맥 실패는 DENY이며 승인으로 우회하지 않는다.

analysis_text는 마스킹 후 암호화 저장, 자료당8192문자/UTF8 16384byte, 외부자료8개/총16384문자·32768byte, ingest32768byte 유지. 잘림/누락은 명시하고 ISSUE_SUMMARY는 같은 이슈의 성공한 읽기 및 검증한 출처 근거가 필요하다. UI512발췌와 분석 텍스트는 별개다.

짧은 transaction에서 단회 client ID/예산/immutable snapshot·lease 고정 → transaction 밖 두 judge 요청 → revision/세션/정책/grant/인자 재확인 → 판정/근거 저장 → 기존 원자 reserve/실행. 분석ID·stage·snapshot hash·검증refs/reasons를 CheckReply/도구결과/이력에 연결한다. 문맥 변경/lease만료는 자동 유료 재분석하지 않는다. 댓글 예산1·단회 승인·UNKNOWN 미환불/미재시도는 유지한다.

Judge는 공식 SDK/HTTPS Responses, 도구0·retry0·proxy환경상속0·redirect0·store:false다. Control 전용 ignored `runtime-f3-01/control/judge.api-key`만 읽고 Gateway/브라우저/actor 문맥에 주입하지 않는다. 요청15초, A/B 합계20초, checks client25초, MCP launcher40초(최소35초), 저비용 resolve/reserve/report1초 유지. 요청당output2048, 개발 judge총24요청·semantic session후보2개·actor180초×최대2episode를 기록한다. fake 시험은 실제 의미 정확도 증거가 아니다.

현재 자동 시연 전용 host8020/8021과 새 DB/PKI는 기존8000/8001·B8010/8011을 교체하지 않는다. 보안 설계/가이드·수정/재진단·실측·독립 검토는 WP-F3-01 handoff로 인계하며 plans/harness의 상태는 관리만 바꾼다. 전체 C/D를 이번 구현의 선행조건으로 추가하지 않는다.


---

## SPEC-3 당시 문서·준비 기록 (역사 참조)

# 요구사항 추적표와 구현 분담

MVP-SPEC-3. 구현 시작 시 이 표에 실제 파일·commit·시험 결과를 채운다. 제품 구현·수용시험은 아직 NOT_RUN이다. Docker 개발 환경·계약 게이트의 확인 결과는06과 구분한다. 예상 코드 경로는02에 있다.

## 1. 요구사항→통제→시험

| 기능 요구 | 보안 요구 | 구현 책임 | 수용시험/완료 기준 |
|---|---|---|---|
| FR-01 세션·권한 | SEC-02/04/10 서버 발급·작업 권한·역할 인증 | Control session/auth | AT-03/08/13, AC-01/05 |
| FR-02/04 MCP·실행 전 검사 | SEC-01/09/10 완전한 집행·입력·API 인증 | Gateway/registry/PDP client | AT-04/09/11/13, AC-01/03/06 |
| FR-03/06 출처·관측 | SEC-02/04/08 신뢰 출처·관측·최소 이력 | source collector/ledger | AT-03/08/10, NT-03, AC-08 |
| FR-05 정책·범위 | SEC-03/04/05 읽기·작업 범위·인자 결합 | policy/canonical action | NT-01/02, AT-01/02/05, AC-02/03/05 |
| FR-07 확인·승인 | SEC-05/06 인자 결합·단회 승인 | approval/control UI/reserve | NT-03, AT-05/06/07, AC-04 |
| FR-08 원자적 실행 | SEC-05/06/07 결합·원자 소비·장애 처리 | reserve transaction/executor | AT-07/09/12/14, AC-06/07 |
| FR-09 기록·UI | SEC-07/08 감사 실패·세션/비밀 보호 | ledger/templates/effects | AT-08/10/12, AC-08 |
| FR-10/11 재생·Codex LIVE | 05 §5 모드·주장 분리, SEC-02/04 최초 사용자 원문·작업 범위 | REPLAY runner / Codex CLI launcher | NT-01..03/AT-01/15, AC-09/10 |
| FR-12 재현 | SEC-01..10 | 실행 스크립트/README/점검 | AC-01..10, 새 환경 재현 |

SEC 이름과 시험 세부 내용은05가 원문이다. 위 표의 짧은 이름은 탐색용이며 enum·권한은03을 따른다. 시험 ID가 변경되면 추적표도 같이 갱신한다.

## 2. 1인 개발의 책임

PLAN-2에서 개발·구현 사람 담당자는 **사용자 1명**이다. P1 p.1의 4인 분담은 당시 제출 이력이며 현재 개발 작업 배정이 아니다. 최신 일정·파일 소유권은 [오늘 계획](../plans/02_today_mvp.md)을 따른다.

| 역할 | 현재 책임 | 인계할 계약/결과 |
|---|---|---|
| 사용자 + 개발 세션의 통합 AI | 세션·정책·DB·Gateway·executor·출처·승인·UI를 의존 순서로 통합 | FR/SEC별 실제 코드·시험·효과와 안전한 RESULT |
| 선택적 AI 보조 | 계약이 고정된 비중복 파일의 구현·fixture 지원 | 실제 변경·검증, 공통 파일은 통합 AI에 요청 |
| 작성자와 별도 AI 검토 | diff·실제 효과·가이드 적용을 독립 문맥에서 검토 | REVIEW와 재현 증거. 공식 진단기관 검수와 구별 |
| 이 관리 세션 | 계획·범위·공통 계약 변경 판단·장부의 최종 상태 | 증거 검토 뒤 완료/보완과 다음 작업 |

추가 사람이 개발·검증을 병렬로 수행한다고 가정하지 않는다. 상태 전이·reserve·공통 schema의 최종 작성자는 개발 통합 AI 한 명이며 알고리즘을 두 곳에 중복 구현하지 않는다. 별도 AI 검토가 없으면 자가 점검으로 보고하고 독립 검토는 미완료로 남긴다.

## 3. 작업 의존 순서와 완료 증거

| 작업 | 선행 | 완료 증거 |
|---|---|---|
| T-00 저장소·Compose·의존성 고정 | Docker 엔진 확인 | 개발 이미지/package 버전, ignore 규칙, 기준 commit, Compose 정적 검사·개발 이미지 build·계약/하네스 게이트. 제품 src·health는 선행조건 아님 |
| T-S01 보호 전송 준비 | T-00 | ADR-S01의 SPEC-3 기계 동기화·TLS/신뢰 구성·독립 fixture 검증. 실제 제품 인증 경로의 검증은 T-01/T-04에서 확인 |
| T-01 제품 health·MCP 인증 smoke | T-00/T-S01/T-02의 auth resolve 최소 구현 | 최소 control/gateway 기동·health, valid/wrong/expired/audience 오류, list/call 성공 |
| T-02 sessions·schema·registry | T-00 | 서버가 grant 생성, typed input, role 분리 |
| T-03 정책·checks·canonical hash | T-02 | 요약 댓글/비밀 DENY, 정확한 댓글 ALLOW |
| T-04 reserve·effects·report | T-01/T-03 | 실제 효과1 또는0, 중복/병렬/UNKNOWN 시험 |
| T-05 source collector·timeline | T-02/T-04 | 같은 session source와 판정·실행 연결 |
| T-06 CONFIRM·approve·resume | T-03/T-04 | 승인 전0, exact call 승인 후1, replay0 |
| T-07 최소 대시보드 | T-05/T-06 | 출처·이유·실행·승인 화면, HTML escape |
| T-08 REPLAY 수용시험 | T-04/T-05/T-06 | 05 core 시험 기록, executor DB 대조 |
| T-09 Codex CLI LIVE 연결·정상/공격 관측 | T-01/T-04/T-05, OpenAI API·모델 설정 | 전용 CODEX_HOME·가짜 연구 workspace, 최초 user_request 일치, CLI·모델 ID, 실제 MCP 호출 원기록, 미시도/차단 구분 |
| T-10 문서·초기 진단·리허설 | T-07/T-08; T-09 결과는 별도 반영 | 재현법, core/LIVE 각각의 결과표, 첫 scan 원본, 짧은 화면 기록 |

UI보다 T-S01/T-02/T-01/T-03/T-04의 연결을 먼저 확보한다. 이후 T-05/T-06→T-07/T-08→T-09→T-10을 기본 순서로 진행한다. 비중복 파일의 AI 보조는 선택 사항이다. API 키를 기다리는 동안 core 구현·검증은 진행 가능하다. 현재 SPEC-2이며 T-S01 구현 전에는 SPEC-3 완료로 표시하지 않는다.

## 4. 증거 파일 규칙

`artifacts/<run_id>/`에 mode(REPLAY/LIVE), commit, policy_version, package versions, fixture hash, task/session/call IDs, safe timeline, effects count, test result와 scan 원본을 묶는다. 실제 키·토큰·원문 비밀을 제거한 뒤 보관한다. 시간은 ISO8601 UTC로 기록하고 화면은 한국시간으로 표시한다.

결과표는 PASS/FAIL/NOT_RUN/BLOCKED를 구분한다. CONFIRM 대기나 모델 미시도를 차단 성공·정상 성공으로 섞지 않는다. 실제 효과는 PDP 판정값과 별도로 확인한다. 첫 baseline은 수정 후 결과로 덮어쓰지 않는다.

## 5. 대회 제출까지 이어갈 항목

실제 구현과 원래 F1~F5 대응·보호 범위·변경 ADR를 개발기획서 **2. 주요 기능 및 개발환경**에 반영한다. [첨부 기준 실행표](../plans/05_contest_security_criteria.md)에 따라 보안 요구·위험/인터페이스·코딩 표준·정적/수동/동적 진단·발견/조치/재진단을 연결한다. 설계20·약점49의 비적용은 실제 기능·의존성 근거로 검토한다. 보호 전송과 내부 mTLS의 ADR-S01 결정, 첫 제품 빌드의 공급망 점검·SBOM은 필수 게이트다. agentgateway 어댑터·추가 에이전트·내장 도구 보호 확대·의미 판단·넓은 평가셋은 선택 확장으로 기본 보류한다. 오늘 문서는 6종 제출물 자체를 완성한 것이 아니라 그 근거다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
