# V5 시연 연결 — DEMO_PREPARED

2026-10-17. 기존 Codex 런처→hook/등록 파일 MCP→실제 agentgateway→명시 V5 profile→예약/파일 executor→기존 viewer의 시연 경로를 연결했다. **준비·무모델 검증·별도 AI 검토 완료**, 사용자 실제 시연은 아직 수행하지 않았다. 실제 actor/TypeSafe/GPT 요청0·사용자 CLI 시작0·기존 서비스 교체0이다. 개발 AI 토큰은 구현과 별도 검토에 사용했고 제품 유료 호출0과 별개이며 정확 계량값은 제공되지 않았다.

## 준비된 사용자 명령

[USER_RUN.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v5-demo/USER_RUN.md)에 고정 start 한 명령과 history 한 명령, 필요 시 기존 승인 watcher 명령을 제공했다. 사용자가 prepare/키 입력/계획 생성을 다시 할 필요 없다.

- revision `behavior-v5-1`, manifest SHA256 `bf656becbe6ed3344e133cd86c2c62234d082c0e5ee5b37679dbcb783b46b33d`
- 독립 프로젝트 `with-human-mvp-demo-behavior-v5-1`, control8036/gateway8046. 새 DB/workspace/role PKI와 보고서 경로는 `artifacts/runtime-mvp-demo/revisions/behavior-v5-1/` 아래다. 기존 V3 프로젝트/DB/normal.md는 보존한다.
- [check.json](C:/sogaeding/artifacts/20261017-v5-demo/check.json): **ready=true**, V5/정확 bundle64·image 확인, JEV_RULES_ONLY/NOT_AUTHORIZED, provider ledger 없음, MCP handshake READY·tools/read_file/write_file 등록. tools_call_count/user_turn_count/candidate_count 모두0이며 모델 접근은 **NOT_VERIFIED_NO_REQUEST**다.
- [inspect.json](C:/sogaeding/artifacts/20261017-v5-demo/inspect.json): 공개 원문·동적 후보 범위·V5 질문 원본 hash·source/image/profile/부모 원장/설정 결합. prepare.json/preparation-commands.json은 실제 PS5.1 준비/inspect/check/history 명령과 결과다.
- [final-state.json](C:/sogaeding/artifacts/20261017-v5-demo/final-state.json): 새 control의 connections/turns/calls/approvals 모두0, 새 CLI claim/provider ledger 없음, provider disabled. 기존8034 V3 정책도 여전히 실행 중이다.

실제 시작 제안은 한 CLI에서 정상/공격 자연어 요청2개다. 새 Jev4요청/입력예약256000, 추가CLI1/시작총4, 전체 대화형1800초. 전체 역사21+4=25요청/1600000예약, demo관련20/1280000이다. 기존8/8 등 소진 원장 증액/초기화·환불이 아니며 start의 명시 사용자 선택 전 새 지출권한이 없다. actor는 기존 사용자 선택 gpt-5.6-luna/API 연결을 재사용하며 비용은 별도다. 현재 provider 요율/실제 금액은 보장하지 않는다.

## 변경과 보호 경계

`server.py`에 `behavior_v5`를 명시적으로 추가했다. V2/V3 분기는 유지한다. live는 **표준 JevClient + JevPolicyV5**이며 질문/A범위/.90/행동·귀속 분리를 바꾸지 않았다. Engine/승인/DB 상태 계약/의존성은 변경하지 않았다.

기존 `mvp_demo.py`의 준비/서비스 check/CLI flags/start/lifecycle/단회 claim/history를 revision 설정으로 재사용한다. `mvp_semantic_followup.py`는 V5의 고정 설정·source/image/원장 부모/추가·누적 한도만 연결한다. 기존 mvp_demo.ps1와 mvp_confirm.ps1/도구를 확장했고 제품용 새 PS1·평가 runner·UI는 만들지 않았다. 신규 compose는 별도 project/network/포트/작업 폴더만 준비한다. artifacts의 PS1/Python은 무모델 검증·기록용이다.

동일 대기 RPC의 CONFIRM→사람 정확 승인→단회 소비/예약→재개를 그대로 쓴다. 중복 actor ID/RPC/승인 재사용은 추가 분석이나 실행으로 바꾸지 않는다. 번호 선택 뒤 approve/reject 직접 입력, Enter 취소, 호스트 Allow와 제품 승인의 차이를 인계했다. DENY는 승인으로 해제하지 않고 UNKNOWN은 재시도/환불하지 않는다. 실제 사용자 turn/권한/source/hash/ref/snapshot/인자/정책 결합, 인증/TLS·역할별 키 RO 참조는 유지한다.

기존 HTML/텍스트 viewer의 V5 선택/확신, 정책, HUMAN_CONFIRMED·NORMAL_AUTO_OBSERVED·ATTACK_BLOCKED_CANDIDATE·ANALYSIS_FAILED·미시도·UNKNOWN 및 실제 파일 결과 표시만 보완했다. 출처는 판정 자료와 관측된 연관으로 표시하며 causal_explanation은 NOT_ESTABLISHED다. 인과 증명 화면이나 인과 정확도 연구는 추가하지 않았다.

## 실제 gateway 무모델 검증

[gateway evidence](C:/sogaeding/artifacts/20261017-mvp-semantic-v5-demo/gateway-1/evidence.json) 및 [기존 viewer HTML](C:/sogaeding/artifacts/20261017-mvp-semantic-v5-demo/gateway-1/history.html): **64/64 PASS**, 실제 TLS gateway/파일 executor, actor/provider 실제 호출0, 금지 파일 효과0. 별도 시험 프로젝트를 사용한 뒤 down으로 정리했다.

저장된 실제 V5 정상 A .86/B LEGITIMATE1.00와 공격 A/B EXTERNAL_ADOPTION .97의 choices/probabilities/provider confidence를 **새 시험 입력에서 A/행동 replay**했다. 새 catalog에 과거 source 귀속을 승격하지 않도록 attribution은 합성 UNCERTAIN이다. 현재 wire/입력/ref는 다시 검증하며 이를 새 실제 관측/의미 정확도라고 표현하지 않는다. 정상 자동 ALLOW는 별도 높은 합성 응답 시험이다. live profile에는 녹화 답·fake transport가 없다.

- 정상 CONFIRM 승인·거절의 실제 trusted terminal, 대기 중 실제 파일 부재, 같은 RPC 승인 후 실제 단회 파일 효과, 거절 효과0 및 재개 모델 호출0
- 높은 확신 공격행동은 A/정밀 귀속 불확실성과 독립적으로 DENY·upstream 금지 쓰기0·reports/review.md 부재
- 합성 높은 정상 ALLOW→실제 쓰기, 인자 변조·RPC replay·중복 actor ID 거부
- 인간 대기 중 기존 freshness 경계를 넘겨도 승인 exact binding 유지, 원 decision CONFIRM 보존
- PDP503 장애는 실행 전 차단·파일 효과0, transport 응답 유실은 UNKNOWN/재시도 금지, 연결 종료 후 늦은 dispatch 차단
- bounded viewer/human auth, FILE_NOT_FOUND 업무 오류와 UNKNOWN 구분, 제품 source 안정성

시험의 가짜 provider10회는 별도 임시 가짜키/가짜 원장의10회 한도로5종 쓰기 경계를 검사한 것으로, 실제 시연의 새4회 allowance와 무관하며 기존 유료 원장을 소비/증액하지 않았다.

## 관련 시험·별도 검토

| 검증 | 관측과 증거 |
|---|---|
| 관련 통합 | related-integrated.txt: **193 PASS/3 FAIL**, 35.92초. 실패3개는 구형 V2 원 관측 파일 RO mount 누락 |
| 해당3개 수리 재진단 | replay-repair.txt: **3 PASS/28 deselected**, 1.53초. 제품 변경 없이 역사 observation.json 1파일 RO mount |
| V5 연결/한도 보강 | related-final.txt: **45 PASS**, 14.29초. 중첩 숫자/disabled config 엄격성 반례2개 포함. 첫 통합의43개와 겹치므로 합산하지 않음 |
| gateway 통합 | gateway-command.json/gateway.txt 및 원 evidence **64 PASS**, 실제 모델0 |
| 별도 AI 검토 | [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v5-demo-review/REVIEW.md), 독립 **13 PASS**, 최종 차단 발견 없음. 별도 사람/공식 진단으로 표현하지 않음 |
| 실제 PS5.1 | native.json **13 PASS**, fake helper의 고정 인자/9한도 거부/history/revise/승인 watcher·Unicode. 별도로 실제 revise/inspect/check/history 완료 |
| 정적 진단 | Ruff exit0. Bandit exit1 **Low10/Medium7** 원진단 보존(static-summary.json/bandit-final.txt). 전체 보안 PASS가 아님 |

최초 import/fixture 정리, 역사파일 mount 누락, 중첩 숫자 엄격성 조치·재검증, sandbox image metadata 접근 실패와 승인된 읽기 전용 재확인을 [INITIAL_DIAGNOSTICS.md](C:/sogaeding/artifacts/20261017-v5-demo/INITIAL_DIAGNOSTICS.md)에 남겼다. Bandit의 bind0.0.0.0는 컨테이너 내부/public loopback 포트 및 private mTLS 경계, `/tmp`는 tmpfs/시험 공개 가짜키, subprocess는 고정 argv/trusted helper, disabled key 문자열은 공개 placeholder다. 원진단을 삭제하거나 모든 취약점 없음으로 표시하지 않았다. gateway 통과 후 문서/hash 때문에 전체 회귀를 반복하지 않았다.

## 보존·가이드·미검증

source-manifest.json/change.diff/original/은 변경 원본과 최종 후보를 결합한다. preservation-before/after.json에서 기존 실제 V5 동결60과 과거 원장5개/CLI3claim/원 결과·manifest/성공파일을 대조했고, 배정된 server/demo_report만 바뀌었다. 기존21요청/1344000예약과 실패/UNKNOWN·CLI3/3은 그대로다. V5 원 후보4개 SHA도 유지됐다. source mismatch는 역사 결과를 덮어써 숨기지 않는다. 관리 plans/harness/AGENTS·개인 로그인/전역 설정/CA/sandbox/reviewer 정책은 바꾸지 않았다.

필수 가이드는 기존 원문/해시 artifacts/20261017-auto-decision/guide-pages.json과 docs/plans/03_guide_compliance.md의 적용성을 재사용한다. R1 PDF14/G1 PDF35~36→source·image·부모 근거 추적, G3 PDF507~508 SR1-4/9→고정 profile/경로/typed limits·사용자 권한, G2 PDF128/135/137→단회 claim/승인/안전 오류·UNKNOWN, G3 PDF510/G4 PDF38→기존 역할키RO·TLS/민감정보 비노출, G4 PDF24→최초 진단·조치·재진단·별도 검토로 연결했다. 미점검20설계/49약점·전체 TLS negative/키수명/공급망을 PASS로 올리지 않는다.

현재는 **DEMO_PREPARED**다. 사용자 실제 DEMO_VERIFIED, 새 actor의 위험 후보 생성/실모델 공격 집행·정상 자동 핵심 성공은 NOT_RUN이다. 정상 CONFIRM→사람승인은 시연 가능하지만 자동 정상/전체 MVP 완료가 아니다. 새 실제 actor가 위험 후보를 만들지 않으면 NO_ATTACK_ATTEMPT다. 등록된 합성 파일 MCP 범위이며 일반 native/hook 사망·Codex 모든 내장 도구·전체 IPI/정밀 인과/모델 전체 정확도 보호를 선언하지 않는다. 실제 시연 뒤 정상 파일 내용·판정/승인/쓰기 횟수, 공격 후보·DENY·금지 쓰기0, 종료·사용량을 history에서 대조한다.
