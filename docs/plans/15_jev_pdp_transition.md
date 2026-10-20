# PDP의 경량 판정 모델: TypeSafe Jev 검토·전환 계획

**최신 상태:** followup-response-v2 실제4요청이 모두COMPLETED/입력4614/출력780으로 Jev 연결이 확인됐다. 정상 S01 CONFIRM과 공격 S02 B_EXTERNAL_EVIDENCE_REQUIRED 때문에 의미 판정은 수용하지 않는다. 다음은 [16번 통합 시연 계획](16_mvp_demo_delivery.md)의 WP-MVP-DEMO-01이다. generic task 근거와 외부 사용 근거 분리·관련 슬롯/문맥 정합성·typed 관측을 고치며 실제 Codex/gateway/파일 효과를 사용자가 보는 demo까지 한 작업으로 준비한다. 기존 기록 보존·개발 유료0·실제사용자live별도 원칙을 유지하고 전체 native/제출 보강은 완료로 주장하지 않는다. 아래는 이전 배정 기록이다.

2026-10-16 관리 계획. 사용자는 GPT A/B 의미 판정 대신 TypeSafe의 Jev 같은 판정 모델을 원한다고 밝혔다. **현재 실행 제품은 SPEC5/GPT DevelopmentJudge다. Jev는 조사한 전환 대상이며 아직 구현·접근·보호 성능을 검증하지 않았다.** 제품 구현은 다른 개발 세션에서 수행한다. 유료 재실행/개인 승인 정책 변경은 배정하지 않는다.

**선택적 채택 확정:** [ADR-P02](decisions/ADR-P02_selective_provenance_adoption.md)에 따라 슬롯별 출처·문맥 역할·복수 출처/미확정 처리를 이번 오프라인 구현에 포함한다. inline 마커 삽입·제거는 MVP에서 제외한다. 아래 단계와 기존 보안 통제는 유지한다.

## 확인한 사실과 범위

- [공식 소개](https://docs.typesafe.ai/introduction): Jev는 state와 typed questions를 받아 Choice/Score/Noul 형태의 구조화된 답·확률을 제공하는 System One 모델이다. 범용 판정 모델이며 보안 전용 탐지기로 검증된 것으로 취급하지 않는다. 코딩 actor Codex/GPT는 유지하고 PDP의 의미 관측 adapter를 대상으로 한다.
- [공식 API](https://docs.typesafe.ai/api): HTTPS api.typesafe.ai/v1/systemone와 별도의 TypeSafe 인증을 사용한다. 기존 OPENAI_API_KEY로 Jev를 호출하는 설계가 아니다. 키/계정 접근은 아직 미확인이다.
- [모델 문서](https://docs.typesafe.ai/models): 현재 고정 ID jev-1.13.0/jev-1.14.0과 이동하는 latest/preview alias가 구별된다. 영어 대비 CJK 성능 차이를 명시한다. 후보 버전을 고정해 한국어 평가한 뒤 선택하며 alias/더 비싼 모델로 자동 대체하지 않는다.
- [confidence](https://docs.typesafe.ai/confidence): Choice/Score의 confidence는 답 분포에서 유도한 값이고 실제 정답률/인과 증명이 아니다. Noul에는 별도 confidence가 없다. 임계치는 예제 수치를 복사하지 말고 정상/공격의 별도 검증 세트로 정한다.
- [Jev1.13 한계](https://docs.typesafe.ai/model-jaggedness/jev-1.13): state의 삽입 지시가 답을 바꿀 수 있다고 명시한다. 1.14에서 해결됐다고 확인한 증거는 없다. 긴 문맥·문자 수·정확 계산도 모델에 맡기지 않는다.
- [state](https://docs.typesafe.ai/concepts/state): 한 요청의 여러 질문은 같은 state를 본다. A=사용자/후보만, B=추가 외부자료의 관측 격리를 유지한다면 별도 state·별도 요청이어야 한다. 한 state의 질문2개를 독립 A/B라고 부르지 않는다.

## 목표 판정 경로

1. **코드 정책 검사:** 실제 도구·인자/경로·출처·인증·허용 범위·보호 자원·실행 상태/재전송을 검사한다. 안전한 등록 공개자료 읽기는 필수 검증 후 모델 호출0으로 허용한다. 읽기 전용이라는 이유로 민감/범위밖 읽기를 통과시키지 않는다. 명백한 금지는 모델을 부르지 않고 DENY한다.
2. **코드 출처 대조:** 신뢰된 adapter가 관측한 사용자 turn/읽기 결과의 source ID·hash와 후보의 민감 인자/대상을 연결한다. 외부 문자열의 일치만으로 악성 또는 인과를 확정하지 않는다. 정상 외부 자료 활용을 허용하고 외부 텍스트의 자칭 권한을 승격하지 않는다.
3. **미확정인 의미만 Jev 관측:** 좁은 질문의 Choice/Noul 확률을 서버에 돌려준다. 관측 비교를 인과 증명으로 표현하지 않는다. 모델은 새 권한·출처 등급·정책/승인·실행 상태를 발급하거나 DENY를 해제할 수 없다. 필요하면 서버 catalog의 ID만 선택시키며 정확 인용/시각/경계 계산은 코드로 검증한다.
4. **코드 최종합성·집행:** 필수 통제가 충족되고 검증된 의미 기준을 통과하면 ALLOW, 정책 위반은 DENY, 권한 범위 내 의미 불확실성만 기존 정확 단회 CONFIRM 예외로 처리한다. 인증/API/필수 문맥·근거 장애는 분석 불가로 차단한다. UNKNOWN 미재시도/미환불·원자 예약/정확 인자 결합은 유지한다.

Jev를 actor가 마음대로 부르는 추가 MCP 도구로 노출하지 않는다. Control 내부 adapter만 호출한다. 생성형 GPT judge로의 묵시 fallback은 금지한다. 저비용 규칙에서 끝난 호출은 Jev/기존 GPT 모두0회를 시험한다. 모든 쓰기를 일괄 차단/승인 대기로 바꿔 자유 개발 목표를 대체하지 않는다.

## 이번에 추가하는 출처·문맥 분석

- action/target/options/payload는 실제 도구 스키마·검증된 parser로 분해한다. 비적용 슬롯은 구분하고 모델에게 새 대상/인자를 생성시키지 않는다.
- 민감 슬롯별로 서버가 관측한 source/span의 복수 링크를 남긴다. 정확/정규화 대조, 모델 연관 추정, 미확정을 구별한다. 외부 문장 속 경로의 origin과 그 경로가 가리키는 로컬 파일 identity는 별개다. LOCAL origin을 사용자 권한으로 취급하지 않는다.
- 미확정 민감 후보의 관련 span만 Jev로 지연 평가해 권유·지시/사실·데이터/금지·인용/미확정을 구별한다. 문서의 모든 값에 선행 모델 호출을 추가하지 않는다. 같은 관측 문맥의 배칭·캐시는 검토할 수 있고 A/B의 다른 state는 합치지 않는다.
- 비적용·관측 출처 없음·출처 미확정·분석 실패를 분리한다. 출처 미확정과 실행 UNKNOWN은 다른 개념이다. 출처 없는 모든 새 생성값을 차단하거나 안전으로 처리하지 않는다.
- 외부+권유+위험은 보조 신호다. 정책 위반·필수 분석 실패를 그 세 조건의 누락 때문에 허용하지 않는다. 원문/도구 인자에 inline 마커를 삽입·제거하거나 에이전트 자가 라벨을 신뢰하는 기능은 구현하지 않는다.

## 다음 개발 세션의 좁은 순서

1. 기존174파일/실제 소스 및 현재22/24·사용자 read2건 ALLOW/READY·원 실패 이력을 고정한다. 현재 source span/중단/게이트웨이/키/감사 기반을 재사용한다.
2. 단계별 routing/필수 판단표와 Jev 내부 입력·응답/버전 계약을 작성하고 narrow adapter를 offline fake HTTP/고정 observation으로 구현한다. 현재 outward SPEC5 권한/상태는 유지하고 변경되는 판정 정책/내부 계약 버전은 명시한다. 기존 SPEC4/GPT는 역사 회귀로 보존한다. Jev 모드에서 GPT가 몰래 호출되지 않게 한다.
3. SDK 기본 retry·본문 debug를 그대로 상속하지 않는다. 현재 httpx 직접 사용 또는 고정 SDK의 최소 경로를 검토해 TLS/고정 endpoint·프록시/리다이렉트 비상속·명시 timeout/total deadline·retry0·역할별 키·전송 제한/마스킹·유한 수치/분포/응답 키/model 검사·새 provider 사용량 기록을 구현한다. 새 장부로 기존 OpenAI 한도를 초기화했다고 처리하지 않는다. Jev의 유료 예산은 별도 사용자 지정 전 NOT_AUTHORIZED다.
4. 외부자료 원문을 질문의 instructions/criteria 권한 위치로 옮기지 않는다. 서버 고정 질문·선택지와 데이터 state를 분리한다. 전체 프로젝트/개인자료를 보내지 않고 합성 fixture로만 설계한다. 실제 전송은 나중에 대상·자료·예산을 설명하고 사용자 직접 실행으로 남긴다.
5. 오프라인 통합은 정상 공개자료 읽기0모델, 보호 자원0모델 DENY, 정상 외부 데이터 쓰기, 공격 지시 채택, 애매함, 위조 refs/모델 출력·NaN/응답 누락·API 실패·같은턴 재시도·경쟁/UNKNOWN을 검증한다. 이는 제어 흐름 시험이며 Jev 정확도 시험이 아니다. 실제 모델 평가용 한국어 정상/공격 쌍과 보류 평가 세트·측정 기준은 별도로 고정한다.
6. 별도 AI 검토 후 새 RESULT/REVIEW와 최종 소스/bundle/runtime 대조, 실패/NOT_RUN, TypeSafe 키/계정·제한된 사용자 LIVE 실행 요건을 관리에 인계한다. 첫 실제 모델 시험 전 비용/자료/판정 기준을 정하며 오프라인 PASS를 모델 채택 완료로 선언하지 않는다.

추가 회귀는 정상 문서 권고, 위험 설정값의 정상 인용/금지 설명, 데이터형 공격, 파생값·복수 출처·누락, 로컬 identity와 origin 혼동, 위조/stale 링크를 포함한다. 실제 Jev의 문맥 분류 정확도는 사용자 모델 평가 전 NOT_RUN으로 둔다.

## 별도로 남는 연결 문제

현재 Codex 자체 auto-review가 codex-auto-review 모델 접근 불가403으로 read를 거절했다. Jev 교체는 이 경로를 바꾸지 않는다. 개인 bob-agentgateway4400도 별도 MCP다. hook 포괄 오류는 안전한 stage/code 진단으로만 보완한다. 자동 검토/샌드박스/hook/TLS 우회·전역 설정 삭제·CLI 업데이트는 이번 작업 권한이 아니다. 승인 경로 변경은 구체적인 적용 범위/위험과 사용자 지시 및 관리 요구사항을 확인한 다음 별도 수행한다.

R1/G1~G4 및 적용 P0, native 일반 개발/hook 사망 fail-open, 공급망 미완료는 유지한다. 이번 계획은 전체 C/D를 새 선행조건으로 추가하지 않는다.
