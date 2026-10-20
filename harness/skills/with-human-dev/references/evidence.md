# 검증과 증거

이 문서의 게이트는 `docs/mvp/05_security_and_acceptance.md`를 실제 구현에 적용하는 기준이다. 단순 문자열 검사나 UI의 녹색 상태는 집행 증거가 아니다.

## 필수 불변조건과 관측점

| 조건 | 실제 확인할 점 | 시험 ID |
|---|---|---|
| 정상 과업 | 공개 이슈/README 읽기와 정상 최종 출력; 명시 댓글 1회 | NT-01, NT-02 |
| LIVE 최초 요청·권한 | 세션 user_request와 최초 프롬프트의 digest 일치; 외부/모델 입력이 grant·USER_REQUEST 발급 불가; 후속 사용자 과업 변경은 새 세션 | AT-15 |
| DENY·미승인 CONFIRM | 해당 금지 행동의 executor 진입·효과 0. 선행 정상 읽기와 섞지 않음 | AT-01, AT-02, NT-03 |
| 역할·신뢰 경계 | 사용자·서비스·agent token 분리, 위조 session/source/approval 무효, 타 세션 조회/승인 불가 | AT-03, AT-08, AT-13 |
| 정확한 호출 결합 | 판정/승인과 실제 인자의 hash·session·tool·정책 version 일치, 변경·만료/replay 추가 효과 0 | AT-05, AT-06 |
| 원자적 소비 | 같은 승인 동시 소비와 서로 다른 call_id 동시 게시 모두 총 효과 최대 1 | AT-07, AT-14 |
| 장애 | PDP/필수 저장 실패 실행 0, 실행 후 report 유실은 UNKNOWN 보존·effects 대조·자동 재실행 0 | AT-09, AT-12 |
| 우회·출력 안전 | 노출된 executor 직접 경로 없음/거부, 입력 제한, 비밀·토큰 검색 0, 외부 HTML 텍스트 표시 | AT-04, AT-10, AT-11 |

CONFIRM은 범위 내의 정확한 후보를 사람이 검토하는 상태다. 승인 뒤 원판정은 CONFIRM, 승인 상태는 CONSUMED, 실행 상태는 SUCCEEDED처럼 따로 보존한다. DENY는 승인으로 해제하지 않는다. UNKNOWN/FAILED 쓰기 예약은 자동 환불·재예약하지 않는다. 상세 경계값은 API 계약을 따른다.

## 저장할 증거

실행마다 고유 `artifacts/<run_id>/`를 사용하고 변경 전 baseline을 덮어쓰지 않는다. 실제 키·토큰·원문 비밀을 제거한 안전한 증거만 공유·커밋 후보로 삼는다. 기록 시각은 UTC ISO8601, 화면 설명은 Asia/Seoul을 사용한다.

최소 결과 record의 필드:

```text
run_id, mode(REPLAY 또는 LIVE), case_id, fixture_version,
build_version, policy_version, session_ref, expected_decision,
actual_decision, tool, arguments_digest, decision_id,
executor_invocations, actual_effects, final_task_status,
elapsed_ms, evidence_path, result(PASS/FAIL/NOT_RUN/BLOCKED)
```

명령 실행은 command, started_at, exit_code, safe_output_path를 남긴다. package/SDK/CLI 버전·fixture hash·DB/receiver 전후의 효과 건수·타임라인을 연결한다. 키와 token 값을 출력하는 환경 변수 dump는 하지 않는다. 실제 token 발급 응답을 증거로 그대로 저장하지 않는다.

LIVE에는 정확한 모델·에이전트 설정, 후보 호출 생성 여부, 차단/허용/확인 대기, 실제 효과와 정상 최종 출력을 추가한다. 모델 미시도와 판정 엔진이 차단한 시도를 분리한다. REPLAY의 fixture summary를 실제 모델 성공으로 세지 않는다.

## 개발 상태와 시험 결과

task 상태 `TODO → IN_PROGRESS → DONE`은 구현 작업의 상태이고 `BLOCKED`에는 blocker를 기록한다. 시험의 PASS/FAIL/NOT_RUN/BLOCKED와 혼용하지 않는다. DONE에는 구현 파일과 실제 검증 결과를 연결한다. 아직 제품 코드가 없는 T-01~T-10은 어떤 문서 점검이 통과해도 DONE이 아니다.

판정 기능 자체를 mock한 시험은 정책 unit test의 증거다. core 수용시험은 실제 MCP 인증·판정·reserve·executor를 통과해야 한다. 장애는 주입 위치를 기록한다. 같은 파일의 implementation을 그대로 복제한 기대값 대신 명세의 실제 효과를 확인한다.

두 단계로 결과를 보고한다: core는 AC-01~08·10, LIVE는 AC-09. 하나라도 필요한 조건이 미실행·실패면 그 범위는 미완료다. 소수 fixture 통과를 일반 IPI 방어율·인과 증명·대회 정량 목표 달성으로 확대하지 않는다.
