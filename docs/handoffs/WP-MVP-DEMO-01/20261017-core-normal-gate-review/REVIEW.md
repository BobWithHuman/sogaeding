# CORE_NORMAL_GATE_RESUME 별도 AI 검토

2026-10-17. 구현 담당과 다른 AI 검토자가 최종 후보를 검토했다. 차단할 발견 사항 없음. 이는 배정된 gate/후속 실행 준비의 검토이며 실제 위험 호출의 수용이나 공식 독립 보안 진단을 뜻하지 않는다.

## 검토 후보와 범위

`CORE_NORMAL_GATE_RESUME_PROMPT.md`, 원 변경 전 파일과 `change.diff`, 최종 source-manifest 5파일, 실제 관리 관측, 실제 RO gate 재현, 준비/READY/보존 결과와 USER_RUN/RESULT를 확인했다. 검토 종료 시 5파일 SHA256을 독립 계산해 동결 후보와 모두 일치함을 기록했다(`artifacts/20261017-core-normal-gate-review/source-check.json`). 제품 코드는 수정하지 않았다.

원 manifest `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`, 후속 manifest `47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`를 확인했다. 후속 binding은 원 source66 중 기존 runner 3파일의 이전/이후만 허용하며 나머지 source, 제품 bundle/image, 정책, 원 고정 후보/목적지, 부모 원장과 원 한도를 계속 검증한다. 원 manifest를 고치거나 current 검증을 단순히 해제하지 않는다.

## 확인한 동작

- 원2호출 및 실제4호출을 수용한다. 실제4호출은 source 읽기→보고서 읽기 FILE_NOT_FOUND/NO_WRITE→보고서 쓰기→보고서 읽기이며, 오류 상태를 성공으로 바꾸지 않는다. 쓰기는 정확1회, 같은 session/turn·정확 사용자/후보 hash·ALLOW/OBSERVED·승인0을 요구한다. 선택적 읽기 외 다른 대상/도구/오류/UNKNOWN/CONFIRM은 거절한다.
- bounded UI 대신 전체 RO 서버 metadata를 확인한다. native hook의 확정 DENY를 별도로 보존하고, 모든 MCP와 upstream의 ID/순서/결과·전체 개수 및 RPC binding 집합을 대조한다. canonical RPC와 raw HTTP의 서로 다른 hash를 잘못 동일시하지 않으며 양쪽 원값을 후속 transcript에 결합한다. body/snapshot 복호화는 없다.
- 정상 보고서334bytes/원 SHA, episode5 정상종료·연결닫힘/정리 VERIFIED, 원장2 COMPLETED·예약128000·잔여2/128000과 위험 claim/result 부재를 결합한다. usage/종료/자료/source/bundle/image/원장/부모/후속 hash가 stale이면 claim 전에 거절한다.
- 원 batch의 명시 opt-in·원/후속 두 SHA·기존 한도를 요구한다. exclusive claim이 경쟁 실행을 한 번으로 제한하며 예외/UNKNOWN에서도 claim을 남겨 재시도하지 않는다. claim 이후 기존 probe/helper도 원+후속 source binding을 유지한다. 새로운 CLI·정상 시험·예산은 발급하지 않는다.
- 기존 PS5.1 진입점의 위험 단계 전용 인자 전달을 확인했다. USER_RUN 명령의 실제 두 SHA와 원 batch 값이 fake helper까지 전달되는 증거가 있으며 start/history/inspect에 resume 인자를 사용하면 거절한다. 실패 출력은 allowlist stage/code로 제한된다.

## 검증 근거

구현 담당의 최종 필요한 통합은 **161 PASS/54.88초**, Ruff PASS이다. PS5.1 fake 검증은 기존14개와 정확 후속 명령/부적절 모드5개가 각각 PASS(합계19)이다. 실제 준비/재검증은 기존 컨테이너의 read-only bundle/image/health 점검이며 모델 호출이 아니다. `actual-gate-replay.json`의 old gate 실패→수리 gate 통과와 `preservation-summary.json`의 원 기록 보존을 확인했다.

별도 검토자는 기존 fixture를 사용하되 구현 시험과 다른 반례 **12개를 직접 실행해 모두 PASS/5.18초**를 확인했다. 확정 native 거절의 보존, 가짜 native upstream, upstream 누락/시각·hash 이상, RPC hash 이상, 성공 호출의 오류 문맥, 원 manifest 승인hash·episode claim·ledger view/예약 변조를 확인했다. 모두 실제 runtime·키·원장을 마운트하지 않은 기존 이미지의 network-none/read-only 컨테이너에서 실행했다. 최초 검토용 파일 mount 위치 오류는 시험 시작 전에 발생했고, 독립 `/review` mount로 고쳐 실행했다. 제품 경로 변경은 없었다. 명령과 결과는 `artifacts/20261017-core-normal-gate-review/{run-review.ps1,review_cases.py,independent-command.json,independent.txt}`에 보존했다.

## 남은 범위

실제 정상 자동 성공은 기존 실증거로 보존했다. 위험 단계는 여전히 **NOT_RUN**이며 사용자 명령 실행 후 실제 gateway/실제 Jev DENY·위험 upstream쓰기0·reports/review.md부재·총4요청 사용량완전을 확인해야 한다. 현재 위험 차단 성공 또는 전체 MVP 완료로 판정하지 않는다. 기존 B 오판 가능성, native/hook 장애·전체 IPI·인과/제출 전수 진단의 한계와 적용 가이드/보안 근거는 유지한다.

검토 중 제품 모델 호출0·actor/CLI 시작0·서비스 교체0·원장/claim 변경0이다. 개발 AI의 구현/검토 토큰은 이 제품 호출0과 별개다.
