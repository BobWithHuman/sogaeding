# SAST 보안 강화 및 재검증

기준: `RESULT.md`, 커밋 `42233ba0551be42a48215ff092ed90b15c2b729c` 이후 작업본.
원본 보고서·로그는 보존하며 재검사는 `sast-results/security-recheck/`에 저장한다.

## 적용한 변경

- 엔진·감사·Jev/OpenAI 예산·실행 이력 및 관리용 SQLite 연결을 공통 경계로 모았다. 중간 디렉터리를 `dir_fd`와 `O_NOFOLLOW`로 열며 DB 부모는 현재 UID 소유 0700을 요구한다. DB와 기존 journal/WAL/SHM은 일반 파일·현재 UID·0600·단일 hardlink 조건을 검사한다. SQLite가 검사 도중 이미 삭제한 sidecar(nlink=0)는 경로에 남은 파일이 아니므로 건너뛴다. 신규 DB는 연결 전에 0600으로 만든다. 조회 전용 연결은 SQLite `mode=ro`를 사용한다.
- SQLite 연결은 정상 종료·예외 모두 닫는다. DB 스키마와 데이터는 변경하지 않는다. 서비스 lease도 같은 디렉터리·파일 경계를 검증한다.
- 런타임 키와 대시보드 마스킹용 Jev 키는 디스크립터 기준으로 읽고 크기를 제한한다. 공개 인증서는 파일 이름 목록으로 권한을 결정한다. 생성되는 개인 키·토큰·연결 프로필은 첫 쓰기부터 0600이다.
- 도구 helper 이름을 제한하고 링크·reparse point·POSIX 비신뢰 소유자와 쓰기 가능한 경로를 거부한다. Codex/Docker 실행 경로를 절대 경로로 확정하며 명시 경로 실패 시 PATH로 대체하지 않는다. 빌드의 `ldd`도 절대 경로를 사용한다. 셸을 사용하지 않으며 자식 종료 코드 처리를 유지한다.
- 대시보드 분포는 고정 상태 목록과 DOM/textContent로 만들고 숫자는 유한한 음이 아닌 값, 너비는 0~100%로 제한한다. ASK 집계도 숫자로 제한하고 지표 설명은 escape한다. 나머지 HTML 템플릿은 출력 문맥의 escape·고정 클래스·수치 연산을 유지하며 악성 입력 회귀 검사로 확인한다.
- 진단 로그는 허용된 reason 및 검증된 call_ref만 추가한다. 임의 details가 stage/code를 덮어쓰거나 비밀값을 출력할 수 없다.

## 파일·권한 경계

| 대상 | 설정·소유 주체 | 적용 경계 |
| --- | --- | --- |
| control DB 및 auth DB | 컨테이너 `/data`, 준비 도구가 UID 10001에 할당 | 전용 0700 디렉터리, DB·sidecar 0600, 링크 거부 |
| upstream 실행 ledger | upstream 전용 `/data` | 위와 동일 |
| Jev budget / 기존 OpenAI budget | 운영자 설정 경로, 제품에서는 전용 volume | 위와 동일, 조회도 공통 검증 |
| 런타임 토큰·암호화 키 | 역할별 `/runtime` 읽기 전용 마운트 | 신뢰하는 소유자의 일반 파일 0600, 링크·hardlink·크기 검사. 실제 읽기 전용 마운트에서는 Windows의 합성 POSIX 권한 대신 마운트 경계 사용 |
| Jev 키 | 호스트 파일 또는 control-provider 읽기 전용 마운트 | 준비/attach/up 단계의 호스트 ACL 및 키 디렉터리 쓰기 권한 검증 + 컨테이너 읽기 검증 |
| 호스트 연결 프로필·자격 | 사용자 전용 디렉터리 | POSIX 디스크립터 검증; Windows 기존 ACL 준비와 reparse point 거부 유지 |
| helper·실행 파일 | 설치자/사용자가 관리하는 저장소·설치 경로 | 고정 helper 목록, 경로 검증 및 절대 실행 경로 |

현재 OS 사용자·root·저장소 설치자는 신뢰한다. 같은 UID의 악성 프로세스에 대한 격리는 제공하지 않는다. SQLite는 FD를 받지 않으므로, 디렉터리 검증은 비신뢰 사용자가 파일 이름을 교체할 수 없다는 경계를 전제로 한다. POSIX 엔진은 Linux 컨테이너에서 동작하며 호스트 Windows ACL 처리를 POSIX UID 검사로 대체하지 않는다.

## 기존 설치 권한 교정

새 검증은 기존 파일을 자동 chmod/chown하지 않는다. 권한 오류가 나면 먼저 해당 runtime 서비스를 중지하고 보존할 DB를 백업한다. 정확한 대상의 소유자가 엔진 UID 10001인지, DB 부모가 0700인지, DB·journal/WAL/SHM·키가 0600인지 확인한다. 검증된 대상만 운영자가 권한을 교정한 뒤 다시 시작한다. symlink/hardlink는 신뢰하는 원본에서 일반 파일로 복원해야 한다. 전체 저장소나 volume에 재귀 chmod/chown하지 않는다. `down` 시 volume 삭제나 기존 이력 초기화도 필요 없다.

## 검증 재현

Python 표준 unittest, 테스트용 Playwright 1.64.1 및 Chromium을 사용한다. Playwright는 제품 requirements에 추가하지 않았다.

```sh
python -m venv /tmp/with-human-security-tests
/tmp/with-human-security-tests/bin/pip install -r requirements.txt
/tmp/with-human-security-tests/bin/pip install playwright==1.64.1
/tmp/with-human-security-tests/bin/python -m playwright install chromium
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools CONTRACT_DIR="$PWD/docs/mvp/contracts" /tmp/with-human-security-tests/bin/python -m unittest discover -s tests -v
node --check src/app/web/observatory/app.js
git -c core.whitespace=cr-at-eol diff --check
```

테스트는 파일·중간 경로 링크, 파일 교체 경쟁, FIFO, 과도한 권한, sidecar 링크/hardlink, DB 동시 쓰기와 재시작, 감사·예산 보존, lease 배타성, helper/실행 경로, 리터럴 인자, 진단 로그, 생성 시 비밀 권한, 브라우저 HTML 공격 문자열·분포 CSS 범위, 로컬 BFF 접근 경계를 검사한다. 외부 모델 API와 실제 Codex는 호출하지 않는다.

## 남은 운영 조건과 검사 한계

- 로컬 HTTP 쿠키와 loopback publish, 컨테이너 내부 0.0.0.0 바인딩, `/tmp` 1777, 공개 인증서 0644는 기존 설계 조건을 유지한다. 외부 공개·HTTPS 브라우저 배포를 추가하면 별도 검토가 필요하다.
- 일반 품질 경고(순환 import, 혼합 반환 등)는 이번 수정 범위 밖이다. 전역 규칙 억제를 추가하지 않았다.
- Opengrep은 dashboard_preview.py에서 기존 `int_of_string` 오류를 계속 보고한다. 각 최상위 문장 조각과 전체 파일의 dump-ast는 성공했으므로, 스캔 경로의 파서/내부 처리 문제로 남긴다. 단편 검사 성공을 파일 전체 보안 검사 통과로 해석하지 않는다.
- Windows/macOS 실기기와 Docker 통합 동작은 이 Linux 환경에서 검증하지 않았다. 기존 호스트 ACL 흐름을 유지했지만 해당 플랫폼의 출시 전 실행 확인은 필요하다.
- SAST 경고 수는 취약점 수가 아니다. Pysa 제한적 0건과 상용 도구 미실행은 원본 보고서의 한계 그대로이며 이번에 해소했다고 간주하지 않는다.

검증 결과: 회귀 테스트 17개 통과, 동시 쓰기 테스트 추가 100회 통과. 엔진 DB 생성·재시작 별도 확인 및 JavaScript 구문 검사, Python 정의되지 않은 이름 검사 통과.

## SAST 재검사 결과

| 도구 | 원본 원시 경고 | 수정 후 원시 경고 |
| --- | ---: | ---: |
| Bandit (억제 무시) | 21 | 20 |
| Ruff S | 17 | 16 |
| Semgrep CE | 1 | 1 |
| Opengrep | 128 | 124 |
| Bearer | 28 | 21 |
| CodeQL Python | 14 | 17 |
| CodeQL JavaScript | 0 | 0 |

CodeQL Python 증가에는 테스트 코드의 script 태그 제거 경고와 `FileExistsError`를 처리하는 방어 코드의 empty-except 품질 경고가 포함된다. 경고 감소를 취약점 해결 건수로 해석하지 않는다. 이번 재검사로 공격 가능한 취약점이 새로 입증되지는 않았다.

실제 명령·종료 코드·소요 시간은 각 `*.run.json`, 원시 경고는 도구별 JSON/SARIF 및 stdout에 있다. 경고 종료 코드 1과 엔진 실행 실패를 구분했다. 도구 버전은 원본과 동일한 격리 설치를 재사용했다. Semgrep 레지스트리 규칙은 원본과 동일한 설정 이름으로 다시 가져왔으므로 규칙 내용의 동일성을 보장하는 고정 커밋 검사는 아니다.

- `sast-results/security-recheck/triage.json`: 수정 후 모든 원시 경고의 판정·근거·중복 원인 그룹. 잔여 경고는 조건부 수용 또는 근거를 기록하며 전역 억제하지 않는다.
- `sast-results/security-recheck/baseline-triage.json`: RESULT.md의 전체 원시 경고에 대응하는 처리 근거. 이번에 재실행하지 않은 도구의 항목은 원본 수동 검토 근거를 유지한 기록이다.
- `sast-results/security-recheck/source-manifest.json`: 검사 대상 작업본 소스 SHA-256. 원본 커밋과 작업본을 구분한다.
- `sast-results/security-recheck/tests.stdout`: 17개 회귀 테스트 실행 결과.

완료 조건은 경고 0건이 아닌 보안 경계 회귀 검사 통과와 잔여 경고의 근거 기록이다. Opengrep의 부분 파싱과 미검증 플랫폼은 위 한계로 남는다.

호스트 연결기와 helper는 Python `-I`에서도 도구 디렉터리만 일시적으로 검색 경로에 넣어 공통 모듈을 로드한 뒤 원래 검색 경로로 복원한다. `product_codex.py`, `hookgw_launch.py`, `hookgw_mcp.py`의 격리 실행 help 진입을 확인했다.

최종 CodeQL Python 추출본의 src/tools Python 파일 51개를 작업본과 바이트 단위로 대조해 일치함을 확인했다. PowerShell 실행·ACL의 실기기 검증은 미실행이다.
