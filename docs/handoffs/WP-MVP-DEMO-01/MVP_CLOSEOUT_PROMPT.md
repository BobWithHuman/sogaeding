# 등록 파일 MCP 엔진 MVP 마감·시연 결과 정리

관리 배정: 2026-10-17, T-DEMO-02. with-human-dev의 필요한 구현/검토 기준으로 기존 개발 세션에서 수행한다. 관리 plans/AGENTS/작업장부·과거 RESULT/REVIEW는 수정하지 않는다.

## 완료된 핵심과 이번 범위

관리는 실제 정상 Codex ALLOW/OBSERVED·쓰기1/PDP승인0과 별도 고정후보의 실제 gateway/실제 Jev DENY·위험쓰기0을 **등록 파일 MCP 엔진 MVP 동작 검증 완료**로 수용했다. 전체 자유개발/native/hook fail-open·모든IPI·모델전반정확도·제출준비완료와는 범위가 다르다.

정본: `docs/plans/reviews/WP-MVP-DEMO-01_20261017_core_engine_accepted_management.md`, 원증거 `artifacts/management-core-engine-accepted-20261017/observation.json`. core-auto-v5p1/provider4 COMPLETED/예약256000/입력5912·출력314, 역사29/1856000·CLI5/5이며 **잔여0**이다. 새 start/verify/evaluate/예산/정책/서비스 변경을 하지 않는다.

이번에는 기존 viewer/보고서와 현재 제품 설명만 마무리한다. 새로운 대시보드·런처·모델 버전·정밀 인과 분석·일반 native 지원을 끼워 넣지 않는다. 기록된 실제 응답/원장·원문/source·manifest/claim/암호화 DB·정상 보고서·모델 wire/정책을 바꾸지 않는다. 새 파생 보고서/화면만 생성한다.

## 고칠 표시

1. read_file ALLOW/OBSERVED는 읽기 완료로 표시한다. FILE_NOT_FOUND/OBSERVED_ERROR는 파일부재 읽기 오류, DENIED 상태방어는 실행전 상태거절, 의미 DENY는 실제 외부지시 차단으로 구분한다. 일반 fallback NOT_COMPLETED로 성공을 덮지 않는다.
2. episode5의 STARTING/FINISHED를 같은 수명주기로 묶는다. 최종 FINISHED exit0·연결닫힘/정리 VERIFIED가 있으면 같은 episode의 미종료 경고를 중복 노출하지 않는다. 실제 finish 없는 시작은 계속 미확정이다.
3. 제어문자 제거/escape 과정에서 문서·요청·후보의 줄바꿈을 지우지 않는다. 안전한 HTML escape와 비밀 마스킹/크기제한은 유지한다.
4. Control 과거UNKNOWN1·새attempt UNKNOWN0·upstream UNKNOWN0을 별도 항목으로 표시한다. 전체8호출/6upstream(성공5·확정 읽기오류1), 실제 위험쓰기0을 정확히 구분한다. 과거 실패를 삭제하지 않고 접어서 볼 수 있게 할 수 있다.
5. 화면 첫 부분에서 '정상: 실제 Codex 자동 허용·보고서 생성', '위험: 별도 고정후보·실제 Jev 의미 DENY·위험쓰기0'을 보여준다. 실제 모델을 사용한 결과임과 등록 파일 MCP 범위를 함께 밝힌다. 고정 위험후보를 actor 피폭/전체IPI보호나 모델정확도PASS로 표현하지 않는다.
6. `current_source_matches_frozen_run=false`는 원 동결 이후 runner4파일의 승인된 변경과 연결해 설명한다. 현재 추가 viewer 변경도 기존 실제 실행 시점의 manifest를 덮어쓰지 않고 변경 영향/파생 보고서 작성 시점을 명시한다. 허용 외 변경을 무조건 정상으로 표시하지 않는다.

## 시연 마감 산출물

기존 history/HTML renderer를 재사용해 실제 기록 기반 최종 로컬 HTML과 간결한 한국어 사용 안내를 제공한다. 정상 요청·원문/정상보고서, 위험 외부지시·위험후보·실제DENY/금지효과0을 한눈에 비교할 수 있게 한다. 원 기록을 재현하는 것과 새로운 모델 실행을 분명히 구분한다. 새 시연을 위해 어떤 추가모델 명령도 요구하지 않는다.

현재 제품 개요/실행 설명의 관련 문서만 갱신해 hooks→agentgateway→PDP(규칙/Jev A/B)→executor 및 출처/결정/실제효과를 짧게 설명한다. A는 외부자료를 가린 사용자 범위 관측, B는 사용자/후보/외부자료를 본 행동 관측이고 현재 B 양의허용/A 부정·충돌검사 정책이라는 점을 정확히 적는다. 제품 PDP승인과 Codex 호스트승인은 다르다. 완료범위/남은native·보안제출보강을 구분한다.

이후 발표/개발기획서 제2항에 쓸 수 있도록 이번 실제 성공, 앞선 gate/Post 최초실패→수리→재검증의 안전한 파일 링크를 묶는다. 키/raw 민감자료·암호화 snapshot을 열거나 외부 업로드하지 않는다. 필수 가이드 적용/기존 진단 이력과 scope는 유지한다.

## 검증과 인계

저장된 성공/이전실패/새위험 결과로 관련 renderer 시험과 실제 HTML 육안 확인을 한다. 새 의미 시험이나 수백 개 제품 회귀는 요구하지 않는다. 별도 AI 검토1회는 표시가 실제 원증거와 일치하고 정상/오류/UNKNOWN/고정위험을 잘못 승격하지 않는지 확인한다. 운영 DB/원장/claim/원 보고서가 변경되지 않았음을 확인한다. history 수집을 사용해도 조회와 새 파생 HTML만 생성하고 모델/연결/claim은 생성하지 않는다.

배정 경로 RESULT/별도 REVIEW, 최종 HTML/화면 예시와 사용자가 볼 링크를 인계한다. 보고서 첫 문장은 등록 파일 MCP 엔진 MVP 실제 동작 완료·화면 마감 여부와 남은 범위를 분명히 한다. 실제모델/actor/CLI/예산/서비스교체0을 유지하고 개발 AI 토큰과 구분한다.
