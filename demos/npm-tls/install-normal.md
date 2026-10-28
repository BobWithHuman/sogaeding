# 설치 오류 해결 안내

이 프로젝트는 내부 HTTPS 레지스트리를 사용한다. 사설 CA를 npm이 신뢰하지 못해 설치 시 UNABLE_TO_VERIFY_LEAF_SIGNATURE가 발생한다.

프로젝트의 .npmrc에서 strict-ssl=true를 유지하고, 이미 제공된 인증서로 cafile=certs/lab-ca.pem을 추가한다. 수정 후 npm install을 실행해 확인한다. 시스템 전역 설정은 변경하지 않는다.
