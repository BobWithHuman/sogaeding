# T-JEV-07 한정 후속 실행 연결 결과

배정: FOLLOWUP_EXECUTION_START_PROMPT.md 전체 지시. 사람 개발자는 사용자1명이며 root 통합/jev_adapter 제한 helper 구현/jev_review 별도 AI 검토를 구별한다. 관리 plans/harness/AGENTS·제품 PDP/권한·모델·질문·임계치는 읽기 전용으로 유지했다. 전역 DONE은 관리 세션 판단이다.

## 목적과 실제 전송 범위

수정된 응답 계약2를 사용해 고정 후속 run `followup-response-v2`의 inspect → 모델0 preflight → 사용자 명시 evaluate → collect를 연결한다. 기존 비실행 followup-plan을 묵시적으로 승격하지 않는다. 새 framework/모델·질문·의미정책·threshold를 추가하지 않는다. 실행 가능한 준비와 실제 모델 성공은 별개다.

endpoint는 https://api.typesafe.ai/v1/systemone, model은 jev-1.13.0이다. fixtures/jev/smoke.json의 동일 S01 정상 배포 사실 요약 후보와 S02 외부 지시를 따른 거짓 보고 후보, 분리 A/B state/고정 질문만 보낸다. expected_local_only는 wire에 넣지 않는다. 제품 도구/실제 report.txt 쓰기0이며 프로젝트 소스·PDF·비밀을 모델 문맥에 넣지 않는다. 개발 AI의 실제 provider/actor 호출은0이다.

## 실행 계약과 보존

고정 한 슬롯만 새 followup-prepare로 만들 수 있고 source/image/정확 wire/부모 manifest·원장 관측·원키 RO 경로에 결합한다. 기본 disabled이며 새 ledger/authorized-run/실행 선점/결과 없이 준비한다. inspect/preflight는 metadata만 확인하고 실제 provider/model 접근은 NOT_VERIFIED_NO_REQUEST다. 키 재입력/복사/본문·해시 출력은 없다. Docker source/plan/key/config RO, 새 ledger/results만 RW, image no-pull/nonroot/network none preflight를 유지한다. 실제 사용자 평가에서만 제한 네트워크를 열며 기존 TLS검증/redirect0/proxy비상속/retry0/timeout은 유지한다.

evaluate는 RunId/정확 manifest/ConfirmSend와 새4/256000·누적5/320000·추가1/64000을 모두 명시해야 한다. 영구 단회 선점 후 authorized-run을 만들고 provider를 시작한다. 경쟁/재실행·선점 이후 장애/UNKNOWN에 자동 재호출·선점삭제·환불0이다. 실패 뒤 collect만 안내한다. A→B 순차와 첫 오류 뒤 다음view/case0을 유지한다. 안전 stage 진단과 독립 유효 usage/부분UNKNOWN은 기존 응답 계약2를 재사용한다.

기존 runtime-jev-eval의 원계획/manifest/disabled policy/authorized-run/실패 결과/원장은 보존한다. 과거 FAILED1/A/64000/usageNULL, S01 NOT_SCORED/B중단/S02미시도를 유지한다. 과거 원응답이 없어 실제 실패 원인·사용량/청구액은 UNKNOWN이다. 원래 한도4/256000에서 잔여3/192000이며 새4회는 기존 승인을 재사용하는 것이 아니다. 누적최대5/320000·추가1/64000이다. 새 예약 입력 산술액 USD0.010752는 실제 계정 청구 보증이 아니다. 개발 준비는 실행/증액 승인이 아니다.

## 기준선·증거와 사용자 절차

기준선203파일 fingerprint `4f0d4949f158928130f81b3424f493ec959ce635b5366975523bf625e1466214`를 다시 고정했다. 보존된 기준선만 마운트한 모델0 회귀는393 PASS/38.04초다. artifacts/20261016-jev-followup/baseline-source/{manifest,summary}.json 및 baseline-regression-command.json/출력에 기록했다. wrapper의 명령 시점 snapshot과 실제 시험한 frozen baseline 경로를 구별한다.

실제 후속 준비의 run/manifest와 최종 검사 결과·정확 evaluate 명령은 아래 최종 검증 절에 기록한다. [사용자 절차](USER_RUN.md)는 inspect/preflight/collect와 실패 뒤 중단 원칙을 설명한다. 실제 evaluate는 사용자가 자료·목적지·정확 해시와6개 한도를 검토한 뒤 직접 한 번만 선택한다.

## 최종 검증과 준비된 run

최종204파일 fingerprint는 `c2b9455912467c907d6639ab326217ff32a2e2e8f5027462699e28080c07521a`다. artifacts/20261016-jev-followup/final-source/{manifest,summary}.json에 고정했다. 변경은 tools/jev_eval.py, scripts/jev_eval.ps1, 새 tests/hookgw/test_jev_followup_execution.py, docs/mvp/09_rules_first_jev.md다. 제품 source/PDP/응답계약2·기존 테스트는 변경하지 않았다. source_hashes에 PS wrapper를 추가하고 source symlink/junction/outside/hardlink를 해시 전에 거절한다. 승인 후 preflight 사이 manifest가 바뀌어도 선점 전에 거절한다.

| 검증 | 실제 결과 | 원증거 (artifacts/ 아래) |
|---|---|---|
| 최종 hookgw/F3/harness 회귀 | 413 PASS/37.05초 | 20261016-jev-followup/regression-command.json, regression.txt |
| 저자 helper/실행 회귀 | 64 PASS/2.57초 | 20261016-jev-followup-helper/ 인계 |
| 별도 AI 독립/관련 회귀 | 자체38 포함250 PASS/15.84초; 중복 합산X | 20261016-jev-followup-review/ 별도 REVIEW |
| 실제 Windows PS5.1 fake argv/인코딩/오류·승인 누락 | 34/34 PASS | 20261016-jev-followup-review/native-result.json, native-r2-command.json |
| 새 실제 prepare/inspect/preflight/collect | 모두 exit0, 모델0, ready:true/disabled/ledger없음/claim없음 | 20261016-jev-followup/actual-{prepare,inspect,preflight,collect}-command.json 및 .txt |
| 정확 합성 plan/네 wire·현재38소스 바인딩 | 부모와 전체 plan 동일/4wire 동일/소스 불일치0 | 20261016-jev-followup/prepared-check.json, verify_prepared.py |
| legacy collect/원6파일·key metadata/ACL | 기존 실패 동일/모두 보존 | 20261016-jev-followup/legacy-collect.txt, preservation-{before,after}.json, preservation-check.json, key-metadata-{before,after}.json |
| Ruff | 프로젝트 규칙 PASS | 20261016-jev-followup/static-r2.txt |
| Bandit | 21 LOW/1 MEDIUM/HIGH0, exit1 보존 | 20261016-jev-followup/bandit.txt 및 command.json |

Bandit clean PASS가 아니다. T-JEV-06의14 LOW/1 MEDIUM 대비 새7 LOW는 후속 prepare/preflight/evaluate의 argv-list subprocess B603 3개와 None/256000 정책 값에 대한 B105 4개다. 실제 OS shell 문자열 실행·비밀번호 상수는 도입하지 않았다. 기존 B108은 컨테이너 전용 tmpfs 설정이며 호스트 공유 임시파일 생성이 아니다. 경고를 suppress하지 않았다. 최초 Ruff 명령은 pyproject mount 누락으로 이미지 기본 규칙7경고가 났고, 실제 프로젝트 설정을 마운트한 재실행은 PASS다. 제품 수정으로 경고를 숨기지 않았다. PS7 AST parse0은 보조 기록이며 실제 PS5.1 시험을 대체하지 않는다. 별도 native r1은 sandbox registry-read 제한의 AuthorizationManager 오류로 실행 전 실패했고 정책을 바꾸지 않은 native r2에서 통과했다. 실패 증거를 보존한다.

가짜 HTTP/공개 fake key·임시 원장에서 정상 ALLOW/DENY 관측4요청, 불량 답/HTTP실패 후1요청에서중단·partialusage/예약64000 유지, 누락/잘못된6한도·hash/run/source/PS/image/parent·경로/권한 거부, 같은 run 동시 prepare/execute의1승자, replay0을 확인했다. 선점 후 timeout·result/ledger 유실은 ATTEMPT_CLAIMED_OR_INTERRUPTED/EXECUTION_STATUS_UNKNOWN이며 새 호출을 추정·재시작하지 않는다. fake fixture의 정상/차단은 실제 모델 정확도·실행 전 IPI 방어 증거가 아니다.

준비된 실제 경로는 `C:\sogaeding\artifacts\runtime-jev-followups\followup-response-v2`이며 manifest SHA는 `91cd5d7772997b376aba2609b2fff4ffad14e70c51f2eeb6cd9f112d4f8a14ce`다. image ID는 `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`다. 원키는 `artifacts/runtime-jev-eval/key/jev.api-key`의 RO 디렉터리 참조만 사용했다. 키 본문/해시를 열거나 복사하지 않았다. 새 run은 disabled이며 execution.claim/authorized-run/ledger/result가 없다. actual preflight의 provider/model_access는 NOT_VERIFIED_NO_REQUEST, actual_key_read:false, paid_requests:0이다. collect는 NOT_STARTED/NOT_RUN/source_matches:true이며 과거 collect는 원래 ANALYSIS_FAILED_PARTIAL/source_matches:false를 보존한다.

아래 inspect/preflight 후 동일 해시·자료·목적지·새/추가/누적 한도에 동의하여 실제 시험하기로 선택할 때만 evaluate를 사용자 직접 한 번 실행한다. 개발 AI는 실제 evaluate를 실행하지 않았다.

```powershell
cd C:\sogaeding
.\scripts\jev_eval.ps1 -Mode inspect -RunId followup-response-v2
.\scripts\jev_eval.ps1 -Mode preflight -RunId followup-response-v2
```

```powershell
.\scripts\jev_eval.ps1 -Mode evaluate -RunId followup-response-v2 `
  -ConfirmSend `
  -ManifestSha256 '91cd5d7772997b376aba2609b2fff4ffad14e70c51f2eeb6cd9f112d4f8a14ce' `
  -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000 `
  -ApproveCumulativeRequestLimit 5 -ApproveCumulativeInputReservationLimit 320000 `
  -ApproveAdditionalRequestLimit 1 -ApproveAdditionalInputReservationLimit 64000
```

```powershell
.\scripts\jev_eval.ps1 -Mode collect -RunId followup-response-v2
```

오류/중단 뒤에도 마지막 collect만 사용한다. NOT_SCORED/NOT_ATTEMPTED/UNKNOWN과 프로그램 exit0을 의미 성공으로 해석하지 않는다. 준비 명령을 다시 시키거나 key/reset/새 plan을 만들도록 안내하지 않는다. 실행 시 소스·image·부모 원장이 달라지면 검사를 끄지 않고 중단한다. 현재 배정은 구현/준비이며 실제 전송/추가 비용은 사용자가 위 정확한 명령으로 새로 선택하기 전까지 미승인이다. 실제 Jev 수리 후 응답/usage·정확도는 NOT_RUN이다.

별도 [REVIEW](../20261016-jev-followup-review/REVIEW.md)를 함께 인계한다. 실제 보존6파일과 키 metadata/ACL 전후 동일, 원 FAILED1/64000/usageNULL 및 기존 예산 유지가 확인됐다. 기존 키/계획/실패 결과/원장·전역 설정/로그인/CA를 변경·초기화하지 않았다.

## 필수 가이드와 남은 범위

필수5개 원문 SHA·16페이지를 다시 대조·추출했다. artifacts/20261016-jev-followup/guide-pages.json 및 GUIDE_MAP.md에 코드/검증을 연결한다. R1 PDF14/G1 PDF35~38은 고정 image/no-pull·변경 무결성·검토/회귀, G2 PDF133/135/137·G3 PDF511/G4 PDF38은 오류·비밀 최소화/안전 실패, G2 PDF146·G3 PDF415는 자원/유한 수행, G3 PDF508/509·G4 PDF37/39는 권한 인자·경로·상태·중요자원 통제에 연결했다. 기존 설계20/약점49 적용성·미완료와 최초진단→조치→재진단을 유지하며 전수PASS/공식 조치율을 추정하지 않는다. 새 SDK/의존성/이미지 도입0이다.

신뢰된 helper 실행·동일 OS 사용자 경계가 전제다. helper 자체 AI 편집 hard-deny 방어는 미보장이다. 실제 Jev 서버 응답 호환/의미 정확도·holdout·Codex IPI·일반 native 지원·hook 장애·전체 공급망 항목은 미검증/미완료를 유지한다. 이 작은 평가 경로의 새 선행조건으로 전체 제품 보강을 추가하지 않았다. 분석 오류/미시도는 공격 식별 PASS가 아니다. 제품 기본 JevRules 배포·기존 DB/전역 설정은 변경하지 않았다.
