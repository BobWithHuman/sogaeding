# WP-PDP-JEV-01 가이드 적용성 재검토

2026-10-16. 기존 설계20·약점49의 전 행을 새 TypeSafe HTTP provider/slot parser/출처 문맥/격리 연결과 대조했다. 아래는 적용성 재검토이며 69개 진단 PASS가 아니다. 원 PDF/관리 기준/이전 원증거를 변경하지 않았다. 사람 개발자1명, 별도 AI 검토와 공식 독립 진단은 다르다.

원본6PDF/18페이지는 artifacts/20261016-jev-dev/guide-original-pages.json에 SHA와 원문을 새로 고정했다. R1 p25/G1 p35·38·47은 고정 source/lock·기존 bundle 보존·code-only 배치·라이선스와 미확정 공급망을, G2 p35·38·136·139·144·146은 검증된 parser·중요정보·전송·예외/자원해제를, G3 p507·509~511/G4 p37~39는 입력/권한·키·보안결정·오류/세션통제를, C1 p26은 최초진단→조치→재진단을 연결한다. PDF 물리 페이지 번호다.

기존 적용성 근거는 [원 표](../../WP-HOOK-GW-01/20261016-hook-gw-dev/GUIDE_APPLICABILITY.md)이며 해당 표의 실행 경로/의존성 한계도 보존한다. 새 패키지/이미지/SDK 취득0, 기존 httpx0.28.1/BSD-3-Clause의 lock·실제license SHA를 대조했다. 신규 endpoint는 고정 TLS·no proxy/redirect/retry·bounded typed data·독립 원장 사전예약으로 검토했다. 계획/전역 DONE·공식 빌드라인/조치율은 변경·추정하지 않는다.

검증 연결 A=282개 관련 회귀(backend/F3/transport/web/hookgw), B=실제 pinned gateway/fakeHTTP25, C=별도 rules-only 실제읽기10/무모델preflight, D=별도 AI 독립299·발견 R01~R04 재진단, E=Bandit 원 경고8개와 수동 sink/통제 검토다. 이 결과는 서로 겹치고 전수 보안 진단이나 실제 Jev 정확도가 아니다. 구체 명령/소스/실패/NOT_RUN은 RESULT와 final-index.json을 따른다.

| ID | 항목 | 기존 적용성·실행 경로(보존) | 이번 재검토·증거/잔여 |
|---|---|---|---|
| SR1-1 | DBMS 조회 및 결과 검증 | 적용. engine의 SQLite sessions/turns/calls/sources/approvals, upstream attempts. SQL 바인딩과 객체 소유권이 함께 필요. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-2 | XML 조회 및 결과 검증 | 직접 경로 비적용 후보. SPEC5 event/RPC는 JSON이고 전용 adapter에서 XML 질의 sink를 관찰하지 않음. 일반 shell이 실행하는 도구는 별도다. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| SR1-3 | 디렉토리 서비스 조회 및 결과 검증 | 직접 경로 비적용 후보. 현재 머신 bearer 연결에 LDAP 조회 없음. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| SR1-4 | 시스템 자원 접근 및 명령어 수행 입력값 검증 | 적용. 기존 mock 한정과 달리 native shell/patch·MCP 파일 read/write가 실제 자원 sink다. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-5 | 웹 서비스 요청 및 결과 검증 | 적용. 기존 대시보드 이력·source·진단 표시와 새 이력 응답. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-6 | 웹 기반 중요 기능 수행 요청 유효성 검증 | 적용. machine 연결, 사용자 turn, 예외 approval은 별개 권한. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-7 | HTTP 프로토콜 유효성 검증 | 적용. TLS HTTP API·RPC·extAuthz·forward header. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-8 | 허용된 범위내 메모리 접근 | 적용. Python의 직접 pointer sink 후보 부재와 CLI/Rust proxy/native 암호 의존성은 분리한다. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-9 | 보안기능 입력값 검증 | 적용. 자동 turn/source/call·서버 grant·정책·role이 핵심 입력. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR1-10 | 업로드·다운로드 파일 검증 | 적용/조건부. 모델 결과에 따른 파일 쓰기, 도구·이미지 취득, 설정 설치. 공개 upload API 없음이 shell 다운로드를 제외하지 않는다. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-1 | 인증 대상 및 방식 | 적용. 사람/machine/gateway/forward/upstream 역할·private mTLS. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-2 | 인증 수행 제한 | 적용. machine/event/history/approval/extAuthz 인증 실패. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-3 | 비밀번호 관리 | 자체 password 로그인 직접 경로 비적용 후보. bearer/초기 machine trust는 적용. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| SR2-4 | 중요자원 접근통제 | 적용. host workspace·hook 정의·runtime keys·DB·budget·CA·인증 파일. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-5 | 암호키 관리 | 적용. storage/machine/human/forward/TLS 키와 기존 모델키. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-6 | 암호연산 | 적용. Fernet·HMAC-SHA256·TLS·보안 난수. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-7 | 중요정보 저장 | 적용. 자유 사용자 요청/소스/인자가 기존 fixture보다 넓은 정보를 포함함. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR2-8 | 중요정보 전송 | 적용. host→control, CLI→gateway, gateway→authz/upstream, 선택 모델 API. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR3-1 | 예외처리 | 적용. hook 미기동/timeout/invalid JSON, PDP/DB/source/semantic/전송 장애. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| SR4-1 | 세션통제 | 적용. 자동 연결 token·Codex session/turn/call·승인·source 장부. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-01 | SQL 삽입 | 적용. 엔진·upstream SQLite. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-02 | 코드 삽입 | 적용. hook 설정/명령, native 실행, 동적으로 쓰는 코드. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-03 | 경로 조작 및 자원 삽입 | 적용. Windows cwd/native patch·shell, Linux MCP open_file. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-04 | 크로스사이트 스크립트 | 적용. 이력/진단/source의 UI 출력. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-05 | 운영체제 명령어 삽입 | 적용. 새 범위의 핵심 native shell과 hook command 실행. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-06 | 위험한 형식 파일 업로드 | 조건부 적용. 공개 upload endpoint 없음과 MCP write/native 파일생성은 분리. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-07 | 신뢰되지 않는 URL 주소로 자동접속 연결 | 적용. UI 링크·MCP/agent/API 대상·native 네트워크 명령. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-08 | 부적절한 XML 외부 개체 참조 | 직접 adapter 비적용 후보. JSON only, parser sink 관찰 없음. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| W-09 | XML 삽입 | 직접 adapter 비적용 후보. XPath/XQuery 없음. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| W-10 | LDAP 삽입 | 직접 adapter 비적용 후보. LDAP auth/query 없음. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| W-11 | 크로스사이트 요청 위조 | 적용. 연결·사용자 승인 등 중요 HTTP 동작. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-12 | 서버사이드 요청 위조 | 적용. extAuthz/upstream/model endpoint·native curl/fetch. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-13 | HTTP 응답분할 | 적용. authz forwarding header·오류·RPC. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-14 | 정수형 오버플로우 | 적용. 길이·시간·expires·count·DB·CLI/native 변환. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-15 | 보안기능 결정에 사용되는 부적절한 입력값 | 적용. 실제 사용자/출처와 agent 자칭 분리. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-16 | 메모리 버퍼 오버플로우 | native 경계 적용. Python 직접 pointer sink는 비적용 후보. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-17 | 포맷스트링 삽입 | 적용 검토. hook command 문자열·format/log·native 출력. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-18 | 적절한 인증 없는 중요 기능 허용 | 적용. machine/event/history/approval/authz/upstream. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-19 | 부적절한 인가 | 적용. 자동 연결은 작업별 수동권한 제거이지 권한검증 제거 아님. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-20 | 중요한 자원에 대한 잘못된 권한 설정 | 적용. hook/config/키/DB/volume/budget/개인 auth. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-21 | 취약한 암호화 알고리즘 사용 | 적용. Fernet/HMAC/TLS. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-22 | 암호화되지 않은 중요정보 | 적용. 요청·본문·토큰·source/DB/로그. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-23 | 하드코드된 중요정보 | 적용. 코드/설정/예제/fixture/artifact. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-24 | 충분하지 않은 키길이 사용 | 적용. bearer·forward HMAC·Fernet·TLS. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-25 | 적절하지 않은 난수 값 사용 | 적용. 연결 token·승인/ID·키 생성. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-26 | 취약한 비밀번호 허용 | 자체 password 직접 경로 비적용 후보. token 인증의 강도는 적용. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| W-27 | 부적절한 전자서명 확인 | 제품 전자서명 기능은 후보 부재; 배포 무결성/forward MAC는 적용. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-28 | 부적절한 인증서 유효성 검증 | 적용. control/gateway/authz/upstream/model. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-29 | 사용자 하드디스크에 저장되는 쿠키를 통한 정보노출 | 직접 cookie auth 비적용 후보. 연결파일/브라우저/개인 Codex auth 보관은 적용 검토. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-30 | 주석문 안에 포함된 시스템 주요 정보 | 적용. 새 코드·README·절차·검토/증거. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-31 | 솔트없이 일방향 해시 함수 사용 | 비밀번호 hash 직접 경로 비적용 후보. bearer/body/source 식별 hash와 MAC는 목적별 적용. | Jev adapter는 JSON/별도 bearer만 추가; XML/LDAP/password sink는 추가하지 않음. 기존 직접 비적용 **후보**와 native/의존성 조건 유지. 전역 N/A 확정 아님. |
| W-32 | 무결성 검사없는 코드 다운로드 | 적용. 새 agentgateway image·도구·CLI. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-33 | 반복된 인증시도 제한 기능부재 | 적용. 새 machine/event/approval/authz. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-34 | 경쟁조건: 검사시점과 사용시점(TOCTOU) | 적용. turn→분석→source snapshot→reserve→forward→effect. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-35 | 종료되지 않는 반복문 또는 재귀함수 | 적용. hook/HTTP/분석·source 처리·long running shell. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-36 | 오류메시지 정보 노출 | 적용. CLI log·HTTP/RPC·모델 진단·artifact. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-37 | 오류상황 대응 부재 | 적용. hook/PDP/DB/전송/관측 실패. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-38 | 부적절한 예외처리 | 적용. broad except·취소·fallback·상태전이. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-39 | Null Pointer 역참조 | 적용. Python None/누락 event/빈 DB/RPC object·native 경계. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-40 | 부적절한 자원 해제 | 적용. SQLite transaction·HTTP stream·file fd·hook childprocess. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-41 | 해제된 자원 사용 | 직접 Python memory 후보 부재; native/닫힌 fd/DB 수명 적용. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-42 | 초기화되지 않은 변수 사용 | Python 직접 native 변수 후보 부재; 상태분기/예외와 native 구성 적용. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-43 | 신뢰할 수 없는 데이터의 역직렬화 | 적용. hook JSON·JSON-RPC·DB JSON·ticket·grant/config. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-44 | 잘못된 세션에 의한 데이터 정보 노출 | 적용. 연결/session/turn/source/history/approval. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-45 | 제거되지 않고 남은 디버그 코드 | 적용. offline fixture provider·test trust bypass·LIVE switch. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-46 | Public 메서드로부터 반환된 Private 배열 | 적용. grant/tool allowlist·source·history dict/list 반환. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-47 | Private 배열에 Public 데이터 할당 | 적용. 외부 args/grant/list/dict의 내부 상태 저장. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-48 | DNS lookup에 의존한 보안결정 | 적용. OpenAI/gateway/authz/upstream host와 machine 신뢰. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |
| W-49 | 취약한 API 사용 | 적용. Python/HTTP/crypto/SQLite/Codex/agentgateway/native. | 새 정책/typed HTTP·slot/provenance 경계를 같은 적용성으로 재검토. 해당 변경은 A~E의 좁은 근거와 연결; native 일반개발·hook fail-open·공급망/전수진단 미완료 유지. |

새 임계치/한국어·CJK·adversarial state/관련 span 검색 누락은 실제 모델 평가 전 NOT_RUN이다. 모델0 공개읽기·hard deny와 fake semantic 합성을 별도 기록하며 source 일치는 인과가 아니다. inline 마커를 삽입/제거하거나 권한으로 쓰는 기능은 없다. 원 표 SHA256: `a844f55dc62b168d938fbefe1a997d437773fda12033adfb0e66a736d00756d6`.
