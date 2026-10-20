# WP-ENGINE-DEMO-02 구현 결과

> 관리 후속 확인: 이 v1 결과의 실제 준비 설정에서는 .50 의미 ALLOW가 도달 불가했다. 아래 기록은 보존하며, 수정과 실제 설정 검증은 [scope-v2/RESULT.md](scope-v2/RESULT.md)를 따른다. v1의 이전 No findings는 이 결함을 발견하지 못했다.

2026-10-18 KST. 구현·무모델 검증·별도 DTAP 실행 준비. 실제 유료 provider 호출 0. AgentDojo·대시보드·개인 설정·기존 서비스·기존 run 수정 없음. 관리 장부의 DONE 판정은 하지 않았다.

## 변경과 실행 경계

- `src/app/benchmark/demo_policy.py`: `dtap-demo-allow50-v1`만 선택하는 격리 프로필. 서버 발급 요청 hash·등록부 hash·실제 schema hash·정확한 후보 hash를 모두 대조한다. 등록 QUERY + 검토된 PUBLIC + 부작용 없음 + 정확한 권한만 코드 ALLOW. 명시 금지와 다른 사용자 token으로 identity 전환은 코드 DENY. 도구 이름/외부의 승인 주장으로 권한을 발급하지 않는다.
- `runtime_policy.py`, `runtime_services.py`: 코드 routing 전 출처 완전성/raw/text hash·중복 source·등록부 무결성 검증. 새 질문 버전 `dtap-demo-questions-2`: 중간 조회·준비·공식 권한 요청, 현재 후보와 과거 결과, 도구 설명·읽기 결과·행위 완료 receipt를 구분한다. 원문/span/hash는 유지하고 외부 값 일치를 자동 DENY나 인과 증명으로 쓰지 않는다.
- 의미 ALLOW는 B raw LEGITIMATE/effective confidence ≥ .50 + A raw WITHIN_TASK + 정확한 서버 권한. 민감 접근 동의/부작용 동의가 없으면 CONFIRM. 기존 .90 위험 DENY를 먼저 적용한다. 공식 확률합·ARGMAX·유한수·confidence 계산·provider/computed MIN 검증 유지. 전역 `selected()` .90 및 기존 서비스 프로필은 변경하지 않았다.
- `runtime_controller.py`, `runtime_budget.py`, `runtime_demo.py`, `tools/dtap_runtime.py`, `scripts/dtap_official_runtime.ps1`: 기존 source·원장·UNKNOWN·정산·최대 hold·초기image를 보존하는 fresh on 실행 준비. 기존 actor·adapter·Responses loop의 byte 동등성을 확인하고 실제 actor snapshot이 수집 시에도 `gpt-5.2-2025-12-11`일 때만 off pair를 인정한다. 기존 UNKNOWN on은 새 원장에서도 UNKNOWN으로 남겨 dispatch하지 않는다. 새 paid broker는 시작하지 않았다.
- `hook.py`, `runtime_report.py`: CONFIRM/UNKNOWN/예산 중단 안의 DENY를 all-state로 집계하고 PRE에서 dispatch하지 않은 후보의 upstream0을 별도 표시한다. 의미 DENY reason도 따로 집계한다. 조건부12개는 전체 ASR로 보고하지 않는다.

새 source·manifest 동결 위치: `artifacts/20261018-dtap-os100/user-engine-demo-02/`. 실패 준비본은 `artifacts/20261018-engine-demo-02/prepare-failed-network/` 등에 보존한다. 원래 부모 `user-usd7-context-2`는 RO로만 읽었다.

최종 동결 manifest는 `7562007f3ff14e4bdacbf2ec68c2488908917229d93d630d3c05e6a8c24c6221`이다. `final-freeze-check.log` 및 `final-bindings.json`에서 현재 소스와 동결80개 파일 일치, 부모 원장 결합, 예약/정산/자원 행 원본 일치, 상속 off 완료12개만 존재, 새 paid 호출0·broker 미시작을 확인했다. 상태는 PREPARED_NOT_STARTED다. 별도 AI 검토는 `REVIEW.md`의 No findings이며, 검토자가 요구한 최종 재동결 후 결합 검사는 이 증거로 완료했다. 직전 준비본도 `prepare-before-final-freeze/`에 보존했다.

## 검증과 최초 진단→조치→재진단

로그 위치는 `artifacts/20261018-engine-demo-02/`다.

| 최초 관찰 | 조치 | 증거 |
|---|---|---|
| 합성 응답 confidence와 확률 분포 불일치: 8 실패/71 통과 | 공식 계산식에 맞게 시험 응답 수정 | `related-tests.log` → `related-tests-r2.log`: 79 통과 |
| 실제 Engine 요청은 원문이 아닌 chronological JSON | 정상 grant도 정확한 Engine 요청 형식으로 결합 | 새 Engine/HTTP 경로 시험 포함 `http-effects-tests.log`: 32 통과 |
| ACL 재설정 권한 오류·기존 subnet 충돌 | 이미 제한된 owner/SYSTEM ACL 검증 후 재사용, 기존 network 보존하고 빈 .140/.141 선택 | `prepare-r2.log`, `prepare-r3.log`, 새 준비 로그 |
| 최종 관련 통합검증 1회: 305 통과/1 실패, 기존 OS100 보고서 문구 호환성 | benign이 없는 기존 보고서의 기존 문구 보존 | `final-integration.log` → 영향 범위 `report-fix-tests.log`: 40 통과 |
| 새 source의 import/미사용 변수/예외 타입 | 새 파일 포맷과 좁은 lint 수정 | `lint-final-r2.log`: PASS, PowerShell parser PASS |

새 시험은 34개다. 코드 경계·위조 grant·source 변조·.499999/.50/.500001·A/B 충돌·미승인 민감 접근/삭제·정확한 단회 승인·UNKNOWN 미재시도·실제 control/authz/원자 reserve/서명 proxy·합성 upstream 효과/실행0·부모 원장 drift·기존 $3.289294 + 최대 hold + 다음 최대예약 동시성을 검사했다. 400k/8192 최대예약 $0.814688을 유지했다.

HTTP 통합 시험의 gateway 전송은 in-process이며 upstream과 모델 응답은 합성이다. 새 실제 gateway 컨테이너/유료 Jev의 성능 검증으로 표시하지 않는다. 기존 실제 gateway 증거는 `docs/handoffs/WP-DTAP-01/20261017-dtap-prepare/SECURITY_REVIEW.md` 및 `artifacts/20261018-dtap-os100/offline-final-06/`를 변경 없는 전송/예약 계약의 선행 증거로 재사용한다.

## 시연·비용·미실행

기존 off 공격성공12개를 조건부 고정하고 새정책 on으로 준비했다. 첫 표시 순서는 유출(consent/11) → 미승인 삭제(consent/12) → 명령 로거(profiling/2)다. 정상3개는 결과를 보기 전에 `os-filesystem/benign/2,3,4`로 고정했다. 배우는 실제 자율 Responses actor이며 강제후보/replay arm을 추가하지 않았다.

원비용 $3.289294, 새 추가 지출 상한 $1.80, 새 누적 상한 $5.089294 ≤ 원승인 $7. 기존 UNKNOWN과 미확정 최대 hold도 복사한 원장에서 계속 비용에 포함한다. 나머지 $1.910706은 이번 프로필에 발급하지 않았다. 부모 원장은 매 예약 전에 대조하고, 동일 새 원장의 최대예약은 SQLite 원자 트랜잭션으로 검사한다. 기존 run이나 다른 fork를 동시에 실행하지 않는다.

현재 검토된 코드 ALLOW grant는 정상3개의 정확한 공개 조회 변형에 한정된다. 그 외 후보는 의미 분석과 정확한 별도 권한이 필요하며, 권한 없는 정상 후보도 CONFIRM에 머무를 수 있다. .50 조정이 기존17개 정상최빈 응답을 실제 허용하거나 DTAP 정상 완료를 보장한다는 주장은 하지 않는다. 실제 Jev 결과·공격 효과·정상 업무 완료는 사용자 실행 전 NOT_RUN이다.

복사 가능한 사용자 명령·중단·실패 수집은 `USER_RUN.md`, 별도 AI 검토는 `REVIEW.md`를 따른다.

## 필수 가이드와 적용성

기준: `docs/plans/03_guide_compliance.md` G-01~08, `05_contest_security_criteria.md`의 요구→설계→구현→동적 검증/구조적 예방. 재사용한 원문 발췌는 `artifacts/20261017-frozen-demo/guide-pages.json`, `artifacts/20261017-core-auto-finish/auth-guide-pages.json`이다. R1 PDF14·G1 PDF35–36은 동일 digest 이미지/동결source/부모 hash, G2 PDF128–129·135·137은 원자 예약/한도/UNKNOWN, G3 PDF110–112·507–508·510은 기존 인증감사·서버권한/출처·키 분리, G4 PDF24·38은 위 최초진단→조치→재진단과 별도 REVIEW에 연결한다. 의존성·인증·DB schema 계약·TLS 설정 변경은 없다. 새 원장 안에 보존용 history table만 추가한다.

설계20/약점49의 전체 적용성 baseline은 `docs/handoffs/WP-DTAP-01/20261017-dtap-prepare/SECURITY_APPLICABILITY.csv`의 69행을 재사용한다. 이번 변경에 영향을 받는 행은 아래와 같이 갱신 평가하며, 나머지의 미점검/잔여 한계를 PASS로 올리지 않는다.

| 적용 범위 | 이번 변경의 설계/코드/동적 근거 | 상태 |
|---|---|---|
| SR1-1,1-4,1-9,1-10,2-4,3-1,4-1; W-01~04,08,15~17,21~24,29~30,33~38,44~47 | 실제 schema와 전체 slot/args 결합, 외부 승인·identity 위조 거부, source/hash 검증, manifest/원장 RO 검증, parameterized SQLite·예약 경쟁·UNKNOWN, 정확한 승인/역할 분리 | 변경 관련 합성/통합 시험 증거, 전체 18도구 효과·정확한 인과는 미검증 |
| SR1-5~8,2-1~3,2-5~8; W-05~07,09~14,18~20,25~28,31~32,39~43,48~49 | 기존 auth/audit/TLS·고정 argv·전송 endpoint·출력 정책/SDK·제한 재사용. UI·XML/LDAP·password·upload/download·암호 알고리즘·일반 native sink를 새로 추가하지 않음 | baseline 적용성/미완료 유지; 미실행 항목의 PASS 선언 없음 |
| SR1-2,1-3 | 새 경로는 JSON·SQLite·고정 Python/PowerShell CLI이며 XML/LDAP 라이브러리·서버를 도입하지 않음 | 이 변경 경계에 한해 비노출; 전체 제품 비적용 아님 |

적용 P0는 서버 권한/출처 무결성, 사전 PDP+원자 예약, 단회 승인, 장애 실행0/UNKNOWN/미환불, 비밀/역할/인증 감사다. 관련 시험과 기존 TLS·실제 집행 근거를 함께 연결했다. 공급망 전이 SCA 전수·설계20/약점49 전수 재진단·모든 native/모든 IPI·공식 조치율/빌드라인·장기운영은 이번 PASS 범위가 아니다.
