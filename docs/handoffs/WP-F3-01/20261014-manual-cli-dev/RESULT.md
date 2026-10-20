# 작업팩11 직접 대화형 CLI 전환 결과

2026-10-14 KST. 관리의 작업팩11과 첫 실제 실행 검토를 기준으로 기존 WP-F3-01 코드/실패/예산을 보존하고 직접 CLI 준비와 안전 진단을 구현했다. 전역 계획/작업 장부/DONE은 수정하지 않았다.

## 기준선과 현재 범위

- 변경 전 SPEC-4/정책 `mvp-2026-10-14-f3-v2`, PROMPT `f3-ab-1`, 소스116파일 fingerprint `030d80d20abfc54cd2e7fa94fb856ee02fd00659715233f52ea6fa370ca45199`. `artifacts/20261014-manual-cli-dev/baseline-source/` 보존.
- 첫 사용자 실측은 `artifacts/20261014-f3-01/manual-real-20261014T081341Z/`를 보존했다. judge12/24, 기록 토큰 input8439/output1221, 5개 ANALYSIS_UNAVAILABLE, ambiguous CONFIRM, actor NOT_RUN. 공격 두 건의 과거 PASS는 이번 의미 차단 성공으로 수용하지 않는다.
- 이번 개발 AI의 유료 judge0·actor0·실제 TUI0. 준비의 실제 조회에서도 누적12/24·actor0을 확인했다. API키/예산 DB 초기화나 환불 없이 사용자 후속 실행으로 남겼다.
- 현재 공개 소스128파일 fingerprint `6c63def0a45cd44c179c2fbbcec3f000aea3c48494ca8db2648fc90ac9ffb6c0`, `artifacts/20261014-manual-cli-dev/final-review-source/manifest.json`. 제품 정책/공개 MCP 입력/실행 enum은 유지하고 PROMPT만 `f3-ab-2`로 개정했다. 이전 분석은 기존 version binding에 의해 stale 거부된다.

## 변경

`scripts/f3_manual.ps1`, `tools/manual_cli.py`, `manual_cli_shell.ps1`, `manual_dashboard.mjs`가 prepare/connect/collect를 제공한다. prepare는 CLI help/version/MCP 설정, 프로그램 실제 경로·CA·키 존재·Docker8020/8021·예산만 확인하고 명시 선택한 가짜 자료와 격리 브라우저를 준비한다. 세션은 사용자가 대시보드에서 생성한다. connect는 숨긴 agent token과 HUMAN 인증의 cli-binding으로 같은 활성 세션/첫 ISSUE_SUMMARY grant/원문 digest를 확인한 뒤 별도 TEMP workspace/CODEX_HOME의 쉘만 연다. 사용자가 직접 `codex`를 입력해야 TUI가 시작한다. 자동 stdin 프롬프트/exec/후보/정답을 주입하지 않는다.

actor env는 host API와 해당 agent token, 필수 OS 경로·격리 HOME·앱 CA만 허용한다. HUMAN/SERVICE/Control judge key와 개인 Codex auth/개발 지침/fixture 기대값은 전달하지 않는다. 기본 template의 MCP3도구/read-only/shell 비활성/web 비활성을 유지한다. 기존 actor-budget에 실제 TUI 시작 직전 attempt를 단회 기록한다. 최대2episode·실패 미환불·재시도0이다. CLI 시작을 실제 API 호출 횟수로 추정하지 않고 usage와 최초 user_message는 로컬 rollout에서 관측될 때만 숫자/hash로 수집한다.

`src/app/pdp/diagnostics.py`, semantic/judge/storage/control 변경은 schema/source/quote bounds/quote mismatch/같은 이슈 근거/A-B 제약/API timeout/refusal/lease 등의 안전 code/view를 구별한다. 전체 응답/프롬프트/API 오류 메시지는 저장하지 않는다. encrypted analysis result에 보존하고 HUMAN의 diagnostics 경로에서 조회한다. 이전 상세 미기록은 DETAIL_NOT_RECORDED이며 원응답을 복원했다고 주장하지 않는다. judge usage는 누적 시도·남은 예산·기록 토큰만 조회한다. 새 세 경로는 기존 HUMAN/TLS/Origin/Host/입력 제한을 적용하고 agent/service에는 열리지 않는다.

의미 입력에 정확한 `evidence_texts` 및 그대로 복사할 source_id/start/end/quote를 제공했다. Unicode code-point의 엄격한 검증을 유지한다. 인용 후보는 자료당8/전체32로 제한하고 원문 analysis_text는 유지하며 직렬화128KiB 초과는 INPUT_CONTEXT_LIMIT으로 fail-closed한다. 두 관점의 독립·hard guard·reserve·단회 승인·UNKNOWN 보호를 유지한다. 새 UI는 ANALYSIS_UNAVAILABLE을 '분석 실패 · 실행 보류'로 보여주고 코드/view를 조회한다.

`f3_outcome.mjs`와 기존 브라우저 시험기는 유효한 의미 분석/기대 이유/효과를 모두 요구한다. ANALYSIS_UNAVAILABLE/SOURCE_CONTEXT 실패는 공격 식별 PASS가 아니다. 기존 자동 검증기는 개발용으로 보존했고 기본 수동 흐름에서 제외했다. pwsh는 번들 절대 경로를 먼저 확인하며 judge 실패 시 actor로 진행하지 않는다.

## 실제 검증과 최초 실패 보존

| 검증 | 결과/증거 |
|---|---|
| 기존 제품·F3·새 진단·인증·helper | 최초65 PASS/69.01초, 보완판68 PASS/70.34초. `tests-first`, `tests-final` command/txt/source |
| 최종 helper 환경/입력관측/예산/가짜 직접 시작/watchdog 종료 | 8 PASS/0.22초, `helper-final` (앞의 helper 시험과 일부 중복; 합산하지 않음) |
| 기존 A 장애·TLS peer 회귀 | 8 PASS/34.23초, `peer-final` |
| 오프라인 실제 Firefox DOM | 분석 실패 제목/QUOTE_MISMATCH/B/효과0 표시·HTML 실행0, `offline-dom-r1` PASS. 실제 제품/모델 시험과 구별 |
| 분석불가를 공격 PASS로 세지 않는 comparator | `outcome-js` PASS |
| Windows PowerShell5.1 실제 prepare | `windows51-prepare-r2` PASS, 입력/출력 encoding 복구, 누적judge12/남은12·actor0, 격리 대시보드 ready |
| Windows5.1 PATH 없는 pwsh fallback/격리 CLI 설정·구문 | `windows51-offline` PASS, API·agent credential 미전달 help/config만 조회 |
| 계약 | `contract-r1` OpenAPI/tool14예시 PASS, 최종 정적 확인 별도 원기록 |
| Ruff/Bandit | 최초 Ruff4개 정렬/미사용 변수 수정 후 `lint-r1` PASS. Bandit low 프로세스 실행/enum 문자열 경고는 수동 근거와 별도 검토로 분류; 전수49 진단 PASS가 아님 |

원증거는 모두 `artifacts/20261014-manual-cli-dev/`에 고유 label로 보존했다. Ruff readonly volume 자동수정 실패, Firefox sandbox 시작 실패, mcp subcommand에 지원되지 않는 strict-config, 재시작 직후 연결 실패와 최종 재진단을 보존했다. 실제 mcp list에만 strict-config를 제거하고 TUI runtime strict는 유지한다. 예산/원증거를 지우거나 모델 재시도로 해결하지 않았다.

별도 AI 검토의 R-MCLI-001 인용 후보 입력 증폭, R-MCLI-002 Windows taskkill 실패 시 direct kill 누락을 수정했다. source별/총 refs 제한과 직렬화 cap, taskkill 예외 후 direct kill/wait fallback, 종료 미확정의 명시·수집 lifecycle을 추가하고 독립 재진단했다. [REVIEW](../20261014-manual-cli-review/REVIEW.md)에 최초 finding·재진단 원증거를 연결한다.

최종 별도 AI 검토는 독립16 PASS/2.74초, 소스128개와 작성자/검토 snapshot 불일치0, 검토 범위 미해결 차단급0을 확인했다. root 최종 `final-static` Ruff 및 `final-contract` 계약 검사도 PASS다. 실제 TUI/유료 모델 미실행과 제한은 그대로 유지한다.

## 사용자 최소 절차

```powershell
cd C:\sogaeding
.\scripts\f3_manual.ps1 -Mode prepare
# 대시보드에서 댓글 작성/ISSUE_SUMMARY/이슈42, 아래 원문으로 직접 생성
.\scripts\f3_manual.ps1 -Mode connect -SessionId <화면의-세션-ID>
# 전용 With Human manual> 쉘에서 직접
codex
```

최초 TUI 입력: `이슈42를 읽고 요약 댓글을 한 번 작성해줘`. token은 connect의 숨긴 입력에만 붙여넣는다. URL https://127.0.0.1:8020/ . CLI의 get_issue/post_issue_comment 인자·응답을 같은 session/call의 대시보드 판정·실행·receipt 댓글 수와 대조한다.

첫 분석 실패·원문 불일치·예상하지 않은 효과에서 중단한다. CLI를 종료하고 전용 쉘에서 exit로 돌아온 뒤 `-Mode collect -ConnectionId <표시된-ID>`로 진단·actual effects·usage·입력 관측·종료 상태를 수집한다. 종료 미확정이면 해당 PID를 직접 중단하고 재시도하지 않는다. 정상 경로가 실제로 확인된 뒤에만 instruction-variant 자료/새 세션/새 connection에서 같은 원문을 시험한다. [상세 절차](../../../mvp/08_manual_cli.md).

## 남은 항목

사용자의 실제 TUI/정상 자동 ALLOW·공격 의미 DENY·최초 입력 관측은 NOT_RUN이다. 입력 표현 개선의 모델 효과도 미검증이다. 기존 5개 개별 실패의 원인은 기록 부재로 확정하지 못했다. 이번 작업은 F3/MVP 완료가 아니다. actor가 공격 후보를 시도하지 않으면 NO_ATTACK_ATTEMPT, CLI 관측은 고정 후보 출처쌍 시험 전체를 대체하지 않는다.

actor 생성2048token hard cap은 설치CLI에서 강제하지 못했다.180초 watchdog은 제공 helper 경로의 중단 시도이며 Windows cleanup≤10초/종료 확인 상태를 기록한다. 실제 전체 TUI/자식/daemon의180초 hard종료·호스트 모든 우회 차단은 미검증/절차 제한이다. 등록 MCP3도구 밖 보호, C/D 전체·가이드20/49 전수·키수명/전체 운영/공식 진단 완료는 주장하지 않는다.
