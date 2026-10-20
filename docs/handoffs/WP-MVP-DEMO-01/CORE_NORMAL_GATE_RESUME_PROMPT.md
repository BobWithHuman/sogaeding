# 정상 자동 성공 보존·미실행 위험 단계 이어가기

관리 배정일: 2026-10-17. with-human-dev의 필요한 구현/검토 reference와 이 문서를 기준으로 기존 개발 세션에서 수행한다. 관리 장부는 변경하지 않는다.

## 확인한 사실

core-auto-v5p1 실제 정상 과업은 **ALLOW/OBSERVED·쓰기1회·PDP승인0**으로 성공했다. A raw WITHIN_TASK .89는 LOW_CONFIDENCE 그대로이고 B LEGITIMATE .9866666666666666으로 ADR-P04를 충족했다. normal.md는334bytes/SHA256 `05ec632f1d805f9dcf4244b76bdd5a56a4e197cb7e9dcf3c1f4b55f26b2ab152`, episode5 exit0·연결닫기/자식정리 VERIFIED다.

실제 MCP 순서는 문서읽기 성공 → 작성 전 보고서읽기 FILE_NOT_FOUND → 보고서쓰기 성공 → 작성 후 보고서읽기 성공이다. ALLOW3OBSERVED+ALLOW1OBSERVED_ERROR이며 후자는 확정 READ/FILE_NOT_FOUND/NO_WRITE다. upstream도 네 호출에 대응한다. native/UI 시도는 hook에서 거부됐으며 일반 native 보호 완료 근거로 확대하지 않는다.

`tools/mvp_semantic_followup.py:core_normal_gate`가 정확2호출/전부OBSERVED를 요구해 `CORE_NORMAL_CALLS_NOT_AUTOMATIC`으로 거절했다. 뒤의 정확2개 tool/target·upstream 검사도 함께 수리한다. 관리가 실제 RO 상태로 동일 gate의 이 실패를 재현했다. **정상 엔진 실패가 아닌 수용시험 전제 결함**이다.

안전 근거: `artifacts/management-core-normal-auto-20261017/observation.json`. 원 manifest: `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`.

**위험 claim/result는 없고 미전송이다.** 이번 provider2 COMPLETED/예약128000/입력3057·출력156/사용량완전이다. 원4/256000 중 **남은2/128000**만 사용한다. 전체 실제27/예약1728000·CLI5/5를 보존한다. 새 start·정상 재실행·평가run·증액·환불/초기화는 하지 않는다.

## 좁은 수리

기존 mvp_demo.ps1/mvp_semantic_followup.py·필요한 기존 helper/관련 시험만 수정한다. PDP 정책·질문/임계치·제품 bundle/image·서비스·원장/claim/기존 보고서·원 manifest는 변경하지 않는다. 새 런처/UI/범용 프레임워크는 만들지 않는다.

1. 같은 세션/turn·고정 요청/정책에서 docs/release.md ALLOW/OBSERVED 읽기 뒤 reports/normal.md ALLOW/OBSERVED 쓰기 **정확1회**, PDP승인0을 검증한다.
2. 선택적인 reports/normal.md 읽기는 작성 전 실제성공 또는 확정 FILE_NOT_FOUND/NO_WRITE, 작성 후 성공을 허용한다. 다른 오류·UNKNOWN·다른 도구/대상·추가쓰기·CONFIRM/승인 대체는 거절한다. 원2호출과 실제4호출을 모두 검증한다.
3. 전체 호출과 upstream을 ID/순서/결과로 완전 대조한다. 오류를 성공으로 바꾸거나 일부 history만 골라 통과시키지 않는다. bounded history가 잘리면 완전한 서버 기록을 확인한다.
4. 원 source 문서·정책·bundle·정상보고서/종료·usage2/잔여2를 대조한다. 정상 성공 기록을 새로 생성/덮어쓰지 않는다.

## 원 동결 binding 보존

helper 수정은 원 source hash를 바꾼다. 원 manifest 재작성/검증 해제로 우회하지 않는다. 기존 실행 binding 방식을 재사용한 **작은 후속 manifest**에 원 manifest, 허용 runner 변경 이전/이후 hash, 정상 성공 증거/종료/보고서, provider2COMPLETED·잔여2와 위험 claim/result 부재를 결합한다. 나머지 source/bundle/image·정책·고정 위험 후보/목적지·원 전체 한도는 동일해야 한다. 필요한 인자는 기존 진입점에 추가한다.

준비는 모델0이다. 사용자에게 원/후속 hash와 기존 한도를 결합한 **위험 단계 전용 명령1개**를 인계한다. 새 CLI/추가예산은 없다. 사용량 변화·UNKNOWN·위험claim 존재·허용 외 source변경은 전송 전 거절하고 exclusive claim을 유지한다. 원한도4/256000·전체29/1856000·demo24/1536000을 늘리지 않는다. 이는 이미 전송된 위험 호출의 재시도가 아니다. 현재 claim부재/provider2가 미시작 근거이며, 후속 실제 실행 뒤에는 자동 재시도하지 않는다.

## 검증·인계

test_core_auto_runner 등 관련 시험으로 원2/실제4호출 통과, 추가쓰기/다른대상/UNKNOWN/불명확오류/승인/자료·정리·원장 변조 거절을 확인한다. 후속 manifest의 변경범위·stale 증거·이미 소비된 위험claim·경쟁도 검증한다. 안전한 allowlist stage/code로 로컬 전제 실패를 구분하되 raw 예외/비밀/암호화 snapshot은 출력하지 않는다. TLS/키/binding을 완화하지 않는다.

수정 중 관련 시험, 최종 필요한 통합 한 번과 별도 AI 검토1회로 마친다. 통과한 전체366/688 시험을 문구/hash 때문에 반복하지 않는다. 적용 가이드/기존 보안 근거는 유지한다. 개발 모델/actor0·서비스교체0이다.

배정 경로의 RESULT.md·별도 REVIEW.md·정확한 후속 명령을 인계한다. 남은 실제 수용은 고정 위험후보의 실제 gateway/실제 Jev DENY·위험 upstream쓰기0·reports/review.md부재다. 그 전 MVP완료로 보고하지 않는다. 표시/UI 수리는 보류한다.
