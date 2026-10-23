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

# 오늘 MVP 개발의 시작점

관리 방식과 필수 보안 기준이 추가됐다. **전체 계획·오늘 세션 인계의 최신 진입점은 관리 문서와 오늘 계획**이다. 이 명세 묶음의 현재 전송/wire 기준은 MVP-SPEC-3이며 [ADR-S01](../security/decisions/ADR-S01.md)의 HTTPS·내부 mTLS로 기계 동기화했다. 전송 계약 개정은 실제 제품 검증·가이드 전수 준수 완료를 의미하지 않는다. 이 문서의 기존 미구현/미실행 상태표는 착수 전 기준선 기록이며 현재 실측은 docs/handoffs/WP-MVP-01의 RESULT/REVIEW를 따른다.

기준일: 2026-10-13(KST). 문서 버전: MVP-SPEC-3. 오늘 목표는 최대한 빠르게 작동하는 MVP를 만드는 것이다. 사용자의 추가 결정인 **Docker, Codex CLI, OpenAI API**를 반영했다. 아래는 구현 기준이며 제품 구동·수용시험 완료를 의미하지 않는다.

## 오늘 만들 결과

현재 실행 계획은 PLAN-2의 **사용자 1인 개발**이다. 아래는 완성할 MVP 범위이며 오늘은 안전한 실제 연결부터 순차 진행한다. 남은 전체 통합·검증은 10/14~16에 이어가고, 일부 연결 성공을 아래 기능 전체 완료로 표시하지 않는다. [첨부 대회 기준](../security/contest_security_criteria.md)의 49개 적용 검토·단계별 진단·재진단 증거를 함께 남긴다.

**Codex CLI가 이슈를 읽고 MCP 도구를 부르면 실행 전에 사용자 위임을 검사한다. 정상 댓글은 작성하고, 허용 범위 밖 댓글·비밀 읽기는 실행하지 않으며, 사용자는 판정과 실제 효과를 화면에서 확인한다.**

이전 문서의 '운영자'는 에이전트에게 일을 시키고 실행을 확인하는 같은 **사용자**였다. 문서와 API 인증 역할명을 사용자로 통일했다. 서비스 배포·장애 복구 담당자는 후속 역할이다. 만들 서비스의 목적과 사용자 화면은 [제품 개요](07_product_overview.md)에 설명했다.

## 바로 읽을 문서

| 순서 | 문서 | 구현에 필요한 결정 |
|---|---|---|
| 1 | [제품 개요](07_product_overview.md) | 무엇을 만드는지, 사용자 흐름, 오늘 보호 범위 |
| 2 | [요구사항서](01_requirements.md) | P0 범위와 완료 기준 |
| 3 | [구조·데이터 설계서](02_architecture_and_data.md) | Compose 두 서비스, 신뢰 경계, DB와 원자적 실행 |
| 4 | [API·상태 계약](03_api_and_state_contract.md) | 사용자·서비스·에이전트 인증, 판정·승인·실행 전이 |
| 5 | [추적표·구현 분담](04_traceability_and_work_breakdown.md) | 요구사항·시험 연결과 구현 순서 |
| 6 | [보안 요구·수용시험](05_security_and_acceptance.md) | 정상·공격·우회·동시성·장애 시험 |
| 7 | 오늘 착수·실행표 | 착수 점검·환경 상태·시간 배분 |

기계가 읽을 계약: [OpenAPI](contracts/openapi.json), [MCP 도구 스키마](contracts/tools.schema.json), [유효·무효 예시](contracts/examples.json). 충돌은 **03의 상태·권한 계약, 기계 스키마, 01의 범위** 순으로 해결하고 변경 기록을 남긴다. 구현의 자동 생성 OpenAPI와 이 계약을 비교한다.

## 고정한 구현 방향

| 항목 | 오늘 기본안 |
|---|---|
| 런타임 | Docker Compose `control`·`gateway` 두 서비스, Python 3.12, SQLite |
| 접속 | 호스트 127.0.0.1:8000 / 127.0.0.1:8001/mcp; 내부 Gateway→Control은 https://control:8443 |
| 실행기 | Gateway의 private DemoExecutor. 모의 이슈·가짜 파일·로컬 댓글만 사용 |
| 실제 에이전트 | 호스트 Codex CLI, 전용 CODEX_HOME·가짜 연구 workspace, OpenAI API 인증 |
| 실제 모델 | 설정으로 선택하고 정확한 model ID를 결과에 기록. 아직 사용자 지정 없음 |
| 재현 시험 | 실제 MCP를 통과하는 결정적 REPLAY. LIVE와 결과를 분리 |
| 사용자 인증 | HUMAN_USER_TOKEN / UserBearer. 에이전트 세션 토큰·서비스 토큰과 분리 |
| 정책 | mvp-2026-10-13-v1. 문서 개정만으로 정책 의미는 변경하지 않음 |

신뢰된 런처는 사용자 원문을 세션의 `user_request`와 Codex의 최초 프롬프트에 동일하게 전달한다. Codex에는 자기 세션 MCP 토큰만 주고 사용자·서비스 토큰은 주지 않는다. 별도의 Python LLM 에이전트를 동시에 만들지 않는다. OpenAI 의미 판정 judge는 후속 P1·기본 OFF다.

## 개발 전 최소 점검

1. 프로젝트 저장소·비밀정보 제외·작업 기록을 준비하고 현재 문서를 기준선으로 남긴다.
2. Compose 정적 검사·개발 컨테이너 환경을 확인한다. 제품 구현 후 이미지 build·두 서비스 health를 확인한다. Docker 엔진 연결과 제품 기동 성공은 다른 결과다.
3. 정상·공격 가짜 데이터를 준비하고 기대 판정과 실제 효과의 기대값을 고정한다.
4. 도구 한 개로 MCP 인증→검사→private 실행 경로를 먼저 연결한다. 정상 실행 1회와 거부 실행 0회를 확인한다.
5. Codex 전용 설정·연구 workspace·OpenAI 인증·모델 설정을 준비해 LIVE 정상 호출을 검증한다. 키 값은 문서·채팅·커밋·로그에 넣지 않는다.

별도 문서 승인 회의를 선행조건으로 만들 필요는 없다. 실제 연결에서 생기는 변경을 ADR·계약·시험에 함께 반영하며 첫 수직 경로부터 구현한다.

## 제품과 개발 harness

제품은 실행 중인 에이전트의 **등록 MCP 호출**을 검사·집행한다. 개발 harness는 개발 Codex가 저장소의 문서·작업 순서·검사 명령·증거 규칙을 지키게 하는 구성이다. 개발 지침·프롬프트·hooks는 제품의 실행 차단을 대체하지 않는다. 구성과 사용법은 개발 harness 안내를 따른다.

Codex 내장 셸·파일 도구·다른 MCP 서버·사용자 PC 전체 행동은 현재 Gateway의 보호 범위에 포함하지 않는다. 출처 일치는 인과 증명 대신 관측 근거로 표시한다. REPLAY 통과율을 실제 LLM 공격 방어율로 발표하지 않는다.

## 변경 기록과 검증 상태

| 버전 | 변경 | 근거 |
|---|---|---|
| MVP-SPEC-1 | 두 Python 프로세스, SQLite, 세 도구, LIVE/REPLAY, 단회 승인 | 초기 속도 목표와 당시 Docker 미연결 상태 |
| MVP-SPEC-2 | Docker Compose로 전환, Codex CLI·OpenAI를 LIVE 기본안으로 확정, 사용자 역할명·제품 개요·최초 요청 일치 명세 추가 | 사용자 추가 지시와 Docker·Codex 설치 재확인 |

Docker 개발 이미지 build·dev 서비스 기동, 계약 예시 12개·harness pytest 1개·Ruff·Bandit·pip check를 확인했다. 해시 기반 의존성 lock을 설치했고 확인 시점 dependency audit에 알려진 취약점이 없다. 이 결과는 제품 코드·실제 API·MCP·LIVE 보안 수용시험이 아니다. **제품 수용시험 18개(NT-01~03 정상 3개 + AT-01~15 보안 15개)는 아직 모두 NOT_RUN**이다. 정확한 실행법과 환경 구분은06을 따른다.

대회 근거와 장기 준비는 통합 분석을 따른다. 추가 미션은 미공개 상태다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
