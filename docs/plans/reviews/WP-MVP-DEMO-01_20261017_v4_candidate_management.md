# V4 후보 수용 범위와 다음 검증

2026-10-17. **수치 수리와 V4 오프라인 후보는 수용하며, V4 실제 모델 평가용 연결 준비를 배정한다. 배포/정상 자동 허용/실제 공격 차단/MVP 완료 수용은 아니다.**

## 확인한 사실

[관리 관측](../../../artifacts/management-auto-v4-ready-20261017/observation.json): candidate manifest7개 현재 SHA 일치, 제안 normal/attack A/B 네 wire의 모델/질문수/크기/hash 확인, 기존 Jev8행 COMPLETED·입력16356/출력2108·예약512000, 실제 성공 normal.md hash 동일이다. episode3는 EXITED/exit0/connection·tree VERIFIED로 정상 종료됐다. 관리 모델호출/키 본문·키hash 접근0이다.

원 USER .92/5 정규화의 .90 경계와, 9선택지에서 실제 .90 미만을 float가 .90으로 올리는 반례의 조치를 RESULT/REVIEW에서 대조했다. 기존 실응답은 수치 수리 후에도 CONFIRM이다. 다른 낮은 confidence는 바뀌지 않았으므로 수치 결함만으로 정상 자동 허용이 해결됐다고 하지 않는다.

V4는 USER/적법한 위임의 허용 의미를 INDEPENDENT로 묶고 각 source의 slot 지지를 독립 질문으로 분리한다. MCP text envelope의 decoded 본문은 원문/catalog/ref/offset을 유지한 보조 문맥이다. envelope가 저확신의 인과 원인이라는 주장은 미입증이다. source 전체 보조 문맥과 개별 raw span의 지지를 혼동하지 않는 제약과 입력 cap 한계도 문서에 있다.

작성자 관련102/통합688·정적검사, 별도 검토의 정확 유리수/추가 지시·split span 반례와 보존 증거를 검토했다. 관리가 해당 전체 시험을 재실행한 것은 아니며 합성 관측 결과를 실제 Jev 정확도로 세지 않는다.

**운영 연결은 아직 없다.** V4 router는 테스트/후보에만 있고 현재 server profile에서 선택하지 않는다. `jev_eval.ps1`의 실행 RunId도 기존 followup-response-v2만 허용한다. FUTURE_EVAL_PROPOSAL은 정확 자료·한도 제안이며 실제 실행 가능한 V4 run이 아니다. 과거 evaluate/start 명령을 그대로 실행하지 않는다.

## 계획상 위치

| 기능/단계 | 현재 근거 |
|---|---|
| 등록 파일 MCP의 Codex/hooks/실제 gateway/도구 연결 | 실제 읽기 성공 |
| 출처·판정·실제 효과 기록 | 실제 읽기/쓰기·별도 원장과 대조, 인과/완전 receipt 주장은 아님 |
| 불확실 판정의 사람 승인·단회 재개 | 실제 CONFIRM 승인·소비/resumed1·OBSERVED·보고서 성공 |
| 정상 자동 허용·외부 추가 행동 자동 차단 | **핵심 미완료. V4 실제 의미 평가 전** |
| V4 실모델 통과 후 제품 통합/사용자 재현 | 미수행. 이번 direct4요청은 executor/actor 시험을 대신하지 않음 |
| 일반 native/hook 장애 경계·제출 전 보강 | 기존 미완료 범위 유지. 현재 적용 P0/필수 가이드는 계속 필수 |

## 다음 결정

[V4 평가 연결 작업](../../handoffs/WP-MVP-DEMO-01/V4_EVAL_START_PROMPT.md): 기존 JevClient/jev_eval을 재사용해 고정 run `followup-auto-v4`의 실제 실행 경로를 모델0으로 완성한다. 정상A→B→공격A→B 총4요청/추가예약256000/CLI0회 제안이다. 새 예산을 실행하지 않고 source/wire/bundle/기존 closed ledger 결합·inspect/preflight/evaluate/collect와 정확 사용자 명령을 한 인계로 준비한다. 정상/공격 각1건은 작은 의미 smoke이며 전체 정확도를 입증하지 않는다.

현재 demo8/512000은 소진·유지한다. 선택 시 제안 누적은 demo관련12/768000, 과거5/320000 포함 전체17/1088000이다. 새 실제 실행은 구체적 준비를 검토한 뒤 사용자의 직접 선택으로 남긴다. 통과하면 V4 제품 연결/실제 CLI 재현, CONFIRM/오류이면 해당 typed 결과를 근거로 판단하며 threshold 임의 하향이나 자동 반복을 하지 않는다.
