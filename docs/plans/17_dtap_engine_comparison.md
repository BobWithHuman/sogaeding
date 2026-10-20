# DTAP OS 간접공격100개 엔진 비교

> 2026-10-18 최신 시연개선은 [18번 계획](18_practical_demo_improvement.md)과 [WP-ENGINE-DEMO-02](../handoffs/WP-ENGINE-DEMO-02/START_PROMPT.md)를 따른다. 기존100개 원결과는 보존하고, 우선 routing·별도.50 허용후보·공격성공조건부 DTAP 사례·AgentDojo 소수 비교를 준비한다. 새 유료 실행은 시작하지 않는다. 아래 전수100개 실행·당시 예산 상태는 그 시점의 계획/기록이다.

2026-10-18 최신 사용자 결정: 6682개 전수 목표를100개로 축소하고 선정을 관리 담당에게 위임했다. 기존 연결된 OS-filesystem 환경의 공식 indirect100개 전부를 선택한다. 원 inventory/config/judge/setup는 보존하며 과거 결과에 따라 선별하지 않는다.

정본은 [100개 연결 작업서](../handoffs/WP-DTAP-01/CONNECT_SELECTED_100_PROMPT.md)와 [ADR-B01](decisions/ADR-B01_dtap_os_indirect_100.md)이다. 선택 목록은 `artifacts/management-dtap-100-20261018/selection.json`, SHA256 `05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b`다. config/judge/setup300개 hash를 확인했다.

| 단계 | 목표 | 상태 |
|---|---|---|
| T-DTAP-01 | 기존 OS18도구 runtime에 선택100개 연결, 실제 provider binding·공유한도·검토·두창 명령 준비 | IN_PROGRESS |
| T-DTAP-02 | 같은100개를 실제 gpt-5.2/low로 engine-off 실행 | TODO/합산 지출 선택 전 |
| T-DTAP-03 | 같은100개를 실제 gpt-5.2/low+Jev로 engine-on 실행하고 두 결과 비교 | TODO/합산 지출 선택 전 |

두 arm은 격리된 동일 초기 상태와 같은 task/공격자료/모델/effort/가용도구/상한을 쓴다. 두 창을 동시에 시작할 수 있으며 총200 task-arm이다. 별도 replay·모델탐색·유료 pilot은 없다. Jev는 jev-1.13.0을 유지한다. 최종 실제 정확도는 평가 결과이지 준비의 선행조건이 아니다.

선택100개는 보안범주9개, tool 주입63·environment 주입33·혼합4개다. direct/benign은 이번 대상이 아니며 정상 오차율은 NOT_EVALUATED다. 전체 DTAP/다른 도메인의 성능으로 확대하지 않는다. 실제 예산 상한과 사용량은100개 규모로 새로 산정하고 사용자에게 구체 명령과 함께 마지막에 선택받는다. 스크립트 기본 $250과 과거6682 예약 계산은 승인 예산이 아니다.

주 비교는 engine-off/on 공격 성공 건수·성공률·감소 폭이다. arm별 대상100개·완료수·judge 판정 가능 수·paired 유효 수를 병기하고 actor 미채택/미시도·실제 semantic DENY/효과0·CONFIRM·UNKNOWN·미지원·인프라 오류·예산 중단을 분리한다. 원 judge를 쓰며 실패/미실행을 방어 성공으로 계산하지 않는다.

다른44서버/43환경·누락12compose·VM 장치 문제의 전수 해결은 이번 완료 조건에서 제외한다. 기존 demo·키·원장·성공·실패 기록은 보존한다. 현재 관리 작업은 선정/범위 배정만이며 제품 source 수정·유료 평가 실행은 하지 않았다.

## 과거 전수 준비 경과 — 아래 목표는 ADR-B01로 대체됨

## 준비 인계의 부분 수용과 후속

[관리 검토](reviews/WP-DTAP-01_20261017_prepare_management.md): source15 SHA/drift0·manifest343bac49…·task6682 unique와 정상/위험×두조건의 각색 결과4개를 대조했다. 정상전달1/1, 위험전달3/1·judge true/false는 fake actor/Jev·2도구 각색 연결 근거이며 실제 ASR이 아니다. 전체 공식runtime 준비0/6682, 실제조건별완료0/13364이므로 T-DTAP-01은 IN_PROGRESS다.

[후속 공식 실행 경로 완성](../handoffs/WP-DTAP-01/COMPLETE_OFFICIAL_RUNTIME_PROMPT.md)을 배정했다. pinned 공식 TaskExecutor/agent/injection/judge를 재사용하고 자율 gpt-5.2/low loop·실제schema/전체초기상태·전공급자한도를 연결한다. 또 다른 고정후보2도구 각색 smoke만으로 종료하지 않으며 실제 모델 정확도는 평가 결과이지 준비의 순환 선행조건이 아니다.

actor상한초안32186.50은 6682×2×16=213824요청의 입력예약14,888,992,768/출력437,911,552를 요율1.75/14 per1M로 계산한 보수값이다. 실제청구/평균/승인예산이 아니며 전체 Jev/환경/judge 비용은 UNKNOWN이다. 다음에는 예약상한·근거있는평균(없으면UNKNOWN)·실제usage를 분리하고 원초안은 보존한다. 현재 유료0·원소진장부보존·전수목표/두조건/별도재생없음은 유지한다.
