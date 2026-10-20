# WP-HOOK-GW-02: API 실행 준비와 실제 모델 첫 검증

**후속 상태:** [B 보완·사용자 실행 관리 판정](reviews/WP-HOOK-GW-02_B_20261016_repair_host_approval_management.md). T-HG-04 오프라인 보완을174파일 일치로 수용했다. 새 read2건의 우리 PDP A/B는 VALID·ALLOW이나 실행 전 READY이며 Codex 자체 자동 승인403으로 정상 작업은 미완료다. 현재22/24·남은2. 사용자의 생성 LLM 대신 TypeSafe Jev 판정 모델 방향은 [15번](15_jev_pdp_transition.md)을 따른다. 아래는 이전 실패/보완 배정 기록이다.

**최신 상태:** [2026-10-16 B 실제 정상 실패](reviews/WP-HOOK-GW-02_B_20261016_live_failure_management.md). 사용자 API 실행의 정상 읽기 후보3건이 QUOTE_MISMATCH/A로 거절됐다. judge18/24·남은6, 새6건 COMPLETED이며 정상 작업은 FAIL이다. 다음은 **B 보완/T-HG-04의 근거 생성·검증 및 무모델 MCP 시작 진단**이다. 추가 LIVE는 보완·검토 후 사용자 정상1건만 재배정한다. [단계 A 준비 수용](reviews/WP-HOOK-GW-02_A_20261016_management.md)은 좁은 범위로 유지하며 전체 MVP는 미완료다.

2026-10-16 관리 배정. [13번 제품 방향](13_transparent_codex_gateway_mvp.md)은 유지한다. [WP-HOOK-GW-01 관리 판정](reviews/WP-HOOK-GW-01_20261016_management.md)에 따라 자동 MCP 연결/모델 없는 집행 범위는 수용하고 전체 MVP는 미완료로 둔다.

## A. 지금 개발 세션에 맡길 좁은 보완

사용자는 API 방식의 실제 Codex를 직접 실행하려 한다. 현재 launcher는 개인 인증을 상속하며, 관리가 조회한 로그인은 CHATGPT였다. `compose.hookgw.live.yaml`의 Control judge API 모드를 켜는 것만으로 actor Codex도 API 방식이 되는 것은 아니다.

1. 현재 터미널/이번 CLI 호출에만 적용되는 명시 API 실행 모드를 추가한다. 개인 `config.toml`/auth·로그인/전역환경·CA를 변경하거나 로그아웃시키지 않는다. 기존 자유 입력·hook/agentgateway·자동 사용자 turn 연결과 원래 sandbox/승인 정책을 유지한다. 위험한 우회 flag나 강제 read-only를 새로 넣지 않는다.
2. 공식 OpenAI Responses endpoint와 env_key 기반 인증을 명시하고 키 값은 환경으로만 전달한다. 실제 적용 provider/model·인증 종류·endpoint를 비밀 없이 확인한다. 모델은 선택값을 명시하고 접근 미확인은 표시하며 임의로 더 비싼 모델로 교체하지 않는다. 일반 로그인 상태와 호출별 provider 인증을 혼동하지 않는다.
3. **모델 없는 preflight:** 키 존재 여부만 검사, 정확한 CLI/설정·hook 신뢰 필요 상태, 앱 CA/TLS health, judge_mode=LIVE_USER, 기존 budget12/24 유지, Control judge 키의 컨테이너 읽기 가능 여부를 값 노출 없이 확인한다. 서비스 준비 실패 때 모델을 먼저 시작하지 않는다. 전역/기존 hook 정의 충돌도 숨기지 않는다.
4. 가짜 자격증명의 로컬 Responses fixture 및 설정 회귀로 실제 요청의 인증 경로를 확인한다. 실제 API키/원문은 캡처하지 않고 개발 AI 유료 호출0을 유지한다. 제품/API 준비가 의미 판단 성공을 뜻하지 않는다.
5. 별도 AI 검토 후 사용자에게 현재 머신의 정확한 최소 명령, 첫 `/hooks` 신뢰 절차, 상태/이력 확인, 중단 조건을 제공한다. 전역 상태/DONE은 수정하지 않는다.

작성 범위: scripts/hookgw_connect.ps1, tools/hookgw_launch.py와 필요한 좁은 preflight helper, 관련 tests/hookgw, docs/mvp 현재 사용 설명/README, 새 RESULT/REVIEW. 필요하면 compose.hookgw.live.yaml의 키 가시성/준비를 좁게 보완하되 기존 키·DB/예산을 교체/초기화하지 않는다. src/app/엔진 정책이나 새로운 기능 확장을 이 보완의 선행조건으로 만들지 않는다.

## B. 그다음 사용자가 직접 수행

무모델 준비가 통과한 뒤 사용자가 API 모드 `codex`를 실행하고 `/hooks`에서 정의를 확인·신뢰한다. 먼저 합성 notes.txt를 읽고 정상 요약을 같은 fixtures/hookgw/normal-output.txt에 쓰는 작업1건만 한다. `history`에서 실제 user/pre/post·판정/진단·실행 상태를 확인하고 실제 파일 결과와 대조한다. 효과 파일은 기존 probe 결과가 있으므로 존재 여부만으로 새 성공을 판정하지 말고 해당 call/이번 실행의 내용·hash/시각을 연결한다.

첫 ANALYSIS_UNAVAILABLE, unexpected native 차단/효과, UNKNOWN, 사용자 turn 미기록이면 중단하고 이력으로 원인을 진단한다. 공격 시험으로 연속 진행하거나 비용을 들여 반복하지 않는다. 정상 성공 후에만 별도 공격 입력1건을 시험한다. 위험 후보 미생성은 NO_ATTACK_ATTEMPT이며 판정 모델이 해당 후보를 근거 있게 DENY하고 실제 효과0일 때만 그 차단을 수용한다.

현재 judge 마지막 기록은 이번 실제 실패 후18/24·남은6이며 실제 runtime preflight에서 다시 읽는다. 이전 A의12/24는 당시 증거다. 이 예산은 Control judge에 적용되고 actor Codex의 API 비용/토큰은 별도다. 개발 세션은 유료 호출·예산 증액/환불/초기화를 하지 않는다. 전체 프로젝트·실자료를 시험 입력으로 자동 수집하지 않는다.

### B 보완의 명시 배정（2026-10-16）

[REPAIR_START_PROMPT](../handoffs/WP-HOOK-GW-02/REPAIR_START_PROMPT.md)가 정확한 쓰기 경계와 수용 조건이다. 서버 생성 exact evidence catalog/ID를 실제 snapshot·뷰·해시에 결합해 모델의 직접 문자 위치 계산 의존성을 줄인다. 정확 근거 검증을 유지하고 진단을 보완하며, 첫 분석 장애 뒤 같은 사용자 turn의 새 call이 유료 분석을 반복하지 못하게 한다. 실제 stdio MCP 초기화/목록 조회도 모델 없이 검증한다. 내부 judge 계약/버전의 필요한 좁은 개정은 이 배정에서 허용하고 SPEC4 공유 회귀를 유지한다. 관리 문서/전역 장부는 개발 세션이 수정하지 않는다. 기존 user LIVE 실패/키/DB/원증거를 보존하고 별도 AI 검토 후 인계한다.

## C. MVP 완료 전 남은 제품 작업

- 정상 native 파일 편집과 일반 개발 명령 지원/결과 관측을 실제 도구 형식에 맞춰 보완한다. 사용자가 요구한 자유 개발을 read-only/전부거절/MCP 두 도구만으로 대체하지 않는다.
- native hook 프로세스 사망/timeout/malformed의 fail-open은 호출 wrapper의 예외처리와 다른 구조적 한계다. 실제 집행 경계/지원 범위를 검증하고 해결 불가능한 경로를 숨기지 않는다. 별도 설계 없이 CLI fork/업데이트·OS격리·전역 권한 변경을 임의 실행하지 않는다.
- 이번 gateway에 실제로 매칭된 권고의 패치/도달성 및 이미지 진단을 마무리한다. 전체 C/D 전수를 당장 A/B의 선행조건으로 묶지는 않는다. 필수 가이드/노출 경로 P0는 유지한다.

A 완료와 B 첫 실제 성공은 전체 C 완료가 아니다. 인계는 docs/handoffs/WP-HOOK-GW-02/<run_id>/RESULT.md와 별도 REVIEW.md이며 최초 실패/조치·현재 소스·실행 결과·실패/미실행과 비용 한계를 구분한다.
