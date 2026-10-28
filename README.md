# With Human

사용자 요청·관측 자료·도구 실행 후보를 대조해 실행 전에 **ALLOW / DENY / ASK**를 판정하는 로컬 보안 엔진입니다. 기본 정책은 gate-6입니다. Codex 연결기와 조회 전용 대시보드를 함께 제공합니다.

현재 검증한 에이전트 범위는 Windows의 Codex CLI와 제품 Docker 작업영역의 MCP `read_file` / `write_file`입니다. macOS용 준비·실행 진입점도 제공하며, 실제 Mac의 Codex/ASK는 아직 미검증입니다. 일반 shell/native 도구 전체나 대화형 Claude Code의 ASK까지 지원한다고 주장하지 않습니다.

## Windows 처음 설치

준비물: Git, PowerShell 5.1 이상, Docker Desktop(Linux containers), Python 3.12 이상, 로그인된 Codex CLI, 본인의 Jev API 키 파일. Codex 앱에 번들된 Python이 있으면 스크립트가 사용하며, 일반 PC는 설치한 Python을 사용합니다. 브라우저 조회만 할 때는 Codex 실행 단계가 필요 없습니다. 검증한 CLI는 Windows native codex-cli 0.154.0입니다. `codex.exe`가 PATH에 없으면 check/start에 `-CodexPath C:\설치경로\codex.exe`를 지정합니다.

키는 저장소 밖의 파일에 보관합니다. 아래 `C:\Private\jev.api-key`는 경로 예시이며 실제 키를 README·Git·프롬프트에 입력하지 않습니다.

```powershell
git clone https://github.com/BobWithHuman/sogaeding.git
cd sogaeding

# 최초 1회: 같은 Dockerfile로 이미지를 빌드하고 이 PC 전용 자격을 생성합니다.
.\scripts\product_codex.ps1 -Mode prepare -RuntimeName local `
  -JevKeyFile C:\Private\jev.api-key

.\scripts\product_codex.ps1 -Mode up -RuntimeName local
.\scripts\product_codex.ps1 -Mode check -RuntimeName local
.\scripts\dashboard_local.ps1 -RuntimeName local
.\scripts\product_codex.ps1 -Mode start -RuntimeName local
```

대시보드: http://127.0.0.1:8150

연결기는 포함되어 있으므로 사용자가 새로 구현할 필요가 없습니다. `start`로 연 Codex에서 다음처럼 요청합니다. 필요한 Hook 신뢰 검토는 사용자가 Codex 화면에서 진행합니다.

```text
with_human MCP로 docs/release.md를 읽고, 내용을 한 줄로 요약해서 reports/trial.md에 저장해줘.
```

ASK 흐름은 `reports/ask-demo.md`를 대상으로 요청해 확인할 수 있습니다. 이 합성 경로에는 사용자 확인 규칙을 예제로 등록했습니다. 실제 민감 자료를 검출했다는 뜻은 아닙니다. Jev가 보류 조건을 인정한 경우 엔진 이유를 포함한 질문을 전달하며, 사용자 응답 뒤에도 재판정해 최종 ALLOW만 실행합니다. 모델 결과에 따라 DENY나 분석 장애가 나올 수 있습니다.

**Jev 요청 횟수·토큰 상한은 기본적으로 두지 않습니다.** 사용량·실패 기록은 계속 남깁니다. 최초 prepare/up/check는 모델을 호출하지 않으며, 공급자의 실제 키 수락은 사용자의 의미 분석 요청 때 확인됩니다. 코드/프로토콜 검증을 모델 정확도나 모든 공격 방어로 확대하지 않습니다.

## macOS 처음 설치

PowerShell은 필요 없습니다. Git, 실행 중인 Docker Desktop(Linux containers), Python **3.12 이상**이 필요합니다. `python3 --version`으로 확인하고, 설치된 명령이 `python3.12`라면 아래의 `python3`를 그 명령으로 바꿉니다. 대시보드 개발만 할 때는 Codex가 필요 없습니다. 에이전트 시험에는 로그인된 Codex CLI와 Hook·MCP 사용자 질문 기능이 필요합니다.

먼저 저장소를 clone하거나 최신 코드를 pull합니다. 본인의 Jev 키 파일을 저장소 밖 `$HOME/.with-human-secrets/jev.api-key`에 준비하고 다음 권한을 적용합니다. 키 값을 명령어·Git·프롬프트에 넣지 않습니다. 아래 chmod는 이미 준비한 파일의 권한만 바꿉니다.

```sh
mkdir -p "$HOME/.with-human-secrets"
chmod 700 "$HOME/.with-human-secrets"
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

`codex`가 PATH에 없으면 check/start에 `--codex-path /절대경로/codex`를 지정합니다. 기존 Codex 설정에 Hook/MCP 충돌이 있으면 덮어쓰지 않고 중단합니다. 질문과 도구 범위는 위 Windows 예제와 같습니다. 개인 설정·로그인·모델·sandbox는 변경하지 않습니다.

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

2026-10-28 확인: 새 clone에서 제품/POSIX 시험213개 통과·5개 skip. Linux ARM64 이미지 빌드와 에뮬레이션 기동, 실제 TLS·MCP 도구 목록·대시보드 상태/집계 조회를 통과했습니다. 실제 actor/Jev 호출은0회이며 실제 Mac 하드웨어·Codex ASK UI는 미검증입니다.

## Windows에서 다시 실행하거나 종료

같은 이름으로 prepare를 반복하면 기존 상태 보호를 위해 거부합니다. 이후에는 up → check → dashboard → start만 사용합니다.

```powershell
.\scripts\product_codex.ps1 -Mode history -RuntimeName local
.\scripts\dashboard_local.ps1 -Mode stop -RuntimeName local
.\scripts\product_codex.ps1 -Mode down -RuntimeName local
```

종료해도 DB·Jev 장부 volume은 보존합니다. 키·인증 자격·파일을 다른 사람에게 복사하지 않습니다. 인증서 leaf는2일, CA는7일이며 만료 시 임의 TLS 검증 해제 대신 기존 유지보수 절차를 사용하거나 별도 이름의 runtime을 준비합니다. 기존 runtime의 키 회전·백업 경계는 [백엔드 기준서](docs/development/BACKEND_REFERENCE.md)를 참고합니다.

기존 Hook/MCP/관리 설정과 충돌하면 개인 설정을 덮어쓰지 않고 중단합니다. Codex 로그인·모델·sandbox·승인 설정은 유지하고 실행한 자식 프로세스에 연결 옵션을 제공합니다.

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

## 팀원용 API·DB 문서

**[BACKEND_REFERENCE.md](docs/development/BACKEND_REFERENCE.md)**: 구성, 역할별 인증, 조회 API5개, query/응답/오류, ASK 이유·상태, DB·암호화·보존, 연결기 계약.

대시보드는 조회만 담당합니다. ASK 답변/승인은 에이전트의 신뢰 연결기에서 처리합니다. 에이전트 종류는 아직 미수집이라 `unknown`, Gateway/Upstream 생존 probe는 미구현이라 `UNKNOWN`입니다. 실제 실행 경로가 없다는 뜻은 아닙니다.

## 선택적 무모델 시험

```powershell
.\scripts\team_dev.ps1 -Mode test
```

같은 Dockerfile의 dev target과 `requirements-dev.lock`을 사용합니다. 실제 Codex·Jev 유료 요청 없이 합성 응답/격리 환경으로 검증합니다. TLS 통합 시험에는 별도 격리 서비스가 필요해 기본 시험에서 일부 skip될 수 있습니다. 실제 다른 물리 PC의 OS 차이까지 검증했다고 확대하지 않습니다.

## 저장소 정리와 평가 원본

과거 실험용 Compose14개·오래된 실행 도구·중복 문서는 Git 추적에서 제외했습니다. 기존 PC의 파일과 실행 원자료는 로컬에 보존하고, 이전 commit `0744fc0`에서도 복구할 수 있습니다. 팀원이 작성/수정한 DTAP 코드·과업 목록·결과와 필요한 의존 파일은 보존했습니다. `src/app/benchmark`, `harness/dtap-cc`, `docs/handoffs/WP-DTAP-CC-01`은 별도 평가 자료이며 제품 설치 과정에서 실행하지 않습니다.

평가 코드 전체가 최신 ASK 제품과 다시 검증됐다는 뜻은 아닙니다. 과거 결과를 현재 수정본의 새 측정으로 표현하지 않습니다. 실제 키·DB·private 인증서·사용자 원문·artifacts·개인 설정은 공유하지 않습니다.


재현 확인: 같은 Windows PC에서 기존 설정을 쓰지 않는 새 clone·새 자격·새 volume으로 빌드/prepare/up/check, 실제 MCP 읽기·보호 쓰기 거부·대시보드 집계를 확인했습니다. 최초 제품 시험195개 통과/5개 skip, 최종 관련50개 통과입니다. 실제 다른 물리 PC와 새 clone의 실제 모델/Jev 호출은 수행하지 않았습니다. 자세한 범위는 백엔드 기준서의 검증 절을 참고합니다.
