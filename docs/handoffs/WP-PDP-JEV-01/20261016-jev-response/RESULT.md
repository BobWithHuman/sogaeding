# T-JEV-06 응답 계약 수리 결과

배정: RESPONSE_CONTRACT_REPAIR_START_PROMPT.md. 개발 통합: root, helper 제한 위임: jev_adapter, 공식 출처 조사: jev_contract_sources, 별도 AI 검토: jev_review. 사람 개발자는 사용자1명이다. 전역 DONE 판단은 관리 세션에 남긴다.

## 결론과 실제 실패

공식 Choice 예제를 거부했던 confidence 비교를 제한된 표시 정밀도 호환 방식으로 수정했다. 실패 필드를 원문 없이 구분하는 allowlist 진단, 답변 실패와 독립적인 유효 usage 기록, 평가의 semantic 실패 표시와 읽기 전용 과거 collect를 구현했다. 실제 provider/actor 호출0, 키 본문/해시 접근0, 새 예산·실제 후속 run 생성0이다. 현재 bundle/service/기존 DB를 배포·교체하지 않았다.

실제2026-10-16T10:45:33.648765Z 시험은 S01/A JEV_RESPONSE_INVALID, B TURN_ANALYSIS_STOPPED, S02 NOT_ATTEMPTED다. 원장 FAILED1/A/input_reserved64000/usage NULL이다. 원응답·상세 단계·HTTP 상태가 보존되지 않아 **실제 세부 원인은 UNKNOWN**이다. 공식 예제 충돌은 별도 재현 사실이며 실제 실패 원인 증명이 아니다. 키401로 단정하거나 교체하지 않았다. 과거 사용량/청구액은 UNKNOWN이고 복구되지 않았다. execution_exit0은 수집 프로그램 종료이며 의미 판정 성공이 아니다. 실제 CLI/파일 효과는 NOT_RUN/0이다.

## 변경과 유지한 계약

- src/app/transparent/jev.py: jev-response-2, 단계/실패종류 고정 진단, 독립 usage 검증·FAILED 기록, bounded nullable usage, 안전한 로컬 per-call metadata/새 진단 테이블. 기존 ledger에는 client를 실행하지 않았다.
- src/app/pdp/diagnostics.py: enriched 진단의 enum/bool/제한 수만 허용. 기존 non-enriched SPEC4 출력은 유지.
- tools/jev_eval.py, scripts/jev_eval.ps1: UTF-8 유지, legacy readonly collect와 semantic_summary, 부분 usage 보고, 명시 disabled followup-plan. 현재 소스/manifest 실행 검사를 유지한다.
- docs/mvp/contracts/jev_observation.schema.json: 내부 응답 계약2와 nullable usage subset 동기화. docs/mvp/09_rules_first_jev.md: 과거 안내 이후의 실제 실패/현재 수리·제한 명령 명시.
- 테스트: test_jev_response_contract.py/test_jev_followup.py 추가, 기존 test_jev_eval.py 회귀 유지. 기존 adapter float 테스트만 pytest.approx로 표현 오차를 비교하고 provider 이하 조건을 추가했다.

모델 jev-1.13.0/endpoint/질문/criteria/출처·ref 검증/정책 임계치 .90은 그대로다. 정확 필드·question/option coverage·finite/type/range·합계·argmax 검증을 유지한다. TLS verify/프록시 비상속/redirect0/HTTP retry0/시간·크기 제한을 유지한다. 정책 권한·원자 실행·예외 승인·UNKNOWN·native 통제는 변경하지 않았다.

## 공식 근거와 호환 경계

[공식 API](https://docs.typesafe.ai/api)의 .88/.12/0 및 confidence .81 예제와 [공식 confidence 수식](https://docs.typesafe.ai/confidence)의 .82는 다르다. 공식 소스에서 표시 정밀도/반올림 보증을 찾지 못했다. 제품은 두 자리 반올림 가정에 한정한 허용 오차 `.005*n/(n-1)+.005+1e-6`를 사용한다(n3=.012501). 공식 보증이나 정확도 보정으로 표현하지 않는다. 정책에 전달하는 값은 **min(provider confidence, 원확률로 계산한 반올림 전 confidence)**이다. 따라서 원계산 .8999999999997을 .90으로 올리지 않는다. 확률·입력 응답은 변경하지 않는다. transient 비교값은 JSON 응답/로그에 추가하지 않는다.

[공식 SDK 응답 타입](https://docs.typesafe.ai/sdk/python/api/types/responses)과 v0.7.5 고정 commit [models.py](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/f36e68549ceca3191e5791e5f99ea1baa1a258b5/src/typesafe_sdk/_schemas/models.py), [response_types.py](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/f36e68549ceca3191e5791e5f99ea1baa1a258b5/src/typesafe_sdk/_core/response_types.py)를 대조했다. nullable usage는 미보고로 처리한다. SDK의 extra-ignore·수치 범위 검증 부재를 제품에 도입하지 않는다. SDK 소스만 읽었으며 설치/실행·새 이미지/의존성은 없다. MIT/고정 commit/공식 URL은 artifacts/20261016-jev-response-sources/EVIDENCE.md와 evidence.json에 기록했다. SDK 로컬 서명 검증은 NOT_RUN이다.

## 진단·사용량·부작용

HTTP 상태/JSON·비JSON·누락 content type/제한 길이/JSON 유효성/모델 일치/필드·coverage 수/고정 수치 실패 종류와 stage를 기록한다. raw body/전체 header/동적 unknown 필드명·문자열/임의 exception/response hash/credential은 출력·저장하지 않는다. 모르는 metadata는 UNKNOWN이다. model mismatch·구조·숫자 오류는 fail closed다.

답변 실패여도 독립적으로 유효한 input/output 계수는 FAILED 행에 보존한다. 한 계수만 유효하면 다른 계수는 null이며 total bill은 UNKNOWN이다. 누락·비정상 계수를0원으로 보지 않는다. HTTP 비200/파싱 불가능한 본문에서 usage를 추측하지 않는다. 알려진 합계0과 총사용량 UNKNOWN을 함께 표시한다. 예약64000은 반환하지 않는다. 첫 실패 뒤 B/다음 후보/재시도0은 유지한다. 분석 오류는 공격 식별 PASS가 아니다.

## 실제 검증과 증거

모든 Docker 시험은 기존 with-human-dev:local 이미지에서 network none으로 실행했다. source manifest/실제 argv/UTC/exit/output은 각 *-command.json에 있다. 무모델 fixture와 임시 DB만 사용했다.

| 확인 | 결과 | 증거 (C:\sogaeding 기준) |
|---|---|---|
| hookgw/F3/harness 관련 회귀 | 393 PASS/34.55초 | artifacts/20261016-jev-response/related-regression-command.json, related-regression.txt |
| 별도 AI 자체·관련 회귀 | 44 PASS 및236 PASS, 중복 합산하지 않음 | artifacts/20261016-jev-response-review/regression-final.txt 및 REVIEW |
| 공식 예제/호환 경계/불량 응답·안전 진단·partial usage·FAILED 보존 | PASS, 위 회귀에 포함 | tests/hookgw/test_jev_response_contract.py |
| 첫 실패 후 중단·과거 collect·별도 disabled 계획/경쟁/경로·key 접근금지 | PASS, 위 회귀에 포함 | test_jev_eval.py, test_jev_followup.py |
| 기존 네 wire body/질문/모델/정책/threshold/한도 | 동일 PASS | artifacts/20261016-jev-response/wire-equality.txt 및 compat_wire.py |
| Windows PowerShell5.1 실제 legacy collect | exit0/ANALYSIS_FAILED_PARTIAL, S01 NOT_SCORED/S02 NOT_ATTEMPTED, 원장/결과 변경0 | artifacts/20261016-jev-response/legacy-collect-command.json, legacy-collect.txt |
| Windows PS5.1 UTF-8/한글 JSON·실패출력 fixture | 21/21 PASS, fake followup exit0 | artifacts/20261016-jev-response-helper/evidence.json, HANDOFF.md, ps-native-default/utf8.json |
| Ruff | PASS | artifacts/20261016-jev-response/static-r2.txt |
| Bandit 원진단/수리 후 재진단 | baseline12 LOW/1 MEDIUM →14 LOW/1 MEDIUM, high0, exit1 보존 | artifacts/20261016-jev-response/bandit-baseline.txt, bandit.txt |
| 기존 파일·원장/키 metadata | 동일 PASS | preservation-before.json, preservation-after.json, key-metadata-before.json, key-metadata-after.json, final-index.json |

Bandit은 clean PASS가 아니다. B404/B603은 argv-list subprocess 사용으로 shell 실행이 없으며 후속 계획 builder도 기존 검증된 Docker/image와 network none만 사용한다. 새2 LOW는 그 builder 호출 B603 및 disabled input_token_limit=None B105다. B105의 None/256000은 비밀번호가 아닌 정책 값이다. MEDIUM B108은 호스트 공유 임시파일이 아닌 컨테이너 전용 tmpfs /tmp 설정이다. 경고를 suppress하지 않았으며 이 검토로49약점 전수 진단 완료를 주장하지 않는다. 기존 경고와 새 경고를 분리했다.

최초 unit121개 중1개 float exact 비교 실패는 증거에 보존했고 위에서 수정했다. 별도 AI RESPONSE-R01/P2: round12가 .90 미만 값을 승격시키는 경계를 지적해 반올림을 제거하고 원값 min/회귀로 수정했다. 최종 차단 지적0은 별도 REVIEW를 따른다.

## 보존·소스·가이드

기준선201파일 fingerprint dbdae09f5b787c5eafad4b58da43f54b0e0872f204c3d968645a6c65bf5cd1b0 → 최종203파일 fingerprint4f0d4949f158928130f81b3424f493ec959ce635b5366975523bf625e1466214. artifacts/20261016-jev-response/baseline-source/manifest.json 및 final-r2-source/manifest.json에 실제 파일별 hash가 있다. 키는 snapshot 대상 밖이며 본문/해시를 읽지 않았다. 기존 plan manifest b542e3ee0cd8b8674f4679b735e8719d8dbe1f6737da75f20ac3d53a0116680f 및6개 공개 파일·원장 hash가 전후 동일하다. 키 length/ctime/mtime/ACL만 비교해 동일했다. 관리 plans/harness/AGENTS·기존 OpenAI22/24예산은 변경하지 않았다.

필수 원문은 SHA를 재확인하고 원 PDF에서 다시 추출한 artifacts/20261016-jev-response/guide-pages.json과 연결했다. G2 PDF133/135(인쇄127/129) 오류 정보 최소화 → diagnostics allowlist/비노출 시험; PDF137(인쇄131) 예외 후 의도하지 않은 정상 흐름 금지 → fail closed/첫 실패 중단/FAILED 유지. G3 PDF511 SR3-1 → 타입·범위/구조 실패·UNKNOWN 처리/상세 오류 비노출. G4 PDF38(인쇄36) 중요자원·중요정보/예외처리 → key 접근0·RO 원장/예약 보존·안전 진단. R1/G1은 기존 고정 이미지·공급망 증거와 official SDK source-only/MIT/commit 기록에 연결한다. 새 패키지·이미지는 도입하지 않았다. 기존 설계20/약점49 적용성 장부를 유지하며 이번 좁은 변경으로 전수 PASS를 선언하지 않는다. 최초 오류→수리→재진단 이력을 남겼다.

## 사용자가 지금 확인할 명령과 다음 제한 제안

```powershell
cd C:\sogaeding
.\scripts\jev_eval.ps1 -Mode collect
```

semantic_summary.outcome=ANALYSIS_FAILED_PARTIAL, scored_candidates=0, S02=NOT_ATTEMPTED, current_source_matches_frozen_run=false, usage_complete=false/총청구null을 확인한다. 이는 실패 보존 수집이며 재호출하지 않는다. 과거 prepare/key/inspect/preflight/evaluate를 다시 실행하거나 manifest 검사를 끄지 않는다.

선택적으로 향후 검토용 계획만 분리하는 명령: ` .\scripts\jev_eval.ps1 -Mode followup-plan -NewRunId 'followup-reviewed-unique-id' -ConfirmNewPlan `. 이번 개발에서는 실제 실행하지 않았다. 생성물은 disabled/NOT_EXECUTABLE/evaluation_supported=false다. 키 경로만 참조하고 내용 복사·새 key/ledger/authorized-run/예산0이다. 과거1회/64000 소비 후 잔여3회/192000이며 완전4회 재시험은 과거 포함5회/320000으로 추가1회/64000이 필요하다. 남은3회에4회가 들어가지 않는다. snapshot은 예약이 아니며 concurrent 변경 시 달라질 수 있다. 이 helper는 followup 평가 실행을 지원하지 않는다. 새 실제 전송은 별도 구체 절차·총량 검토 후 사용자 직접 선택으로 남긴다.

## 남은 범위와 별도 검토

실제 Jev 응답 수리의 서버 호환성·새 상세 진단/usage 실제 응답은 NOT_RUN이다. 실제 의미 정확도·holdout·Codex CLI/파일쓰기·native 지원·hook 장애·전체 공급망은 미완료/기존 한계 유지다. 기존 helper 보호 prefix는 tools/hookgw·scripts/hookgw 중심이므로 tools/jev_eval.py/scripts/jev_eval.ps1 자체를 독립적인 hard-deny로 보호한다고 주장하지 않는다. trusted helper 안의 manifest 검사는 helper 자체 변조 방어가 아니다. 정책 권한 변경은 배정 밖이라 보존했고 별도 관리 판단이 필요하다.

별도 검토: [REVIEW](../20261016-jev-response-review/REVIEW.md). 공식 출처 조사와 helper 자체 검증은 독립 검토를 대체하지 않는다. 실제 실패를 공격 탐지 PASS나 전체 제품 완료로 보고하지 않는다.
