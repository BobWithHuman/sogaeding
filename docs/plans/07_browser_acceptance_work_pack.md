# WP-HARDEN-01 단계 B: 실제 화면과 사용자 흐름 검증

> **B 인계 검토 후:** 유한 브라우저 기능·효과 범위는 수용했다. 현재 R-B-002 필수 잔여와 최종 연결 근거는 [MVP 마무리 작업서](08_mvp_final_closure.md)를 따른다. 아래 B 배정은 당시 기록이며 C/D 전체는 제출 전 보강이다.

PLAN-2 후속 / 2026-10-13 KST. 단계 A의 유한 보존·장애 범위는 [관리 판정](reviews/WP-HARDEN-01_A_20261013_management.md)에서 수용했다. **현재 배정은 B**다. 사람 개발자는 사용자 1명이며 기존 개발 세션에서 이어간다. [ADR-M01](decisions/ADR-M01_mvp_completion_scope.md)에 따라 B와 현재 기능의 필수 보안·재현/LIVE 근거를 확인해 MVP 동작 완료를 판정한다. C/D 전체 운영·전수 보강은 대회 제출 전 작업으로 분리했다. 현재 완료 상태를 자동 승격하지 않는다.

## 1. 현재 기준과 이번 목표

- SPEC-3 / policy `mvp-2026-10-13-v1`.
- [A RESULT](../handoffs/WP-HARDEN-01/20261013-harden-a-dev/RESULT.md), [별도 A REVIEW](../handoffs/WP-HARDEN-01/20261013-harden-a-review/REVIEW.md), [전체 보완 작업팩](06_mvp_completion_work_pack.md)을 읽는다.
- 최종 A fingerprint `6c6d6a98e33fff4177293022f61c4a33956192dc427b24f01d42f71a5e825423`, manifest69파일이 관리 확인 시 실제 파일과 일치했다.
- 저장된 독립 결과는 제품30 PASS / fault peer8 PASS / 자체 재현3 PASS다. 서로 다른 시험을 새 NT/AT 개수로 합산하지 않는다.
- A 검증은 전용 임시 제품 환경에서 수행됐다. 공유 Compose 서비스가 A 코드로 재배포됐다는 증거는 없다. 기존 서비스의 화면을 열었다는 사실만으로 A 후보 검증으로 세지 않는다.
- 현재 `tests/web/test_shell.py`는 JS 문자열 점검이다. **실제 브라우저에서 현재 후보를 조작하고, UI·Control 이력·private executor 효과를 같은 run으로 연결**하는 것이 B의 목표다. 미관 개선·새 도구·새 에이전트 개발을 병행하지 않는다.

## 2. 한 작성자가 진행할 순서

1. 변경 전 기준 source/image/lock과 실제 명령 시각을 고정한다. A의 기존 코드/시험을 보존하고 현재 환경을 확인한다.
2. 가짜 자료·서로 다른 테스트 자격증명·전용 DB/볼륨·포트를 가진 제품 인스턴스를 띄운다. 브라우저가 실제로 연결한 host/port와 코드 fingerprint를 기록한다. 기존 runtime의 키를 교체하거나 DB/원증거를 삭제하지 않는다.
3. 실제 브라우저를 실행해 아래 유한 시나리오를 검증한다. 처음 실패가 나온 경로는 좁게 수정하고 관련 정상·보안 회귀를 실행한다.
4. 화면·이력·실제 effects를 대조하고 작성자와 별도 AI가 같은 후보를 검토한다. 사용자에게 접속 URL과 짧은 정상/승인 시연 절차를 제공한다. 시연 계정의 비밀은 RESULT·채팅·URL에 넣지 않는다.

TLS 인증서 검증을 유지한다. 앱 시험에 한정한 브라우저 프로필/컨테이너의 CA 신뢰를 사용하고 사용자 PC 전역 인증서 저장소를 바꾸지 않는다. `ignoreHTTPSErrors`·검증 해제·HTTP fallback으로 브라우저 시험을 통과시키지 않는다. 신뢰 구성 지원이 안 되면 정확한 제한과 대안을 남기고 독립 가능한 시험을 계속한다.

## 3. 필수 브라우저·효과 시나리오

| B ID / 기존 요구 | 실제 조작과 입력 | 확인할 결과 |
|---|---|---|
| B-01 / AC-01·02, FR-01/09 | 요약 작업과 정확한 댓글 작업의 세션 생성, 같은 세션 MCP REPLAY 실행 후 화면 조회 | 요청·출처·판정·실행 상태/효과가 해당 session/call과 일치. 정상 읽기·정확한 댓글1회 실제 완료 |
| B-02 / AC-04, NT-03 | 범위 안의 다른 비민감 댓글 후보를 MCP로 생성하고 UI의 정확한 본문·인자·판정·승인 대상을 확인해 승인 | 승인 클릭만으로 댓글0. 같은 immutable action/call의 MCP resume 뒤 댓글1, 원판정 CONFIRM·승인 CONSUMED·실행 SUCCEEDED 표시. 재조회/재개 추가0 |
| B-03 / AT-05/06/07 | UI에서 거절·만료 후보·연속/중복 클릭, 승인과 거절의 반복 조작 | 잘못된/만료/거절/재사용 승인으로 효과0. 동일 승인 후 정상 resume 총1. 오류·버튼 상태가 실제 서버 결과와 맞으며 클릭 완료를 실행 완료로 표시하지 않음 |
| B-04 / AC-03, AT-01/02 | 요약 세션의 금지 댓글·SECRET_ENV 후보, UI 조회 | DENY 판정·이유가 표시되고 승인으로 해제되는 UI 경로 없음. 금지 executor/effects0 |
| B-05 / AC-08, AT-10 | 외부 제목·본문·오류/긴 값에 script/HTML 이벤트·가짜 비밀 canary, 타임라인 갱신 | 브라우저 JS/XSS 실행0·의도 밖 요청0, 텍스트 표시·길이/생략 일치, 비밀/스택/원문 자격증명 노출0. 구조가 DOM에서 실제로 안전한지 확인 |
| B-06 / AT-08/13 | 잘못된 사용자 토큰, agent/service 역할의 UI API 접근, closed/expired/보존기한 경과 세션, 잘못된 session ID | 서버가 거부하고 이전 화면을 최신 성공으로 오인하지 않게 표시. 현재 단일 인간 사용자 체계에 없는 다중 tenant 소유권 분리를 구현했다고 주장하지 않음 |
| B-07 / AT-10/11 | 새로고침·페이지 종료·오류 후 credential 저장/URL·브라우저 storage·콘솔/증거 확인, 외부 Origin 요청 | 사용자·agent 토큰을 local/sessionStorage·cookie·URL·로그에 지속 저장하지 않음. password 값/응답 원문을 스크린샷·trace에 보관하지 않음. 새로고침 후 브라우저 자동 복원 여부와 앱 저장을 구분 |
| B-08 / SR2-2, W-33 | 유한 횟수의 로컬 인증 실패·잘못된 역할 요청 후 정상 회복 | 문서화한 제한·상태 코드·대기/회복, 유한 자원 사용. 제품 구현과 동일한 테스트 값을 복제해 성공으로 세지 말고 실제 경계에서 관측 |

MCP 호출은 기존 안전한 REPLAY/시험 드라이버로 수행할 수 있다. UI에 새 실행 endpoint를 추가해 Gateway/PDP/reserve를 우회하지 않는다. UI의 사용자 승인은 기존 서버 승인 API만 사용하며 DENY를 승인으로 해제하지 않는다. B-02의 실제 resume를 사용자가 할 수 있는 절차로 설명한다. 별도 유료 LIVE는 이번 B에 필요하지 않다.

## 4. 도구·쓰기 권한과 증거

- 기본은 기존 브라우저 제어/설치된 시험 도구를 사용한다. 해당 도구의 skill/API 지시를 먼저 읽는다. 제품 코드 검사나 HTTP client만 사용하고 브라우저 실행으로 보고하지 않는다.
- **관리 사전 위임:** 기존 도구로 브라우저 검증을 못 하면, 개발 전용 브라우저 자동화 도구·브라우저·프로필 CA 신뢰용 최소 도구를 로컬/시험 컨테이너에 추가할 수 있다. 공식 배포 출처·고정 버전/digest·라이선스·무결성·의존성 영향과 삭제/재현 방법을 먼저 기록하고 audit·관련 회귀를 수행한다. 제품 runtime 의존성으로 확대하지 않는다. 출처가 불명확하거나 새 외부 데이터 전송·권한 확대가 필요한 도구는 후보와 영향만 결정 요청한다.
- 단일 작성자의 허용 경로는 `src/app/web/`, 필요한 Control 안전 출력/입력 처리, `tests/web/`·관련 수용시험, 로컬 browser fixture/runner·증거 도구, 개발용 설정/lock/Docker 설정의 필요한 최소 변경, 자기 `docs/handoffs/WP-HARDEN-01/<B-run>/`·ignored `artifacts/<B-run>/`다. 공통 DB/권한 정책의 재설계는 이번 B 범위가 아니다.
- `docs/plans/`, `harness/build_tasks.json`, AGENTS·설치 skill·공개 계약·기존 handoff/원증거는 읽기 전용이다. 실제 필요가 생긴 공개 API·enum·권한 의미 변경만 결정 요청한다. 배정 범위의 버튼/오류/안전한 표시 개선은 계속 진행한다.
- **새 증거 절차:** 각 최초 진단/시험 직전에 manifest를 고정해 그 명령의 `source_fingerprint`로 사용한다. 내용이 같으면 동일 snapshot를 재사용해도 되지만 명령 시점에 같은 hash임을 확인한다. 최초 실패의 fingerprint를 최종 수정판 fingerprint로 덮어쓰지 않는다. `command UTC·exit·원본·case별 실제 effects·수정·재진단`을 연결한다. A의 과거 중간 snapshot 공백을 복원했다고 주장하지 않는다.
- 브라우저 버전/프로필 신뢰 범위, 제품 image/source, session/call/approval ID, 실제 요청 조건·UI/서버 상태·effects 전후, 안전한 화면 캡처와 결과를 기록한다. 원시 브라우저 trace/network log에 자격증명·token 발급 응답이 들어가지 않도록 수집 전에 구성한다. 마스킹하지 않은 raw trace를 안전한 증거로 간주하지 않는다.

## 5. B 완료와 인계

B-01~08의 적용 결과·미실행·실패를 구분하고 관련 제품/A 장애 회귀를 통과시킨다. 별도 AI가 새 diff와 대표 브라우저 흐름·effects를 재현/대조한다. 확인하지 않은 범위를 PASS로 복사하지 않는다.

새 `RESULT.md`, `SECURITY_DESIGN.md`, `GUIDE_APPLICABILITY.md`, `FINDINGS.jsonl`과 별도 `REVIEW.md`에 B 결과를 기록한다. 남은 항목은 ADR-M01에 따라 **현재 MVP의 필수 통제/재현/LIVE**와 **제출 전 C/D 전수 보강**으로 나눈다. 사용자 시연용 URL·세션 준비·승인→MCP resume→화면 갱신의 짧은 설명을 포함한다. B 결과와 필수 근거를 관리 세션이 대조한 후 MVP 동작 완료를 판정한다. C/D 전수 완료나 대회 제출 준비 완료를 주장하지 않는다.

## 6. 기존 개발 세션에 보낼 메시지

```text
$with-human-dev

관리 세션에서 WP-HARDEN-01 단계 A의 지정 범위 완료를 수용했어.
docs/plans/07_browser_acceptance_work_pack.md를 전체 읽고 단계 B를 진행해줘.
현재 A 최종 후보를 기준으로 실제 브라우저의 요청·이력·승인·거절·XSS·토큰 저장·인증 제한을 검증하고,
화면·서버 상태·실제 executor 효과를 연결해줘.
변경 전/각 최초 시험의 기준선을 고정하고 필요한 결함을 수정한 뒤 기존 A 회귀와 별도 AI 검토를 수행해줘.
최종 RESULT/REVIEW 경로와 내가 직접 확인할 로컬 URL·짧은 시연 절차를 알려줘.
```
