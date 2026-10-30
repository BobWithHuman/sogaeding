# With Human

**AI 에이전트의 도구 실행을 검사하는 로컬 보안 엔진**입니다. 사용자 요청, 에이전트가 읽은 자료와 출처, 실행하려는 도구·인자를 함께 검토해 **ALLOW / DENY / ASK**를 판정합니다. 사용자 요청과 무관한 외부 문서의 지시가 도구 실행으로 이어지는 간접 프롬프트 인젝션을 검사하는 데 목적이 있습니다.

| 판정 | 동작 |
| --- | --- |
| ALLOW | 집행 검사와 단회 실행 예약을 통과한 후보를 실행합니다. 실행 성공 여부는 별도로 기록합니다. |
| DENY | 실행을 거부합니다. |
| ASK | 실행을 보류하고 Codex의 사용자 질문 양식으로 답변을 받은 뒤 재검토합니다. 사용자 답변이 곧 실행 허용은 아닙니다. |

gate-6 정책을 사용하는 엔진, Jev(TypeSafe) 의미 분석 연동, Codex CLI 연결기, 파일 실행기, 조회용 대시보드와 Docker 실행 구성이 포함되어 있습니다. 각 PC에서 독립된 인증 자격과 저장공간을 생성합니다.

## 제공 범위

- 연결기로 연 **Codex CLI**에서 Docker 작업영역 **`/files`**의 MCP `read_file` / `write_file`을 사용합니다.
- 사용자 PC 전체 파일이나 Codex의 모든 내장 도구를 보호하는 제품은 아닙니다. 연결 세션에는 등록한 MCP를 제공하며 개인 설정 파일은 유지합니다.
- 대시보드는 상태·판정·실행 이력을 조회하는 화면입니다. **ASK 답변은 대시보드가 아닌 Codex 대화형 세션에서 처리합니다.**
- 회사 서버에서 여러 사용자를 운영하는 배포와 npm 실험용 도구는 이 실행 경로의 범위에 포함하지 않습니다.

## 실행 전 준비

| 준비물 | 설명 |
| --- | --- |
| Git 또는 GitHub 소스 ZIP | 이 저장소를 다운로드합니다. |
| Docker Desktop | **Linux containers** 모드로 실행합니다. 이미지 빌드·다운로드를 위한 네트워크가 필요합니다. |
| Python **3.12 이상** | 호스트 연결기를 실행합니다. 호스트에 별도 pip 패키지를 설치할 필요는 없습니다. |
| 본인의 유효한 **Jev API 키 파일** | 저장소 밖에 키 한 줄을 담은 파일을 준비합니다. 공급자 측 API 이용 권한·사용 가능 한도가 필요합니다. |
| 로그인된 **Codex CLI** | 에이전트 연동에 필요합니다. 확인한 Windows 버전은 `codex-cli 0.154.0`입니다. Hook과 MCP 사용자 질문 양식을 지원해야 합니다. |

**의미 분석에 필요한 데이터는 외부 Jev API로 전송되며 요금이 발생할 수 있습니다.** 요청 횟수·입력 토큰 상한은 기본적으로 두지 않습니다. 키 값을 명령어·프롬프트·Git에 넣거나 다른 사람에게 공유하지 마세요.

`prepare`, `up`, `check`는 모델을 호출하지 않습니다. `check`의 `READY`는 로컬 연결 준비 상태이며, **Jev 공급자가 키를 수락했다는 뜻은 아닙니다.** 실제 인증·판정은 첫 의미 분석 요청에서 확인됩니다.

## 저장소 다운로드

```sh
git clone https://github.com/BobWithHuman/with_human.git
cd with_human
```

ZIP으로 받았다면 압축을 푼 뒤 `README.md`와 `compose.yaml`이 있는 폴더에서 터미널을 엽니다. 이후 명령은 모두 저장소 루트에서 실행합니다.

## Windows 처음 실행

### 1. 키 파일 준비

PowerShell에서 아래를 **최초 한 번** 실행해 본인·SYSTEM·Administrators만 접근할 수 있는 새 키 보관 폴더를 만듭니다. 기존 폴더가 있으면 중단하므로 다른 새 폴더 이름을 사용하거나 기존 권한을 확인하세요.

```powershell
$ErrorActionPreference = 'Stop'
$secretDir = Join-Path $env:USERPROFILE '.with-human-secrets'
New-Item -ItemType Directory -Path $secretDir -ErrorAction Stop | Out-Null
$owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [Security.AccessControl.DirectorySecurity]::new()
$acl.SetOwner($owner)
$acl.SetAccessRuleProtection($true, $false)
foreach ($sidValue in @($owner.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique) {
    $sid = [Security.Principal.SecurityIdentifier]::new($sidValue)
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $secretDir -AclObject $acl
New-Item -ItemType File -Path (Join-Path $secretDir 'jev.api-key') | Out-Null
notepad.exe (Join-Path $secretDir 'jev.api-key')
```

열린 편집기에 **본인의 Jev 키 한 줄**을 저장하고 닫습니다. 키 파일과 부모 폴더의 권한을 검사하므로 공유 폴더는 사용하지 마세요.

### 2. 준비·기동·연결 확인

Docker Desktop을 실행한 상태에서 저장소 루트의 PowerShell에서 실행합니다. `local`은 이 설치의 runtime 이름이며, 모든 명령에서 같은 이름을 사용합니다.

```powershell
# 처음 한 번만 실행: 이미지 빌드, 인증서·토큰·저장공간 생성
.\scripts\product_codex.ps1 -Mode prepare -RuntimeName local `
  -JevKeyFile "$env:USERPROFILE\.with-human-secrets\jev.api-key"

.\scripts\product_codex.ps1 -Mode up -RuntimeName local

# Codex 없이 내부 TLS·인증·Gateway 도구 목록 확인
.\scripts\team_dev.ps1 -Mode check -RuntimeName local

# 대시보드 실행
.\scripts\dashboard_local.ps1 -RuntimeName local
```

내부 점검 결과에 `"state": "READY"`, `"mcp_tools": ["read_file", "write_file"]`이 나오면 연결 준비가 된 것입니다. **`up`의 Started 출력만으로 정상 기동을 판단하지 말고 반드시 `check`까지 확인하세요.**

대시보드는 **http://127.0.0.1:8150/** 에서 엽니다. 새 설치에는 과거 이력이 없으므로 0건이 정상입니다. 엔진·대시보드만 사용할 때는 Codex 실행 단계가 필요 없습니다.

### 3. Codex 연결

본인 계정으로 로그인한 Codex CLI를 준비하고 실행합니다.

```powershell
.\scripts\product_codex.ps1 -Mode check -RuntimeName local
.\scripts\product_codex.ps1 -Mode start -RuntimeName local
```

`check`는 CLI 설정과 엔진 준비 상태를 확인하며 모델 세션을 열지 않습니다. `start`로 열린 Codex에 작업을 입력합니다. Hook 신뢰 확인이 표시되면 내용을 검토하세요. 기존 Hook/MCP 설정이 충돌하면 덮어쓰지 않고 중단합니다.

Python이나 Codex가 PATH에 없으면 해당 `product_codex.ps1` 명령에 실제 설치 경로를 지정합니다. Python 경로가 필요한 환경에서는 이후 호출에도 동일하게 지정하세요.

```powershell
.\scripts\product_codex.ps1 -Mode check -RuntimeName local `
  -PythonPath 'C:\설치경로\python.exe' -CodexPath 'C:\설치경로\codex.exe'
```

### 4. 이력 조회·종료·다시 실행

Codex에서 `/exit`한 뒤 실행합니다.

```powershell
.\scripts\product_codex.ps1 -Mode history -RuntimeName local
.\scripts\product_codex.ps1 -Mode security -RuntimeName local
.\scripts\dashboard_local.ps1 -Mode stop -RuntimeName local
.\scripts\product_codex.ps1 -Mode down -RuntimeName local
```

`down`은 DB와 사용량 volume을 삭제하지 않습니다. 다시 사용할 때는 **up → 내부 check → dashboard → Codex check → start** 순서로 실행합니다. 같은 runtime에 `prepare`를 반복하지 마세요.

## macOS / POSIX 처음 실행

Python 3.12 이상, 실행 중인 Docker Desktop과 본인의 Jev 키가 필요합니다. 에이전트 연결에는 로그인된 Codex CLI도 필요합니다. **실제 Mac의 Codex/ASK UI는 미검증입니다.**

먼저 새 개인 키 보관 폴더를 만들고, 텍스트 편집기로 `jev.api-key`에 본인의 키 한 줄을 저장합니다. 아래 `mkdir`는 이미 있는 폴더에 대해서는 실패하므로 기존 폴더라면 권한을 확인하세요.

```sh
mkdir -m 700 "$HOME/.with-human-secrets"
# 텍스트 편집기로 "$HOME/.with-human-secrets/jev.api-key"를 생성·저장한 뒤:
chmod 600 "$HOME/.with-human-secrets/jev.api-key"
```

저장소 루트에서 실행합니다.

```sh
python3 --version
python3 tools/product_local.py prepare --runtime local \
  --jev-key-file "$HOME/.with-human-secrets/jev.api-key"
python3 tools/product_local.py up --runtime local
python3 tools/product_local.py check --runtime local --engine-only
python3 tools/product_local.py dashboard --runtime local

# 에이전트 연결 시 이어서 실행
python3 tools/product_local.py check --runtime local
python3 tools/product_local.py start --runtime local
```

브라우저에서 http://127.0.0.1:8150/ 을 엽니다. `codex`가 PATH에 없다면 check/start에 `--codex-path /절대경로/codex`를 지정합니다. 설치 명령이 `python3.12`라면 위 `python3`를 해당 명령으로 바꿉니다.

```sh
# Codex에서 /exit한 뒤 조회·종료
python3 tools/product_local.py history --runtime local
python3 tools/product_local.py security --runtime local
python3 tools/product_local.py status --runtime local
python3 tools/product_local.py dashboard-stop --runtime local
python3 tools/product_local.py down --runtime local
```

다시 실행할 때는 prepare를 제외하고 up/check/dashboard/start를 사용합니다. POSIX에서는 호스트 키를 Control 전용 volume에 사본으로 보관하므로 해당 volume도 비밀 자료로 취급하세요. 기존 runtime의 외부 키 파일이 바뀌면 새 runtime 준비가 필요합니다.

## 첫 파일 작업과 ASK 확인

`start`로 연 Codex에 다음처럼 입력합니다. **실제 분석 요청에는 Jev 요금이 발생할 수 있습니다.**

```text
docs/release.md를 읽고 내용을 한 줄로 요약해서 reports/trial.md에 저장해줘.
저장한 파일을 다시 읽어서 확인해줘.
```

`docs/release.md`는 prepare가 만드는 합성 예제 문서입니다. 파일은 호스트 저장소가 아니라 Docker의 `/files` 작업영역에 있습니다. Codex의 실행 결과와 대시보드의 판정·실행 이력을 함께 확인합니다.

ASK 흐름을 확인할 때는 다음처럼 요청합니다.

```text
docs/release.md를 읽고 내용을 한 줄로 요약해서 reports/ask-demo.md에 저장해줘.
사용자 확인이 필요하면 엔진이 알려준 이유를 설명하고 질문해줘.
```

`reports/ask-demo.md`에는 사용자 확인 규칙이 등록되어 있습니다. 실제 질문이 나오면 **Codex의 사용자 질문 양식**에서 답변합니다. 외부 문서나 모델의 승인 주장은 사용자 답변으로 인정하지 않습니다. 판정과 분석 결과에 따라 ASK 대신 DENY나 분석 오류가 나올 수 있으며, 승인 답변 후에도 재검토합니다.

연결 점검은 Jev 인증·판정이나 실제 도구 실행을 검증하지 않습니다. 처음 설치한 PC에서는 위 읽기·쓰기·다시 읽기 및 ASK 확인까지 별도로 수행하세요. 이 예제는 공격 방어 성능을 입증하는 테스트가 아닙니다.

## 문제 해결

| 증상 | 확인할 내용 |
| --- | --- |
| Docker 연결 실패 / permission denied | Docker Desktop 실행 여부, Linux containers 모드와 현재 사용자 Docker 접근 권한을 확인합니다. |
| Python/Codex 실행 파일을 찾을 수 없음 | Python 3.12 이상과 Codex CLI 설치를 확인하고 명시 경로 옵션을 사용합니다. |
| Jev 키 ACL·소유권 오류 | Windows 키 파일과 부모 폴더를 본인·SYSTEM·Administrators 전용으로 준비합니다. POSIX는 부모 0700, 파일 0600을 확인합니다. |
| `Existing runtime preserved` | 기존 상태를 덮어쓰지 않습니다. 준비된 runtime은 up/check로 사용하고, 새 설치는 다른 runtime 이름으로 prepare합니다. |
| `PRIVATE_RUNTIME_DIRECTORY_REQUIRED` | 최신 `compose.yaml`의 데이터 volume에 `nocopy: true`가 있는지 확인합니다. 이전 실패로 이미 바뀐 권한은 아래 업그레이드 안내를 따릅니다. |
| 대시보드 화면만 열리고 엔진 연결 실패 | 내부 check를 실행합니다. HTML 200이나 컨테이너 Started만으로 엔진 정상 상태를 판단하지 않습니다. |
| Hook/MCP 설정 충돌 | 오류에 표시된 기존 설정을 확인해 수동으로 병합합니다. 연결기는 개인 정의를 덮어쓰지 않습니다. |
| 첫 의미 분석에서 인증·한도 오류 | Jev 키의 유효성, 공급자 이용 권한·잔여 한도와 네트워크를 확인합니다. 로컬 READY는 공급자 인증 검증 결과가 아닙니다. |
| 포트 사용 중 | 기존 runtime을 종료하거나 새 runtime을 다른 포트로 준비합니다. 아래 옵션을 참고하세요. |
| 인증서 만료 | TLS 검증을 끄지 말고 기존 runtime을 종료한 뒤 새 이름으로 준비합니다. 이전 이력은 기존 volume에 보존되며 새 runtime에 자동 이전되지 않습니다. |

Windows는 최초 prepare에 `-ControlPort 8230 -GatewayPort 8240`을, 대시보드에 `-Port 8250`을 지정할 수 있습니다. 다른 포트로 준비했다면 내부 점검에도 `team_dev.ps1 -Mode check -RuntimeName local -ControlPort 8230 -GatewayPort 8240`을 지정합니다. POSIX는 최초 prepare에 서로 다른 `--control-port 8230 --gateway-port 8240 --dashboard-port 8250`을 지정합니다.

### 이전 버전에서 기동에 실패한 경우

이 버전은 Control/Upstream 데이터와 Jev 사용량 volume의 `nocopy: true` 설정으로 신규 디렉터리 권한을 보존합니다. 이미 `0755`로 바뀐 기존 디렉터리를 자동 교정하지는 않습니다.

- 기존 이력이 필요 없는 새 설치라면 이전 runtime을 down한 뒤, **새 runtime 이름**으로 prepare/up/check를 실행합니다. 대시보드·Codex 명령에도 새 이름을 사용합니다.
- 기존 이력을 계속 사용하려면 서비스를 중지하고 백업한 뒤, 해당 volume의 `control-data`, `upstream-data`, `jev-budget` 디렉터리가 UID/GID `10001:10001`, 권한 `0700`인지 관리자가 확인·교정해야 합니다. 기존 DB·sidecar 파일은 UID 10001 소유·0600이어야 합니다. 전체 저장소나 volume에 재귀 chmod/chown을 적용하지 마세요.
- 소스를 업데이트한 뒤에는 기존 runtime을 down/up하고 대시보드도 다시 기동한 다음 check합니다. Dockerfile/requirements가 바뀌었다면 Windows는 `product_codex.ps1 -Mode build`, POSIX는 `product_local.py build`를 먼저 실행합니다.

## 구성과 운영 범위

| 구성 | 역할 | 주요 경로 |
| --- | --- | --- |
| Control | 세션·출처·권한·판정·실행 예약·조회 API | `src/app/transparent/engine.py`, `server.py` |
| gate-6 / Jev | 정책과 외부 의미 분석·응답 검증 | `src/app/transparent/jev_gate6.py`, `gate_policy.py`, `jev.py` |
| Codex 연결기 | Hook·MCP 전송과 사용자 질문 응답 | `tools/product_codex.py`, `hookgw_*.py` |
| Gateway | 실행 후보의 권한 검사와 도구 중계 | `agentgateway/config.yaml` |
| Upstream | 등록된 파일 도구 실행·중복 실행 방지 | `src/app/transparent/upstream.py` |
| 대시보드 | 브라우저 중계·조회 UI | `src/app/dashboard_local.py`, `src/app/web/observatory/` |
| 실행 계약 | 실행 시 읽는 JSON 4개 | `docs/mvp/contracts/` |

기본 주소는 Control `https://127.0.0.1:8130`, Gateway `https://127.0.0.1:8140/mcp`, 대시보드 `http://127.0.0.1:8150/`입니다. 로컬 CA·역할별 토큰과 Gateway 내부 mTLS를 사용합니다. 브라우저에는 엔진 토큰을 전달하지 않습니다.

SQLite의 주요 테이블은 `sessions`, `turns`, `sources`, `calls`, `transport`, `asks`, `audit`입니다. 주요 원문 문맥은 암호화하지만 DB 파일 전체와 작업영역 파일 전체를 암호화하는 구조는 아닙니다. 기본 세션 보존은 1일, 원문 이력은 7일이며 leaf 인증서는 2일, CA는 7일입니다. volume·연결 자격도 개인 키와 함께 보호하세요.

누적 출처 근거 8개 초과 등 문맥 제한으로 정상 작업도 분석 불가·DENY가 될 수 있습니다. 분석 오류는 공격 탐지 성공이 아닙니다. 에이전트 식별과 Gateway/Upstream 생존 정보가 미수집이면 대시보드는 UNKNOWN으로 표시합니다.

## 검증 범위

이 기동 수정은 Windows / Docker Engine 29.6.1의 Linux containers, Python 3.12.14, Codex CLI 0.154.0에서 독립된 신규 runtime으로 확인했습니다.

- 캐시 없는 이미지 빌드와 의존성 다운로드·해시 검증
- 신규 PKI·토큰 생성과 Control/Upstream 기동
- 내부 TLS·인증 검사 및 Gateway의 `read_file` / `write_file` 목록 조회
- 호스트 stdio MCP의 initialize·tools/list와 Codex CLI 설정 수락
- 대시보드 첫 화면과 상태·요약·이벤트·보안 조회 API

위 연결 검증에는 가짜 키를 사용했으며 외부 모델·파일 도구를 호출하지 않았습니다. **이 수정의 검증 결과에 실제 Jev 분석·파일 실행·대화형 ASK 및 실제 macOS UI의 종단 간 성공은 포함하지 않습니다.**
