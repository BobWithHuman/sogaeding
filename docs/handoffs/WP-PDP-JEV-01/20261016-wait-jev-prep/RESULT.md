# T-JEV-03/04 구현·무모델 준비 RESULT

2026-10-16. WAIT_AND_JEV_PREP_START_PROMPT 전체·최신 AGENTS/관리 host_wait 검토/control state·with-human-dev 및 관련 SPEC5/Jev 계약/필수 가이드 원문을 적용했다. 사람 개발자는 사용자1명이다. `/root`가 Engine/Control/bridge/문서·통합을 작성하고, `/root/wait_gateway`가 격리 실제 gateway fixture, `/root/jev_adapter`가 별도 제한 평가 helper, `/root/jev_review`가 별도 AI 검토를 맡았다. 공식 독립 보안 진단이 아니다.

**승인 대기 수리와 Jev 평가 준비를 구현·오프라인 검증·제품 코드 통합했다. 실제 OpenAI/TypeSafe/actor 모델 호출0, 사용자 새 TypeSafe 키 값 수집·읽기0이다. 사용자 승인 UI 재시험/새 공개 읽기·실제 Jev 접근과 의미 정확도는 NOT_RUN이다.** 기존1회 유료 CLI 시험 동의는 앞선 시험에서 사용됐으므로 새 유료 CLI나 Jev 전송을 자동 실행하지 않았다.

- [별도 REVIEW](../20261016-wait-jev-review/REVIEW.md)
- [증거 인덱스](../../../../artifacts/20261016-wait-jev-prep/final-index.json)
- [가이드 적용성 변경분](GUIDE_APPLICABILITY.md)
- [현재 사용자 절차·전송 자료/가격 설명](../../../mvp/09_rules_first_jev.md)

## 최초 진단·기준선

관리의 [실제 실패 관측](../../../../artifacts/management-host-wait-20261016/observation.json)을 보존했다. 당시 새 read는 RULE_ALLOW/PUBLIC_ENROLLED_READ/model0·ALLOW/READY 후 약90.074초에 FORWARD_SNAPSHOT_STALE/403, upstream시도0이었다. 기존30초 freshness와 승인 대기가 충돌했고 bridge는 모든401/403을 HTTP_AUTH_REJECTED로 합쳤다. 원 REJECT의 call빈값 한계도 유지한다.

시작193파일 fingerprint `bdc7df912c9d2c815b9c2928814004b4afc83310fe66e6686084a0f367daa999`을 [원본 source 복사/manifest](../../../../artifacts/20261016-wait-jev-prep/baseline-source/manifest.json)로 고정했다. 새 격리 실제 pinned gateway/TLS upstream에서 **Engine의 시계만91초 이동**시켜 변경 전 즉시 read200/OBSERVED/attempt1과 지연 read403/attempt0을 재현했다([baseline 6/6](../../../../artifacts/20261016-wait-gateway/baseline-probe.json), [원장](../../../../artifacts/20261016-wait-gateway/baseline-effects.json)). 원 analyzed_at을 덮거나 사람이 실제91초 기다린 시험이 아니다. ticket/upstream의 실제 벽시계는 그대로다.

## T-JEV-03 변경·집행

새 판정에 원 action/request hash와 내부 `forward_revalidation:public-read-1`을 기록한다. **새 RULE_ALLOW/PUBLIC_ENROLLED_READ/model0의 MCP read_file만**30초가 지났을 때 실제 gateway 요청의 BEGIN IMMEDIATE 안에서 현재 connection/session 만료·소유권/turn·실제 정책/grant·동일 action/사용자 대화/출처 hash·전체 exact source catalog·completeness·등록도구·공개 경로 parser·민감 marker·analysis stop·미해결 선행 호출을 재확인한다. 모두 충족한 같은 call만 EXECUTING으로 단회 예약한다. 원 analyzed_at/snapshot/reason을 보존하고 별도 forward_check에 checked_at/정책·grant/request/source/action hash와 model0 근거를 남긴다.

전체 lease/30초 의미 판정 시효를 늘리지 않았다. 기존 READY에 marker를 소급 추가하지 않고 기존 READY/UNKNOWN을 해제·재실행하지 않았다. 의미 ALLOW·예외 승인·native·민감/보호/범위밖 읽기·변경된 문맥·재전송·UNKNOWN은 이 경로로 갱신하지 않는다. 예외 승인 소비도30초 지난 분석을 덮어써 되살리지 않고 APPROVAL_SNAPSHOT_STALE로 원자 rollback/미소비 거절한다. 자동 유료 재분석/위험 쓰기 재시도/예산 환불0이다. 최종 검증·예약 뒤에만 기존 body+call+30초 HMAC ticket을 발급하고 upstream NOFOLLOW/regular/hardlink/내용 검사를 유지한다.

gateway 설정의 유일한 diff는 진단용 `x-with-human-request` 전달이다. bridge가 무작위 nonce를 생성하며 권한 정보가 아니다. private mTLS authz는 거절 시 token hash+nonce+실제 tool/args hash에 고정 사유와 call SHA만 결합해60초/128개 보관한다. 별도 machine 인증 TLS `/transport-rejection` 조회를 검증했을 때만 CONTROL_FRESHNESS_REJECTED/CONTROL_AUTHENTICATION_REJECTED/CONTROL_POLICY_OR_STATE_REJECTED와 allowlist reason/call_ref를 표시한다. 확인 불가능한401/403은 HTTP_REJECTION_UNCLASSIFIED다. arbitrary gateway/upstream 본문·문자열·헤더를 신뢰하지 않고 TLS/transport 장애는 따로 분류한다. 진단은 실행 재시도가 아니며 기존 failure 수집은 EXECUTING만 UNKNOWN으로 남긴다. 확인된 REJECT에는 실제 call 감사 상관관계를 추가했다.

## T-JEV-04 준비·전송 경계

새 `scripts/jev_eval.ps1`/`tools/jev_eval.py`는 별도 ignored `artifacts/runtime-jev-eval`만 사용한다. 키 입력 전에 ignore/owner-SYSTEM ACL(Windows, POSIX700/600)을 확인하고 숨긴 사용자 입력→stdin→새 key 파일로 저장한다. key/config/plan/source는 RO, provider ledger/results만 RW container mount다. 기존 개발 image ID와 --pull never·비root·RO rootfs·cap-drop·no-new-privileges를 사용하며 새 다운로드/이미지/패키지는 없다. 기본 policy.enabled:false와 기존 -JevRules/키 없음 readiness를 보존한다.

prepare/preflight는 network none/모델0이며 key metadata만 검사한다. endpoint/실제 키 인증/고정 모델 접근은 NOT_VERIFIED다. 실제 사용자 hidden UI는 NOT_RUN이고 공개 FAKE key의 stdin·ACL·실제 Docker prepare→preflight→collect를 격리 복사소스에서 검증했다. 원장·결과·기존 준비를 덮어쓰거나 초기화하는 명령은 없다. collect는 source가 이후 변경돼도 동결 계획/한도를 확인해 읽기만 하고 불일치를 표시한다.

[한국어 smoke 두 후보](../../../../fixtures/jev/smoke.json)는 정상 배포 사실 활용1/외부 추가 거짓보고 지시1이며 각 A/B의 정확 body와 기존 고정 질문을 inspect로 확인한다. 라벨/정답은 wire state/questions에서 제외한다. 기존 calibration/holdout/질문/임계치를 바꾸거나 전체 자동 호출하지 않는다. 실제 도구/파일 효과0인 adapter 연결 smoke로만 준비했다.

고정 endpoint `https://api.typesafe.ai/v1/systemone`/model `jev-1.13.0`, 최대4요청·요청당64000/총256000 입력 토큰 보수예약은 **제안**이다. actual usage가 아니다. 2026-10-16 [공식 가격](https://docs.typesafe.ai/models)은 입력 USD0.042/Mtok·출력 무료로, 제안 예약의 단순 세전 산술값은 **USD0.010752**다. 계정 계약·최소과금/반올림·세금/환율·변경·실패 과금은 검증하지 않았으며 provider 결제의 강제 상한을 보장하지 않는다. [공식 API](https://docs.typesafe.ai/api)의 실제 응답/모델 접근 호환성도 사용자 제한 시험에서 확인해야 한다. 누락 usage는 총금액 null/UNKNOWN, 기록 부분합과 구분하고0원/환불로 취급하지 않는다.

사용자가 자료/질문·manifest SHA·최종4/256000/비용 제안을 확정하고 명시 실행할 때만 별도 authorized-run config가 생긴다. 기존 원장22/24와 섞지 않으며 GPT fallback/alias/HTTP retry/redirect/프록시 상속0이다. 제한 helper만 A 성공 뒤 B를 시작하고 첫 실패 뒤 B/다음 후보를 중단한다. 기존 production JevPolicy의 A/B 병렬 구현은 변경하지 않았다. 실패는 ANALYSIS_UNAVAILABLE/NOT_SCORED이며 공격 식별 PASS가 아니다. 실제 TypeSafe key/config/ledger는 현재 제품에 추가/마운트/활성화하지 않았다.

## 실제 검증 결과

| 검증 | 결과와 근거 |
|---|---|
| 최종 관련 회귀 | **346 PASS/42.56초**: hookgw+SPEC4/F3+harness, network none/RO source/임시 DB. [명령/시각/소스](../../../../artifacts/20261016-wait-jev-prep/final-regression-command.json), [출력](../../../../artifacts/20261016-wait-jev-prep/final-regression.txt). source fingerprint는 최종200파일과 동일. |
| 실제 pinned gateway | **45/45 PASS**: [probe](../../../../artifacts/20261016-wait-gateway/final-r5-probe.json)/[effects](../../../../artifacts/20261016-wait-gateway/final-r5-effects.json). 즉시·91초 읽기 각attempt1/OBSERVED/완전출처, 경쟁 합계1. 인자/turn/grant/policy/보호/source/request/미해결/UNKNOWN/의미만료/세션·연결만료/analysis stop·범위밖 후보 모두attempt0.13종 실제 gateway 헤더→Control TLS 고정사유·callhash와 잘못된nonce UNCONFIRMED 검증. 실제 잘못된 인증403·잘못된CA TLS 거절은 별도. 실제401 서버 응답은 미실행이며 fake bridge에서401/403 미분류 동작 확인. |
| 별도 AI | **223 PASS/3.94초**, 자체26개 포함. 작성자 시험과 겹쳐 합산하지 않는다. WAIT-R01/R02 최초 발견→수정→재진단 보존, 미해결 차단0. [REVIEW](../20261016-wait-jev-review/REVIEW.md). |
| 사용자 평가 helper | **105 PASS/1.67초**(helper24+기존 adapter50+policy31), 위346과 겹침. fakeHTTP 정상/공격 exact ref 합성4요청/256000, 첫401/403/429/500/302 실패1요청/64000·B/후속0. Windows ACL/ignored·fake stdin·실제 Docker 모델0 준비와 무승인 evaluate 거절. [인계](../../../../artifacts/20261016-wait-jev-prep-helper/HANDOFF.md)/[정확 명령](../../../../artifacts/20261016-wait-jev-prep-helper/command-final.json). |
| 정적 | Ruff PASS, PowerShell AST 오류0. Bandit exit1 **High0/Medium2/Low14** 원 경고 보존. 기존 container0.0.0.0 bind(B104)는 host127.0.0.1+역할인증/private mTLS, B108은 고정 container tmpfs `/tmp` mount이며 host 예측 임시 파일이 아니다. Low subprocess는 고정 trusted executable/argv·shell=false, B105의 None/256000은 key가 아닌 예산 정책 값이다. 수동 검토/원 경고를 보존하며 suppression/전체49 PASS 선언0. [진단](../../../../artifacts/20261016-wait-jev-prep/bandit.txt). |

처음 root 시험은 PowerShell native 배열 전달 오류로 Docker 실행이 실패했고, Ruff는 RO source에 cache를 쓰려다 실패했다. 배열 인자와 --no-cache로 재진단했으며 실패 증거를 보존했다. 격리 gateway는 subnet pool/계약·mountpoint/빈 legacy sentinel 준비 오류, upstream 교체 뒤 DNS cache로503/attempt0, 반복 fixture의64세션 상한에 도달한 실패를 보존했다. 한도를 늘리지 않고 앞선 DB를 보존한 새 fixture DB에서45/45를 확인했다([전체 이력](../../../../artifacts/20261016-wait-gateway/README.md)). helper 첫 `/runner.py` 경로 IndexError도 원 소스 보존 후 수정했다. 실패/설정 장애를 공격 식별 PASS로 계산하지 않았다.

별도 AI WAIT-R01은 병렬 A/B가 첫 장애 시 두 provider 예약을 시작하는 비용 위험이었다. 평가 helper 전용 순차 fail-stop으로 재진단했다. WAIT-R02는 누락 usage를0비용처럼 읽을 가능성이었고 기록 부분합/총액 UNKNOWN을 분리했다. [최초 발견](../../../../artifacts/20261016-wait-jev-review/initial-findings.json)/[조치·재진단](../../../../artifacts/20261016-wait-jev-review/findings-final.json).

## 제품 코드 통합·보존

최종 **200파일 fingerprint `5e023a303a2e48569efbc326c49172972cd4a0054b6103bc3c36a085820b395b`**, [manifest](../../../../artifacts/20261016-wait-jev-prep/final-source/manifest.json)/[변경15파일](../../../../artifacts/20261016-wait-jev-prep/source-delta.json). 정책/권한 범용 완화나 관리 문서/장부/AGENTS/skill 변경0이다.

기존 명시 code-only bundle/update·upgrade_product를 사용했다. 이전 bundle35파일 manifest SHA `816211073c88452ac28dcde64263ea097d540f6599d42d1447f3b66c1ed9d745`를 archive로 보존·검증하고 제품 volume만 새 SHA **`ebedb6876e91fb8b2d035d9d03d7cd496bf33e9911946d83eff614b28bebb546`**로 갱신했다. installer는 uid10001/network none·제품 volume만 RW, role key/DB/원장 mount 없이 수행했다. 기존 GPT/Jev rules-only 서비스는 동일 키/설정/volume으로 재개하고 gateway를 reload했다. 진단용 gateway_rejections additive schema 생성이 있으므로 DB bytes 무변경이라고 주장하지 않는다.

[실제 Windows PS5.1 모델0 preflight](../../../../artifacts/20261016-wait-jev-prep/actual-manual-preflight.txt)는 **ready=true/issues=[]/frozen bundle verified**, 설치CLI0.154.0/user/on-request/기존sandbox·hooks 유지·TLS·stdio initialize→initialized→tools/list→임시 unbound connection 정리 PASS다. product tools/call·turn/candidate·모델0, TypeSafe NOT_AUTHORIZED·semantic_write_ready=false·key/ledger 없음이다. 이 점검은 실제 사용자 승인 성공이나 모든 managed 계층 집행을 입증하지 않는다.

[보존 전후](../../../../artifacts/20261016-wait-jev-prep/preservation-final.json): GPT5/Jev6 전체 history hash(원 call/reason/state 포함) 동일, 개인 config/auth·기존 key·프로필/CA/token·공개 notes SHA 동일, OpenAI **22/24·남은2/장부 SHA 불변**. 기존 READY/UNKNOWN을 수정·해제·재실행하지 않았다. 실제 사용자 key가 저장될 루트 runtime-jev-eval은 만들지 않았고 fake 준비는 격리 복사본에만 있다. fixture DB/키/원증거는 기존 것과 분리하며 삭제하지 않았다.

검증을 마친 테스트 전용8033/8043 fixture 서비스는 정지하고 원증거/DB volume은 보존했다([정지 명령](../../../../artifacts/20261016-wait-jev-prep/fixture-stop-command.json)). 기존 GPT/Jev rules-only 제품 서비스는 유지한다.

## 사용자 최소 명령·다음 승인 범위

현재 해도 되는 준비는 다음뿐이다. **키는 채팅에 보내지 말고 첫 명령의 숨긴 입력창에 직접 입력한다.** 기존 폴더/키가 있거나 ignore/ACL 오류가 나면 반복/삭제하지 말고 고정 코드와 함께 중단한다.

```powershell
cd C:\sogaeding
.\scripts\jev_eval.ps1 -Mode prepare
.\scripts\jev_eval.ps1 -Mode inspect
.\scripts\jev_eval.ps1 -Mode preflight
.\scripts\jev_eval.ps1 -Mode collect
```

preflight에서 default_enabled=false/live_authorized=false/ready_for_user_opt_in=true/provider_access=NOT_VERIFIED_NO_REQUEST/paid_requests=0을 함께 확인한다. actual key 인증/모델 접근을 확인한 결과는 아니다. inspect는 정확한 합성 요청·자료·질문/criteria·A/B body와 manifest SHA를 출력한다.

관리에서 이 자료/고정 endpoint/model/최종4요청·256000예약·가격 제안을 확정한 뒤에만 사용자가 다음을 한 번 실행할 수 있다. **현재 실제 평가 실행 승인은 없고 개발 AI는 실행하지 않았다.**

```powershell
$inspection = .\scripts\jev_eval.ps1 -Mode inspect | ConvertFrom-Json
.\scripts\jev_eval.ps1 -Mode evaluate -ConfirmSend `
  -ManifestSha256 $inspection.manifest_sha256 `
  -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000
.\scripts\jev_eval.ps1 -Mode collect
```

실패 뒤에는 collect만 한다. 원장/실행 config 삭제·키/모델 교체·예산 초기화로 반복하지 않는다. 실제 CLI/의미 쓰기/실파일 효과 통합과 calibration/holdout 전체는 별도다. 새 공개 notes CLI 재시험도 관리에서 이번 새1회/같은 공개 자료의 actor 전송·정확 read 범위를 확정한 뒤에만 한다. 준비된 과거 opt-in 명령은 유지하지만 이 RESULT를 자동 실행 승인으로 해석하지 않는다.

일반 native 개발·hook 사망/timeout/malformed fail-open·개인 bob MCP 경고·전체 TLS negative/키수명·공급망 잔여·실제 Jev 한국어/공격 성능은 미완료다. 출처 일치는 관측이고 인과 증명이 아니다. 전역 DONE/MVP 수용은 관리 세션이 판단한다.
