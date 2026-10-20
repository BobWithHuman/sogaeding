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

# MVP 구조·데이터 설계와 결정 기록

버전 MVP-SPEC-3. 세부 상태·권한은03, 보안 시험은05를 따른다. 제품의 구현 예정 설계다. Docker 개발 환경·의존성 설치 확인은06에 구분해 기록하며 제품 서비스·MCP·LIVE 수용시험 결과는 아직 NOT_RUN이다.

## 1. Docker Compose 두 서비스와 모듈 경계

| 구성 | 실행 위치 | 책임 | 다른 구성에 줄 권한 |
|---|---|---|---|
| Control/PDP | Compose `control`, 컨테이너 0.0.0.0:8000, 호스트 127.0.0.1:8000 / FastAPI | 사용자 API, 세션·정책·출처·판정·승인·원자적 실행 예약, HTML 대시보드 | 사용자 토큰과 게이트웨이 서비스 토큰을 분리 |
| MCP Gateway/PEP | Compose `gateway`, 컨테이너 0.0.0.0:8001/mcp, 호스트 127.0.0.1:8001/mcp / 공식 Python SDK | 세션 bearer 인증, 등록 도구 래핑, 검사·예약, private 실행, 출처 수집·결과 보고 | 사용자 세션 발급·승인 권한 없음 |
| DemoExecutor | Gateway의 private 모듈 | seed issue/README 조회, 로컬 모의 댓글 저장 | 별도 HTTP/MCP endpoint 없음, 승인 텍스트를 해석하지 않음 |
| Codex CLI LIVE runner | 호스트, 전용 CODEX_HOME·가짜 연구 workspace | OpenAI API 인증과 사용자 세션 토큰으로 보호 MCP 호출; 최초 사용자 원문 전달 | 사용자 API/service 토큰·실제 실행기 직접 접근 없음 |
| REPLAY runner | 로컬 시험 클라이언트 | 고정 시나리오를 사용자 세션 토큰으로 실제 MCP에 제출 | 사용자 API/service 토큰·실제 실행기 직접 접근 없음 |

대시보드는 Control/PDP의 단순 HTML과 JSON API로 만든다. React·Streamlit·그래프 라이브러리는 오늘 기본 의존성에서 뺀다. 원문은 텍스트로 escape하여 표시하고 API 권한은 서버에서 검사한다.

컨테이너 사이의 Gateway→Control 주소는 `https://control:8443`이다. Codex가 접속하는 resource audience는 호스트의 `https://127.0.0.1:8001/mcp`로 고정하고 내부 접속 주소와 혼동하지 않는다. DB는 두 서비스에 분리한 저장 경로로 둔다. Codex 연구 workspace에는 실제 프로젝트 소스·`.env`·DB·reference 원문을 연결하지 않는다. 개발용 Compose override에서 사용하는 소스 mount는 Gateway 프로세스 개발용이며 LIVE 연구 workspace와 별개다.

관문 프로세스 내부 실행기는 코드 접근 권한을 가진 같은 OS 사용자를 격리하지 않는다. 따라서 공격자 모델은 **외부 이슈/문서 및 에이전트 Tool 인자**이고, 보호 주장은 등록 MCP 호출 경로에 한정한다.

## 2. 한 호출의 실행 순서

1. MCP 인증 verifier가 bearer를 Control 내부 API에서 검증하고 서버 세션 ID·owner·만료·audience를 확정한다. 모델이 보낸 session/trace/source_label은 사용하지 않는다.
2. Gateway가 Tool registry와 스키마로 인자를 검증하고 요청 UUID를 발급한다. 같은 내부 HTTP 재시도는 UUID를 유지한다.
3. PDP가 불변 호출 record를 만들고 작업 범위, 대상, 민감정보, 호출/쓰기 예산, 정책과 출처 관측을 검사한다.
4. DENY 또는 미승인 CONFIRM은 구조화된 MCP 결과만 반환한다. 실행기는 호출하지 않는다.
5. ALLOW 또는 유효한 독립 승인이 있는 CONFIRM은 PDP의 reserve 트랜잭션을 통과해야 한다.
6. Gateway는 reserve 성공 후에만 private 실행기를 부른다. 읽기 반환은 출처 수집·마스킹이 끝난 뒤 에이전트로 전달한다.
7. 실행기는 effects DB에 call_id와 효과를 함께 저장한다. Gateway가 PDP에 실행 결과/receipt를 보고한다.
8. 결과 보고가 유실되면 ‘실행 안 됨’으로 바꾸지 않는다. UNKNOWN과 effects DB를 대조하고 추가 쓰기는 멈춘다.

## 3. 정책과 출처 관측의 역할

**1단계:** 인증·등록 도구·작업 grant·대상·민감 파일·예산·기본 제한 검사. 사용자 원문이 아닌 외부 텍스트는 권한을 만들 수 없다.

**2단계:** 서버가 수집한 issue 제목·허용된 식별자 등 최대16개, 항목당128문자 이하의 공개 match value와 호출 값을 대조한다. 일치는 OBSERVED_EXACT_MATCH 근거로만 저장한다. 외부 값이라는 이유만으로 DENY하지 않는다. 같은 문자열이 두 출처에 있으면 두 출처를 표시한다. 복잡한 변형·번역·분할의 탐지는 오늘 보장하지 않는다.

**3단계:** 의미 판단 어댑터는 후속 P1이고 기본 OFF다. 모델이 Tool 호출을 만드는 LIVE 에이전트와 PDP의 의미 판단 모델은 다른 구성이다. 향후 judge를 켜도 인증·금지 정책·민감 파일·범위·예산을 무효화하지 못한다.

오늘 정책의 추가 차단 효과를 출처 추적만의 효과로 발표하지 않는다. 원문→호출의 연관 관측과 권한에 따른 차단을 구분한다.

## 4. 저장소와 데이터 정의

Control용 `control.sqlite3`와 Gateway용 `effects.sqlite3` 두 파일을 사용한다. Compose의 서비스별 저장 경로로 분리하고 실제 위치는 실행 설정에 고정한다. 런타임 데이터는 Git 제외, 해당 서비스와 신뢰된 개발자만 접근하도록 설정·확인한다. 두 DB의 분산 트랜잭션을 주장하지 않는다. 각각의 원자성과 결과 대조로 장애를 처리한다.

| 테이블 | 주요 필드 | 제약 |
|---|---|---|
| sessions | id, owner_id, user_request, task_kind, issue_id, allowed_comment_body, policy_version, status, expires_at, call_budget, write_budget | 사용자만 생성; grant는 task_kind에서 서버가 구성; 기본 쓰기0 또는1 |
| session_tokens | token_sha256, session_id, audience, expires_at, revoked_at | 고엔트로피 raw token은 발급 응답에 한 번만; DB에는 해시 |
| sources | id, session_id, call_id?, kind, origin_ref, content_sha256, masked_excerpt, match_values, collected_at | USER_REQUEST는 사용자 세션 생성만(call_id null); read 출처는 unique(call_id,content_sha256); gateway ingestion은 EXTERNAL/WORKSPACE_DATA만 |
| calls | id, session_id, client_request_id, tool_name, backend_id, canonical_args_json?, masked_args_json, args_sha256, policy_version, created_at | unique(session_id,client_request_id); 동일 key·다른 action은409; 호출 불변; 민감 DENY는 canonical_args_json null |
| decisions | id, call_id, decision, reason_codes, source_ids, created_at | 최초 판정 append-only; 승인으로 원판정 삭제/수정 안 함 |
| approvals | id, call_id, args_sha256, policy_version, status, expires_at, approved_at, consumed_at | CONFIRM만, 세션/owner/tool/backend는 call에 결합 |
| executions | call_id, reservation_id, state, reserved_at, finished_at, effect_receipt, error_code | call_id당1건; 위험 쓰기 자동 재예약 금지 |
| events | id, session_id, call_id?, event_kind, safe_payload, created_at | 토큰·키 제외; phase별 판정/실행 구분 |
| effects DB: comments | id, session_id, call_id, issue_id, body, created_at | unique(session_id,call_id); 효과와 receipt를 같은 트랜잭션에 기록 |
| effects DB: invocations | call_id, session_id, tool_name, started_at, outcome | call_id 유일; 실제 실행기 진입·읽기/쓰기 횟수 관찰용. DENY에 record가 생기면 실패 |

SQLite의 트랜잭션은 각 DB 내 원자성의 근거다. [SQLite 공식 설명](https://www.sqlite.org/transactional.html). reserve에서는 BEGIN IMMEDIATE 및 조건부 UPDATE로 호출 상태·승인 소비·쓰기 예산을 함께 변경한다. concurrent reserve 검증은 별도 수용시험으로 남긴다.

canonical_args_json은 CONFIRM 화면과 재개에 필요한 최대4096문자의 비민감 본문을 포함한다. 민감정보로 DENY한 호출은 canonical_args_json을 null로 두고 masked_args_json만 저장한다. args_sha256은 마스킹 전 검증된 원후보의 digest이며, 이 DENY 예외에서는 masked_args_json의 hash와 같지 않다. DENY 호출은 승인·재개 대상이 될 수 없다. 출처 원문은 요청 범위 임시 데이터로 처리하며 excerpt/match_values는 민감정보 제거 뒤 저장한다.

## 5. 인증·데이터 경계

- HUMAN_USER_TOKEN: 세션·승인·타임라인 API. Gateway와 모델에 전달하지 않는다.
- GATEWAY_SERVICE_TOKEN: 내부 검증·출처·검사·reserve·report API. 세션 생성/승인 권한 없음.
- agent_session_token: 한 세션·audience·만료에 제한. 모델 prompt와 로그에 넣지 않는다.
- OPENAI_API_KEY: 호스트 Codex CLI의 OpenAI 인증용 환경변수. P0 Control/Gateway에는 주입할 필요가 없다. Tool 결과·프롬프트·대시보드에 전달하지 않는다.
- CODEX_HOME: LIVE 세션의 전용 설정 디렉터리. 사용자의 일반 Codex 설정·인증 파일과 분리하며 실제 경로는 Git 제외한다.

사용자 페이지는 token 입력 후 브라우저 메모리에만 유지하고 Authorization header로 API를 호출한다. 쿠키/localStorage 기반 토큰 저장·외부 CORS 허용은 기본안에 없다. 페이지 shell 자체에 세션 데이터·키를 넣지 않는다.

인증 TCP 경로는 TLS와 서버 인증서 검증을 필수로 한다. Gateway→Control은 8443의 mTLS 내부 포트를 사용한다. 공개 8000 포트는 내부 API를 거부한다. 앱 전용 CA와 런타임 키를 사용하며 전역 신뢰 저장소를 변경하지 않는다.

## 6. SDK·기술 결정(ADR)

| ID | 선택 | 이유·대가·후속 |
|---|---|---|
| ADR-01 | Python 3.12 + Docker Compose 두 서비스 | 사용자가 Docker를 켰고 엔진 연결을 재확인했다. 실행·의존성 재현을 컨테이너 기준으로 통일; 이미지 build와 제품 기동은 별도 검증 |
| ADR-02 | Python MCP PEP + FastAPI PDP | body 인자와 반환 출처를 직접 다루기 쉬움. agentgateway 연동은 다음 어댑터로 보존 |
| ADR-03 | SQLite와 단순 HTML | 설치·UI 시간을 줄임. PostgreSQL/Redis/멀티워커/운영 확장은 후속 |
| ADR-04 | MCP SDK **mcp==2.3.0** 고정 | 해시가 포함된 requirements-dev.lock으로 Docker 개발 환경에 설치했다. 실제 MCP 인증 handshake는 미검증; v1 FastMCP 예제와 혼용 금지 |
| ADR-05 | 구조화된 작업 grants 우선 | 의미 모델이 권한을 만들지 않음. 자유형 의도 해석·판정 성능은 후속 측정 |
| ADR-06 | 모의 로컬 실행기 | 실제 위험 효과 없이 write count를 증명. 실제 GitHub 쓰기·Codex 내장 셸/파일 도구까지 보호했다고 주장하지 않음 |
| ADR-07 | Codex CLI LIVE + 결정적 REPLAY | Codex CLI 0.154.0 설치를 확인했고 OpenAI API 키 사용 가능 정보가 있다. 모델 ID는 설정에서 확정. 모델 변동성과 통제 경로 재현을 분리 |
| ADR-08 | 최초 사용자 원문을 신뢰된 런처에서 동일 전달 | 세션의 user_request와 Codex 최초 프롬프트 불일치로 권한 기준이 어긋나는 일을 막는다. 후속 사용자 작업 변경은 새 세션 |

SDK2의 MCPServer·Client·token verifier API는 정확한 v2.3.0 문서/태그를 따른다. [공식 authorization 문서](https://py.sdk.modelcontextprotocol.io/run/authorization/). 오늘은 localhost 개발용 사전 발급 opaque bearer 인증이며 OAuth2.1 authorization/token/discovery 상호운용을 완성했다고 표시하지 않는다.

MCP verifier는 audience(resource URL), required scope tools:invoke, 서버 세션의 활성/만료를 확인한다. handler는 검증된 access-token 문맥만 사용한다. Client의 bearer 전달은 해당 버전 transport HTTP client로 설정한다. `Client(url, headers=...)` 같은 다른 버전 예제를 추정해 사용하지 않는다. 설치 후 최소 인증 smoke가 첫 구현 게이트다.

SDK2.3.0의 transport는 해당 SDK가 사용하는 httpx2.AsyncClient를 streamable_http_client의 http_client에 전달한 뒤 Client에 transport를 주는 방식으로 확인했다. [v2.3.0 transport 원본](https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/client/streamable_http.py). SDK 의존성의 실제 설치 버전과 소스를 대조한다. Control HTTP client를 다른 HTTPX 버전으로 만들 경우 두 client 타입을 섞지 않는다.

agentgateway의 [외부 인가](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/external-authz/)는 지원되지만 요청 인가만으로 반환 데이터의 출처 수집이 만들어지지는 않는다. 이번 변경은 예선 기획을 폐기하는 것이 아니라 PEP/PDP 계약을 먼저 고정한 뒤 adapter로 확장하는 순서다. 기획서 업데이트에 실제 변경·보호 범위·남은 연동을 명시한다.

## 7. 예상 코드 배치

아래 경로는 앞으로 만들 구현 파일의 책임이며 지금 존재하는 앱 코드가 아니다.

| 경로 | 책임 |
|---|---|
| src/app/control/ | 세션·승인·조회 API와 사용자 인증 |
| src/app/pdp/ | 정책·출처 관측·canonicalization·reserve 상태 전이 |
| src/app/storage/ | control DB schema·repository·transaction |
| src/app/gateway/ | SDK2 인증·세 도구·Control HTTP client |
| src/app/executor/ | private fixture 읽기·effects DB |
| src/app/agents/ | 결정적 REPLAY runner; LIVE 모델 에이전트를 재구현하지 않음 |
| scripts/ | Compose 점검·실행, Codex CLI 전용 환경·LIVE 실행, 결과 수집 |
| src/app/web/ | escape된 HTML·타임라인·승인 UI |
| fixtures/ | 가짜 이슈·README·가짜 비밀, 정상/공격 쌍 |
| tests/ | 05의 실제 수용시험과 race/failure 검사 |
| artifacts/ | 실행·진단 증거; 민감정보 점검 후 보관 |

## 8. 제품과 개발 harness의 구분

제품의 런타임 통제는 Control/PDP·Gateway/PEP·private executor가 수행한다. 개발 harness는 Codex가 이 저장소를 구현할 때 문서·작업 순서·검사 명령·증거 위치를 따라가도록 하는 `AGENTS.md`, 작업 기록, 실행 스크립트와 검증 규칙이다. 개발 지침이나 프롬프트만으로 실제 도구의 실행 권한을 집행했다고 주장하지 않는다. LIVE runner는 구현된 제품에 Codex CLI를 연결하는 시험·데모 진입점이며, 개발에 사용하는 Codex 세션과 전용 CODEX_HOME을 분리한다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
