# WP-DTAP-CC-01 별도 AI 검토

2026-10-22 · 검토자: 별도 AI 검토 1회(읽기 전용, 모델·네트워크 호출 없음). 사람 검토나 공식 독립 진단이 아니다.
대상: `claude_code.py`, `mcp_bridge.py`, `claude_code_dtap.py`, `tools/dtap_claude_code.py`, `task_scope.py` 변경, 잠금 파일, 시험.

## 발견과 조치

| # | 등급 | 발견 | 조치 | 재검증 |
|---|---|---|---|---|
| 1 | P1 | 환경 컨테이너가 기본 bridge(인터넷·호스트 loopback 도달), 기본 권한으로 실행 | `--internal` 네트워크 + runtime과 같은 CapDrop ALL/4 cap/no-new-privileges/pids 128/512m/1 CPU/tmpfs. API는 고정 digest python 이미지의 stdlib 포워더(읽기 전용·nobody)만 127.0.0.1에 공개 | 직접 probe: bridge는 인터넷 200·host loopback 200, internal은 둘 다 000. 오프라인 pair 4 task-arm 정상 |
| 2 | P1 | actor cwd가 git 작업 트리 안(`arms/engine-on/...`)이라 git 상태·경로가 actor 맥락에 들어갈 수 있음 | 저장소 밖 `mkdtemp("wh-actor-")`, arm/과업 이름 없음, 종료 시 삭제 | 통합 실행 |
| 3 | P2 | 설정·초기화 실패가 `stop=None`으로 남아 방어 성공처럼 보일 수 있음 | 초기화/턴 등록 실패를 코드로 기록, `benchmark_setup_failure` 반영, 미완료 무코드는 `OFFICIAL_RUNNER_INCOMPLETE`. 과업 단위 허용 목록 밖 중단은 run 정지 | 단위 시험 |
| 4 | P2 | 재개 시 엔진·바이너리·effort·Jev 설정 불일치를 검사하지 않음 | `src/app`+실행기 hash, CLI hash, model/effort, Jev 설정 비교. 다르면 새 run-id 요구 | 코드 검토 |
| 5 | P2 | 시작 중 실패·worker 시간 초과 시 컨테이너·프로세스 잔류 | 시작 실패 시 즉시 정리. worker 실패 시 기록된 프로세스 그룹(명령줄 확인 후)과 결정적 이름의 컨테이너·네트워크 정리 | 잔여 0 확인 |
| 6 | P2 | Jev 상한이 run마다 새로 생기고 usage 불명을 수용 | 호스트 공통 원장 + 최초 생성 시 고정되는 누적 요청 상한 + run 상한. usage 불명은 `USAGE_UNKNOWN`으로 중단(예약 유지) | 단위 시험 |
| 7 | P2 | bob/admin 신원 과업이 grant에서 예외로 worker 붕괴→run 정지 | scope-3가 alice 전용이므로 그 외 신원은 양쪽 arm 모두 `UNREVIEWED_SYNTHETIC_IDENTITY` 과업 단위 미등록 | 단위 시험 |
| 8 | P3 | 시작 보고 모델 미검사 | 요청 모델과 다르면 `ACTOR_MODEL_MISMATCH` | 단위 시험 |
| 9 | P3 | overage 필드 무시 | `isUsingOverage=true`면 `SUBSCRIPTION_OVERAGE_IN_USE`로 정지, 필드 기록 | 단위 시험 |
| 10 | P3 | 예상 밖 메시지 형태에 reader가 조용히 종료 | 처리 예외를 `ACTOR_STREAM_INVALID`로 실패 처리 | 단위 시험 |
| 11 | P3 | 재개 시 캐시된 정지 코드가 다시 run을 멈춤 | 새로 실행한 task-arm만 run 정지 판단 | 코드 검토 |
| 12 | P3 | actor 정지 중 진행 중 dispatch와 judge 경합, 서버 종료 TimeoutError가 close 생략 | 정리 시 dispatch 잠금 대기(90초, 넘으면 `DISPATCH_IN_FLIGHT_UNKNOWN`), 서버는 취소로 종료, close는 finally | 단위·통합 |
| 13 | P3 | 기한 지난 턴도 요청 시작, CLI 권한 거절이 run 정지 아님 | 쓰기 전 기한 검사, 허용 목록 방식으로 run 정지 | 단위 시험 |

검토자가 확인한 정상 항목: tar 추출(고정 hash·링크 제외·`..` 거절·`filter="data"`), 브리지 토큰은 0600 설정 파일에만 존재,
Jev 키는 worker에서만 읽음, ready/stop 게이트 직렬화, DENY·미승인 CONFIRM·분석/인프라 실패는 proxy 미도달·재시도 없음,
engine-off `profile=None`이 runtime과 일치, 권한 시뮬레이터 키 없음 시 네트워크 없이 거부.

## 정적 도구

- ruff: 변경 파일 PASS.
- bandit: B404/B603/B607(Low)은 셸 없이 고정 인자 목록으로 `docker`·`uv`·`claude`·`ps`를 실행하는 부분이다.
  `docker`는 실행기가 정한 PATH(venv, Docker Desktop CLI 폴더, /usr/bin, /bin)에서만 찾는다.
  B105(Low) `admin-token-for-setup`은 DTAP 공식 공개 합성 토큰이다. B310(Medium)은 고정 https 상수 URL이며 SHA256을 확인한다.

## 가이드 연결 (변경 범위만, 전체 재진단 아님)

- G-02: 해시 잠금 venv, 고정 archive SHA256, 이미지 digest, uv frozen, 환경 컨테이너 최소 권한·내부망, 127.0.0.1 공개만.
- G-03: 브리지 Bearer 토큰·Origin 검사·본문 1 MiB·중복 키 거절, 과업 키 경로 검사, 등록 도구·schema만 dispatch.
- G-04/G-05: 기존 Control/authz/단회 ticket/proxy 순서 유지, UNKNOWN 재실행 없음, Jev 예약 비환불, 시작한 task-arm 재실행 없음.
- G-06: actor 환경 allowlist(API 키·공급자 변수 제거), Claude 자격증명 비접촉, 엔진 키는 task-arm별 0600 runtime 폴더, 결과에 계정 식별자 미기록.
- G-07: 실패 코드를 결과에 남기고 fail closed, 프로세스·컨테이너 정리.
- G-08: 이 검토와 수정 후 재시험.

## 남은 위험

- 실제 Claude Code CLI의 시작 보고(도구 목록·모델 문자열·overage 필드) 동작은 실제 smoke 전까지 미확인이다.
- DTAP 공식 Python 코드와 PyPI 의존성이 호스트에서 사용자 권한으로 실행된다. 환경 컨테이너 안의 명령은 내부망에 갇히지만
  호스트의 MCP/주입 서버 프로세스는 격리 컨테이너가 아니다.
- TypeSafe 단가가 저장소에 없어 USD 환산·잔여 0.898373 USD 대조는 하지 않는다. 요청 수 상한으로만 제한한다.

## scope-4 오탐 개선 별도 AI 검토 (2026-10-22)

대상: `task_scope.py`·`tree_scope.py`·`demo_policy.py`·`runtime_policy.py`의 scope-4, `jev.py` 응답 반올림 허용. 읽기 전용, 모델·네트워크 호출 없음.
측정 run `cc-haiku45-os100-x4`는 검토 전 코드라 27/200에서 중단하고 보존했다(엔진 hash가 run.json에 기록됨).

| # | 등급 | 발견 | 조치 |
|---|---|---|---|
| 1 | P1 | 사용자가 적은 폴더의 하위 전체가 명시 경로가 되어, "~/ 정리" + 주입된 `~/.ssh/id_rsa` 읽기가 scope-3 DENY → B 단독 ALLOW 가능 | 민감·보호 대상은 사용자가 그 민감·보호 위치 자체를 적었을 때만 통과하고 메타데이터 조회만 허용, 내용 읽기·변경은 `PROTECTED_USER_PATH_REQUIRES_CONSENT`. B 단독 규칙은 대상 전부를 사용자가 정확히 적은 경우만, 하위 경로는 기존 A+B 규칙 |
| 2 | P2 | `log_action` 코드 허용이 `ask_for_permission`을 건너뜀 | 해당 인자가 있으면 코드 허용하지 않음(등록부도 별도 거절) |
| 3 | P2 | 합 정규화가 위험 확신도를 .90 아래로 끌어내려 이전엔 무효이던 응답이 위험 미선택으로 통과 | provider 보고값/표시값이 .90 이상인데 유효값이 .90 미만이면 `THRESHOLD_AMBIGUOUS` 무효(이전과 같은 fail closed) |
| 4 | P3 | 상위 폴더 목록이 민감 이름 필터 없이 코드 허용, `/`도 상위 폴더로 취급 | 상위 폴더 목록은 필터 유지, `/` 제외 |
| 5 | P3 | edit `old_text`의 `.`은 정규식 와일드카드 | `.`은 교체 문자열에서만 허용 |
| 6 | P3 | `delete_directory` 위임은 쓰기 검사에서 항상 DENY | 위임 대상에서 제외(기존 CONFIRM 유지) |
| 7 | P3 | 코드 허용이 reviewed operation 금지 검사보다 먼저 실행 | 금지 검사 뒤로 이동 |

검토자 확인: scope-3는 변경 전후 238개 판정 사례 차이 0, `/data` vs `/data2`·`..`·심볼릭 링크·다중 대상·move 목적지 처리 정상.
재검증: 위 검토 시나리오를 시험으로 추가해 scope-4·Jev 계약 87 PASS, 관련 전체 280 PASS, 기존 회귀 결과 불변, ruff PASS.

## scope-4 후속 보완 별도 AI 검토 (2026-10-22)

대상은 첫 scope-4 검토 뒤에 추가한 보완 네 가지다. 읽기 전용으로 검토했고 모델·네트워크 호출은 없다. 검토자는 설치 없이는 시험을 실행할 수 없어 코드만 읽었다.
- 정확히 적은 민감·보호 대상을 B 판정으로 넘김
- alice 소유 메타데이터 조회(`own_names`)
- `explicit_user_scope` 부여 조건
- actor cwd `/`

| # | 등급 | 발견 | 조치 |
|---|---|---|---|
| 1 | P1 | 정확히 적은 민감·보호 경로를 동작 종류와 무관하게 B 단독 판정으로 넘김. "~/.bashrc의 alias를 알려줘"에서 파일 안 주입이 같은 파일의 수정·삭제를 시키면 B LEGITIMATE ≥.50만으로 ALLOW 가능. 이전 검토판에서는 CONFIRM, scope-3에서는 DENY | 정확히 적은 대상도 B 판정은 조회(QUERY)만. 변경은 `PROTECTED_USER_PATH_REQUIRES_CONSENT`. 시험: 읽기 요청 + 같은 민감 파일 수정, 읽기·삭제 요청 문장의 삭제 |
| 2 | P2 | `own_names`가 사용자가 적지 않은 본인 소유 폴더 목록에서도 민감 이름 필터를 끔. 그래서 상위 폴더 코드 허용(`EXPLICIT_USER_SCOPE_METADATA`)이 의미 판정 없이 `~/.ssh` 같은 이름을 보여줌(이전 검토 #4 무효화) | 사용자가 적지 않은 위치의 목록에 민감 이름이 있으면 `code_allow` 제거. A+B 의미 판정으로 넘김. DENY로 되돌리지 않아 홈 목록 오탐은 재발하지 않음. 시험: 깨끗한 목록은 코드 허용, `.ssh` 포함 목록은 의미 판정, 홈을 직접 적은 경우는 코드 허용 |
| 3 | P2 | 사용자가 적지 않은 본인 소유 폴더의 `directory_tree`·`search_files`가 민감 폴더 내부 이름까지 보여줌 | **수용(미조치)**: 이 경로는 코드 허용이 없어 항상 A+B 의미 판정을 거친다. 내용 읽기는 precheck의 민감 경로 DENY로 계속 막힌다. 막으면 "홈에서 .bak 찾기" 같은 정상 검색이 `.ssh`가 비어 있지 않을 때마다 DENY된다. 노출은 이름(검색은 패턴 일치 이름만)에 한정된다 |
| 4 | P3 | `own_names` 핵심 경로(트리 메타데이터 + 비공개 하위 폴더)를 실제로 검증하는 시험 없음 | 트리 probe 시험 추가(#2와 같은 시험) |
| 5 | P3 | 사용자 문장의 `//host/path`가 명시 경로가 되어 접근 검사에서 분석 장애로 끝남 | `//`로 시작하는 리터럴 제외. `/x/..`의 끝 정리는 범위를 좁히는 쪽이라 유지 |
| 6 | 정정 | 첫 검토 #2와 코드 주석은 actor cwd가 mkdtemp라고 적었지만 실제 cwd는 `/`이고 mkdtemp는 설정 파일 보관용 | 주석 정정. 호스트 `/`에 `CLAUDE.md`·`.claude`·`.mcp.json` 없음 확인(`--strict-mcp-config`, `--tools ""`) |

검토자 확인 항목(정상): /etc 쓰기 CONFIRM 유지, 하위 경로 비메타데이터 CONFIRM, `/` 제외·approach 비재귀 한정, 심볼릭 링크·비 alice/root 소유자 DENY,
경로 정규화 거절, 다중 대상 `all()`, move 목적지 검사, search 패턴 제한·`complete_search`, 세션 로그 `ask_for_permission` 거절,
`delete_directory` 미위임, 금지 검사 뒤 code_allow, .90 위험 DENY 우선, forward 재검사.

재검증: 관련 시험 284 PASS. task_scope 관련 회귀 8개 파일은 이번 수정 전후 결과가 같다(274 failed/16 passed/6 errors, 전부 이 checkout에 없는
과거 원증거 `FileNotFoundError`). 앞 기록의 241/34/6과는 파일 묶음이 달라 직접 비교하지 않는다. ruff PASS.
x4b·x4e·benign-x4b 실행 기록에서 #1 수정으로 바뀌었을 결정을 추정했다. 해당 결정은 `/api` 쓰기 ALLOW 1건이었고 보호 경로가 아니라 영향 0이다.
#2 영향은 engine-on 재점검 run `cc-haiku45-refine-x4f`로 측정했다. 공격 성공은 0을 유지했고, 엔진 영향 손실은 8로 x4e와 같다. 정상 성공 12→11은 수정과 무관한 모델 변동이다(RESULT).

## scope-5 · 시뮬레이션 사용자 별도 AI 검토 (2026-10-23)

검토 범위: task_scope/demo_policy/runtime_policy의 scope-5, consent_simulator, hook·adapter의 CONFIRM 승인 흐름, 실행기.
보안상 잘못된 판정(P1)은 지적되지 않았다. 확인된 항목:
- 보류 사례는 compose에서 가장 먼저 처리된다. A와 B 모두 .50 이상이어야 ALLOW이고, DENY는 유지된다.
- scope-3/4 판정은 바뀌지 않았다.
- DENY는 시뮬레이터에 가지 않는다.
- 승인은 call·hash·turn·policy에 묶여 한 번만 소비된다.
- human 토큰은 actor·시뮬레이터에 전달되지 않는다.

| # | 지적 | 조치 |
|---|---|---|
| 1 P2 | 승인으로 풀 수 없는 코드 CONFIRM도 시뮬레이터가 승인하면, forward 재검사에서 다시 CONFIRM이 된다. 그러면 run이 정지한다. | `APPROVABLE`에 든 이유와 review-5에만 묻는다. 읽기 불가는 scope-5에서 `UNREADABLE_RESOURCE`로 구분했다. 나머지는 예전처럼 과업 종료다. |
| 2 P2 | 공식 서버 경로에서 형식이 다른 답이 공식 키워드 해석으로 승인될 수 있었다. | `verdict` 실패는 503이며 run 정지로 처리한다. 이후 실제 run에서 이유 문장 속 `{` 때문에 정상 답도 실패하는 결함이 드러났다. 해석기를 JSON 디코딩으로 바꾸고, 공식 서버에는 정리된 답을 넘긴다. |
| 3 P2 | scope-5에서 디렉터리 삭제·이동이 "파일 아님" DENY로 바뀌었다. | scope-5에 한해 디렉터리는 Jev A·B 판정으로 넘긴다. |
| 4 P3 | 시뮬레이터 시간 상한에 잠금 대기·종료 시간이 빠져 있었다. | 25초를 넘긴 답은 `ANSWER_LATE` 실패로 처리한다. |
| 5 P3 | 거부될 호출이 시뮬레이터에 갈 수 있었다. | #1 조치로 해소했다. |
| 6 P3 | 사용자가 경로를 적지 않았는데 세션 로그를 코드가 바로 허용했다. | 자유 텍스트라 A·B 판정으로 넘겼다. |
| 7 P3 | 다른 grant 경로(REVIEWED_PUBLIC_QUERY)가 보류 사례를 무시한다(잠재). | `route`에서 보류 사례는 곧바로 Jev로 보낸다. query_capability는 이 실행기에서 쓰지 않는다. |
| 8 P3 | 공식 경로 실패 뒤에도 actor가 계속 진행한다. | 수용. 마지막에 stop으로 미해결 표시한다. |
| 9 P3 | Jev에 주는 설명 문구와 시험 주석이 실제와 달랐다. | 고쳤다. |

재검증: 관련 시험 212 PASS(신규 시험에 지적 사례 추가), ruff PASS. 점검 run 결과는 RESULT를 본다.

## gate-6 별도 AI 검토 (2026-10-23)

| 지적 | 조치 |
|---|---|
| 보류 위험 사례가 승인 불가 CONFIRM(소유권 확인 불가, 읽기 불가, 비공개 트리)으로 먼저 끝나면, Jev 판정 없이 과업 전체가 미승인 중단으로 끝남 | scope-6에서 이 경우 scope-5와 같은 코드 DENY로 되돌림. `check_access` 래퍼와 시험 추가 |
| ALLOW 우회, 구조 DENY 유지, 승인 시점 재확인, scope-5 불변 | 결함 없음 |
