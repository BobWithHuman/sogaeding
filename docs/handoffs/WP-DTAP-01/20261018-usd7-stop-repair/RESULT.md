# DTAP $7 정산·중단 처리 수리

> 사용자 실제 실행 후속: 정산은 작동했고 누적$0.834584/완료6(공격성공3)이 기록됐다. /16의128KiB 응답 경계에서중단됐으며 새on실행기록은없다. 최신 수리는 [20261018-context-output-repair/RESULT.md](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-context-output-repair/RESULT.md). 아래는 최초 수리 준비 시점 기록이다.

2026-10-18. 사용자가 관리 채팅에 직접 수정을 위임했다. **구현·무모델 검증·별도 AI 검토·후속 준비 완료, 후속 실제 모델 실행은 NOT_RUN**이다.

기존 비용 계산은 완료된 요청에도 전체 context 최대 예약액을 영구 합산했다. 원 실행을 재현하면 GPT 4회 후 창별 한도로 중단된다. 새 버전은 요청 전 최대 비용을 원자적으로 확보하고, 검증된 완료 usage만 등록 요율로 정산한다. STARTED/UNKNOWN·usage 누락/범위 초과·미등록 billing model은 최대 예약을 유지한다. 요청 수·토큰·시간의 별도 제한도 유지한다.

예산 거절에는 과업·조건·공급자별 전송 전 거절 기록을 남긴다. 해당 기록과 미확정 provider/파일 효과가 없을 때만 BUDGET_STOPPED로 분류한다. 다른 창의 CAP와 실제 응답 유실이 겹치면 UNKNOWN을 유지한다. 최초 중단 사유를 보존하고, 뒤 과업의 heartbeat/storage 반복을 끝내며, 진행 중 과업의 최종 snapshot 저장은 기존 소유권·저장 한도 안에서 마친다.

후속 실행은 원 manifest/논리 원장 hash에 결합한 단일 successor다. 원장의 13 provider 기록·4 과업·3 stop을 복사·보존하고, 원 기록은 수정하지 않았다. 후속 원장이 누락되거나 부모 행이 바뀌면 초기화 대신 거절한다. 원 과업의 완료·CONFIRM·UNKNOWN은 재실행하지 않는다. 원 폴더에는 단일 후속을 가리키는 `usd7-successor.json`만 새로 추가했다. 기존 제품 서비스와 이전 broker는 교체하지 않았으며 새 broker 포트는 18661이다.

| 확인 항목 | 결과 |
|---|---|
| 원 최대 예약액 합계 | $5.718944 — 원 기록 유지 |
| 기존 검증 사용액 정산 | $0.078217 (OpenAI $0.076779 + Jev $0.001438) |
| 기존 포함 누적 상한 / 잔여 | $7 / $6.921783 |
| 기존 provider 기록 / 추가 유료 호출 | 13 / 0 |
| 기존 과업 / 이어서 시도할 미시작 과업 | 4 / 196 |
| 관련 pytest | 66 PASS |
| PowerShell 5.1 구문·조기 거절 | 8 PASS, Docker·provider 호출 0 |
| Ruff | PASS |
| 실제 PowerShell check | 준비·동결·원장 결합 PASS, 키/paid-opt-in/새 broker 없음 |
| 별도 AI 검토 | PASS, 발견 2건 수정·재검증, 미해결 P1/P2 없음 |

시험은 원 4회 조기 중단 재현, 완료 30회 정산, 80개 동시 예약/정산, 한도 경계, 잘못된 usage/model, provider 응답 유실 hold, 미확정 효과 분류, 단일 successor, 누락/변조 원장 거절, broker의 HTTP 예산 코드 전달 및 queue 중단을 확인한다. 기존 DTAP 경계·보고·회귀를 포함한다. 정책·질문·`.90` 임계치·공식 시나리오·피해 모델은 변경하지 않았다.

고정 manifest: `764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb`. 동결 소스 78개와 현재 파일 일치. 제품 키를 읽거나 새 유료 호출을 보내지 않았다. 개발 AI 검토 비용과 제품 모델 호출은 별개다.

근거: [verification.json](C:/sogaeding/artifacts/20261018-usd7-stop-repair/verification.json), [수정 파일 hash](C:/sogaeding/artifacts/20261018-usd7-stop-repair/source-manifest.json), [별도 검토](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-usd7-stop-repair-review/REVIEW.md), [실행 안내](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-usd7-stop-repair/USER_RUN.md).

필수 가이드 적용: G3 PDF406의 공유 자원 임계구역을 SQLite BEGIN IMMEDIATE와 경쟁 시험에 연결했다. G3 PDF511 SR3-1 및 G4 PDF37~39의 입력/예외 기준을 정수 usage·등록 model·오류 타입·미확정 보존에 연결했다. SQL 식별자는 고정 표/열 목록만 사용하고 값은 parameter binding한다. TLS/인증·의존성·판정 정책을 변경하지 않았다. 이 검증은 전체 20설계/49약점 전수 진단 완료 주장이 아니다.

남은 범위: 유료 후속은 미실행이다. 기존 유효 완료 pair는 없으므로 최종 ASR/방어율을 주장할 수 없다. 98개 남은 pair의 실제 결과와 예산 내 완료 개수는 실행 후 판단한다. 새 후속은 실제 사용자 입력으로만 시작한다.
