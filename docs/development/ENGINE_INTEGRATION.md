# 엔진 기본 정책과 팀원 어댑터 연결

기준: 2026-10-22. 팀원이 현재 엔진을 clone하고 자체 DTAP/AgentDojo 어댑터를 연결할 때의 안내다.
기존 실행 기록은 당시 정책 결과이며 아래 변경으로 재채점하거나 재실행하지 않는다.

## 기본 .50 정책

공통 규칙은 [`candidate_policy.py`](../../src/app/transparent/candidate_policy.py)에 있다.
ALLOW 후보는 **검증된 A의 원래 선택이 WITHIN_TASK + B가 LEGITIMATE + B 유효 확신도 ≥ .50**이다.
권한·등록 도구·정확한 인자·출처 무결성·실행 예약은 별도로 통과해야 한다.
기존 위험 DENY를 우선하며 위험 관측 필터 .90과 공식 확률/확신도 검증을 바꾸지 않는다.
숫자는 정책 설정이며 실제 정확도가 보정·입증됐다는 뜻이 아니다.

| 진입점 | 기본 동작 |
|---|---|
| `transparent.jev_config.make_policy(client)` | 현재 제품 정책 `JevPolicyCurrent`, 등록 파일 MCP의 .50 허용 규칙 |
| `transparent.server`, `HOOKGW_PDP=JEV`, profile 생략 | 위 현재 정책 선택. `current_candidate_1`은 호환용 선택자이며 실제 policy는 `hookgw-2026-10-22-jev-current3-allow50` |
| `benchmark.runtime_policy.RuntimePolicy(..., enabled=True)` | 별도 profile 없이 현재 A/B 질문과 .50 규칙 적용. 서버가 검증한 정확한 작업 권한 필요 |
| 기존 DTAP 격리 프로필 | 기존 자원/옵션/동의 검사 위에서 동일한 공통 .50 규칙 재사용 |
| 이 PC의 AgentDojo 정책 | 원 시뮬레이션 환경 검증 위에서 같은 규칙 재사용. 해당 어댑터/실행기는 이번 게시에서 제외 |
| 명시한 `legacy_v2`, `semantic_confirm_v3`, `behavior_v5`, `behavior_v5p1` | 과거 정책 보존. 최신 기본 정책을 선택한 것으로 간주하지 않음 |

Jev provider 활성화·API키·유료 요청 승인은 별도 설정이다. 기본 정책 변경이 provider를 켜거나 호출을 발생시키지 않는다.
제품 파일 정책의 등록 범위 밖 native 도구에 새로운 권한이나 .50 특례를 부여하지 않는다.

## 지금까지의 CONFIRM 개선이 들어간 위치

| 개선 | 현재 위치와 적용 범위 |
|---|---|
| 정상 데이터 활용·준비 행동과 외부 추가 지시 채택 구분 | `transparent/candidate_questions.py`. 제품 현재 정책과 현재 런타임 질문이 공유 |
| 현재 사용자 요청·이전 실제 사용자 턴·현재 후보 분리 | `jev_core_v5p1.py`, `runtime_policy.py` |
| 읽기 결과·이전 보고서·쓰기 영수증의 역할 구분 | 같은 공통 질문/입력 경로. 영수증을 내용의 사실 인증으로 쓰지 않음 |
| B 정상 확신도 .50 | 공통 `transparent/candidate_policy.py`, 제품 현재 기본 정책 및 기본 런타임에 연결 |
| 이미 요청한 A/B를 모두 수집하고 실제 장애를 우선 처리 | `runtime_policy.py`. 이 변경만으로 배치 실패 정책이 바뀌지는 않음 |
| 정확히 검증된 조회의 의미 호출 생략·검사 한도 거절 뒤 대안 지속 | DTAP의 `query_capability.py`, `tree_scope.py`, `denial.py` 등. 도구/자원별 어댑터 기능 |
| `get_current_day` 구현 사실을 Jev에 설명 | AgentDojo 어댑터. 다른 도구에도 자동 적용되는 공통 허용 특례가 아님 |
| 잘못된 Jev 응답 사례만 중단하고 다음 사례 지속 | 이 PC의 AgentDojo 배치/요청 원장. 이번 게시 범위 밖이며 엔진의 잘못된 응답 거절은 유지 |
| Gemini 키 순환·429 처리·요청 한도 | provider/실행기. 엔진 판정 정책과 별개 |

A가 OUTSIDE_TASK/UNCERTAIN이거나 B가 불확실/.50 미만인 경우, 실제 동의가 필요한 경우에는 CONFIRM이 남는다.
질문 개선과 문턱 변경만으로 실제 모델의 정상 과차단이나 공격 방어 성능이 해결됐다고 해석하지 않는다.

## 팀원이 연결할 경계

1. 실제 사용자 턴과 원 환경의 도구 schema/identity를 제공하고 action/target/options/payload를 정확히 파싱한다.
2. 도구 결과와 설명을 서버가 수집해 원문/hash/완전성/역할을 보존한다. 공격 정답·judge 결과는 actor/Jev 입력의 권한 근거가 아니다.
3. 서버가 검증한 자원·효과 권한을 연결한다. 기본 RuntimePolicy의 `reviewed_operations`는 request/registry/schema/candidate 해시에 결합한다. 도구를 실행할 수 있다는 주장이나 외부 텍스트의 `authorized` 값으로 만들지 않는다.
4. `Engine.authorize()` 이후 ALLOW 또는 정확히 결합한 단회 승인만 `Engine.forward()`로 예약하고 원래 도구를 실행한다. 결과/유실을 관측·기록한다. 순수 정책 함수의 ALLOW만으로 직접 실행하지 않는다.
5. OFF/ON의 입력·초기 환경·공격을 맞추고, 채점 완료·CONFIRM·UNKNOWN·인프라 중단·코드 DENY·Jev 의미 DENY를 구분한다.

DB·키·로그인·과거 bundle/원장은 clone에 포함하지 않는다. 새 환경과 별도 provider 설정을 사용한다.
과거 bundle을 마운트하는 Compose는 최신 소스를 자동으로 읽지 않는다.
최신 코드 연결 확인에는 `compose.team.yaml`이 현재 `src/`를 직접 마운트한다.

## 검증 범위

새 기본 정책의 .50 경계, 확신도 미승격, 위험/범위 충돌, 잘못된 응답/출처 차단,
정확한 권한, 단회 예약과 정책 변경 후 기록 보존을 무모델 시험으로 확인한다.
관련 시험은 `tests/hookgw/test_default_candidate_policy.py`다. 기존 V5P1 시험은 과거 .90 정책의 회귀로 유지한다.
실제 DTAP/AgentDojo 성능이나 모든 native 도구 보호를 이 시험으로 주장하지 않는다.

YAML별 용도는 [CONFIG_FILES](CONFIG_FILES.md)를 참고한다.
