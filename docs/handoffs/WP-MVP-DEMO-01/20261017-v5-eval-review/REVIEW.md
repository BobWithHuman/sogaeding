# V5 고정 4요청 준비 별도 AI 검토

2026-10-17. 검토 역할: 구현 담당과 분리된 보조 AI 1개. 사람/공식 독립 진단으로 표현하지 않는다. 제품 코드 수정 없이 배정된 검토 문서·증거만 작성했다.

## 판단

검토한 최종 후보에서 차단할 결함을 발견하지 않았다. 관측 범위는 기존 평가 도구의 V5 고정 실행 경로와 무모델 준비이며, 관리 수용 또는 실제 모델 성공 판정은 하지 않는다.

- `tools/jev_eval.py`, `scripts/jev_eval.ps1`, `tests/hookgw/test_jev_v5_eval.py`, `docs/mvp/09_rules_first_jev.md`의 실제 변경 및 변경 전 원본을 대조했다. 검토 시점 4파일 SHA는 `artifacts/20261017-v5-eval-review/reviewed-source-manifest.json`에 기록했다.
- 실제 준비 manifest SHA는 `84a51d1653b7e8523c2ccadf16f3c069f62ff8212ee617cd21f1012d7221c401`이며 inspect/원 plan wire SHA와 일치한다. manifest의 source 60개는 현재 파일과 전부 일치한다. 원 V4의 정상·공격 snapshot 각각이 정확히 동일하다.
- 준비 정책은 disabled이며 execution claim, authorized config, 새 provider ledger, 실제 result가 없다. preflight의 `ready_for_user_opt_in=true`와 `NOT_VERIFIED_NO_REQUEST`를 실제 파일 상태 및 소스 동작과 구분해 확인했다. 실제 키 본문·기존 원장은 이 검토에서 읽거나 mount하지 않았다.

## 경계 검토

1. 고정 run ID/원 plan SHA/정상·공격 snapshot SHA와 실제 V5 `build`를 통해 정상 A→B, 공격 A→B 4개 wire를 생성하고 worker에서 재구축·대조한다. 로컬 case/기대값은 wire에 삽입하지 않는다. A에는 외부 source가 없고 B의 short key/원문 및 서버 inventory와 질문 분리를 유지한다.
2. V5 worker는 표준 `JevClient`를 사용한다. 기존 V4 `FixedPublicDigestClient` 예외의 선택 범위를 확장하지 않았다. TLS·민감값 guard·응답계약2·usage·.90 및 원 V5 행동/귀속 분리 조합을 그대로 사용한다. 합성 높은 정상 ALLOW/확정 외부행동 DENY와 낮은 행동확신 CONFIRM은 의미 모델의 실제 답으로 표현하지 않는다.
3. 첫 transport/응답/ref/usage/분석 실패 후 뒤 요청을 중단한다. 예약은 소비 상태로 보존하며 자동 재요청·환불 경로를 추가하지 않았다. null usage 및 중단 결과는 성공으로 바꾸지 않는다.
4. 부모 binding은 역사4원장 총 17/1088000과 원 V3 bundle에 묶인다. 추가4/256000, 전체21/1344000, demo관련16/1024000을 모두 명시적으로 검사한다. 기존 demo ledger를 증액하지 않고 prepare는 새 지출권한을 만들지 않는다. 정확 manifest/현재 source·image·parent 재검사 뒤 `open('x')` claim을 생성하며 재실행을 거부한다.
5. historical collect는 현재 source 불일치를 표시하면서 역사 result를 보존한다. claim 뒤 result 유실은 실행 UNKNOWN·재시도 금지로 표시한다. 실제 PowerShell 5.1 probe의 4개 검사는 fake helper의 인자/오류 경계만 확인했으며 모델 전송 시험이 아니다. USER_RUN의 evaluate 한 명령은 위 manifest와 모든 추가/누적 한도를 포함하고 이어 collect 명령을 제공한다.

## 검증 증거

별도 reviewer가 network none/read-only/cap-drop Docker에서 추가 반례 **3시험 PASS, 8.76초**를 실행했다. 실제 키·역사 원장은 mount하지 않았고 모든 DB/키는 pytest 임시 합성 fixture다.

- 8개 한도 필드마다 float/초과값/bool 총 24개 승인값 및 manifest의 float 한도 거부: HTTP·claim·authorized config·새 ledger 모두0.
- claim/authorized config/ledger/result 중 한 개만 이미 있어도 재전송 거부.
- plan Docker의 credential/budget mount 없음, 평가 credential mount RO와 offline/live network 선택 경계.

명령·출력: `artifacts/20261017-v5-eval-review/independent-command.json`, `independent.txt`, `test_independent.py`. 최초 sandbox Docker API 접근은 실행 전 permission denied였고, 승인된 동일 network-none 명령으로 실제 시험을 실행했다. 제품 실패나 유료 요청이 아니다.

구현 담당의 관련 fake transport 시험은 정확4 wire/표준 guard/행동조합/첫오류 중단/부분usage/변조·오래된 입력/parent·image/claim 경쟁을 포함함을 코드와 원출력으로 확인했다. 최종 통합은 **275 PASS/5 FAIL, 288.27초**였고, 실패5개 모두 기존 실응답 재현의 원 result 파일이 시험 mount에서 누락된 `FileNotFoundError`임을 확인했다. 제품 소스 변경 없이 정확 원 result 1파일의 RO mount를 추가한 관련5개 재진단은 **5 PASS/30 deselected, 1.39초**다. 따라서 최종 후보의 관련280개 범위가 해결됐으며 단일 280 PASS 실행으로 표현하지 않는다. 원명령/출력은 `artifacts/20261017-v5-eval/integrated-command.json`, `integrated.txt`, `replay-repair-command.json`, `replay-repair.txt`다. V5 새38개는 첫 통합에서 모두 통과했다.

Ruff PASS, Bandit LOW28/MEDIUM1 원진단을 숨기지 않았다. 고정 subprocess argv·tmpfs 문자열·평가/동결 hash 상수에 대한 잔여 정적 진단이며 전수 보안 준수 PASS로 바꾸지 않는다.

## 보존 및 필수 가이드

`preservation-check.json`으로 V4 동결54개와 실제 plan/result 2개 총56개를 재해시했다. 허용된 helper/wrapper 2개만 바뀌었고 저장 원본은 변경 전 SHA와 일치한다. 나머지52개, 실제 plan/result는 유지됐다. V5 후보4개는 동결 manifest SHA와 일치하며 Engine/server/DB/서비스는 변경 범위에 없다. 원 역사 manifest를 새 source에 맞춰 덮어쓰지 않는다.

구현 측 `collect-readonly-check.json`의 역사3종 collect는 현재 source 불일치 false를 정직하게 표시하며 결과를 보존한다. 준비3파일도 읽기 전후 그대로다. `final-state.json`은 기존4원장 hash변경0/누적17·1088000을 기록하며 `success-report-preservation.json`의 V3 성공 보고서 SHA `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0`도 유지됐다. 이 검토는 위 안전한 보고서를 읽었고 실제 원장/키 본문을 직접 열지 않았다.

필수 원문은 기존 `artifacts/20261017-auto-decision/guide-pages.json`의 발췌를 재사용하고 원 PDF5개 SHA를 다시 대조했다(`guide-reference-check.json`, 전부 일치). R1 PDF14/G1 PDF35–36은 출처·빌드/검증 결합, G3 PDF507–508은 고정 입력·보안 인자·server 권한 검증, G2 PDF128–129는 단회 상태/유한4요청, G2 PDF135·137 및 G4 PDF24·38은 실패 처리·진단/수정/재검증·보호된 키 참조, G3 PDF510은 기존 보호 전송/키 분리 유지에 연결한다. 설계20/약점49 마스터 적용성 및 부분 보안 게이트를 전수 완료로 올리지 않는다.

## 미검증

실제 TypeSafe/actor 호출0, CLI 시작0, 서비스 교체0. 제품 유료 호출0은 개발 AI 토큰0을 뜻하지 않는다. 실제 V5 behavior 답/정상 자동ALLOW/공격DENY/효과 통합/일반 native/hook 장애/정확도/전체 IPI 및 MVP 완료는 미검증이다. 평가 후 CONFIRM·불일치라도 원결과를 보존하며 자동 반복·임계치 하향·새 질문/유료 run 연속생성으로 보정하지 않는다.
