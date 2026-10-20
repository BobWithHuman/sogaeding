# HANDS_ON_PREPARED_NATIVE_HOOK_E2E_NOT_RUN

2026-10-17, T-DEMO-03. with-human-dev로 기존 연결 진입점에 최신 검증 엔진의 직접 체험 경로를 연결했다. 현재 PowerShell에서 최초 연결 뒤 사용자가 직접 인자 없는 `codex`를 실행하고 자유롭게 요청하는 경로다. 사용자 요청을 자동 입력하지 않는다. **신뢰 변경 없이 나머지만 완료**하라는 최종 지시에 따라 hooks 신뢰를 변경하지 않았다. 모델 없는 준비·코드 수정·별도 검토를 완료했으며 실제 native Pre/Post 정상·위험 종단은 미실행이다. 전체 hands-on 실증 완료로 보고하지 않는다.

## 변경과 재사용

- `scripts/hookgw_connect.ps1`: `-HandsOn -ConfirmSend -ApproveHandsOnLimits -ManifestSha256` 선택, 무모델 사전검사, 현재 터미널 wrapper. 인자 없는 `codex`만 기존 start/lifecycle에 전달한다. 종료 후 기존 함수/별칭/options/description을 복원한다. 개인 전역 config/auth/login 및 sandbox 설정은 수정하지 않는다. 기존 child host 사용자 승인 경로를 재사용한다.
- `tools/mvp_semantic_followup.py`: 별도 `hands-on-1` 준비/검증/시작/RO 이력. 소진된 core4/4 원장·실제 정상 보고서·실제 고정 위험 DENY 결과·종료를 확인하고 기존 V5P1 정책/bundle/image를 재사용한다. 미래 입력을 고정 prompt와 비교하지 않는다. 기존 approval/정확인자·출처/예약·단회/UNKNOWN/no unsafe retry 통제를 유지했다.
- `tools/mvp_demo.py`, `scripts/mvp_demo.ps1`: 기존 CLI의 해당 revision 연결. 별도 새 CLI/범용 runner를 만들지 않았다. PowerShell demo 진입점은 해당 revision의 check/inspect/history만 제공한다.
- `tools/mvp_demo_hook.py`, `tools/mvp_demo_mcp.py`: 기존 Post/source/OBSERVED 경로 유지, hands-on CONFIRM은 중단하며 기존 승인 watcher로 잘못 안내하지 않는다. `mvp_demo_viewer.py`는 기존 viewer의 CLI총6 표시 범위만 확장했다.
- `compose.mvp-demo.hands-on-1.yaml`: 별도 runtime·8038/8048·네트워크. 기존 서비스/원장/성공/실패를 교체하지 않는다. 제품 bundle RO·기존 Jev 키 RO·TLS/mTLS·최소권한을 유지했다. 새 의존성/정책/모델 의미 변경은 없다.
- `mvp_semantic_probe.py`의 가짜 Jev 응답/한도는 새 offline fixture에 한정된다. 제품 actor에게 oracle/정답을 넣지 않는다. 새 `test_hands_on.py`는 drift·명시선택·소진거절·판정표시를 검증한다.

## 진단·조치·재진단

| 검사 | 결과와 증거 (`artifacts/20261017-hands-on/`) |
|---|---|
| 최초 관련 시험 | 15 PASS, `related-first.txt` |
| 필요한 통합 회귀 | 118 PASS/36.13초, `integrated-final.txt` 및 command JSON. 기존 demo/V5/followup/lifecycle 포함 |
| 실제 native fixture 시도 | `e2e-attack-2`: 실제 PS connector→plain codex→진짜 CLI 시작/종료. 실제 사전검사 TLS MCP handshake 통과, finish EXITED0·tree_cleanup/connection_closed VERIFIED. fake actor 요청0, native turn/Pre/Post는 미실행 |
| 최초 실패 보존 | `e2e-attack/failure.json`의 시험용 container layout adapter 오류와 `e2e-attack-2/failure.json`의 함수 복원 불일치를 보존했다. 실패를 E2E 통과로 바꾸지 않았다 |
| 복원 수리 | 변경 가능한 FunctionInfo/AliasInfo 참조 대신 값 snapshot. PS5.1 함수/별칭 복원·오류 시 상태 보존·ReadOnly 거절4시나리오 PASS, `wrapper-check.json`. helper는 wrapper만 검증하며 native 종단 대체물이 아니다 |
| 별도 검토 발견 수정 | HANDS-R1: ALLOW/OBSERVED만으로 NO_ATTACK_ATTEMPT를 단정하던 표시를 `REVIEW_WRITE_ALLOWED_ATTACK_ADOPTION_UNASSESSED`로 수정. 독립 내용 검토 전 확정/차단 성공 계산 금지 |
| 검토 수정 관련 재진단 | 17 PASS/5.94초, `related-review-fix.txt`. 소진 claim/ledger 각각 재시작 거절 추가 |
| 관련 경계 추가 | 22 PASS/2.22초(33 deselected), `boundaries-final.txt`: 다중 실제 user turn/위조·stale binding/분석실패·UNKNOWN·예약 경쟁·host reviewer. sandbox 단위/컴포넌트 근거이며 native hooks 실증으로 확대하지 않음 |
| 최종 Ruff | PASS, `lint-review-fix.txt` |
| Bandit 전후 | 각16경고 동일: B404 LOW3/B603 LOW6/B108 MEDIUM5/B105 LOW1/B104 MEDIUM1. 원 JSON/stdErr 보존. subprocess 고정 argv/shell 없음, tmpfs/시험 fake key·TLS listener, legacy 예약512000 상수의 B105 문맥을 검토했다. 무경고/전체 보안 PASS가 아님 |
| 실제 환경 무모델 준비 | `prepare.json`/`ready.json`: issues0, bundle/image 일치·기존 키 메타데이터·TLS gateway initialize/initialized/tools-list PASS, tools_call/user_turn/candidate0·unbound probe connection 제거 |
| 실행 전 실제 history/viewer | `history-prepared.txt`, 이력0/효과0/NOT_OBSERVED/source match true, 새 고유 HTML만 저장 |
| 보존 | `preservation-before.json`/`preservation-after.json`: 역사48파일 hash·개인 config hash/auth/hooks 메타데이터 일치. 실제 키 body/hash를 읽거나 출력하지 않음 |

자동 승인 검토는 격리 fake CODEX_HOME의 세 hooks 신뢰 활성화를 거절했다. 사용자는 신뢰 변경 없이 나머지 완료를 선택했다. native CLI를 과업 입력 없이 종료했고 hook 신뢰0·fake actor요청0이다. fake home의 앞선 **디렉터리 trust** prompt 수락은 `native-boundary.json`에 별도 명시했다. 개인 전역 설정은 변경되지 않았다. hooks 신뢰 변경을 다른 경로로 우회하거나 성공 stub으로 대체하지 않았다. actual native Pre/Post·같은 CLI의 정상/위험/공격무시 종단은 NOT_RUN이다.

## 동결·한도·인계

새 manifest SHA256: **`dbb7ecd4cc778f33836a0dd6c9b359782936f4063814b5a927bfe34277c04a38`**.

실제 hands-on 환경은 `PREPARED_DISABLED`/`JEV_RULES_ONLY`/`jev_live NOT_AUTHORIZED`다. 새 provider ledger 없음·요청0/입력예약0·CLI claim0이다. 기존 core4/4·역사29/1856000·CLI5 기록을 보존했다. 새 사용자 선택안은 Jev8/예약512000·CLI1/1800초이며 누적 상한37/2368000·CLI총6, actor 비용은 별도다. 사용자 실행 전 새 유료 사용 승인/소비로 계산하지 않는다. 개발 중 제품 actor/Jev 실제 호출0·실제 유료actor 시작0이며 개발 AI 토큰/별도 AI 검토 사용과는 구분한다. 격리된 실제 native 프로세스는 fake endpoint fixture에서만 한 번 시작했다.

기존 core의 실제 정상 자동 ALLOW/쓰기1/승인0과 고정 위험 후보의 실제 gateway/Jev 의미 DENY/쓰기0은 보존 증거다. 이번 same-CLI 실제 actor 공격 채택/차단이나 hands-on 실제 성공의 증거로 대신하지 않는다. 원본8개·신규2개 diff/hash는 `original/`, `candidate.diff`, `candidate-hashes.json`에 있다. 관리 plans/harness/AGENTS를 수정하거나 DONE으로 바꾸지 않았다.

필수 기준은 `docs/plans/03_guide_compliance.md`와 기존 GUIDE_MAPPING을 재사용하고 원문12페이지를 `guide-pages.json`에 보존했다. R1 PDF14/G1 PDF35–36→기존 image/bundle 동결·무빌드; G2 PDF128–129→예약/단회/상한, PDF135/137→안전한 오류 처리; G3 PDF507–508/510→정확 입력·권한·RO 키, G4 PDF24/38→진단/수리/재진단과 인증 경계에 연결했다. 이번 노출 P0는 권한·출처/인자 binding·예산/단회·UNKNOWN·비밀·TLS/역할을 유지한다. 설계20/약점49 전수·TLS 전체 negative·hook 사망 fail-open·일반 native/모든 IPI·인과/모델 정확도·B 오판 가능성의 기존 미완료를 PASS로 올리지 않는다.

복사 가능한 **연결→직접 codex→권장 입력→이력**은 [USER_RUN](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-hands-on/USER_RUN.md)에 있다. 신뢰 미변경 상태의 native 종단 제한을 먼저 명시했다. [별도 AI REVIEW](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-hands-on-review/REVIEW.md)는 공식 외부 독립진단이 아니다.
