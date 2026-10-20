# 새 코드 정책 DENY를 인프라 장애로 오분류하는 실행기 보완

2026-10-18 실제 사용자 실행 후속. 기존 scope-v2 run을 재실행하지 않는다. [관리 RO 관측](../../../../artifacts/20261018-engine-demo-02-scope-v2-management/observation.json)을 기준으로 아래 변경만 수행한다. 유료 호출·AgentDojo 작업0.

## 원인

새 on은 첫 consent/11 한 과업을 시도했다. 실제 Jev에서 정상 조회2개가 ALLOW→OBSERVED됐다. 다음 `execute_command` 백업 후보가 scope 정책의 `NONLITERAL_OFFICIAL_SHELL_RESOURCE`로 DENY됐고 upstream0이다. 이 후보는 원 사용자 작업의 백업 단계로서 공격 채택이 확인된 것이 아니다.

`official_adapter.dispatch()`는 기존 `OUTSIDE_TASK_SCOPE`, `EXTERNAL_INSTRUCTION_DEPENDENCY` 두 사유만 일반 정책 DENY로 처리한다. 새 코드 DENY를 `ANALYSIS_OR_INFRASTRUCTURE_STOP`으로 바꿔 Controller가 UNKNOWN/전체중단으로 기록했다. 실제 provider 요청은 전부COMPLETED, POST도2건모두OBSERVED, close도관측됐다. 저장된 UNKNOWN은 역사 그대로 보존한다.

## 좁은 수정과 검증

1. 신뢰된 PDP의 정상 정책 거부/지원하지 않는 후보와 실제 분석·전송·저장 장애를 구분한다. 명시된 typed 분류 또는 검토된 정확 사유 목록을 사용한다. 임의 외부 문자열이나 모든DENY를 정상으로 간주해서 장애 차단을 약화하지 않는다.
2. 정책 DENY는 해당 호출 실행0을 유지하며 actor에 정확한 거부 사유를 돌려 지원된 파일 API 등 다른 정상 방법을 선택할 수 있게 한다. 지원하지 않는 일반 shell을 이 오류 때문에 허용하지 않는다. 도구/슬롯 유형 확인보다 앞에서 shell 문자열을 파일 경로로 검사해 오해하기 쉬운 사유를 내는 부분도 구분한다.
3. 새CODE DENY 이후 다른 정상 호출로 진행하는 경로를 실제 adapter→hook→control→controller에 연결한 무모델 시험1개로 재현한다. 분석/API/POST유실은 계속 UNKNOWN/중단되는 반례도 확인한다. 동결 source의 실제 이벤트를 replay한 원 오분류와 수정 후 결과를 구분한다.
4. status에 재사용 off12와 새on 진행률을 분리한다. 화면40%는 기존 off12가 포함된 값이며 실제 새완료0/15, 시도1/15, 미시작on14다. 이를 새 시연 성공률로 표시하지 않는다.
5. 기존 run/UNKNOWN/원장/source를 덮지 않는다. 후속 준비는 이번 실제 지출까지 계승하고 **기존 미시작14개만** 대상으로 한다. UNKNOWN이 된 consent/11을 자동 재시도하지 않는다. 원 누적명목비용3.332794, 이번사용.043500, 기존 run 누적상한5.089294이므로 이 run에서 남은 한도는1.756500이다. 새로1.80을 추가하지 않는다. 원총7도 유지한다.

관련 실패 경계만 수정·시험하고 최종 좁은 검토 후 새 사용자 명령을 인계한다. 과거121/32 등 전체 회귀를 문서 때문에 반복하거나 새 도메인·환경·단계를 추가하지 않는다. 부모 지출·중단 상태·지원 경계·actual paid NOT_RUN을 명확히 결합한다.
