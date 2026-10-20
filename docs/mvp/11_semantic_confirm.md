# 의미 범위·출처 슬롯과 실제 예외 승인

2026-10-17, WP-MVP-DEMO-01 REPAIR_SEMANTIC_CONFIRM. 이 문서는 명시 opt-in `semantic-confirm-1`의 내부 질문·승인·업무 오류 계약이다. SPEC5의 인증·등록 파일 MCP·정확 원문 ref·TLS·원자 예약·UNKNOWN/no-retry 경계를 유지한다. 기존 v2 실행 기록과 정책 코드는 보존하며 새 v3 관측으로 소급 변환하지 않는다.

## 질문과 정책

새 정책은 `hookgw-2026-10-17-jev-v3`, 질문 `jev-narrow-3`, 내부 출처 계약 `jev-slots-context-3`다. 임계치 .90과 provider/computed confidence의 최솟값은 그대로다. 실제 정확도로 보정된 임계치라는 뜻이 아니다.

A/B `task_relation`은 WITHIN_TASK / OUTSIDE_TASK / UNCERTAIN이다. 사용자 범위 안의 직접 생성과 외부 사실 활용을 서로 경쟁하는 정상 선택지로 만들지 않는다. 실제 USER 요청 span만 `task_evidence`가 될 수 있고 candidate/외부자료가 USER 권한을 자가 선언할 수 없다. A는 외부 사실 진위를 인증하지 않는다. 원 v2 DIRECT/DATA_DEPENDENT 분포를 더하거나 confidence를 높이지 않는다.

B는 적용되는 action/target/options/payload별 `basis_*`를 USER / TASK_DATA / GENERATED / ADDED_INSTRUCTION / UNCERTAIN으로 관측한다. USER는 실제 요청에서 정한 값, GENERATED는 외부 사실/권고를 나타내지 않는 독립 생성/위임 선택이다. 사실을 바꿔 쓴 표현은 TASK_DATA다. USER/GENERATED 슬롯에는 외부 link를 강요하지 않는다. TASK_DATA/ADDED_INSTRUCTION에는 해당 슬롯의 정확 source link와 실제 관련 context role이 필요하다. 서버 catalog membership/원문 슬라이스는 규칙으로 검증한다. 모델의 basis 라벨은 권한을 늘리지 않는다.

별개 슬롯의 불확실성이 이미 정확 근거와 높은 확신으로 확인된 추가 지시의 DENY를 CONFIRM으로 낮추지 않는다. instruction 자체의 근거나 역할이 미확정이면 CONFIRM을 유지한다. 정상 사실·인용/금지·정당한 외부 안내·다중 출처·외부 target/options 변경·낮은 확신을 각각 시험한다. 출처 연관성은 인과 증명이 아니다.

## 호스트 승인과 PDP 예외 승인

호스트 PreToolUse는 intent만 등록한다. 호스트 도구 승인을 거친 실제 MCP 요청에서 private gateway extAuthz가 단회 의미 판정을 한다. 자동 ALLOW는 바로 기존30초 freshness/예약을 거쳐 실행한다. DENY는 예외 승인으로 해제할 수 없다. 진짜 CONFIRM만 별도 사용자 터미널에서 검토한다.

| API | 인증 | 고정 계약 |
|---|---|---|
| GET `/demo/pending` | HUMAN | `{version:'demo-confirm-1',pending:[{call,approval_binding,candidate,request,source_excerpts,uncertainty,expires_at}],truncated}`. 최대8개·전체120k·정확 후보와 서버 USER 요청·bounded 근거·typed 불확실성 |
| POST `/approval` | HUMAN | demo는 `{call,approve:boolean,approval_binding}`. 기존 일반 경로의 별도 계약 유지. actor/MCP/machine credential로 승인 불가 |
| POST `/demo/wait` | machine + 정확 connection | `{connection,tool,args}` → `{status,pending_ref,expires_at,resume_allowed}`. status는 PENDING/APPROVED/REJECTED/EXPIRED/STALE/CONSUMED/NOT_FOUND |

리뷰 유효시간600초 안에 사용자가 정확 후보를 승인하면 **새 인간 권한의30초**를 발급한다. 원 analysis timestamp·decision CONFIRM·reasons는 변경하지 않는다. 현재 connection/session/turn/인자·요청·source snapshot/grant/policy를 검증하고 정확 원 JSON-RPC(id/meta 포함)만 한 번 재개한다. 승인 소비와 실행 예약은 같은 transaction이다. 만료/변조/거절/close/DENY는 효과0, 이미 전달한 결과 유실은 UNKNOWN이다. 과거 새 RPC binding이 없는 demo CONFIRM은 소급 승인하지 않는다.

`tools/mvp_demo_mcp.py`가 같은 호출을 보류하고 별도 `scripts/mvp_confirm.ps1`을 안내한다. 신뢰된 사용자 터미널은 후보 번호와 정확 내용/근거를 보여준 뒤 approve/reject를 직접 입력받아 기존 human credential로 승인한다. credential은 actor에 전달하지 않는다. 승인 후 같은 RPC를 gateway에 한 번 재전송하며 새 Jev 요청/actor 새 도구 호출에 의존하지 않는다. 거절·만료·장애에서는 명시적으로 중단한다. child에만 MCP `tool_timeout_sec=720`, 별도 PDP 리뷰600초·전체 CLI1800초를 적용한다. 전역 설정을 수정하지 않는다.

같은 connection/session/turn/정책/정규화 인자의 semantic write intent는 새 actor call ID로 다시 보내도 원 후보를 안내하고 provider 요청/중복 실행0이다. snapshot이 바뀌어 승인 불가능하면 존재하지 않는 확인 UI 대신 terminal 중단을 안내한다. 같은 turn의 거절·UNKNOWN·이미 실행한 쓰기를 새 분석으로 우회하지 않는다. 실제 새 USER turn만 새로운 위임을 만들 수 있다. 모델 없는 공개 읽기는 이 semantic write 중복 제한으로 일괄 차단하지 않는다.

## 읽기 오류와 UNKNOWN

유효한 ticket/예약 뒤 read open에서 확정한 파일 부재는 HTTP200 JSON-RPC result의 `isError:true`와 다음 고정 typed envelope로 반환한다.

```json
{"with_human_error":{"version":"file-error-1","code":"FILE_NOT_FOUND","operation":"READ","effect":"NO_WRITE"}}
```

이는 `structuredContent`이며 고정 안전 문장 `content`와 함께 정확 검증한다. 후보/파일 내용의 JSON 문자열은 이 envelope가 아니다. trusted transport 관측은 OBSERVED_ERROR로 기록하고 source를 만들지 않는다. 후속 PostToolUse도 기존 typed 오류를 UNKNOWN으로 바꾸지 않는다. 다른 오류/응답 유실·이미 UNKNOWN인 호출은 이 규칙으로 복구하거나 환불하지 않는다. 기존 실제 UNKNOWN의 원인을 소급 파일 부재라고 확정하지 않는다.

## 배포와 실증의 한계

기존 host-wait 실제 원장은 Jev4/8 사용·시작2/2다. 이번 개발은 모델0이며 현재 서비스/키/원장/실패/예약을 재시작·초기화하지 않는다. 새 bundle의 공개 후속 제안은 기존 예산을 공유하고, 사용자가 정확 manifest·추가 시작1/총3·기존 provider8/512000·CLI1800초를 명시 선택했을 때만 실행될 수 있다. 준비는 추가 시작/비용 승인이 아니다. 현재 두 CONFIRM은 사용자 CLI close 뒤 STALE/decision CONFIRM이 됐으며 그대로 보존한다.

기존 실응답의 enum·수치 policy replay와 새 가짜 typed 관측, 실제 gateway/파일 효과/인간 CLI 시험을 구분한다. 새 질문의 실제 Jev 성능·사용자 정상 자동 완료·위험 후보 실제 차단은 LIVE 이후 판단한다. 일반 native 개발·hook 사망·동일 OS/helper 변조·모든 IPI·전체 공급망/C/D·전체 MVP 완료는 남은 범위다.
