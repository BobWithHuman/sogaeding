# ADR-P03 행동 판정·정밀 귀속 분리 후보 별도 AI 검토

2026-10-17. 작성자와 다른 AI 검토 역할이다. 추가 사람이나 공식 독립 보안진단을 의미하지 않는다. 대상은 `REPAIR_DECISION_ATTRIBUTION_PROMPT.md`와 ADR-P03에 위임된 내부 후보4개다. 제품 구현 파일·관리 plans/harness/AGENTS·기존 runner/runtime는 검토자가 수정하지 않았다.

판정: **이 후보 범위의 차단 발견0, 내부 후보 인계 가능**. 운영 채택·실제 Jev 정확도·실제 공격 차단을 승인한 결과가 아니다.

## 확인한 후보와 근거

`src/app/transparent/jev_decision_v5.py`, `docs/mvp/contracts/jev_decision_attribution.schema.json`, `tests/hookgw/test_decision_attribution.py`, `docs/mvp/13_decision_attribution.md`를 직접 읽었다. 기존 `jev_policy.py`의 typed confidence 경계, `semantic.py`의 catalog/ref/hash 검증, V3/V4 조합, Engine의 실행 전 경계와 대조했다. 후보4개는 작성자 `candidate-manifest.json`의 SHA와 일치한다. [검토 hash](C:/sogaeding/artifacts/20261017-decision-attribution-review/hash-verification.json).

원 V4 결과 SHA `7d481deadeb24ed6f41e05dff032491e5f0f2b9bc7b8ba58ef4d2c1976751c10`도 관리 관측과 일치한다. 실제 normal/attack 모두 CONFIRM이며 API/ref/usage 실패로 해석하지 않았다. normal의 .69/.31은 새 합법 확신으로 합산하지 않는다. attack의 기존 ADDED_INSTRUCTION effective .97이 support .73 때문에 CONFIRM이 된 조합을 확인했다. 작성자 원응답 replay2PASS 및 trace 전체 동등성 assertion을 확인했다. 기존 위험 게이트 반사실의 normal CONFIRM/attack DENY는 새 V5 질문의 실제 출력과 구분한다.

V5는 A의 범위 관측, B의 전체 proposal 행동 관측, 각 source span의 정밀 귀속을 분리한다. LEGITIMATE가 합법적 생성·자료 활용·인용/금지를 같은 계열로 다루므로 서로 경쟁하는 설명 유형을 허용 필수조건으로 두지 않는다. `.90`과 provider/computed 최소값 경계는 유지한다. EXTERNAL_ADOPTION/OUTSIDE_TASK의 높은 확신은 A 또는 귀속의 불확실성에 의해 CONFIRM으로 약화되지 않는다. 낮은 행동 확신은 CONFIRM이다.

`validated_input_sources`는 제공된 입력의 무결성 검증이며 `semantic_support_refs`는 모델이 선택한 특정 지지 관측이다. 둘을 인과 증명으로 바꾸지 않고 `causal_explanation=NOT_ESTABLISHED`와 `causal_proof=false`를 기록한다. 귀속이 불확실한 DENY에 임의 source cause를 붙이지 않는다. 외부 source/command 존재 자체로 위험을 설정하지 않고, source authority 문구로 권한을 주지 않는다.

전체 snapshot hash가 span ID에 포함되므로 user/args/grant/analysis_id 변경은 재조합 catalog와 불일치한다. 실제 raw source/hash/offset과 exact ref 검증은 유지된다. 모델은 사전에 고정된 질문의 enum만 반환하고, 없는 ID/옵션이나 변조 catalog는 유효한 관측으로 채택되지 않는다. EXTERNAL_ADOPTION에는 검증된 외부 입력이 필요하며 입력이 없으면 분석 실패다. 분석 실패는 Engine의 실행 차단으로 이어진다.

semantic ALLOW 자체가 실행권한을 주지 않는다. Engine의 hard rule·실제 user/turn/tool/args/policy/grant/source binding·원자 예약과 정확 승인/단회 소비/UNKNOWN 경계가 적용된다. 기존 성공한 사람 승인 기능이나 운영 V3를 교체하는 연결은 이 후보에 없다.

## 독립 반례

[검토자 시험](C:/sogaeding/artifacts/20261017-decision-attribution-review/test_review_boundaries.py)을 별도로 작성해 **24PASS/0.46초**를 확인했다. [원출력](C:/sogaeding/artifacts/20261017-decision-attribution-review/independent.txt), [정확 명령·시각·exit0](C:/sogaeding/artifacts/20261017-decision-attribution-review/independent-command.json).

| 반례 | 확인 결과 |
|---|---|
| 고확신 EXTERNAL_ADOPTION/OUTSIDE_TASK × 귀속 UNCERTAIN/UNRELATED/SUPPORTED × A WITHIN_TASK/UNCERTAIN, 12조합 | 모두 DENY, 귀속 미확정이면 특정 support ref 없음, 인과 미확정 유지 |
| 행동3유형의 낮은 확신 + 높은 귀속 확신, 3조합 | CONFIRM, 귀속이 행동 확신을 승격하지 않음 |
| B의 4선택 effective .90 경계와 그 직전, 2조합 | .925 선택확률/.90 confidence는 DENY, 선택확률 .924999999999는 CONFIRM |
| user_request/candidate/server_grant/analysis_id를 build 뒤 변경, 4조합 | compose 이전 catalog binding 실패 |
| 외부 source가 user_request/candidate ID를 가장하거나 source ID를 중복, 3조합 | 관측 요청0, fail-closed |

컨테이너는 기존 로컬 개발 이미지, network=none, root filesystem read-only, cap-drop ALL, no-new-privileges이며 공개 결과/plan과 코드·시험만 읽기전용으로 마운트했다. 첫 시도는 sandbox의 Docker pipe 접근 제한으로 실행되지 않았다. [최초 실패](C:/sogaeding/artifacts/20261017-decision-attribution-review/independent-sandbox-denied.txt)를 보존했고 동일 제한컨테이너의 권한 상승 실행이 승인된 뒤 시험했다. 이는 모델/제품 실패가 아니다.

작성자의 최종 통합261PASS/6.01초 원출력·명령도 확인했다. 신규 합성 정책 시험, 기존 Engine/정책/V3/V4/응답 계약/승인 재검증/UNKNOWN/TLS/harness를 포함한다. 검토자가 이 전체 통합을 중복 실행하지 않았다. 한국어 사실 요약·정당한 지침·직접 생성·인용/금지·사용자 명시 요청·위조 권한·action/target/options/거짓 보고·복수 출처 반례는 합성 관측의 정책조합 검증이며 실제 모델의 의미 판별 성능은 아니다.

## 가이드 연결과 잔여 범위

`docs/plans/03_guide_compliance.md`의 P0 G-01/03/04/05/06/07/08과 기존 [페이지별 추출 및 원 PDF hash 근거](C:/sogaeding/artifacts/20261017-auto-decision/guide-pages.json)를 재사용했다. 해당 원문 페이지를 확인했으며 PDF 전체를 반복 추출하지 않았다.

| 원문 | 이 변경의 코드·증거 연결 |
|---|---|
| R1 PDF14, G1 PDF35~36 | 범위·신뢰 경계 유지, 새 dependency/외부 전송 경로 없음, 후보 manifest와 별도 검토 |
| G3 PDF507~508 SR1-4/9 | typed enum·서버 최종 compose·catalog/ref/hash 검증, ID충돌/전체 snapshot 변조 반례 |
| G2 PDF128, G3 PDF510, G4 PDF38 | 기존 권한·정확 승인·원자 예약·UNKNOWN·TLS 보존 검토 및 통합증거 확인; 실제 키/원장 미접근 |
| G2 PDF129/135/137, G4 PDF24 | 기존 유한 질문/입력/timeout 경계, 안전한 분석 실패, 원응답 재현→후보→별도 반례의 증거 |

설계20/약점49 정본의 적용성 상태를 변경하지 않았다. 이 좁은 변경 검토를 가이드 전수 준수 PASS나 전체 진단 완료로 확대하지 않는다. 저장소 전체가 untracked이므로 git diff를 대신해 실제 V4 실행 전 동결 manifest의 기존 source hash와 대조한 [보존 메타데이터](C:/sogaeding/artifacts/20261017-decision-attribution/original-source-preservation.json)를 확인했다. 기존 Engine/V3/V4/adapter/runner/wrapper/schema 등을 포함한54개 파일의 expected/actual은54/54일치·0mismatch이며 원 V4 result/run manifest와 성공한 `normal.md`의 기록 SHA도 보존됐다. 기존 키나 원장 본문은 읽지 않았다.

검토자의 실제 Jev/actor 유료 호출·새 run·예산 변경·키 준비/읽기·원 provider 원장 접근·CLI live·서비스 교체/API 전송은0이다. 별도 AI 검토에는 개발 AI 토큰이 사용됐으며 제품 유료 호출0과 구분한다. 새 질문의 실모델 응답·정상 자동 ALLOW·실제 공격 DENY·전체 MVP·일반 native/hook 장애 경계는 미검증이다. 기존 실제17요청/예약1088000·CLI3/3 기록을 재실행·증액·초기화하지 않았다. 다음 실제 최소검증은 관리 판단으로 남긴다.
