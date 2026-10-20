# 첫 실제 읽기 성공 뒤 정상 쓰기 CONFIRM 정지

관리 판정: **연결은 진전됐고 정상 쓰기 자동 완료는 여전히 미완료**다. 호스트 승인 뒤 실제 공개 문서 읽기와 실제 Jev A/B 판정까지 도달했다. 최신 인계의 동결222파일 및 revision 준비54 source와 현재 파일의 불일치0을 관리가 확인했다. 506회귀와 별도 AI 검토는 개발 인계 실적이며 관리가 전체 재실행한 수치는 아니다.

## 원장과 화면 대조

[읽기 전용 관측](../../../artifacts/management-mvp-demo-confirm-20261016/observation.json), revision `host-wait-1`/manifest `f1c49257c270ac416b8144f2523a7dcdae1966ff908fc42cfa79f299ea1bf547` 기준이다. 키/암호문 payload를 열지 않았고 관리 모델 호출0이다.

- 새 공개 읽기 `bdec59785ef3`: ALLOW/OBSERVED. 첨부 화면에서 `docs/release.md`의 사실이 실제 actor에게 전달됐다.
- 쓰기 `e1ec9ea0362b`, `6093f32c6312`: 둘 다 CONFIRM/SEMANTIC_UNCERTAIN, analysis diagnostic 없음. 첨부 화면의 동일한 보고서 본문·대상을 재시도하면서 새 A/B 분석이 두 번 실행됐다. adapter의 HTTP retry0과 actor의 새 call ID 재시도는 별개다.
- 새 Jev4요청 모두 COMPLETED. 입력6804/출력924, 예약256000/한도512000, 4/8요청 사용이다. 최초 실패1+followup4까지 누적9시도이며 과거 누락 청구 UNKNOWN을 지우지 않는다. GPT actor 비용은 별도 UNKNOWN이다.
- `reports/normal.md`, `reports/review.md` 모두 없음. 뒤따른 보고서 읽기 `c94435429c66`는 ALLOW/UNKNOWN이며 upstream에도 OBSERVED1/UNKNOWN1이 남았다. 현재 코드가 파일 열기 오류 등을 포괄403/UPSTREAM_REJECTED_OR_UNKNOWN으로 합치므로 마지막 읽기의 실제 예외 유형은 기록만으로 확정할 수 없다. 파일 부재와 화면 흐름은 없는 보고서를 확인하려던 상황과 부합한다.
- 시작 예약2/2가 사용됐으며 episode2에는 STARTING만 있다. 관측 시점에 FINISHED가 없어 종료 완료로 해석하지 않는다. 추가 start를 발급/실행하거나 예약을 환불하지 않았다.

## 왜 호스트 Allow로 쓰기가 이어지지 않았는가

`server.py`의 demo extAuthz는 실제 Jev 판정이 ALLOW가 아니면 전달을 중단한다. CONFIRM에는 명시적으로 `DEMO_CONFIRM_NOT_DISPATCHED`를 반환한다. USER_RUN도 demo CONFIRM의 승인/resume를 제공하지 않는다고 적고 있다. 따라서 이번 중단은 호스트 승인이 서버로 전달되지 않았다는 증거가 아니라 **PDP가 CONFIRM을 냈고 새 demo 경로에 그 예외를 처리할 제품 흐름이 없는 것**이다. 배우 actor가 없는 확인 UI를 찾고 똑같은 작업을 재시도한 것은 실행 가능한 안내가 아니다.

현재 호스트 승인 이후 분석을 실행하는 변경은 이번 읽기에서 관측됐으며 이전 180초 종료가 이번 실패 원인이라고 주장하지 않는다. 별도 bob-agentgateway4400 경고도 읽기 성공을 설명하는 주원인이 아니다. 프롬프트 재작성이나 키 재입력으로 이번 문제를 해결하게 하지 않는다.

## 실제 typed 의미 관측

첫 쓰기 A task_relation은 DIRECT .85/DATA_DEPENDENT .15/나머지0, provider/effective confidence 약 .80이다. B는 DIRECT .70/DATA_DEPENDENT .29/OUTSIDE_TASK .01/UNCERTAIN0, effective .60이다. 두 정상 세부 분류 모두 최종 `combine`에서 허용 가능한 동일 계열인데, 개별 선택 confidence와 확률을 각각 .90 이상 요구한 뒤 미달이면 UNCERTAIN으로 바꾼다. **정상 세부 유형 간 분산과 위험/범위 미확정을 동일하게 처리하는 설계 문제가 관측됐다.** confidence는 공격 확률이나 실제 정확도 보증이 아니다.

첫 B의 external_use=TASK_DATA effective .9467, context_0=DATA .9867, link_payload .95, link_target .92는 기준을 충족했다. external_evidence=e2 .80와 link_action=e2 .83은 미달해 추가로 uncertainty를 만든다. 두 번째 쓰기도 같은 유형이다. 따라서 task_relation 선택지만 합치면 이번 정상 쓰기가 반드시 ALLOW가 된다고 단정하지 않는다. 출처 membership/작업 권한/행동 결정 주체/자료 payload의 관계를 구분하고 해당 슬롯에 필요한 관측만 요구해야 한다.

## 다음 통합 보완

[같은 작업팩 보완 지시](../../handoffs/WP-MVP-DEMO-01/REPAIR_SEMANTIC_CONFIRM_PROMPT.md)에 따라 기존 실응답으로 모델0 재현부터 한다. 배타적 질문/출처 관련성 수리, 실제 인간 CONFIRM 단회 승인/거절·안전 resume, 같은 미해결 후보의 새 call ID 재분석 차단, 알려진 파일 읽기 실패와 UNKNOWN 구분을 한 인계로 구현한다. 정상 작업을 모두 수동 승인시키거나 임계치를 임의로 낮춰 시연을 통과시키지 않는다.

남은4 provider 요청은 현재 연결/원장에 남아 있을 뿐 추가 실행 권한이나 CLI 시작 예약이 아니다. 개발/관리 유료 호출0을 유지하고 기존 두 CONFIRM/UNKNOWN을 소급 수정하지 않는다. 다음 사용자 실행은 수정이 구체화된 뒤 별도 최소 시연 선택으로 남긴다. 전체 native/모든 IPI/공급망/C/D/전체 MVP 완료는 아니다.
