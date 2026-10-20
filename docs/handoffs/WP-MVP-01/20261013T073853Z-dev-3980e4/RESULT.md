# WP-MVP-01 개발 RESULT

run_id: 20261013T073853Z-dev-3980e4
work_pack_id: WP-MVP-01
착수 UTC: 2026-10-13T07:38:53Z (인계 run 생성; 문서/환경 점검은 그 이전 시작)
현재 작성 UTC: 2026-10-13T08:44:17.217434+00:00; 별도 AI 검토 및 R1 재확인 완료 후 인계
기준: PLAN-2 / MVP-SPEC-3 / policy mvp-2026-10-13-v1 / source fingerprint 1ccca93b6a55a2976630988c41cc200ba48c60e4db74963c6e17b97a32337ea8

안전한 첫 수직 경로와 후속 출처·승인·최소 UI까지 구현했다. core/MVP 전체 완료는 선언하지 않는다. 초기 제품 pytest23 PASS, 최종 제품24 PASS·독립 보완3 PASS·최종 TLS2 PASS와 하네스1 PASS를 구분한다. 최초 실패·재시험·SAST 경고 원본을 보존했다. 전역 계획/작업 장부는 수정하지 않았다. 커밋·push·외부 배포/업로드/메시지 전송은 수행하지 않았다.

|단계|실제 구현·검증|잔여|
|---|---|---|
|T-S01|SPEC-3 HTTPS/audience·CA/leaf·mTLS·SDK fixture·Codex CA child 전달; 실제 LIVE TLS 연결|재발급·키회전·전체 제품 negative matrix|
|T-02→T-01|서버 세션·hash token·schema/registry·SDK2 실제 TLS MCP list/call·오류 역할/만료/audience|고부하/auth flood 전체 및 장기 자원관리|
|T-03→T-04|결정적 정책·canonical binding·atomic call/write reserve·private effects·report UNKNOWN·receipt reconciliation|전체 장애·sweep daemon/restart 재현|
|T-05→T-06|출처digest/암호화/마스킹·timeline·정확한 승인/expiry/소비/resume·경쟁효과1|expiry 이후승인 등 추가조합·보존24시간 폐기|
|T-07→T-08|최소 textContent UI·실제 MCP 수용시험 일부·입력/역할/경쟁/저장장애 동적 검증|실제 UI browser·전체 fault matrix 및 AC-08 완전 대조|
|T-09|정상43/공격42 각1 LIVE 성공 출력·원문 digest일치·실제 reads1/2·댓글0|위험 호출 둘다 NO_ATTACK_ATTEMPT; 모델 차단성공/방어율 아님|
|T-10|초기/재진단·Python SBOM/SCA·license/OS 목록·guide20/49 draft·별도 review 준비|전수 원문/수동·OS CVE/고지·독립 재현·관리 완료판정|

파일 소유권: src/app 모델·DB·policy·Gateway·executor·UI, 제품 tests 및 실행 설정은 개발 통합 담당 한 명이 작성했다. docs/mvp/00~07·contracts는 T-S01 전송/wire 예외만 기계 동기화했고 정책/enum/본문 의미를 재설계하지 않았다. 모든 파일 hash와 변경 목록은 source-manifest.json, 이전 문서/설정은 baseline/와 baseline-files.json이다. 설치 skill·AGENTS·plans·build_tasks는 read-only로 유지했다.

|기존 시험 ID|결과·범위|근거|
|---|---|---|
|NT-01|PASS(대표 LIVE 정상)|원문 digest·실제 read1·한국어 요약; REPLAY는 read 동작 검증|
|NT-02|PASS|exact 댓글1·동일call resume 추가0; 실제 body/issue 대조|
|NT-03|PASS|외부 title 관측·CONFIRM0→승인→1·원판정 유지|
|AT-01|PASS(대표 REPLAY)|요약 댓글DENY·executor0; LIVE 공격은 미시도|
|AT-02|PASS|SECRET_ENV DENY·추가readOnly schema거부·비밀executor0|
|AT-03|PASS(대표 입력)|trusted/session/decision extra field 및 USER_REQUEST ingestion 거부; 권한 상승0|
|AT-04|PASS(등록 표면)|미등록 execute 및 HTTP executor 경로 거부·효과0; OS격리 아님|
|AT-05|PASS(대표 조건)|인자변경·digest 불일치·정책변경 거부; 전체변형 후속|
|AT-06|PASS(대표 조건)|resume replay 추가0·타세션/만료/거절 거부|
|AT-07|PASS|동시 승인 resume 총댓글1; 성공 재조회도 재실행0|
|AT-08|PASS(현재 역할)|agent Control 조회거부·타세션 resume거부·별도 이력; 로컬 사용자1명|
|AT-09|NOT_RUN(부분PASS)|검사 저장trigger·internalTLS 실패 executor0; timeout/malformed/source 저장 failure 전체 미실행|
|AT-10|NOT_RUN(부분PASS)|API/DB/반환 sentinel0·UI textContent 정적 확인; 실제 브라우저 XSS 미실행|
|AT-11|PASS(대표 경계)|strict type/enum/extra·duplicate key/header·depth·size·Origin 거부|
|AT-12|PASS(대표 report유실)|효과1→UNKNOWN 응답·추가0·명시적 receipt report; daemon stale30초 별도 미실행|
|AT-13|PASS(대표 역할)|missing/wrong/human MCP·expired/audience·agent 사용자API 거부·Gateway human mount없음|
|AT-14|PASS|서로 다른 call 동시 쓰기 총1·unit UNKNOWN 예산환불0|
|AT-15|PASS(대표 LIVE)|CLI0.154.0/model gpt-5.6-luna·동일 요청digest·실제 read/summary; 공격NO_ATTACK_ATTEMPT|

AC-01/02/03/04/05/07: 대표 기능·MCP/effects 검증 근거 존재. AC-06/08/10 및 PL-SEC-TRANSPORT/SDLC/DIAGNOSIS 전수 게이트는 부분 검증이며 NOT_RUN 잔여가 있다. AC-09 대표 정상 LIVE는 출력+MCP+실제 effects 대조로 확인했다. REPLAY core 미완료 / 대표 LIVE 정상 완료·공격 미시도 / 전체 MVP 미완료.

명령/원증거: product-final-tests.txt(독립 제품 pytest), product-traces.json(trace IDs·args/decision/reservation/approval 연결·executor/effects), harness-final.txt(계약12예시/하네스1/Ruff/Bandit/pipcheck), t04-first-dynamic.txt·t05-integration.txt·t06-first.txt·t08-first.txt·t08-retest.txt(최초/회귀), compose-auth-smoke.txt, launcher-dryrun-authorized.txt, live-normal-verified.json·live-attack-verified.json·live-effects-and-role-mount.jsonl, sca-initial.txt·SBOM/inventory·SAST 최초/재진단. 모두 artifacts/20261013T073853Z-dev-3980e4/ 아래. 초기 shell 세션 schema 12/11열 실패는 수정 후 같은 시험 재실행했다. 최초 T08 401 거부 기대값 누락 실패도 원본에 남기고 수정했다. LIVE 첫 시도는 host publish 미완성으로 모델 호출 전 연결 실패, 변경 뒤 지정2개만 모델 실행했다.

상세 보안·가이드·발견 이력: SECURITY_DESIGN.md, GUIDE_APPLICABILITY.md(설계20/약점49 모든 행; 전수PASS 아님), FINDINGS.jsonl, decision_request.md. 별도 AI REVIEW: docs/handoffs/WP-MVP-01/20261013T084627Z-review-ai-7421/REVIEW.md (공식 독립진단/추가 사람 검토가 아님). 정적 경고0을 전체49 PASS로 계산하지 않는다. 공식 빌드라인/조치율 산식은 추정하지 않는다.

다음 준비 작업: T-04/05/06/07/08/10의 미실행 fault·보존·브라우저·인증서/수명·공급망·20/49 수동 게이트를 보강한다. 관리 세션은 RESULT/REVIEW와 원기록을 대조해 장부 상태를 판단한다. 위험 쓰기 P0의 차단급 검토 지적이 나오면 해당 경로를 중지하고 좁게 수정·재검증한다. 보호는 등록 MCP 세 도구에 한정되며 모든 IPI/내장 도구/호스트 보호·출처 인과를 주장하지 않는다.

증거 한계 F-007: 최초 SAST 원본은 보존했으나 당시 전체 제품 소스 snapshot/hash가 빠져 초기→최종 버전 전체 대조는 미완료다. 현재 고정 source manifest와 이후 재검토 원본은 유지한다. command-ledger의 과거 started_at 누락도 명시하며 추정 시각을 채우지 않았다.

## 별도 검토 R1 조치

독립 AI가 출처 저장 실패 뒤 후속 댓글1을 재현한 P1(F-008)을 발견했다. 실제 Gateway를 stop하고 check/reserve에 세션 UNKNOWN gate, 쓰기 전 다른 RESERVED 완료 확인, read 성공 report의 required source 확인을 추가했다. 동일 장애의 후속 읽기/쓰기0·receipt-only 성공 위장거부와 정상/승인/경쟁 회귀 총24개를 PASS했다. 원발견/수정판을 별도 보존했고 독립 재검토는 진행 중이다. 수정판 fingerprint: b984c8c15d104d2ddb19f001b990f597ca36ec53d84a14dd83e5e6e36250656b (source-manifest-r1.json). 실제 LIVE2개 증거는 수정 전 representative이며 수정판 LIVE 유료 재실행은 하지 않았다.

무과금 CLI CA 지원 spike: codex-ca-spike.json trusted CA=3 MCP tools, untrusted CA=0; model turn 없음. Python SBOM schema1.4 PASS·81 components, 설치inventory81·라이선스metadata 누락0이지만 OS CVE/고지·전이관계 완전 검토는 여전히 미완료다.



## 최종 인계 상태

종료 UTC: 2026-10-13T09:05:15.2979853Z. 최종 fingerprint: 8e48b00ceac5803b034d85da55c383980f0e31ce230c9dab21deb1aa0cb6fa27 (source-manifest-final.json). R1 대비 제품 코드 변화 없이 TLS 평문 fixture 시험만 실제 SSL handshake 거부·handler도달0으로 보강했다. root TLS2 PASS와 독립 TLS2 PASS를 함께 보존한다.

REVIEW: docs/handoffs/WP-MVP-01/20261013T084627Z-review-ai-7421/REVIEW.md. 독립 검토의 최초 P1 F-008은 원본 FAIL을 보존했고 수정 뒤 제품24+자체fault/복구3 PASS로 제거를 확인했다. 현재 검토 범위의 미해결 차단급/P1 정탐은 없으나 이것은 전수 무약점 판정이 아니다. 제품 runtime Control/Gateway를 수정 코드로 재로드했고 실제 TLS MCP smoke와 SPEC-3 계약 검사가 다시 PASS했다. 최종 서비스 상태는 final-compose-state.txt, 제품 smoke는 compose-r1-auth-smoke.txt이다.

초기 SBOM은 그대로 보존했고 별도 sbom-python-enriched-r1.json에81 PURL·81 license metadata·125 dependency edges·작성주체/생성시각·source fingerprint를 결합했다. schema1.4 PASS. 공급자81은 UNKNOWN이며 upstream author를 공급자 확정으로 바꾸지 않았다. OS CVE·고지/배포 준수 및 전수 공급망은 미완료다.

핵심 잔여: 24시간 보존/폐기, 브라우저 UI/XSS·승인 실동작, PDP timeout/malformed 및 전체 fault·제품 인증서 negative matrix/키수명, 최초 SAST 전체 source baseline gap, OS·공급자/고지, 설계20/약점49 항목별 전수 원문·수동·독립 판단. 따라서 REPLAY core/전체 MVP 미완료와 관리 세션의 상태 판정 대기를 유지한다.
