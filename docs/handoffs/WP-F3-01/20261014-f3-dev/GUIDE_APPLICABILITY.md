# F3 가이드 적용성

원본PDF6개의 hash를재검증하고29페이지를직접추출했다: `artifacts/20261014-f3-01/guide-pages/manifest.json`. 원본/기존증거는읽기전용이다. 관련변경의 실제통제/시험판단이며 전체설계20/약점49완료표가 아니다.

| 요구/원문PDF페이지 | 구현·시험 | 적용판단 |
|---|---|---|
| G3 507/509/511 권한·검증 | hardPDP·role·strictschemas·서버source/refs/정책버전·F3fake/기존회귀 | 해당집행PASS; 모델의 의미진실성은NOT_RUN |
| G3 406/415 경쟁/세션 | 단회analysis/lease·transaction외await·snapshot/reserve·추가효과0 | 단위/실제A회귀PASS; 전운영조합아님 |
| G3 110~112 SR2-2, G2 123/125 | 기존제한+durable401/403/429집계·restart/ASGI故障503 | 좁은persistence보완PASS; 20회정책/분산·원인별forensics는전수가이드준수아님 |
| G2 28/31·G3 66/69 XSS | UItext nodes·소스발췌·원시JSON접힘·실제B05 | 해당DOM/요청/secret시험PASS; BanditJS미지원은PASS아님 |
| G2 133/135·G3 164/169/171 오류 | 예외/timeout/refusal/schema/근거/취소·실행전failclosed | fake/spy/실제peerPASS; 실제API故障NOT_RUN |
| G4 37/38 중요정보 | 암호화snapshot/source·모델마스킹·Control전용키·TLS검증·역할mount·browser환경allowlist | 해당경계코드/회귀PASS; 임의민감정보탐지·provider전보존/물리삭제보장아님 |
| R1 13/14·G1 35/47 공급망 | 기존해시lock/image/SDK2.54·기존Playwright/Firefox·추가설치0 | 새도구체인확대0; OS/native전수/Firefox서명미제공한계유지 |
| G4 24·C1 14/15/26 SDLC/평가 | 요구→위험/경계→source→정적/동적→finding→조치→재진단→독립검토 | 공식빌드라인/조치율 추정0. 기획서제2항근거인계 |

B1043원경고는loopback publish·TLS/mTLS와 내부allNIC/OSegress제한을구분해보존했다. 49개 도구rulecoverage/비적용기능·경로·의존성 전수와native/OS/license은제출전C/D다. 미점검/도구미탐/실제모델미실행을PASS로복사하지 않았다. 현재 F3필수실험과 제출전전수는구분하며 C/D전체를이번선행조건으로추가하지 않는다.
