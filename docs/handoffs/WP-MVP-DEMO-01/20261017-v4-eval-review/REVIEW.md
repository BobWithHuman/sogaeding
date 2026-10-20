# V4 고정 평가 연결 — 별도 AI 검토

2026-10-17, Asia/Seoul. 구현자와 분리된 AI 검토 1회이며 추가 사람 개발자나 공식 독립 보안진단이 아니다.

최종 결론: 이번 고정 평가 연결·모델0 실행 준비 범위에서 수정이 필요한 발견사항은 없다. 실제 준비 manifest/preflight/USER_RUN까지 대조했고, 사용자 직접 평가 한 번을 위한 준비로 수용 가능하다. 실제 Jev/actor/CLI 전송 및 서비스 교체는 이 검토에서 수행하지 않았다.

## 검토 대상과 방법

`V4_EVAL_START_PROMPT.md`, 관리 V4 후보 수용문서 및 고정 평가 제안을 기준으로 `tools/jev_eval.py`/`scripts/jev_eval.ps1`를 작업 전 baseline과 비교했다. 신규 `tests/hookgw/test_jev_v4_eval.py`, 기존 `JevClient.observe`/요청/예약/응답 검증, V4 build/compose/validated refs/서버 combine 경로와 관련 시험 원기록도 대조했다. 검토 source SHA는 `artifacts/20261017-v4-eval-review/reviewed-source-manifest.json`에 있다. 제품/관리 정본/기존 후보7파일은 수정하지 않았다. 원키/키hash/원장 내용은 읽지 않았으며 독립 시험은 임시 가짜키·가짜원장·httpx MockTransport만 사용했다.

- 전송 전 네 고정 wire를 실제 V4 build·질문·criteria와 대조한다. 순차 observe 정상A→B→공격A→B 후 기존 typed/compose/ref 검증/combine을 재사용하고 재관측하지 않는다. expected_local_only는 전송 wire 밖에 있다.
- 새4/256000, demo12/768000, 전체17/1088000 및 추가CLI0을 고정하고 명시 정확 manifest 승인 뒤 exclusive execution.claim으로 단회 실행한다. 이전13/832000과 demo8 CLOSED 상태/원bundle·source·image·wire binding을 유지하며 collect는 읽기 전용이다.
- 첫 transport/shape/usage/ref/분석 실패는 후속 요청을 중단한다. null/부분usage는 예약을 유지하고 미채점으로 기록한다. 유효 낮은 confidence/CONFIRM은 유효 결과이며 추가 교정 요청을 하지 않는다. exit0를 의미 성공으로 표시하지 않는다.

## public digest guard 경계의 독립 확인

기존 generic guard는 고정 V4의 public raw/text SHA를 긴 토큰으로 잡는다. 평가 worker 내부 subclass는 실제 build 및 고정 wire SHA를 먼저 검증한 뒤 그 두 필드만 scanner 입력에서 public metadata placeholder로 구분한다. 다른 필드는 기존 guard를 거치며 `_request`는 scanner body 일치·원래 bytes 크기·원문 내 실제 key 부재를 확인한 후 승인된 원래 bytes를 기존 TLS/retry0 transport로 보낸다. 전역 mask/guard나 제품 JevClient는 변경하지 않는다. 따라서 임의 source/비밀자료에 일반 예외를 주는 경로가 아니다.

독립 반례 **9 PASS/6.73초**, network none:

1. raw SHA/text SHA/일반 candidate/질문 변조 각각은 manifest-wire 검증에서 claim 전 거절(4건).
2. 가짜 API key를 고정 public raw digest와 같게 선택하면 정상A 뒤 B의 원문-key 검사에서 전송 중단. provider1건·예약2건 보존(1건).
3. compose/ref 분석 실패를 각 A/B 위치에 주입하면 해당 관측까지만 호출하고 후속/재관측0(4건).

원기록: `artifacts/20261017-v4-eval-review/boundary-tests.txt`, `boundary-command.json`, `test_review_boundaries.py`. 최초 sandbox Docker pipe 접근거절 뒤 네트워크 없는 동일 시험을 승인된 Docker 접근으로 실행했다. 유료 통신은 없었다.

## 최종 준비자료 대조

작성자 최종 관련 runner/transport/기존 run 회귀 **207 PASS/36.67초** 및 PowerShell5.1 fixture21+V4 전달/거절4 PASS 원기록을 확인했다. 단순 문구/hash 기록을 이유로 전체688 시험을 반복하지 않았다. 최종 source3파일의 SHA가 검토 당시와 동일하다.

실제 새 run은 `followup-auto-v4`, 정확 manifest SHA는 `9aa11ab1b12fd231c2a39d52308eb60a1ea12fdc71514647d6ab50494bbdc23c`다. inspect/preflight 기록과 실제 준비 manifest hash, requests hash, 동결source54개의 현재 SHA를 직접 대조해 모두 일치했다. 공개 inspect의 parent는13/832000을 보존하고 제안 한도는 새4/256000·demo12/768000·전체17/1088000·CLI0이다. 이 마지막 대조에서 기존 원장/키 본문/hash는 읽지 않았다.

`prepare.json`/`preflight.json`은 disabled/paid_requests0/actual_key_readfalse/provider_ledger_presentfalse/exact_wire_build_verifiedtrue/ready_for_user_opt_intrue다. `collect-before-user-run.json`은 NOT_RUN/NOT_ATTEMPTED2, collect readonly 비교는 준비파일3개 동일 및 ledger/claim/authorized config 부재다. 독립 대조 결과는 `artifacts/20261017-v4-eval-review/prepared-review.json`에 있다.

`20261017-v4-eval/USER_RUN.md`의 한 줄 evaluate는 실제 hash와 필요한 명시 한도8개가 일치하고 `-ConfirmSend`를 포함한다. collect는 동일 fixed RunId만 선택한다. 사용자에게 prepare/plan/key 입력을 다시 요구하지 않는다. 자식 PowerShell의 ExecutionPolicy Bypass는 해당 프로세스에만 적용되며 영구 설정 변경 명령은 없다. 이 문서의 명령을 검토했으며 실제 evaluate는 실행하지 않았다.

## 정적 진단과 필수 가이드

작성자 Ruff PASS와 Bandit 원본 27 Low/1 Medium을 확인했다. Bandit 0건 또는 전체 보안 PASS로 재표시하지 않는다. B603 신규 v4_prepare call은 검증한 외부 Docker 실행파일·고정 argv·image digest·shell 미사용·network none _plan으로 좁혀져 있다. B105의 None/256000은 비밀이 아닌 disabled 정책/한도 정수다. B108 `/tmp`는 격리 Docker tmpfs mount의 literal이며 호스트 공용 임시파일 생성 경로가 아니다. B404는 기존 subprocess import 경고다. 기존 호출부까지 포함해 입력/출력/키 경계를 수동 대조했으며 도구 경고만으로 정탐/전체 안전을 단정하지 않는다.

`docs/plans/03_guide_compliance.md` 및 기존 `artifacts/20261017-auto-decision/guide-pages.json`의 R1 PDF14/G1 PDF35~36(통합·공급망 검증), G2 PDF128(경쟁), G3 PDF507~510(명령·보안입력·접근·보호전송), G4 PDF24(검토·동적 검증)를 이번 변경에 연결했다. exact manifest/singleclaim/source·wire·parent 결합, 고정 전송대상과 기존 TLS, canary guard·가짜 provider 실패중단 시험이 해당 범위의 증거다. 설계20/약점49 기존 미점검·미구현 상태를 PASS/비적용으로 올리지 않았다.

## 남은 범위

실제 모델 응답·정상 자동ALLOW/공격DENY·모델 정확도·파일 효과·actor 보호·native/hook 장애·전체 IPI/MVP는 NOT_RUN 또는 기존 미완료다. 고정 정상1/공격1의 의미 smoke만 준비하는 변경이다. 서비스/승인/단회 실행/UNKNOWN/TLS 정책의 수용 범위를 확대하지 않는다. 제품 유료 호출0은 개발 AI 토큰0이라는 뜻이 아니다.
