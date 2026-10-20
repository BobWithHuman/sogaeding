# 합성 IPI 시나리오 입력 독립 검토

2026-10-17. 검토 대상은 `fixtures/ipi_scenarios/`, `tools/prepare_ipi_scenarios.py`, `docs/demos/ipi_scenarios.md`의 최종 입력 후보이다. 제품 서비스, actor, Jev, 외부 네트워크, 유료 모델은 호출하지 않았다.

## 지적 사항 조치

| 항목 | 최종 확인 |
| --- | --- |
| PR diff의 잘못된 `index` blob hash | **조치됨.** 두 diff의 공통 원본과 각각의 변경본 hash가 합성 내용과 일치한다. `git apply --numstat` 두 건 모두 exit 0. |
| Nginx `error.log`처럼 보이는 혼합 형식 | **조치됨.** 시나리오 메타데이터와 설명에서 요청 헤더·앱 오류·supervisor 사건을 담은 합성 애플리케이션 오류 로그로 명시했다. |
| `scenarios.json`이 manifest에서 빠짐 | **조치됨.** `scenarios_sha256`을 manifest에 포함하고 `check`에서 현재 메타데이터와 대조한다. |
| 중간 경로 symlink·junction 가능성 | **조치됨.** `safe_path`가 소스·런타임의 각 경로 구성 요소를 검사한다. 이는 준비 시점의 로컬 검사이며 동시 파일시스템 변경까지 막는 OS 격리는 아니다. |

최종 `prepare_ipi_scenarios.py check`는 **READY: 3 scenarios, 6 local input files**로 종료했다. 정상/공격 쌍은 PR 주석, 로그 `User-Agent`, 이슈 댓글만 달라 시연 대조에 적합하다. 모든 공격 입력의 HTTP 목적지는 `.invalid` 예약 도메인으로 제한된다.

## 남은 범위

현재 자료는 별도 입력 환경이다. SPEC5 등록 workspace 연결, 실제 모델의 위험 후보 생성, `env`/네트워크·패키지 설치·최종 메시지 표시의 실행 전 차단과 효과 관측은 **NOT_RUN**이다. LIVE 시연 전 별도 격리 profile과 집행 차단을 마련하고 정상/공격을 각각 새 세션에서 확인해야 한다. 현재 파일 검사 통과를 의미 기반 IPI 차단 성공으로 해석하지 않는다.
