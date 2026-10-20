# DTAP 큰 응답·초기 상태 계승 수리 별도 AI 검토

2026-10-18. **PASS — 무모델 수리·후속 실행 준비 범위. 미해결 P1/P2 발견 없음.** 검토자는 제품 코드를 수정하거나 유료 요청을 보내지 않았다. 키·암호화 snapshot 본문에 접근하지 않고, 변경 코드·관련 시험과 원장의 안전한 집계/초기 image 메타데이터를 읽기 전용으로 확인했다.

## 대상과 최종 후보

`benchmark`의 proxy/hook/official adapter/runtime policy/server/budget/controller/continuation, product Engine/server의 기본값을 유지하는 확장 지점, DTAP Python/PowerShell 진입점 및 큰 응답·정산 시험을 검토했다. 비교 기준은 보존된 `user-usd7-settled-1/source`다.

최종 실행본은 `artifacts/20261018-dtap-os100/user-usd7-context-2`, manifest는 `6bd1d554f5d3df72443e1ff5b5d218e4e27983e2edb3176257048f38a5958c41`이다. 동결 78개 파일과 현재 소스의 hash 불일치가 0임을 직접 확인했다.

## 확인한 경계

- 제품 기본 output 64KiB·HTTP body 128KiB는 유지한다. benchmark의 MCP 수신만 bounded streaming 1MiB, benchmark Engine output 1MiB·HTTP envelope 1MiB+64KiB로 확장한다. SSE는 해당 JSON-RPC id의 완전한 응답에서 종료하고 전체 수신량 상한을 유지한다.
- 약 155KB의 완전한 결과는 transport와 PostToolUse에 OBSERVED로 저장할 수 있다. 의미 분석 한도 64KiB는 유지한다. 분석 불완전 자료는 축약하거나 모델에 전달하지 않고 해당 task를 CONTEXT_LIMIT으로 종료한다. 이후 task는 진행한다.
- 1MiB 초과·실제 응답 유실·Post/close 미확정은 UNKNOWN/필수 중단을 유지한다. CONTEXT_LIMIT은 semantic DENY나 방어 성공으로 세지 않는다. 완료하지 못한 task는 최종 ASR 또는 유효한 완료 pair로 계산하지 않는다.
- 기존 GPT-5.2 low·Jev 모델/질문/정책/임계치, provider UNKNOWN hold, 원 과업의 재실행 금지와 누적 $7 상한을 유지한다. 기존 settlement를 복사하고 원 최대 예약과 실패 이력을 보존한다.

## 검토 중 발견 및 보완

P1: 후속 원장만 복사하면 이미 완료한 engine-off 5건과 새 engine-on의 initial image가 달라져 유효 pair에서 제외될 수 있었다. 원 initial snapshot의 task/setup hash·JSON hash·image identity를 manifest에 결합하여 계승하도록 보완했다. Controller와 PowerShell은 기존 image 존재/identity를 확인하며, 메타데이터·image가 없으면 setup을 재실행하지 않는다.

존재하는 폴더만 나열하면 폴더 전체 누락을 놓칠 수 있는 경계도 보완했다. 반대 arm이 미시작인 원 jobs의 기록된 initial image를 required 집합으로 삼아 누락과 바뀐 image를 거절한다. 관련 폴더 삭제·기존 image 재사용 반례와 최종 코드를 재검토했다.

## 직접 대조한 준비 상태

후속 SQLite를 `mode=ro`/`query_only`로 확인했다. 이전 provider 62개는 모두 COMPLETED이며 정산액은 834,584 micro-USD($0.834584), 미확정 hold는 0이다. 합산 상한은 기존 사용액을 포함한 $7이며 남은 상한은 $6.165416이다. 공급자 최종 청구서/계정 잔액 조회는 아니다.

원 과업 10개(오프 완료 6·UNKNOWN 2, 온 미승인 CONFIRM 1·UNKNOWN 1), lineage history 1개를 계승했다. 미시작은 190개다. 이전 off 과업 6개의 initial image/JSON과 후속에 결합한 6개를 직접 대조해 불일치 0을 확인했다. 새 keys 디렉터리·paid opt-in·broker 시작 기록은 없고 owner도 0이다.

구현자는 최종 관련 pytest 114개 PASS, PS5.1 guard 8개 PASS, ruff PASS와 실제 PowerShell 무모델 check/6개 Docker image 확인을 보고했다. 검토자는 같은 전체 시험을 반복하지 않고 변경 경계와 준비본 대조를 독립 수행했다. 최종 명령·원증거는 구현 RESULT/USER_RUN을 따른다.

이 검토는 실제 후속 모델 평가를 실행하거나 engine-on 방어율을 수용한 결과가 아니다. 기존 실제 공격 성공/실패·CONFIRM·UNKNOWN을 보존하며, 미시작 task의 후속 실행과 향후 공식 judge 결과를 구분한다. 100쌍 완주·자동 허용/차단 정확도는 보장하지 않는다.
