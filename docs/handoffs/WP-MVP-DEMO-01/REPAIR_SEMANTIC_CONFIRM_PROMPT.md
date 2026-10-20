# WP-MVP-DEMO-01 계속: 정상 의미 판정과 CONFIRM의 실제 완료 경로

with-human-dev, 최신 AGENTS/control_state, `docs/plans/reviews/WP-MVP-DEMO-01_20261016_semantic_confirm_management.md`, `artifacts/management-mvp-demo-confirm-20261016/observation.json`, host-wait 인계를 읽고 같은 작업팩을 이어서 수행한다. 관리 정본(plans/harness/AGENTS)은 수정하지 않는다. 기존 구현 배정 경로 및 필요한 내부 질문/정책/관측 계약·예외 승인/오류 코드·관련 테스트 개정은 아래 범위로 명시 위임한다. outward 권한·원자 예약/단회 소비·TLS·출처 원문 binding·UNKNOWN 경계는 유지하고 계약/사용법을 같은 수정으로 맞춘다.

현재 실증: 공개 읽기1 OBSERVED, 정상 쓰기2 CONFIRM/SEMANTIC_UNCERTAIN, 실제 Jev A/B4요청 COMPLETED(입력6804/출력924), 보고서 없음, 후속 읽기 UNKNOWN1. provider/key/response 오류로 진단하지 않는다. demo extAuthz가 CONFIRM을 `DEMO_CONFIRM_NOT_DISPATCHED`로 종료하며 현재 demo에는 실제 승인/resume가 없다. 호스트 Allow와 PDP CONFIRM은 별개다.

## 한 번에 고칠 제품 흐름

1. **질문/정책 합성의 불필요한 미확정 수리.** 기존 저장 typed 응답으로 모델0 재현한다. task_relation의 DIRECT와 DATA_DEPENDENT는 겹치며 최종 정책상 같은 정상 계열이다. A/B가 둘 사이에 .85/.15 또는 .70/.29를 나눈 것과 OUTSIDE/UNCERTAIN 위험 판단을 구별하도록 배타적 질문을 설계한다. 현재 confidence를 임의 승격하거나 과거 확률을 더해 모델이 높은 확신을 냈다고 재기록하지 않는다. 임계치 .90를 이번 한 건에 맞춰 내리지 않는다. 새 질문/정책 버전과 적용 범위를 명시하고 실제 새 모델 성능은 미검증으로 남긴다.
2. **출처 관측의 역할 구분.** USER가 요청한 행동/대상, 외부가 공급한 payload/옵션/추가 행동, 생성된 표현을 분리한다. 모든 action/target에 외부 링크를 강요하지 않는다. 첫 B에서 TASK_DATA/DATA/payload는 기준 통과지만 external_evidence/action link가 기준 미달한 원인도 처리한다. 서버 catalog membership/정확 span binding은 규칙으로 검증하고, 관측 연관성을 실행 권한이나 인과 증명으로 쓰지 않는다. 외부가 target/options/행동을 바꾸는 공격과 USER 요청 안에서 사실을 사용하는 정상을 일반화된 반례로 나눈다. case ID/경로/문장 정답 하드코딩과 단순 문자열 일치에 의한 자동 권한 부여는 금지한다.
3. **예외 CONFIRM을 실제로 처리.** 진짜 미확정이면 같은 사용자가 정확한 candidate·근거·의미 불확실성을 보고 승인/거절할 최소 로컬 흐름을 구현한다. 기존 human `/approval` 통제를 재사용하거나 최소 trusted CLI/viewer에 연결한다. 작업별 세션 사전 등록/토큰 복사나 큰 새 웹앱은 만들지 않는다. 호스트 승인을 PDP 승인으로 간주하지 않으며 actor/MCP token은 승인 권한을 갖지 않는다. 단회 승인은 정확 session/turn/tool/args/policy/source·intent에 묶고, 거절/DENY/만료/변조/종료 연결에서는 효과0이다. 승인 후 동일 의도를 gateway에서 한 번만 재개하고 freshness·현재 binding·원자 예약을 검사한다. 추가 Jev 요청이나 actor 새 도구 호출에 의존해 승인 루프를 만들지 않는다. 정상 쓰기를 모두 CONFIRM으로 돌리는 제품으로 바꾸지 않는다.
4. **같은 미해결 후보의 중복 유료 분석 방지.** 현재 actor가 동일 내용/대상을 새 call ID로 재시도해 A/B가 또 실행됐다. 같은 connection/session/turn/정책/출처 snapshot/정규화 인자에 미해결 CONFIRM이 있으면 기존 후보를 안내하고 provider 재호출/중복 집행을 막는다. 다른 인자로 바꿔 기존 승인을 재사용하지 못하게 한다. 분석 실패/UNKNOWN 뒤 자동 쓰기 재시도·환불 금지도 유지한다. MCP 결과는 실제 존재하는 확인 경로 또는 명시적 중단을 안내하고, 없는 UI를 찾도록 유도하지 않는다.
5. **읽기 실패의 안전한 의미.** 뒤따른 보고서 읽기는 ALLOW 뒤 UNKNOWN/HTTP_REJECTION_UNCLASSIFIED다. 현재 포괄403 처리에서 어떤 예외가 났는지 과거 사실로 확정하지 않는다. 새 경로에서 effect 전 확정 가능한 파일 부재 등은 비민감 typed 업무 오류/관측 실패로 구별하고, transport 결과 유실/실제 실행 불명만 UNKNOWN으로 유지한다. 예외 원문/비밀 경로·내부 stack을 노출하지 않는다. 이미 저장된 UNKNOWN을 소급 해제하지 않는다.

## 검증과 인계

기존 실제 typed 응답을 그대로 입력하는 모델0 policy replay에서 최초 CONFIRM 원인을 재현한다. 서로 다른 정상·공격·정당한 외부 안내·인용/금지·다중 출처·명시 사용자 대상·외부 target/options 변경·낮은 확신 반례를 유지한다. 새로운 질문에는 새로운 가짜 typed 응답을 명확히 구별하고 과거 모델 출력으로 가장하지 않는다. 실제 Jev 정확도나 .90 보정 완료를 주장하지 않는다.

가짜 provider/로컬 actor+실제 pinned gateway에서 정상 자동 보고서 쓰기, 진짜 uncertain→사용자 승인/거절→동일 인자 단회 실행, 승인 경쟁/변조/만료/close, actor 새 call ID 중복에도 provider 증가0·효과 중복0, 파일 부재/진짜 응답 유실을 검증한다. 사용자 손으로 제어 가능한 승인 경로와 화면을 별도 AI가 실제 사용해 확인한다. 기존 중요 회귀와 필수 PDF→코드→증거 연결도 보완한다.

현재 CLI 시작 예약은 **2/2 사용**, 새 provider는 **4/8 사용**이다. 사용자 CLI가 아직 열려 있으면 관리 확인이나 단순 오류 조회를 이유로 추가 모델 작업을 넣지 않는다. 개발 AI는 사용자 프로세스를 임의 종료하지 않고 실제 actor/Jev 호출0을 유지한다. 기존 키/manifest/두 실패·두 CONFIRM/UNKNOWN/원장/예약을 보존한다. 새 start를 몰래 발급하거나 숫자를 초기화하지 않는다. 필요한 후속 시작 제안은 기존 원장 잔여와 누적 한도를 보존한 최소 정상/공격 시연으로 구체화하고, 최종 USER_RUN에서 자료/추가 시작 수/비용 한도를 명시해 사용자 직접 선택으로 남긴다.

새 RESULT/REVIEW/USER_RUN에 실제 해결한 흐름·모델0 재현·효과·안전 진단·보존·정확한 최소 사용자 명령을 한 번에 인계한다. API 연결 재준비/계획 생성만 반복하지 않는다. 실제 정상 자동 완료/실제 위험 후보 차단은 사용자 LIVE 확인 전 미완료다.
