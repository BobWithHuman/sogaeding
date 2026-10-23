# DTAP OFF/ON — Claude Code 구독 actor 실행 안내

2026-10-22 · macOS 호스트 · actor는 이 PC의 `claude` CLI(구독 로그인), engine-on 판정은 TypeSafe Jev.

아래 명령은 안내일 뿐 실행 승인이 아니다. 실제 실행은 사용자가 선택한다.

## 무엇을 쓰고 무엇을 쓰지 않나

- actor: 수정하지 않은 `claude -p`를 전용 설정 폴더의 Claude 구독 로그인으로 실행한다.
  API 키 환경변수는 자식 프로세스에 전달하지 않고, 시작 보고의 `apiKeySource`가 `none`이 아니면 즉시 중단한다.
- 실행기는 Claude 로그인 토큰을 읽거나 복사하거나 전달하지 않는다. 로그인은 Anthropic 자체 흐름으로 사용자가 1회 한다.
- 구독 사용량을 쓴다. 한도 거절(`rate_limit_event` rejected) 시 run 전체를 멈춘다.
  claude.ai 설정에서 **추가 사용량(extra usage) 결제가 켜져 있으면 한도 이후 과금될 수 있다.** 과금 0을 원하면 먼저 끈다.
- engine-on의 Jev는 별도 TypeSafe 키와 요청 상한을 쓴다(유료). engine-off만 돌리면 Jev 호출은 0이다.
- DTAP 권한 확인 시뮬레이터(LLM)는 키가 없어 쓰지 않는다. `ask_for_permission=True` 호출은 양쪽 arm 모두
  엔진 등록부가 같은 규칙으로 거절하고 그 과업을 끝낸다(컨테이너 runtime과 같은 규칙).

## 1회 준비

```bash
cd ~/withHuman/sogaeding
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv artifacts/dtap-cc/venv
artifacts/dtap-cc/venv/bin/pip install --require-hashes --no-deps -r harness/dtap-cc/requirements.lock

# 평가 전용 Claude 로그인(브라우저). 평소 쓰는 ~/.claude 설정·훅·메모리와 분리된다.
mkdir -p -m 700 ~/.config/with-human/claude-dtap
CLAUDE_CONFIG_DIR=~/.config/with-human/claude-dtap ~/.local/bin/claude auth login --claudeai

# 고정 DTAP 소스(해시 확인)·환경 이미지·MCP 서버 잠금 예열·로그인 확인. 모델 호출 없음.
artifacts/dtap-cc/venv/bin/python tools/dtap_claude_code.py prepare
```

engine-on을 돌릴 때만 TypeSafe 키를 둔다.

```bash
install -m 600 /dev/null ~/.config/with-human/jev.api-key   # 그다음 키 한 줄을 붙여 넣는다
```

## 첫 실제 확인 (구독만, Jev 0)

```bash
artifacts/dtap-cc/venv/bin/python tools/dtap_claude_code.py run \
  --run-id cc-smoke-off-1 --tasks @harness/dtap-cc/smoke-tasks.txt \
  --arms engine-off --model claude-haiku-4-5
```

과업 2개 × engine-off. `claude-haiku-4-5`는 effort를 지원하지 않으므로 `--effort`를 생략한다
(effort 지원 모델에서만 `--effort low` 등을 붙인다). 첫 시작 보고에서 도구 목록·인증 출처·모델 문자열이 기대와 다르면 즉시 멈추고 이유를 남긴다.
`ACTOR_MODEL_MISMATCH`면 `runtime-events.json`의 `actor_init.model` 값을 확인해 그 정확한 문자열로 새 run-id를 쓴다.

## OFF/ON pair (Jev 유료)

```bash
artifacts/dtap-cc/venv/bin/python tools/dtap_claude_code.py run \
  --run-id cc-pair-1 --tasks @harness/dtap-cc/smoke-tasks.txt \
  --model claude-haiku-4-5 --jev-requests 40 --jev-total-requests 200
```

- `--jev-total-requests`는 이 PC의 모든 run을 합친 TypeSafe 요청 상한이다. 처음 원장을 만들 때 고정되고
  이후 run은 같은 값만 허용한다(새 run-id로 상한이 초기화되지 않는다). 원장: `artifacts/dtap-cc/typesafe-ledger.sqlite3`.

- 과업마다 engine-off → engine-on 순서. 각 task-arm은 새 환경 컨테이너(인터넷·호스트 접근이 없는 내부망)·새 엔진 DB에서 시작한다.
- `--jev-requests`는 run 전체 TypeSafe 요청 상한이다. 요청마다 64k 토큰을 예약하고 실패해도 환불하지 않는다.
- 같은 `--run-id`로 다시 실행하면 끝난 task-arm은 건너뛰고, 시작했지만 결과가 없는 task-arm은
  `UNKNOWN_PREVIOUS_ATTEMPT`로 남기며 다시 돌리지 않는다. 설정을 바꾸려면 새 run-id를 쓴다.

## 결과 보기

```bash
artifacts/dtap-cc/venv/bin/python tools/dtap_claude_code.py status --run-id cc-pair-1
```

`artifacts/dtap-cc/runs/<run-id>/`의 `summary.md`·`summary.json`, task-arm별 `result.json`·`runtime-events.json`·`logs/`.

| 표시 | 뜻 |
|---|---|
| `task_success` / `attack_success` | DTAP 공식 judge(규칙 코드) 결과 |
| `ALLOW/DENY/CONFIRM` | 엔진 PRE 판정 수. engine-off는 모두 `BENCHMARK_ENGINE_OFF` ALLOW |
| `executed` | 실제 upstream 실행 수 |
| `CONFIRM_UNAPPROVED` | 미승인 CONFIRM으로 그 과업 종료(자동 승인 없음) |
| `UNSUPPORTED_*` | 등록부가 actor 인자를 거절해 그 과업 종료(양쪽 arm 동일 규칙) |
| `UNREVIEWED_SYNTHETIC_IDENTITY` | alice 외 신원 과업. 양쪽 arm 모두 미등록 처리 |
| run `stopped` | 구독 한도·overage·로그인/API키/모델 가드·분석/인프라 장애·예상 밖 상태. 이후 과업은 시작하지 않음 |

무모델 시험 통과나 일부 pair 결과를 전체 방어율로 해석하지 않는다.
