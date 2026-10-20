# core-auto-v5p1 최종 수용 준비 관리 수용

2026-10-17. 작성자 RESULT/USER_RUN과 별도 REVIEW, `jev_core_v5p1.py`·기존 evaluate 재사용 지점·`core_normal_gate/core_verify_block`의 실제 조건을 확인했다. **CORE_AUTO_PREPARED를 수용**한다. 새 사용자 실제 수용/MVP 완료는 아직 NOT_RUN이다.

현재 manifest SHA `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`, source66/변경후보17/bundle43 모두 현재 hash 일치다. bundle binding도 일치한다. `behavior_v5p1` 정책은 표준 JevClient/V5 질문을 재사용하며 완전한 응답 재검증 후에만 raw A를 쓴다. B LEGITIMATE와 검증된 raw A WITHIN_TASK를 양의 근거로 사용하고 A의 LOW_CONFIDENCE는 승격하지 않는다. 기존 V5 동작/원증거는 보존한다.

새 DB의 connection/turn/call/approval0, provider disabled(boolean false), 새 provider ledger/episode5 claim/verify-block claim 없음이다. 관리가 모델/CLI/서비스를 실행하지 않았다. 저장된 check READY는 모델 성공이 아니며 start가 image/profile/부모/소스·자료와 현재 상태를 다시 검사한다.

실응답 replay·통합366/최종관련84/실제gateway69·별도16 시험을 저장된 증거로 수용한다. 이 수치는 겹치므로 합산하지 않는다. gateway는 fixture 의미 응답을 실제 집행한 근거다. Bandit18건 원경고와 좁은 문맥 검토는 보존하고 전수 보안 PASS로 표현하지 않는다.

R-B-002는 기존 AuthAudit의 현재 control/public-authz/private-upstream 노출 실패 경로 연결, 세션 독립 영속 집계/제한, 감사 저장 실패시503/보호효과0을 관련 gateway·회귀/별도 검토 근거로 현재 등록 파일 MCP 범위에서 수용한다. 일반 TLS handshake 전체 감사/키수명 전수 보강까지 완료됐다고 하지 않는다. 다른 필수 보안 범위를 이번 좁은 수용으로 없애지 않는다.

`verify-block`은 다음 모두를 검사한 뒤에만 고정 위험 전송을 한다: 정확 정상 read/write2건 ALLOW/OBSERVED·제품 승인0, 실제 normal.md와 위험 파일 부재, upstream정상2, usage완전/소비2/잔여2, 정상CLI종료·연결닫기·자식정리, 같은 manifest/자료/한도 opt-in. exclusive claim 이후 고정 후보를 한 번 보내고 실패/UNKNOWN/소진시 재시도하지 않는다. 성공은 실제 Control DENY·분석 실패 제외·upstream위험쓰기0·위험파일0·총4요청 usage완전이다.

다음은 [고정 사용자 수용 절차](../../handoffs/WP-MVP-DEMO-01/USER_NEXT_RUN.md)다. 정상 요청은 동결된 문장을 그대로 쓰며 제품 CONFIRM을 사람 승인으로 통과시키지 않는다. 호스트 Codex Allow와 제품 PDP 승인을 구분한다. 원CLI에 위험 후보를 주입하지 않고 별도 엔진 시험으로 검증한다.

새4/예약256000·CLI1/총5/1800초, 역사29/1856000·demo24/1536000은 사용자가 선택할 새 상한이며 아직 소비되지 않았다. 기존25/1600000·CLI4/4는 유지된다. 실제 두 결과와 필수 통제가 확인된 뒤 등록 MCP 엔진 MVP 완료를 판정한다. B 고확신 오판 가능성·일반 native/hook fail-open·모델 전체 정확도·전체 제출보강은 남는다. [관리 현재 관측](../../../artifacts/management-core-auto-ready-20261017/observation.json).
