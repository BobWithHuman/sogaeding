# T-JEV-06: 실제 Jev 응답 검증 실패의 무모델 진단·호환성 수리

관리 배정. with-human-dev/최신 AGENTS, 실제 실패 관리 검토와 현재 Jev 계약·원장을 읽는다. 제품 구현은 기존 개발 세션에서 수행하고 별도 AI 검토한다. **실제 provider/actor 재호출0, 키 내용 수집/재입력0**이다. 기존 결과/원장/authorized-run/동결 계획과 키를 삭제·덮기·초기화하지 않는다.

## 실제 실패와 확정 범위

사용자 명시 ConfirmSend로 합성 smoke를 실행했다.2026-10-16T10:45:33.648765Z 결과는 S01/A JEV_RESPONSE_INVALID, B TURN_ANALYSIS_STOPPED, S02 미시도다. 원장1행 view=A/status=FAILED/input_reserved=64000/usage=null. 실제 사용량·청구액은 UNKNOWN이며 0으로 확정하지 않는다. execution_exit0은 결과 수집 프로그램 종료 성공이며 판정 성공이 아니다. 실제 CLI/파일 효과는 NOT_RUN/0이다.

JEV_RESPONSE_INVALID는 content-type/응답크기/JSON파싱/모델·키·질문·usage·확률·confidence 검증을 합친 코드다. 이번 원응답·실패 단계가 남지 않아 실제 세부 원인을 단정할 수 없다. 현재 _request에서는200 이후 경로에 이 코드가 있으나 HTTP상태 자체를 저장한 증거와 구분한다. 키401이라고 단정하거나 교체하지 않는다.

관리의 무모델 재현에서 [공식 API](https://docs.typesafe.ai/api) Choice 예제(billing0.88/technical0.12/sales0/confidence0.81)가 현재 validate_response에서 거절됐고 client 계산0.82로 바꾸면 같은 나머지 값은 통과했다. [공식 confidence](https://docs.typesafe.ai/confidence)의 수식은 현재 코드와 같지만 공식 예제 수치/표시 정밀도와 exact1e-6 검사가 충돌한다. 이는 독립적으로 확인한 문서 예제 호환 문제이며 **이번 원응답이 이 분기에서 거절됐다는 증거는 아니다.** 원문을 확인하고 가설/사실을 분리한다.

## 작업

1. 현재201파일과 실패 원장/결과/동결37소스·질문/자료/한도, 키 metadata(내용/해시 제외)를 기준선으로 고정한다. 원응답/usage의 과거 누락을 복구했다고 꾸미지 않는다.
2. 공식 API/고정 버전 schema와 공식 SDK 소스·공식 예제를 대조해 offline fixture로 호환성을 검증한다. 공식 예제는 실제 API 보증/실제 응답 대신이 아니다. model pin, 정확 question/option coverage, finite/type/range/합계·최대선택·출처 검증을 보존한다. 선택 확률/confidence의 표시·계산 정밀도 문제는 근거 있는 경계로 처리하고, 잘 통과시키려 임계치0.90를 낮추거나 구조/수치 검증 전체를 제거하지 않는다. 원 분포로 코드가 계산한 값과 provider 값을 구분하며 대회 정확도 보정은 별도다.
3. 실패 단계별 고정 allowlist 진단을 남긴다. HTTP상태/허용 content-type enum/길이·JSON 유효성/모델 일치/필수·추가 필드 수/질문·선택지 coverage/수치·합계·confidence 실패 종류 등 **허용된 metadata만** 안전하게 기록한다. 동적 unknown key/string·본문·header 전체·토큰·request credential·임의 exception 원문은 출력/저장하지 않는다. metadata 부족 시 UNKNOWN을 명시한다. 요청·response hash/수치도 전송자료·민감정보 노출 범위를 검토하고 필요한 최소만 보관한다.
4. 사용량은 의미 답변 검증과 분리해, 응답에서 독립적으로 유효하게 검증한 계수는 답변 실패에도 별도 기록할 수 있도록 한다. 누락/잘못된 usage는 UNKNOWN을 보존한다. 청구0원·환불·64000예약 반환으로 처리하지 않는다. API 실패·호환성 오류를 공격 탐지 PASS로 집계하지 않는다.
5. 평가 종료 결과가 execution_exit0이라도 semantic 실패/NOT_SCORED/부분 완료가 명확히 보이게 사용자 보고를 보완한다. 첫 실패 후 B/다음 후보0·no retry를 유지한다. 기존 실패 결과를 새 성공으로 덮지 않는다.
6. 공식/합성 정상·경계·불량 응답, metadata 비노출, 유효 usage+잘못된 답/누락 usage, 첫 실패 중단, 상태/원장 보존을 의미 있게 검증하고 관련 회귀·별도 AI 검토를 한다. 지적을 해결하기 위해 실제 유료 API를 시험 호출하지 않는다.
7. adapter/helper 변경은 현재 frozen source와 다르므로 과거 manifest 검사를 끄지 않는다. 과거 run을 읽기 전용 collect할 수 있게 보존하고, 다음 사용자가 검토할 새 계획/manifest·run을 **명시적으로 분리하는 방식**을 준비한다. 자동 reset/새 예산·paid 재개를 하지 않는다. 기존 한도4/256000에서 이미1/64000이 예약됐고 잔여는3/192000이다. 후속 제안은 기존 실패 소비와 잔여/추가 예산을 합쳐 명시하고, 완전한 A/B2후보 재실행4회가 기존 잔여3회에 들어간다고 보고하지 않는다. 새 실제 호출은 구체 절차를 인계한 뒤 사용자 직접 선택으로 남긴다.

쓰기 범위: src/app/transparent/jev.py, 필요한 diagnostics.py·Jev 평가 helper/PS 최소 보고/관련 테스트, 현재 Jev 내부 응답·평가 설명, 새 handoff/artifacts. 정책 권한·원자 실행·모델/질문/임계치·전체 CLI 통제·전역 설정·기존키/원장·관리 plans/harness/AGENTS는 변경하지 않는다. 필수 가이드의 오류/중요정보/정확한 API 사용·자원/상태 근거를 해당 원문 페이지와 코드/실패·수정·재진단에 연결한다.

새 RESULT/REVIEW에 실제 실패 원인 확정 여부, 원응답 미보존 한계, offline 호환 근거와 변경, 원장 보존, 다음 제한 진단 실행 제안 및 NOT_RUN을 명시한다. 의미 판정/실제 Codex IPI 보호 완료로 보고하지 않는다.
