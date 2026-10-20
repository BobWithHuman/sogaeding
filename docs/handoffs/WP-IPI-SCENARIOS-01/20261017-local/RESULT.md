# 합성 IPI 시나리오 환경 인계

2026-10-17. 이 작업은 엔진 구현과 분리된 **시나리오 입력 환경** 준비다. 실제 actor/Jev/OpenAI 호출, 서비스 재설정, 유료 원장 변경, 외부 전송은 0이다. 개발 AI의 통상 작업과 제품 유료 호출을 혼동하지 않는다.

## 준비물

- `fixtures/ipi_scenarios/`: PR diff·웹 로그·이슈 내보내기 각 정상/공격 쌍과 로컬 시나리오 메타데이터.
- `tools/prepare_ipi_scenarios.py`: 공격 입력을 `artifacts/runtime-ipi-scenarios/workspaces/`, 대조군을 `controls/`에 분리 복사하고 SHA-256·파일 집합·시나리오 메타데이터·경로 중간 symlink/junction을 검사한다. 준비 후 소스/런타임 차이는 실패로 표시하고 덮어쓰지 않는다.
- `docs/demos/ipi_scenarios.md`: 사용자 요청, 정상 작업, 공격 목표, actor에 보여줄 파일과 현재 엔진 보호 경계를 기술한다.

`artifacts/runtime-ipi-scenarios/manifest.json`은 생성 완료되었으며 세 입력/세 대조군이 현재 fixture와 일치한다. actor에게는 하나의 시나리오 작업공간만 보여주며 메타데이터의 기대 결과는 제공하지 않는다.

## 실행한 확인

| UTC | 확인 | 결과 |
| --- | --- | --- |
| 2026-10-17 02:55~02:59 | 준비 스크립트 `prepare` 후 `check` | READY, 3시나리오/6파일, actor0/provider0 |
| 같은 실행 | `python -m py_compile tools/prepare_ipi_scenarios.py` | exit0 |
| 같은 실행 | 합성 원본 두 종류의 PR diff에 `git apply --check` | 각각 exit0 |
| 같은 실행 | 공격 diff에 실제 URL을 추가한 임시 fixture의 준비 검사 | 예약 도메인이 아닌 URL 거부 |

호스트 WindowsApps의 `python.exe` 별칭은 실행 불가였다. 저장된 번들 Python의 절대 경로로 실행했다. 최초 입력 검증이 로그 사례에도 URL을 요구해 실패한 것은 해당 조건을 URL 사례에만 적용하도록 수정했다. PR diff의 원본 hunk 줄 수를 바로잡은 뒤 이 작업에서 새로 만든 런타임만 재생성하고 최종 준비·검사를 통과했다. 별도 AI 검토에서 PR blob hash 불일치, 로그 형식 오인 가능성, 메타데이터 무결성 누락, 중간 경로 바꿔치기 가능성을 발견했다. blob hash를 실제 합성 파일 내용에 맞추고 로그를 합성 앱 오류 로그로 명확히 했으며 메타데이터 hash와 symlink/junction 검사를 추가했다. URL은 모든 HTTP 목적지의 `.invalid` 호스트를 검사하도록 수정했다. 최종 변경 후 준비·diff 적용 검사·컴파일을 다시 통과했다. 기존 제품 원증거/원장은 건드리지 않았다.

## 범위와 다음 연결

이번 PASS는 파일 배치와 정합성에 한정된다. 현재 `mvp_demo` 등록 workspace/manifest, server V4 경로, 기존 Jev·CLI 예산은 그대로다. `env` 송신·`pip install`·최종 메시지 링크는 현재 등록 파일 MCP 시연 범위를 넘어선다. 외부 송신·패키지 설치·메시지 표시의 실제 집행/차단 관측 및 모델이 위험 후보를 제안하는지는 **NOT_RUN**이다. 다음 엔진 개발 세션은 별도 profile로 이 세 workspace를 등록하고 실행 전 호출/효과 경계를 계측한 후 정상 대조군과 공격 자료를 새 세션에서 각각 확인한다. `NO_ATTACK_ATTEMPT`, `CONFIRM`, `DENY`, 실제 효과0을 별도 결과로 기록한다.
