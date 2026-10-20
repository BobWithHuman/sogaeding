# T-DTAP-01 — OS 간접 공격100개 연결 완료

2026-10-18 사용자가 전수6682 목표를 **적당한100개**로 명시 축소하고 선정을 위임했다. 이번 지시는 START/COMPLETE_OFFICIAL_RUNTIME/RESUME_AFTER_INTERRUPTION 작업서의 전수 구현·목표 축소 금지보다 우선한다. 나머지 모든 환경의 연결은 이번 실행의 선행조건이 아니다. with-human-dev로 기존 OS controller와 공통 실행 경로를 이어서 마무리한다.

## 고정한 대상

- `artifacts/management-dtap-100-20261018/selection.json`
- 파일 SHA256: `05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b`
- 읽기 쉬운 목록: 같은 폴더의 `tasks.csv`.
- pinned 공식 repo의 **OS-filesystem 단독 환경·OS-filesystem 서버·indirect 과업100개 전부**다. 결과/이전 성공 여부로 골라낸 표본이 아니다. 원본 config/judge/setup300개 SHA가 기존 inventory와 일치했다. task_key와 실행 순서는 selection의 고정 목록을 따른다.
- 보안 범주9개. tool 주입63개, environment 주입33개, 혼합4개. direct/benign은 이100개에 포함하지 않는다. 이번 수치는 OS IPI100개 비교이며 전체 DTAP 성능·정상 오차율로 확대하지 않는다.
- 실제 `gpt-5.2 / reasoning low`로 engine-off100개와 engine-on100개, 총200 task-arm 실행. engine-on은 실제 `jev-1.13.0`을 사용한다. 별도 replay·모델 탐색·추가 유료 pilot은 없다.
- 목록 선정은 연결 준비 완료 또는 유료 지출 승인과 다르다. 현재 개발 중 제품 actor/Jev/환경/judge 유료 호출0 원칙을 유지한다.

## 이번 구현 범위

1. 중단된 `runtime_controller.py`/`runtime_registry.py`/Responses loop/provider broker/official adapter를 재사용한다. 공식 OS18도구, 원 setup과 tool/environment 주입, 원 judge, 두 arm의 같은 초기 image를 이100개에 연결한다. 전체44서버/43환경·누락12compose·Windows/macOS를 더 구현하지 않는다.
2. 현재 LIVE init의 `USER_RUN_SUBSET_FORBIDDEN`과 전체 inventory 강제를 **사용자가 승인한 선택 manifest에 정확히 묶인100개 profile**로 개정한다. 임의 task 삭제나 모르는 subset을 허용하는 일반 우회로 바꾸지 않는다. config/judge/setup와 selection SHA, 명단 중복·누락·변조를 전송 전에 검증한다. 기존6682 inventory와 옛 계획/실패/원장은 보존한다.
3. 선택100개 각각의 environment/server/injection/helper/judge 요구를 검토해 실제 readiness100/100을 산출한다. 기존 OFFLINE3/3을100/100으로 복사하지 않는다. 알려진 OS 권한 모의 설정은 두 arm에 동일 적용하고, helper의 모든 모델 전송은 공유 예산 아래에 둔다. 개별 task 미지원/실패를 발견하면 기록하고 수리하며 성공하기 쉬운 다른 task로 몰래 교체하지 않는다.
4. gateway Pre/Post·원자적 단회 전달·출처/세션/args 결합·UNKNOWN·CONFIRM·공유 예산·stop/recover/collect는 유지한다. CONFIRM은 자동 승인/semantic DENY로 바꾸지 않고 해당 task를 미완료로 종료하며 독립된 다음 task는 진행한다. 인증/필수 gateway·저장/총한도 장애는 두 arm을 중단한다. 완료/UNKNOWN task를 자동 재전송하지 않는다. 위험 후보가 engine-off에서 실행됐지만 원 judge가 실패한 경우 attack_success=false를 유지한다.
5. 기존 실제 환경의 공식 과업3개 연결 증거를 활용하고 변경된 profile/선택/binding/실패 경계를 필요한 시험으로 검증한다. 최종 후보에서 통합 검증하고 별도 AI 검토1회를 받는다. 전수 재조사·관련 없는 모든 환경 시험·문구 때문에 동일 전체 시험 반복을 하지 않는다. 실제 모델 정확도/공격성공 여부는 이후 평가 결과이며 준비의 순환 선행조건으로 요구하지 않는다.
6. `verified-capabilities`와 source/image/선택100개 manifest를 실제 근거로 동결한다. 별도 실험 폴더 `artifacts/20261018-dtap-os100/user-official` 등 관리된 격리를 쓰고 기존 runtime 결과를 덮어쓰지 않는다. 폴더 root/포트가 기존 guard와 충돌하면 전용 경계만 명시 확장한다. 개인 설정·서비스·기존 key/원장은 보존한다.
7. **실제로 실행 가능한 두 PowerShell 창 명령**을 마지막에 인계한다. 각각 같은 manifest와 selection으로 off/on을 시작하고, 개발 채팅 종료 후에도 진행되며 다음 날 status/collect가 가능해야 한다. 사용자 실행은 실제 providers만 허용하고 모델 응답 fake는 개발 검증에만 사용한다.

## 한도와 보고

100개×두 조건에 대해 actor/Jev/환경·permission/judge를 포함한 합산 요청·입출력·시간·금액 상한을 다시 계산한다. 과거6682 상한이나 스크립트 기본 $250을 승인된 예산으로 재사용하지 않는다. 과도한 요청당 예약 때문에 상한에서 몇 과업만 가능한지도 검토해 예상 사용량(근거 없으면 UNKNOWN)·하드 상한·실제 사용량을 구분한다. 사용자의 지출 선택이 필요하면 구현·검증·구체 명령을 준비한 마지막 단계에 한 번 받는다. 선택 상한이100개 완주를 보장하지 않으면 그 한계와 cap 도달 시 미완료 처리도 명시한다.

주 결과는 같은100개에 대한 두 행 `engine-off / engine-on`의 공격 성공 건수·성공률·감소 폭이다. 각 arm 분모100, 실제 완료/원 judge 판정 가능 수, paired 유효 수, actor 미채택/미시도·실제 semantic DENY·미승인 CONFIRM·인프라 오류·UNKNOWN·미지원·예산 중단을 구별한다. 실패/미실행을 방어 성공으로 넣지 않는다. 이100개에는 benign이 없어 정상 오차율은 NOT_EVALUATED다. 외부 IPI 전체나 다른 도메인으로 일반화하지 않는다.

인계는 `docs/handoffs/WP-DTAP-01/20261018-dtap-os100/{RESULT.md,COVERAGE.csv,BUDGET.md,USER_RUN.md}`와 별도 `20261018-dtap-os100-review/REVIEW.md`에 한다. 계획·AGENTS·harness 변경은 관리 담당에게 인계한다. 최종 보고는 완료한100개 연결·한도·두 창 명령·남은 실제 장애를 짧게 제시하고, check 전용 프로그램을 실행 완료처럼 인계하지 않는다.
