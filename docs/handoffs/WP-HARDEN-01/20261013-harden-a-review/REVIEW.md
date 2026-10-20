# WP-HARDEN-01 단계 A 별도 AI 검토

검토 run: `20261013-harden-a-review`. 검토자 역할은 작성자와 분리된 보조 AI다. 사람 개발자는 사용자 1명이며 공식 독립 진단이나 추가 사람 검토가 아니다. 최종 검토 시각과 명령은 `artifacts/20261013-harden-a-review/review-summary.json` 및 `*-command.json`을 따른다.

**판정: 단계 A의 배정된 A1/A2 유한 범위에서 독립 회귀·장애 재현이 통과했다. 현재 검토 범위의 미해결 차단급/P1 제품 정탐은 없다. 관리 검토에 인계할 수 있으나 전체 core/MVP·후속 LIVE는 미완료다.** 보존 문서의 엄격한 1800초 상한 주장은 검토 지적 후 좁혀졌다. 최초 실패의 전체 소스 버전과 최종 후보 참조는 구분해야 한다.

## 고정 기준과 경계

- MVP-SPEC-3, policy `mvp-2026-10-13-v1`; 공개 endpoint·enum·권한·상태 계약의 변경은 없다.
- 검토 최종 후보는 `artifacts/20261013-harden-a/r1/manifest.json`, fingerprint `6c6d6a98e33fff4177293022f61c4a33956192dc427b24f01d42f71a5e825423`다. 69개 실제 파일의 hash와 snapshot/fingerprint를 독립 대조했다. mismatch 0. 이전 최종50개와 이번 baseline snapshot도 모두 일치했다(`frozen-check.json`). 최초 candidate `cc3b435e…` 이후 변경3개는 HTTP 2xx 검사 및 302 TLS peer 회귀다.
- `requirements-dev.lock` hash는 `4ba8fe14ea9ead50796f2a782a716fde6c9ba0efc6620893544c8ba6f97b1c5d`, 실제 dev image ID/digest는 `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`다. 기존 image/lock을 사용했고 추가 도구 설치·유료 LIVE 호출은 0이다.
- AGENTS, with-human-dev workflow/roles/evidence, 단계 A 작업팩 전체, SPEC-3 계약, 이전 RESULT/REVIEW, 작성자 SECURITY_DESIGN/GUIDE_APPLICABILITY/FINDINGS 및 안전한 원증거를 읽고 대조했다. 초기 Git은 untracked 제품이므로 commit diff 대신 고정 snapshot과 실제 파일을 사용했다.
- 검토자의 쓰기는 자신의 handoff와 ignored artifact에 한정했다. 제품·공용시험·계약·plans·작업 장부·기존 원증거·runtime·키·DB를 수정하지 않았다. 제품 기동/재시작 시험은 각 독립 Docker run의 `/tmp` DB와 생성한 임시 PKI/subprocess만 대상으로 했다. 기존 Compose 앱의 재기동·폐기는 하지 않았다. 동일 포트의 fixture들은 별도 컨테이너로 실행했다.

## 독립 실행과 원증거

공통 증거 경로는 `C:/sogaeding/artifacts/20261013-harden-a-review/`다. 모든 아래 성공 실행의 정확한 인자·시작/종료 UTC·exit·raw output은 같은 label의 `*-command.json`과 `.txt`에 있다. pytest 수는 실제 함수/param 수이며 기존 NT/AT 번호나 제품 수용시험18개의 새 번호로 바꾸지 않는다.

| 검토 실행 | 결과 | 의미·원증거 |
|---|---|---|
| 최초 sandbox Docker 접근 | exit1 | npipe 권한 오류. `product.txt`/`product-command.json` 보존. 제품 실패가 아니다. 읽기/전용 fixture에 대해 escalation 후 성공했다. 최초 image label은 성공 재실행에 재사용돼 해당 첫 image 실패 파일을 별도 보존하지 못했고 도구 출력 관찰만 남는다. |
| image inspect | exit0 | `image.txt`: 위 digest·비root image 확인. |
| candidate 제품 회귀 | exit0, 30 PASS, 47.04s | `product-r0.txt`. 최종 판정은 아래 r1 재실행에 둔다. |
| **r1 제품 회귀**: `docker compose run --rm --no-deps … dev python -m pytest tests/backend tests/transport tests/web tests/acceptance -q -p no:cacheprovider` | **exit0, 30 PASS, 46.95s** | `product-r1.txt`, `product-r1-traces/product-traces.json`. 실제 MCP·PDP·예약·executor와 DB 상태 대조. |
| **r1 TLS fault peer**: 같은 전용 run에서 `python -m pytest tests/hardening -q -p no:cacheprovider` | **exit0, 8 PASS, 8.40s** | `peer-r1.txt`, `peer-r1-traces/fault-traces.json`. pre-execution timeout 1100ms, JSON/schema/error/list-error/valid-schema302 모두 실행0·효과0·canary 비노출; 회복 정상댓글1. |
| 검토자 자체 `test_independent.py` 첫 실행 | exit0, 3 PASS, 8.14s | `independent.txt`. 아래와 같은 경계/역순 장애/receipt 결합 재현. |
| **자체 fixture 최종본**: 안전한 session/call 참조를 기록에 추가하고 재실행 | **exit0, 3 PASS, 8.79s** | `independent-final.txt`, `independent-final-traces/*.json`. 제품 기대값·policy/reserve를 mock하지 않았다. |
| r1 Ruff | exit0 | `lint-r1.txt`: `ruff check src tests/acceptance tests/backend tests/hardening`. |
| r1 Bandit | exit1, B104 3건 | `bandit-r1.txt`: `bandit -r src -f json`. 아래 구성 의존 판단 유지; 경고 억제/무약점 PASS 아님. |
| 원문 PDF·snapshot 검사 첫 Docker 시도 | exit1 | `frozen-guides.txt`: dev image에 pypdf가 없어 실행 구성 실패. 의존성 추가 설치 없이 번들 Python으로 재실행했다. |
| 번들 Python 원문·snapshot 검사 | exit0 | `frozen-guides-host.txt`, `frozen-check.json`, `guide-pages/manifest.json`: 원본PDF6개 hash 일치, 읽기 전용 원본에서 해당 페이지를 직접 재추출. |

30개 제품 회귀, 8개 peer, 3개 자체 경계 재현은 서로 다른 시험 범위/실행이다. 41개 제품 수용시험 또는 전체 core 통과로 합산하지 않는다. 작성자의 최종 candidate/r1 시험·command/exit/raw와 독립 결과가 일치한다. 작성자의 최초 취소 FAIL과 peer teardown ERROR는 제거하거나 PASS로 바꾸지 않았다.

## A1 보존·폐기 판단

`Repository.session()`은 보존 기한을 active=False 접근에도 적용하고 `call()`이 재사용하므로 timeline, 기존 call/reserve/report, 승인, source가 함께 제한된다. `resolve()`의 token 수명1800초 및 `session()`의 보존86400초는 별개다. session 생성·조회·자식 생성·복구로 보존 기한을 갱신하지 않는다.

Control은 session 서버 생성+24시간을 묶음 기한으로 쓰고 Gateway comments/receipt는 실제 invocation 서버 `started_at`+24시간을 쓴다. A1은 서버가 기록한 생성시각과 데이터 목록/기한의 명시를 요구하며 두 DB 모든 행을 동일 session 생성 시각으로 폐기하라고 정하지 않았다. 따라서 이 내부 선택은 공개 계약을 바꾸지 않고 배정 범위를 충족한다. **두 DB 자료가 같은 시각에 사라진다는 의미는 아니다.** 자체 가짜 시계 재현에서 invocation을90초 늦게 만들었고 Control timeline은1086400에 거부·폐기되지만 Gateway receipt는1086490 직전까지 살아 있었다. 이후 Gateway receipt 접근은 None이고 정리는 멱등적이다.

삭제 순서는 코드·작성자 설계와 일치한다. 각 DB의 tombstone 생성과 자식/부모 DELETE는 단일 transaction이며 다른 DB와의 분산 commit은 없다. 원자적 실패·다음 daemon/startup의 재시도를 구분한다. 제품 시험은 Gateway DELETE 실패/Control 성공을 재현했고, 자체 시험은 **Control DELETE 실패/Gateway 성공**을 반대로 재현했다. 실패한 Control transaction의 session·예산0이 보존되고 disposals0이며 trigger 제거 뒤 실제 startup2회에서 purge가 완료됐다. 옛 timeline404/token401/reserve404, 추가 effects0, 새 세션 정상댓글1이다.

legacy SPEC-3의 서버 세션 수명1800초를 근거로 `expires_at-1800`을 복원하는 migration은 비파괴·멱등적이다. 자체 시험에서 두 번 migration 후 생성시각1000000 및 request cipher 불변을 확인했다. 알려지지 않은 다른 schema나 변경된 수명의 migration 전수호환을 주장하지 않는다.

Control tombstone의 unresolved_count는 RESERVED/UNKNOWN 합계이고 write_budget0을 유지한다. Gateway EFFECT_RECORDED는 private effects 기록이 있었다는 뜻이며 Control 성공확정이 아니다. 최소 hash/기한/미해결수/예산 기록은 원래 자료 기한+7일에 삭제돼 늦은 재시작이 보관기간을 연장하지 않는다. 제거된 Control session/call/token이 복원되지 않으므로 옛 실행권·승인·예산 재발급이 없고 tombstone 만료도 위험 쓰기 자동 재실행 경로가 아니다.

제품의 Control/Gateway **실제 daemon 정리**, Control stale30초 **실제 daemon/startup UNKNOWN 전이**, 반복 startup, 기한 전 보존·기한 후 접근 거부를 시험했다. 정상10초 주기와 처리/스케줄/DB lock 지연은 구분한다. 지속 저장 오류·서비스 비가동 중 물리 삭제 완료의 유한 상한은 보장하지 않으며 기한 접근 guard와 회복 후 cleanup을 보장한다. 지정 canary/token/ciphertext의 현재 테스트 DB 및 이름에 매칭되는 journal 잔존0은 앱 접근불가·현재 파일 검사 결과다. SSD·백업·삭제 파일 복구·메모리/CPython zeroization의 완전 삭제 증명이 아니다.

## A2 장애·복구 판단

| A2 유한 항목 | 실제 관찰 |
|---|---|
| 실행 전 PDP timeout·malformed JSON/schema·오류·302 | 실제 TLS peer가 real PDP 앞에서 해당 경로에만 주입. timeout 약1.1초, 나머지60~67ms, executor/effects0, 원문 오류·사용자/서비스 자격증명 비노출, 회복 정상댓글1. 302는 real CheckReply의 valid JSON이어도 거부. |
| check/reserve/필수 감사 실패 | calls/검사감사/예약감사/executions INSERT trigger 실패에 실제 MCP 중단·효과0. call/write예산·APPROVED·execution 부분commit 없고 trigger 제거 뒤 정확재개1. |
| source 저장 F-008 회귀 | real read 뒤 UNKNOWN, 새 check 후속 쓰기/읽기0, 미리 발급된 ALLOW write reserve도409. source없는 actualreceipt-only SUCCEEDED 위장은503 AUDIT_UNAVAILABLE. |
| 쓰기 report/응답 손실 | 댓글효과1, UNKNOWN 및 write예산0. 같은call/다른call 위험 재시도 추가0. 실제 effects receipt와 기존 reservation의 명시적 reconciliation만 확정. |
| 실제 MCP 취소 | SDK2.3.0 protocol2026-07-28 response stream close를 실제 수행. 취소 후 UNKNOWN 기록22ms, 댓글1·추가0, 실제 receipt로 상태복구. 이 transport에 해당하는 관측이며 모든 protocol/취소시점의 증명은 아님. |
| stale30초·daemon/startup | 테스트 reserved_at만 과거로 조정한 뒤 real service가 UNKNOWN으로 전이. 예산0·추가효과0, fresh session 정상완료. 함수 직접 호출만을 daemon 시험으로 세지 않음. |
| 정상·DENY·승인·만료·거절·경쟁 | 기존 전체 관련 회귀: 정확댓글1, DENY/SECRET_ENV0, CONFIRM 승인전0/승인후1, 동일approval 및 다른call 경쟁 총1, replay추가0, 만료/거절/타세션/인자변형 거부. |

자체 receipt 시험은 실제 write report 저장 실패→실제 startup UNKNOWN 후, 다른 reservation_id·다른 receipt session_id·reconciled=False를 각각409로 거부했다. 실제 receipt report는2회 모두200 SUCCEEDED, MCP 성공call 재개도 invocation/effects1/1을 유지했다. 서비스 bearer에 의한 명시 복구 경로이며 에이전트가 자체 성공을 선언하는 경로가 아니다.

## 발견과 증거 한계

**R-A-001 / 낮은 우선순위 / 문서 정리 확인.** 작성자 설계의 두 DB 삭제시각 차이 “최대1800초”는 예약 후30초 시작 여유 및 worker 지연이 session expires_at에 다시 묶이지 않아 엄격한 상한으로 입증되지 않았다. 작성자에게 알렸고 정상은 보통1800초 안에 시작하지만 정확한 상한을 주장하지 않는 것으로 수정됐다. 제품수정은 없다. record별24시간 보존이나 옛권한 복원이 발생했다는 제품 결함은 아니다.

**R-A-002 / 증거 표현 보완 확인, 기록 부재 한계 유지.** F-009 최초FAIL 및 F-011 최초B608 이벤트에 최종r1 fingerprint가 공통으로 붙어 있었다. 이를 최초 실패 소스가 최종r1과 같았다는 증거로 읽으면 부정확하다. baseline·최초raw/snippet·수정·최종snapshot/독립 재진단의 연결은 존재하나 각 중간 실패 전체소스의 동시 snapshot은 별도로 고정되지 않았다. 작성자는 기존 이벤트를 보존한 채 F-009/F-011 `EVIDENCE_QUALIFICATION`을 추가해 final candidate 참조와 실제 command UTC를 구분했고, RESULT에 중간 전체snapshot 부재·소급복원 미주장을 명시했다. 최종 문서 표현 보완은 확인했으며 증거 부재 자체는 남는다. 과거 F-007 공백이나 중간 소스를 추정 복원한 것으로 표시하지 않는다.

F-009은 작성자의 최초 요청취소1FAIL(4.94s)→RequestGuard의 modern tools/call disconnect 감시·bounded shielded UNKNOWN→최종독립22ms의 조치·재진단으로 연결된다. F-010은 기존 >=400 처리의3xx valid-schema 허용조건을 수동 확인한 뒤2xx만 인정하는 수정과302 동적 차단0으로 확인됐다. 수정 전 동적 공격 재현을 새로 주장하지 않는다. F-011의 최초B6082건은 고정 developer table tuple로 외부 table선택 입력이 없었으며 고정 SQL statement로 변경 후 최종Bandit에서 제거됐다. 이를 확정 SQL injection 정탐/공식 조치율로 계산하지 않는다. F-008 옛 최초FAIL→조치→이번 회귀PASS 이력은 유지한다.

## 가이드·잔여와 인계

원본PDF6개 hash를 독립 확인하고 관련 원문을 직접 재추출했다. 이번 관련 읽기는 R1 PDF13~14, G1 PDF35·47, G2 PDF133·135·137·143, G3 PDF510·511, G4 PDF24·38, C1 PDF14·15·26의 보존/오류/세션/개발검증 원칙이다. `guide-pages`에153·164·171도 추출했지만 이것을20/49 모든 본문 전수 수동검토로 세지 않는다.

보존은 SR2-7의 중요정보 저장→두SQLite/사용자조회 경계→암호화·serverclock guard·고정 parameter SQL·bounded tombstone→실제 경계/폐기/복구로 연결된다. 장애는 SR3-1의 예외처리→TLS JSON/SQLite/취소 경계→identifier allowlist·timeout·atomic reserve·UNKNOWN latch→금지 실행0/효과후1+추가0으로 연결된다. G4 PDF24와 C1 PDF14·15·26의 요구·위험/인터페이스·코딩/정적진단·동적검증 연결을 보완하는 증거이며 공식 점수/빌드라인/조치율을 추정하지 않는다.

Bandit1.9.4 B1043개는 Control serve 2곳/Gateway listener1곳의0.0.0.0 bind다. localhost publish·TLS·내부 mTLS+service bearer 조건의 구성 의존 경고를 유지한다. 내부8443도 container 모든NIC에서 listen하고 local-ingress/OS outbound 전면 차단은 아니다. 외부publish/hostnetwork/TLS·인증/네트워크 변경 시 재검토해야 한다.

F-007 과거 최초SAST 전체소스/정확시각 공백은 영구 한계다. 이번 시작 baseline과 최종source/image/lock·정확성공command UTC/exit/raw는 확인됐으며 앞으로의 절차 보완으로만 평가한다. 신규 LIVE0; 기존 수정 전 LIVE의 정상연결/요약 및 NO_ATTACK_ATTEMPT를 최종r1 LIVE차단으로 이전하지 않는다.

작성자 최종 RESULT 전체와 보충 장부를 대조했다. 작성자 r1-product30 PASS46.55s/r1-peer8 PASS8.59s/하네스1 PASS 및 정적 결과는 자신의 독립30/8/3 결과와 구분해 수용한다. 마지막 대조에서도 r1 manifest69개 실제 hash mismatch0이고 문서 정리 후 제품 변경이 없었다.

단계 B 실제브라우저·XSS/승인동작·중복·token저장/인증부하, C 제품전체 TLSnegative·재발급/회전/수명·clean환경, D 설계20/약점49 개별본문·rulecoverage·수동source→sink/native경계·비적용·OS SCA/공급자/NOTICE/SBOM 완전성은 미완료다. 전체core·LIVE/MVP 완료판정은 관리 세션에 둔다. 등록 MCP3도구의 검증된 Gateway 경로에만 보호 판단을 한정한다. 모든IPI·Codex내장shell/file·다른MCP·호스트보호 및 출처일치의 인과증명은 주장하지 않는다.
