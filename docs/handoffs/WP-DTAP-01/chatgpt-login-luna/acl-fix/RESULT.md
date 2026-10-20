# 로그인 후 account-check ACL 오류 수정

2026-10-20. 사용자는 공식 브라우저 로그인 성공을 보고했다. 이후 account-check는 Set-Acl의 SeSecurityPrivilege 오류로 모델 목록 조회 전에 중단됐다. 로그인 실패나 모델 거절로 판정하지 않는다.

원 Protect-LoginFolder를 일반 권한의 공개 fixture에 두 번 적용해 첫 성공/둘째 PrivilegeNotHeldException을 재현했다. launcher-before.ps1과 before-reproduction.json을 `artifacts/20261020-siwc-acl-fix/`에 보존했다.

수정은 실행 런처의 ACL 저장 경계뿐이다. 새 DirectorySecurity/FileSecurity에서 수정한 DACL만 .NET API로 저장하며 SACL·소유자·그룹 변경은 요청하지 않는다. Windows PowerShell 5.1은 Directory/File.SetAccessControl, PowerShell 7은 FileSystemAclExtensions를 쓴다. 실제 로그인 토큰·credential 파일 내용·개인 설정은 읽거나 변경하지 않았다. 사용자 account-check가 재실행될 때 기존 전용 credential 경로를 그대로 사용한다.

- PS5.1과 PS7 일반 권한(elevated=false)에서 각각 반복3회, 디렉터리/하위 디렉터리/파일의 user+SYSTEM FullControl만 유지, Everyone 제거, 공개 본문 보존을 확인했다. `tests/powershell/test_dtap_login_acl.ps1`과 final-powershell51/7.log가 증거다. 최초 PS7의 Framework API 부재 실패 후 Core API를 분리한 경과도 보존했다.
- 원 준비본과 acl1 중간본은 그대로 두고 **user-chatgpt-login-luna-acl2**를 새로 동결했다. 현재 지원 명령은 같은 host launcher가 acl2만 가리킨다. 원/acl1의 역사 명령이나 source/scripts 복사본을 별도로 실행하지 않는다.
- 새 manifest **a922ec20a08bf24585149415929b4eb07a05f77a722437030ac18179927da5c9**. current/frozen93파일 일치, 원본과 차이는 scripts/dtap_chatgpt_login.ps1 하나다. actor/Jev/OAuth Python·정책·선택100·초기 환경·공식 judge는 같다.
- credential mount 없는 network none·읽기 전용 verify가 FULL_READY100으로 통과했다. 원/acl1/acl2 각각 과거429예약·새 jobs0·시작claim0이다. 제품 provider 호출/계정 조회/추론/평가 시작은 이 수정 작업에서0이다.
- 누적$4.190921 / 상한$5.089294 / 잔여$0.898373을 유지했다. 별도 좁은 AI 검토를 받았으며 [REVIEW](REVIEW.md)에 범위를 기록한다.

이제 **재로그인 없이 account-check만** 다시 실행한다. 실제 계정의 Luna 제공 여부와 추론 호환성은 아직 확인 전이다. 계정 확인 뒤 사용할 check/run/status/collect 명령은 [최신 USER_RUN](../USER_RUN.md)을 따른다. 무모델 검사나 ACL 시험이 모델 성능·평가 완료를 뜻하지 않는다.

안전한 종합 증거: `artifacts/20261020-siwc-acl-fix/final-verification.json`.
