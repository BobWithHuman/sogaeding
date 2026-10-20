# WP-MVP-DEMO-01 별도 AI 검토

2026-10-16. with-human-dev, START_PROMPT·계획16 전체, 최신 AGENTS/control_state·가이드 준수표와 기존 실제 실패/인계를 읽었다. 작성자와 분리된 AI 검토이며 사람 개발자는 사용자1명이다. 공식 독립 보안 진단이 아니다. **의미 질문·근거 합성 수리와 등록 MCP 데모 준비는 현재 검토 범위에서 수용 가능, 발견 P2 두 건은 조치·독립 재진단 완료, 미해결 차단 지적0이다. 최종 RESULT/USER_RUN·실제 준비 manifest·보존 대조를 완료했다.** 실제 사용자 CLI 성공·실제 모델 정확도·전체 MVP 완료는 수용하지 않는다.

제품/관리 파일은 읽기 전용으로 검토했다. 본 REVIEW와 배정 artifacts만 작성했다. 실제 actor/provider/evaluate 호출0, 기존 TypeSafe 키 파일의 본문/hash 접근0이며 새 테스트 TLS·가짜 키/원장만 사용했다. 개인 로그인/설정/CA·기존 원장/결과를 변경하지 않았다.

## 기준선과 판정 계약

기존 원13개 공개 파일/원장에 대해 mode=ro+query_only와 전후 hash를 기록했다. 최초 A/FAILED1·64000·usageNULL과 후속4/COMPLETED·256000·입력4614/출력780, 누적5·320000이 보존돼 있었다. 최초 원응답/상세 선택은 없으므로 그 실패 원인이나 후속 실제 선택/확률을 복원하지 않았다. [기준선](../../../../artifacts/20261016-mvp-demo-review/baseline.json).

보존된204파일 v1 소스만 마운트한 [독립 재현](../../../../artifacts/20261016-mvp-demo-review/baseline-contract.txt)에서 USER task 근거와 TASK_DATA 관측이 B_EXTERNAL_EVIDENCE_REQUIRED로 충돌하는 설계를 확인했다. 실제 사용자의 폐기된 선택값까지 재현했다는 뜻은 아니다.

새 내부 정책 v2/jev-slots-context-2/jev-narrow-2는 task_evidence(USER 전용)와 external_evidence(SOURCE_DATA 전용)를 분리한다. A는 외부 사실을 인증하지 않고 사용자 요청/후보의 행동·대상·출력 범위를 관측하며, B는 실제 외부 사용과 관련 슬롯을 관측한다. candidate 자체와 외부문서는 권한 근거가 아니다. 사용자 target의 NONE·생성값은 자동 불확실로 만들지 않고, 선택된 외부 근거와 슬롯 연결 없이 TASK_DATA/NEW_INSTRUCTION을 확정하지 않는다. 사용한 관련 문맥의 미확정은 유지하며 무관한 문맥의 UNRESOLVED/낮은 confidence를 전체 과업으로 전파하지 않는다.

정확 모델/옵션·타입/finite/범위·합계/argmax·출처 hash/view/exact ref, 유효 confidence=min(provider,원계산), threshold0.90을 유지한다. 실패·UNKNOWN·예외 승인은 권한 승격이나 재시도로 바꾸지 않는다. 두 case ID·정답 문자열로 제품 분기를 추가하지 않았다. fake 응답의 의미 선택은 검토자가 주는 관측이며 실제 모델의 한국어/공격 정확도를 증명하지 않는다.

## 발견·조치와 독립 시험

- DEMO-OBS-01/P2: low-confidence raw evidence 선택은 정책의 검증 ids에서 빠질 수 있는데 모든 typed row에 EXACT_VALIDATED를 표시했다. 선택해 exact 검증한 참조와 SERVER_CATALOG_BOUND_NOT_SELECTED를 구분하도록 수정했고 독립 반례로 확인했다.
- DEMO-OBS-02/P2: JevClient의 canonical 질문 정렬 뒤 numeric index와 정책 build 삽입 순서가 달라 다른 질문의 provider confidence를 표시했다. 독립 시험에서 provider0.965가1.0으로 보이는 실패를 재현했다. 서버 질문명으로 transient 비교값을 결합하도록 수정했고, 무관한 질문의 낮은 confidence가 다른 질문을 하향하지 않는 반례까지 통과했다.
- viewer의 link_action 누락과 인용된 JSON credential 마스킹은 소스 검토 피드백 뒤 첫 독립 실행 전에 보완됐다. 해당 초기 실행 FAIL을 만들지 않았다.

[발견·조치 이력](../../../../artifacts/20261016-mvp-demo-review/findings.json)을 보존했다. 초기 독립 fixture 원장명이 budget.sqlite3여서 발생한18 실패는 요구 파일명 typesafe-budget.sqlite3로 검토 harness만 수정했다. 최종 compact CLI에서 허용된 일부 관측만 보이고 HTML에서 전체 상세를 보는 변경에 맞춰 검토 assertion도 고쳤다. 제품 결함·검토 fixture 오류와 출력이 잘린 초기 traceback 기록을 구별했다.

자체 **54개**(semantic28/viewer18/runtime8)를 포함한 관련 회귀는 **255 PASS/14.88초**다. [명령](../../../../artifacts/20261016-mvp-demo-review/regression-final-r2-command.json), [출력](../../../../artifacts/20261016-mvp-demo-review/regression-final-r2.txt). network none/비root/RO source Docker와 새 임시 파일·가짜 key·MockTransport만 사용했다. 실제 사용자 runtime 키/원장은 마운트하지 않았다. 작성자 회귀와 중복되므로 합산하지 않는다.

정상 사실·합법적 문서 권고·금지/인용 보고·생성값·사용자 target, 외부 추가 지시·연결 근거 없음/관련·무관 문맥·명시 UNCERTAIN과 LOW_CONFIDENCE, 교차 origin/비유한/동적 필드/출처 hash·중복·잘림, quote-aware credential 비노출·HTML escape/CSP·허용 경로·분석 실패/CONFIRM/UNKNOWN의 공격 PASS 금지, 실제 시작 전 승인/manifest/source/image·bundle mismatch·episode timeout 재시도/추가 발급0, 파일 symlink/hardlink를 확인했다.

실제 Windows PowerShell5.1에서 복사 wrapper+fake Python으로 **16/16 PASS**다. [증거](../../../../artifacts/20261016-mvp-demo-review/native-start-r2.json). UTF8/-I·인코딩 복원·명시 start3한도·승인6필드 누락 거부·Python 시작 실패·기본 Codex 경로1개 전달을 확인했다. 실제 Codex actor/Docker/provider는 이 native fixture에서 실행하지 않았다. 기본 Get-Command가2개 Application을 반환하던 문제는 작성자의 실제 check에서 발견했고 Select-Object -First1 수리를 독립 재진단했다.

## 실제 gateway·화면 연결

[독립 gateway-r2](../../../../artifacts/20261016-mvp-demo-review/gateway-r2/evidence.json)는 **22/22 PASS**, 실제 TLS hooks 프로세스/UserPrompt·Pre·Post → MCP adapter → 고정 digest agentgateway → 파일 upstream을 통과했다. 실제 source hash 시작/종료 일치와 고정 image를 기록했다. 정상 파일 본문/bytes/hash와 OBSERVED, 인자변조/replay 거절, 두 번째 사용자 turn, 외부 지시를 따른 강제 후보의 실행 전 DENY/금지 파일 미생성, human 이력 인증을 확인했다. upstream3회/OBSERVED3이며 원자 receipt라고 가정하지 않았다. 사용한 Jev4회는 MockTransport이고 피해 actor의 후보를 강제한 REPLAY다. 실제 모델 정확도/공격 유도 성공이 아니다. fixture는 종료 후 down했으며 기존 서비스/DB를 내리지 않았다.

같은 증거로 [오프라인 화면](../../../../artifacts/20261016-mvp-demo-review/offline-example.html)을 생성했다. 작성자의 최신 screenshot도 직접 봤으며 요청→자료→후보/판정→실제 파일 효과4개 카드와 금지 파일 없음이 읽히고 JSON 전체/본문 wrapper가 주 화면이 아니었다. typed 상세는 접어 두며 source 역할/검증 상태를 구분한다. HTML은 외부값을 escape하고 active content/credential을 반환하지 않는다. 화면의 현재 파일과 호출 OBSERVED는 별도 관측이며 인과/원자 receipt를 보장하지 않는다는 설명을 확인했다. 실제 actor가 위험 후보를 만들지 않으면 NO_ATTACK_ATTEMPT 또는 미확정으로 표시하며 차단 PASS로 세지 않는다.

## 준비·가이드·남은 범위

단일 entrypoint의 prepare/check는 모델0, start만 정확 manifest/목적지·자료·새 Jev8/512000·actor2episode를 사용자 직접 선택으로 허용한다. episode는 단회 선점하며 timeout/중단 뒤 삭제·자동 재시도하지 않는다. 기존5시도/첫 UNKNOWN과 분리한다. 새8회까지의 누적 예약 산술13/832000은 실제 사용량·계정 청구가 아니다. TypeSafe 키는 별도 Control에 RO 참조하고 actor OPENAI 환경과 과거 OpenAI judge/원장을 분리한다. 전역 로그인·reviewer·CA를 바꾸지 않는다. child CLI의 사용자 reviewer/on-request와 demo-only project_doc_max_bytes=0은 이번 호출에 한정하고 sandbox/hooks/PDP를 끄지 않는다. 후자는 상위 개발 AGENTS/하네스·정답의 피해 actor 유입을 막기 위한 시연 자료 분리다.

새 disabled demo에서 기본 CLI 경로 수리 후 원 manifest를 archive하고 PS source hash1개만 갱신한 절차를 검토했다. exact old SHA·disabled/episode0·ledger 없음·calls/turns/sources0·차이PS1개를 확인한 뒤 새 현재 검증을 요구하며 키/PKI/DB/예산을 초기화하지 않는다. 기존 run의 manifest 재사용/검증 무시는 아니다. 수리 중 sandbox Docker inspect 권한 실패와 후속 read-only 확인을 구별한다.

[최종 독립 대조](../../../../artifacts/20261016-mvp-demo-review/final-check.json)는 최종216파일 fingerprint `85f933383aead74c84819c36980f638c63fc2851f411727ddf6df36a4e0f0dd3`의 현재/동결 SHA 불일치0, 준비된 manifest `454466abc92df12740a8ce9e16837ddc88f85dbbcf85a473d522077a1278ed05`의50개 source와 bundle36개 exact set/current 일치, gateway-r2 제품/이미지 일치를 확인했다. 자체255회귀 뒤 runtime 변경은 PS 기본 executable 선택1줄뿐이며 최종 PS5.1 fixture16건으로 재검증했다. 원13개 파일 hash·원5시도/320000·키 metadata/ACL 동일, 새 enabled=false·episode0·ledger 없음·DB calls/turns/sources0, RESULT/USER_RUN/REVIEW 로컬 링크 누락0이다. 부모 전후 보존 JSON은 서로 다른 보고 schema이므로 최초 전체 dict 비교 assertion 실패를 보존한 뒤 실제13개 hash·동일 예약 합계·UNKNOWN 상태별로 대조했다. 제품 상태 변경을 뜻하지 않았다.

작성자 관련466 PASS/35.84초와 Ruff PASS 증거도 읽었다. 그 회귀 뒤 PS1줄 수리를 위와 같이 별도 검증했으며 회귀 전체를 수리 후 다시 돌렸다고 주장하지 않는다. 변경7파일 Bandit은 HIGH0·MEDIUM7·LOW7/exit1이며 clean PASS가 아니다. container bind 0.0.0.0·전용 tmpfs/공개 fake key 경로와 고정 argv subprocess 경고의 사용 경계·negative 검증을 수동 대조했다. 과거 다른 검사 집합과 경고 수를 개선율로 비교하지 않았다. 실제 사용자 start는 미실행이며 무모델 실제 check READY·issues none과 empty history까지만 확인됐다.

필수5개 PDF SHA와 적용16페이지 재추출을 대조하고, 새 화면에 직접 관련된 G3 PDF507 SR1-5의 HTML 인코딩·요청 검증과 G4 PDF24의 코딩/리뷰/통합시험도 추가로 읽었다. [원문 대조](../../../../artifacts/20261016-mvp-demo-review/guide-check.json). G3 PDF508/509·G4 PDF37~39는 task 권한/출처·인자/경로·human endpoint와 negative 시험, G2 PDF133/135/137·G3 PDF511은 typed 안전 진단·마스킹·fail-stop/UNKNOWN, G2 PDF146/G3 PDF415는 유한 예산/timeout·자원, R1 PDF14/G1 PDF35~38은 고정 이미지/무결성·RO·회귀/분리 환경에 연결했다. 새 의존성·이미지 도입0이며 기존 설계20/약점49 전수 적용성·미완료/공급망 잔여를 유지한다.

실제 수정 질문의 Jev 의미 정확도·사용자 interactive Codex/host 승인 성공·전체 native/hook 사망·전체 공급망/모든 IPI는 NOT_RUN 또는 미완료다. 신뢰된 helper/동일 OS 사용자 경계를 유지하며 helper 자체 변조의 독립 보호를 주장하지 않는다. 분석 오류·CONFIRM·미시도는 공격 식별 PASS가 아니다. 사용자 실제 시연 뒤의 최종 수용·전역 DONE은 관리 세션 판단이다.
