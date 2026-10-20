# WP-PDP-JEV-01: 규칙 우선 PDP와 Jev adapter의 오프라인 구현

with-human-dev 스킬로 docs/plans/15_jev_pdp_transition.md와 최신 관리 검토를 읽고 다음 좁은 구현을 수행해줘. 현재 관리 세션은 계획/판정만 하며 제품 구현은 이 개발 세션에서 한다. 사람 개발자는 사용자1명이다.

**2026-10-16 추가 확정:** 사용자 위임에 따른 관리 결정 ADR-P02를 함께 읽어라. 기존 지시를 유지하면서 아래 인자별 출처·문맥 분석을 포함하고 inline 마커 기능은 구현하지 않는다. 이미 구현 중이면 현재 변경을 먼저 확인해 이 범위로 통합하고 중복 작업/원증거 덮어쓰기를 하지 않는다.

사용자는 생성형 GPT A/B 대신 TypeSafe의 Jev 같은 구조화된 판정 모델을 원한다. 평소 Codex/hooks/실제 agentgateway 자동 연결 목표는 그대로다. Codex actor GPT를 바꾸거나 Jev를 actor용 MCP로 노출하는 작업이 아니다. 현재 실제 제품은 아직 SPEC5/GPT이고 기존174파일/실제 소스·키·DB·OpenAI judge22/24·사용자 read2건 ALLOW/READY와 최초 실패를 보존한다. 현재 Codex 자체 auto-review403은 별도 장애이며 Jev 전환으로 해결됐다고 하지 않는다.

1. 정책→출처 대조→미확정 의미만 모델의 단계/판정표를 구체화해라. 정상 등록 공개자료 읽기는 필수 범위/민감자원 통제 후 모델0회로 허용하고 명백한 금지는 모델0회로 DENY한다. 외부자료 문자열 일치만으로 공격을 확정하거나 모든 쓰기를 일괄 CONFIRM하는 구현은 금지한다.
2. TypeSafe 공식 API/모델/한계/SDK 근거와 적용 PDF 원문을 확인해라. https://api.typesafe.ai/v1/systemone에 연결할 최소 Jev adapter를 offline fake HTTP/가짜키로 구현한다. 실제 요청은0회다. 기존 httpx 재사용을 우선 검토하며 새 의존성이 필요하면 출처/버전/해시/라이선스·공급망 근거를 남긴다.
3. Choice/Noul 등 좁은 질문, 응답 키/모델/유한 확률·분포/범위 검증, 서버 소유의 최종 조합·근거/인자/hash/정책 결합을 설계해라. A/B 격리를 유지하면 별도 state/별도 요청으로 하며 한 state에 질문2개를 넣고 A가 외부자료를 보지 않는다고 하지 않는다. source catalog/정확 참조는 코드로 유지하고 외부 원문을 instructions/criteria의 권한 위치로 승격하지 않는다.
4. Jev 모드에서 OpenAI judge로 자동 fallback하지 않는다. 고정 endpoint/TLS·역할별 키·proxy/redirect 비상속·timeout/total deadline·retry0·debug 본문 비기록·전송 제한/마스킹·호출 전 사용량 예약·같은턴 분석 장애 중단을 유지한다. 새 TypeSafe 사용량 정책/한도는 설정되기 전 LIVE 비활성으로 둔다. OpenAI 원장22/24를 초기화/환불/증액하거나 새 장부로 재허용하지 않는다.
5. Jev1.13은 adversarial state에 영향받을 수 있고 한국어/CJK 검증이 필요하다는 공식 한계를 반영해라. 임계치는 placeholder/미검증 상태를 명시하고 평가 전 정확도/보호 성능을 보장하지 않는다. 한국어 정상·외부자료 활용·지시 따름 공격·모호함을 구분하는 별도 평가 세트와 질문/버전/임계치 고정 계획을 준비한다. 모델 답을 시험 정답으로 삼지 않는다.
6. 모델0회 fast path, fake Jev 응답 조합, unknown/위조/민감/stale 근거, API/문맥/수치 오류, 권한 우회/승인/경쟁/UNKNOWN, 기존 SPEC4/실제gateway 영향 회귀를 수행해라. actual model 정확도는 NOT_RUN으로 둔다. generic hook 오류는 고정 stage/code로만 분리하고 원 인자/개인 transcript를 저장하지 않는다.

이번에 포함할 인자별 출처 분석:

- action/target/options/payload를 실제 도구 스키마와 검증된 parser로 확정한다. 비적용과 해석 불가를 구분하고 Jev가 실행 대상/인자를 새로 만들지 못하게 한다.
- 민감 슬롯별 복수 source/span 링크를 서버 catalog에 결합한다. 원문 정확/정규화 대조, 모델의 연관 추정, 미확정을 별도로 남기며 인과 증명으로 표시하지 않는다. 외부 문장에서 관측한 .npmrc와 실제 로컬 파일의 identity/origin은 분리한다. LOCAL은 자동 신뢰가 아니다.
- 코드 단계로 미확정인 민감 후보의 관련 span만 권유·실행 지시/사실·데이터/금지·인용/미확정으로 Jev 관측한다. 모든 문서·값의 사전 분류를 추가하지 않는다. 배칭·캐시는 같은 snapshot/문맥 안에서만 검토하고 A/B의 state 격리를 유지한다.
- 비적용/관측된 출처 없음/출처 미확정/필수 분석 실패를 구분한다. 출처 미확정은 실행 상태 UNKNOWN과 분리한다. 모든 정상 생성값에 source를 강제하거나 출처를 못 찾았다는 이유로 허용하지 않는다.
- 외부+권유+위험은 하나의 신호이며 기존 정책·권한·장애 통제를 대체하지 않는다. 정상 외부 권고/위험 문자열의 정상 인용·금지/데이터형 공격/파생값/복수·누락 출처/로컬 origin 혼동/위조·stale 링크를 회귀에 넣는다. 합성 PASS와 실제 Jev 정확도는 분리한다.
- **inline 마커를 본문·URL·경로·코드·설정에 삽입하거나 실행 직전 제거하는 기능은 MVP 범위에서 제외**한다. 이를 필수 후속 실험으로 추가하거나 권한 증거로 사용하지 않는다. 서버 원문과 실제 실행 인자를 이 기능 때문에 변경하지 않는다.

쓰기 범위는 src/app/transparent/의 좁은 정책/adapter/설정·진단과 필요한 src/app/pdp/ 공유 인터페이스, 관련 tools/scripts·별도 Compose의 Jev key/설정 준비, tests/hookgw/ 및 관련 회귀, docs/mvp 계약/사용 설명 및 새 handoff/evidence다. 필요 내부 계약/판정 정책 버전 변경은 명시해 문서·코드·시험을 동기화한다. outward 권한/승인/실행 상태는 보존하며 SPEC4 회귀를 유지한다. 변경된 product bundle/실제 실행 소스를 연결한다. 계획/전역 장부/AGENTS/skill·원 PDF와 개인 전역 설정/auth/CA는 수정하지 않는다.

Codex 자체 reviewer 변경·auto-review 회피·승인/샌드박스/hook/TLS 우회·bob MCP 전역 삭제·CLI 업데이트는 배정하지 않는다. 해당 호스트 문제는 안전한 메타데이터와 필요한 별도 사용자 조치만 보고한다. native 일반 개발/hook 사망 fail-open/공급망 미완료와 필수 가이드는 유지한다. 전체 C/D나 모델 학습 프로젝트를 이번 선행조건으로 추가하지 않는다.

개발 AI의 실제 actor/judge/Jev API 호출0, 키/계정 생성0으로 별도 AI 검토 후 docs/handoffs/WP-PDP-JEV-01/<run_id>/RESULT.md와 REVIEW.md에 인계해줘. 정상 연결·모델 평가용 최소 사용자 절차와 TypeSafe 키/비용/자료/예산 요건을 준비하되 사용자가 실행하기 전 결과를 PASS로 표시하지 마라. 오프라인 adapter 완료와 실제 Jev 채택·보호 성능·전체 MVP 완료를 분리한다.
