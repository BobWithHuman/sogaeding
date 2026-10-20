# followup-auto-v4 실행 준비 결과

2026-10-17. 기존 Jev 평가 도구에 고정 V4 평가 경로를 연결하고 **개발 세션에서 prepare/inspect/preflight를 완료**했다. 실제 actor/Jev 유료 호출0·CLI0·서비스 교체0·기존 예산/원장 초기화·환불0이다. 개발 AI 토큰은 구현/별도 AI 검토에서 사용되며 제품 호출 수와 별개이고 정확 계량값은 제공되지 않았다.

## 준비된 사용자 실행

- run ID: `followup-auto-v4`
- manifest SHA256: `9aa11ab1b12fd231c2a39d52308eb60a1ea12fdc71514647d6ab50494bbdc23c`
- [USER_RUN.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v4-eval/USER_RUN.md): exact hash·8개 한도의 한 줄 evaluate와 collect. 사용자가 다시 prepare/plan/key 입력을 할 필요가 없다.
- [preflight.json](C:/sogaeding/artifacts/20261017-v4-eval/preflight.json): ready_for_user_opt_in=true, default_enabled=false, live_authorized=false, exact_wire_build_verified=true, paid_requests0, actual_key_read=false, provider_ledger_present=false. provider/model 접근은 NOT_VERIFIED_NO_REQUEST다.
- [inspect.json](C:/sogaeding/artifacts/20261017-v4-eval/inspect.json): 원문·고정 후보·질문/criteria·wire·source/image/bundle/parent 결합. actual prepare 결과는 prepare.json이다.
- [collect-readonly-check.json](C:/sogaeding/artifacts/20261017-v4-eval/collect-readonly-check.json): 준비 파일3개 hash변경0. 새 DB/claim/authorized config 부재, collect는 NOT_RUN/NOT_ATTEMPTED2다.

실제 전송을 선택하면 정상A→정상B→공격A→공격B 최대4요청/입력예약256000이다. demo관련 최대12/768000, 최초 실패 등 전체과거 포함 최대17/1088000, actor/CLI0이다. 현재 old demo8/512000·전체13/832000은 보존하고 새 run의 provider 원장은 사용자의 정확 전송 선택 뒤에만 생성한다. 과거 usage/청구 UNKNOWN을 환불/0으로 바꾸지 않는다.

## 구현 범위

변경은 `tools/jev_eval.py`, `scripts/jev_eval.ps1`, 신규 `tests/hookgw/test_jev_v4_eval.py`다. [source-manifest.json](C:/sogaeding/artifacts/20261017-v4-eval/source-manifest.json)과 원 helper/wrapper 대비 change.diff에 보존했다. 관리 plans/harness/AGENTS, server/runtime/V3/승인/예약/UNKNOWN/TLS, V4 후보7개는 수정하지 않았다.

기존 followup 위치/보호 ACL/RO key mount/disabled config/atomic execution.claim/정확 manifest 승인/후속 collect 경로를 재사용한다. 구형 run 경로·원 장부는 유지하며 현재 소스가 달라도 과거 collect는 읽기 전용이다. V4의 old closed parent3개(1+4+8요청)와 manifest/실제 동결 bundle 전체·현재 source54개/image·원 proposal/wire를 결합한다. bundle manifest는 bundle 밖 파일을 hash할 수 없다.

실제 V4 build를 재생성해 pinned 원 wire 네 개와 byte 단위로 비교한다. 정답은 plan의 expected_local_only에만 두고 모델 wire에는 넣지 않는다. provider 관측은 명시 순차 await이며, 각 응답의 typed choices/probabilities/provider/computed/effective confidence와 exact refs를 보존하고 기존 compose_view/validated_spans/combine으로 조합한다. A/B를 다시 요청하는 policy parallel evaluate는 호출하지 않는다. 유효 CONFIRM은 채점 결과이며 재요청하지 않는다. 최초 transport/shape/usage/ref/분석 오류 후 나머지 요청은 중단한다. missing/partial/null usage는 UNKNOWN 예약을 유지하고 중단하며 retry/fallback/reset0이다.

## 발견과 수리

처음 실제 transport 경계를 연결하자 V4 B wire의 공개 raw_sha256/text_sha256가 일반 long-token guard에 걸렸다. 후보7개/원 wire를 바꾸거나 전역 guard를 완화하지 않고 평가 전용 `FixedPublicDigestClient`를 추가했다. 실제 rebuild와 네 pinned wire SHA를 먼저 검증한 입력에서 source_presentations의 파생 공개 digest 필드만 scanner 입력에 typed placeholder로 구분한다. 다른 필드는 기존 JevClient scanner를 사용하며 `_request`는 scanned body 일치·원 body 크기·실제 key의 원 body 포함 여부를 검증하고 원 exact bytes를 기존 HTTP transport로 전송한다. budget/response/usage/ref validation은 재사용한다.

독립 검토는 digest/non-digest 변조의 claim 전 거부, 가짜 API key가 공개 digest와 같을 때 B 전송 차단/원 예약 보존, A/B ref/compose 오류마다 fail-stop을 확인했다. 실제 key는 준비/검토에서 읽거나 hash하지 않았다. 초기 실패와 scripts 마운트 누락·lint 정렬·native 실행 정책 거부 및 조치는 [INITIAL_DIAGNOSTICS.md](C:/sogaeding/artifacts/20261017-v4-eval/INITIAL_DIAGNOSTICS.md)에 분리했다.

## 검증

| 확인 | 결과/증거 |
|---|---|
| 직접 영향 범위 최종 회귀 | **207 PASS/36.67초**, related-command.json/related.txt. V4·구형 eval/followup·원 transport/response 계약. 실제 모델0 |
| 별도 AI 독립 반례 | **9 PASS**, [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-v4-eval-review/REVIEW.md), artifacts/20261017-v4-eval-review/boundary-* |
| Windows PowerShell5.1 | Unicode21/V4 flags4 PASS, native-utf8.json/native-v4.json. fake helper만 사용. ExecutionPolicy는 해당 자식 프로세스에만 적용/영구 설정 변경0 |
| Ruff | static-command.json/static.txt exit0 |
| Bandit | bandit-command.json/bandit.txt **exit1, 27 Low/1 Medium** 원진단 보존. 경고를 제거/0건 PASS로 표시하지 않음 |
| 실제 disabled 준비/사전 점검 | prepare.json/inspect.json/preflight.json, 전송/새 유료 DB0 |
| 보존 | preservation.json: V4 후보7개 SHA mismatch0, 성공 normal.md `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0` 유지 |

Bandit B404 1/B603 13은 trusted executable·고정 argv·shell 미사용의 기존/신규 subprocess 경계다. 새 _plan은 network none이다. B108 1은 Docker tmpfs mount의 `/tmp` literal이며 host 공유 임시파일 sink가 아니다. B105 13은 input_token_limit의 공개 한도/disabled None을 password로 탐지한 항목이다. 원진단을 남기고 별도 검토자가 해당 callsite/데이터 흐름을 대조했다. source 진단 전체/모든 보안 약점 PASS를 선언하지 않는다. V4 정책 변경이 없으므로 688개/브라우저/gateway 전체를 반복하지 않았다.

## 필수 가이드와 한계

docs/plans/03_guide_compliance.md의 기존20설계/49약점 정본 상태는 유지한다. 이번은 평가 입력/경로/실행/출력 경계의 좁은 재검토다. 기존 원문·해시의 `artifacts/20261017-auto-decision/guide-pages.json`을 재사용했다: R1 PDF14·G1 PDF35~36의 추적/개발검증→원본/pinned manifest 보존; G3 PDF507~508 SR1-4/9와 W-03/05/15→경로/typed 입력/정확 한도/실행 전 fail-stop; G2 PDF128/135/137과 G3 PDF510→단회 claim/보호 key/안전 오류·UNKNOWN; G4 PDF24의 최초진단→조치→재검증/별도 코드검토. 신규 dependency/모델 변경/개인 설정 변경은 없다. 미점검20/49나 전체 TLS/키수명/공급망을 PASS로 올리지 않는다.

현재 실제 의미 결과는 NOT_RUN이다. exit0를 ALLOW/DENY 의미 성공으로 보지 않는다. 사용자가 실행해도 고정 정상1/공격1의 작은 semantic smoke이며 파일 효과·actor 보호·전체 정확도·일반 native/hook 장애·전체 IPI·서비스 배포·MVP 완료의 근거가 아니다. 다음 단계는 준비된 exact 명령의 사용자 직접 선택이며, 이 세션은 evaluate를 실행하지 않았다.
