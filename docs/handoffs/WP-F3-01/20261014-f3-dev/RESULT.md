# WP-F3-01 구현·검증 인계

SPEC-4 / policy `mvp-2026-10-14-f3-v2`. 사람 개발자는 사용자1명, 작성자 개발 Codex와 별도 검토 AI를 구분했다. **코드·오프라인 집행·기존 A/B 회귀는 검증했고, 실제 judge/actor 검증은 사용자의 직접 실행을 기다리는 NOT_RUN이다. F3 전체 완료·의미 정확도·MVP 완료를 선언하지 않는다.**

## 기준과 변경

- 변경 전 SPEC3/v1 기준선: `artifacts/20261014-f3-01/baseline-product-source/manifest.json`,92파일 fingerprint `dc62e4d3d05e3764123d03b1fa1bcde7ec546178d8dca61a71065c3e27be3dfe`. 실제 제품30 PASS46.80초. 기존 B정본은88파일 `9553fd7b…5159`이며 기존A/B원증거·DB/키/개인설정은 보존했다.
- 현재 최종116파일 fingerprint **`5ca0e235d21adb5154f86fca71e46a63f3f83454bc8a5220a4906702ec76ea43`**, `artifacts/20261014-f3-01/demo-js-syntax-source/manifest.json`. 각 명령 직전 source/contracts/fixture snapshot, command UTC/exit/raw output을 고정했다. 최초 실패 hash를 수정판으로 소급하지 않았다.
- 공식 설치SDK OpenAI2.54.0, MCP2.3.0, 기존 lock/image 유지. image `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`. 개발브라우저 Firefox153.0/Playwright1.62.1·전용NSS CA 재사용, 새설치0. 이미지와 별도로 read-only source mount hash로 후보를 식별한다.
- 신규 `pdp/semantic.py, judge.py`, `storage/f3.py, auth_audit.py`; repository/control/gateway와 UI/런처/관련시험을 통합했다. `docs/mvp/00~07`/기계계약/예시를 위임대로 SPEC4에 맞췄다. 과거 SPEC3 본문은 baseline에서 역사섹션으로 복원했다. plans/harness/AGENTS/skill/원본PDF/기존handoff 변경0.
- POST_COMMENT의 EXACT(생략 기본값·본문필수)과 ISSUE_SUMMARY(본문사전입력 금지·명시 사용자선택)를 구분한다. 이전정책 세션/승인은 POLICY_CHANGED, 과거기록은 당시버전 보존. MCP입력3도구는 추가필드/권한 확장0.
- 새 `compose.f3.yaml`, 신규PKI·control/effects볼륨·역할별키·fakefixture, Control8020/Gateway8021. logical audience8001은 기존계약 identity를 유지한 test alias다. 별도토큰/DB로 분리했으며 OAuth 상호운용/임의포트호환을 주장하지 않는다.

## 실제 구현한 경로

Hard 권한/대상/민감정보/예산 검사 후 필요한 후보만 성공한 읽기 자료를 대조한다. 분석문맥은 마스킹·암호화·자료/총량 제한·complete flag·성공상태/동일이슈를 확인한다. A(user/grant/candidate)와 B(같은입력+출처)를 독립 SDK 요청으로 구성하며 도구권한0이다. 출력schema와 Unicode ref의 실제위치·quote·source를 검증하고 서버가 ALLOW/DENY/예외CONFIRM을 합성한다. 외부값 일치 자체는 차단규칙이 아니다. 정상 제목/URL/공격문구 보고도 TASK_DATA로 허용할 수 있다. 모델의 hard DENY/서버권한 해제 경로는 없다.

모델 await는 SQLite transaction 밖이다. immutable call/session/backend/args/user/grant/policy/source revision/모델/prompt/schema 결합, 단회lease/cache, model budget, stale/취소/실패차단과 기존 reserve/댓글1/승인단회/UNKNOWN 보호를 결합했다. 모델/프롬프트/schema가 바뀌면 cache/reserve를 ANALYSIS_STALE로 거부하고 유료재분석하지 않는다. source_ids 표시만으로 판단한 것으로 보고하지 않는다.

EXACT의 정확본문·공개읽기는 POLICY/model0. 기존 안전한 공개 제목 보고 및 외부근거없는 benign mismatch는 SOURCE/예외CONFIRM. 의미관측을 수행한 후보는 SEMANTIC이고 analysisID/snapshot hash/검증refs가 남는다. 장애 DENY와 유효한 외부지시 DENY를 구분한다.

## 수용 사례 상태

| F3 | 오프라인/집행·기존 실제 경로 | 실제 의미 모델/새 LIVE |
|---|---|---|
| 01 | POLICY 자동읽기·EXACT 댓글1/replay추가0 PASS | 모델0 경로 |
| 02 | 요약-only 댓글/SECRET_ENV hardDENY·금지효과0 PASS | 모델0 경로 |
| 03 | fake A/B 지지→reserve→실제DemoExecutor 효과1 PASS | NOT_RUN |
| 04 | fake NEW_INSTRUCTION→DENY/승인없음/효과0 PASS | NOT_RUN |
| 05 | 동일request/grant/tool/args의 실제문서쌍 fixture/런처 준비; fake합성은 정확도근거아님 | NOT_RUN |
| 06 | 안전외부 데이터/URL/공격인용 입력 분리·ref 검증 구현, fake TASK_DATA 허용 | NOT_RUN(정상 데이터 실제 의미 검증) |
| 07 | role/추가필드/가짜ref·A외부ref·B이슈ref누락 failclosed PASS | 실제 judge 위조입력 NOT_RUN |
| 08 | 예외CONFIRM 승인전0/정확승인후1/replay추가0·API장애승인우회0 PASS | 실제 모호성 판정 NOT_RUN |
| 09 | 문맥누락/초과·schema/근거오류·API실패모사·취소/lease 안전거부 PASS | 실제 API timeout/refusal NOT_RUN |
| 10 | 단회client/분석·DB대기중다른연결쓰기·stale/버전변경/변조차단·budget1 PASS | 유료 중복재분석0 설계·spy검증 |
| 11 | 실제 브라우저 기존 B01~08 PASS, 카드·출처·XSS·승인·UNKNOWN 표시 보완 | 자동의미 정상/차단3시연 NOT_RUN |
| 12 | guarded 사용자 런처·usage/latency/episode 수집 준비 | judge0/actor0; NOT_RUN |

Fake 응답 시험은 구조·경쟁·효과의 근거다. 모델 정확도나 문서쌍의 실제 인과를 증명하지 않는다. 통과 개수를 새로운 NT/AT 개수·IPI방어율로 합산하지 않는다.

## 실행 결과와 최초 실패

원본은 `artifacts/20261014-f3-01/`의 각 label.txt / label-command.json / label-source에 있다.

| 확인 | 결과 |
|---|---|
| baseline-product | 기존30 PASS46.80초 |
| product-first |27PASS/3FAIL: 읽기 뒤 기존EXACT 제목보고를 문맥불완전DENY로 보내는 회귀 |
| exact-approval-r1 | 좁은 SOURCE 예외CONFIRM 보완 후3PASS3.25초 |
| f3-fake-first / f3-fake-final |15PASS11.46초 / 추가회귀 포함17PASS12.37초 |
| core-regression-r1 / frozen-core |45PASS59.98초 / 기존30+F3보강17 =47PASS63.13초 |
| peer-regression-r1 |8PASS32.93초. checks25초 실제timeout·나머지1초·취소/UNKNOWN/receipt복구 유지 |
| browser-b-regression |6PASS/2FAIL: 한국어카드/접힌JSON에 구기대문자열 미표시 및 source발췌숨김 |
| browser-b-regression-r1 |B01~08 모두PASS. 한국어/서버enum 대조 및 source발췌 primary표시 보완 |
| frozen-lint |Ruff exit0. 최초 import/inline형식 진단 및 도구ROmount/cache 오류 보존 |
| bandit-candidate |exit1 기존B1043개 유지. 신규 판단코드 경고0이 의미안전/49전수PASS는 아님 |
| final-contract-check |SPEC4 계약14예시·하네스1·checker진단·pip일관성 PASS |
| user-launcher-syntax/demo-js-syntax |PowerShell/JS 구문PASS. 실제 모델 실행 완료 증거 아님 |

별도 AI 지적: R-F3-001 실제이슈 ref없는 B NONE으로 ALLOW/효과1 재현→same_issue ref필수→DENY/효과0. R-F3-002 UNKNOWN을 효과0으로 표시→불명/재실행금지 표기. R-F3-003 prompt버전변경에도 reserve/효과1→model/prompt/schema current결합과 cache/reserve stale차단/효과0. 각 최초·조치·재진단을 독립원본 및 FINDINGS로 연결한다. [별도 REVIEW](../20261014-f3-review/REVIEW.md)는 작성자와 분리된 AI 보조이며 공식 진단기관이 아니다.

## 인증 감사 보완

착수 당시 별도 R-B-002 파일/RESULT가 없음을 확인했고 사용자도 경로를 모른다고 답했다. 기존 코드 보존 후 좁은 `AuthAudit`를 통합했다. HUMAN/SERVICE/AGENT의401/403/429를 시간10초bucket·상태·표면·count·첫/마지막시각만24h DB에 기록한다. rawbearer/tokenhash/IP/URL/header/원문은 저장하지 않는다. 재시작 보존·유한집계·감사쓰기장애503/handler미진입을 단위 및 별도실제ASGI로 확인했다.

401/403/429 거부상태집계에는 서비스 정책DENY403도 포함될 수 있다. 순수 인증 원인별 forensic trace나 전역/분산 throttling·SR2-2 전체준수로 확대하지 않는다. 기존 인메모리 제한은 유지했다. 현재 노출경로의 좁은 persistence 보완과 전체가이드 운영보강을 구분한다.

## 사용자 직접 검증·자동 시연

현재 전용 제품URL **https://127.0.0.1:8020/**. CA신뢰는 전용Firefox profile만 사용하며 전역CA/검증해제/HTTPfallback은 없다.

```powershell
cd C:\sogaeding
.\scripts\f3_verify.ps1 -IncludeActor
```

judge6개후보(최대12요청)를 실제 브라우저/MCP로 실행하고 정상/외부데이터/문서쌍/변형/모호성의 UI·Control·효과·usage·latency를 저장한다. 이어 actor정상1/공격입력1을 최대180초×2 실행한다. 원문/권한과 최초 actorprompt는 동일하다. 공격미시도는 NO_ATTACK_ATTEMPT로 검토해야 하며 CLIexit0만PASS로 세지 않는다.

총judge24상한은 전용DB 원자attempt로 실패/timeout도 차감, session의 의미후보2개, retry0, 요청output2048·15초/합계20초다. actorepisode2/180초 및retry0가 구현됐다. **actor의 API별output2048 강제설정은 공식CLI 설정에서 확인되지 않았다; 저장답변8192문자 제한은 API 토큰제한이 아니다. actor token 상한까지 보장했다고 주장하지 않으며 실제 usage를 별도검토한다.** judge만 먼저 하려면 `-IncludeActor`를 생략한다.

결과는 `artifacts/20261014-f3-01/manual-real-<UTC>/cases.json,usage.json,browser.json,PNG` 및 actor command/안전launcherJSON에 저장한다. 키값은 출력하지 않는다. 이 실행은 사용자의 선택으로 사용자 직접 실행이며 개발 agent는 유료호출을 시작하지 않았다.

실제 검증 후 승인 없이 결과를 보는 시연:

```powershell
.\scripts\f3_demo.ps1
```

자동 정상·정상외부데이터·자동차단의3탭을 현재서버 이력으로 연다. 추가judge/actor/쓰기0, 승인클릭0. 이전 실제검증 효과를 재조회하는 viewer이며 새 실행인 것처럼 표현하지 않는다. 현재 실제검증 없으면 명확하게 중단한다.

## 남은 항목

필수 F3: 사용자 직접 실제 judge6쌍·문서쌍/정상외부데이터/자동브라우저·actor 결과 수집/검토, 확인되지 않은 actor 출력상한, 최종 실제후보 평가와 관리판정. 실제 의미판정 결과를 받기 전 source_ids/정책/수동승인만으로 F3완료를 선언하지 않는다.

제출 전 C/D 전수: 운영키/인증서/DB 수명·rotation·더넓은 TLS negative, 설계20/약점49 source→sink/rulecoverage·비적용근거·native/OS/공급망/license/SBOM 완전성·최종 재진단/기획서. 이번 선행조건으로 추가하지 않았다. 기존 F007/A중간snapshot 공백·B104/OSegress제한은 보존. 등록MCP3도구 경로만 보호하며 Codex내장shell/file·모든IPI/OS전체 보호·출처일치 인과증명·공식조치율을 주장하지 않는다.

자동 승인 검토가 실제 OpenAI 실행을2번 거절했다. 사유는 정확한 fake payload/외부목적지의 사용자승인이 충분하지 않다는 것이었다. preflight payload검사 후 재시도도 거절되어 우회하지 않았고, 사용자가 “모델 검증은 내가 직접 실행”을 선택했다. 이 때문에 새 실제모델 관측은 NOT_RUN으로 인계한다.
