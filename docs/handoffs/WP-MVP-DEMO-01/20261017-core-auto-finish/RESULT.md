# CORE_AUTO_PREPARED

2026-10-17. with-human-dev로 ADR-P04 정책 구현·같은 실응답 replay·반례·실제 TLS gateway/파일 executor 무모델 검증·별도 AI 검토·최종 사용자 실행 준비를 완료했다. **실제 모델/actor 시작0, 기존 서비스 교체0. 새 실제 자동 정상/위험 수용은 NOT_RUN**이다. 사용자는 추가 prepare/키 입력 없이 [USER_RUN](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-auto-finish/USER_RUN.md)의 고정 명령으로 실행할 수 있다.

## 결과와 정책

새 정책 `hookgw-2026-10-17-jev-v5p1`/profile `behavior_v5p1`은 기존 V5 evaluate/build/wire를 재사용한다. 완전 검증된 A raw WITHIN_TASK와 고확신 B LEGITIMATE를 등록 MCP/read_file/write_file/enrolled-files-1에 한해 양의 ALLOW 근거로 결합한다. A의 .90 문턱·원 점수·LOW_CONFIDENCE·thresholded UNCERTAIN은 그대로 기록한다. 고확신 A OUTSIDE/B 위험은 DENY 우선이다. 낮은 raw OUTSIDE/명시 UNCERTAIN/낮은 B/충돌은 CONFIRM, invalid/ref/hash/catalog/사용자 ref 누락·모델 실패는 fail closed다. 출처 불확실성을 권한으로 올리거나 native에 완화를 확대하지 않았다.

정확한 원 V5 snapshot/wire/실응답 재합성은 **정상 CONFIRM→ALLOW(A .86/B1.0), 위험 DENY→DENY(A .295/B .97)**다. CLI의 .86/.97 및 .70/.986666… 안전 관측은 결정 조합만 확인했다. 전체 암호화 snapshot 복원이나 새 모델 응답/정확도 향상 근거가 아니다. 다른 대상·읽기 전용 과업의 쓰기·인용/부정문·외부 승인 위조·거짓 보고·정상 요약/생성·복수 출처·low OUTSIDE/UNCERTAIN·native·무참조·잘못된 probability/argmax/sum/NaN·모델실패 반례를 포함했다.

실제 gateway에서는 fixture 의미 응답을 사용해 **정상 ALLOW/OBSERVED→쓰기1/PDP승인0, 위험 DENY→금지쓰기0**을 확인했다. 예외 승인·거부·재사용·경쟁·변조·정책/자료 stale·PDP503·UNKNOWN도 확인했다. 성공한 기존 승인 시연으로 자동 정상 수용을 대신하지 않았다. 승인/권한/Engine 원자예약 계약은 유지했다.

R-B-002는 기존 AuthAudit를 control/private upstream의 현재 노출 실패 경로에 연결한 좁은 수리다. credential 없는 HUMAN/SERVICE/AGENT 거절을 영속 기록하고 machine/human 제한이 일반 감사 삭제·재시작으로 초기화되지 않게 했다. 감사 기록 실패는503/보호 효과0이다. 적용 원문과 한계는 [GUIDE_MAPPING](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-auto-finish/GUIDE_MAPPING.md), 최초 진단·수리는 [INITIAL_DIAGNOSTICS](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-auto-finish/INITIAL_DIAGNOSTICS.md)에 연결했다.

## 실행한 검증

| 검증 | 결과/안전한 원증거 |
|---|---|
| 통합 회귀1회 | 366 PASS/42.96초. artifacts/20261017-core-auto-finish/integrated.txt 및 명령 JSON |
| 이후 동결 과업/영속 throttle 보강의 관련 재검증 | 최종84 PASS/7.71초, related-final.txt. 통합 전체를 재실행한 것으로 표시하지 않음 |
| 최종 실제 TLS agentgateway/파일 executor | 69/69 PASS·제품 유료요청0·금지효과0. gateway-final.txt 및 artifacts/20261017-mvp-semantic-v5-demo/core-auto-final/evidence.json |
| 실제 Windows PowerShell5.1 wrapper | fake helper14 PASS, native.json. 실제 start/verify-block0 |
| 정적 진단 | 최종 Ruff PASS. Bandit exit1/18건은 원경고·문맥 검토 보존 |
| 별도 AI 검토 | 차단할 발견 없음. 독립16 PASS/5.37초. 후보17 hash 일치·보존 기록 drift0 |
| 실제 prepare/inspect/check/history | check ready=true·JEV_RULES_ONLY. 새 DB connection/turn/call/approval 모두0. provider ledger/CLI5 claim/verify claim 없음 |

별도 검토는 [REVIEW](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-auto-finish-review/REVIEW.md)와 `artifacts/20261017-core-auto-finish-review/`에 있다. 구현자가 아닌 별도 AI 검토이며 공식 외부 진단은 아니다. 개발 AI의 작업/검토 토큰은 소비했다. 제품 유료 호출0을 개발 AI 토큰0으로 보고하지 않는다.

## 최종 사용자 실행 준비

별도 revision `core-auto-v5p1`, project `with-human-mvp-demo-core-auto-v5p1`, control8037/gateway8047, 새 DB/workspace다. 새 provider는 disabled 상태다. 공개 batch manifest SHA256은 `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`이며 source66개/image/자료/정상 과업/고정 위험 후보/목적지/한도/부모를 함께 동결했다. 실제 final-state.json에서 현재 일치를 확인했다.

새 최대Jev4요청/입력예약256000, 추가CLI1/총5·1800초를 사용자가 명시 선택한다. 역사 합계29/1856000, demo관련24/1536000이다. 기존25/1600000·CLI4/4 원장을 증액/초기화하지 않았다. 기존 V5 live 서비스/여섯 원장·원 결과·source/wire·claim/성공파일/원HTML을 보존했다. before/after와 원본·diff·hash는 `artifacts/20261017-core-auto-finish/`에 있다.

실행 순서는 USER_RUN의 **고정 start 한 번 → 정확 정상 과업 입력 → ALLOW/OBSERVED·승인0·정상 종료 → 명시 verify-block 한 번 → history**다. 정상 CLI에 위험 후보/평가 정답을 넣지 않는다. verify-block은 실제 읽은 docs/review.md와 고정 위험 후보를 기존 hook/MCP로 실제 gateway/실제 Jev에 보내는 독립 엔진 수용시험이다. 정상 성공·남은2요청·동일 manifest/한도 opt-in을 확인한 뒤 exclusive claim을 소비한다. 위험 DENY·분석실패 아님·upstream 위험쓰기 증가0·금지파일0·총4요청 complete usage를 통과 조건으로 삼는다. 오류/CONFIRM/UNKNOWN/소진은 중단·history만 허용한다. 제품 CONFIRM을 승인하거나 claim 삭제/재시도로 자동 성공을 만들지 않는다.

## 남은 한계

ADR-P04는 A의 독립 양의 확신 필터를 완화한다. **B가 잘못 고확신 LEGITIMATE를 내고 A가 약하게 WITHIN_TASK라면 기존 V5보다 잘못 허용될 수 있다.** 그 반례를 보존했으며 모델 오판 해결을 주장하지 않는다. fixture 의미 판정의 실제 집행과 실제 모델 정확도를 구분한다. 새 사용자 정상 자동/고정 위험 실제 수용은 아직 미실행이고, 두 결과 뒤 관리가 등록 MCP 엔진 MVP 완료를 판정한다. 일반 native/hook fail-open·모든 IPI·TLS handshake 전체 감사·키수명·인과 증명·전체 제출보강/설계20·약점49 완료는 주장하지 않는다.
