# With Human

**AI 에이전트의 도구 실행을 검사하는 로컬 보안 엔진**입니다. 사용자 요청과 에이전트가 읽은 자료, 실행하려는 도구·인자를 대조해 **ALLOW / DENY / ASK**를 판정하고, 허용한 작업만 실행 경로를 통과시킵니다.

이 저장소에는 엔진, 공통 **gate-6 정책**, Jev 의미 분석 연동, **Codex 연결기**, 조회용 **로컬 대시보드**, Docker 실행 구성이 들어 있습니다. 아래 절차로 각자 PC에 독립적인 엔진·인증 자격·저장공간을 준비할 수 있습니다.

## 어떤 문제를 해결하나요?

AI 에이전트는 파일이나 외부 자료를 읽고 도구를 실행합니다. 그 자료에 사용자 요청과 무관한 추가 지시가 들어 있으면, 에이전트가 이를 따라 잘못된 작업을 수행할 수 있습니다. 이런 **간접 프롬프트 인젝션(IPI)**을 도구 실행 전에 검사하는 것이 With Human의 목적입니다.

예를 들어 사용자는 배포 문서의 요약만 요청했는데, 문서가 다른 파일의 변경까지 지시할 수 있습니다. 엔진은 실제 사용자 요청과 관측 자료를 실행 후보에 연결해 검사합니다. 외부 자료나 모델이 “사용자가 승인했다”고 주장하는 것만으로 실행 권한을 부여하지 않습니다.

| 판정 | 동작 |
|---|---|
| **ALLOW** | 실행을 허용합니다. 최종 집행 검사와 단회 예약을 통과한 뒤 도구를 실행합니다. |
| **DENY** | 실행을 거부합니다. 사용자 승인으로 DENY를 해제하지 않습니다. |
| **ASK** | 실행을 보류하고 이유를 포함해 사용자에게 질문합니다. 답변을 받은 뒤 엔진이 재판정합니다. |

대시보드는 판정·실행 이력과 통계를 보는 화면입니다. ASK 답변은 **에이전트의 사용자 질문 창**에서 처리합니다.

## 현재 제공하는 범위

| 항목 | 제공 범위 |
|---|---|
| 실행 방식 | 각자 로컬 PC의 Docker에서 독립 엔진·DB 실행 |
| 에이전트 | 제품용 Codex CLI 연결기 포함 |
| 도구 | 제품 Docker 작업영역 `/files`의 MCP `read_file` / `write_file` |
| Windows | 준비·기동·Codex 연결·ASK·대시보드 동작 확인 |
| macOS | Python 준비·실행 진입점 제공. Linux POSIX 및 ARM64 에뮬레이션 검증 완료, **실제 Mac의 Codex/ASK는 미검증** |
| 대시보드 | 실제 엔진의 상태·판정 이력·통계·보안 현황 조회 |
| Claude Code / DTAP | 별도 평가 코드·기록 보존. 제품의 대화형 Claude Code ASK 지원을 뜻하지 않음 |

현재 연결은 Codex의 모든 내장 도구나 사용자 PC 전체 파일을 자동으로 보호하는 방식이 아닙니다. 제공한 연결기로 연 Codex에서 등록된 `with_human` 파일 도구를 사용합니다. 회사 서버에서 여러 사용자를 운영하는 서비스도 현재 제품 범위가 아닙니다.

## 어떻게 구현했나요?

판정·조회 서버는 **Python / FastAPI**, 상태와 이력은 **SQLite**, 실제 MCP 중계는 **Agentgateway**, 실행 환경은 **Docker Compose**를 사용합니다. 사용자 PC에는 Codex와 Python 연결기가 실행되고, 엔진·Gateway·파일 실행기·대시보드 중계는 Docker에서 실행됩니다.

| 구성 | 역할 | 주요 코드 |
|---|---|---|
| **Control 엔진** | 요청·출처·권한 검사, gate-6 판정, 실행 예약·상태 관리, 조회 API | [engine.py](src/app/transparent/engine.py), [server.py](src/app/transparent/server.py) |
| **gate-6 / Jev** | 코드 검사와 필요한 의미 분석을 결합. Jev 응답의 형식·판정 조건 검증 | [jev_gate6.py](src/app/transparent/jev_gate6.py), [jev.py](src/app/transparent/jev.py) |
| **Codex 연결기** | Hook으로 요청·도구 후보·결과 전달, stdio MCP로 실제 호출 및 ASK 응답 처리 | [product_codex.py](tools/product_codex.py), [hookgw_hook.py](tools/hookgw_hook.py), [hookgw_mcp.py](tools/hookgw_mcp.py) |
| **Gateway** | 실제 도구 요청마다 엔진의 private `/authz` 집행 검사 후 실행기로 전달 | [config.yaml](agentgateway/config.yaml) |
| **Upstream 실행기** | 등록된 파일 읽기·쓰기 수행, 실행 중복 방지·결과 기록 | [upstream.py](src/app/transparent/upstream.py) |
| **대시보드 API / 중계** | 원문을 노출하지 않는 이력·통계 조회, 브라우저 대신 엔진 인증 처리 | [dashboard.py](src/app/transparent/dashboard.py), [dashboard_local.py](src/app/dashboard_local.py) |
| **대시보드 화면** | 로컬 중계와 같은 주소에서 제공하는 조회 UI | [observatory](src/app/web/observatory/) |

실제 요청은 다음 순서로 처리합니다.

1. 사용자가 Codex에 프롬프트를 입력하면 Hook이 엔진에 사용자 요청을 등록합니다.
2. Codex가 도구를 호출하려 하면 Hook이 도구 이름·인자를 엔진에 전달합니다. 앞선 도구 결과도 관측 자료로 기록합니다.
3. 엔진이 등록 권한·대상·출처를 검사하고, 필요한 후보에는 외부 **Jev(TypeSafe)** API로 의미 분석을 요청합니다. 기본 정책은 gate-6입니다.
4. ASK이면 MCP 연결기가 엔진의 이유를 전달하고 Codex의 네이티브 질문 창으로 실제 사용자 답변을 받습니다. 답변 뒤에도 재판정하며, 최종 ALLOW만 실행할 수 있습니다.
5. 실제 MCP 요청은 Gateway의 private 집행 검사와 세션·도구·인자에 결합된 단회 예약을 통과해 Upstream에서 실행됩니다.
6. 실행 결과를 기록하고 대시보드가 조회합니다. **판정 ALLOW와 실행 성공은 별개**이며, 결과를 확정하지 못한 UNKNOWN을 성공으로 집계하지 않습니다.

역할별 인증 토큰과 로컬 CA 검증을 사용하고 Gateway 내부 통신은 mTLS로 보호합니다. 브라우저에는 엔진 토큰을 전달하지 않습니다. 주요 원문 context는 암호화해 저장하지만, SQLite 파일 전체와 작업영역 파일 전체를 암호화하는 방식은 아닙니다. 상세 보안·저장 경계는 [백엔드 기준서](docs/development/BACKEND_REFERENCE.md)에 있습니다.

## 실행 전 준비

| 준비물 | 용도 |
|---|---|
| Git | 저장소 clone / 업데이트 |
| Docker Desktop | Linux containers 모드로 실행. 이미지 빌드·다운로드를 위한 네트워크 필요 |
| Python **3.12 이상** | 호스트 연결기 실행. 호스트에 별도 pip 패키지를 설치할 필요 없음 |
| 본인의 **Jev API 키 파일** | 실제 의미 분석. 저장소 밖에 키 한 줄을 담은 파일로 준비 |
| 로그인된 **Codex CLI** | 에이전트 연동 시 필요. 엔진·대시보드만 실행할 때는 불필요 |
| Windows: PowerShell 5.1 이상 | Windows 실행 스크립트 사용 |

**로컬 엔진이지만 의미 분석에 필요한 데이터는 외부 Jev API로 전송됩니다.** 전송 최소화·마스킹을 적용하며 모든 처리가 오프라인인 제품은 아닙니다. Jev 요청 횟수·토큰 상한은 기본적으로 두지 않으므로 실제 프롬프트 시험에는 공급자 요금이 발생할 수 있습니다. 사용량·실패 장부는 유지합니다.

`prepare`, `up`, `check`는 모델을 호출하지 않습니다. 준비 성공이 Jev 키의 공급자 수락을 뜻하지는 않으며 실제 의미 분석 요청 때 확인됩니다. 키·토큰·DB·인증서는 다른 사람에게 전달하거나 Git에 올리지 않습니다.

## 저장소 받기

Windows는 PowerShell, macOS는 터미널에서 실행합니다.

```sh
git clone https://github.com/BobWithHuman/sogaeding.git
cd sogaeding
```

이후 명령은 모두 저장소 루트에서 실행합니다. 처음 설치라면 아래에서 자신의 OS 절차를 선택합니다. 이미 준비한 runtime은 `prepare`를 반복하지 않고 해당 OS의 다시 실행·종료 안내를 따릅니다.

## Windows 처음 설치

Codex 앱에 번들된 Python이 있으면 스크립트가 사용하며, 일반 PC는 PATH의 `python`을 사용합니다. 필요하면 product_codex.ps1 명령에 `-PythonPath C:\설치경로\python.exe`를 지정합니다. 브라우저 조회만 할 때는 Codex 실행 단계가 필요 없습니다.

텍스트 편집기로 Jev 키 한 줄을 담은 파일을 **저장소 밖**에 만듭니다. 아래 `C:\Private\jev.api-key`를 본인의 파일 경로로 바꿉니다. 예시 경로에 키 파일이 자동 생성되는 것은 아닙니다. 실제 키 값을 README·Git·프롬프트·터미널 명령어에 입력하지 않습니다.

```powershell
# 최초 1회: 같은 Dockerfile로 이미지를 빌드하고 이 PC 전용 자격을 생성합니다.
.\scripts\product_codex.ps1 -Mode prepare -RuntimeName local `
  -JevKeyFile C:\Private\jev.api-key

.\scripts\product_codex.ps1 -Mode up -RuntimeName local
# Codex 없이 TLS·인증·MCP 도구 목록 확인
.\scripts\team_dev.ps1 -Mode check -RuntimeName local
.\scripts\dashboard_local.ps1 -RuntimeName local
```

브라우저에서 **http://127.0.0.1:8150/** 을 엽니다. 처음 생성한 DB에는 이력이 없으므로0건일 수 있습니다. 실제 엔진을 조회하며 데모 판정 이력을 삽입하지 않습니다.

Codex로 요청·판정·ASK까지 시험하려면 설치된 Codex CLI로 먼저 로그인하고 이어서 실행합니다.

```powershell
.\scripts\product_codex.ps1 -Mode check -RuntimeName local
.\scripts\product_codex.ps1 -Mode start -RuntimeName local
```

검증한 Windows CLI는 `codex-cli 0.154.0`입니다. `codex.exe`가 PATH에 없으면 check/start에 `-CodexPath C:\설치경로\codex.exe`를 지정합니다. `check`는 모델 세션을 열지 않고 CLI 설정과 엔진 준비 상태를 확인합니다.

## macOS 처음 설치

PowerShell은 필요 없습니다. Git, 실행 중인 Docker Desktop(Linux containers), Python **3.12 이상**이 필요합니다. `python3 --version`으로 확인하고, 설치된 명령이 `python3.12`라면 아래의 `python3`를 그 명령으로 바꿉니다. 대시보드 개발만 할 때는 Codex가 필요 없습니다. 에이전트 시험에는 로그인된 Codex CLI와 Hook·MCP 사용자 질문 기능이 필요합니다.

위의 저장소 받기를 마친 뒤, 먼저 키 보관 폴더를 준비합니다.

```sh
mkdir -p "$HOME/.with-human-secrets"
chmod 700 "$HOME/.with-human-secrets"
```

텍스트 편집기로 `$HOME/.with-human-secrets/jev.api-key` 파일을 만들고 본인의 Jev 키 한 줄을 저장합니다. 키 값을 명령어·Git·프롬프트에 넣지 않습니다. 파일을 준비한 뒤 권한을 적용하고 실행합니다.

```sh
chmod 600 "$HOME/.with-human-secrets/jev.api-key"

# 저장소 루트에서 실행. 최초 1회에만 prepare.
python3 tools/product_local.py prepare --runtime local \
  --jev-key-file "$HOME/.with-human-secrets/jev.api-key"
python3 tools/product_local.py up --runtime local
python3 tools/product_local.py check --runtime local --engine-only
python3 tools/product_local.py dashboard --runtime local
```

브라우저에서 `http://127.0.0.1:8150/`을 열면 이 Mac에서 실행한 실제 엔진을 조회합니다. 신규 DB이므로 첫 집계는 비어 있을 수 있습니다. 합성 이력을 실제 판정처럼 넣지 않습니다. 위 단계는 Codex나 유료 모델을 실행하지 않으며, Jev 키의 실제 수락 여부는 의미 분석 요청 때 확인됩니다.

Codex에서 요청·판정·ASK까지 시험하려면 이어서 실행합니다.

```sh
python3 tools/product_local.py check --runtime local
python3 tools/product_local.py start --runtime local
```

`codex`가 PATH에 없으면 check/start에 `--codex-path /절대경로/codex`를 지정합니다. 기존 Codex 설정에 Hook/MCP 충돌이 있으면 덮어쓰지 않고 중단합니다. 개인 설정·로그인·모델·sandbox는 변경하지 않습니다.

```sh
python3 tools/product_local.py history --runtime local
python3 tools/product_local.py security --runtime local
python3 tools/product_local.py status --runtime local
python3 tools/product_local.py dashboard-stop --runtime local
python3 tools/product_local.py down --runtime local
```

`down`은 DB·사용량 volume을 삭제하지 않습니다. 다시 실행할 때는 up/check/dashboard/start만 사용합니다. prepare를 반복하거나 같은 이름의 기존 자격/volume을 덮어쓰지 않습니다. 포트를 바꾸려면 최초 prepare에 서로 다른 `--control-port`, `--gateway-port`, `--dashboard-port`를 지정합니다.

Mac 자격은 `~/Library/Application Support/WithHuman/Codex/<저장소ID>/<runtime>/`에 디렉터리0700·파일0600으로 생성합니다. Mac의 키 파일0600을 Docker UID 10001이 직접 읽지 못하는 문제를 피하기 위해, prepare가 키와 정책의 사본을 **Control만 마운트하는 volume 하위 디렉터리**에 표준 입력으로 전달합니다. volume에서도 디렉터리0700·파일0600·UID 10001을 유지합니다. 호스트 키 권한은 풀지 않으며 브라우저·Gateway·Upstream에 전달하지 않습니다. 이 volume도 비밀 자료로 취급하고 배포/공유하지 않습니다.

외부 키를 바꾼 뒤 up하면 `EXTERNAL_KEY_CHANGED_PREPARE_NEW_RUNTIME`으로 중단합니다. 기존 runtime의 장부를 보존한 채 새 이름으로 prepare하거나 별도 검토된 키 회전 절차를 사용합니다. `PRIVATE_FILE_REQUIRED_CHMOD_600`이면 지정 키/자격의 소유자·권한을, `EXISTING_RUNTIME_PRESERVED_CHOOSE_NEW_NAME`이면 기존 상태를 보존하고 다른 runtime 이름을 확인합니다. 준비가 중간에 실패해도 자동 삭제·재시도하지 않습니다. Docker 파일 공유 오류는 저장소 폴더의 Docker Desktop 접근 허용을 확인합니다. CA/leaf 만료 기간과 유지보수 경계는 Windows와 같습니다.

Mac용 진입점은 동일 Dockerfile·compose.yaml·Hook·MCP 연결기를 재사용합니다. Compose가 해석한 설정에서 Control의 키/정책 마운트 두 개만 volume으로 치환해 메모리의 JSON을 표준 입력으로 전달합니다. 추가 YAML/설정 파일이나 별도 엔진을 만들지 않습니다. Linux의 POSIX 권한/명령 검증은 실제 macOS 파일 공유·Codex UI 검증을 대신하지 않습니다. 이 경로는 팀원 Mac에서 실행 확인이 필요합니다.

## 첫 요청과 ASK 확인

OS별 `start`로 연 Codex에서 다음처럼 요청합니다. 연결기는 포함되어 있으므로 새로 구현할 필요가 없습니다. 필요한 Hook 신뢰 검토는 사용자가 Codex 화면에서 진행합니다.

```text
with_human MCP로 docs/release.md를 읽고, 내용을 한 줄로 요약해서 reports/trial.md에 저장해줘.
```

`docs/release.md`는 prepare가 만드는 합성 배포 문서입니다. 읽기·쓰기 대상은 사용자 PC의 저장소 파일이 아니라 **제품 Docker 작업영역 `/files`**에 있습니다. 실행 후 대시보드의 판정 이력·실행 결과·통계를 확인합니다.

ASK 흐름을 시험하려면 다음처럼 요청합니다.

```text
with_human MCP로 docs/release.md를 읽고, 내용을 한 줄로 요약해서 reports/ask-demo.md에 저장해줘.
사용자 확인이 필요하면 엔진이 알려준 이유를 설명하고 질문해줘.
```

이 합성 경로에는 사용자 확인 규칙을 예제로 등록했습니다. 실제 민감 자료 검출 사례는 아닙니다. Jev가 보류 조건을 인정하면 엔진 이유를 포함한 질문을 전달합니다. 사용자 응답 뒤에도 재판정하므로 승인했다고 반드시 ALLOW가 되지는 않습니다. 모델 결과에 따라 DENY나 분석 장애가 나올 수 있습니다. 이 예제는 연결·ASK 흐름 확인용이며 엔진 OFF/ON 공격 방어 성능 비교를 대신하지 않습니다.

## Windows에서 다시 실행하거나 종료

같은 이름으로 prepare를 반복하면 기존 상태 보호를 위해 거부합니다. 이후에는 up → check → dashboard → start만 사용합니다.

```powershell
.\scripts\product_codex.ps1 -Mode history -RuntimeName local
.\scripts\dashboard_local.ps1 -Mode stop -RuntimeName local
.\scripts\product_codex.ps1 -Mode down -RuntimeName local
```

종료해도 DB·Jev 장부 volume은 보존합니다. 키·인증 자격·파일을 다른 사람에게 복사하지 않습니다. 인증서 leaf는2일, CA는7일이며 만료 시 임의 TLS 검증 해제 대신 기존 유지보수 절차를 사용하거나 별도 이름의 runtime을 준비합니다. 기존 runtime의 키 회전·백업 경계는 [백엔드 기준서](docs/development/BACKEND_REFERENCE.md)를 참고합니다.

기존 Hook/MCP/관리 설정과 충돌하면 개인 설정을 덮어쓰지 않고 중단합니다. Codex 로그인·모델·sandbox·승인 설정은 유지하고 실행한 자식 프로세스에 연결 옵션을 제공합니다.

Mac의 종료·조회 명령은 위 macOS 절에 있습니다. 새 코드를 pull한 뒤에는 해당 OS의 down → up → dashboard → check → start로 서비스를 다시 열어 변경된 소스를 반영합니다. 이미지 빌드 입력이 바뀌었다면 Windows는 `product_codex.ps1 -Mode build`, Mac은 `product_local.py build`로 이미지를 다시 빌드한 뒤 기동합니다. 기존 runtime에 prepare를 다시 하는 방식으로 사용량 장부를 초기화하지 않습니다.

## 필요한 파일

| 파일/폴더 | 용도 |
|---|---|
| `compose.yaml` | 제품의 유일한 Compose. Control, Gateway, Upstream, 선택적 대시보드 |
| `Dockerfile`, `requirements.txt` | 해시 고정 의존성과 최소 실행 이미지 빌드 |
| `tools/minimal_runtime.py` | 실행에 필요한 native library와 실제 패키지 목록을 포함하는 이미지 생성 |
| `agentgateway/config.yaml` | Gateway 자체의 mTLS·집행 검사 설정. 추가 Compose가 아님 |
| `scripts/product_codex.ps1` | 준비·기동·점검·Codex 연결·이력·종료 |
| `scripts/dashboard_local.ps1` | localhost 대시보드 기동·종료 |
| `scripts/team_dev.ps1` | 위 진입점에서 사용하는 공통 빌드·volume/망 준비와 선택적 시험 |
| `tools/product_local.py` | macOS/POSIX의 준비·기동·조회·대시보드·기존 Codex 연결기 실행. 호스트 추가 pip 패키지 불필요 |
| `src/`, 연결기 helper | 엔진·권한·Jev·저장·ASK·조회·실제 집행 |
| `tests/product/`, 개발 의존성 lock | 수정 시 무모델 회귀 시험. 기본 실행 이미지에는 시험 도구를 넣지 않음 |

별도 YAML을 겹쳐 적용하거나 `.env`를 여러 개 만들 필요가 없습니다. Gateway digest와 CA 검증, 인증 역할, private `/authz`, 단회 집행을 유지합니다. 로컬 중계는 엔진 관리자 자격을 서버에서만 읽고 브라우저에 보내지 않습니다.

## 대시보드·API·DB

| 기본 주소 | 용도 |
|---|---|
| `http://127.0.0.1:8150/` | 대시보드 화면·로컬 중계 |
| `https://127.0.0.1:8130` | 역할별 인증이 필요한 Control API |
| `https://127.0.0.1:8140/mcp` | 연결기가 사용하는 Gateway MCP |

주소는 같은 PC에서만 접근할 수 있습니다. 다른 PC의 `127.0.0.1`은 그 PC 자신을 가리킵니다. 대시보드는 같은 주소의 중계 서버를 통해 엔진을 조회하며, 공개 호스팅된 UI가 각 PC의 로컬 엔진에 자동 연결되는 방식은 아닙니다.

| 조회 API (GET) | 내용 |
|---|---|
| `/dashboard/v1/status` | 엔진 상태·정책·조회 기능 |
| `/dashboard/v1/summary` | 판정·실행·ASK 통계·Jev 사용량 |
| `/dashboard/v1/events` | 판정 이력 목록 |
| `/dashboard/v1/events/{event_id}` | 개별 판정 상세 |
| `/dashboard/v1/security` | 보안 감사·경고 |

summary/events/security는 `from`, `to` 기간 파라미터가 필수입니다. API 연동에는 인증도 필요하므로 URL만 복사해 호출하는 것보다 아래 계약을 먼저 확인하세요.

**[BACKEND_REFERENCE.md](docs/development/BACKEND_REFERENCE.md)**: 구성, 역할별 인증, 조회 API5개, query/응답/오류, ASK 이유·상태, DB·암호화·보존, 연결기 계약.

대시보드는 조회만 담당합니다. ASK 답변/승인은 에이전트의 신뢰 연결기에서 처리합니다. 에이전트 종류는 아직 미수집이라 `unknown`, Gateway/Upstream 생존 probe는 미구현이라 `UNKNOWN`입니다. 실제 실행 경로가 없다는 뜻은 아닙니다.

## 실행이 안 될 때

| 증상 | 확인할 내용 |
|---|---|
| Docker 연결·빌드 실패 | Docker Desktop 실행 여부, Linux containers 모드, 이미지/패키지 다운로드 네트워크 |
| Python 실행 실패 | Python 3.12 이상과 실행 경로. Mac 기본 Python이 낮으면 설치된3.12 이상 명령 사용 |
| Codex를 찾지 못함 | Windows `-CodexPath` / Mac `--codex-path`. 대시보드만 볼 때는 Codex 연결 단계 생략 |
| 기존 runtime 거부 | 같은 이름의 prepare를 반복하지 말고 up 사용. 중간 실패 상태는 보존하고 별도 새 이름으로 준비 |
| Mac `PRIVATE_FILE_REQUIRED_CHMOD_600` | 키/자격 파일의 현재 사용자 소유권과0600 권한 확인 |
| Mac `EXTERNAL_KEY_CHANGED_PREPARE_NEW_RUNTIME` | 외부 키와 volume 사본이 달라짐. 기존 장부를 보존하고 새 runtime 또는 검토된 회전 절차 사용 |
| TLS·인증서 실패 | leaf2일 / CA7일. TLS 검증을 끄지 말고 유지보수 또는 새 runtime 준비 |
| 포트 충돌 | 다른 실행 여부 확인. 최초 prepare 때 Windows `-ControlPort`/`-GatewayPort`, Mac `--control-port`/`--gateway-port`/`--dashboard-port` 지정 |
| 대시보드0건 | 새 DB에는 이력이 없을 수 있음. 등록 도구를 호출하고 화면의 기간 필터 확인 |
| Mac Docker 파일 공유 오류 | 저장소 폴더의 Docker Desktop 접근 허용 확인 |
| 기존 Hook/MCP 충돌 | 개인 설정을 자동 덮어쓰지 않음. 충돌 설정을 확인하고 병합 검토 |

## 선택적 무모델 시험

```powershell
.\scripts\team_dev.ps1 -Mode test
```

같은 Dockerfile의 dev target과 `requirements-dev.lock`을 사용합니다. 실제 Codex·Jev 유료 요청 없이 합성 응답/격리 환경으로 검증합니다. TLS 통합 시험에는 별도 격리 서비스가 필요해 기본 시험에서 일부 skip될 수 있습니다. 실제 다른 물리 PC의 OS 차이까지 검증했다고 확대하지 않습니다.

Mac/POSIX에서도 개발 이미지로 선택적 시험을 실행할 수 있습니다.

```sh
docker build --target dev -f Dockerfile -t with-human-dev:local .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --network none --tmpfs /tmp \
  --mount "type=bind,source=$PWD,target=/workspace,readonly" -w /workspace \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src:/workspace/tests/hookgw:/workspace/tools \
  -e CONTRACT_DIR=/workspace/docs/mvp/contracts \
  with-human-dev:local python -m pytest -q -p no:cacheprovider tests/product
```

## 검증 범위와 평가 자료

- **Windows**: 새 clone·새 자격·새 volume으로 빌드/준비/기동, 실제 MCP 읽기·보호 쓰기 거부·대시보드 집계를 확인했습니다. 별도 기존 runtime에서 실제 Codex·Jev·사용자 답변의 ASK→재판정 ALLOW→쓰기 OBSERVED를 확인했습니다.
- **2026-10-28 새 clone**: 제품/POSIX 시험 **213개 통과·5개 skip**. skip은 제거한 과거 control 모듈 검사2개와 별도 TLS 통합 서비스용3개입니다. 무모델 시험을 모델 정확도로 표현하지 않습니다.
- **ARM64**: Linux ARM64 이미지 빌드와 Windows Docker Desktop의 에뮬레이션 기동에서 TLS·인증·MCP 도구 목록·실제 대시보드 조회를 확인했습니다. 해당 확인의 actor/Jev 요청과 도구 실행은0회입니다.
- **아직 미검증**: 실제 Mac의 파일 공유·Codex/ASK 화면, 최신 제품 변경을 반영한 DTAP 전체 재실행. 과거 평가 결과를 현재 코드의 새 측정으로 표현하지 않습니다.

`src/app/benchmark`, `harness/dtap-cc`, `docs/handoffs/WP-DTAP-CC-01`은 별도 DTAP 평가 코드·기록이며 제품 설치 과정에서 실행하지 않습니다. 상세 근거는 [백엔드 기준서](docs/development/BACKEND_REFERENCE.md)에 있습니다. 실행용 개인 키·DB·인증서·사용자 원문·로컬 artifacts는 clone에 포함되지 않으며 각 PC에서 새로 준비합니다.
