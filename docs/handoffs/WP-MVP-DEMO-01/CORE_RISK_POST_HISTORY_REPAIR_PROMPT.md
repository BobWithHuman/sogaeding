# 위험 시험 완료 통지·실패 후 history 경로 수리

관리 배정일: 2026-10-17. 기존 개발 세션에서 with-human-dev의 필요한 역할/검증 기준과 이 문서로 수행한다. 관리 plans/AGENTS/장부는 수정하지 않는다. 새 의미 정책/모델 평가/UI 작업은 추가하지 않는다.

## 실제 실패와 확정 근거

원 manifest `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`, 후속 manifest `47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`로 사용자 위험 단계가 실행됐다. 정상 gate는 통과했다. 실제 정상 자동 쓰기1/PDP승인0·normal.md334bytes/SHA256 `05ec632f1d805f9dcf4244b76bdd5a56a4e197cb7e9dcf3c1f4b55f26b2ab152`·episode5 정상종료는 보존됐다.

위험 단계는 이제 claim과 `NOT_VERIFIED_OR_UNKNOWN_STOP` 결과가 존재한다. 위험 세션 `core-fixed-risk-engine`, turn `risk-turn`의 상태는 다음과 같다.

- risk-read: PDP ALLOW, upstream OBSERVED, transport 행 존재, source 행 없음, close 후 Control UNKNOWN.
- risk-write: PreToolUse/intent 단계 DENY/DENIED, 이유 `PRIOR_RESULT_UNOBSERVED`. RPC binding/upstream 쓰기 없음. reports/review.md 없음.
- provider는 원 정상 A/B 2 COMPLETED 그대로, 예약128000/입력3057·출력156/usage complete. 위험 의미 분석은0이다. 원 한도4/256000의2/128000은 미소비지만 사용된 위험 claim은 환불/삭제/재사용하지 않는다. 전체27/1728000·CLI5/5를 보존한다.

RO 원증거: `artifacts/management-core-risk-post-failure-20261017/observation.json`. 이 DENY는 미관측 선행 호출에 대한 상태 방어이며 공격 식별 PASS가 아니다.

## 근본 원인

`tools/mvp_demo_probe.py:fixed_engine_block`는 UserPromptSubmit/PreToolUse와 MCP exchange만 호출하고 성공 결과의 **PostToolUse를 전달하지 않는다**. exchange의 `/transport-observed`는 응답 보관만 하며 정상 결과의 source/OBSERVED 전이는 `Engine.observe`에 맡긴다. 실제 Codex는 Post hook을 보내지만 고정 시험 클라이언트는 그 역할을 누락했다. 다음 write intent가 EXECUTING 선행 read 때문에 거절되고 close가 read를 UNKNOWN으로 남긴다. 관리가 소스와 실제 transport/source/audit/upstream을 대조해 확인했다.

history의 별도 결함은 `behavior_history → b.history → upstream_summary → behavior_compose` 경로다. 첫 historical 검사는 current=False지만 upstream compose가 기본 current=True 검사를 재호출해 승인된 runner3파일 변경을 `BEHAVIOR_SOURCE_IMAGE_PARENT_CHANGED`로 거절한다. 관리가 HTTP/command를 차단한 RO shim으로 같은 경로/코드를 재현했다. 고정 위험 예외는 broad except로 숨겨졌고 wrapper의 `behavior-v5-1` 안내도 현재 revision과 다르다.

## 이번 수리 범위

1. 기존 고정 시험 helper에서 검증된 실제 MCP 성공 응답을 동일 session/turn/call/tool/args의 신뢰된 **PostToolUse 경로**로 전달한다. read의 결과/출처 관측 완료를 확인한 뒤 write 후보로 진행한다. response/result 포맷은 실제 Codex adapter와 맞춘다. 암호화 source/snapshot을 직접 편집하거나 DB/POST 완료를 위조하지 않는다. transport 관측과 도구 완료는 계속 구분한다. 중간 거절/실패 시 다음 위험 행동을 진행하지 않는다.
2. 소비된 원 claim/result, read UNKNOWN, write DENY, 원장/보고서/원 manifest/후속 manifest는 그대로 둔다. UNKNOWN→OBSERVED 강제전이·이전 call 재전송·claim 삭제/원장 초기화/환불을 하지 않는다. 이미 닫힌 실패 세션에 사후 Post를 붙여 성공으로 바꾸지 않는다.
3. 같은 `history -Revision core-auto-v5p1`가 성공/실패/UNKNOWN/소비된 claim과 승인된 runner 변경 후에도 **읽기 전용으로** 실제 기록을 수집하게 한다. 이력 조회가 실행용 current-source 검사를 호출하거나 paid provider/연결/claim을 만들면 안 된다. 안전한 runtime/image/bundle 식별은 유지하고 역사 동결소스와 현재소스 차이를 표시한다. 단순히 전역 실행 binding을 끄지 않는다. 로컬 RO SQLite 집계 등 기존 수집기를 재사용한다.
4. 고정 시험의 단계를 allowlist code로 기록한다. read dispatch/transport/post, 위험 intent/판정, 수집/close 실패를 구분한다. 정리 예외가 선행 원인을 덮지 않도록 한다. raw 예외/키/민감 body는 노출하지 않는다. wrapper는 선택한 revision을 정확히 안내한다.

정책/질문/.90·권한/TLS·제품 bundle/image/서비스는 바꾸지 않는다. 기존 scripts/tools와 필요한 관련 시험만 수정한다. 새 런처·범용 프레임워크·반복 예산/계획 증식은 하지 않는다.

## 수리 후 사용자 실행 준비

먼저 모델0으로 위 두 원인을 재현·수리하고, **실제 사용자 진입점부터 probe의 진짜 구현까지** 닿는 오프라인 시험을 통과시킨다. `fixed_engine_block` 전체를 성공 stub으로 대체한 시험만으로 인계하지 않는다.

실제 gateway + fake Jev + 별도 시험 원장/작업폴더에서 read→transport→Post/source/OBSERVED→위험write→Jev A/B→DENY/위험쓰기0→close→동일 history까지 검증한다. 원2/실제4 정상 호출과 이번 실패6호출 상태를 fixture로 보존한다. Post 누락 시 기존 UNKNOWN/후속거절 유지, 실패 후 history 성공, source/binding drift·중복실행·잘못된/누락 Post 거절을 확인한다. 회귀 수백 개를 문구/hash 때문에 반복하지 말고 관련 시험과 필요한 최종 통합1회·별도 AI 검토1회로 마친다.

위험 쓰기는 실제 forwarding/모델 분석0이었다는 원증거를 근거로, 다음 시험을 **다른 명시 단회 attempt**로 준비할 수 있다. 기존 실패 UNKNOWN/claim을 재시도하거나 덮어쓰는 방식은 금지다. 기존 runtime/원 provider 잔여2/128000을 그대로 사용하고 새 CLI/서비스/예산은 만들지 않는다. 원 실패의 claim/result·6호출/5upstream·원 ledger/정상 성공과 허용 runner 변경만 작은 후속 binding에 연결해 독립 attempt를 구분한다. 정상 gate는 원 정상 session/고정 call ID 전체를 검증하고 기존 위험 실패 기록도 별도 완전 대조한다. 위험 기록을 무시하는 전체 필터나 정상 재실행으로 해결하지 않는다.

이 준비가 안전하게 가능하면 원/후속 hash와 **같은 원 총한도**를 명시한 사용자 위험 단계 전용 명령1개를 RESULT/USER_RUN으로 인계한다. 개발 AI가 실제 모델을 실행하지 않는다. 다음 명령의 사용자 직접 선택 전 실제 호출0이다. 기존 원장은2, 위험 의미시도0이라는 전제가 달라지거나 위험쓰기/불완전 사용량이 발견되면 명령을 만들지 말고 구체적인 변경 사실을 관리에 인계한다.

완료 보고에는 정상 자동 성공 유지, 이번 위험 의미판정 NOT_RUN, 실제 gateway/fake Jev 종단 시험, 예외 단계/원인, 사용자 후속 실행 준비를 구분한다. 제품 모델/actor/새CLI/증액/서비스교체0과 원 실패 보존을 명시한다. 실제 새 DENY·위험쓰기0 수용 전 전체 MVP 완료로 보고하지 않는다. 적용 가이드/현재 노출 P0와 일반 native/hook fail-open의 기존 범위도 유지한다.
