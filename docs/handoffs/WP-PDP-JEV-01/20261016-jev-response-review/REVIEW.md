# T-JEV-06 응답 계약 수리 별도 AI 검토

2026-10-16. with-human-dev와 최신 배정을 적용한 작성자와 분리된 AI 검토다. 사람 개발자는 사용자 1명이며 공식 독립 보안 진단이 아니다. **무모델 응답 호환·안전 진단·사용량/과거 run 보존·비활성 후속 제안 범위는 수용 가능, 최종 대조 완료, 현재 미해결 차단 finding 0.** 실제 Jev 접근/정확도·사용자 재평가·Codex IPI 집행 완료는 수용하지 않는다.

RESPONSE_CONTRACT_REPAIR_START_PROMPT 전체, 최신 AGENTS·관리 실제 실패 검토, 현재 계약/소스와 with-human-dev 검증 기준을 읽었다. 제품 소스는 읽기 전용이다. 실제 키 파일의 본문/hash를 읽지 않았고 provider/actor 재호출·실제 원장/결과/동결 계획·authorized-run 변경·개인 설정/CA 변경은 0이다. 별도 증거와 이 REVIEW만 작성했다.

## 실제 실패와 공식 근거

사용자 최초 실행은 S01/A JEV_RESPONSE_INVALID, B 중단/S02 미시도, FAILED 1회·64000 예약·usage NULL이다. 원응답·세부 stage/HTTP status가 남지 않아 정확한 실패 필드를 확정하거나 누락 usage를 복원할 수 없다. 코드상 JEV_RESPONSE_INVALID의 HTTP200 이후 분기와 실제 저장된 상태 증거는 구분한다. 키401·의미 오답·공격 차단 PASS로 해석하지 않는다. execution_exit0은 수집 프로그램 종료이며 의미 성공이 아니다.

[공식 API](https://docs.typesafe.ai/api)의 Choice 예제 0.88/0.12/0·confidence0.81과 [공식 수식](https://docs.typesafe.ai/confidence)의 계산0.82를 직접 대조했다. 보존된 201파일 소스만 마운트한 순수 함수 시험에서 기존 검증의 예제 거절을 재현했다. 이는 실제 사용자의 폐기된 원응답이 이 예제와 같았다는 증거가 아니다.

공식 문서가 연결한 Python SDK0.7.5/MIT의 commit `f36e68549ceca3191e5791e5f99ea1baa1a258b5`에서 [generated wire](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/f36e68549ceca3191e5791e5f99ea1baa1a258b5/src/typesafe_sdk/_schemas/models.py)와 [공개 응답 타입](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/f36e68549ceca3191e5791e5f99ea1baa1a258b5/src/typesafe_sdk/_core/response_types.py)을 읽었다. confidence는 별도 숫자 필드이고 Usage는 미보고 null 카운터를 허용한다. 이 소스는 exact 수식 equality나 특정 2자리 정밀도를 보증하지 않는다. SDK의 느슨한 forward compatibility를 제품 권한/검증 완화로 가져오지 않았다. 설치·SDK 실행은 0이며 [조회 근거](../../../../artifacts/20261016-jev-response-review/official-references.json)를 보존했다.

## 구현 검토

새 응답 계약은 모델 pin·정확 envelope/question/option coverage·타입/finite/0..1·합계·최대선택·기존 source/ref 검증을 유지한다. confidence 표시 차이는 2자리 반올림을 가정한 제한 경계로만 수용한다. 이는 제공자 보증이나 성능 보정이 아닌 제품의 명시한 호환 가정이다. 정책에는 **반올림 전 계산값과 provider 값의 min**을 주고 임계치0.90은 유지한다. 두 관측값은 transient 속성으로만 구분하며 원 확률/응답 숫자·동적 이름을 진단에 보관하지 않는다.

진단은 고정 stage/issue enum, HTTP status, content-type 분류, bounded bytes/count/index, bool/UNKNOWN, usage 상태와 고정 계약/basis만 남긴다. JSON/타입·비유한/범위/합계/최대선택·confidence 실패를 구분한다. arbitrary body/header/key/option 이름·exception 문장·request/response hash는 저장/출력하지 않는다. 과거 실패에는 없던 새 상세를 소급 생성하지 않는다.

사용량은 답변 검증 전에 독립 타입/범위 검증한다. 답이 실패해도 유효 카운터는 별도 보존하고, 일부만 유효하면 부분 관측과 미확정을 구분한다. 정확 usage key 구조와 null 미보고를 허용하되 잘못된 필드/타입/범위는 판정 실패다. FAILED/CANCELLED 요청·64000 예약은 환불하지 않는다. 새 진단 table은 향후 claim/record에만 생기며 과거 collect는 읽기 전용이다. 첫 실패 뒤 B/다음 후보는 호출하지 않고 semantic_summary에서 NOT_SCORED/NOT_ATTEMPTED·프로그램 exit와 의미 실패를 분리한다.

기존 run을 현재 소스로 평가하도록 manifest 검사를 끄지 않는다. 후속은 명시 새 run ID/confirm 뒤 새 소스 manifest와 disabled proposal만 생성한다. 기존 키를 복사/읽거나 새 원장/allowance/authorized-run을 만들지 않는다. 과거1/64000·잔여3/192000, 전체 재시험4/256000, 소비 포함 총5/320000·추가1/64000을 표시하며 잔여는 재시도 권한이 아니다. **후속 proposal은 현재 실행 가능한 evaluate 경로가 아니다.** 별도 사용자 판단·구체 후속 작업을 요구한다.

## 독립 시험과 조치

[독립 시험](../../../../artifacts/20261016-jev-response-review/test_independent.py) 44개를 포함한 관련 회귀 **236 PASS/11.72초**다. [명령](../../../../artifacts/20261016-jev-response-review/regression-final-command.json), [출력](../../../../artifacts/20261016-jev-response-review/regression-final.txt). network none/RO source/비root/cap-drop Docker와 가짜 HTTP·생성된 가짜 key/임시 원장만 사용했고 실제 runtime 키·원장·결과 디렉터리는 마운트하지 않았다. 작성자 회귀와 겹치므로 합산하지 않는다.

공식 예제, model/coverage·선택/확률/합/비유한/bool·큰 confidence 불일치 거부, provider confidence로0.90 승격 금지, 유효 usage+잘못된 답/부분·누락 usage, 안전 진단 비노출, 원래 실패의 읽기 전용 collect, 후속 plan 명시/경로/덮어쓰기 거부·정확 누적 예산, 첫 실패 provider1·B/S020을 확인했다.

RESPONSE-R01/P2: 초안이 계산 confidence를12자리 round한 뒤 정책 min에 사용해 0.8999999999997을0.90으로 승격했다. raw 계산값 사용으로 수정했고 경계 재진단 PASS다. [발견·재진단](../../../../artifacts/20261016-jev-response-review/findings.json). 최초 관련 시험의2개 FileNotFound는 검토 command의 scripts RO mount 누락이었으며 제품 수정 없이 고친 후 전부 통과했다. 초기 baseline-official 이름의 시험은 동시 편집 뒤 초안을 사용했음을 명시하고 실제 frozen201 baseline 재현과 구분했다.

실제 과거 run은 SQLite URI mode=ro+query_only로 안전 필드만 독립 조회했다. A/FAILED/64000/usageNULL 1행·S01 NOT_SCORED·기존 manifest/plan/disabled policy·authorized-run/결과를 확인했고 명시한 NONSECRET6파일은 읽기 전후 hash가 같다. 키는 접근하지 않았다. [과거 원증거 대조](../../../../artifacts/20261016-jev-response-review/legacy-readonly-check.json). 사용량·청구액 UNKNOWN과 원 실패 stage 미확정을 유지한다.

[최종 RESULT](../20261016-jev-response/RESULT.md)와 final-index·보존 증거를 대조했다. final-r2-source 최종203파일 fingerprint `4f0d4949f158928130f81b3424f493ec959ce635b5366975523bf625e1466214`와 frozen/current 파일별 SHA가 모두 같고, 독립236건을 실행한 runtime4파일도 동일하다. 실제 NONSECRET6파일은 독립 조회 시점 이후에도 같으며 작성자의 키 metadata/ACL 전후 비교도 같았다. 키 본문/hash는 접근하지 않았다. RESULT/REVIEW의 로컬 링크 누락0이다. [최종 독립 대조](../../../../artifacts/20261016-jev-response-review/final-check-r2.json). 최종 인계 예시의 대문자 run ID는 Python 검증과 맞지 않아 소문자로 교정했다. 문서만 바뀌었으며 초안 final-source와 최종 final-r2-source 증거를 함께 보존했다.

작성자 회귀393 PASS/34.55초·네 wire body/질문/모델/threshold/한도 동일을 원출력과 대조했다. 독립236건과 중복되므로 합산하지 않는다. Bandit은 baseline12 LOW/1 MEDIUM→14 LOW/1 MEDIUM, HIGH0이며 exit1을 보존했다. 새 builder argv-list B603과 disabled 정책 None B105, 기존 컨테이너 전용 tmpfs B108의 실제 사용 위치를 확인했다. shell 실행·임시 호스트 공유 파일 생성으로 해석하지 않지만 clean PASS/49약점 전수 완료로 보고하지 않는다. 현재 bundle/service/기존 DB는 배포하지 않았다.

## 가이드와 남은 경계

기존에 원 SHA/페이지 추출로 읽은 G2 PDF133/135/137의 오류 노출·예외, G3 PDF511·G4 PDF38의 오류/중요정보, G2 PDF146·G3 PDF415의 자원·유한 수행 원칙을 안전 allowlist·typed 입력/수치·timeout·원장 단회 예약/실패 보존·원문 미저장에 연결했다. 공식 source는 읽기만 했고 SDK/의존성/이미지를 새로 설치하지 않았다. 기존 설계20/약점49 적용성과 미완료를 유지하며 전수 PASS·정량 성능을 선언하지 않는다.

잔여: tools/jev_eval.py와 scripts/jev_eval.ps1은 기존 control hard-deny 경로 prefix에 포함되지 않는다. 평가 helper 자체의 AI 편집 방어는 미보장이고 frozen 검사는 신뢰된 helper 실행을 전제로 하므로 helper 자체 변조의 독립 방어로 확대하지 않는다. 이번 정책/권한 변경 금지에 따라 기존 정책을 보존했다. 실제 우회 시도/효과를 검증했다고 주장하지 않으며 별도 위협 경계로 남긴다.

실제 Jev 응답 호환성·한국어/공격 정확도·새 유료 재시험·Codex IPI 실행 전 차단과 일반 native/hook 장애/공급망 잔여는 미검증/미완료다. API/분석 실패는 공격 식별 PASS가 아니다. 다음 실제 호출은 구체 자료·총량/추가 비용·실행 범위를 사용자가 새로 결정해야 하며 이 REVIEW는 실행 승인이 아니다.
