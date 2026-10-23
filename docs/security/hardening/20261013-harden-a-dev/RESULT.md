# WP-HARDEN-01 단계 A RESULT

SPEC-3 / 정책 `mvp-2026-10-13-v1` / PLAN-2 후속 배정. 사람 개발자는 사용자1명, 구현과 별도 AI 검토의 역할을 분리했다. **단계 A의 지정 유한 범위를 구현·검증해 관리 검토에 인계한다. B~D와 전체 core/MVP·최종 LIVE 완료는 미완료다.** 공유 plans/작업 장부의 DONE 판정은 변경하지 않았다.

## 변경과 기준선

- Control 세션 생성기준24h 접근 차단·원자적 폐기, Gateway 실제 invocation 생성기준24h receipt/comments 폐기, startup/10초 daemon, 원기한+7일의 본문 없는 disposal 기록을 추가했다. 두 DB 기산점 차이·정리 실패 지연·물리 삭제 한계는 [SECURITY_DESIGN](C:/sogaeding/docs/handoffs/WP-HARDEN-01/20261013-harden-a-dev/SECURITY_DESIGN.md)에 명시했다.
- 기존 DB에 생성시각을 비파괴·재실행 가능하게 추가했다. 예산·승인·판정은 그대로 유지한다. UNKNOWN/RESERVED 폐기는 성공확정·환불·재실행권이 아니다.
- PDP JSON/schema/오류 구조/HTTP302 처리, 필수 저장 rollback, 실제 daemon·재시작 복구와 MCP 요청 취소를 보완했다. 실제 effect receipt를 통한 명시 복구만 사용한다.
- 변경 파일: `src/app/storage/retention.py`, `repository.py`, `executor/demo.py`, `gateway/client.py`, `gateway/main.py`, `control/main.py`; 보존·장애 시험 및 `tests/acceptance/conftest.py`, `test_audit_latch.py`, `test_vertical.py`; 로컬 증거 도구 `tools/harden_{evidence.ps1,snapshot.py,guides.py}`. 공개 계약·정책·enum·Compose·의존성 변경 없음.

변경 전 [baseline summary](C:/sogaeding/artifacts/20261013-harden-a/baseline/summary.json)의 캡처는 **2026-10-13T09:41:39.088991Z**, source62파일/원문 snapshot, fingerprint `cf2e4106eb26aa6bce26287308e1e89ff85bd8ca551c9a400a75734c235396e7`이다. 기존50파일 mismatch0으로 관리 기준 `8e48b00ceac5803b034d85da55c383980f0e31ce230c9dab21deb1aa0cb6fa27`을 이어받았다. 새 helper 포함 범위가 달라 전체 fingerprint는 다르다. lock은 snapshot의 `requirements-dev.lock`, 기존 이미지 inspect/digest는 `baseline-image.txt`: `sha256:a263fc0fe3cb9e5934add3a405a8c65b6d000d1cca9ca8c4852b621d17812c26`. 도구/SDK·Python의 기존 이미지와 lock을 사용했다.

최종 [r1 manifest](C:/sogaeding/artifacts/20261013-harden-a/r1/manifest.json)는69파일, **`6c6d6a98e33fff4177293022f61c4a33956192dc427b24f01d42f71a5e825423`**, 캡처10:03:49.497179Z다. 이후 제품 수정 없이 이 버전의 시험·별도 AI 검토를 연결했다. 추가 생산 서비스 재배포/재시작·LIVE는 하지 않았다. 기존 Compose 서비스가 실행 중이라는 사실을 새 source로 재배포 완료한 것으로 표시하지 않는다.

## 명령·원본과 결과

아래 파일은 모두 `artifacts/20261013-harden-a/` 아래에 있다. 각각 `*-command.json`에 **전체 argv, UTC started/completed, exit, 출력경로**, 같은 이름 `.txt`에 안전한 raw output을 보존했다. `docker compose run --rm --no-deps dev`의 별도 컨테이너·전용 `/tmp` TLS/DB이며 기존 runtime/DB/원증거를 변경하지 않았다. 증거를 쓰는 실행은 추가 evidence bind/EVIDENCE_DIR를 사용한다.

| 실행/범위 | 실제 결과 | 명령·원본 |
|---|---|---|
| 변경 전 제품 `python -m pytest tests/backend tests/transport tests/web tests/acceptance -q -p no:cacheprovider` | exit0, **24 PASS**,11.91s | baseline-product-command.json / baseline-product.txt / baseline-traces/product-traces.json |
| 변경 전 `bandit -r src/app -f json` | exit1, B1043 원경고 | baseline-bandit-command.json / baseline-bandit.txt |
| 초기 보존/기존회귀 | exit0,25 PASS,10.93s | implementation-first-tests* |
| 실제 daemon/재시작·두 DB 장애·필수 감사 rollback | exit0,3 PASS,26.75s | retention-daemon-first* / retention-daemon-traces |
| 최초 실제 MCP 취소 | **exit1,1 FAIL**, UNKNOWN이0.8s 안에 저장되지 않음 | cancellation-first*; F-009 원본 유지 |
| disconnect/shield 조치 후 동일 취소 | exit0,1 PASS,5.25s, UNKNOWN22ms / 댓글1 / 추가0 | cancellation-retest* / cancellation-retest-traces |
| 확대 중 peer8개 이전 버전 | final-peer: 7 PASS 뒤 **teardown1 ERROR**, exit1; 시험 상대 종료 timeout | final-peer*; timeout_graceful_shutdown/kill fallback 보완 후 candidate-peer exit0,7 PASS |
| 첫 새 lint/SAST | lint exit1,4개(정렬/loop binding); Bandit exit1,기존B1043+고정 table loop B6082 | new-lint-first* / new-bandit-first*; 고정 SQL·정렬 수정 이력 유지 |
| 최종 r1 제품 전체, 위 pytest argv | **exit0,30 PASS**,46.55s | r1-product-command.json / r1-product.txt / r1-product-traces/product-traces.json |
| 최종 TLS fault peer `python -m pytest tests/hardening -q -p no:cacheprovider` | **exit0,8 PASS**,8.59s | r1-peer-command.json / r1-peer.txt / r1-peer-traces/fault-traces.json |
| 최종 Ruff 제품/관련시험/helper | exit0 | r1-lint-command.json / r1-lint.txt |
| 최종 Bandit1.9.4 제품 전체 | **exit1,B1043 경고 유지**, 새 B608 제거 | r1-bandit-command.json / r1-bandit.txt |
| 기존 하네스 계약 검사 `python -m pytest tests/harness -q -p no:cacheprovider` | exit0,1 PASS,0.53s; 제품 수용시험과 구분 | r1-harness* |

30은 pytest 수집 case 수(기존24와 신규6)다. peer8과 독립 AI 자체시험은 별도 실행이며 새 NT/AT38개 또는 전체 수용시험 전수PASS로 합산하지 않는다. 스냅샷 이후 새 client의2xx 조건을 넣은 r1에서 전체30/peer8/lint/SAST를 다시 실행했다. 실패·시험 종료 오류·중간 진단은 삭제하거나 PASS로 덮어쓰지 않았다.

## A1/A2 case별 효과·근거

안전한 통합 [case-evidence.json](C:/sogaeding/artifacts/20261013-harden-a/case-evidence.json)은38개 관측 record를 원 trace경로·fixture hash·최종 source에 연결한다. 원 trace는 session/call/args digest/decision/reservation/approval ID 및 효과 수를 포함하며 bearer·raw body·DB 복사본은 없다. 일부 record는 복구 뒤 누적 effects를 표시하므로 `fault_actual_effects`, `effects_before_purge`, `additional_effects` 및 아래 표를 함께 읽는다. ID만 보존된 폐기 case는 과거 call body를 새로 만들어 기록하지 않는다.

| 배정 case / 기존·신규 | 실제 검증과 결과 | 시험·증거 |
|---|---|---|
| A1 생성+24h 경계 / 신규 | fake clock: 직전 자료 유지, 정확 경계 timeline403/receipt None; RESERVED·UNKNOWN 모두 동일. 조회로 기한 연장0 | backend/test_retention.py 2조건, r1-product exit0 |
| A1 migration·멱등·최소기록 / 신규 | legacy table shape에서2회 migration, 기한/암호문 보존; DELETE trigger시 tx rollback; 반복 purge 후 자료0, 미해결1/쓰기예산0의 body-free record; 원기한+7일 후 기록0 | 같은 backend 시험; 실제 파일 ciphertext/body/token 검색0 |
| A1 두 DB 중간 실패/재시작 / 신규 | Control 삭제 성공·Gateway DELETE 실패시 댓글1 남음, 조회/approve/reject/token/reserve/report 거부; 장애 제거·2회 startup으로 두 DB 자료0, **추가effects0**; 기한 전 다른 세션 유지 | test_hardening.py::test_two_db_retention_failure_then_restart_no_old_access; A1-two-db-failure-startup |
| A1 양 daemon 정리 / 신규 | startup 대신 실제10초 주기 Control/Gateway 둘 다 해당 자료0, 삭제 전댓글1·추가0 | test_both_real_daemons_purge_without_restart; A1-both-daemons elapsed 기록 |
| A2 PDP timeout / 신규 | 실제 MCP→인증TLS peer의 check 지연: 유한 오류 PDP_UNAVAILABLE, executor/effects **0/0**, 회복 후1 | peer parametrized timeout, r1-peer-traces |
| A2 malformed JSON/schema/error / 신규 | 잘못된 JSON·schema, list error·unhashable code, valid-schema302 모두 안전한 PDP_UNAVAILABLE; 원문/credential 반사0, **0/0** | peer parametrized json/schema/error/list-error/redirect |
| A2 check/reserve/필수 감사 저장 / 기존+보강 | calls INSERT 실패와 CHECKED/RESERVED events/EXECUTIONS INSERT trigger; fault 실행0, call/write budget 유지·APPROVED 소비0·execution partial row0. 장애 제거 후 정확 승인1 | test_vertical storage_failure; test_hardening mandatory_event; fault0/recovery1 trace |
| A2 F-008 source 실패 / 기존+보강 | 읽기 invocation1·UNKNOWN, source없는 receipt-only 확정503. 후속 새 check·미리 만든 ALLOW reserve 모두 거부, 쓰기/다음읽기0 | test_audit_latch.py; AT-09-source-followup |
| A2 write report DB손실·startup / 기존+보강 | 첫댓글1, durable RESERVED/반환UNKNOWN, stale timestamp 후 실제restart로UNKNOWN·write_budget0; 동일/다른 위험재시도 추가0; 실제 receipt report만SUCCEEDED | test_vertical report_loss_unknown_no_repeat; AT-12 |
| A2 report 응답 손실 / 신규 | 효과 발생 뒤 성공report를 peer가 지연시켜 수신 실패, UNKNOWN보고는 실PDP에 도달. 실제댓글1/추가0, reservation 결합한 실제receipt 명시 복구 | peer::test_after_write_report_response_loss_and_real_receipt_reconciliation |
| A2 요청 취소 / 신규 결함 수정 | 실제 SDK 응답 stream close; UNKNOWN22ms(1s peer timeout 이전), 댓글1·동일/다른 재시도0·예산0; 실제receipt 명시 복구 | peer::test_real_mcp_request_cancellation_after_effect; F-009 |
| A2 RESERVED30초 daemon/startup / 신규 | reserved_at만 과거 fixture; 실제Control daemon 및 프로세스restart가UNKNOWN으로 전이·예산0 유지, executor/effects0; 새 정상session댓글1 | test_hardening real_daemon_and_startup_stale_unknown_no_refund |
| 정상/승인/거절/만료/경쟁 / 기존 회귀 | 정상issue/readme/정확댓글1, DENY·비밀0, CONFIRM 승인 전0/후1, 원판정CONFIRM·CONSUMED/SUCCEEDED 분리, replay추가0, 동일승인/다른call 경쟁 총1, 만료/거절 거부 | test_vertical/test_approval/test_security 및 backend; r1-product 전체 |

## NT/AT·AC 연결과 완료 한계

| 기존 ID | 실제 함수·현재 증거 | 범위 판단 |
|---|---|---|
| NT-01·02 / AT-01·02 | test_vertical real_mcp/one_effect_and_replay | 대표 REPLAY 정상/거부 PASS. 모델 최종 요약 LIVE는 이번 NOT_RUN |
| NT-03 / AT-05·06·07 | test_approval exact_approval_race/binding_expiry_policy/rejected | API/MCP 승인·경쟁 대표 PASS. 실제 브라우저는 B |
| AT-03·04·11 | test_security tool_inputs_and_bypass/rest_duplicate_depth_size | 해당 입력/공개경로 대표 PASS; 호스트 전체 격리 아님 |
| AT-08·10·13 | test_security roles_and_masked_storage/actual_mcp_expired_audience_scope | 역할·대표 저장/인증 PASS, 실제 브라우저·모든 과거 credential은 미점검 |
| AT-09·12 | 위A2 fault matrix·F008·startup/daemon/receipt | 지정 유한표 PASS. 모든 장애 조합 PASS 아님 |
| AT-14 | test_vertical different_call_write_race | 실제 총댓글1 PASS |
| AT-15 | 이번 새LIVE0, 이전 LIVE 최초 요청digest 관측은 이전 빌드 | 이번NOT_RUN; 과거 결과를 새 source로 이전하지 않음 |

AC-01~07의 단계A 관련 대표 경로는 실제 Docker 임시 TLS 제품에서 확인했다. AC-08 실제 브라우저, AC-09 최종LIVE, AC-10/PL-SDLC·DIAGNOSIS 전수진단/공급망·이행은 남는다. PL-SEC-TRANSPORT 대표 회귀는30개에 포함하지만 전체 negative/certificate lifecycle은 C다. 하네스PASS나 소수TLS fixture를 전체 core 완료로 표시하지 않는다.

## 별도 검토·발견·남은 작업

[FINDINGS.jsonl](C:/sogaeding/docs/handoffs/WP-HARDEN-01/20261013-harden-a-dev/FINDINGS.jsonl)은 기존 원문 이력을 복사해 유지하고 새 이벤트/원증거 링크를 추가했다. F-004 단계A 보완, F-008 회귀, F-009 최초FAIL→수정→재진단, F-010 non2xx 수동발견/실제302 재검증, F-011 고정 SQL SAST경고의 조치를 연결했다. F-003 B1043 경고는 숨기지 않았고, **F-007 옛 초기 snapshot/start UTC 공백은 영구 한계**다. 새 변경 전 baseline·최종 후보에는 전체source/image/lock과 실제 command UTC가 있다. 다만 이번 중간 F-009 최초FAIL·F-011 최초B608 진단 직전의 전체 source snapshot도 별도로 고정하지 않았다. 그 시점의 raw/snippet/수정 경로는 보존했지만 최종source와 동일했다거나 최초빌드 전체hash를 소급복원했다는 주장은 하지 않는다. 장부의 기존 `source_fingerprint`는 최종 인계 후보 참조이며 최초 발견 빌드 hash가 아니라는 보충 이벤트를 추가했다.

별도 AI 검토의 결과와 독립 명령·효과·manifest 대조는 [REVIEW.md](C:/sogaeding/docs/handoffs/WP-HARDEN-01/20261013-harden-a-review/REVIEW.md)에 둔다. **독립 제품30 PASS(46.95s), peer8 PASS(8.40s), 자체 경계/반대방향 장애/복구3 PASS(8.79s), source69 mismatch0; 현재 범위 미해결 차단급/P1 제품 발견 없음**이다. 추가 사람 개발자나 공식 진단기관의 결과가 아니다. R-A-001 두 DB 삭제간격 상한 지적에 따라 SECURITY_DESIGN의 엄격1800초 주장을 제거했다. R-A-002 중간 전체snapshot 부재와 최종candidate 참조는 보충장부·위 한계에 명시했다. 제품 source는 그대로다.

[GUIDE_APPLICABILITY](C:/sogaeding/docs/handoffs/WP-HARDEN-01/20261013-harden-a-dev/GUIDE_APPLICABILITY.md)은 관련원문→위험/인터페이스→코딩통제→진단rule coverage/실효과를 연결했다. 전체20/49 전수완료·공식 조치율/빌드라인/점수는 선언하지 않는다. 현재 role credential 및 호스트에서 사용 가능한 API key를 값 출력 없이 새 source/tests/tools/scripts/artifacts/handoff와 비교한 초기 [credential-scan.json](C:/sogaeding/artifacts/20261013-harden-a/credential-scan.json)은333파일 hit0이다. RESULT 포함 최종 [handoff-verification.json](C:/sogaeding/artifacts/20261013-harden-a/handoff-verification.json)은69 source mismatch0, 현재 인계파일 credential hit0, 기존장부 원문보존·명령UTC/exit/output경로를 확인했다. 모든 과거 키/PC 전체에 대한 검사나 디스크 완전삭제가 아니다.

단계A 작성자 작업 실측 앵커: 변경 전 baseline09:41:39Z → 인계검사 첫실행10:15:29Z, 약34분(2026-10-13 KST18:41~19:15). 이후 별도 AI 문서 연결·최종검사 완료시각은 handoff-verification.json의 completed_at에 기록한다. 단계B~D 시간은 이번에 미측정이다.

**다음 배정 B 조건:** 관리 세션이 이번 A RESULT/별도 REVIEW·잔여를 검토한 뒤 B를 발급한다. B 실제 브라우저 요청/타임라인/승인/거절·XSS/token/중복클릭·auth제한, C 실제 제품 전체TLS negative·재발급/회전/복구·새 환경, D 설계20/약점49 개별본문·source→sink·tool coverage/수동보완·OS SCA/라이선스NOTICE/SBOM이 미완료다. 새 유료LIVE0. 기존 두 LIVE는 F008 수정 전 빌드의 정상연결/요약·NO_ATTACK_ATTEMPT 관측이며 최종후보 LIVE PASS가 아니다.

보호 주장은 등록 MCP3도구의 Gateway 경로에 한정한다. Codex 내장shell/file·다른MCP·모든IPI·호스트 전체 보호, 출처 일치의 인과증명으로 확대하지 않는다.
