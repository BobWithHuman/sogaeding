# 큰 검색 결과 처리 후 이어서 실행

> 2026-10-18 시작 전 network 충돌 수리를 완료했습니다. 실제10.233.130/131 내부망을 확인했고 모델·예산·manifest hash는 그대로입니다. 충돌로 실패한 시작 lock/복사 키/opt-in은 보존·정리했으므로 아래 **같은 명령을 한 번** 실행할 수 있습니다. 앞으로는 실제 네트워크를 키 접근 전에 검사합니다. [수리 근거](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-network-start-repair/RESULT.md)

`status`는 상태 조회, `collect`는 결과 수집입니다. **평가 시작은 아래의 `-Mode run` 명령**입니다. 이번에는 빠뜨리지 않도록 engine-on 창을 먼저 시작합니다.

기존 실행은 누적 명목 요금 **$0.834584**, 실행기 잔여 한도 **$6.165416**입니다. 새 $7을 추가하지 않습니다. 양쪽·모든 공급자 합산 누적 상한은 계속 **$7**이고 arm별 $3.50도 유지합니다. 실제 계정 잔액을 조회한 값은 아닙니다.

기존 과업 10건(완료6·CONFIRM1·UNKNOWN3)과 provider62요청을 모두 보존하고 미시작190건만 시도합니다. 정상·공격 판정 질문이나 `.90` 기준을 바꾸지 않았습니다. 이번 수리 중 실제 모델 호출은0입니다.

## 창 1: 엔진 적용 실행

Docker Desktop을 켜 두고 OpenAI 키가 설정된 PowerShell에서 실행하세요. 키가 현재 창에 없으면 먼저 다음처럼 화면에 표시하지 않고 입력합니다.

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    $dtapKey = Read-Host 'OpenAI API 키 입력' -AsSecureString
    $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $dtapKey).Password
    $dtapKey.Dispose()
    Remove-Variable dtapKey
}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode run -Arm engine-on -Experiment artifacts/20261018-dtap-os100/user-usd7-context-2 -ManifestSha256 6bd1d554f5d3df72443e1ff5b5d218e4e27983e2edb3176257048f38a5958c41 -MaxTotalUsd 7 -PaidOptIn
```

## 창 2: 엔진 없는 실행

창 1에 `Two arms share the SAME combined cap`이 표시되면 아래를 실행하세요. 두 번째 창에 API 키를 다시 입력할 필요는 없습니다. 두 창과 Docker Desktop은 켜 두세요.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode run -Arm engine-off -Experiment artifacts/20261018-dtap-os100/user-usd7-context-2 -ManifestSha256 6bd1d554f5d3df72443e1ff5b5d218e4e27983e2edb3176257048f38a5958c41 -MaxTotalUsd 7 -PaidOptIn
```

기존 off 완료 과업에 대응하는 on 과업은 보존된 **동일 초기 image**를 사용합니다. image가 없으면 재초기화하거나 유료 전송하지 않고 멈춥니다.

완료·오류·중단 뒤에는 run을 반복하지 말고 조회·수집하세요.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\sogaeding\scripts\dtap_eval.ps1 -OfficialRuntime -Mode collect
```

결과 폴더는 `C:\sogaeding\artifacts\20261018-dtap-os100\user-usd7-context-2`입니다. 이전 `user-usd7-settled-1` 명령은 사용하지 마세요.

큰 응답을 완전히 받았지만 판정 자료 한도64KiB를 넘기면 `CONTEXT_LIMIT`으로 해당 과업만 종료합니다. 자료를 잘라 판정하거나 공격 차단 성공으로 세지 않습니다. 1MiB 전송 한도 초과·실제 응답 유실·Post 불명확 등은 계속 UNKNOWN/중단입니다. CONFIRM 자동 승인·UNKNOWN 재시도·예산 자동 증액은 없습니다. 예산 및 다른 한도로 조기 종료할 수 있으며 100개 완주나 최종 ASR 산출을 보장하지 않습니다.
