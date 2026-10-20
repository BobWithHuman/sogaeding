# WP-MVP-01 관리 검토와 후속 판단

2026-10-13 KST / PLAN-2. 이 관리 검토는 인계 문서·현재 코드 경로·보존된 원증거를 대조한 결과다. 이 세션에서 Docker/제품 시험·LIVE를 다시 실행하지 않았다.

## 근거와 판정

- [개발 RESULT](../../handoffs/WP-MVP-01/20261013T073853Z-dev-3980e4/RESULT.md)와 [별도 AI REVIEW](../../handoffs/WP-MVP-01/20261013T084627Z-review-ai-7421/REVIEW.md)를 읽고 실제 명령/exit·시험 출력·LIVE 안전한 결과·FINDINGS를 대조했다.
- [관리 manifest 확인](../../../artifacts/management-wp-mvp-01/manifest-check.json): 최종 source manifest **50개 파일 모두 일치**. 최종 fingerprint `8e48b00ceac5803b034d85da55c383980f0e31ce230c9dab21deb1aa0cb6fa27`.
- R1 제품24 PASS, 별도 장애 보완3 PASS를 원본 출력과 exit0 기록으로 확인했다. 마지막 변경은 TLS 시험 파일 하나이고 최종 TLS2 PASS가 별도로 있다. 서로 다른 실행의 시험 수를 합산·재번호하지 않는다.
- F-008 P1은 원본 FAIL→작성자 수정→독립 재현 PASS가 연결됐다. repository의 UNKNOWN check/reserve 차단·필수 source 확인도 읽어 대조했다. 해당 재현 범위의 해결을 수용한다.
- 현재 source·runtime은 구현되어 있으며 전송/wire 계약은 SPEC-3이다. **제품 상태는 부분 구현/부분 검증, core/MVP 미완료**다. 가이드20/49 전수 적용성은 초안이며 전수 판정으로 승인하지 않는다.

## 작업 장부 판단

| 작업 | 관리 상태 | 범위/잔여 |
|---|---|---|
| T-00 | DONE 유지 | 개발 환경 준비의 기존 기록 |
| T-S01 | DONE | SPEC-3 기계 동기화·TLS fixture·Codex CA 지원 준비. 실제 제품 TLS 전체 negative/rotation은 별도 미완료 |
| T-02 | DONE | 서버 발급 session/grant, 역할 인증·schema/registry의 현재 계약 범위. 장기 보존·전체 부하 검증 완료를 의미하지 않음 |
| T-03 | DONE | 결정적 정책·정확한 인자/정책 결합·대표 ALLOW/DENY/CONFIRM과 효과 증거 |
| T-01·04·05·06·07·08·10 | IN_PROGRESS | 실제 TLS/장애·복구·보존·UI·전수 가이드/공급망 및 각 연결 게이트 잔여 |
| T-09 | IN_PROGRESS | 이전 빌드 정상 LIVE와 공격 입력 관측 수용. 공격은 미시도, 최종 후보 빌드 검증은 추후 영향 판단 |

T-01의 TLS 전체 검증이 남았어도 이미 구현된 후속 작업의 대표 증거를 폐기하지 않는다. 선행 게이트가 완료되지 않은 작업은 최종 DONE으로 승격하지 않는다. 상태 IN_PROGRESS는 미완료 구현/검증을 의미하며 지금 다른 세션이 실행 중이라는 뜻이 아니다. 현재 관리 채팅이 배정한 활성 쓰기 세션은 없다.

## 수용한 결정과 다음 행동

1. **기존 개발 세션에서 [WP-HARDEN-01 단계 A](../06_mvp_completion_work_pack.md)를 시작한다.** F-004 보존/폐기 및 AT-09/AT-12 장애·daemon/restart 복구부터 보완한다. 그 다음 실제 브라우저, TLS 수명/전체 negative, 가이드/공급망 순서다.
2. local-ingress 구성은 현재 loopback 공개·TLS·내부 mTLS+bearer 조건과 함께 수용한다. 내부8443 모든 NIC listen/OS egress 전체 비격리 한계를 유지한다. B104 세 경고는 이 구성에 한정한 검토이며 무약점 판정이 아니다.
3. F-007의 최초 SAST 전체 snapshot/start UTC 공백은 과거 증거 한계로 보존한다. 거짓 복원/소급 PASS를 금지하고 이번 변경 전 baseline부터 완전한 추적을 남기면 앞으로의 절차 보완으로 판정한다.
4. 공급자 UNKNOWN을 패키지 author로 바꾸어 확정하지 않는다. SBOM schema 유효성과 실제 이미지/전이관계/고지/OS 진단 완전성을 구분한다. 다음 A는 기존 도구로 가능하므로 추가 도구 판단 때문에 착수를 막지 않는다.
5. LIVE 정상/공격 두 건은 모델 `gpt-5.6-luna`, CLI0.154.0의 **F-008 수정 전** 결과다. 해당 관측을 보존하고 위험 호출을 만들 때까지 반복하는 작업은 우선 배정하지 않는다. 현재 후보의 최종 LIVE 확인은 안정화 이후 필요한 최소 범위로 결정한다.

보호 범위는 등록 MCP 세 도구의 Gateway 경로다. 모든 IPI·내장 셸/파일·다른 MCP·호스트 전체 보호나 출처의 인과 증명으로 확대하지 않는다.
