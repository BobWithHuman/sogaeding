# YAML 설정 파일 안내

기준: 2026-10-22. 로컬 artifacts/다운로드 데이터셋을 제외한 저장소 소스에는 YAML 17개가 있다.
루트 Docker Compose 15개, gateway 설정 1개, Jev 설정 예시 1개다.
각 파일은 서비스·실행 명령·포트·마운트·실험 버전을 선택한다. 엔진 판정 알고리즘은 Python 소스에 있다.

## 파일별 용도

| 파일 | 용도 |
|---|---|
| `compose.team.yaml` | 현재 팀 개발용. `src/`를 직접 마운트하고 현재 Jev 정책 선택. provider는 비활성 상태로 시작 |
| `compose.yaml` | 기본 Python 개발 컨테이너와 이전 control/gateway 앱 프로필 |
| `compose.hookgw.yaml` | transparent control·원 MCP upstream·agentgateway를 연결하는 기본 환경 |
| `compose.hookgw.offline.yaml` | 위 환경의 control을 합성 fixture 서버로 바꾸는 시험용 overlay |
| `compose.hookgw.live.yaml` | 과거 GPT LIVE judge 연결용 overlay. provider 실행은 별도 승인/설정 대상 |
| `compose.hookgw.jev.yaml` | Jev 경로로 바꾸는 overlay. 기본 rules-first/provider-disabled 설정이며 유료 설정은 별도 |
| `compose.mvp-demo.yaml` | 보존한 MVP 시연 bundle용 기본 환경 |
| `compose.mvp-demo.semantic-confirm-1.yaml` | semantic-confirm V3 시연 정책/연결 변경 |
| `compose.mvp-demo.behavior-v5-1.yaml` | 행동 판단과 출처 관측을 나눈 V5 시연 환경 |
| `compose.mvp-demo.core-auto-v5p1.yaml` | 과거 V5P1 자동 판정 시연 환경 |
| `compose.mvp-demo.hands-on-1.yaml` | 과거 hands-on 시연 revision 환경, V5P1 선택 |
| `compose.mvp-demo.frozen-demo-1.yaml` | 보존한 frozen-demo bundle/현재 후보 질문 선택 환경 |
| `compose.mvp-demo.host-wait-1.yaml` | 기존 시연 runtime/자격/DB를 유지하는 host-wait revision overlay |
| `compose.f3.yaml` | 이전 F3 control/gateway/driver 회귀 환경 |
| `compose.browser.yaml` | 이전 브라우저 driver를 포함하는 검증 환경 |
| `agentgateway/config.yaml` | 실제 gateway의 MCP 라우팅·인가·TLS 설정. Compose 파일이 아님 |
| `docs/mvp/jev_live_override.example.yaml` | Jev 키와 정책 파일을 로컬에서 연결하는 overlay 예시. 실제 키 값은 없음 |

## 팀원이 볼 최소 범위

- 엔진을 Python에서 가져와 자체 어댑터로 평가한다면 Compose 15개를 모두 사용할 필요가 없다. [엔진 연결 계약](ENGINE_INTEGRATION.md)을 따른다.
- 현재 팀 개발 stack을 실행할 때는 `compose.team.yaml`과 `scripts/team_dev.ps1`를 사용한다. gateway를 쓰는 구성에는 `agentgateway/config.yaml`이 필요하다.
- 기존 hook/gateway 경로를 검증할 때만 `compose.hookgw.yaml`에 필요한 overlay 하나를 명시적으로 조합한다. 모든 YAML을 한꺼번에 합치는 구성이 아니다.
- 과거 시연 파일은 당시 bundle·포트·DB·정책 연결을 재현하는 자료다. 파일명에 frozen/current가 있어도 내부 마운트한 bundle이 최신 소스라는 뜻은 아니다.

파일이 많은 이유는 시연/검증 revision을 별도 설정으로 보존했기 때문이다.
삭제·이동하려면 참조하는 scripts/tools와 재현 경로도 함께 정리해야 한다. 이번에는 기존 실행 기록과 연결을 보존한다.
