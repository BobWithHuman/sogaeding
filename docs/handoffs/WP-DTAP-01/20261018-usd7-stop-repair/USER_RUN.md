# $7 누적 한도 수리 후 이어서 실행

> 이 실행본은 사용자 실행 후 /16의 큰 MCP 응답에서 중단되었습니다. 아래 run 명령은 보존 기록이며 다시 실행하지 마세요. 최신 단일 후속은 [20261018-context-output-repair/USER_RUN.md](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-context-output-repair/USER_RUN.md)입니다. 기존 비용도 그 후속의 누적$7에 포함됩니다.

기존 실행은 그대로 보존했습니다. 아래 명령은 **기존 사용액 $0.078217을 포함한 합산 $7** 안에서만 이어갑니다. 현재 실행기 잔여 한도는 **$6.921783**이며 계정 잔액을 조회한 값은 아닙니다. 두 창 각각 $7이 아닙니다. GPT-5.2 low와 engine-on의 Jev만 사용합니다.

이미 시도한 4건(완료 1·CONFIRM 1·UNKNOWN 2)은 건너뜁니다. 미시작 **98개 시나리오 × 두 조건 = 196건**만 시도합니다. 예산 또는 다른 제한으로 더 일찍 종료할 수 있으며 완주는 보장하지 않습니다. CONFIRM 자동 승인과 UNKNOWN 재시도는 하지 않습니다.

## 창 1

Docker Desktop을 켜 두고 `OPENAI_API_KEY`가 설정된 PowerShell에서 실행합니다. 기존 키가 현재 창에 없으면 아래처럼 화면에 표시하지 않고 입력할 수 있습니다. 키를 채팅에 붙이지 마세요.

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    $dtapKey = Read-Host 'OpenAI API 키 입력' -AsSecureString
    $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $dtapKey).Password
    $dtapKey.Dispose()
    Remove-Variable dtapKey
}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode run -Arm engine-off -Experiment artifacts/20261018-dtap-os100/user-usd7-settled-1 -ManifestSha256 764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb -MaxTotalUsd 7 -PaidOptIn
```

## 창 2

창 1에 `Two arms share the SAME combined cap`이 표시되면 실행합니다. 첫 창의 broker가 키를 보관하며 두 번째 창에 키를 다시 입력할 필요는 없습니다. 기존 TypeSafe 키는 런처가 기존 파일에서 참조합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode run -Arm engine-on -Experiment artifacts/20261018-dtap-os100/user-usd7-settled-1 -ManifestSha256 764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb -MaxTotalUsd 7 -PaidOptIn
```

완료·오류·중단 뒤에는 run을 반복하지 말고 아래로 확인합니다. 예산 종료도 실행 상한을 지킨 중단이며 공격 차단 성공으로 세지 않습니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode collect
```

새 기본 결과 폴더: `C:\sogaeding\artifacts\20261018-dtap-os100\user-usd7-settled-1`.

`settled_micro_usd`는 확인된 사용량의 명목 환산액, `unresolved_hold_micro_usd`는 진행 중·사용량 미확정 예약액, `committed_micro_usd`는 둘의 합입니다. `provider_reservations`는 최초 최대 예약 기록을 보존하므로 실제 결제액으로 읽지 마세요. 다음 요청의 최대 예약까지 합쳐 한도를 넘으면 전송 전에 중단합니다. 다른 앱의 API 사용이나 공급자 최종 청구서를 조회·통제하는 기능은 아닙니다.

원 실행 상태는 `-Experiment artifacts/20261018-dtap-os100/user-usd7 -Mode status`로 따로 볼 수 있습니다. 원 실행의 stop·UNKNOWN은 소급 변경하지 않았습니다.
