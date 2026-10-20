# HOST_REVIEW 준비 RESULT

2026-10-16. HOST_REVIEW_START_PROMPT 전체·최신 AGENTS·관리 검토와 with-human-dev를 적용했다. 사용자가 명시한 **이번 테스트 CLI1회 수동 호스트 reviewer + 공개 notes.txt 읽기1회**만 준비했다. 구현 `/root`, 격리 native fixture 보조 `/root/jev_adapter`, 별도 AI 검토 `/root/jev_review`. 사람 개발자는 사용자1명이고 공식 독립 보안 진단이 아니다.

**구현·무모델 준비 검증 완료. 실제 사용자 승인창/notes 실행 성공은 NOT_RUN이다.** 개발 AI의 실제 OpenAI/TypeSafe/actor 모델 요청·제품 tools/call은0회다. TypeSafe 키를 수집하거나 Jev를 enable하지 않았다. 사용자 보유 보고를 유료 전송/사용량 동의로 해석하지 않았다.

- [별도 REVIEW](../20261016-host-review-ai/REVIEW.md)
- [증거 인덱스](../../../../artifacts/20261016-host-review/final-index.json)
- [현재 사용 설명](../../../mvp/09_rules_first_jev.md)

## 변경과 경계

`tools/hookgw_launch.py`에 **`--manual-review`**를 명시 추가했다. API+JevRules에서만 허용하며 중복·축약 옵션·임의 `-c`/profile/sandbox/yolo/추가 API 인자는 계속 거절한다. 해당 child CLI argv에만 `approvals_reviewer="user"`, `approval_policy="on-request"` 두 값이 추가된다. 샌드박스·hooks·MCP 권한·TLS·PDP 정책/예약/승인/UNKNOWN은 변경하지 않는다.

PS에 `-ManualReview` 영구 스위치나 상태를 추가하지 않았다. `scripts/hookgw_connect.ps1`에는 안내만 추가했고 **`codex --manual-review`를 입력한 호출만** 수동 reviewer다. 종료 후 다음 `codex`에는 이 두 override가 없다. 개인 config/auth/신뢰를 쓰지 않는다. `never`/full-access/자동 허용/permissionDecision=allow를 추가하지 않았다.

로컬 system requirements의 reviewer/approval allowlist·managed-hooks-only를 보수적으로 읽어 충돌 시 거절한다. 기존 managed_config 거절도 유지한다. CLI가 managed 제약에 맞게 다른 값으로 fallback하면서 exit0일 수 있으므로 **manual config 점검의 stderr가 조금이라도 있으면** 고정 HOST_MANUAL_REVIEW_CLI_WARNING으로 중단한다. CLI 오류는 HOST_MANUAL_REVIEW_CONFIGURATION_REJECTED로 구분하고 원 stderr/config 내용을 로그에 넣지 않는다. 경고가 있으면 안전하게 준비 미완료이며 범용 경고 무시 옵션은 없다.

preflight는 actor model/API·PDP RULES_ONLY/model0·요청한 host reviewer·on-request/이번호출 scope·상속 sandbox·사람 승인 NOT_RUN을 분리한다. `managed_requirements:CLI_ENFORCED`는 CLI에 제약 집행을 위임하는 설계 표시이며 이번 테스트가 모든 실제 managed 계층을 입증했다는 뜻이 아니다. 준비 true는 계정 모델 접근이나 실제 사람 승인 완료가 아니다.

정책/DB/키/원증거/관리 장부/AGENTS/skill/전역 설정·인증·CA·bob MCP·CLI 설치를 변경하지 않았다. 이 작업은 host 도구 승인 경로만 준비하며 PDP의 자동 판정을 수동 승인으로 바꾸지 않는다. TypeSafe와 기존 auto-review403의 원인을 혼동하지 않는다.

## 검증·실패/한계

| 구분 | 실제 결과 |
|---|---|
| 작성자 관련 회귀 | **285 PASS/72.01초**, hookgw+SPEC4/F3. [명령](../../../../artifacts/20261016-host-review/related-regression-command.json), [출력](../../../../artifacts/20261016-host-review/related-regression.txt). 모델0 Docker network none·RO source·임시 DB. |
| 별도 AI | **99 PASS/5.66초**, API/Jev preflight/MCP/manual 및 검토자21개. 작성자285와 겹치므로 합산하지 않는다. local requirements/경고 fallback 차단/한번 manual→다음 기본값·config/auth 불변 포함. |
| 실제 설치 CLI 구문/로컬 fake actor | [최종 r3](../../../../artifacts/20261016-host-review-fixture/native-manual-review-r3.json): Codex0.154.0의 reviewer=user 옵션 수용/invalid enum 거절. fake-key의 loopback actor POST1, catalog GET2. 생성한 config/auth hash·기본 auto_review/on-request/read-only 불변·임시 폴더 정리. 실제 API/제품 도구0. |
| native fixture 한계 | **대화형 사람 승인 NOT_RUN**, exec 모드의 on-request 실효 NOT_PROVEN. 임시 ProgramData의 요구파일을 native가 로드하지 않아 **실제 managed 집행 NOT_VERIFIED**. 로컬 precheck·모의 fallback 경고 거절과 구별한다. 격리 fixture에는 일반 PATH 경고가 있어 production preflight라면 거절될 것이며 이를 managed 경고라고 주장하지 않는다. |
| 실제 Windows PS5.1 무모델 preflight | [결과](../../../../artifacts/20261016-host-review/actual-manual-preflight.txt) **ready=true/issues=[]/exit0**. 실제 환경의 config stderr 없음, CLI 설정 수용, requested reviewer=user/on-request/THIS_CLI_INVOCATION, sandbox 상속. 실제 stdio init→initialized→tools/list→임시 연결 정리, tool/turn/candidate/모델0. Jev NOT_AUTHORIZED·key/ledger 없음·semantic_write_ready=false 유지. |
| 정적/수동 | Ruff PASS. Bandit **exit1/High0/Medium0/Low5** 기존 subprocess import/고정 argv 경고 보존·수동 검토. shell=false, 신뢰 helper·고정 executable/인자. 경고 억제나 전체49 PASS 선언 없음. |

초기 native fixture의 GET2를 POST만으로 기대한 assertion과 너무 넓은 managed PASS 조건 때문에 r1/r2가 FAIL했다. 원 증거를 보존하고 r3는 **옵션 구문/로컬 fake actor/생성 파일 보존만** PASS로 한정했다. 관리 제약 실제 주입 실패를 성공으로 바꾸지 않았다. 별도 검토의 HOST-R01(exit0 fallback 경고를 준비 성공으로 오판할 위험)은 stderr fail-closed와 독립 재진단으로 조치했다. 첫 native help 실행은 sandbox LOCALAPPDATA fallback 경로 미발견/arg0 권한 경고가 있었고, 실제 Get-Command의 설치 경로·격리 환경으로 구분했다. CLI 업데이트·전역 권한 변경은 하지 않았다.

## 기준선·최종 보존·원문 연결

시작191파일 fingerprint `2b7f8a4e7aa6dd47d1c9a30c0331ca6f79fffe8b310690b7b7434e67e8e65892`에서 최종193파일 fingerprint **`bdc7df912c9d2c815b9c2928814004b4afc83310fe66e6686084a0f367daa999`**로 좁게 변경했다([최종 manifest](../../../../artifacts/20261016-host-review/final-source/manifest.json)). 회귀 이후 차이는 새 native fixture helper의 검증/보고 보완뿐이며 해당 최신 r3를 별도로 실행했다. 제품 src/contract/Compose/bundle35파일은 변경하지 않았으므로 재배치·서비스/DB 재시작을 하지 않았다. 실제 preflight의 bundle --verify --current도 통과했다.

[보존 대조](../../../../artifacts/20261016-host-review/preservation-final.json): 기존 GPT history5·Jev history5의 전체 hash/상태 동일, 개인 config/auth·기존 key·두 profile/CA/token·notes SHA 동일. **OpenAI22/24·남은2 및 장부 SHA 불변**. 기존 READY/UNKNOWN을 삭제·해제·재실행하지 않았다. 성공한 preflight의 임시 unbound connection 생성/정리는 있지만 사용자 turn/call/source/분석을 만들지 않았다. 순수 DB byte 무변경이라고 확대하지 않는다.

필수 원문 중 G2 PDF146, G3 PDF509/511, G4 PDF38을 원본에서 새 추출·SHA 대조했다([4페이지](../../../../artifacts/20261016-host-review/guide-pages.json)). 오류 최소화/권한·인증 주체/중요정보·세션 통제를 위 거절·불변·고정 진단 시험에 연결한다. R1/G1과 나머지 필수 원문·설계20/약점49 적용성은 [직전 전행 검토](../20261016-jev-dev/GUIDE_APPLICABILITY.md)를 유지한다. 새 의존성/이미지/다운로드0, C/D 전체를 새 선행조건으로 추가하지 않았다.

OpenAI Docs 스킬로 [reviewer 설정](https://learn.chatgpt.com/docs/config-file/config-reference), [관리 제약](https://learn.chatgpt.com/docs/enterprise/managed-configuration), [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review)를 확인했다. reviewer 선택은 sandbox 확대가 아니며 관리 요구사항이 우선한다.

## 사용자가 직접 실행할 정확한 명령

기존 서비스/등록 profile과 현재 PowerShell의 OPENAI_API_KEY를 사용한다. 실제 키 값은 보내지 않는다. TypeSafe 키는 준비·마운트·사용하지 않는다. 기존 승인 실패 CLI는 종료하고 새 CLI를 사용한다.

```powershell
cd C:\sogaeding
. .\scripts\hookgw_connect.ps1 -Api -Model gpt-5.6-luna -JevRules
codex --manual-review --preflight
codex --manual-review
```

첫 codex 명령은 점검만 한다. ready=true/issues=[]·requested_reviewer=user·on-request·Jev NOT_AUTHORIZED를 확인한 뒤 마지막 명령으로 **테스트 interactive CLI 한 번만** 연다. preflight 경고/거절 시 진행하지 않는다. 서비스가 정지돼 있다면 기존 `docker compose -f compose.hookgw.yaml -f compose.hookgw.jev.yaml up -d`로 재개하되 prepare/reset/install/정책/원장 교체는 하지 않는다.

`/hooks` 정의를 직접 검토하고 다음 한 건만 직접 입력한다:

> 사전 파일 점검이나 셸·다른 도구 없이 with_human read_file로 fixtures/hookgw/notes.txt를 한 번만 읽고 핵심 사실만 알려줘. 파일을 쓰지 마.

호스트 승인창에서 **with_human.read_file / path=fixtures/hookgw/notes.txt 한 건만 이번 요청에 한해 승인**한다. 서버/세션 전체 자동승인은 선택하지 않는다. 다른 파일·native·쓰기·외부접속·TypeSafe 요청/추가 승인창이면 승인하지 말고 중단한다. 제품 DENY/UNKNOWN·403/준비 오류·예상과 다른 reviewer가 나오면 반복 요청/승인 우회 없이 중단한다. 이전 READY call을 수동 해제하지 않는다.

notes 결과와 새 host-jev call의 PUBLIC_ENROLLED_READ/model0·ALLOW→OBSERVED를 대조한다. **READY만으로 성공 처리하지 않는다.** 정확한 이력 조회 명령:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -I tools/hookgw_hook.py artifacts/runtime-hookgw/host-jev history
```

확인 뒤 `/exit`로 끝낸다. 다음 평소 `codex`에는 --manual-review를 붙이지 않는다. 사용자 직접 실행에서만 actor GPT 비용/공개 notes의 작업 자료 전송이 발생할 수 있으며 개발 AI는 이를 실행하지 않았다. 이 호스트 승인은 PDP 자동판정/CONFIRM을 대신하는 UX가 아니다.

실제 사용자 승인·notes 효과, 실제 Jev 접근/자료·비용·한도/성능 평가, native 일반개발·hook 사망 fail-open·개인 bob 경고·공급망 미완료는 별도다. 전역 DONE/MVP 수용은 관리 세션이 판단한다.
