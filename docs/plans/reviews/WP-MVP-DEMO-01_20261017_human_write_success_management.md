# 실제 사람 승인 후 파일 쓰기 성공

2026-10-17. 관리가 실제 DB mode=ro/query_only·승인 소비·upstream·파일을 대조했다. **등록 파일 MCP의 실제 읽기→Jev CONFIRM→사용자 승인→단회 예약/실행→보고서 생성 흐름은 성공했다. 정상 자동 허용·실제 공격 차단·전체 MVP 완료는 아니다.**

[관측](../../../artifacts/management-mvp-write-observed-20261017/observation.json), [최신 typed trace](../../../artifacts/management-mvp-write-observed-20261017/typed-policy-trace.json). 새 호출16523ab679d2는 decision CONFIRM을 보존하면서 state OBSERVED다. `HUMAN_APPROVED_EXACT`→`RESERVED`→`OBSERVED`, approvals.consumed=true, demo confirmation resumed=1을 확인했다. UI의 일반 성공 문장으로 자동 ALLOW를 주장하지 않는다.

실제 `artifacts/runtime-mvp-demo/workspace/reports/normal.md`는 배포2.4 완료·기능시험28개 통과, 보안검토/백업복원 진행 중, 운영문서/미완료 추적을 구분한다. 원 합성 docs/release.md와 맞는다. SHA256 `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0`이다. 같은 OS 사용자의 변경 가능성과 비원자 파일 receipt 한계는 유지한다. 기존 만료 CONFIRM은 STALE/미승인으로 남았고 과거 UNKNOWN도 해제하지 않았다.

새 Jev8/8요청 모두 COMPLETED, 입력16356/출력2108, 예약512000/512000을 사용했다. 이전5시도까지 누적13/예약832000이며 첫 실패 청구 UNKNOWN은 보존한다. CLI 시작3/3도 사용됐다. 추가 모델 시험·예산 증액·새 start를 배정하지 않는다. 기존 CLI는 작업을 더 입력하지 않고 정상 종료 후 history를 수집한다.

## 남은 자동 판정 문제와 다음 좁은 개발

새 A WITHIN_TASK가 effective .83, B basis_action .5375, payload link .38 등으로 실제 CONFIRM이 유지됐다. 사람 승인 흐름이 정상이라도 정상 자동 허용의 기준을 충족한 것은 아니다. 과거 실응답을 올바른 자동판정처럼 다시 표시하지 않는다.

추가로 **수치 경계 결함**을 확인했다. basis_target은 USER probability .92, 5선택지 정규화의 수학적 confidence .90, provider .90인데 이진 float 계산값 .8999999999999999로 LOW_CONFIDENCE다. 이는 기계 정밀도 처리 대상으로, 전체 임계치를 낮추는 근거가 아니다. 다른 낮은 확신은 이 보완으로 해결되지 않는다.

다음은 [자동 판정 집중 작업](../../handoffs/WP-MVP-DEMO-01/AUTO_DECISION_NEXT_PROMPT.md)이다. 현재 실응답을 먼저 모델0으로 재현하고 source/slot 질문의 실제 입력 표현·catalog 선택을 확인한 뒤 근거 있는 최소 수정만 한다. 실제 승인 기능/새 웹앱/보존·런처 전체를 다시 구현하지 않는다. 필요 후속 실제 검증은 정상/공격 각1후보의 명시적 소규모 제안으로만 남긴다. 개발·관리 모델 호출0, 원 기록/키/원장/한도 보존이다.
