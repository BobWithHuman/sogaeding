# ADR-P04 등록 파일 MCP 자동 핵심

정책 `hookgw-2026-10-17-jev-v5p1`, profile `behavior_v5p1`, revision `core-auto-v5p1`다. V5 wire/질문/선택지·.90과 원 confidence 계산은 그대로다. 재사용 evaluate의 view validation/decision hook만 분리했다.

등록 mcp/read_file/write_file/enrolled-files-1에서 B 고확신 LEGITIMATE와 완전 검증된 A raw WITHIN_TASK가 있으면 B를 양의 의미 허용 근거로 ALLOW한다. A의 낮은 confidence/LOW_CONFIDENCE/thresholded UNCERTAIN은 보존한다. 고확신 A OUTSIDE 또는 B 위험은 DENY 우선, 낮은 raw OUTSIDE/명시 UNCERTAIN/낮은 B/충돌은 CONFIRM이다. 모델/입력/ref/hash 실패는 분석 실패다. native에는 새 양의 규칙을 적용하지 않는다. `decision_rule_version=jev-b-owned-positive-1`, positive_authorization_basis와 A 원 선택/thresholded scope/승격false를 기록한다.

이는 A의 독립 양의 확신 필터를 완화한 정책 변경이다. B가 잘못 고확신 LEGITIMATE를 내고 A가 약하게 동의하면 잘못 허용할 수 있다. 모델 정확도 개선이나 확신 승격을 주장하지 않는다. 같은 실제 V5 snapshot/wire/답 재합성은 정상 ALLOW·위험 DENY이며 새 모델 관측이 아니다. 실제 CLI의 .86/.70 안전한 관측은 조합만 확인한다.

현재 SPEC5 노출 API의 R-B-002는 기존 AuthAudit의 독립 SQLite·10초 bucket/24시간 집계·credential 없는 HUMAN/SERVICE/AGENT 표면과403/429 기록을 재사용한다. control API·gateway connection·private upstream signed ticket 실패를 기록한다. 제한은 최근60초 집계10회로 기존 한도를 유지하며 일반/session 감사 정리나 프로세스 재시작이 reset하지 않는다. 저장 실패는503·보호 동작0이다. TLS handshake 자체의 서버 전수 로깅/모든 운영 진단 완료를 뜻하지 않는다.

사용자 최종 수용은 USER_RUN의 한 정상 CLI→정상 종료→별도 verify-block이다. 정상은 ALLOW/OBSERVED·PDP승인0·실제 단회 효과여야 한다. CONFIRM을 승인으로 대신하지 않는다. verify-block은 동일 batch manifest/추가 한도 선택과 정상 성공·남은2요청 확인 후에만 고정 위험 후보를 실제 gateway/실제 Jev로 전송한다. actor에는 위험 후보/답안을 주입하지 않는다. 실패/미확정/UNKNOWN/소진은 중단·history만 허용하고 재시도하지 않는다.
