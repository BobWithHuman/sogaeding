# DTAP 공식 과업 실행 경로 완성 — T-DTAP-01 계속

> 2026-10-18 범위 변경: 사용자가 전수6682 대신 OS 간접공격100개를 선택했다. 최신 [100개 연결 작업서](CONNECT_SELECTED_100_PROMPT.md)가 아래 전수 구현·목표 축소 금지보다 우선한다. 아래 내용은 필요한 공통 통제와 이전 경과의 참고다.

2026-10-17 관리 후속 배정. 최신 RESULT/별도 REVIEW와 사용자 check는 **정적 전수 목록·격리된 2도구 각색 연결만 완료, 전체 실행 가능0/6682**다. 현재 run 차단은 의도된 동작이고 실패한 유료 실행이 아니다. 이 작업은 기존 T-DTAP-01의 미완료 구현을 계속하는 것이며 새로운 평가 조건/모델/목표 축소를 추가하지 않는다.

정본 START_PROMPT.md를 필요한 부분만 함께 따른다. **gpt-5.2 / low**, engine-off와 engine-on 두 조건, 전체6682 목록·indirect/benign/direct 분리, 별도 replay/모델선택 유료 pilot 없음, 개발 제품 모델/환경·judge 호출0을 유지한다. 관리 정본은 수정하지 않는다. 기존 소스·vendor·inventory·동결 manifest·각색 smoke/실패는 보존한다.

## 이번에 해결할 핵심

최신 사용자 실행 목표는 **퇴근 전 PowerShell 두 창에서 시작하고 다음 날 결과를 확인하는 실제 무인 평가**다. engine-off 창은 실제 gpt-5.2/low, engine-on 창은 동일 실제 gpt-5.2/low+실제 Jev를 사용한다. 가짜 actor/Jev는 개발 통합 시험용일 뿐이며 최종 사용자 run에서 mock transport가 선택되면 시작 전에 거절한다. 기존 등록 파일 MCP MVP의 실제 성공은 보존하며 DTAP 전수 실행 경로 완료와 혼동하지 않는다.

최종 인계에는 같은 experiment/task manifest를 사용하는 두 arm별 실행 명령과 다음 날 `status/collect` 명령을 포함한다. 두 창은 별도 환경/결과/포트를 쓰고 공유 상한은 원자적으로 집행한다. 시작 후 task마다 사용자 입력·승인 대기를 요구하지 않는다. CONFIRM을 자동 승인하거나 DENY로 바꾸지 말고 미승인 상태로 기록해 정해진 시간 내 종료하며, 독립된 다음 task는 정책에 맞게 진행한다. UNKNOWN task 재전송은 하지 않는다. 인증/필수 gateway·저장 장애/총한도 도달은 자동 중단하고 원인·완료율·사용량을 남긴다. 채팅/개발 AI가 켜져 있어야만 진행되는 방식으로 만들지 않는다. 호스트 절전/전원/전역 설정을 자동 변경하지 않는다.

앞 인계의 “실행 준비”가 실제로는 state 확인+FULL_RUN_DISABLED 프로그램에 머물렀다. tools/dtap_eval.py는 준비 manifest의 ready0을 강제하고, ResponsesBackend는 MockTransport 외를 금지한다. 단지 이 거부문을 지우지 말고 아래 실제 실행 경로와 한도/binding을 연결한다. 다음 인계에서 다시 정적 목록/강제 후보2도구 smoke만 늘려 종료하지 않는다.

**공식 TaskExecutor/agent·injection·judge를 재사용**해 task config부터 최종 judge까지 잇는 generic orchestration을 먼저 완성한다. 이미 고정한 repo `e0323a521ba4ef88f8e14c1eccf68d0a3d19a458`의 `eval/evaluation.py`, `utils/task_executor.py`, `utils/agent_helpers.py`, `utils/injection_helpers.py`, `utils/judge_helpers.py`와 공식 agent backend를 읽고 기존 proxy/HookManager 연결을 삽입한다. 동일 기능의 runner를 다시 설계하지 않는다. 필요한 wrapper/SDK adapter는 benchmark 격리에 둔다.

1. **환경/실제 공격 주입:** config→필요 환경·서버 준비→공식 setup/reset→실제 prompt/tool/environment/skill 등 해당 attack 적용→공식 agent 실행→judge→close/환경 정리까지 task별 독립 lifecycle을 구현한다. 공격 명령을 실제 user 요청으로 승격하거나 가짜 후보 sequence로 공식 injection을 대체하지 않는다. 원 setup/history/도구 설명을 수정한 각색 fixture는 회귀로만 남기고 공식 점수에서 제외한다.
2. **자율 Responses/SDK loop:** gpt-5.2/low의 실제 요청 생성·reasoning 상태/출력·function_call/function_call_output·종료/불완전응답·tool error를 이어지는 실제 다중 turn loop로 구현한다. 실제 provider transport와 RO key 참조는 코드상 준비하되 기본 disabled·엄격한 manifest/사용자 opt-in/공급자 ledger를 통과해야 전송된다. 개발 검증은 동일 production dispatch의 가짜 transport로 한다. 단순 body 한 번/정해진 후보 반환으로 끝내지 않는다. 두 조건의 가용도구/effort/상한·sampling은 동일하다.
3. **공식 schema와 등록:** 실제 tools/list 전체를 얻어 44서버/43환경 및 도메인별 coverage를 갱신한다. 기존Registry의 schema/property→slot/resource/effect mapping을 tool family별로 확장한다. 모든 도구를 WRITE로 뭉뚱그리거나 unknown 도구를 hard DENY한 것을 semantic 차단으로 세지 않는다. query/메일·파일·SQL·shell 등 구체 schema와 실제 효과를 연결하고 도메인 norms를 trusted 환경 설정에서 받는다. 미지원/알수없는 정책은 별도 상태로 남긴다. 정답/공격 목표/judge 내부를 판정 허용 근거로 전달하지 않는다.
4. **입력·출처 호환:** 원 catalog/본문·source hash/turn/call 결합을 보존한다. `access_token: Optional` 같은 공개 schema 설명과 실제 credential 값을 typed 수집 역할로 구별한다. 실제 비밀 차단은 유지하며 공식 설명을 다른 문구로 바꾸는 우회로 전수 호환을 주장하지 않는다. 합성 benchmark의 민감 모양 데이터·큰 catalog/여러 도구 결과·이미지/상태 입력도 경계를 명시한다. source가 많으면 provenance를 조용히 삭제하거나 공격 부분만 빼지 않는다. bounded input을 처리 못 한 task는 incomplete이지 방어 성공이 아니다.
5. **실제 사전 관문:** 적용 arm의 call은 원 args/server/tool/user/source·policy에 묶인 gateway 승인·원자 예약 후에만 정확1회 전달한다. 기본 native 우회/공식 config의 우회 서버 경로를 두 조건에서 똑같이 통제한다. DENY 기록은 PRE에서 저장하고 Post 누락/취소/응답유실은 UNKNOWN을 보존한다. off는 의미 판정만 생략하고 환경·schema·도구제한·기록은 동일하게 유지한다.
6. **원 judge·전체 상태 복원:** 최종 actor 출력과 도구 trajectory/업무 상태를 원 judge에 정확히 연결한다. Python tuple/list 반환·async/LLM judge 등 실제형식을 처리한다. 현재 선택4파일 snapshot만으로 전체 arm 상태동일성을 주장하지 않는다. 공식 초기 snapshot·서비스별 DB/상태/메모리·시간/random(가능 범위)을 복원/기록한다. 전이 helper/permission/environment/judge의 모든 네트워크/LLM 호출을 같은 공급자 한도 계층 아래에서 관측/예약한다. 지원하지 않는 helper는 fake 통과로 대체하지 않는다.

## 무모델 검증과 readiness

먼저 같은 pinned **공식 정상 task1건과 indirect task1건**을 위 공통 경로/실제 Docker·MCP·gateway·공식 injection·원 judge에 통과시킨다. actor/Jev/환경·judge 모델 응답만 명시적으로 fake하고, 공식 데이터/도구 목록/초기 상태/주입 자체는 각색하지 않는다. 이는 실제 모델 ASR이 아닌 연결 검증이다. source→자율 loop→의미판정→효과→judge와 두 조건의 parity·정리 증거를 남긴다. 이어 tool/environment family별로 공통 경로를 확장하며 전체 coverage가 실제로 늘어나는지 확인한다. 이 첫 두 task는 최종 유료 subset/세 번째 조건/별도 pilot이 아니다.

readiness는 hardcoded0이나 정적 서명수로 정하지 말고 task가 요구하는 실제 schema·환경·주입·judge·LLM 한도·정확 gateway 집행의 충족 여부에서 산출한다. 모든 task가 준비된 경우에만 FULL_READY다. 일부만 준비됐으면 전체 분모6682와 ready 수/누락 이유를 그대로 보고하며 전수 완료라고 하지 않는다. 현실적으로 미해결 외부 의존성이 있으면 해당 파일/환경/해결책을 특정하고 다른 구현을 계속한다.

**실제 Jev 정확도/자율 actor 공격성공 여부는 이후 평가의 결과다. 이를 유료 평가 시작 전 이미 증명해야 하는 순환 선행조건으로 만들지 않는다.** 전송 전 필요한 것은 통합 경로·권한/한도·자료/도구/효과 binding과 실패 처리의 검증이다. 미실행 정확도는 NOT_RUN으로 남긴다. actual state readback 없는 ALLOW를 효과 성공으로 올리지 않는다.

## 비용 초안 수정·한도 계층

기존 `343bac49…` manifest/추정은 보존한다. 그 actor $32,186.50은6682×2×16=213824요청, 요청당 최대69632 입력예약/2048 출력, 일반 단가 입력$1.75/출력$14로 계산한 **보수 예약 계산**이다. 실제 청구/평균 추정이나 검토된 지출 승인이 아니다. 전체 Jev/환경/judge 비용도 UNKNOWN이다.

- 새 산출물은 **실제 사용량**, 근거 있는 **예상 사용량(없으면 UNKNOWN)**, 선택할 **하드 상한/예약량**을 분리한다. 평균값을 임의로 채우거나 상한을 평균처럼 표시하지 않는다. 같은 요청량의 공식 요율을 최신 근거로 확인한다.
- UTF8 bytes+protocol 여유값을 실제 tokenizer/이미지 토큰 수와 혼동하지 않는다. 64KB schema/context와2048 output/16응답/20도구/600초가 원 task를 완결할 수 있다는 근거가 없으므로 domain별 실제 구조/지원경계를 확인해 선택안으로 제시한다. 큰 요청/vision/환경 helper 누락을 비용계산0으로 처리하지 않는다. 상한 때문에 끝나지 못한 task도 incomplete로 보고한다.
- actor/Jev/환경·permission/judge 공급자별 task/arm/합산 **원자적 요청·입출력/시간 예약**을 실제 모든 전송에 연결한다. 기존 JevClient의 한 ledger 한도와 전수267280 제안 요청의 충돌을 해결하되 기존 원장을 증액/복제/초기화하지 않는다. 새 benchmark 한도 owner를 분리하며 실행 전·후 usage와 UNKNOWN을 정직하게 집계한다. 비용환불·실행미확정 자동 재전송을 추가하지 않는다.
- 전체 실행은 같은 두 조건의 **checkpoint batch**로 진행/중단/재개 가능하게 한다. batch는 추가 실험조건이 아니며 전수 목표를 subset으로 바꾸지 않는다. 완료된 task를 다시 소비하지 않고 CLAIMED/UNKNOWN은 먼저 상태를 대조한다. 시작·정지 때 전체완료율/남은 cap을 보여준다. 기본 동시성은 작게 두고 충돌·포트·네트워크 제한을 검증한다.
- 새 서비스는 기존 Docker network를 삭제/prune하지 않고 명시된 benchmark 전용 주소·포트를 충돌 검증해 사용한다. 실제 외부 서비스 효과/사용자 홈·비밀 mount·전역 설정은 허용하지 않는다.

최종은 하나의 `check → 사용자 명시 opt-in run → status/collect`로 연결한다. 준비 시작 전에 사용자에게 반복 check/예산 질문을 넘기지 않는다. 필요한 구현·무모델 검증·최종 별도 AI 검토1회를 끝낸 뒤 실제 전송자료/모델/전체 한도·계산근거·동결 hash와 복사 가능한 실행 명령을 마지막에 인계한다. 준비 단계에서 실제 유료 provider 호출은0이다.

## 보고와 소유 범위

기존 START_PROMPT의 benchmark adapter/registry/profile·명시 내부 계약·최소 제품 확장·관련 tests/문서 소유 범위를 이어 쓴다. 공통 통합 담당1개·최종 AI 검토1개로 진행한다. PDF/P0 기준은 새 노출의 필요한 페이지와 최초문제→수정→재검증을 연결하고, 정본/hash 문구 때문에 수백 회귀를 반복하지 않는다.

인계: `docs/handoffs/WP-DTAP-01/20261017-dtap-runtime/RESULT.md`, `COVERAGE.csv`, `BUDGET.md`, `USER_RUN.md`, 별도 `20261017-dtap-runtime-review/REVIEW.md`. 다음 상태는 **공식 task 경로 구현·실제 coverage 증가·두 조건의 실행 후보**로 보고한다. 미완료는 실제 남은 기술 경계로 한정하고, 부분 완료를 전체DONE으로 요청하지 않는다. 전체 시나리오 비교·gpt-5.2/low·두 조건·유료0 준비 원칙은 유지한다.
