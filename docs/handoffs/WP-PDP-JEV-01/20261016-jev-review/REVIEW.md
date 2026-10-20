# WP-PDP-JEV-01 별도 AI 검토

작성자와 분리된 AI 검토. 실제 사람 개발자는 사용자1명이다. 공식 독립 진단·실제 모델 성능 검증을 의미하지 않는다.

상태: **배정된 오프라인 구현·검증 범위 수용 가능 / 검토 발견4건 해결·재진단 확인 / 해당 범위의 미해결 차단 finding0**. 실제 Jev 채택·보호 성능·전체 자유개발 완료 수용은 아니다. 관리의 전역 DONE/MVP 판단은 수행하지 않는다.

## 범위와 판단 기준

갱신 START_PROMPT 전체, ADR-P02,15번 계획, 최신 AGENTS/with-human-dev 역할·검증 reference, 관리의 T-HG-04/호스트 승인 장애 검토를 읽었다. 제품 소스는 읽기 전용으로 검토했고 이 REVIEW 및 `artifacts/20261016-jev-review/` 외 수정0이다.

정책→서버 출처 대조→미확정 의미만 별도 Jev state A/B→코드 최종합성 경로를 확인했다. source origin, 로컬 target identity, 실제 권한을 구분하고, 정확/정규화/모델 연관 관측을 인과 증명으로 취급하지 않는다. 비적용·관측 출처 없음·출처 미확정·필수 분석 실패와 실행 UNKNOWN을 구분한다. 원문/인자 inline 마커 삽입·제거는 없다.

## 독립 검증

모든 시험은 실제 actor/OpenAI judge/Jev API0이다. Docker 시험은 network none·소스 read-only·일반 UID·capabilities drop 환경이며 production DB/키/장부 볼륨을 마운트하지 않았다. 가짜키와 `/tmp` 새 장부만 사용했다.

| 검증 | 실제 결과 | 증거 |
|---|---|---|
| 변경 전 hookgw/SPEC4 선택 회귀 |149 PASS/39.94s|`baseline-regression.json`|
| 독립 wire 부정·정상 시험 |19 PASS/1.73s|`wire-final.json`|
| 실제 JevClient+fake HTTP policy 통합 |7 PASS/1.35s|`policy-integration.json`|
| 승인 poll 수정 관련 독립2+제품23 |25 PASS/3.15s|`hook-closure.json`|
| 최종 hookgw/SPEC4+독립28 선택 회귀 |299 PASS/39.94s|`final-regression.json`|
| host source↔bundle 및 실제 Control 제품 |35파일 불일치0·/product import|`deployed-product.json`|

위 시험 묶음은 서로 겹치므로 합산하지 않는다. 검토 입력73파일 fingerprint=`6fa72f26e9dbfa12f90c4108161518a4d724b7cdafdc2ad2c6bf26190600adaa`, `final-test-inputs.json`에 고정했다. 제품 manifest SHA=`816211073c88452ac28dcde64263ea097d540f6599d42d1447f3b66c1ed9d745`다.

독립 시험은 모델alias/extra/missing keys·부정확 분포/argmax/confidence·NaN/bool·usage범위 거부, 기본 미승인 전송0, redirect/인증/rate-limit 요청1·재시도0·예약환불0, 동일 analysis/view 재사용 및 정책 원장 재바인딩 거부를 확인했다. TypeSafe 원장에 원문·가짜키가 기록되지 않았다.

정상 외부자료 쓰기는 fake typed 답을 실제 adapter에 통과시켜 ALLOW를 확인했다. A에는 외부 state가 없고, 외부 원문이 고정 instructions/criteria로 들어가지 않는다. payload 사실 근거가 target에 무차별 복사되지 않으며 복수 정확/정규화 링크·LOCAL/EXTERNAL origin과 target identity를 구분했다. MCP·Bash·지원 apply_patch의 실제 설정 위험은 모델0 DENY, 같은 문자열의 report 인용은 정상 허용했다. stale source hash는 전송0이다. API/필수근거 실패는 의미 공격 식별 PASS로 처리하지 않는다.

## 발견·수정·재진단

`artifacts/20261016-jev-review/findings.jsonl`에 초기 관찰과 해결 이벤트를 별도로 보존했다.

| ID | 발견 | 최종 확인 |
|---|---|---|
|JEV-R01|서버 대문자 option과 소문자 전용 validator 불일치|option/question ID 검증 분리. 실제 HTTP adapter 통합 PASS|
|JEV-R02|task-level ref를 모든 slot MODEL_ASSOCIATION에 복사|slot별 link 질문 및 정확 매핑. 무관 target 링크0 PASS|
|JEV-R03|전체 apply_patch를 JSON으로 해석해 설정 위험 누락 가능|완전 Add File 내용 재구성, 부분/불가 설정 fail-closed.3경로 동등 위험 DENY PASS|
|JEV-R04|CONFIRM pending poll에 재발급 hash를 요구해 승인 대기 중단|초기 CONTROL_EVENT만 hash 필수. 원hash 유지한 pending→ALLOW PASS|

R04는 독립 시험2 FAIL 원본 `hook-first.json`과 수정 후 `hook-closure.json`을 보존했다. wire 첫 시험6 FAIL은 검토자 assertion이 외부 SafeError 문자열을 검사한 오류였다. 의도된 내부 diagnostic 검사로 정정했고 `wire-first-attempt.json`에 명시했다. 가이드 추출의 dev 이미지 pypdf 부재 실패도 보존하고 기존 bundled Python으로 재추출했으며 새 설치0이다.

## 가이드·공식 API 대조

기존 bundled Python으로 원 PDF6문서 SHA를 검증하고 관련18페이지를 새로 추출·전체 읽었다. `guide-pages/manifest.json`과 `guide-extraction-final.json`을 확인한다. R1 PDF13~14/G1 PDF35,47은 기존 의존성 재사용·공급망 미완료 보존, G2 PDF133,135,137,143/G3 PDF164,511은 안전한 stage/code·엄격 schema·장애 차단, G3 PDF153,171,510/G4 PDF24,38은 암호화/키분리/TLS/세션·원자 집행·재진단, C1 PDF14,15,26은 설계→코딩→동적 효과·최초/조치/재진단 이력에 연결했다. 이는 설계20/약점49 전체 PASS나 공식 점수·조치율이 아니다.

[공식 API](https://docs.typesafe.ai/api), [confidence](https://docs.typesafe.ai/confidence), [state](https://docs.typesafe.ai/concepts/state), [Jev1.13 한계](https://docs.typesafe.ai/model-jaggedness/jev-1.13)를 독립 확인했다. Choice의 confidence는 답 분포 통계이며 실제 정답 확률/인과가 아니다. 각 request의 질문은 같은 state를 보므로 A/B는 별도 request/state다. SDK 기본 재시도 대신 기존 httpx 직접 고정 endpoint/TLS·proxy/redirect0·retry0·기한·전송/응답 한도를 사용한다. 공식 adversarial state 및 CJK 한계를 해결했다고 판단하지 않는다.

## 실제 실행 증거의 범위

작성자의 `artifacts/20261016-jev-dev/actual-gateway.json`은 실제 pinned agentgateway→extAuthz→upstream의 scripted typed observation25/25, 정상 쓰기 효과 및 금지 효과0을 연결한다. fake 제어 흐름이며 Jev 의미 정확도 수치가 아니다. `actual-jev-preflight.txt`는 격리8032/8042 profile, MCP initialize/initialized/tools-list 및 임시 연결 정리, semantic_write_ready=false·JEV_NOT_AUTHORIZED를 보여준다. 모델 access는 미검증이다.

추가 `actual-rules.json`10/10은 실제 격리 gateway의 공개 파일 읽기 ALLOW→upstream 결과 일치→OBSERVED, 미설정 의미 쓰기 JEV_NOT_AUTHORIZED/DENY→같은턴 중단→금지 쓰기 효과0을 연결한다. 이것도 actor/Jev 모델 호출0이며 사용자 실제 CLI 과업 완료를 대신하지 않는다.

Jev rules-only는 새 project/DB/profile이고 기존 GPT 실행은 compatibility 경로다. 공개 nonempty sentinel은 기존 빈 OpenAI key mountpoint의 literal masking 결함만 격리하고 기존 role/key 파일은 변경하지 않는다. TypeSafe 자격증명은 별도 `/jev-key/jev.api-key`다. mask를 끄거나 기존 OpenAI budget을 새 provider 허가로 바꾸지 않는다. 공통 mask 결함을 해결한 것으로 확대하지 않는다.

`runtime-baseline.json`과 `runtime-final.json`/`preservation-final.json`을 대조했다. 기존5개 호출 reason/history hash는 같고 사용자2개 ALLOW/READY와 최초3개 DENIED가 보존됐다. OpenAI22/24·남은2 및 budget SHA=`c4d2b5a24f9f69a28be81dc12a4ddd9d3371727d48596fea52c9eb4a6bf37283`, role10개·개인 config/auth·기존 key/출력 hash가 같다. 기존 READY를 지우거나 정책 전환으로 DENIED 처리하지 않았다.

작성자 최종 관련 회귀282 PASS/66.25s와 Ruff PASS, Bandit8경고(High0/Medium3/Low5·오류0·억제0)를 읽었다. B608은 기존 GPT 지시문의 “Select…from” 문자열로 SQL sink가 없는 오탐이다. B1042건은 컨테이너의 TLS/mTLS listener이며 Compose 호스트 노출은 loopback이다. B404/B6035건은 trusted CLI/고정 argv와 shell=false 실행 경로다. 이를 약점49 전수 무결함 판정으로 해석하지 않는다. 기존 httpx0.28.1/BSD-3-Clause 재사용·LICENSE hash 증거가 있고 새 SDK/package/image 추가0이다.

`docs/mvp/09_rules_first_jev.md`, 비활성 LIVE override 예제, 수동 기대값 기반 calibration12/holdout4 fixture를 검토했다. 사용자 최소 명령이 `-JevRules`의 새 profile과8032/8042로 향하며 read-only 첫 요청만 안내한다. actor 비용/기존 auto-review403 가능성을 명시하고, 실제 Jev 자료·키·요청/토큰/비용 상한·policy_id를 정하기 전 유료 평가를 시작하지 않는다. 공식 models 페이지의 고정1.13.0·$0.042/M input·output free·CJK 한계도 재확인했다.

## 남은 한계

실제 Jev API 접근·한국어/공격 문맥 정확도·임계치 calibration·TypeSafe 키/비용/자료/유료 예산은 미승인/NOT_RUN이다. 관련512자 span의 lexical retrieval·고정 질문/placeholder threshold는 실제 평가가 필요하며 출처 링크가 인과를 입증하지 않는다. native 일반개발·hook 사망 fail-open·호스트 Codex 자동 검토403·별도 개인 MCP 경고·공급망/전체20·49 보강은 그대로 남는다. 이번 오프라인 adapter를 전체 자유개발/MVP 완료로 판단하지 않는다.

## 최종 인계 대조와 수용 범위

`../20261016-jev-dev/RESULT.md`, `GUIDE_APPLICABILITY.md`의 설계20/약점49 모든 행, `artifacts/20261016-jev-dev/final-index.json`을 전체 읽고 실제 증거와 대조했다. 적용성 표는 기존 source/sink와 비적용 후보를 보존하면서 새 provider 경계를 검토하는 부록이며 전수 진단 PASS가 아니다. C/D 전체나 모델 학습을 새 선행조건으로 요구하지 않는다.

최종 공개 소스191파일 fingerprint=`2b7f8a4e7aa6dd47d1c9a30c0331ca6f79fffe8b310690b7b7434e67e8e65892`를 독립 재계산해 현재 파일 불일치0을 확인했다. 독립 시험 입력73파일도 변경0이다. 작성자 최종 core 이후 차이는 SPEC5·새 Jev 계약·비활성 LIVE 예제의 문서3개뿐이다. `artifacts/20261016-jev-review/final-handoff-verification.json`에 남겼다. 마지막07:51 preflight도 ready=true/NOT_AUTHORIZED/모델0이며 이전 예산·원 이력 보존 결과와 모순이 없다.

따라서 규칙 우선 routing, strict Jev adapter와 ADR-P02 slot/source/context의 **오프라인 구현·회귀·배치 연결** 인계는 수용 가능하다. 보고서가 scripted PASS·모델 없는 실제 읽기·실제 사용자/의미 모델 NOT_RUN을 분리하고 정확 인용·보안 검증·예산·원증거를 보존하는 점을 확인했다. 다음 실제 Jev 평가나 전체 MVP 완료는 별도 사용자 자료/비용/정책 지정과 관리 판단이 필요하다.
