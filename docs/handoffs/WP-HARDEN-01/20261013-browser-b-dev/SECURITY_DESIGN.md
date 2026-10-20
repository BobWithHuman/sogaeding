# 단계 B 통제 설계

위험입력은 사람요청·외부issue/readme·tool결과·오류·역할bearer·Origin이다. 보호대상은 정확한 session/call/args/policy 승인, 자격증명, 이력과 실제효과 일치다. 단일 인간 사용자 체계다.

Control은 CONTROL_PORT의 두loopback HTTPS Origin만 허용하고 기존 역할/mTLS검사를 유지한다. 실제8010 create201·다른Origin 차단을 관측했다. Origin검사는 bearer검사의 대체가 아니다.

UI는 textContent/createElement, 고정 안전 오류 문구, 알수없는 오류 일반화, timeout5초/redirect:error/cache:no-store, revision으로 늦은 응답폐기, context변경/실패시 과거이력 제거를 사용한다. B05 실제script/event fixture·create503에서 DOM실행0·의도밖요청0·스택/비밀노출0이다. 기존CSP/서버마스킹도 유지한다.

승인버튼은 ACTIVE/PENDING/CHECKED argsdigest 일치 조건이다. 클릭즉시양버튼busy, 완료/실패 모두 실제서버 재조회. 최종권한은 정확한 바인딩/PDP/원자reserve/단회소비다. 승인200효과0→동일call resume효과1, DENY해제경로0. UI경쟁제어를 서버안전 증명으로 대체하지 않고 A경쟁회귀 별도실행했다.

human/agent는 DOMpassword/실행메모리만 사용하고 pagehide/pageshow복원에 비운다. 앱persistent storage/cookie/URL저장0. 전용profile formfill/password저장/crashrestore 제한, B07reload/back 값0이다. 모든브라우저/OS forensic완전삭제 증명은 아니다. MCP credential은 stdin만 전달, argv/콘솔0. 스크린샷password/요청/body는 수집전mask, rawHAR/trace/video수집0.

B08은 실제401/429/정상200/대기회복이며 유한메모리큐를 사용한다. 실패이력은 **volatile**, public/internal access log 비활성화, 영속trace 미구현·재시작초기화/다중프로세스 전역제한 미보장(R-B-002). SR2-2 전체준수는 미완료이며 적용P0판단을 관리에 인계한다.

FirefoxNSS는 taskprofile cert9.db의 CA C,,만 import. blank초기화/종료→CA import→검증유지 방문. OS/GPO/개인profile변경0, 미신뢰profile UNKNOWN_ISSUER 확인. UI실행endpoint추가0. private개발CLI만 신규fixtureDB fault/expiry조작 및 실제SDKMCP/Control/effects관측을 한다.

같은session/call의 Control판정을 실제효과로 추정하지 않고 privateexecutor invocation/effectsDB를 별도대조했다. 출처일치는 관측연결이며 인과증명은 아니다. RESULT·FINDINGS·GUIDE_APPLICABILITY는 요구→위험원→코드→진단→동적시험을 연결하며 평가기획서제2항의 구조적예방 근거로 인계한다. 정본기획서 편집은 배정밖이다.
