# F3 사용자 런처 오류 보완

2026-10-14 KST. 사용자 보고: Windows PowerShell에서 `scripts/f3_verify.ps1 -IncludeActor` 실행 시 Docker `Container ... Running` 출력이 `tools/f3_evidence.ps1:15 NativeCommandError`로 중단됐다.

## 원인과 변경

Windows PowerShell 5.1은 `2>&1`로 합친 native stderr를 ErrorRecord로 전달한다. 기존 `$ErrorActionPreference='Stop'` 때문에 정상 진행 메시지에도 실제 종료 코드 확인 전 중단됐다. `tools/f3_evidence.ps1`은 실행 파일을 먼저 확인하고, native 호출 동안만 Continue와 PS7 native-error 옵션 false를 적용한다. stdout/stderr는 텍스트로 보존하며 실제 종료 코드를 기록·반환하고 원래 오류 설정은 finally에서 복구한다. 실행 파일 없음은 여전히 오류다. Docker처럼 이름이 같은 확장자 유무 실행 파일이 함께 있으면 명령 검색 순서의 첫 파일만 사용한다.

`scripts/f3_verify.ps1`의 별도 컨테이너 restart도 증거 래퍼를 통해 실행한다. Actor 하위 스크립트는 기존 필수 런타임 pwsh를 명시하여 UTF-8 한국어 요청이 Windows PowerShell 5.1의 기본 인코딩으로 오해석되지 않게 한다. 모델/권한/예산/제품 코드는 변경하지 않았다.

## 실제 검증

- Windows PowerShell 5.1.26100.9444에서 기존 native stderr 중단 재현.
- 수정 후 Windows PowerShell 5.1 및 pwsh 7.6.5: stderr+종료0 PASS, stderr+종료37의 실제 실패/증거 보존 PASS, 호출자 설정 보존 PASS, 실행 파일 없음 거부 PASS, 중복 증거 label 거부 PASS.
- 실제 Windows PowerShell 5.1 Docker Compose up: 두 컨테이너 Running stderr를 보존하고 exit0 PASS. Compose ps exit0 PASS, 기존 로컬 포트8020/8021 실행 확인.
- 최초 시험 fixture의 Python quote 전달 오류, Docker 복수 실행 경로 선택 오류, sandbox의 Docker pipe 접근 실패는 원기록에 보존했다. 수정된 최종 시험과 구별한다.
- 실제 judge/actor 호출0. 이 런처 수정은 기존 실제 모델 NOT_RUN 게이트를 완료하지 않는다. 사용자 전체 검증 재실행은 남아 있다. 제품 변경이 없어 제품 전체 회귀는 재실행하지 않았다.

원증거: `artifacts/20261014-f3-launcher-fix/`의 `windows51-final-checks.json`, `pwsh76-final-checks.json`, `windows51-docker-up-r3-command.json`, `windows51-docker-ps-command.json` 및 대응 txt/source manifest. 변경 전 두 스크립트도 같은 폴더에 `*-before.ps1`로 보존했다.

별도 AI 검토: `docs/handoffs/WP-F3-01/20261014-launcher-fix-review/REVIEW.md`.

최종 공개 소스116파일의 snapshot: `artifacts/20261014-f3-launcher-fix/launcher-final-source/manifest.json`, fingerprint `030d80d20abfc54cd2e7fa94fb856ee02fd00659715233f52ea6fa370ca45199`.

재실행:

```powershell
cd C:\sogaeding
.\scripts\f3_verify.ps1 -IncludeActor
```

기존 WP-F3-01 RESULT/REVIEW와 원증거는 보존했다. 관리 장부와 전역 DONE 상태는 변경하지 않았다.
