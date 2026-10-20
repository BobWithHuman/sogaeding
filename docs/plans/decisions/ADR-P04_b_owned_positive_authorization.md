# ADR-P04: 등록 파일 MCP의 정상 자동 허용 책임 조정

2026-10-17 관리 결정. 사용자 목표는 오늘 정상 자동 ALLOW·비정상 엔진 DENY를 구현·검증하는 것이다. 사람승인은 예외이며 정상 경로의 대체물이 아니다. 정확한 인과 증명·표시 미관은 선행조건에서 제외한다.

## 근거와 실제 변경

V5 실제 정상 쓰기2건에서 A는 WITHIN_TASK를 골랐지만 effective .86/.70, B는 LEGITIMATE .97/.986666...였다. 둘 다 높은 확신을 필수로 요구하는 합성 때문에 CONFIRM이었다. B의 기존 질문/선택지는 이미 실제 사용자 요청과 action/target/options/payload의 전체 적합성·충실성·추가 행동을 함께 판단한다. 따라서 등록 파일 MCP에서는 B에 양의 의미 허용 책임을 맡기고 A는 독립 위반/충돌 확인에 사용한다.

이것은 A의 독립 양의 확신 필터를 완화하는 **실제 정책 변경**이다. A가 .90을 통과했다고 하거나 점수를 승격한 수치 수리로 표현하지 않는다. B가 잘못 고확신 LEGITIMATE를 내고 A도 약하게 WITHIN_TASK를 고르면 기존보다 허용될 수 있다. 등록 공개 파일 MCP로 제한하고 반례·실제 효과 검증과 별도 검토를 통과한 뒤 명시 profile에서만 활성화한다. 전체 모델 정확도나 모든 IPI 보호를 주장하지 않는다.

TypeSafe의 confidence는 분포 집중도이며 도메인별 검증이 필요하다([공식 설명](https://docs.typesafe.ai/confidence)). `.86`에 맞춰 임계치·정규화·반올림을 바꾸지 않는다. 기존 .90 계산/검사, V5 질문·선택지·A/B 격리·wire 계약은 유지한다.

## 새 최종 조합

새 정책 `hookgw-2026-10-17-jev-v5p1`, profile `behavior_v5p1`로 구분한다. 기존 V5의 정책/과거 결과와 동작은 유지한다. 등록 `mcp`/`enrolled-files-1`의 read_file/write_file에만 적용하고 native/미지원 도구에 확대하지 않는다.

1. 기존 인증/권한·신뢰된 사용자 refs·source completeness/hash/catalog/ref·정확 snapshot/turn/tool/args/policy binding·민감/보호 경로·hard rule·예산·원자 예약은 계속 필수다. 모델 오류/누락·검증 실패는 fail-closed다.
2. 유효한 A의 고확신 OUTSIDE_TASK 또는 B의 고확신 EXTERNAL_ADOPTION/OUTSIDE_TASK는 DENY한다. B의 위험은 A/귀속 미확정 때문에 CONFIRM으로 낮추지 않는다.
3. **B가 기존 .90 검사를 통과한 LEGITIMATE이고, A가 완전히 검증된 응답에서 raw WITHIN_TASK를 선택한 경우 ALLOW**한다. A의 effective .90 미달만을 추가 거부 조건으로 삼지 않는다. A에 검증된 사용자 ref가 없거나 입력 검증을 통과하지 못했으면 이 규칙을 적용할 수 없다.
4. A의 raw OUTSIDE_TASK 저확신/명시 UNCERTAIN, B의 미확정/저확신, 다른 실제 판정 충돌은 CONFIRM이다. collapsed scope=UNCERTAIN이라는 이유만으로 허용하지 않는다.
5. A confidence/status와 원 V5 trace는 그대로 보존하고 새 decision_rule_version/양의 결정 근거 B를 분리 기록한다. 정확 귀속은 권한도 인과 증명도 아니다. DENY 승인 해제·UNKNOWN 자동 재실행/환불은 금지한다.

## 활성화 전 필수 검증

[별도 설계 검토](../../handoffs/WP-MVP-DEMO-01/20261017-core-policy-management-review/REVIEW.md)는 좁은 범위의 조건부 수용이다. 구현/실제 실행 수용을 대신하지 않는다. 같은 wire의 기존 실제 V5 응답을 새 규칙으로 replay하되 과거 CONFIRM을 덮어쓰지 않는다. 정상2건/고정위험 후보의 새 결과와 원 V5 결과를 구분한다. 합성 질문 응답은 모델 정확도 근거로 쓰지 않는다.

양/음성·충돌/미확정 전체 조합, raw 응답 검증·사용자 ref 누락·변조, path/권한/외부 승인 주장/인용·부정문/읽기만 요청/다른 대상/다중출처 반례, 기존 실행 전 검증·단회 예약·장애/UNKNOWN과 실제 gateway 효과를 확인한다. 마지막 후보 별도 AI 검토 후 사용자 최종 실행을 준비한다.

최소 실제 완료 근거는 **실제 Codex 정상 쓰기 ALLOW→OBSERVED·PDP 사람승인0**과 **명시된 고정 악성 호출 시험 클라이언트→실제 gateway→실제 Jev DENY·upstream 쓰기0/금지효과0**다. 고정 호출은 피해 actor에 주입하지 않고 독립 엔진 수용시험으로 표시한다. actor 자체의 인젝션 저항/공격미시도와 혼동하지 않는다. 이로써 제한된 등록 MCP 엔진 MVP를 검증하며 일반 native·hook fail-open·전체 제출 보강은 범위 밖 잔여다. 현재 적용 P0는 제외하지 않는다.
