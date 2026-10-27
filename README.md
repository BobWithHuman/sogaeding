# With Human

사용자 요청·관측 자료·도구 실행 후보를 대조해 실행 전에 **ALLOW / DENY / ASK**를 판정하는 로컬 보안 엔진입니다. 기본 정책은 gate-6입니다. Codex 연결기와 조회 전용 대시보드를 함께 제공합니다.

현재 지원 범위는 Windows의 Codex CLI와 제품 Docker 작업영역의 MCP `read_file` / `write_file`입니다. 일반 shell/native 도구 전체나 대화형 Claude Code의 ASK까지 지원한다고 주장하지 않습니다.

## 처음 설치

준비물: Git, PowerShell 5.1 이상, Docker Desktop(Linux containers), Python 3.12 이상, 로그인된 Codex CLI, 본인의 Jev API 키 파일. Codex 앱에 번들된 Python이 있으면 스크립트가 사용하며, 일반 PC는 설치한 Python을 사용합니다. 브라우저 조회만 할 때는 Codex 실행 단계가 필요 없습니다.

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

## 다시 실행하거나 종료

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
