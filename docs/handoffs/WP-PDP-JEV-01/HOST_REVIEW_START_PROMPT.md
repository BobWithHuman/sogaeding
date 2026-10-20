# 호스트 자동 검토403 복구 준비

후속 상태(2026-10-16): 이 배정의 옵션/오프라인 준비는193파일 범위로 수용했다. 사용자 승인창 이후 새 read는 FORWARD_SNAPSHOT_STALE로 실패했다. 다음 작업은 [승인 대기 수리·Jev 준비](WAIT_AND_JEV_PREP_START_PROMPT.md)다. 아래는 당시 명시 승인·구현 배정 기록이며 실제 읽기 성공을 뜻하지 않는다.

상태: **AUTHORIZED_OFFLINE_IMPLEMENTATION** — 2026-10-16 사용자가 “이번 테스트만 직접 승인으로 진행”이라고 명시했다. 아래 좁은 launcher 보완을 개발 세션에 배정한다. 구현·오프라인 검증·별도 AI 검토 후 사용자가 새 CLI 한 번에서 공개 notes 읽기1회를 직접 요청·승인한다. 현재 옵션은 아직 구현되지 않았으며 이 기록 자체가 설정을 바꾸거나 도구를 실행하지 않는다.

같은 답변에서 TypeSafe API 키를 발급받았다고 밝혔다. 키 값은 수집하지 않았고 계정/모델 접근은 미확인이다. 이는 실제 Jev 호출·자료 전송·예산 승인으로 해석하지 않는다. 개발 세션의 실제 OpenAI/TypeSafe 호출은0회로 유지한다.

문제: -JevRules의 공개 notes 읽기는 제품에서 model0/RULE_ALLOW/READY지만 Codex 자체 auto-review가 codex-auto-review 접근 불가403으로 거절했다. 반복 read나 Jev enable로 해결되지 않는다. 현재 wrapper는 API 모드에서 임의 -c 등 추가 인자를 거절하므로 사용자에게 지원하지 않는 override 명령을 안내하지 않는다.

제안 변경은 **호출1회에만 적용되는 opt-in 수동 reviewer**다. 개발 세션은 with-human-dev/최신 AGENTS 및 관리 검토를 읽고 scripts/hookgw_connect.ps1, tools/hookgw_launch.py/preflight.py, 필요한 tests/hookgw와 현재 사용 설명만 좁게 보완한다. 정책/DB/원증거/키/개인 설정·인증·신뢰는 보존한다.

1. wrapper의 이번 실행에만 쓸 단일 --manual-review 옵션을 명시 지원하는 방안을 구현한다. 이는 아직 존재하지 않는 제안 옵션이다. -Api/-JevRules에만 허용하고 다른 임의 -c/profile/sandbox/security override 거절은 유지한다. 여러 실행에 영구 상속되거나 개인 config를 쓰지 않는다.
2. 해당 opt-in은 설치 CLI에서 실제 지원하는 approvals_reviewer=user를 적용한다. on-request 및 기존 샌드박스/보호 경로·hooks·MCP 권한/TLS를 유지한다. never/yolo/full-access/자동 허용/permissionDecision=allow로 검토를 우회하지 않는다. managed requirements에 어긋나면 실패하고 이유만 보고한다.
3. 무모델 preflight에 actor 모델, 제품 RULES_ONLY/model0, Codex reviewer/승인 경로를 구분해 표시한다. 키 존재·MCP 준비가 host reviewer 모델 접근까지 확인한 것처럼 ready를 설명하지 않는다. 정확한 사용자 실행 명령은 구현·검증 후에만 제시한다.
4. fake key/로컬 actor fixture·격리 config로 호출별 설정과 전역 config/auth hash 불변, 제약 우선, 종료 후 기본 설정 보존을 검증한다. 실제 OpenAI/Jev/actor 호출0이다. 설정 지원/권한 실패를 제품 공격 차단으로 집계하지 않는다.
5. 별도 AI 검토 후 사용자가 새 CLI에서 fixture read1회만 직접 요청하고 호스트 승인창에서 해당 한 건을 승인하는 절차를 인계한다. 이 호스트 승인은 PDP의 자동 판정을 대신하는 제품 UX가 아니라 현재 API 계정의 reviewer 접근 문제를 분리하는 제한된 시험 경로다. 성공은 실제 host-jev read의 ALLOW→OBSERVED와 notes 결과로 확인한다.

사용자가 승인한 정확 행동: 이번 테스트 CLI 한 번에 한정한 호스트 수동 reviewer와 fixtures/hookgw/notes.txt 공개 합성자료 읽기1회. 쓰기·임의 명령·외부 사이트 접근·TypeSafe 실평가는 포함하지 않는다. 해당 파일 내용이 기존 actor GPT 요청의 작업 자료가 될 수 있다는 설명을 받고 동의했다. 실패한 자동 검토 대신 사용자가 해당 도구 요청의 승인 책임을 맡는다. 이전 READY 호출은 해제하거나 재실행하지 않고 새 CLI의 새 호출을 사용한다.

native skill 보호 경로/미지원 인자 거절과 개인 bob-agentgateway4400 경고는 별도다. 이를 명분으로 정책/전역 MCP를 수정하지 않는다. 기존 READY/UNKNOWN을 삭제·해제하지 않는다. TypeSafe 실제키·policy/원장/한도 설정과 모델 성능 평가는 후속 별도 작업이다.

계획/장부/전역 DONE은 수정하지 않고 docs/handoffs/WP-PDP-JEV-01/<새run>/RESULT.md와 별도 REVIEW.md로 인계한다.
