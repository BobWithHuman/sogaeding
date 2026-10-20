# WP-HOOK-GW-02 B 보완 / T-HG-04 RESULT

2026-10-16. 구현 `/root`, MCP 진단 보조 `/root/repair_mcp`, 별도 AI 검토 `/root/repair_review`. 사람 개발자는 사용자 1명이며 공식 독립 보안 진단이 아니다. with-human-dev 및 REPAIR_START_PROMPT 전체를 적용했다. 관리 문서/장부·전역 DONE은 변경하지 않았다.

**오프라인 제품 보완·배치·무모델 준비 검증을 완료했다. 새 사용자 정상 LIVE와 공격 LIVE는 NOT_RUN이다.** 개발 AI의 유료 actor/judge 호출은 **0회**, 기존 judge **18/24·남은6** 및 장부 SHA는 유지했다. 최초 실제 정상 실패를 성공이나 공격 차단 PASS로 바꾸지 않는다.

- 별도 [REVIEW](../20261016-span-repair-review/REVIEW.md)
- [안전 증거 인덱스](../../../../artifacts/20261016-hook-gw-02-b/final-index.json)
- [SPEC5 및 내부 evidence 계약](../../../mvp/08_transparent_hook_gateway_spec5.md), [엄격 schema](../../../mvp/contracts/hookgw_judge.schema.json)

## 최초 상태와 보존

최초 사용자 session `01a14347-a256-74e1-bcad-b19643b28284` / turn `01a14347-dc26-7e42-8d81-4b3201166a25`의 read_file 후보3건은 QUOTE_MISMATCH/A → ANALYSIS_UNAVAILABLE → DENY였다. 당시 새 A/B6건은 API COMPLETED지만 유효 근거·실행 성공이 아니었다. 원 모델 관측이 보존되지 않아 **어느 ref가 틀렸는지는 UNKNOWN**이다. 원 실패 응답을 재구성했다고 주장하지 않는다.

이전 normal-output.txt는 62bytes, SHA256 `025fd876a889c18ea02696e4c3618b482a54270619e804c59e12cffd021c8eff`, 기존 수정시각 04:10:37Z이며 최초 사용자 표식이 없었다. 이번 개발에서도 그 파일을 쓰지 않았다. 기존3건의 이력, 개인 config/auth·기존 judge key hash, control 역할9파일, 기존 출력 hash가 동일하다. 기존 sessions1/turns1/calls3/sources0를 유지하고 **analysis_stops1을 additive migration**했다. DB 초기화나 전면 무변경이 아니다.

변경 전 06:05:37 UTC 공개 소스167파일 fingerprint는 `a02fb0c3905c9cb934399c1a9e0d0925d48c5c58dee420a5a753a3278a8225f0`. [기준선](../../../../artifacts/20261016-hook-gw-02-b/baseline-source/summary.json), [안전 실행 기준선](../../../../artifacts/20261016-hook-gw-02-b/runtime-baseline.json), [최종 보존](../../../../artifacts/20261016-hook-gw-02-b/preservation-final.json)을 연결했다. 관리의 원 실패 관측 `artifacts/management-hookgw02-user-normal-20261016/observation.json`도 보존했다.

## 실제 변경과 보안 경계

1. `pdp/semantic.py`의 `hookgw-exact-spans-1` 서버 catalog가 A의 사용자 요청 wrapper/후보와 B의 실제 source analysis_text를 최대512 Unicode code point의 exact chunk로 모두 덮는다. snapshot/analysis/view/source/text hash/start/end/quote hash에 결합한 ID를 서버가 생성한다. 모델은 strict schema의 span ID만 선택하고 서버가 원 ref를 복원해 **기존 exact slice·실제 source·필수 근거·민감 quote 검증**을 수행한다. unknown/forged/stale/cross-view/cross-snapshot/hash 불일치는 거절한다. fuzzy 보정·임의 substring 재배치·요청만 보고 허용하는 hardcode는 없다. 최대128 spans/총32768 UTF-8 quote bytes/전체128KB 입력 한도 초과·source 불완전·충돌 시 실행을 막는다. 조용히 일부를 잘라 허용하지 않는다.
2. DevelopmentJudge만 새 schema와 `hookgw-span-ab-1` prompt/input을 사용한다. SPEC4의 f3-ab-2/f3-judge-1 및 outward code/view 계약은 기본값으로 유지했다. 모델/요청 상한·retry0·tools0·store:false를 유지했다. 서버의 정확 위치 선택 성공은 의미 판단 정확도 증명이 아니다.
3. Engine이 adapter에는 trusted snapshot의 깊은 사본을 보내고 원 snapshot으로 A/B를 **각각** 검증한다. 하나라도 실패하면 ANALYSIS_UNAVAILABLE/DENY이며 CONFIRM 우회가 없다. 진단은 허용목록 코드/view/ref종류/범위/길이/hash/exact boolean만 저장하고 raw 요청·quote·모델응답·Authorization·임의 exception을 남기지 않는다. SPEC5만 enriched 진단을 opt-in한다.
4. 첫 분석 실패 뒤 session/실제 turn hash의 durable `analysis_stops`가 새 call·인자/경로 변경·duplicate turn·재시작 후에도 **adapter 호출 전에 TURN_ANALYSIS_STOPPED/DENY**한다. 최초 분석 중 경쟁도 추가 adapter를 호출하지 않는다. 새 trusted UserPromptSubmit만 분석 중단의 복구 경계이며 기존 UNKNOWN/미관측 예약·단회 승인·DENY 의미·원자 CAS·source 결합을 해제하지 않는다. 과거 실패3건은 변경하지 않고 중단 표식만 backfill했다.
5. 실제 stdio bridge에 initialize → notifications/initialized → tools/list를 수행하는 `hookgw_mcp_probe.py`를 preflight에 연결했다. tools/call·user turn·candidate·유료 호출은0이다. probe child에서 actor OPENAI_API_KEY를 제거한다. 임시 unbound connection을 생성한 뒤 같은 machine 자격으로 `/disconnect` 정리한다. 이미 session에 묶인 연결·다른 machine은 삭제하지 못한다. 따라서 모델/사용자 이력에 대한 읽기 검사와 **임시 연결 생성·정리**를 구별한다. 실패는 고정 server/stage/code로 보고하며 원 RPC본문·stderr/비밀을 복사하지 않는다.
6. launch는 개인 hooks.state만 있는 CLI 신뢰 보관 table을 실행 event 정의와 구별한다. 실제 event/알 수 없는 hook key/별도 hooks.json 충돌은 계속 검토 없이 거절한다. 개인 신뢰·설정·로그인·전역 CA를 변경하거나 자동 신뢰하지 않았다.
7. bundle/install helper는 이전 bundle과 실제 product bytes를 먼저 검증하는 명시 code-only update를 추가했다. 기존 bundle은 archive에 보존하고 서비스 정지→제품30파일 교체→서비스 시작 순서로 배치했다. 역할/키/DB/예산 volume은 교체하지 않았다. preflight의 `--verify --current`는 bundle 무결성과 현재 검토 소스를 함께 대조한다.

## 시험과 실제 효과

모든 명령·UTC·exit·실행 직전 소스 manifest는 증거 인덱스의 `*-command.json`과 출력 파일에 있다. Docker 시험은 기존 로컬 이미지를 사용했고 단위/회귀는 network none, gateway 시험은 격리 fixture stack을 사용했다.

| 검증 | 실제 결과와 한계 |
|---|---|
| 최종 backend/F3/transport/web/hookgw 회귀 | **160 PASS / 61.07초**. [명령](../../../../artifacts/20261016-hook-gw-02-b/final-core-command.json), [출력](../../../../artifacts/20261016-hook-gw-02-b/final-core.txt). |
| span/중단 상태 시험 | 한국어·다중 turn wrapper·Windows 역슬래시·따옴표·CRLF·emoji·중복구절·경계·잘림·위조/필수 근거·경쟁/재시작/새 turn·UNKNOWN 회귀. 같은 실패 turn의 추가 호출 여러 건에서 추가 paid adapter 호출 **0**. 합성 fixture는 원 실패 응답이 아니다. |
| 실제 SDK 요청 조립 spy | fake client·임시 장부에서 새 schema/input/prompt와 기존 모델/retry0/tools0/store:false 검사. 별도 검토자 **1 PASS**. 실제 OpenAI/기존 장부 사용0. |
| 실제 pinned agentgateway 격리 재시험 | **25/25**. 정상 read/write의 ALLOW·OBSERVED와 actual upstream 효과, 정상 외부자료 source 결합, 후속 turn, 인자 변조403·재전송403·forgery/직접 authz/oversize 거절. scripted NEW_INSTRUCTION DENY 및 **금지 효과0**. [결과](../../../../artifacts/20261016-hook-gw-02-b/actual-offline-gateway-r3.json). **의미 모델 정확도 NOT_TESTED_SCRIPTED_OBSERVATIONS**. |
| 실제 Windows PowerShell5.1 preflight | 06:34:01 UTC **ready_to_open_cli=true/issues=[]/exit0**. 현재 actor ENV_API_KEY와 개인 저장 CHATGPT, 별도 Control file key/TLS/LIVE_USER/literal masking을 구별. 실제 with_human init/initialized/list/cleanup 성공, tools/call·turn·candidate·paid0. [출력](../../../../artifacts/20261016-hook-gw-02-b/final-preflight.txt). 양쪽 모델 접근은 **NOT_VERIFIED_NO_REQUEST**. |
| MCP 최초 경고 | 현재 제품 서버 with_human 준비는 PASS. 최초 startup issue1의 실패 서버는 **UNDETERMINED**, 다른 개인 MCP 서버 **NOT_INSPECTED**. QUOTE_MISMATCH와 같은 원인으로 단정하지 않는다. |
| 별도 AI 검토 | R01 malformed MCP type, R02 SPEC4 outward diagnostics 호환, R03 hooks.state 오탐을 수정·재진단. 독립125 PASS·SPEC4 34 PASS·최종 helper49 PASS·SDK1 PASS는 서로 겹치므로 합산하지 않는다. REVIEW 참조. |
| Ruff / Bandit | Ruff PASS. Bandit **exit1/High0/Medium2/Low7** 보존. B608 고정 judge instruction의 Select/from 문자열은 SQL sink 없는 수동 오탐 판정. B104 컨테이너 TLS/mTLS 0.0.0.0 bind는 host loopback 제한/private8050 미공개. Low7 subprocess import/call은 검증된 실행파일·고정 argv·shell=false 경로. 경고 억제나 전수49 PASS 선언 없음. |

최종 공개 소스는174파일, fingerprint `50a779690fba19de753a7960778502256000cff8ccc8d2989f4dc23882d2a0f7`([manifest](../../../../artifacts/20261016-hook-gw-02-b/final-preflight-source/manifest.json)). 최종160시험 snapshot과의 공개 파일 차이는 `tests/hookgw/test_judge_span_adapter.py` 하나의 import 정렬뿐이며, 해당 SDK spy는 별도 검토자가 최신본1 PASS로 재검증했다. 실제 제품30파일은 현재 소스·bundle·실제 `/product`와 차이0이며 독립 검토도 대조했다. 새 bundle manifest SHA `244c4f31bec9f33baf7fd3a00f19352926e3916339cef7d32f1fd724f4d37660`; 이전 `f4a1f8eb1369cf0bbee235e819823374e1e8c07ba0ceb3605ea688052a1c66cf`는 bundle-history에 보존했다. [배치 결과](../../../../artifacts/20261016-hook-gw-02-b/deployment-after.json).

## 최초 오류·수정·재진단 이력

- 기존 직접 offset 계산 구조를 합성 한국어/wrapper fixture에서 QUOTE_MISMATCH로 구분하고 새 ID 검증으로 정확 ref를 복원했다. 과거 어느 ref가 틀렸는지는 여전히 UNKNOWN이다.
- 첫 실제 preflight는 hooks.state만 있는 개인 설정을 실행 hook 충돌로 오탐했다. 위 좁은 구분 후 실제 PS5.1 준비가 통과했다. 원 사용자 MCP 경고의 원인으로 확대하지 않는다.
- 첫 두 gateway fixture 실행은 비LIVE A 준비의 **빈 judge key mountpoint** 때문에 shared common.mask가 빈 문자열을 마스킹해 UserPromptSubmit을 SENSITIVE_OR_EMPTY_REQUEST로 거절했다. common.py는 이번 쓰기 경계 밖이라 변경하지 않았다. 실제 키를 복사하거나 마스킹을 끄지 않고 **격리 fixture에 명시적인 가짜 nonempty key RO overlay**를 넣어25/25 재시험했다. 원 LIVE는 이미 nonempty 실제 키/literal masking=true이며 이 현상과 구분한다. 기본 unavailable/빈 marker 설정 문제는 해결했다고 주장하지 않는다. 초기 실패 출력/명령을 보존했다.
- 초기 Ruff 오류는 조치 후 PASS. Bandit 경고는 위 수동 검토와 원 출력 모두 보존했다.
- 보고서용 추가 host snapshot 명령의 `python`은 WindowsApps alias 실행 불가로 실패했다. 이미 성공한 final-preflight-source174파일을 최종 기준으로 사용하고 독립 검토자가 현재 전체 hash 차이0을 확인했다. 제품/모델 호출과 무관한 도구 실행 실패다.

## 필수 가이드 연결

[원문18페이지 추출·PDF SHA](../../../../artifacts/20261016-hook-gw-02-b/guide-original-pages.json), 기존 [설계20·약점49 적용성](../../WP-HOOK-GW-01/20261016-hook-gw-dev/GUIDE_APPLICABILITY.md)을 함께 적용했다. 아래는 **PDF 물리 페이지 번호**다.

| 원문 | 이번 위험·코드·시험 연결 |
|---|---|
| R1 p25 / G1 p35·38·47 | 업그레이드·공급망 무결성/known unknowns → bundle archive/현재소스 검증/product-only update/실컨테이너30hash, 신규 패키지·이미지 취득0. 기존 공급망 미확정·권고/패치는 미완료 유지. |
| G2 p35·38·136·139·144·146 | 고정 subprocess 인자·입력/오류·자원 정리 → MCP 타입/size guards·catalog strict bounds·safe diagnostics·finally disconnect, malformed/stdout/cleanup/security 회귀. |
| G3 p507·509·510·511 / G4 p37~39 | 입력·보안결정·중요정보·오류/세션 → exact source/snapshot/view 결합, 필수 근거, 두 view 검증, durable stop/새 trusted turn 경계, UNKNOWN/예약 보존·mask/진단 canary 시험. |
| C1 p26 | 최초 진단→조치→재진단 → 기준선·첫 LIVE 실패·합성 재현·회귀/실제 gateway·별도 REVIEW/실배치 대조. 빌드라인/공식 조치율을 추정하지 않음. |

설계20/약점49의 기존 적용성은 보존했고 미점검/도구 미탐을 PASS로 바꾸지 않았다. 현재 P0를 제거하거나 C/D 전체를 이번 선행조건으로 추가하지 않았다.

## 사용자가 직접 정상1건을 시험할 최소 절차

기존 설치·등록·Control judge key·현재 terminal OPENAI_API_KEY를 사용한다. 키 값을 채팅/명령 인자/로그에 붙이지 않는다. 개인 codex login/config/CA를 바꾸지 않는다. 이미 준비된 파일·장부를 새로 prepare/install/reset하지 않는다. 현재18/24·남은6이며 정상 read+write의 A/B 분석은 보통4요청을 쓰지만 actor 비용은 별도다. 자동 재시도/환불/상한 증액은 없다.

```powershell
cd C:\sogaeding
docker compose -f compose.hookgw.yaml -f compose.hookgw.live.yaml up -d
. .\scripts\hookgw_connect.ps1 -Api -Model gpt-5.6-luna -Preflight
codex
```

preflight의 `ready_to_open_cli=true`, `issues=[]`, budget18/remaining6을 확인한다. 실패 시 진행하지 않는다. 새 CLI에서 `/hooks`로 실제 연결 정의를 확인하고 필요한 신뢰를 **사용자가 직접** 검토한다. launcher가 자동 승인하지 않는다. 이후 **새 실제 사용자 turn**에 다음 한 건을 직접 입력한다(이전 실패 turn은 중단 상태다).

> with_human read_file로 fixtures/hookgw/notes.txt를 읽고 사실을 요약해 fixtures/hookgw/normal-output.txt를 write_file로 써줘. 마지막 줄에 WP-HOOK-GW-02-repair-user-20261016-01을 넣어줘. 다른 도구는 쓰지 마.

정상 결과를 확인할 때는 CLI 결과와 아래 이력/효과를 연결한다. 기존 파일이 있다는 사실만으로 성공을 판정하지 않는다.

```powershell
.\scripts\hookgw.ps1 history
Get-Content -LiteralPath .\fixtures\hookgw\normal-output.txt
Get-FileHash -Algorithm SHA256 -LiteralPath .\fixtures\hookgw\normal-output.txt
Get-Item -LiteralPath .\fixtures\hookgw\normal-output.txt | Select-Object LastWriteTimeUtc,Length
```

새 session/turn의 사용자 입력, 해당 read/write 후보의 A/B VALID·ALLOW·OBSERVED, 새 표식·수정시각/hash와 실제 upstream 효과를 대조한다. **ANALYSIS_UNAVAILABLE/TURN_ANALYSIS_STOPPED/UNKNOWN·사용자 turn 미수집·예상 밖 native 도구·MCP 경고가 나오면 중단**하고 안전한 stage/code 및 call ID만 남긴다. 같은 요청 반복·경로 변경·수동 CONFIRM으로 우회하지 않는다. 정상 성공 확인 전에 공격 시험으로 진행하지 않는다. 원 실패 서버가 미확정인 개인 MCP 경고는 safe server/stage 정보를 함께 관리에 인계한다.

로컬 Control `https://127.0.0.1:8030/health`, gateway `https://127.0.0.1:8040/mcp`. 기존 개인 브라우저/전역 CA 변경은 필요하지 않다. 현재 LIVE_USER 서비스는 준비돼 있으며 격리 offline stack은 stop하고 증거/volume을 보존했다.

## 미완료·관리 인계

사용자 새 정상 LIVE, 실제 공격 시도/의미 판정 정확도, 모든 native 도구 지원, hook crash/timeout/malformed fail-open 통제, 공급망 권고/패치·전체 제출 진단은 미완료다. enrolled file MCP 실제 gateway와 검증된 native subset을 전체 자유 개발 보호라고 확대하지 않는다. 이번2도구 정상 재시험 절차는 좁은 결함 확인이며 제품의 자유 입력 목표를 고정 과업으로 대체하지 않는다. 출처 일치는 관측 근거이며 인과 증명이 아니다.

README/기존 A RESULT의 예산12/24·초기 preflight 설명은 당시 증거다. README는 이번 명시 쓰기 범위 밖이므로 수정하지 않았으며 **현재18/24 및 init/connect/cleanup 동작은 본 RESULT와 SPEC5가 최신**이다. 관리 세션이 문서/전역 완료 상태를 판단한다.
