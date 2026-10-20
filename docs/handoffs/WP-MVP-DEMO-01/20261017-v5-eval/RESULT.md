# V5 고정4요청 평가 준비 결과

2026-10-17. 기존 평가 도구에 `followup-behavior-v5`를 연결하고 실제 prepare/inspect/preflight 및 무모델 검증·별도 AI 검토를 완료했다. **실제 actor/Jev 호출0·CLI0·서비스 교체0**, 기존 예산/실패/UNKNOWN/원장/승인 성공 보존이다. 개발 AI 토큰은 구현·별도 AI 검토에 사용했으며 제품 유료 호출0과 별개다. 정확한 개발 AI 계량값은 제공되지 않았다.

## 사용자가 실행할 준비

- [USER_RUN.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v5-eval/USER_RUN.md)에 복사 가능한 evaluate 한 명령과 이어 collect 한 명령을 인계했다. 사용자의 추가 prepare/plan/key 입력은 필요 없다.
- manifest SHA256: `84a51d1653b7e8523c2ccadf16f3c069f62ff8212ee617cd21f1012d7221c401`
- [preflight.json](C:/sogaeding/artifacts/20261017-v5-eval/preflight.json): ready_for_user_opt_in=true, default_enabled=false, live_authorized=false, exact_wire_build_verified=true, paid_requests0, actual_key_read=false, provider_ledger_present=false. provider/model 접근은 **NOT_VERIFIED_NO_REQUEST**다.
- [inspect.json](C:/sogaeding/artifacts/20261017-v5-eval/inspect.json): 목적지/실제 자료/질문/정확 wire/source60개/image/후보4개/부모 원장 결합. [wire-inventory.json](C:/sogaeding/artifacts/20261017-v5-eval/wire-inventory.json)의 wire 크기는 순서대로2450/5666/1956/5965byte다.
- [collect-readonly-check.json](C:/sogaeding/artifacts/20261017-v5-eval/collect-readonly-check.json): 준비 파일3개 hash변경0, NOT_STARTED/NOT_RUN/미시도2개. 새 provider DB·claim·authorized config가 없다. prepare.json 및 preparation-commands.json에 실제 준비 결과/명령을 남겼다.

목적지 `https://api.typesafe.ai/v1/systemone`, 모델 `jev-1.13.0`, 정상A→정상B→공격A→공격B 최대4요청/입력예약256000이다. 제안 추가4/256000, 전체 역사17+4=21/1344000, demo관련8+4+4=16/1024000을 사용자 evaluate의 모든 승인 차원에 명시한다. 준비는 지출권한이 아니며 현재 disabled다. 기존 demo8/8 증액·기존CLI3/3 재개는 없다. 현재 provider 요율은 새로 확인하지 않았고 금액을 보장하지 않는다. 예약량과 실제 사용·청구는 다르며 과거 UNKNOWN을 환불/0으로 바꾸지 않는다.

## 구현과 보존 경계

배정된 `tools/jev_eval.py`, `scripts/jev_eval.ps1`, 신규 `tests/hookgw/test_jev_v5_eval.py`, `docs/mvp/09_rules_first_jev.md`의 평가 설명만 바꿨다. source-manifest.json/change.diff 및 original/에 현재 hash·원본·diff가 있다. 제품용 runner/PS1/CLI/UI/DB 체계를 새로 만들지 않았다. artifacts의 PS1은 무모델 시험/기록용이다. 관리 plans/harness/AGENTS, Engine/server/승인/예약/UNKNOWN/compose/배포 중 V3는 수정하지 않았다.

기존 followup 준비·inspect·preflight·단회 atomic claim·고정 manifest 선택·provider ledger/usage·실패 중단·collect를 재사용한다. V4와 V5는 고정 프로필의 build/compose/한도/부모 결합만 다르다. V5 실행은 표준 **JevClient 자체**를 사용하며 V4 전용 FixedPublicDigestClient 예외를 확장하지 않는다. TLS/응답계약2/민감값 guard/.90 경계를 유지한다. 생산 policy의 A/B 병렬 evaluate를 호출하지 않고 평가에서만 순차 await한다. 첫 transport/응답/ref/분석/불완전 usage 오류 뒤 나머지 view/case는 중단한다. 유효한 낮은 행동 confidence는 CONFIRM으로 채점하며 추가 교정 요청을 하지 않는다.

입력은 원 V4 실제 plan SHA `0d36e068c29ca7b0ccfa08af981ac3c38e3bca85a193884d89548cc9060ad735`의 두 snapshot 그대로다. 새 정상/공격 자료를 만들지 않았다. snapshot별 hash와 실제 V5 build/wire/catalog를 요청 전에 검사하고, 조합 시 입력/ref도 원 후보 검증기를 재사용한다. 과거 V4 확률·typed 답은 V5 질문의 답으로 사용하지 않는다. `expected_local_only`와 평가 case ID는 모델 wire에 추가하지 않는다. 정밀 귀속의 불확실성은 확정 외부추가행동 DENY를 약화하지 않는다. 입력 무결성은 DENY에서도 필수다.

변경 전 V4 동결54개 모두 일치했다. 원본을 저장한 뒤 배정된 helper/wrapper2개만 바꿨으며 나머지52개·원 실제 requests/result·V5 후보4개는 그대로다(preservation-before/after.json). 기존4원장은 읽기 전용 부모 근거로 hash/manifest/usage/닫힌 상태를 결합했고 **17요청/1088000예약·hash변경0**이다. 기존3개 collect는 역사 결과를 읽고 현재 source 불일치를 false로 정직하게 표시한다. 원 manifest를 덮어쓰지 않았다. 성공 V3 normal.md SHA `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0`도 유지했다(success-report-preservation.json). 실제 키 본문은 준비/검증/검토에서 읽거나 hash/복사하지 않았다.

## 검증과 별도 검토

| 확인 | 관측 |
|---|---|
| 최종 관련 통합 | **275 PASS/5 환경 FAIL**, 288.27초. V5 38개·구형 평가/응답·후보 시험. integrated.txt/command.json |
| 누락 mount 수리 후 실패5개 | **5 PASS/30 deselected**, 1.39초. 원 result파일 RO mount만 추가, 제품/manifest 변경0. replay-repair.txt/command.json. 합계 범위280개 해결이며 단일280PASS 실행은 아니다 |
| V5 경계 | 정확 snapshot/네 wire/표준 client 자체·높은행동확신 ALLOW/DENY·불명확귀속 독립DENY·낮은행동확신 CONFIRM·변조/ref/첫오류 중단·usage보존·각 승인 차원·부모/source/image 변경·재실행/경쟁·UNKNOWN |
| 별도 AI 검토 | [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v5-eval-review/REVIEW.md), 독립 **3 PASS/8.76초**, 차단 발견 없음. 엄격 type/초과 한도24변형·manifest float 거부, 소비상태4종 재전송 거부, plan 무키/평가 RO키 마운트. 실제 모델0 |
| 실제 Windows PowerShell5.1 | native-v5.json **4 PASS**, fake helper의 evaluate 인자/잘못된 한도 거부/collect/prepare. 실제 prepare/inspect/preflight/collect도 해당 PS5.1 wrapper 사용 |
| Ruff | static-final-testfix.txt exit0 |
| Bandit | 원진단 **exit1/28 Low·1 Medium** 보존. static-summary.json/bandit.txt. 전체 보안 PASS로 바꾸지 않음 |

Bandit B4041/B60313은 기존 trusted executable·고정 argv·shell 미사용 subprocess 경계이며 새 준비/시험은 network none이다. B1081은 host 공유 임시파일 sink가 아닌 Docker tmpfs `/tmp` literal이다. B10514는 input_token_limit/input_token_reservation_limit의 공개 한도/disabled None 관련 항목이며 실제 password를 추가하지 않았다. 원진단·데이터 흐름을 별도 검토와 연결한다. 최초 Docker pipe 거부, lint2개, 가짜 confidence/guard fixture2개, 통합 결과 mount누락5개와 수리는 [INITIAL_DIAGNOSTICS.md](C:/sogaeding/artifacts/20261017-v5-eval/INITIAL_DIAGNOSTICS.md)에 남겼다. 통과한 제품 전체/브라우저/gateway 시험은 반복하지 않았다.

## 적용 가이드와 남은 범위

docs/plans/03_guide_compliance.md의20설계/49약점 정본은 수정하지 않았다. guide-mapping.json은 기존 원문/해시 artifacts/20261017-auto-decision/guide-pages.json과 이번 코드·시험을 연결한다. R1 PDF14/G1 PDF35~36→원본/source/image 추적, G3 PDF507 SR1-4/508 SR1-9→고정 입력/명령/한도/typed guard, G2 PDF128/135/137·G3 PDF510→단회 claim/키RO/안전오류/UNKNOWN, G4 PDF24→최초 진단/조치/재진단/별도 검토를 재확인했다. 신규 dependency나 개인 모델/설정 변경이 없다. 전체20/49·TLS negative·키수명·공급망 완료를 주장하지 않는다.

실제 V5 behavior 답/정상 ALLOW·공격 DENY는 **NOT_RUN**이다. 준비 ready/가짜 transport 통과/exit0는 실제 모델 성공이 아니다. 사용자가 실행하더라도 고정 두 예제의 연결·판정 관측이며 실제 파일 효과/actor 보호/전체 정확도/전체 IPI/일반 native·hook 장애/MVP 완료 증명이 아니다. 불일치/CONFIRM은 보존하고 질문별 실제 관측/모델 적합성을 검토한다. 자동 재시도·임계치 임의 하향·같은 예제 맞춤 새 질문/새 유료 run 연속 생성은 하지 않는다. 다음 실제 실행은 관리 확인 및 사용자의 고정 명령 직접 선택으로 남긴다.
