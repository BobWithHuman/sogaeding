# T-JEV-03/04 별도 AI 검토

2026-10-16. 작성자와 분리된 AI 검토이며 사람 개발자는 사용자 1명이다. 공식 독립 보안 진단이 아니다. **배정된 승인 대기 수리·Jev 오프라인 준비 범위는 수용 가능, 미해결 차단 finding 0. 최종 RESULT/manifest·보존 대조 완료.** 실제 사용자 CLI 읽기 완료·TypeSafe 접근/정확도·전체 MVP 완료는 수용하지 않는다.

## 범위와 최초 실패

WAIT_AND_JEV_PREP_START_PROMPT 전체, 최신 AGENTS, 관리 host_wait 검토, with-human-dev와 검증 reference, 현재 SPEC5/Jev 계약 및 직전 HOST RESULT/REVIEW를 대조했다. 기준선은 193파일 fingerprint `bdc7df912c9d2c815b9c2928814004b4afc83310fe66e6686084a0f367daa999`다. 제품 소스는 읽기 전용으로 검토했고 자체 시험/증거와 이 REVIEW만 작성했다. 실제 actor/OpenAI/TypeSafe API 호출·키 생성·개인 설정 변경·제품 DB/원장 변경은 검토자 0이다.

사용자 최초 새 읽기는 RULE_ALLOW/READY였지만 약 90.074초 뒤 30초 freshness에서 거절됐고 upstream 시도는 0이었다. 과거 REJECT audit의 call은 비어 있어 개별 연결은 시간대·유일 호출·고정 코드·소스 분기·upstream 부재에 의존했다는 한계를 보존한다. 이 실패를 인증 실패나 공격 차단 PASS로 바꾸지 않는다. 과거 동의는 한 번의 CLI/read 시험에 한정됐으며 추가 유료 CLI를 자동 실행할 권한이 아니다.

## 코드와 집행 검토

새 public-read-1 표식·원 action/request hash가 있는 RULE_ALLOW/PUBLIC_ENROLLED_READ만 30초 이후 재검사 대상이다. 의미 판정/CONFIRM·기존 marker 없는 READY·UNKNOWN은 갱신하지 않는다. 전체 TTL과 원 analyzed_at/snapshot은 유지한다. 현행 연결/세션/turn·정책/grant·정확 도구/인자·전체 source hash와 원문/catalog 유효성·공개 parser/민감 경로·분석 중단·미해결 선행 호출을 다시 검사하고 같은 BEGIN IMMEDIATE에서 EXECUTING 예약을 한 번 수행한다. 원분석과 forward_check/REVALIDATE를 구분하며 ticket은 이 최종 검사 뒤 짧은 만료로 발급한다. 의미 승인 소비도 만료 시 timestamp를 갱신하지 않고 트랜잭션을 rollback해 미소비 상태를 보존한다. 이 예약은 upstream receipt나 멱등성 보증이 아니다.

bridge는 401/403 본문으로 원인을 단정하지 않는다. random request nonce와 connection/tool/args가 결합한 별도 인증 TLS Control 조회만 신뢰한다. Control은 짧은 보관/개수 제한의 고정 allowlist 사유와 call SHA 또는 미결합 null만 반환한다. 임의 gateway/upstream 문자열·추가 필드·잘못된 hash·조회 실패는 HTTP_REJECTION_UNCLASSIFIED이며 raw token/body를 출력하지 않는다. 실패 수집은 기존 READY를 성공으로 바꾸지 않고, 전달 뒤 불명 상태는 UNKNOWN으로 유지한다.

Jev 준비는 별도 ignored 소유자/SYSTEM ACL 저장소, 숨긴 stdin 키 입력, 역할별 key/config/plan/source RO와 별도 provider 원장/결과 RW, 기존 image ID 고정/no-pull·기본 enabled:false를 사용한다. prepare/preflight는 network none이고 provider 접근은 NOT_VERIFIED다. inspect의 정확 자료·고정 질문과 manifest SHA, 명시 confirm-send/4요청/256000 예약 승인이 모두 필요하다. 두 한국어 합성 후보의 A/B만 전송 대상이며 라벨·정답·키·실제 프로젝트/PDF는 wire에 없다. 기본 policy는 비활성 상태로 남고 별도 일회 authorized-run만 생긴다. 새 원장/결과/설정의 덮어쓰기·자동 재시도·GPT fallback·alias·예산 환불/초기화 경로는 없다. stale 소스에서도 collect는 전송 없이 동결 계획/상한을 검증한 후 관측 결과를 읽고 current_source_matches_frozen_run을 표시한다.

## 독립 시험과 발견·조치

[독립 시험](../../../../artifacts/20261016-wait-jev-review/test_independent.py)과 관련 회귀를 network-none/RO/비root/cap-drop Docker에서 실행했다. 최종 **223 PASS/3.94초**, 그중 자체 26개다. [정확한 명령](../../../../artifacts/20261016-wait-jev-review/regression-final-command.json)과 [출력](../../../../artifacts/20261016-wait-jev-review/regression-final.txt)을 보존한다. 작성자 회귀와 겹치므로 시험 수를 합산하지 않는다. 제품 DB·실제 키·원장 볼륨은 이 시험에 마운트하지 않았다.

- WAIT-R01/P2: 새 smoke가 기존 병렬 A/B를 사용해 첫 provider 실패에도 두 시도/128000 예약을 소비했다. smoke 전용 SequentialFailStop이 A 완료 뒤 B를 시작하고 A 실패 때 B claim을 막도록 수정됐다. fake 401/403/429/500/302는 각각 provider 1/64000 예약 보존, 다음 후보 미시도, NOT_SCORED/NOT_ESTABLISHED로 재진단 PASS다. 기존 제품 정책 A/B 구조는 보존한다.
- WAIT-R02/P2: 사용량 누락 때 숫자 0 비용으로 오해할 수 있었다. 기록된 부분합과 전체 비용을 분리했고, incomplete이면 total=null/INCOMPLETE_UNKNOWN_BILLABLE_USAGE다. 합성 실패 원장 독립 시험 PASS다. 공개 단가에 따른 제안 예약 산식은 실제 청구 보증이나 소비량이 아니다.
- 검토 시험의 최초 invalid connection 기대값은 실제 expiry 선검사 코드에 맞춰 수정했다. 비용 시험도 제품 수정과 겹쳐 구 필드명 KeyError였던 원출력을 보존하고 새 명시 total/status 필드로 수정했다. 제품 실패와 검토 시험 수정은 구분한다. [발견 기록](../../../../artifacts/20261016-wait-jev-review/findings-final.json).

작성자 [실제 pinned gateway r5](../../../../artifacts/20261016-wait-gateway/final-r5-probe.json)와 [효과/감사](../../../../artifacts/20261016-wait-gateway/final-r5-effects.json)를 별도로 재대조했다. 45/45 체크·probe SHA·실행 시 source SHA가 일치한다. 즉시/시계 91초 지연/동시 replay는 각각 upstream 1로 총 3이고 결과는 OBSERVED다. 인자·turn·grant·정책·출처·사용자 문맥·세션/연결 만료·분석 중단·보호/범위밖·의미 만료·UNKNOWN 후보는 upstream 0이다. random32 header가 실제 gateway를 통과한 Control 상관관계 13건, unmatched UNCONFIRMED와 잘못된 CA 거부도 확인했다. r2에 없던 실제 헤더 진단 연결은 r5로 보강했다. 시계 제어 fixture이며 실제 사람 승인 UI의 91초 대기 성공 시험은 아니다.

## 가이드·보존과 남은 범위

원 PDF 3개 SHA와 G2 PDF126/133/137/146, G3 PDF406/415/509/510/511, G4 PDF38의 10페이지를 기존 bundled pypdf로 다시 추출해 작성자 원문과 대조했다. [독립 원문 대조](../../../../artifacts/20261016-wait-jev-review/guide-original-check.json). 시간/상태 경쟁→같은 DB 예약·동시 실행1, 인증/세션→현행 연결/만료·정확 결합, 오류 최소공개→trusted fixed diagnostic·임의 문자열 배제, 키/전송→숨긴 입력·최소 ACL·RO/RW 분리, 자원/반복→상한·timeout·실패 보존·추가 호출 중단으로 코드/시험을 연결한다. R1/G1과 기존 설계20/약점49 전행 적용성은 직전 검토의 근거·미완료를 유지하며 [변경 적용성](../20261016-wait-jev-prep/GUIDE_APPLICABILITY.md)을 대조했다. 전수 PASS나 공식 조치율/점수는 선언하지 않는다.

작성자의 preservation-final은 GPT 5/Jev 6 기존 history, 보호 파일 hash, OpenAI 22/24 예산의 동일성과 기존 READY/UNKNOWN 미해제를 기록한다. 진단용 gateway_rejections 추가 migration은 있으므로 DB bytes 불변이라고 주장하지 않는다. code-only 35파일 배치 및 기존 설정 재시작 뒤 실제 Windows 무모델 preflight는 ready=true/issues=[]·paid0/tools_call0/turn0/candidate0, semantic_write_ready=false, TypeSafe 실제 key/ledger 없음이다. preflight 수용은 모델 인증/접근 성공이나 사용자 작업 성공이 아니다.

최종 [RESULT](../20261016-wait-jev-prep/RESULT.md)와 [증거 인덱스](../../../../artifacts/20261016-wait-jev-prep/final-index.json)를 읽고 최종 source 200파일을 현재 파일과 직접 SHA 대조했다. 불일치 0, fingerprint `5e023a303a2e48569efbc326c49172972cd4a0054b6103bc3c36a085820b395b`, 독립 시험 후 검토 runtime 7파일 변경 0이다. 기준선/최종의 histories·openai_budget·protected_sha256를 독립 비교해 모두 동일함을 확인했다. [최종 독립 대조](../../../../artifacts/20261016-wait-jev-review/final-comparison.json). 작성자 최종 346 PASS/42.56초·Ruff PASS와 별도 223 PASS를 합산하지 않는다. Bandit High0/Medium2/Low14 원 경고와 고정 container bind/tmpfs/subprocess 통제 설명을 대조했으며 정적 미탐이나 경고 수를 전수 보안 합격으로 해석하지 않는다.

실제 TypeSafe endpoint/model 응답 호환성·한국어 정상/공격 정확도·calibration/holdout·실제 CLI 의미 쓰기/실파일 효과는 NOT_RUN이다. 추가 사용자 CLI/read 시험과 TypeSafe 자료/최종 한도/명시 실행 동의는 관리가 구체 범위를 확정한 뒤 사용자 직접 실행으로 남긴다. 일반 native 개발·hook 사망/timeout/malformed fail-open·전체 TLS negative/키수명·공급망 잔여는 유지한다. 이 항목과 C/D 전체를 이번 좁은 완료의 새 선행조건으로 추가하지 않는다.
