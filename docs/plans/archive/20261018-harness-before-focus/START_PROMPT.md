# WP-ENGINE-DEMO-02: 시연 중심 판정 routing·.50 후보·DTAP/Dojo

`with-human-dev`를 사용한다. 정본은 [18번 관리 계획](../../plans/18_practical_demo_improvement.md)이다. 이 배정은 구현·무모델 검증·별도 AI검토·실행 준비이며 실제 유료 전송은 하지 않는다. 현재 사용자는 계획을 요청했고 아직 실제 새 실행 명령을 선택하지 않았다.

## 우선 읽기

- [18번 계획](../../plans/18_practical_demo_improvement.md): 구체적 판정 조건·범위·예산·평가 분모
- [현재 실제 결과](../WP-DTAP-01/20261018-context2-results/RESULT.md), [독립 감사](../WP-DTAP-01/20261018-context2-results-review/REVIEW.md)
- 변경할 함수: `src/app/benchmark/runtime_policy.py`, `registry.py`, `runtime_report.py`, `runtime_budget.py`; 기존 gateway/adapter/원장 수용시험은 필요한 함수와 관련 증거만 읽는다.
- ADR-P02/P03/P04와 적용 guide P0는 계획의 실제 변경 지점에 연결한다. 원문 전체나 과거 로그를 반복 출력하지 않는다.

## 구현 순서

1. 현재 raw 응답·.90 정책 replay는 그대로 보존한다. 공개 schema/사용자 요청/원 후보를 대조해 일반 조회와 불확실·민감 행동을 나눈다.
2. trusted registry의 schema/권한/부작용으로 코드 routing을 보강한다. 공개·비민감·사용자 범위가 확인된 조회는 모델0 ALLOW, 확정 금지는 모델0 거부. 도구 이름·외부 설명·공격 목표/정답별 예외로 분류하지 않는다.
3. 출처 role와 현재 후보/현재 사용자 요청을 구분한 새 질문 버전을 만든다. A는 과업의 필요한 중간 단계, B는 실제 추가 지시 채택/충실성의 판단이다. 원문·hash·span과 완전성 검증을 유지한다.
4. 별도 benchmark 시연 프로필에서만 `allow_threshold=.50`, `risk_threshold=.90`을 둔다. B rawLEGITIMATE/.50 이상+A rawWITHIN_TASK+모든정확권한·검증 통과 때만 허용한다. 기존 명확한 DENY를 낮은 허용 기준으로 덮지 않는다. 위험값/UNCERTAIN을 .50 넘는다는 이유로 허용하지 않는다.
5. 최종CONFIRM 내부의 DENY·실제forward0을 all-state 관측으로 보고한다. 최종ASR/utility와 분리한다. 정상 완료를 희생한 차단은 정상성공으로 세지 않는다.
6. DTAP은 기존 off 성공12개에 대한 조건부 사례 평가와 결과를 보기 전 고정한 정상3개를 새 revision으로 준비한다. 최초 표시순서의 서로 다른3유형을 고정한다. actor/model/input settings/공격/초기image 동등성이 검증될 때만 기존off 결과를 재사용한다. 새 on은 실제 자율 actor이며 강제 tool 후보나 replay arm을 만들지 않는다.
7. AgentDojo는 official commit과 workspace의 공격3조합+동일user clean3과업×off/on=12조건을 먼저 동결한다. originalFunctionsRuntime/utility/security를 유지하고 함수 실행 전 같은PDP를 거치는 trustedexecutor를 연결한다. 실제gateway경유 증거와 함수adapter증거를 구분한다. fixedattack을 사용하고 추가 paid attacker/judge 모델은 금지한다. GPU·다른suite·새대시보드·전수환경 확장은 하지 않는다.
8. 잔여 예산은 원누적3.289294/총7을 계승한다. 제안 작업상한 DTAP1.80·Dojo1.20·미집행여유.710706이며 자동전용하지 않는다. 실제 입출력 최악상계/중복동시예약/비정상usage/UNKNOWN hold를 검증한다. 기존400k예약을 근거 없이 평균값으로 바꾸지 않는다. 정확한 모델wire와 비용상계 검증 없이 지출명령을 인계하지 않는다.

작은예산의 기본은 arm순차·전체actor동시1요청이다. 현재 최대예약2개=1.629376이 Dojo1.20보다 크므로 동시실행이 가능하다고 인계하지 않는다. 현재정산+hold+동시최대예약을 무모델 preflight로 검사한다. Dojo 전용 입력/출력상한을 정하면 양조건 동일설정·완전입력상계 검증을 하고 기존DTAP에 소급하지 않는다. 요청을 잘라서 한도에 맞추지 않는다.

1~5의 엔진 보완을 먼저 완료한다. 그 경계가 작동한 뒤6~7의 실제 연결을 수행한다. 사용자에게 준비 단계만 계속 늘려 인계하지 않도록 필요 없는 도메인/모델/환경을 추가하지 않는다.

## 파일 소유권

허용: 필요한 benchmark별 policy/registry/adapter/provider/report/비용 코드, 관련 tests와 benchmark전용설정, scripts/tools의 좁은 실행기 변경, `artifacts/` 새 하위, 이 작업팩의 RESULT/USER_RUN.

공통 계약·DB·장부는 통합 담당1개가 소유한다. 명시된 신규프로필·benchmark별 계약 확장만 허용하며 기존 product전역.90·기존service·개인Codex설정·원키·모든동결run의source/manifest/DB를 수정하지 않는다. docs/plans·harness·AGENTS 최종 상태변경은 관리담당만 수행한다. 대시보드 팀원의 파일은 수정하지 않는다.

## 검증과 완료

정상 조회/권한요청/생성쓰기·외부데이터활용·위장권한·미승인비밀읽기·수신자변경·보안설정변조·파괴행동·인용/금지·경계confidence·모호함·PDP장애·응답유실·중복호출/UNKNOWN을 필요한 경계에서 검증한다. 기존 실제응답은 원정책에서 원결과, 새질문은 별도 합성응답과 프로토콜 검증으로 구별한다. 무모델 시험을 실제 Jev 정확도라고 하지 않는다.

관련시험→최종통합1회→별도AI검토1회를 기본으로 한다. 로그는 안전한 파일에 저장하고 모델에는 실패/결과 요약만 보낸다. 실제키열람·snapshot복호화·유료모델호출0, 원실패/UNKNOWN/CONFIRM 보존을 대조한다. 기존CONFIRM이나UNKNOWN을 같은call로 자동재개하지 않는다. 새정책 평가의 fresh run도 인계된 정확한 비용·자료·범위를 사용자가 명시선택하기 전에는 전송하지 않는다.

최종 인계는 변경 목적, 실제 routing/threshold계약, 시험·실제효과 근거, 한계, 동일모델/초기환경/공격 고정, 기존 비용 승계, 정확한 사용자 실행·수집 명령을 한 번에 담는다. 준비완료와 실제모델성공을 구분한다. AgentDojo가 연결되지 않았다면 전체완료라고 하지 말고 정확한 남은adapter경계를 남긴다.
