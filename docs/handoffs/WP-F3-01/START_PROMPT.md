# 기존 개발 세션에 전달할 프롬프트

아래 내용을 C:\sogaeding을 사용하는 기존 개발 세션에 전달한다. 실제 작업은 이 문서가 사용자 메시지로 전달된 세션에서 수행한다.

```text
$with-human-dev

C:\sogaeding의 WP-F3-01을 구현해줘.
사람 개발자는 나1명이고, 이 채팅은 단일 개발/통합 세션이야.
관리 세션이 정한 docs/plans/10_f3_automatic_decision_work_pack.md를 전체 읽고
그 계약/권한/예산/시험 범위를 실행 명세로 적용해 실제 구현과 검증을 진행해줘.

제품 목표는 PDP가 사용자 요청·서버가 발급한 권한·실제 수집 출처를 판단해
정상 행동을 자동 허용하고 외부 지시가 추가한 행동을 자동 차단하는 거야.
사용자 CONFIRM은 모호한 정상 범위 후보의 예외로 남겨줘.
source_ids 표시나 기존 권한 규칙만으로 F3를 구현했다고 보고하지 마.

AGENTS.md, with-human-dev의 필요한 reference, docs/plans/09·10, ADR-M01,
docs/mvp 명세/기계 계약과 최신 실제 RESULT/REVIEW·현재 코드/diff를 대조해 착수해줘.
진행 중이거나 완료한 R-B-002 인증 감사 수정은 그대로 보존하고 한 작성자로 통합해줘.
현재 SPEC-3/정책v1을 기준선으로 고정하고 작업팩의 명시 위임에 따라
SPEC-4/정책 mvp-2026-10-14-f3-v2로 요구/API/schema/예시/런처/UI/시험을 함께 개정해줘.

세 도구와 TLS/역할 인증·원자 예약·단회 승인·댓글 예산1·UNKNOWN 보호는 재사용해줘.
POST_COMMENT의 ISSUE_SUMMARY 모드에서 본문을 사전 입력하지 않아도
같은 이슈의 정상 요약 댓글은 자동 실행되게 해줘. 외부 데이터 사용 자체는 공격이 아니야.
PDP의 정책→판정 전 출처 대조→필요한 경우 두 관점 의미 판단을 구현해줘.
judge는 도구 없는 OpenAI 분석 어댑터이며 A(사용자 기준)/B(출처 포함)를 독립 요청으로 수행하고,
schema와 실제 evidence refs를 검증한 뒤 서버가 최종결정을 내려야 해.
모델 출력이 hard DENY·세션 권한을 해제하거나 승인권을 만들 수 없어.

모델 호출을 SQLite transaction 밖에서 수행하고 immutable snapshot·단회 분석·캐시·reserve를 결합해줘.
동시 요청/분석 중 문맥 변화/timeout/refusal/잘못된 근거는 작업팩대로 안전하게 처리해줘.
fake judge 시험과 실제 judge 시험을 분리하고 모델의 미시도·오류를 차단 성공으로 세지 마.
실제 judge 최대24요청, actor Codex 최대2 episode와 timeout/token 제한을 지켜줘.
키는 지정한 로컬 secret 경로로만 주입하고 값·raw 응답·개발 정답을 로그/프롬프트에 넣지 마.

단일 작성자로 공유계약·DB전이·공통설정을 통합하고 별도 AI 검토를 받아줘.
기존 A/B·R-B-002 회귀와 F3-01~12를 실제 effects까지 검증해줘.
같은 user request/grant/tool/args에 정상 문서와 공격 문서를 바꾼 쌍,
정상 외부 데이터 활용, 자동 정상/자동 차단/예외 확인을 구별해서 보여줘.
기본 시연은 매 호출마다 사람이 승인하거나 터미널 Enter로 판정하지 않아도 되게 해줘.
UI에는 자동판정의 짧은 이유·관련 출처·실제 실행 결과를 우선 표시해줘.

docs/plans·harness/build_tasks.json·AGENTS·설치skill·원본PDF·기존원증거는 수정하지 마.
이번 명세 밖 권한/도구/상태 확장은 결정 요청으로 남기고 독립 가능한 일은 계속해줘.
C/D 전체나 새 인프라·대규모 benchmark를 선행조건으로 추가하지 마.

최종 인계: docs/handoffs/WP-F3-01/<run_id>/RESULT.md와 별도 REVIEW.md.
기준버전/변경파일, F3별 실제 PASS/FAIL/NOT_RUN, 모델/비용사용량·원증거,
정책-only와 출처/의미 판정의 구분, 실제 effects·정상과업 완료,
내가 실행할 자동 정상/차단 시연 명령·URL, 남은 MVP필수/제출전 보강을 알려줘.
```
