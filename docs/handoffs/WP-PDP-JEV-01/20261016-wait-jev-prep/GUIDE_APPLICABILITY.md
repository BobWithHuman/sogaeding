# 승인 대기·Jev 준비의 가이드 적용성 변경분

T-JEV-03/04, 사용자1명·별도 AI 검토. 전체 설계20/구현49 적용성의 기준은 [직전 전행 검토](../20261016-jev-dev/GUIDE_APPLICABILITY.md)다. 이번에는 아래 실행 경로의 변경분을 재검토하며 기존 미완료를 PASS로 올리지 않는다. 원문 SHA를 대조하고 직접 추출한 [원문12페이지](../../../../artifacts/20261016-wait-jev-prep/guide-pages.json)를 코드/시험에 연결한다. PDF p.와 인쇄 p.는 G2 -6/G3 동일/G4 -2다.

| 원문 | 위험·통제 | 실제 코드 | 실제 확인 |
|---|---|---|---|
| G2 PDF126, G3 PDF406 | 승인 대기 중 TOCTOU/동시 replay. 현재 권한·동일 call·문맥 확인과 한 transaction의 단회 예약 | engine.forward/_revalidate_public_read, server.authz | 시계91초+실제 agentgateway, 동시 replay upstream총1, 인자/턴/정책/grant/출처/사용자문맥/미해결 변경 upstream0; test_wait_revalidation |
| G3 PDF509/511, G4 PDF38 | 세션/연결 소유권·수명·정확 도구/인자/공개 경로/필수근거; 기존 READY 되살림 금지 | engine._current/forward/public read parser+provenance, marker+원 action/request hash | 만료/위조/보호/범위밖·기존marker없음/의미만료·UNKNOWN 거절, 원 analyzed_at 보존 |
| G2 PDF133/135/137, G3 PDF511 | 정책403을 인증실패로 오판하거나 임의 오류 문자열/본문 유출 | trusted_rejection와 machine TLS /transport-rejection의 allowlist·nonce/token/action 결합 | 실제 gateway→고정 Control 사유/call SHA 대조; 다른 nonce/args/token UNCONFIRMED; raw secret fixture 출력0; TLS별도 |
| G3 PDF510, G4 PDF38 | TypeSafe 키/장부/역할 혼합·무단 활성화/자료 전송 | jev_eval protected ignored key/config RO·ledger RW, 기본 enabled:false, 사용자 명시 manifest+4/256000 승인 gate | fake 키만으로 Windows hidden stdin/ACL·RO/RW 준비·network none preflight, 기존OpenAI22/24불변, 실제키/모델접근 NOT_VERIFIED |
| G3 PDF415, G2 PDF146 | 실패 뒤 반복 과금·자원 미해제 | 평가전용 순차 fail-stop A→B, 기존 원장 보수예약·실패보존, timeout/with, 재실행 거절 | fake HTTP401/403/429/500/302에서 provider1/64000만, API실패 NOT_SCORED, 실제모델0 |

설계20 변경 관련은 권한·중요자원/암호키/전송·예외/오류·세션·입력/상태 검증이다. 나머지 항목은 위 전행 검토의 범위/잔여 상태를 유지한다. 구현49 중 W-03/12/15/18~20/22~23/28/33~40/43~48은 현재 공개 읽기·진단·평가 helper 경로를 다시 수동/동적으로 확인한다. SQL은 바인딩과 고정 query, JSON은 고정 schema/필드·길이/수량, 외부 URL은 고정 HTTPS·TLS검증·redirect/proxy/retry0을 유지한다. 새 web/XML/LDAP/파일업로드/비밀번호/암호 알고리즘/네이티브 메모리 API는 도입하지 않았다. 이것은 관련없음의 전역 확정이나 49행 모두 PASS 판정이 아니다.

R1 PDF14/G1 PDF35~38·47의 전주기/빌드/공급망·비밀보호 원칙은 기존 적용성을 유지한다. 새 패키지/다운로드/이미지0, 기존 고정 agentgateway digest 및 기존 개발 image ID를 사용한다. 공급망 잔여·native 일반개발/hook 사망 fail-open·전체 TLS negative/키수명·TypeSafe 실제 API 호환성/의미정확도는 미완료다. 공식 대회 조치율·점수를 추정하지 않는다.
