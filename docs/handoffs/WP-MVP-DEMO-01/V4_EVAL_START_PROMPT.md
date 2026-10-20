# V4의 고정 4요청 평가를 기존 도구에 연결

with-human-dev로 다음 근거를 읽고 **실행 가능한 평가 준비만** 완성한다. 이번에는 정상/공격 모델 결과를 얻기 위한 연결이 목적이며, 제품/서비스 배포나 새 의미 정책 설계 작업이 아니다.

- `docs/plans/reviews/WP-MVP-DEMO-01_20261017_v4_candidate_management.md`
- `docs/handoffs/WP-MVP-DEMO-01/20261017-auto-decision/FUTURE_EVAL_PROPOSAL.md`
- `artifacts/20261017-auto-decision/future-eval-proposal.json`과 `proposal-{normal,attack}-{A,B}.json`
- 기존 tools/jev_eval.py, scripts/jev_eval.ps1의 관련 분기와 src/app/transparent/jev.py·jev_semantic_v4.py

## 고정 범위

1. V4를 **평가용으로 채택**한다. 현재 server/runtime/V3/승인/원자예약/UNKNOWN/TLS를 교체하지 않는다. 기존 endpoint/model `https://api.typesafe.ai/v1/systemone`, `jev-1.13.0`, 임계치 .90/응답계약/usage 검증을 재사용한다. V4 후보7개와 원 실제 응답/기록을 보존한다. 구현/검토 실제 actor/Jev 호출0이다.
2. 기존 `JevClient.observe`와 `tools/jev_eval.py`/`scripts/jev_eval.ps1`를 재사용해 정확 run ID **followup-auto-v4**를 지원한다. 별도 live 스크립트 묶음/새 키 준비/브라우저/CLI actor를 만들지 않는다. 알려진 구형 run은 불변 유지하며 closed 원장/manifest 우회·초기화·환불·재활성화를 하지 않는다.
3. 준비 시 고정 자료/wire SHA·실제 V4 build 질문/criteria의 일치와 현재 의존 source/image/bundle을 결합한다. 기존 TypeSafe 키는 보호된 원 파일을 RO 참조하고 내용/키hash를 출력하지 않는다. 준비는 disabled이며 실제 evaluate 전 새 유료 원장/예약을 생성하지 않는다. 별도 명시 새 평가 allowance가 필요하면 기존8/8 원장을 parent로 묶어 보존한다.
4. 전송 순서는 **정상A→정상B→공격A→공격B**, 최대4요청·추가 입력예약256000·actor/CLI0회다. 각 실제 응답은 기존 shape/usage/ref/cap 검증을 통과한 뒤 해당 V4 후보의 서버 판정으로 조합한다. A/B 응답을 서버 조합에 재사용해도 provider 재요청하지 않는다. 구형 parallel analyze가 순서를 무시하지 않게 한다. 최초 transport/응답/usage/ref/분석 오류에서 남은 요청을 중단하며 retry/fallback/reset0이다. 유효한 낮은 confidence/CONFIRM은 결과로 기록하고 추가 요청으로 교정하지 않는다.
5. 정답 expected_local_only는 로컬에만 둔다. 모델 state/questions에 기대 ALLOW/DENY·평가 답안·attack label을 주입하지 않는다. 실제 typed choice/probability/provider·computed/effective confidence·사용량·고정 source/ref 검증 결과를 비민감 필드로 보존한다. 미시도/미채점/분석 실패/CONFIRM/실제 ALLOW-DENY 일치를 구분하고 프로그램 exit0를 의미 성공으로 표시하지 않는다. 파일 효과/actor 보호/전체 정확도는 이 평가에서 NOT_RUN이다.
6. 누적 한도는 새4/256000, demo관련12/768000, 전체과거 포함17/1088000, 추가CLI0이다. 확정된 구체적 manifest에 대해 사용자가 직접 `-ConfirmSend`와 정확 한도를 고른 evaluate **한 번**만 실행하도록 준비한다. 기존 동결 계획/누적 이력을 덮거나 이미 승인된 것처럼 실행하지 않는다. 자료/목적지/한도 변경은 최종 USER_RUN에서 표시한다.

## 검증·인계

관련 runner/transport/원장 결합 분기만 가짜 provider로 검증한다. 모델0 preflight, exact wire/순서4, 정상ALLOW·공격DENY·유효CONFIRM, 첫 실패 후 중단, 미사용/부분usage, 두 번 evaluate·manifest/source/parent 변경 거절, collect 읽기 전용과 기존 이력 보존을 확인한다. 정책 코드가 그대로면 브라우저/gateway/688개 전체 시험을 다시 시작하지 않는다. 새 변경의 직접 영향 범위는 빠뜨리지 않는다. 구현1+최종 별도 AI검토1, 필요한 가이드 원문/기존 연결만 읽는다.

개발 세션에서 새 run의 **모델0 준비와 preflight를 완료한 상태**로 RESULT/REVIEW/USER_RUN을 준다. 사용자에게 다시 prepare/plan/key 단계를 시키는 인계로 끝내지 않는다. exact hash 포함 한 줄 evaluate와 collect를 함께 제공한다. 관리 정본(plans/harness/AGENTS)은 수정하지 않는다. 다음 단계는 준비된 고정4요청의 사용자 직접 평가이며, 실제 실행·배포·전체MVP 완료는 아직 아니다.
