# 최종 별도 AI 검토

검토일: 2026-10-17. 구현자와 분리된 AI 검토다. 제품 코드 수정, 제품 모델 호출, Codex CLI 시작, 서비스 변경, 실제 키 열람, snapshot 복호화, 원 DB·원장·claim 수정은 하지 않았다.

판정: **현재 후보에서 수정이 필요한 발견 없음**. 범위는 `CORE_RISK_POST_HISTORY_REPAIR_PROMPT.md`의 프로토콜·history 수리와 별도 단회 attempt 준비다. 실제 Jev 위험 의미판정은 NOT_RUN이며, 전체 MVP 완료나 모델 정확도·일반 IPI 방어를 승인하지 않는다.

## 직접 확인한 구현

- `fixed_engine_block`의 실제 `mcp.exchange` 성공 결과를 그대로 같은 session/turn/call/tool/args의 PostToolUse `tool_response`로 전달한다. 기존 hook→Control Engine 경로에서 검증하고, 같은 call의 OBSERVED와 source 1건을 RO 조회로 확인한 뒤에만 위험 후보로 진행한다. 응답 오류·Post 누락/거절·source 미확정이면 다음 위험 write로 진행하지 않는다. 기존 제품 정책·권한·TLS·Engine·원 bundle은 변경되지 않았다.
- 의미 DENY 수용은 정확한 새 call_ref, DENY/DENIED, `SEMANTIC` routing 및 `EXTERNAL_INSTRUCTION_DEPENDENCY`/`OUTSIDE_TASK_SCOPE` 이유를 요구한다. 기존 `PRIOR_RESULT_UNOBSERVED`, `ANALYSIS_UNAVAILABLE`, 잘못된 routing은 성공으로 계산하지 않는다. 수집 실패 때 upstream 효과는 null로 남으며, close 실패는 선행 READ_POST 원인을 덮지 않는다. raw 예외 문구는 출력하지 않는다.
- `behavior_history`가 upstream만 기존 RO SQLite 수집기로 연결해 execution compose/current-source 검사를 재진입하지 않는다. frozen runtime/bundle 검증은 유지하며 현재 source drift를 별도 표시한다. 원 consumed claim/실패 result/UNKNOWN 및 새 attempt 결과를 함께 출력한다. 원장·연결·claim 생성은 없다(기존 방식의 새 로컬 history HTML 저장은 존재한다).
- 실행 전 실패 호출 6개, upstream 5개, transport/source ID 목록, 두 위험 후보 hash, 원 claim/result, 원 후속 manifest hash를 전수 대조한다. 이 대조 후 정상 session의 정확한 4개만 별도 gate에 전달한다. 정상4만 필터링해 실패기록을 건너뛰는 방식이 아니다.
- 원 총상한 4/256000과 잔여 2/128000, actor/CLI 총5 및 이미 닫힌 정상성공을 요구한다. 별도 `post-complete-1`의 독점 생성 claim을 한 번 소비하며, 기존 실패 claim을 재사용·삭제하거나 UNKNOWN을 사후 수리하지 않는다. 중복·usage 변화·source/bundle/manifest drift는 claim/전송 전 거절된다.

## 증거와 독립 확인

실제 gateway 종단 증거의 adapter 소스 `artifacts/20261017-core-risk-post/e2e.py`를 읽었다. 복제 PS5.1 wrapper에서 실제 `mvp_demo.main`→실제 `core_post_verify`→실제 `fixed_engine_block`→실제 hooks/MCP/TLS gateway/Engine/JevClient(HTTP fake)→Post/source→DENY→같은 history를 실행한다. probe 전체 성공 stub으로 대체하지 않는다. 시험용 root/ports, fixture genealogy, OFFLINE health의 명시적 adapter와 fault 주입은 별도 격리돼 있다. 실제 원장·실제 키를 fixture에 mount하지 않는다.

- 최종 성공 종단 `e2e-final-success/evidence.json`: 12/12 PASS. read OBSERVED/source1 선행, 의미 DENY, 위험쓰기0, fake usage 총4, 기존 실패 UNKNOWN/claim 보존, 같은 사용자 history 성공 및 중복전송0을 확인했다.
- Post 누락 종단 `e2e-missing-post/evidence.json`: 11/11 PASS. 최종 잘못된 Post+close 오류 `e2e-final-negative/evidence.json`: 12/12 PASS. read UNKNOWN/source0, 새 write0, fake usage2 유지, primary READ_POST 보존 및 미검증 upstream null을 확인했다.
- 필요한 최종 통합 로그: 177 PASS/55.29초, lint PASS. 로그와 실제 명령을 대조했다.
- 검토자가 별도로 만든 실제 probe 보조 반례 14/14 PASS: 상태방어 DENY·분석실패·잘못 routing, MCP result 오류, malformed content, source 누락, Post 거절, Pre 거절, transport 오류, close 오류, 주오류+close, 수집 실패. 이 double 기반 단위시험은 위 실제 TLS 종단 증거를 대신하지 않는다. 최초 보조시험의 잘못된 mock RPC 인덱스를 고친 뒤 14개를 통과했다(제품 결함 아님).
- 검토자 별도 파일 대조: before83개 중 승인 runner4개만 변경됨, 최종 source6개 hash 일치, 새 attempt의 preserved_files 전체 일치. 원·이전·새 manifest와 정확히4개 runner override의 before/after/current binding을 확인했다. `independent-binding.json`, `independent-probe.json`을 남겼다.

## 실행 준비 binding과 한계

원 manifest: `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`.

이전 후속 manifest: `47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`.

새 `post-complete-1` manifest: `5d5de664a3ed337ec65bf58d2e753321cd42c48b58f6c69f3a3dd0f4f3fbf945`.

실제 정상 자동 ALLOW/OBSERVED·쓰기1·PDP승인0은 유지된다. 원 위험 실패는 상태방어 DENY이며 의미판정 성공으로 바꾸지 않았다. 새 attempt의 실제 Jev 결과·위험 효과는 사용자 실행 전 NOT_RUN이다. 적용된 P0는 완료 통지의 정확 결합·미관측 차단·RO 이력·한도·단회 소비·민감 오류 비노출이며, 기존 가이드와 일반 native/hook fail-open/TLS negative 전체의 미완료 범위는 그대로 남는다. 개발 AI 검토는 제품 actor/Jev 유료 호출0과 별개다.

USER_RUN/RESULT 문서가 생성된 뒤 실제 고정 명령도 별도로 대조했다. 원 hash와 새 attempt hash, `post-complete-1`, ConfirmSend, 원 한도9개, actor Model/start 부재, 이전 ResumeManifest 혼합 부재, 동일 revision history 명령이 일치한다(`user-command.json`). 이전47 hash는 새 manifest 내부 binding으로 보존한다. 사용자 명령은 실행하지 않았다.
