# Hook/gateway 구현 인계 관리 판정

2026-10-16. 관리 세션은 RESULT/REVIEW/설정·코드·공급망 기록과 별도 읽기 검토를 확인했다. 제품·컨테이너·유료 모델은 실행하지 않았다. `docsync-final-source/manifest.json`163파일을 현재 파일과 SHA256 대조해 불일치0, fingerprint `c7f48e7c27bf5a54c36094262ac2b084d59c076dcffcdb37879789798a3e6f48`다.

## 수용

실제 Windows Codex hooks·실제 agentgateway·PDP·파일 MCP의 **자동 연결 및 모델 없는 집행 검증 범위**를 수용한다. 사용자 turn/후속turn·인자/출처 결합·정상 실제 파일 효과·위험 후보의 실행 전 DENY/금지 RPC0·파일0 근거가 있다. 실제 인가403·upstream503/UNKNOWN·CA/hostname 거부 근거도 있다. 시험41개 및 독립 검토 결과를 실제 의미 모델 정확도로 해석하지 않는다. 전체 MVP와 자유 개발 지원은 미완료다.

## 실제 남은 범위

- 현재 성공은 scripted actor/FixtureJudge다. 실제 사용자 TUI·초기 hook 신뢰·실제 판정 모델은 NOT_RUN이다.
- native callback crash/timeout/malformed에서 도구 실행이 계속되는 한계가 실측됐다. 실제 fail-open probe는 view_image 경로이며 위험 쓰기 성공까지 확대하지 않는다. 살아 있는 adapter가 PDP 오류를 명시적 deny로 바꾸는 것과 callback 자체 사망을 구분한다. MCP는 gateway가 별도로 집행한다.
- 정상 native apply_patch/일반 개발 shell은 미수용이다. 개인 CLI read-only 설정과 극히 좁은 shell 문법 지원이 원인이다. MCP 파일 쓰기를 정상 native 개발 성공이라고 보고하지 않는다.
- 새 이미지 rustls 등 권고 매칭, feature/binary 도달성·patched image·최종 이미지 진단이 남는다. source lock OSV 매칭/Scout 로그인 실패를 SCA PASS로 표시하지 않는다. 제한된 합성/로컬 진단과 배포 수용을 구별한다.

## 추가로 발견한 API 실행 조건

`hookgw_launch.py`는 hook/MCP 설정만 덧붙이고 개인 provider/model/auth를 그대로 쓴다. 현재 선택된 비밀 제외 설정은 model gpt-6.1-sol, provider 기본openai이며, 설치 CLI의 `login status`를 원출력 비공개로 분류한 결과 CHATGPT였다. 이 검사는 모델 호출0·자격증명 값 출력0이다. 따라서 사용자에게 제시한 `codex` 명령이 요청한 API 인증을 보장하지 않는다. Control의 LIVE judge와 actor Codex의 인증을 별도로 확인해야 한다.

개인 로그인/logout을 바꾸지 않는 호출별 API provider/키 환경 연결과 무모델 preflight를 먼저 추가한다. 이후 사용자 직접 정상 MCP LIVE1건, 성공 시 공격 입력1건을 진행한다. 자유 개발/native 집행 보완과 실제 노출 의존성 확인은 별도 필수 후속이며 이번 작은 API 준비의 선행조건으로 전체 C/D를 추가하지 않는다.

다음 배정은 [14번](../14_hookgw_live_completion.md) WP-HOOK-GW-02의 A다. 기존 runtime/예산/원증거는 보존하고 관리 세션은 유료 호출을 시작하지 않는다.
