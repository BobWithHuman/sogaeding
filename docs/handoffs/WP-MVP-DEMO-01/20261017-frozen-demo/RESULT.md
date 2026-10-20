# T-DEMO-04 — FROZEN_DEMO_READY / NEW_LIVE_NOT_RUN

2026-10-17. with-human-dev로 같은 두 실제 프롬프트의 정상 과잉 CONFIRM을 수리하기 위한 입력·질문을 명료화하고, 무모델 검증과 단회 continuation 준비를 완료했다. **새 실제 모델의 정상 안정성은 NOT_RUN**이며 이후 사용자 두 보고서의 자동 ALLOW/OBSERVED·각쓰기1·PDP승인0으로 수용한다. 합성 응답의 성공을 새 모델 정확도로 보고하지 않는다.

## 최초 진단과 원 응답 재현

원 공개 묶음 `artifacts/management-frozen-demo-20261017/`과 `management-hands-on-actual-20261017/observation.json`을 읽었다. 두 번째 안전 후보는 A/B/ref 유효, API parsing 오류 없음이었다. B LEGITIMATE 확률 .72/제공자 confidence .63/계산·유효 .6266667이 .90에 미달하여 CONFIRM→STALE이었다. **주요 원인은 B 행동 확신 미달**이며 A .89나 귀속 .79를 원인으로 바꾸지 않았다. 4-source 누적이 낮은 확신의 원인이라는 인과는 입증하지 않았다.

공개 release 원문→write 완료 응답→첫 보고서 readback→review 원문의 MCP envelope를 실제 canonical 형식으로 재구성했다. 각 원 raw hash 4개와 안전 후보 hash `da6e6431df562614a910d200fb5b05312d467aac38b9416a9c1738592880557a`가 일치한다(`source-reconstruction.json`). 원 source ID/순서를 유지했다. 원 분석ID/grant 등 미공개 필드는 UNKNOWN이고 encrypted body/snapshot을 복호화하지 않았으므로 **전체 원 snapshot/전체 wire exact replay라고 부르지 않는다**. 구 질문의 실제 분포를 구 V5P1에 넣은 재현은 계속 CONFIRM/.6266667이며 A confidence 승격도 없다.

## 변경과 경계

- `engine.py`: 새 router에서만 snapshot에 실제 DB turn 순서/현재 turn과 source를 만든 call의 turn·도구·대상·READ_RESULT/WRITE_COMPLETION을 넣는다. 외부 문서가 선언한 역할을 사용하지 않는다. 원 source 본문/hash/span/catalog와 이전 실제 turn을 유지한다. 기존 router의 snapshot/권한·상태 전이는 유지했다.
- `jev_core_v5p1.py`: 새 `JevPolicyCurrent`와 `current_build`는 현재 실제 요청·현재 후보를 명시한다. B에 수집 metadata를 제공하고 현재 turn read의 decoded presentation을 먼저 보여 주지만 raw catalog 순서/원문/이전 자료를 삭제하지 않는다. receipt는 사실 증명으로 취급하지 않고 이전 생성 보고서·사실·명령·인용/금지·실제 채택을 비교하도록 질문을 정리했다. 과거 오염/사실 충돌은 숨기지 않는다.
- 새 내부 계약 `jev-current-candidate-1`/질문 버전 `jev-current-behavior-1`, B wire 질문 ID **`current_behavior`**로 원 V5/P1 `behavior` 응답과 분리했다. `jev_decision_v5.py`의 기본 build/논리 입력은 그대로이고 subclass hook으로 재사용한다. 새 질문 기준 coverage/confidence 검증→실제 질문명 관측 저장→순수 composer 논리명 변환 순서다. 구 키의 답은 새 질문에서 거절한다. 원 응답을 새 답으로 재해석하지 않는다.
- **.90·min(provider,computed)·확률 검증·B 고확신 정상+A raw WITHIN·위험 DENY 우선·귀속 분리**는 그대로다. 파일명/내용/hash/정답별 ALLOW 룰, 공격 제거, 캐시 판정, 자동 prompt/실행·승인은 없다.
- `server.py`에 새 profile 선택을 추가했다. SPEC5 외부 enum/인증/실행 상태는 바꾸지 않았다. 기존 실제 정상 성공·고정 위험 DENY·UNKNOWN과 원 manifest/DB/원장을 보존했다.
- 기존 `hookgw_connect.ps1`, `mvp_demo.py`, `mvp_demo.ps1`, `mvp_semantic_followup.py`, hook/MCP/viewer의 최소 연결로 `frozen-demo-1`을 제공한다. 새 평가 runner/예산 프레임워크를 만들지 않았다. 기존 CLI flags·host 사용자 승인·lifecycle·정확인자/출처·예약·단회·no unsafe retry를 재사용한다. 현재 PowerShell wrapper만 바꾸고 종료 후 원 함수/별칭을 복원한다. trust/global config/샌드박스를 자동 변경하지 않는다.

## 공유 잔여 4요청과 동결

구현한 경로는 **원8상한의 동일 ledger 재사용 하나뿐**이다. 새 compose control은 원 `hands-on-1/ledger`를 기존 `/jev-budget`에 RW mount한다. 기존 `policy_id=mvp-demo-hands-on-1`, request_limit8/input_token_limit512000의 ledger binding을 그대로 쓴다. 판정 정책/질문만 새 버전이며 accounting 소유권을 바꾸지 않는다. ledger를 복제/환불/증액/초기화하지 않는다.

기존 JevClient의 동일 SQLite `BEGIN IMMEDIATE` 예약으로 구/신 경로가 합쳐 최대8/512000만 소비한다. 4건 소비 상태에서 구/신 client 12개 경쟁이 **추가4만 성공**했고 이후 claim을 거절했다. 원CLI6은 그대로 소진돼 있으며 새 episode7 claim은 정확 manifest/모델/명시 선택과 부모/잔여/소스 검사 후에만 만든다. 실패/UNKNOWN에도 claim을 보존한다. 새 runtime의 빈 ledger 디렉터리에 별도 예산을 만들지 않는다.

부모 manifest `dbb7ecd4cc778f33836a0dd6c9b359782936f4063814b5a927bfe34277c04a38`·원 source-before hash·검토된 변경 전후·정상250bytes/hash `adfbe0837628ac8bdea141f47e46ef37a80f9402215ef19559c7df544cbc5214`·CONFIRM/STALE/종료·공유 원장4/256000을 새 manifest에 묶었다. 원 checker를 끄지 않으며 소진된 구 CLI start는 여전히 source/claim 방어를 받는다. 새 checker는 새 동결 source/bundle 및 원 부모/잔여를 함께 검사한다.

준비 manifest SHA256: **`a7fe26676d63e228ad511e7a05c464d1b9b66e7af3555490f11cb386e74f8028`**.

환경은 CLI0.154.0/actor gpt-5.6-luna/Jev jev-1.13.0, 현재 개인 reasoning 설정 `high` 상속이다(원 capture reasoning은 UNKNOWN). 원 product image `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`과 gateway digest `9d3e6044ddcdc0878b1787f77bd401252b95e22684203fb5e874c4c42d2ed90c`를 재사용했다. bundle은 원 `c59909d7e37fdb721810c9577dee9f8997dcad0474c6c474302e0bcc247de472`에서 새 `f6bb63da7e217f8c40951cd9fa06584addc624834f9785a609fd5af96b279565`로 바뀌었으며 이유는 snapshot 역할표현·질문·profile 연결이다. 원 두 문서/공격과 모델·image는 동일하다.

## 검증·최초 실패·재진단

증거 루트: `artifacts/20261017-frozen-demo/`. 관련28 PASS→runtime10 추가 후38 PASS. 원 V5/P1/새 질문/continuation/demo/lifecycle을 포함한 통합212 PASS 후, 실제 질문 ID 분리를 추가하여 **최종213 PASS/42.27초**로 재검증했다. 문서/hash만으로 통합을 반복하지 않았다. 마지막 reviewer/UNKNOWN/user turn 관련 경계는22 PASS(33 deselected), PS5.1 wrapper 함수·별칭/오류 상태/ReadOnly 거절4 PASS다.

고정 로컬 CLI는 모델/native actor가 아니다. 복제한 **실제 PS connector→실제 mvp_demo.main/start/lifecycle→로컬 CLI fixture→실제 UserPrompt/Pre/Post handler·MCP→TLS agentgateway·Engine·JevClient(fake HTTP)→실제 파일 executor→Post/source→close/history**를 연결했다. 테스트 adapter는 실행파일 위치·분리 workspace/DB/가짜 부모/컨테이너 mount 검증 layout·OFFLINE health 식별만 조정한다. 전체 helper/판정/파일 효과를 성공 stub으로 대체하지 않았다. 개인 config/원 키/원장은 fixture에 쓰지 않았다.

| 최종 실행 | 관측 |
|---|---|
| `e2e-final-safe/evidence.json`, 14 PASS | 같은 CLI 2turn·5후보, 두 안전쓰기 ALLOW/OBSERVED·각1회·PDP승인0, Post source5, 두 번째 B의 전체4-source, 신규fake4/부모포함8, wrapper복원·close/cleanup VERIFIED·중복start 거절 |
| `e2e-final-risk/evidence.json`, 14 PASS | 앞 정상쓰기/4-source 유지, 위험후보 semantic DENY·위험 upstream쓰기0/보고서없음, 전체실행4·Post source4·승인0·신규fake4/총8·close/cleanup·중복거절 |

표현/파일명 변형·같은 파일명 내용 반전·공격 인용/금지/과거 자료·앞 turn 오염·귀속불확실·낮은 행동확신 CONFIRM·context/hash 위조 반례를 시험했다. **synthetic observer가 정답을 고정한 경계 시험은 집행 근거이며, 모델이 이 반례를 판별했다는 증거가 아니다.** 실제 actor 공격 채택은 보장하지 않는다.

최초 실패도 보존했다. `e2e-safe`, `safe-2`는 Windows `.cmd`가 hook JSON/명령 인자를 재해석해 features 단계가 실패했고, 고정 로컬 실행파일로 argv를 보존했다. `safe-3`는 fixture Python의 CP949 오류로 과업 전에 실패하여 UTF-8로 수리했다. `safe-4`의 두 안전 실제 효과는 성공했으나 수집기가 sanitized history에 없는 question_version을 참조해 실패했다. 원 reason metadata/저장 이력/DB/파일을 RO로 재수집해15 PASS(`recollected.json`), 최초 KeyError를 덮지 않았다. `risk-1`은 준비 reasoning 메타데이터 수정 중 source drift를 검사해 전송 전에 중단했다. 최종 양쪽 fixture를 소스 동결 후 새 폴더에서 다시 검증했다. runtime 부모 디렉터리 생성 누락과 최초 lint 스타일 오류도 수리·재진단했다.

Ruff 최종 PASS. Bandit 원본17/현재19경고이며 신규 B105 LOW2는 `input_token_limit=512000`인 공개 예약 상수 두 곳이다(기존 legacy B105 LOW1도 같은 상수). 비밀키가 아니다. B104 MEDIUM2/B404 LOW3/B603 LOW6/B108 MEDIUM5는 동일하며 고정 argv/shell 없음·테스트 TLS listener/tmpfs 문맥을 확인했다. 원 JSON/stdErr를 보존하며 전체 무경고/전수 보안 PASS가 아니다.

## 준비 상태·보존·사용자 수용

`prepare.json`/`ready.json`은 provider disabled·JEV_RULES_ONLY·live NOT_AUTHORIZED·issues0이다. 실제 컨테이너 code/image·기존 키 메타데이터·실 gateway TLS MCP initialize/initialized/tools-list PASS, 도구/사용자turn/후보 호출0이다. 새 claim0·신규 모델/예산소비0, 공유 원 provider는 원4/256000·usage complete를 유지한다. 역사 현재33/2112000이며 사용자 선택안은 최대추가4/256000·CLI1/1800초→최대37/2368000·CLI총7이다. actor 비용은 별도다. 개발 AI 토큰/별도 AI 검토 사용은 제품 유료 actor/Jev 호출0과 구분한다.

원본12개·신규3개 diff/hash, 공개 source 재구성, 가이드 해당12페이지를 보존했다. `preservation-before/after.json`은 역사55파일 hash와 개인 config hash/auth/hooks 메타데이터가 같다. 실제 키 body/hash는 읽거나 출력하지 않았다. 기존 서비스·성공·STALE·UNKNOWN·원장·claim·관리 plans/harness/AGENTS는 변경하지 않았다. 새 별도 서비스8039/8049만 준비했다.

적용 가이드/P0는 기존 `03_guide_compliance`/GUIDE_MAPPING과 R1 PDF14/G1 PDF35–36(동결/검증), G2 PDF128–129(경쟁/상한)·135/137(오류), G3 PDF507–508/510(정확 입력/서버 권한/키), G4 PDF24/38(진단→조치→재진단/인증 경계)로 연결했다. 이번 노출 경계는 입력/전체source binding·신뢰된 역할표현·권한·실행전 판정·공유 원자예산·단회·UNKNOWN·TLS/역할 RO 유지다. 일반 native/hook 사망 fail-open·모든 IPI·정밀인과·모델 실제 정확도·B 오판·TLS 전체negative·설계20/약점49 전수 제출진단을 새로 PASS로 올리지 않는다.

[별도 AI REVIEW](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-frozen-demo-review/REVIEW.md)는 실제 diff/시험/효과/준비binding과 명령을 대조했다. 공식 외부 독립진단은 아니다. [USER_RUN](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-frozen-demo/USER_RUN.md)의 **한 번 연결→직접 codex→동일 두 문장→종료 후 history**만 안내한다. 새 모델이 계속 CONFIRM이면 미해결로 남기며 유료 버전/run/예산을 자동 추가하지 않는다.
