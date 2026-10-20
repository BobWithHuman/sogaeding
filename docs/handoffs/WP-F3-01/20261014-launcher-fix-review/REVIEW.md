# WP-F3-01 Windows 런처 수정 별도 검토

검토 run `20261014-f3-launcher-fix-review`. **이번 두 파일의 좁은 수정은 검토 범위에서 수용한다.** Windows PowerShell5.1과 PowerShell7.6에서 정상 stderr를 실패로 오인하지 않고 실제 native exit0/37을 그대로 기록하는 동작을 독립 확인했다. 모델·actor 실행0, 제품 변경·공유 환경 조작0이다. 별도 보조 AI 검토이며 공식 독립 진단이나 F3 전체 검증이 아니다.

최종 source는 작성자의 `artifacts/20261014-f3-launcher-fix/launcher-final-source/manifest.json`, 116파일 fingerprint `030d80d20abfc54cd2e7fa94fb856ee02fd00659715233f52ea6fa370ca45199`다. 직접 검토한 `tools/f3_evidence.ps1`, `scripts/f3_verify.ps1` 두 파일의 현재 hash가 해당 manifest와 같음을 `artifacts/20261014-f3-launcher-fix-review/final-source-check.json`에서 확인했다. 제품 전체 hash를 이 수정에서 새로 검증한 것으로 주장하지 않는다.

## 변경 확인

- `f3_evidence-before.ps1`와 비교해 실행 대상을 Application으로 사전 확인하고, 복수 후보 중 기존 해결 순서의 첫 실행파일만 선택한다. 정상 Docker stderr를 `ErrorRecord`로 받는 PS5.1의 특성을 처리하기 위해 native 호출 구간에서만 EAP Continue/PS native preference false를 사용한다. stdout/stderr를 문자열로 보존하고 실제 `$LASTEXITCODE`를 기록한다. finally에서 EAP를 복구하며 호출자의 preference는 자식 script scope 밖으로 변경하지 않는다.
- nonzero 종료를 성공으로 바꾸지 않는다. missing executable은 호출 전에 실패하며 duplicate label은 기존 기록을 보호한다. 부모의 `if ($LASTEXITCODE -ne 0)` 검사는 유지됐다.
- `f3_verify-before.ps1`와 비교해 직접 Docker restart를 같은 evidence wrapper로 변경했다. PS5.1에서 UTF8 BOM 없는 actor 요청문을 직접 해석하는 대신 `pwsh -NoProfile -File`로 actor helper를 실행한다. actor의 마지막 종료코드 검사는 유지됐다. AST parse에서 현재 launcher syntax0·직접 docker invocation0을 확인했다. 실제 actor helper 실행은 하지 않았다.

## 독립 원증거

공통 경로는 `artifacts/20261014-f3-launcher-fix-review/`다. `*-snapshot/manifest.json`에 두 변경 파일과 자기 fixture의 명령 전 hash·UTC·복사본을 보존했고, `*-command.json`/`.txt`에 실제 argv·UTC·exit·안전한 출력을 보존했다. tested wrapper가 생성한 각 case의 별도 `*-source`, `*-command.json`, `.txt`도 유지했다.

| 실행 | 결과 | 확인 |
|---|---|---|
| windows51-final | exit1, 미기동 | Sandbox AuthorizationManager 거부. 제품/fixture 검증 PASS로 세지 않음 |
| windows51-r1 | exit0, PASS, PS5.1.26100.9444 | 정상 stderr+0, stderr+37, 실제/기록 exit 일치, stdout/stderr 문자열 보존·ErrorRecord 외부 출력0, caller preference 보존 |
| pwsh76-final | exit0, PASS, PS7.6.5 | 같은 계약의 독립 확인 |
| 두 환경의 추가 case | PASS | missing application 실행 전 거부, duplicate 기존 command hash 불변, Docker client 이름 해결·`--version` exit0, launcher AST syntax0·직접 Docker0 |

실제 Docker server/compose 조작은 하지 않았다. Docker client `--version`은 read-only이며 daemon operation0이다. 각 review JSON의 `application-name-resolution`은 `.exe` 및 extensionless 후보 환경과 선택된 첫 경로를 기록한다. 오프라인 stderr fixture는 안전한 고정 문자열만 사용한다.

작성자의 windows51/pwsh76 최종 checks 및 실제 `windows51-docker-up-r3-command.json`/출력, `windows51-docker-ps-command.json`을 읽어 수용했다. 실제 Running stderr2줄·exit0은 작성자 관측으로 구분한다. 작성자의 최초 fixture quote 오류, 복수 PATH 해결 오류, Docker pipe 권한 실패와 자신의 sandbox 실패는 원본을 유지했다.

이 변경은 native stderr 처리·exit provenance·런처 호환성만 다룬다. 기존 제품47/peer8·브라우저 회귀는 제품 변경0이므로 이 좁은 수정에서 반복하지 않았다. 실제 judge/actor·사용자 전체 `f3_verify -IncludeActor` 실행은 NOT_RUN이며 이전 모델 검증 미완료 상태를 바꾸지 않는다. 검토 범위의 미해결 확정 발견은 없다.
