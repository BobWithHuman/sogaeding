# F3 보안 설계

위험원은 외부 tool 자료의 새로운 지시/위조권한, 후보의 임의권한확장, 비밀전송, 모델허위근거/거절/지연, 분석중 문맥/버전변화, 병렬·재사용·취소다. 서버grant와 사용자원문은 외부데이터와 분리한다. 추가도구/범용shell/URLexecutor를 만들지 않았다.

정책 검사로 명확한 읽기/EXACT본문 ALLOW, scope/민감자료/예산위반 DENY를 우선한다. 추가후보는 성공한read의 call/session/tool/대상·서버수집시각으로 근거를 구성하고 mask·UTF8/문자/개수/총량·complete·암호화 저장을 적용한다. 문자열일치는 관측자료이며 공격확정 규칙이 아니다.

A입력에는 외부source가 없고 B만 고정source와 Unicode span을 받는다. 고정developer instructions와 별도user JSON으로 분리, 기대정답/fixtureID/harness미주입, tools0·공식SDK2.54HTTPS·proxy상속0·redirect0·retry0·storeFalse. Control전용secret은Gateway/브라우저/actor에 제공하지 않으며 browser child환경도 allowlist로 제한한다.

서버는 strict schema/enum/sourceID·문자위치·실제quote/A금지ref/B동일이슈근거를 검사한다. hard금지를 해제하지 않고 외부NEW_INSTRUCTION은DENY, 양관점 정상TASK_DATA 지지는ALLOW, 정상권한내 불확실성만CONFIRM, API/근거실패는DENY다. EXACT mismatch는 의미지지가 있어도 예외확인으로 남긴다. 모델은승인/예약/도구권한을 갖지 않는다. schema준수는 의미의 진실성 보장이 아니다.

원자budget/client/call/lease/snapshot 고정 후 transaction을닫고 API await. 최종판정과reserve에서 세션/grant/policy/인자/backend/user/source revision/model/prompt/schema를 재확인한다. 단회캐시·session분석2개·총24attempt·유료재분석0. stale/취소/lease만료는 실행전DENY. 실행후불확실성은 기존UNKNOWN이며 budget환불/자동위험재시도0. 성공replay는executeFalse·기존receipt다.

UI는 기존textContent/CSP/오류allowlist/revision/양버튼busy/pagehide/storage미저장을 보존한다. 한국어판정·짧은source excerpt·실행상태를 우선하고 JSON상세는접는다. UNKNOWN/RESERVED는효과불명/확인중, receipt있는결과만확인된효과수로표시한다. 실제DB효과와UI상태를 별도대조하고 출처일치를 인과증명으로 확대하지 않는다.

인증감사는 credential-free 거부상태집계를 별도DB에24h보관한다. status/surface/10초bucket/count/time만남기고 raw토큰/hash/IP/URL미저장. 감사장애는503/handler미진입. 순수인증원인분류·분산throttle/fullSR2-2준수는별도다.

시험과SAST/별도finding 최초·조치·재진단은 RESULT/FINDINGS/독립REVIEW에 연결한다. 평가기획서제2항에 사용할구조적예방 근거이며 정본plans/기획서 편집은 관리범위다. 실제모델/브라우저 자동의미판정은 사용자 실행전NOT_RUN이다.
