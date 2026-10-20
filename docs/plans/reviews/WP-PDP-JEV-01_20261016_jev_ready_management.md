# UTF-8 수리 수용·사용자 자료 확인·실제 Jev 제한 시험 준비

2026-10-16 관리 검토. 사용자 첨부 텍스트의 inspect JSON과 preflight, T-JEV-05 RESULT 및 별도 REVIEW, 현재201파일 manifest와 동결 합성 계획을 읽기 전용으로 대조했다. 실제 키 본문·API 인증·모델·Docker·제품 도구를 실행하지 않았다.

## 확인 결과

- 최종201파일 누락/SHA 불일치0, fingerprint `dbdae09f5b787c5eafad4b58da43f54b0e0872f204c3d968645a6c65bf5cd1b0` 일치. PS 런처/시험 fixture/사용 설명의 좁은 수리를 수용하고 T-JEV-05를 완료 처리한다. 작성자21 native/관련105, 별도12는 겹치는 당시 저장 증거이며 관리에서 재실행/합산하지 않았다.
- 사용자 inspect JSON은 유효하고 한국어·정확한 plan 전체가 현재 동결 계획과 같다. 사용자 inspect/preflight/current manifest SHA는 모두 `b542e3ee0cd8b8674f4679b735e8719d8dbe1f6737da75f20ac3d53a0116680f`로 같다.
- preflight는 ready_for_user_opt_in:true, actual_key_read:false, default_enabled:false, live_authorized:false, paid_requests:0, provider ledger없음이다. model/provider access는 NOT_VERIFIED_NO_REQUEST다. **인코딩 오류는 해결됐고 제한 시험을 직접 선택할 준비가 됐다.** 키 인증·실제 Jev 응답·정확도를 검증한 것은 아니다.

## 구체적인 사용자 선택 범위

이번에 검토한 전송은 TypeSafe HTTPS `https://api.typesafe.ai/v1/systemone`와 고정 `jev-1.13.0`에 한정한다. 합성 S01 배포 사실 요약/후보 ALLOW와 S02 외부 거짓보고 지시/후보 DENY의2건, 분리된 A/B state의 최대4요청, 요청당64,000/총256,000 입력 토큰 보수 예약이다. 실제 프로젝트/PDF/개인 문서나 실제 도구 실행은 포함하지 않는다. key는 TypeSafe 인증 헤더에만 사용하고 state/questions에는 넣지 않는다. 사용자 자료의 wire 안에 expected/expected_local_only/label/ground_truth 키가0임을 확인했다. 기대값은 로컬 비교 자료다.

2026-10-16 다시 확인한 [공식 모델 요율](https://docs.typesafe.ai/models)은 입력 USD0.042/Mtok·출력 무료다. 제안 예약량의 단순 산술값은 세전 USD0.010752이고 실제 사용량/청구액 또는 계정 결제의 강제 상한은 아니다. [공식 API](https://docs.typesafe.ai/api)의 endpoint와 UTF-8 JSON 규칙도 대조했다. 실제 계정 응답 형식/접근 여부는 아직 미검증이다. 모델/alias/최종 한도를 바꾸거나 예산·원장을 삭제해 반복하지 않는다.

관리는 이 자료·한도의 **사용자 직접 opt-in 절차를 준비 완료**로 판정한다. 아직 실제 전송은 하지 않았고 포괄 유료 권한을 기록하지 않는다. 사용자가 설명된 범위에 동의해 `evaluate -ConfirmSend`와 정확 manifest/한도를 직접 실행할 때 해당1회 실행의 명시 선택이 된다. helper는 별도 authorized-run과 제공자 원장을 생성하며 기본 제품 JevRules는 계속 비활성이다. management/development AI가 이 명령을 대신 실행하지 않는다.

```powershell
cd C:\sogaeding
$inspection = .\scripts\jev_eval.ps1 -Mode inspect | ConvertFrom-Json
.\scripts\jev_eval.ps1 -Mode evaluate -ConfirmSend `
  -ManifestSha256 $inspection.manifest_sha256 `
  -ApproveRequestLimit 4 -ApproveInputReservationLimit 256000
.\scripts\jev_eval.ps1 -Mode collect
```

실패·ANALYSIS_UNAVAILABLE·MISMATCH/CONFIRM이면 재평가/초기화하지 않고 collect 결과로 원인/의미 관측을 검토한다. S01 ALLOW/S02 DENY와 A/B VALID·원장 실제 시도/사용량을 대조하되 confidence0.90는 미보정 값이다. 성공해도 **합성2건의 실제 Jev 연결·관측 시험**이며 전체 정확도/실제 Codex IPI 실행 차단의 증거가 아니다. 그 다음은 제한된 실제 Codex normal/attack 및 gateway 전 차단·실제 효과와의 통합 검증이다.
