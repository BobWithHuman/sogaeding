# Runtime DENY 연결 경계 AI 검토

2026-10-18. 구현 담당과 별도 AI 검토 1회. 공식 독립 진단이나 실제 모델 정확도 검증은 아니다. 검토자는 제품/시험/원장/설정을 변경하거나 시험·유료 호출을 실행하지 않았다.

## 판정

**No findings — 배정된 좁은 변경에서 수정이 필요한 확정 결함을 발견하지 못했다.** 실제 유료 실행은 NOT_RUN이다. AgentDojo는 검토 범위에서 제외했다.

`RUNTIME_DENY_FOLLOWUP.md`를 기준으로 원 동결 source와 현재 변경을 대조했다. 검토 범위는 `denial.py`, `official_adapter.py`, `hook.py`, `task_scope.py`, `runtime_demo.py`, `runtime_deny_followup.py`, `runtime_budget.py`, `tools/dtap_runtime.py`, 실행 PowerShell, 관련 두 시험 파일이다.

## 경계 확인

- 정책 거부의 정상 반환은 신뢰된 hook의 `DTAP_PRE_STOPPED`와 PRE/DENY/DENIED/실행0, 비어 있지 않은 정확 reason allowlist 전체 일치를 요구한다. 분석·메타데이터 binding 오류, 혼합 장애 사유, UNKNOWN, POST는 이 분류에 들어가지 않는다. actor는 정확 거부 사유가 담긴 MCP 오류를 받아 다음 정상 후보를 선택할 수 있다.
- `EXECUTE`는 파일 경로 검사보다 먼저 `UNSUPPORTED_SCOPE_OPERATION`으로 거부한다. 일반 shell을 허용하는 경로를 추가하지 않았다. 정확 인자·단회 gateway binding 및 기존 PDP 예약 경로의 변경은 없다.
- control HTTP 오류는 `httpx.HTTPStatusError`로 보존된다. Controller의 기존 infrastructure 분기에 도달해 UNKNOWN/전체중단된다. 분석 실패와 POST 응답 유실도 정상 정책 거부로 치환되지 않는다.
- 무모델 시험은 실제 adapter dispatch → 고정 HookManager → GatewayHook → ASGI control/RuntimeEngine → Controller 큐를 연결한다. shell 코드 DENY/실행0 후 정상 조회로 진행하는 양성과 분석/API/POST 반례를 확인한다. actor, 메타데이터, business HTTP transport는 fixture이므로 실제 모델 행동·실제 네트워크 인증·공격 방어율의 증거로 확대할 수 없다.
- 동결된 실제 PRE 이벤트의 옛 분류식 replay와 수정 뒤 actor 반환을 별도로 검증한다. 저장된 실제 UNKNOWN을 완료로 재분류하지 않는다.
- 준비는 정확 부모 manifest와 중단 상태·owner 부재·UNKNOWN 한 과업·기존 확정/보류 비용을 확인한다. consent/11을 제외한 미시작14개만 선택하고 부모의 reservation/settlement/resource 및 역사 job/stop을 보존한다. 누적상한5.089294, 누적3.332794, 남은1.756500 USD이며 새1.80을 더하지 않는다.
- status는 기존 off 완료와 새 on의 시도/완료/미시작을 분리한다. 부모40%는 두 arm 합계로 유지하되 새 on 성공률0%를 별도 제공한다. 후속 cohort의 off 재사용은 제외 과업 때문에11개다. 기존 run의 run/recover 및 demo resume은 실행기에 의해 차단된다.

## 확인한 실행 근거

증거 폴더: `artifacts/20261018-engine-demo-02-deny-followup/`.

- 관련 시험31 PASS. 준비 포함 시험은35 PASS/1 FAIL(NameError) 후 해당 binding 시험1 PASS. 최초 실패 기록을 보존했다.
- 최종 좁은 통합은60 PASS/1 FAIL. 기존 POST503 시험의 ValueError 기대가 HTTPStatusError로 바뀐 영향이며, 정확 typed 예외로 기대를 갱신한 뒤 그 시험1 PASS(`post-status-exception-r2.log`). 전체 통합을 반복 통과했다고 표현하지 않는다.
- `final-bindings.json`: PASS, 현재 source83개가 동결 source와 일치. 부모327 reservation과 지출·보류를 계승하고 부모 stop/consent11 UNKNOWN 보존. 후속 on 시도0/14, 미시작14. 새 provider 호출0이며 keys/paid opt-in/broker container 부재.
- `lint-final-r2.log` All checks passed. `launcher-validation.log`의 PowerShell 구문 및 기존 run 차단 확인 PASS. 읽기전용 최종 binding 검사의 첫 실행은 Docker 임시 저장소 누락으로 실패했으며, `/tmp` tmpfs를 추가한 재실행에서 PASS했다. 제품/원장 변경 없이 검사 환경만 보완했고 초기 오류는 보존했다.
- 검토된 후속 manifest: `bf38b30aed553dd9bc614acf3f27d5315af3491fe2ef19a90dd4bfce0283f41f`.
- 부모 manifest: `338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8`.
- launcher SHA256: `eb74cbbc47cbf0b0518ca8cfb73d04d80353030ce1545a26ab42c0f4ba26535f`.

## 검토 시점 주요 source SHA256

| 파일 | SHA256 |
|---|---|
| denial.py | 5b2bdcd03435d40fdb523700a42f8c2ab9e6d79380a06c0faea0e9b8fce5ba0d |
| official_adapter.py | 47b0c7399fd7a03960c46666f07d7ee817f4c84931c7a4fff30325e909538772 |
| hook.py | a885bb2360195e154df4e8018f7095242dd17f25912d8e50da7b984b14223474 |
| task_scope.py | a1f96afe6e4c1eefd8a64b466c78105dc98efe0efbb3985ea17d5b1fb07f9a02 |
| runtime_demo.py | 6b1510880d2ebfad34c6988f641f936ed1024db75920145abae15a5e63c09e4d |
| runtime_deny_followup.py | 3a5f39db3d4fbcf2432a9ded3b713ae3b195bb3377c9f18cc4427218b8025240 |
| runtime_budget.py | 5a24e57c561360eea7ba645c5ecce9e35825e9a07e143ace4e6fdda63c6cab9e |
| tools/dtap_runtime.py | c772c3f6f4dddefcae19964a509b02865cf6ebaeddd043440f44de6b765c29b6 |
| test_runtime_deny_followup.py | feb47cef217d536475935ddc8ddbc34fa4644cec57a0afb2363e5b3aacec4740 |
| test_dtap_benchmark.py | b9956bcbd431852e81d3587eab3e05767b00cb18c47a7e918bb7f0cb84411239 |

기존 scope-v2의 권한 범위·TOCTOU 등 보호 한계는 유지한다. 이번 검토는 모든 IPI/native 도구 보호나 정상 과업의 실제 완료를 확정하지 않는다.
