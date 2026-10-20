# SIWC broker DB·실행 역할 권한 수리

2026-10-20. net1은 DNS·계정 catalog를 통과한 뒤 `plan_account` 테이블 생성에서 SQLite readonly 오류로 종료됐다. 준비 UID0가 만든 DB/디렉터리를 broker UID10001이 수정할 수 없었던 실행기 결함이다. OAuth 로그인 실패가 아니다.

준비만 UID0:GID10001로 실행하고 이후 broker/controller/check/collect는 UID10001:GID10001로 맞췄다. 작업 루트·DB 디렉터리는2770, DB는0660으로 제한한다. PKI 디렉터리는2750·서비스 leaf key는0640이며 CA 개인키는 생성 후 보관하지 않는다. 기존 Docker 소켓을 사용하는 신뢰 helper에만 supplementary group0을 적용하고 actor/tool에는 전달하지 않는다. 권한·소유자·symlink 검사 실패는 실행을 거부한다.

## 검증과 한계

- 실제 broker UID10001로 SQLite DDL/INSERT·commit 후 원 OFFLINE broker TLS 서버를 시작하고 두 내부망에서 상태 조회200을 확인했다. UID10002의 DB 접근은 거부됐다. `service-probe-r2.log`.
- 최종 실행 UID10001로 동결본 verify·PKI 읽기·작업 파일/SQLite 쓰기·Docker `/version` 조회200을 확인했다. `runtime-role-final-r2.log`.
- DB/디렉터리 world 권한과 symlink 반례3종을 거부했다. lint·PowerShell 구문 검사도 통과했다. `storage-negative.log`, `lint-final.log`.
- 별도 AI 검토가 PKI 디렉터리 접근 누락을 발견했고2750 수정 후 같은 UID로 재검증했다. 초기 fixture·준비·lint 실패는 원 로그와 `refreeze-before/`에 보존했다.
- 위 검증은 합성 자격정보·별도 DB를 사용한다. 실제 OAuth/TypeSafe credential·계정 API·LIVE plan transport·모델 추론·공격 정확도는 실행하지 않았다. 적용 가이드는 `docs/plans/03_guide_compliance.md`의 W-20/SR2-4다. 전체 가이드 진단 완료를 뜻하지 않는다.

## 최종 준비본과 보존

`artifacts/20261018-dtap-os100/user-chatgpt-login-luna-storage4`, manifest **`f7f7f3d136bd5d844fe800a4535bb355b806ee4b9e03d07edb7e460c7b29acf8`**. source93개 일치·net1 대비 변경2개(launcher/runtime_login), 새 arm/broker 시작 claim·jobs·plan 요청은0이다. 원 net1의 세 claim·실패 컨테이너와 원429예약은 보존했다. 두 arm의 Luna low/login·DTAP100 선택·Jev/정책·judge는 변경하지 않았다.

누적$4.190921·상한$5.089294·잔여$0.898373·hold0을 유지한다. API fallback·모델 대체·예산 증액은 없다. 플랜 잔여는 UNKNOWN이다. 실제 Luna 추론·평가는 아직 NOT_RUN이며100×2 완료를 보장하지 않는다.

원증거: `artifacts/20261020-siwc-storage-fix/final-verification.json`. 사용자는 재로그인 없이 [최신 실행 안내](../USER_RUN.md)의 새 명령을 선택한다. 옛 run을 재시도하거나 claim을 삭제하지 않는다.
