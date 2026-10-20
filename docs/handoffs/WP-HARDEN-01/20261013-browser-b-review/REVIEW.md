# WP-HARDEN-01 단계 B 별도 AI 검토

검토 run `20261013-browser-b-review`, SPEC-3 / policy `mvp-2026-10-13-v1`. 작성자와 분리된 보조 AI 검토이며 사람 개발자는 사용자 1명이다. 공식 독립 진단기관의 결과가 아니다.

**지정된 실제 브라우저의 유한 기능·효과 검증은 통과했다. 독립 제품 회귀30 PASS, A 장애 peer8 PASS, 자체 브라우저 대표7 PASS 및 추가 권한/세션 경계3 PASS다. 새 프로필의 시연 준비 결함 R-B-001은 수정·독립 재현을 확인했다. R-B-002의 현재 노출 인증 경로에 대한 영속 실패 추적은 미구현이며 관리의 적용 P0 처리 판단이 필요하다. 전체 MVP/가이드 준수 완료를 수용한 검토가 아니다.**

## 기준·읽기·쓰기 경계

- AGENTS, with-human-dev와 workflow/roles/evidence, 단계 B 작업팩 전체, SPEC-3 상태/권한 계약, A RESULT/REVIEW, 관리 상태 및 작성자 B RESULT/SECURITY_DESIGN/GUIDE_APPLICABILITY/TOOLING/FINDINGS를 읽고 실제 코드·원증거와 대조했다.
- 최초 동결87파일 `c37acf3dcba04e83c912aff8ea7152179e05721cb2d438a61e257b8bc13e9ed9`와 실제 파일 hash mismatch0을 확인했다. A69파일과의 기존 파일 변경은 `src/app/control/main.py`, `src/app/web/ui.js` 두 개다. 공개 endpoint/enum/정책/DB 의미·Python lock 변경은 없다. `scope/*.diff`에 독립 diff를 보존했다.
- 검토 지적 후 초기화 도구 추가·시연 옵션 보완으로88파일 `a1c20340fe4e5254e9aa0b25ed34bcacbd93d371ee8077f6672e9b15523d5300`이 됐고, 정상 시연 분기 추가 후 최종 **`9553fd7be6fb9c60a88c853939216530abad0ababa59a393cac4fa7a9b7b5159`**를 확인했다. 정본은 `artifacts/20261013-browser-b/demo-normal-smoke-source/manifest.json`이다. 최초87판과 차이는 demo.mjs/browser_demo.ps1 및 신규 browser_prepare_profile.mjs뿐이다. 제품2파일·핵심 helper/driver/browser acceptance·NSS wrapper·lock은 동일하다. 최종88 실제 hash mismatch0이다.
- 독립 image inspect에서 기존 digest `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`, user `10001:10001`을 확인했다. 읽기전용 source mount이므로 image digest만으로 제품 후보를 식별하지 않는다. `requirements-dev.lock` SHA256은 A와 같은 `4ba8fe14ea9ead50796f2a782a716fde6c9ba0efc6620893544c8ba6f97b1c5d`다.
- 실제 브라우저는 Firefox153.0/revision1538, 기존 Playwright1.62.1·번들 Node24.19.0이다. 자신의 `artifacts/profile-browser-b-review`, `profile-browser-b-review-fresh`만 사용했다. `ignoreHTTPSErrors:false`와 CA 검증을 유지했다. Windows 전역 trust/GPO/개인 프로필 변경0, 원시 HAR/trace/video 수집0이다.
- 브라우저는 전용 `with-human-browser-b`의 localhost8010/8011, 새 세션만 사용했다. 기존 B session/원증거·원래 runtime/DB/볼륨을 수정하지 않았다. 자체 global DB trigger 주입은0이며 expiry fixture는 자신의 approval/session에만 적용했다. A 회귀는 `docker compose run --rm --no-deps dev`의 별도 컨테이너·임시 TLS/DB다. 기존 앱 stop/restart/delete 명령0이다.
- 검토자의 쓰기는 자기 handoff/artifact/profile에 한정했다. 제품·공용시험·계약·plans·harness 장부를 수정하지 않았다. 새 유료 LIVE0, 원격 자료 업로드·메시지 전송0이다.

## 독립 명령·원증거

공통 경로 `C:/sogaeding/artifacts/20261013-browser-b-review/`. 각 label의 `*-command.json`에 실제 argv·started/completed UTC·exit·source fingerprint, `.txt`에 안전한 출력을 보존했다. 매 명령 직전 `browser_evidence.ps1`의 snapshot을 사용했고 최초 실패를 최종 hash로 덮어쓰지 않았다.

| 실행 label | 결과 | 범위 |
|---|---|---|
| profile-ca | exit1 | 완전히 빈 profile의 CERT_ChangeCertTrust 실패 원본. R-B-001 |
| profile-bootstrap / profile-ca-after-bootstrap | 각각 exit0 | Firefox 초기화/종료 후 동일 NSS CA 신뢰 성공 |
| product | exit0, 30 PASS, 48.15초 | 실제 MCP/PDP/reserve/executor, A/F008·승인·경쟁·보존 회귀. `product-traces/product-traces.json` |
| peer | exit0, 8 PASS, 9.54초 | TLS fault peer·취소·receipt 복구. `peer-traces/fault-traces.json` |
| browser-independent | exit1, 6 PASS/1 FAIL | T06의 Node APIRequestContext 별도 CA store에 의한 검증 실패. Firefox 앱 방문/앞선 실제 기능은 성공. 제품 실패로 분류하지 않음 |
| browser-r1 | exit0, 7 PASS | 보조 Node Origin probe에 fixture CA 명시, `rejectUnauthorized:true` 유지 후 대표 전부 재실행. `browser-r1/cases.json` |
| browser-extra | exit0, 3 PASS | closed/expired MCP 거부, agent/service 생성·승인·거절 거부. `browser-extra/cases.json` |
| scope-guides | exit0 | 원본PDF6개 hash·관련 페이지 직접 재추출, A diff/lock |
| image | exit0 | image digest/비root 사용자 읽기 |
| fresh-profile-init / fresh-profile-ca / fresh-demo | 각각 exit0 | 보완된 공식 도구를 완전히 새 자기 profile로 초기화→CA import→실제 브라우저 승인0/resume1 |
| demo-normal | exit0 | 최종 도구 정상 분기: ALLOW/SUCCEEDED·invocation1/effect1 |
| final-verify-first | exit1 | 작성자의 정상 시연 도구 변경 도중 이전a1 snapshot과 현재 파일이 달라 검증 중단. 제품 시험 실패 아님. 갱신된 정본으로 아래 재검증 |
| final-verify | exit0 | 최종88 mismatch0, 독립 브라우저10 PASS, 알려진 현재 credential 텍스트 hit0 |

제품30·peer8·브라우저7/3·시연 smoke는 서로 다른 범위다. 이를 새 NT/AT 수나 LLM 공격 방어율로 합산하지 않는다. 명령 시각의 소스가 달라도 제품·핵심 시험 불변을 hash로 확인한 경우만 결과를 연결했다.

검토자 최초 browser-independent fixture의 파일 복사본은 실행 후 `browser-independent/fixture-as-executed.mjs`에 보존했다. 당시 제품 snapshot은 명령 직전에 있었지만 검토자 별도 fixture manifest는 처음부터 명령 직전 고정되지 않았다. 이를 소급 snapshot으로 주장하지 않는다. 이후 browser-r1부터 `review_evidence.ps1`가 매 명령 전에 자기 fixture 파일/hash/UTC를 `*-review-fixtures/manifest.json`에 추가 고정했다. 과거 F007/A 중간 snapshot 공백도 복원하지 않았다.

## 실제 브라우저·서버·효과 대조

각 자체 case는 rendered DOM·인증된 Control timeline과 private effects SQLite를 함께 확인한다. safe record에는 session/call/approval ID·args hash·UI text·서버 상태·invocations/effects가 있다. credential은 메모리만 사용하고 파일 기록 전에 알려진 bearer가 없음을 검사했다. 마스킹된 T01 화면도 직접 시각 확인했다.

| 자체 ID / B 연결 | 독립 관측 |
|---|---|
| R-B-T01 / B02·03 | exact candidate 표시, 연속 두 click에서 approval HTTP1회, APPROVED 후 invocation/effect0. 변형 body resume 오류·효과0. 같은 call/인자 resume 후 CONFIRM/CONSUMED/SUCCEEDED·invocation/effect1. replay 추가0 |
| R-B-T02 / B03 | UI REJECTED, 승인 버튼0, 실제 MCP resume 거부·invocation/effect0 |
| R-B-T03 / B03 | 자신의 approval만 만료 fixture. approve409→UI EXPIRED, 실제 resume 거부·효과0 |
| R-B-T04 / B04·05 | issue43 실제 읽기1. 금지댓글/SECRET_ENV DENY, 해당 금지 invocation0/effects0. 외부 `<img`는 문자로 표시, img/script/iframe node0·window canary 미실행·probe 요청0·가짜 비밀 마스킹 |
| R-B-T05 / B06·stale | 과거 버튼 DOM reference를 남긴 뒤 session input 변경; 오래된 handler가 보낸 approval 요청0. CLOSED 표시·버튼0. wrong/agent/service timeline 각각401, 이전 이력 empty |
| R-B-T06 / B07 | local/sessionStorage/cookie/cache/SW0, reload/back human·agent password empty. about:blank의 실제 browser cross-origin fetch 거부. 별도 CA 검증 HTTPS probe에서 올바른 human bearer+untrusted Origin403. 두 관측을 구분함 |
| R-B-T07 / B08 | 이전 실패와 같은 프로세스 창에서 bad bearer17회 이내429 도달, 정상 human200, 10.5초 뒤 bad bearer401 회복. 효과0. threshold를 코드에서 복제해 기대값으로 쓰지 않음 |
| R-B-X-close / B06 | 새 session CLOSED 후 actual MCP 인증/호출 거부, human approve403, 버튼0·invocation/effect0 |
| R-B-X-expire_session / B06 | 자신의 session 만료 후 actual MCP 인증/호출 거부, human approve403, UI EXPIRED·버튼0·invocation/effect0 |
| R-B-X-roles / B06 | agent/service 각각 실제 browser fetch로 session create/approval approve/reject401×3. 기존 승인 PENDING·invocation/effect0 |

닫힘/만료 후 보존기한 전 human timeline200은 계약의 이력 조회다. 실행 가능으로 표시하지 않는 것과 실제 MCP·승인 거부를 별도로 확인했다. 단일 인간 사용자 체계이며 다중 tenant 소유권 분리를 검증했다고 주장하지 않는다.

작성자 B01~08 최종 PASS와 최초 B02/03 PENDING 잔류·B06 CLOSED 버튼 FAIL, Origin8010 최초403을 확인했다. r1의 만료409 뒤 즉시 검사한 fixture timing FAIL은 최종 UI EXPIRED record와 동기화 수정 후 PASS가 연결된다. 원본을 PASS로 덮어쓰지 않았다. B01 요약 issue/readme2 및 정확댓글1, B05 create503 safe error, 보존경과 조회는 작성자 증거+독립 A 회귀를 읽어 수용하며, 자신이 새 브라우저로 모두 재현한 것으로 표현하지 않는다.

## 발견과 잔여

**R-B-001 / 개발 도구 재현 결함 / 조치·재진단 확인.** 완전히 새 profile에서 NSS trust 최초 실패를 직접 확인했다. Firefox blank 초기화/종료 후 CA import가 필요했다. 작성자는 최소 초기화 도구와 런처 순서를 보완했다. 자신의 또 다른 새 profile에서 공식 초기화→import→실제 승인 시연을 독립 실행해 성공했다. CA 검증 해제나 기존 profile 재사용으로 성공 처리하지 않았다.

**R-B-002 / 현재 노출 인증 경로의 보안기준 이행 공백 / 미해결.** 원문 G3 PDF110~112/SR2-2는 제한과 실패 추적·영속성 있는 기록을 요구한다. `RequestGuard.attempts/failures`는 volatile deque이고 public/internal Uvicorn은 `access_log=False`, `log_level=critical`이다. 인증 실패의 durable trace는 구현되지 않았다. 이번 B08은 현재 단일 프로세스의 유한 제한·회복 PASS이며 SR2-2 전체 PASS가 아니다. 재시작 초기화·다중 프로세스/분산 제한 및 영속 추적은 입증되지 않았다. 작성자가 RESULT/SECURITY_DESIGN/GUIDE_APPLICABILITY/FINDINGS에 이 미완료를 반영한 것을 확인했다. 현재 적용 P0의 처리를 관리에 인계하며 C/D 전체 보강으로 자동 유예됐다고 수용하지 않는다.

**R-B-003 / 검토 fixture 구성 오류 / 수정·재진단 확인.** Node APIRequestContext는 Firefox NSS의 task CA를 자동 공유하지 않았다. 첫 T06 TLS 검증 실패를 보존했고 Node HTTPS에 고정 fixture CA와 `rejectUnauthorized:true`를 명시해 실제 browser 관측과 별도 서버 Origin probe를 구분했다. 이후 대표7개 전체 PASS다. 첫 실패의 원시 예외는 credential을 마스킹해 저장했다. 브라우저 cert 검증을 끈 조치는 없다.

`final-verification.json`은 현재 source88/known credential 텍스트 검사와 명령/자체case를 연결한다. issued agent credential은 브라우저 runner가 메모리 set과 비교해 저장 전에 검사했다. profile/native binary·모든 과거 credential·OS 전체·forensic 완전 삭제 검사는 아니다. 안전하지 않은 raw trace는 수집하지 않았다.

## 가이드·도구 영향·인계

원본PDF6개 hash를 독립 검증하고 `scope/`에 관련 페이지를 재추출했다. 직접 읽은 핵심은 R1 PDF13~14, G1 PDF35·47, G2 PDF28~31·123~125·133·135, G3 PDF66~69·110~112·164·169·171·511, G4 PDF24·37·38, C1 PDF14·15·26이다. 기타 추출 페이지를 전수 검토했다고 세지 않는다.

외부 issue/DB 조회값→UI textContent/createElement sink→DOM node/실행/요청0으로 SR1-5/W04를 연결했고, 정확한 후보/승인→서버 바인딩/PDP/reserve→효과0/1로 SR1-6/세션·경쟁을 연결했다. 오류·늦은 상태→fixed safe code/revision/초기화→401/409 및 과거이력 empty로 SR3-1을 확인했다. 인증 실패의 원문 요구에는 R-B-002가 남는다. 평가기획서 제2항의 구조적 예방 근거로 사용할 수 있으나 공식 빌드라인/조치율을 계산하지 않는다.

Firefox ZIP/exe SHA256이 다운로드 manifest와 같음을 독립 확인했다. Authenticode `NotSigned`이며 공급자의 독립 예상ZIP digest는 없다. 공식 TLS CDN 출처와 사후 hash는 재현 byte 근거이며 publisher 서명 인증 증명이 아니다. NSS wrapper는 고정 DLL·fixture CA·작업 profile을 사용하고 profile resolved path를 artifacts 아래로 제한한다. [Mozilla NSS 문서](https://firefox-source-docs.mozilla.org/security/nss/runbooks/rootstore.html)의 `C,,` website trust와 [공식 cert.h](https://github.com/mozilla/nss/blob/master/lib/certdb/cert.h)의 certificate/trust pointer API를 대조했다. 직접 trust 범위는 해당 profile뿐이며 제품에 ctypes/native endpoint를 추가하지 않았다.

작성자 pnpm audit0은 JS automation3 component 범위다. Firefox/OS/native 전체 SCA·ABI 수동 검토·전체 공급자 인증/NOTICE/SBOM 완료로 확대하지 않는다. 제품 Python lock/image 변경0. 작성자 최종 Ruff0·Bandit B1043 원경고를 대조했지만 자신이 해당 도구를 새로 실행한 것으로 보고하지 않는다. B104는 내부/allNIC listen과 localhost publish/TLS/mTLS의 구성 의존 경고다. OS egress 전면 차단 증거는 아니다.

사용자 시연 URL은 **https://127.0.0.1:8010/**, 승인 시연 `.\scripts\browser_demo.ps1`, 정확댓글 정상 시연 `.\scripts\browser_demo.ps1 -Normal`이다. 승인 시연은 세션 만들기→Enter로 실제 MCP 후보→정확 본문/call 확인 후 UI 승인(효과0)→Enter로 같은 call 재개(효과1)→이력 확인이다. 자격증명은 런처가 메모리로 채우며 문서·URL·채팅에 제공하지 않는다. CA/leaf 수명과 재발급은 별도 runtime 준비로 처리하고 검증을 해제하지 않는다.

관리에는 B 유한 브라우저 결과와 R-B-002의 현재 적용 P0 판단을 함께 인계한다. 전체 C/D 운영·전수 진단을 이번 B 완료의 자동 선행조건으로 추가하지 않는다. 현재 기능의 필수 통제·재현/최종 LIVE 근거는 별도로 남는다. 신규 LIVE NOT_RUN, 과거 수정 전 정상/NO_ATTACK_ATTEMPT는 최종 후보의 공격 차단 PASS가 아니다. 전체 TLS negative·인증서/키 생명주기, 설계20/약점49 전수 적용성/source→sink/도구coverage·비적용 근거/native 공급망 및 제출 준비는 미완료다.

보호 판단은 관측한 등록 MCP3도구의 Gateway 경로에 한정한다. Codex 내장 shell/file·다른 MCP·호스트 전체·모든 IPI 및 출처 일치의 인과증명을 주장하지 않는다. plans/harness의 DONE 또는 관리 상태는 변경하지 않았다.
