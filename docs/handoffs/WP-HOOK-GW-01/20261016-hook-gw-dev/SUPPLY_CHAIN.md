# 신규 agentgateway 공급망 확인

2026-10-16. 공식 release1.6.0/registry만 사용, image digest·source revision·license는 `agentgateway/dependency.lock.json`에 고정했다. 실제 `docker image inspect`와 config validate를 확인했다. 기존 Python 개발 이미지/lock을 재사용했고 새 Python 패키지는 설치하지 않았다. 공식 registry digest 검증은 publisher 서명 검증과 다르며 후자는 NOT_VERIFIED다. Codex는 설치된0.154.0 native binary hash를 실측했고 별도 CLI 다운로드/업데이트하지 않았다.

근거: [공식 release](https://github.com/agentgateway/agentgateway/releases/tag/v1.6.0), [고정 소스](https://github.com/agentgateway/agentgateway/tree/ea5608642b9d5c94c5baf5fd9f2f9849b808e963), 원문 `artifacts/20261016-hook-gw-dev/agentgateway-LICENSE`(Apache-2.0). 이미지 전체 OS 패키지의 라이선스를 Apache 하나로 판정하지 않는다.

설치된 Docker Scout1.22.0으로 고정 로컬 이미지 SPDX SBOM을 생성했다(`scout-sbom-command.json`, `agentgateway.spdx.json`). package/recipe 항목은 실제 SBOM을 따른다. 전체 Rust 바이너리 구성요소를 이 OS 위주 SBOM이 모두 탐지했다는 뜻이 아니다. image CVE 조회는 Docker 로그인 요구로 실행 실패했다(`scout-cves.txt`, exit1). 개인 Docker 인증을 변경하거나 새 계정/도구를 설치하지 않았으며 이 실패를 clean scan으로 세지 않았다.

보완으로 **공식 고정 커밋의 공개 Cargo.lock**(SHA256 `38fb7a6c71b8d71768cbb947184ddfb140e66278f9fa3780f1038f68869d1386`)만 [OSV querybatch](https://google.github.io/osv.dev/post-v1-querybatch/)에 대조했다. 808개 registry 패키지·버전, 응답 page 누락0, 4개 패키지/12개 advisory 레코드 매칭. 중복 alias/미유지보수 권고가 있으므로 12개 고유 취약점으로 계산하지 않는다. 사용자 프로젝트/키/DB는 전송하지 않았다. `osv-public-cargo` 명령/원응답 `agentgateway-osv.json`, 권고 원문 `agentgateway-osv-details.json`, 고정 Cargo.toml 두 개를 보존했다.

| 매칭 | 원문/설정 대조 | 결론 |
|---|---|---|
| atomic-polyfill1.0.3 / paste1.0.15 | RUSTSEC-2023-0089 / 2024-0436 미유지보수 권고. lockfile 존재가 곧 실행 경로는 아님 | 유지보수 위험 기록, 대체/실포함 확인 남음 |
| rmcp0.10.0 6레코드 | 고정 `crates/agentgateway/Cargo.toml`207줄 dev-dependencies,231줄 legacy-rmcp. production rmcp는125줄3.1.0. OAuth/StreamableHTTP 관련 권고. 현재 proxy 설정은 host HTTP backend이며 rmcp MCP aggregation/OAuth discovery를 구성하지 않음 | **source dev/test dependency 및 현재 비구성 경로라는 근거**. 이것만으로 이미지 전체 VEX/비영향 인증을 주장하지 않음 |
| rustls0.23.45 4레코드 | 0.23.46 수정. Debug client session secrets(0346), ECH rejection/early buffered data(0347), non-default Brotli certificate decompressor(0348), unauthenticated key-share prediction/PQ downgrade(0349) | 아래 제한적 경로 대조. patched binary 적용/feature closure 최종 확인 미완 |

rustls 경로 대조: 저장한 고정 root Cargo.toml189줄은 default-features=false와 tls12/std/logging이며 rustls Brotli를 명시하지 않는다(279줄 Brotli는 async-compression의 다른 feature). 저장한 backendtls.rs는 기본 검증 cache/설정으로 CA·hostname을 검증하며 ECH 설정이나 custom session Debug logger를 추가하지 않는다. 이번 목적지는 고정 private mTLS 두 곳이고 임의 OAuth/remote upstream을 받지 않는다. PQ 권고 원문은 인증 우회/키 compromise가 아닌 후속 연결 기밀성 약화를 구별한다. **전이 feature/실제 binary 빌드 재현·런타임 도달성은 완전 증명하지 않았다.** 따라서 종합 SCA PASS/모든 advisory 조치완료/공식 조치율을 표시하지 않는다. 보안 배포 전 patched 공식 이미지 또는 검증 빌드와 재진단이 남는다.

이 결과는 R1 PDF25, G1 PDF35~41·47~53의 구성요소/무결성/SBOM·CVE·라이선스 추적 요구에 연결한다. 출처·pin·부분 진단을 남겼으며 C/D 전체나 공식 인증으로 확대하지 않는다. 신규 도구는 현재 로컬·고정 목적지 개발 검증 범위에 한정하고 일반 원격 배포 승인은 아니다.
