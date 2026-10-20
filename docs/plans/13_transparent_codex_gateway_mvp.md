# 제품 방향 정정: 평소 Codex에 자동 연결되는 실행 전 엔진

**2026-10-16 후속 모델 방향:** 평소 CLI/hooks/실제 gateway 목표는 유지한다. 사용자는 PDP 의미 판정에 생성 GPT 대신 TypeSafe Jev 같은 판정 모델을 원한다고 밝혔으며 [15번 계획](15_jev_pdp_transition.md)을 따른다. 코드 정책→출처 대조→미확정일 때만 좁은 판정 모델 관측으로 정리한다. 현재 제품은 여전히 SPEC5/GPT이며 Jev 구현/정확도는 미검증이다.

2026-10-16 / 사용자 명시 정정에 따른 관리 결정. 이 문서는 기존09~12 및 SPEC4 모의 실험의 제품 사용 방식보다 우선한다. 기존 코드·원증거·필수 가이드와 보안 불변조건은 보존한다. 현재 관리 세션은 계획/판단만 하고 제품 구현·유료 호출은 하지 않는다.

## 사용자가 원하는 MVP

개발자는 자신의 단말에서 평소처럼 `codex`를 실행하고 자연어로 자유롭게 개발한다. 최초 연결 설정 후 사용자 입력·도구 결과·도구 호출이 hooks/agentgateway를 통해 자동 연결되고, PDP가 도구 실행 전에 판정해 결과를 돌려준다. 대시보드에서 작업을 사전 등록하거나 agent token을 복사하지 않는다. 외부 자료의 IPI를 따른 행동은 실행 전에 차단하고 정상 개발은 계속할 수 있어야 한다.

현재 제품은 이 목표를 달성하지 못했다. 고정 이슈42/POST_COMMENT/정확한 원문/쓰기1회/모의3도구/별도 실험 CLI는 반복 가능한 fixture로 보존하되 일반 제품의 필수 조건으로 사용하지 않는다. 단순히 세션 발급을 자동화하는 작업으로 축소하지 않는다. 앞선 '원하는 구조대로 가고 있다'는 설명은 등록3도구 실험 경로에만 해당했으며 평소 개발 환경의 훅·agentgateway 연동 완료를 의미하지 않는다.

## 새 연결 구조와 책임

| 계층 | 역할 |
|---|---|
| 사용자 입력 hook | 실제 사용자 입력과 session/turn을 자동 취득. 최초 요청뿐 아니라 후속 요청 변경도 기록. 에이전트/도구가 자칭한 user_request는 신뢰하지 않음 |
| 도구 결과 hook / MCP 응답 관측 | 읽은 자료와 출처·정확한 호출을 연결. 사용자 입력과 외부 지시를 섞지 않음 |
| 실행 전 hook | 지원되는 로컬 도구의 이름/인자/호출ID/세션·turn을 PDP로 보내 응답을 기다리고 실제 차단 |
| agentgateway | MCP upstream 앞의 실제 프록시·외부 인가 연동. 도구 호출의 본문/대상/세션과 PDP 결정을 연결해 실행 전 집행 |
| 기존 PDP | 정책→출처 대조→필요한 의미 판단. 서버가 ALLOW/DENY/예외CONFIRM을 결정 |
| 대시보드 | 이력·진단·실제 효과·필요한 예외 확인. 작업 시작의 필수 관문이 아님 |

MCP 호출과 로컬 내장 도구는 다른 실행 경로다. agentgateway가 내장 shell/file 호출까지 자동 프록시한다고 가정하지 않는다. 두 adapter가 같은 PDP 계약과 식별자를 사용하도록 하며, 동일 MCP 호출을 hook과 gateway가 각각 유료 분석하지 않도록 결합한다. 사용자 동작은 자유롭게 유지하되 지원하지 못한 도구는 실제 관측/집행 범위를 표시한다.

각 호출의 최종 실행 경로가 실제 집행 책임을 지며 다른 adapter의 ALLOW만으로 인자·정책 결합 검증을 생략하지 않는다.

세션ID·연결 인증은 필요하면 내부에서 자동 발급/전달한다. 사람이 작업별로 권한/토큰을 입력하는 UX는 제거한다. 초기 신뢰 설정과 머신 인증을 없애는 결정이 아니다. 사람의 요청 이벤트와 외부 자료를 구분하는 신뢰 경계는 유지한다. 개인 API키/설정을 무단 변경·복사하거나 원격에 프로젝트 전체를 보내지 않는다.

## 기술 확인 사실과 미검증

2026-10-16 [Codex Hooks 공식 문서](https://learn.chatgpt.com/docs/hooks)를 열어 UserPromptSubmit의 prompt/turn, PreToolUse의 지원 도구와 deny 반환, PostToolUse의 사후 관측을 확인했다. `codex --version`은0.154.0, features list는 hooks stable true였다. 이 조회는 모델을 호출하지 않았다. 실제 이벤트·차단·실패 동작이 이 설치/Windows에서 검증됐다는 뜻은 아니다.

공식 문서는 shell/exec_command, apply_patch, MCP 등 지원 경로와 hosted tool/특수 경로 예외를 구별한다. PostToolUse는 이미 발생한 효과를 되돌리지 못하며 write_stdin은 기존 프로세스에 입력/폴링할 때 PreToolUse가 다시 발생하지 않는다고 설명한다. hooks는 완전한 OS 보안 경계가 아니다. 이 한계를 숨기거나 단순 관측을 실행 전 차단으로 보고하지 않는다.

[agentgateway 외부 인가 공식 문서](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/external-authz/)는 HTTP/gRPC extAuthz와 요청 본문 포함, TLS 및 timeout 설정을 제공한다. HTTP MCP 본문과 원래 JSON-RPC tool/call을 실제로 검사할 수 있는 고정 버전·구성을 검증해야 한다. [MCP 인가 문서](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/)의 mcpAuthorization 단계에서는 tool arguments가 없을 수 있으므로 이름 기반 규칙만으로 내용 판정을 완료했다고 하지 않는다.

## 개발 배정: WP-HOOK-GW-01

단일 개발 통합 세션이 다음 의존 순서로 수행하고 별도 AI 검토 후 인계한다.

1. **연결 능력 확인:** Windows/설치 CLI의 실제 hook 이벤트·입력/출력·동기 deny·정상 통과·hook/PDP 장애를 최소 재현한다. agentgateway 버전/이미지/출처·해시·라이선스를 고정하고 실제 MCP 프록시의 도구 인자/응답·extAuthz 거부→upstream효과0을 확인한다. 모델 없는 계약 fixture를 우선 사용한다. 빠진 hook 필드나 실패 시 계속 실행되는 경로를 발견하면 명시해 해당 경로의 보호를 주장하지 않는다.
2. **새 계약과 adapter:** 실제 사용자 turn/session/tool-call의 자동 결합, 후속 대화, 출처 ingest, 실행 전 판정/결과 관측 계약을 분리한다. 현재 SPEC4는 과거 실험 계약으로 보존하고 SPEC5/정책 개정은 이 문서의 범위에서 명시 위임한다. 고정 POST_COMMENT/이슈42/원문/쓰기1회 제약은 일반 adapter에서 제거한다. 정책의 민감정보·권한·출처 검증을 무조건 ALLOW로 대체하지 않는다.
3. **PDP 재사용·일반화:** 기존 의미 관측/엄격 refs/진단/저장 보호를 재사용한다. 로컬 코드·문서·MCP 결과를 얻는 실제 경로와 누락/잘림을 표시하고 잘못된 사용자 출처 승격을 막는다. 자연어 요청은 hook에서 자동 취득하고 모델이 만든 위임을 신뢰하지 않는다. 도구 결과의 문자열 일치는 인과 증명이 아니다.
4. **실행 안전 계약:** gateway/hook의 중복 분석/실행과 인자 변경을 막는다. 일반 upstream/호스트 도구에는 DemoExecutor의 transaction/멱등성/receipt 보장이 자동 적용되지 않는다. 관측한 실행 결과와 실제 효과를 구별하고 UNKNOWN 자동 위험 재시도·환불 금지를 유지한다. 지원하는 native shell/file 경로는 정책과 차단 증거를 갖추고, 기본적으로 모든 개발 도구를 끄는 방식으로 제품 목표를 대체하지 않는다. Codex 자체 권한을 불필요하게 확대하거나 우회하지 않는다.
5. **최소 수용:** 대시보드 작업 생성/토큰 복사 없이 직접 CLI에 요청1회, 정상 읽기/편집/지원 MCP 작업 성공, 후속 사용자 요청 자동 반영, 외부자료의 위험 지시 차단·금지 효과0, 정상 외부자료 활용 허용, 장애/출처 위조/동시 호출·재전송 검증. 위험 후보 미시도는 NO_ATTACK_ATTEMPT다. 모의 이슈/안전한 upstream은 시험 자료로 쓸 수 있지만 제품을 특정 이슈에 고정하지 않는다.

현재 실측 judge12/24와 actor0 기록은 보존한다. 개발 AI가 유료 모델을 재실행하거나 예산을 초기화/늘리는 권한을 부여하지 않는다. 새 adapter의 실제 LIVE는 사용자 직접 실행으로 남기며, 필요 예산과 전송 자료/대상·보호 범위·미검증을 설명한다. 기존 회귀에 해당하는 필수 통제와 R1/G1~G4 가이드, 설계20/약점49 적용 근거는 유지한다. C/D 전체를 이번 통합의 선행조건으로 추가하지 않는다.

## 쓰기 범위·인계

개발 세션은 src/app/의 adapter/PDP/저장·웹 관련 범위, scripts/tools, 관련 tests/안전 fixtures, 별도 agentgateway Compose/설정·의존성 고정/공급망 증거, docs/mvp 현재/과거 계약 구분과 SPEC5 동기화, README의 새 사용 절차를 수정할 수 있다. 공통 정책·DB·계약·설정은 단일 작성자가 통합한다. 새 tool 실행은 지원 경로를 명시하며 임의 위험 실행기를 자동 도입하지 않는다.

개인 Codex 전역 설정/인증·전역CA·기존DB/키·예산·원증거는 교체하지 않는다. 연결 설정은 검토 가능한 프로젝트/전용 프로필 구성과 적용 절차를 제공한다. docs/plans·harness/build_tasks.json·AGENTS·skill·원본PDF는 개발 세션 쓰기 범위가 아니다.

결과는 docs/handoffs/WP-HOOK-GW-01/<run_id>/RESULT.md와 별도 REVIEW.md로 전달한다. 훅 이름·도구·agentgateway 경유 여부·실행 전 차단 여부·정상 기능·남은 우회/미지원 경로를 표로 보고하고 실제 소스·실행 전후 효과·UTC·명령·최초 실패/조치/재진단을 연결한다. 새 연결 미구현/미검증을 과거3도구 시험 PASS로 완료 처리하지 않는다.
