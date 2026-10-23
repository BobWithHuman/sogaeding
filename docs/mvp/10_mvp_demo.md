# Jev 의미·출처 합성과 한정 CLI 시연

2026-10-17 후속 의미/실제 CONFIRM 보완의 내부 계약은 [11_semantic_confirm.md](11_semantic_confirm.md)다. 아래 host-wait-1과 최초 준비 기록은 역사 증거로 보존한다. 현재 실제 시작2/2·Jev4/8·두 원 CONFIRM/UNKNOWN을 초기화하지 않으며 새 v3의 실제 정확도/자동 정상 완료는 아직 검증하지 않았다.

## 2026-10-16 호스트 승인 대기 보완

이 절은 아래 최초 준비 시점의 180초·호스트 승인 전 판정 설명을 수정한다. 사용자의 첫 실제 실행은 시작 예약 1/2, 읽기 READY/ALLOW 1건, upstream 0, 보고서 없음, demo Jev 0이었다. 종료 원인은 기록되지 않아 UNKNOWN이며 180초 timeout으로 확정하지 않는다. 최초 manifest/실패 HTML/원장/예약은 보존한다.

`host-wait-1` revision은 같은 runtime·DB·키·예산을 참조한다. 부모 manifest와 변경 소스·bundle을 새 manifest로 결합하고 이전 hash로 수정 코드를 실행하지 않는다. 새 대화형 한도 제안은 1800초이며 입력·호스트 승인·모델 계산 시간을 모두 포함한다. 사용자가 정확 revision/hash와 `ApproveInteractiveWallSeconds`를 직접 선택해야 한다. Jev 8요청/입력예약512000, 총 CLI 시작 예약 2는 그대로이며 이미 사용한 1회가 복구되지 않는다.

demo 전용 hook은 PreToolUse에서 정확한 의도와 당시 사용자 turn·인자·출처·정책을 등록한다. 이 시점은 PENDING이며 PDP 허용이 아니다. 호스트 도구 승인을 거쳐 실제 MCP 호출이 gateway private extAuthz에 도착한 뒤 단회 판정을 수행한다. 허용 시 기존 30초 freshness와 원자 reserve를 통과해 즉시 upstream으로 전달한다. 승인 대기 중 유효시간을 늘리거나 원문/ref 검증을 생략하지 않는다. 변경된 인자/출처/turn/정책·동시 재전송·분석 장애는 집행 전 차단하며 자동 유료 재분석을 추가하지 않는다. 호스트 승인은 Codex의 통제이며 MCP 호출 관측만으로 신뢰된 사람 클릭의 증명을 주장하지 않는다.

CLI 수명주기는 예약별 새 start/finish 파일에 UTC·경과 시간·exit code·timeout/취소/시작 실패·자식 정리를 기록한다. 원본 argv/env/터미널은 저장하지 않는다. 종료 기록이 없는 과거 예약과 끝 기록이 유실된 실행은 UNKNOWN이다. 정상 프로세스 종료도 보고서 성공과 별도다. timeout/오류 뒤에는 실제 판정/효과 history를 함께 표시하고 명령을 비정상 종료한다. 이력의 USER_DEMO/OFFLINE_REPLAY, PDP 대기/OBSERVED/UNKNOWN, 실제 파일 효과를 구분한다.

현재 최소 절차와 검증 결과는 호스트 대기 보완 인계에 연결한다. 실제 유료 actor/Jev 호출은 사용자가 직접 수행하며 개발 AI는 모델 없는 검증만 한다. 남은 시작 예약 1회는 정상 보고서 확인에 사용한다. 공격 시연을 위한 추가 시작 예약은 이 보완에서 발급하지 않는다.

2026-10-16 WP-MVP-DEMO-01. 기존 SPEC5 outward 인증·인자 결합·원자 예약·UNKNOWN/TLS·역할키 경계를 유지한다. 새 내부 정책은 hookgw-2026-10-16-jev-v2, 질문 jev-narrow-2, 근거 계약 jev-slots-context-2다. 응답 검증 jev-response-2와 임계치 .90은 유지하며 임계치는 아직 실제 정확도로 보정되지 않았다.

## 실제 과거 결과와 수리

첫 실행1요청은 FAILED/usageUNKNOWN이다. 사용자가 직접 실행한 followup4요청은 모두COMPLETED, 입력4614/출력780이었다. 누적5시도·예약320000을 보존한다. S01 CONFIRM/문맥미확정과 S02 B_EXTERNAL_EVIDENCE_REQUIRED를 의미 성공으로 덮지 않는다. 과거 선택/확률은 보존되지 않았으며 복구했다고 주장하지 않는다.

v1은 task relation을 지지하는 generic evidence를 외부활용의 출처 검사에도 사용했다. v2는 task_evidence(USER 전용)와 external_evidence(서버 source catalog 전용)를 분리한다. 후보 자체는 사용자 권한 근거가 아니다. A는 외부 사실을 보지 않은 요청 범위를 관측하고, B는 실제 관련 슬롯의 외부 데이터/추가 행동 활용을 관측한다. 사용자 지정 target·생성값의 NONE을 일괄 불확실로 취급하지 않는다. 선택되지 않은 무관 문맥의 미확정이 전체 판정을 무조건 CONFIRM으로 만들지 않는다. 실제 관련 불확실성과 정확 ref·출처 검증은 유지한다. 두 예제 문자열/정답 하드코딩으로 허용/차단하지 않는다.

typed 관측은 고정 질문/선택 enum·유한 확률·provider/computed/effective confidence와 LOW_CONFIDENCE/모델 명시 미확정을 구별한다. 원 응답 자유 문장은 저장하지 않는다. confidence 비교는 canonical 정렬 순서의 숫자 index가 아닌 서버 질문명에 결합한다. 정책에 쓰는 값은 provider와 반올림 전 계산값의 최솟값이다. 외부 source 역할 관측은 권한이나 인과 증명이 아니다.

## 시연 흐름

`scripts/mvp_demo.ps1`이 단일 진입점이다. prepare/check/inspect/history는 모델0이다. 실제 Codex는 사용자가 명시 start할 때만 열고 프롬프트는 사용자가 직접 입력한다. 작업 등록·수동 세션/토큰 복사·자동 프롬프트 주입은 없다. 기존 보호 TypeSafe key는 Control에 RO 참조하며 actor OPENAI_API_KEY와 기존 OpenAI judge 원장을 분리한다. 별도 runtime-mvp-demo의 PKI/DB/원장/ports8034·8044/합성 workspace/bundle을 사용한다.

사용자에게는 원문이 합성임을 알리고 docs/release.md 또는 docs/review.md의 사실을 요약해 reports/normal.md 또는 reports/review.md에 쓰도록 자연어로 요청하게 한다. actor에 정답·예상 판정·개발 하네스·case ID를 주입하지 않는다. actor가 위험 후보를 만들지 않으면 공격 식별 PASS가 아니라 NO_ATTACK_ATTEMPT/미관측으로 표시한다. 정상 쓰기는 실제 파일 변경과 확인하고 차단은 upstream 금지 효과0과 별도로 대조한다.

제안 한도는 별도 Jev 최대8요청/입력예약512000, actor180초×최대2 episode다. 과거5요청은 그대로 보존하고 새 요청 상한과 혼합하지 않는다. actor 비용은 별도이며 고정 금액을 보증하지 않는다. prepare/check가 키/모델 접근 성공이나 실행/추가 비용 승인인 것은 아니다. 정확한 manifest/자료·목적지·한도에 사용자 ConfirmSend가 있어야 새 demo 정책을 활성화한다. 호스트 user reviewer는 해당 CLI 호출에만 적용하며 샌드박스/전역 로그인·설정·CA를 바꾸지 않는다. 호스트 승인 UI와 실제 With Human CONFIRM을 구별한다.

## 읽기 전용 결과 화면

기존 인증 이력과 별개로 demo opt-in `HOOKGW_DEMO_VIEWER=1`+합성 grant에서 human 인증된 `/demo/history`만 제한된 투영을 제공한다. 요청/읽은 자료/제안 도구·대상/판정·이유/typed 근거를 최근10개·전체120k 이내로 제한한다. 자료는 마스킹 발췌이며 동적 필드명·credential·raw exception/본문 전체를 출력하지 않는다. 나중에 읽은 자료를 앞선 판정의 근거로 소급 표시하지 않는다.

CLI의 짧은 타임라인과 로컬 HTML 결과는 ALLOW/실행관측, DENY, CONFIRM, 분석실패, UNKNOWN, 공격 미시도를 구별한다. HTML은 script/network/form 실행을 차단하는 CSP와 HTML escape를 적용한다. 실제 파일의 현재 내용/해시와 별도 upstream 원장을 판정과 대조한다. OBSERVED는 원자적 receipt/멱등성 보증이 아니며 실제 파일과 SQLite 변경은 원자적이지 않다. UNKNOWN을 자동 재시도하지 않는다. 결과 HTML은 새 파생 파일로 쓰고 원증거를 덮지 않는다.

최종 정확 명령·manifest·화면 예시와 실행 증거는 WP-MVP-DEMO-01 인계에 있다. 개발 AI는 실제 모델을 호출하지 않는다. fake provider/합성 trusted hook actor+실제 gateway·파일 효과 회귀는 실제 모델 정확도/사용자 CLI 성공과 구분한다. 일반 native 개발·hook 사망 fail-open·동일 OS 사용자/helper 자기변조·전체 IPI/공급망·C/D/전체 MVP 완료를 주장하지 않는다.
# V5 별도 시연 revision (2026-10-17)

최신 준비는 `behavior-v5-1`이며 USER_RUN의 고정 start/history 명령을 사용한다. 기존 `mvp_demo.ps1`·승인 터미널·viewer를 재사용하고 V3와 별도 workspace/DB/8036·8046 포트를 쓴다. V5 질문/조합/.90은 유지하며 live는 표준 JevClient다. 개발 검증은 저장된 V5 A/행동 숫자의 재현과 별도 합성 높은 정상 답을 구분한다. 정밀 귀속은 새 시험 자료에서 합성 UNCERTAIN으로 두며 과거 source 의미를 새 실제 관측으로 승격하지 않는다.

개발 준비의 상태는 DEMO_PREPARED다. 새 Jev4/256000·CLI1(시작총4)·1800초, 역사합계25/1600000·demo관련20/1280000은 사용자 선택용 제안이며 실제 호출 승인이 아니다. 기존21/1344000·CLI3/3·V3 성공 파일과 서비스를 보존한다. 현재 V5 서비스는 disabled/JEV_RULES_ONLY이며 새 provider ledger/CLI claim이 없다.

정상 CONFIRM이면 별도 터미널의 `mvp_confirm.ps1 -Revision behavior-v5-1 -Watch`에서 번호 선택 뒤 정확한 후보를 보고 approve/reject를 직접 입력한다. Enter는 승인/거절 전송 없이 취소한다. Codex 호스트 Allow는 제품 PDP 승인이 아니다. 승인 후 동일 대기 RPC가 단회 재개되며 Jev를 다시 호출하지 않는다. 정상 사람확인은 HUMAN_CONFIRMED이고 자동 정상 성공과 구분한다. 공격 DENY는 승인으로 해제할 수 없다. 원문/후보/V5 선택·confidence/파일 존재·내용을 기존 HTML에서 확인하되 인과 설명은 NOT_ESTABLISHED다.

새 사용자 실제 시연·파일 효과 대조 전 DEMO_VERIFIED/정상 자동 핵심/전체 MVP 완료를 선언하지 않는다. 위험 후보를 만들지 않으면 NO_ATTACK_ATTEMPT이며 반복 유도하지 않는다. 등록된 합성 파일 MCP 범위이며 일반 native·hook 장애·전체 IPI 보호는 미검증이다.

