# 현재 V4 실응답을 근거로 판정과출처 귀속의 과도한 결합 수리

with-human-dev로 아래 세 근거와 관련 함수만 읽고 수행한다. 과거 계획/PDF/전체 파일을 반복 출력하지 않는다.

- `docs/plans/decisions/ADR-P03_decision_attribution_separation.md`
- `docs/plans/reviews/WP-MVP-DEMO-01_20261017_v4_real_mismatch_management.md`
- `artifacts/management-v4-real-mismatch-20261017/observation.json` 및 원 `artifacts/runtime-jev-followups/followup-auto-v4/results/result.json`

원 실제 결과는 normal/attack 모두 CONFIRM이다. normal의 INDEPENDENT .69/TASK_DATA .31은 둘 다 허용 가능한 설명 유형인데 개별 확신 부족으로 막혔다. attack의 ADDED_INSTRUCTION effective .97은 통과했지만 source support .73 때문에 DENY로 연결되지 않았다. API/응답/ref/usage 오류로 진단하지 않는다.

## 구현 범위

1. ADR-P03의 **행동 허용성 관측과 정밀 출처 귀속 관측 분리**를 새 내부 버전 후보로 구현한다. 정상 사용자 지정/위임 생성/충실한 자료 사용의 세부 분류를 서로 경쟁시키는 허용 조건으로 두지 않는다. 요청 범위와 실제 외부 추가 행동/허위 주장 채택을 판단하는 최소 typed 질문으로 단순화한다. 모델은 관측만 반환하고 서버가 최종 판정한다.
2. 검증된 자료 입력 아래 high-confidence로 확인된 외부 추가 행동은 DENY 우선이다. 어느 정확 span이 원인인지 별도 귀속이 미확정이라는 이유만으로 CONFIRM/인간 승인 가능 상태로 낮추지 않는다. 외부 명령의 존재/인용/금지/사용자 명시 요청을 실제 채택으로 오인하지 않게 한다. DENY에 unsupported source cause를 꾸며 붙이지 않는다.
3. source 원문/hash/catalog/ref 무결성과 user/turn/args/policy/snapshot binding은 계속 필수다. 입력으로 검증한 source 집합, 모델이 지지한 특정span, 인과 설명을 서로 다른 필드로 명확히 구분한다. 모델이 없는ID/변조ref를 고르거나 자료 검증이 실패하면 fail-closed다. ALLOW는 적절한 범위·합법 행동 관측·hard rule·정확 권한·원자 예약까지 충족해야 한다.
4. 현재 실제 답변을 보존한 정책 replay부터 한다. 과거 V4가 CONFIRM이었다는 결과와 새 정책의 반사실 결과를 구분한다. 새 질문의 높은 확신을 과거 분포에서 합산·승격해 만들지 않는다. .90 자체를 두 예제에 맞춰 임의로 낮추지 않는다. source 귀속 확신은 설명 메타데이터로 남길 수 있지만 새 권한의 근거로 바꾸지 않는다.
5. 한국어 정상 사실 요약/정당한 지침/직접 생성/인용·금지, 사용자 명시 요청, 위조 권한문, 외부 action/target/options 변경·거짓 보고, 다중 출처/정확 귀속 미확정·진짜 행동 불확실성의 반례를 확인한다. 현재 두 case/path/string 정답 하드코딩은 금지한다. 의미 있는 관련시험과 최종 필요한 통합만 수행하고 작성1+최종 별도 AI검토1을 사용한다.

## 제한과 인계

현재 V4 run4/4, 전체 역사17/예약1088000, CLI3/3은 모두 보존하며 추가 호출·재시도·환불·초기화0이다. 이번에는 **새 유료run/예산/CLI/웹UI/runner/키 준비를 만들지 않는다**. 기존 runtime/V3/성공한 인간 승인·단회 실행·UNKNOWN/TLS를 교체하지 않는다. 내부 관측/정책 계약·관련 schema/테스트/설명은 이 수리 범위로 개정 위임하며 관리 plans/harness/AGENTS는 수정하지 않는다.

최종 RESULT/REVIEW에 기존 실제 관측의 원인 재현, 새 판정의 조건/귀속 한계, 반례/관련 검증, 원 기록 보존을 짧게 인계한다. fake 응답 정책 통과를 실제 Jev 정확도·실제 공격 차단으로 표현하지 않는다. 완료 후 관리가 질문/정책을 검토하고 다음 실제 최소검증을 정한다. 단순히 질문 표현을 바꿔 새 버전을 또 유료 재시도하는 루프를 반복하지 않는다.
