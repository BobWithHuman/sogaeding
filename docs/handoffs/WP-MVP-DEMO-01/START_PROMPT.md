# WP-MVP-DEMO-01 개발 시작

with-human-dev, 최신 AGENTS/control_state, **docs/plans/16_mvp_demo_delivery.md 전체**와 관련 가이드 준수표/원문을 읽고 수행한다. 이 작업은 기존 개발 세션의 단일 통합 작업이며 별도 AI 검토를 거친다. 관리 plans/harness/AGENTS는 변경하지 않는다.

목표는 **Jev 의미 질문/출처 합성의 설계 불일치 수리와 실제 Codex→hooks→Jev PDP→agentgateway→파일 효과를 사용자가 보는 시연 준비를 한 인계로 마무리**하는 것이다. API키 재준비·후속 평가 스크립트만 추가하는 작업으로 축소하지 않는다. 최근4요청은 모두 provider COMPLETED이고 현재 문제는 S01 CONFIRM/문맥 미확정 및 S02 B_EXTERNAL_EVIDENCE_REQUIRED다. 실제 선택·확률 세부는 미보존이므로 추측과 확정을 구분한다.

필수 수리: task 권한/범위 근거와 external 사용 근거 분리, A의 범위 관측/B의 외부자료 활용 관측 정합성, 실제 관련 슬롯에만 외부 연관 요구, 안전한 typed 선택/확률·confidence/판정 사유 관측. 계약·정책 버전 변경은 이 범위로 명시 위임한다. threshold를 두 사례에 맞춰 낮추거나 기대값을 하드코딩하지 않는다. 정상 외부 데이터 활용과 추가 지시 채택을 일반화한 반례로 검증한다.

시연: 기존 실제 gateway/파일 MCP/hook와 명시 LIVE Jev demo profile을 연결하고 합성 workspace에서 정상 보고서 쓰기와 외부 지시 후보 실행 전 차단을 준비한다. 작업별 수동 세션/토큰 발급은 없다. 실제 actor가 공격 후보를 만들지 않으면 미시도로 표시한다. 사용자용 출력은 짧은 읽기 쉬운 타임라인과 실제 파일 효과이며 JSON 전체를 주 화면으로 삼지 않는다. 단일 준비/시작 진입점과 최소 사용자 명령을 제공한다.

쓰기 범위: src/app/transparent/jev_policy.py 및 필요한 semantic/diagnostics·내부 observation schema·현재 설명, demo용 Control/기존gateway 연결·별도 Compose/profile·scripts/tools/안전 fixture/관련 테스트/로컬 읽기 전용 viewer, docs/mvp, docs/handoffs/WP-MVP-DEMO-01/<run>/와 안전 artifacts. 공통 outward 권한·인자 결합·원자 예약/UNKNOWN/TLS·역할키 경계는 유지한다. demo외 일반 native/전체 웹앱/전체 공급망·C/D를 새 선행조건으로 추가하지 않는다.

기존 key/원장/두 실패·followup 결과·예산/개인 전역 설정은 보존한다. 1회 UNKNOWN사용량+4회 실제COMPLETED를 합쳐 누적5회이며 지우거나 새 성공으로 덮지 않는다. 별도 demo allowance 제안은 준비만 하고 실제 OpenAI/TypeSafe/actor 호출0을 유지한다. 현재 코드와 실제 컨테이너/bundle 일치를 검증하고 유료 CLI는 사용자 직접 시작으로 남긴다. fake 검증을 실제 모델 성능으로 보고하지 않는다.

새 RESULT/별도 REVIEW에 실행 가능한 시연 명령·화면 예시/효과 증거·변경 목적/구현·필수 가이드 연결·남은 모델/CLI NOT_RUN을 기록한다. 다음 사용자 단계는 다시 계획 파일 생성이 아니라 **준비된 CLI 시연 실행**이어야 한다. 정량 방어율/전체 MVP DONE은 관리가 실제 결과를 보고 결정한다.
