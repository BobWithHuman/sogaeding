# 실제 고정 시연 결과 마감

2026-10-17 관리 배정, **T-DEMO-02**. T-DEMO-04의 실제 두 사실보고 자동 ALLOW/OBSERVED·각쓰기1·PDP승인0을 수용했다. 다음 두 자료와 기존 표시 수정 함수만 읽어 오프라인으로 마감한다.

- `docs/plans/reviews/WP-MVP-DEMO-01_20261017_frozen_actual_management.md`
- `artifacts/management-frozen-demo-actual-20261017/observation.json`

실제 실행은 Jev4/입력9046·출력455, 공유 원장8/8, 역사37/2368000·CLI7 claim 소비다. 원 키·manifest·원장·실파일·과거 실패/UNKNOWN은 그대로 두고 제품 모델/actor/새 CLI/새 예산/서비스 교체 없이 작업한다. 관리 정본/장부는 수정하지 않는다. 기존 T-DEMO-02/MVP_CLOSEOUT의 범위 중 이번 결과에 필요한 표시·문서만 우선한다.

## 수정할 표시

추가 관리 확인: episode7은 실제 `/quit` 후 EXITED/exit0·616.968초, connection_closed/tree_cleanup VERIFIED·connection0이다. `artifacts/management-frozen-demo-actual-20261017/closure.json`을 추가 근거로 사용한다. 사용자에게 다시 종료를 요구하지 않는다. 현재 이력에서 정책 UNKNOWN/B current_behavior 누락도 재현됐다. `src/app/transparent/demo_report.py`의 정책/질문 허용목록과 viewer의 질문 표시 목록이 current1/current_behavior를 빠뜨린 것이므로 **이 collector의 해당 표시 목록 수정도 이번 소유 범위에 명시 추가**한다. 새 엔진 판정·확신값·원 DB는 바꾸지 않는다.

1. 실제 읽기 OBSERVED를 NOT_COMPLETED로 오표시하지 않는다. FILE_NOT_FOUND/NO_WRITE2건과 UNKNOWN을 구별한다. 성공 쓰기2건의 ALLOW와 실제 효과를 구분해 표시한다.
2. STARTING/FINISHED는 같은 episode로 묶고, 실제 finish가 없으면 현재 실행 중 또는 종료 미관측으로 표시한다. 사용자 `/quit` 전 완료·cleanup을 확정하지 않는다. 기존 RO history로 종료 후에도 source drift 때문에 원 실제 결과를 읽지 못하게 하지 않는다.
3. 보고서 줄바꿈을 보존한다. “A의 낮은 확신 유지” 같은 문구는 실제 관측과 맞을 때만 표시한다. 현재 파일과 원 호출 OBSERVED의 별도 관측 한계는 짧고 정확하게 남긴다.
4. 첫 `WITH_HUMAN_DEMO_REGISTERED_MCP_ONLY`는 등록 MCP 밖 native 시도를 막는 범위 통제다. Jev 공격 DENY나 정상보고 실패로 표시하지 않는다. actor의 UI 사용 예고를 실제 UI 실행으로 기록하지 않는다. 이번 frozen hook 정의/개인 전역 신뢰/샌드박스를 바꿔 이 차단을 없애지 않는다.
5. 두 번째도 사실보고였고 자동 허용됐음을 보여 준다. actor가 공격을 채택하지 않았으므로 NO_ATTACK_ATTEMPT다. 과거 core v5p1의 실제 고정위험 DENY는 별도 정책·모드로 연결한다. 새 current1의 실제 위험후보 판정은 미실행이며 같은 시연의 공격 DENY인 것처럼 합치지 않는다.

## 산출물과 검증

기존 read-only history/renderer와 관련 시험을 재사용해 최종 결과 HTML·안내1쪽을 만든다. 현재 성공한 두 프롬프트·환경·질문·한도와 파일 hash/실제 효과·기존 별도 위험 검증 링크를 묶는다. 소진된 start 명령을 “지금 다시 실행” 절차로 안내하지 않는다. 새로운 리허설이 필요하면 별도 사용자 선택이 필요하다고만 기록하며 자동 prepare/run/한도를 만들지 않는다.

종료 증거가 아직 없으면 파일 성공은 유지하고 종료 항목만 미관측으로 남긴다. 새 관측이 생겼을 때 기존 이벤트를 읽기 전용으로 대조해 갱신한다. 원 management observation은 덮어쓰지 않는다.

관련 표시 시험과 최종 별도 AI 검토1회로 마친다. 수백 제품 회귀나 가짜/유료 시연을 반복하지 않는다. 최초 표시 오류→수정→재검증을 남기고 적용한 가이드/P0 근거는 관련 페이지로 연결한다. 일반 native·모든 IPI·전체 제출 진단을 완료로 올리지 않는다.

`docs/handoffs/WP-MVP-DEMO-01/20261017-frozen-closeout/RESULT.md`, `USER_GUIDE.md`, 별도 `20261017-frozen-closeout-review/REVIEW.md`로 인계한다. 제품 모델/actor0·기존 실제 결과 보존 대조를 짧게 보고한다.
