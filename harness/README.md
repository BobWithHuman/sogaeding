# with-human 개발 하네스

## 현재 작업의 간결한 실행 기준

2026-10-18 사용자 지시: AgentDojo는 후순위다. 현재는 [WP-ENGINE-DEMO-02](../docs/handoffs/WP-ENGINE-DEMO-02/START_PROMPT.md)의 엔진 routing·격리.50 허용·DTAP 준비만 수행한다. 아래 오래된 T-00/세도구/전체시작 절차는 당시 설명이며 현재 준비 상태가 아니다.

- 처음에는 AGENTS·스킬·현재 작업서 각1회와 변경 함수·관련 시험만 읽는다. 과거 계획/PDF/로그는 필요한 부분만 조회한다.
- 최초 재현 → 최소 수정 → 관련 시험 → 최종 관련 통합1회 → 별도 AI검토1회를 기본으로 한다. 조사용 보조 AI는 기본으로 추가하지 않는다.
- 소스 변경·실패·새 우려가 있을 때만 영향 범위를 다시 검사한다. 문서 수정이나 동일hash 기록 때문에 통과한 전체 시험을 반복하지 않는다.
- 로그는 안전한 파일에, 모델에는 핵심 실패/변경/결과만 출력한다. 최종 RESULT·USER_RUN·별도 REVIEW를 기본으로 두고 단계별 중간 인계를 늘리지 않는다.
- 권한/출처/인자 결합, DENY 실행0, 승인 단회, UNKNOWN 미재시도, 비용상한, 적용P0·필수 가이드 근거는 유지한다. 기존 적용성/진단 근거는 재사용하고 변경 영향 부분만 갱신한다. 미검사를 PASS로 쓰지 않는다.
- 개인 모델/추론/로그인은 바꾸지 않는다. 개발 AI 토큰·제품 actor/Jev 요금과 무모델 시험·실제 모델 성능을 구분한다.

현재 작업서가 실행 범위를 정한다. 아래 역사 설명 때문에 초기 환경이나 하네스를 다시 만들지 않는다.

이 폴더는 **오늘 MVP를 구현하는 Codex CLI의 작업 안내·역할·검증 흐름**이다. 제품은 별도로 개발할 MCP Gateway/PDP와 사용자 작업·승인·이력 화면이다. 하네스 문서를 설치해도 제품의 차단 기능이 생기지 않는다.

단일 진입 스킬은 [with-human-dev](skills/with-human-dev/SKILL.md)이고 필요한 역할·워크플로·증거 기준만 참조 파일에서 읽는다. 작업 장부는 [build_tasks.json](build_tasks.json)이며 [원래 개발 작업표](../docs/mvp/04_traceability_and_work_breakdown.md)의 T-00~T-10을 따른다. Docker·의존성·준비 검증을 마친 **T-00만 DONE**이다. 제품 작업 T-01~T-10은 TODO이며 실제 제품 수용시험은 NOT_RUN이다.

최신 [관리 계획](../docs/plans/00_CONTROL_CENTER.md)에 따라 전역 작업 장부의 최종 판정은 관리 세션이 맡고, 구현 세션의 통합 담당은 배정 코드·설정만 단일 작성자로 통합한다. 결과는 [인계 양식](../docs/handoffs/RESULT_TEMPLATE.md)으로 제출한다. 필수 가이드 준수를 위한 추가 T-S01과 SPEC-3 전송 기준 전환은 [오늘 계획](../docs/plans/02_today_mvp.md)과 [ADR-S01](../docs/plans/decisions/ADR-S01.md)을 따른다. 기존 역할 설명의 쓰기 범위도 현재 work pack의 명시 소유권 안에서 적용한다.

## Codex에서 사용

저장소에서 Codex가 발견하는 `.agents/skills/with-human-dev/`에 설치를 마쳤다. `harness/skills/with-human-dev/`는 버전 관리하는 원본이다. 두 사본을 별개로 수정하지 않고 원본에서 수정한 뒤 설치본을 동기화·검증한다. 루트의 개발 안내와 검증 명령은 현재 프로젝트 README와 `docs/mvp/06_today_execution.md`를 따른다.

설치 뒤 저장소 루트에서 Codex CLI를 시작하고 다음처럼 요청한다.

```text
$with-human-dev
오늘 MVP를 구현해줘. build_tasks.json의 첫 미완료 작업부터 시작하고,
실제 MCP 정상 호출과 거부 시 executor 실행 0을 먼저 검증해줘.
docs/plans/02_today_mvp.md의 PLAN-2 1인 순서로 진행하고 실제 시험 결과와 증거 경로를 남겨줘.
별도 AI 검토를 받되 사람 개발자가 여러 명 있다는 전제로 배정하지 마.
```

사람 개발자는 사용자 1명이고 기본은 한 개발 세션에서 순차 통합한다. 서브에이전트를 쓸 수 있는 환경은 orchestrator가 고정 계약과 비중복 경로의 보조 작업만 선택적으로 나눈다. 별도 AI 검토를 공식 독립 진단이나 추가 사람으로 계산하지 않는다. 사용 불가 환경은 구현을 계속하고 작성자 자가 점검과 미실행 독립 검토를 구분해 인계한다. 특정 모델·실험 flag·Claude 전용 도구 설치가 필요하지 않다.

| 경로 | 의미 |
|---|---|
| 개발용 Codex CLI | 이 하네스를 읽고 제품 파일을 구현·검토 |
| 제품 REPLAY | 고정 후보를 실제 MCP 관문에 보내 계약·집행을 재현 |
| 제품 LIVE | 실제 에이전트/모델이 만든 호출을 별도 제품 세션으로 검사 |

GPT API키는 LIVE 연결에 참고하되 키를 문서·채팅·버전 관리에 넣지 않는다. 실제 모델 ID와 Codex CLI 인증·MCP 연결은 T-09에서 확인한다. Codex 내장 셸·파일/다른 MCP 도구가 제품 관문 밖이면 보호 범위에 포함시키지 않는다.

현재 PowerShell 준비 게이트는 `./scripts/dev_docker.ps1 -Mode up`과 `./scripts/dev_docker.ps1 -Mode check`다. 첫 명령은 개발 도구 컨테이너를 준비하고 두 번째는 계약·가짜 fixture·개발 도구를 확인한다. `-Mode audit`은 잠금파일의 공개 취약점 정보를 조회한다. 제품 코드가 생긴 뒤 `-Mode app`으로 제품을 시작하고 실제 MCP 수용시험을 따로 실행한다. 준비 게이트 통과가 제품 시험 통과는 아니다.

`dev`에는 `src/`, `tests/`, `tools/`가 읽기 전용으로 연결되어 있다. 제품 시험이 구현되면 `docker compose run --rm --no-deps dev python -m pytest tests/backend tests/gateway -q -p no:cacheprovider`로 실행한다. 현재 해당 제품 시험은 NOT_RUN이며, 상세 경로 안내는 [src/README.md](../src/README.md)를 따른다.

## 참고한 설계

사용자가 지정한 [revfactory/harness](https://github.com/revfactory/harness)의 역할 전문화, 단계별 통합, 병렬 작업, 작성자와 검토자 분리, 필요한 참조만 읽는 구조를 참고해 이 저장소의 요구사항에 맞게 새로 작성했다. 확인일은 **2026-10-13(KST)**, 확인 커밋은 [92d9f1b](https://github.com/revfactory/harness/commit/92d9f1b29e7af81acebf51a9fcd1832e739a1414)이다. 참조 README의 v2는 Claude Code용이므로 도구/API·설정은 복사하지 않았다. 해당 저장소의 성능 수치는 이 프로젝트 결과가 아니다.

프로젝트 원격 저장소: [gu1trh2ro/with-human](https://github.com/gu1trh2ro/with-human). 현재 로컬 파일과 원격의 연결·변경 상태는 루트 Git 안내를 따른다. 참조만으로 자동 push·릴리스·배포 권한을 부여하지 않는다.

## 개발 직전 판단

Docker 엔진 연결과 기본 image build, MCP SDK 인증 smoke, 세 역할 token 전달 경로, 가짜 fixture와 실제 효과 관측점을 먼저 확인한다. T-00 준비 사실을 재확인하고 T-S01 보호 전송 준비→T-02→T-01의 연결 구현을 진행한다. 최신 순서와 추가 보안 게이트는 [오늘 계획](../docs/plans/02_today_mvp.md), 역할별 확인은 [워크플로](skills/with-human-dev/references/workflow.md)를 따른다.
