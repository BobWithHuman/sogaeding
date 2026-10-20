# T-JEV-07 사용자 직접 실행 절차

준비된 run은 `followup-response-v2` 한 개다. 키를 다시 입력/복사하지 않는다. 기존 runtime-jev-eval의 키 경로를 RO로 참조하고 원계획/실패/원장을 보존한다. 개발 AI는 실제 evaluate를 실행하지 않았다.

## 먼저 확인 (모델0)

```powershell
cd C:\sogaeding
.\scripts\jev_eval.ps1 -Mode inspect -RunId followup-response-v2
.\scripts\jev_eval.ps1 -Mode preflight -RunId followup-response-v2
.\scripts\jev_eval.ps1 -Mode collect -RunId followup-response-v2
```

inspect의 manifest SHA는 아래 실행 명령의64자리 값과 같아야 한다. endpoint는 `https://api.typesafe.ai/v1/systemone`, model은 `jev-1.13.0`이다. exact_data_and_questions에서 S01 정상 배포 사실 요약 후보와 S02 외부 지시를 따른 거짓 보고 후보, 분리된 A/B state·고정 질문을 직접 확인한다. local 기대값은 wire에 보내지 않는다. 실제 파일쓰기/도구 실행은 없다. 프로젝트 소스·PDF·실제 비밀을 모델 문맥에 넣지 않는다.

preflight는 ready_for_user_opt_in:true/default_enabled:false/paid_requests:0/actual_key_read:false/provider_access:NOT_VERIFIED_NO_REQUEST여야 한다. 이는 인증·모델 접근 성공이 아니다. collect는 준비 상태 NOT_STARTED/NOT_RUN이며 원장·결과·실행 선점이 없어야 한다. 이 값이 다르거나 source/image/parent가 바뀌었다면 실행하지 않고 해당 출력으로 검토한다. prepare/key/reset/manifest 재작성은 하지 않는다.

## 전송·한도 확인 후 사용자만 한 번 실행

새 run은 최대4요청/입력예약256000이다. 과거 실패1요청/64000을 포함한 누적최대5/320000이며 원계획 대비 추가1/64000이다. 원래 남은3/192000을 새4회 승인으로 재사용하지 않는다. 과거 사용량·실제 청구액은 UNKNOWN이다. 새 입력 예약 산술액 USD0.010752(공개 단가 기준)는 실제 청구/세금 보증이 아니다. 아래 ConfirmSend와6개 한도는 **이 정확한 자료·목적지·새 한도 및 추가/누적 총량에 대한 사용자 선택**이다. 준비/키 보유는 실행 승인이 아니다.

준비된 manifest는 `91cd5d7772997b376aba2609b2fff4ffad14e70c51f2eeb6cd9f112d4f8a14ce`다. 아래는 실제 전송 명령이며 개발 AI는 실행하지 않았다. 위 자료·목적지·새/추가/누적 한도에 동의하여 직접 시험할 때 한 번만 사용한다.

```powershell
.\scripts\jev_eval.ps1 -Mode evaluate -RunId followup-response-v2 `
  -ConfirmSend `
  -ManifestSha256 '91cd5d7772997b376aba2609b2fff4ffad14e70c51f2eeb6cd9f112d4f8a14ce' `
  -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000 `
  -ApproveCumulativeRequestLimit 5 -ApproveCumulativeInputReservationLimit 320000 `
  -ApproveAdditionalRequestLimit 1 -ApproveAdditionalInputReservationLimit 64000
```

실행은 A→B 순서이고 첫 필수 오류 뒤 후속 view/case를 보내지 않는다. 실패·프로세스 중단/timeout/출력 유실 뒤에도 같은 명령을 다시 실행하지 않는다. 단회 선점 파일·원장·결과를 지우거나 새 run을 만들지 않는다.

## 실행 뒤 또는 오류 뒤 수집만

```powershell
.\scripts\jev_eval.ps1 -Mode collect -RunId followup-response-v2
```

execution_exit0과 semantic_summary를 구별한다. ANALYSIS_FAILED_PARTIAL/NOT_SCORED/NOT_ATTEMPTED는 공격 탐지 PASS가 아니다. ATTEMPT_CLAIMED_OR_INTERRUPTED/EXECUTION_STATUS_UNKNOWN이면 추가 provider 여부도 미확정이므로 재실행하지 않는다. 유효 usage 일부만 관측되면 총청구 UNKNOWN을 유지한다. 실제 정상/공격 관측도 단독 합성 연결 smoke일 뿐 일반 Codex IPI 보호 완료가 아니다.

원래 실패 기록은 다음 명령으로 별도 보존 조회한다.

```powershell
.\scripts\jev_eval.ps1 -Mode collect
```

신뢰된 helper 실행과 동일 OS 사용자 경계가 전제다. helper 자체 AI 편집 방어, 일반 native/hook 장애·전체 공급망 검증은 남아 있다.
