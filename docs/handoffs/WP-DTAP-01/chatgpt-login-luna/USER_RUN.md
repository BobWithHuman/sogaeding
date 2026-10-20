# 현재: 실제 분석 장애를 수정한 미시작188건 후속

이전 dde77…/-StreamContinuation 실행은 종료했다. 같은 run을 반복하지 않는다. 원 source100·12종료행·UNKNOWN8·플랜 UNKNOWN5·원 stop·파일 효과·지출을 보존했다. 현재새버전실제평가는 NOT_RUN이다.

고정root: C:/sogaeding/artifacts/20261018-dtap-os100/user-functional-metadata-fix-1
고정hash: `01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be`

수정: 실제 읽을수없는 하위폴더를 전체분석장애로 처리하던 오류, 감사로그 이름/크기조회까지 금지하던 오류, 정상 directory trailing slash 오판을 고쳤다. 권한없는 하위경로는 policy DENY/CONFIRM으로 진행을 제한하고 다른 과업을 계속할 수 있다. 숨은 하위를 빈곳으로 보거나 다른신원으로 우회하지 않는다. 감사로그 내용/삭제/변경·비밀파일·링크·private 통제는 유지한다. 진짜 인증/모델/IO/분석/Post/저장 장애는 여전히 양쪽중단이다.

## 창1: engine-off

Docker Desktop을 켠 상태에서 아래를 한 번 실행한다. 기존 전용로그인을 재사용한다.

```powershell
& C:/sogaeding/scripts/dtap_functional.ps1 -Mode run -MetadataFix -Arm engine-off -StartEvaluation -ManifestSha256 01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be
```

## 창2: engine-on

창1에 PROVIDER_BROKER_STARTED_LIVE가 나온 뒤 두 번째 PowerShell에서 한 번 실행한다.

```powershell
& C:/sogaeding/scripts/dtap_functional.ps1 -Mode run -MetadataFix -Arm engine-on -StartEvaluation -ManifestSha256 01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be
```

두조건 actor/조건부권한시뮬레이터는 Luna low/ChatGPT로그인, API fallback·다른모델·judge LLM 없음이다. 원100목록과 초기image·공식주입/judge·.50/.90을 유지하고 종료12건은 실행하지않는다. 추가개발모델호출0, 사용자새실행은 아직없다. 기존누적$4.191420/상한$5.089294/잔여$0.897874를공유한다. 플랜2000/arm1000 상한은 과거153회포함이며 quota/완주는 보장하지않는다.

## 상태·수집·중단

오류/UNKNOWN이면 run을반복하지않고 collect한다.

```powershell
& C:/sogaeding/scripts/dtap_functional.ps1 -Mode status -MetadataFix -ManifestSha256 01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be
& C:/sogaeding/scripts/dtap_functional.ps1 -Mode collect -MetadataFix -ManifestSha256 01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be
# 필요할때양쪽중단
& C:/sogaeding/scripts/dtap_functional.ps1 -Mode stop -MetadataFix -ManifestSha256 01107ca17aa8a8527932f0796c5b6305f63f4478e8bbbd3cc8a6bf2b2c90a7be
```

status는 보존 원장 합산이다. 새정책 성능은 collect 후 root의 summary.json/summary.md에서 본다. 이전12건은 INHERITED_*로구분하고 새policy성공/방어율에서제외한다. 원100전체의단일버전ASR은미완료다.

## 남은한계

정당한동의가필요한작업의 CONFIRM은자동승인하지않는다. 이번수정은모든정상업무성공을보장하지않는다. 실제실패환경의metadata검사+실제Engine/모의Jev·관련238PASS/역사준비1제외, 보고서영향35PASS+기존보고서1PASS, 최종PS5.1/UID10001/hash check PASS다. 이번에 실제gateway전체나 실제모델평가를 새로실행하지않았다. 준비된runtime100은등록부범위이며100건실제성공을뜻하지않는다. 별도검토는 REVIEW.md를따른다.
