# 승인 대기 수리 인계와 Jev 준비 오류 검토

2026-10-16 관리 검토. T-JEV-03/04 작성자 RESULT와 별도 AI REVIEW를 읽었다. 별도 읽기 전용 보조가 최종200파일을 현재 SHA와 대조해 누락/불일치0, fingerprint `5e023a303a2e48569efbc326c49172972cd4a0054b6103bc3c36a085820b395b` 일치를 확인했다. 작성자346회귀/실제gateway45, 별도223와 helper105는 겹치는 저장 증거이며 이번 관리가 재실행/합산하지 않았다.

공개 읽기만 현행 통제를 재검사하는 단회 전달과 고정 사유 진단, 별도 disabled Jev 평가 helper의 **구현·오프라인 준비 범위**를 T-JEV-03/04로 수용한다. 실제 사용자 지연 승인 읽기·실제 Jev 응답/접근/정확도는 미검증이다. 원 증거/기존 READY·UNKNOWN/OpenAI22/24 보존은 인계 당시 근거이며 전체 보안 또는 MVP 완료로 확대하지 않는다.

## 사용자 prepare 실패의 현재 관측

사용자 실행은 키 입력 전에 공통 오류로 중단됐다. 현재 정확한 저장 위치를 읽기 전용으로 확인했다.

- 실제 Git worktree이며 정확한 key 경로가 artifacts/ ignore 규칙에 해당한다. 로컬 Git은 프로젝트 밖의 설치 실행 파일이다.
- `artifacts/runtime-jev-eval`과 plan/manifest·requests·disabled policy가 이미 있다. 여섯 저장 폴더의 ACL은 보호돼 있고 현재 사용자/SYSTEM 외 추가 Allow는0이다.
- key·provider ledger·authorized-run·result는 없다. 키 본문은 읽지 않았다.
- 현재 소스의 정식 `tools/jev_eval.py storage-check`가 **exit0 / ignored_owner_protected:true / paid_requests:0**으로 통과했다. 이 명령은 계획/현재 소스 결합·Gitignore·ACL 검사이며 Docker/모델 실행과 키 입력이 아니다.

따라서 현재는 **기존 준비를 보존하고 `-Mode key`로 이어갈 수 있다.** `prepare`는 폴더가 이미 있으면 거절하므로 반복·삭제·초기화로 해결하지 않는다. 최초 실패의 구체 단계는 기록되지 않아 확정할 수 없다. 초기 마지막 검사 실패 또는 이미 준비된 뒤 재prepare 거절이 동일 공통 오류로 보일 수 있다. 현재 ACL 통과를 과거 실패 원인이 ACL이었다는 증거로 사용하지 않는다.

단위시험의 prepared fixture는 private_ready를 성공으로 대체하고 실제 명령 검증은 별도 Git 복사본이었다. 이것은 실제 사용자 저장소에서 모든 준비 상황이 검증됐다는 근거가 아니다. 일반적인 'ignored storage failed'와 'paid_call_status'는 키 입력 전 실패의 정확한 원인을 설명하지 못한다. 향후 안전한 고정 단계별 코드·이미 준비됐고 키만 없는 경우의 이어가기 안내를 보완할 수 있으나, **현재 사용자의 안전한 다음 단계를 막는 새 구현 선행조건으로 추가하지 않는다.**

근거: [관리 저장 관측](../../../artifacts/management-jev-storage-20261016/observation.json).

## 다음 사용자 행동

```powershell
cd C:\sogaeding
.\scripts\jev_eval.ps1 -Mode key
.\scripts\jev_eval.ps1 -Mode inspect
.\scripts\jev_eval.ps1 -Mode preflight
```

첫 명령의 숨긴 입력에 사용자가 TypeSafe 키를 직접 넣는다. 키를 채팅에 보내지 않는다. 이 과정은 enabled:false를 유지하고 모델을 호출하지 않는다. key_stored:true와 preflight의 ready_for_user_opt_in:true/default_enabled:false/live_authorized:false/모델 접근 미검증을 확인한다. 실패 시 원문 키/토큰 없이 고정 오류와 해당 단계만 인계한다. 실제 evaluate/추가 유료 CLI는 아직 실행하지 않는다. 정확한 전송 자료·고정 모델/질문·최종 한도와 명시 사용자 실행이 다음 게이트다.
