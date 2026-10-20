# Broker 시작 DNS 오류 수정

2026-10-20. 사용자 acl2 실행은 로그인/모델 목록 확인 뒤 provider broker가 DNS 해석 실패로 종료돼 controller가 MANDATORY_PROVIDER_BROKER_HEALTH_FAILED를 반환했다.

실제 실패 broker의 안전한 오류 유형과 읽기 전용 원장을 확인했다. 새 jobs0/owners0/plan 요청0, 기존429예약이며 두 arm과 broker 시작claim은 남아 있다. broker는 재시작하지 않았고 원 claim·원장·실패 컨테이너를 보존했다. 실제 모델 추론에 도달한 기록은 없다.

원인은 DockerSandbox.create가 컨테이너를 즉시 시작하는데, 기존 broker_start는 내부 전용망에서 시작한 뒤 외부 bridge를 연결한 순서다. SIWC broker는 시작 즉시 계정 모델 목록을 GET하므로 DNS가 필요한 시점과 외부망 연결 순서가 충돌했다.

수정한 create_broker는 **LIVE broker만 생성 시점부터 bridge**를 사용하고 양 내부망의 broker alias를 붙인다. OFFLINE은 기존 내부망만 사용한다. actor/도구의 create 경로와 내부망 격리·정책·Luna low·공식100과업·초기환경·judge·API fallback 금지는 바꾸지 않았다.

- 회귀4개와 변경 경계 lint PASS.
- 실제 Docker에서 자격정보 없는 broker가 부팅과 양 내부망 GET 시 공개 DNS를 해석하고, 두 내부 클라이언트가 broker에 연결되는 것을 확인했다. 각 클라이언트는 자기 내부망만 가지며 외부 bridge가 없다. provider API/모델/credential mount0이다. OFFLINE 외부망 제외는 이번 unit 증거이며 실제 OFFLINE 종단 재실행은 하지 않았다.
- 최초 검증의 Docker socket UID 권한과 두 번째 검증의 결과 파일 덮어쓰기 권한 오류를 보존했다. controller UID와 호스트 stdout 저장 경계를 고친 뒤 별도 검증 namespace에서 통과했다. 사용한 검증용 컨테이너/네트워크만 소유 라벨 대조 후 정리했다.
- 새 준비본은 **user-chatgpt-login-luna-net1**이며, 독립 이름/서브넷153·154로 기존 실패 객체와 분리했다. 원429예약과 누적$4.190921/상한$5.089294/잔여$0.898373을 그대로 계승한다. 새 실행claim/jobs/모델 호출은0이다. 이번 실패는 후보 제출 전이므로 UNKNOWN 호출을 재시도하는 경로를 만들지 않았다.
- 새 manifest **84abda14b5182e8cbf755037398d46c8bc609436c8a149d006bc9f2a1b5c8684**, source93 일치/변경4개. 모델·정책·과업·이미지·예산 동일성을 대조했다. credential mount 없는 network-none 읽기 전용 verify는 FULL_READY100이다.

증거는 `artifacts/20261020-siwc-broker-fix/{original-failure,probe-failure-history,network-probe-final,final-verification}.json`과 focused-tests/final-network-none-check/lint 로그다. 별도 좁은 AI 검토는 [REVIEW](REVIEW.md)에 기록한다.

실제 Luna 추론·100×2 평가는 아직 NOT_RUN이다. 재로그인 없이 최신 [USER_RUN](../USER_RUN.md)의 새 net1 명령을 사용자가 선택 실행한다. 원 acl2나 중간 준비본의 실행 명령·claim을 재사용/초기화하지 않는다.
