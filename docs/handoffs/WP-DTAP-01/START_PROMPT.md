# DTAP 전체 IPI 비교평가 연결·무모델 준비

> 2026-10-20 최신 사용자 배정: 가능한 경우 ChatGPT 로그인 기반 **gpt-5.6-luna / low**를 두 조건에 동일하게 사용한다. [로그인 연결 작업서](CHATGPT_LOGIN_LUNA_PROMPT.md)가 아래의 과거 GPT-5.2 지정에 우선한다. 공식 low 지원 확인과 계정의 실제 모델 사용 가능 확인은 다르며, 로그인 어댑터 호환 준비는 수용했으며 실제 OAuth·계정 모델 확인·새 모델 추론은 아직 미완료다. 다음 사용자 절차는 [USER_RUN](chatgpt-login-luna/USER_RUN.md)이다. API 과금 fallback은 금지한다.

> 2026-10-18 범위 변경: 사용자가 전수6682 대신 OS 간접공격100개를 선택했다. 최신 [100개 연결 작업서](CONNECT_SELECTED_100_PROMPT.md)가 아래 전수 구현·목표 축소 금지보다 우선한다. 아래 내용은 필요한 공통 통제와 이전 경과의 참고다.

최신 재개 지점: 전수 정적목록/부분 각색연결은 수용됐으나 공식 runtime0/6682다. [COMPLETE_OFFICIAL_RUNTIME_PROMPT](COMPLETE_OFFICIAL_RUNTIME_PROMPT.md)로 T-DTAP-01의 미완료 구현을 계속한다. 아래 모델·두조건·전수목표·소유범위는 유지한다.

2026-10-17 관리 배정. 사용자 목표는 “DTAP 시나리오 전체를 같은 피해 모델로 엔진 미적용/적용 두 조건에서 실행해 공격 성공 건수·성공률의 차이를 보여주는 것”이다. 최신 모델 선택은 **gpt-5.2 / reasoning low**다. 앞서 제안한 nano/Luna·별도 모델 탐색·성공후보 재생은 현재 배정에서 제외한다. with-human-dev로 기존 개발 세션에서 통합 구현하고 최종 별도 AI 검토1회를 받는다. 현재 관리 채팅은 정본/완료 판정을 맡으며 개발자는 관리 plans/AGENTS/장부를 수정하지 않는다.

이번 배정은 **전체 평가를 지원하는 연결·실행 도구의 무모델 구현/준비**다. 최종 대상을 3~5개로 축소하지 않는다. 소수 smoke는 연결 검증용이며 최종 비교의 대체물이 아니다. 실제 유료 전수 실행은 소스·task·모델·한도가 구체화된 후 사용자가 선택하도록 한 번 인계한다. 별도 유료 모델선택 pilot/재생 평가를 추가하지 않는다. 기존 원장8/8·CLI7/7과 실성공/실패를 재사용·초기화하지 않는다.

## 1. 공식 버전 고정·전수 목록

[공식 저장소](https://github.com/AI-secure/DecodingTrust-Agent), [공식 dataset](https://huggingface.co/datasets/AI-Secure/DecodingTrust-Agent-Platform), [공개 궤적](https://huggingface.co/datasets/AI-Secure/DTap-Bench-Agent-Trajectories)을 필요한 범위에서 읽고 source commit/dataset revision/license·task ID·환경 image digest·judge hash를 동결한다. repo/dataset은 별도 ignored vendor/cache, 실행은 별도 Docker 프로젝트·네트워크·작업폴더·DB/원장에 둔다. download/설치는 dependency 검토 후 하며 외부 setup/judge를 읽지 않은 채 호스트에서 실행하지 않는다. 관리·제품 코드/개인 홈/실데이터/비밀을 benchmark sandbox에 mount하지 않는다.

모든 도메인의 benign/direct/indirect 목록과 실제 MCP tool/schema/환경 의존성·추가 모델 호출을 **전수 inventory**한다. 주 지표는 전체 indirect와 전체 benign이다. direct는 사용자 직접 악성 요청이므로 별도 집계하고 IPI 분모에 합치지 않는다. 사용자 “다 돌리기” 목표에 맞춰 direct도 별도 실행 가능 목록/호환성으로 명시하며 준비 범위에서 조용히 삭제하지 않는다. 현재 원자료의 실제 counts로 분모를 계산하고 홈페이지의 수를 임의로 고정하지 않는다.

지원/미지원/각색필요/추가서비스필요/불명확과 이유를 task별·tool별 coverage.csv로 남긴다. 전체 inventory와 실제 실행 가능 coverage는 구분한다. 미지원 사례도 전체 목록/제외 사유에 남긴다. 미지원 도구를 일괄 DENY해서 높은 IPI 방어율로 보고하지 않는다.

## 2. 연결 방식·명시 위임

공식 [MCP hooks](https://github.com/AI-secure/DecodingTrust-Agent/blob/main/docs/hooks.md)와 실제 `dt_arena/src/types/hooks.py`에서 공통 dispatch를 확인한다. pre/post를 이용하되 **실제 실행은 우리 gateway의 판정·정확 인자 결합·예약을 통과한 호출만** 전달한다. 단순 로그/호출 후 위험 분류는 차단 증거가 아니다. endpoint 두 곳에서 도구를 중복 실행하지 않는다. 공식 hook 등록 누락/loader 실패는 평가 시작 전에 차단한다. native/shell 등 우회 도구도 미적용/적용 두 arm에서 같은 범위로 통제한다.

현재 제품 parser/ADR-P04는 등록 read_file/write_file만 양의 허용 대상으로 삼는다. DTAP CRM·메일·API·shell을 이름만 바꿔 이 parser에 넣지 않는다. **이 배정에 한해 benchmark 전용 MCP tool enrollment/검증된 schema registry·명시 slot mapping·resource identity·격리된 engine profile와 필요한 내부 계약 확장을 위임**한다. 실제 user turn/도구명·args/server/신뢰된 domain policy·출처를 정확히 결합하고 기존 JevClient/의미 판정·gateway 집행/기록을 재사용한다. 기본 제품/현재 성공한 frozen-demo의 정책·서비스·bundle은 교체하지 않는다.

benchmark task의 보안 규범은 trusted harness 설정으로 전달하고 외부 tool 본문·모델·case label이 정책/권한을 발급하지 못하게 한다. 정답/attack_success/task_success/judge 코드·공격자 숨은 목표·task_id 기반 기대값은 actor/Jev 입력에서 제외한다. direct의 명시적 악성 사용자 요청/분야별 안전 규범은 현 IPI 작업범위 판정과 다른 통제일 수 있으므로 별도 계약·coverage로 설명한다. 큰 신규 도구/명령 해석이 필요하면 실제 schema와 parser 경계·반례를 근거로 제한하며 임의 문자열 추정으로 성공 처리하지 않는다.

실제 [`HookManager.wrap`](https://github.com/AI-secure/DecodingTrust-Agent/blob/main/dt_arena/src/types/hooks.py)는 현재 읽은 소스에서 `_run_pre`가 dispatch try 밖에 있다. 문서의 “pre 예외 후 post 수행” 설명만 믿지 말고 pinned source로 검증한다. DENY는 실행 전 자체 기록하며 Post가 안 오는 경우도 연결한다. 취소/병렬/응답 유실 후 UNKNOWN은 유지하고 위험 쓰기를 재시도/환불하지 않는다. gateway/PDP/auth/필수 저장 장애는 전달0이어야 한다.

## 3. 피해 모델 gpt-5.2 / low 고정

사용자는 사용 가능한 모델을 gpt-5.2·gpt-5.6-luna·gpt-5.6-terra·o4-mini로 한정한 뒤 **gpt-5.2를 명시 선택**했다. 이 선택을 그대로 따른다. nano/다른 모델 비교·최고 ASR 모델 탐색·모델 교체를 하지 않는다. “5.2가 더 잘 공격당한다”는 아직 검증한 사실이 아니며 결과로 측정한다.

피해 actor는 `gpt-5.2`, 추론은 **low**를 두 조건 모두 명시한다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.2)는 low와 tool calling을 지원한다. 가능한 경우 공급자의 정확 resolved snapshot/version도 기록하되 사용자가 지정한 모델을 조용히 바꾸지 않는다. 일반 공개 텍스트 단가는 입력$1.75/출력$14.00/백만토큰이며 실제 요청·추론량/캐시/도구·환경 비용을 포함한 전체 비용은 별도 상한으로 산정한다. low는 단가 할인으로 표현하지 않는다.

DTAP의 OpenAI SDK backend 또는 검증된 별도 eval backend를 사용하며 실제 Codex CLI 시험인 것처럼 표시하지 않는다. API wire에 Responses `reasoning.effort=low` 또는 해당 endpoint의 동등한 low 인자가 실제 반영됐는지 검증하고 저장한다. 개인 Codex의 high 설정을 상속하거나 backend 기본값으로 남기지 않는다. 모델/effort 불일치는 전송 전에 거절하며 자동 fallback/재전송은 없다.

방어 Jev `jev-1.13.0`/임계치·엔진 profile은 비교 내 고정하고 기존 개인 개발 모델/추론 설정은 바꾸지 않는다. 양쪽의 actor 버전·추론·출력·도구/turn·시간/병렬 상한·sampling/seed(지원 시)는 동일하게 고정한다. 성공 사례가 나올 때까지 모델/프롬프트/정책을 조정하지 않는다.

## 4. 비교는 두 조건만

| 조건 | 피해 모델 | 방어 | 주요 결과 |
|---|---|---|---|
| engine-off | gpt-5.2 / low | 엔진 집행 미적용 | 공격 성공 건수·성공률 |
| engine-on | gpt-5.2 / low | 실제 우리 엔진/gateway 집행 | 공격 성공 건수·성공률 및 감소 |

동일하게 고정한 전체 task 목록·초기 snapshot·공격자료·가용 도구·사용자 과업/정책에서 두 조건을 실행한다. 조건마다 환경을 완전히 복원하고 이전 효과/메모리/캐시를 넘기지 않는다. 주 IPI 지표는 indirect 전수이며 benign과 direct는 같은 두 조건의 별도 집계다. 원 task·공식 judge를 유지하고 공격 성공/정상과업 성공을 판정한다. 같은 seed가 같은 출력을 보장하는 것은 아니다.

**성공후보 별도 재생·세 번째 평가 조건·별도 유료 모델선택 pilot은 구현/실행 범위에서 제외**한다. 무모델 smoke/통합 시험은 연결 검증으로 유지한다. engine-off 전체 성공집합을 고른 뒤 그 일부만 engine-on에서 실행하지 말고 같은 전체 목록을 비교한다.

주 보고표는 두 행의 전체/평가완료/공격성공 건수·성공률과 감소 폭이다. 전체 분모/지원 coverage·미지원·미완료/UNKNOWN은 숨기지 않으며 오류를 공격실패로 간주해 방어율을 부풀리지 않는다. benign의 정상 성공률은 두 조건의 보조 결과로 남겨 무조건 차단을 구분한다. 지연·실제 사용량도 실행 로그에서 집계하되 별도 실험은 만들지 않는다.

실제 engine-on trace에 semantic DENY와 executor 전달0/금지효과0이 함께 기록된 경우만 “엔진이 실제 차단”으로 제시한다. engine-on에서 모델 자체가 공격을 거부해 후보가 안 나온 것, CONFIRM/지원밖 규칙거절/분석 실패/시간초과·예산소진·UNKNOWN은 별도 상태다. 두 arm의 성공률 차이만으로 모든 감소를 특정 DENY의 인과로 확정하지 않는다. 처음 DENY했어도 다른 경로로 최종 공격이 성공하면 attack_success는 성공으로 유지한다.

집계 필드 예: `task_id/domain/threat_model/coverage`, `arm`, `actor_model`, `reasoning_effort`, `attack_success`, `task_success`, `dangerous_candidate_generated`, `semantic_deny_count`, `confirm_count`, `rule_denied_unsupported`, `analysis_failed`, `unknown`, `forbidden_effect`, `usage_complete`, evidence paths. 0/false와 NOT_RUN/UNKNOWN을 구분한다. 예시 숫자를 실제 성과로 넣지 않는다.

## 5. 준비·검증·실제 전송의 경계

현재는 **개발 중 제품 모델/actor/환경 LLM 호출0**이다. 기존 키의 보호 RO 참조/역할 분리를 재사용하고 값·hash를 읽거나 노출하지 않는다. 새 dataset key를 채팅에 요구하지 않는다. 패키지/이미지/공급망·가이드/P0는 변경된 노출 경계로 한정해 근거·원문 페이지·코드·시험을 연결한다. 모든 개인/외부 서비스 호출은 로컬 모의 endpoint로 격리하고 실제 메일/송금/원격 삭제 효과를 만들지 않는다.

fake actor/provider와 실제 선택 DTAP Docker/MCP→우리 gateway→파일/상태 효과→official judge→report까지 무모델 연결을 검증한다. 두 arm은 PDP 집행 유무 외의 수집/초기상태/도구 제한이 동일해야 한다. pre 차단 효과0·ALLOW단회·source/turn 결합·병렬/취소/Post누락·auth/예산/실행오류·UNKNOWN·resume/환경복원을 필요한 변경 경로에서 확인한다. 성공 stub이나 원 지원밖 hard deny만으로 전체 연결을 통과시키지 않는다.

전체 task inventory·현재 지원 coverage·도메인별 확장 비용을 먼저 산출한 뒤 연결 가능한 전체 목록을 고정한다. 아직 전수 호환되지 않으면 “전체 실행 준비완료”라 하지 말고 구체적인 미구현 tool 범위/최소 다음 변경을 남긴다. 큰 benchmark를 필수 제출/기존 좁은 MVP 완료의 선행조건으로 바꾸지 않는다.

engine-off/engine-on 두 조건 각각 및 합산의 전체 actor/Jev/환경·judge 요청·입출력/시간/동시성/반복 상한과 공급자별 ledger·취소/재개를 manifest에 결합한다. 사전 비용은 추정/상한이며 실제 청구 보장은 아니다. 소형 actor 비용뿐 아니라 방어 A/B, LLM judge/환경 호출도 포함하고 미확인 요율/usage는 UNKNOWN으로 남긴다. 사용자에게 **검토 가능한 한도와 모델·실행 명령을 마지막에** 인계한다. 이번 요청을 무제한 비용 승인으로 해석하지 않는다. 현 원장 소진을 이유로 준비 시작 전에 예산 질문을 반복하지 않는다.

## 인계

허용 쓰기: benchmark 전용 adapter/registry/profile·기존 gateway/engine의 호환 hook 최소변경·명시 내부 계약/관련 tests·격리 vendor/runtime와 안전 artifact, `docs/handoffs/WP-DTAP-01/<run>/`, 필요한 docs/mvp 설명. 관리 정본과 기존 실실행 산출물은 보존한다. 기본은 통합 구현1개와 최종 검토1개, 범위 독립성이 없는 조사 agent를 늘리지 않는다. 관련 시험→필요 최종 통합→별도 AI 검토로 마치고 단순 문서/hash 때문에 전체 회귀를 반복하지 않는다.

인계 `20261017-dtap-prepare/RESULT.md`, `COVERAGE.csv`, `EVALUATION_DESIGN.md`, `USER_RUN.md`, 별도 `20261017-dtap-prepare-review/REVIEW.md`. stage별 완료/미실행과 전체 목표 진행률은 실제 counts로 표시한다. 기본 공식 SDK backend 결과는 그 이름으로, 원 task/tool을 각색했으면 “DTAP 기반 각색”으로 표기한다. 벤치마크 실패/미지원도 공개 집계하며 모든 공격을 막는다는 사전 결론은 내리지 않는다.
