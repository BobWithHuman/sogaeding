# 개발 흐름과 게이트

설계의 원문은 `docs/mvp/01_requirements.md`, `03_api_and_state_contract.md`, `05_security_and_acceptance.md`다. 이 문서는 구현 순서와 개발 작업의 종료 조건을 정한다. task ID는 `harness/build_tasks.json`과 `docs/mvp/04_traceability_and_work_breakdown.md`의 T-00~T-10을 사용한다.

## 준비

현재 Docker preflight 절차는 `docs/mvp/06_today_execution.md`를 따른다. PowerShell의 `./scripts/dev_docker.ps1 -Mode up`, `./scripts/dev_docker.ps1 -Mode check`는 개발 도구·계약 준비 게이트다. `check`의 fixture/계약 시험은 제품의 실제 MCP 수용시험이 아니다. Docker CLI가 있다는 사실과 엔진 연결 성공, 이미지 빌드 성공, 제품 서비스 성공을 구별한다. 정확한 명령·exit code를 남긴다. 키가 없어도 core/REPLAY 개발은 진행한다.

계약이 고정되면 T-00에서 저장소 상태·ignore·의존성/컨테이너 설정을 확인하고 T-02의 최소 session/auth/registry를 구현한다. 사용자·gateway·agent의 인증 역할을 먼저 분리한다. 선택한 MCP SDK 버전의 인증 API를 확인하며 다른 버전의 예제를 추정해 섞지 않는다.

## 얇은 연결: T-01, T-03, T-04

1. 실제 MCP transport와 bearer 문맥으로 도구 한 개를 호출한다. 유효·누락·오류·만료·audience 불일치 인증을 검사한다.
2. 세션 작업 범위에 맞는 정상 읽기를 실제 executor까지 보내고, 요약 세션의 댓글 후보 또는 비밀 읽기를 판정 전에 우회할 수 없게 한다.
3. 거부 응답과 별도로 executor invocation/effects에서 금지 행동 0을 확인한다. 이 게이트가 실패하면 고급 화면과 대규모 LIVE 평가를 시작하지 않고 연결·집행 경계를 먼저 고친다.

T-04에서 원자적 reserve, effects receipt, report 유실과 reconciliation을 붙인다. 예약 성공 전에 executor에 접근하는 코드 경로가 없어야 한다. 읽기 출처 저장 실패와 쓰기 결과 보고 실패의 시점을 구별한다.

## 병렬 구현: T-05, T-06, T-07, T-08

계약과 기본 연결이 통과한 뒤 출처/장부, 승인/resume, fixture/수용시험을 파일 소유권에 따라 병렬 진행한다. UI는 이미 정해진 조회·승인 API를 사용하며 서버 정책을 브라우저 로직으로 대체하지 않는다. 외부값 일치는 관측으로만 설명하고 원판정 CONFIRM을 승인 후에도 유지한다.

구현이 끝난 범위마다 문서의 NT/AT ID를 실행하고 효과 저장소와 대조한다. 인증·비밀 읽기·승인 replay·세션 혼합·장애·동시성 실패가 남으면 core 완료를 선언하지 않는다.

## 제품 LIVE: T-09

Codex CLI를 제품의 실제 에이전트로 연결하는 경로를 우선 확인한다. 개발용 Codex 실행과 별도 세션·권한·설정·증거로 구분하고 등록 MCP만 시험한다. 내장 shell/file/다른 MCP 경로는 별도로 목록화하고 필요한 제한을 확인한다. 일반 개발 세션에서 비밀 파일 읽기를 시켜 제품 보호 증거로 삼지 않는다.

OpenAI API키는 환경변수로 주입한다. 신뢰된 런처가 세션 `user_request`와 Codex 최초 프롬프트에 동일한 사용자 원문을 전달하고, Codex에는 agent session token만 제공한다. 전용 CODEX_HOME·가짜 연구 workspace와 `scripts/run_codex_live.ps1`의 연결 절차를 따른다. 정확한 model ID와 CLI/SDK 버전·auth 방식·설정을 기록한다. 실제 호출 비용이 있는 LIVE는 이미 승인된 시험 범위의 짧은 정상/공격 smoke부터 시작하고, 설정 오류를 대규모 반복으로 해결하지 않는다. CLI 경로가 막히면 원인을 기록하고 REPLAY 검증을 계속한다. 문서의 기본안대로 별도 Python LLM 에이전트를 동시에 만들지 않는다.

고정된 REPLAY 후보로 판정이 통과했다고 모델 보호가 완료된 것은 아니다. LIVE가 위험 후보를 생성하지 않았으면 `NO_ATTACK_ATTEMPT` 관측으로 기록한다. 정상 과업 최종 출력도 별도로 확인한다.

## 검토·수정·재개: T-10

작성자가 변경과 최소 증거를 넘기면 독립 검토자가 diff와 실제 결과를 확인한다. 기본은 작성→검토→관련 수정·재시험 두 차례까지다. 오류가 반복되면 정확한 실패와 다음 조치를 남기고 독립적으로 가능한 작업을 계속한다. 예산은 디버깅 자체를 금지하거나 사용자가 승인한 범위를 줄이는 규칙이 아니다.

작업을 재개할 때 TODO/IN_PROGRESS/BLOCKED/DONE을 파일과 증거에 대조한다. 선행 DONE이 잘못되었거나 계약이 바뀌었으면 관련 작업을 다시 검증 대상으로 돌린다. 명령이 실패·중단되었으면 결과를 기록하고 원인을 고친다. 시험 생략·mock 판정만으로 완료 처리하지 않는다.

완료 보고에는 core/LIVE를 나누고 NOT_RUN/FAIL/BLOCKED를 보존한다. 실제 제품 서비스와 시험이 아직 없다면 문서·컨테이너 준비 완료까지만 보고한다. 제출·push·공개 운영은 사용자가 요청한 범위에서 따로 진행한다.
