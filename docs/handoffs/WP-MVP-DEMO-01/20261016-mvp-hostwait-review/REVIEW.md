# WP-MVP-DEMO-01 HOST_WAIT 별도 AI 검토

2026-10-16. with-human-dev와 REPAIR_HOST_WAIT_PROMPT 전체, 최신 AGENTS, 관리 host_wait review·observation, 기존 RESULT/REVIEW/USER_RUN을 읽었다. 사람 개발자는 사용자1명이며 본 검토는 구현 담당과 분리된 AI 보조 검토다. 공식 독립 보안 진단이 아니다. **보완 코드와 오프라인 시험은 좁은 시연 준비 범위에서 수용 가능하다. 실제 재현한 P1은 수정·독립 재진단 완료했으며 미해결 차단 지적0이다. 최종 revision/실제 무모델 READY·보존·RESULT/USER_RUN 대조를 완료했다.** 사용자 실제 정상 보고서/모델 정확도·전체 MVP 완료를 판정하지 않는다.

제품/관리 파일은 읽기 전용으로 검토했다. 쓰기는 본 REVIEW와 배정 artifacts만 했다. 실제 actor/Jev/provider 호출0, 기존 키 본문/hash 접근0, 개인 로그인·설정·CA 변경0이다. 가짜 키와 새 로컬 Windows/격리 gateway fixture만 사용했다.

## 기준선·계약

[독립 기준선](../../../../artifacts/20261016-mvp-hostwait-review/baseline.json)은 기존 공개13파일 SHA 동일, 원 manifest454466…8ed05·episode-1.claim·첫 실패 HTML·정책 파일을 고정했다. 읽기 전용 DB mode=ro+query_only에서 기존 DENIED1/READY 공개 read1·upstream에 도달하지 않은 상태, provider 원장 없음·시작1/2·남은1, 정상/금지 보고서 없음을 확인했다. 실제 첫 actor는 실행됐으며 종료 원인과 actor 청구는 UNKNOWN이다. 180초 timeout과 부합하는 시각만으로 원인을 확정하지 않는다.

새 revision은 원 runtime/DB/키/8요청·512000/시작2한도를 이어받고 시작 예약1회를 남긴다. 대화형1800초는 사람 대기와 실행을 합산한 **새 명시 선택**이며 원180초를 자동 연장하지 않는다. 종료 시 연결 닫기와 OS 자식 정리의 별도 유예가 있다. 과거 Jev5시도/320000 및 최초 사용량 UNKNOWN·followup4완료4614/780을 보존한다.

demo 전용 PreToolUse는 정확 candidate의 PENDING intent만 기록하고 PDP ALLOW를 반환하지 않는다. Codex 호스트 승인을 통과한 실제 MCP 요청에서 같은 connection/turn/인자·요청·출처·grant/policy를 단회 claim한 뒤 기존 Jev 판정과30초 freshness/원자 forward를 실행한다. 승인 대기 동안 의미 판정/lease를 소비하지 않고 old READY를 갱신하지 않는다. 범위/금지 설정의 hard 거부는 유지한다. 새 경로의 CONFIRM은 효과0으로 멈추고 자동 resume/재분석은 제공하지 않는 좁은 한계이며 기존 별도 인간 승인 통제는 보존한다.

`/demo/close`는 machine 인증과 opt-in gate 아래 해당 child connection의 새 intent만 정리한다. 대기/분석은 STALE, 이미 전달 중이면 UNKNOWN이며 원 reason·claim은 보존한다. 다른 connection·과거 legacy READY를 재실행하지 않는다. 새 요청과 로컬 Job tree 종료는 이미 전달된 원격 upstream 효과를 철회하지 않으며 UNKNOWN의 사후 효과 가능성/무환불·무재시도를 문서에 유지한다.

## 발견·조치·독립 재진단

**HOSTWAIT-LIFE-01/P1**을 실제 Windows에서 재현했다. `stop_control()`이 Exception만 잡으므로 연결 close callback 도중 KeyboardInterrupt가 나면 `finally`의 Job terminate/handle close까지 건너뛰었다. 호출자는 interruption을 잡고 history를 조회하는 동안 child가 살아 있을 수 있었다. [첫 반례](../../../../artifacts/20261016-mvp-hostwait-review/cleanup-interrupt-r1.json)는 STARTING만 남고 로컬 손자 지연 파일 생성=true다. fixture 종료 시 Windows Job handle이 닫혀 남은 자식은 종료됐다.

작성자는 callback 중단 포착, SIGINT 정리 구간 보호/원 handler 복원, 중첩 finally의 Job kill·ActiveProcesses0·handle close를 추가했다. [동일 실제 반례 재진단](../../../../artifacts/20261016-mvp-hostwait-review/cleanup-interrupt-r2.json)과 [최종 소스 재진단](../../../../artifacts/20261016-mvp-hostwait-review/cleanup-interrupt-r3.json)은 FINISHED/INTERRUPTED·started=true·tree VERIFIED·connection UNVERIFIED를 보존하고 지연 파일=false다. 실패를 LAUNCH_FAILED/미시작으로 바꾸지 않는다. 실제 서비스/모델/키 접근0이다.

P3 진단 피드백으로 과거 LEGACY_UNKNOWN에 started=false를 합성하던 값도 제거했다. claim만으로 미시작을 확정하지 않으며 과거 실제 종료는 UNKNOWN이다. [발견 이력](../../../../artifacts/20261016-mvp-hostwait-review/findings.json).

자체 **47개**(dispatch19/runtime17/viewer11)를 포함한 최종 관련 회귀 **117 PASS/7.47초**다. [명령·결과](../../../../artifacts/20261016-mvp-hostwait-review/regression-final.json). network none/비root/RO source Docker, 새 임시 DB/가짜 키·MockTransport만 사용했고 실제 runtime/키/원장은 마운트하지 않았다. 정확 duplicate intent 모호성·무비용 거절, 분석 중 connection/grant/source/turn 변경, 공개 listener authz 차단, 자가 authority 필드 거절, claim 이후 장애 영구 보존, close 중분석 STALE/no-ticket, EXECUTING close→UNKNOWN, 타 connection/원 claim 보존, 각 종료 main의 비정상 exit·이력조회/재시도0, 새 wall·한도 tamper·append-only·typed 안전 화면을 확인했다. 작성자 회귀와 중복되므로 합산하지 않는다.

실제 Windows PowerShell5.1의 동등 대화형 자식은 [최종45/45 PASS](../../../../artifacts/20261016-mvp-hostwait-review/native-lifecycle-r5.json)다. 입력 대기 후 명시 승인 전 효과0/후 정상 파일, exit7, timeout2초, cancel_event 경로, 정상 종료 시 남은 손자, launch 실패, Job tree 정리/손자3초 지연 효과0, close callback·SIGINT handler 복원을 확인했다. 자동 즉시 성공 subprocess mock이 아니다. 이전r4 뒤 import 정렬만 바뀌었지만 최종 current SHA와 일치하는r5를 다시 실행했다. cancel_event와 callback KeyboardInterrupt는 제품의 취소/정리 경로 주입이며 실제 데스크톱 OS Ctrl+C 전달·Codex TTY·창 닫기·서비스/broker 생성 작업을 검증했다고 확대하지 않는다.

초기 Windows fixture -File은 기존 실행 정책의 AuthorizationManager 거부를 받았고 검토 assertion이 없는 파일을 읽어 실패했다. 고정 신뢰 fixture를 inline command로 실행하여 정책/전역 설정 변경 없이 고쳤다. 다음 회차의 harmless PS CLIXML progress·너무 이른 cancel 타이머 assertion 오류도 원기록을 보존하고 대기 신호 뒤 취소하도록 검토 fixture만 수정했다. 통합 회귀 초기115PASS/1FAIL은 draft 미지원 skip_host_skill_discovery 옵션을 검토 assertion에서 요구한 오류이며 제품 결함으로 세지 않았다. [각 원실패](../../../../artifacts/20261016-mvp-hostwait-review/native-r1-failure.json), [2차](../../../../artifacts/20261016-mvp-hostwait-review/native-r2-failure.json), [회귀](../../../../artifacts/20261016-mvp-hostwait-review/regression-r1-failure.json).

## 실제 gateway·화면·맥락

[독립 실제 gateway](../../../../artifacts/20261016-mvp-hostwait-review/gateway-r1/evidence.json) **28/28 PASS**. 실제 TLS hook 프로세스→MCP bridge→digest 고정 agentgateway→실제 파일 upstream을 통과했다. 실제1.1초 대기와 시험 전용 논리35초 경과 뒤 PENDING/model0에서 fresh Jev 두 관측→정상 파일 생성/OBSERVED, 인자변조/replay 거절, 외부 문서 활용, 강제 위험 후보 DENY/금지 파일0, close 이후 late dispatch0을 확인했다. upstream3/OBSERVED3·fake Jev4, 실제 provider0이다. source hash 시작/종료 일치를 기록했으며 fixture는 down했다. 강제 후보·경로 기반 fake oracle은 시험 코드에만 있고 실제 Jev 정확도/actor 공격 유도 증거가 아니다. 관측은 원자 receipt/인과 증명이 아니다.

화면은 USER_DEMO/OFFLINE_REPLAY·CLI 시작/종료와 정책/관측/파일 효과를 분리하고, PENDING은 ‘호스트 승인·집행 요청 대기(PDP 미실행)’로 보인다. 분석 오류·CONFIRM·UNKNOWN·미시도는 공격 PASS가 아니다. lifecycle 필드는 enum/수치/UTC/episode allowlist만 반환하며 raw argv/env/터미널 기록을 노출하지 않는다. `bob-agentgateway:4400`은 별도 개인 MCP 상태로 표시한다.

작성자의 현재 실제 이력 screenshot도 직접 봤다. USER_DEMO·Jev0·시작1/2·legacy 종료 UNKNOWN, 예전 범위 밖 거절/공개 읽기 READY·upstream0·두 파일 없음·공격 관측0을 읽을 수 있으며 정상/LIVE 성공으로 표시하지 않는다. 오프라인 화면 예시의 종료 이벤트는 화면 시험용 합성임을 RESULT에서 구분했다.

개발 AGENTS·하네스 오염을 줄이는 child-only project_doc_max_bytes=0 및 정확 with-human-dev SKILL.md의 enabled=false를 검토했다. 미지원 skip_host_skill_discovery 옵션은 설치 CLI의 features list에서 true 지원 근거가 없어 제거했고 원 실패를 보존했다. 작성자의 PS5.1 argv15/15·설치 CLI 무경고 parse/기존 hooks·user reviewer/on-request 유지 증거를 대조했다. 실제 LIVE prompt skill catalog 제외는 NOT_OBSERVED이며 개인 설정을 삭제하거나 sandbox/approval을 끄지 않았다.

## 가이드·잔여

[최종 독립 대조](../../../../artifacts/20261016-mvp-hostwait-review/final-check.json)는 동결222파일 fingerprint `af89e13d13540d310f5a909ae0b78b0958a89e9b99153d1a164d0a4e3360b695`의 현재/동결 SHA 불일치0, 검토runtime43개 불일치0을 확인했다. 새 revision manifest는 `f1c49257c270ac416b8144f2523a7dcdae1966ff908fc42cfa79f299ea1bf547`이며54source와 bundle36개 exact set/current 일치, 부모454/원13자료·demo공개4파일·기존2암호문행·키 metadata/ACL 일치다. episode2/새provider원장/두보고서 없음·남은1, 원READY read 상태 보존, gateway28 current source/image 일치, 문서 로컬 링크 누락0이다. 실제 PS5.1 `check` READY/issues none·model0과 보존 이력을 대조했고 유료 start는 실행하지 않았다.

작성자 전체 관련506 PASS/43.62초, 기존 A/B·TLS·승인·경쟁30 PASS/49.98초 및 장애8 PASS/33.79초 증거를 읽었다. 최초 합친 fixture 포트 충돌·새 Compose mount 누락·RO lint cache 실패와 수정 명령의 재진단을 구분했다. 수정8Python Bandit 전체 범위는 **HIGH0/MEDIUM7/LOW8·errors0/exit1**이며 clean PASS가 아니다. [수동 판별](../../../../artifacts/20261016-mvp-hostwait/static-triage.md)의 container listener B104·tmpfs/공개 fake key B108·고정 argv subprocess B404/B603를 실제 source/Compose·negative 시험과 대조했다. 작성자 최초 dispatch subset Medium1 결과와 전체 범위를 혼동하지 않으며 PowerShell/Windows ABI는 scanner 범위 밖이다.

필수5 PDF의 원 SHA를 재검증하고 이번 변경 관련16페이지를 원본에서 다시 읽었다. [원문 증거](../../../../artifacts/20261016-mvp-hostwait-review/guide-pages.json). G2 PDF135/137·G3 PDF511은 고정 오류/중단·비민감 lifecycle·UNKNOWN, G2 PDF146·G3 PDF415는 Job/handle 정리·유한 wall, G3 PDF508/509·G4 PDF37~39는 exact 입력·서버 권한/connection·출처/정책/단회 예약, G4 PDF24는 실제 동적 반례→조치→재진단에 연결한다. R1 PDF14·G1 PDF35~38은 기존 이미지 pin·변경 binding/원본 보존·회귀/격리에 연결했다. 새 dependency/image 설치0이며 기존 설계20/약점49 미완료·공급망/C/D 잔여를 유지한다.

최종 실제 사용자 시작·정상 보고서·Jev 의미 정확도·전체 native/모든 IPI·hook 사망 fail-open·동일 OS/helper 변조 경계는 미검증/미완료다. 실제 위험 후보가 없으면 NO_ATTACK_ATTEMPT다. 사용자 남은1회 정상 시연 이후 최종 수용·전역 DONE은 관리 세션 판단이다.
