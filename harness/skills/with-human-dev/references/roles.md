# 역할과 파일 소유권

역할은 협업용 책임이다. OS 권한이나 제품의 보안 경계가 아니다. 실제 사람 담당은 `docs/mvp/04_traceability_and_work_breakdown.md`를 따른다.

| 역할 | 판단·산출물 | 기본 쓰기 범위 |
|---|---|---|
| orchestrator | 준비된 task 선택, 소유권 배정, 통합, 공통 설정·문서 동기화 | 루트 설정·README·AGENTS.md, Docker/의존성 파일, scripts/, harness/build_tasks.json, 계약 밖 문서 |
| contracts | 입력·응답·상태·인증 계약 확인과 변경 검토 | 배정된 docs/mvp/contracts/ 파일; 공통 schema 코드가 생기면 해당 파일만 명시 배정 |
| backend | 사용자/세션 인증, 정책·장부, canonical hash, 원자적 reserve·승인 소비 | src/app/control/, src/app/pdp/, src/app/storage/, tests/backend/ |
| gateway | MCP 인증·세 도구·내부 PDP client·비공개 executor·resume/report | src/app/gateway/, src/app/executor/, tests/gateway/ |
| frontend | 사용자 작업·승인·이력 화면, 서버 인가를 사용하는 안전한 표시 | src/app/web/, tests/web/ |
| security-review | 정상·공격 fixture, 실제 효과·실패·경쟁 검증, 변경의 독립 검토 | fixtures/, tests/acceptance/, tests/security/, 배정된 artifacts/ 하위 실행 폴더 |

`src/app/agents/`의 REPLAY/LIVE runner는 task마다 gateway 또는 security-review 중 한 명에게 배정한다. task 장부의 owned_paths는 계획 영역이며 동시에 쓰는 권한 배정표가 아니다. 같은 역할의 T-05/T-06을 병렬로 나누려면 orchestrator가 구체적인 파일을 서로 겹치지 않게 배정한다. backend/gateway가 같은 task T-04에 참여하더라도 하위 경로의 소유자는 한 명이다. 모든 agent가 루트 의존성 파일이나 공용 conftest를 동시에 수정하지 않는다. runner의 코드 작성자와 그 결과 검토자는 다르게 둔다.

구현 작업에 보낼 인계는 아래 항목만 채운다. 존재하지 않는 시험 명령을 이미 통과한 명령처럼 제시하지 않는다.

```text
task_id: T-04
goal: 승인/쓰기 예산을 원자적으로 예약하고 실제 효과를 확인
read: docs/mvp/03_api_and_state_contract.md, 지정 schema
write: src/app/pdp/reservation.py, tests/backend/test_reservation.py
do_not_write: executor/, compose.yaml, pyproject.toml, 공용 장부
dependencies: T-01, T-03의 검증 결과 경로
acceptance: AT-07, AT-12, AT-14
checks: 구현 후 사용할 정확한 실행 명령
handoff: 변경 파일, 인터페이스 변경, 시험 결과·증거, 미해결 사항
```

통합 전 인터페이스 변경은 contracts와 관련 구현 담당에게 알리고 orphan field·enum을 남기지 않는다. contracts는 규격 검토 역할이므로 제품의 가짜 승인 토큰·우회 실행 기능을 테스트 편의로 도입하지 않는다.

검토 요청에는 변경 파일과 요구사항/시험 ID, 원기록 경로를 준다. 작성자의 예상 결론을 주입하지 않고 정상 완료, 금지 효과, 권한 경계, 장애 복구를 독립 확인하게 한다. 검토자가 수정해야 하는 경우 먼저 해당 파일의 쓰기 소유권을 이전한다.
