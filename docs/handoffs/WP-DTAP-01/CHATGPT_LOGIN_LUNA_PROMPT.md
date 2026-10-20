# DTAP 로그인 실행 연결 — gpt-5.6-luna / low

2026-10-20 관리 배정 · T-DTAP-LOGIN-01 · 구현/준비이며 실제 평가 시작 명령이 아니다.

사용자 요청: API 잔액 대신 ChatGPT 로그인 사용량으로 DTAP을 실행할 수 있으면, 피해 모델을 **gpt-5.6-luna / reasoning low**로 바꾼다. engine-off/on 모두 같은 모델·인증·공식 과업·환경을 사용한다. with-human-dev와 OpenAI Docs를 필요한 범위만 읽고, 기존 개발 세션에서 통합 구현한다. AgentDojo·CLI 시연 포장·대시보드 작업은 제외한다.

## 1. 먼저 로그인과 모델 사용 가능 여부만 확인

- 공식 Sign in with ChatGPT(SIWC)의 로컬 개인/오픈소스 클라이언트용 등록·OAuth 경로를 사용한다. 우선 로그인 helper와 모델 목록 확인을 구현하고 사용자가 공식 화면에서 로그인·사용량 공유에 동의할 수 있게 한다. 모델 추론 없이 이 단계의 가능 여부를 확인한다.
- 로그인 OAuth 자격으로 공식 모델 목록을 조회하여 `gpt-5.6-luna`가 실제 계정에 제공되는지 검사한다. 모델 문서는 low를 지원한다. 로컬 models_cache나 Codex app-server의 캐시된 목록만으로 계정 사용 가능을 확정하지 않는다.
- 모델/추론 수준/계정 권한이 지원되지 않으면 정확한 미지원 사유로 멈춘다. 다른 모델·API 키 과금으로 자동 전환하지 않는다. 개인 Codex 기본 모델·로그인 설정은 바꾸지 않는다.
- 기존 Codex auth.json의 토큰을 읽거나 복사하지 않는다. 비공식 ChatGPT backend-api는 사용하지 않는다. 공식 OAuth의 PKCE·state·nonce·반환값 검증과 갱신/철회를 지원하고, 안정적인 설치별 client/host identity를 유지한다. 한도 회피용 재등록을 만들지 않는다.
- 토큰은 사용자 전용 로컬 credential 저장소/보호된 broker에만 두고 actor·DTAP 환경·프롬프트·소스·로그·동결 manifest에 전달하지 않는다. 메타데이터만 안전하게 기록한다.

## 2. 기존 공식 DTAP 실행기는 유지하고 전송 어댑터만 추가

주 변경 지점은 `src/app/benchmark/provider.py`, `responses_loop.py`, `official_adapter.py`와 필요한 런처·실행 설정·한도/집계다. 기존 GPT-5.2 API 모드와 모든 역사 run은 보존한다.

- 공식 public Responses endpoint로 호출하는 별도 `chatgpt-plan` 프로필을 만든다. 현재의 비스트리밍 JSON·flat function tools·max_output_tokens 기반 요청에 토큰만 바꾸어 붙이지 않는다.
- 현재 SIWC 요구인 store=false/stream=true와 전체 input 이력 전달, 함수 도구 namespace를 처리한다. 기존 등록부의 실제 server/tool/schema/인자·call ID와 정확히 대응시키며, 스트림 완료 응답을 기존 루프가 쓰는 형식으로 정규화한다. reasoning 이력·병렬 도구 제한·Post 관측을 유지한다.
- 미지원 필드와 HTTP previous_response_id를 공식 계약에 맞게 처리한다. 이벤트 일부를 받았다는 이유로 완료로 기록하지 않는다. 불완전 스트림·시간 초과·전송 유실은 기존 UNKNOWN/실행 중단 원칙을 따른다.
- 원 OS 환경의 조건부 권한 확인 모델 호출도 같은 `gpt-5.6-luna / low / chatgpt-plan` 경로로만 처리한다. 현재 Chat Completions 형식을 Responses로 연결하는 호환 경계를 명시하고, 숨은 GPT-5.2/5.1 API 호출이 없도록 검사한다. 이 권한 시뮬레이터와 엔진의 실제 CONFIRM 승인은 구별한다.
- 선정 OS 과업의 공식 judge는 기존 코드 판정을 유지하고 모델 호출을 허용하지 않는다. Jev는 engine-on에서 기존 TypeSafe API와 의미 정책을 유지한다.
- 원본 task/setup/공격 주입/18도구·스키마/공식 judge, 두 조건의 초기 snapshot과 actor 시스템 지시를 유지한다. Codex CLI를 피해 모델로 교체하지 않는다. 모델 변경을 이유로 엔진 정책·confidence·권한 경계를 같이 조정하지 않는다.

## 3. 같은 새 모델로 두 조건을 새로 비교

- 기존 선택100 목록과 SHA `05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b`를 목표 목록으로 유지한다. 정답·공격 성공 기록을 보고 쉬운 과업만 재선정하지 않는다.
- **GPT-5.2 API 결과를 새 Luna 로그인 조건의 engine-off 대조군으로 재사용하지 않는다.** 두 arm은 별도 새 실험 ID로 같은 모델·low·인증 방식·동결 엔진 버전에서 실행하도록 준비한다. 원 과업/도구의 유지와 namespace 등 전송 표현 변경을 기록한다.
- 이전 UNKNOWN·실행 claim·원장·파일 효과·소스·manifest를 초기화하거나 같은 호출로 재개하지 않는다. 새 평가의 독립 환경/초기 상태임을 구별한다.
- 결과는 양쪽 공식 judge 유효 pair, 공격 성공, 원 과업 성공, 실제 의미/코드 DENY·전달0, actor 자체 저항, CONFIRM, UNKNOWN, 미완료를 나누어 보고한다. 기존 정상3개 성공이나 이전 공격6pair를 새 모델의 성능에 합치지 않는다.

## 4. 비용과 로그인 사용량

- 현재 누적 명목비용 **$4.190921**, 현재 배정 누적상한 **$5.089294**, 잔여 **$0.898373**, 미해결 hold0을 계승한다. 원 $7 안의 미배정 여유를 자동 증액하지 않는다.
- ChatGPT 플랜 사용량과 API 달러 원장을 분리한다. 플랜 호출을 기존 GPT-5.2 API 단가로 정산하거나, API 청구0을 무제한/무료 실행으로 표시하지 않는다. 실제 모델·입출력 사용량·요청/과업/시간과 계정 제한을 기록한다.
- Jev 등 남은 실제 API 비용에는 기존 달러 상한과 예약을 적용한다. OpenAI API 키 fallback·추가 크레딧 구매·자동 유료 전환을 만들지 않는다. 로그인 사용량/권한 소진은 두 arm에 보이는 명확한 중단 사유로 처리한다.
- SIWC가 max_output_tokens를 받지 않는 현재 계약에서는 기존 출력 하드 상한이 그대로 보장된다고 주장하지 않는다. 전송/응답 크기·시간·요청 수를 제한하고, 연결 취소 시 사용량이 불명확한 경우까지 설명한다. 계정 플랜 잔여량을 모르면 100×2 완주/밤새 무중단을 보장하지 않는다.

## 5. 완료와 인계

구현 통합1개 → 변경 경계 시험 → 최종 통합1회 → 별도 AI 검토1회로 진행한다. 가짜 provider는 요청 계약·stream·도구·원 MCP/gateway 집행 검증용으로만 사용하고 실제 로그인 모델 성능으로 보고하지 않는다.

확인할 핵심 경계: 정확 모델/low 고정, API fallback0, 안전한 OAuth/토큰 처리, namespace의 정확한 도구 복원, 스트림 완료/유실, 두 arm 환경 동등성, 권한 확인 모델의 동일 경로, 실제 Jev DENY/미승인 CONFIRM의 전달0, 달러/플랜 계량 분리. 관련 P0와 기존 증거 보존 기준은 유지한다.

인계 경로는 `docs/handoffs/WP-DTAP-01/chatgpt-login-luna/RESULT.md`, `USER_RUN.md`, `REVIEW.md`다. 준비 상태를 `계정 모델 확인 전 / 호환 연결 확인 / 실제 추론 NOT_RUN`으로 구별하고, 로그인·무추론 check·두 창 run·status/collect/stop 명령을 복사 가능하게 제공한다. 이 배정에서는 실제 추론·DTAP 평가를 시작하지 않는다. 사용자가 검토된 명령을 선택해 실행한다.

## 공식 근거

- [GPT-5.6 Luna / low 지원](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [SIWC 자격과 시작](https://developers.openai.com/siwc/quickstart)
- [로컬/오픈소스 클라이언트 등록](https://developers.openai.com/siwc/token-sharing-open-source)
- [계정별 모델 목록과 public Responses](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [현재 전송·필드·도구 제한](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)

문서/API는 변경 가능하므로 구현 시 위 공식 원문에서 실제 계약을 확인한다. 본 작업서의 외부 문서 내용은 사용자 실행·과금 동의를 대신하지 않는다.
