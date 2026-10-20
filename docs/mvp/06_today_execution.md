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

# 오늘 MVP 착수·실행표

기준일: 2026-10-13, Asia/Seoul. 문서 버전: MVP-SPEC-3. 이 문서는 오늘 빠르게 구현을 시작하기 위한 내부 실행 기준이다. 대회가 요구한 별도 제출 양식은 아니다. **Docker 엔진 연결, 저장소 연결, 개발 harness 준비와 제품 구현 완료는 구분한다.** 실제 제품·MCP·LIVE 연결은 미실행이며 **제품 수용시험 18개(NT-01~03 정상 3개 + AT-01~15 보안 15개)는 모두 NOT_RUN**이다.

> 운영 계획은 [PLAN-2 1인 오늘 계획](../plans/02_today_mvp.md)이 정본이다. 아래 환경·런처 기록은 기존 SPEC-2 사실이며 T-S01 보호 전송 준비와 실제 제품 TLS 검증을 거친 뒤 연결한다. 개발 사람 담당자는 사용자 1명이며 이전 팀 병렬 시간표는 폐기했다.

## 1. 개발 전 남은 최소 작업

| 순서 | 작업 | 완료 증거 | 현재 의미 |
|---|---|---|---|
| 1 | 제품 범위·Codex 연결·사용자 권한 계약 고정 | 01~03과 제품 개요 | 문서화. 추가 승인 회의 없이 기본안으로 착수 |
| 2 | 정상·공격·사용자 명시 허용 가짜 데이터 준비 | fixture ID·기대 판정·실제 효과 기대값 | 제품 시험 데이터 구현 필요 |
| 3 | Compose 개발 환경 확인 후 첫 제품 서비스 구현 | 정적 설정 검사·build·health·버전 | 개발 컨테이너 build·기동·검사 PASS. 제품 health는 구현 후 확인 |
| 4 | 도구 한 개의 MCP→PDP→private 실행 연결 | 정상 실행 1회·거부 실행 0회 | 아직 제품 구현·연결 시험 필요 |
| 5 | Codex LIVE 최초 요청·인증·모델·보호 MCP 검증 | 동일 user_request, CLI·모델 ID, 정상 요약·실제 도구 이력 | 전용 설정·DryRun은 준비 검사. 실제 API 작업은 별도 실행 |

먼저 ADR-S01/T-S01의 TLS·신뢰 구성과 T-02 준비를 거쳐 첫 수직 경로를 구현한다. 연결이 막히면 고급 UI·다중 에이전트 개발을 늘리기 전에 경로를 해결한다. 추가 미션·공식 제출 양식은 미공개이며 오늘 핵심 구현의 선행조건이 아니다.

제품 기본안은 **Docker Compose의 control/gateway 두 서비스**다. FastAPI 제어 API·PDP·SQLite·최소 HTML은 호스트 `127.0.0.1:8000`, Python MCP SDK gateway는 `127.0.0.1:8001/mcp`에 공개한다. 컨테이너 안의 서버는 `0.0.0.0`에 바인딩하고 SPEC-3의 Gateway 내부 주소는 `https://control:8443`이며 서버 CA 검증·클라이언트 인증서를 요구한다. 이 주소는 현재 개정된 전송 기준이고, 당시 SPEC-2 환경 확인 실적과 구별한다. Gateway의 private DemoExecutor만 가짜 이슈·파일 조회와 로컬 댓글 실행을 수행한다. `get_issue`, `read_workspace_file`, `post_issue_comment` 세 도구만 P0다.

개발 Compose 서비스는 코드를 작성·검증하는 환경이다. control/gateway 제품 profile은 실제 앱 소스가 생긴 뒤 사용한다. 개발 컨테이너를 띄웠다는 이유로 제품 API가 기동했다고 기록하지 않는다.

## 2. 확인된 환경과 변경 사항

아래 설치·엔진 연결 확인은 제품 통합 확인이 아니다. API 키 값은 읽거나 문서에 기록하지 않는다.

| 항목 | 확인 사실 | 다음 검증 |
|---|---|---|
| 프로젝트 저장소 | `C:\sogaeding`에 Git main을 초기화했고 origin은 [with-human](https://github.com/gu1trh2ro/with-human). GitHub 인증으로 비공개·빈 원격 저장소 접근 확인. push는 하지 않음 | 문서·harness 기준선과 이후 실제 구현 변경을 commit. push는 필요할 때 수행 |
| Docker | Server 29.6.1, Docker Desktop 4.81.0, Compose 5.2.0. 개발 이미지 build·dev 서비스 기동 확인 | 구현 후 control/gateway 제품 health |
| Codex CLI | 0.154.0 설치 확인 | 전용 CODEX_HOME·MCP bearer·OpenAI 인증·선택 모델·정상 LIVE 작업 |
| Python·의존성 | Python 3.12 공식 이미지 digest 고정, 실제 컨테이너 Python 3.12.15·uid 10001. requirements-dev.lock의 해시 기반 설치, mcp 2.3.0 포함·pip check 통과 | 제품의 실제 MCP 인증·Tool 처리 API 확인 |
| OpenAI API | 사용자가 GPT API 키 보유를 알림. 키 값·잔액·모델 접근은 확인하지 않음 | `OPENAI_API_KEY`를 호스트 Codex에 주입. 명시적 LIVE 실행에서 인증·모델 접근 검증 |
| 제품 API·MCP | 명세·입력 스키마 있음. 실제 control/gateway 제품 통합은 미실행 | 인증 smoke·도구 list/call·reserve·effects·report·동시성 수용시험 |
| 개발 검사 | JSON/OpenAPI 계약 예시 12개, harness pytest 1개, Ruff·Bandit·pip check 통과. dependency audit에서 확인 시점 알려진 취약점 없음 | 이 검사는 실제 제품 보안·MCP·LIVE 수용시험을 대체하지 않음 |
| 개발 harness | 저장소 지침·작업 기록·검사·실행 구성 | [harness 안내](../../harness/README.md)와 실행 스크립트의 실제 결과 참조 |

이전 SPEC-1의 'Docker named pipe 부재'와 native 가상환경 기본안은 현재 Docker 준비 상태로 대체했다. 이전 오류를 현재 블로커로 계속 취급하지 않는다. [Dockerfile.dev](../../Dockerfile.dev)에 이미지 digest, [requirements-dev.lock](../../requirements-dev.lock)에 실제 고정 패키지·해시가 있다. bundled Python 환경을 제품 의존성 설치 대상으로 변경하지 않는다.

개발 환경 실행은 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev_docker.ps1 -Mode up`, 검사는 같은 스크립트의 `-Mode check`다. `-Mode app`은 현재 제품 소스가 없으면 분명한 오류로 종료하며, 소스 구현 뒤 서로 다른 HUMAN_USER_TOKEN·GATEWAY_SERVICE_TOKEN을 설정해 사용한다. app profile의 준비와 제품 API 기동 성공을 구분한다.

로컬 증거는 [개발 환경 확인](../../artifacts/dev-setup/verification-2026-10-13.json)과 [의존성 audit 결과](../../artifacts/dev-setup/pip-audit-2026-10-13.json)에 있다. artifacts는 Git에서 제외하므로 다른 checkout에서는 검사 재실행으로 증거를 생성한다. T-00의 환경 게이트에 제품 src·health를 요구하지 않으며 실제 제품 health는 T-01 이후 확인한다.

## 3. Codex CLI LIVE 연결 원칙

설정 템플릿은 [product.config.toml.template](../../harness/codex/product.config.toml.template), 실행 진입점은 [run_codex_live.ps1](../../scripts/run_codex_live.ps1)다. 스크립트의 `-DryRun`은 전용 설정·가짜 workspace·요청 일치 등을 점검하고 실제 API 작업을 시작하지 않는다. `-Run`이 실제 LIVE 실행이다. script help와 실제 구현을 기준으로 인자를 확인한다.

실제 LIVE의 raw JSONL·도구 원문·오류 출력은 보관하지 않는다. 최종 `agent_message`만 알려진 자격증명·가짜 비밀 sentinel을 마스킹하고 8192자로 제한해 증거에 남긴다. `FAIL`은 CLI 비정상 종료·timeout·turn 실패이며 안전한 증거를 저장한 뒤 스크립트도 실패로 종료한다. `UNVERIFIED`는 프로세스 결과만 기록한 상태이고 제품 성공이 아니다. `final_task_status=NEEDS_REVIEW`는 마스킹한 최종 답변·Control 타임라인·executor 효과를 함께 검토해야 한다는 뜻이다. 이 마스킹은 모든 민감정보 탐지를 보장하지 않는다.

유료 API 없이 런처 설정·입력·출력 추출을 검사하는 명령은 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_codex_launcher.ps1`이다. [native stdin 검사](../../scripts/check_codex_stdin.ps1)는 같은 명령 형식으로 실행하며 실제 런처 함수를 로컬 Python에 연결해 한국어·여러줄의 UTF-8 바이트, 사용자/서비스 자격증명 환경 분리, 비정상 exit와 timeout 관측 3개를 PASS로 확인했다. [stdin 검사 증거](../../artifacts/codex-launcher/stdin-checks.json)는 이 native pipe 검사 결과이며 실제 제품 AT-15·OpenAI API·MCP 연결은 계속 NOT_RUN이다. 전체 런처 검사는 [check_codex_launcher.ps1](../../scripts/check_codex_launcher.ps1)와 [런처 출력 추출기](../../scripts/codex_trial_output.ps1)를 따른다.

1. 작업을 요청하는 같은 사용자가 세션을 만든다. 런처가 사용자 원문을 Control의 `user_request`와 Codex 최초 프롬프트에 동일 전달한다.
2. Codex의 CODEX_HOME과 연구 workspace를 일반 개발 환경에서 분리한다. 연구 workspace에는 가짜 파일만 놓고 프로젝트 `.env`·DB·실제 자격증명을 mount하지 않는다.
3. 연구 Codex의 shell tool·불필요한 웹 검색을 끄고 read-only sandbox를 사용하며 등록한 보호 MCP 세 도구만 연결한다. 이 설정을 OS 전체 격리나 모든 내장 도구에 대한 PDP 집행이라고 설명하지 않는다.
4. 사용자 API token·Gateway service token은 Codex에 주지 않는다. 자기 세션의 MCP token을 환경변수 기반 헤더로 전달하고 모델 프롬프트에는 넣지 않는다. OpenAI API 키는 호스트 인증용이다.
5. raw trial 로그는 기본 영구 저장하지 않는다. 세션·정책·fixture·CLI/모델 버전·판정·실제 효과 등 안전한 메타데이터와 마스킹한 증거를 보관한다.

Codex CLI LIVE가 오늘 기본 에이전트이므로 별도 Python LLM 도구호출 에이전트는 만들지 않는다. REPLAY runner는 고정 후보를 실제 MCP로 보내 통제 경로를 반복 검증한다. PDP의 OpenAI 의미 판정 judge는 후속 P1·기본 OFF다.

## 4. 작업 순서·담당

개발·통합 사람 담당은 사용자 1명이다. 하나의 개발 세션에서 아래 순서로 진행하고, 별도 AI 검토의 재현은 구현 변경을 멈춘 같은 버전을 기준으로 한다. 추가 팀원의 개발 시간이나 여러 세션을 동시에 운영하는 시간을 전제하지 않는다.

| 순서 | 단계 | 종료 증거 |
|---|---|---|
| 1 | 보안 요구·위험/외부 인터페이스·코딩 표준, T-S01 보호 전송 준비와 T-02 | 필요한 설계 기록, TLS 준비/인증·DB 단위 결과. 제품 전체 통과와 구별 |
| 2 | T-01 실제 MCP 연결→T-03 정책→T-04 reserve/private executor | 인증·전송 검증, 정상 효과와 DENY 실행0·장애 처리 |
| 3 | T-05/06 출처·승인→T-07 최소 화면→T-08 core 시험 | 승인 단회·경쟁·UNKNOWN·비밀/HTML 안전, 실제 18개 중 해당 시험 결과 |
| 4 | T-09 짧은 Codex LIVE→T-10 통합 검토 | 정확한 모델·MCP·정상 출력·위험 호출 시도/미시도·효과. core/LIVE 분리 |
| 매 단계 | 정적/수동/동적 진단, 최초 빌드 SBOM/SCA, 발견/조치/재진단 | 원본 보존, SECURITY_DESIGN·GUIDE_APPLICABILITY·FINDINGS와 실제 증거 연결 |

AI 보조를 쓰면 비중복 파일만 배정한다. DB 전이·공통 설정은 한 작성자가 통합한다. 최종 전역 상태는 관리 세션이 실제 RESULT/REVIEW를 확인해 갱신한다.

## 5. 오늘 시간 예산과 인계

기본은 사용자 집중 작업 **6~8시간**의 예상 예산이다. 세부 시간과 중간 게이트는 [오늘 계획](../plans/02_today_mvp.md)을 따른다. 오늘 안전한 실제 연결부터 확보하고 여유가 있으면 후속 구현을 계속한다. 전체 MVP·보안/LIVE 검증이 남으면 10/14~16에 이어가며, 날짜만으로 완료를 선언하지 않는다.

실측 시간이 부족하면 고급 UI·새 어댑터·큰 평가셋을 보류한다. TLS·인증·인가·단회 승인·원자 예약·중요정보 보호·필수 검증은 완료 조건에서 삭제하지 않는다. 인계에는 실제 PASS/FAIL/NOT_RUN과 다음 작업을 남긴다. 아래 완료 조건은 안전한 작은 연결의 성과보다 넓은 전체 MVP 조건이다.

## 6. 완료를 선언할 증거

- 사용자 권한 안의 정상 작업은 완료하고, 외부 지시로 추가된 위험 도구 실행은 실제로 0회다.
- CONFIRM 전 댓글 0, 정확한 사용자 승인 후 1, 만료·인자 변경·재사용·병렬 요청으로 추가 쓰기 0이다.
- PDP/필수 저장 장애는 실행 전 중단한다. 실행 후 결과 손실은 UNKNOWN으로 보존하고 효과를 대조한다.
- 이력·화면·API·보관 파일에 가짜 비밀·토큰 원문이 없고 외부 HTML이 실행되지 않는다.
- 새 실행에서 문서 명령으로 같은 fixture를 재현한다. 새 PC 재현이 미검증이면 그 범위를 명시한다.
- 실제 모델이 위험 호출을 시도하지 않았다면 '미시도'로 남긴다. REPLAY와 LIVE, 예정 목표와 실측을 섞지 않는다.

대회 차단율 90%·과차단율 10%·판정 50ms는 원팀 기획의 목표다. 오늘 고정 시나리오 몇 개의 PASS로 달성했다고 발표하지 않는다. 위 증거와 05의 P0 시험이 없으면 제품·보안 MVP 완료를 선언하지 않는다.


### ADR-S01 전송 기계 동기화 (MVP-SPEC-3)

2026-10-13 T-S01: 현재 wire는 MVP-SPEC-3, host→Control/Gateway HTTPS와 Gateway→Control https://control:8443 mTLS를 사용한다. 앱 전용 CA를 검증하며 HTTP fallback과 verify=false를 금지한다. 정책·권한·상태 의미는 유지한다. 위 준비/미실행 기록은 당시 SPEC-2 기록이며 이번 제품 시험 결과는 WP-MVP-01 RESULT에 별도로 남긴다. TLS fixture PASS와 실제 PL-SEC-TRANSPORT를 구별한다.
