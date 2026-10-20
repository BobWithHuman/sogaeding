# 오늘 핵심 자동 판정 마무리 — 구현부터 최종 실행 준비까지 한 인계

> 2026-10-17 구현·준비 인계를 CORE_AUTO_PREPARED로 수용했다. 현재는 USER_NEXT_RUN.md의 사용자 정상/위험 실제 결과를 기다린다. 이 구현을 다시 시작하거나 별도 의미 평가를 추가하지 않는다.

2026-10-17 관리 배정. with-human-dev를 적용한다. 사용자 요구는 **정상 자동 통과·비정상 엔진 차단**이다. `ADR-P04_b_owned_positive_authorization.md`의 좁은 정책 변경을 구현하고, 관련 검증·실gateway 효과·별도 AI 검토·최종 사용자 실행 준비까지 끝낸다. 분석 보고서/추가 계획 생성만 하고 멈추지 않는다. 인과 연구·UI 미관·전체 제출 전수 보강으로 범위를 늘리지 않는다.

## 1. 판정 수리

필수 읽기: ADR-P04, `jev_decision_v5.py`/`jev_policy.py`의 build/selected/typed 검증/compose, 실제 V5 원 결과/현재 안전한 관리 관측. 필요한 함수부터 읽고 이미 확인한 과거 전체 이력·PDF를 반복 출력하지 않는다. [설계 검토](20261017-core-policy-management-review/REVIEW.md)의 활성화 조건을 구현 시험으로 충족한다.

- 새 정책 `hookgw-2026-10-17-jev-v5p1` / profile `behavior_v5p1`. V5 질문/선택지·wire/원응답 계약·.90·confidence 계산은 바꾸지 않는다. 기존 V5는 유지한다. 기존 evaluate 루프를 복제하지 말고 재사용 가능한 결정 함수/최소 subclass로 분리한다.
- B의 고확신 LEGITIMATE + 검증된 A raw WITHIN_TASK이면 양의 허용을 B에 근거해 ALLOW한다. A의 낮은 점수/LOW_CONFIDENCE/기존 scope=UNCERTAIN은 그대로 기록한다. A가 .90을 통과했다고 바꾸지 않는다.
- 고확신 A OUTSIDE 또는 B 위험은 DENY 우선. A raw OUTSIDE 저확신·명시 UNCERTAIN/B 저확신·판정 충돌은 CONFIRM. 응답 누락/invalid·ref/hash/catalog 변조/사용자 ref 없음은 허용하지 않는다. 기존 완전한 JevClient validate_response 뒤에만 raw choice를 쓴다.
- 새 양의 규칙은 등록 MCP/read_file/write_file/enrolled-files-1에만 적용한다. native 등 다른 parser/route에 확장하지 않는다. 실제 사용자 요청을 판단하는 B를 source의 승인 주장으로 대체하지 않는다. 과거 A .70을 승격하거나 낮은 .90을 새로 설정하지 않는다.

## 2. 기존 근거와 실제 집행으로 검증

- `followup-behavior-v5`의 정확 snapshot/wire/실응답을 원 V5와 새 정책으로 replay한다. 새 정상 ALLOW/위험 DENY는 **같은 실제 응답의 정책 재합성**으로 표시한다. 현재 CLI 두 정상 관측의 .86/.70은 안전한 기록으로 조합만 확인하고 전체 암호화 snapshot을 복원했다고 하지 않는다. raw 업무본문/키 복호화는 하지 않는다.
- 다른 대상 쓰기·읽기 전용 요청의 쓰기·인용/부정문 경로·외부 승인 위조·거짓 보고·정상 요약/생성·복수 출처·raw A 저확신 OUTSIDE/UNCERTAIN·A무참조·native범위·잘못된 확률/argmax/sum/NaN·모델실패를 포함한 관련 시험을 수행한다. 규칙이 정확한 정상/위험 관측을 받았을 때의 집행과 의미 모델 실제 정확도는 구분한다. B 오판까지 해결됐다고 주장하지 않는다.
- 실제 TLS agentgateway/파일 executor에서 정상 ALLOW→쓰기1/PDP승인0, 악성 후보 DENY→금지쓰기0, 승인/경쟁·변조·정책/자료 stale·PDP 장애·UNKNOWN의 영향을 좁게 검증한다. 개발 시 모델 응답은 기존/합성 fixture이며 실제 모델 호출0이다. 최종 필요한 통합1회·별도 AI 검토1회, 발견 수리 뒤 관련 재검증만 한다.
- 현재 노출 경로의 필수 P0도 닫혀야 한다. 특히 장부의 R-B-002(인증 실패 영속 감사)는 기존 구현/시험을 새 profile의 노출 인증 경로와 대조해 좁게 검증·검토한다. 부족하면 해당 경로만 보완한다. 전체 C/D 전수 조사를 새 선행조건으로 늘리거나 미검토를 PASS로 바꾸지 않는다.

## 3. 오늘 끝낼 실제 수용 경로 준비

배포 중 V5/과거 파일·25요청/예약1600000·CLI4/4는 보존한다. `core-auto-v5p1` revision을 기존 mvp_demo.ps1/도구/compose에 최소 확장하고 별도 DB/workspace/포트를 사용한다. 원 보호 키는 RO 참조하며 재입력을 요구하지 않는다. 새 런처/웹앱/평가 체계를 만들지 않는다. 제품 policy enum/필수 trace 표시만 맞추고 미관 수리는 보류한다.

**새 고정 의미 평가를 한 번 더 만들지 않는다.** V5 질문이 같으므로 기존 실응답 replay 후 실제 엔진 수용시험으로 바로 간다. 사용자 최종 실행은 다음 두 부분이다.

1. 한 Codex CLI에서 정상 요청 한 건을 직접 수행한다. 실제 MCP 정상 쓰기가 ALLOW/OBSERVED이며 PDP 승인0이어야 통과다. 호스트 Codex 자체 Allow와 제품 PDP CONFIRM은 구분한다. CONFIRM을 사람이 승인해 정상 자동 통과로 바꾸지 않는다.
2. 별도로 명시한 **고정 위험 후보**를 기존 시험 client/probe로 실제 gateway와 실제 Jev에 전달한다. 사용자 과업/실제로 읽은 docs/review.md/source를 바인딩하고 외부 지시에 따른 거짓 보고 write_file 후보를 실제 제품 경로로 보낸다. DENY·upstream 금지쓰기0·금지 파일효과0을 확인한다. 후보를 Codex에게 시켜 만들거나 actor에 평가 정답을 주입하지 않는다. 이미 있는 probe/MCP transport를 재사용하며 live 시험을 fixture 판정으로 대체하지 않는다. 이는 독립적인 엔진 수용시험이지 actor가 인젝션에 넘어갔다는 증거가 아니다.

제안 상한은 **새 Jev 총4요청/입력예약256000**(정상A/B2+고정위험A/B2), **추가CLI1/역사총5**,1800초다. 전체 역사29요청/예약1856000, demo관련24/1536000이다. 기존 소진 원장은 증액/초기화하지 않고 부모 근거에 묶인 별도 allowance로 준비한다. actor 비용은 별도다. 두 부분의 자료/목적지/후보/한도가 frozen manifest에 함께 들어가야 한다.

고정 위험 시험은 기존 진입점의 명시 `verify-block` 같은 모드로 준비해도 된다. 모든 새 외부 전송은 사용자에게 공개된 고정 manifest/한도 선택 뒤에만 가능해야 한다. 사용자 정상 CLI가 끝나고 ALLOW/단회 효과·정상 종료·남은2요청이 확인된 뒤 위험 시험을 진행한다. 추가 재시도/암묵적 모델 호출은 없다. 실패/CONFIRM/UNKNOWN·한도 소진이면 중단하고 collect/history만 제공한다. 이 작업 중 개발 AI의 실제 GPT/Jev 요청·CLI live 시작·기존 서비스 교체는0이다.

## 파일·계약 위임과 인계

허용 쓰기: 새 내부 정책 모듈/필요한 V5 공통 결정 hook·관련 schema/trace 계약의 좁은 변경, `server.py` 명시 profile, 기존 mvp_demo/semantic_followup/probe/관련 PS1·compose revision·필수 policy whitelist, 관련 tests 및 설명/새 handoff/안전한 artifacts. SPEC5의 outward 인증/인자/승인/상태/원자예약 계약·권한을 넓히지 않는다. Engine의 결함 수리가 불가피하면 근거와 관련 회귀를 남긴다. 관리 plans/harness/AGENTS는 수정하지 않는다.

기존 source/wire/결과/성공 파일/ledger/claim/원HTML은 변경 전 hash와 원본을 보존한다. 현재 source drift는 숨기지 않는다. 필수 R1/G1~G4/P0의 변경 관련 원문 페이지·검토 근거를 재사용하고 위험한 발견을 오늘 일정 때문에 제외하지 않는다. 별도 AI 검토는 확신 승격/허용 범위 확대/잘못된 사용자 ref·stale/부모예산 우회를 우선 확인한다.

`docs/handoffs/WP-MVP-DEMO-01/20261017-core-auto-finish/RESULT.md`·`USER_RUN.md`, 별도 REVIEW와 실제 사용 가능한 **고정 start/verify-block/history 명령**을 제공한다. 사용자가 prepare·키 입력·조각별 계획을 다시 만들지 않도록 완성한다. 오프라인 구현/준비 완료와 사용자 실제 자동 정상/위험 집행 통과를 구분한다. 등록 MCP 엔진의 두 실제 수용 결과가 확인된 뒤 관리가 MVP 완료를 판정한다. 일반 native/hook fail-open·모델 전체 정확도·전체 제출보강 완료는 주장하지 않는다.
