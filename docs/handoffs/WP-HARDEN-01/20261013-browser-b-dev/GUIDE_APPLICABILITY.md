# 단계 B 가이드 적용성

원문PDF6개 hash/1-based페이지: `artifacts/20261013-browser-b/guide-pages/manifest.json`. 기존PageIndex와 대조해 직접추출했다. 전체설계20/약점49 PASS가 아닌 B변경 적용성이다. A판단은 기존handoff를 유지한다.

| 연결 | 읽은 원문PDF페이지 | 실제근거·판단 |
|---|---|---|
| SR1-5/W04 XSS | G2 28~31, G3 66~69 | ui.js textContent/안전오류, B05 DOM·요청·마스킹PASS; Bandit JS미지원은PASS아님 |
| SR2-2/W33 인증제한 | G2 123~125, G3 110~112/507 | B06/08 실제401/429/200/회복PASS. 실패기록volatile, durable trace미구현·restart/다중process 한계(R-B-002); 전체준수미완료 |
| SR3-1/W36~38 오류 | G2 133/135, G3 164/169/171 | 안전오류/revision, B05 create503·A audit latch회귀PASS; 모든예외 전수아님 |
| SR4-1/W20 정보보호 | G4 24/37/38, G3 507/509/511 | token메모리/pagehide·source마스킹·NSS TLS·B07/A회귀; OS/native/물리삭제/rotation미완료 |
| W34 승인/경쟁 | 기존A guide reference·SPEC3 | busy/digest/PDPreserve, B02/03·A경쟁회귀PASS; 서버단회보호 A동일코드 |
| R1/G1 공급망 | R1 13/14, G1 35/47 | 공식CDN·고정SHA·license·devlock/auditJS3취약점0. native/OS전수·공급자 서명미확인, Authenticode NotSigned |
| C1 평가기준 | C1 14/15/19/20/22/26 | 요구→경계→source→진단→실행→최초/조치/재진단ledger. 공식빌드라인/조치율추정0 |

G3p110은 인증횟수뿐 아니라 실패추적도 요구한다. B08제한동작으로 전체P0준수를 주장하지 않으며 남은처리판단은 관리에 인계한다. 기존B1043도 내부bind/실제loopback/mTLS범위를 구분해 유지한다. 도구미탐/미점검/전수미완료는PASS로 세지 않는다.

사용자지정PDF예시는 전송권한이 아니다. officialbinary download+localhost시험만 추가했으며 자료/키원격업로드·배포·메시지전송0. 제출전C/D에 설계20/약점49 전수적용성/비적용기능·실행경로·의존성근거·별도검토와 재진단을 남겨야 한다.
