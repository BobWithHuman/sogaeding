# 변경 경계의 보안 진단·조치·재진단

설계20/약점49행은 SECURITY_APPLICABILITY.csv에 유지했다. 비노출은 이번2도구 JSON/CLI smoke 범위다. 모든 DTAP 서버/이미지까지 준수 PASS로 확장하지 않는다. 기존 공통 인증/원자소비/P0를 배제하지 않는다.

원문은 이전에 읽은 `artifacts/20261017-frozen-demo/guide-pages.json`과 `artifacts/20261017-core-auto-finish/auth-guide-pages.json`의 필요한 발췌를 재사용했다: R1 PDF14·G1 PDF35–36(공급망/개발검증), G2 PDF128–129·135·137(경쟁/제한/안전한 예외), G3 PDF110–112·507–508·510(인증/서버권한/입력·비밀), G4 PDF24·38(요구→코드→동적 검증·조치·재진단). 원문 경로/페이지 차이는 관리03_guide_compliance.md에 따른다.

| 최초 관찰 | 조치 | 재진단·한계 |
|---|---|---|
| static task path 계산이 benign risk category를 누락해 중복처럼 보임 | official task_helpers의 경로 규칙을 적용, component 검증 | inventory-canonical-paths.txt:6682 unique·누락0. 잘못된 초기 출력 inventory-initial-path-bug/ 보존 |
| MCP2 개발 image에 official FastMCP 없음 | 제품 유지, benchmark만 별도 wheel overlay | actual18 schema 조회/실제 MCP 호출 |
| MCP1.26 PyPI advisory7개(중복 alias 포함) | MCP1.30으로 수정, 공개 메타데이터0·SHA256/오프라인no-deps 설치 | benchmark-dependencies-130.json·pip check; 전체 이미지 전이 SCA 완료 아님 |
| 경로를 official MCP가 unquoted shell에 삽입 | 양 arm 모두 POSIX literal/canonical path·unknown arg·credential override/permission LLM 제한 | exact schema/resource 반례+실제파일 단회. query/shell 범용 지원은 미완료 |
| pre가 dispatch try 밖 / Post 필수 route 누락 | PRE 자체기록, explicit hook fail-start, 정확 Post route 추가, control 오류를 semantic stop과 분리 | 실제 official hooks→gateway→MCP→Post→judge. 초기 실패/빈 final은 성공 취급하지 않음 |
| schema/hash metadata가 secret gate에 걸림 | 해시는 서버 trace 보존, fixture catalog는 공개 설명 투영 | 기본 마스킹 유지. generic catalog/민감 source는 NOT_READY |
| actor 실패 뒤 사용량 부재/취소 | STARTED→UNKNOWN, 예약 유지, 재전송없음, 실제 live transport 비활성 | 모델/effort mismatch 전송0, 누락 usage/cancel/race/manifest drift 반례 |

최초 Bandit14(High1/Medium7/Low6), 조치 후12(High0/Medium7/Low5). SHA1은 Git object identity만 쓰며 `usedforsecurity=False`, archive와 파일은SHA256. fixture wire assertion을 런타임 검사로 교체했다. 잔여 B104×2는 Docker listener(내부mTLS/호스트loopback), B108×5는 격리 컨테이너 tmpfs/합성 exfil, B404×1·B603×3·B607×1은 shell=False·고정 Docker/Python argv의 개발 launcher다. 입력 명령을 호스트 shell로 실행하지 않는다. 원문 setup은 먼저 읽고 pinned source만 별도 컨테이너 stdin으로 실행한다. 남은 경고를 스캐너 PASS로 표시하지 않는다.

전송/저장/권한: 실제 agentgateway TLS+private mTLS, role별 새 가짜 PKI, server-owned norm·정확 body hash ticket·SQLite primary key 예약, 실패시 dispatch0/UNKNOWN, 소스 hash/전체 catalog 검증, native grant[]를 확인했다. environment는 관리/제품 코드·개인홈·실데이터·비밀 mount0, 별도 internal networks, synthetic data뿐이다. 환경API의 공개 admin token은 격리 sandbox fixture이며 외부 서비스 인증정보가 아니다. judge는 별도 filesystem에서 공식 helper를 사용하며 actor 파일도구로 judge/정답을 읽을 수 없게 분리했다.

보존 검사89파일(호환 확장1파일 제외)·개인 config hash/auth·hooks metadata 동일. 개발 제품 유료 호출0; 개발 AI 토큰과 구별. 추가 전체 동적 negative/전수 SCA/전체14도메인 P0 검증은 NOT_RUN이며 실행 준비0의 사유다.
