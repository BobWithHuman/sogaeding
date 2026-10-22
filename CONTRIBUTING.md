# 엔진 공동 개발

현재 구현은 Python/FastAPI/SQLite + Codex hooks + 실제 agentgateway다.
조직의 Rust `withhuman-core`, Claude Code/Neo4j `engine-prototype`과 별도 구현이다.
기존 조직의 PR·커밋·리뷰 강제 규칙은 이 저장소에 추가하지 않았다.

## 개발 시작

Docker Desktop의 Linux containers와 Windows PowerShell 5.1 이상을 준비한다.
clone한 저장소 경로에서 실행한다. 기본 빌드·시험에는 호스트 Python이나 기존 개발자의 키가 필요 없다.

```powershell
.\scripts\team_dev.ps1 -Mode build
.\scripts\team_dev.ps1 -Mode test
.\scripts\team_dev.ps1 -Mode prepare
.\scripts\team_dev.ps1 -Mode up
.\scripts\team_dev.ps1 -Mode check
```

| 명령 | 동작 |
|---|---|
| build | 잠금 의존성과 고정 베이스 이미지로 `sogaeding-team-dev:local` 생성 |
| test | 네트워크 없이 대표 엔진·Jev 계약·승인·인증 시험 |
| prepare | 새 로컬 인증서·토큰·합성 workspace 생성. 기존 runtime 덮어쓰기 거절 |
| up | 현재 소스를 실제 Control·TLS agentgateway·MCP에 연결 |
| check | health·인증 거절·MCP 도구 목록 확인. 도구 실행·모델 호출 없음 |
| down | 팀 개발 stack만 종료. 키·DB·기록은 보존 |

키·DB·합성 workspace는 저장소 경로와 RuntimeName별 새 Docker 볼륨에 보관한다.
호스트의 `artifacts/team-dev/<이름>`에는 비밀이 없는 준비·네트워크 메타데이터만 저장한다.
호스트 파일 ACL을 완화하거나 다른 개발자의 키를 복사하지 않는다.

Control은 `https://127.0.0.1:8130`, MCP는 `https://127.0.0.1:8140/mcp`다.
기본 stack은 `current_candidate_1` 정책을 읽으며 provider는 비활성화한다.
의미 분석이 필요한 호출은 모델을 우회하지 않고 실행을 거절한다.
공유 키가 있어도 기본 절차가 이를 읽거나 사용하지 않는다.
실제 Jev/actor 시험은 대상·한도·원장을 검토한 별도 명령으로 실행한다.
과거 handoff의 hash·상한·실행 명령을 신규 설치 명령으로 복사하지 않는다.

## 변경 반영과 환경 분리

소스를 수정한 뒤 test를 실행하고 `down`/`up`한다. 자동 reload는 사용하지 않는다.
의존성을 수정하면 build를 다시 한다. 정책 변경 시 기존 DB와 호환되는지도 확인한다.
현재 CA는 7일, 서비스 인증서는 2일이다. 만료됐거나 독립 DB가 필요하면 기존 stack을 내린 뒤
`-RuntimeName dev2`처럼 새 이름으로 prepare/up/check한다. 매 명령에 같은 이름을 전달한다.
포트 충돌 시 up/check에 `-ControlPort 8230 -GatewayPort 8240`처럼 같은 값을 전달한다.
이 경로는 전역 CA·개인 Codex 로그인·기존 서비스·예산을 수정하지 않는다.
up은 기존 Docker 서브넷 목록을 읽고 겹치지 않는 두 /24를 선택해 해당 runtime에 저장한다.
기존 네트워크를 삭제하거나 재구성하지 않는다. 호스트/VPN 경로와의 충돌까지 자동 검증하는 기능은 아니다.

## 먼저 볼 코드

| 대상 | 파일 |
|---|---|
| turn·출처·호출·승인·단회 실행 | `src/app/transparent/engine.py` |
| HTTP API·gateway 인가 | `src/app/transparent/server.py` |
| Jev HTTP·응답/confidence 계약 | `src/app/transparent/jev.py` |
| V5 행동 질문·판정 합성 | `src/app/transparent/jev_decision_v5.py`, `jev_core_v5p1.py` |
| 실제 파일 효과·서명 검증 | `src/app/transparent/upstream.py` |
| 실제 gateway·mTLS | `agentgateway/config.yaml` |
| DTAP 전용 범위·조회·shell 정책 | `src/app/benchmark/runtime_policy.py`, `task_scope.py` 등 |
| CLI hooks·MCP 전송 | `tools/hookgw_hook.py`, `mvp_demo_hook.py`, `mvp_demo_mcp.py` |

현재 제품 Jev 정책과 기본 런타임은 공통 `.50` 정상 허용 규칙을 사용한다. 위험 기준은 `.90`이다.
명시한 과거 정책과 동결된 시연 bundle은 별도다. 비교할 실제 policy ID를 기록한다.
팀원 자체 어댑터 연결은 README와 `docs/development/ENGINE_INTEGRATION.md`를 따른다.
기본 `python -m pytest`는 설정상 harness 시험만 선택하므로 제품 시험 경로를 명시해야 한다.
`team_dev.ps1 -Mode test`는 새 clone에서 실행 가능한 대표 제품 시험을 선택한다.
과거 실제 응답 replay 시험 일부는 비공유 `artifacts/`에 의존하므로 기본 목록에서 제외했다.
해당 자료를 검토된 비민감 fixture로 분리하기 전까지 전체 pytest 통과를 주장하지 않는다.
합성 모델 응답 시험은 연결·집행 검증이며 실제 Jev 정확도 증거가 아니다.

## 대시보드·변경 경계

화면 요구와 mock 예제는 `docs/handoffs/WP-DASHBOARD-01/TEAMMATE_HANDOFF.md`를 참고한다.
제안 API를 현재 구현으로 혼동하지 않는다. 현재 HTTP·인증은 `docs/development/TEAM_HANDOFF.md`를 본다.
DTAP 성적·실행 화면은 대시보드 범위에서 제외한다.

판정과 실행 결과를 분리한다. DENY를 승인으로 해제하지 않는다.
승인은 정확한 사용자 세션·도구·인자·정책에 결합해 단회 소비한다.
UNKNOWN은 자동 재실행·예산 환불하지 않는다. 출처 일치는 인과 증명이 아니다.
실제 키·토큰·개인키·개인 로그인·실행 DB·원본 로그를 커밋하지 않는다.
인증서 검증·mTLS·필수 저장 실패 시 실행 거부를 개발 편의로 끄지 않는다.
