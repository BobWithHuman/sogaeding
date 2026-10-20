# sogaeding 팀 개발 인계

기준: 2026-10-20. 게시용 소스와 과거 로컬 실행 증거를 구분한다.

## 목적과 구현 상태

With Human은 Codex의 등록 MCP 실행 전에 사용자 요청·권한·출처·호출 후보를 연결하고,
코드 정책과 필요한 Jev 관측으로 허용·차단·사람 확인을 집행하는 MVP다.
엔진·Jev 연동·실행 전 집행·단회 승인·출처/이력·DTAP 연결 코드가 있다.
등록 합성 파일 경로의 실제 정상 자동 쓰기와 별도 고정 위험 후보의 실제 Jev DENY를 관측했다.
모든 native 도구나 모든 IPI를 보호한다는 뜻은 아니다.

미완료는 DTAP에서 Jev 의미 DENY 효과 입증, 정상 검색/백업 일부의 과도한 보류,
탐색 검사 한도 초과의 전체 중단 처리, 일반 개발 환경 전체 보호, 완성형 대시보드다.
직전 DTAP 수정본의 코드 DENY는 26회, Jev 의미 DENY는 0회다.
양쪽 채점이 끝난 동일 6쌍에서 공격 성공 off 4/on 0, 정상 성공 off 6/on 5였다.
이는 일부 완료 표본의 중간 관측이며 전체 100개 결과·일반 정확도가 아니다.
실행 DB·모델 원문·증거는 로컬 artifacts에 보존되며 clone에 포함하지 않는다.

## 현재 실행 경로

사용자 → Codex hooks → Control 요청/후보 결합 → agentgateway 인가 →
정책/필요한 Jev 분석 → 정확한 호출 예약 → MCP executor → 응답/PostToolUse → 출처·이력.

- 팀 개발: `compose.team.yaml`. 현재 소스를 직접 읽으며 provider 비활성화.
- 파일 시연: `tools/mvp_demo.py`, `mvp_semantic_followup.py`와 revision별 Compose.
  다른 PC의 기존 bundle·원장·PKI를 복사해 재사용하지 않는다.
- DTAP: `src/app/benchmark/`, `tools/dtap_runtime.py`. pinned 공식 자료는 별도 준비가 필요하다.
  clone만으로 과거 유료 run을 재개할 수 있다고 가정하지 않는다.
- 이전 SPEC3/4: `src/app/control`, `gateway`, `pdp` 등의 이전 계약·회귀와 공통 부품.
  최신 transparent 서버와 혼동하지 않는다.

## 현재 HTTP API

구현 정본은 `src/app/transparent/server.py`다.
새 machine/human 토큰은 전용 Docker 볼륨의 `artifacts/team-dev/<이름>/host`에 생성한다.
호스트의 같은 상대 경로에는 비밀이 없는 준비·네트워크 메타데이터만 둔다. 토큰 값은 화면·로그에 출력하지 않는다.
브라우저에 machine 토큰을 복사하는 방식으로 대시보드를 구현하지 않는다.
프론트 인증·CORS/BFF 연결은 별도 합의가 필요하며 공개 운영 API로 배포한 상태는 아니다.

| endpoint | 역할·인증 |
|---|---|
| `GET /health` | 정책·Jev 모드, 비인증 |
| `POST /connect` | machine 인증으로 연결 발급. 일반 화면용 아님 |
| `POST /event` | machine 인증 + connection, 실제 사용자 turn·Pre/Post 이벤트 |
| `GET /history` | human 인증, `{calls: [...]}` |
| `GET /demo/history` | viewer 활성화 + human 인증, 기존 안전 projection |
| `POST /approval` | human 인증, 정확한 `call`, `approve`, 필요한 `approval_binding` |
| `GET /demo/pending` | demo dispatch 활성화 시에만 사용. 기본 개발 stack은 비활성 |
| `POST /authz` | gateway 전용 mTLS listener. 공개 포트에서 사용 금지 |

`docs/mvp/contracts/spec5.schema.json`은 hook 이벤트 계약이다.
과거 OpenAPI 전체가 최신 서버 전체와 일치한다는 뜻은 아니다.
대시보드 통합 조회·페이지네이션은 기존 projection을 바탕으로 추가 합의가 필요하다.
화면의 제안 계약과 이미 존재하는 서버 API를 구분한다.

## 공유 범위

소스·시험·합성 fixture·잠금 의존성·Compose·개발/설계 문서를 공유한다.
키·토큰·DB·개인 설정·원본 로그·다운로드 DTAP 자료·Windows 캐시는 제외한다.
`tools/repository_export.py`는 지정 소스 경로만 새 디렉토리에 복사하고 해시 목록을 남긴다.
credential 패턴 검사는 보조 점검이며 모든 비밀 부재를 보증하지 않는다.
공유 키도 팀원이 별도 로컬 환경으로 설정하며 소스에 기록하지 않는다.
조직의 Rust core·Claude Code/Neo4j prototype과 별도 구현임을 명시한다.
원격 생성·첫 commit/push는 별도 작업이며 준비 검사만으로 업로드됐다고 표시하지 않는다.
