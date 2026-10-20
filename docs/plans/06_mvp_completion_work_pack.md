# WP-HARDEN-01: 첫 구현 이후 MVP 보완 작업

> **A 인계 검토 후 현재 상태:** 단계 A의 유한 범위를 수용했다. 아래 A 배정은 당시 기록이며 재개는 [단계 B](07_browser_acceptance_work_pack.md)와 [A 관리 판정](reviews/WP-HARDEN-01_A_20261013_management.md)을 따른다.

> **MVP 범위 정정:** [ADR-M01](decisions/ADR-M01_mvp_completion_scope.md)에 따라 B와 현재 적용 필수 통제·재현/연결 근거로 MVP 동작 완료를 판정한다. 아래 C/D 전체를 MVP의 선행조건으로 묶는 표현은 이전 계획이다. C/D 전수 보강은 대회 제출 전 수행한다.

PLAN-2 후속 배정 / 2026-10-13 KST. 사람 개발자는 사용자 1명이다. **기존 개발 세션에서 이어서 작업**한다. 전체 범위는 아래 A~D이며, 이번 인계의 실행 범위는 **A: 보존·폐기와 장애 복구**다. A가 검증되면 RESULT/별도 AI REVIEW를 관리 세션에 전달하고 B~D를 이어서 배정한다. 제품 기능을 새로 확장하는 작업이 아니다.

## 1. 시작 기준

- [관리 판정](reviews/WP-MVP-01_20261013_management.md), [이전 RESULT](../handoffs/WP-MVP-01/20261013T073853Z-dev-3980e4/RESULT.md), [별도 REVIEW](../handoffs/WP-MVP-01/20261013T084627Z-review-ai-7421/REVIEW.md)를 먼저 읽는다.
- 현재 전송/wire 명세는 **MVP-SPEC-3**, 권한 정책은 `mvp-2026-10-13-v1`이다. T-S01을 처음부터 다시 구현하지 않는다.
- 관리 검토 시 최종 source manifest의 50개 파일이 실제 파일과 일치했다. 기준 fingerprint는 `8e48b00ceac5803b034d85da55c383980f0e31ce230c9dab21deb1aa0cb6fa27`이다. 착수 시 다시 대조하고 이후 변경은 새 manifest로 기록한다.
- 제품 pytest 24개, 독립 장애 보완 3개, 마지막 변경 TLS 2개는 서로 다른 범위/실행이다. 합쳐서 새 제품 수용시험 29개로 세지 않는다. 기존 NT/AT 18개 및 AC/PL 게이트와 실제 시험 함수를 연결한다.
- F-008 출처 저장 장애 후 후속 쓰기 결함은 수정·독립 재현으로 제거가 확인됐다. 회귀시험을 유지한다. core/MVP는 미완료다.
- 기존 LIVE 정상·공격 각 1회는 **수정 전 빌드**의 정상 요약·MCP 연결 증거다. 공격 호출은 `NO_ATTACK_ATTEMPT`. R1/후속 빌드의 LIVE 통과나 엔진 공격 차단으로 이전하지 않는다.

## 2. 순서와 종료 조건

| 단계 | 해야 할 일 | 해당 단계의 종료 증거 |
|---|---|---|
| **A — 이번 배정** | 기본 24시간 보존/폐기, PDP timeout/malformed·필수 저장 장애, stale reservation/재시작·명시 복구 보완 | 아래 A1/A2의 실제 통합 결과, 기존 정상·DENY·승인·경쟁 회귀, 별도 AI 재현. 남은 B~D는 미완료로 유지 |
| B — A 검토 뒤 | 실제 브라우저 요청→타임라인→정확한 승인·거절·재개, XSS/비밀/토큰 저장·중복 클릭, 인증 요청 제한 | UI/서버/실제 effects가 같은 run에서 일치. 단순 JS 문자열 검사를 브라우저 실행 증거로 세지 않음 |
| C — B 검토 뒤 | 실제 제품의 세 인증 경로에서 잘못된/만료 인증서·client 인증·재발급·회전·복구, 새 임시 환경 재현 | TLS 준비 fixture와 제품 시험 분리, HTTP fallback/검증 해제 없이 실패 거부·정상 회복. 전역 CA 저장소 변경 없이 신뢰 구성 |
| D — 기능 게이트 이후 | 설계20/약점49 항목별 본문·source→sink·도구 rule coverage·수동/동적 보완, OS SCA·라이선스/NOTICE·SBOM 검토 | 현재 후보의 진단·수정·재진단과 구성요소/버전/한계 연결. 공급자 미확인을 허위 확정하지 않음. 전체 core/LIVE 완료 판정은 관리 검토 후 |

각 단계의 시간은 최초 실측 후 갱신한다. 날짜를 맞추기 위해 적용 P0를 빼지 않는다. UI 미관·judge·새 도구·새 모델·큰 공격 평가셋은 기존 PLAN-2대로 보류한다.

### A1. 보존·폐기 — T-05/T-10, F-004

기존 요구서의 로컬 데이터 기본 24시간 보존을 구현한다. 다음은 그 요구를 실행하기 위한 관리 결정이다.

1. 서버가 기록한 생성 시각 기준의 보존 기한을 명시한다. 사용자 입력 시간이나 마지막 조회로 기한을 연장하지 않는다. session 원문·sources/events/calls/approvals 및 gateway comments/receipts를 포함해 두 DB의 데이터 목록과 삭제 순서를 기록한다. 기존 세션 유효기간·단회 승인·예산 정책은 유지한다.
2. 기한 이후 새 실행/조회·승인 접근을 먼저 막고, startup 및 주기적 정리로 만료 자료를 제거한다. 정리 주기와 최대 지연을 문서화하고 가짜 시계 또는 독립 fixture로 검증한다. 실제 PC 시계를 바꾸거나 24시간을 기다리는 시험을 만들지 않는다.
3. `UNKNOWN`/`RESERVED`의 삭제가 성공확정·예산 환불·동일 call 재실행을 허용해서는 안 된다. 폐기할 때 미해결 상태의 의미를 보존하고 본문 없는 최소 정리 기록의 필드·보존기간도 정한다. 무기한 예외 보관을 기본값으로 두지 않는다.
4. 두 DB 간 정리의 중간 실패/재시작을 고려하고 반복 실행해도 안전하게 만든다. 실제 기존 개발 DB나 이전 원증거를 지우는 시험을 하지 않는다. 생성한 전용 테스트 저장소만 사용한다.
5. 본문·토큰·가짜 비밀의 DB/저널·출력 잔존 확인, 기한 전 데이터 보존, 기한 후 조회 거부, 반복 정리, 재시작, 기존 call/approval/token 재사용 거부와 추가 effects0을 검증한다. 앱에서 접근 불가와 디스크 물리적 완전 삭제를 같은 주장으로 쓰지 않는다. 개발용 안전 증거의 별도 보관은 제품 데이터 무기한 보존의 우회가 아니다.

공개 API·권한·상태 enum 변경 없이 내부 DB 생성시각·정리 함수·기동 스케줄과 시험을 추가하는 것은 이번 배정 범위다. 기존 데이터 migration은 비파괴·재실행 가능한 방식으로 작성한다. 새 외부 endpoint나 정책 의미 변경이 필요하면 관련 부분만 결정 요청하고 독립 가능한 구현은 계속한다.

### A2. 장애·재시작 — T-04/T-06/T-08, AT-09/AT-12

아래는 유한한 최소 장애 표다. 모든 가능한 장애 조합을 요구하는 문구로 확장하지 않는다. 기존 재현이 같은 조건을 충족하면 재사용하고 새 실패/변경 경로만 보완한다.

| 위치/상황 | 검증할 결과 |
|---|---|
| 실행 전 PDP timeout·잘못된 JSON/스키마·오류 응답 | 제한 시간 안의 안전한 실패, executor/effects0, 원문 오류·자격증명 비노출 |
| check/reserve/필수 감사 저장 실패 | 실행0, 승인·예산·상태 부분 commit/무단 환불 없음 |
| 읽기 후 source 저장 실패 | 기존 F-008의 새 check와 미리 발급한 reserve 모두 후속 실행0, source 없는 receipt-only 성공 위장 거부 |
| 쓰기 효과 후 report/응답 손실·요청 취소 | 첫 효과 최대1, UNKNOWN 유지, 동일 call 및 다른 call의 위험 재시도0, 명시적 실제 receipt 대조만 상태 복구 |
| RESERVED 상태의 30초 경과·Control 주기 sweep·프로세스 재시작 | 실제 daemon/startup 경로에서 UNKNOWN 전환, 예산 유지·추가효과0. Repository 함수만 직접 부른 결과와 구분 |
| 정상 회복·승인 만료/거절·경쟁 회귀 | 유효한 정상 과업은 여전히 완료, CONFIRM 승인 전0/승인 후1, replay·동시 쓰기 총1, 만료 승인 거부 |

관측은 실제 MCP→PDP→reserve→private executor 경로와 독립 effects 저장소를 사용한다. 정책·예약 자체를 mock한 결과로 통합 통과를 대체하지 않는다. 제어된 시험 상대/DB trigger 등 fault 주입 위치를 밝히고 제품에 공개 우회·fault API를 넣지 않는다.

## 3. 증거·의존성·보호 범위 판단

- **F-007 과거 증거 공백:** 최초 SAST 직전 전체 소스/시각을 복원했다고 주장하지 않는다. 과거 공백은 영구 한계로 남기고 이번 변경 전 source/image/lock manifest·정확한 command UTC·exit code·안전한 raw output을 고정해 이후 증거 사슬을 만든다. 새 baseline부터 진단·조치·재진단이 연결되면 앞으로의 절차 보완으로 판정한다. 복구 불가능한 옛 기록을 만드는 작업 때문에 기능 보완을 멈추지 않는다.
- `FINDINGS.jsonl`에는 기존 ID/원문 링크를 유지하며 새 이벤트를 추가한다. F-008 해결 이력은 지우지 않는다. F-003의 B104 3건은 현재 loopback publish/TLS/mTLS 조건부 검토이며 경고 숨김이나 무약점0 판정이 아니다.
- `local-ingress` bridge는 현재 Docker Desktop의 localhost 접속을 위한 구성으로 수용한다. 내부8443이 모든 container NIC에서 listen하고 OS outbound가 전면 차단되지 않는 한계를 유지한다. 공개 포트는 localhost, 내부 호출은 mTLS+service bearer를 유지한다.
- A는 기존 lock과 도구로 진행한다. B의 브라우저 또는 D의 OS 진단에 추가 도구가 필요하면 실제 후보·공식 출처·고정 버전/digest·라이선스·실행 권한·수집/외부 전송 범위를 제시한다. 도구 부재를 제품 실패나 진단PASS로 표시하지 않는다. 새로운 유료 모델 반복은 이번 A 배정에 포함하지 않는다.
- 가이드/대회 기준은 [03](03_guide_compliance.md), [05](05_contest_security_criteria.md)를 따르고 관련 PDF 본문을 직접 대조한다. 현재의 20/49 초안 행 존재만으로 전수 검토 완료를 선언하지 않는다.

## 4. 파일 소유권과 인계

작성자 한 명이 공통 DB 전이·모델·시험 fixture를 통합한다. 허용 쓰기는 `src/app/`, 관련 `tests/`, 필요한 로컬 `scripts/`·`tools/`, 실행에 필요한 Compose 설정, 자기 `docs/handoffs/WP-HARDEN-01/<run_id>/` 및 ignored `artifacts/<run_id>/`다. 사용자 로컬키/기존 runtime·DB·원증거를 덮어쓰지 않는다. 공개 계약 변경 없이 가능한 내부 구현 선택은 자율 진행한다.

`docs/plans/`, `harness/build_tasks.json`, `AGENTS.md`, 원본 PDF·기존 handoff·설치 skill은 읽기 전용이다. 내부 보존/복구 세부사항은 자기 SECURITY_DESIGN에 기록하고 공통 명세 동기화가 필요하면 정확한 diff 제안으로 인계한다. 변경해야 하는 공유 파일은 실제 필요와 소유권을 먼저 확인한다.

실제 제품 변화에 해당하는 정상·보안 회귀를 실행하고, 작성자와 별도 AI가 새 기준 파일·효과·원증거를 검토한다. 기존 검토자는 이어서 쓸 수 있지만 이전 PASS를 새 버전에 그대로 복사하지 않는다. 검토 증거는 별도 run에 보관한다. 이 문서는 다른 사용자 채팅 자동 생성/메시지 전송 요청이 아니다.

최종 인계는 `RESULT.md`, `SECURITY_DESIGN.md`, `GUIDE_APPLICABILITY.md`, `FINDINGS.jsonl`과 별도 `REVIEW.md`다. A1/A2 case별 기존/신규·명령/exit·실제효과·원증거·미실행을 표로 남긴다. B~D의 잔여, core/LIVE 전체 판정의 미완료, 다음 단계 B 착수 조건을 명시한다. 관리 세션만 전역 상태를 갱신한다.

## 5. 기존 개발 세션에 보낼 메시지

```text
$with-human-dev

WP-MVP-01 인계 결과를 관리 세션에서 검토했어.
docs/plans/06_mvp_completion_work_pack.md를 전체 읽고
WP-HARDEN-01의 단계 A(24시간 보존·폐기와 장애·재시작 복구)를 진행해줘.
현재 SPEC-3·최종 fingerprint와 기존 RESULT/REVIEW를 기준으로 이어서 구현하고,
기존 F-008 회귀와 정상·승인·경쟁 동작을 유지해줘.
변경 전 baseline과 실제 시험 증거를 보존하고 별도 AI 검토까지 받아줘.
새 run의 RESULT.md와 REVIEW.md 경로, 남은 B~D를 알려줘.
```
