# 공동 개발 공유 준비 별도 AI 검토

검토일: 2026-10-20. 검토 범위는 아래 10개 공유/개발 초기화 파일이다. 기존 제품 소스·계약·정책·모델 설정·키·원장·서비스는 수정하지 않았다. GitHub 생성/업로드 및 실제 actor/Jev/로그인 요청은 하지 않았다.

## 결론

검토 범위에서 확정된 P1/P2 결함을 발견하지 않았다. 소스 공유/초기 개발 연결을 위한 후보로 수용 가능하다. 새 clone의 실제 Docker 빌드·대표 통합시험·TLS gateway/MCP 확인은 구현 담당이 별도로 수행하며, 본 검토에서 이를 중복 수행하거나 무모델 연결을 모델 정확도 증거로 표시하지 않는다.

## 대조한 경계

- Compose는 저장소 절대경로 hash와 RuntimeName에 결합된 새 전용 Docker named volume을 사용한다. prepare는 기존 host runtime 또는 동명 volume이 있으면 거절하며, 새 볼륨에만 PKI·DB·합성 workspace를 생성한다. Compose의 `external: true`는 prepare가 생성한 이 볼륨을 재사용하기 위한 선언이다. 기존 제품 runtime·기존 제품 named volume·개인 키 저장소를 참조하지 않는다. 서비스는 volume subpath로 필요한 역할 키만 RO, 각자 DB·executor workspace만 RW로 받는다.
- Control/MCP 공개 포트는 loopback에만 바인딩하고, 실제 agentgateway의 고정 digest와 기존 gateway→Control/upstream mTLS·서명 전달 계약을 유지한다. 서비스는 UID/GID 10001, read-only root, cap-drop과 제한된 tmpfs를 사용한다.
- `JEV_POLICY_FILE=/not-mounted/policy.json`으로 provider가 비활성인 모드를 확인하며, check는 연결 발급·initialize·tools/list·disconnect만 수행한다. tools/call을 실행하거나 의미 판단을 우회하지 않는다.
- 새 PKI는 매 runtime 생성하고 기존 이름·경로 탈출을 거절한다. Windows host ACL을 넓히지 않고 비밀은 Linux 볼륨의 UID 10001, directory 0700/file 0600으로 보관한다. 준비 시 root/CAP_CHOWN helper는 새 볼륨 루트의 owner만 설정하며, 나머지는 비root로 실행한다. 호스트에는 비밀 없는 prepared/networks JSON만 남긴다. 전역 신뢰·개인 Codex 설정을 변경하지 않는다. 인증서 2일 수명과 새 이름 재발급 절차를 문서화했다.
- export는 허용한 소스 디렉터리만 선택한다. artifacts/data/runtime/개인 로그인/Git 이력은 복사하지 않고 private 파일명·확장자와 credential 패턴을 검사한다. symlink 또는 resolve 결과의 root 외부 경로를 거절한다. 패턴 검사를 모든 비밀 부재의 증명으로 주장하지 않는다.
- Docker 기본 주소 풀 소진 대응은 기존 네트워크의 IPAM을 읽어 새 /24 두 개를 선택·저장하며, 기존 네트워크의 삭제/이름 교체/서브넷 변경을 하지 않는다. 충돌 경쟁이나 선택 풀 소진은 실패로 남는다. 프로세스 환경값은 finally에서 복원한다.
- README/개발 안내는 provider 없는 연결검사, 실제 모델 미검증, DTAP 미완료, 일부 local-artifact 의존 시험, native 전체 보호 미완료를 구분한다. HTTP endpoint/인증/enable 조건은 현재 server.py와 대조했다. 과거 조직 PR 강제 규칙을 새로 추가하지 않았다.

## 독립 확인

1. 합성 runtime/credential 파일의 source export 제외: PASS.
2. credential 패턴 발견 시 값 비노출·output 디렉터리 생성 전 거절: PASS.
3. network_pair 빈 Docker 목록: 두 별도 /24 선택 PASS.
4. broad IPv4 CIDR와 IPv6 혼합: 겹침 없는 /24 선택 PASS.
5. 10/8 전체 점유: 기존 보존 오류로 거절 PASS.
6. 실제 Windows symlink 생성 반례: OS 권한 부족으로 미실행. 거절 분기는 정적 검토했으며 이 항목의 동적 PASS를 주장하지 않는다.

첫 로컬 반례 시도는 sandbox Temp 권한 오류로 fixture 생성 전에 실패했다. 저장소 artifacts 아래 별도 합성 fixture로 옮겨 1~2를 완료했으며 제품 오류로 분류하지 않았다. 전체 통합시험은 중복 실행하지 않았다.

## 후속 변경 재검토

구현 담당의 실제 새-clone 연결에서 Windows bind-mounted 파일 권한 오류와 upstream contracts mount 누락이 발견됐다. 실패 증거·생성 키를 보존한 채 실패 stack만 종료했으며, named-volume 저장·역할별 subpath 분리·upstream contracts RO mount를 추가한 최종 변경을 재검토했다. 현재 확정 결함은 발견하지 않았다. ROOT hash/RuntimeName 명명, 기존 volume/runtime 거절, 단회 생성 경로, 환경 복원, down의 volume 보존, 문서의 새 위치 설명이 코드와 일치한다. 이 부분의 실제 수정 후 TLS/MCP 결과는 구현 담당의 후속 연결검증으로 확인하며 본 검토에서 아직 실행하지 않은 통합 결과를 PASS로 표시하지 않는다.

## 적용 보안 기준 및 한계

`docs/plans/03_guide_compliance.md`의 G-02(이미지/의존성 고정·최소권한·secret 제외), G-03(경로/역할/인증), G-06(전송 검증·키 분리), G-07(안전한 오류), G-08(별도 검토)를 변경 범위에서 대조했다. 해당 문서가 연결한 G1 PDF35~38, G3 PDF507~511, G4 PDF24의 기존 근거를 재사용하며 PDF 전체 재진단 또는 설계20/약점49 전체 신규 PASS라고 표시하지 않는다.

secret 패턴 점검은 일반 secret scanner/수동 검토를 대체하지 않는다. Windows PowerShell+Docker Desktop 외 OS의 ACL/ownership은 이번 동적 검증 범위가 아니다. 공개 운영 배포·전체 pytest·실제 Jev 성능·DTAP 완주는 별도 범위다.

## 검토 당시 파일 SHA256

- `.gitignore`: `5147b61e6a6cf35805f2aed052d57d66b1f30da13e3a0fd1c193b0d64cc7718b`
- `.gitattributes`: `62e0479552733938db9f24cf4448ed05a849d6875ffb6cf97b3fbe422f563d4f`
- `README.md`: `4b183ee6df3a7478b763fa24eabe2b41e0dfe354a656ef6e13f2fd8079b11290`
- `CONTRIBUTING.md`: `22e7cf1ca70397ca55828a3e42ffba62d6343fb0e91e7ddb39f989cb535b118a`
- `compose.team.yaml`: `1cb94a83df47db6fe8dcca6addd28ac249a6d367d740279c6d7c9a17d2b283ab`
- `scripts/team_dev.ps1`: `acdb010e9602a2d69ece6a2ebbc1bd916a1ad663c7c577193419ade589c1c5c1`
- `tools/team_runtime.py`: `32c5f5b209d8cb7785a9c0639a40637e4c0c5b10730b932dd606264b9cde0276`
- `tools/repository_export.py`: `1c8887f19a9a365e42b1198c278024207a3186e85085c5f9b901ec2653a564a6`
- `tests/hookgw/test_team_share.py`: `c1306bf87a5ec08f06e3ce6da5dd0e1cff9f40df9a3960b7903f2f230f20cfb5`
- `docs/development/TEAM_HANDOFF.md`: `6e6c01341dca13a90a95c8eae8c551e5e59caef81280b4b29b8a20bfae6e8945`
