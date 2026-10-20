# WP-MVP-DEMO-01 · 호스트 승인 대기 보완

구현·모델 없는 검증 인계. 실제 사용자 정상 보고서 작성/LIVE 의미 정확도는 미실행이며 전체 MVP DONE 판단은 관리 담당에게 남긴다. 개발 AI의 유료 actor/Jev 호출0, 시작 예약은 기존1/2를 보존한다.

## 변경 원인과 구현

이전 런처는 `subprocess.run(timeout=180)`에 사람 입력/호스트 승인 대기를 포함하고, main에서 timeout/exit 결과를 버렸다. 사용자의 첫 CLI는 읽기 READY/ALLOW 뒤 upstream0·보고서 없음·Jev0이었다. 188.383초 경과가 제한과 부합해도 종료 원인은 기록되지 않아 **UNKNOWN**이다. 키/API 오류나 확정 timeout으로 소급 진단하지 않는다.

- `tools/mvp_demo_lifecycle.py`: 실제 Windows 자식을 suspended 생성→Job 할당→resume한다. KILL_ON_JOB_CLOSE·명시적 tree 정리·SIGINT 정리 보호·safe lifecycle start/finish 기록을 추가했다. terminal/env/argv 원문은 기록하지 않는다. timeout/취소/nonzero/시작실패는 비정상 main exit와 기존 history를 함께 제공한다.
- `tools/mvp_demo.py`, `scripts/mvp_demo.ps1`, `compose.mvp-demo.host-wait-1.yaml`: 부모454 manifest와 원 bundle을 보존하고 `host-wait-1` 공개 revision/bundle만 추가한다. 동일 DB·키·예산·예약을 참조한다. 1800초 제안은 정확 revision/hash/명시 한도 선택이 있어야 시작하며 옛180초 승인을 재사용하지 않는다. 입력/승인/계산 시간을 분리할 수 없다는 한계와 종료 시 close 최대5초/tree 정리 최대3초 유예를 공개한다.
- `src/app/transparent/engine.py`, `server.py`, `tools/mvp_demo_hook.py`, `mvp_demo_mcp.py`: demo opt-in에서 PreToolUse는 정확 intent만 PENDING으로 등록한다. PDP ALLOW를 미리 내리지 않는다. host 뒤 실제 gateway private extAuthz가 단회 intent claim→기존 의미 판정→기존30초 freshness/원자 reserve→upstream을 수행한다. 정확 turn·연결·인자·USER request·출처·grant·정책 binding을 판정 전/후 재검사한다. 자동 유료 재분석/재전송은 없다. 기존 generic 경로와 정책v2/임계치 .90/원문ref·TLS·암호화·분석stop은 보존한다.
- `/demo/close`: 종료 child 연결을 폐기한다. 새 intent는 STALE, 이미 EXECUTING은 UNKNOWN으로 보존하며 이미 전달된 효과를 철회하지 않는다. 기존 두 call/다른 연결/원문 사유는 덮지 않는다.
- `tools/mvp_demo_viewer.py`: USER_DEMO/OFFLINE_REPLAY, typed 종료 원인, PENDING/PDP미실행, ALLOW와 OBSERVED/UNKNOWN, 실제 파일을 구분한다. 과거 실행 종료 사유는 UNKNOWN이다. HTML은 escape/CSP·필드 allowlist와 마스킹을 유지하고 새 파일에만 쓴다.

호스트 승인 자체를 MCP 관측만으로 증명하지 않는다. 새 demo의 CONFIRM은 자동 resume 없이 실행0으로 중단하며 기존 인간 승인 통제는 보존한다. 일반 native 개발 지원을 이 합성 MCP 시연으로 대체하거나 완료로 표시하지 않는다.

## 실제 검증

최종 통합 및 설치 상태는 final-index.json에 연결한다.

| 검증 | 결과와 근거 |
|---|---|
| 변경 전 기준선 | 216파일 fingerprint `85f933383aead74c84819c36980f638c63fc2851f411727ddf6df36a4e0f0dd3`; artifacts/20261016-mvp-hostwait/baseline-source |
| 최종 통합 회귀 | **506 PASS /43.62초**. 최종222파일 fingerprint `af89e13d13540d310f5a909ae0b78b0958a89e9b99153d1a164d0a4e3360b695`와 실제 설치 check 소스 일치 |
| 실제 Windows 설치 | PS5.1 revise/check/history exit0·**READY/issues none**. 새 manifest `f1c49257c270ac416b8144f2523a7dcdae1966ff908fc42cfa79f299ea1bf547`, 실제 provider 인증/모델 접근은 미검증 |
| dispatch 관련 단위·회귀 | 100 PASS; artifacts/20261016-mvp-hostwait-dispatch/close-regression-command.json |
| 실제 pinned agentgateway | 작성자28/28·별도 검토28/28 PASS. 실제1.1초 대기 + 격리 fixture 논리35초 전진, 대기 중 모델0/ALLOW없음→fresh 판정→정상 파일1. 강제 공격 후보/변조/replay/close 뒤 금지 효과0. 실제 모델 정확도 아님 |
| 실제 Windows PowerShell5.1 자식 | 별도 검토45/45 PASS. 실제 stdin 대기/입력, exit7, timeout2초, cancel_event, 정상 종료 손자 정리, 시작실패, 정리 중 취소·SIGINT 복구. 로컬 지연 자식 효과0. 실제 데스크톱 Ctrl+C/Codex TTY는 미검증 |
| 설치 CLI·PowerShell 한도/맥락 | 15/15 PASS. 지원 hooks 유지, per-skill disabled child config 구문 수용, 새wall 명시 필수. 실제 LIVE catalog에서 skill 제외는 미관측 |
| 기존 A/B·TLS·장애 | 승인·경쟁·보존·TLS30 PASS /49.98초, 장애·응답유실·취소8 PASS /33.79초; previous-ab-isolated / previous-hardening-isolated 명령 기록 |
| 정적 검사 | 수정 helper/viewer/집행 파일 Ruff PASS. dispatch4파일 Bandit Medium1/High0과 별도로, 변경8 Python파일 전체는 High0/Medium7/Low8·errors0·exit1. listener/tmpfs/명시argv 사용을 static-triage.md에서 sink별 판별했으며 억제/진단0/전수PASS로 표시하지 않음 |
| 필수 가이드 | 원본5 SHA·18페이지 실제 대조. guide-pages.json, guide-code-test.md에 원문→위협→코드→시험 연결. 설계20/약점49 전체를 새로 PASS 처리하지 않음 |

첫 합친 A/B 시험은 동일 포트를 쓰는 session fixture가 겹쳐 30PASS/8setupERROR였고 컨테이너를 분리한 뒤 30+8PASS였다. 첫 통합 명령은 새 Compose 파일 마운트 누락으로 479PASS/27setupERROR였으며 완전 마운트 재진단에서 **506 PASS /43.62초**를 확인했다. 최초 lint는 RO 캐시 생성 실패였고 `--no-cache`로 PASS다. 모두 원증거를 보존한다.

별도 검토에서 **HOSTWAIT-LIFE-01** P1을 실제 재현했다. before_stop 중 KeyboardInterrupt가 tree 정리를 건너뛰어 로컬 손자 지연 효과가 생겼다. 정리 구간 SIGINT 보호와 모든 callback 종료의 안전 처리 후 FINISHED/INTERRUPTED, Job VERIFIED, connection UNVERIFIED, 지연 효과0으로 재진단했다. 정리 실패를 성공으로 숨기지 않는다. 미지원 `skip_host_skill_discovery` 가정은 실제 CLI features 점검 후 제거했고 실패 증거도 보존했다.

## 보존과 공급망

최초13개 Jev 계획·실패결과·followup·원장의 SHA, 원454 manifest·episode-1.claim·실패HTML·활성 policy의 SHA와 기존 암호문 call2행 digest의 before/after가 **모두 일치했다**. 보호 키는 본문/해시 없이 크기·mtime·ACL metadata가 일치했다. 새 demo provider 원장/episode2/실제 보고서는 개발 검증에서 생성하지 않았다. 과거 실제 actor 비용은 UNKNOWN이다. 기존 누적 Jev5시도/예약320000·followup 입력4614/출력780, 새 한도8/512000·총 시작2는 그대로다. 현재 config는 기존 enabled 상태를 보존하고 health와 대조했으며, 상속 manifest의 최초 초기화 `live_default` 문구로 현재 상태를 덮지 않는다.

새 dependency/image/다운로드는 없다. 기존 pinned gateway `cr.agentgateway.dev/agentgateway@sha256:9d3e6044ddcdc0878b1787f77bd401252b95e22684203fb5e874c4c42d2ed90c`, 개발 image `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`를 재사용한다. 새 ctypes Job 구현은 Windows OS API/기존 Python 표준 라이브러리를 사용한다. 공식 함수/skill 설정 근거와 실제 지원 한계는 runtime HANDOFF·native-context-evidence에 있다. 개인 전역 설정·로그인·CA·기존 키/DB/예산 초기화0, 관리 정본 쓰기0이다.

## 사용자 인계와 남은 검증

정확한 수정 revision/manifest·한 번의 시작 명령은 [USER_RUN.md](USER_RUN.md)에 있다. 새 한도1800초를 직접 선택한 뒤 정상 문서를 먼저 작성한다. 사용자가 실제 정상 요청·개별 host 승인·OBSERVED와 실제 `reports/normal.md`를 확인해야 LIVE 성공을 판단한다. 분석 실패·CONFIRM·공격 미시도는 공격 식별 PASS가 아니다. 남은1회이므로 추가 공격 CLI 시작은 별도 배정이 필요하다.

[별도 AI 검토](../20261016-mvp-hostwait-review/REVIEW.md), [안전한 오프라인 화면 예시](../../../../artifacts/20261016-mvp-hostwait/offline-example-r2.html). 예시 종료 이벤트는 화면 시험용 합성이며 사용자 episode 기록이 아니다.

기존 자유 개발 목표와 native 지원·hook 사망 fail-open·동일 OS 사용자/helper 변조·전체 공급망/SBOM·운영 C/D는 유지된 미완료 범위다. 이미 forward한 원격 작업은 종료 후 효과가 생길 수 있어 UNKNOWN/no-retry로 관리한다. Job 정리는 로컬 직접 자식 tree에 한정하며 서비스/broker/외부 효과를 철회하지 않는다. 실제 모델 분류 정확도·전체 IPI/전체MVP·대회 제출 완료를 주장하지 않는다.


