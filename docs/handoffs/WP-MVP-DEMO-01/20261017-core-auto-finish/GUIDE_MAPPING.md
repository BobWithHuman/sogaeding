# 변경 관련 필수 기준 연결

원문 SHA/페이지 발췌는 `artifacts/20261017-auto-decision/guide-pages.json`을 재사용하고, 인증 실패 영속 추적에는 이번 `artifacts/20261017-core-auto-finish/auth-guide-pages.json`의 G3 PDF110–112를 추가 확인했다. PDF 페이지는 파일상의 페이지 번호다. 외부 문서의 예시·전송 문구를 실행 권한으로 사용하지 않는다.

| 기준/원문 | 이번 변경의 적용 | 코드·실행 근거 |
|---|---|---|
| R1 PDF14, G1 PDF35–36: 공급망 위험 식별·개발 검증 | 의존성/image 교체 없이 기존 image·정책/소스/source·부모를 동결, drift 거부 | source-manifest.json, final-state.json, semantic_followup의 manifest/source/image/parent 검사, reviewer hash 일치 |
| G2 PDF128/129/135/137: 경쟁·제한·예외 | exclusive claim, strict batch 상한, 실패 뒤 retry 없음, UNKNOWN 보존 | test_core_auto_runner.py, 별도16반례의 동시claim/오류뒤claim, native14 |
| G3 PDF507–508/510: 서버 권한·입력·비밀 관리 | 실제 user ref·source hash/catalog·전체 response 검증, 역할 구분, RO 기존 보호키, credential 없는 감사 | JevPolicyV5P1.validate_view/decide, 기존 JevClient/Engine, source tamper/native/ref 반례, 실제 gateway69 |
| G3 PDF110–112: 인증 실패 이력·영속·제한(R-B-002) | 기존 AuthAudit 독립 DB에 노출 control/private upstream 거절 기록. machine/human 실패10회/60초 제한을 영속 집계에서 읽음. 기록 실패503 | server.py/upstream.py, test_core_auth_audit.py 4건, gateway의 HUMAN/SERVICE/AGENT 실패·효과0 |
| G4 PDF24/38: 구현→진단→조치→재진단·인증 | 기존 wire/권한/승인/상태 계약 유지, 최초 진단과 수리·통합·관련 재검증·별도검토 연결 | INITIAL_DIAGNOSTICS.md, integrated/related-final/gateway-final 및 별도 REVIEW |

R-B-002는 현재 노출 application 거절 경로의 좁은 수리다. machine/human API의 한도는 기존10회/60초를 유지했다. private gateway connection/upstream ticket 실패도 영속 기록하지만 TLS handshake 전체 실패 로깅·모든 전송 계층의 rate limit을 검증했다고 주장하지 않는다. 계정 로그인에 관한 원문 예시 수치를 모든 MCP transport에 적용한 것으로 표시하지 않는다.

Bandit `bandit-final.txt`는 exit1/18건(Low10, Medium8)이다. B104 Medium3은 Docker의 고정 listener(외부 loopback publish/내부 mTLS), B108 Medium5는 컨테이너 tmpfs 경로, B404 Low3/B603 Low6은 고정 argv·shell 없는 process 실행, B105 Low1은 고정 authorization trace 문자열로 대조했다. 사용자 인자를 shell 문자열로 실행하거나 실제 credential을 이 문자열에 저장하지 않는다. 이 문맥 검토를 스캐너 무경고 또는 보안 전수 PASS로 바꾸지 않는다.

설계20/약점49 전체의 기존 적용성/미완료 상태를 이번 변경으로 재판정하지 않았다. 현재 노출 기능의 적용 P0(서버측 권한, 출처/입력 무결성, 승인 단회 소비·경쟁, 장애시 효과0, UNKNOWN, 영속 인증 실패 감사)는 관련 시험과 실제 집행 근거를 연결했다. 키수명/TLS 전체 negative·일반 native/hook fail-open·전체 C/D 및 제출 전수 진단은 미완료 범위를 유지한다.
