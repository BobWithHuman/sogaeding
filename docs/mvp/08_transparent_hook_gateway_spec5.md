# SPEC5: 평소 Codex hook / 실제 gateway 연결

> WP-PDP-JEV-01/ADR-P02의 선택적 개정: [규칙 우선 Jev 계약·사용 절차](09_rules_first_jev.md). 기존 GPT/SPEC4 실험은 보존한다. Jev 정책은 `hookgw-2026-10-16-jev-v1`, 내부 계약 `jev-slots-context-1`/질문 `jev-narrow-1`이다. 실제 기존 GPT 제품의 OpenAI 사용량은 현재22/24·남은2이며 아래 B 보완 당시18/24는 역사 기록이다. Jev는 별도 DB/8032·8042/rules-only opt-in, 실제 모델 평가·유료 한도 미승인 상태다. inline 마커 삽입/제거는 구현하지 않는다.

2026-10-16, 작업팩13 위임 개정. SPEC5는 `app.transparent`와 `compose.hookgw.yaml`의 새 경로다. 정책 `hookgw-2026-10-16-v1`. 기존 `app.control`/`app.gateway`와 OpenAPI·3도구 schema의 SPEC4는 역사·회귀 fixture로 보존한다. 새 연결 구현과 오프라인 검증은 전체 MVP 수용/DONE을 뜻하지 않는다. 실제 상태는 WP-HOOK-GW-01 RESULT/별도 REVIEW를 따른다.

## 사용자 흐름

최초 머신 연결 후 현재 터미널의 `codex` 함수가 설치된 native CLI를 실행한다. 기본 연결은 사용자 개인 설정·인증을 상속한다. WP-HOOK-GW-02의 `hookgw_connect.ps1 -Api -Model <id>`는 이번 호출에만 custom OpenAI Responses provider/env_key를 명시하고 개인 로그인·config/auth는 유지한다. 프롬프트를 자동 입력하지 않는다. API 모드는 모델 없는 preflight가 준비 실패를 보고하면 CLI를 시작하지 않는다. `/hooks`에서 정확한 정의를 검토·신뢰한다. 같은 이름의 기존 hook 설정이 있으면 조용히 덮어쓰지 않고 시작을 거부한다. 아직 자동 병합은 지원하지 않는다. 세션별 connection은 내부 생성·환경 전달되며 작업별 대시보드 등록이나 token 복사는 없다.

`UserPromptSubmit` → 실제 session/turn/요청, `PreToolUse` → 실제 도구/인자/call, `PostToolUse.tool_response` → 완료 결과를 연결한다. 최신 요청만 덮어쓰지 않고 실제 사용자 대화를 순서대로 보관해 판단한다. 외부 자료의 사용자/승인/출처 자가 선언은 권한이 아니다. 이력과 예외 승인은 별도 human 자격증명만 사용한다.

## 실행 경로

| 경로 | 실제 집행 |
|---|---|
| native apply_patch, 제한 Bash | trusted Python hook이 TLS PDP 결과를 기다려 explicit deny 또는 기본 권한 유지 `{}`를 반환한다. Codex 자체 승인을 확대하는 allow를 출력하지 않는다. |
| with_human MCP read_file/write_file | stdio bridge → HTTPS 실제 agentgateway v1.6.0 → HTTP extAuthz(mTLS) → private mTLS file upstream. 단순 MCP tool-name 인가 기능을 본문 인가로 오인하지 않는다. 실제 HTTP proxy가 MCP JSON-RPC를 전달한다. |
| 다른 MCP/hosted 도구/재입력 | 자동 프록시·보호를 주장하지 않는다. 현재 adapter의 미지원 도구는 거부한다. hosted/special 경로는 hook 자체가 없을 수 있다. |

새 MCP는 특정 이슈/댓글이 아닌 등록 workspace의 일반 UTF-8 파일 읽기·쓰기다. shell 실행 upstream은 도입하지 않았다. 프로젝트 안의 제품 신뢰 코드·설정·키·관리 문서·원증거는 지원 쓰기에서 보호한다. 정상 일반 소스/문서는 편집할 수 있다. `src/app` 전체는 이 저장소의 보호 제품 코드이므로 MVP 사용자 데모는 `fixtures/hookgw` 또는 별도 일반 파일을 사용한다. 제품 자체를 개발·업데이트하는 행위는 이 보호 런처 밖의 명시 개발 작업이다.

## API / 인증 계약

제어 public TLS8030과 private mTLS8050은 분리한다. `/authz`는 public listener에서 거부한다. forwarded headers/proxy 환경을 신뢰하지 않는다.

| API | 자격/동작 |
|---|---|
| POST /connect | machine.token → 역할이 낮은 새 connection bearer. 작업 등록 없음. |
| POST /disconnect | machine.token + connection. 같은 machine의 session 미결합 metadata 연결만 삭제한다. 사용자 세션에 결합한 연결은 종료할 수 없다. |
| POST /event | machine.token + connection/session/turn. 세 event를 분리. 추가 user_request/source_ids/approved 필드 거부. |
| POST /transport-observed | trusted bridge의 machine.token + connection/tool/args/정상 MCP result. 실제 반환 자료를 암호화 고정. 승인이나 실행 영수증이 아니다. |
| POST /transport-failure | 같은 trusted bridge만 실행 후보를 UNKNOWN으로 유지. |
| POST /authz | private mTLS + connection bearer. 실제 전체 JSON-RPC body를 파싱하고 준비된 단 하나의 call과 대조. |
| GET /history | human.token. 판정/실행 상태/enum 진단만 표시. raw 자료/키 없음. |
| POST /approval | human.token, {call, approve:bool}. CONFIRM만 정확한 hash/turn/정책에 묶음. DENY 해제 불가. |
| POST /sessions/forget | human.token, {session}. 실행 미확정 세션은 거부. 논리적 암호문 삭제이며 SSD/백업 물리 소거 증명이 아니다. |

envelope와 상태는 [SPEC5 schema](contracts/spec5.schema.json)를 따른다. SPEC/정책은 서버가 지정한다. machine 키를 모델 환경에 넣지 않으며 connection은 사람 승인/turn/source 쓰기 자격이 없다. 같은 OS 사용자의 임의 프로세스·관리자에 대한 키 보호/강제성은 보장하지 않는다.

## 판정 / 원자 실행

등록 도구·민감자료·보호 자원 → 선행 결과 누락/잘림 → 기존 제한 의미 관측 A/B와 엄격한 Unicode ref 검증 → 서버 ALLOW/DENY/예외 CONFIRM. DEVELOPMENT grant는 ISSUE_SUMMARY의 same_issue 조건을 적용하지 않는다. 원문/refs 검증·민감자료 차단·진단은 끄지 않는다. 외부 사실 사용은 허용 가능하고 외부의 추가 명령을 따른 행동은 DENY다. 분석 실패는 DENY/ANALYSIS_UNAVAILABLE + 세부 enum이며 공격 식별 PASS가 아니다.

hook에서 MCP 후보를 한 번 분석해 READY를 고정한다. gateway는 실제 이름/인자·connection/session/현재 turn·grant hash·출처 snapshot·30초 유효기간을 다시 검사하고 SQLite transaction에서 EXECUTING으로 단회 전이한다. 같은 MCP의 hook/gateway 이중 유료 분석은 없다. T-JEV-03의 새 공개 규칙 읽기만 아래 현행 통제 재검사를 지원하며, 의미 판정의30초 시효는 그대로다. 실제 전체 body hash+call+30초 만료 HMAC ticket을 gateway가 upstream에 전달한다. ticket은 최종 검증/예약 뒤 발급하므로 호스트 승인창에서 기다린 시간과 구별한다. client의 가짜 ticket은 신뢰하지 않는다. 등록 file upstream도 durable 단회 시도를 기록한 뒤 파일을 연다. 이것은 일반 upstream의 멱등성 보장을 뜻하지 않는다.

### T-JEV-03 승인 대기 / 신뢰된 거절 진단

내부 forward 재검사 버전 `public-read-1`은 새로 생성된 RULE_ALLOW/PUBLIC_ENROLLED_READ/model0 후보에만 기록한다. 동일 MCP read_file 후보를 실제 gateway가 보낼 때30초가 지났으면 BEGIN IMMEDIATE 안에서 현행 connection/session 만료·소유권·현재 turn·정책/실제 grant·원 action hash·사용자 대화 hash·출처 hash/전체 exact catalog·필수 문맥·등록 도구와 공개 경로 parser·민감 marker·analysis stop·미해결 선행 호출을 다시 확인한다. 모두 맞으면 같은 call을 한 번 EXECUTING으로 예약한다. 원 `analyzed_at`/snapshot/reason은 보존하며 `forward_check`에 새 checked_at/정책·grant/request/source/action hash와 model0 근거를 별도로 남긴다. 전체 TTL을 늘리거나 새 권한·승인을 발급하지 않는다. upstream의 실제 NOFOLLOW/regular/hardlink/민감 내용 검사도 유지한다.

기존 READY에 marker를 소급해 넣지 않는다. 의미 ALLOW·예외 승인·native·보호/민감/범위밖 자원·변경된 문맥·재전송·UNKNOWN은 이 경로로 갱신할 수 없다. 예외 승인 소비도 만료된 분석을 새 analyzed_at으로 덮어써 되살리지 않고 APPROVAL_SNAPSHOT_STALE로 미소비 거절한다. 실패는 유료 재분석이나 자동 재시도로 이어지지 않는다.

bridge는 각 gateway 요청에 무작위 `x-with-human-request`를 붙인다. 이 헤더는 진단 상관관계만 가지며 권한/승인 정보가 아니다. private mTLS /authz는 거절 시 connection hash+request ID+실제 tool/args hash에 고정 사유와 call SHA256만 결합해60초/최대128개 보관한다. machine 인증의 별도 TLS `POST /transport-rejection`은 정확히 같은 `{connection,request_id,tool,args}`만 조회한다. gateway/upstream의 오류 본문·문자열·헤더를 판정 근거로 사용하지 않는다. REJECT 감사에는 확인된 실제 call을 연결한다.

trusted Control 응답을 엄격한 allowlist로 검증한 경우에만 `CONTROL_FRESHNESS_REJECTED`/`CONTROL_AUTHENTICATION_REJECTED`/`CONTROL_POLICY_OR_STATE_REJECTED`와 reason/call_ref를 표시한다. 신뢰된 근거가 없는401/403은 `HTTP_REJECTION_UNCLASSIFIED`이며 인증 또는 정책으로 단정하지 않는다. TLS 검증 실패·transport 장애는 별도 코드다. 진단 조회는 실행 재시도가 아니며 기존 transport-failure 수집은 EXECUTING만 UNKNOWN으로 만들고 READY 거절을 성공으로 바꾸지 않는다.

정상 bridge 응답의 인증된 관측이 있어야 MCP Post가 OBSERVED가 된다. transport/JSON 오류, 응답 유실, Post 누락, 재시작 시 실행 예약은 UNKNOWN/미해결이며 자동 위험 재시도·환불하지 않는다. 파일 쓰기와 DB 완료 기록은 하나의 transaction이 아니다. 실제 효과 후 fsync/응답 실패 시험은 이 불확실성을 확인한다. native Post 역시 사후 관측이며 receipt가 아니다. 승인 소비와 최종 forward도 경쟁·현재 turn·출처를 재검증한다. 설정 변경은 미실행 후보/승인을 무효화한다.

## 저장 / 제한

### T-HG-04 내부 근거 계약 / 분석 실패 중단 (2026-10-16 B 보완)

외부 권한/승인/실행 상태와 정책v1은 유지한다. SPEC5 내부 judge만 `hookgw-exact-spans-1`, prompt `hookgw-span-ab-1`, [응답 schema](contracts/hookgw_judge.schema.json)로 개정했다. SPEC4의 f3-ab-2/f3-judge-1과 기존 offset 응답 계약은 그대로다.

서버가 A의 user_request/candidate, B의 동일 문맥+실제 성공 출처를 Unicode code point의 연속512자 이하 exact chunk로 나눈다. 각 view catalog는 모든 원문을 빠짐없이 덮어야 하며 quote 합계 UTF8 32768byte·128span, 최종 입력128KB 한도다. 잘림/민감정보/출처 hash 불일치/ID 충돌/한도 초과는 미완료 실패이며 앞부분만으로 허용하지 않는다. 모델은 서버 span ID만 선택한다. ID는 전체 immutable snapshot(analysis ID 포함)/view/실제 source ID/text hash/범위/quote hash에 결합된다. 서버가 동일 snapshot/view에서 원 ref를 복원하고 기존 exact slice·실제 출처·필수근거·마스킹을 다시 검증한다. 모호한 인용을 substring/fuzzy로 고치거나 임의 offset을 보정하지 않는다. unknown/위조/cross-view/cross-snapshot/stale ID와 직접 offset 응답은 거절한다. ID 선택 성공은 의미 판단 정확도나 인과 증명이 아니다.

adapter에는 신뢰 snapshot의 복사본만 전달한다. A/B 관측을 각각 검증해 `view_checks`와 allowlist 진단을 남기며, 하나라도 실패하면 DENY/ANALYSIS_UNAVAILABLE다. 진단은 code/view/ref 종류·index/범위·길이·hash·일치 boolean만 허용한다. raw 사용자 요청·인용·응답·비밀·Authorization을 이력에 기록하지 않는다. SPEC4 외부 진단은 기존 code/view 두 필드만 유지한다.

첫 분석 장애를 해당 session/turn의 hash에 묶은 `analysis_stops`에 단회 기록한다. 같은 turn의 다른 call ID/인자/route/연결 재시도는 `TURN_ANALYSIS_STOPPED`로 거절하고 유료 adapter를 호출하지 않는다. 중복 UserPromptSubmit·서비스 재시작·논리 삭제로 해제하지 않는다. 기존 DENIED/ANALYSIS_UNAVAILABLE 이력도 원행을 수정하지 않고 additive migration으로 중단 상태를 만든다. 새 실제 UserPromptSubmit turn에서만 새 판단이 가능하다. 기존 UNKNOWN/미관측 실행은 새 turn에서도 별도 session gap 통제로 계속 차단한다. 모델 변경·자동 유료 재시도·예산 환불/초기화·승인 우회는 없다. hash tombstone은 기존 UNKNOWN replay 방지와 같이 보존한다.

### 무모델 MCP 준비 진단

preflight는 기존 CLI/API/TLS/judge 키·원장 검사 외에 **실제 설치 stdio bridge**로 initialize → notifications/initialized → tools/list를 순차 왕복한다. 임시 session 미결합 connection만 생성하고 finally의 /disconnect로 제거한다. 따라서 이 준비는 완전한 DB read-only가 아니며, 사용자 turn/후보/출처/tools/call/judge 분석·예산 claim은0이다. 정리 실패도 readiness 실패다. 단계·분류·server=with_human의 allowlist 진단만 출력한다. 개인 MCP를 삭제하거나 TLS·hook 신뢰를 우회하지 않는다. 이번 with_human의 현재 결과와 당시 startup issue1의 실패 서버 미확정, 다른 개인 MCP 미점검을 구별한다.

현재 judge는 사용자 실제 실패 후 **18/24·남은6**이다. 이전 A의12/24는 당시 증거다. 사용자 직접 재시험은 새 CLI/새 실제 turn에서 합성 notes 정상1건만, 표식 `WP-HOOK-GW-02-repair-user-20261016-01`을 사용한다. 첫 ANALYSIS_UNAVAILABLE/UNKNOWN/turn 누락/예상 밖 native 동작이면 중단한다. 정상 성공 전 공격 시험을 이어서 하지 않는다. 준비·오프라인 catalog/집행 시험을 실제 모델 성공으로 계산하지 않는다.

새 DB/역할별 PKI를 기존 A/B/F3와 분리한다. prompt/candidate/source/transport 결과는 기존 Fernet 저장 보호를 재사용한다. session/connection24시간, 암호문7일 보존 후 논리 삭제. UNKNOWN call ID/hash tombstone과 upstream 시도 원장은 재전송 방지를 위해 남긴다. 감사는 최대4096행, 인증 실패10회/60초 제한(현재 전역 제한으로 로컬 가용성 한계 있음), 연결128/세션64/세션 call1024. 도구 결과65KB 이하, 자료당 기존8192문자/16KB 분석, 출처16개 및 총 입력128KB·사용자 대화16KB 한도를 넘으면 fail closed다. 누락한 문맥을 삭제해 ALLOW하지 않는다. 장기 무제한 개발 세션 지원은 아니다.

native Bash는 절대 LiteralPath의 단순 Get-Content/Get-ChildItem/Set-Content 및 Get-Location만 지원한다. 복합/상호작용 shell, 다른 인자·workdir는 미지원이다. apply_patch는 모든 파일 헤더를 검사한다. 보호 경로, symlink 외부 해석, hardlink/nonregular/Windows 특수 파일을 거부한다. 검사 후 호스트 파일 변경 경쟁은 완전 OS 격리로 방지됐다고 주장하지 않는다. upstream은 Linux dirfd/O_NOFOLLOW/fstat를 사용한다.

## 실제 지원 한계 / LIVE

최종 설치는 새 Windows host 키의 개인 ACL을 유지하고, 컨테이너 역할 키와 동결 제품 코드를 **새 전용 Docker named volumes**로 복사·검증한다. 기존 키를 복사하는 절차가 아니다. runtime은 UID10001·비밀0600과 read-only mount, 제품은 `/product/src`에서 import하며 MCP 편집 workspace `/files`와 분리한다. 호스트 진입점은 Python `-I`와 정확한 인접 helper만 import해 workspace/PYTHONPATH의 import shadow를 막는다. native 쓰기 Post에 입증된 typed completion이 없으면 UNKNOWN을 유지하므로 정상 native 편집 후 계속 작업하는 흐름도 아직 수용하지 않는다.

Windows Codex0.154.0에서 실제 user/pre/post·후속 turn·explicit deny와 MCP 정상 파일 효과를 확인했다. 그러나 native hook 프로세스 crash/timeout/malformed 출력은 실제 fail-open이다. 격리 CLI의 정상 native 쓰기는 자체 read-only 정책 때문에 BLOCKED다. write_stdin 추가 입력, hosted WebSearch, 임의 shell과 모든 MCP를 보호하지 않는다. 사용자 interactive TUI/정의 신뢰 UX 및 실제 의미 모델 정확도는 사용자 직접 LIVE로 남긴다.

기본 제품 judge는 UNAVAILABLE라 유료 호출하지 않는다. offline override는 명시된 테스트 관측 fixture이며 제품 기본 설치가 아니다. 사용자 LIVE override만 기존 원장(현재18/24)과 기존 API key 파일을 원위치 mount해 사용한다. 새 예산/키 복사/초기화는 없다. 후보당 A/B2요청, 현재 남은6요청은 최대3후보다. 공급망 보안 권고/미확정은 기존 SUPPLY_CHAIN.md에 남긴다. WP-HOOK-GW-01에서는 개발 AI가 LIVE override를 실행하지 않았고 WP-HOOK-GW-02 A/B 보완은 무모델 준비/배치 검증만 수행했다. judge 기존 키는 원위치 read-only로 `/runtime/judge.api-key`에 연결한다. NEW control volume에 빈 mountpoint만 별도 명시 준비하며 기존 키 복사/변경은 없다. `RUNTIME_DIR`와 `HOOKGW_RUNTIME` 모두 `/runtime`, 기존 literal 마스킹과 비root 권한을 유지한다. preflight 자체는 mountpoint 준비를 수행하지 않는다. 개발 AI의 유료 actor/judge 호출은0이며 실제 모델 의미 검증은 사용자 직접 실행으로 남긴다. A 시점 README/RESULT의12/24·MCP 시작 미검사 설명과 현재 B 보완을 구별한다. 현재 최소 절차·준비의 임시 연결·중단 조건은 [B 보완 RESULT](../handoffs/WP-HOOK-GW-02/20261016-span-repair/RESULT.md)를 따른다.
