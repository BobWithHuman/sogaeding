# Broker DNS 수리 별도 좁은 AI 검토

2026-10-20 · 구현 담당과 별도 `/root/siwc_broker_review` 역할. 파일 수정·실제 OAuth credential/키·계정 API·모델 추론 접근 없이 원 acl2 frozen source 대비 diff와 증거를 검토했다. 공식 독립 보안 진단이나 실제 모델 성능 검증은 아니다.

최종 결론: 확정 수정 지적 없음. broker DNS 수리의 무모델 준비 범위를 수용한다.

- LIVE create_broker의 시작 시 bridge와 이후 양 내부 alias 연결, OFFLINE 내부망 전용을 확인했다. actor/tool create·namespace는 유지되며 실제 외부 접속을 broker만 갖는다.
- network-probe-final.json과 probe 소스를 대조했다. boot와 양 GET에서 public DNS 조회, 양 내부 client의 broker 접근 PASS다. credential mount/모델/provider API는0이다. OFFLINE 격리는 이번 unit 증거이며 실제 OFFLINE 종단을 재실행한 것으로 표현하지 않는다.
- source93 current/frozen 일치·차이4개, net1 manifest84abda14b5182e8cbf755037398d46c8bc609436c8a149d006bc9f2a1b5c8684와 새 이름/153·154 네트워크를 확인했다. 정책·모델·과업·예산은 같다.
- 원429예약·원 실패·양 arm/broker 시작claim 보존, 새 jobs/owners/시작claim0·잔여898373 micro USD를 확인했다. network-none verify/관련4시험/lint PASS를 확인했다.
- 초기 두 probe의 소켓 UID/증거파일 권한 실패와 조치 기록을 보존했다. RESULT/USER_RUN의 새 root/hash 및 실제 추론 NOT_RUN 표기를 확인했다.

문서 명료성 권고1건으로 USER_RUN §1에도 이미 성공한 login/account-check 예시를 건너뛴다고 명시했다. 최종 준비 수용을 막는 결함은 아니며 코드/동결 소스의 추가 수정은 없다.

실제 Luna 추론·DTAP 공격/과업 성능은 사용자 평가에서 확인할 미실행 범위다.
