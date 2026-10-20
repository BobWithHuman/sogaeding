# WP-HOOK-GW-02 단계 A 결과

2026-10-16, 작성 `/root`, 별도 AI 검토 `/root/hookgw02_review`, 사람 개발자는 사용자1명이다. with-human-dev와 작업팩14의 **A만** 수행했다. **API 실행 준비·무모델 preflight를 구현·검증했다. 실제 모델 정상 작업은 사용자 직접 검증으로 남는다. 전체 자유 개발 MVP 완료나 전역 DONE 판정은 하지 않았다.** 계획/장부·엔진/정책·기존 원증거는 수정하지 않았다.

## 변경과 현재 준비 상태

- `scripts/hookgw_connect.ps1 -Api -Model <id>`가 현재 터미널의 codex 함수에 호출별 API 모드를 연결한다. `tools/hookgw_launch.py`는 custom provider `with_human_openai_api`, `env_key=OPENAI_API_KEY`, `requires_openai_auth=false`, Responses `https://api.openai.com/v1/responses`, 선택한 모델을 명시한다. 개인 ChatGPT 로그인·config/auth·전역 환경·CA를 변경/복사/로그아웃하지 않는다. 추가 sandbox/승인/trust 우회 flag도 없다.
- `-Preflight` 또는 API 연결 후 `codex --preflight`는 모델을 시작하지 않는다. 실제 `codex` 직전에도 준비 검사에 실패하면 `/connect`와 모델 시작 전에 중단한다. actor key 존재와 개인 저장 인증 종류, CLI 버전/hash/설정/hooks 활성·충돌, 앱 CA/control·gateway TLS, frozen product bundle, host 연결 자격 가독성, LIVE_USER, 실제 Control UID의 judge 키 가독, 기존 원장 COUNT/hash를 비밀 없이 구분한다.
- `/hooks` 신뢰는 자동 승인하지 않고 **NOT_VERIFIED**로 보고한다. API key의 유효성·선택 모델 접근·의미 판단 성공도 무모델 검사로 PASS하지 않는다. API 모드의 임의 model/provider/profile/보안 인자·login/resume와 중복 root/exe/model 선택값은 거절한다. 모델 선택은 연결 시 명시한다. 기존 hooks와 profile 내 충돌, CLI flags보다 우선할 managed defaults는 검토 전 거절한다.
- 최종 실제 preflight: **ready_to_open_cli=true, issues=[]**, Codex0.154.0, 개인 저장 인증 CHATGPT / 이번 actor 인증 ENV_API_KEY, actor/judge 각각 기존 선택 **gpt-5.6-luna**, Control LIVE_USER, 두 키 준비 확인. **judge12/24·남은12, 기존 DB SHA256 `2c1e21be30a4a1c30f9ff2d21fa5c4678af9fe8751895663110ebd2708f1e6ec` 불변**. 개발 AI의 유료 actor/judge 호출은 각각0이다.

## 기준선·최초 실패·보완

기준선은 04:53:04.886187 UTC의163파일, fingerprint `c7f48e7c27bf5a54c36094262ac2b084d59c076dcffcdb37879789798a3e6f48`이다. `artifacts/20261016-hook-gw-02-a/baseline-source/`에 실제 소스를 보존했다. 기존 WP-HOOK-GW-01 원증거/RESULT/REVIEW와 WP-F3 최초 실제 실패를 덮어쓰지 않았다.

1. 최초 기본 sandbox의 Docker pipe/host credential 접근 제한과 CLI hooks stage를 experimental로 가정한 준비 실패를 관측했다. 실제 설치0.154.0의 stage는 stable이다. 활성 상태 true를 파싱하도록 보완했고 허용된 로컬 실행 환경에서 재검증했다. sandbox 권한 실패를 제품의 공격 차단 PASS로 세지 않았다.
2. 최초 LIVE 시작은 `/runtime` read-only role volume 안에 `/runtime/judge.api-key` mountpoint가 없어 runc의 `read-only file system`으로 실패했다. 중간 대안인 `/judge.api-key`와 RUNTIME_DIR=/는 기동·키 가독은 성공했으나 별도 검토 **HG02-R01**에서 기존 human.token literal 마스킹 탐색을 바꾸는 영향이 발견됐다. Unicode 인접 토큰에서 generic regex만으로 동등 보호를 주장할 수 없어 최종안에서 되돌렸다.
3. 최종안은 `tools/hookgw_key_mountpoint.py`의 **명시 준비**로 NEW control 역할 volume에 빈 정규 mountpoint만 생성한다. UID10001/network none/cap-drop ALL/read-only rootfs이며 기존9개 역할파일 hash 불변, 기존 judge 키 복사0이다. 기존 키는 원위치에서 `/runtime/judge.api-key`로 read-only mount한다. **최종 compose LIVE 파일은 기준선과 바이트가 같다.** RUNTIME_DIR와 HOOKGW_RUNTIME 모두 /runtime, 실제 Unicode 인접 literal 마스킹=true·키 가독성을 재검증했다.
4. 필요한 좁은 준비 호환으로 `tools/hookgw_install.py`는 빈 정규·단일링크 judge mountpoint만 기존 역할파일 목록에서 허용한다. 내용이 있거나 symlink/hardlink이면 교체하지 않고 거절한다. 키/정책/엔진을 변경하는 확장이 아니다. preflight 자체는 mountpoint를 생성하지 않으며 `-PrepareJudgeMountpoint`와 `-Preflight`를 동시에 지정할 수 없다.
5. 최초 fake CLI fixture는 기본 sandbox의 Temp 하위 mkdir PermissionError로 모델 요청 전에 실패했다(`api-auth-fixture`). 허용된 실행 환경의 `api-auth-fixture-r2` 및 최종 `api-auth-final`은 성공했다. 추가 profile 조합은 CLI가 legacy `profile=...`를 지원하지 않아 요청0으로 실패했다(`api-auth-profile-fixture`, `api-auth-profile-diagnostic`). 이 실패를 보존하고 명시 음성시험 `api-profile-negative`에서 같은 설정이 요청 전에 거절됨을 구분했다. 개인 profile을 수정한 시험이 아니다.

## 코드·시험·원증거

원증거 루트: `C:/sogaeding/artifacts/20261016-hook-gw-02-a/`. `*-command.json`은 명령·UTC·exit·그 시점 source fingerprint/manifest를 기록한다. 실제키·개인 원문·전체 환경/Authorization을 출력/저장하지 않았다. fixture는 가짜 자격증명·합성 입력·loopback Responses만 사용했다.

| 요구/위험 | 구현·검증 | 실제 결과 |
|---|---|---|
| 개인 ChatGPT 인증과 actor API 경로 분리 | launch custom provider, `tests/hookgw/cli_api_fixture.py`, `api-auth-final` | 설치 CLI가 `/v1/responses`1건에 지정 gpt-5.6-luna와 fake env Authorization 사용, fake ChatGPT bearer 미사용, 고립 config/auth hash 불변. CLI exit0. 실제 모델 접근/품질 시험 아님 |
| 준비 실패 전 모델 미시작 | `hookgw_preflight.py`, `test_api_preflight.py` | key missing/judge key/budget/LIVE/TLS/config/masking 실패 구별. 실패 또는 preflight-only에서 connect·model spawn 호출0을 시험 |
| 실제 사용자 최소 준비 | `ps51-preflight-final` | Windows PowerShell5.1 exit0, TLS와 LIVE_USER·각 인증·budget12/24·literal masking 보존 확인(05:08:42 UTC) |
| 기존 키/마스킹·동결 제품 보존 | `empty-mountpoint-prepare`, `live-start-masking-preserved` | 기존9개 역할파일 그대로, key copied=false, 실제 서비스 시작 exit0, frozen bundle 검증 PASS. src/app 변경0 |
| 회귀 | `core-regression`, `final-api-regression` | 기존 backend/F3/transport/web와 당시 hookgw **108 PASS/58.72초**. 후속 mountpoint/installer/masking을 포함한 최종 hookgw **68 PASS/8.33초**. 중복 범위이므로 합산하지 않는다 |
| 코드 정적 검사 | `final-lint`, `bandit-a` | Ruff PASS. Bandit launcher/preflight2파일은 **Low5/Medium0/High0**, exit1. B404×2/B603×3은 shell=false argv 기반의 native CLI/Docker/Python 실행에 대한 경고로 수동 검토했다. 숨김·전수 보안 PASS 아님 |
| 별도 AI 검토 | [REVIEW](../20261016-api-preflight-review/REVIEW.md) | 작성자와 분리한 역할의 실제 소스·독립 회귀/로컬 인증 재실행 및 HG02-R01 조치 확인. 공식 독립 진단 아님 |

최종 소스는 05:10:29.589555 UTC167파일, fingerprint **`a02fb0c3905c9cb934399c1a9e0d0925d48c5c58dee420a5a753a3278a8225f0`**, `final-source/manifest.json`이다. 기준선 대비 변경/추가9개는 README, SPEC5 사용 설명, connect, launch, preflight, 빈 mountpoint helper, installer 빈파일 호환, 관련 test/fixture2개다. src/app/기존 엔진·정책·SPEC4 계약은 변경0이다. `final-index.json`은 최종 소스·보존 대조·유료0과 보고서 경로를 연결한다.

## 필수 가이드와 적용 보안

관리 `03_guide_compliance`와 기존 [GUIDE_APPLICABILITY](../../WP-HOOK-GW-01/20261016-hook-gw-dev/GUIDE_APPLICABILITY.md)의 원문 해시/추출·설계20/약점49 적용성 근거를 유지했다. 이번 범위의 관련 원문 추출을 다시 읽고 아래 코드/실제 시험에 연결했다. 이번에 PDF 전체 재진단이나 49개 PASS를 새로 수행했다는 뜻은 아니다.

| 원문 PDF 페이지 | 이번 위협·통제·증거 |
|---|---|
| R1 PDF25, G1 PDF35~41·47~53 | 기존 고정 CLI/개발 이미지 재사용, 새 다운로드·패키지·이미지 추가0. 기존 gateway 공급망 미확정/권고는 해소로 변경하지 않는다 |
| G2 PDF35~38, G3 PDF507(SR1-4) | argv/shell=false·명시 모델/provider·인자 충돌 거절, workspace docker 실행 거부, actual CLI fake 인증 및 scope 회귀 |
| G3 PDF510(SR2-5~8), G4 PDF38 | actor env_key/Control 파일키 역할 분리, 값 비노출·앱 CA 검증, 기존키/예산 보존, Unicode 인접 literal 마스킹 보존 재진단 |
| G2 PDF144~146, G3 PDF511, G4 PDF37~39 | socket/file context manager·유한 timeout, 준비 실패 중단·safe issue code, preflight 실패 시 모델0/예산 claim0 |
| C1 PDF26, G3 PDF20·23~28 | 최초실패·HG02-R01 조치·재진단·별도 AI 검토 이력. 공식 조치율/대회 점수는 계산하지 않음 |

API 동작 근거는 [OpenAI 공식 인증 문서](https://learn.chatgpt.com/docs/auth), [설정 reference](https://learn.chatgpt.com/docs/config-file/config-reference), [managed config](https://learn.chatgpt.com/docs/enterprise/managed-configuration)와 실제 설치 CLI/fake 요청을 함께 확인했다. requires_openai_auth=true는 env_key를 무시하므로 새 provider에서는 false를 명시했다. 로그인 강제/전역 login을 해결책으로 사용하지 않았다.

## 사용자가 직접 정상 한 건을 시험할 최소 명령

현재 머신의 빈 mountpoint/runtime/bundle은 준비돼 있다. actor용 키가 **현재 터미널의 OPENAI_API_KEY에만** 준비된 상태에서:

```powershell
cd C:\sogaeding
docker compose -f compose.hookgw.yaml -f compose.hookgw.live.yaml up -d
. .\scripts\hookgw_connect.ps1 -Api -Model gpt-5.6-luna -Preflight
codex
```

`ready_to_open_cli=true`/issues=[]가 아니면 마지막 codex를 실행하지 않는다. 키가 없는 별도 터미널에서 화면에 표시하지 않고 입력하는 방법은 [README](../../../../README.md)의 Read-Host -AsSecureString 절차를 따른다. 키 값은 채팅/명령/프로젝트 파일에 쓰지 않는다. `codex login`/logout이나 전역 provider 변경은 필요 없다. 모델 접근·요금은 preflight로 검증되지 않았으며 더 비싼 모델로 자동 대체하지 않는다. actor API 비용은 기존 judge 예산과 별도다.

CLI에서 `/hooks`를 먼저 열어 UserPromptSubmit/PreToolUse/PostToolUse의 정확한 Python -I hook 경로·host를 검토/신뢰한다. 기존 Codex 자체 도구 승인을 유지한다. 그 다음 아래 **한 요청만** 직접 입력한다:

> with_human의 read_file로 fixtures/hookgw/notes.txt를 읽고 사실을 두 문장으로 요약해 fixtures/hookgw/normal-output.txt를 write_file로 수정해줘. 마지막 줄에는 이번 시험 표식 WP-HOOK-GW-02-user-20261016-01을 넣어줘. 다른 도구는 사용하지 마.

별도 터미널:

```powershell
.\scripts\hookgw.ps1 history
Get-Content -LiteralPath .\fixtures\hookgw\normal-output.txt
Get-Item -LiteralPath .\fixtures\hookgw\normal-output.txt | Select-Object LastWriteTimeUtc
Get-FileHash -LiteralPath .\fixtures\hookgw\normal-output.txt -Algorithm SHA256
```

이번 session/turn/call의 user/pre/post와 판정 ALLOW·실행 OBSERVED, 이번 표식/내용·수정시각·hash를 연결한다. 기존 출력 파일의 존재만으로 PASS하지 않는다. 정상 읽기/쓰기 두 후보는 통상 judge4요청이므로 현재12요청 잔여 안에서 시작한다. 예외 CONFIRM은 정확한 call에 기존 approve/reject만 사용하며 DENY는 해제하지 않는다.

**첫 ANALYSIS_UNAVAILABLE/UNKNOWN, 사용자 turn 미기록, 예상 밖 native 호출·차단·효과이면 중단한다.** 이력의 reason/diagnostic을 보존하고 공격 시험이나 유료 재시도를 연속 진행하지 않는다. 공격 후보 미생성은 NO_ATTACK_ATTEMPT이며 분석 실패를 공격 식별 PASS로 세지 않는다. 정상 성공 다음의 공격1건은 사용자 후속 단계다.

새 머신/이전 볼륨에 빈 mountpoint가 없을 때만 LIVE up 이전 `. .\scripts\hookgw_connect.ps1 -Api -Model gpt-5.6-luna -PrepareJudgeMountpoint`를 별도로 한 번 실행한다. preflight 자체는 읽기 전용이다. 이미 다른 내용의 파일이면 지우거나 덮지 않고 준비를 거절한다.

상태 URL: 제어 `https://127.0.0.1:8030/health`, 실제 MCP `https://127.0.0.1:8040/mcp`. CA를 브라우저/전역에 설치하지 않았다. 새 이력은 CLI/API이며 기존 SPEC4 대시보드를 새 경로 UI로 세지 않는다.

## 남은 범위

사용자 직접 유료 actor/judge 의미 검증·실제 TUI 초기 hook 신뢰 UX는 NOT_RUN이다. 키 가독성은 유효성/모델 접근/정상 의미 판단 성공이 아니다. 현재 서비스는 LIVE_USER 준비 상태지만 개발 AI는 후보·모델 분석을 실행하지 않았다. 기존 자유 개발 목표와 정상 native 편집/일반 명령 지원, native hook 사망·timeout·malformed fail-open, gateway rustls/기타 공급망 권고 및 이미지 진단/패치 확인은 그대로 남는다. stage A 준비 완료를 이 남은 작업이나 전체 MVP 완료로 바꾸지 않았다. C/D 전체를 이번 작은 보완의 선행조건으로 추가하지 않았다.
