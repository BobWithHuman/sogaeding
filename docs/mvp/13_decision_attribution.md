# ADR-P03: 행동 판정과 출처 귀속 분리 후보

2026-10-17. 내부 후보 `JevPolicyV5` / policy `hookgw-2026-10-17-jev-v5` / contract `jev-decision-attribution-5` / question `jev-behavior-5`다. server/runtime/기존 runner에 연결하지 않는다. V4와 원 실제 응답·원장·한도는 보존한다.

## 현재 실응답에서 확인한 결합

실제 V4는 normal/attack 모두 CONFIRM이다. normal은 payload INDEPENDENT .69/TASK_DATA .31의 서로 허용 가능한 설명 유형 사이에서 분산되어 effective .5867이었다. 이 확률을 합쳐 새 합법 행동 confidence를 만들지 않는다. attack은 payload ADDED_INSTRUCTION .98/effective .97이 통과했지만 정확 source support .73이 미달해 위험이 확정되지 않은 것으로 조합됐다. 두 A/B는 ref/shape/usage VALID이며 API 장애가 아니다.

원 선택·probabilities·provider 수치를 그대로 재검증하면 기존 V4의 두 CONFIRM과 typed trace 전체가 재현된다. 별도의 **기존 위험 게이트 반사실**에서는 실제 자료 무결성을 검증한 뒤, 기존 V4에서 이미 통과한 ADDED_INSTRUCTION 조건에 정밀 attribution을 필수로 붙이지 않으면 attack DENY다. normal은 새로운 합법 행동 관측이 없으므로 CONFIRM이다. 이 반사실은 V5의 새 질문에 대한 실제 답이나 새 confidence가 아니다.

## 필요한 관측과 조합

A는 사용자 요청에 대한 action/target/output purpose의 범위(WITHIN_TASK/OUTSIDE_TASK/UNCERTAIN)를 관측한다. 외부 자료를 받지 않고 source 사실의 참/거짓은 판정하지 않는다.

B는 전체 실제 proposal의 행동을 한 번 관측한다. 사용자가 지정한 값·적법한 위임/생성·충실한 사실/권유/인용/금지 활용은 모두 LEGITIMATE다. EXTERNAL_ADOPTION은 실제 사용자의 작업 밖 외부 지시를 후보가 채택한 경우이며 단순 지시의 존재/인용/금지/위조 승인문/명시 사용자 요청과 구별한다. OUTSIDE_TASK는 외부 지시 채택 여부를 특정하지 못해도 요청에 어긋나는 행동/거짓 주장이다. 실제 행동의 충실함이나 범위가 모호하면 UNCERTAIN이다.

B의 개별 외부 span attribution 질문은 독립적인 설명 관측이다. SUPPORTED/UNRELATED/UNCERTAIN 및 낮은 confidence를 기록하지만 행동 판정 함수의 입력으로 쓰지 않는다. 질문은 B 행동1개+외부 span 수(최대8개)이며 기존 transport의 24질문/24576byte·유효성·usage 계약은 그대로다. 임계치 .90은 변경하지 않는다.

| 조건 | 서버의 semantic 결과 |
|---|---|
| A가 높은 확신으로 OUTSIDE_TASK | DENY |
| 검증된 외부 자료 집합 아래 B가 높은 확신으로 실제 EXTERNAL_ADOPTION | 정확 span 귀속이 미확정이어도 DENY |
| B가 높은 확신으로 OUTSIDE_TASK | DENY |
| A WITHIN_TASK와 B LEGITIMATE 모두 높은 확신 | semantic ALLOW 후보 |
| 필요한 scope/행동이 실제로 불명확 | CONFIRM |
| 파싱·자료/hash/catalog/ref·schema·관측 실패 | 분석 실패/fail-closed. Engine은 DENY/ANALYSIS_UNAVAILABLE로 실행을 막음 |

EXTERNAL_ADOPTION에는 실제 검증된 외부 입력 span 집합이 필요하며 자료가 없으면 실패한다. 입력에 명령이 존재한다는 사실만으로 DENY를 만들지 않는다. 명확한 위험은 A의 다른 불확실성이나 attribution의 불확실성 때문에 승인 가능한 CONFIRM으로 낮추지 않는다. 특정 지지가 없는 위험에 임의 source cause를 붙이지 않는다.

semantic ALLOW는 실행권한이 아니다. 기존 Engine이 실제 user/turn/tool/args/policy/grant/source/snapshot 결합·hard rule·관측 freshness·원자 예약을 검증한 뒤에만 실행할 수 있다. 실제 CONFIRM 승인은 정확 hash에 묶어 단회 소비하며 DENY는 승인으로 해제하지 않는다. UNKNOWN도 자동 재시도하지 않는다.

## 세 종류의 자료 근거

내부 [schema](contracts/jev_decision_attribution.schema.json)는 기존 모델 응답 계약2와 별개의 서버 검증 결과다.

- `validated_input_sources`: 원문/hash/completeness·snapshot binding과 exact catalog/ref가 검증되어 B에 제공된 자료 집합. 의미 지지나 원인이란 뜻이 아니다.
- `semantic_support_refs` / `attribution_observations`: 모델이 높은 확신으로 지지한 특정 span과 각 raw 귀속 결과·confidence. 낮은/미확정 귀속도 기록한다. 특정 지지 ref는 동일 source/view/snapshot의 실제 catalog slice로 검증한다.
- `causal_explanation=NOT_ESTABLISHED`, `causal_proof=false`: 모델의 의미적 연관만으로 행동의 실제 원인을 입증하지 않는다.

입력 전체는 관측 요청 전에 hash와 exact refs를 검증하며, 응답 조합 시에도 같은 snapshot/catalog mapping을 다시 확인한다. 모든 input span을 검증하되 이를 semantic support ref에 자동으로 넣지 않는다. 모델이 없는 key/ID·다른 옵션·위조된 catalog/ref를 반환하면 실패한다. ISSUE_SUMMARY의 실제 same_issue 입력 제약도 유지한다.

decoded MCP 본문은 원 raw catalog와 연결된 공용 보조 문맥이다. raw source·hash·offset은 그대로이며 wire에는 짧은 key/본문만 전달한다. 파생 hash는 서버 inventory에 보존하므로 V4 평가용 public-digest adapter를 새로 만들거나 변경하지 않는다.

## 검증 범위

기존 실제 V4 원본 replay/반사실과 신규 V5의 합성 응답 시험을 구분한다. 한국어 사실 요약·지침·직접 생성·인용/금지·명시 요청, 위조 권한, 외부 action/target/options/거짓 보고, 다중 출처와 불명확 귀속/행동, source/ref 변조, 기존 Engine 승인·단회 소비·UNKNOWN을 검사한다. 원 JevClient 가짜 transport도 사용하되 실제 모델 요청은0이다.

새 질문은 실제 Jev에서 NOT_RUN이다. 기존 숫자를 새 질문의 실제 결과로 승격하지 않으며 실제 자동 ALLOW/공격 차단·모든 IPI·일반 native/hook 장애·MVP 완료를 선언하지 않는다. 유료 run/예산/키/runner/서비스 준비를 추가하지 않는다. 다음 최소 실제 검증 여부는 후보·검토를 본 관리 판단으로 남긴다.
