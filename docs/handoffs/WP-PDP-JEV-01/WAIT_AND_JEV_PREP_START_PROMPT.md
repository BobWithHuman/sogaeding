# 승인 대기와 gateway 판정 시효 수정 / 실제 Jev 평가 준비

상태: **AUTHORIZED_OFFLINE_IMPLEMENTATION**. 관리 배정 T-JEV-03/04. 제품 구현은 기존 개발 세션에서 하고 별도 AI 검토를 거친다. with-human-dev, 최신 AGENTS/00_CONTROL_CENTER/control_state, `docs/plans/reviews/WP-PDP-JEV-01_20261016_host_wait_management.md`, `docs/plans/03_guide_compliance.md`, SPEC5/현재 Jev 계약과 직전 HOST_REVIEW RESULT/REVIEW를 읽는다. 실제 OpenAI/TypeSafe/actor 호출0회로 수행한다.

## 고정할 사실

최종193파일 fingerprint `bdc7df912c9d2c815b9c2928814004b4afc83310fe66e6686084a0f367daa999`의 호스트 수동 reviewer 옵션 준비를 관리가 좁게 수용했다. 사용자 수동 승인 UI는 열렸으나 새 read ALLOW/READY 후 약90.074초에 Control `FORWARD_SNAPSHOT_STALE`/403, upstream attempts0이었다. `engine.forward()`의30초 freshness와 승인 대기가 충돌했고 MCP가 이를 `HTTP_AUTH_REJECTED`로 뭉갰다. 근거 `artifacts/management-host-wait-20261016/observation.json`. 키 재발급이나 bob4400 삭제로 해결하지 않는다. REJECT audit는 call빈값이므로 연결의 한계도 보존한다.

## T-JEV-03: 승인 대기를 지원하는 좁은 수리

1. 최초 진단과 변경 전 소스/실패를 고정하고, 로컬 fixture·가짜 actor·시계 제어로 수동 승인에 해당하는 지연을 실제 gateway 경로에서 재현한다. paid actor나 사용자에게 빠르게 승인/반복 실행을 요구하지 않는다.
2. 전체 lease 연장·시효 검사 삭제·`analyzed_at` 무조건 덮어쓰기는 하지 않는다. **기존 RULE_ALLOW/PUBLIC_ENROLLED_READ 후보에만**, 실제 gateway의 동일 요청에서 현행 인증/세션/turn/정책·grant/실제 도구·인자·출처 snapshot/공개 대상·경로 통제와 미해결 선행 호출을 다시 검사하는 무모델 경로를 검토·구현한다. 모든 검증이 현재에도 충족될 때만 같은 call을 원자적으로 한 번 전달한다. 원판정과 새 재검증의 시각/정책/근거를 구분해 보존한다. 새 권한이나 범용 승인 우회는 발급하지 않는다.
3. 의미 판정의 만료, 인자/turn/정책/grant/필수 문맥 변경, 보호 자원, 재전송/경쟁, UNKNOWN은 계속 차단한다. 만료를 묵시적 유료 재분석이나 자동 위험 쓰기 재시도로 바꾸지 않는다. signed forwarding ticket의 짧은 유효시간은 호스트 승인 대기와 구별하고 발급은 최종 검증 후다. 과거 READY/UNKNOWN은 수정·해제·재실행하지 않는다.
4. 401/403만으로 인증 실패라고 단정하는 표시를 고친다. 신뢰된 Control에서 나온 고정 allowlist 사유와 안전한 call 상관관계를 보존하되 토큰·요청/응답 본문·임의 upstream 문자열은 출력하지 않는다. 출처를 확정할 수 없는 거절은 인증/정책 미분류로 명시한다. 실패 수집이 원 실행 상태를 성공으로 바꾸지 않아야 한다.
5. 정상 즉시/90초 이상 대기 읽기의 실제 upstream1회·출처 관측, 인자/turn/정책/grant/문맥 변경 시0회, 범위밖/민감 읽기0회, 동시 replay 추가0회, 의미 만료/UNKNOWN 미재시도, 실제 인증 거절·TLS 거절과 시효 거절의 진단 구분을 검증한다. 관련 기존 회귀와 별도 AI 검토를 수행한다. 오프라인 결과를 실제 사용자 성공으로 기록하지 않는다.

쓰기 경로: `src/app/transparent/engine.py`, `server.py`, 필요한 `tools/hookgw_mcp.py`/진단 helper·관련 테스트, SPEC5/Jev 사용·내부 freshness 설명, 새 handoff/artifacts. 실제 gateway 설정 변경이 필요하면 근거와 최소 diff를 기록한다. wire 권한·정책의 범용 완화, 기존 DB/예산 초기화, 전역 config/auth/CA·개인 MCP/CLI 변경은 범위 밖이다.

## T-JEV-04: 실제 Jev를 쓸 수 있는 준비를 함께 끝내기

이는 **실제 모델 호출 전 준비**이며 T-JEV-03 성공을 무조건 선행조건으로 삼지 않는다. 사용자에게 TypeSafe 키가 있고 값은 전달받지 않는다. 현재 `-JevRules`는 코드 규칙 전용이며 preflight도 키/원장이 없는 상태를 요구하므로, 단순 key mount만으로 live가 준비됐다고 보고하지 않는다.

- 기존 규칙 전용 실행을 보존하면서 별도 명시 opt-in 평가 구성을 준비한다. 숨긴 사용자 입력/보호된 ignored 파일과 역할별 RO key/config, 별도 RW 원장, 최소 ACL/권한을 사용한다. 키를 명령 인자·프롬프트·로그에 넣거나 자동 수집하지 않는다. 준비/preflight는 모델 요청0이며 실제 endpoint/model 접근은 NOT_VERIFIED다.
- 규칙-only와 실제 TypeSafe 평가 readiness를 분리하고 기존 GPT fallback/모델 alias/자동 retry는 금지한다. endpoint/model은 기존 검토한 고정 후보를 사용하고 실제 공식 응답 형식/접근 호환성은 사용자 제한 시험에서 확인한다. 기본 enabled:false를 유지한다.
- 우선 합성 한국어 정상 데이터 활용1후보/외부 추가 지시1후보의 **최대 A/B4 API 요청** 경로를 준비한다. 기존 정답/라벨을 모델 state로 보내지 않는다. 정확한 전송자료와 고정 질문을 사용자 검토 가능하게 고정한다. 이2후보는 연결/관측 smoke이며 전체 정확도·보류 평가 성공으로 부르지 않는다. 안전한 read/hard deny는 모델0을 유지한다.
- 요청4회 상한과 기존 제공자 원장의 요청당64,000 입력 토큰 보수 예약에 맞춘 총256,000 예약 상한을 **제안값**으로 표시한다. 이는 실제 토큰 소비/금액이 아니다. 실제 공식 가격·사용량 과금 기준으로 가능한 금액 상한과 불확실성을 설명하고, 자료/최종 한도/사용자 실행 지시가 확정되기 전 활성화·호출하지 않는다. 실제 호출 후 API 실패/해석 실패를 공격 차단 PASS로 집계하지 않는다. 기존 OpenAI22/24와 새 원장을 혼합/환불/초기화하지 않는다.
- 사용자 key 준비→0요청 preflight→명시적 제한 평가→안전 결과/사용량 수집까지 정확한 명령을 검증해 인계한다. 실제 CLI·의미 쓰기·실파일 효과의 통합은 별도 범위로 표시한다. 동결된 calibration/holdout 전체를 자동 호출하지 않는다.

쓰기 경로: 필요한 별도 Jev 사용자 준비/평가 helper·fixture 기반 테스트, 비활성 Compose override 예제/필요한 별도 opt-in 구성, `docs/mvp/09_rules_first_jev.md`와 평가 절차·해당 handoff/artifacts. 기존 질문/임계치·동결 holdout을 결과에 맞춰 변경하지 않는다. 관리 계획/작업 장부·전역 DONE은 관리가 갱신한다.

## 인계

새 run의 RESULT와 별도 REVIEW, 기준선/최종 manifest·실제 진단→수정→재진단·효과/원장 보존 증거를 제출한다. 가이드 관련 원문 페이지→통제→코드→시험을 연결한다. 개발 모델 호출0·사용자 실제 시험 NOT_RUN·남은 보호 범위를 구분한다. 사용자에게 승인 변경/재시험이 더 필요한 경우 기존 동의가 한 번의 시험에 한정됐음을 기록하고 **다음 구체 절차가 준비된 뒤 관리에 인계**한다. 관리 동의 없이 추가 paid CLI를 자동 실행하지 않는다.
