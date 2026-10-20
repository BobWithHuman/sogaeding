# 시작 전 Docker 네트워크 충돌 수리

2026-10-18. 사용자 context2 시작 명령은 provider broker 생성 전에 `NETWORK_SUBNET_COLLISION_PRESERVE_EXISTING`으로 실패했다. 지정한10.233.114/115는 이전 무모델 시험 `dtap-8e50f8df33` 소유였다. 실제 네트워크 검사 없이 이전 check를 준비 완료로 안내한 런처의 공백이다.

새 과업·모델 호출은0이었다. 이전62 provider/10과업/정산$0.834584, owner0, 활성stop0을 읽기 전용으로 대조했다. 이번 실험 소유의 컨테이너도 없었다. 키가 이미 복사됐지만 값은 열거나 해시하지 않았다.

운영 plan.networks의 주소만10.233.130/131로 바꾸고 동일 실험명·동일 network name·Internal=true로 실제 생성했다. 원 plan은 `user-usd7-context-2/start-failures/network-collision-1/plan.before.json`, 전후 hash/주소는 `network-repair.json`으로 보존했다. manifest/동결 Python78파일/정책/원장/예산은 변경하지 않았다. 다른 실험의 네트워크는 삭제하거나 변경하지 않았다.

실행 전용 startup 조정 파일인 broker-start.lock, 복사된 keys 디렉터리, paid-opt-in.json은 같은 접근제한 실험 폴더의 위 실패 기록 디렉터리로 이동·보존했다. 실행 과업 claim이나 UNKNOWN을 초기화한 것이 아니다. 이동 전 절대 경로와 reparse 여부를 검사했고 키 내용은 읽지 않았다. 다음 명시적인 사용자 PaidOptIn 명령이 새 시작 설정을 만든다.

런처 `Test-DtapNetworks`는 실제 network name·소유 label·Internal·정확한 subnet을 check와 run에서 검사한다. run에서는 시작 lock 생성/키 읽기보다 먼저 검사하므로 같은 종류의 실패가 시작 설정을 소비하지 않는다.

검증: PowerShell5.1 구문/정상·누락·소유권·외부망·주소·중복주소·조회실패·키 이전 거절 **9검사 PASS**. 실제 PowerShell check에서 동결 소스·원장·초기 image6개·두 내부망이 PASS. 제품 Python을 수정하지 않아 앞선114개 회귀는 반복하지 않았다. 이번 추가 유료 호출·broker/controller 시작은0이다.

Manifest는 계속 `6bd1d554f5d3df72443e1ff5b5d218e4e27983e2edb3176257048f38a5958c41`다. **같은 사용자 명령을 이제 한 번 실행할 수 있다.** 먼저 engine-on, shared cap 문구 후 다른 창에서 engine-off를 실행한다. [명령](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-context-output-repair/USER_RUN.md).

근거: [network-start-verification.json](C:/sogaeding/artifacts/20261018-context-output-repair/network-start-verification.json), [PS 시험](C:/sogaeding/artifacts/20261018-context-output-repair/verify_network_start.ps1), [별도 검토](C:/sogaeding/docs/handoffs/WP-DTAP-01/20261018-network-start-repair-review/REVIEW.md). 후속 실제 모델 실행은 사용자 시작 전까지 NOT_RUN이다.
