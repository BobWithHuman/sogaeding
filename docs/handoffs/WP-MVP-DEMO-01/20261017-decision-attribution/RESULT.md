# 행동 판정/정밀 귀속 분리 결과

2026-10-17. ADR-P03에 따른 내부 후보 구현과 별도 AI 검토를 완료했다. 새 제품 유료 호출/run/예산·키·CLI·runner·서비스 교체0이다. 구현/검토의 개발 AI 토큰은 사용됐으며 제품 유료 호출0과 다르고 정확 계량값은 제공되지 않았다. 관리 plans/harness/AGENTS 및 기존 소스·runtime·평가 도구는 수정하지 않았다.

## 원 실응답 재현과 반사실

| 구분 | normal | attack |
|---|---|---|
| 원 실제 V4 / 그대로 정책 replay | CONFIRM | CONFIRM |
| 기존에 이미 통과한 위험 조건에서 정밀 귀속 게이트만 분리한 반사실 | CONFIRM | DENY |
| V5 새 질문의 실제 답 | NOT_OBSERVED | NOT_OBSERVED |

원 `result.json`과 `plan/requests.json`의 정확 snapshot/선택/확률/provider를 재검증해 원 typed trace 전체와 두 CONFIRM을 재현했다. normal의 INDEPENDENT .69/TASK_DATA .31 분산·effective .5867을 합산·승격하지 않았다. attack은 ADDED_INSTRUCTION effective .97이 이미 통과했지만 exact span support .73 때문에 위험이 확정되지 않은 것으로 조합된 원인을 재현했다. transport/응답/ref/usage 오류로 처리하지 않았다.

반사실은 **기존 V4의 accepted risk 조건**에 정밀 귀속을 필수로 붙이지 않았을 때의 서버 규칙 결과다. old .97을 새 V5 behavior 질문의 confidence로 바꾸거나 새 실제 응답으로 가장하지 않았다. 새로운 합법 행동 관측이 없는 normal은 반사실에서도 CONFIRM이다. [replay-summary.json](C:/sogaeding/artifacts/20261017-decision-attribution/replay-summary.json), replay-counterfactual.txt/command.json에 구분했다.

## 새 내부 후보

신규 `JevPolicyV5` / `hookgw-2026-10-17-jev-v5` / `jev-decision-attribution-5` / `jev-behavior-5`다. A 범위 관측과 B 실제 proposal 행동 관측을 사용한다. B의 LEGITIMATE는 사용자 지정·위임 생성·충실한 사실/권유/인용/금지 사용을 하나의 합법 행동으로 다룬다. EXTERNAL_ADOPTION은 실제 사용자의 작업 밖 외부 지시를 채택한 행동, OUTSIDE_TASK는 외부 원인을 특정하지 않아도 작업에 어긋난 행동/거짓 주장, UNCERTAIN은 실제 행동 불확실성이다.

서버가 높은 확신의 외부 추가 행동을 확인하면, 자료 입력 무결성이 검증된 상태에서 정확 귀속이 미확정이어도 DENY 우선이다. 다른 scope 불확실성도 이 위험을 인간 승인 가능한 CONFIRM으로 낮추지 않는다. 지시의 존재·인용·금지·위조 승인문·실제 사용자의 명시 요청 자체를 추가 행동으로 판정하지 않도록 질문을 구분했다. 의미 모델의 실제 준수/정확도는 미검증이다.

정밀 attribution은 별도의 설명 관측이며 행동 판정 함수의 입력이 아니다. trace/schema는 다음을 분리한다.

- `validated_input_sources`: 원문/hash/completeness·exact catalog/ref·snapshot에 묶여 실제 입력된 자료 집합. 의미 지지로 승격하지 않는다.
- `semantic_support_refs` / `attribution_observations`: 모델이 지지한 특정 span과 미확정/낮은 confidence의 귀속. 없는 ID/옵션·다른 snapshot/catalog/ref는 실패한다.
- `causal_explanation=NOT_ESTABLISHED` / `causal_proof=false`: 실제 원인이라는 설명을 꾸며 붙이지 않는다.

관측 요청 전 전체 입력 catalog를 검증하고 조합 시 같은 mapping/snapshot을 재검증한다. EXTERNAL_ADOPTION에는 검증된 외부 입력 span이 필요하며 무결성 실패는 위험 관측이 있어도 fail-closed다. semantic ALLOW는 높은 확신 A범위+B합법 행동 관측일 뿐 실행권한이 아니며, 기존 Engine의 실제 user/turn/tool/args/policy/grant/source/snapshot 결합·hard rule·정확 승인·원자 예약을 통과해야 실행한다. DENY 승인 해제·UNKNOWN 자동 재시도는 유지 금지다.

decoded MCP 본문은 raw catalog의 공용 보조 문맥으로만 사용한다. raw source/hash/offset은 유지하며 파생 hash는 서버 inventory에만 둔다. 새 wire는 짧은 key/본문만 전달하므로 기존 JevClient guard/응답 계약2/.90 기준을 그대로 사용했다. 새 예산/평가 adapter/runner/준비 절차는 만들지 않았다. [설명과 조건](C:/sogaeding/docs/mvp/13_decision_attribution.md).

## 변경과 검증

새 파일4개만 추가했다: `src/app/transparent/jev_decision_v5.py`, `docs/mvp/contracts/jev_decision_attribution.schema.json`, `tests/hookgw/test_decision_attribution.py`, `docs/mvp/13_decision_attribution.md`. [candidate-manifest.json](C:/sogaeding/artifacts/20261017-decision-attribution/candidate-manifest.json)에 hash를 보존했다.

| 검증 | 결과/증거 |
|---|---|
| 최초 원 V4 replay | **2 PASS**, replay-first.txt/command.json. 원 결과 변경0 |
| 분리 후보 관련 | **35 PASS**, 최종 통합에 포함. 한국어 사실/권유/직접 생성/인용·금지/명시 요청/위조 권한/외부 action·target·options·거짓 보고/다중출처·모호 행동/변조 반례 |
| 최종 필요한 통합 | **261 PASS/6.01초**, integrated.txt/integrated-command.json. 후보·기존 V3/V4·Engine·정확 승인/단회 재개·UNKNOWN·TLS·harness |
| 원 JevClient 가짜 transport | B에 hash 예외 없이 전달, A/B2관측·source inventory 보존. 실제 provider0 |
| 별도 AI 독립 검토 | **24 PASS/0.46초**, [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-decision-attribution-review/REVIEW.md). 위험/귀속/범위 조합, .90 경계, snapshot·source ID 변조와 보호 경계. 차단 발견0 |
| 정적/계약 | Ruff/Bandit 새 후보 파일 exit0, static-diagnostics.json. 새 schema check_schema/로컬 refs VALID, schema.txt/command.json. 전수 보안 진단 PASS가 아님 |

최초 pytest는 예약 fixture 이름 `request` 사용으로 collection 오류였고 related-first*에 보존한 뒤 이름을 고쳤다. 최초 Ruff import 정렬/unused4건도 수정했다. 원장 메타데이터를 읽는 최초 inline 진단은 PowerShell quoting에서 실패했으며, literal here-string으로 바꾸어 mode=ro/query_only 확인을 완료했다. 제품/모델 실패나 공격 식별 성공으로 계산하지 않는다. 성공 뒤 문구/hash 기록만을 위해 전체 시험을 반복하지 않았다.

## 원 기록과 필수 가이드

실제 V4 실행 전 동결 manifest의 기존 source54개를 현재 SHA와 대조해 **54/54 일치·0 mismatch**다. [original-source-preservation.json](C:/sogaeding/artifacts/20261017-decision-attribution/original-source-preservation.json)에 기존 Engine/V3/V4/adapter/runner/wrapper/schema/후보 자료의 파일별 expected/actual을 남겼다. 원 result SHA `7d481deadeb24ed6f41e05dff032491e5f0f2b9bc7b8ba58ef4d2c1976751c10`, run manifest `9aa11ab1b12fd231c2a39d52308eb60a1ea12fdc71514647d6ab50494bbdc23c`, 기존 성공 normal.md `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0`도 유지했다.

읽기 전용/query_only 원장 집계의 [budget-observation.json](C:/sogaeding/artifacts/20261017-decision-attribution/budget-observation.json)은 역사17요청/예약1088000을 확인한다. 기존 실패 상태와 원 소비/usage/UNKNOWN은 유지했으며 새 유료 run/예산·추가CLI0, 기존 CLI3/3을 재개하지 않았다. 실제 키 본문/키hash는 읽지 않았다.

필수 R1/G1/G2/G3/G4와 P0는 기존 `docs/plans/03_guide_compliance.md` 및 원문/hash가 있는 `artifacts/20261017-auto-decision/guide-pages.json`의 필요한 페이지 연결을 재사용했다. R1 PDF14/G1 PDF35~36→범위·source 추적/검토; G3 PDF507~508 SR1-4/9→typed enum·서버 권한/입력 무결성·변조 반례; G2 PDF128/G3 PDF510/G4 PDF38→기존 정확 승인·예약/UNKNOWN·키/TLS 보호 유지; G2 PDF129/135/137/G4 PDF24→입력/timeout 제한·안전 실패·최초진단→조치→재검증. 설계20/약점49 정본의 적용성/미점검 상태를 변경하거나 전수 PASS로 표시하지 않는다.

## 남은 범위

새 질문의 실제 Jev 답/의미 정확도·정상 자동 ALLOW·실제 공격 DENY·파일 executor/actor 보호는 NOT_RUN이다. source 연관은 관측이며 인과 증명이 아니다. 현재 운영 V3·성공한 사람 승인/단회쓰기·원 UNKNOWN/TLS 경계는 유지하며, 일반 native/hook 장애·전체 IPI·전체 공급망/키수명·MVP 완료를 선언하지 않는다.

다음 단계는 관리의 내부 질문/정책 검토와 필요 최소 실제 검증 판단이다. 새 유료 run/명령/예산을 준비하거나 단순 질문 변경 후 반복 실행을 제안하지 않았다.
