# ACL 수리 별도 AI 검토

2026-10-20 · 구현 담당과 별도 AI 역할 `/root/siwc_acl_review`가 원 런처 대비 diff, 회귀 시험, 최종 준비본 binding과 사용자 문서를 좁게 검토했다. 공식 독립 보안 진단이나 실제 계정/모델 검증은 아니다.

최종 결론: 미해결 수정 지적 없음.

- 새 DirectorySecurity/FileSecurity의 수정된 Access 섹션만 저장하는 .NET 경로로 SACL·owner·group 변경을 요청하지 않는 것을 [.NET 구현](https://source.dot.net/System.IO.FileSystem.AccessControl/System/Security/AccessControl/FileSystemSecurity.cs.html)과 대조했다. PS5.1/7 API 분기와 reparse 거절·사용자/SYSTEM만 접근하는 기준이 유지된다.
- 비관리자 회귀 로그의 반복3회·넓은 Everyone 규칙 제거·본문 보존 PASS를 확인했다. 실제 credential 파일에는 접근하지 않았다.
- 새 manifest a922ec20a08bf24585149415929b4eb07a05f77a722437030ac18179927da5c9, source93 일치/launcher만 변경, 세 준비본의 과거429예약/jobs0/시작claim0과 network none 검증을 확인했다.
- 첫 문서 검토에서 USER_RUN의 옛 root·원 검증 로그·원 인증서 만료시각 혼용을 지적했다. acl2와 새 manifest/ACL 검증 증거로 정정하고 임의 인증서 시각을 제거한 후 재확인했다.

검토자는 파일 수정·실제 credential 읽기/수정·계정 API·모델 추론을 수행하지 않았다. 로그인은 사용자가 성공을 보고했으며 실제 계정 모델 목록은 account-check 재실행으로 확인해야 한다. 실제 추론·평가는 NOT_RUN이다.
