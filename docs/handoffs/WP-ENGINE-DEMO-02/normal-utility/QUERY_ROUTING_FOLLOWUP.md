# T-PDP-QUERY-01: 명확한 정상 조회의 Jev 생략과 최종 정상3개 준비

2026-10-18 관리 배정. 앞선 정상3개 준비본의 무모델47 PASS·별도 검토·고정 check FULL_READY3를 수용한다. 다만 **공개 조회의 작업 범위를 코드로 판정해 Jev를 생략하는 개선은 미포함**이다. 사용자와 논의한 선택적 분석 방향을 반영한 뒤 같은 정상3개를 한 번 실제 검증하도록 준비한다. 현재 잔여가0.970547 USD이므로 이전 준비본을 먼저 유료 실행하고 다시 평가하는 순서를 기본으로 삼지 않는다. 이 배정의 실제 provider 호출은0이며 실행 명령 선택은 사용자에게 남긴다.

## 최소 입력과 현재 원인

with-human-dev·AGENTS·이 작업서와 `runtime_policy.py:evaluate`, `demo_policy.py:route`, scope의 권한/forward proof, 기존 utility 준비 builder·관련 시험을 먼저 읽는다. 과거 전체 계획·PDF·로그/성공한47/83개 전체를 반복하지 않는다. 구현 통합1개→관련 시험→최종 관련 통합1회→별도 좁은 AI 검토1회다.

`demo_policy.route`의 모델0 공개 조회는 지금 **정확한 후보 전체 hash의 reviewed_operations**를 요구한다. `check_access`의 ALLOW만으로는 이 분기를 통과하지 않으므로 다른 정상 조회는 다시 A/B를 호출한다. 반대로 현재 task_scope의 넓은 ROOTS 전체를 사용자 업무 범위로 간주하여 모든 공개 QUERY를 허용해도 안 된다.

## 좁은 구현

1. **서버가 검토한 정상 조회 capability를 발급한다.** 신뢰된 사용자 원 요청/세션·principal·registry/schema·정확한 파일 또는 명시된 조회 root와 허용 operation·옵션/재귀 한도를 결합한다. 개별 후보 전체를 사전열거하는 방식은 피한다. 경로 언급만으로 파일 읽기/변경 권한을 추론하거나 외부 자료·actor 설명·모델 LEGITIMATE로 권한을 발급하지 않는다. 원 요청과 필요한 조회 동작의 검토 근거를 남긴다. 정책 코드는 task ID·benign label·judge 정답을 보지 않는다.
2. **현재 hard 정책과 실제 자원 검사를 먼저 수행한다.** 잘못된 identity·민감 자원·범위 밖·지원하지 않는 shell/side effect·메타데이터/출처·관측 장애는 기존 보호대로 닫는다. 조회 이름이나 PUBLIC 라벨만으로 권한/원문 무결성을 승격하지 않는다.
3. **정확히 capability 안이고 실제 공개/비민감·부작용 없는 typed QUERY만 CODE_ALLOW한다.** 공개 metadata/list/tree, 명시적으로 검토한 읽기에 적용할 수 있지만, 필요한 검사/실제 원 구현의 범위를 입증한 것만 활성화한다. 경로·모든 옵션·범위/깊이·대상 유형·owner/DAC·symlink·민감 descendant/한도 검사와 forward proof를 유지한다. ask_for_permission=True는 동의가 아니며, 새 코드 분기로 실제 동의 요구를 해제하지 않는다. 재귀 search_files의 기존 미검증 범위를 열지 않는다.
4. **내용 의미가 필요한 후보만 기존 Jev로 보낸다.** 요약 보고서·새 목적지/변형된 payload 등은 scope 권한 확인 후 현재 A업무범위/B행동적합성을 유지한다. `.50`/`.90`, 공식 confidence/질문 버전·위험 우선·CONFIRM과 UNKNOWN 규칙을 바꾸지 않는다. 이번에는 같은 질문의 전후 비교나 새로운 인과 판정기를 도입하지 않는다.
5. **보고에 실제 routing과 호출 수를 남긴다.** CODE_ALLOW/CODE_DENY/CONSENT_REQUIRED/SEMANTIC의 구분, 사유, 작업 권한 binding을 표시하고 provider 실제 Jev 요청과 대조한다. 차단을 분석 생략률의 성공으로만 세지 않는다. cap 불일치의 무리한 ALLOW나 임의 fallback을 만들지 않는다.

capability는 새 revision의 신뢰된 manifest/control 설정에서만 전달한다. 외부/actor에게 발급 API를 노출하지 않는다. 실제 후보/옵션 hash·세션·정책 결합과 기존 signed forward/단회 실행은 유지한다. 예전 grant/프로필/동결 run은 소급 변경하지 않는다.

## 검증과 실행 준비

- 같은 자원/도구/옵션의 정상 조회가 원 MCP 응답→Post/OBSERVED까지 이어지고 **Jev 호출0**임을 연결 검증한다. cap 없음/요청·schema·principal 변경, 범위 밖 공개 파일, 형제 파일, secret/private/symlink·옵션 주입/재귀 초과·probe 변경은 자동 허용되지 않아야 한다.
- 실제 요청상 내용을 판단해야 하는 쓰기는 Jev 경로를 유지한다. 임계치와 risk/CONFIRM/UNKNOWN, 분석/API/Post 장애·정확 승인/once·예산 관련 변경 경계만 검증한다. 원 MCP 업무 효과와 synthetic Jev 사용 여부를 구별한다.
- 이전 고정 utility 준비본 `user-normal-utility-acceptance`/manifest `b95c0992e67790350eb9e91e6512b1b3422da5b06ecc72ac661d463b3056a77a`는 아직 미시작이다. 덮어쓰거나 실행하지 않고 보존한다. 기존 초안과 실패 증거도 남긴다.
- 실제 마지막 지출 parent는 `user-engine-demo-02-deny-followup`/manifest `bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f`다. **누적4.118747/현재누적상한5.089294/잔여0.970547 USD, hold0/420예약**을 새 준비본에 정확히 계승한다. 원 총상한7의 미배정 여유를 전용하지 않는다. 모든 fork의 동시 사용·중복 지출을 막고 parent drift를 실행 전에 거부한다.
- 새 revision에도 동일한 원 정상 `benign/2→3→4`·engine-on만 준비한다. actor GPT-5.2/low와 원 prompt/catalog18/setup/image/judge/실제 Jev 설정을 유지한다. 첫 과업 최종 실패/CONFIRM/UNKNOWN/예산 소진 후 후속 전송 중단, 키 누락/검사 실패 시 claim 미소비, 재실행 금지와 정확한3개 scope/control 전달 검증을 유지한다.
- 기존 utility 성공 연결은 유효 범위에서 재사용하되 **새 cap/CODE_ALLOW가 실제 준비 설정에서 전달되어 모델0으로 원 MCP를 실행하는지**는 새 연결 증거가 필요하다. A/B 응답만 가짜로 ALLOW해 모델0 경로의 성공으로 표시하지 않는다.
- 새 고정 명령·manifest/source·원장·scope·이미지·PKI/network의 최종 무모델 check를 수행한다. 예상 평균가격으로 최대예약을 낮추거나3개 완주를 보장하지 않는다. 준비 상태가 PASS여도 실제 유료 run은 시작하지 않는다.

## 소유권/인계

관련 benchmark policy/scope/cap 발급·utility 준비/launcher/report 함수, 필요한 tests와 새 안전 artifacts만 변경한다. 새 전역 framework/공급자/AgentDojo/대시보드는 제외한다. 통합 작성자1개. GUIDE/P0 baseline은 재사용하고 이번 권한/입력/집행 변경의 관련 코드·시험만 연결한다. docs/plans·harness·AGENTS는 관리만 변경한다.

같은 폴더 RESULT/USER_RUN/REVIEW에 새 후보를 최상단으로 정리하고 이전 준비·검토/실패 이력은 보존한다. 최종 통합·별도 검토·무모델 check 뒤 한 번 실행할 명령과 collect/stop을 인계한다. **Jev0으로 진행한 정상 호출 수, 여전히 의미 분석/동의/미지원인 호출, 실제 모델 NOT_RUN 범위**를 분명히 보고한다. 전체 IPI/전체100/모든 native/인과 증명 완료를 주장하지 않는다.
