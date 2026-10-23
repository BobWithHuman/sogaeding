# sogaeding · With Human 엔진

사용자 요청·서버가 수집한 출처·도구 호출 후보를 연결해 실행 전에 ALLOW/DENY/CONFIRM을 판정하는 Python 엔진이다.
이 저장소의 엔진을 clone하고 팀원이 자체 어댑터·실행기를 연결해 DTAP으로 OFF/ON 평가한다.

## 현재 기본 정책

**정상 허용 기준은 .50, 위험 DENY 기준은 .90이다.**
검증된 A의 원래 선택이 WITHIN_TASK이고, B가 LEGITIMATE이며 유효 확신도 .50 이상이어야 정상 ALLOW 후보다.
권한·도구 schema·출처 무결성·단회 실행 예약도 통과해야 한다.
A가 업무 밖/불확실이거나 B 확신도가 부족한 경우, 실제 동의가 필요한 경우에는 CONFIRM이 남는다.

공통 규칙은 `src/app/transparent/candidate_policy.py`에 있다.
현재 제품 Jev 정책과 기본 RuntimePolicy에 연결돼 있어 별도 .50 프로필을 켤 필요가 없다.
과거 정책을 명시적으로 선택하거나 동결된 시연 bundle을 쓰면 해당 버전이 적용된다.

## 1. clone하고 무모델 시험하기

Git, Windows PowerShell 5.1 이상, Docker Desktop의 Linux containers를 준비한다.
호스트 Python이나 다른 개발자의 키·DB·Docker 볼륨은 필요하지 않다.

```powershell
git clone https://github.com/BobWithHuman/sogaeding.git
cd sogaeding
.\scripts\team_dev.ps1 -Mode build
.\scripts\team_dev.ps1 -Mode test
```

- build: Python 3.12와 잠금 의존성을 설치한 개발 이미지를 만든다.
- test: 네트워크를 차단한 컨테이너에서 기본 .50 정책·Jev 응답 검증·승인·인증·단회 예약을 시험한다.
- **여기까지 모델 호출·API키·과금은 없다.** 현재 게시 후보의 깨끗한 checkout에서 141개 시험이 통과했다.
- 이미 clone했다면 `git pull --ff-only` 후 시험한다. 의존성이 바뀌면 build도 다시 한다.

Linux/macOS에서는 기본 정책 시험을 다음처럼 실행할 수 있다.

```bash
docker build --target dev -f Dockerfile.dev -t sogaeding-team-dev:local .
docker run --rm --network none --read-only --tmpfs /tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src:/workspace/tests/hookgw:/workspace/tools \
  -e CONTRACT_DIR=/workspace/docs/mvp/contracts \
  -v "$PWD:/workspace:ro" -w /workspace sogaeding-team-dev:local \
  python -m pytest -q -p no:cacheprovider tests/hookgw/test_default_candidate_policy.py
```

전체 시험은 두 번에 나눠 실행한다. hardening 시험은 acceptance 시험과 같은 포트로 제품을 띄우므로 따로 돌린다.
두 명령 모두 깨끗한 clone에서 로컬 산출물·키·모델 호출 없이 통과한다.

```bash
T="docker run --rm --network none --read-only --tmpfs /tmp:exec -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src:/workspace/tests/hookgw:/workspace/tools \
  -e CONTRACT_DIR=/workspace/docs/mvp/contracts -v $PWD:/workspace:ro -w /workspace \
  sogaeding-team-dev:local python -m pytest -q -p no:cacheprovider"
$T tests --ignore=tests/hardening
$T tests/hardening
```

## 2. 자체 어댑터 연결하기

| 용도 | 진입점 |
|---|---|
| 등록 파일 MCP 제품 엔진 | `app.transparent.engine.Engine` + `app.transparent.jev_config.make_policy(jev_client)` |
| DTAP 등 새 schema를 연결하는 런타임 | `app.benchmark.registry.Registry` + `app.benchmark.runtime_policy.RuntimeEngine` / `RuntimePolicy` |
| 공통 .50 허용 규칙 | `app.transparent.candidate_policy` |
| 현재 A/B 질문 | `app.transparent.candidate_questions` |

1. 실제 사용자 턴, 원 도구의 schema/identity와 인자를 연결한다.
2. 도구 결과·설명을 서버가 수집해 원문/hash/완전성/수집 역할을 보존한다.
3. 실제 환경에서 검증한 자원·효과 권한을 연결한다. 외부 문서의 승인 주장은 권한이 아니다.
4. `turn → register → authorize → forward → 원 도구 실행 → transport_observed/observe` 흐름을 유지한다.
5. DENY·미승인 CONFIRM·필수 분석 실패에서 실행하지 않는다. 정책 함수의 ALLOW만 보고 직접 실행하지 않는다.

기본 RuntimePolicy의 완화된 허용 경로에는 서버가 검증한 정확한 권한이 필요하다.
제품 서버는 `HOOKGW_PDP=JEV`일 때 profile 생략 시 현재 Jev 정책을 선택한다.
등록 파일 제품 정책 밖 native 도구에 새로운 권한을 부여하는 변경은 아니다.

자세한 입력·권한·집행 계약은 [엔진 연결 안내](docs/development/ENGINE_INTEGRATION.md)를 따른다.

## 3. DTAP 평가하기

DTAP 원 데이터셋과 actor 모델, Jev 키·요청 예산은 각자 새 로컬 환경에서 설정한다.
이 게시본에는 기존 개발자의 키·로그인·실행 DB·원본 로그·데이터셋이 없다.
AgentDojo/Gemini 전용 실행기도 이번 게시에 포함하지 않는다.

같은 과업·공격·초기 환경으로 OFF/ON을 비교하고 다음을 각각 기록한다.

- 공격 성공과 원래 업무 성공
- 코드 DENY와 Jev 의미 DENY, 해당 도구의 실제 실행 여부
- CONFIRM, UNKNOWN, 오류, 미시작
- OFF에서 공격 성공한 사례가 ON에서 방어됐는지

무모델 시험 통과를 실제 Jev 정확도나 방어율로 해석하지 않는다.
모든 native 도구·모든 IPI 보호, 실제 벤치마크 방어 성능은 별도 검증 대상이다.

macOS에서 actor를 **Claude Code CLI(본인 구독 로그인, API 키 미사용)**로 돌리는 실행기는
`tools/dtap_claude_code.py`다. 준비·실행 명령과 제약은
[Claude Code DTAP 실행 안내](docs/handoffs/WP-DTAP-CC-01/USER_RUN.md)를 따른다.

## gateway 연결이 필요할 때

자체 Python 어댑터 평가에 Compose 파일을 모두 사용할 필요는 없다.
제품 HTTP/TLS gateway 경로도 연결하려면 build/test 이후 실행한다.

```powershell
.\scripts\team_dev.ps1 -Mode prepare
.\scripts\team_dev.ps1 -Mode up
.\scripts\team_dev.ps1 -Mode check
```

Control은 `https://127.0.0.1:8130`, MCP는 `https://127.0.0.1:8140/mcp`다.
prepare는 새 전용 Docker 볼륨에 PKI·역할별 토큰·합성 workspace를 만든다.
check는 TLS/gateway/MCP 연결과 인증 거절을 확인하며 모델 호출은 하지 않는다.
기본 provider는 비활성이다. 실제 Jev 호출은 별도 키·정책·예산 설정이 필요하다.
종료는 `.\scripts\team_dev.ps1 -Mode down`이며 키·DB는 보존한다.

## YAML과 코드 위치

소스의 YAML은 17개다. 현재 팀 개발은 `compose.team.yaml`을 기준으로 한다.
나머지는 gateway 설정·과거 시연 revision·회귀 검증·Jev 연결 예시다.
[파일별 용도](docs/development/CONFIG_FILES.md)를 참고한다.

| 경로 | 내용 |
|---|---|
| `src/app/transparent/` | 현재 엔진·Jev·출처·승인·실행 상태 |
| `src/app/benchmark/` | schema 등록·런타임 정책·기존 DTAP 연결 부품 |
| `agentgateway/` | HTTPS/mTLS·실행 전 인가 |
| `tests/`, `fixtures/` | 시험과 합성 자료 |
| `docs/mvp/` | 요구·설계·API·보안/수용 기준, `contracts/`에 이벤트·도구·상태 계약 |
| `docs/security/` | 보안 가이드 적용표·보안 기준·설계 결정(ADR)·보안 진단과 조치 기록(`hardening/`) |
| `docs/handoffs/WP-DTAP-CC-01/` | Claude Code DTAP 실행 안내·결과·검토 |
| `harness/dtap-cc/` | DTAP 과업 목록과 실행기 의존성 잠금 |

[상세 개발 환경](CONTRIBUTING.md) · [엔진 연결 계약](docs/development/ENGINE_INTEGRATION.md)
