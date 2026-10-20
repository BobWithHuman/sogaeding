# 첫 실제 Jev smoke 실패 관리 검토

2026-10-16. 사용자는 검토한 합성 S01/S02·고정 Jev1.13·A/B 최대4요청/입력예약256000·정확 manifest를 ConfirmSend로 직접 실행했다. 이 사용자 실행의 한정 동의와 실제 시도를 기록한다. 관리/개발 AI의 별도 유료 호출 권한으로 확대하지 않는다.

## 실제 결과

사용자 출력과 로컬 result.json·SQLite URI mode=ro 원장의 안전 필드를 대조했다. S01/A에 JEV_RESPONSE_INVALID가 났고 B는 TURN_ANALYSIS_STOPPED, S02는 미시도다. 원장 **1행/A/FAILED/예약64000/usage 없음**이다. 실제 토큰0과 기록된 비용0은 자료 없음의 표기이며 총 비용null/INCOMPLETE_UNKNOWN_BILLABLE_USAGE가 실제 의미다. 과금 여부/액수는 확정하지 못한다. 남은 기존 예약 상한은3회/192000이며 실패분을 환불/초기화하지 않는다.

execution_exit0은 결과 기록·collect의 정상 종료이며 의미 판정 성공이 아니다. local_expected_comparison은 NOT_SCORED, 공격 식별은 NOT_ESTABLISHED다. Codex 통합은 NOT_RUN, 실제 파일 효과0이다. 기본 JevRules 제품이 실제 의미 모델로 전환됐다는 결과도 아니다.

## 원인과 증거 한계

JEV_RESPONSE_INVALID는 여러 검증 실패를 하나로 표시한다. 코드상 HTTP200 이후 content-type/크기/JSON이나 value schema/model/usage/확률/confidence 검증 경로다. 이번 실제 응답·세부 실패 stage를 보존하지 않아 정확한 실패 필드를 현재 확정할 수 없다. 키 인증401로 단정하거나 의미 분류 오답으로 계산하지 않는다. 과거 원응답/사용량은 새 호출 없이 복원할 수 있다는 근거가 없다.

추가로 [공식 API의 Choice 예제](https://docs.typesafe.ai/api)를 현재 validate_response 순수 함수에만 오프라인 전달해 **거절**됨을 재현했다. 예제의 probabilities0.88/0.12/0, confidence0.81에 대해 client는0.82/허용오차1e-6을 요구한다. confidence만 client 계산값으로 바꾸면 통과한다. [공식 confidence 수식](https://docs.typesafe.ai/confidence)은 코드 수식과 같다. 문서 예제 표시 정밀도와 client 검증의 호환 문제가 확인됐지만 실제 이번 응답이 그 형태였다는 증거는 없다. 이 둘을 혼동하지 않는다.

## 다음

[T-JEV-06 무모델 응답 계약 수리](../../handoffs/WP-PDP-JEV-01/RESPONSE_CONTRACT_REPAIR_START_PROMPT.md)를 기존 개발 세션에 배정한다. 검증 완화로 성공을 만드는 대신 공식 형식/정밀도를 대조하고, 유효 usage 독립 보존과 safe stage metadata를 준비한다. 원 실행·plan/key/authorized-run/원장/결과를 보존한다. 소스 변경 뒤 기존 manifest를 덮지 않고 별도 검토할 후속 run 준비를 한다. 실제 재요청·후속 추가 비용은 이번 관리가 실행/포괄 승인하지 않는다.

관리 관측은 [안전 관측](../../../artifacts/management-jev-live-failure-20261016/observation.json)에 기록했다. 로컬 원장 읽기·공식 문서·순수 함수 진단만 했고 키 읽기/모델/제품 도구/DB 변경은0이다. 전체 MVP·실제 Jev 한국어 정확도·Codex 정상/공격 실행 전 차단은 미완료다.
