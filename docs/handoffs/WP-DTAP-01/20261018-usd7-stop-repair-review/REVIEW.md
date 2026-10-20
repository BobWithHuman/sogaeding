# DTAP $7 정산·종료 수리 별도 AI 검토

2026-10-18. 판정: **PASS — 무모델 구현·실행 준비 범위**. 미해결 P1/P2 발견 없음. 실제 유료 후속 실행·모델 정확도·100쌍 완주를 수용한 결과는 아니다.

검토자는 구현자와 분리된 AI이며 제품 코드를 수정하지 않았다. 실제 키·암호화 snapshot을 열지 않았고, 유료 요청·서비스 교체 없이 diff/시험 코드와 준비 원장의 안전한 집계만 확인했다.

## 검토 대상

- `src/app/benchmark/runtime_budget.py`, `runtime_continuation.py`, `runtime_controller.py`, `provider.py`
- `tools/dtap_runtime.py`, `scripts/dtap_eval.ps1`, `scripts/dtap_official_runtime.ps1`
- `tests/hookgw/test_dtap_usd7_settlement.py`
- 원본 `artifacts/20261018-dtap-os100/user-usd7/source` 및 단일 후속 `user-usd7-settled-1`

최종 후속 manifest는 `764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb`다. 동결 78개 파일과 현재 소스의 hash 불일치가 0임을 직접 확인했다.

## 확인한 경계

1. 기존 사용량을 포함한 두 조건 합산 7,000,000 micro-USD, arm별 3,500,000 micro-USD를 유지한다. `BEGIN IMMEDIATE` 안에서 예약과 검증된 usage 정산을 직렬화한다. 원 최대 예약은 보존하고 비용 검사에만 검증된 settlement를 반영한다. 요청 수·토큰·시간 상한을 정산으로 초기화하지 않는다.
2. 진행 중·provider UNKNOWN·잘못된 usage·미등록 billing model은 원 최대 hold를 유지한다. 과업 UNKNOWN과 provider usage UNKNOWN을 구분한다. 원 과업은 COMPLETED/CONFIRM/UNKNOWN 모두 claim에서 다시 실행하지 않는다.
3. 부모 manifest·원장 fingerprint·행 baseline과 배타적 successor claim을 후속에 결합한다. 기존 stopped 부모 원장을 수정하지 않고 과거 금액과 원기록을 후속으로 계승한다.
4. 예산 거절은 전송 전에 task/arm/provider receipt를 기록한다. 현재 task의 receipt 및 provider/POST/close 미확정 여부를 함께 확인한다. 예산 stop을 일반 infra 오류로 덮어쓰지 않고 이후 task dispatch를 끝낸다. 실제 미확정은 UNKNOWN을 유지한다.
5. GPT-5.2 low/Jev 계약, Jev 질문·정책·`.90` 임계치, 기존 판정은 변경 대상에 포함하지 않는다. 실제 후속 실행은 명시적 사용자 명령으로만 시작한다.

## 검토 중 발견·보완

- 첫 CAP가 다른 arm에서 발생한 뒤 현재 provider 응답이 유실되는 경합에서 과업 UNKNOWN을 BUDGET_STOPPED로 약화할 수 있었다. 현재 task별 전송 전 receipt와 STARTED/UNKNOWN provider 조회 및 관련 반례로 보완했다.
- 후속 DB 누락 시 빈 원장을 자동 생성하면 과거 비용이 빠질 수 있었다. DB 생성 전 읽기 전용 lineage·binding·부모행 hash 검증과 누락/빈 DB/부모행 삭제 거절로 보완했다.

두 발견의 수정과 반례 시험 코드를 재검토했다. 구현자가 관련 무모델 시험 66개 PASS를 보고했다. 검토자는 같은 전체 시험을 반복하지 않고 변경 경계와 준비 원장의 읽기 전용 대조를 수행했다. 최종 시험 명령·로그는 구현 인계의 RESULT와 증거를 따른다.

## 준비 원장 직접 대조

후속 DB를 `mode=ro`/`query_only`로 열어 provider 13개 모두 COMPLETED, 기존 과업 4개(완료 1·미승인 CONFIRM 1·UNKNOWN 2), 기존 stop 3개를 확인했다. 정산 78,217 micro-USD, unresolved hold 0, owner 0, lineage 1이다. 즉 과거 명목 비용 $0.078217을 포함하며 남은 합산 한도는 $6.921783이다. 이는 공급자 최종 청구서나 계정 잔액 조회가 아니다.

남은 196개 과업 조건만 후속 대상이다. 기존 UNKNOWN/CONFIRM 재시도, 새 $7 예산 발급, 기존 결과 수정, 모델 정확도 또는 ASR 개선 주장은 승인하지 않았다.
