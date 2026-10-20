# DB·실행 역할 권한 별도 AI 검토

2026-10-20. 구현과 별도 `/root/siwc_storage_review` 역할이 변경 코드·원인·실행 증거를 검토했다. 실제 credential/계정 API·모델 호출·제품 파일 수정은 수행하지 않았다. 공식 독립 보안 진단은 아니다.

최종 결론: 이 권한 수리의 무모델 준비 범위를 수용하며 미해결 수정 지적은 없다.

- 준비 UID0:GID10001, 실행 UID10001과 역할별 DB/작업 폴더 권한을 확인했다. 다른 UID 접근 거부와 world 권한·symlink 반례 거부를 확인했다.
- PKI 디렉터리 접근 누락 P1을 발견했다.2750 수정 뒤 `runtime-role-final-r2.log`의 실제 UID10001 frozen verify·PKI·작업 쓰기·Docker 소켓 조회PASS로 해소됐다. CA 개인키는 보관하지 않는다.
- supplementary group0은 기존 소켓을 사용하는 신뢰 helper에 한정하며 actor/tool에는 전달하지 않는다. 새 capability는 추가하지 않았다.
- `service-probe-r2.log`의 실제 UID SQLite 쓰기·원 OFFLINE broker·양쪽 TLS 조회와 `storage-negative.log`, lint PASS를 확인했다. LIVE provider 응답이나 실제 Luna 정확도 검증으로 확대하지 않는다.

최종 source93/원장/claim 묶음은 `artifacts/20261020-siwc-storage-fix/final-verification.json`에 별도로 기록했다. 원 실패와 이전 지출을 보존하며 최신 USER_RUN의 storage4 manifest만 활성 실행 안내로 사용한다. 실제 평가 결과는 NOT_RUN이다.
