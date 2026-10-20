# 최초 진단·조치·재진단

2026-10-17. 현재 배정 CORE_AUTO_FINISH/ADR-P04에 한정한다. 관리 plans/harness/AGENTS, Engine 상태·승인·원자예약 계약, 기존 원장·결과는 수정하지 않았다.

| 최초 확인 | 조치 | 재진단/증거 |
|---|---|---|
| 동일 실제 V5 정상 응답 A WITHIN_TASK .86/LOW_CONFIDENCE·B LEGITIMATE 1.0이 기존 V5에서 CONFIRM | 새 behavior_v5p1에서 완전 검증된 raw A와 고확신 B의 결합만 양의 허용 근거로 사용 | 원 snapshot/wire/답 replay 정상 ALLOW, 위험 DENY 유지. A 확신·thresholded UNCERTAIN 보존. replay-summary.json, test_core_auto_policy.py |
| 실제 CLI 안전 기록의 .86/.70도 독립 A 양의 확신 문턱 때문에 막힘 | 안전한 관측 값의 결정 합성만 시험 | 두 조합 ALLOW. 암호화 snapshot 복원·새 모델 관측0 |
| 현재 control/private upstream 실패는 기존 별도 AuthAudit 구현과 연결이 부족함(R-B-002) | credential 없는 HUMAN/SERVICE/AGENT 실패를 독립 영속 저장. machine/human 최근60초 실패 한도는 독립 집계로 조회. 감사 저장 실패503 | 재시작/일반감사 삭제 뒤 제한 유지, 감사 장애 효과0, upstream ticket 거절 영속. 관련84/최종gateway69 통과 |
| 자동 정상 수용에 기존 CONFIRM 승인·재개를 허용하면 목표를 대신할 수 있음 | core MCP 경로 승인대기 끔. 정상 ALLOW/OBSERVED·승인0·정상종료·정리·연결종료·남은2요청을 위험 시험 전 확인 | runner 반례 및 별도 검토16 PASS. 실패/UNKNOWN 뒤 claim 유지·재시도 거부 |
| 새 allowance가 소진 부모 원장과 분리되면 누적 상한을 우회할 수 있음 | 역사25/1600000·CLI4와 부모 hash를 manifest에 결합. 새4/256000·CLI1, 역사29/1856000·CLI5 상한을 엄격한 정수와 exact opt-in으로 검사 | prepare/check ready=true, 기존6원장 hash 보존, 현재 새 provider ledger·CLI5 claim·위험 claim 없음 |
| 최초 Ruff import 정렬2건 실패 | server/upstream import 정렬 수리 | lint-first.txt 보존, lint-final.txt PASS |
| Bandit exit1: Low10/Medium8 | 고정 listener/tmpfs/argv/trace의 실제 경로·통제와 대조 | GUIDE_MAPPING.md 및 별도 REVIEW에 문맥 검토. 원 경고 삭제/전수 PASS 처리 안 함 |

최초 관련 정책67 PASS 뒤 통합366 PASS를 실행했다. 이후 정상 과업 동결 대조와 인증 제한의 독립 영속 집계를 보강했으므로 관련84 및 실제 gateway69를 다시 실행했다. 통합366을 수리 뒤 전체 재실행 결과로 표시하지 않는다. PS5.1 wrapper는 fake helper로14 PASS이며 실제 start/verify-block은 실행하지 않았다.

원증거는 `C:\sogaeding\artifacts\20261017-core-auto-finish\`에 보존했다. `original/`, `preservation-before.json`과 `preservation-after.json`, `change.diff`, `source-manifest.json`을 함께 사용한다. `mvp_demo_mcp.py`의 최초 파일 복사는 누락되어 세 변경만 역적용한 이전 파일을 복원했고, 수정 전 기록과 이전 prepared manifest의 동일 SHA로 확인했다. 원 HTML은 소스 수정 뒤지만 HTML 변경을 수행하기 전에 별도 hash를 기록했다(`original-html-preservation.json`). 이를 모든 파일의 사전 백업이 완전했다고 표현하지 않는다. 기존 source drift는 명시된 source 변경이며 과거 결과의 source가 현재와 같다고 주장하지 않는다.

Docker pipe의 sandbox 접근 거부는 허용된 Docker 접근으로 동일 격리 명령을 실행해 해소했다. 제품 코드 실패나 모델 결과를 성공으로 바꾼 것이 아니다. 개발/검토 컨테이너는 기존 image를 사용했고 원격 pull·모델·actor 호출은 없었다.
