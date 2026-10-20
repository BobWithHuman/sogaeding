# WP-F3-01 작업11 별도 AI 검토

검토일: 2026-10-14 UTC. 제품 작성자와 분리한 저장소 내부 AI 검토이며 공식 독립 진단은 아니다. 작업11 계획 전체와 첫 실제 실행 관리 판정, 변경 제품·런처·계약을 읽었다. 제품·계획·공유 runtime·원증거·예산 DB는 수정하지 않았다.

**판정: 검토 범위의 확인된 차단급 지적은 수정·재검증됐다. 사용자 직접 수동 CLI 검증을 진행할 수 있다. 실제 F3 정상 실행·공격 식별 완료 판정은 보류한다.**

최종 source 128개 fingerprint: `6c63def0a45cd44c179c2fbbcec3f000aea3c48494ca8db2648fc90ac9ffb6c0`. 작성자 `final-review-source`, 검토자 `final-own-source`, 현재 파일을 각각 SHA-256 비교해 불일치 0을 확인했다. 검토자 명령·fixture snapshot·UTC·실제 종료코드는 `artifacts/20261014-manual-cli-review/`에 보존했다.

| 지적 | 최초 관측 | 조치·재검증 |
|---|---|---|
| R-MCLI-001 출처 입력 확대 | 기존 8,192바이트 원문이 4,096개 복사 ref와 376,204바이트 judge 입력으로 확대. `input-amplification-before` exit1 | source당 8개/전체 32개 ref, 직렬화 입력 128KiB 제한. 원문 보존, 초과는 INPUT_CONTEXT_LIMIT로 안전 차단. 최종 독립 시험 PASS |
| R-MCLI-002 Windows 종료 실패 | taskkill timeout 시 direct kill/wait를 건너뛰는 기존 코드. 실제 프로세스 없이 spy 재현, `tree-kill-before` exit1 | taskkill 예외·실패에도 fallback, 종료 확인 결과 저장, 미확인 시 UNCONFIRMED와 재시도 금지 표시. 최종 spy PASS |

R-MCLI-001 최초 재현 소스는 작성자의 `tests-first-source` fingerprint `baf12ad1b8a326f464542447e70de92fcce794fcd3a6ae36b634e9f5133acd21`에서 복사한 `initial-input-fixture/semantic-unbounded-before.py`다. R-MCLI-002는 검토자 `focused-current-r1-source`의 당시 helper다. 최종 소스와 구분해 보존했다. 검토 fixture가 개선된 process.poll을 제공하지 않아 발생한 `focused-current` 14 PASS/1 FAIL도 삭제하지 않았다. fixture 보완 후 15 PASS, 최종 16 PASS다.

독립 최종 확인: `final-own-command.json` exit0, **16 PASS / 2.74초**. 별도 dev 프로세스와 임시 DB/PKI, fake judge와 프로세스 spy만 사용했다. 근거 텍스트·Unicode 인용·엄격한 source 검증, 안전 진단 및 캐시/예약 차단, 실제 RequestGuard의 HUMAN 전용 권한, 같은 세션 토큰 결합과 다른 세션 거부, 원래 요청 hash·작업종류·모드·이슈 결합, 환경 allowlist, actor 2회 제한, 180초 watchdog 및 종료 fallback, 미관측 입력/모델 호출의 비주장을 확인했다. paid judge 0, 실제 actor/TUI 시작 0, 실제 외부 쓰기 효과 0이다.

정적 확인에서 진단은 code/view 허용 목록만 저장·표시하며 기존 실패를 ALLOW/CONFIRM으로 완화하지 않는다. 최초 raw 응답을 복원하지 않고 기존 실패는 DETAIL_NOT_RECORDED로 구분한다. 검토한 `f3_outcome`은 ANALYSIS_UNAVAILABLE을 공격 식별 PASS로 계산하지 않는다. CLI 시작은 사용자 codex 입력으로만 이루어지며 사용자 요청은 TUI에서 직접 입력하고 rollout 관측 여부를 별도로 기록한다. CLI 프로세스 시작으로 유료 모델 호출을 추정하지 않는다.

작성자 Windows prepare-r2 증거를 읽어 기존 judge **12/24 시도·잔여12**, actor **0** 유지 및 콘솔 인코딩 복구를 확인했다. 검토자의 공유 DB 직접 조회·초기화는 하지 않았다. 작성자의 product 68/peer 8/helper 8 및 DOM 결과는 작성자 증거이며 검토자 16개 시험과 구분한다.

실제 모델 정상 동작, 의미에 따른 공격 식별, 실제 TUI 전체 종료와 Windows 프로세스 트리 종료는 NOT_RUN이다. actor 2,048 생성토큰 제한은 NOT_VERIFIED이며 180초 watchdog 뒤 정리 최대 10초라는 절차상 한계가 문서에 남아 있다. 미확인 종료·분석 실패·UNKNOWN 효과·입력 불일치에서는 다음 시도를 진행하지 않아야 한다. 보호 주장은 등록 MCP 도구 범위에 한정하며 내장 셸/파일 또는 모든 IPI 보호로 확대하지 않는다. 출처 일치 관측은 인과 증명이 아니다.
