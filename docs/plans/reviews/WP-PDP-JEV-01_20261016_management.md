# WP-PDP-JEV-01 오프라인 인계 및 사용자 공개 읽기 검토

2026-10-16. 관리 검토. 작성자/별도 AI REVIEW와 현재 소스를 읽고 보조 검토가 최종191파일을 해시 대조했다. 모델/API 추론·제품/승인 설정 변경0이다.

## 수용 범위

최종191파일 fingerprint=2b7f8a4e7aa6dd47d1c9a30c0331ca6f79fffe8b310690b7b7434e67e8e65892, manifest=artifacts/20261016-jev-dev/final-preflight-source/manifest.json, 현재 불일치0으로 확인했다. **규칙 우선 routing, ADR-P02 슬롯/복수 출처/문맥, Jev adapter의 오프라인 구현·관련 회귀·배치 증거를 T-JEV-01 범위로 수용한다.**

작성자282 PASS, 실제 gateway+fake Jev25/25, rules-only10/10, 별도299 PASS는 서로 겹치는 기록이며 합산하지 않는다. actual Jev/한국어 정확도/임계치 보정은 NOT_RUN이다. 실제 runtime35파일 대조와 기존키·READY5건/원 OpenAI22/24 보존은 작성자/검토자의 당시 증거다. 이번 관리에서 새 전체 제품 시험을 재실행하지 않았다.

## 실제 Jev를 사용 중인지

- compose.hookgw.jev.yaml 및 -JevRules는 HOOKGW_PDP=JEV의 **규칙 전용 모드**다. TypeSafe key/policy/ledger와 사용량 한도는 설정하지 않았다.
- PUBLIC_ENROLLED_READ는 코드로 ALLOW하고 model_requests=0이다. 의미 판단이 필요한 쓰기는 JEV_NOT_AUTHORIZED로 차단한다. GPT로 fallback하지 않는다.
- 따라서 Jev adapter의 코드가 준비됐다는 것과 실제 Jev 모델이 판정했다는 것은 다르다. 현재 사용자 시험은 실제 Jev 성능 검증이 아니다.
- gpt-5.6-luna는 사용자 Codex actor 모델이다. 화면에 이 이름이 표시되는 것은 PDP backend를 뜻하지 않는다.

## 사용자 실행의 최신 증거

새 host-jev profile을 인증된 history로 읽기 전용 조회했다. 기존 GPT profile의 hookgw.ps1 history를 혼용하지 않았다.

- 사용자 session=01a143b8-cdb0-7c91-ba5a-6c6140606d18, turn=01a143b8-e771-72c2-9e3b-2010a3298d2f
- read call=exec-4c491ec6-9ccd-4099-8b43-63e9a4107cae, PUBLIC_ENROLLED_READ, RULE_ALLOW, model_requests0, decision ALLOW/state READY
- 앞선 MCP call exec-f7cff975-d347-4f52-a878-4964ba497296는 TOOL_ARGUMENTS_UNPARSED_OR_SCOPE/RULE_DENY/model0다. 정확 인자를 읽지 않아 이를 특정 경로로 단정하지 않는다.
- user 출력에서 native PROTECTED_PATH/UNSUPPORTED_NATIVE_ARGUMENTS도 확인됐다. 제품/스킬 보호 경로와 지원 subset의 통제이며 공개 notes 읽기 자체가 막힌 원인과 구별한다. 이 문제를 해결하려 보호 범위를 일괄 해제하지 않는다.
- 동일 profile에 있는 41f6f8bc… session의 OBSERVED read/미승인 write DENY는 **작성자 합성 규칙 시험**이다. 사용자 새 과업 성공으로 계산하지 않는다.

사용자 read의 실제 실행은 Codex 자체 자동 승인 검토가 거절했다. 표시 사유는 API 프로젝트에 codex-auto-review 접근 권한이 없어403으로 검토가 실패했다는 것이다. 이는 Jev 장애나 IPI 탐지 성공이 아니다. READY는 실행 성공이 아니므로 이번 사용자 과업은 미완료다.

## 다음 순서

1. **2026-10-16 사용자 동의 기록:** “이번 테스트만 직접 승인으로 진행”. 이번 테스트 CLI1회에만 reviewer=user를 명시하고 사용자가 공개 notes read1회를 직접 승인하는 좁은 launcher 보완을 배정한다. 기존 on-request/샌드박스/With Human 정책·hooks·TLS와 전역 config/auth를 유지한다. 설정 적용·실제 읽기는 아직 수행하지 않았다.
2. 기존 개발 세션에서 아래 보완을 실제 모델0회로 구현·검증하고 별도 AI 검토한다. 현재 wrapper에는 해당 옵션이 없으므로 검증 전 실행 명령을 안내하지 않는다. 이후 사용자 새 CLI의 새 read ALLOW/READY→OBSERVED와 실제 notes 결과를 확인한다. 기존 READY를 해제/재실행하거나 다른 도구·승인 우회 flag로 같은 outcome을 달성하지 않는다. 이 수동 승인은 Codex 호스트 승인만 대상으로 하며 PDP 자동 판정은 유지한다.
3. 사용자는 TypeSafe API 키를 “발급받았음”이라고 답했다. 값은 수집하지 않았고 계정/모델 접근은 미확인이다. 합성 자료/고정 질문·모델/호출·토큰·비용 상한을 정한 뒤 실제 Jev 평가를 별도 사용자 실행으로 배정한다. 키 보유를 실제 호출 동의로 해석하지 않는다. 현재 placeholder0.90/calibration12/holdout4는 정확도 근거가 아니다. 기존 OpenAI22/24를 초기화하거나 Jev 요청으로 대체 집계하지 않는다.

개발 배정: [호스트 승인 복구 지시서](../../handoffs/WP-PDP-JEV-01/HOST_REVIEW_START_PROMPT.md). 이번 공개 fixture read가 기존 actor에 작업 자료로 전달되는 범위를 제외한 추가 원문 전송·Jev enable·개발 AI 유료 호출·개인 bob MCP 삭제·CLI 업데이트는 배정하지 않는다. 일반 native/hook 실패 경계·공급망/전체 제출 진단은 미완료다. 별도 AI의 읽기 전용 범위 검토에서도 현재 launcher에 옵션이 없음을 확인했고 한 번의 CLI 인자로만 적용하도록 재확인했다.

공식 근거: [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review), [reviewer 설정](https://learn.chatgpt.com/docs/config-file/config-reference). reviewer는 승인 주체를 고르는 설정이며 샌드박스 자체를 확장하는 설정이 아니다. 관리 요구사항이 있으면 그 제약이 우선한다.
