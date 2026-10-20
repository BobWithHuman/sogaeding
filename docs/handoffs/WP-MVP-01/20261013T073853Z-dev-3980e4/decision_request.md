# 관리 인계·잔여 게이트

추가 의존성/기능 의미 변경은 시행하지 않았다. cryptography50.0.2는 기존 고정 lock의 설치 의존성을 사용했다. ADR-S01에 따라 전송/wire만 SPEC-3으로 동기화했다. Docker Desktop의 internal-only 네트워크에서 host publish가 되지 않아 127.0.0.1 전용 local-ingress bridge를 추가했다. 서비스 간 통신은 별도 internal development network 및 mTLS+service bearer다. 임의 outbound URL 기능은 없으나 OS egress 전체 격리로 주장하지 않는다. 관리 세션이 변경 근거와 잔여 네트워크 보호 범위를 검토해야 한다.

진행 가능한 후속: 기존 코드·lock으로 retention/실제 fault matrix/브라우저·인증서 만료·키수명·20/49 수동 및 원문 본문 검토를 보강한다. OS 이미지 SCA 및 SBOM schema·고지 완전성을 위한 추가 도구/의존성이 필요하면 후보·출처/무결성·라이선스·범위를 관리 세션에서 결정한다. 현재 inventory/SCA를 전수 완료로 올리지 않는다. 전역 plans/build_tasks DONE 판정은 관리 세션 전용이다.
