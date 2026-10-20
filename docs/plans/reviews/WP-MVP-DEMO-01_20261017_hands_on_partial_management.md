# 직접 Codex 체험 준비 부분 수용·hooks 신뢰 대기

2026-10-17 관리 확인. 기존 등록 파일 MCP 엔진의 실제 정상자동/고정위험 실제Jev DENY 완료 판정은 유지한다. 새 hands-on은 **PREPARED_DISABLED / NATIVE_HOOK_E2E_NOT_RUN**이며 직접 체험 검증 완료로 올리지 않는다.

## 확인한 상태

- USER_RUN/RESULT/별도 REVIEW와 기존 connector/launcher/start의 실제 코드를 대조했다. manifest `dbb7ecd4cc778f33836a0dd6c9b359782936f4063814b5a927bfe34277c04a38` 현재 일치, source64개 mismatch0이다.
- runtime hands-on-1 policy enabled=false, provider ledger없음·episode6 claim없음이다. 제안8/512000·CLI1/1800초는 미사용이며 기존29/1856000·CLI5/5와 분리된다. 관리 모델/신뢰설정/제품코드/서비스 변경0이다.
- 개발 기록의 회귀118/관련17/경계22·wrapper복원4 및 별도 검토는 코드/부분 연결 근거다. native CLI는 가짜 CODEX_HOME에서 시작·종료만 했고 UserPromptSubmit/Pre/Post·모델요청은0이다. 자동 승인 검토의 hooks 신뢰 거절과 사용자의 “신뢰 변경 없이 나머지만 완료” 선택을 확인했다.
- 세 이벤트의 실제 handler는 `tools/mvp_demo_hook.py`와 신뢰채널 `hookgw_hook.py`를 사용한다. 현재 hook SHA256은 `24603265d7e9a11303fd828aa919208aa6a4f48bae8fc21e8a6e5517c86aeed7`이다. 모델 본문을 hook실행 명령으로 해석하지 않는 경로를 읽었다. 이 확인이 사용자 신뢰 동의를 대신하지 않는다.

## 남은 조건과 실행 안내 문제

공식 OpenAI Docs의 [Hooks](https://learn.chatgpt.com/docs/hooks)는 비관리 hooks가 현재 정의에 대한 검토/신뢰 전에는 실행되지 않는다고 명시한다. 현재 설치 CLI에서의 신뢰 요구는 native fixture에서도 관측됐다. 따라서 features.hooks=true/handshake READY만으로 hooks의 실제 실행 준비를 단정할 수 없다.

현재 hands_start→기존 start는 CLI를 열기 전에 episode claim과 live 정책을 설정한다. USER_RUN은 그 뒤 /hooks에서 미신뢰면 종료하도록 해 사용자 슬롯을 보호 검증 없이 소모할 수 있다. 이를 그대로 최종 체험 안내로 수용하지 않는다. 모델/슬롯 소비 전에 신뢰 검토·유효성 확인이 가능하도록 [작업서](../../handoffs/WP-MVP-DEMO-01/HANDS_ON_TRUST_GATE_PROMPT.md)에 조건을 정리했다.

최초 검토 시 신뢰 미변경 선택을 유지하며 변경 의사를 질문했다. 이후 사용자는 관리 채팅에서 **“이 hooks만 검토·신뢰하며 진행”**으로 답했다. 동의 범위는 해당 hooks3개에 대한 격리 가짜 CODEX_HOME/가짜 키의 개발 검증, 실제 체험에서는 사용자 직접 /hooks 확인이다. sandbox 밖 로컬 코드 실행 가능성을 명시한 뒤 받은 동의다. AI의 실제 사용자 전역 신뢰 변경/다른 hooks/trust bypass로 확대하지 않는다. 다음은 허용된 무모델 native 종단 검증과 슬롯 소비 전 신뢰 gate 수리다.

자동 승인 검토가 거절한 동작은 격리 CLI에서 hooks3개를 일괄 신뢰하는 것이고, stated reason은 sandbox 밖 코드 실행과 명시 허용 부족이었다. OpenAI의 신뢰 검토 요구와 별개로 자동 승인 거절도 해제된 것으로 가정하지 않는다. 새 동의 시 정확 범위/위험을 명시한 뒤 검토받고, 재거절이면 이유를 보고한다.
