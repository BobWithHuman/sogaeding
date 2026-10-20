# WP-ENGINE-DEMO-02 별도 AI 검토

2026-10-18 KST. 구현자와 별도 AI 검토 역할로 수행했다. 공식 독립 진단이나 추가 사람 개발자 검토가 아니다. 검토자는 코드·원장·키·기존 run·서비스를 수정하지 않았고, provider 호출 및 전체 회귀 재실행도 하지 않았다.

## 판정

**No findings.** 읽은 변경 경계에서 수정이 필요한 확정 결함을 발견하지 못했다. 이 판정은 아래 한계와 최종 source binding 확인을 전제로 하며 실제 Jev 정확도나 DTAP 시연 성공의 판정은 아니다.

검토 대상은 START_PROMPT·RESULT·USER_RUN, 새 `demo_policy.py`·`runtime_demo.py`, 변경된 runtime policy/services/controller/budget/report·hook, `tools/dtap_runtime.py`, PowerShell launcher, 새 시험이다. tracked baseline 대신 부모 동결 source와 runtime budget/controller/launcher Python 경로의 실제 차이를 대조했다. 기존 전역 .90과 현재 서비스의 프로필을 바꾸는 변경은 확인하지 못했다.

- 코드 ALLOW 전에 실제 등록 schema 파싱, 등록부 digest 및 전체 출처 raw/text hash·완전성·source ID 충돌 검증이 실행된다. PUBLIC은 서버가 검토한 정확한 request/registry/schema/candidate 결합을 요구하며 도구명·출처 문장·외부 승인 주장만으로 발급되지 않는다. 다른 identity의 access token은 모델 호출 없이 DENY한다.
- 의미 ALLOW는 B raw LEGITIMATE/effective confidence ≥ .50 및 A raw WITHIN_TASK와 정확한 서버 grant·민감 접근/부작용 동의를 요구한다. 기존 .90 위험 DENY가 먼저 적용된다. 새 질문은 중간 조회/공식 권한 요청과 과거 행동 receipt를 구분하고, source 값 일치를 인과 증명으로 쓰지 않는다. 공식 응답 검증은 기존 validate_response·typed_observations 경로를 사용한다.
- runtime grant는 control 전용 경로에 놓이고 실제 집행은 기존 Engine 사전 판정·예약·정확한 승인 소비·서명 proxy를 지난다. DENY 승인을 허용하거나 UNKNOWN을 새 호출로 바꾸는 변경을 발견하지 못했다. HTTP 시험은 실제 ASGI control/authz/proxy와 HookManager를 사용하지만 gateway 운송과 upstream/모델은 합성이다.
- 새 원장은 부모 예약·정산·미확정 hold를 보존하고 jobs/stops/owners 이력은 별도 보존한다. 기존 UNKNOWN on은 terminal 상태로 가져온다. 부모 digest/fingerprint를 실행/예약 전에 확인하고 새 원장의 합산 비용과 다음 최대예약은 기존 SQLite 원자 트랜잭션에서 제한한다. 부모/다른 fork를 동시에 실행하는 분산 예산 잠금은 제공하지 않으므로 USER_RUN의 순차 실행 제한이 필요하다.
- 기존 off 조건부12개와 정상3개를 고정하고 actor 코드·snapshot·공격/도구/초기image binding을 확인한다. 보고서는 non-completed 상태 안의 DENY와 명시적 upstream 미호출을 별도 집계하며 demo의 final_asr_reportable은 false다. 사용자 명령은 새 root/manifest/누적상한·명시적 유료 opt-in을 요구하고 기존 resume를 거부한다.

## 시험 증거와 적용성

`artifacts/20261018-engine-demo-02/final-integration.log`의 최종 통합 1회는 **305 통과/1 실패**다. 실패는 기존 benign 없는 보고서의 문구 호환성이며, 현재 수정은 benign 유무를 구분한다. 이후 관련 범위 `report-fix-tests.log` **40 통과**, 원장·동시 예약/부모 drift 관련 `budget-tests.log` **34 통과**, `lint-final-r2.log` **PASS**를 읽어 확인했다. 실패 기록을 전체 통합 PASS로 바꾸지 않는다. 검토자가 같은 전체 시험을 반복하지 않았다.

R1/G1 동결 source·digest, G2 원자 예약/UNKNOWN, G3 서버 권한·출처/역할, G4 최초진단→조치→재진단 연결과 설계20/약점49 baseline 재사용·변경 영향 평가를 RESULT에서 확인했다. 전수 재진단·공식 조치율·모든 native sink를 이번 검토 PASS로 확장하지 않는다.

## 최종 확인과 한계

검토 시작 시 새 prepared root는 직전 보고 문구 수정 전 source였다. 이는 이미 구현자가 인지한 최종 동결 작업이며 별도 결함으로 중복 계수하지 않았다. 사용자 인계 전 최종 코드가 새 `source-manifest.json`/manifest/prepared binding에 반영되고 **PREPARED_NOT_STARTED, 신규 paid broker 없음**인지를 무모델 verify로 확인해야 한다. 검토자는 그 이후 생성될 최종 hash를 사전 승인한 것으로 표현하지 않는다.

실제 새 gateway 컨테이너 경유 효과·유료 actor/Jev·공격 효과/정상 완료는 NOT_RUN이다. 준비된 grant는 정상3개의 정확한 공개 조회 변형뿐이다. 이 외 후보는 .50 LEGITIMATE여도 정확한 grant가 없어 CONFIRM일 수 있고, 실제 demo에서 .50 의미 ALLOW가 관측된다는 보장은 없다. 정상17개 최빈 결과를 안전 정답이나 권한으로 사용하지 않는다. $1.80으로15개 완주를 보장하지 않는다. 조건부12개의 관측을 전체 ASR·방어율·인과 보호로 확대하지 않는다. AgentDojo·대시보드·개인 설정은 이번 검토 범위 밖이다.
