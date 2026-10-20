# sogaeding 공동 개발 공유 준비

2026-10-20 · 범위: GitHub 게시 전 소스·문서·새 개발 환경 재현 준비.

## 결과

- 최신 README, CONTRIBUTING, 현재 API/구조 인계 작성.
- 별도 `compose.team.yaml`과 `scripts/team_dev.ps1` 추가. 기존 서비스·키·원장·정책 소스는 수정하지 않음.
- 준비한 소스만 새 로컬 Git 저장소에 넣고 별도 경로에 실제 clone하여 검증.
- 고정 Dockerfile/잠금 의존성 build PASS. 같은 머신의 Docker 레이어 캐시를 사용했으며
  다른 PC의 다운로드·설치까지 수행한 결과는 아님.
- 최종 clone에서 대표 제품 시험 122개 PASS, PowerShell 5.1 진입점 동작 확인.
- 실제 Control HTTPS → agentgateway → upstream MCP TLS/mTLS와 도구 목록 확인 READY.
  비인증 history는 403. 실제 도구 실행 0, actor/Jev/로그인 요청 0.
- 기존 runtime 이름의 재준비 거절. 검증 stack down 완료, 키·DB·실패 증거는 보존.
- 별도 AI 검토 1개에서 최종 변경까지 재검토. 확정 P1/P2 발견 없음.
- GitHub 저장소 생성·remote 변경·원격 push는 수행하지 않음. 조직 PR 강제 규칙도 추가하지 않음.

## 최초 실패 → 조치 → 재검증

1. 기본 sandbox의 Git local clone sh 생성이 거절됨. 로컬 clone만 승인된 경로에서 수행해 PASS.
2. Docker 기본 address pool 소진으로 up 실패. 기존 IPAM을 읽고 비중복 /24 두 개를
   새 runtime에 저장하도록 수정. 기존 네트워크 변경·삭제 없이 후속 up PASS.
3. Windows bind-mounted 새 grant/CA의 읽기 PermissionError 및 upstream 계약 mount 누락 확인.
   전용 named volume에서 비root로 새 PKI·데이터를 생성하고 역할별 subpath RO/RW로 mount,
   upstream 계약 RO mount 추가. 호스트 ACL 완화 없이 최종 TLS/MCP READY.

로컬 원증거: `artifacts/20261020-team-share/`의 clean-build.log, final-clean-tests.log,
volume-prepare.log, volume-up.log, volume-check.log, existing-runtime-rejection.log,
final-down.log 및 최초 실패 로그. 원증거·개발용 인증서·DB는 게시하지 않는다.
검토 정리: 같은 디렉터리 REVIEW.md 및 이 handoff의 REVIEW.md.

## 팀원 명령

```powershell
.\scripts\team_dev.ps1 -Mode build
.\scripts\team_dev.ps1 -Mode test
.\scripts\team_dev.ps1 -Mode prepare
.\scripts\team_dev.ps1 -Mode up
.\scripts\team_dev.ps1 -Mode check
```

이 절차는 엔진 개발용 연결/시험이며 Codex actor를 실행하거나 실제 Jev를 호출하지 않는다.
공유 키를 사용하는 LIVE, DTAP 완주, 일반 native 보호, 새로운 대시보드 API는 별도 작업이다.
일부 전체 시험은 비공유 과거 artifacts에 의존하며 기본 대표 시험 목록과 구분한다.

## 공유 점검 및 보안 범위

`tools/repository_export.py`가 허용한 소스·시험·설정·문서만 새 게시 폴더로 복사하고
경로·바이트·SHA256 목록을 남긴다. 실제 credential 파일, 개인 로그인, DB, 로그,
다운로드 DTAP 자료와 Windows 캐시는 제외한다. credential 패턴 검사는 보조 점검이며
모든 비밀 부재의 증명은 아니다. 첫 게시 전 포함 파일 목록을 검토할 수 있다.
LF checkout 속성으로 Windows/Linux의 텍스트 변환을 일관되게 한다.

변경 범위의 G-02(고정 이미지/의존성·최소권한·secret 제외), G-03(경로·역할),
G-06(TLS·키 분리), G-07(오류 출력), G-08(별도 검토)를 기존 코드·가이드 근거와 연결했다.
설계20/약점49 전체 재진단 또는 전체 제품 보안 PASS를 새로 선언하지 않는다.
최초 동적 symlink 생성 반례는 Windows 권한 제한으로 미실행이며 정적 거절 분기만 검토했다.
