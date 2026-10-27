# With Human 대시보드 개발 인계서 — ASK 전환 기준

작성: 2026-10-27 / 대상: 대시보드 구현 담당 팀원

이 문서만으로 화면·mock·연동 코드를 개발할 수 있도록 제품 역할, 필수 기능, 데이터 계약, 예시, 예외 처리와 완료 기준을 정의한다. 디자인, 화면 배치, 차트 종류, 프레임워크는 담당자가 자유롭게 결정한다.

**제품 방향은 확정됐지만 ASK와 아래 dashboard/v1 API는 아직 구현 전이다.** 현재 소스는 CONFIRM을 반환한다. 이 문서의 목표 API는 팀원이 바로 사용 가능한 기존 API라고 간주하면 안 된다. 프론트는 목표 계약을 mock으로 개발하고, 엔진 담당이 같은 계약의 조회 API와 ASK 흐름을 구현한다. 문서 작성 자체가 엔진 변경 완료를 뜻하지 않는다.

## 1. 제품과 대시보드의 역할

With Human은 AI 에이전트가 도구를 실행하기 전에 실제 사용자 요청, 도구로 관측한 외부 자료, 실행 후보를 대조하는 로컬 보안 엔진이다. 외부 자료에 섞인 추가 지시가 사용자의 권한인 것처럼 실행되는 간접 프롬프트 인젝션(IPI)을 방어하는 것이 목적이다.

배포 목표는 각 사용자의 로컬 단말에서 독립 엔진·키·DB를 실행하는 것이다. 현재 기본 정책은 gate-6이다. 실제 제공되는 기본 도구는 등록 작업영역의 MCP read_file/write_file이며, 일반적인 모든 shell/native 도구를 이미 보호한다고 표현하면 안 된다.

### 엔진의 동작 순서

1. 신뢰 연결기가 실제 사용자 프롬프트·세션·턴을 엔진에 전달한다.
2. 에이전트가 도구를 실행하려 할 때 도구명·대상·인자·출처를 실행 전에 등록한다.
3. 엔진이 도구 schema, 작업영역, 보호 경로, 권한, 출처의 실제 관측·완전성 등을 코드로 확인한다.
4. 필요한 후보는 외부 Jev API로 의미를 분석한다. Jev는 관측을 반환하고 최종 판정·권한·집행은 엔진이 담당한다. 모든 호출에 Jev를 쓰는 것은 아니다.
5. 엔진은 ALLOW / DENY / ASK 중 하나를 반환하는 구조로 변경할 예정이다. 필수 분석 장애를 임의 ALLOW로 바꾸지 않는다.
6. ALLOW인 정확한 후보만 gateway의 최종 대조·단회 예약을 통과해 실제 도구로 집행된다. 결과가 관측되면 이력에 저장한다. 결과를 확정할 수 없으면 UNKNOWN으로 남긴다.
7. 에이전트·엔진 실행이 끝나도 보존 기간 안의 이력은 대시보드에서 조회한다. 다만 엔진 조회 서버는 실행 중이어야 한다. 서버가 꺼져 있는데 영구 조회가 가능한 제품은 아니다.

기본 정상 허용은 A의 실제 WITHIN_TASK 선택과 B의 LEGITIMATE 유효 확신도 .50 이상 및 권한·출처 검사를 요구한다. 위험 DENY 기준 .90과 하드 금지는 유지한다. 대시보드가 이 점수로 자체 재판정하거나 정책을 바꾸지 않는다.

### 세 판정의 의미

| 판정 | 의미 | 실행 여부 |
|---|---|---|
| ALLOW | 현 후보의 실행을 허용할 수 있음 | 최종 집행 검사 후 실행. ALLOW 자체는 실행 성공 아님 |
| DENY | 현 후보를 거부 | 실행 금지. 사용자 답변이나 대시보드로 해제하지 않음 |
| ASK | 현 정보로 바로 실행하지 않고 실제 사용자에게 질문해야 함 | 질문·답변·재검토가 끝나기 전 실행 금지 |

### 기존 계획과의 차이

| 항목 | 기존 CONFIRM | 변경할 ASK |
|---|---|---|
| 사용자에게 묻는 곳 | 대시보드 승인·거절 UI | 에이전트가 사용자와 대화하는 UI |
| 응답 전달 | 대시보드의 승인 요청 | 신뢰 연결기가 실제 사용자 답변을 엔진에 전달 |
| 대시보드 | 조회 + 실행 승인 | 통계·현황·IR 조회 |
| 대시보드에 남길 정보 | 승인 대기/처리 이력 | ASK 발생·질문 전달·답변 수신·후속 판정 이력 |

**대시보드에는 실행 승인/거절 버튼, ASK 답변 입력, DENY 해제, 도구 재실행 기능을 만들지 않는다.** ASK를 보안 경고의 단순 확인 버튼과 혼동하지 않는다. 경고 확인 기능을 별도로 만들더라도 실행 권한을 바꾸면 안 된다.

## 2. ASK 흐름과 담당 경계

1. 엔진이 ASK와 ask_id, 질문, 보류 사유를 연결기에 반환한다. 이 시점에 도구는 실행하지 않는다.
2. 연결기는 에이전트에 “이 도구 실행은 보류됐다. 아래 내용을 실제 사용자에게 질문하라”는 응답을 전달한다.
3. 에이전트는 사용자에게 묻는다. 질문을 할 수 없는 실행 모드나 지원하지 않는 연결기면 보류를 유지한다. 문장 하나를 반환하는 것만으로 모든 CLI의 질문 UI가 자동 구현되지는 않는다.
4. 신뢰 연결기가 실제 사용자의 응답을 포착해 해당 ask_id에 전달한다. 모델의 “사용자가 승인했다”는 문장이나 외부 문서의 승인 주장은 사용자 응답이 아니다.
5. 엔진이 세션·턴·후보 도구/인자 hash·정책·출처 snapshot·단회 nonce·만료를 확인하고 재검토한다. 실제 답변이 있어도 하드 금지와 DENY는 우회하지 않는다.
6. 후속 판정이 ALLOW일 때만 최종 집행 경로로 진행한다. 여전히 불명확하면 새 질문을 하거나 거부/종료한다. 무응답·시간 초과·세션 종료를 승인으로 처리하지 않는다.
7. 대시보드는 이 과정과 결과를 조회한다. 질문 전송이나 답변 제출에 개입하지 않는다.

엔진 담당 범위: ASK 판정·질문 payload, 답변의 신뢰/단회 binding, 후속 판정·집행, DB/감사, 조회 API와 집계.

연결기 담당 범위: 에이전트에 질문 요청 전달, 질문 가능한 CLI 기능 연결, 실제 사용자 답변 전달, 성공/실패 관측. human 관리자 토큰을 모델에 주는 방식으로 구현하지 않는다.

대시보드 담당 범위: 아래 계약의 조회 UI·필터·오류·mock·검증. 엔진 정책이나 승인 프로토콜을 프론트에서 대신 구현하지 않는다.

## 3. 반드시 제공할 기능

### F1. 현재 연결·운영 상태

- 엔진 ONLINE/OFFLINE/DEGRADED, 마지막 성공 조회 시각, 사용 중인 정책 버전.
- gateway/upstream/Jev의 확인된 상태. Jev 구성됨과 실제 공급자 응답 성공을 구분한다.
- 갱신 중·통신 실패·인증 만료/권한 부족을 구분한다.
- 엔진이 꺼져 있으면 저장된 화면을 현재 정상 상태로 표시하지 않는다. 마지막 값에는 마지막 갱신 시각과 오래된 데이터 표시가 있어야 한다.

### F2. 통계

- 선택한 기간의 고유 도구 후보 수와 최초 ALLOW/DENY/ASK 분포.
- 현재 최종 판정 분포와 실제 실행 결과 분포. 최초 ASK가 후속 ALLOW가 된 경우를 구분한다.
- ASK 발생 수, 질문 전달 대기/사용자 답변 대기, 답변 수신 후 재검토 대기, 재검토 완료·사용자 거절·만료·취소 수.
- 최종 DENY의 차단 근거별 수: 코드 규칙 / Jev 의미 판정 / 사용자 거절 / 분석·인프라 실패 / 기타·미분류.
- 시간에 따른 후보/판정 추이와 사유별 집계. 표시 방식은 자유다.
- Jev 요청 수, 알려진 토큰 사용량, 예약량, 한도/잔여를 분리한다. 수집되지 않은 값은 “미수집”으로 표시하고0으로 대체하지 않는다. 실제 usage와 사전 예약량은 다른 값이다.

### F3. 판정·도구 실행 이력

- 최신 순 목록. 시간, 세션, 에이전트 종류, 도구, 마스킹한 대상, 최초 판정, 최종 판정, 실행 결과, 사유, 판정 경로를 확인할 수 있어야 한다.
- 기간·세션·에이전트·도구·판정·실행 결과·사유·경로 필터와 다음 페이지 조회.
- 항목 선택 시 F4 상세로 이동. 새로고침 후에도 event_id로 같은 항목을 열 수 있어야 한다.
- “ASK만 보기”, “최종 DENY만 보기”, “UNKNOWN/분석 실패 보기”가 가능해야 한다. 반드시 별도 페이지일 필요는 없다.

### F4. 사건 상세 / IR 조사

- 언제 어떤 에이전트·도구 후보가 무엇을 하려 했고, 어떤 근거로 판정됐고, 실제 효과는 어디까지 확인됐는지 보여준다.
- 실제 사용자 요청 → 외부 자료 관측 → 후보 등록 → 코드 검사 → 필요 시 Jev → 판정 → ASK 흐름 → 최종 집행/관측을 시간순으로 조회한다. 없는 단계는 생략한다.
- 사유 코드와 사람이 읽을 수 있는 설명, 코드/의미/장애의 구분, 당시 정책 버전.
- 출처 목록·서버 관측 여부·무결성/완전성 상태. 모델이 스스로 주장한 출처를 검증 완료로 표시하지 않는다.
- ASK의 질문 요약, 전달/응답/후속 판정 시각과 상태. 민감한 실제 답변 원문은 기본 노출하지 않는다.
- UNKNOWN/미완료에는 “실행 효과 미확정”을 표시한다. 실행 안 됨으로 단정하지 않는다.

### F5. 보안 감사·경고 조회

- 반복 인증 실패, 반복 접근 거부, 자격 교체 등의 서버 제공 경고 목록.
- 경고 시간·종류·심각도·확인 상태와 관련 감사 기록.
- 감사에는 주체 hash·행위·대상 hash·결과·시각을 표시한다. hash로 실제 사용자 이름을 추측하지 않는다.
- 대시보드에서 경고를 “확인”하는 기능은 선택 구현이다. 실행 승인과 별개이고, 쓰기 API/권한이 준비됐을 때만 활성화한다.

### F6. 개인정보·보존·안전한 표시

- 목록·상세에는 서버가 만든 마스킹 projection만 사용한다. raw /history 전체를 브라우저에 내려받아 숨기는 방식은 사용하지 않는다.
- 프롬프트·도구 결과·파일 내용은 신뢰할 수 없는 문자열이다. HTML/Markdown 실행·자동 링크 접근·명령 실행 없이 텍스트로 표시한다.
- API 키, bearer, storage/forward 키, 인증서 private key를 표시·보관·내보내지 않는다.
- TTL로 삭제된 원문은 “보존 기간 만료/삭제”로 표시한다. 삭제된 내용이 브라우저 저장소에 계속 남지 않도록 한다.
- 대시보드는 삭제·정책 변경·원격 실행 UI를 이번 범위에 넣지 않는다.

필수 범위 밖: 디자인 고정안, 사용자 가입/회사 tenant 관리, 승인센터, 정책 편집기, 실시간 WS/SSE, 외부 SIEM/메일 발송. 필수 기능이 완성된 뒤 메타데이터 JSON 내보내기 등을 선택 추가할 수 있다. 내보내기도 같은 마스킹·조회 권한을 적용해야 한다.

## 4. 통계 집계 규칙 — 반드시 동일하게 구현

| 항목 | 집계 기준 |
|---|---|
| 기본 단위 | 등록 도구 후보의 고유 event_id 1개. polling/동일 event 재조회는 추가 건수 아님 |
| 최초 판정 분포 | initial_decision으로 집계. ASK→ALLOW도 최초 분포에는 ASK1개 |
| 최종 판정 분포 | 현재 decision으로 집계. ASK→ALLOW는 ALLOW1개이며 ASK에 중복 집계하지 않음 |
| ASK 흐름 | ask_id 단위. 한 후보가 새 질문을2번 받으면 후보1개/ASK요청2개로 구분 |
| 실제 실행 | execution.outcome으로 집계. ALLOW만 보고 실행 성공으로 계산하지 않음 |
| 차단 근거 | 최종 DENY 후보의 denial_origin을 집계. 추정하지 않음 |
| 기간 | 후보의 created_at이 from 이상/to 미만인 집합. 이후 판정 변경은 그 후보의 현재 결과로 반영 |
| 시간 추이 | 같은 created_at 집합을 서버가 bucket별 집계. 날짜 경계는 지정 timezone 사용 |
| 분모 | 모든 카드·추이·목록에 동일한 기간/필터 적용. 현재 페이지 건수를 전체로 쓰지 않음 |

**호출 거부 횟수는 공격 시나리오 방어 건수가 아니다.** 정상 작업이 거부될 수도 있고 하나의 공격이 여러 후보를 만들 수도 있다. 실제 운영 대시보드에는 “공격 성공률/방어율100%”를 판정 건수로 계산해 넣지 않는다. 벤치마크 수치는 정답·OFF/ON 대응 시나리오가 있는 별도 평가다.

코드와 Jev가 모두 관여해도 서버의 단일 denial_origin으로 집계한다. SEMANTIC 경로라는 이유만으로 모든 DENY를 “Jev가 공격을 발견함”이라고 표시하지 않는다. 분석 불가·예산 소진·인프라 중단은 별도다.

기록을 아직 받지 못한 값은 null/미수집, 실제0건은0으로 구분한다. API가 scope=LATEST_100_CALLS를 반환하면 “최근100건”으로만 표시하고 전체 누적으로 바꾸지 않는다.

## 5. 연결·인증·브라우저 구성

대시보드 화면은 로컬 dashboard backend/BFF를 통해 엔진에 접근하는 구성을 기본으로 한다. 개발 서버 주소·포트는 자유지만 외부 네트워크 공개는 기본값으로 두지 않는다.

- 브라우저는 같은 origin의 상대 경로 /dashboard/v1/*를 호출한다. 프론트 코드에서 엔진 주소나 토큰을 하드코딩하지 않는다.
- BFF만 접근 제한된 파일/secret mount의 조회 전용 운영자 자격과 엔진 CA를 읽는다. 필요한 권한은 history:read, security:read다. approval:write, session:purge, machine 권한을 주지 않는다.
- 브라우저 localStorage/sessionStorage, URL query, JS bundle, console, analytics에 bearer를 넣지 않는다. VITE_ 같은 공개 환경변수에 넣지 않는다.
- BFF→엔진은 명시 CA 검증 HTTPS, timeout, redirect 미추적. verify=false/임의 HTTP 우회 금지.
- 엔진의 현재 public endpoint는 https://127.0.0.1:8130, 내부 Docker 주소는 https://control:8030이다. 다른 포트를 쓸 수 있으므로 BFF 서버 측 설정으로 받는다.
- 현재 엔진은 Host/Origin 경계를 검사한다. 브라우저에서 다른 origin의 Control에 바로 fetch하는 방식으로 우회하지 않는다. BFF는 서버 간 호출로 적절한 Host와 인증을 사용한다.
- 브라우저→BFF도 로컬 세션/접근 제한과 Host/Origin 검사를 적용한다. 경고 확인 같은 쓰기는 인증·CSRF 방어를 갖춰야 한다.
- 독립 단말/자격의 분리이지 동일 Docker daemon 관리자나 동일 OS 계정의 무제한 프로세스를 격리하는 제품은 아니다.

## 6. 현재 API와 목표 API의 구분

### 지금 소스에 있는 API

| API | 현재 반환/용도 | 대시보드 사용 시 한계 |
|---|---|---|
| GET /health | 무인증이면 status 정도. machine 인증 시 상세 구성 | 원문/운영 자격을 브라우저에 주지 않음. Jev 실제 추론 성공 증명 아님 |
| GET /history/summary | 최근100개 호출의 counts/calls | 누적·기간 필터·pagination·시각/세션/ASK 상세 계약 부족 |
| GET /history | 운영자 인증 후 원문을 포함할 수 있는 이력 | 브라우저용 안전한 상세 API가 아님. BFF/엔진 projection 필요 |
| GET /demo/history | 환경변수로 활성화하는 기존 demo projection | 기본 엔진 ZIP은 demo viewer 비활성. 최종 대시보드 계약으로 고정하지 않음 |
| GET /security | 최근100개 보안 사건과 경고 | 보안 보강 작업의 현재 working tree 기능. 원격 릴리즈 배포 완료 아님 |
| POST /security/alerts/ack | security:ack 권한으로 경고 확인 | 선택 기능. 실행 승인 아님 |
| POST /approval | 현 CONFIRM의 운영자 승인 | 새 대시보드는 연결하지 않음. ASK 전환 시 엔진/연결기 담당이 대체 |

현재 /history/summary의 실제 형태 예시:

```json
{"scope":"LATEST_100_CALLS","counts":{"ALLOW":1,"CONFIRM":1},"calls":[{"id":"call-1","decision":"ALLOW","state":"OBSERVED","policy":"engine-2026-10-24-gate6-1","routing":"RULE_ALLOW","reasons":["PUBLIC_ENROLLED_READ"],"reasons_truncated":false},{"id":"call-2","decision":"CONFIRM","state":"CONFIRM","policy":"engine-2026-10-24-gate6-1","routing":"SEMANTIC","reasons":["SENSITIVE_RESOURCE_REQUIRES_CONSENT"],"reasons_truncated":false}]}
```

구버전 CONFIRM을 새 ASK 처리 완료로 바꿔 표시하지 않는다. 이행 기간에는 “이전 방식 CONFIRM”으로 식별하거나 지원되지 않는 버전이라고 알린다. 단순 문자열 치환은 ASK 질문/응답 구현이 아니다.

### 목표 조회 API — 구현 계약 v1, 아직 미구현

이하 API를 엔진 담당/BFF가 제공하면 프론트는 그대로 연동한다. UI가 raw engine DB를 직접 읽거나 민감한 /history를 대신 수집하지 않는다. 프론트 담당은 이 계약의 mock provider를 먼저 구현한다.

공통:

- UTF-8 JSON, Cache-Control: no-store. 모든 시각은 UTC ISO8601(Z), 화면은 Asia/Seoul 등 선택한 timezone을 명시한다.
- GET은 부작용 없이 재시도 가능. 실패한 읽기를 도구 실행 재시도로 연결하지 않는다.
- event_id/ask_id는 opaque 문자열이다. URL에 넣을 때 encodeURIComponent를 사용하고 내용으로 경로나 권한을 만들지 않는다.
- 알 수 없는 enum/새 reason code는 앱을 중단하지 않고 “알 수 없음 + 원 코드”로 표시한다. 안전하지 않은 문자열을 HTML로 삽입하지 않는다.
- 요청 범위 최대7일, limit 기본50/최대100. cursor는 서버가 발급하는 opaque 값이다.
- from/to는 필수 UTC 시각, timezone 기본 Asia/Seoul. from 포함/to 미포함.
- 필터: session_id, agent, tool, initial_decision, decision, execution_outcome, denial_origin, reason_code, routing. 같은 필터는 AND이며 비어 있으면 전체다. 임의 텍스트 정규식 검색은 필수 아님.

#### 6.1 GET /dashboard/v1/status

```json
{
  "contract_version":"dashboard-v1",
  "observed_at":"2026-10-27T06:00:00Z",
  "engine":{"state":"ONLINE","policy":"engine-2026-10-24-gate6-1","decision_contract":"ASK_V1"},
  "services":{"gateway":"ONLINE","upstream":"ONLINE","jev":"CONFIGURED_NOT_TESTED"},
  "capabilities":{"ask_history":true,"security_events":true,"alert_ack":false,"raw_context":false},
  "retention":{"session_seconds":86400,"history_seconds":604800,"security_seconds":604800},
  "data_window":{"earliest_available_at":"2026-10-20T06:00:00Z","latest_available_at":"2026-10-27T06:00:00Z"}
}
```

engine.state: ONLINE / DEGRADED / OFFLINE / UNKNOWN. service 상태는 ONLINE / OFFLINE / UNKNOWN이며 Jev는 CONFIGURED_NOT_TESTED / LAST_REQUEST_OK / LAST_REQUEST_FAILED / DISABLED도 허용한다. 실제 새 모델 요청으로 상태검사를 수행하지 않는다. decision_contract는 ASK_V1 또는 LEGACY_CONFIRM이며 후자면 ASK 이력 지원을 가정하지 않는다. BFF만 장애이면 엔진 자체 장애라고 단정하지 않는다.

#### 6.2 GET /dashboard/v1/summary?from=...&to=...&timezone=Asia%2FSeoul

공통 필터를 함께 받는다. period bucket은 hour/day이며 bucket_start는 UTC다. 아래는 후보3개: 최초 ALLOW1·DENY1·ASK1, ASK는 사용자 응답 후 ALLOW가 된 예시다.

```json
{
  "scope":"FILTERED_RETAINED_CALLS",
  "generated_at":"2026-10-27T06:00:00Z",
  "range":{"from":"2026-10-26T15:00:00Z","to":"2026-10-27T15:00:00Z","timezone":"Asia/Seoul"},
  "total_calls":3,
  "initial_decisions":{"ALLOW":1,"DENY":1,"ASK":1,"UNKNOWN":0},
  "effective_decisions":{"ALLOW":2,"DENY":1,"ASK":0,"UNKNOWN":0},
  "execution_outcomes":{"SUCCEEDED":2,"REPORTED_ERROR":0,"NOT_EXECUTED":1,"IN_PROGRESS":0,"UNKNOWN":0},
  "asks":{"total_requests":1,"ISSUED":0,"PRESENTED":0,"ANSWER_RECEIVED":0,"RECHECKED":1,"DECLINED":0,"EXPIRED":0,"CANCELLED":0},
  "denials":{"STRUCTURAL_RULE":0,"JEV_SEMANTIC":1,"USER_DECLINED":0,"ANALYSIS_FAILURE":0,"OTHER":0,"UNATTRIBUTED":0},
  "jev":{"requests":4,"input_tokens_actual":null,"output_tokens_actual":null,"input_tokens_reserved":256000,"request_limit":20,"requests_remaining":16,"input_reservation_limit":1280000,"input_reservation_remaining":1024000,"scope":"RUNTIME_LEDGER"},
  "series":[{"bucket_start":"2026-10-27T05:00:00Z","total_calls":3,"initial_ALLOW":1,"initial_DENY":1,"initial_ASK":1,"initial_UNKNOWN":0}],
  "reasons":[{"code":"EXTERNAL_INSTRUCTION_DEPENDENCY","count":1}]
}
```

Jev 원장은 runtime 전체 범위다. period 카드와 분모가 다르므로 별도 범위를 명시한다. 기간별 Jev 통계가 제공되면 scope=FILTERED_CALLS로 구별한다. 현재 장부에서 연결할 수 없는 값을 호출 수 비례로 추정하지 않는다.

#### 6.3 GET /dashboard/v1/events?from=...&to=...&limit=50&cursor=...

공통 필터를 받는다. created_at 내림차순, 동률은 event_id 순으로 서버가 안정 정렬한다. 다음 페이지 요청은 동일 필터를 유지한다. 새 polling으로 첫 페이지를 갱신할 때 이전 cursor 체인은 초기화한다.

```json
{
  "scope":"FILTERED_RETAINED_CALLS",
  "generated_at":"2026-10-27T06:00:00Z",
  "total":1,
  "items":[{
    "event_id":"evt-003","call_id":"call-003","session_id":"session-demo","turn_id":"turn-1",
    "created_at":"2026-10-27T05:57:00Z","updated_at":"2026-10-27T05:58:02Z",
    "agent":"codex","tool":"write_file","target_display":"reports/summary.md",
    "initial_decision":"ASK","decision":"ALLOW","engine_state":"OBSERVED",
    "execution":{"outcome":"SUCCEEDED","started_at":"2026-10-27T05:58:01Z","observed_at":"2026-10-27T05:58:02Z"},
    "routing":"SEMANTIC","denial_origin":null,
    "reasons":[{"code":"USER_INTENT_SUPPORTED","label":"사용자 요청 범위로 확인됨"}],
    "policy":"engine-2026-10-24-gate6-1",
    "ask":{"ask_id":"ask-003-1","state":"RECHECKED","outcome":"ALLOW"},
    "redacted":true,"context_status":"AVAILABLE_REDACTED"
  }],
  "next_cursor":null
}
```

agent: codex / claude_code / other / unknown. 모르는 에이전트를 codex로 추정하지 않는다. routing: RULE_ALLOW / RULE_DENY / SEMANTIC / ANALYSIS_FAILED / UNKNOWN. 구조 차단 전이라 경로가 없으면 UNKNOWN이다.

decision/initial_decision: ALLOW / DENY / ASK / UNKNOWN. denial_origin: STRUCTURAL_RULE / JEV_SEMANTIC / USER_DECLINED / ANALYSIS_FAILURE / OTHER / UNATTRIBUTED, 비DENY는 null.

execution.outcome: SUCCEEDED / REPORTED_ERROR / NOT_EXECUTED / IN_PROGRESS / UNKNOWN. REPORTED_ERROR는 오류 응답을 관측했다는 의미이며 부작용0 보증이 아니다. 서버가 결과를 확정할 수 없다면 UNKNOWN으로 반환한다. UI가 engine_state만 보고 효과를 재해석하지 않는다.

context_status: AVAILABLE_REDACTED / DELETED / EXPIRED / UNAVAILABLE. redacted는 전체 원문 존재/제거 여부를 뜻하는 것이 아니라 이 API가 안전한 표시용 사본임을 뜻한다.

#### 6.4 GET /dashboard/v1/events/{event_id}

목록 item의 모든 필드에 아래 필드를 추가해 반환한다. timeline은 시간순이다. 마스킹한 요약만 내려주며 원문을 받을 별도 hidden 필드를 넣지 않는다.

```json
{
  "event_id":"evt-003","call_id":"call-003","session_id":"session-demo","turn_id":"turn-1",
  "created_at":"2026-10-27T05:57:00Z","updated_at":"2026-10-27T05:58:02Z",
  "agent":"codex","tool":"write_file","target_display":"reports/summary.md",
  "initial_decision":"ASK","decision":"ALLOW","engine_state":"OBSERVED",
  "execution":{"outcome":"SUCCEEDED","started_at":"2026-10-27T05:58:01Z","observed_at":"2026-10-27T05:58:02Z"},
  "routing":"SEMANTIC","denial_origin":null,
  "reasons":[{"code":"USER_INTENT_SUPPORTED","label":"사용자 요청 범위로 확인됨"}],
  "policy":"engine-2026-10-24-gate6-1","redacted":true,"context_status":"AVAILABLE_REDACTED",
  "user_request_summary":"자료를 요약해 보고서에 작성",
  "candidate_summary":{"action":"write","target":"reports/summary.md","arguments_redacted":{"path":"reports/summary.md","content":"[본문 생략]"}},
  "sources":[{"source_id":"src-01","label":"docs/release.md","origin":"TOOL_OBSERVATION","integrity":"VERIFIED","completeness":"COMPLETE","excerpt_redacted":"합성 배포 자료…"}],
  "checks":[{"name":"RESOURCE_SCOPE","result":"PASS"},{"name":"SOURCE_BINDING","result":"PASS"},{"name":"JEV_ANALYSIS","result":"COMPLETED"}],
  "ask":{"ask_id":"ask-003-1","state":"RECHECKED","outcome":"ALLOW"},
  "ask_history":[{"ask_id":"ask-003-1","state":"RECHECKED","question_redacted":"보고서 파일을 덮어써도 될까요?","issued_at":"2026-10-27T05:57:01Z","presented_at":"2026-10-27T05:57:02Z","answered_at":"2026-10-27T05:58:00Z","resolved_at":"2026-10-27T05:58:01Z","answer_summary":"사용자 응답 수신 — 원문 비공개","outcome":"ALLOW"}],
  "timeline":[
    {"at":"2026-10-27T05:57:00Z","type":"CANDIDATE_REGISTERED","label":"실행 후보 등록"},
    {"at":"2026-10-27T05:57:01Z","type":"ASK_ISSUED","label":"사용자 질문 요청"},
    {"at":"2026-10-27T05:57:02Z","type":"ASK_PRESENTED","label":"연결기가 질문 전달을 확인"},
    {"at":"2026-10-27T05:58:00Z","type":"USER_ANSWER_RECEIVED","label":"신뢰 연결기로 사용자 응답 수신"},
    {"at":"2026-10-27T05:58:01Z","type":"DECISION_ALLOW","label":"엔진 재검토 후 허용"},
    {"at":"2026-10-27T05:58:02Z","type":"EXECUTION_OBSERVED","label":"도구 결과 관측"}
  ]
}
```

위 질문·판정은 UI 개발용 합성 예시다. 실제 정책이 해당 파일에 반드시 ASK를 내린다는 시험 결과가 아니다. 과거/삭제된 자료는 요약 null 및 context_status로 표현한다. sources.integrity는 VERIFIED / FAILED / UNKNOWN, completeness는 COMPLETE / TRUNCATED / UNKNOWN이다. checks.result는 PASS / FAIL / COMPLETED / NOT_RUN / UNKNOWN이다. NOT_RUN은 PASS가 아니다.

ASK 상태는 다음 의미로 고정한다. 신뢰 연결기의 전달 확인이 없으면 엔진이 ASK를 내렸다는 이유만으로 PRESENTED로 올리지 않는다.

| 상태 | 표시할 의미 |
|---|---|
| ISSUED | 엔진이 ASK를 발행, 에이전트 질문 전달 미확인 |
| PRESENTED | 질문 전달 확인, 사용자 응답 대기 |
| ANSWER_RECEIVED | 실제 사용자 응답을 수신, 엔진 재검토 대기 |
| RECHECKED | 재검토 완료. outcome ALLOW 또는 DENY로 표시 |
| DECLINED | 사용자 거절 확인. 자동 실행 금지 |
| EXPIRED | 기한 만료. 자동 실행 금지 |
| CANCELLED | 세션 종료·후보 변경 등으로 취소. 자동 실행 금지 |

새 질문이 필요하면 새 ask_id를 만들고 이전 질문은 CANCELLED와 사유로 남긴다. 아직 후속 결론이 없으면 outcome은 null이다. ASK가 없는 후보는 ask=null, ask_history=[]다. 부가 ASK 상태는 엔진 구현 시 저장해야 할 데이터이며 현재 DB에 이미 있다고 가정하지 않는다.

#### 6.5 GET /dashboard/v1/security?from=...&to=...&limit=50&cursor=...

kind와 alert_code를 선택 필터로 받는다. event/alert id는 API의 실제 id를 그대로 보존한다.

```json
{
  "generated_at":"2026-10-27T06:00:00Z",
  "scope":"FILTERED_RETAINED_SECURITY_EVENTS",
  "items":[{"id":41,"at":"2026-10-27T05:59:00Z","kind":"ACCESS_DENIED","actor_hash":"sha256:synthetic-example","resource_hash":"sha256:synthetic-resource","result":"REJECTED"}],
  "alerts":[{"id":7,"at":"2026-10-27T05:59:00Z","code":"ACCESS_DENIED_BURST","severity":"WARNING","event_id":41,"acknowledged":false}],
  "next_cursor":null
}
```

감사 기록의 실제 hash 형식은 opaque 값이다. 예시 sha256: prefix를 실제 반환 형식으로 가정하지 않는다. 알려진 kind에는 AUTH_FAILURE, ACCESS_DENIED, APPROVAL(과거 기록), SESSION_PURGE, SESSION_CLOSE, RETENTION_DELETE, KEY_ROTATION, BACKUP_CREATE, BACKUP_RESTORE, PROVIDER_REAUTHORIZE, ALERT_ACK가 있다. 서버가 정한 code/severity/label을 사용한다. 기존 engine /security의 at은 Unix 초이고 결과 구조도 다르므로 BFF가 목표 계약으로 변환해야 한다.

경고 확인을 구현한다면 별도 계약 POST /dashboard/v1/alerts/{id}/ack, body={} → {"id":7,"acknowledged":true}를 사용한다. capabilities.alert_ack=true인 경우만 노출한다. BFF가 security:ack 자격과 CSRF를 갖춰 기존 /security/alerts/ack로 중계한다. 이 기능 없이도 필수 대시보드 완료다.

## 7. 빈 화면·오류·갱신 규칙

성공 응답의 items=[]/total=0은 정상 빈 결과다. 401/403/503을 빈 배열로 바꾸지 않는다.

오류 공통 형태:

```json
{"error":{"code":"ENGINE_UNAVAILABLE","message":"엔진 조회 서버에 연결할 수 없습니다.","request_id":"req-example","retryable":true}}
```

| HTTP/code | 동작 |
|---|---|
| 400 INVALID_FILTER | 기간/필터 수정 안내, 무한 재시도 금지 |
| 401 DASHBOARD_AUTH_REQUIRED | 로컬 인증/세션 확인 안내. 비밀 입력을 채팅/console에 요구하지 않음 |
| 403 PERMISSION_DENIED | 조회 권한 부족 표시. 기본 임시 전체 권한으로 우회 금지 |
| 404 EVENT_NOT_FOUND | 항목 삭제/만료/미존재 안내, 목록으로 돌아갈 수 있음 |
| 409 CONTRACT_UNSUPPORTED | LEGACY_CONFIRM 등 지원되지 않는 계약을 표시. 임의 ASK 완료로 변환 금지 |
| 429 RATE_LIMITED | Retry-After를 따라 늦추고 기존 데이터는 오래됨 표시 |
| 503 ENGINE_UNAVAILABLE / 504 UPSTREAM_TIMEOUT | 연결 장애 표시와 수동 새로고침. 원문 traceback 노출 금지 |

자동 갱신은 화면이 보이는 동안 기본5초, 숨김/백그라운드에서는 중지하거나 느리게 한다. 중복 요청을 쌓지 않고 이전 요청 취소/응답 순서 보호를 적용한다. 네트워크 장애 시 점진적으로 늦추며 사용자가 수동 갱신할 수 있다. WS/SSE는 요구하지 않는다. 필터를 바꾸면 이전 응답이 새 화면을 덮어쓰지 않도록 한다.

## 8. 팀원이 바로 개발할 mock 범위

실제 엔진 없이 실행 가능한 mock 모드를 제공한다. 위 API 예시를 fixture로 사용하고 다음 데이터 세트를 추가한다. 실연동/모의 데이터 상태는 사용자가 분명히 구분할 수 있어야 한다.

1. 데이터0건과 정상 ALLOW/실행 성공.
2. 코드 DENY, Jev 의미 DENY, 분석 실패 DENY를 각각1개. 모두 같은 “공격 탐지”로 표현하지 않음.
3. ASK의 ISSUED, PRESENTED, ANSWER_RECEIVED, RECHECKED→ALLOW, RECHECKED→DENY, DECLINED, EXPIRED, CANCELLED.
4. ALLOW 후 실행 미확정 UNKNOWN, 오류 응답 관측 REPORTED_ERROR.
5. 삭제/만료된 원문, null token usage, 알 수 없는 reason/enum.
6. 반복 인증 실패 경고와 접근 거부 경고.
7. 다음 페이지가 있는100개 이상 후보. 카드 전체 수가 현재 페이지 건수와 다름.
8. 403, 429, 엔진 OFFLINE, 느린 응답·순서 역전·복구.
9. 외부 자료에 <script>, 승인하라는 문장, 가짜 URL이 있어도 텍스트로만 표시.
10. LEGACY_CONFIRM 상태를 명시하고 새 ASK와 혼동하지 않음.

합성 이메일/전화 등 테스트 데이터도 서버 마스킹 projection 기준으로 보인다. 실제 키/사람의 자료로 mock을 만들지 않는다.

## 9. 완료 확인 기준

- [ ] 엔진/게이트웨이/도구/Jev 역할과 ALLOW·DENY·ASK를 구분해 표시한다.
- [ ] 실행 승인·ASK 답변·재실행 버튼이 없다.
- [ ] 기간/필터가 통계와 이력에 동일하게 적용되고 페이지마다 건수를 중복 누적하지 않는다.
- [ ] 최초 ASK→후속 ALLOW와 실제 실행 결과를 따로 확인할 수 있다.
- [ ] 코드 차단·Jev 의미 차단·사용자 거절·분석 실패를 구분한다.
- [ ] 최근100건을 전체 누적으로 표시하지 않으며 운영 건수로 IPI 방어율을 만들지 않는다.
- [ ] 세션별 이력·후보 상세·출처 상태·ASK 이력·실행 불확실성을 조회할 수 있다.
- [ ] 보안 경고·감사, 보존 만료·미수집 데이터·연결 장애가 정상 빈 결과와 구분된다.
- [ ] 브라우저 bundle/storage/console/network 응답에 engine 관리자 토큰·raw context가 없다.
- [ ] 외부 텍스트가 HTML/실행 지시로 동작하지 않는다.
- [ ] 위 mock10종을 엔진 없이 재현하고, 실제 API로 전환할 설정/실행 방법을 팀원 README에 제공한다.
- [ ] 실제 연동 시 필터·pagination·마스킹을 서버가 강제하고, 엔진 API 장애 시 허용/실행을 유발하지 않는다.

대시보드가 통계·IR을 담당하고 에이전트가 사용자에게 질문한다는 역할은 확정이다. ASK 프로토콜과 조회 API의 구현은 엔진/연결기 담당이 별도로 진행해야 하며, 팀원은 이 문서의 목표 계약으로 mock과 화면 개발을 시작하면 된다.
