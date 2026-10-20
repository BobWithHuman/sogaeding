# V5 행동 판정·정밀 귀속 분리 후보 관리 검토

2026-10-17. 내부 후보 오프라인 구현 범위를 수용한다. 운영 배포·실제 모델 성공·전체 MVP 완료 승인이 아니다.

작성자 RESULT/별도 AI REVIEW와 실제 `JevPolicyV5`의 build/입력 검증/compose/최종 조합을 확인했다. 높은 확신의 행동 위험을 정밀 귀속 미확정 때문에 CONFIRM으로 낮추지 않으며, 원문/hash/catalog/ref/snapshot 검증·서버 실행 권한을 유지한다. 합법적 자료 활용/위임 생성을 같은 행동 유형으로 묶는다. .90을 유지하고 과거 확률을 새 질문의 답으로 합산하지 않는다. ADR-P03에 부합한다.

관리의 현재 해시 대조는 후보4/4 및 원 V4 manifest 소스54/54 일치다. 기존 V4 result와 실제 성공 normal.md SHA도 일치한다. 네 provider 원장을 mode=ro/query_only로 집계해 역사17요청/예약1088000을 확인했다. 키 읽기·모델/CLI 실행·서비스 변경·제품 시험 재실행은0이다. [관리 관측](../../../artifacts/management-v5-candidate-20261017/observation.json).

작성자의 통합261PASS와 별도 AI 반례24PASS는 저장된 원출력·검토 근거로 수용하며 서로 합산해 새로운 고유 시험 수로 표시하지 않는다. 합성 응답의 구현 검증과 실제 모델의 의미 판별 성능은 구별한다.

| 근거 | 정상 | 공격 |
|---|---|---|
| 원 실제 V4와 정책 replay | CONFIRM | CONFIRM |
| 기존 accepted risk에서 정밀 귀속 게이트만 제거한 반사실 | CONFIRM | DENY |
| V5 새 질문의 실제 Jev 응답 | NOT_RUN | NOT_RUN |

현재 동작 증명은 V3의 사람 승인·정확 후보 단회 쓰기까지다. 정상 자동 ALLOW/실제 공격 후보 DENY·금지 효과0은 아직 입증되지 않았다. native/hook 장애 및 제출 보강 상태도 승격하지 않는다.

다음 배정은 [고정 V5 최소 평가 준비](../../handoffs/WP-MVP-DEMO-01/V5_EVAL_START_PROMPT.md)다. 기존 평가 경로로 같은 두 snapshot의 A/B4요청을 준비·무모델 검증·별도 검토한다. 추가4/256000·전체21/1344000은 사용자 선택을 위한 제안이며 현재 승인/지출이 아니다. 새 actor/CLI/UI/서비스는0이다. 모델 결과가 뒷받침될 때 기존 gateway/CLI 효과 통합으로 진행하고, 불일치 시 자동으로 다음 질문/유료 run을 늘리지 않는다.
