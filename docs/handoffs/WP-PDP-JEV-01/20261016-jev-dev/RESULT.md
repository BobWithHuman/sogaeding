# WP-PDP-JEV-01 RESULT

2026-10-16. START_PROMPT 전체·15번 계획·ADR-P02 선택적 채택·최신 관리 검토를 적용했다. 구현 통합 `/root`, 좁은 adapter/연결 보조 `/root/jev_adapter`, 별도 AI 검토 `/root/jev_review`. 사람 개발자는 사용자1명이며 공식 독립 보안 진단이 아니다.

**규칙 우선 PDP·Jev fake HTTP adapter·인자별 출처/문맥 분석의 오프라인 구현과 배치 검증을 완료했다. 실제 Jev 채택/한국어 정확도/공격 보호 성능 및 사용자 CLI 정상 과업은 NOT_RUN/미완료다.** 개발 AI의 실제 actor/judge/Jev 요청·키/계정 생성은0이다. native 일반 개발·hook 사망 fail-open·공급망 미완료, Codex 자체 auto-review403을 해결했다고 주장하지 않는다.

- [별도 REVIEW](../20261016-jev-review/REVIEW.md)
- [최신 계약·판정표·직접 CLI·TypeSafe 평가 요건](../../../mvp/09_rules_first_jev.md)
- [증거 인덱스](../../../../artifacts/20261016-jev-dev/final-index.json)
- [가이드 적용성 재검토](GUIDE_APPLICABILITY.md)

## 기준선·기존 작업 보존

착수 시 파일은 이전174파일/fingerprint `50a779690fba19de753a7960778502256000cff8ccc8d2989f4dc23882d2a0f7`와 같았다. 기존 span·두 view exact 검증·durable turn stop·인증/마스킹/암호화·TLS·원자 예약·단회 승인/UNKNOWN 기반을 재사용했다. 이미 진행된 Jev 제품 변경은 없었고 기존 작업을 초기화하지 않았다.

실제 runtime 기준선은 **OpenAI22/24·남은2**, 최초 실패3건 DENY와 새 read2건 ALLOW/READY, 총5건이었다. API COMPLETED/판정 ALLOW/READY/실제 OBSERVED는 다르다. 현재 Codex auto-review403과 개인 bob MCP 장애는 별도이며 설정/로그인/검토 정책을 바꾸지 않았다.

[전후 보존 대조](../../../../artifacts/20261016-jev-dev/preservation-final.json): **기존5건 history hash·역할 파일·개인 config/auth·기존 judge key·사용자 출력·예산 SHA 모두 동일**. 예산 SHA `c4d2b5a24f9f69a28be81dc12a4ddd9d3371727d48596fea52c9eb4a6bf37283`,22회 유지. OpenAI 원장을 초기화·환불·증액하거나 새 provider 장부로 재허용하지 않았다. 관리 문서/장부·AGENTS·skill·원 PDF는 읽기 전용이었다.

## 구현

`tool_schema.py`가 실제 upstream tools/list와 schema를 공유하며 MCP/지원 native subset의 action/target/options/payload를 파싱한다. 해석 불가와 NOT_APPLICABLE을 구분하고 실제 인자를 변경하지 않는다. 범위/숨김·보호·민감 키 파일/특수 경로와 구조화된 TLS 해제 설정은 모델0회 DENY다. 등록 공개 범위 읽기/지원 metadata는 기존 필수 통제 후 모델0회 ALLOW하며 기존 hash/forward/UNKNOWN을 우회하지 않는다. 일반 코드/문서 쓰기와 정상 외부 권고는 미확정 의미 경로에 남긴다. 부분 보안 config patch는 결과를 재구성하지 못하면 명시적 미지원 차단하고 일반 편집 전체를 끄지 않는다.

`jev_policy.py`는 서버 catalog의 복수 EXACT/NORMALIZED 링크와 slot별 MODEL_ASSOCIATION을 구분한다. 외부 문장의 경로 occurrence origin과 로컬 대상 identity/hash는 별개이며 LOCAL도 권한이 아니다. NOT_APPLICABLE/NO_OBSERVED_SOURCE/PROVENANCE_UNRESOLVED/ANALYSIS_FAILED와 실행 UNKNOWN을 구별한다. source 없는 생성값은 의미 판단으로 허용 가능하고, source 없음 자체를 안전 근거로 쓰지 않는다. 문서 전체의 모든 값에 사전 모델 분류를 추가하지 않았다.

관련 span 최대8/view evidence14 내에서만 지연 문맥 관측한다. A/B는 서로 다른 state/HTTP 요청이며 source text는 고정 instructions/criteria에 들어가지 않는다. 모델에는 짧은 e0…키만 보여주고 원 source/hash/ref는 서버 snapshot에 보존한다. 슬롯 연관·권유/데이터/금지·인용/미확정 관측 뒤 기존 exact/source/필수 근거 검증과 서버 combine을 통과해야 한다. 링크/모델 확률은 권한이나 인과 증명이 아니다. inline 마커 삽입/제거는 없다.

`jev.py`는 기존 **httpx0.28.1/BSD-3-Clause**를 재사용한 고정 TypeSafe endpoint/jev-1.13.0 adapter다. Choice/Noul 응답 model/key/type/유한 수치·확률·합계·argmax·confidence 수식·usage를 검증한다. TLS verify/proxy·redirect 비상속/retry0/15초·총20초/크기 제한·마스킹·별도 key 검사를 유지한다. 기본 NOT_AUTHORIZED, OpenAI fallback 없음. 별도 TypeSafe 정책/원장이 설정된 경우만 요청 전 요청수와64,000 input tokens를 보수 예약하고 실패·취소도 미환불한다. 현재 실제 TypeSafe key/config/장부/유료 한도는 만들지 않았다.

Engine은 router opt-in과 정책을 포함한 grant hash를 추가했고 GPT 기본 경로와 SPEC4 의미를 보존했다. generic hook 진단은 원 인자·transcript·exception 대신 고정 stage/code로 분리했다. hook HTTP redirect도 차단했다. 최초 CONFIRM의 정확 hash를 승인 대기 동안 유지하고 Codex 자체 승인 정책은 그대로 둔다.

## 실제 검증

모든 `*-command.json`에 정확한 argv·UTC·exit·실행 전 소스 manifest와 출력 경로가 있다. 단위/회귀는 Docker network none, 가짜 HTTP/임시 DB만 사용했다.

| 항목 | 결과·증거 |
|---|---|
| 최종 backend/F3/transport/web/hookgw | **282 PASS/66.25초**, [명령](../../../../artifacts/20261016-jev-dev/final-core-command.json), [출력](../../../../artifacts/20261016-jev-dev/final-core.txt). safe read/hard deny0, 정상 외부자료·권고·위험 인용, 생성값·복수/누락/LOCAL·파생 설정·위조/stale/cross-view/hash·응답/수치/API 오류·같은 turn 반복0·승인·경쟁·UNKNOWN/SPEC4 회귀 포함. |
| 실제 pinned agentgateway + fake Jev HTTP | **25/25**, [결과](../../../../artifacts/20261016-jev-dev/actual-gateway.json). 실제 read/write·OBSERVED 효과, 인자 변조/재전송403, 위조/직접 authz/과대입력 차단, scripted 위험 후보 DENY·금지 파일 효과0. 효과는 artifacts/offline-effects로 격리. **의미 정확도 NOT_TESTED_SCRIPTED_OBSERVATIONS**. |
| 별도 실제 rules-only 제품 | **10/10**, [결과](../../../../artifacts/20261016-jev-dev/actual-rules.json). 합성 trusted turn→공개 파일 실제 read/내용 일치/OBSERVED·model0, 미승인 쓰기 ANALYSIS_UNAVAILABLE/JEV_NOT_AUTHORIZED, 반복 TURN_ANALYSIS_STOPPED, 원 사용자 파일 불변/금지 효과0. 이것은 실제 actor CLI 과업이 아니다. |
| 실제 Windows PowerShell5.1 최종 preflight | **ready=true/issues=[]/exit0**, [출력](../../../../artifacts/20261016-jev-dev/final-preflight.txt). actor ENV_API_KEY vs 개인 저장 CHATGPT, TLS8032/8042, 실제 stdio init/initialized/tools-list/cleanup, literal masking=true. tools/call·turn·candidate·paid0. **semantic_write_ready=false/Jev NOT_AUTHORIZED/provider key·ledger 없음**. 모델 접근·/hooks 신뢰는 미검증. |
| 별도 AI 독립 검토 | 최종 **299 PASS**는 hookgw/F3/검토자28개를 포함하며 작성자282와 겹치므로 합산하지 않는다. code/runtime35파일·가이드·실제 gateway/rules/preflight 증거 대조, R01~R04 조치 확인. |
| 정적 진단 | Ruff PASS. Bandit exit1, **High0/Medium3/Low5**. 고정 GPT instruction 문자열 B608은 SQL sink 없는 오탐, Control/upstream B104는 컨테이너 TLS/mTLS bind·host loopback/private listener 통제, Low5는 고정 argv·shell=false subprocess 수동 검토. 경고 원본을 보존하고 전체49 PASS로 바꾸지 않았다. |

최종 테스트 소스189파일과 이후 최종191파일의 차이는 SPEC5/새 Jev 계약/비활성 LIVE 예제 **문서3개뿐**이다. 최종 공개 소스 fingerprint `2b7f8a4e7aa6dd47d1c9a30c0331ca6f79fffe8b310690b7b7434e67e8e65892`([manifest](../../../../artifacts/20261016-jev-dev/final-preflight-source/manifest.json)). 실제 제품 **35파일이 host·bundle·container와 동일**, import는 `/product/src`다. bundle manifest `816211073c88452ac28dcde64263ea097d540f6599d42d1447f3b66c1ed9d745`. 이전 `244c4f31…d37660` bundle을 archive에 보존하고 서비스 정지→code-only upgrade→동일 GPT 설정 재개했다. 역할/DB/예산 volume 교체 없음.

## 최초 발견·수정·재진단

- fake wire 초기39 PASS/1 FAIL: quoted JSON password 검출 누락을 typed-tree 재귀 검사로 수정. provider 초기 증거에 보존했다.
- R01 대문자 Choice enum을 question ID regex가 거절 → option key validator 분리, 실제 policy→HTTP 통합 회귀.
- R02 과업 지지 span을 모든 slot에 MODEL_ASSOCIATION으로 복사 → slot별 질문/링크로 분리.
- R03 structured config TLS 위험의 native patch 우회 → 완전 Add File 재구성·부분 config patch 미지원 차단. 정상 report 인용은 허용 시험.
- **R04** 새 hook 진단이 미승인 ApprovalPoll의 hash 없는 정상 CONFIRM을 거절 → 최초 CONFIRM만 hash 필수, poll은 원 binding 보존. 검토자 최초2 FAIL과 수정 후25 PASS를 함께 남겼다.
- 첫 lint는 RO cache 생성 실패 → --no-cache 재실행 PASS. Docker 기본 sandbox pipe 접근 실패는 승인된 Docker 검사로 재실행했으며 제품 차단 PASS가 아니다.
- 새 offline fixture 네트워크 생성은 Docker address pool 부족으로 FAIL. 다른 네트워크를 prune/delete하지 않았다. 이전 소유 fixture의 **정지·endpoint0/internal=true**를 확인한 뒤 새 DB로 해당 보존 네트워크만 재사용하여25/25를 확인했다. 최초 실패·변경 override를 보존했고 시험 후 stop했다.

## 필수 원문·공급망

R1 PDF25, G1 PDF35/38/47, G2 PDF35/38/136/139/144/146, G3 PDF507/509/510/511, G4 PDF37~39, C1 PDF26을 **원본에서18페이지 재추출·6PDF SHA 대조**했다([원문 근거](../../../../artifacts/20261016-jev-dev/guide-original-pages.json)). 별도 검토자도 기존 bundled pypdf로 다른 관련18페이지를 재추출·읽었다. 설계20/약점49 전 행의 적용성을 기존 기준과 재검토한 부록에서 새 provider/입력/전송/오류·세션 위험과 코드·동적 시험을 연결한다. 공식 조치율/전수 진단 PASS를 추정하지 않는다.

새 SDK/의존성·이미지 취득0. 기존 lock의 httpx0.28.1 hash와 실제 BSD-3-Clause/LICENSE SHA를 [재사용 근거](../../../../artifacts/20261016-jev-dev/reused-dependencies.txt)에 기록했다. TypeSafe [API](https://docs.typesafe.ai/api), [state](https://docs.typesafe.ai/concepts/state), [모델/CJK](https://docs.typesafe.ai/models), [1.13 한계](https://docs.typesafe.ai/model-jaggedness/jev-1.13), [confidence](https://docs.typesafe.ai/confidence)를 읽었고 세부 근거·한계는 제품 계약에 링크했다. 실제 요청/계정/키 생성 권한으로 해석하지 않았다.

## 사용자가 직접 확인할 최소 절차

현재 profile/코드는 준비됐다. **TypeSafe 모델은 미승인/비활성**이며 아래는 공개자료 읽기 연결 확인이다. OPENAI_API_KEY가 준비된 현재 PowerShell에서 개인 login/config를 변경하지 않고:

```powershell
cd C:\sogaeding
docker compose -f compose.hookgw.yaml -f compose.hookgw.jev.yaml up -d
. .\scripts\hookgw_connect.ps1 -Api -Model gpt-5.6-luna -JevRules -Preflight
codex
```

ready=true와 semantic_write_ready=false/NOT_AUTHORIZED를 함께 확인한다. `/hooks`의 정의를 직접 검토한 후 **새 실제 turn**에 다음만 직접 입력한다:

> with_human read_file로 fixtures/hookgw/notes.txt를 읽고 핵심 사실만 알려줘. 파일을 쓰지 마.

actor 비용은 사용자 실행 때 발생할 수 있고 이번 개발에서는 호출하지 않았다. 제품 judge는 이 read에서 모델0회다. 새 history는 `tools/hookgw_hook.py artifacts/runtime-hookgw/host-jev history`로 조회한다(정확한 bundled Python 명령은 제품 계약). 기존 hookgw.ps1 history는 GPT profile이므로 혼동하지 않는다. UI 출력·call/turn·ALLOW/READY→OBSERVED·실제 읽기를 연결하며 auto-review403/UNKNOWN/분석 오류·예상 밖 native 전환이면 중단한다. 반복/정책 우회로 해결하지 않는다.

Jev의 실제 의미 평가 전에는 사용자가 별도 TypeSafe 계정/key·보낼 합성자료·고정 모델/질문/threshold·요청/토큰/비용 상한·policy_id를 정해야 한다. [평가 세트](../../../../fixtures/jev/evaluation.json)의 calibration12/holdout4는 수동 기대값이며 실행 결과가 아니다. 현재0.90 임계치는 placeholder다. 비활성 mount 예제와 별도 원장 조건은 제품 계약에 있다. **원문·개인자료/프로젝트·키 전송은 준비 절차에 포함하지 않았다.**

## 남은 범위

실제 Jev 한국어·adversarial state/관련 span 누락·분류 성능, 실제 actor 정상/공격 작업, Codex auto-review403, native 일반 개발·hook crash/timeout/malformed fail-open, 공급망 권고/패치·전체 제출 진단은 남는다. Jev live key/policy/원장은 아직 없다. 공개 sentinel은 기존 빈 literal 마스킹 결함의 격리 호환 조치이며 공통 결함 해결이 아니다. 기존 실제 key/role bytes는 보존했고 TypeSafe는 별도 실제 key literal 검사를 한다. C/D 전체를 새 선행조건으로 추가하지 않았으며 전역 DONE/MVP 완료는 관리 세션이 판단한다.
