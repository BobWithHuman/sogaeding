# WP-MVP-DEMO-01 정상 의미·CONFIRM 후속 수정

2026-10-17. 요청한 개발/오프라인 통합을 완료했다. 개발 AI의 실제 actor/Jev 유료 호출은 **0**이다. 새 사용자 LIVE 정상 자동 완료·실제 위험 후보 차단은 **NOT_RUN**이며 전체 MVP 완료로 판정하지 않는다. 현재 실제 서비스는 V2, 시작2/2·Jev4/8 그대로다. 새 V3와 추가 시작1회는 공개 준비/사용자 선택으로만 인계했다.

## 변경과 동작

- **의미 질문/합성**: 새 `jev_semantic_v3.py`, 정책 `hookgw-2026-10-17-jev-v3`, 질문 `jev-narrow-3`/계약 `jev-slots-context-3`. WITHIN_TASK/OUTSIDE_TASK/UNCERTAIN과 action/target/options/payload별 USER/TASK_DATA/GENERATED/ADDED_INSTRUCTION을 구별했다. USER/GENERATED에 불필요한 외부 link를 요구하지 않고 실제 필요한 출처에는 catalog/원문/ref 검증을 유지한다. .90와 최소 confidence는 그대로다. 검증된 추가 지시/OUTSIDE를 다른 슬롯 불확실성으로 희석하지 않는다. 출처 일치/모델 라벨로 grant를 늘리지 않는다. 기존 v2 파일은 그대로 보존한다.
- **실제 인간 승인/동일 호출 재개**: `demo_approval.py`/engine/server의 human `/demo/pending`과 기존 `/approval`, machine `/demo/wait`를 별도 `mvp_confirm.ps1` 사용자 터미널에 연결했다. 정확 candidate·요청·근거·불확실성을 보고 approve/reject를 직접 선택한다. actor/MCP 인증으로 승인 불가. 검토600초 내 새 인간 권한30초를 발급하되 원 분석시각/CONFIRM을 덮어쓰지 않는다. 현재 session/turn/source/grant/policy/정확 canonical RPC를 실행 직전 재검사하고 소비+예약을 한 transaction으로 수행한다. 동일 RPC 한 번만 재개하며 새 모델 호출은 없다. native host Allow와 PDP 승인은 다르다.
- **같은 후보 비용/효과 중복 방지**: 동일 connection/session/turn/policy/정규화 semantic write intent는 actor 새 call ID에도 기존 pending/terminal을 안내한다. source 변경·거절·실패·UNKNOWN·기실행을 자동 분석/쓰기 재시도나 환불로 우회하지 않는다. 실제 새 사용자 turn만 새 위임을 만든다. 읽기 전체를 이 제한으로 차단하지 않는다.
- **안전한 읽기 오류**: 유효 예약 후 read open의 확정 파일 부재는 고정 `FILE_NOT_FOUND`/`OBSERVED_ERROR`, source 생성0이다. raw 예외/경로/stack은 반환하지 않는다. 실제 응답 유실은 UNKNOWN이며 과거 UNKNOWN도 소급 해제하지 않는다.
- **도구/화면/설치**: MCP가 동일 요청을 대기하고 실제 존재하는 별도 승인 CLI 또는 명시적 중단을 안내한다. child MCP timeout720초·전체 CLI1800초, 전역 설정 변경0. viewer는 CONFIRM/사람 소비/실행·typed 오류·UNKNOWN·episode3 종료를 분리한다. 새 승인/런처 경로는 등록된 파일 도구의 자체 수정 대상에서 제외한다. 일반 파일 편집은 유지한다.

계약은 `docs/mvp/11_semantic_confirm.md`, 필수 PDF→위험→코드→시험은 [GUIDE_MAP.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-mvp-semantic-confirm/GUIDE_MAP.md), 정확 사용자 절차는 [USER_RUN.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-mvp-semantic-confirm/USER_RUN.md)에 있다. 관리 정본(plans/harness/AGENTS)은 수정하지 않았다.

## 기준선과 실증

기준선: `artifacts/20261017-mvp-semantic-confirm/baseline-source`, 222파일, fingerprint `af89e13d13540d310f5a909ae0b78b0958a89e9b99153d1a164d0a4e3360b695`. 저장소는 기존 전체 untracked 상태여서 Git diff만을 변경 증거로 사용하지 않고 매 실행 source snapshot을 남겼다.

최종은236파일/fingerprint `53e3daa16cf76cc3660fae9e163b78cf6331edd57e51b9eb676d00cea64bc3b3`, 변경·신규26파일은 `artifacts/20261017-mvp-semantic-confirm/changed-source-files.json`, 검증 요약은 `final-index.json`이다. 원키 metadata의 크기/ACL/수정시각도 before/after 동일(`key-metadata-comparison.json`); 키 본문·hash는 읽지 않았다. 첫 metadata 비교의 PowerShell 자동 DateTime/string 형식 차이는 DateTimeOffset 비교로 바로잡았고 파일 변화는 없었다.

| 확인 | 실제 결과·증거 |
|---|---|
| 기존 실응답 정책 재현 | 원 enum/수치 그대로 v2 두 CONFIRM 재현. `artifacts/20261017-mvp-semantic-policy/`. 원 catalog/암호화 snapshot은 관리 projection에 없어 같은 short-key의 유효 합성 catalog를 사용한 **정책 합성 재현**이다. 전체 원 요청의 복원이나 새 V3 정확도 증거가 아니다. 확률 합산/승격0 |
| 최종 hookgw/F3/하네스 | **613 PASS/49.01초**. `artifacts/20261017-mvp-semantic-confirm/integrated-final-observation-mount-command.json`/`.txt` |
| 실제 pinned gateway/파일MCP | **58/58 PASS**, paid0·forbidden effect0. `.../actual-gateway-final-serial-command.json`, `.../gateway-final-serial/evidence.json`. 정상 자동 쓰기, 외부 위험 DENY, 승인·거절·단회 재개, old freshness 경과, 중복provider0, typed 부재, 실제 transport유실UNKNOWN 포함. provider 응답은 명확히 가짜이며 실제 actor/Jev 정확도 시험이 아니다 |
| 별도 AI 검토 | 독립 반례 **56 PASS**. 실제 Windows PowerShell5.1 human CLI에서 검토자가 `approve`/`reject`를 직접 입력한 gateway **58/58 PASS**. `artifacts/20261017-mvp-semantic-review/`. 작성자와 분리된 보조 AI 검토이며 공식 독립 진단/추가 사람 개발자가 아니다 |
| 정적 검사 | 최종 Ruff PASS. `final-bandit.txt`는 exit1/Medium2·Low2, 무조건 PASS 처리하지 않음. 컨테이너 내부 기존 TLS bind0.0.0.0 2건(B104): 기존 localhost published port/서비스 TLS 인증 유지. subprocess import(B404): 고정 argv·shell 미사용·정확 SHA/user gates. 512000(B105): 비밀번호가 아닌 기존 입력예약 숫자. suppress0·새 패키지/이미지0 |
| 실제 PS5.1 준비/점검 | `followup-prepare-ps51`/`followup-check-ps51`: exit0, PREPARED_NOT_DEPLOYED, issues[], readytrue, MCP initialize/list, tool calls0/user turns0. actor key존재/Jev 키metadata만 확인, 유료 접근 자체는 NOT_VERIFIED_NO_REQUEST |

기존 A/B 핵심 **30 PASS/51.12초**(`ab-core-isolated-final`), 장애·복구 **8 PASS/33.53초**(`hardening-isolated-final`)도 별도 네트워크 없는 컨테이너에서 순차 검증했다. command.json/.txt는 같은 artifact 루트에 있다. 테스트 횟수는 겹치는 검증이므로 합산해 독립 표본 수로 주장하지 않는다.

## 검토 발견·실패의 보존

SC-SEM-01(확정 지시가 다른 불확실성에 희석), SC-APP-02(source변경 후 빈 승인 UI 안내), SC-START-03(preflight 후 manifest결합) 모두 수정하고 독립 재진단했다. 승인 helper 파일 자체도 공개 source binding에 넣고 이후 사용량 증가/소스 변화에도 읽기 전용 episode3 이력을 제공한다.

최초 source lint 정렬/unused, 가짜 response fixture 오류, 승인 clock 주입 불일치, 양측 offline Compose project 충돌, 통합시험 관측 JSON 미마운트(610PASS+3FAIL), 과거 혼합 A/B 명령 재사용으로 fixture 공유 포트 오류(30PASS+8ERROR)는 각각 원 command/output으로 보존했다. 제품/실제 provider 실패나 공격 식별 PASS로 바꾸지 않았다. fixture 수정 뒤 최종 gateway58/통합613은 성공했다.

## 보존과 사용자 선택

원 manifest454/hostwait f1, 실제 Jev4행(입력6804/출력924), 기존 실패/원장/예약·두 claim·upstream2행·원call6행과 보고서 부재는 별도 AI의 opaque row/hash 대조로 유지했다. 기존 두 CONFIRM은 이전 CLI close 후 **STALE/decision CONFIRM**, 기존 UNKNOWN1도 그대로다. episode2의 자연 종료 기록은 TIMEOUT1800초/cleanup VERIFIED, episode1 종료는 UNKNOWN으로 유지한다. 키 본문/키hash를 읽거나 인증/전역 CA를 변경하지 않았다.

새 공개 proposal `artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/manifest.json` SHA:

`53b521a42358fdce9575225377233baae1b225647e9f17625c53690df336f0f8`

독립 source62/bundle39 대조 일치. 현재 배포/새 claim3/예산증액0. 사용자가 USER_RUN의 정확 승인값을 직접 선택할 때만 같은 원장·키에 V3를 활성화하고 추가 시작1/총3을 소비한다. Jev 총8/예약512000은 유지하며 남은4/256000만 사용, actor 비용은 별도다. 소스/문서/원장 변조·기준선 변화 시 새 예산 발급 대신 중단한다.

## 남은 범위

실제 새 V3 Jev 성능/보정, 사용자 정상 자동 보고서, 실제 위험 후보의 실행 전 차단은 사용자 LIVE 확인 전 미완료다. 내장 셸/모든 IPI/자유 native 일반개발·hook 사망, 동일 OS 사용자 공격, 전체 TLS negative/키수명/공급망/C/D 전수 진단은 기존 범위대로 남는다. 이번 fake 시험으로 이를 대체하거나 전역 DONE 판정하지 않는다.

별도 최종 검토: [REVIEW.md](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-mvp-semantic-confirm-review/REVIEW.md).
