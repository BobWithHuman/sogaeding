# WP-HOOK-GW-02 단계 A 개발 지시

with-human-dev 스킬과 `docs/plans/14_hookgw_live_completion.md`의 A만 우선 수행해줘. 제품 목표는13번의 평소 Codex hooks/실제 agentgateway 자동 연결로 유지한다.

현재 `hookgw_launch.py`가 개인 provider/auth를 상속하고 관리 조회에서 ChatGPT 로그인이 확인됐다. Control judge LIVE와 actor Codex API 인증을 혼동하지 말고, 개인 전역 config/auth/로그인 상태를 변경하지 않는 명시적 호출별 API 모드를 제공해줘. API키 값은 환경으로만 전달하고 모델/인증 종류/provider/endpoint를 비밀 없이 확인할 수 있게 해줘.

모델을 호출하지 않는 preflight로 CLI·hook 설정/신뢰 필요·TLS health·LIVE_USER·키 읽기 가능 여부(값 출력 금지)·기존 예산을 확인하고 준비 실패면 모델을 시작하지 마. 실제 API 동작은 가짜 자격증명/로컬 fixture로 검증하고 실제 actor/judge 유료 호출은0으로 남겨줘. 모델은 선택값을 명시하고 더 비싼 모델로 임의 변경하지 마.

14번의 좁은 쓰기 경계를 지키고 기존 엔진·정책·키·DB/예산/원증거를 보존해줘. native 정상 편집·hook fail-open·공급망 잔여는 기록하되 이번 작은 준비의 선행조건으로 전체 C/D를 추가하지 마. 관련 회귀와 별도 AI 검토 후 내가 직접 실행할 최소 명령과 첫 정상 요청·이력 확인·중단 조건을 새 RESULT/REVIEW로 인계해줘. 계획/전역 장부/DONE은 수정하지 마.
