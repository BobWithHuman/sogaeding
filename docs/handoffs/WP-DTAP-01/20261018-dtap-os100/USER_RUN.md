# DTAP OS100 — 두 창 합산 $7 한도

> **실제 실행 중단 후 안내:** 이 실행본은 첫 `CAP_EXHAUSTED_ARM` 후 409/`INFRASTRUCTURE_STOP_ALL`로 종료됐다. 아래 run 명령을 반복하지 않는다. `status`/`collect`만 사용한다. 기록된 nominal 사용량은 $0.078217, 보수적 예약은 $5.718944이며 서로 다르다. 예산 정산·종료 분류 후속은 `docs/handoffs/WP-DTAP-01/USD7_STOP_RECOVERY_PROMPT.md`를 따른다. 아래 실행 명령은 이미 사용한 절차의 기록으로 보존한다.

2026-10-18 사용자 지시로 기존 $3,000 명령을 철회하고 한도를 낮췄다. 새 manifest: `742efbc00e212f7e313bace19e4e296234de6a1b41630f16f92dbfa9d1368433`. 폴더: `C:\sogaeding\artifacts\20261018-dtap-os100\user-usd7`.

**두 창 합산 $7, 각 창 $3.50이며 GPT와 Jev 예약액을 모두 포함한다.** 요청 전 원자 예약에서 다음 요청의 최대 비용까지 더해 한도를 검사한다. 예산 부족이면 전송하지 않는다. 다른 OpenAI 모델·judge 모델 전송은 여전히 금지하며 GPT-5.2 low와 engine-on Jev만 사용한다.

현재 보수적 예약(요청당 GPT 입력40만·출력 최대8192토큰, 완료 예약 유지)을 그대로 썼다. 따라서 이 $7로100쌍 완료를 보장하지 않으며 실제 청구액이 작아도 몇 건 후 예약 한도로 중단될 수 있다. 자동 증액·자동 재시도·UNKNOWN 환불은 없다. 기존 $3,000 명령은 새 진입점에서 전송 전에 거절된다.

설정·무모델 점검만 완료했다. 실제 평가는 아직 시작하지 않았다. 실행하려는 경우에만 아래 명령을 사용한다.

창1 — 기존 OPENAI_API_KEY가 설정된 PowerShell:

```powershell
& 'C:\sogaeding\scripts\dtap_eval.ps1' -OfficialRuntime -Mode run -Arm engine-off -ManifestSha256 '742efbc00e212f7e313bace19e4e296234de6a1b41630f16f92dbfa9d1368433' -MaxTotalUsd 7 -PaidOptIn
```

`Two arms share the SAME combined cap` 표시 뒤 창2:

```powershell
& 'C:\sogaeding\scripts\dtap_eval.ps1' -OfficialRuntime -Mode run -Arm engine-on -ManifestSha256 '742efbc00e212f7e313bace19e4e296234de6a1b41630f16f92dbfa9d1368433' -MaxTotalUsd 7 -PaidOptIn
```

두 창 모두 같은 $7을 공유한다. 창마다 $7씩이 아니다. 모델 수행 gpt-5.2/low·조건부 원본 승인 시뮬레이터 gpt-5.2/low·코드 judge는 기존 원칙을 유지한다. 엔진 판정용 Jev는 engine-on에서만 호출한다.

```powershell
& 'C:\sogaeding\scripts\dtap_eval.ps1' -OfficialRuntime -Mode status
& 'C:\sogaeding\scripts\dtap_eval.ps1' -OfficialRuntime -Mode collect
```

실패·UNKNOWN·예산 중단 뒤 run을 반복하지 않는다. 종료된 과업과 미완료 과업을 구분해 수집한다. 이 한도는 이번 실험의 공급자 요청에 적용되며 같은 OpenAI 계정의 다른 프로그램 사용량을 통제하는 계정 설정은 아니다.
