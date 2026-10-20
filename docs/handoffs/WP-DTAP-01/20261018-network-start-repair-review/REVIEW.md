# Docker 네트워크 시작 수리 별도 AI 검토

2026-10-18. **PASS — 시작 전 네트워크 수리·실행 준비 범위. 미해결 P1/P2 발견 없음.** 검토자는 제품 파일·원장·키를 수정하지 않았으며 유료 모델이나 broker/controller를 시작하지 않았다. 키 내용과 hash에 접근하지 않았다.

검토 대상은 `scripts/dtap_official_runtime.ps1`의 `Test-DtapNetworks`, 현재 operational plan과 보존된 `plan.before.json`, PS 시험/검증 기록이다. 제품 Python 수정이 없어 이전 전체 회귀를 반복하지 않았다.

## 직접 확인

- 원 plan과 현재 plan의 의미상 차이는 `engine-off/subnet`, `engine-on/subnet` 두 항목뿐이다. 114/115를 130/131로 바꾸며 실험·network name·manifest를 유지한다. 전후 plan hash와 조정 내역은 `network-repair.json`에 남아 있다.
- 두 해당 Docker network만 읽기 전용으로 직접 inspect했다. 둘 모두 `Internal=true`, 소유 label `dtap-f6f0319aa5-settled1-settled1`, 각각 `10.233.130.0/24`, `10.233.131.0/24`임을 확인했다. 타 실험 network를 삭제/변경하는 수리 코드는 없다.
- `Test-DtapNetworks`는 조회 실패·미준비·소유권/내부망/subnet 불일치를 거절한다. 실제 run 경로에서 시작 lock 생성과 API 키 읽기/복사보다 먼저 실행된다. 기존 충돌을 시작 설정을 소비하기 전에 탐지한다.
- 보존된 실패용 시작 설정을 archive로 이동한 상태다. 현재 새 `broker-start.lock`, `keys`, `paid-opt-in.json`, broker 시작 기록이 없다. 제품 과업 claim·UNKNOWN·비용 원장을 초기화하는 변경은 없다.
- 원장을 `mode=ro`/`query_only`로 대조했다. provider 62개, 과업 10개, 정산 834,584 micro-USD($0.834584), owner 0, 활성 stop 0으로 유지된다. 기존 완료 6·미승인 CONFIRM 1·UNKNOWN 3은 그대로다.
- manifest `6bd1d554f5d3df72443e1ff5b5d218e4e27983e2edb3176257048f38a5958c41`와 동결 Python 78개가 유지되며 파일 hash 불일치는 0이다. 누적 $7 상한이나 기존 사용액을 변경하지 않았다.

## 검증 근거와 한계

`artifacts/20261018-context-output-repair/verify_network_start.ps1`의 PS5.1 검사 9개와 `network-start-verification.json`의 실제 PowerShell check PASS 기록을 검토했다. 구현자가 동결 소스·초기 image 6개·두 내부망 검사를 완료했고, 검토자는 실제 네트워크와 보존 상태를 독립 대조했다. 추가 provider 요청은 0이다.

이 수리는 실제 모델 실행 전에 확정된 network 생성 실패만 복구한다. 미확정 실행의 재시도나 새 예산 발급이 아니다. 후속 유료 실행은 사용자의 명시적 PaidOptIn 명령으로만 시작하며, 과거 UNKNOWN을 다시 실행하지 않는다. 실제 engine-on 결과·공격 차단율·100쌍 완주를 이 검토로 주장하지 않는다.
