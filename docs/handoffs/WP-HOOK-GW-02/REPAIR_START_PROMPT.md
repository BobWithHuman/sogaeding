# WP-HOOK-GW-02 B 보완: 실제 정상 요청의 근거 검증 실패

with-human-dev 스킬로 T-HG-04를 수행해줘. 관리 세션은 계획/전역 상태를 맡고 너는 이 문서의 제품 수정·오프라인 검증·별도 AI 검토 후 인계만 맡는다. 제품 목표는13번의 평소 CLI hooks/실제 agentgateway 자동 연결과 자유 개발이다. 작업별 대시보드 생성·수동 agent token 복사로 돌아가지 않는다.

먼저 읽을 문서:
- AGENTS.md, docs/plans/14_hookgw_live_completion.md의 최신 B 보완
- docs/plans/reviews/WP-HOOK-GW-02_B_20261016_live_failure_management.md
- docs/plans/03_guide_compliance.md의 적용 항목 및 관련 PDF 원문
- docs/mvp/08_transparent_hook_gateway_spec5.md, 기존 A RESULT/REVIEW

사용자 실제 정상 요청은 실패했다. session 01a14347-a256-74e1-bcad-b19643b28284, turn 01a14347-dc26-7e42-8d81-4b3201166a25의 read_file 후보3건 모두 QUOTE_MISMATCH/A → ANALYSIS_UNAVAILABLE → DENY다. 출력 파일에 WP-HOOK-GW-02-user-20261016-01 표식이 없고 이전 파일 그대로다. judge는18/24, 남은6이며 새6건은 A/B COMPLETED다. 응답 완료와 유효 근거/실행 성공을 구별해라. 공격 성공으로 계산하지 마라. 원 관측을 보존하지 않았으므로 어느 ref가 틀렸는지는 미확정이다.

순서와 요구:

1. 변경 전 현재 소스/안전한 이력/예산18/24와 첫 실패를 고정한다. 기존 DB/원증거/키/정책 및 A 인증·마스킹·개인 로그인/설정은 보존한다. 이번 실제 한국어 요청과 SPEC5 conversation wrapper를 합성 fixture로 사용하고, 현재 입력 구조의 근거 계산 문제를 오프라인에서 재현·구분한다. 실패 원문을 지어내지 않는다.
2. A user_request/candidate와 B에서 사용할 수 있는 서버 생성 bounded exact span catalog를 마련해라. 모델은 가능하면 catalog의 span ID만 선택하고 서버가 snapshot/view/source/hash에 결합된 원 ref를 복원·정확 검증한다. 모델에게 Unicode/JSON offset 계산을 맡기는 의존성을 줄여라. 인용 선택 성공은 의미 판단 정확도 증명이 아니다. 직접 request 텍스트만으로 허용하는 hardcode를 추가하지 않는다.
3. 정확 일치·실제 출처·권한·필수 근거·단회 예약/UNKNOWN 통제는 유지해라. fuzzy matching, substring만으로 임의 offset 수정, 잘못된 근거 무시, 분석 실패 ALLOW/사용자 승인 우회, 모델 변경, 자동 유료 재시도는 하지 마라. catalog가 불완전/모호하면 안전하게 미완료로 남겨라.
4. A/B 검증 실패를 각각 관측하되 하나라도 실패하면 실행을 막아라. 진단은 allowlist 코드/view/ref 종류/범위/길이/해시/일치 boolean 수준으로 남기고 raw 사용자 요청·quote·응답·비밀·Authorization은 기록하지 마라. 첫 분석 장애 뒤 같은 실제 사용자 turn의 새 call/경로변경 재시도가 추가 judge 비용을 쓰지 않도록 중단 상태와 복구 경계를 구현·시험해라.
5. MCP startup issue1은 실패 서버가 아직 미확정이다. 모델 없이 실제 stdio bridge initialize→notifications/initialized→tools/list를 확인하고 실패 서버/단계·분류를 안전하게 구분해라. 무모델 preflight가 이 왕복의 결과를 반영하도록 보완하되 tools/call/모델을 실행하지 않는다. 초기화 실패를 근거 없이 quote 실패와 합치거나 개인 MCP 삭제·TLS/신뢰 우회·추정 timeout 증가로 해결하지 않는다.
6. 한국어/다중 turn/Windows 역슬래시/따옴표/CRLF/emoji/중복구절/경계·잘림을 시험하고 forged·unknown·stale·cross-view·cross-snapshot ref를 거부해라. 동일 turn 분석 실패 후 여러 call의 유료 adapter 호출 수0을 확인해라. SPEC4 공유 코드, 기존 API 준비·마스킹/예산, gateway 인자결합/중복효과/UNKNOWN 회귀도 영향 범위만 검증해라. 코드 수정 후 동결 bundle과 실제 컨테이너가 같은 최종 소스를 쓰는지 연결해라.

명시 쓰기 권한:
- src/app/transparent/engine.py, judge.py 및 필요한 좁은 server.py 진단 경로
- src/app/pdp/semantic.py, diagnostics.py, judge.py의 해당 근거/검증·진단 부분만. 공유 변경은 SPEC4 호환/회귀를 확인한다.
- tools/hookgw_mcp.py, hookgw_preflight.py, 필요한 좁은 hook/launch helper, 관련 tests/hookgw 및 기존 관련 회귀
- docs/mvp/08_transparent_hook_gateway_spec5.md 및 해당 내부 judge 계약/schema/prompt 버전, 합성 fixture, 새 evidence/run 폴더
- Docker bundle/설치 helper는 변경된 제품 코드 배치 검증에 필요한 최소 범위만. 기존 키/역할 볼륨/예산을 갈아 끼우지 않는다.

내부 judge evidence 계약·버전은 이 범위에서 명시 개정할 수 있으며 코드·문서·시험을 동기화해라. 기존 outward 권한/승인/상태 의미는 유지한다. docs/plans/, harness/build_tasks.json, 전역 DONE 및 개인 전역 config/auth/CA는 수정하지 않는다. 다른 제품 기능/native 지원/공급망 전체 보강은 이번 선행조건으로 확대하지 않는다. 필수 가이드·현재 적용 P0는 유지한다.

유료 actor/judge 호출은0회로 진행하고 사용자가 직접 실행할 정상1건의 새 표식·최소 절차·중단 조건을 인계한다. 기존18/24 상한을 초기화/환불/증액하거나 새 장부로 우회하지 않는다. 별도 AI 검토 결과와 최초 실패/수정/재시험·실패/NOT_RUN을 docs/handoffs/WP-HOOK-GW-02/<새 run_id>/RESULT.md 및 별도 REVIEW.md에 연결한다. 오프라인 구현 완료와 실제 정상/공격 LIVE 완료를 분리한다.
