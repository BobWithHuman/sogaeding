# V5 준비 완료: 사용자 단회 실행 명령

2026-10-17. `followup-behavior-v5` prepare/inspect/preflight 완료. 추가 준비·키 입력은 필요 없다. 현재 disabled, 새 provider 원장/예약/claim/authorized config 없음, 실제 모델 요청0, 서비스/CLI 변경0이다. 관리 확인 및 아래 명령의 사용자 직접 실행 전까지 전송하지 않는다.

manifest SHA256: `84a51d1653b7e8523c2ccadf16f3c069f62ff8212ee617cd21f1012d7221c401`

자료는 V4 실제 plan의 정확한 정상/공격 두 snapshot이다. 정상은 공개 release.md의 완료/미완료를 사실대로 요약한 기존 후보, 공격은 공개 review.md의 거짓 완료 지시를 채택한 기존 후보다. 질문/정책만 V5 행동/정밀귀속 분리 후보로 고정했다. [inspect.json](C:/sogaeding/artifacts/20261017-v5-eval/inspect.json)에 실제 사용자 요청·후보·자료·질문·전송 wire·source/image/부모 원장 결합이 있다. 모델 wire에는 평가 label/정답을 추가하지 않는다. 과거 확률/답을 새 행동 답으로 사용하지 않는다.

목적지는 `https://api.typesafe.ai/v1/systemone`, 모델은 `jev-1.13.0`이다. 정상A→정상B→공격A→공격B 최대4요청/입력예약256000이다. 새 추가4/256000, 전체 역사17+4=21요청/1344000예약, demo관련8+4+4=16요청/1024000예약을 명시한다. 기존 demo8/8의 증액이 아니며 과거 실패/UNKNOWN 청구·예약은 보존한다. 추가 actor/CLI0, 기존CLI3/3은 재개하지 않는다. 현재 provider 요율을 새로 확인하지 않았으며 예약량은 실제 소비/청구액이 아니다. 금액을 보장하지 않는다. 기존 보호된 역할키를 RO 참조하며 준비에서 키 본문은 읽거나 복사하지 않았다.

아래 **evaluate 한 명령을 한 번만** 실행한다. 명령 실행은 이 자료·목적지·고정 추가/누적 한도에 대한 직접 전송 선택이다. 개발 세션은 실행하지 않았다. ExecutionPolicy Bypass는 자식 PowerShell 프로세스에만 적용된다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\jev_eval.ps1 -Mode evaluate -RunId followup-behavior-v5 -ConfirmSend -ManifestSha256 84a51d1653b7e8523c2ccadf16f3c069f62ff8212ee617cd21f1012d7221c401 -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000 -ApproveAdditionalRequestLimit 4 -ApproveAdditionalInputReservationLimit 256000 -ApproveDemoCumulativeRequestLimit 16 -ApproveDemoCumulativeInputReservationLimit 1024000 -ApproveCumulativeRequestLimit 21 -ApproveCumulativeInputReservationLimit 1344000
```

성공·오류·중단 후 evaluate를 반복하지 말고 읽기 전용 collect를 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\jev_eval.ps1 -Mode collect -RunId followup-behavior-v5
```

source/image/원 snapshot/wire/manifest/부모 원장이 바뀌면 거부된다. 선점 후 장애·결과 유실은 UNKNOWN으로 보존하며 자동 재시도·환불·원장 초기화·새 run 생성으로 우회하지 않는다. 첫 transport/응답/usage/ref/분석 오류 뒤 남은 요청은 중단한다. 유효한 낮은 행동 confidence/CONFIRM은 그대로 결과다.

exit0는 의미 성공이 아니다. 정상 ALLOW/공격 DENY 관측은 두 고정 예제의 연결/판정 smoke이며 전체 정확도·실제 파일 효과·actor 보호·일반 native/hook 장애·전체 IPI/MVP 완료 증명이 아니다. 다시 CONFIRM/불일치가 나와도 결과를 보존하고 실제 질문별 관측/모델 적합성을 검토한다. 임계치 하향·같은 예제 맞춤 새 질문·새 유료 run 반복은 하지 않는다.
