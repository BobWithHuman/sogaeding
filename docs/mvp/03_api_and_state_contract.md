> **WP-HOOK-GW-01 / SPEC5 연결 개정 (2026-10-16)**: 평소 Codex hooks·실제 agentgateway 경로의 계약은 [SPEC5](08_transparent_hook_gateway_spec5.md)와 [별도 schema](contracts/spec5.schema.json)다. 아래 SPEC4 고정3도구 내용은 기존 실험·회귀 경로에 유지한다. 새 경로 수용/미지원/사용자 LIVE 상태는 WP-HOOK-GW-01 RESULT/REVIEW를 따른다.

## 작업팩11: 인증된 사용자 진단·직접 CLI 연결

SPEC-4의 사용자 역할·등록 MCP 입력·실행 상태는 유지한다. `GET /v1/sessions/{session_id}/diagnostics`는 encrypted analysis result의 제한된 code/view만 반환하며 raw 모델 응답·프롬프트·오류 메시지는 반환하지 않는다. 과거 미기록 상세는 DETAIL_NOT_RECORDED다. `GET /v1/judge-usage`는 누적 시도/남은24회 예산/기록된 토큰 총계를 조회하고 초기화하지 않는다. 두 경로와 `POST /v1/sessions/{session_id}/cli-binding`은 기존 HUMAN 인증·HTTPS·no-store/Origin/Host 검사를 적용하며 agent/service에는 열리지 않는다. cli-binding은 사용자에게 발급된 agent token이 같은 활성 세션인지 확인하고 작업 모드/요청 digest의 안전한 메타데이터만 반환한다. 세션/grant/승인/도구를 발급하거나 실행하지 않는다.

schema/ref/인용/같은 이슈/A-B 제약의 실패는 DENY/ANALYSIS_UNAVAILABLE을 유지한다. 의미 인용 좌표 입력은 PROMPT_VERSION f3-ab-2로 개정했으며 이전 분석 캐시는 기존 version binding에 의해 stale 거부된다. ANALYSIS_UNAVAILABLE은 공격 식별 성공 이유가 아니다. [직접 CLI 절차](08_manual_cli.md)를 기본 수동 흐름으로 사용한다.




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

# API·MCP·상태 계약

MVP-SPEC-3. 이 문서와 `contracts/openapi.json`, `contracts/tools.schema.json`은 구현의 입력·출력 계약이다. API 서버 구현에서 자동 생성된 계약과 대조한다. 경로·필드·enum을 바꾸면 두 계약과 시험도 함께 수정한다.

## 1. 인증과 표면

호스트의 Control URL은 https://127.0.0.1:8000, MCP URL은 https://127.0.0.1:8001/mcp다. Compose의 호스트 포트는 localhost에만 공개하고 컨테이너 안의 서버는 각 서비스 포트의 0.0.0.0에 바인딩한다. Gateway의 내부 Control 주소는 https://control:8443이다. GET /healthz와 대시보드의 빈 HTML shell만 공개한다. 모든 업무 데이터 API는 인증이 필요하다.

| 자격증명 | 허용 API | 거부 API |
|---|---|---|
| UserBearer | /v1/sessions 생성·종료·timeline, /v1/approvals 승인·거절 | /internal/* |
| GatewayServiceBearer | /internal/auth/resolve, sources, checks, reserve, report | /v1/sessions 생성·승인·사용자 조회 |
| AgentSessionBearer | MCP 연결·세 Tool 호출(자기 세션) | Control 업무 API, session/grant/source/approval 발급 |

잘못된 역할·누락/만료 token은401/403이다. 토큰은 querystring에 넣지 않는다. 요청 본문/헤더 로깅에서도 제거한다. MCP의 session header·JSON-RPC ID는 인증 수단이 아니다.

`UserBearer`의 '사용자'는 작업을 요청하고 추가 실행을 확인하는 같은 사람이다. 서비스 관리자의 별도 API를 뜻하지 않는다. 환경변수는 `HUMAN_USER_TOKEN`이며 Gateway·Codex에는 전달하지 않는다. MVP-SPEC-2는 문서·인증 역할명을 정리한 버전이고, 실행 정책의 의미는 바꾸지 않았으므로 `policy_version=mvp-2026-10-13-v1`을 유지한다.

SDK2.3.0의 verifier는 서버가 검증한 opaque bearer로 owner/session, expires_at, scope tools:invoke와 정확한 resource audience를 반환한다. handler는 검증된 access token 문맥에서 session을 얻는다. 클라이언트가 tool arguments에 session_id, source_label, trusted, approval_status를 넣으면 추가 필드 오류로 거부한다.

## 2. MCP Tool 입력

| Tool | 입력 | 실제 실행 범위 |
|---|---|---|
| get_issue | issue_id: seed된 양의 정수 | fixture 이슈 조회. 세션 대상 이슈만 |
| read_workspace_file | file_id: PUBLIC_README 또는 SECRET_ENV | 서버 내부 ID→fixture 매핑. SECRET_ENV는 항상 DENY |
| post_issue_comment | issue_id, body:1~4096문자, resume_call_id?:UUID | 로컬 effects DB 댓글. 임의 URL/파일/셸 인자 없음 |

`resume_call_id`는 승인 뒤 재개하기 위한 제어 참조다. 실제 action hash에서는 제외하되 그 UUID가 **자기 세션의 불변 call**이고 tool/backend/args/policy가 일치하는지 PDP에서 검사한다. 다른 본문으로 재개하면409 ACTION_BINDING_MISMATCH다. 이 값은 승인 자체가 아니다.

정상 결과와 실패 결과는 공통 구조로 표시한다.

```json
{
  "version": "MVP-SPEC-3",
  "call_id": "server-issued-uuid",
  "decision": "DENY",
  "execution_state": "NOT_STARTED",
  "reason_codes": ["OUTSIDE_TASK_SCOPE"],
  "source_ids": ["source-uuid"],
  "approval_id": null,
  "result": null
}
```

실제 UUID는 유효한 UUID 문자열이어야 한다. 예시의 문자열은 설명용이다. DENY, 미승인 CONFIRM, 시스템 오류는 MCP Tool 오류/중단 결과로 반환하고 executor를 호출하지 않는다. ALLOW라도 실제 실행 성공 여부는 execution_state로 따로 표시한다. sdk result/structured_content의 구현 방법은 설치 버전과 smoke 시험으로 확인한다.

## 3. REST 작업 계약

### 사용자 경로

| Method/path | 입력/출력 | 규칙 |
|---|---|---|
| POST /v1/sessions | task_kind,user_request,issue_id,allowed_comment_body? → SessionCreated | SUMMARIZE에는 본문 없음; POST_COMMENT에는 정확한 본문 필수. grants·owner·budget·token은 서버가 구성 |
| POST /v1/sessions/{session_id}/close | 빈 객체 → status CLOSED | 이후 새 검사/reserve와 token 사용 거부 |
| GET /v1/sessions/{session_id}/timeline | SessionTimeline | 토큰 제외; 출처·call·decision·approval·execution·safe event |
| POST /v1/approvals/{approval_id}/approve | expected_args_sha256 → ApprovalView | 화면에서 본 digest와 저장 call이 같고 pending·미만료·CONFIRM만 승인 |
| POST /v1/approvals/{approval_id}/reject | 빈 객체 → ApprovalView | 이후 해당 call 실행 금지 |

allowed_comment_body는 사용자의 정확한 요청이다. grants JSON을 에이전트가 직접 전달하는 API는 없다. 승인 응답은 실행을 시작하지 않는다. 승인 후 동일 도구·인자와 resume_call_id로 MCP를 다시 호출해야 한다.

LIVE의 신뢰된 런처는 사용자가 입력한 원문을 `POST /v1/sessions`의 `user_request`와 Codex CLI 최초 사용자 프롬프트에 동일하게 전달한다. Tool 결과·외부 이슈·모델 요약으로 USER_REQUEST를 다시 발급하지 않는다. 세션 생성은 사용자 자격증명이 있는 런처가 처리하고, Codex에는 발급된 자기 세션의 AgentSessionBearer만 환경변수 기반 MCP 헤더로 제공한다. 사용자가 Codex의 후속 대화에서 과업을 바꾼다면 새 세션을 생성한다.

### 게이트웨이 내부 경로

| Method/path | 입력/출력 | 규칙 |
|---|---|---|
| POST /internal/auth/resolve | agent_token → AuthContext | raw token은 검증용으로만 사용, 저장/로그 금지 |
| POST /internal/checks | session_id,client_request_id,tool_name,backend_id,args,resume_call_id? → CheckReply | session은 검증된 문맥, backend=demo.v1. 신규 call server UUID. 업무상 DENY/CONFIRM도200 |
| POST /internal/sources | call_id,kind,origin_ref,content_sha256,masked_excerpt,match_values → SourceView | read call과 세션을 확인. USER_REQUEST는 거부. 같은 call/snapshot 중복은 기존 record 반환 |
| POST /internal/calls/{call_id}/reserve | tool_name,backend_id,args → ReservationReply | 정확한 action 재검증 + 원자적 상태/승인/예산 소비. 성공 시 execute=true |
| POST /internal/calls/{call_id}/report | reservation_id,state,receipt?,error_code?,reconciled? → ExecutionView | state는 SUCCEEDED/FAILED/UNKNOWN. 실제 실행 이후만. 토큰/비밀 제외 |

인증·인가 실패는401/403, 미존재404, 불변 호출/승인/실행 충돌409, 스키마 오류422, 본문 크기 초과413, 서비스 장애503다. Error의 public message에는 stack·키·원문·DB 경로를 넣지 않는다. 모든 내부 API는 service 인증과 객체/상태 검사를 함께 한다.

## 4. canonical action과 멱등성

스키마 검증 후 기본값을 적용하고 다음 객체를 canonical JSON으로 만든다.

```json
{"tool_name":"post_issue_comment","backend_id":"demo.v1","args":{"issue_id":42,"body":"검토 완료"}}
```

정렬된 object key, 공백 없는 separators, UTF-8, ensure_ascii=False, NaN/Infinity 거부. body의 대소문자·공백·줄바꿈·Unicode를 임의로 바꾸지 않는다. 중복 JSON key·추가 필드는 거부한다. SHA-256은 위 canonical UTF-8 바이트에 적용한다. 입력 schema가 바뀌면 policy/contract 버전을 올린다.

승인은 owner/session/call/tool/backend/args_sha256/policy_version/expiry에 결합한다. 승인 ID만 같다고 다른 action을 실행할 수 없다.

- client_request_id는 gateway가 요청마다 발급하는 UUID다. 내부 PDP HTTP 재시도는 UUID를 유지한다.
- 같은(session_id,client_request_id)·같은 action은 기존 call/decision 반환. 다른 action이면409. 신규 요청으로 계산하거나 예산을 다시 쓰지 않는다.
- 신규 호출은 call budget을 한 번 소비한다. resume는 기존 call을 재검사하며 새로운 budget을 소비하지 않는다.
- 신규 call insert와 call budget 감소도 같은 트랜잭션/CAS로 처리한다. 병렬 checks가8회를 넘길 수 없고 멱등 key 재시도에는 감소가 없다. insert/필수 기록 실패 시 트랜잭션을 rollback하고 실행하지 않는다.
- 성공한 call의 재개/reserve는 **execute=false + 기존 receipt**를 반환한다. 실행기를 다시 부르지 않는다.
- RESERVED 중복은409 EXECUTION_IN_PROGRESS다. FAILED/UNKNOWN을 재개하여 자동 실행하지 않는다.
- 새로운 call_id의 반복 쓰기도 세션 write_budget=1과 reserve 트랜잭션으로 막는다.

## 5. 판정표

| 조건 | 판정 | 승인으로 변경 가능? |
|---|---|---|
| 유효 세션·허용 이슈 get_issue, PUBLIC_README 읽기 | ALLOW | 불필요 |
| SECRET_ENV 또는 범위 밖 이슈·미등록 Tool·민감 인자 | DENY | 불가 |
| SUMMARIZE_ISSUE의 댓글 | DENY / OUTSIDE_TASK_SCOPE | 불가; 새 사용자 작업은 새 세션 |
| POST_COMMENT의 같은 이슈·정확한 사용자 본문 | ALLOW / EXACT_USER_CONTENT | 불필요 |
| POST_COMMENT의 같은 이슈·다른 비민감 본문 | CONFIRM / CONTENT_REVIEW_REQUIRED | 정확한 call만 가능 |
| 외부 값이 본문에 일치 | 관측 근거 추가 | 일치만으로 DENY/권한 상승 없음 |
| 세션/정책/예산/승인 상태 불일치 | DENY 또는 reserve409 | 불가 |
| PDP/필수 검사 기록 장애 | 실행 전 중단 | 장애를 사용자 승인으로 우회하지 않음 |

## 6. 판정·승인·실행 상태를 분리

Decision: ALLOW, DENY, CONFIRM. 최초 결정은 불변이다. 승인 사건은 별도 record로 append하고 원래 CONFIRM을 지우지 않는다.

Approval: PENDING → APPROVED → CONSUMED. PENDING/APPROVED가 만료되면 EXPIRED. PENDING은 REJECTED 가능. EXPIRED/REJECTED/CONSUMED는 실행권이 없다. APPROVED는 아직 실행된 상태가 아니다.

Execution: NOT_STARTED → RESERVED → SUCCEEDED 또는 FAILED 또는 UNKNOWN.

| 전이 | 반드시 한 트랜잭션에서 확인·처리 |
|---|---|
| NOT_STARTED→RESERVED | session ACTIVE·미만료, owner·tool·backend·args·정책 일치, ALLOW 또는 유효 CONFIRM 승인, 필요시 approval 소비, write budget 감소 |
| RESERVED→SUCCEEDED | 해당 reservation 결과와 로컬 효과 receipt 확인 |
| RESERVED→FAILED | 실행기가 효과가 없음을 확정한 실패. 자동 예산 환불 없음 |
| RESERVED→UNKNOWN | timeout/프로세스 중단/결과 보고 유실 등 효과를 확정할 수 없음 |
| UNKNOWN→SUCCEEDED/FAILED | effects DB 대조·기존 reservation 결과로 명시적 reconciliation; 실행 재시도 아님 |

write budget은0 아래로 내려가지 않는다. 같은 call_id뿐 아니라 서로 다른 병렬 호출을 transaction/CAS로 제어한다. ALLOW 결정만 받았다고 executor를 실행하지 않는다. reserve 응답 execute=true가 있어야 한다.

Control 시작 시와10초마다 RESERVED를 확인한다. 예약 후30초가 지난 미종료 호출은 UNKNOWN으로 보존하며 실행권·쓰기 예산을 자동 반환하지 않는다. Gateway 재시작/명시적 reconciliation은 effects DB와 기존 call_id를 대조해 결과만 보고한다. 원래 쓰기를 재실행하는 복구 경로는 없다. 예약 직후30초 안에 실행을 시작하지 못했다면 Gateway도 실행하지 않고 UNKNOWN을 보고한다.

report는 같은 reservation/state/receipt의 재보고에 기존 결과를 반환한다. 서로 다른 확정 terminal 결과는409다. UNKNOWN에서 receipt로 결과를 확인한 reconciliation만 예외이며 reconciled=true와 같은 reservation_id를 요구한다. 늦게 도착한 결과도 실제 효과를 대조한 뒤 이 경로로 확정한다.

source 저장/결과 보고의 실패 시점도 구별한다. 실행 전 검사·필수 기록 실패는 실행0. read 이후 source 저장 실패는 반환을 막고 기록 실패를 표시한다. write 이후 report 실패는 UNKNOWN이며 실제 댓글0으로 거짓 표시하지 않는다. 이미 실행된 효과를 자동 rollback했다고 주장하지 않는다.

## 7. 안정된 reason code

구현·시험·대시보드가 공유할 코드는 다음이다. UI의 한국어 문장은 코드와 별도로 관리한다.

VALID_TASK_CALL, EXACT_USER_CONTENT, OUTSIDE_TASK_SCOPE, RESOURCE_OUT_OF_SCOPE, SENSITIVE_RESOURCE, SENSITIVE_DATA_IN_ARGUMENTS, CONTENT_REVIEW_REQUIRED, SOURCE_VALUE_OBSERVED, AUTH_REQUIRED, SESSION_INACTIVE, UNSUPPORTED_TOOL, INVALID_ARGUMENTS, TASK_CALL_BUDGET_EXHAUSTED, TASK_WRITE_BUDGET_EXHAUSTED, PDP_UNAVAILABLE, AUDIT_UNAVAILABLE, REQUEST_KEY_CONFLICT, ACTION_BINDING_MISMATCH, POLICY_CHANGED, APPROVAL_PENDING, APPROVAL_EXPIRED, APPROVAL_REJECTED, APPROVAL_CONSUMED, EXECUTION_IN_PROGRESS, EXECUTION_ALREADY_SUCCEEDED, EXECUTION_FAILED, EXECUTION_OUTCOME_UNKNOWN.

로그의 source_ids는 존재하고 같은 session에 속한 ID만 허용한다. Tool 인자가 직접 제시한 source_ids를 권한/판정 근거로 사용하지 않는다. LLM이 공격 호출을 시도하지 않았다는 관측은 LIVE 평가 event이며 DENY reason이 아니다.

## 8. 아직 실행으로 확인할 항목

SDK 2.3.0의 Docker 개발 환경 설치는 확인했다. 남은 항목은 HTTP client transport bearer 전달, session scope/audience 검증, 실제 MCP list/call, SQLite concurrent reserve, executor receipt와 report 재전송이다. Codex CLI의 OpenAI API 인증·선택 모델·HTTP MCP bearer 설정·최초 요청 일치·정상 요약은 실제 LIVE smoke로 확인한다. CLI 0.154.0 설치 확인은 LIVE 연결 완료를 뜻하지 않는다. 이 항목들은 명세에 이름만 적었다고 완료되지 않는다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
