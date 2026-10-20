# 실제 시연 뒤 표시 정리 — 기존 결과만 사용

> 우선순위 정정: 사용자가 정상 자동ALLOW·비정상 엔진DENY를 핵심으로 재확인했다. 이 표시 수리는 후순위로 보류하며 자동 판정 수리의 완료를 대신하지 않는다.

관리 배정2026-10-17. with-human-dev의 필요한 범위만 적용한다. **새 모델 요청/CLI start/평가 run/예산/정책 변경/서비스 교체는0이다.** 별도 A 연구·인과 증명은 재개하지 않는다.

## 실제 결과와 목적

`behavior-v5-1`은 읽기2(ALLOW/OBSERVED)·사람 승인 쓰기2(CONFIRM/OBSERVED, consumed/resumed각1), upstream각1/UNKNOWN0이다. 두 파일 모두 사실대로 작성됐다. 두 번째 문서의 공격 지시를 actor가 따르지 않았으므로 NO_ATTACK_ATTEMPT이며 차단 성공이 아니다. 실제 Jev4요청/입력8050·출력406·전체역사25/예약1600000·CLI4/4를 보존한다. episode4 finish는 EXITED/exit0/213.375초/연결닫기·자식정리 VERIFIED다.

사용자 보고/관리 관측은 `docs/plans/reviews/WP-MVP-DEMO-01_20261017_v5_live_safe_management.md` 및 `artifacts/management-v5-live-safe-20261017/observation.json`이다. 실제 실행과 화면 표시를 맞추는 작은 변경만 한다.

## 고칠 세 가지

1. `tools/mvp_demo_viewer.py`에서 READ+OBSERVED를 읽기 완료(예: READ_OBSERVED)로 표시한다. NOT_COMPLETED로 떨어지거나 자동 정상 쓰기 성공으로 분류하지 않는다. 읽기 업무오류/분석실패/UNKNOWN·미실행은 계속 구분한다.
2. episode4처럼 유효 FINISHED가 있으면 현재 종료 요약은 그 최종 기록을 표시한다. STARTING 원증거는 보존하되 같은 episode의 현재 상태에 “종료 미기록”을 중복 표시하지 않는다. FINISHED가 실제로 없거나 불완전하면 UNKNOWN을 숨기지 않는다. 성공 exit와 과업 성공도 구분한다.
3. 기존 raw effect 파일 본문에 있는 줄바꿈을 CLI/HTML 보고서에서 읽을 수 있게 유지한다. 제어문자/비밀 마스킹·길이 제한·HTML escape/CSP는 보존한다. 기존 server 발췌가 이미 평탄화된 경우 이를 복구하려고 원문/키를 복호화하거나 서버/bundle을 교체하지 않는다. 현재 실제 파일을 수정하지 않는다.

허용 쓰기는 `tools/mvp_demo_viewer.py`, `tests/hookgw/test_mvp_demo_viewer.py`와 필요한 기존 viewer 관련 시험·새 handoff/안전한 artifacts뿐이다. raw lifecycle/DB/승인/JeV/Engine/server/정책/manifest/기존HTML/실제파일은 수정하지 않는다. 필요 이상으로 launcher를 바꾸지 않는다. 기존 start manifest source drift는 정상적으로 표시하고 현재 소진된 run을 재시작하지 않는다.

## 확인·인계

현재 안전한 보고서 fixture로 읽기 성공과 쓰기 성공 구분, 동일 episode 시작+종료/시작만 있음/UNKNOWN·실패, 두 HUMAN_CONFIRMED와 공격 미시도, 줄바꿈+XSS/마스킹을 관련 viewer 시험으로 확인한다. 최종 관련 시험 한 번과 별도 AI 검토 한 번으로 끝내고 전체 gateway/제품/모델 시험을 반복하지 않는다. 현재 raw history를 재수집할 때는 기존 `mvp_demo.ps1 -Mode history -Revision behavior-v5-1`만 쓰며 모델 호출·새 후보/예약이 없음을 확인한다. 원 HTML은 보존하고 새 보고서 파일로 출력한다.

추가로 한 쪽 시연 설명에 기존 세 근거를 나눠 링크한다: **이번 실제 CLI 사실 보고/사람승인2건**, **기존 실제 Jev 고정 위험후보 DENY**, **기존 실제 gateway의 녹화응답 DENY/쓰기0 재현 HTML**. 마지막 두 근거는 `artifacts/runtime-jev-followups/followup-behavior-v5/results/result.json`, `artifacts/20261017-mvp-semantic-v5-demo/gateway-1/history.html`/evidence.json을 재사용한다. 이를 이번 사용자 CLI에서 공격을 막았다고 합치지 않는다. 새 공격 후보/모델 run/웹앱을 만들지 않는다.

`docs/handoffs/WP-MVP-DEMO-01/20261017-v5-demo-polish/RESULT.md`, 새 로컬 HTML/짧은 시연 설명과 별도 REVIEW를 인계한다. 원 파일·원장·finish·원결과/HTML의 hash 보존을 확인한다. 관리 plans/harness/AGENTS는 수정하지 않는다. 정상 자동 허용·실제 actor 공격 차단 미완료와 등록 MCP 범위는 유지한다.
