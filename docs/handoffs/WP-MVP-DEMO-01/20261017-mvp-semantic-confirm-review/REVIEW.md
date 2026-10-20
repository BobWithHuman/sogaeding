# WP-MVP-DEMO-01 SEMANTIC_CONFIRM 별도 AI 검토

2026-10-17. **배정한 코드 보완과 오프라인 검증·사용자 후속 준비 범위에서 수용 가능하다. 미해결 차단 지적0이다.** 독립 반례56개, 실제 PowerShell5.1 대화형 승인/거절 gateway58개, 최종 작성자 통합·source·보존·RESULT/USER_RUN을 대조했다. 실제 V3 LIVE 성능·정상 자동 완료·전체 MVP 완료를 판정하지 않으며, 새 코드는 현재 서비스에 미배포다. 관리 세션의 전역 DONE 판단을 대신하지 않는다.

검토자는 구현자와 분리된 AI이며 추가 사람 개발자나 공식 독립 보안 진단 기관이 아니다. 제품·관리 파일은 읽기만 했고, 검토 산출물은 이 문서와 `artifacts/20261017-mvp-semantic-review/`에만 작성했다. 실제 actor/Jev/OpenAI 호출0, 기존 키 본문·내용 hash 읽기0, 기존 암호문 복호화0, 사용자 CLI·실제 제품 프로세스 조작0이다.

## 기준과 최초 사실

`REPAIR_SEMANTIC_CONFIRM_PROMPT.md`, 최신 AGENTS·with-human-dev, 관리 semantic_confirm 검토·안전한 observation, 기존 host-wait 인계를 기준으로 검토했다. 기존 v2의 과거 실제 의미 응답을 성공으로 바꾸거나 낮은 confidence를 올리는 수정은 허용하지 않았다.

독립 기준선은 [baseline.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/baseline.json)에 있다. 기존 비밀 아닌 원증거23파일, 원 call6행의 암호문 포함 불투명 digest, 실제 Jev4행/원장, upstream행, 두 claim과 event를 읽기 전용 SQLite로 기록했다. 원 실제 Jev는 **4/8요청·예약256000/512000·입력6804/출력924**이고 CLI 시작은 **2/2**다. 이전 WP-PDP의5시도/320000과 첫 usage NULL도 보존 대상이다.

관리 관측 뒤 생성된 episode2 FINISHED를 기준선에서 확인했다. **TIMEOUT/1800초·tree_cleanup VERIFIED·connection_closed VERIFIED**이며, 원 두 decision CONFIRM은 close 후 state STALE다. 이를 새 승인 가능한 후보나 성공으로 바꾸지 않았다. episode1의 종료/청구 UNKNOWN 및 기존 읽기 UNKNOWN은 별개로 남는다. 실제 보고서 두 파일은 여전히 없다.

## 독립 검증

|검증|결과와 한계|원증거|
|---|---|---|
|과거 실제 typed v2 재현|2건 모두 CONFIRM/SEMANTIC_UNCERTAIN. 저장된 choice/분포/provider confidence 그대로 사용. 새 합성 유효 catalog이며 원 암호화 snapshot/ref 복원 아님|[legacy-replay-result.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/legacy-replay-result.json)|
|새 V3 의미 반례|24 PASS. 정상 사실·정당한 안내·인용/금지·다중 출처·USER 대상·GENERATED·외부 action/target/options/payload 변경·진짜 낮은 확신·정확 ref/hash 검증|[test_semantic_independent.py](C:/sogaeding/artifacts/20261017-mvp-semantic-review/test_semantic_independent.py)|
|승인·중복·업무 오류|19 PASS. human 전용 인증, same RPC 단회·경쟁, 변조·만료·source 변경·close·거절, 새 call ID 분석 증가0, typed missing read와 진짜 UNKNOWN 분리|[test_approval_independent.py](C:/sogaeding/artifacts/20261017-mvp-semantic-review/test_approval_independent.py)|
|신뢰 도구·최종 승인 SHA·이력|13 PASS. parser/hook/upstream의 새 helper 보호·정상 개발 파일 허용, check 중 manifest 교체 시 claim 이전 차단, human UI hash drift 차단, 사용량/source 변화 후 episode3 이력도 예산 재개 없음|[test_final_boundaries.py](C:/sogaeding/artifacts/20261017-mvp-semantic-review/test_final_boundaries.py)|
|최신 독립 합계|**56 PASS/1.60초**. 네트워크 없는 Docker·공개 소스 RO·합성 임시 DB. 실제 runtime/키 미마운트|[unit-final-r2-result.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/unit-final-r2-result.json)|
|실제 gateway·사람 승인 경로|**58/58 PASS**. 고정 digest gateway·로컬 TLS·실제 hook/MCP/upstream·가짜 Jev. 검토자가 실제 Windows PowerShell5.1 상속 stdin에서 후보1을 고르고 직접 `approve`, 다음 후보에서 `reject` 입력|[gateway 증거](C:/sogaeding/artifacts/20261017-mvp-semantic-review/gateway-interactive-r1/evidence.json), [human 실행](C:/sogaeding/artifacts/20261017-mvp-semantic-review/gateway-interactive-r1-human-invocations.json)|

실제 승인 CLI는 정확한 candidate·USER 요청·source·불확실성·만료를 표시했다. 승인된 **기존 대기 MCP RPC**만 한 번 실행되어 합성 보고서가 생성됐고 원 decision CONFIRM/analyzed_at가 유지됐다. 거절 파일과 공격 보고서는 없었다. 정상 자동 보고서는 생성됐다. 승인/거절 재개에 provider 증가0, 동일 후보 새 call ID에도 provider 증가0이었다. 파일 부재는 OBSERVED_ERROR/FILE_NOT_FOUND이며 source를 만들지 않았고, 진짜 응답 유실은 UNKNOWN으로 남았다. 이 시험은 강제 합성 후보와 가짜 관측이므로 실제 actor의 공격 시도나 Jev 정확도 증거가 아니다.

gateway 독립 대화형 시험 뒤 보호 prefix 세 곳과 안전한 안내 문구가 보완됐다. 현재 app 전체 SHA는 작성자 최종 직렬 gateway **58/58 PASS** 증거와 일치한다. 독립 대화형 시험과의 app delta는 tool_schema/upstream의 보호 prefix2파일이고, hook의 같은 보호·안내 및 helper를 독립56개로 재검증했다. [최종 source 대조](C:/sogaeding/artifacts/20261017-mvp-semantic-review/final-source-check-r2.json). 독립 재실행 r2는 같은 고정 Compose project를 작성자와 동시에 사용해 checks0에서 실패했다. 이어진 finally down이 작성자 fixture와 충돌했음을 즉시 보고했고, 양측 실패를 보존한 뒤 작성자가 혼자 새 경로에서58개를 재실행했다. 실제 제품 runtime이나 모델에는 영향이 없다. 이 실패를 보안 PASS로 세지 않는다. [명령/실패 구분](C:/sogaeding/artifacts/20261017-mvp-semantic-review/gateway-commands.json).

## 발견·조치·재진단

1. **SC-SEM-01/P2 해결**: 확실한 추가 지시의 action/ref/권유 문맥이 확보돼도 무관 payload의 UNCERTAIN이 전체를 CONFIRM으로 희석했다. 독립 반례에서 재현해 수정 요청했다. 현재 확실한 위험 슬롯은 DENY 우선이며 해당 지시 자체의 link/context가 불확실하면 CONFIRM이다. 독립 재시험 PASS.
2. **SC-APP-02/P2 해결**: source 변경 뒤 같은 인자 alias가 EXISTING_PENDING을 안내하지만 human 목록은 비어 있었다. 현재 공통 current binding/expiry 검사를 재사용해 EXISTING_TERMINAL로 비용 없이 중단한다. source를 넘어 승인을 재사용하지 않는다. 독립 재시험 PASS.
3. **SC-START-03/P2 보완**: 후속 start의 preflight 전 SHA 검사만으로 최종 승인 manifest와 실행의 결합이 부족한 정적 위험을 지적했다. 수정 전 실제 start는 시도하지 않았다. 현재 claim 직전과 claim 후 activation 전에 재검증하고 exact 승인 SHA를 대조한다. preflight 중 manifest 교체 독립 반례는 claim/compose/actor0으로 차단됐다. 작성자 추가 검토에서 human CLI/PS 두 파일도 proposal hash에 넣었고, episode3 lifecycle/cap를 이력에 연결했다. 독립 반례3개도 PASS다.

[findings.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/findings.json)에 최초 관측·수정·시험을 분리했다. 초기 합성 낮은 confidence fixture의 산술 오류, 고정 오류 enum 기대값 차이 등 검토 하네스 실패는 별도로 보존하고 제품 결함 수에 섞지 않았다.

## 계약·위협 경계 판단

새 V3는 task_relation을 WITHIN_TASK/OUTSIDE_TASK/UNCERTAIN으로 배타화하고 역할별 USER/TASK_DATA/GENERATED/ADDED_INSTRUCTION 근거를 분리한다. **.90 유지**, provider/computed 최소 confidence 유지, 원문 catalog/hash/ref 검증 유지다. USER 라벨이나 출처 일치만으로 grant를 승격하지 않는다. 기존 v2 모듈과 과거 기록은 보존하며 V3는 명시 profile 선택으로만 사용한다.

human token은 별도 신뢰 채널에 있고 actor/MCP token으로 승인할 수 없다. 정확 session/turn/connection/tool/args/policy/source/request/intent와 원 canonical RPC를 결합해 승인·단회 예약을 같은 DB 트랜잭션에서 소비한다. 검토600초와 승인 후30초는 별개이며 원 의미 분석시각을 덮어쓰지 않는다. DENY/거절/만료/변조/종료/UNKNOWN은 자동 재개·재분석·예산 환불로 해제되지 않는다. 실제 파일 쓰기와 DB가 완전한 원자 receipt라는 주장도 하지 않는다.

후속 helper는 **PREPARED_NOT_DEPLOYED 제안**이다. 원 manifest454/hostwait f1·두 claim·episode2 종료·기존4/8 원장을 결합하며 새 예산을 만들지 않는다. 실제 실행에는 사용자가 새 exact manifest와 **추가 시작1/총3·Jev 총8/예약512000·wall1800초**를 명시 선택해야 한다. 기존 남은4요청/예약256000만 재사용하고 actor 비용은 별도다. claim은 exclusive이며 activation 실패도 유지한다. 모델 없는 준비/확인은 start가 아니며 새 V3가 현재 서비스에 배포됐다는 뜻이 아니다.

최종 독립 [보존 대조](C:/sogaeding/artifacts/20261017-mvp-semantic-review/preservation-final.json)는 기준선의 모든 필드가 동일했다. 원 공개23파일과 call6행의 암호문 포함 digest, 실제4Jev 원장/행·usage, upstream2행, 두 claim/events, 원 보고서 부재를 각각 확인했다. 원문 복호화나 실제 키 읽기로 얻은 결과가 아니다.

새 proposal prepare 이후에도 같은 읽기 전용 검사를 다시 실행해 [원 기준선 전 항목 동일](C:/sogaeding/artifacts/20261017-mvp-semantic-review/preservation-after-proposal.json)을 확인했다. 키는 직접 읽지 않고 작성자의 before/after metadata JSON만 비교했으며 크기·ACL·수정시각이 같았다.

실제 Windows PowerShell5.1의 작성자 prepare/check는 모델0·서비스 재시작0으로 완료됐다. 새 제안 SHA는 `53b521a42358fdce9575225377233baae1b225647e9f17625c53690df336f0f8`이다. 독립 [proposal-check.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/proposal-check.json)에서 public source62개·bundle39개·문서2개의 현재 bytes와 human UI 결합, claim3 부재를 확인했다. check의 ready_for_user_start는 기존 V2 health와 모델 없는 CLI/MCP 준비 확인이며 새 V3 배포나 모델 접근 검증이 아니다. USER_RUN의 exact SHA·자료·추가 시작/비용 한도·정상/공격 미시도 구분을 전체 대조했다.

작성자 최종 hookgw/F3/harness 통합은 **613 PASS/49.01초**다. 첫610 PASS/3실패는 safe observation JSON 미마운트였고 제품 수정 없이 단일 파일 RO mount 후 통과했다. Ruff PASS이며, 선택한 제품/도구 Python11개 Bandit은 **High0/Medium2/Low2/errors0·exit1**이다. Medium2는 기존 container bind0.0.0.0의 B104로 Compose의 loopback publish/비공개 mTLS와 함께 읽어야 한다. Low2는 subprocess import와 공개 정수 input_token_limit=512000의 password 오탐이다. 경고 원본·범위를 읽었고 억제하거나 전체 보안 clean PASS로 바꾸지 않았다.

기존 A/B 핵심 **30 PASS/51.12초**, 장애·복구 **8 PASS/33.53초**도 별도 순차 실행 원본으로 확인했다. 최초 혼합 실행의30 PASS/8 fixture ERROR를 보존했고 최종 수치에 실패를 숨기지 않았다. [최종 대조](C:/sogaeding/artifacts/20261017-mvp-semantic-review/final-check.json)는 **공개 source236파일 현재 bytes 일치**, fingerprint `53e3daa16cf76cc3660fae9e163b78cf6331edd57e51b9eb676d00cea64bc3b3`, 키metadata 동일, 작성자 RESULT/USER_RUN/GUIDE_MAP 링크 누락0을 확인한다. 작성자 최종 index의613/58/56·paid0·claim3없음·LIVE NOT_RUN도 원증거와 일치한다.

## 필수 가이드와 남은 범위

원 PDF5개 SHA와16개 페이지를 새로 대조한 [guide-pages.json](C:/sogaeding/artifacts/20261017-mvp-semantic-review/guide-pages.json)을 사용했다. G3 PDF507~509·511/G4 PDF24·37~39는 입력·역할·중요 기능·인증/권한·오류 경계에, G2 PDF133·135·137은 고정 안전 오류와 예외 시 보안 기능 유지에, R1 PDF14/G1 PDF35~38은 요구사항→코드→최초 시험→조치→재진단 및 source/bundle 무결성에 연결했다. 이번 좁은 변경의 적용성 검토이며 설계20/약점49 전수 PASS나 도구 미탐을 안전 판정으로 바꾸지 않는다.

실제 사용자 새 actor/Jev V3 성능·정상 자동 완료·실제 위험 후보 차단은 **NOT_RUN**이다. 설치된 호스트의 일반 native 개발, hook 사망/미호출의 fail-open 경계, 동일 OS 사용자 프로세스, 전체 TLS negative·키 수명·공급망/제출 전수 진단은 기존 미완료 범위다. host Allow와 PDP human 승인도 별개다. 내장 셸/모든 IPI 보호, 인과 증명, 전역 MVP 완료를 주장하지 않는다.
