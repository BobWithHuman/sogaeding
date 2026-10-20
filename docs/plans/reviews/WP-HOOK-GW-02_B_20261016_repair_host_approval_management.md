# WP-HOOK-GW-02 B 보완 및 후속 사용자 실행 관리 검토

2026-10-16. 현재 제품/개인 설정/승인 정책을 변경하지 않고 인계와 로컬 이력·사용량을 읽었다. 관리 AI 모델 호출0. API 키/개인 transcript는 수집하지 않았다.

## 좁은 보완 수용

작성자 20261016-span-repair RESULT와 별도 REVIEW 및 최종174파일 manifest를 대조했다. 읽기 전용 보조 검토가 현재174개 파일의 해시 일치/불일치0을 확인했다. fingerprint=50a779690fba19de753a7960778502256000cff8ccc8d2989f4dc23882d2a0f7.

서버 생성 span ID와 정확 ref 복원/양뷰 각각 검증, durable 분석 장애 중단, 무모델 stdio initialize/initialized/tools-list/임시 연결 정리를 **T-HG-04 오프라인 범위로 수용**한다. 기록된 회귀160 및 실제 gateway25는 scripted/오프라인 증거이며 독립된 의미 정확도 수치로 합산하지 않는다. 현재 모델 없는 검사도 임시 연결 생성/정리를 포함하므로 순수 무변경 조회라고 표현하지 않는다. 기존18/24 보존은 작성자 당시 기록이고 현재 값은 아래22/24다.

## 최신 사용자 실행: 아직 정상 작업 미완료

현재 인증된 history에 새 MCP read 후보2건이 있다.

- session 01a14373-12e3-7383-a3cd-b38180106a96 / call exec-c36aac3e-0f44-45f0-9195-8ddddc9b8871
- session 01a14374-1066-7873-906f-5e255360d46a / call exec-36f5c5b1-0148-4421-96d3-d8cac0c53c22

두 후보 모두 decision=ALLOW, state=READY, view_checks A/B=VALID, hookgw-exact-spans-1 / hookgw-span-ab-1이다. 이전 QUOTE_MISMATCH 재발로 집계하지 않는다. **READY는 실행/효과 성공이 아니다.** 사용자 출력의 실제 read 실행은 Codex 자체 자동 승인 검토가 거절했다. 동일 세션의 미관측 예약을 삭제·UNKNOWN 해제·자동 쓰기 재시도로 우회하지 않는다.

judge DB를 mode=ro 조회한 현재 사용량은 **22/24·남은2**, A/B 각각11 COMPLETED다. 새두 후보가4요청을 썼으며 API COMPLETED/유효근거/정상실행을 구분한다. actor 및 Codex 자체 reviewer 비용은 이 ledger 밖이고 미집계다. 추가 유료 호출·예산 초기화/증액은 하지 않았다.

## 서로 다른 실패 계층

1. bob-agentgateway의 http://localhost:4400/mcp 초기화 실패: 사용자 출력으로 서버명이 식별됐다. 개인 config의 해당 MCP가 활성화되고 같은 URL인 것을 필요한 필드만 확인했다. 제품의 with_human/HTTPS8040과 별개다. 전역 설정 삭제/비활성화는 하지 않는다.
2. WITH_HUMAN_ADAPTER_UNAVAILABLE_OR_SCOPE_REJECTED 1회: hook main의 포괄 예외 응답이다. 필드/환경/작업경로/native 범위/통신 등 어느 단계인지는 미확정이다. 스킬의 보호 경로 접근일 가능성은 가설이다. 원 인자/개인 transcript를 수집하지 않고 향후 고정 stage/code 진단으로 구분한다.
3. with_human.read_file의 Codex 자동 승인 검토 거절: 표시된 사유는 API 프로젝트의 codex-auto-review 접근 불가403이다. 개인 config의 approvals_reviewer=auto_review, approval_policy=on-request를 읽기 확인했다. 이는 제품 DevelopmentJudge의 판정이 아니다. hook ALLOW는 빈 응답으로 Codex 자체 승인 정책을 보존한다. 관리 검토 중 reviewer/승인/샌드박스 우회나 CLI 업데이트를 수행하지 않았다. 변경이 필요하면 구체 행동/영향을 설명하고 사용자 승인과 관리 요구사항을 확인한다.

## PDP 모델에 대한 사용자 추가 방향

사용자는 PDP의 GPT A/B에 문제를 제기한 뒤 **생성 LLM 대신 TypeSafe Jev 같은 판정 모델**을 원한다고 명확히 했다. 원 기획서 P1 PDF4는 정책→출처 대조→미확정일 때만 경량 모델 두 관측을 명시한다. 현재 안전한 읽기까지 A/B를 수행하는 구현에는 저비용 단계 복원이 필요하다. AI 완전 제거 지시로 해석하지 않는다.

[15번 계획](../15_jev_pdp_transition.md)에 따라 Jev 공식 문서 검토와 코드가 소유하는3단계 판정/교체 가능한 adapter를 다음 준비 범위로 둔다. Jev의 실제 계정 접근·키·성능·개인자료 전송·유료 호출을 승인받은 것으로 해석하지 않는다. Codex 자체 자동 검토403도 이 교체로 해결되지 않는다. 기존 증거/키/DB/22요청 및 native 실패 경계·공급망 미완료를 유지한다.

공식 자료: [Codex Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review), [Codex 설정](https://learn.chatgpt.com/docs/config-file/config-reference), [Jev 소개](https://docs.typesafe.ai/introduction), [Jev1.13 한계](https://docs.typesafe.ai/model-jaggedness/jev-1.13). 실제 설정 조회에서는 비밀/전체 환경을 출력하지 않았다.
