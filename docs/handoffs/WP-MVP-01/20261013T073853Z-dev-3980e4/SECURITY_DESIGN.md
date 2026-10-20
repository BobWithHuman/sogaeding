# WP-MVP-01 보안 설계·구현 근거

run_id: 20261013T073853Z-dev-3980e4; 작성 2026-10-13T08:44:17.217434+00:00; PLAN-2, MVP-SPEC-3, policy mvp-2026-10-13-v1.
작성자/모델·DB·실행 설정 통합 소유자: 이 개발 AI 세션 1개. 사람 개발자는 사용자 1명이다.

사용자 위임, 세션 토큰, 승인, 모의 게시 저장소, 원문 digest와 이력이 자산이다. 외부 이슈·도구 인자는 불신 데이터이며 사용자/출처/승인 라벨을 발급하지 않는다. 권한은 SUMMARIZE_ISSUE 또는 POST_COMMENT와 고정 이슈·정확한 본문에서 서버가 구성한다. 실제 비밀·실제 GitHub 게시를 사용하지 않는다.

| 경계·외부 인터페이스 | 인증·허용 대상·통제 | 실패·한도 | 코드·시험 |
|---|---|---|---|
| 호스트/브라우저/런처→Control 8000 | HTTPS 앱 CA·hostname 검증; 사용자 bearer. /healthz·빈 shell·정적 JS만 공개. 내부 API 거부 | 32KiB·깊이16·중복 key/header·Origin/Host 검사; 실패 인증 제한 | control/main.py RequestGuard, scripts/create_control_session.py; 실제 TLS·AT-11/13 부분시험 |
| Codex/REPLAY→Gateway 8001/mcp | SDK2.3 opaque session bearer; scopes tools:invoke·정확한 HTTPS audience·만료; dispatch 때 resolve 재확인 | stateless MCP·32KiB; 추가 필드/타입/enum 먼저 거부 | gateway/main.py StrictServer/SessionVerifier; actual MCP expired/audience·tool-schema |
| Gateway→Control 8443 | 서버 CA/hostname 검증+mTLS client 인증+service bearer; URL 고정·redirect/proxy 상속 없음 | 요청1초·위험 쓰기 자동 재시도 없음 | gateway/client.py; TLS failure executor0 |
| Gateway→private DemoExecutor/등록 fixture | 공개 실행 API 없음; 스키마→check→reserve 성공 뒤 동일 args 사용 | executor2초·예약 시작30초; SECRET_ENV 진입0 | executor/demo.py; NT-02·AT-01/02/14 |
| 서비스→SQLite/런타임 파일 | 서비스별 volume·파일600·키 분리; 요청/정확한 인자/출처 발췌/event/댓글 Fernet 암호화; token은 secrets 생성+SHA256 검증용 digest | BEGIN IMMEDIATE·call8/write1·단회 승인; 결과 유실 UNKNOWN·budget 반환 없음 | storage/repository.py; atomic call/write race·approval race·report loss |
| Codex→OpenAI | host 환경 API키·정상 HTTPS 검증; 전용 CODEX_HOME·가짜 workspace; 사용자/서비스 토큰 child 미전달 | 정상1+공격1, gpt-5.6-luna, CLI0.154.0, rawJSONL 미보관 | run_codex_live.ps1; live-*-verified.json·실제 effects 대조 |

위협→구조적 예방→실측: SEC-01/03은 등록 file ID와 private executor 단일 경로로 경로 조작·임의 명령·비밀 읽기를 제거한다. SEC-02/04는 서버 발급 grant와 외부 출처 분리로 trusted/approved 자가 선언이 권한을 만들지 못하게 한다. SEC-05/06은 canonical UTF-8 JSON digest, 불변 call, 승인의 정확한 digest/expiry/정책 결합과 한 DB 트랜잭션의 예산/소비로 인자 교체·TOCTOU·중복 게시를 제한한다. SEC-07은 실행 전 audit/PDP 실패를 차단하고 실행 후 불명 상태를 UNKNOWN으로 보존한다. SEC-08/10은 역할·세션별 API, 비밀 마스킹, 안전한 오류, 암호화 저장, UI textContent로 이력 유출·저장형 XSS를 줄인다. 관련 실제 시험은 product-final-tests.txt와 product-traces.json에 연결한다.

코딩 표준: 입력은 checked-in JSON Schema와 strict JSON으로 검사한다. SQL 값은 parameter bind, 식별자는 고정한다. 정책에 eval/exec/shell/pickle/YAML object를 사용하지 않는다. URL/파일 경로는 도구 입력으로 받지 않는다. 난수는 secrets·검증된 cryptography API를 사용한다. httpx와 SDK httpx2 타입을 구분하고 CA 검증·timeout·context manager를 강제한다. 동적 외부 문자열은 DOM textContent, 오류는 allowlisted code만 사용한다.

원문 근거: G2 PDF15(SQL bind), 70~71(보안결정 입력); G3 PDF159~160·510(TLS), 406(TOCTOU), 511(오류/세션); G4 PDF22~24·37~39(SDLC/설계20); R1 PDF13~14(전주기), G1 PDF45~47(SBOM); C1 PDF14~15·26(정적/동적·구조예방). 원본 해시·페이지 재추출은 guide-original-read.json과 guide-pages/이다. 전체 가이드 전수 준수 PASS는 아니다.

기획서 제2항용 근거: 등록 MCP 집행 경계→strict registry/PDP/private executor→금지 호출0; 정확한 위임·단회 승인→원자 reserve→경쟁 효과1; TLS 역할 분리·토큰 digest·암호화→실제 MCP+LIVE 인증/비밀 검색; 오류→UNKNOWN/명시적 receipt reconciliation→추가 효과0. 행동 출처 이력은 SBOM이나 인과 증명이 아니다.

잔여 P0·검증: 기본24시간 보존/폐기 구현, 인증서 재발급/키회전·복구 절차의 실제 재현, Gateway 인증 flood/자원 부하, 실제 UI 브라우저 XSS/승인 조작, 제품의 만료/잘못된 client cert 전체 matrix, PDP timeout/malformed/source 저장 실패의 전체 동적 fault matrix, 새 PC 재현, OS 이미지 CVE·license/고지 완전성, 20/49 원문 항목별 전체 수동·별도 검토가 남는다. 실행 경로를 보호했다고 이 미확인을 PASS로 바꾸지 않는다. local-ingress는 호스트 공개를 위해 추가했고 OS outbound 전체 차단은 없다. CA/leaf는 7일/2일이며 만료 시 fail-closed, CA 개인키는 보관하지 않는다. Windows ACL은 사용자/SYSTEM만 허용하며 실제 read 재확인 후 기록한다.

보호 범위는 등록 MCP 3도구뿐이다. 같은 OS 계정/관리자에 의한 코드·DB 직접 접근, Codex 내장 셸/파일, 다른 MCP, 모든 IPI, 사용자 PC 전체의 보호는 주장하지 않는다.

R1 보완: check/reserve의 세션 미해결 UNKNOWN gate, 위험 쓰기 전 다른 RESERVED 완료 확인, read SUCCEEDED report의 required source 존재 확인을 적용했다. source실패 후 추가읽기/쓰기0, 기존 prechecked call reserve409, 출처 없는 receipt-only report503, 명시 source복구+receipt후 재실행0/정상댓글1을 독립 검토에서 재현했다. 해당 P1은 제거 확인했고 전체 fault/수명/브라우저·가이드 게이트는 남아 있다.
