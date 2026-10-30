# With Human — 배포·실행 패키지

사용자 요청·에이전트가 읽은 자료의 출처·도구 실행 후보를 검토해 ALLOW / DENY / ASK를 판정하는 로컬 보안 엔진입니다.
gate-6 정책, Jev 연동, Codex 연결기, 파일 실행기, 조회 대시보드가 포함됩니다. 소스 기준은 2026-10-30 로컬 작업본입니다.

## 실행 범위와 준비물

- 각 PC의 Docker에서 엔진·Gateway·실행기·대시보드 중계를 독립 실행합니다.
- 제품용 연결기로 연 Codex에 Docker 작업영역 `/files`의 `read_file` / `write_file`을 제공합니다.
- ASK 답변은 Codex의 실제 사용자 질문 양식으로 받고 재검토합니다. 대시보드는 조회 전용입니다.
- Docker Desktop(Linux containers), Python 3.12 이상, 본인의 Jev(TypeSafe) API 키 파일이 필요합니다.
- 에이전트 연결에는 로그인된 Codex CLI가 필요합니다. 확인한 Windows CLI는 0.154.0입니다.
- 실제 의미 분석은 외부 Jev로 데이터를 전송하며 요금이 발생할 수 있습니다. 요청·토큰 과금 상한은 기본적으로 두지 않습니다.
- 키는 텍스트 편집기로 저장소 밖의 파일에 한 줄로 저장하세요. 실제 키 값을 명령어·Git·프롬프트에 넣지 마세요.
- ZIP의 `with-human` 폴더에서 실행합니다. 호스트 연결기는 Python 표준 라이브러리를 사용하며 별도 pip 설치가 필요하지 않습니다.

## Windows 실행

PowerShell에서 키 경로를 실제 경로로 바꿔 실행합니다. `prepare`는 신규 runtime 이름으로 처음 한 번만 실행합니다.

```powershell
.\scripts\product_codex.ps1 -Mode prepare -RuntimeName local -JevKeyFile C:\Private\jev.api-key
.\scripts\product_codex.ps1 -Mode up -RuntimeName local
.\scripts\team_dev.ps1 -Mode check -RuntimeName local
.\scripts\dashboard_local.ps1 -RuntimeName local
```

대시보드: http://127.0.0.1:8150/ . 새 설치에서는 과거 이력 없이 시작합니다.
엔진·대시보드만 실행할 때는 Codex가 필요 없습니다. 연결하려면 이어서 실행합니다.

```powershell
.\scripts\product_codex.ps1 -Mode check -RuntimeName local
.\scripts\product_codex.ps1 -Mode start -RuntimeName local
```

Python 또는 Codex가 PATH에 없으면 `-PythonPath` / `-CodexPath`로 설치 경로를 지정합니다.
기존 Hook 설정이 충돌하면 덮어쓰지 않고 중단합니다. 사용자 로그인·모델·sandbox는 유지합니다.
사용자 요청은 연결기로 연 Codex에 입력합니다. 호스트 PC의 모든 도구·파일을 자동 보호하는 구조는 아닙니다.

```powershell
# Codex에서 먼저 /exit한 뒤 조회·종료합니다.
.\scripts\product_codex.ps1 -Mode history -RuntimeName local
.\scripts\product_codex.ps1 -Mode security -RuntimeName local
.\scripts\dashboard_local.ps1 -Mode stop -RuntimeName local
.\scripts\product_codex.ps1 -Mode down -RuntimeName local
```

## macOS/POSIX 실행

저장소 밖에 본인의 키 파일을 준비하고 파일·부모 폴더 권한을 각각 600, 700으로 설정합니다.

```sh
chmod 700 "$HOME/.with-human-secrets"
chmod 600 "$HOME/.with-human-secrets/jev.api-key"
python3 tools/product_local.py prepare --runtime local --jev-key-file "$HOME/.with-human-secrets/jev.api-key"
python3 tools/product_local.py up --runtime local
python3 tools/product_local.py check --runtime local --engine-only
python3 tools/product_local.py dashboard --runtime local
python3 tools/product_local.py check --runtime local
python3 tools/product_local.py start --runtime local
```

`--codex-path`로 설치 경로를 지정할 수 있습니다. `history`, `security`, `dashboard-stop`, `down`도 같은 `--runtime`으로 실행합니다.
Windows 연결·ASK·대시보드 동작을 확인했습니다. macOS 진입점은 포함하지만 실제 Mac의 Codex/ASK UI는 미검증입니다.

## 구성과 연결 인터페이스

| 경로 | 역할 |
|---|---|
| `src/app/transparent/engine.py`, `server.py` | 세션·출처·권한·판정·집행·조회 API |
| `src/app/transparent/jev_gate6.py`, `gate_policy.py`, `jev.py` | gate-6 정책, Jev 전송·응답 검증 |
| `tools/product_codex.py`, `hookgw_*.py` | Codex Hook·MCP 연결 및 사용자 질문 응답 |
| `src/app/transparent/upstream.py` | 등록된 파일 도구 실행과 중복 실행 방지 |
| `src/app/dashboard_local.py`, `src/app/web/observatory/` | 브라우저 중계와 대시보드 |
| `agentgateway/config.yaml`, `compose.yaml` | mTLS·집행 중계와 서비스 실행 |
| `docs/mvp/contracts/` | 실행 중 사용하는 요청·응답 검증 JSON 4개 |

기본 주소는 Control `https://127.0.0.1:8130`, Gateway `https://127.0.0.1:8140/mcp`입니다.
역할별 토큰과 로컬 CA 검증을 사용하고 Gateway 내부 통신은 mTLS로 보호합니다. 자격은 각 PC에서 생성합니다.
조회 API는 `/dashboard/v1/status`, `/dashboard/v1/summary`, `/dashboard/v1/events`,
`/dashboard/v1/events/{event_id}`, `/dashboard/v1/security`입니다. 브라우저에는 엔진 토큰을 넣지 말고 로컬 중계를 사용합니다.
문서·요청 미리보기는 민감정보를 마스킹한 텍스트이며 실제로 실행하지 않습니다.

SQLite의 주요 테이블은 `sessions`, `turns`, `sources`, `calls`, `transport`, `asks`, `audit`입니다.
주요 원문 문맥은 암호화하지만 DB 파일 전체와 작업영역 파일 전체를 암호화하는 것은 아닙니다.
기본 세션 보존은 1일, 원문 이력은 7일입니다. `down`은 DB·사용량 volume을 삭제하지 않습니다.

## 운영 범위와 현재 제한

- 개발·API 설명서, 보안검토 보고서·SBOM·검사 로그, 테스트·실험 자료, 참고 PDF, 개인 키·인증서·DB·로그·Git 이력은 포함하지 않습니다. `docs`에는 실행 시 읽는 계약 JSON 4개만 있습니다.
- 기본 파일 도구 제품의 배포·운영 경로만 제공합니다. npm 실험·시나리오 실행과 개발용 테스트 빌드 모드는 포함하지 않습니다.
- `npm_lab.py`, `demo_approval.py`, `demo_report.py`, 이전 Jev 보조 모듈은 현재 제품의 import 의존성이므로 남겼습니다.
- 누적 출처 근거 8개 초과 등 문맥 제한으로 정상 작업도 분석 불가·DENY가 될 수 있는 미해결 문제가 있습니다. 분석 오류는 공격 탐지 성공이 아닙니다.
- 에이전트 식별과 Gateway/Upstream 생존 상태는 미수집이면 UNKNOWN으로 표시합니다.
- 준비·점검은 모델을 호출하지 않습니다. 공급자가 키를 실제 수락하는지는 의미 분석 요청 때 확인됩니다.
- 기본 leaf 인증서는 2일, CA는 7일입니다. 만료 시 TLS 검증을 끄지 말고, 기존 볼륨과 이력을 보존한 채 새로운 RuntimeName으로 prepare/up 하여 새 인증서를 발급합니다.
