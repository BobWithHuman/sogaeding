# WP-HOOK-GW-02 B 보완 / T-HG-04 별도 AI 검토

검토자 `/root/repair_review`, 구현자 `/root` 및 MCP 진단 담당과 분리한 AI 역할이다. 사람 개발자는 사용자 1명이며 공식 독립 보안 진단이 아니다. 검토자의 쓰기 범위는 이 REVIEW와 `artifacts/20261016-hook-gw-02-b-review/`뿐이다. 유료 actor/judge 호출은 0회다.

**판정: WP-HOOK-GW-02 B 보완/T-HG-04의 좁은 오프라인 제품 보완 인계는 수용 가능하다. 최초 실제 정상 LIVE 실패는 그대로이며 사용자 정상/공격 LIVE와 전체 자유 개발 MVP 수용은 미완료다.** HG02B-R01/R02/R03은 수정·독립 재진단으로 조치 확인했다. 공식 보안 진단/전역 DONE·배포 승인을 내리지 않는다.

## 기준과 최초 실패

REPAIR_START_PROMPT 전체, 최신 AGENTS, 작업팩14의 A/B/C 및 B 보완, 실제 정상 LIVE 실패 관리 검토, SPEC5, 기존 단계 A RESULT/REVIEW, with-human-dev 역할·워크플로·증거 지침을 읽었다. 개인 전역 인증/설정·키/DB/예산/원증거·관리 장부 보존, server exact span 결합, 정확 ref와 필수 근거, 실행 전 fail-closed, 동일 실제 turn 분석 실패 뒤 추가 adapter 호출 0, 무모델 실제 MCP initialize/initialized/list와 tools/call 0이 이번 좁은 기준이다.

첫 사용자 정상 LIVE는 read 후보 3건 모두 QUOTE_MISMATCH/A → ANALYSIS_UNAVAILABLE → DENY이고 정상 작업 FAIL, 공격 NOT_RUN이다. judge 18/24·남은 6은 과거 12/24와 구별한다. 원 모델 관측이 남아 있지 않아 어느 ref·offset·quote가 틀렸는지는 미확정이다. 합성 한국어/JSON offset fixture의 실패를 과거 원 모델 응답 복구로 표현하지 않는다.

초기 소스에서는 A exact offset을 모델이 계산하는 구조, A 검증 예외시 B 미검증, 분석 장애 후 새 call의 같은 turn 재분석 비용 소비를 확인했다. 이 최초 구조와 실패 증거를 덮어쓰지 않고 수정 후 검증을 분리한다.

## 검토 한계

정상 native 일반 개발·hook 프로세스 crash/timeout/malformed fail-open·공급망 권고/패치와 실제 사용자 의미 모델 검증은 이번 수정의 완료로 바꾸지 않는다. source span 정확 일치는 의미 판단의 정확도나 인과 증명이 아니다. 계획/전역 DONE·예산/키·개인 auth를 검토자가 변경하지 않는다.

## 초기 발견

| ID | 발견 | 조치 확인 |
|---|---|---|
| HG02B-R01 | 무모델 MCP probe의 initialize 결과에서 capabilities/serverInfo가 null·list인 경우 AttributeError가 안전한 stage/code 보고 경계를 벗어날 수 있다. 정확 타입 검사와 합성 malformed 응답 회귀가 필요하다. | 조치·독립 재진단 완료. |

HG02B-R01은 capabilities/serverInfo 타입 검사·helper import 보호·잘못된 tools 이름 타입 회귀로 조치됐다. 독립 오프라인 `test_mcp_startup.py` 19 PASS 후, 도구 이름 타입 회귀가 추가된 최신 20개와 검토자 작성 13개를 함께 실행해 33 PASS/3.82초를 확인했다. 앞선19·30과 겹치므로 합산하지 않는다.

HG02B-R02는 공유 diagnostics의 enriched metadata가 SPEC4의 `{code,view}` additionalProperties:false 계약을 깨뜨릴 수 있다는 발견이다. 작성자가 `failure_details(error,enriched=False)`를 기본으로 보존하고 SPEC5만 opt-in하여 code/view 의미와 outward legacy schema를 유지했다. 아래 최종 SPEC4 회귀와 계약 대조로 조치를 확인했다.

중간 독립 시험은 [independent-engine-span-mcp.json](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-engine-span-mcp.json)에 명령·UTC·exit·해당 소스 hash를 기록했다. Docker `--network none --read-only`, UID10001, 합성 자료·임시 DB만 사용했다. 검토자 작성13개는 한국어/다중 turn/CRLF/emoji/역슬래시/따옴표·원문 전체 coverage, snapshot/analysis/request/grant/candidate/source 변경·view/source hash·예약 source ID·한도 거절, 진단 allowlist canary, 첫 실패 뒤 새 call/route/인자/duplicate turn/restart에서 추가 분석0, 첫 분석 중 경쟁 호출0, 새 trusted turn 복구, adapter snapshot 변조 거절을 확인했다. fake judge의 관측 선택은 의미 모델 정확도 증거가 아니다.

## 구현 경계 검토

서버 catalog는 user_request wrapper·canonical candidate와 B의 실제 source analysis_text를 Unicode code point의 최대512문자 chunk로 모두 덮는다. source 원 hash·완전성·예약 ID/중복 source ID를 검증하고, 총32768 UTF-8 byte·128 span 또는 전체128KB 입력을 넘으면 분석을 중단한다. span ID는 contract/snapshot hash/view/source/text hash/start/end/quote hash에 결합하며 모델이 낸 quote나 위치를 서버가 fuzzy 보정하지 않는다. 모델 출력은 별도 span ID schema로 제한하고 서버가 정확 ref를 복원한 후 기존 validated()의 exact slice·source·필수 근거·민감 quote 검사를 재사용한다. 후보가 사용자 요청을 따른다는 hardcode는 추가되지 않았다. SPEC4의 schema/prompt 기본값은 유지하고 DevelopmentJudge만 새 schema·prompt/input을 opt-in한다.

Engine은 adapter에 trusted snapshot의 깊은 사본을 전달한다. 각 A/B 관측을 각각 검증해 한쪽 실패가 다른 쪽 유효성을 숨기지 않으며, 하나라도 실패하면 ALLOW/CONFIRM을 발급하지 않는다. 허용목록 코드/view·ref종류·범위·길이·hash·exact boolean만 진단으로 저장한다. raw 사용자/quote/모델응답/키/Authorization/임의 exception은 진단에 넣지 않는다. 분석 실패 후 session/turn hash에 결합한 durable analysis_stops를 저장하고 같은 실제 turn의 새 call·경로·인자 변형/재시작/duplicate turn에서 adapter를 부르기 전 DENY한다. 과거 failed call은 수정 없이 additive stop migration한다. 새 trusted user turn은 별도 경계이고 기존 UNKNOWN·미관측 예약을 자동 해제하지 않는다.

MCP 무모델 준비는 실제 stdio bridge subprocess에 initialize→notifications/initialized→tools/list만 순차 전송하고 등록 read_file/write_file 목록을 확인한다. OPENAI_API_KEY는 probe child env에서 제거한다. temporary unbound connection만 machine 자격으로 생성·finally 삭제하고 session에 이미 묶인 connection이나 타 machine은 삭제하지 못한다. 기존 사용자 turn/candidate/source/예산/개인 MCP 설정은 변경하지 않는다. 실패 server=with_human·stage·allowlist code를 보고하며 임의 stderr/RPC본문을 보고서에 복사하지 않는다. 당시 startup issue1의 실패 서버는 여전히 UNDETERMINED이며 개인 다른 MCP 서버는 NOT_INSPECTED다.

## 독립 검증

- 검토자가 직접 Docker network none/read-only/UID10001에서 최신 `tests/hookgw`112개와 검토자 자체 시험13개를 실행해 **125 PASS/7.54초, exit0**을 확인했다. [명령·소스 해시](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-hookgw-final.json).
- 공유 코드의 기존 `tests/f3` 전체를 따로 실행해 **34 PASS/29.85초, exit0**을 확인했다. [SPEC4 독립 증거](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-spec4.json). 기존 exact diagnostics outward code/view·원문 ref 필수·SDK tools0/retry0·기존 budget 의미의 회귀를 포함한다. HG02B-R02는 이 재진단으로 조치 확인했다.
- Docker pipe 권한 때문에 최초 기본 sandbox MCP 시험은 실행 전에 실패했다. 허용된 승격으로 실제 오프라인 시험을 수행했으며 자동 승인 심사 거절은 없었다. sandbox 거절을 제품의 공격 차단 PASS로 계산하지 않는다.

검토자는 별도 SCA/전체49약점 도구 진단, 실제 OpenAI 호출, 실제 사용자 의미 정확도, native 전체 경로 시험을 수행하지 않았다. 작성자의 결과를 검토자의 독립 실행으로 바꾸지 않는다. 이전19·30·33은125와 겹치므로 합산하지 않는다.

## 실제 preflight의 추가 발견·재진단

HG02B-R03: 첫 실제 Windows PowerShell5.1 preflight가 `Existing hook config requires a reviewed merge`로 JSON/MCP 검사 전에 중단됐다. 검토자가 개인 config를 읽기 전용으로 **키 이름/자료형만** 확인한 결과 `hooks` 아래에는 CLI가 저장한 `state` table만 있고 실행 event 배열은 없었다. 예전 검사 `any(layer.get("hooks"))`가 consent metadata와 실행 정의를 혼동했다. 개인 설정이나 신뢰 hash를 지우는 해결은 사용하지 않았다.

작성자는 state-only를 per-event overlay와 충돌하지 않는 보관 정보로 구분했다. 다른 event/알 수 없는 hook 키나 hooks.json은 계속 reviewed merge 없이는 거절한다. 새 자동 신뢰/승인 flag를 넣지 않았고 기존 /hooks 상태를 덮지 않는다. 검토자가 `test_api_preflight.py`를 독립 재실행해 **28 PASS/2.04초**(consent-only 통과·파일 불변·실행 event 혼합 거절 포함)를 확인했다. [추가 독립 증거](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-trust-state.json). 앞선125 중 기존 API 시험과 겹치므로 합산하지 않는다.

작성자의 `actual-preflight-trust-state.txt`는 06:25:40 UTC Windows 실제 준비 결과 **ready_to_open_cli=true/issues=[]**이며 Codex0.154.0·현재 ENV_API_KEY actor와 개인 저장 CHATGPT 구별, TLS/LIVE_USER·기존 literal masking, 실제 stdio initialize/initialized/list와 unbound connection 정리, tools/call/turn/candidate/paid 모두0을 보고했다. 기존 budget **18/24·남은6·SHA256 fd2706d6739db9e84b1a328e927d4cbe6352d8ff4dc7143fb7c634ec6424b660** 그대로다. 원래 startup issue1 서버를 식별했다고 주장하지 않는다.


## 동결 배치·실제 gateway·보존

이전 bundle manifest `f4a1f8eb1369cf0bbee235e819823374e1e8c07ba0ceb3605ea688052a1c66cf`는 bundle-history에 보존했다. 서비스 정지 후 UID10001/network none의 명시 code-only helper가 기존 product volume의 기존29개 파일 bytes/manifest와 보존 archive를 대조한 뒤 새30파일을 게시하고 서비스를 재시작했다. 기존 역할/키/DB/예산 volume을 교체하지 않았다. 부분 실패 시 자동 덮어쓰기/롤백·예산 환불 경로는 추가하지 않았다.

검토자가 실제 Control 컨테이너의 공개 파일 hash를 직접 조회해 **현재 host 소스·동결 bundle·실제 /product의30파일 차이0**을 확인했다. manifest는 `244c4f31bec9f33baf7fd3a00f19352926e3916339cef7d32f1fd724f4d37660`, engine/judge import는 모두 `/product/src/app/transparent/`다. [독립 배치 대조](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-deployed-bundle.json)는 DB/키/모델 접근 없는 공개 코드 대조다.

작성자의 실제 gateway offline 재시험 `actual-offline-gateway-r3.json`과 명령/fixture/분리 effect bind를 검토했다. **25/25**: 정상 read/write는 actual upstream 효과와 OBSERVED·A/B VALID를 연결했고, 인자 변경·replay·직접 authz·forged user·oversize를 거절했으며 scripted NEW_INSTRUCTION 후보 DENY·금지 파일0을 확인했다. 이 25개는 검토자의 독립 실행이 아니며 **의미 모델 정확도 NOT_TESTED_SCRIPTED_OBSERVATIONS**다. 최초 두 offline 실행은 A의 빈 judge key mountpoint를 fake key overlay 없이 사용해 common.mask가 빈 문자열을 치환하는 설정 문제로 UserPromptSubmit을 거절했다. 기존 LIVE는 nonempty 실제 키 overlay/literal masking=true라 이 시험 문제와 구별한다. common.py/제품 마스킹을 끄거나 실제키를 시험으로 복사하지 않고, 격리 FixtureJudge에 명시 fake nonempty key를 RO overlay해 재시험했다. 최초실패를 PASS로 바꾸지 않는다. 효과는 artifacts/offline-effects에 격리하여 기존 사용자 normal-output 파일을 쓰지 않았다.

작성자의 최종 범위 backend/F3/transport/web/hookgw 회귀 **160 PASS/61.07초**, Ruff PASS를 검토했다. Bandit는 **High0/Medium2/Low7, exit1**을 보존했다. B608은 고정 model instructions의 Select/from 문자열에 대한 경고이며 SQL 실행 sink가 없다. B104는 컨테이너 내부 TLS/mTLS bind이며 공개 listener는 Compose loopback 제한, private8050은 미공개다. Low7은 subprocess import/호출에 대한 경고로 검증된 실행파일/고정 argv/shell=false 경로를 읽었다. 경고를 감추거나 이 수치를 전체49약점 PASS로 바꾸지 않았다.

`preservation-final.json`과 전후 안전 관측은 원래3개 failed call 내용, 개인 config/auth/기존 judge key hash, 기존 사용자 effect hash, 기존 control 역할9파일의 불변을 보고한다. production sessions1/turns1/calls3/sources0는 유지되고 additive analysis_stops1만 추가됐다. budget18/24·남은6·원 SHA가 같다. 분석 장애 후 중단 상태를 추가하는 DB migration을 DB 초기화/전면 무변경으로 표현하지 않는다.

마지막 host helper 수정(비객체 MCP 입력, cleanup 형식 오류, --verify --current)은 영향 범위 MCP/API preflight **49 PASS/3.17초**로 검토자가 독립 재검증했다. [최종 좁은 재시험](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-mcp-preflight-closure.json). 이전125 전체/34 SPEC4와 겹치는 부분을 합산하지 않는다.

## 필수 가이드와 남은 판정

이번 guide-original-pages.json의 원문 식별/추출과 이전 GUIDE_APPLICABILITY의 설계20·약점49 적용성 근거를 대조했다. G2 PDF35~38의 고정 실행 인자, PDF144~146의 오류·자원 정리, G3 PDF507~511의 입력·보안결정·중요정보·예외/세션, G4 PDF37~39의 설계통제, R1 PDF25/G1 PDF35·38·47의 무결성·기존 공급망 미확정 보존, C1 PDF26의 최초진단→수정→재진단을 이번 코드와 위 시험에 연결한다. 새 패키지/이미지 취득·개인 CA/인증 수정·유료 호출은 없고, 이번 수정 때문에 C/D 전체를 선행조건으로 추가하지 않았다.

사용자는 새 실제 user turn에서 정상1건을 직접 시험해야 한다. 정상 의미 판정 성공·공격 식별·interactive /hooks 신뢰는 개발 AI가 실제 모델로 확인하지 않았다. 준비 실패·ANALYSIS_UNAVAILABLE·UNKNOWN·예상 밖 native 경로이면 중단하고 새 유료 재시도를 반복하지 않는다. 정상 성공 전 공격 시험으로 진행하지 않는다. catalog 선택 성공과 scripted 집행을 의미 모델 정확도 또는 인과 증명으로 확대하지 않는다. 정상 native 일반 개발·native hook 사망/timeout/malformed fail-open·공급망 권고/패치 확인은 그대로 남는다.


## 최종 소스·준비 재확인

검토자는 `final-preflight-source`의 **174파일 / fingerprint 50a779690fba19de753a7960778502256000cff8ccc8d2989f4dc23882d2a0f7**와 현재174파일 SHA256을 읽기 전용 대조해 차이0을 확인했다. [최종 manifest 대조](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-final-manifest.json). 새 `hookgw_judge.schema.json`은 Python SPAN_JUDGE_SCHEMA와 일치하는 시험·코드를 읽었다. 최종 helper에는 `--verify --current`가 적용돼 동결 bundle 자체 무결성과 현재 검토 소스의 일치도 함께 확인한다.

새 SDK spy 시험도 검토자가 독립1 PASS/2.61초로 확인했다. [independent-sdk-span.json](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-sdk-span.json). 실제 DevelopmentJudge/OpenAIJudge의 request 생성 흐름을 fake AsyncOpenAI로 대체하며 span catalog/schema/name 선택, 직접 offset helper 미전송, store:false/tools0/retry0, 동일 모델·임시18회 기준선에서2회 claim을 검사한다. 실제 OpenAI 요청/기존 예산/실키는 사용하지 않았다.

작성자의 **06:34:01 UTC 최종 실제 preflight**도 ready=true/issues=[]·실제 stdio init/initialized/list·cleanup·paid/tools/turn/candidate0·기존18/24 및 같은 SHA를 보고한다. 격리 offline stack은 stop으로 종료하고 DB/효과/최초실패 증거를 남겼다. production LIVE_USER는 사용자가 직접 시작할 준비 상태이며 개발 AI의 유료 분석은0이다. 이 상태가 실제 정상 의미 판단 성공을 뜻하지 않는다.

## 최종 인계 문서 대조

완성된 [RESULT](../20261016-span-repair/RESULT.md)와 [final-index.json](C:/sogaeding/artifacts/20261016-hook-gw-02-b/final-index.json)을 마지막으로 읽었다. 실제 정상 LIVE 실패/원 ref 미확정·유료0·예산18/24·temporary connection을 수반하는 무모델 준비·서버 span의 관측 한계·별도 시험 중복·기존 자유 개발 목표와 남은 native/fail-open/공급망을 구별한다. 새 표식의 사용자 정상1건·새 실제 turn·/hooks 직접 신뢰·첫 오류 중단·정상 성공 전 공격 금지 절차가 준비돼 있다. 개발 AI가 actual 의미 모델 성공이나 전체 MVP 완료를 선언하지 않는다.

RESULT의 로컬 상대 링크 전부 존재하며 누락0이다. final-index JSON을 파싱했고 보고된 최종 소스/배치/실행/보존 숫자와 원증거를 대조했다. final-core→final-preflight 두 manifest의 차이는 `test_judge_span_adapter.py` import 정렬1개뿐이며 제품 코드 차이0이고 해당 최신 시험을 검토자가 독립1 PASS로 확인했다. WindowsApps python alias 추가 snapshot 실패는 제품/모델 실패와 구별해 보고되고, 이미 성공한174파일 기준선 및 독립 현재 hash 대조를 사용한다. [최종 문서 검토 기록](C:/sogaeding/artifacts/20261016-hook-gw-02-b-review/independent-final-documents.json)에 문서 hash·링크·manifest delta를 남겼다.

**최종 판정 유지: 좁은 B 보완/T-HG-04 오프라인 인계 수용 가능. 사용자 새 정상/공격 LIVE 및 전체 자유 개발 MVP 수용은 미완료.** 이 문서 최종 대조에서 신규 runtime 변경·유료 호출은0이며 추가 인계 차단 발견은 없다.
