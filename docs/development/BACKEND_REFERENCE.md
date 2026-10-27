# With Human 백엔드 연동 기준서

기준: 2026-10-27, 현재 로컬 working tree. 대시보드 개발자가 이 문서로 엔진 역할, API, 인증, DB와 실행 경계를 파악하기 위한 문서다. 예시 JSON의 ID·통계는 설명용이며 실측 결과가 아니다. GitHub의 기존 공유 commit `0744fc0` 이후 ASK·조회 API·로컬 중계 변경이 포함되어 있다. 이 문서를 작성했다고 원격 push나 릴리즈가 완료된 것은 아니다.

## 1. 구현 상태와 제품 범위

- 각 사용자의 로컬 단말에서 독립 엔진·키·DB를 실행한다. 회사 서버의 다중 사용자 서비스나 로그인 시스템이 아니다.
- 공통 기본 정책: gate-6, policy ID `engine-2026-10-24-gate6-1`. 판정은 ALLOW / DENY / ASK다.
- 현재 제품 Codex 연결 범위는 Docker 작업영역 `/files`의 MCP `read_file`, `write_file`이다. 일반 Codex native 도구 전체를 보호하는 구조로 확대해 설명하면 안 된다.
- 대시보드용 조회 API 5개와 로컬 HTTP→HTTPS 중계를 구현했고 실제 이력·상세·보안 감사 화면까지 연결했다.
- 실제 Codex·실제 Jev·실제 사용자 응답에서 ASK→재판정 ALLOW→파일 쓰기 OBSERVED를 확인했다. 등록 파일 시나리오 한 경로의 확인이며 모든 도구·모든 공격 검증은 아니다.
- 이후 추가한 ASK 한글 이유 전달은 관련 무모델 시험으로 검증했다. 새 문구가 실제 Codex UI에서 어떻게 표현되는지는 새 세션에서 확인한다.
- `agent` 신원은 아직 수집하지 않아 `unknown`이다. Gateway/Upstream 실시간 생존 probe도 미구현이므로 `UNKNOWN`이다. 도구 실행 경로가 없다는 뜻은 아니다.
- 대시보드에서 ASK 답변, 실행 승인, DENY 해제, 재실행, 정책 변경은 하지 않는다. 실제 사용자 질문·답변은 에이전트의 신뢰 연결기가 담당한다.

## 2. 구성과 데이터 흐름

```text
사용자 → Codex CLI
          ├─ 사용자 턴 / 실행 전 Hook → Control 엔진
          │                            ├─ 코드·권한·출처 검증
          │                            ├─ 필요 시 Jev A/B 의미 분석
          │                            └─ ALLOW / DENY / ASK
          └─ with_human stdio MCP 연결기
               ├─ ASK: 엔진 이유를 설명하고 네이티브 사용자 질문
               │        실제 응답 → 엔진 재판정
               └─ 최종 ALLOW만 Gateway → private /authz → Upstream 파일 도구
                                             └─ 서명·단회 예약·실제 결과 기록

브라우저 대시보드 → localhost 중계(BFF) → Control /dashboard/v1/* → DB projection
```

Control은 판정·상태·권한을 관리한다. Gateway는 실제 MCP 요청을 중계하고 최종 집행 검사를 거친다. Upstream은 허용된 정확한 파일 도구를 실행한다. Jev의 응답 자체가 실행 권한은 아니다.

ALLOW는 실행 허용 후보이며 성공과 다르다. 실제 실행 결과가 관측되어 `OBSERVED`가 되면 `execution.outcome=SUCCEEDED`로 표시한다. 결과를 확정하지 못한 `UNKNOWN`을 성공이나 미실행으로 바꾸지 않는다.

## 3. 주소·인증·브라우저 연결

기본 포트는 실행 설정으로 바꿀 수 있다. 현재 `try-gate6`는 다음 주소를 사용한다.

| 용도 | 호스트 주소 / 내부 주소 | 인증·공개 범위 |
|---|---|---|
| 대시보드와 BFF | `http://127.0.0.1:8150` | 로컬 브라우저 쿠키, 동일 origin |
| Control 공개 API | `https://127.0.0.1:8130` / `https://control:8030` | 역할별 Bearer, 로컬 호스트 공개 |
| Gateway MCP | `https://127.0.0.1:8140/mcp` / gateway:8040 | bound 연결 자격, 로컬 호스트 공개 |
| Control 집행 검사 | `https://control:8050/authz` | private 망 + mTLS + 연결 대조. 호스트 포트 공개 안 함 |
| Upstream MCP | `https://upstream:8060/mcp` | private 망 + mTLS + 서명 대조. 호스트 포트 공개 안 함 |
| Jev | TypeSafe HTTPS API | 서버에서 외부 Jev 키 사용 |

`/authz`는 공개 Control listener에서403 `PRIVATE_ENDPOINT`다. 브라우저나 프런트엔드가 대신 호출하면 안 된다. 실제 배포 listener 구성은 `src/app/transparent/server.py`, `upstream.py`, `compose.yaml`이 기준이다.

역할:

- **machine**: `/connect`, `/event`, ASK 및 transport 관측을 제출하는 신뢰 연결기.
- **connection**: 특정 machine·세션에 결합된 일시 연결 자격. Gateway 실행 경로에서 사용한다.
- **operator(human)**: 이력·보안 조회 등 운영자 API. `history:read`, `security:read`, `security:ack`, `session:purge`, 과거 `approval:write` 권한으로 구분한다.
- 현재 기본 `human.token`은 로컬 관리자다. BFF는 이를 서버에서만 읽고 조회 경로만 중계한다. 추가 조회 전용 operator를 설정할 때는 `history:read`/`security:read`만 부여한다.

브라우저 연결 규칙:

1. UI와 BFF를 같은 origin으로 제공한다. 브라우저는 상대 경로 `/dashboard/v1/...`를 호출한다.
2. BFF의 `/` 방문으로 HttpOnly·SameSite=Strict 쿠키를 발급받는다. API 요청에는 같은 origin 쿠키를 사용한다. 재시작 시 쿠키가 바뀌므로 새로고침한다.
3. BFF가 서버에 보관한 `human.token`과 CA로 Control HTTPS를 호출한다. 브라우저에 엔진 토큰·키·CA private key를 보내지 않는다.
4. 임의 Origin/Host·교차 사이트 요청을 거부한다. 현재 임의 원격 사이트에서 로컬 API를 바로 호출하도록 CORS를 열지 않았다.
5. 팀원 공개 Sites 화면은 게시된 mock 버전이다. 실제 로컬 연동본의 원본은 `src/app/web/observatory/`다. 해당 UI를 교체할 때도 동일 origin 중계 경계를 유지한다.

브라우저가 DB나 raw `/history`를 직접 읽는 방식은 지원하지 않는다. 대시보드 연동에는 아래 5개 조회 API만 필요하다.

## 4. 대시보드 API

모든 응답은 JSON이다. 엔진 시각은 UTC ISO8601 `Z`, 화면은 `Asia/Seoul` 등 선택한 timezone으로 표시한다. 캐시하지 않으며 SSE/WebSocket 대신 현재 UI는5초 polling을 사용한다. 오류 시 이전 자료를 오래된 자료로 표시하고0건/ONLINE으로 대체하지 않는다.

| Method / 경로 | 권한 | 반환 내용 |
|---|---|---|
| GET `/dashboard/v1/status` | history:read | 정책·ASK 계약·관측 가능 서비스 상태·보존/자료 범위 |
| GET `/dashboard/v1/summary` | history:read | 필터 전체 후보 통계·실행 결과·ASK 상태·시간 추이·Jev 사용량 |
| GET `/dashboard/v1/events` | history:read | 후보 목록·전체 건수·다음 cursor |
| GET `/dashboard/v1/events/{event_id}` | history:read | 단일 후보의 원문 비공개 상세·ASK·검사·타임라인 |
| GET `/dashboard/v1/security` | security:read | 보안 감사·경고·다음 cursor |

### 4.1 공통 query

`summary`, `events`, `security`에서 `from`, `to`가 필수다. status와 event 상세에는 필요하지 않다.

| 파라미터 | 규칙 |
|---|---|
| from / to | timezone이 있는 ISO8601. from 포함, to 미포함. 기간은0초 초과·최대7일 |
| timezone | `Asia/Seoul`(기본) 또는 `UTC`. 반환 시각은 UTC이고 집계 버킷 경계에 사용 |
| bucket | `hour`(기본) 또는 `day` |
| limit | 기본50, 1~100. 목록 페이지만 제한하며 통계 분모를 줄이지 않음 |
| cursor | 서버가 발급한 opaque 문자열. 기존 필터·기간을 유지해 다음 목록 조회 |

후보 필터: `session_id`, `agent`, `tool`, `initial_decision`, `decision`, `execution_outcome`, `denial_origin`, `reason_code`, `routing`.

- 여러 조건은 AND이며 서버가 실제로 적용한다. `session_id`는 응답에 나온 hash ID를 사용한다.
- `agent=codex`로 필터하면 현재 자료는 나오지 않는다. 현재 신원 미수집 값은 `unknown`이다.
- `security`는 후보 필터 대신 `kind`, `alert_code`를 사용한다.
- 알 수 없는 query 이름, 중복 query, 잘못된 기간·limit·cursor는400이다.
- cursor는 필터·endpoint와 HMAC으로 결합하고 시간/ID 기준으로 다음 목록을 반환한다. 엔진 프로세스가 재시작되면 새 cursor로 시작한다.
- 후보 조회가20,000건을 넘으면503으로 기간 축소를 요구한다. 조용히 일부만 전체 통계처럼 반환하지 않는다.
- `security.alerts`는 최대512개, 감사 목록은 cursor 페이지다. 현재 UI는 최근50개를 먼저 보여준다.

호출 예시:

```javascript
// UI와 BFF가 같은 origin인 경우. 실제 시간 범위를 사용한다.
const to = new Date();
const from = new Date(to.getTime() - 24 * 60 * 60 * 1000);
const query = new URLSearchParams({
  from: from.toISOString(), to: to.toISOString(),
  timezone: 'Asia/Seoul', limit: '50'
});
const response = await fetch('/dashboard/v1/events?' + query, {
  credentials: 'same-origin', cache: 'no-store'
});
if (!response.ok) throw new Error('engine query failed: ' + response.status);
const page = await response.json();
// page.total / page.items / page.next_cursor
```

### 4.2 status

주요 필드: `contract_version=dashboard-v1`, `observed_at`, `data_mode`, `engine`, `services`, `capabilities`, `retention`, `data_window`.

```json
{
  "contract_version": "dashboard-v1",
  "data_mode": "ENGINE",
  "engine": {
    "state": "ONLINE",
    "policy": "engine-2026-10-24-gate6-1",
    "decision_contract": "ASK_V1"
  },
  "services": {
    "gateway": "UNKNOWN",
    "upstream": "UNKNOWN",
    "jev": "CONFIGURED_NOT_TESTED"
  }
}
```

위 JSON은 주요 필드의 발췌이며 실제 응답에는 관측 시각 등도 포함된다.

`ENGINE_FIXTURE`는 합성 검증 엔진이다. 실제 엔진이라고 표시하지 않는다. `CONFIGURED_NOT_TESTED`는 현재 상태 조회가 유료 provider 인증/생존 probe를 호출하지 않았다는 뜻이며 과거 이력의 Jev 성공 건수와 별개다. BFF를 경유하면 `relay` 상태가 추가된다.

### 4.3 summary

| 필드 | 의미 |
|---|---|
| scope | FILTERED_RETAINED_CALLS |
| range / generated_at | 실제 조회 기간과 생성 시각 |
| total_calls | 선택 기간/필터의 고유 후보 수. 현재 페이지 크기가 아님 |
| initial_decisions | ALLOW / DENY / ASK / UNKNOWN 최초 분포 |
| effective_decisions | 현재 최종 판정 분포 |
| execution_outcomes | SUCCEEDED / REPORTED_ERROR / NOT_EXECUTED / IN_PROGRESS / UNKNOWN |
| asks | total_requests와 ISSUED / PRESENTED / ANSWER_RECEIVED / RECHECKED / DECLINED / EXPIRED / CANCELLED 수 |
| denials | STRUCTURAL_RULE / JEV_SEMANTIC / USER_DECLINED / ANALYSIS_FAILURE / OTHER / UNATTRIBUTED |
| series | bucket_start / total_calls / initial_ALLOW 등 버킷별 수 |
| reasons | code / count 목록 |
| jev | 해당 후보 기간이 아닌 전체 runtime의 장부 집계 |

ASK→ALLOW인 후보는 최초 ASK1건·최종 ALLOW1건이다. ALLOW와 ASK 양쪽에 최종 결과로 중복 합산하지 않는다. ASK 상태는 질문 단위이고, 후보 분모와 구분한다. 후보의 `created_at`으로 기간을 선택하고 현재 결과를 표시한다. 차단 호출 수로 공격 방어율이나 시나리오 방어 건수를 계산하지 않는다.

현재 Jev는 명시적 `unlimited=true`, 요청/예약 토큰 한도는 null이다. 새 시도에는 토큰 예약을 하지 않으며 실제 사용량은 기록한다. 과거 예약량은 이력으로 남는다. `jev.unlimited=true`일 때 한도 null은 “제한 없음”, `status=UNAVAILABLE` 또는 실제 usage null은 “미수집”으로 표시한다. 미수집을0으로 바꾸지 않는다.

### 4.4 events와 상세

목록 envelope: `scope`, `generated_at`, `total`, `items`, `next_cursor`.

항목 주요 필드: `event_id`, `call_id`, `session_id`, `turn_id`, `created_at`, `updated_at`, `agent`, `tool`, `target_display`, `initial_decision`, `decision`, `engine_state`, `execution`, `routing`, `denial_origin`, `reasons`, `policy`, `ask`, `redacted`, `context_status`.

ID는 hash 기반 opaque 값이다. 현재 `event_id`는64자리 소문자 hex이고 상세 URL에 넣어 조회한다. 응답 ID를 원래 DB ID로 역추정하거나 실행 권한으로 사용하지 않는다.

상세에는 추가로 `user_request_summary`, `candidate_summary`, `sources`, `checks`, `ask_history`, `timeline`이 있다. 원문 요청/쓰기 본문은 비공개다. source의 integrity/completeness는 이 조회 경로에서 검증하지 않아 UNKNOWN이다. agent unknown과 마찬가지로 화면에서 임의로 VERIFIED로 바꾸지 않는다.

`ask_history.reason_details`는 보류 당시 사유 코드에 대한 안전한 설명 목록이다. 사용자 답변 원문·nonce는 포함하지 않는다. 실제 질문에는 정확한 실행 후보가 들어가므로 그 원문은 연결기 전용이며 대시보드의 `question_redacted`와 구분한다.

### 4.5 security와 오류

보안 envelope: `scope=FILTERED_RETAINED_SECURITY_EVENTS`, `generated_at`, `total`, `items`, `alerts`, `next_cursor`.

감사 항목: `id`, `event_id`, `created_at`, `at`, `kind`, `actor_hash`, `resource_hash`, `result`. 경고: `id`, `at`, `code`, `severity`, `event_id`, `acknowledged`. hash로 사용자 실명을 추측하지 않는다. 현재 BFF에는 경고 확인 쓰기 경로가 없다.

대시보드 오류 예시:

```json
{"error":{"code":"INVALID_FILTER","message":"INVALID_FILTER","retryable":false}}
```

주요 HTTP: 400 필터/기간/cursor 오류, 401 BFF 쿠키 없음, 403 권한/로컬 접근 경계 거부, 404 자료 없음/만료, 429 제한, 503 엔진·TLS·자료 검증/조회 한도 장애. 엔진의 일반 인증 오류는 `{"code":"..."}` 형태일 수도 있으며 BFF가 대시보드 오류 형식으로 중계한다. 대시보드 상세의 없는 기록은404다. `/docs`, `/openapi.json` 자동 공개 기능은 비활성이다.

## 5. 연결기·ASK API

대시보드 개발자는 이 API를 호출하지 않는다. 별도 에이전트 연결기를 구현할 때만 참고한다. machine Bearer와 세션 결합이 필요하다.

| 경로 | 역할 |
|---|---|
| POST /connect | 임시 연결 발급 |
| POST /event | UserPromptSubmit / PreToolUse / PostToolUse 이벤트. schema는 docs/mvp/contracts/spec5.schema.json |
| POST /ask/pending | 정확한 세션·도구·인자에 보류된 ASK를 단회 claim. 연결기 전용 nonce 반환 |
| POST /ask/presented | 질문을 신뢰 client에 전달했음을 기록. 실제 사람이 읽었다는 증거는 아님 |
| POST /ask/answer | YES / NO / CANCEL. 실제 client 응답만 전달하며 YES도 엔진에서 새로 재판정 |
| POST /transport-observed | Gateway 도구 결과 관측 |
| POST /transport-failure | 전달 이후 결과가 불명확한 상태 기록 |
| POST /transport-rejection | 신뢰 Control 경로에서 거절 원인 조회 |
| POST /connections/close | 세션 종료·잔여 실행 권한 무효화·이력 보존 |
| POST /disconnect | 연결 자격 종료. 세션 종료 용도는 connections/close 사용 |

`PreToolUse`가 ASK면 `ask`에 다음 필드가 포함된다. 예시는 일부 필드만 표시했다.

```json
{
  "decision": "ASK",
  "state": "ASK",
  "ask": {
    "ask_id": "opaque-ask-id",
    "state": "ISSUED",
    "reasons": ["SENSITIVE_RESOURCE_REQUIRES_CONSENT"],
    "reason_details": [{
      "code": "SENSITIVE_RESOURCE_REQUIRES_CONSENT",
      "message": "이 대상은 서버 정책에 사용자 확인이 필요한 리소스로 등록되어 있습니다. 자동으로 실행하지 않고 이번 작업의 동의를 확인합니다."
    }]
  }
}
```

`reason_details`는 서버의 고정 정책 설명이다. 외부 문서나 모델의 주장을 보류 이유인 것처럼 복사하지 않는다. 알 수 없는 사유는 고정된 일반 설명을 반환한다. “민감 정보가 실제로 검출됐다”는 단정과 “이 리소스에 확인 규칙이 설정됐다”는 설명을 구분한다. 현재 ask-demo.md는 합성 시연용으로 후자에 해당한다.

신뢰 연결기는 이 설명을 사용자에게 함께 말하도록 안내하고 네이티브 `elicitation/create` 메시지에도 넣는다. 지원 프로토콜과 `capabilities.elicitation.form`이 없으면 실행을 보류한다. 임의 일반 채팅·도구 인자·모델의 “승인받았다”는 문장은 실행 권한이 아니다.

ASK는120초 만료, 세션·턴·연결·도구·정확한 인자·정책·권한·출처 snapshot에 결합된다. nonce는 이벤트·모델용 도구 응답·대시보드에 노출하지 않는다. 단회 응답 후 재판정하며 DENY를 동의로 해제하지 않는다. 분석 장애는 DENY/UNKNOWN 등 실제 상태로 남기고 임의 ALLOW나 자동 재시도를 하지 않는다.

과거 `/approval`은 인증 후409 `LEGACY_CONFIRM_READ_ONLY`다. 과거 CONFIRM 기록을 ASK로 문자열 치환하거나 현재 승인 UI를 만들지 않는다.

## 6. DB와 파일 저장

SQLite를 사용하며 별도 DB 서버는 없다. API 서버가 스키마를 초기화한다. 실제 runtime DB에 수동 UPDATE를 하거나 대시보드가 직접 연결하지 않는다.

현재 Docker volume은 저장소 경로에서 계산한 root ID와 runtime 이름으로 분리된다. 이 PC는 `sogaeding-team-c7506d01-try-gate6-runtime`, volume 내부 기준 root는 `artifacts/team-dev/try-gate6`다. 다른 PC의 ID는 달라질 수 있다.

| runtime root 상대 경로 | 컨테이너 경로 | 내용 |
|---|---|---|
| control-data/control.sqlite3 | Control /data/control.sqlite3 | 세션·후보·출처·ASK·감사·보존 |
| control-data/control.sqlite3.auth | Control /data/control.sqlite3.auth | 세션과 별개로 유지하는 인증 실패 집계 |
| upstream-data/attempts.sqlite3 | Upstream /data/attempts.sqlite3 | 정확한 실행 시도와 효과 관측 상태 |
| jev-budget/typesafe-budget.sqlite3 | Control /jev-budget/typesafe-budget.sqlite3 | Jev 설정 binding·시도·사용량·진단 |
| workspace/ | Upstream /files | 실제 등록 파일. 현재 docs/release.md, reports 등 |
| control/, host/, gateway/, upstream/ | 역할별 readonly mount | 역할 자격·TLS·grant·저장/서명 키. Git 공유 대상 아님 |

Control 주요 테이블:

| 테이블 | 역할·핵심 열 |
|---|---|
| sessions / turns | machine·현재 turn·암호화 사용자 턴. sessions.id / turns(session,id) |
| calls | id·session·turn·도구 인자 hash·route·state·decision·reason·body·created |
| sources | 세션의 관측 자료와 source call 결합. call UNIQUE |
| transport | call별 암호화 관측 결과 |
| asks | id·call UNIQUE·state·expires·consumed. 상세 binding/질문/응답은 암호화 calls.reason.ask_record |
| connections / expiry / closed_sessions | 연결 hash·소유 세션·기한·종료 상태 |
| audit | at·kind·code·call 중심의 단계별 메타데이터 |
| security_events / security_alerts | 암호화 보안 감사와 원문 없는 경고 |
| retention_deadlines / deletion_evidence | 세션별 보존 기한·원문 없는 삭제 증거 |
| analysis_stops / gateway_rejections | 분석 장애 턴의 중단 근거·짧은 수명의 전달 거절 근거 |
| approvals / demo_* | 과거 승인·평가 연결 호환용. 현재 대시보드 승인 기능 아님 |
| configuration / tombstones / key_rotation | grant 결합·재실행 방지·키 회전 bookkeeping |

SQLite 파일 전체를 암호화하는 방식은 아니다. 주요 body·판정 context를 Fernet으로 암호화하고 메타데이터 열은 남긴다. 원문 요청·출처·정확한 인자는 암호화 context에 저장하며 공개 projection은 이를 그대로 반환하지 않는다. DB·키 파일은 OS 권한으로 보호한다. workspace의 실제 사용자 파일 전체를 엔진이 자동 암호화하는 기능은 아니다.

Jev 장부 테이블은 `jev_policy(singleton,binding)`, `jev_attempts(analysis_id,view,started,status,input_reserved,usage)`, `jev_diagnostics(analysis_id,view,details)`다. A/B는 별도 요청이다. 모델 변경·설정 모드 변경은 binding에 영향을 준다. 기존 장부를 지우거나 파일 이름만 바꿔 사용량을 초기화하지 않는다. 이번 무제한 전환은 사용자 지시 후 서버를 정지한 오프라인 절차로 기존 행을 보존하며 수행했다.

인증 DB의 `auth_failures`는 시간 bucket·인증 surface·status·count·first/last 시각만 기록하며 bearer·IP·원문 헤더를 저장하지 않는다. Upstream `attempts`는 call·hash·state·at으로 실행 중복을 방지한다. 파일 쓰기와 SQLite 기록은 하나의 원자 트랜잭션이 아니므로 응답 유실 시 UNKNOWN을 유지한다.

보존 기본값: 세션24시간, 원문/이력 최대7일, 삭제 증거30일, 보안 감사7일. 인증 실패 집계는1일 범위로 정리한다. 기간은 상한 내에서 짧게 설정할 수 있다. Jev/Upstream 장부는 이 세션 원문 TTL과 별개이며 재실행/사용량 근거로 유지한다. 엔진의 유지보수·회전·백업/복원은 `src/app/transparent/maintenance.py`를 사용하며 실행 중 DB 복사·수동 키 교체로 대체하지 않는다.

## 7. 현재 PC 실행·팀원 인계

현재 PC는 이미 runtime·인증서·이미지가 준비돼 있다. PowerShell:

```powershell
cd C:\sogaeding
.\scripts\product_codex.ps1 -Mode check -RuntimeName try-gate6
.\scripts\dashboard_local.ps1 -RuntimeName try-gate6
.\scripts\product_codex.ps1 -Mode start -RuntimeName try-gate6
```

대시보드는 `http://127.0.0.1:8150`. 프롬프트는 사용자가 직접 입력한다. start 전후에 자동 모델 시험을 돌리지 않는다. 코드 변경 뒤 엔진 Python 프로세스를 재시작하고 Codex 연결기도 새로 열어야 최신 코드가 적용된다. 종료는 Codex exit, 대시보드만 중지는 dashboard_local.ps1 -Mode stop, 엔진 전체 종료는 product_codex.ps1 -Mode down이다. 장부 volume은 보존한다.

다른 PC에는 이 PC의 키·토큰·DB·volume을 보내지 않는다. 해당 PC에서 키 경로를 제공하고 새 runtime을 prepare한다. Windows DACL, 로컬 CA, 역할별 TLS가 필요하다. 현재 스크립트는 저장소의 단일 Dockerfile로 `with-human-engine:local`을 빌드한다. prepare가 빌드를 호출하므로 다른 개발자 PC의 이미지를 복사하지 않는다. requirements.txt는 실행 의존성의 버전/hash를 고정하고, tools/minimal_runtime.py가 실제 native library와 패키지 목록을 포함한 최소 이미지를 만든다. 제품 Compose는 compose.yaml 하나다. 선택적 시험은 같은 Dockerfile의 dev target을 사용한다. 새 clone·새 volume·새 자격으로 준비/기동/연결기/대시보드 재현을 확인했다. 같은 Windows PC의 격리 환경 검증이며 실제 다른 물리 PC/다른 OS 검증은 아니다.

## 8. Git 공유 범위와 확인 근거

API 공유의 핵심은 다음 소스와 이 문서다. 파일 내용 확인 없이 git add .로 작업 트리 전체를 올리지 않는다.

- 엔진/ASK/조회: `src/app/transparent/engine.py`, `server.py`, `dashboard.py`, `jev_gate6.py`, `jev.py`, `jev_config.py`.
- 대시보드 중계: `src/app/dashboard_local.py`. 현재 로컬 UI도 함께 제공한다면 `src/app/web/observatory/`와 해당 실행 스크립트·compose 서비스가 함께 필요하다.
- 에이전트 이유 설명/ASK: `tools/hookgw_mcp.py`와 현재 ASK 연결에 필요한 hook/launch/preflight 및 `tools/product_codex.py` 변경.
- 문서: 이 기준서와 루트 README. 중복된 이전 인계 문서는 Git에서 제외하고 로컬/이전 commit에 보존한다.
- 관련 시험: ASK·dashboard·Jev 설정/사용량 회귀. 선택한 실행 구성에는 필요한 의존성 잠금과 실행 파일을 같이 검토한다.

제외: runtime·실제 키/토큰·인증서 private key·DB·사용자 원문·실행 artifacts·DTAP 산출물·무관한 benchmark 변경·기존 미커밋 작업·개인 Codex 설정. 현재 원격은 BobWithHuman/sogaeding임을 확인했다. 현재 공유에는 ASK·이유 설명·대시보드·Codex 연결기·재현 가능한 빌드/실행 구성이 포함된다. 원격 반영은 해당 commit의 GitHub 상태를 확인한다.

검증 근거는 로컬 artifacts/dashboard-integration-20261027-01에 보관한다. 기존 무제한/사용량/응답 검증190개, 이번 이유 전달·ASK/조회/엔진/연결기99개 시험 통과(겹치는 시험 수를 합산해 독립 시험 수로 표현하지 않음). 실제 사용자 성공 기록은 ASK initial → RECHECKED/ALLOW → OBSERVED이며, 이전 한도 소진 실패 기록도 그대로 보존했다. 변경된 이유 문구에 대한 실제 사람 UI 재시험은 별도다. 새 clone 패키징 검증 결과는 다음 절에 기록했다.


## 9. 최소 배포·새 clone 재현 결과

2026-10-27 코드 기준 `81a7e42`를 별도 폴더에 실제 clone하여 다음을 확인했다. 원래 PC의 runtime·키·DB·인증서를 복사하지 않았다. 새 이름 clone-check, 새 volume·역할 자격·CA와 별도 포트8230/8240/8250을 사용했다. provider용 키는 의도적으로 합성 파일을 썼으며 실제 provider 요청은0회다.

- 단일 Dockerfile의 runtime target: cache 없이 공식 digest 기반 이미지와 해시 고정 실행 패키지30개를 설치해 빌드 성공. 설치 내역은 실제 빌드 로그와 고정 requirements.txt를 기준으로 한다.
- 동일 Dockerfile의 dev target과 README 명령: 제품 회귀195개 통과/5개 skip. skip2개는 제거한 과거 control 모듈용 검사, 3개는 별도 TLS 통합 환경용 시험이다. 이후 소규모 수정의 영향 범위50개도 통과했다. 겹치는 시험 수를 합산하지 않는다.
- prepare→up→check에서 새 PC 전용 자격 생성, 설치된 Codex의 설정 파싱과 엔진 TLS READY 확인. 실제 actor 모델은 호출하지 않았다.
- 새 clone의 실제 stdio MCP 연결기→Gateway→private mTLS /authz→Upstream을 거쳐 docs/release.md 읽기 OBSERVED 확인. 합성 .env 쓰기는 PROTECTED_RESOURCE DENY이며 파일 생성0, upstream 시도는 읽기1개뿐이다.
- 새 대시보드 API와 브라우저에 후보2개/ALLOW1/DENY1/성공1 집계 확인. 최초 사용량 장부가 없을 때 실제 사용량은 미수집으로 두면서 무제한 설정은 표시한다.
- 기동 중 일시적인 TLS EOF는 기존15초 health 대기 내에서만 재시도한다. 인증서 검증 실패/HTTP 인증 오류는 즉시 거부하고, 모델/도구 실행을 자동 재시도하지 않는다.
- 별도 AI 읽기 전용 검토에서 배포 경계·import closure·최소 수정에 핵심 미해결 결함을 찾지 못했다. 독립적인 공식 보안 진단이나 새 이미지 CVE 검사 통과를 뜻하지 않는다.

과거 Compose14개 등180개 파일은 Git 추적만 제외했으며 원래 작업 폴더와 로컬 백업을 보존했다. 공유 파일은370개에서216개로 줄었고, 새 백엔드/연결기/시험 파일을 추가한 순감 수치다. YAML은 제품 compose.yaml과 Gateway의 agentgateway/config.yaml 두 개뿐이다. 팀원 변경92개와 DTAP 참조 의존 파일은 보존했으며, DTAP을 새 엔진으로 다시 실행한 것은 아니다.

증거: 로컬 artifacts/package-20261027-01의 clone-smoke-result.json, clone-unit-tests.log, final-related-tests.xml, staged-check.json, cleanup-plan.json, fresh-clone-dashboard.png. 증거의 로컬 경로는 공유 저장소에 runtime 자료를 넣었다는 뜻이 아니다. 검증용 서비스는 종료하고 새 장부/volume은 로컬에 보존한다.
