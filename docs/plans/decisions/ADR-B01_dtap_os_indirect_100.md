# ADR-B01 — DTAP OS 간접 공격100개로 비교 범위 축소

상태: 사용자 지시에 따른 범위 결정, 2026-10-18. 구현·유료 실행 완료 결정이 아니다.

사용자는6682개가 너무 많으므로100개를 골라 연결하라고 지시했다. 현재 공통 실행기가 OS-filesystem18도구에 연결되어 있고, pinned 공식 inventory에 이 환경/서버만 사용하는 간접 공격이 정확100개 있다. 이를 빠짐없이 선택한다. 공격 성공이나 방어 결과를 보고 선별하지 않는다.

피해 모델 gpt-5.2/low와 engine-off/on 두 조건은 유지한다. 각각 같은100개를 실행하여 총200 task-arm이며 engine-on 판정은 실제 Jev다. tool 주입63, environment 주입33, 혼합4로 보안 범주9개를 포함한다. 원본 config/judge/setup300개 hash를 검증하고 선택 파일을 동결했다.

선택 정본: `artifacts/management-dtap-100-20261018/selection.json`, SHA256 `05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b`.

나머지 서버/환경과 전체6682 실행 준비는 이번 완료 조건에서 제외한다. 옛 inventory·실패·사용량·판정 근거를 보존한다. 이번 결과는 OS IPI100개 한정으로 보고하며 direct 및 benign 성능은 평가하지 않는다. 기존 정상 자동 허용 MVP 근거는 별도로 유지한다. 목록 선정으로 runtime_ready100/100을 주장하지 않고 실제 연결·최종 검토·동결된 두 창 명령이 필요하다. 구체 합산 지출 상한은 아직 승인되지 않았다.

다음 배정: `docs/handoffs/WP-DTAP-01/CONNECT_SELECTED_100_PROMPT.md`. 옛 작업서의 전수 구현과 축소 금지 문구는 이 결정으로 대체한다.
