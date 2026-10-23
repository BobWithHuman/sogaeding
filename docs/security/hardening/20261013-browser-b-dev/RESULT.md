# WP-HARDEN-01 단계 B 결과

작성자: 개발 세션 Codex. 사람 개발자 사용자1명, 별도 AI 검토 보조. SPEC-3 / policy `mvp-2026-10-13-v1`. 지정 브라우저 시험은 통과했으며 관리의 최종 수용/상태 판정이 남는다.

## 후보와 환경

- A69파일 기준 `6c6d6a98e33fff4177293022f61c4a33956192dc427b24f01d42f71a5e825423` 대조. B 변경 전 `baseline-image-source`75파일/A 불일치0, baseline제품30 PASS.
- 제품 변경은 `control/main.py` 설정 포트 Origin 검사와 `web/ui.js` 안전 오류·재조회·버튼·자격증명 화면 처리뿐이다. 정책/DB/API/공개계약/기존Compose 변경0. 신규 `compose.browser.yaml`·시험도구·fixture 추가.
- 최종88파일 fingerprint **`9553fd7be6fb9c60a88c853939216530abad0ababa59a393cac4fa7a9b7b5159`**, `artifacts/20261013-browser-b/demo-normal-smoke-source/manifest.json`. 각 최초 시험은 자기 `*-source`/`*-command.json` 당시hash·UTC·exit와 연결한다. 최종hash를 실패에 소급하지 않았다.
- image digest `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`. source는 읽기전용 mount이므로 image만으로 후보를 식별하지 않는다. Python lock 변경0.
- 전용 Docker `with-human-browser-b`, 신규 control/effects 볼륨·역할별키·가짜자료·host8010/8011. 기존앱/DB/runtime/증거 교체·삭제0. internal8443 mTLS+service bearer.
- 실제 Firefox153.0/revision1538 + Playwright1.62.1. 전용 NSS profile CA, `ignoreHTTPSErrors:false`; 별도 미신뢰 profile UNKNOWN_ISSUER 거부. Windows전역CA/개인profile 변경0. 도구 출처/hash/license/audit/실패: [TOOLING.md](TOOLING.md).

## 실제 브라우저·효과

원본 `artifacts/20261013-browser-b/browser-ui-r1-synchronised/cases.json`, `browser-metadata.json`, B01~08 마스킹PNG. 같은 session/call/approval/args digest를 화면 text·Control timeline·private executor/effects DB로 연결했다. 실제 MCP SDK REPLAY이며 유료 모델 LIVE는 아니다. 효과는 해당 세션 누적값이다.

| ID | 관측 결과 | 판정 |
|---|---|---|
| B01 | UI요청→issue/readme 읽기 invocation2/effects0; 정확댓글 ALLOW/SUCCEEDED invocation1/effects1 | PASS |
| B02 | CONFIRM→UI APPROVED 효과0→동일call resume CONFIRM/CONSUMED/SUCCEEDED 효과1; replay추가0 | PASS |
| B03 | 거절0, 만료409/EXPIRED/0; 연속클릭 API1·양버튼busy; 변형args0, 정확resume총1 | PASS |
| B04 | 금지댓글/SECRET_ENV DENY·이유표시·승인버튼0·executor/effects0 | PASS |
| B05 | HTML/script/event text표시·실행0·의도밖 페이지요청0; source≤512/canary마스킹; 실제create503 안전오류/과거화면제거/스택노출0 | PASS |
| B06 | wrong/agent/service UI bearer401·과거화면제거; closed승인403/버튼0; expired상태; 보존경과403/404; 잘못UUID 초기화 | PASS(계약구분 아래) |
| B07 | local/sessionStorage/cookie/cache/SW0·URL credential0·수집console0; reload/back password0; 다른Origin차단/효과0 | PASS(관측profile 범위) |
| B08 | 실제bad bearer429 도달→정상human200→10.5초대기 후bad bearer401 회복·효과0 | PASS(유한 제한/회복 범위) |

Closed/expired의 보존기한 전 사람 timeline조회는 SPEC-3에서 허용한다. UI는 해당 상태를 표시하고 승인 실행 가능으로 오인시키지 않는다. 실행/승인은 거부하며 보존 경과 접근은 거부/삭제한다. 다중tenant 분리를 구현했다고 주장하지 않는다. **B08은 영속 인증 실패 추적 준수를 의미하지 않는다**(R-B-002, 아래).

## 최초 실패·조치·재진단

- `first-browser-session-trusted` create403(F-012): Origin8000고정. CONTROL_PORT의 두loopback Origin을 사용한 `first-browser-session-origin-fix` exit0.
- `browser-ui-initial` B01/04/05/07/08 PASS, B02/03/06 FAIL: 승인/거절 후 과거PENDING(F-013), closed버튼잔류(F-014). 재조회·양버튼잠금·ACTIVE/PENDING/digest조건·revision/실패초기화 수정. 당시 승인직후효과0 및 서버거부 유지.
- `browser-ui-r1` B03실패는 만료 재조회 전 검사한 **시험 동기화 오류**다. 실제409/EXPIRED. 완료조건 보완 후 `browser-ui-r1-synchronised` B01~08 PASS, exit0(2026-10-14 01:59:14Z~02:01:06Z). 이전결과 보존.
- 별도 AI R-B-001: 완전히 빈profile NSS trust실패. blankFirefox 초기화/종료→CA import를 런처에 추가. 신규 `fresh-demo-profile-init`/`fresh-demo-ca-import`/`fresh-demo-smoke` exit0, 승인전후0/resume1.
- Chromium nativeCA선택 승인timeout, Firefox policy미적용, NSSreadonly실패, 최초tmpfs설정실패는 도구준비 실패 원본으로 보존. 제품약점/성공개수에 합산하지 않음.

## 회귀·진단·검토

아래 파일은 `artifacts/20261013-browser-b/`에 각 command UTC/exit/snapshot과 함께 있다.

| 확인 | 결과 / 원본 |
|---|---|
| 변경 전 제품 | 30 PASS45.86초 / baseline-product.txt |
| B 수정 후 제품(A/F008/경쟁포함) | 30 PASS45.91초 / b-r1-product-regression.txt |
| 실제 A 장애peer | 8 PASS8.60초 / b-r1-peer-regression.txt |
| Ruff | exit0 / final-b-lint.txt |
| Bandit | exit1 기존B1043 유지 / initial-b-bandit.txt·final-b-bandit.txt |
| 도구 JS audit | exit0 취약점0(JS3범위) / browser-tool-audit.txt |
| 기존 Docker check | exit0 계약/12예시·하네스1·checker정적진단·pip일관성 / final-harness-check.txt |
| 시연 | 기존·완전히 새profile 각각 댓글1 / demo-smoke.json·demo-smoke-fresh.json·demo-normal-smoke.json·demo-approval-final.json |

시험제품2파일/핵심driver/browser acceptance는911946…→c37acf…→최종9553fd…에서 동일하다. 차이는 시연/도구 추가이며 manifest로 대조한다. 별도 신규profile/session 대표브라우저·효과 및 A회귀: [REVIEW.md](../20261013-browser-b-review/REVIEW.md). 별도 검토 범위·판정은 그 문서가 정본이며 공식 독립기관 진단이 아니다.

## 직접 시연

전용제품 실행 상태, **https://127.0.0.1:8010/**. CA 전용profile과 password필드 준비는 런처가 하며 비밀은 문서/채팅/URL에 넣지 않는다.

```powershell
cd C:\sogaeding
.\scripts\browser_demo.ps1
```

1. 열린 Firefox에서 `세션 만들기`, 터미널 Enter → 실제MCP 다른댓글 후보.
2. 화면본문·call ID·CONFIRM 확인 → `이 후보 승인`. 실제댓글0.
3. 터미널 Enter → **동일call MCP resume** → CONFIRM/CONSUMED/SUCCEEDED·댓글1. 거절하면0.
4. 마지막 Enter로 브라우저 종료. 제품은 계속 실행.

정상 정확댓글의 짧은 시연은 `.\scripts\browser_demo.ps1 -Normal` → 세션만들기 → Enter이며 ALLOW/SUCCEEDED·효과1을 확인한다. 정상요약/정확댓글 및 승인 전체 재현은 `tests/web/browser_acceptance.mjs <새라벨>`과 snapshot wrapper로 수행한다(B01/B02). 외부모델은 호출하지 않는다. 현재leaf인증서2026-10-15약10:41Z/CA10-20 만료. 만료 후 새 별도runtime을 준비하며 검증해제하지 않는다.

## 남은 판단

현재MVP 필수: 관리의 B/A/기존LIVE·현후보 변경영향 대조와 상태판정. **R-B-002/SR2-2: 실패이력이 volatile deque이며 영속기록·재시작/다중프로세스 추적 미구현이다. 적용P0의 남은 처리 판단을 관리에 인계하고 전체준수로 승인하지 않는다.** 이번유료LIVE NOT_RUN, 과거공격미시도와 제품차단 구분 유지.

제출전C/D: 운영키/인증서/DB lifecycle·rotation, 인증실패 영속추적, 설계20/약점49 전수 적용성/비적용근거·native/OS공급망·JS정적검사 보완·재진단·기획서 반영, 기존B104내부allNIC/OS egress제한. 공식빌드라인/조치율 추정0. 미점검PASS/논리purge물리완전삭제/모든IPI·Codex내장shell 보호 주장0. 과거F007/A중간snapshot 공백은 복원하지 않았다.

별도 AI 최종 판정: 제품30/peer8/대표브라우저7/추가경계3 PASS, 신규profile 및 정상/승인시연 재현 PASS. R-B-002는 현재 적용P0 미완료로 유지한다. `artifacts/20261013-browser-b/review-receipt.json`에 REVIEW hash를 연결했다. `evidence-integrity-check`의 명령별hash·기존ledger보존·알려진credential검사는PASS이며 실제issued agent token은 수집전 memory검사/마스킹으로 보호했다(전체OS/OCR삭제검사 아님).
