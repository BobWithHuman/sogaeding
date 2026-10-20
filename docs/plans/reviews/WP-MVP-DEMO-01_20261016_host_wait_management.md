# MVP 시연 첫 사용자 실행: 허용 뒤 집행 대기에서 종료

관리 판정: **WP-MVP-DEMO-01 진행 중, 실제 정상 시연 미완료**. 개발 인계의 오프라인 의미/출처 수리와 시연 경로는 구현됐으나 실제 사용자 흐름의 완료 근거는 없다. 466개 회귀/별도 검토는 개발 인계 실적이며 관리가 전부 재실행한 수치는 아니다. 동결 소스216개와 준비 manifest의 소스는 현재 파일과 모두 일치한다.

## 읽기 전용 대조

- 준비 manifest: `454466abc92df12740a8ce9e16837ddc88f85dbbcf85a473d522077a1278ed05`.
- Control calls: MCP `DENIED/DENY/TOOL_ARGUMENTS_UNPARSED_OR_SCOPE` 1개, 요청된 공개 읽기 `READY/ALLOW/PUBLIC_ENROLLED_READ` 1개. 범위 밖 보조 호출 거절을 외부 문서 공격 식별 성공으로 계산하지 않는다.
- Upstream attempts 0개, 두 보고서 파일 없음, 새 Jev provider 원장 없음. Jev 요청0은 의미 판정에 필요한 쓰기까지 도달하지 않았음을 뜻한다. GPT actor는 실행됐으므로 actor 비용0이라는 뜻이 아니다.
- CLI 시작 예약1/2는 보존됐다. 원장/키/파일/예약을 초기화하거나 환불하지 않았다. 관리 모델 호출0, 인증정보 읽기/해시0이다.
- [관측 JSON](../../../artifacts/management-mvp-demo-host-wait-20261016/observation.json)은 경로상 실제 `artifacts/management-mvp-demo-host-wait-20261016/observation.json`을 가리키는 관리 근거다. 원사용자 HTML은 `artifacts/runtime-mvp-demo/reports/history-36ab12d09c5881a1.html`에 보존돼 있다.

## 확인된 런처 결함과 원인 확정의 한계

`tools/mvp_demo.py:start`는 대화형 Codex에 `subprocess.run(..., timeout=180)`을 적용한다. 프롬프트 입력·`/hooks` 검토·호스트 승인 대기까지 모두 180초에 포함돼 자식 프로세스를 종료할 수 있다. `TimeoutExpired`에서 `actor_exit=TIMEOUT`을 반환하지만 `main`은 이를 출력/기록하지 않고 시작했다는 문장만 출력한다. 정상 종료, 사용자 취소, 강제 timeout을 사후에 구별할 자료가 없다. 기존 fake 시작 시험은 `timeout==180`을 확인하며 실제 승인 대기를 거치지 않았다.

예약 생성부터 결과 HTML까지188.383초로 180초 제한과 추가 준비/보고 시간에 부합한다. **이번 실제 종료가 timeout이었다는 종료 기록은 없어 확정하지 않는다.** 다만 사람 대기를 죽이는 전역 타이머와 종료 원인 유실은 코드로 확인된 수리 대상이다. 키/TypeSafe/API 응답 실패를 이번 원인으로 지목할 근거는 없다.

`bob-agentgateway:4400` 경고는 개인 설정의 별도 MCP 시작 실패다. `with_human` 도구의 후보/호스트 승인창은 생성됐으므로 이 경고만으로 이번 집행 대기 종료를 설명하지 않는다. 전역 설정 삭제나 Codex 업데이트를 이번 해결책으로 추가하지 않는다.

## 다음 작업

[같은 작업팩의 보완 지시](../../handoffs/WP-MVP-DEMO-01/REPAIR_HOST_WAIT_PROMPT.md)를 기존 개발 세션에 전달한다. 대화형 수명주기·종료 진단·실행 모드 표시를 수리하고, 문서에 이미 알려진 의미 쓰기 READY30초와 호스트 승인 대기의 순서도 함께 해결한다. 단순히 사용자에게 빠르게 승인하라고 요구하지 않는다. 현재 승인된180초 제한을 몰래 늘리지 않으며 수정 시연의 구체적 제안으로 명시한다. 기존 소스 manifest/실패/예약은 보존하고 변경분을 명시한 후속 연결을 한 번에 인계한다. 실제 유료 재시험은 개발/관리 AI가 실행하지 않는다.

전체 native/모든 IPI/공급망 전수/대회 제출 완료를 선언하지 않는다. 정상 파일 작성과 실제 위험 후보 차단은 여전히 미검증이다.
