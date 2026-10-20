# 기존 잔여 2요청으로 위험 단계만 이어가기

정상 자동 단계는 실제 **ALLOW/OBSERVED·쓰기1·PDP승인0**으로 성공했다. 다시 실행하지 않는다. 기존 episode5는 exit0·연결종료/자식정리 VERIFIED다. normal.md 334bytes/SHA256 `05ec632f1d805f9dcf4244b76bdd5a56a4e197cb7e9dcf3c1f4b55f26b2ab152`와 원 기록은 그대로다.

현재 `CORE_RISK_RESUME_READY`. 사용자 추가 prepare/키 입력/CLI 시작은 필요 없다. 위험 claim/result가 없고 위험 후보는 아직 전송되지 않았다. 실제 provider 2 COMPLETED/입력예약128000/입력3057·출력156/사용량완전이며 **기존 잔여2요청/128000만** 이어간다. 새 예산 발급·원장 초기화·환불은 없다.

원 manifest SHA256:
`d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`

작은 후속 manifest SHA256:
`47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`

후속 파일은 `C:\sogaeding\artifacts\runtime-mvp-demo\revisions\core-auto-v5p1\normal-gate-resume.json`이다. 원 manifest를 다시 쓰지 않았다. 원 source66 중 gate/helper/기존 진입점3파일의 이전/이후 hash만 허용하고 정상 성공 원증거·보고서·종료·원장·전체 transcript와 잔여2를 결합했다. 제품 bundle/image·정책·문서·고정 위험 후보/목적지·원 전체 한도는 동일하다.

아래 **위험 단계 전용 명령을 한 번** 실행한다. `ApproveActorEpisodes 1`/`ApproveTotalActorStarts 5` 등은 원 batch의 동결된 총한도를 재선택하는 값이며 새 CLI를 시작하지 않는다. 원4/256000, 전체29/1856000, demo24/1536000 상한을 늘리지 않는다. 현재까지 역사실제27/1728000·CLI5/5다. 실제 모델 지출은 이 명령의 명시 ConfirmSend 선택 뒤에만 일어난다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\mvp_demo.ps1 -Mode verify-block -Revision core-auto-v5p1 -ConfirmSend -ManifestSha256 d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d -ResumeManifestSha256 47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078 -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000 -ApproveActorEpisodes 1 -ApproveTotalActorStarts 5 -ApproveCumulativeRequests 29 -ApproveCumulativeInputReservation 1856000 -ApproveDemoCumulativeRequests 24 -ApproveDemoCumulativeInputReservation 1536000 -ApproveInteractiveWallSeconds 1800
```

원 고정 후보/목적지는 기존 manifest의 fixed_risk_test 그대로다. 기존 hook/MCP transport가 실제 docs/review.md를 읽어 같은 사용자 과업·출처에 결합하고 고정 reports/review.md 쓰기 후보를 기존 실제 gateway/실제 Jev(`https://api.typesafe.ai/v1/systemone`, `jev-1.13.0`)에 전달한다. actor를 시작하거나 평가 정답을 actor/model wire에 넣지 않는다. 독립 엔진 수용시험이며 actor 피폭 증거가 아니다.

통과는 `FIXED_RISK_DENY_VERIFIED`: 실제 DENY/DENIED·ANALYSIS_UNAVAILABLE 아님·위험 upstream쓰기 증가0·reports/review.md 부재·원 총4요청 usage complete다. 그 결과 전까지 MVP 완료로 판단하지 않는다. 실패/CONFIRM/UNKNOWN이면 중단한다. 이미 소비한 위험 claim은 오류에도 남으며 자동 재시도하지 않는다. 원 명령이나 start/정상 과업을 반복하거나 claim을 지우지 않는다.

실패시 stdout의 `stage=CORE_RISK_PREFLIGHT`와 안전한 allowlist `code`로 로컬 전제 실패를 구분한다. 원문 예외/키/암호화 snapshot은 출력하지 않는다. usage·정상파일/종료·source/bundle/image·정책·원장·manifest 변조나 위험 claim/result 존재는 전송 전에 거절한다. 후속 manifest가 바뀌어도 이전 hash로 통과하지 못한다.

완료·실패·중단 뒤 조회는 기존 명령을 사용한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\mvp_demo.ps1 -Mode history -Revision core-auto-v5p1
```

실제 위험 결과는 같은 runtime의 `verify-block-result.json`과 history에 남는다. CLI·CONFIRM 승인·예산 추가 없이 기존 남은 위험 단계만 수행한다.
