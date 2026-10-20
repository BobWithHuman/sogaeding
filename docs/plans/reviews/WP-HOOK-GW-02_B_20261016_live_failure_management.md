# WP-HOOK-GW-02 B: 사용자 정상 LIVE 실패 관리 판정

2026-10-16. 관리 세션은 사용자 출력, 현재 코드, 인증된 로컬 history와 judge DB의 mode=ro 조회 및 출력 파일 메타데이터를 대조했다. 관리/검토 AI는 모델을 호출하거나 제품 코드를 변경하지 않았다. 최초 기본 sandbox 조회는 WinError10013/Docker pipe 권한 오류였으며 허용된 읽기 전용 조회로 확인했다. 이는 사용자 제품 실패의 원인으로 집계하지 않는다.

안전한 관리 관측 요약은 [observation.json](../../../artifacts/management-hookgw02-user-normal-20261016/observation.json)이다. 실제 조회 출력과 사용자 보고에서 정리한 기록이며 원 모델 응답을 복구한 파일이 아니다.

## 판정

**정상 작업 FAIL, 공격 시험 NOT_RUN.** API 실행 준비 A의 좁은 수용은 유지하되, 다음은 유료 재실행이 아니라 아래 B 보완이다. hook→PDP의 판정/거절은 관측됐지만 정상 사용과 실제 gateway upstream 효과 검증은 이번 실행에서 성공하지 않았다. 전체 MVP는 미완료다.

- session: 01a14347-a256-74e1-bcad-b19643b28284
- turn: 01a14347-dc26-7e42-8d81-4b3201166a25
- calls: exec-4d12190b-9fb4-4d4b-9b30-ea145381531e, exec-164162b7-6f6b-4dca-8dc7-a34dbeacb48c, exec-8f92da4a-cd35-4124-b0d8-ec4cfddd6f87（각각 위 session 접두사）
- 세 후보 모두 path=mcp, state=DENIED, decision=DENY, reason=ANALYSIS_UNAVAILABLE, diagnostic=QUOTE_MISMATCH/view A다. 외부 읽기 출처는 이 시점에 없었다. 분석 실패 DENY를 공격 식별 성공으로 계산하지 않는다.
- 사용자의 Codex 응답과 기존 ledger의 새 A/B 6건 COMPLETED는 모델 응답 도착을 뒷받침한다. COMPLETED는 API 응답 상태이며 근거 검증/정상 실행 성공을 뜻하지 않는다. A 검증에서 예외가 나면 현재 코드가 B 검증을 하지 않으므로 B가 유효했다고 말할 수 없다.
- judge 기존12/24 → 현재18/24, 남은6. A/B 각9 COMPLETED. 현재 budget SHA256: fd2706d6739db9e84b1a328e927d4cbe6352d8ff4dc7143fb7c634ec6424b660. actor 비용은 별도이며 이번 관리 조회에서는 집계하지 않았다. 예산을 초기화/환불/증액하지 않았다.
- normal-output.txt: 62 bytes, LastWriteTimeUtc=2026-10-16T04:10:37.1706889Z, SHA256=025fd876a889c18ea02696e4c3618b482a54270619e804c59e12cffd021c8eff. 사용자 출력에 이번 표식이 없고 파일 시각도 이번 호출보다 앞선다. 기존 probe 파일을 새 성공으로 계산하지 않는다.

## 확정된 오류와 가설

semantic.py의 QUOTE_MISMATCH는 모델이 낸 source_id/start/end/quote 중 지정 문자열의 slice와 quote가 다를 때 발생한다. engine.py는 실제 사용자 turn 배열을 canonical JSON 문자열로 감싸고, semantic.inputs는 이 문자열 및 candidate canonical 문자열을 다시 JSON 입력에 넣는다. 현재 A에는 evidence_texts만 있고 서버 계산 evidence_spans는 B의 sources에만 있다. 모델에게 한국어·중첩 JSON·escape의 문자 위치 계산을 맡기는 구조가 유력한 실패 원인이다.

**어느 ref의 어느 offset/quote가 잘못됐는지는 원 모델 관측 미보존으로 확정할 수 없다.** 원응답을 복구했다고 주장하거나 개인 transcript를 일괄 수집하지 않는다. 기존 시험 fixture가 Python의 정확한 slice를 만들어 주는 한계도 분리한다.

MCP startup issue1의 실패 서버 이름/상세는 현재 자료에 없다. 위 DENY와 동일 원인이라고 단정하지 않는다. preflight는 TLS/health/config를 확인하지만 실제 stdio initialize→initialized→tools/list 왕복을 확인하지 않는 공백이 있다. bridge의 generic 오류만으로 서버/단계를 알 수 없어 무모델 진단이 필요하다.

## 다음 배정: WP-HOOK-GW-02 B 보완 / T-HG-04

[개발 지시](../../handoffs/WP-HOOK-GW-02/REPAIR_START_PROMPT.md)를 기존 개발 세션에 전달한다. 관리가 제품을 직접 수정하거나 다른 사용자 채팅으로 메시지를 보내지 않는다.

1. 서버 생성의 제한된 exact evidence catalog를 두 관점에 제공하고, 모델이 서버 span ID를 선택하면 동일 snapshot/view/hash에서 실제 ref를 복원·검증하는 방식을 우선한다. 정확 인용·출처·권한 검증은 유지한다. 모호한 근거를 강제로 맞추지 않는다.
2. 비밀 없는 실패 진단과 A/B 각각의 검증 상태를 남긴다. 첫 분석 장애 이후 같은 사용자 turn의 새 call/인자변경 재시도가 추가 유료 분석을 소비하지 않도록 중단 상태를 유지한다. 새로운 실제 사용자 turn/명시 복구와의 경계를 시험한다.
3. 실제 stdio bridge의 MCP 시작/목록 왕복을 모델 없이 검증하고 실패 서버/단계/분류를 안전하게 구분한다. tools/call은 준비 검사에서 실행하지 않는다. 개인 MCP 설정 삭제나 trust/TLS 우회는 하지 않는다.
4. 한국어·중첩 JSON·Windows 경로·따옴표·CRLF·emoji·다회 turn 및 위조/stale/cross-view 근거 거부를 오프라인으로 검증한다. 기존 SPEC4 및 gateway/UNKNOWN/단회 실행 회귀를 보존한다.
5. 별도 AI 검토와 동결 제품 소스/실행 경로 확인 후 관리에 인계한다. 개발 AI 유료 호출0. 그 뒤 사용자 정상1건 재시험을 배정하고 성공 전 공격 시험을 하지 않는다. 남은6회/24상한을 유지하고 부족하면 구체 필요량을 인계한다.

native 일반 개발/hook 프로세스 사망 fail-open/공급망 미완료는 유지한다. 이번 보완을 이유로 전체 C/D를 선행조건으로 추가하지 않는다.
