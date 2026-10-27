# With Human 엔진 동작·변경 내역

기준: 2026-10-27. 팀원이 현재 엔진 소스를 읽고 동작과 변경점을 이해하기 위한 문서다.

이번 공유는 **엔진 Python 코드와 설명 문서만** 반영한다. 실행·배포 구성, 의존성 변경, 연결기, DTAP 호환 수정, 시험·CI·패키징 도구는 이번 커밋에 포함하지 않는다. 기존 파일은 삭제하지 않는다. 최신 실행 구성까지 통합한 배포·릴리즈 완료본으로 취급하면 안 된다.

## 현재 상태

- 기본 제품 정책은 gate-6, policy ID는 engine-2026-10-24-gate6-1이다.
- 현재 판정은 **ALLOW / DENY / CONFIRM**이다. ASK는 아직 구현 전이다.
- 현재 CONFIRM은 운영자 자격의 /approval로 정확한 후보를 승인하는 방식이다. DENY는 승인으로 풀 수 없다.
- 목표는 엔진 ASK → 에이전트가 실제 사용자에게 질문 → 신뢰 연결기가 답변 전달 → 엔진 재검토다. 대시보드는 통계·현황·IR을 맡는다.
- 질문 발행·전달 확인·실제 사용자 응답·단회 binding·후속 판정·이력 저장이 필요하다. CONFIRM의 문자열 치환만으로 완료되지 않는다.
- 대시보드 기능과 목표 API는 [DASHBOARD_ASK_HANDOFF.md](DASHBOARD_ASK_HANDOFF.md)에 있다. 그 문서의 dashboard/v1 API도 아직 구현 전이다.

## 엔진 동작 순서

1. 신뢰 연결기가 실제 사용자 프롬프트를 세션·턴에 연결한다.
2. 도구 실행 전에 원 도구명·인자·call ID·route를 등록한다.
3. 서버가 도구 schema, 작업영역, 보호 경로, 실제 권한, 서버 관측 출처·완전성을 검사한다.
4. 필요한 후보에 실제 Jev API로 A/B 의미 분석을 요청한다. 모든 후보에 모델을 호출하는 것은 아니다.
5. 공통 gate-6과 현재 권한·문맥으로 ALLOW / DENY / CONFIRM을 판정한다. Jev는 관측을 반환하고 최종 권한·집행은 엔진이 담당한다.
6. 허용·승인된 정확한 후보도 gateway의 최종 대조·원자적 단회 예약을 통과해야 한다. 서명된 정확한 요청만 upstream이 실행한다.
7. 결과를 관측해 이력을 갱신한다. 효과 미확정은 UNKNOWN으로 보존하며 자동 위험 재실행이나 예산 환불로 처리하지 않는다.

ALLOW는 실행 성공이 아니고 CONFIRM은 실행 보류다. 외부 문서의 지시·승인 주장이나 모델의 “사용자가 승인했다”는 문장은 실제 사용자 권한이 아니다. 현재 기본 도구는 등록 작업영역의 MCP read_file/write_file이며 모든 shell/native 도구가 보호된 상태는 아니다.

## 소스 읽는 순서와 역할

| 파일 | 역할 |
|---|---|
| src/app/transparent/server.py | 연결·이벤트·인증·조회 API, TLS listener, 기동 검사 |
| src/app/transparent/engine.py | 세션·턴·출처·후보 연결, 판정/승인/예약 상태, 암호화 DB |
| src/app/transparent/jev_config.py | Jev 설정 검증과 기본 정책 선택 |
| src/app/transparent/jev_gate6.py | 등록 파일 권한과 공통 gate-6 연결 |
| src/app/transparent/gate_policy.py | 재사용하는 순수 gate-6 판정 규칙 |
| src/app/transparent/jev.py | 실제 HTTPS 요청·응답 검증·예산 장부·전송 보호 |
| src/app/transparent/privacy.py | 전송 사본 마스킹·안전하게 변환할 수 없는 입력 거부 |
| src/app/transparent/upstream.py | 서명·단회 시도·등록 경로 확인 후 실제 파일 집행 |
| src/app/transparent/operator_access.py | 운영자 permission과 추가 운영자의 만료 |
| src/app/transparent/retention.py | 상한 있는 보존 기한 설정 |
| src/app/transparent/security_audit.py | 원문 없는 보안 감사와 로컬 경고 |
| src/app/transparent/runtime_lock.py | 실행 중 유지보수 차단 |
| src/app/transparent/maintenance.py | 키 회전·중단 복구·암호화 백업·새 runtime 복원 |
| src/app/security_headers.py | Control 응답 보안 헤더 |

기존 jev_core_v5p1.py / jev_decision_v5.py / jev_policy.py 등은 gate-6의 상속·검증 의존성이다. demo_approval.py / demo_report.py도 현재 서버가 import하는 backend이며 대시보드 UI 소스가 아니다. 엔진은 DTAP actor·시뮬레이터·채점기를 import하지 않는다.

## 무엇을 수정했는가

비교 기준은 이번 공유 이전 로컬 기준 commit a83a5c0이다. 원격에 추가된 팀원의 DTAP 결과 문서는 보존한다.

| 변경 | 주요 파일 | 이전 → 현재 |
|---|---|---|
| 공통 gate-6 | gate_policy.py, jev_gate6.py, jev_config.py, jev_decision_v5.py | 제품 기본 current_candidate_1 → gate-6. 등록 파일의 권한 경계와 공통 판정 연결, 이전 정책 선택자 유지 |
| 판정 문맥 암호화 | engine.py, demo_approval.py, demo_report.py | calls.reason 원문 문맥 → Fernet 봉투. read_reason/write_reason 사용, 명시적으로 연 제품 DB의 평문 이관 |
| 자격·조회 경계 | server.py, operator_access.py | runtime machine 범위·permission/만료, Host/Origin 검사, 공개 health 최소화, 원문 없는 최근100건 요약 |
| Jev 전송 보호 | jev.py, privacy.py, src/app/pdp/diagnostics.py | credential 위주 검사 → 전송 사본 마스킹, 변환 불가 개인정보·발견된 인코딩·별칭 위조 거부 |
| 보존·삭제 | engine.py, retention.py | 고정 기한 → 상한 있는 설정, 생성 시 저장한 deadline, 논리 삭제와 hash/건수 증거 |
| 세션 종료 | engine.py, server.py | CLI 종료 시 미실행 후보·승인 무효화, 실행 불명확 보존, 이력 유지 |
| 키·복구·백업 | maintenance.py, runtime_lock.py, server.py, upstream.py | 오프라인 storage/token/forward/TLS 회전, 문맥 재암호화, journal·fsync, 관리 백업 기한·변조 검사와 새 runtime 복원 |
| 복원 후 예산 | maintenance.py, server.py | 과거 장부로 자동 기동하지 않음. 새 policy_id/새 예산 명시 승인, 이전 장부 보존, 승인 정책 hash와 기동 결합 |
| 감사·경고 | security_audit.py, engine.py, server.py, demo_approval.py | 주체/대상 hash·행위·결과 기록, 승인/삭제와 같은 transaction, 반복 실패·접근 거부 경고 |
| 응답 보호 | security_headers.py, server.py | HSTS(HTTPS), Referrer/Permissions-Policy 등 공통 응답·오류 헤더 |

## 정책·개인정보·권한의 범위

일반 정상 허용 후보는 A의 실제 WITHIN_TASK 선택 + B LEGITIMATE 유효 확신도 .50 이상 및 정확한 권한·출처 검사 통과가 필요하다. 위험 DENY .90과 하드 금지는 유지한다. 민감/위임 범위 밖 보류는 양쪽이 긍정해도 사람 CONFIRM이며 자동 ALLOW가 아니다. 공식 응답 schema, 확률 합·argmax, provider/계산 확신도 중 작은 값 검증을 유지한다.

기본 masked_minimal_v1은 이메일·한국 전화·주민번호 형태·미국 SSN·Luhn 카드번호를 Jev 전송 사본에서 분석별 HMAC 별칭으로 바꾼다. 같은 분석의 A/B에서 같은 원문은 같은 별칭, 다른 대상/분석은 다른 별칭이다. 로컬 원문·hash·span·실행 인자는 바꾸지 않고 복원 대응표를 저장하지 않는다. 지원하지 않는 이름/주소 필드나 안전한 변환이 불가능한 경우 HTTP·예산 예약 전에 거부한다. 모든 개인정보·인코딩을 탐지하는 DLP는 아니다.

history:read / approval:write / session:purge / security:read / security:ack로 운영자 권한을 나눈다. machine은 사람 승인을 대신하지 못한다. 기본 human.token은 해당 runtime 관리자다. 목표는 각자의 단말·OS 계정에서 독립 runtime을 운영하는 제품이며, 동일 OS의 무제한 프로세스·Docker daemon 관리자 침해를 격리하지 않는다.

## 현재 조회·승인 API

| API | 현재 기능 |
|---|---|
| POST /connect, /event | machine 인증의 연결·사용자 턴·실행 전후 이벤트 |
| POST /connections/close | bound CLI 세션 종료·잔여 권한 무효화 |
| POST /authz | private mTLS 집행 검사. public 경로로 대체 불가 |
| GET /history/summary | history:read, 원문 없는 최근100개 판정/상태/사유. 전체 누적 아님 |
| GET /history | history:read, 원문 context를 포함할 수 있는 운영자 이력 |
| POST /approval | 현재 CONFIRM의 정확한 후보 승인/거절. ASK API가 아님 |
| POST /sessions/forget | session:purge, 해당 runtime 범위 삭제 |
| GET /security | security:read, 최근100개 보안 사건·경고 |
| POST /security/alerts/ack | security:ack, 경고 확인. 실행 승인과 무관 |

기존 이벤트 envelope는 docs/mvp/contracts/spec5.schema.json을 따른다. 대시보드에는 raw /history를 그대로 내리지 않고 마스킹 projection이 필요하다. 기간 집계·pagination·ASK 상세는 아직 미구현이다.

## 검증·남은 작업과 이번 공유의 한계

로컬 전체 회귀 1670 passed / 4 skipped, 이후 관련 보안·엔진·연결기·hardening 111 passed, 실제 TLS/gateway/파일 집행 통합3개 통과를 확인했다. 관측 provider는 합성 HTTP fixture이며 유료 actor/Jev 호출0이다. 실제 키 교체 후 기동·이전 토큰/CA 거부·암호화 백업/새 runtime 복원·명시 새 예산 승인 전후 기동도 합성 전용 환경에서 확인했다. 이 수치는 해당 로컬 환경의 증거이며 이번 코드 전용 커밋을 깨끗한 clone에서 전체 재검증한 결과는 아니다.

시험·도구·새 배포 이미지/구성은 이번 커밋에서 제외한다. 기존 실행/평가 코드까지 모두 새 엔진에 맞춰 갱신됐다고 보지 않는다. 특히 직접 json.loads(DB.reason)을 쓰는 소비자는 암호화 봉투를 해석하지 못하므로 Engine.read_reason 또는 인증된 API로 전환해야 한다. 일부 로컬 연결기·DTAP 호환 수정은 업로드 범위 밖에 남아 있다. 유지보수의 TLS 재발급은 기존 tools/prepare_tls.py도 사용한다.

남은 구현은 ASK 전환과 대시보드 목표 조회 API다. 중단된 보안 작업에는 마지막 검사 도구 시험·최종 결과/가이드 매핑 정리·원격 CI/게시가 남아 있다. 실제 provider 보관/삭제/지역·계약 확인과 관리 밖 OS/클라우드 복제본 폐기는 별도 운영 과제다. 이전 DTAP의 방어율을 보안 수정본의 재측정 결과로 표현하지 않는다. 기존 릴리즈·원자료를 덮어쓰지 않았고 모든 IPI 보호·취약점0·공식 심사 점수를 보장하지 않는다.
