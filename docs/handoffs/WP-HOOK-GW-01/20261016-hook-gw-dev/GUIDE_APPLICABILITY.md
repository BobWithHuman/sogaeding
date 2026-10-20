# WP-HOOK-GW-01 가이드 적용성 검토

2026-10-16 / 보조 AI `guide_map` / 사람 개발자 1명. 이 문서는 원문 확인과 새 연결 범위의 적용성 검토다. 제품 작성자와 다른 AI 역할이 작성했으나 공식 독립 진단이나 최종 코드 검토 보고서가 아니다. 관리 문서·장부·원본 PDF는 변경하지 않았다. 전체 기능, 보안, 설계20/약점49 준수 PASS를 선언하지 않는다.

## 범위와 판정 방법

최신 사용자 지시와 [작업팩13](C:/sogaeding/docs/plans/13_transparent_codex_gateway_mvp.md)을 적용한다. SPEC4의 이슈42/댓글1회/모의3도구는 과거 회귀 범위다. SPEC5의 사용자 turn, native shell/file hook, 실제 agentgateway HTTP extAuthz, MCP upstream, 연결 자격증명과 자동 출처 관측을 새 공격면으로 검토한다. 기존 3도구의 비적용 결론을 새 경로로 복사하지 않았다.

- `적용`: 실제 입력·sink·의존성 또는 필수 보안 경계가 존재한다. 구현 완료나 시험 통과를 뜻하지 않는다.
- `조건부 적용`: 등록 도구/실행 경로에 따라 노출된다. 일반 개발 shell/file에는 미래 실행 코드를 미리 알 수 없으므로 비적용 확정하지 않는다.
- `직접 경로 비적용 후보`: 현재 전용 adapter에서 sink가 관찰되지 않았지만 native 의존성·일반 도구 전체를 제외한 판정은 아니다. 최종 별도 검토 전 비적용 확정으로 쓰지 않는다.
- 표의 시험은 확인해야 할 조건이다. 실제 실행 여부와 결과는 같은 run의 RESULT/REVIEW와 명령 원증거를 대조해야 한다. `필요`를 PASS로 읽으면 안 된다.

읽은 현재 파일은 `src/app/transparent/{engine,judge,server,upstream}.py`, `tools/hookgw_native_probe.py`, `compose.hookgw.yaml`, `agentgateway/config.yaml`, 기존 `app.common`, PDP 의미/진단/모델 코드를 포함한다. 구현 통합 중의 적용성 검토이므로 이후 변경 소스의 최종 해시·시험은 작성자의 최종 snapshot과 별도 REVIEW를 기준으로 한다.

## 원문 확인과 재현 증거

[원문 해시·페이지 manifest](C:/sogaeding/artifacts/20261016-hook-gw-dev/guide-originals-manifest.json)는 `references/manifest.json`의 기존 해시와 원본 PDF 바이트를 SHA256로 대조한 결과다. R1/G1/G2/G3/G4/C1 6개 모두 일치했다. `pypdf`로 원본에서 다시 추출했으며 기존 extracted 파일을 복사하지 않았다. 원문은 읽기 전용으로 유지했다. [6쪽 시각 확인](C:/sogaeding/artifacts/20261016-hook-gw-dev/guide-contact.png)은 R1 PDF25, G1 PDF36, G2 PDF28, G3 PDF510, G4 PDF38, C1 PDF26을 렌더링해 표·페이지·문맥을 확인한 증거다. 전체 PDF를 시각 검토했다는 뜻은 아니다.

| 원문 | 이번에 확인한 핵심 PDF 페이지 | 새 코드·위협·검증 연결 |
|---|---|---|
| [R1 공급망 로드맵](<C:/sogaeding/references/originals/SW 공급망 보안 강화 로드맵.pdf>) | 14·19·25·35 / PDF25=인쇄021 | 구성요소·출처·취약점 영향 정보의 기밀성/무결성/가용성. agentgateway 도입 버전·digest·출처·license와 알려진 미확정 사항을 기록한다. 정부 추진 일정을 팀의 인증·대회 의무로 바꾸지 않는다. |
| [G1 공급망 가이드](<C:/sogaeding/references/originals/240525-(전체본)_SW_공급망_보안_가이드라인_최종 수정본.pdf>) | 35~41·45~53 / 인쇄25~31·35~43 | 안전한 개발·통합, 타사 구성 검증, build/release 무결성, 설치 전후 정상/보안 회귀. 버전 pin만으로 SCA·SBOM·license 점검 완료가 아니다. |
| [G2 Python 가이드](<C:/sogaeding/references/originals/Python_시큐어코딩_가이드(2023년_개정본).pdf>) | 11·21·23·25~26·28~29·42·118·121·124·136·139·144·146·149·151·158·162·170~172; 추가 확인은 아래 보충 증거 | 엄격 입력, 경로/코드/명령 주입, 인증·오류·자원·캡슐화. PDF11의 Python 본문 46항목 설명은 native CLI/Rust proxy/crypto 의존성을 포함한 제품의 49행 면제 근거가 아니다. |
| [G3 진단 가이드](<C:/sogaeding/references/originals/소프트웨어_보안약점_진단가이드(2021).pdf>) | 20·23~28·319·406·415·425·429·506~515 / 인쇄 동일 | 설계20, 구현49, 최초 진단→수정→같은 조건 재진단. 원자 승인/예약, 보고 유실 UNKNOWN, 실제 효과와 판정 분리를 확인한다. |
| [G4 개발보안 가이드](<C:/sogaeding/references/originals/소프트웨어_개발보안_가이드(2021.12.29).pdf>) | 22~24·37~39·350~353 / PDF=인쇄+2 | 요구→위협/외부 인터페이스→표준코딩/소스 진단→실행 중 동적 검증. 20항목과 49약점의 관계를 새 native/MCP 경계에 적용한다. |
| [C1 대회 교육자료](<C:/sogaeding/references/originals/[CM] 2026_소개딩 2라운드 사전교육 자료_vF.pdf>) | 14~15·18~26 | 7범주49약점 유지, 최초 발견·조치·재진단 이력, 기획서 제2항 구조적 예방 근거. 공식 빌드라인 분모/점수/조치율을 임의 계산하지 않는다. |

추출은 각각 `artifacts/20261016-hook-gw-dev/guide-<ID>-pages.json`에 있다. 기본 manifest의 85쪽에 더해 G2 PDF14~17·20·24·35~41의 13쪽을 `guide-G2-command-path-pages.json`으로 직접 보충 추출해 총 98쪽의 원문 증거를 생성했다. G2 PDF35~38(인쇄29~32)의 명령어 삽입·subprocess 예제를 별도로 읽었다. G2 PDF21·23의 eval/exec 예제, PDF25~26의 문자 삭제 경로 예제, PDF35~38의 단순 특수문자 제거/Windows cmd 예제, PDF149의 pickle 예제, PDF42·162의 URL/DNS 예제는 완전한 방어 코드로 복제하면 안 된다. 실제 제품에서는 불필요한 eval/exec/pickle이 없고, shell 입력을 문자 몇 개 삭제해 안전하다고 판단하지 않으며, 경로·대상·역할과 실행 전 결합을 검증해야 한다. [추출·렌더 도구와 읽기 시점 소스 해시](C:/sogaeding/artifacts/20261016-hook-gw-dev/guide-evidence-index.json)는 최종 통합 snapshot과 구별한다.

## 새 신뢰 경계와 적용 P0

| 경계 | 보호 대상·위험 | 코드에서 확인할 통제와 실제 시험 |
|---|---|---|
| 사용자 CLI→UserPromptSubmit→신뢰 adapter | 모델·외부 자료가 user_request/turn을 자칭하거나 후속 요청을 덮어쓰기 | 실제 hook 입력만 turn으로 저장, 연결/세션 소유권, turn 재전송 불일치·stale 거부. 외부 문장의 사용자 권한 승격 금지. 정상 후속 turn도 성공해야 한다. |
| native PreToolUse→PDP→호스트 실행 | shell/patch 인자 변경, hook 누락/오류 시 계속 실행, 오래 실행되는 프로세스의 추가 입력 | 실제 도구별 hook 이름/인자·차단·정상 효과를 확인한다. PostToolUse는 관측이고 취소가 아니다. `write_stdin` 같은 재입력 경로를 보호했다고 가정하지 않는다. |
| PostToolUse→출처 저장→다음 판정 | 결과 위조·다른 call/세션·잘린 원문을 완전 자료로 취급 | 원래 session/turn/tool/args/hash·실행 상태 결합. 외부 문자열의 source_ids·신뢰 등급은 무시. 원문 길이·ref 검증, 잘림/누락 fail-closed. |
| CLI MCP→실제 agentgateway→extAuthz | tool 이름만 검사, 본문 누락/부분 전달, 중복 분석, RPC/인자 변조 | HTTP 본문을 실제로 수신해 tool/args와 pending hook을 결합. 본문 한도·partial 거부. deny/장애/위조/직접 upstream 호출에서 효과0. `mcpAuthorization` 이름 규칙만으로 완료하지 않는다. |
| extAuthz ALLOW→upstream | 검사 후 본문·헤더 바꾸기, replay, 한 번 처리됐는지 불명 | per-body hash와 짧은 수명 ticket/일회 예약, 원자 중복 차단. 일반 upstream의 transaction/receipt/idempotency는 없음. 전송 후 유실은 UNKNOWN, 자동 위험 재시도 금지. |
| 호스트·컨테이너→설정/키/DB/연결 상태 | 같은 계정의 shell이 hook/키를 고치거나 보호 경로를 읽기 | 역할별 키/마운트/포트, 개인 전역 설정·CA·기존 예산 보존. hooks는 완전한 OS 격리가 아니며 같은 사용자 악성 프로세스 보호를 과장하지 않는다. substring marker만으로 경로/symlink/동적 shell을 완전 제어했다고 하지 않는다. |
| 원문·모델·로그·증거 | 민감자료 전송·raw 오류·분석 실패의 오분류 | 저장 암호화·키 분리·마스킹·유한 timeout·진단 enum. ANALYSIS_UNAVAILABLE/NO_ATTACK_ATTEMPT는 공격 식별 PASS가 아니다. 개발 AI 유료 실행0, 기존 judge12/24·actor0 기록 보존. |

## 설계20 전수 적용성

원문 항목명은 G4 PDF37~38, 상세 요구는 G3 PDF507~511이다. 이 표는 20행의 적용성·확인 경로이며 설계 진단 합격표가 아니다. 구현 상태에 관계없이 현재 노출 경로의 필수 통제는 남는다.

| ID | 원문 항목 | 새 범위 적용성과 코드/위협 | 필요한 시험·남은 확인 |
|---|---|---|---|
| SR1-1 | DBMS 조회 및 결과 검증 | 적용. engine의 SQLite sessions/turns/calls/sources/approvals, upstream attempts. SQL 바인딩과 객체 소유권이 함께 필요. | SQL payload, 다른 연결/세션 조회, 경쟁 update·DB 장애. |
| SR1-2 | XML 조회 및 결과 검증 | 직접 경로 비적용 후보. SPEC5 event/RPC는 JSON이고 전용 adapter에서 XML 질의 sink를 관찰하지 않음. 일반 shell이 실행하는 도구는 별도다. | XML/XPath/DTD parser 검색·전이 dependency 확인. XML 도구 등록 시 재검토. |
| SR1-3 | 디렉토리 서비스 조회 및 결과 검증 | 직접 경로 비적용 후보. 현재 머신 bearer 연결에 LDAP 조회 없음. | LDAP 인증/client 도입 여부·전이 의존성 확인; 범용 개발 환경 전체의 N/A 아님. |
| SR1-4 | 시스템 자원 접근 및 명령어 수행 입력값 검증 | 적용. 기존 mock 한정과 달리 native shell/patch·MCP 파일 read/write가 실제 자원 sink다. | 정상 편집과 위험 명령 차단을 함께 확인. 경로 탈출·symlink·인자 변경·보호 파일·명령 인코딩/간접 실행. |
| SR1-5 | 웹 서비스 요청 및 결과 검증 | 적용. 기존 대시보드 이력·source·진단 표시와 새 이력 응답. | XSS canary·텍스트 sink·unsafe 링크; 새 UI를 추가하지 않아도 기존 화면 회귀 필요. |
| SR1-6 | 웹 기반 중요 기능 수행 요청 유효성 검증 | 적용. machine 연결, 사용자 turn, 예외 approval은 별개 권한. | CSRF/origin, 역할 위조, DENY 승인 불가, 정확한 call/turn/hash/policy 단회 소비. |
| SR1-7 | HTTP 프로토콜 유효성 검증 | 적용. TLS HTTP API·RPC·extAuthz·forward header. | Host/중복 Authorization/CRLF/크기·깊이·중복 JSON 키·부적절 RPC. Forward header 위조/덮어쓰기 실제 확인. |
| SR1-8 | 허용된 범위내 메모리 접근 | 적용. Python의 직접 pointer sink 후보 부재와 CLI/Rust proxy/native 암호 의존성은 분리한다. | 모든 경계 size/depth 제한·과대 body, 네이티브 구성 SBOM/SCA. Python이라는 이유로 제외 금지. |
| SR1-9 | 보안기능 입력값 검증 | 적용. 자동 turn/source/call·서버 grant·정책·role이 핵심 입력. | 자가 선언 user_request/source_ids/trust/decision 거부, cross-session/turn/call 위조·stale·재전송. |
| SR1-10 | 업로드·다운로드 파일 검증 | 적용/조건부. 모델 결과에 따른 파일 쓰기, 도구·이미지 취득, 설정 설치. 공개 upload API 없음이 shell 다운로드를 제외하지 않는다. | 경로·형식·실행권한·크기 제한, 공식 출처·hash pin·변조 거부·license. |
| SR2-1 | 인증 대상 및 방식 | 적용. 사람/machine/gateway/forward/upstream 역할·private mTLS. | 인증 누락·교차 role/audience·직접 호출·기존 개인 auth 무변경. |
| SR2-2 | 인증 수행 제한 | 적용. machine/event/history/approval/extAuthz 인증 실패. | 영속 실패 감사·반복/병렬 제한·재시작 후 제한·정상 복구. legacy 인증 시험만으로 새 endpoint 면제 금지. |
| SR2-3 | 비밀번호 관리 | 자체 password 로그인 직접 경로 비적용 후보. bearer/초기 machine trust는 적용. | password 저장/API 부재 확인, token entropy/수명/폐기. 향후 password 도입 시 salted password KDF와 정책 필요. |
| SR2-4 | 중요자원 접근통제 | 적용. host workspace·hook 정의·runtime keys·DB·budget·CA·인증 파일. | 최소권한 파일/volume·grant 객체별 인가·hook 변조·직접 upstream 우회·보호 경로/alias. |
| SR2-5 | 암호키 관리 | 적용. storage/machine/human/forward/TLS 키와 기존 모델키. | 역할 분리·보관·초기발급·만료·회전·폐기·child env/canary. 신규 런타임으로 기존키/CA를 교체하지 않는다. |
| SR2-6 | 암호연산 | 적용. Fernet·HMAC-SHA256·TLS·보안 난수. | 검증된 library/설정, 목적별 hash, 충분한 길이, 잘못된 서명·변조·nonce, 최신 지원은 공식 출처로 확인. |
| SR2-7 | 중요정보 저장 | 적용. 자유 사용자 요청/소스/인자가 기존 fixture보다 넓은 정보를 포함함. | encrypted DB·마스킹·평문 canary 검색·보존/폐기·접근제어·로그 최소화. 승인/예산/UNKNOWN 이력 삭제 의미도 검토. |
| SR2-8 | 중요정보 전송 | 적용. host→control, CLI→gateway, gateway→authz/upstream, 선택 모델 API. | TLS peer/CA/hostname/expiry 및 client cert negative, proxy/redirect 차단, 실제 전송자료 최소화. local/internal network만으로 완료 아님. |
| SR3-1 | 예외처리 | 적용. hook 미기동/timeout/invalid JSON, PDP/DB/source/semantic/전송 장애. | 실행 전 동기 deny 효과0와 hook 자체 fail-open 구분, 전송 후 UNKNOWN, 오류 최소화·취소/자원 정리. |
| SR4-1 | 세션통제 | 적용. 자동 연결 token·Codex session/turn/call·승인·source 장부. | 연결 만료/재연결·세션 혼합·타 machine·후속 turn·stale·동시/replay·재시작; 원문 session ID 공개 최소화. |

## 구현49 전수 적용성

원문 범주/행은 G3 PDF512~515, G4 PDF350~353, G2 PDF170~172, C1 PDF19~25를 대조했다. W 번호는 팀 추적 ID다. 아래의 적용은 특정 약점이 발견됐다는 뜻도, 제거됐다는 뜻도 아니다.

| ID | 원문 약점명 | 적용성·실제 경로/판단 | 확인할 코드·동적 조건 |
|---|---|---|---|
| W-01 | SQL 삽입 | 적용. 엔진·upstream SQLite. | 파라미터 binding·고정 질의, 악성 ID/문자열·소유권 조건·DB 실패. |
| W-02 | 코드 삽입 | 적용. hook 설정/명령, native 실행, 동적으로 쓰는 코드. | adapter의 eval/exec 금지, 고정 callback executable/args; 외부 지시로 코드 실행 추가 차단. 사용자 정상 코딩 자체를 전부 금지하지 않는다. |
| W-03 | 경로 조작 및 자원 삽입 | 적용. Windows cwd/native patch·shell, Linux MCP open_file. | canonical root·보호 경로·절대/UNC/drive/ADS·symlink/reparse·TOCTOU. Linux openat/O_NOFOLLOW 결과를 Windows native 보호로 확대 금지. |
| W-04 | 크로스사이트 스크립트 | 적용. 이력/진단/source의 UI 출력. | HTML/DOM text sink·escape·저장형/반사형 canary·URL scheme. |
| W-05 | 운영체제 명령어 삽입 | 적용. 새 범위의 핵심 native shell과 hook command 실행. | PowerShell/명령 인코딩·연쇄·환경/따옴표·간접 interpreter·수신 stdin. 고정 launcher argv만으로 모델 shell 내용 전체 안전 주장 금지. |
| W-06 | 위험한 형식 파일 업로드 | 조건부 적용. 공개 upload endpoint 없음과 MCP write/native 파일생성은 분리. | 실행 가능한 파일/설정 쓰기 범위·파일명·확장·mode·본문한도·후속 실행 통제. |
| W-07 | 신뢰되지 않는 URL 주소로 자동접속 연결 | 적용. UI 링크·MCP/agent/API 대상·native 네트워크 명령. | 고정/등록 대상·redirect 미추종·scheme/authority 검증·악성 링크. |
| W-08 | 부적절한 XML 외부 개체 참조 | 직접 adapter 비적용 후보. JSON only, parser sink 관찰 없음. | XML/DTD/entity 및 전이 dependency 검색; 등록 tool이 XML을 처리하면 별도 적용. |
| W-09 | XML 삽입 | 직접 adapter 비적용 후보. XPath/XQuery 없음. | XML 질의 sink 부재 재확인; native 전체가 XML 미사용이라는 주장은 하지 않는다. |
| W-10 | LDAP 삽입 | 직접 adapter 비적용 후보. LDAP auth/query 없음. | LDAP client/dependency·환경 auth provider 확인. |
| W-11 | 크로스사이트 요청 위조 | 적용. 연결·사용자 승인 등 중요 HTTP 동작. | bearer 인증뿐 아니라 origin/CORS·정확한 승인 결합·cross-role·외부 site 요청. |
| W-12 | 서버사이드 요청 위조 | 적용. extAuthz/upstream/model endpoint·native curl/fetch. | 호출 대상 고정·URL/host/port/proxy/redirect 변조·내부망/metadata 대상·DNS 재결합 경계. |
| W-13 | HTTP 응답분할 | 적용. authz forwarding header·오류·RPC. | CRLF·header 중복·forward ticket header 덮어쓰기·응답에 외부 문자열 직접 반영 금지. |
| W-14 | 정수형 오버플로우 | 적용. 길이·시간·expires·count·DB·CLI/native 변환. | bool/int 혼동·음수·과대·expiry 경계, SQLite 범위·본문 길이 한도. |
| W-15 | 보안기능 결정에 사용되는 부적절한 입력값 | 적용. 실제 사용자/출처와 agent 자칭 분리. | 서버 grant·연결 role·strict event schema·source/call hash; 모델이 user_request/권한/label을 발급하지 못함. |
| W-16 | 메모리 버퍼 오버플로우 | native 경계 적용. Python 직접 pointer sink는 비적용 후보. | Codex CLI·agentgateway·TLS/crypto/SQLite의 고정 버전·SCA·과대입력. Rust/Python 이름만으로 전부 N/A 아님. |
| W-17 | 포맷스트링 삽입 | 적용 검토. hook command 문자열·format/log·native 출력. | 외부 값을 format template/command로 재해석하지 않음·safe argv·가짜 format payload·log 노출. |
| W-18 | 적절한 인증 없는 중요 기능 허용 | 적용. machine/event/history/approval/authz/upstream. | 누락/오류 credential·private endpoint·mTLS client 검증·직접 upstream 시도. |
| W-19 | 부적절한 인가 | 적용. 자동 연결은 작업별 수동권한 제거이지 권한검증 제거 아님. | tool/workspace/객체/role·turn·call 결합, DENY 승인 해제 금지, grant 변경·타 세션. |
| W-20 | 중요한 자원에 대한 잘못된 권한 설정 | 적용. hook/config/키/DB/volume/budget/개인 auth. | 비root·최소 mount/port·파일 ACL·agent 접근·동일 OS 사용자 한계. |
| W-21 | 취약한 암호화 알고리즘 사용 | 적용. Fernet/HMAC/TLS. | 지원 library·목적별 hash·알고리즘/키길이·실제 TLS 구성·SCA. |
| W-22 | 암호화되지 않은 중요정보 | 적용. 요청·본문·토큰·source/DB/로그. | DB 암호화·role 분리·canary·host/gateway/authz TLS·raw 증거 최소화. |
| W-23 | 하드코드된 중요정보 | 적용. 코드/설정/예제/fixture/artifact. | 실제키 secret scan·가짜값 표시·자동생성·이미지/커밋 제외. fixture key를 운영키로 사용하지 않음. |
| W-24 | 충분하지 않은 키길이 사용 | 적용. bearer·forward HMAC·Fernet·TLS. | 보안 난수·충분한 바이트/비트·잘린 key 거부·라이브러리 key format. |
| W-25 | 적절하지 않은 난수 값 사용 | 적용. 연결 token·승인/ID·키 생성. | secrets/검증된 crypto 사용; 시간/UUID/순차 ID만으로 인증하지 않는다. |
| W-26 | 취약한 비밀번호 허용 | 자체 password 직접 경로 비적용 후보. token 인증의 강도는 적용. | password API/storage 부재·bearer entropy와 폐기·초기 machine trust 확인. |
| W-27 | 부적절한 전자서명 확인 | 제품 전자서명 기능은 후보 부재; 배포 무결성/forward MAC는 적용. | HMAC 검증·변조·expiry·서명 지원 시 signer 검증. digest pin과 publisher 서명 검증을 구분한다. |
| W-28 | 부적절한 인증서 유효성 검증 | 적용. control/gateway/authz/upstream/model. | CA/hostname/expiry·missing/wrong client certificate 거부, verify=False 금지. |
| W-29 | 사용자 하드디스크에 저장되는 쿠키를 통한 정보노출 | 직접 cookie auth 비적용 후보. 연결파일/브라우저/개인 Codex auth 보관은 적용 검토. | cookie·localStorage·URL·config·auth.json 복사/노출 금지; 전역 개인 설정 읽기/변경 범위 제한. |
| W-30 | 주석문 안에 포함된 시스템 주요 정보 | 적용. 새 코드·README·절차·검토/증거. | 실제키·token·개인 경로/내부접속·raw prompt/response 검색, 필요한 가짜 식별값만. |
| W-31 | 솔트없이 일방향 해시 함수 사용 | 비밀번호 hash 직접 경로 비적용 후보. bearer/body/source 식별 hash와 MAC는 목적별 적용. | high-entropy token digest를 password KDF라고 부르지 않음. 비밀번호 도입 시 별도 salted KDF. |
| W-32 | 무결성 검사없는 코드 다운로드 | 적용. 새 agentgateway image·도구·CLI. | 공식 출처·고정 digest/version·해시 대조·license/NOTICE·변조실패. 태그 pull만으로 완료 금지. |
| W-33 | 반복된 인증시도 제한 기능부재 | 적용. 새 machine/event/approval/authz. | 실패 감사와 rate/concurrency 제한은 별개; 영속 기록만으로 반복제한 PASS 금지. |
| W-34 | 경쟁조건: 검사시점과 사용시점(TOCTOU) | 적용. turn→분석→source snapshot→reserve→forward→effect. | 원자 예약·일회 소비·최신 turn/source/policy·인자 변조·동시 gateway claim·재전송·symlink race·UNKNOWN 재시도0. |
| W-35 | 종료되지 않는 반복문 또는 재귀함수 | 적용. hook/HTTP/분석·source 처리·long running shell. | timeout·길이/깊이/수/concurrency·유한 재시도·프로세스/취소 수명. |
| W-36 | 오류메시지 정보 노출 | 적용. CLI log·HTTP/RPC·모델 진단·artifact. | enum 최소정보·traceback/키/본문 비노출·가짜비밀 canary·오류 강제. |
| W-37 | 오류상황 대응 부재 | 적용. hook/PDP/DB/전송/관측 실패. | 실행 전 deny 효과0; hook 프로세스가 안 뜨는 fail-open 별도 표시. 전송 후 유실 UNKNOWN·위험 재시도0. |
| W-38 | 부적절한 예외처리 | 적용. broad except·취소·fallback·상태전이. | catch 후 ALLOW 없음·미완성 분석/원문/JSON 거부·CancelledError·보존/정리·실제 오류코드 검증. |
| W-39 | Null Pointer 역참조 | 적용. Python None/누락 event/빈 DB/RPC object·native 경계. | 정확한 타입·필수 필드·None 분기·잘못된 body/list/null/unknown call. |
| W-40 | 부적절한 자원 해제 | 적용. SQLite transaction·HTTP stream·file fd·hook childprocess. | context/finally·timeout/cancel·열기 중 실패·반복부하·file close·no hung process. |
| W-41 | 해제된 자원 사용 | 직접 Python memory 후보 부재; native/닫힌 fd/DB 수명 적용. | fd/connection 종료 후 재사용·race·SCA·새 도구 수명 검토. |
| W-42 | 초기화되지 않은 변수 사용 | Python 직접 native 변수 후보 부재; 상태분기/예외와 native 구성 적용. | decision 기본값 DENY·미할당 결과/에러 분기·초기화/복구·SCA. |
| W-43 | 신뢰할 수 없는 데이터의 역직렬화 | 적용. hook JSON·JSON-RPC·DB JSON·ticket·grant/config. | strict JSON 중복키/깊이/길이/스키마·pickle/unsafe YAML 금지·추가필드/type 거부. |
| W-44 | 잘못된 세션에 의한 데이터 정보 노출 | 적용. 연결/session/turn/source/history/approval. | 타 연결/세션/call 분리·소유권·재연결·후속 turn·history 역할·stale/source混합 거부. |
| W-45 | 제거되지 않고 남은 디버그 코드 | 적용. offline fixture provider·test trust bypass·LIVE switch. | fixture와 제품 설정 분리·모델/분석 우회 기본 금지·테스트 credential 미배포·debug API 없음. |
| W-46 | Public 메서드로부터 반환된 Private 배열 | 적용. grant/tool allowlist·source·history dict/list 반환. | immutable/deepcopy·반환값 바꿔 정책/저장 상태 불변 검증. |
| W-47 | Private 배열에 Public 데이터 할당 | 적용. 외부 args/grant/list/dict의 내부 상태 저장. | 검증·정규화·deepcopy/직렬화 snapshot; 호출 이후 원객체 변경에도 action/policy hash 불변. |
| W-48 | DNS lookup에 의존한 보안결정 | 적용. OpenAI/gateway/authz/upstream host와 machine 신뢰. | DNS/Host만 신뢰 금지·TLS identity+credential·고정 endpoint·등록경계·재결합. |
| W-49 | 취약한 API 사용 | 적용. Python/HTTP/crypto/SQLite/Codex/agentgateway/native. | 위험API·지원설정·고정version·SCA·공식문서·대체·재진단. |

## 코드 관찰과 시험 증거의 구분

초기 읽기에서 `engine.db`의 `BEGIN IMMEDIATE`·SQL 바인딩·Fernet 저장, call/turn/hash 결합, 재시작 중 ANALYZING/EXECUTING의 UNKNOWN 전이, `authorize`의 strict refs/의미 판정/안전한 진단 재사용을 관찰했다. `observe`는 OBSERVED/OBSERVED_ERROR이며 일반 upstream의 transactional SUCCEEDED receipt로 표현하지 않는다. `upstream.open_file`은 Linux dir_fd·O_NOFOLLOW 기반이고 파일 쓰기와 SQLite attempts를 하나의 transaction으로 보장한다고 쓰지 않는다. `compose.hookgw.yaml`은 private network·최소권한·고정 agentgateway digest를 구성한다. 이는 코드 관찰이며 해당 통제의 모든 negative 시험 PASS가 아니다.

다음 사항은 최종 통합에서 실제 시험·별도 코드 검토가 필요하다.

1. native hook 프로세스가 실행되기 전의 오류/신뢰 미승인과 PDP가 반환한 deny를 구분한다. Codex 자체 정책으로 도구가 막힌 결과를 제품 hook 차단 성공으로 계산하지 않는다. 정상 native shell/patch 효과와 Post 이벤트가 없는 경우 보호·정상 기능을 지원 완료로 쓰지 않는다.
2. 실제 agentgateway v1.6.0에서 JSON-RPC 원문/args가 extAuthz로 전달되는지, 본문/헤더가 upstream 전에 변경되지 않는지 확인한다. source 관측, deny, timeout, 인증/인자/replay 실패별 upstream 효과0이 필요하다.
3. bearer role, mTLS listener 분리, connection/session/turn 소유권, 승인 단회 CAS, 판정 도중 source/turn 변경과 UNKNOWN의 재시도를 확인한다. DB restart가 진행 중인 요청과 경합하는 경우도 별도다.
4. 머신 키를 가진 같은 OS 사용자/프로세스와 host 관리자에 대한 한계를 명시한다. hook source 신뢰와 OS 권한은 동일한 통제가 아니다. protected-marker 문자열 검사만으로 shell의 모든 경로/인코딩/alias를 통제했다고 하지 않는다.
5. 새 API의 반복 인증제한·영속 감사·보존/폐기·연결 만료, body/형식/자원 한도·canary·TLS negative를 실제로 확인한다. 기존 A/B 시험은 회귀 자료이며 신규 endpoint 전체의 완료 증거가 아니다.
6. grant/list/dict의 참조 공유, 출력/출처의 raw 민감값, generic tool 결과의 크기/잘림·안전한 파일 IO를 최종 소스에서 다시 확인한다. 구현 중 발견을 조치실적으로 임의 계산하지 않는다.

## 정적·동적·공급망 진단 범위

이 보조 검토는 별도 SAST/SCA/비밀검색 실행을 수행하지 않았다. 해당 결과는 **NOT_RUN(이 문서 작성 역할)** 이며 0건이 아니다. `rg`로 신규 adapter의 eval/exec/pickle/unsafe YAML/shell=True/verify=False/인증/상태전이 위치를 읽은 것은 제한된 수동 검색이다. 이 검색은 49개 룰 지원이나 전체 source 분석 결과가 아니다. root가 실행한 도구는 최종 RESULT의 도구명/버전/rule/명령/exit code/대상 snapshot에 연결해야 한다.

| 활동 | 이 문서의 실제 수행 | 최종 인계에 추가할 근거 |
|---|---|---|
| 원문·무결성 | 6 PDF SHA256 대조 일치, 관련페이지 재추출, 6쪽 시각검토 | 위 guide manifest·추출·렌더 파일. 원문 수정 없음. |
| 적용성·수동 source 읽기 | 설계20/약점49 전체 적용성, 새 adapter/구성의 일부 경계 읽기 | 최종 코드 snapshot과 별도 REVIEW. 전체 수동 source 진단 완료 아님. |
| SAST/secret scan | 이 역할 미실행 | 실제 룰/버전·포함/제외·원시경고·finding ID·재진단. |
| 실제 native hook | root 실행 증거 읽기만 | 각 `native-*/summary.json`·events·cli·명령·source hash. 정상 효과와 실제 차단 원인을 구분한다. |
| 실제 gateway/extAuthz | 이 역할 미실행 | 실제 고정 이미지·TLS 요청·args 수신·status·upstream 전후 effects/attempts·장애/위조/replay. |
| 공급망 | R1/G1 적용 요구와 digest pin 코드 읽기 | OCI source/revision/license·release·실제 image digest·license/NOTICE·SBOM/SCA. 이미지 tag/label만으로 publisher 서명·CVE0을 주장하지 않는다. |
| 모델 의미 검증 | 이 역할 유료 호출0 | 사용자가 직접 실행. ANALYSIS_UNAVAILABLE/NO_ATTACK_ATTEMPT 분리, 기존 budget 보존. |

초기 source 기준선은 [baseline summary](C:/sogaeding/artifacts/20261016-hook-gw-dev/baseline-source/summary.json) 128개 파일, fingerprint `6c63def0a45cd44c179c2fbbcec3f000aea3c48494ca8db2648fc90ac9ffb6c0`이다. 최종 소스/명령/최초 실패/조치/재진단은 같은 run의 RESULT와 FINDINGS 장부에 연결한다. 이 문서가 최초 실패나 기존 수동 모델 실패를 덮어쓰지 않는다.

공식 평가 조치율·빌드라인 산식을 만들지 않았다. 본 작업의 신규 adapter 검증과 C/D 전체 운영·전수진단 보강은 구분하되 현재 노출 경로의 적용 P0를 제외하지 않는다. 최종 DONE/MVP 판정은 관리 세션의 권한이다.
