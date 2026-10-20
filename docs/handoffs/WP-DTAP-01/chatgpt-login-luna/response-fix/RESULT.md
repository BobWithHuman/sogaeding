# storage4 실제 응답 실패 조사·진단 보강

2026-10-20. **복구 완료나 새 평가 준비 완료가 아니다.** 사용자 storage4 실행은 broker·공식 과업 시작까지 진행됐지만 첫 모델 HTTP 응답에서 `SIWC_SSE_REQUIRED`로 중단됐다. 로그인·DB·TLS 이전 오류와는 다른 전송 단계다.

두 arm 각1요청·총2요청과 과업2개가 모두UNKNOWN이며 완료된 Luna 응답/과업은0이다. 원 코드의 HTTP status 검사를 통과한 뒤 Content-Type 검사가 실패했으므로 응답은2xx였으나, 정확한 status/Content-Type/본문은 저장되지 않았다. JSON·HTML·헤더 표기 차이 등 구체 원인은 현재 증거로 확정할 수 없다. 공식 judge의 attack_success=false를 엔진 방어 성공으로 세지 않는다. 선택 외 agent 패키지 warning은 이번 stop의 직접 원인이 아니다.

## 미동결 진단 후보

- 요청의 Accept를SSE로 명시하고 MIME 토큰의 대소문자·공백만 표준화했다. 이것이 실제 실패 원인이라고 주장하지 않는다.
- 내부 요청ID·HTTP status·고정 MIME 분류만 같은 STARTED 요청에 기록하고 상태 요약에 표시한다. 본문·원 header·provider ID·credential은 저장하지 않는다. 과거 응답은 소급 복구할 수 없다.
- JSON/HTML/누락/임의 형식은 계속 `SIWC_SSE_REQUIRED`→UNKNOWN/중단이다. 완료 이벤트·정확 모델·usage·단회 실행·API fallback 금지·Jev 정책·비용 상한을 완화하지 않았다.
- 관련59개PASS, 역사 준비본/current-source 동결검사1개 제외. 첫 시험은 tools PYTHONPATH 누락으로59PASS/1실패였고 로그를 보존했다. 제외된 역사 검사를PASS로 계산하지 않는다. Ruff PASS·별도 AI검토 확정 지적0.

제품 소스 변경은 `siwc_transport.py`·`runtime_budget.py` 두 파일과 관련 시험이다. 옛 frozen source·원 DB·claim은 변경하지 않았다. 새 실행본/manifest/run 명령은 만들지 않았고 개발 중 실제 credential·계정 API·모델 호출은0이다. 원429예약·누적4190921/상한5089294/잔여898373 microUSD를 유지한다. 실제 플랜2요청의 사용량은UNKNOWN이며 기록된0토큰을 미소모로 해석하지 않는다.

원증거는 `artifacts/20261020-siwc-response-fix/observation.json`·`focused-tests*.log`·`lint.log`·두 제품 diff다. [USER_RUN](../USER_RUN.md)은 실행 중단 상태로 바꿨다. 다음은 실제 응답 프로토콜 식별이며 전체100×2 재시작이 아니다.

보안 근거: `docs/plans/03_guide_compliance.md` G-07/G3 PDF507·511의 안전한 오류·민감정보 비노출 원칙을 고정 분류 진단과 거부 시험으로 연결했다. 공식 SIWC 요구: https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference — stream=true/store=false와 response.completed 확인. 비정상 형식의 의미를 추정해 성공으로 승격하지 않는다.

## 후속: 새 공개 문장 단회 연결진단 준비

사용자 “그럼 이제 뭘해야해”에 따라 [USER_PROBE](USER_PROBE.md)의 명령을 준비했다. 별도 bundle10파일·manifest `6c057571e87137faaff64e6e5332d65d64717575df2e72ede88c2f22eafda981`, Responses POST 최대1·60초/2MB·Luna low·기존 main 계정 binding이다. 원 DTAP 요청의 재전송/재개가 아니며 원 DB·claim을 변경하지 않는다. API키·Jev·도구 실행·소켓 mount가 없고 다른 모델 전환도 없다. 실제 모델 호출은 사용자가 -SendOneRequest를 선택할 때만 시작한다.

새 진단 시험57PASS/역사동결검사1제외, lint 잔여0·PS 구문PASS, 실제 launcher→worker UID10001의 frozen verify·증거폴더쓰기·networknone/credential무mount 사전검사PASS다. 첫 시험의 HTML SafeError 미처리2건은 수정 후 재검증했고 실패 로그를 보존했다. G3 PDF511/SR3-1 원문을 다시 대조해 임의 오류 내용 비노출·고정 오류분류·실패UNKNOWN/단회claim 보존을 연결했다. 원증거 `artifacts/20261020-siwc-protocol-probe/`.

단회 진단은 준비됐지만 실제 응답 원인과 모델 복구는 여전히NOT_RUN/미확정이다. 성공 결과도 벤치마크 정확도로 세지 않는다. 플랜 잔여UNKNOWN·누적 API 상한/기존 지출은 그대로다.

별도 검토의 P1(진단 코드/evidence의 넓은 상속 변경 권한)은 새 artifact 전체의 사용자/SYSTEM 전용 DACL과 Python/credential 연결 전 호스트 source/ACL 검증으로 수정했다. 보호된 bundle 런처의 실제 preflight-private PASS, 공개 프로젝트 런처 거부PASS, metadata 재검토로 종결했다. 위 내용은 v1 준비 당시의 역사 기록이며 최신 USER_PROBE는 아래 v2를 따른다. 기존 진단 manifest/PS는 preserved-before-acl에 보존하며 실제 credential 저장소는 변경하지 않았다.

## v1 AUTH_OR_LOCAL_FAILURE 후속과 v2

사용자가 v1 진단을 실행했으나 광범위한 예외 처리로 실패 단계와 구체 오류가 누락됐다. 인증 실패나 Responses 미전송을 확정할 수 없으며 원 claim/result는 보존한다. 실제 파일의 소유자/읽기 metadata는 정상이고, 기존 frozen helper의 live server account-check는 동일 계정 Luna low를 확인했다(추론NOT_RUN). 원 v1 오류의 소급 원인은 미확정이다.

v2는 고정 단계·예외 class/StopRun code allowlist를 기록하고 응답 중 예외에서도 HTTP/stage/POST attempted를 보존한다. 기존 trusted model-check metadata를 계정/model/low와 대조해 반복 catalog GET을 제거한다. --CheckLogin은 실제 credential의 정상 access/필요시refresh만 확인하고 모델 POST·claim을 소비하지 않는다. 이 경로는 AUTH_READY/inferenceNOT_RUN으로 통과했다. fresh token이면 서버 GET 없이 끝나므로 서버 추론 권한의 새 검증으로 해석하지 않는다. 별도로 수행한 기존 helper의 catalog GET 성공과 구분한다. 실제 token/응답본문은 모델 컨텍스트나 로그에 노출하지 않았다.

새 공개 prompt READY·별도v2 root·새claim을 사용하며 v1의 OK/DTAP UNKNOWN 재전송이 아니다. bundle10파일·manifest `52575b21dd4b2f4ecc7c62dd8f227eef3379bbc4083ef8f26c25203078609036`, 사용자/SYSTEM 전용 ACL·모든 source 사전검증을 유지한다. 개발 검증은63PASS/역사1제외, 이후 응답준비 단계 표기 수정의 영향16PASS, 최종UID/networknone preflight와 실제worker/가짜credential/loopback HTTP 전체main PASS다. 초기 worker-fixture의 progress 인자 누락은 fixture를 고쳐 재검증했고 실패 로그를 보존했다.

원증거 `artifacts/20261020-siwc-protocol-probe-v2/prepared.json`. 현재 실제 v2 모델POST는NOT_RUN·개발 모델POST0이며 누적4190921/상한5089294/잔여898373 microUSD를 유지한다. 기존 helper account-check와 v2 access 확인은 실제 전용 인증 helper의 정상 사용이며 실제 credential 파일을 전혀 쓰지 않았다고 표현하지 않는다. API 키·Jev·DTAP실행·모델대체·fallback은 없다. 사용자가 USER_PROBE의 새 단회 명령을 선택하며 전체평가는 아직 재개하지 않는다.

## 최신: v2 실제 SSE의 Content-Type 누락과 공유 파서 수정

사용자 v2 실제 결과는 HTTP200·body_kindSSE·6357bytes·빈media_type였다. 구버전이 완료 이벤트/usage 검증 전에 Content-Type만으로 거부한 원인을 확인했다. 어디서 헤더가 누락됐는지는 미확정이며 provider 오류라고 단정하지 않는다. 본문의 SSE 분류는 prefix 관측으로, 실제완료/정확모델/usage 성공을 소급 확정하지 않는다. 원 v2 result/claim은 그대로다.

공유 completed_stream은2xx이며 명시적인 MIME 충돌이 없는 경우에만 SSE 본문 검증에 진입한다. 헤더가 없으면 라인 framing·event/type 일치·JSON 구조를 추가 검사하고 모든 경우에 정확MODEL·단일 completed terminal·정수/비음수usage·전체EOF를 요구한다. JSON/HTML·불완전·타모델·잘못된usage는 거부한다. shared PlanTransport와 진단이 같은 parser를 사용하며 원 권한/namespace/callID·정책·Jev/confidence·fallback/UNKNOWN 원칙은 유지한다.

별도 검토에서 null/누락된 첫 completed 뒤 정상completed가 오면 기존 sentinel이 중복을 놓치는 P2를 발견했다. 독립 terminal_seen과 첫 terminal dict 검사로 고치고 반례8종을 추가했다. 최종 관련91PASS/역사동결검사1제외, lintPASS다. 실제 worker UID10001·가짜credential·loopback HTTP가 Content-Type 없이 SSE를 반환하는 전체main에서 HEADERLESS_FULL_SSE/COMPLETED를 확인했다. 이것은 실제 Luna 응답 성공이 아니다.

v3는 별도 공개CONNECTED·새claim·동결10파일·manifest `1ebfcfe637b58e7af67fcb2e05d1a88543145a1a238456c8790573dccdb0d290`다. 보호ACL/host source검사·단회1POST·60초/2MB·noAPIkey/Jev를 유지하고 신규 실계정API/모델호출은0이다. 실제 v3 확인은NOT_RUN이다. 현재 USER_PROBE의 v3만 선택하며 기존 UNKNOWN을 재시도/환불하지 않는다. 원증거 `artifacts/20261020-siwc-protocol-probe-v3/prepared.json`.

전체DTAP 실행용 소스/원장/서비스를 교체한 것은 아니다. 실제 단회 연결 확인 뒤 두조건 runtime의 새 동결·부모/UNKNOWN/플랜 원장 연결을 검토해야 하며 전체비교는IN_PROGRESS다. API 누적비용4190921/상한5089294/잔여898373 microUSD·플랜잔여UNKNOWN을 유지한다.


## 사용자 v3 실제 결과

2026-10-20: COMPLETED/HEADERLESS_FULL_SSE, HTTP200·빈MIME·usage12/5를 원 result.json으로 확인했다. 실제 최소 로그인 전송은 복구됐다. DTAP 점수나 function-tool 실제 모델 성능은 이 호출로 검증하지 않았다. 새 실행 절차는 상위 USER_RUN.md를 따른다. 원 UNKNOWN/claims는 보존한다.
