# 같은 WP-MVP-DEMO-01 보완: 승인창에서 종료되는 시연 수리

with-human-dev와 최신 관리 판정 `docs/plans/reviews/WP-MVP-DEMO-01_20261016_host_wait_management.md`, 기존 RESULT/REVIEW/USER_RUN, `artifacts/management-mvp-demo-host-wait-20261016/observation.json`을 읽고 이어서 수행한다. 새 제품/평가 계획만 생성하는 작업으로 끝내지 않는다. 관리 정본(plans/harness/AGENTS)은 수정하지 않는다. 기존 작업팩의 구현 경로와 필요한 현재 내부 계약/진단 변경은 이 보완 범위에서 계속 위임한다.

사용자 실제 실행은 호스트 읽기 승인창에서 CLI가 끝났으며 현재 Control 공개 읽기1건은 READY/ALLOW, upstream0, 보고서 없음, Jev0, CLI 예약1/2다. 코드의 `subprocess.run(timeout=180)`은 사람의 입력/승인 대기도 포함하고, 반환된 TIMEOUT/actor_exit를 main이 버린다. 예약→보고서188.383초는 이 제한과 부합하지만 원래 종료 사유가 기록되지 않았으므로 확정해 쓰지 않는다.

이번 수정은 다음을 하나의 인계로 완성한다.

1. **대화형 CLI 수명주기 수리.** 사람이 `/hooks`나 요청/승인창을 보는 동안 180초 전역 타이머가 CLI를 예고 없이 종료하는 구조를 고친다. 기존 승인된180초 제한을 몰래 해제/확대하지 않는다. 대기와 실행을 신뢰성 있게 구분할 수 없으면 그 한계를 밝히고 실제 가능한 명시적 대화형 시간 한도를 제안한다. actor/provider 요청 수/실패 no-retry·종료 후 자식/후속 효과 경계는 유지한다. 새 한도/자료 변경은 최종 구체적 USER_RUN에서 명시하고 사용자 직접 선택으로 남긴다.
2. **종료 원인 보존.** 시작/종료 UTC, elapsed, exit code 또는 timeout/interrupt/launch failure를 안전한 append-only 결과로 남기고 CLI·HTML에 구분해 표시한다. `started`를 성공으로 표시하지 않는다. 예전 실행은 종료 사유 UNKNOWN으로 유지한다. timeout/실패 시 스크립트 성공 종료로 숨기지 말고 이미 있던 판정/실제 효과 조회 결과를 함께 보여준다. 민감 argv/env/auth·터미널 원문을 덤프하지 않는다.
3. **쓰기의 호스트 승인 대기도 포함한 연결.** 기존 USER_RUN의 의미 쓰기 READY30초가 호스트 승인 대기 중 만료되는 알려진 경계를 이번 보완에서 다룬다. 현재 write30초 freshness·정확 인자/출처 snapshot/정책 binding을 끄거나 모든 쓰기를 allow/confirm으로 바꾸지 않는다. 집행 직전 의미 판정 시점/승인 순서를 정합적으로 구성하는 등 실제 승인 대기를 통과할 구조를 구현한다. 재분석/재전송이 필요하면 동일 작업/예산에 대한 명시적 방식과 비용 한도를 제안하며 자동 유료 재시도는 추가하지 않는다. 빠른 클릭만 요구하는 절차로 해결했다고 하지 않는다.
4. **시연 화면과 작업 맥락.** 실제 history는 mode가 없어 NOT_ESTABLISHED다. USER_DEMO/OFFLINE_REPLAY, actor 시작/종료, 정책 허용 대기와 실제 OBSERVED/UNKNOWN을 구분해 표시하되 USER_DEMO를 모델 정확도 통과로 오해시키지 않는다. 개발 스킬/하네스 자동 적용으로 범위 밖 읽기가 생긴 경로도 확인한다. 전역 개인 설정을 지우지 말고 이번 demo child의 필요 최소 맥락만 조정한다. `bob-agentgateway`4400은 별도 경고로 표시하고 개인 설정/로그인/샌드박스/승인 정책을 우회하지 않는다.
5. **실제 대기를 거치는 무모델 검증.** 즉시 성공을 반환하는 subprocess mock만으로 끝내지 않는다. Windows PowerShell5.1과 실제 CLI/로컬 고정 provider 또는 동등한 대화형 자식으로 입력·승인 대기, 정상 종료/취소/timeout, 남는 자식과 지연 효과를 검증한다. 시간은 시험 전용 축소 clock 등을 사용해 불필요한 긴 대기를 피한다. 실제 gateway의 읽기→출처→정상 쓰기 효과 및 강제 공격 후보 차단 효과0 회귀도 확인하고 별도 AI 검토한다. 가짜 의미/actor 검증을 실제 Jev 정확도로 표현하지 않는다.

기존 키/manifest/원장/실패 HTML/episode-1.claim을 보존하고 초기화·환불·덮어쓰지 않는다. 현재 manifest 해시로 변경 소스를 다시 시작하게 하거나 drift 검사를 무시하지 않는다. 같은 demo의 새 revision이 기존 runtime·예산/예약1/2를 이어받도록 검증 가능한 변경 binding을 준비한다. 새 DB/예산으로 실패를 숨기거나 한도를 자동 증가시키지 않는다. 남은1회 시작 예약으로 정상 작업을 우선 확인하고, 공격 시연에 추가 시작이 필요하면 그 사실을 구체적으로 명시한다. 개발 AI 유료 actor/Jev 호출0이다.

최종 RESULT/REVIEW/USER_RUN에는 수정 원인·무모델 재현·기존 자료 보존·정확한 수정 revision/한도·한 번의 최소 사용자 시작 명령을 함께 준다. 완료 조건은 사용자가 정상 요청을 입력하고 개별 호스트 승인을 검토한 뒤 실제 보고서를 볼 수 있도록 준비하는 것이다. 실제 LIVE 성공은 사용자 실행 후에만 판단한다.
