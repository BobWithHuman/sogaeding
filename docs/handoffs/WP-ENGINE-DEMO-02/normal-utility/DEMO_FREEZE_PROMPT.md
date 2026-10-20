# T-MVP-DEMO-FINAL-01: 실제 결과 고정과 지원된 CLI 시연 인계

2026-10-20 관리 배정. QueryRouting 정상3개 실모델 수용시험을 통과했다. benchmark를 다시 돌리거나 추가 튜닝하는 단계가 아니다. 기존 제품의 지원된 CLI 흐름과 결과를 사용자가 재현할 절차로 정리한다. 개발 중 유료 provider 호출·실제 actor 시작·예산 증액은 하지 않는다.

## 확인된 사실

안전한 원증거 요약은 `artifacts/20261020-query-routing/actual-user-results.json`이다. 원 run은 `artifacts/20261018-dtap-os100/user-query-utility`, manifest `4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770`이다.

- 실제 GPT-5.2 snapshot으로 benign2/3/4 모두 task_success=true·accepted3·PDP 승인0·CONFIRM0·UNKNOWN0·close 관측이다.
- 실제 업무 호출은4개: directory_tree/check_file_exists/get_file_info의 CODE_ALLOW3, 추가 list_directory의 SEMANTIC1. 후자는 A/B를 호출하여 **이번 실제 Jev2회**가 있었다. 고정 fixture의 전체 Jev0을 실모델 전체 결과로 복사하지 않는다.
- 이번 명목비용0.072174 USD(GPT0.071686/Jev0.000488), 누적4.190921, 현재누적상한5.089294, 해당잔여0.898373 USD, 미해결 hold0이다. 역사 budget_rejections는 이번 stop이 아니고 현재 stop은null이다. 원 총상한7의 미배정 여유를 자동 사용하지 않는다.
- 이는3개 정확한 검토 요청과 제한된 metadata/tree 권한의 utility 수용이다. 일반 자연어 전체의 권한 발급, 모든 native 도구/모든 IPI, 새 정책의 전체 공격 방어율은 미완료다. 과거6pair off공격성공6/on0과 코드28/의미1 DENY는 이전 정책/run의 별도 증거다.

## 이번 순서

1. with-human-dev·AGENTS·이 작업서와 현재 지원된 CLI 진입점/결합 함수만 먼저 읽는다. 현재 결과와 관련된 이전 read_file/write_file 정상 자동·실제 위험 DENY 증거는 필요한 부분만 재사용한다. 계획/PDF/실패로그 전체 통독이나 통과한 benchmark72/47/83 재실행은 하지 않는다.
2. **DTAP 전용 policy/runtime와 제품 CLI 정책의 적용 관계를 먼저 명시한다.** QueryRouting이 Codex의 모든 도구에 자동 적용됐다고 가정하지 않는다. 기존 hooks·agentgateway·등록 파일 MCP·launcher·viewer를 재사용하고, 지원 도구·실제 정책/revision·사용자 turn/출처/호출 결합을 짧게 정리한다. benchmark 코드를 제품에 통째로 이식하거나 새 native shell 지원을 이번 선행조건으로 추가하지 않는다.
3. 사용자 실행 절차는 PowerShell 연결→직접 codex→정상 과업→위험 호출/엔진 거부 확인→history/종료로 최소화한다. 정상과 위험 판정은 같은 시연 revision에 연결하고 실제 효과·source/정책 hash를 확인한다. actor가 공격을 무시하면 공격 미시도로 표시한다. 엔진 시험기의 고정 위험 후보를 사용하면 피해 actor가 실제 피폭한 것처럼 표시하지 않는다. 서로 다른 정책의 과거 결과를 새 단일 실시간 실행처럼 합치지 않는다.
4. 새 모델 호출 없이 현재 진입점의 연결·MCP 등록/차단·turn/Pre/Post·history·종료를 변경 영향에 맞게 확인한다. 과거의 유효한 실제 증거를 재사용한 부분, 새 무모델 연결 부분, 아직 실모델 미실행인 부분을 구별한다. 필요한 PKI/검사/단회 실행본은 기존 실패 기록을 덮지 않는 별도 revision으로 준비한다. 개인 전역 설정·로그인·검토 범위 밖 hook 신뢰를 변경하지 않는다.
5. 추가 list_directory의 모델0 지원은 기능 한계로 기록한다. 현재3개 정상 성공을 취소하고 전체 benchmark를 다시 시작하지 않는다. 같은 요청의 정상 metadata 동작을 추가 검토하는 작은 변경이 정말 필요하면 관련 경계만 검증하고, 추가 유료 DTAP 반복을 완료 조건으로 만들지 않는다.
6. 대시보드는 별도 팀원 소유다. 요청·관측 출처·후보 도구·판정/사유·승인·실제 실행/UNKNOWN·history를 연결할 기존 API/이벤트/안전한 예시만 짧게 인계한다. teammate 파일/화면을 수정하지 않으며 DTAP 결과/벤치마크 화면을 제품에 추가하지 않는다. 실제 token/키/비밀자료를 예시로 주지 않는다.

## 한도와 완료 조건

원 결과/모든 원장·UNKNOWN·키·동결 source·서비스를 보존한다. 종료된 QueryRouting run은 재실행하지 않는다. 새로운 사용자 실행이 실제로 필요한 경우에만, 현재 누적4.190921/한도5.089294/잔여0.898373과 미해결 최대hold를 반영한 단회 준비 명령을 인계한다. 개발 중 실행하지 않는다. CLI의 인증/비용 경로가 benchmark broker와 다르면 이를 명확히 설명하고 그 비용이 동일 상한으로 통제된다고 주장하지 않는다. API키·토큰은 출력/기록하지 않는다.

기본은 구현 통합1개, 변경 관련 확인, 최종 좁은 통합1회, 별도 검토1회다. 코드가 바뀌지 않은 문서/증거 고정에 불필요한 제품 시험을 추가하지 않는다. 적용 P0·기존 GUIDE 근거와 실제 지원 경로의 필수 통제는 유지한다.

쓰기 범위는 필요한 기존 시연 연결/검증 코드·관련 tests·새 안전 artifacts와 이 폴더의 RESULT/USER_RUN/REVIEW 및 필요한 짧은 팀원 API 인계뿐이다. 공통 작성자1개. docs/plans·harness·AGENTS는 관리만 변경한다.

최종 인계에는 **지원 범위·한 줄 연결/실행 절차·정상/위험 입력·history·종료·실제 비용/호출 구분·남은 제한**을 담는다. 제출 전 전수 보강과 일반 native 개발 완료를 좁은 시연 인계 완료로 대체하지 않는다. AgentDojo/추가 모델 탐색/전체100개 재실행은 이번 범위 밖이다.
