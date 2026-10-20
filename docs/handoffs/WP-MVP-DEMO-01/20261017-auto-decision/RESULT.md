# WP-MVP-DEMO-01 자동 판정 집중 보완

2026-10-17. 구현1 + 별도 보조 AI검토1. 제품 actor/Jev/API 유료 호출0, CLI start0, runtime 교체0, 원장/예산/키 변경0. 개발 AI는 이 구현 채팅과 별도 검토에서 토큰을 사용했으며 제품 유료 호출 수와 별개다(정확 토큰 계량값 미제공).

## 확정 원인과 수정

1. **수치 결함 재현/수리:** 실제 choice/probabilities/provider를 그대로 재사용한 V3 정책 재현에서 basis_target USER .92/5choices·provider .90은 기존 .8999999999999999로 거부됐다. 공유 정확 십진 유리수 계산으로 .90 ACCEPTED다. 임계치/유효성/usage/ref 계약은 유지한다. 기존 실응답의 나머지 낮은 확신을 승격하지 않아 최종 decision은 수정 전후 **CONFIRM**이다. 원 snapshot이 없는 합성 catalog 정책 재현임을 보존한다.
2. **별도 검토 발견/수정:** 9choices p=.9111111111111111의 정확 .8999999999999999875가 최종 float 변환에서 .90으로 올라가는 P2를 검토자가 발견했다. 변환값이 정확값을 과장할 때만 인접 아래 float로 표현한다. 2~16선택지의 경계/직전/직후 입력과 낮은 provider가 그대로 보류되는지 검증했다. 최초/조치/재진단은 [검토 증거](C:/sogaeding/artifacts/20261017-auto-decision-review/)에 보존한다.
3. **입력 확인:** upstream의 text envelope→Engine canonical source→V3 exact span 경로를 확인했다. 공개 release 원문과 runtime 공개 자료가 같고, 성공 report로 재구성한 action/target/payload hash 모두 실제 trace와 일치한다. A=e0 USER/e1 CANDIDATE, B=e2 SOURCE_DATA 추가의 questions/criteria 집합도 대응한다. 원 user turn/source ID/암호화 snapshot 전체 복원·실제 원 wire의 byte 동일·저확신 인과 원인 입증은 아니다.
4. **V4 후보:** 사용자 지정/위임의 허용 의미를 INDEPENDENT로 묶고, 실제 action/target/options/payload를 분리한다. 필요한 slot basis와 개별 source support만 판단하고 semantic scope/source membership/중복 context 판정을 구별한다. 여러 출처의 지지와 확정 외부 추가 지시 DENY 우선, 실제 모호함 CONFIRM을 구현했다. text-only envelope의 본문은 공용 보조 문맥으로만 제공하고 원문/hash/원 catalog/ref/offset을 유지한다. 분할 span에 다른 span의 본문을 귀속하지 않도록 문구를 보완했다.

V4는 `JevPolicyV4` Python router 후보이며 현재 server profile/동결 runtime에 활성화하지 않았다. V3/승인 UI/단회 재개·예약·UNKNOWN/TLS/예산 기능은 재구현하지 않았다. 상세 계약은 [12_auto_decision_candidate.md](C:/sogaeding/docs/mvp/12_auto_decision_candidate.md).

## 검증과 보존

| 검증 | 결과/증거 |
|---|---|
| 기존 실응답 수정 전후 재현·입력 대조 | [diagnosis.json](C:/sogaeding/artifacts/20261017-auto-decision/diagnosis.json), before/after CONFIRM, 원 선택·확률·provider 보존, basis_target만 경계 통과 |
| 관련 회귀 | **102 PASS** [related-command.json](C:/sogaeding/artifacts/20261017-auto-decision/related-command.json)/related.txt. 한국어 사실·합법 권유·인용/금지·다중 출처·추가 action/target/options/거짓 보고·위조 hash·승인/단회/UNKNOWN·question cap |
| 최종 통합 | **688 PASS/84.44초**, [integrated-command.json](C:/sogaeding/artifacts/20261017-auto-decision/integrated-command.json)/integrated.txt. hookgw/F3/harness/backend/transport/web/acceptance. 수정 전 후보 672 PASS/85.45초는 integrated-before-review-fix*로 별도 보존 |
| 정적 진단 | Ruff/Bandit exit0. static-command.json/bandit-command.json과 원출력. 전체 약점 진단 PASS를 뜻하지 않음 |
| 별도 AI 검토 | [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-auto-decision-review/REVIEW.md). 작성자와 분리된 보조 AI 검토이며 공식 독립 진단/추가 사람 개발자 아님 |
| 소스 동결 | [candidate-manifest.json](C:/sogaeding/artifacts/20261017-auto-decision/candidate-manifest.json) 제품4/시험2/계약설명1개. 과거 원본3개 및 수정 전 후보 hash 보존 |

초기 관련 실행은 Docker compose의 관측 JSON 미마운트로 55 PASS/3 FAIL이었다. 올바른 읽기 전용 공개 JSON 마운트로 재실행했다. 별도 진단 import 경로 실패와 pypdf 부재는 *first-failure* 원출력을 보존하고 경로 수정/기존 추출문 사용으로 조치했다. 신규 cap 시험의 exception 공용 메시지 오인 assert도 related-cap-assertion-failure*에 보존하고 안전한 failure_details enum 확인으로 고쳤다. 이를 제품 실패/모델 공격 성공으로 계산하지 않는다.

현재 `reports/normal.md` SHA256은 기존 `74461a1177158a32674463b1bd2446dfbe7863f135aac332522f7b0f887943d0`과 같다. 관리 observation/typed trace 원본 SHA는 diagnosis.json에 기록했다. 원 성공·실패·CONFIRM·승인 소비·UNKNOWN 기록을 수정하거나 지우지 않았다. 관리 plans/harness/AGENTS는 수정하지 않았다.

## 필수 가이드/P0 연결

docs/plans/03_guide_compliance.md의 설계20/약점49 정본/기존 적용성 상태는 유지한다. 이번 변경에 대한 좁은 재검토이며 미점검 항목을 PASS/비적용으로 올리지 않는다. 신규 외부 interface/의존성/인증/DB 전이는 없다. Fraction은 표준 라이브러리다. 원 PDF SHA를 검증하고 필요한 기존 페이지 추출문만 [guide-pages.json](C:/sogaeding/artifacts/20261017-auto-decision/guide-pages.json)에 보존했다.

| 적용 원문/요구 | 변경 코드·검증 연결 |
|---|---|
| R1 PDF14, G1 PDF35~36: 위험관리·개발/통합 보안 검증 | 유료 호출/새 dependency0, source manifest, 변경 전 재현→검토 발견→수리→재진단 이력 |
| G3 PDF507~508 SR1-4/9, W-15/19 | validated shape/argmax/usage·정확 catalog/hash/ref, strict envelope parse, server compose, 위조·모호·추가행동·경계 반례 |
| G2 PDF128(상태/경쟁), G3 PDF510, G4 PDF38의 접근/보호 | 승인·원자적 예약 코드 유지, 기존 승인/단회/UNKNOWN/TLS 통합 회귀, 키/원장/민감 원문 미접근 |
| G2 PDF129/135/137, G4 PDF24: 제한·안전 오류·수정/재검증 | 최대24질문/24576byte·catalog/context 제한 유지, cap 거부가 key 읽기/예산 선점/전송 전에 일어남, safe diagnostic enum, 코드검토/시험 이력 |

## 남은 범위와 다음 제안

현재 배포의 정상 자동 ALLOW·실제 공격 DENY·V4 실제 모델 의미 정확도/보정은 **미검증**이다. 독립 span 지원의 질문수·byte 상한을 유지하므로 모든 최대 catalog 조합을 지원하지 않는다. 원문과 source 일치는 관측이며 모델의 인과 추론이나 권한 증명이 아니다. 일반 native/hook 사망·전체 IPI·TLS 전체 negative/키수명·공급망 전체/C/D 완료를 선언하지 않는다.

다음 후보는 **정상1+공격1의 A/B 총4요청, CLI 추가0회**라는 [명시적 평가 제안](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-auto-decision/FUTURE_EVAL_PROPOSAL.md)으로만 준비했다. 정확 원문/목적지/네 wire·hash·누적 한도를 함께 남겼다. 현재 승인 소진 상태에서 실제 호출/증액/예산 초기화는 없다. 다음 준비 작업은 관리 검토와 V4 채택/한정 평가 여부 결정이며 전역 DONE은 관리 담당 소관이다.
