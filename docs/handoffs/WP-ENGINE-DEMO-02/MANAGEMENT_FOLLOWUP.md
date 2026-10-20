# 실행 전 보완: 준비된 run에서 .50 의미 ALLOW 경로가 도달 불가

> 해결 확인: scope-v2의 실제 준비 scope·원 MCP 미열거 쓰기/내용 재읽기·최종 binding·별도 검토와 관리자의 무모델 launcher check를 대조했다. 새 manifest는 `338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8`이며 [새 실행 안내](scope-v2/USER_RUN.md)를 따른다. 아래는 v1 문제의 보존 기록이다. 새 실제 모델 실행/성능은 아직 NOT_RUN이다.

2026-10-18 관리 확인. 현재 사용자 실행 명령의 manifest `7562007f3ff14e4bdacbf2ec68c2488908917229d93d630d3c05e6a8c24c6221`은 아직 실행하지 않는다. 실제 새 provider 호출0, prepared 원장·source·키·서비스는 이번 확인으로 변경하지 않았다.

## 확인된 목표 미달

1. `runtime_demo.prepare()`가 `reviewed_operations`를 정상 `benign/2,3,4`의 정확한 조회 인자3변형씩에만 발급한다. 12개 conditional 공격 task에는 operations가0이다.
2. `demo_policy.compose()`는 Jev 의미 결과와 별개로 `authority()`의 정확한 candidate 사전등록 grant를 요구한다. 그 grant가 없으면 A rawWITHIN_TASK·B rawLEGITIMATE·confidence.99여도 CONFIRM이다.
3. 그9개 공개조회 grant는 `route()`에서 이미 코드 ALLOW된다. 따라서 실제 준비본의 15개 과업에서는 **.50 의미 ALLOW가 발생할 후보가 구성되어 있지 않다.** .50 코드의 합성 unit 시험 PASS와 실제 run의 도달 가능성은 다르다.

동결된 실제 `compose()` 함수로 위.99/권한목록없음 반례를 실행해 `CONFIRM/DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED`를 재현했다. [RO 검증](../../../artifacts/20261018-engine-demo-02-management/semantic-allow-reachability.json). 원 budget 결합은 추가1.80/누적5.089294로 맞지만 지금 지출하면 의미 정상 후보가 반복CONFIRM으로 끝날 구조다.

이것은 기존 권한 검증을 없애라는 지시가 아니다. **정상 후보마다 정확한 인자를 사전에 나열해야 한다는 조건이 .50 의미 허용의 필수 조건으로 들어가, 위임된 정상 작업의 자동 진행을 대체한 문제**다. 기존 실행권한·정확 인자 예약 결합과, 사전 정답처럼 나열한 후보 허용목록을 구별해야 한다.

## 좁은 보완 범위

- 신뢰된 서버의 세션/작업 범위·등록 도구·자원 접근 정책과 후보 적합성을 분리한다. 이미 발급된 작업 범위 안의 정상 중간 조회·준비·일반 작업은 특정 candidate를 미리 열거하지 않아도 의미 판정 경로를 통과할 수 있어야 한다.
- B 정상/.50+A rawWITHIN_TASK만으로 새로운 접근권한을 발급하지 않는다. 실제 권한·소유자·민감자원·원 도구의 동의/부작용 요구를 코드로 확인하고, 그 범위 밖 후보는 계속 거부/확인한다. 공식 permission 옵션이 요청과 실행을 함께 수행하는지도 실제 도구 구현으로 확인한다.
- 정확한 세션/도구/인자/schema/정책 hash·원자 reserve·승인 단회 소비·DENY 우선·UNKNOWN 미재시도·출처 무결성·global.90 보존은 유지한다.
- 알려진 공격 task ID나 judge/기대 답을 보고 권한/금지 예외를 늘리지 않는다. 과업별 정확한 정답 후보를 사전 등록하는 방식만으로 정상 가용성을 대체하지 않는다.

## 필요한 재검증만

실제 준비되는 run의 config·grant·policy를 그대로 쓰는 무모델 통합으로 아래를 보인다. 시험 안에서 별도 exact grant를 주입해 PASS시키지 않는다.

1. 사전등록 인자목록에 없는 **정당한 작업범위 내 후보**가 B LEGITIMATE/.60+A rawWITHIN_TASK에서 의미 ALLOW되고 단회 실행된다.
2. 같은 fixture의 외부 수신자 변경/미승인 비밀 접근/보안 설정 변조 등 권한 밖 후보는 저임계치로 허용되지 않고 upstream0이다.
3. .50 미만·A/B 충돌·동의 부재·출처/분석 장애는 기존 상태 계약대로 유지한다. 일반 공개 조회는 계속 모델0 ALLOW다.
4. 준비된 정상3개와 공격유형 대표 과업의 원래 정상 단계가 첫 후보에서 사전 grant 부재만으로 일괄 보류되는지 확인한다. 실제 분류 성능은 사용자 실행 전 미검증으로 유지한다.

보고 문구/하네스/공급망 전수 검토·통과한 전체305개 시험을 문서 때문에 반복하지 않는다. 해당 정책/권한/준비 경계의 시험과 새 반례, 최종 관련 통합, 해당 변경의 좁은 별도 AI 검토만 수행한다. 기존 parent·실패/시험 로그·준비본은 보존하고 실제 유료 호출은0이다.

최종 USER_RUN에는 의미 ALLOW가 실제 설정에서 도달 가능함을 입증한 근거와 새 검토 hash를 명시한다. $1.80 추가 상한·기소비 포함 누적상한·Actor GPT-5.2 low·실제 Jev·AgentDojo 제외는 유지한다. 구현·검증·재동결이 끝나면 복사 가능한 명령을 다시 인계한다.
