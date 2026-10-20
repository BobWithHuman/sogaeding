# 단계 A 가이드 적용성과 증거

정본은 읽기 전용 `docs/plans/03_guide_compliance.md`와 `05_contest_security_criteria.md`다. 기존20/49 목록/ID/이전 이력은 WP-MVP-01 GUIDE_APPLICABILITY/FINDINGS에서 유지한다. 이 문서는 **변경에 관련된 행의 추가 검토**이며 전체69항목 PASS/비적용 확정이 아니다. 원본 PDF6개 hash 일치와 직접 페이지 추출은 `artifacts/20261013-harden-a/guide-pages/manifest.json` 및 각 text에 있다.

| 요구/행 | 원문 PDF쪽(인쇄쪽) | source→sink·통제 | 도구 coverage / 실제 동적 증거 | 이번 판단 |
|---|---|---|---|---|
| SR2-7 / W-22 | G3 153·510(동일), G4 38(36) | request/comment/call/source/event→Control/Gateway SQLite→암호화·24h guard·secure_delete/폐기 | Bandit 전체 source scan은 보존시간·물리삭제를 검사하지 못함. test_retention 2조건, test_hardening two_db/both_daemons | 지정 데이터·파일 검색 및 폐기 경계 PASS; 물리/메모리 완전삭제 미증명 |
| SR4-1 / W-20 | G3 171·511(동일), G4 38(36) | 서버 발급 session→resolve/check/reserve/report/approval/timeline→생성기준 deadline | 수동 공통 guard 경로, old token/call/approval/reject/report 재사용0; 기존 cross-session/auth 회귀 | 단계 A 관련 경계 PASS. 브라우저/전체 부하 잔여 |
| SR3-1 / W-36 | G3 164·511(동일), G2 133·135(127·129) | peer/SQLite 상세 오류→MCP/API→allowlisted identifier | Bandit는 traceback/peer 반사 전체를 진단하지 못함. error/list/unhashable/schema/JSON/timeout/canary 실제 MCP 응답 | 해당 유한 장애표 비노출 PASS |
| SR3-1 / W-37·38 | G3 164·511(동일), G2 137(131) | PDP/필수 저장/보고/취소→executor→fail closed/UNKNOWN/shield/startup·daemon | test_peer_faults, mandatory_event rollback, report_loss startup, F-008 prechecked reserve. broad fallback ALLOW 없음 수동 검토 | 실행 전0/효과 후1+추가0 대표 PASS; 모든 장애 조합으로 확대하지 않음 |
| SR2-4 / W-20 | G3 509(이전 원문 evidence), G4 38(36) | 만료/미해결 state→예약권→공통 guard·정확 승인·소비 예산 | 기존 approval/binding/race 회귀 + 새 A1/A2 | 해당 회귀 PASS. B1043은 동일 구성 의존 경고 |
| W-34 | G3 406(이전 원문 evidence), G4 38(36) | 동시 승인/쓰기·fault/delete→SQLite transaction→단회 소비·rollback | test_approval exact_approval_race, test_vertical different_call_write_race, new rollback/purge | 대표 경쟁·폐기 원자성 PASS; 병렬 모든 상황 PASS 아님 |
| W-01 | 기존 적용성 정본 SQL 행 | purge IDs/시간→고정 SQL parameter binding | 최초 새 Bandit B6082건은 개발자 고정 table tuple 문자열 구성(외부 선택 불가). 더 직접적인 고정 statement로 수정, 재진단 원본 보존 | 새 B608 제거. 기존 전체 SQL source→sink 전수는 D |
| W-40 자원 정리 | G4/G2 기존49행 본문 연결은 D에서 보완 | sqlite/httpx/maintenance/request tasks→finally close/cancel + 유한 timeout | 기존 source 수동검토·fault/취소/재시작 시험; 전체 leak/장기 부하는 미실행 | 부분 검토/대표 PASS, 전수PASS 아님 |

R1 PDF13~14(9~10): 전주기 공급망 위험·복원력 원칙을 새 baseline/source/image/lock 및 실제 복구에 연결. G1 PDF35(25)·47(37): 구성요소·빌드 근거와 known unknown을 유지. 이번 기존 lock/image 사용은 공급망 전수검토 완료가 아니다. G4 PDF24(22): 코드·원기록·실행 검증을 분리했다. C1 PDF14/15/26: SAST 최초→조치→재진단 원본과 동적 효과를 보존하고 구조를 SECURITY_DESIGN에 기술했다. 추가 도구·외부 전송0.

설계20의 나머지 행 및 약점49의 나머지 행은 이전 부분증거/NOT_RUN 상태를 유지하며 D에서 개별 본문/rule coverage/source→sink/native 경계·비적용 근거를 보완한다. 이번 단계에서 공유 plans/장부의 DONE이나 전수 진단 상태를 변경하지 않았다. F-007 옛 최초 snapshot/time 공백은 복구되지 않는다. 새 baseline부터의 절차 보완만 입증한다.
