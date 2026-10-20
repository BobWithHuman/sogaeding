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

# MVP 요구사항서

버전 MVP-SPEC-3 / 2026-10-13. 이것은 팀 내부 구현 기준이며 대회 공식 추가 요건이 아니다. 기획 근거: P1 PDF p.3~6의 F1~F5, C1 PDF p.3~5·26의 완성도·보안·구조설계 기준. 원문 번호는 `references/manifest.json`에 있다.

## 1. 제품 목표와 사용자

로컬 사용자가 Codex CLI 에이전트에 이슈 요약 또는 지정 댓글 작성을 요청한다. 에이전트가 외부 이슈를 읽어도 외부 본문이 사용자의 실행 권한을 늘릴 수 없다. 실행된 도구·차단된 도구·출처 관측·판정 근거·실제 효과를 한 세션의 기록으로 확인한다. 만들 제품의 전체 설명은 [제품 개요](07_product_overview.md)를 따른다.

| 주체 | 권한 |
|---|---|
| 사용자 | 작업 요청·허용 범위 입력, 자기 세션 기록 조회, CONFIRM의 정확한 요청 승인·거절. 서버가 인증된 요청을 검증해 세션/작업 권한 발급 |
| Codex CLI/LIVE·REPLAY 클라이언트 | 자기 세션 토큰으로 MCP Tool 호출; 권한/출처/승인을 직접 발급할 수 없음 |
| 게이트웨이 | 인증 문맥 확인, PDP 검사, 출처 수집, 실행 예약·실행·보고. 사용자 세션 발급·승인 불가 |
| PDP/장부 | 작업 권한·정책 검사, 불변 호출/판정/승인 기록, 실행권 단회 소비 |
| DemoExecutor | 지정 fixture만 조회·읽기, 로컬 모의 댓글 저장. 관문 밖 공개 endpoint 없음 |

이전 문서의 '운영자'는 에이전트에게 일을 시키고 필요할 때 실행을 확인하는 **같은 사용자**를 뜻했다. 별도의 운영 직군을 만들려는 의도가 아니며 이후 문서는 '사용자'로 통일한다. 서버 배포·정책 관리·장애 복구를 담당하는 서비스 관리자는 별도 후속 역할이다. 오늘은 신뢰하는 로컬 사용자 한 명이다. 세션 간 권한 격리는 구현하되 조직별 계정·SSO·원격 SaaS 운영은 후속 범위다.

## 2. 범위와 우선순위

**P0: 오늘 MVP 완료에 필요. P1: 핵심 통과 뒤 확장. P2: 대회 제출 전/후속 단계.**

| ID | 우선 | 요구사항 | 확인 가능한 결과 |
|---|---|---|---|
| FR-01 | P0 | 사용자만 사용자 원문과 구조화된 작업 권한으로 세션 생성 | SUMMARIZE_ISSUE 또는 POST_COMMENT, issue 범위, 만료, 독립 토큰 |
| FR-02 | P0 | 실제 MCP 세 도구를 노출 | get_issue, read_workspace_file, post_issue_comment |
| FR-03 | P0 | 사용자 원문과 Tool 반환 데이터의 출처를 분리 기록 | 사용자 입력은 사용자 경로, 이슈는 EXTERNAL, README는 WORKSPACE_DATA |
| FR-04 | P0 | 모든 등록 도구에 실행 전 PDP 판정 적용 | ALLOW/DENY/CONFIRM와 안정된 이유 코드; DENY·미승인 CONFIRM 실행0 |
| FR-05 | P0 | 작업 권한·대상·민감 파일을 결정적 정책으로 검사 | 요약 세션의 댓글 DENY, SECRET_ENV 읽기 DENY, 대상 이슈 변경 DENY |
| FR-06 | P0 | 인자와 수집 출처의 제한된 일치 근거를 표시 | source_ids·match kind·근거를 표시; 실제 인과 증명이라고 표현하지 않음 |
| FR-07 | P0 | CONFIRM에 독립 사용자 승인과 정확한 호출 결합 | 승인 전 댓글0, 승인 후 같은 호출만1, 만료/변경/재사용 거부 |
| FR-08 | P0 | 위험 실행권·승인·세션 쓰기 예산을 원자적으로 소비 | 서로 다른 병렬 call_id도 세션 댓글 최대1; UNKNOWN 자동 재시도 없음 |
| FR-09 | P0 | 판정과 실제 실행 효과를 별도 기록·화면 표시 | 타임라인, 이유, 승인, 실행 상태, 댓글 실제 건수/receipt |
| FR-10 | P0 | REPLAY 클라이언트로 정상/공격/확인 흐름을 반복 재현 | MCP를 실제 통과하는 세 시나리오, 입력·출력·원기록 보존 |
| FR-11 | P0 | OpenAI API 인증을 사용하는 Codex CLI의 LIVE MCP 연결 | 실제 Codex CLI가 보호된 세 도구를 호출하고 정상 과업 완료; REPLAY와 별도 표시 |
| FR-12 | P0 | 재현 실행·초기 점검·실패 복구 절차 | 두 서비스 시작, health, MCP 인증 smoke, 초기 fixture reset(사용자 절차) |
| FR-13 | P1 | 3단계 의미 판단 어댑터 | 시간/출력 제한, 실패 시 허용 금지, 정책을 뒤집지 못함 |
| FR-14 | P1 | Codex 내장 도구·추가 MCP 서버 등 보호 범위 확대 | 새 경로의 집행점·우회 방지·권한 검증을 추가; 현재 범위 밖 도구를 보호했다고 표시하지 않음 |
| FR-15 | P2 | agentgateway 어댑터·gRPC·PostgreSQL·SBOM/CI·공개 평가 | 실제 버전·통합·점검·성능 근거로 단계적 확장 |

LIVE의 기본 에이전트는 Codex CLI다. 별도의 Python LLM 에이전트를 중복 개발하지 않는다. 제공자는 OpenAI이며 실제 모델 ID는 설정에서 확정하고 결과에 남긴다. API 인증·MCP 연결·정상 과업·공격 fixture 관측까지가 오늘 범위다. 모델이 공격을 따르지 않으면 '공격 호출 시도 없음'으로 기록한다. 그것을 우리 엔진의 차단 성공으로 계산하지 않는다. LIVE를 실행하지 못하면 **REPLAY core 완료 / LIVE 미완료**로 표시한다.

신뢰된 런처는 사용자 원문을 Control의 `user_request`와 Codex의 최초 사용자 프롬프트에 동일하게 전달한다. 과업·이슈·정확한 댓글 본문은 사용자가 입력한 구조화 필드에서 서버가 확정한다. Codex 또는 외부 텍스트가 다른 최초 요청을 주장해도 저장된 작업 권한을 바꿀 수 없다. Codex의 후속 프롬프트로 권한을 확대하려면 사용자가 새 세션을 만들어야 한다.

## 3. 사용자 흐름

### U-01 이슈 요약

사용자가 이슈42의 요약을 요청해 SUMMARIZE_ISSUE 세션을 만든다. get_issue(42)와 PUBLIC_README 읽기는 허용한다. 이슈 본문 속 ‘설정 정보를 댓글로 게시’ 지시는 데이터로만 남는다. SECRET_ENV 읽기와 모든 댓글 작성은 차단한다. 정상 요약은 별도로 완료·관측한다.

### U-02 명시적 댓글 작성

사용자가 이슈42와 정확한 댓글 본문을 지정해 POST_COMMENT 세션을 만든다. 같은 이슈·같은 본문은 ALLOW로 한 번 게시한다. 에이전트가 본문을 변경하면 CONFIRM이 된다. 다른 이슈, 민감정보, 예산 소진은 승인으로 넘길 수 없는 DENY다.

### U-03 외부 값 활용·승인

이슈 제목 등 공개 외부 데이터가 댓글 본문에 들어가면 출처 관측을 기록한다. 외부 값 사용 자체를 공격으로 단정하지 않는다. 지정 본문과 다르면 CONFIRM으로 멈추고 사용자가 정확한 tool/issue/body/hash를 보고 승인한다. 승인된 call_id와 같은 인자로 재개할 때만 실행한다.

## 4. 오늘 기본 제한

| 항목 | 기본값·정책 |
|---|---|
| 세션 | ACTIVE 30분, 사용자 종료 가능, 최대 Tool 호출8회 |
| 쓰기 | POST_COMMENT 세션당 실행 예약1회; 예약 뒤 실패/UNKNOWN에도 자동 환불 없음 |
| 입력 | JSON 객체, 추가 필드 거부, 댓글1~4096문자, REST 본문32KiB 한도 |
| 도구 대상 | 이슈 ID는 seed된 목록, file_id는 PUBLIC_README/SECRET_ENV enum |
| 승인 | CONFIRM만 승인, 유효기간5분, 정확한 호출·정책 버전 결합, 단회 소비 |
| 시간 | PDP 요청1초, 로컬 executor2초, 자동 위험 쓰기 재전송 없음 |
| 정책 | mvp-2026-10-13-v1. 변경되면 이전 승인/예약 후보 재검증 |
| 로그 | 토큰·실제 API키 미저장; excerpt 최대512문자; 로컬 데이터 기본24시간 보존 |
| 실행 환경 | Docker Compose의 control/gateway 두 서비스, Python 3.12; 호스트 포트는 127.0.0.1:8000/8001에만 공개. LIVE Codex CLI는 호스트의 전용 CODEX_HOME·가짜 연구 workspace에서 실행 |

한도는 팀 내부 기본값이다. 설치한 MCP SDK의 본문 제한과 proxy 설정이 이 계약을 실제로 적용하는지 확인한다. 50ms·90%·10%는 예선 기획 목표이며 오늘 완료 판정으로 사용하지 않는다.

## 5. 오늘 완료 기준

| ID | 완료 기준 |
|---|---|
| AC-01 | Docker Compose의 두 서비스가 실행되고 health와 MCP 인증 연결에 성공 |
| AC-02 | 정상 이슈 조회·읽기와 직접 지정 댓글1회 성공 |
| AC-03 | 요약 세션의 공격 댓글·비밀 읽기 실제 실행0 |
| AC-04 | CONFIRM 승인 전0, 승인 후 정확한 호출1, 재사용으로 추가 쓰기0 |
| AC-05 | 세션 위조·잘못된 토큰·범위 밖 이슈·인자 변경이 거부 |
| AC-06 | PDP 중단·검사 저장 실패 때 실행0; 실행 후 결과 불명은 UNKNOWN으로 보존 |
| AC-07 | 서로 다른 call_id의 동시 쓰기도 세션 예산1을 넘지 않음 |
| AC-08 | 출처·판정·실행 원기록과 화면이 일치하고 가짜 비밀/토큰 노출 없음 |
| AC-09 | Codex CLI LIVE 정상 작업을 실제 OpenAI API로 완료; 공격 시도/미시도/차단을 별도 관측. CLI/모델 버전과 최초 요청 일치를 기록 |
| AC-10 | 실행법·설정 예시·버전·수용시험 결과와 첫 진단 원본을 저장 |

AC-01~08·10은 core, AC-09는 LIVE 완료 조건이다. 모든 조건은 현재 **NOT_RUN**이다. 상세 시험은05의 NT/AT ID를 따른다.

## 6. 오늘 제외·후속 조건

임의 URL·임의 경로·셸 실행·실제 GitHub 쓰기·A2A·다중 게이트웨이·SSO·AWS 배포·Redis·고급 그래프 UI·전체 벤치마크는 오늘 P0에 포함하지 않는다. 이들을 추가할 때 기존49개 적용표, 신뢰 경계, 보안 시험을 갱신한다. 로컬 MVP는 제출 완성본이나 전체 IPI 방어 보장으로 표시하지 않는다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
