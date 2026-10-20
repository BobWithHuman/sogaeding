# WP-MVP-01 별도 AI 검토

review_run_id: `20261013T084627Z-review-ai-7421`  
검토 착수 UTC: `2026-10-13T08:46:27Z`  
검토 종료 UTC는 자기 `artifacts/20261013T084627Z-review-ai-7421/review-summary.json`의 `completed_at`을 따른다. 최종 TLS 시험 delta 확인까지 포함한다.  
검토 역할: 제품 작성자와 분리된 AI 검토. 실제 사람 개발자는 사용자 1명이다. 공식 독립진단기관의 진단이나 추가 사람의 검토가 아니다.

**판정: 최초 P1 정탐 1건(F-008)을 발견했고, 작성자의 R1 수정 후 동일 조건 및 정상·승인·경쟁 회귀를 독립 재현해 제거를 확인했다. 현재 검토 범위의 미해결 차단급/P1 정탐은 없다. REPLAY core와 전체 MVP는 여전히 미완료다.** 미실행·증거 부족을 무약점/PASS로 바꾸지 않는다. 관리 담당이 최종 상태를 판정한다.

## 1. 고정 기준과 경계

- PLAN-2 / ADR-S01 / MVP-SPEC-3 / policy `mvp-2026-10-13-v1`.
- 최초 개발 fingerprint: `1ccca93b6a55a2976630988c41cc200ba48c60e4db74963c6e17b97a32337ea8`. `source-manifest.json`을 최초 검토 시 파일과 비교해 모두 일치했다. 결과: `artifacts/20261013T084627Z-review-ai-7421/manifest-verification.json`.
- R1 fingerprint: `b984c8c15d104d2ddb19f001b990f597ca36ec53d84a14dd83e5e6e36250656b`. `source-manifest-r1.json`의 50개 파일 모두 hash 일치. 결과: `manifest-r1-verification.json`.
- 최종 fingerprint: `8e48b00ceac5803b034d85da55c383980f0e31ce230c9dab21deb1aa0cb6fa27`. 최종 manifest50개 hash 일치. R1 대비 delta는 `tests/transport/test_tls_prepare.py` 한 파일뿐이며 제품 코드는 같다(`final-manifest-delta.json`).
- 기준 개발 handoff: `docs/handoffs/WP-MVP-01/20261013T073853Z-dev-3980e4/RESULT.md`, `SECURITY_DESIGN.md`, `GUIDE_APPLICABILITY.md`, `FINDINGS.jsonl`, `decision_request.md` 및 그 run의 안전한 원증거.
- AGENTS, with-human-dev의 workflow/roles/evidence, 관리 00/02/03/05, 제품 00~07, 기계 계약, 작업 장부, 가이드 manifest/분석과 관련 원문을 대조했다. Git은 제품 변경들이 untracked인 초기 저장소이므로, 존재하지 않는 commit diff 대신 보존된 baseline과 source manifest를 사용했다.
- 검토자의 쓰기는 자기 handoff 및 ignored artifact에만 수행했다. 제품·공용 설정·계약·plans·작업 장부 수정, 공유 서비스/DB/volume reset·재기동, 유료 LIVE 추가 호출은 하지 않았다. F-008 수정 및 공유 gateway 중지는 작성자가 수행했다.
- 실제 서비스/DB는 각 Docker run의 `/tmp`에 만든 TLS/mTLS·가짜 DB·제품 subprocess다. 제품의 인증/PDP/reserve를 mock하지 않았다. 동일 포트를 쓰는 두 fixture는 별도 컨테이너로 분리했다.

## 2. 실제 재현

아래 증거의 공통 경로는 `C:/sogaeding/artifacts/20261013T084627Z-review-ai-7421/`이다. 명령의 전체 인자·실제 시작/종료 UTC·exit code는 해당 `*-command.json`에 있다.

| 실행 | 결과 | 실제 효과·의미 | 증거 |
|---|---|---|---|
| 최초 고정 제품: `docker compose run --rm --no-deps dev python -m pytest tests/backend tests/transport tests/web tests/acceptance -q -p no:cacheprovider` | exit 0, 23 PASS, 8.93s | 대표 정상·DENY·비밀읽기·정확승인/경쟁·report손실 경로 재현. 전체 NT/AT 모든 변형 완료는 아님 | tool output 관찰. 최초 명령의 별도 start 시각/파일 원본은 미수집; R1은 아래에 완전 수집 |
| 최초 독립 `test_review_faults.py` | exit 1, 1 FAIL/1 PASS, 3.36s | source저장 실패 뒤 UNKNOWN인데 다음 댓글의 executor/effects가 1. F-008 정탐 | `review-fault-tests.txt`, `review-fault-command.json` |
| R1 제품과 독립 fixture를 한 pytest에서 합친 시도 | exit 1, 24 PASS/3 setup ERROR, 10.93s | 두 fixture가 같은 컨테이너의 8000/8001/8443를 점유한 검토 실행 구성 오류. 제품 결함/차단 성공으로 계산하지 않음 | `review-r1-tests.txt`, `review-r1-command.json` |
| R1 제품 전체: 독립 Docker run, `tests/backend tests/transport tests/web tests/acceptance` | exit 0, 24 PASS, 9.56s | 정상 댓글의 실제 issue/body/call 복호화 대조, DENY/비밀0, 승인0→1/replay추가0, 두 종류 경쟁 최대1, UNKNOWN/예산 및 source 장애 후속0 | `review-r1-core-tests.txt`, `review-r1-core-command.json`, `core-r1/product-traces.json` |
| R1 독립 보완: 별도 Docker run, 자기 `test_review_faults.py` | exit 0, 3 PASS, 3.50s | 같은 source fault 뒤 댓글0; 미리 만든 ALLOW call의 reserve도 차단; source없는 receipt-only 성공확정 거부; source복구+실제receipt 대조 후 읽기 재실행0/정상댓글1. 실제 SessionCreated/Timeline/CheckReply schema 확인 | `review-r1-fault-tests.txt`, `review-r1-fault-command.json` |
| 원문/manifest/민감정보/행수 대조 | exit 0 | 관련 PDF 6개 해시 일치, 설계20/약점49행·중복0, scoped 실제 credential marker hit0 | 자기 `check_evidence.py`, `safe-evidence-summary.json`, `pdf-verification.json` |

R1 제품과 독립 보완은 별개 실행의 24+3 시험이다. 이를 27개 제품 수용시험이나 전체 core 통과로 재번호하지 않는다.

최종의 좁은 시험 delta: 작성자가 준비 fixture의 plaintext negative를 실제 SSL listener에 credential 없는 HTTP를 보내 handshake 거부/handler 도달0을 검사하도록 보강했다. 독립 `docker compose run --rm --no-deps dev python -m pytest tests/transport -q -p no:cacheprovider`는 exit0, **2 PASS, 1.42s**다(`review-final-tls-tests.txt`, `review-final-tls-command.json`). R1 제품 코드가 그대로라 관련 TLS 시험만 다시 확인했고 정상·승인·경쟁의24+3 결과는 R1 fingerprint에 그대로 연결한다. 제품 자체의 credential 없는 HTTP 거부 시험은 R1 전체 제품 시험에도 존재했다.

## 3. 발견·조치·독립 재검증

### F-008 / P1 정탐: 필수 출처 기록 실패 뒤 후속 쓰기 실행

연결: **SEC-07, AT-09, AC-06**, G3 SR3-1(PDF511), W-37/W-38; G4 예외처리(PDF38).

최초 위치: `src/app/gateway/main.py:129`의 예외 처리와 `src/app/storage/repository.py`의 기존 `check`/`reserve`. Gateway는 읽기 실행 뒤 source 저장 실패를 개별 call UNKNOWN으로 보고했으나, 저장소는 같은 세션의 미해결 UNKNOWN을 새 검사·새 예약의 차단 조건으로 사용하지 않았다. POST_COMMENT의 쓰기 예산은 아직 1이라 다음 정확한 댓글이 정상 게시됐다.

재현은 자체 DB의 sources INSERT에만 fail trigger를 넣어 실제 MCP get_issue를 호출한 뒤 같은 세션에서 정확한 post_issue_comment를 호출했다. 모델/외부 공격자의 DB 변조를 주장하는 시험이 아니라 필수 감사 저장 장애의 주입이다. 실패 시 출처 누락을 가진 실행 흐름이 계속되는 것이 문제다.

- 최초 session `be8385d2-4714-458b-9b2c-438a1d8d7cbf`.
- read call `eefb6c36-8ec3-41c3-89b0-921143590bd8`: UNKNOWN, 반환 data 없음.
- 후속 write call `4f055e6b-389f-4966-a5e8-775398bd9f61`: SUCCEEDED; 댓글 executor 1, 실제 댓글 1. 기대는 후속 금지 실행 0.
- **최초 FAIL 원본은 `review-fault-tests.txt`에 그대로 보존했다.** 작성자 장부 F-008과 연결된다.

권고한 수정은 unresolved 감사/실행 상태를 세션 단위에서 확인하고, 예약 트랜잭션 안에서 후속 위험 실행을 차단하며, 누락 출처와 효과를 명시적으로 대조하기 전 성공확정으로 풀지 않는 것이었다. 직접 제품을 수정하지 않았다.

작성자의 R1 수정: `repository.py:192` 신규 check UNKNOWN 차단, `:241` reserve UNKNOWN 및 위험쓰기의 다른 RESERVED 차단, `:301` read SUCCEEDED 필수 source 확인, `:332` UNKNOWN read의 명시 source복구 허용. 원판정/승인/예산·reason enum은 유지했다.

독립 재검증:

- session `f24b4d8c-41fe-41c0-9b52-a0da297f8549`; read `43d983f3-0284-460f-931c-8e89959d68ec` UNKNOWN 뒤 후속 쓰기는 오류/NOT_STARTED, executor/effects **0/0**.
- 미리 발급한 ALLOW write의 reserve도 409 거부하여 신규 check만 막는 우회가 없음을 확인했다.
- source가 없는 read에 실제 effects receipt만 보고한 reconciliation은 503 AUDIT_UNAVAILABLE. 누락 감사를 성공 상태로 숨기지 않았다.
- session `3ec52b1d-acd1-4d34-be35-9b2217256d71`; read `62b0ecbb-2522-48eb-8695-90e172f1534f`의 source를 명시 복구하고 실제 receipt를 보고한 후 정상댓글1. read invocation은 1로 유지, 자동 재실행0.
- **R1 판정: 관련 정탐 제거 PASS(이 재현 범위).** 전체 malformed/timeout/취소/동시 장애 조합의 PASS는 아니다.

### 문서 불일치 / 낮은 우선순위 / R1 정리 확인

최초 `docs/mvp/01_requirements.md:3`은 SPEC-2였고 `00_START_HERE.md:3`은 현재 묶음을 SPEC-2로 설명했다. `06_today_execution.md`는 과거 SPEC-2 내부 HTTP 주소를 새 HTTPS 주소로 치환해 역사 설명이 모순이었다. README도 과거 준비 기록이 최신 안내보다 앞에 있었다. R1의 현재/과거 구분과 SPEC-3 header 정리를 확인했다. 이 지적은 인증 우회 결함이 아니다.

### F-007 / 초기 진단 source 추적 증거 공백 / 미해결

최초 Ruff/Bandit raw output 및 수정/재진단 원본은 존재하지만, **최초 SAST 직전 제품 전체 source snapshot/hash와 정확한 command start UTC가 없다.** 초기 metrics/snippet으로 전체 source를 재구성할 수 없다. 개발 장부가 이를 F-007로 명시한 것은 맞다. 현재/R1 manifest가 일치해도 과거 처음부터 완전한 source→발견→수정 추적 PASS로 소급하지 않는다. 후속 run부터 정확한 source/image/lock·시각·명령·원본을 고정해야 한다.

## 4. 주요 보안 경로의 대조

| 경계 | 코드·실측 | 판정·한계 |
|---|---|---|
| 역할/세션 인증 | `control/main.py`의 포트/route/UserBearer/service 검사, MCP SDK verifier·scope/audience·dispatch 재resolve. 실제 expired/audience·cross-role·타세션 resume 시험 | 현재 로컬 단일 사용자 경로 대표 PASS. 다중 계정/tenant 서비스 완료 아님 |
| 정확한 판정/승인 | canonical JSON UTF-8 SHA256·session/tool/backend/args/policy 결합; approve expected digest; reserve의 단회 approval 소비 | 변조/만료/타세션/replay·동시 승인 대표 PASS. 원 CONFIRM과 CONSUMED/SUCCEEDED를 각각 유지 |
| 집행/예산 | `invoke`의 check→reserve execute=true→private executor→source/report 순서; BEGIN IMMEDIATE·write_budget·effects 유일성 | DENY/미승인/SECRET_ENV0, 정확 게시1, 경쟁 최대1. R1 audit latch도 재현. 동일 OS 관리자/직접 Python 실행 격리 주장 없음 |
| UNKNOWN | 예산 환불/위험 쓰기 자동 재시도 없음; effects DB와 명시 report | write report 유실1→UNKNOWN→추가0. R1 read audit 실패 뒤 후속0/명시복구 확인. daemon30초/restart 전체 재현은 NOT_RUN |
| 저장/표시 | token digest; request/action/source/event/comment 암호화·마스킹; UI textContent, 메모리 bearer; role별 runtime mount·저장키 | API/DB canary 및 현재 runtime human/service/key/API credential marker 검색0(아래 범위). 브라우저 실제 XSS/승인조작은 NOT_RUN |
| 공개 계약 | baseline OpenAPI/schema/examples 차이는 전송/wire 기계 동기화 범위. 내부 client response validation, 실제 발급/이력/CheckReply schema 보완검사 | 대표 응답 일치. `app.openapi=lambda:API`는 자동 생성 API와의 독립 대조가 아니라 수동 계약 재사용이므로 전 endpoint 자동대조 완료는 아님 |

민감정보 scoped 검색은 `src`, `scripts`, `tools`, 개발 run artifact 전체에서 현재 human/service/storage키 4개와 호스트 OPENAI_API_KEY를 메모리에서 대조해 **hit0**이었다. 값은 출력/저장하지 않았다. 모든 과거 키·사용자 PC·Codex의 모든 저장파일에 대한 완전 secret scan이라는 뜻이 아니다. 고정 fixture의 가짜 sentinel 자체는 테스트 자료이며 실제 credential로 계산하지 않는다.

## 5. TLS와 Bandit B104 세 건

- 실제 host→Control/Gateway HTTPS, Gateway→Control CA/hostname 검증+mTLS+service bearer를 제품 pytest 및 기존 LIVE 증거에서 확인했다. httpx는 proxy 상속/redirect/HTTP fallback/verify=false를 사용하지 않는다. Credential 없는 HTTP 접속 거부·untrusted CA/hostname 거부·client cert 없는 내부 접속 거부의 대표 제품 시험이 있다.
- TLS 준비 fixture의 expiry 성공/거부와 실제 제품 negative certificate 전체 matrix는 구별한다. 실제 제품 wrong/expired client cert·재발급/키수명·회전·복구 전수는 NOT_RUN.
- 작성자의 추가 Codex app-server CA spike는 무과금 준비 검증이며 trusted CA 3tools/untrusted 0tools, model_turn_started=false를 기록한다. 기존 두 LIVE 실행의 정확한 CLI/모델, 최종 출력·timeline과 효과를 별도로 확인했다. CA spike 자체를 LIVE 모델 시험으로 합치지 않는다.

Bandit1.9.4 B104는 `control/serve.py:13`, `:17`, `gateway/main.py:174`의 0.0.0.0 bind 세 건이다. **판정: 해당 로컬 Compose 구성에서는 의도적 container listener이며 실질 노출을 제한하는 통제가 있는 구성 의존 경고. 원경고는 유지한다.**

공개 8000/8001은 127.0.0.1에만 publish하며 TLS·역할 인증을 요구한다. 내부8443은 host publish가 없고 mTLS+service bearer 및 route/port 분리를 요구한다. 다만 두 서비스가 development와 local-ingress에 함께 붙고 all-interface listener이므로 **8443도 container의 local-ingress NIC에서 listen한다.** 내부 전용 NIC만 listen하거나 OS outbound가 전면 차단된 것으로 표현하면 틀리다. Docker 네트워크의 다른 주체에 대한 상대 인증은 mTLS/bearer에 의존한다. 외부 publish·host network·TLS/인증 제거·네트워크 변경 시 재판정이 필요하다. 세 warning을 억제하거나 49개 약점의 확정 정탐3/무약점0으로 계산하지 않는다.

## 6. LIVE 및 공급망·가이드 증거

추가 유료 LIVE는 0회다. 기존 `gpt-5.6-luna` / Codex CLI0.154.0의 정상43(session `125fd172-ba4a-4ded-a7fb-afc130234f08`)과 공격42(session `e8d4818f-235f-41bb-a1e8-63cb361bbe1d`)를 확인했다. 요청/최초 prompt digest 일치, 한국어 정상 최종 출력, 실제 reads 1 및 2, 댓글0이다. **두 경우 모두 NO_ATTACK_ATTEMPT**이며 엔진의 실제 LIVE 공격 차단 성공/일반 방어율은 아니다. R1 source 수정 뒤 새 LIVE는 수행하지 않았으며 기존 LIVE 증거의 build 차이를 유지한다.

관련 원문 PDF를 직접 다시 읽고 manifest hash를 확인했다: R1 PDF13~14, G1 PDF45~47, G2 PDF70~71, G3 PDF159~160/406/511, G4 PDF37~39, C1 PDF14~15/26. PDF 재추출과 hash 결과는 자기 artifacts에 있다. 이 범위는 모든 PDF 예제/20·49항목의 개별 본문 전수검증이 아니다.

`GUIDE_APPLICABILITY.md`는 **설계20·약점49 모든 행·누락/중복0**을 갖췄고 전수 NOT_RUN/부분증거로 표시한다. 그러나 여러 행의 파일·근거는 일반 경로/넓은 페이지 묶음이며 rule ID, source→sink, 개별 동적 조건이 충분히 확정되지 않았다. 비적용 확정이나 전수PASS는 승인하지 않는다. SECURITY_DESIGN의 요구→위험·외부 인터페이스→코딩 규칙→동적 효과 연결은 구조적 예방 설명의 초안 근거가 된다. C1의 공식 빌드라인/점수/조치율은 추정하지 않는다.

이미지는 digest 고정, Python 설치는 hash lock, 두 서비스는 비root/read-only/capdrop/no-new-privileges·역할별 DB/mount를 사용한다. Python SCA raw는 'No known vulnerabilities found'지만 그 시점/범위의 결과이며 OS 전체 안전은 아니다.

첫 Python CycloneDX1.4 SBOM은 schema validation PASS(작성자 `sbom-schema-validation.json`), components81 및 별도 installed inventory81이 있다. **형식 유효성과 G1의 최소 필드/완전성은 별개다.** 독립 필드 확인에서 SBOM의 supplier0/purl0/license0/metadata author0/dependency edge0이고 별도 inventory에는 requires가 있는39개 component가 있다. 관계/공급자/작성자/식별자·고지 정보의 기계 연결과 누락 검증은 남는다(`sbom-fields-review.json`). 임시 bom-ref의 존재를 안정된 package 식별자 완전성으로 계산하지 않는다. 라이선스 metadata 존재는 고지·재배포 준수 확정이 아니다. OS CVE 진단 및 runtime/dev 분리 SBOM·이미지/빌드 출처 전체 연결도 미완료다.

추가 보완은 최초 파일과 별개인 작성자 `sbom-python-enriched-r1.json`에 있다. 독립 필드 대조에서 components81/PURL81/license metadata81/dependency edges125/작성자1·timestamp·R1 source fingerprint가 확인됐다(`sbom-enriched-fields-review.json`). 작성자의 별도 schema1.4 검증도 PASS다. supplier81개는 모두 `UNKNOWN - upstream supplier not independently verified`이며 upstream author 문자열은 별도 property로 구분해 확정 공급자로 오인하지 않는다. 따라서 초기 필드 누락 일부의 보완은 확인했으나 공급자 검증·라이선스 고지/재배포·OS 취약점·runtime/dev 전수 완전성은 계속 미완료다. 최초 SBOM 지적과 원본은 유지한다.

## 7. 남은 게이트와 인계

| 남은 범위 | 현재 판정 |
|---|---|
| 기본24시간 보존/폐기, 키·인증서 lifecycle/rotation·복구 | 구현/실측 미완료; 적용 P0 삭제 허용 아님 |
| PDP timeout/malformed, 취소, source/report 저장 장애의 전체 위치·조합, daemon stale30초/재시작/reconcile | 대표 PASS와 별도로 전체 matrix NOT_RUN |
| 실제 브라우저 XSS/승인조작·token 저장 상태, auth flood/부하·장기 자원관리 | NOT_RUN |
| 실제 제품 negative TLS 전체 matrix·새 PC/clean build 재현 | NOT_RUN |
| 설계20/약점49 개별 본문·rule coverage·수동 source→sink·조건부 비적용의 의존성/native 경계 | 전수 판정 미완료 |
| 최초 SAST 전체 source/time 추적(F-007), SBOM 최소필드/관계·OS SCA·license/NOTICE | 미완료 |

관리 인계: F-008은 최초 FAIL→작성자 수정→독립 PASS의 이력이 연결됐다. R1의 위험 쓰기 게이트 재현은 통과했으나, 위 잔여와 전체 NT/AT/AC·PL-SEC-TRANSPORT/SDLC/DIAGNOSIS의 완료 판단이 남는다. 다음 준비 작업은 T-04/05/06/07/08/10의 잔여 fault·보존·브라우저·TLS/공급망·20/49 검증이다. 전역 작업 장부는 수정하지 않았다.

보호 주장은 등록 MCP 세 도구의 해당 Gateway 경로에 한정한다. 모든 IPI·Codex 내장 셸/파일·다른 MCP·호스트 전체 보호, 출처 일치의 인과 증명, 공인 진단/대회 정량 목표 달성을 승인하지 않는다.
