# 직접 CLI와 안전 진단의 구조적 예방

기존 세 역할/TLS/PDP/hard guard/엄격 근거/원자 reserve/단회 승인/UNKNOWN을 유지한다. 새 사용자 metadata API는 RequestGuard HUMAN/HTTPS/Origin/Host/body/schema를 통과한다. cli-binding은 입력 agent token을 resolve한 세션과 path 세션을 대조하고 token/원문을 응답에 넣지 않는다. diagnostics는 암호화 result의 enum/view만 읽고 raw 모델 응답/프롬프트/자격증명/SDK 오류 메시지를 저장하지 않는다. 과거 미기록은 DETAIL_NOT_RECORDED이다.

출처/인용 검증 실패는 ANALYSIS_UNAVAILABLE DENY를 유지하며 approval/reserve 효과0으로 시험한다. 악성 ref를 유효화하거나 자동 retry하지 않는다. 입력 hint는 텍스트의 실제 위치만 제공하고 정답/권한은 제공하지 않는다. 짧은 줄 입력 증폭을 source8/전체32/직렬화128KiB로 제한하며 원문을 조용히 잘라 허용하지 않는다. PROMPT version과 snapshot/cache/reserve 결합도 유지한다.

CLI는 TEMP workspace/별도 CODEX_HOME/OS env allowlist/API env+agent only/app CA·고정 endpoint/provider/template를 사용한다. 사용자 생성 세션 연결과 사용자 직접 TUI 시작을 분리하고 최초 stdin을 자동 주입하지 않는다. 사용량 ledger는 기존24/2를 유지한다. 중단 실패도 enum/bool/PID로 기록하여 성공처럼 표시하지 않는다. 실제 actor 토큰hardcap/daemon 전체 lifetime은 미검증으로 남긴다.

요구→통제→검증: 직접입력/credentials 분리→manual_cli actor_environment/bind→fake env/binding+Windows preflight; 안전오류→AnalysisFailure/encrypted result→schema/source/quote/A-B/lease/API spy; 의미 공격 vs 장애→semanticOutcomeMatches/UI→JS+실제Firefox offline DOM; 원자 실행보존→기존 reserve/f3 bound→제품68 및 A peer8 회귀. paid/TUI0은 실제 의미 정확도의 증거가 아니다.
