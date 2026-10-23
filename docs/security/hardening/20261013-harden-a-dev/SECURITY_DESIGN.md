# WP-HARDEN-01 단계 A 내부 설계

작성자: 구현 AI / 사람 개발자는 사용자 1명. SPEC-3, 정책 `mvp-2026-10-13-v1`, 공개 schema·endpoint·enum 변경 없음. 기준 배정은 `docs/plans/06_mvp_completion_work_pack.md` A1/A2. 기존 runtime·키·DB·원증거를 폐기하거나 재시작하지 않았다. 모든 fault/폐기 실험은 Docker dev의 전용 `/tmp` DB다.

## 보존 기한과 접근 경계

Control은 서버 발급 session 생성 시각을 `session_retention.created_at`에 저장한다. 원문 request/comment, token digest, sources/events/calls/decisions/approvals/executions는 이 세션 묶음의 생성+86400초까지 보관한다. 자식 생성·조회·승인·명시 복구가 기한을 연장하지 않는다. 세션 실행권1800초, 승인300초, call8/write1 및 단회 소비는 기존 그대로다. 보존 기한은 실행권 연장이 아니다.

Gateway는 서버가 실제 실행을 기록한 `invocations.started_at`을 comments/receipt 묶음의 생성 시각으로 사용하고 생성+86400초에 폐기한다. 댓글과 invocation은 같은 트랜잭션/서버 시각으로 생성한다. 기존 orphan comment는 자기 `created_at`+86400초로 정리한다. **두 DB의 기산점은 다르다.** 정상 실행은 보통 세션 유효기간1800초 안에 시작하므로 Control 삭제 이후에도 그 생성 시각 차이만큼 Gateway 원기록이 남을 수 있다(각 기록 자체의 보관은24시간). reserve 뒤30초 시작 여유·2초 waiter timeout·thread 스케줄 지연은 세션 expires_at에 다시 결합하지 않으므로, 두 DB 삭제 완료 간격을 정확히1800초 이내라는 엄격한 상한으로 주장하지 않는다. 외부 입력 시각이나 조회 시각은 사용하지 않는다.

`Repository.session`은 active=False인 timeline/close/최종 report도 기한에 도달하면403 SESSION_INACTIVE로 거부한다. `call`이 공통 guard를 거치므로 오래된 call의 reserve/report/check resume, approval 및 source에도 같은 제한이 적용된다. 정리 후에는404/401로 거부한다. Gateway의 비공개 receipt 조회도 자기 기한 이후 None이다. 제어/PDP 접근 실패는 executor 실행권을 만들지 않는다.

## Migration·삭제와 최소 기록

Control startup의 DDL과 migration은 `BEGIN IMMEDIATE` 트랜잭션 안에서 개별 statement로 수행한다. 기존 SPEC-3 세션은 서버가 항상 expires_at=생성+1800으로 발급했으므로 `INSERT OR IGNORE ... expires_at-1800`으로 기존 시각을 복원한다. 사용자 시각/이관 시각으로 새24시간을 부여하지 않는다. 기존 본문·예산·승인·판정은 변경하지 않고 재실행해도 같은 시각을 유지한다. Gateway의 기존 started_at/created_at은 그대로 사용하고 disposals table만 추가한다. 알려지지 않은 다른 schema에 대한 무조건 migration 호환성을 주장하지 않는다.

Control 삭제 순서(단일 tx): 최소 disposals 기록 → executions → approvals → decisions → sources → events → calls → session_tokens → session_retention → sessions. Gateway 삭제 순서(단일 tx): 최소 disposals 기록 → 해당 comments → invocations → 만료 orphan comments. DELETE 실패 시 같은 DB 전체 tx가 rollback된다. Control/Gateway 간 분산 트랜잭션은 없다. 서로 DB를 mount하거나 공유 키를 전달하지 않고 각 서비스가 startup 및 daemon에서 멱등적으로 재시도한다. 한쪽이 먼저 폐기되어도 다른 쪽의 잔존 기록은 새 PDP 예약을 발급하지 않는다.

최소 disposal record는 원래 자료 기한+7일에 제거한다. 지연된 startup도 이 기한을 새로 연장하지 않는다.

| DB | 필드 | 의미 |
|---|---|---|
| Control | session_sha256, deadline, purged_at, retain_until, unresolved_count, call_budget, write_budget | RESERVED/UNKNOWN 합계는 **미해결**로 보존. 성공확정·예산환불 사건이 아니다. 본문/토큰/인자/receipt/원 session ID 없음 |
| Gateway | call_sha256, deadline, purged_at, retain_until, state=EFFECT_RECORDED, write_count | 이 executor에 기록된 효과 존재만 뜻한다. Control의 UNKNOWN을 SUCCEEDED로 바꾸지 않는다. 원 call/session ID, 댓글 본문·receipt·secret 없음 |

폐기한 호출은 Control의 call/session/token이 없어 재예약할 수 없다. 보존 중인 Gateway tombstone도 동일 call 직접 중복 실행을 거부한다. 7일 후 tombstone 제거는 옛 Control 권한을 복원하지 않는다. Gateway private Python 객체를 호스트 관리자가 직접 사용하는 경로의 격리는 기존 보호 범위 밖이다.

## 스케줄·장애 복구

Control과 Gateway는 startup 정리 후 매 sweep 완료에서10초 간격으로 다음 정리를 수행한다. 정상 fixture에서 기한 후 다음 sweep이10초 안팎에 완료되는 것을 실제 daemon으로 관측한다. 처리 중 기한 도달 시 최대 지연 산정은 **진행 중 처리시간+10초+스케줄/정리 실행시간**, SQLite lock 대기는 각 transaction 최대1초다. 저장 오류·중단·프로세스 비가동에서는 물리 삭제 완료의 유한 최대 지연을 보장하지 않는다. 기한 guard는 정리 지연과 무관하게 요청 시 즉시 거부하며, 장애 제거 후 다음 sweep/startup이 다시 시도한다. startup 정리 자체가 실패하면 서비스가 시작되지 않는다.

Control startup/daemon은30초 이상 RESERVED를 UNKNOWN으로 바꾸고, 같은 tx에 감사 사건을 남긴다. 감사 실패는 전이와 함께 rollback; 예약/소비 예산은 남아 위험 재시도가 허용되지 않는다. DB 자료를 직접 UNKNOWN으로 바꿔 통합 통과로 계산하지 않는다. 시험은 전용 DB의 reserved_at만 과거로 이동시킨 뒤 실제 daemon 또는 프로세스 stop/start를 통과한다.

PDP client는 timeout1초, trust_env=False, 검증 mTLS, redirect/재시도 없음, 2xx·정확 schema만 인정한다. malformed JSON/schema 및 dict/list/unhashable 오류코드, valid-schema302도 PDP_UNAVAILABLE로 축약한다. peer의 오류 원문을 저장/반사하지 않는다. reserve·승인·예산·필수 CHECKED/RESERVED 감사는 한 SQLite tx로 묶인다.

읽기 source 실패 후에는 기존 F-008 session UNKNOWN latch가 새 check와 미리 발급한 reserve를 모두 차단한다. source 없는 읽기의 receipt-only 성공 확정은 AUDIT_UNAVAILABLE다. 쓰기 report 손실은 효과1을 없앤 것으로 처리하지 않고 UNKNOWN/소비 예산을 유지한다. 복구는 실제 effects receipt와 기존 reservation의 명시 report만 수행하며 executor를 호출하지 않는다.

SDK2.3.0의 modern JSON response 경로는 http.disconnect를 처리 중 tool에 전달하지 않았다. Gateway RequestGuard가2026-07-28 tools/call에만 연결 종료 감시를 더하고 handler를 취소한다. 이미 예약한 호출은 최대1.5초 shield 안에서 UNKNOWN을 보고하고 취소를 다시 전달한다. 그 보고도 실패하면 durable RESERVED를 daemon/startup이 UNKNOWN으로 만든다. older MCP protocol에서 disconnect를 사용자 취소로 새로 해석하지 않는다. 이미 SUCCEEDED가 확정된 결과를 UNKNOWN으로 역전하지 않는다. worker thread가 취소 후 완료되어도 예약/예산 및 executor 유일성 때문에 자동 재실행하지 않는다.

## 코딩·동적 근거와 잔여

필요한 보존 위험(SEC-08/SR2-7) → 두 DB/조회·승인·보고 외부 인터페이스 → 서버 생성시각 guard·고정 SQL·암호화·secure_delete → 경계/migration/중간실패/daemon/startup 시험으로 연결했다. 장애 위험(SEC-07/SR3-1) → PDP JSON/TLS·SQLite/취소 인터페이스 → bounded client/원자적 reserve/UNKNOWN latch → TLS peer/DB trigger/실제 MCP 취소·receipt 대조로 연결했다. C1 PDF14/15/26 및 G4 PDF24의 요구→설계→소스진단→동적검증·기획서 제2항 설명을 위한 구조적 예방 근거다. 공식 빌드라인·조치율·점수는 추정하지 않는다.

SQLite secure_delete와 암호화 상태에서 전용 DB 및 이름에 매칭되는 journal 파일의 marker/ciphertext/token 검색을 수행했다. **앱 조회 불가·현재 파일에서 지정 marker 잔존0**까지만 의미한다. SSD/호스트 백업/삭제 파일 복구/메모리의 물리적 완전 삭제 또는 CPython secret zeroization은 증명하지 않았다. 역할 키/CA는 데이터 retention 대상이 아니며 lifecycle/rotation은 단계 C/D와 기존 잔여다.

내부8443 모든 container NIC listen, local-ingress·OS outbound 전면 비격리 한계와 B1043 경고를 유지한다. 등록 MCP3도구의 해당 Gateway만 보호한다. 브라우저 UI의 실제 상호작용/XSS는 B, 제품 전체 TLS 수명/복구는 C, 설계20/약점49·OS SCA/NOTICE/SBOM은 D에 남는다. 새 유료 LIVE0, 전체 core/MVP 및 최종 LIVE 미완료.
