# T-JEV-05 Windows inspect UTF-8 수리 RESULT

2026-10-16. UTF8_INSPECT_REPAIR_START_PROMPT 전체·최신 AGENTS/관리 관측·with-human-dev/검증 기준을 적용했다. 구현 `/root`, 별도 AI 검토 `/root/jev_review`, 사람 개발자는 사용자1명이다. 공식 독립 보안 진단이 아니다.

**수정·실제 PowerShell5.1 한국어 출력/JSON 파싱·관련 회귀·별도 AI 검토 완료. 실제 OpenAI/TypeSafe/actor 요청0, 실제 TypeSafe 키 본문·내용 해시 읽기0.** 기존 키를 다시 입력하거나 prepare/key/evaluate를 실제 준비에 실행하지 않았다. 모델 접근/인증·의미 정확도는 NOT_VERIFIED/NOT_RUN이다.

- [별도 REVIEW](../20261016-jev-utf8-review/REVIEW.md)
- [증거 인덱스](../../../../artifacts/20261016-jev-utf8/final-index.json)
- [최신 사용자 절차](../../../mvp/09_rules_first_jev.md)

## 최초 실패와 최소 변경

변경 전 [200파일 source/manifest](../../../../artifacts/20261016-jev-utf8/baseline-source/manifest.json), fingerprint `5e023a303a2e48569efbc326c49172972cd4a0054b6103bc3c36a085820b395b`를 고정했다. [관리 진단](../../../../artifacts/management-jev-inspect-20261016/observation.json)의 cp949/utf8_mode0·UnicodeDecodeError(offset144)와 동일한 조건을 실제 PS5.1에서 재현했다. [기준선](../../../../artifacts/20261016-jev-utf8/baseline.json)은 PS5.1.26100.9711·cp949·utf8_mode0·inspect 실패다. 이 재현은 기존 helper의 안전한 오류 응답만 수집하며 키/Docker/모델0이다.

수리는 **scripts/jev_eval.ps1만의 런처 I/O 변경**으로 끝냈다. 모든 신뢰 Python 호출에 `-X utf8 -I`를 명시한다. CP949인 기본 read_text와 Python의 stdout을 UTF-8로 고정하고 PS5.1 native 캡처/기존 ASCII key stdin을 위해 Console.OutputEncoding/OutputEncoding을 호출 동안만 UTF-8로 설정한다. 정상·오류·취소·승인 거절에서도 finally로 원 상태를 복원한다. 환경변수/전역 설정·실행정책·chcp·CLI 설치에 의존하거나 변경하지 않는다.

고정 stage/code로 Python 시작 실패/PYTHON_START_FAILED, nonzero/HELPER_NONZERO_EXIT, 빈 출력/HELPER_EMPTY_OUTPUT, 비JSON·object 이외 출력/HELPER_JSON_INVALID, 숨긴 입력 실패/KEY_INPUT·HIDDEN_INPUT_FAILED, UTF-8 설정 실패/UTF8_SETUP_FAILED를 구분한다. native stderr·실패 stdout·원 exception 문장/자료·비밀 경로는 진단 메시지로 복사하지 않는다. 성공 stdout은 단일 JSON object 유효성만 확인하고 원 문자열을 그대로 내보낸다. helper가 거절한 모든 이유를 인코딩이나 저장 오류라고 단정하지 않는다. 기존 실제 이유의 typed helper/PDP 계약은 그대로다.

숨긴 입력→ASCII 값→stdin·SecureString/BSTR 정리는 유지하고 key 값을 argv/환경/콘솔/로그로 전달하지 않는다. evaluate의 manifest/ConfirmSend/4요청·256000 승인 조건과 helper의 TLS/별도 원장·no-retry/실패 중단은 그대로다. 실제 평가를 실행하지 않았다.

**tools/jev_eval.py·src·질문·fixture·동결 계획·manifest·disabled policy를 수정하지 않았다.** 기존 source_hashes는 PS를 포함하지 않으므로 migration·manifest 덮기·새 준비/예산 발급 없이 같은 manifest 검증을 유지한다. helper SHA `6e271c33...614ab`와 동결37소스 일치는 별도 검토의 [frozen check](../../../../artifacts/20261016-jev-utf8-review/frozen-check.json)에 있다.

## 실제 검증

| 검증 | 결과 |
|---|---|
| 실제 기존 준비 inspect | [최종 PS5.1](../../../../artifacts/20261016-jev-utf8/inspect-final-r3.json): CP949/OutputEncoding ASCII에서 시작, ConvertFrom-Json PASS, 한국어 보존·합성2후보·원 계획 전체와 동일, Console/OutputEncoding 복원 PASS. |
| 실제 stdout bytes | [직접 capture](../../../../artifacts/20261016-jev-utf8/direct-output-r3.json): exit0/strict UTF8 decode/JSON PASS·한국어·원계획 동일·stderr없음, stdout SHA `bdd4d7c33304ca742908906708f15887e505d1e714aa2f68d58f98ce435928d3`. |
| 실제 모델0 preflight | [최종 결과](../../../../artifacts/20261016-jev-utf8/actual-preflight-r2.txt): ready_for_user_opt_in=true/default_enabled=false/live_authorized=false/paid_requests0/provider ledger없음·actual_key_read=false·provider/model 접근 NOT_VERIFIED_NO_REQUEST. network none의 metadata 검사이며 실제 키 인증이 아니다. |
| 실제 collect | [결과](../../../../artifacts/20261016-jev-utf8/actual-collect.txt): current_source_matches_frozen_run=true·NO_ATTEMPTS·0요청/예약·결과 NOT_RUN. |
| 작성자 재사용 native fixture | [21/21 PASS](../../../../artifacts/20261016-jev-utf8/native-r2/native.json), [명령](../../../../artifacts/20261016-jev-utf8/native-fixture-r2-command.json). 한국어/漢/emoji/combining mark·JSON/모든 Python isolated+UTF8·CP949 복원·시작/nonzero/malformed/empty 고정 오류·합성 ASCII stdin·숨긴 입력 취소·미승인 evaluate 차단. 실제 key/Docker/모델0. 테스트는 `tests/hookgw/jev_utf8_probe.ps1`에 남겼다. |
| 별도 AI native fixture | [12/12 PASS](../../../../artifacts/20261016-jev-utf8-review/independent-final.json). 실제 PS5.1에서6모드·정확 evaluate argv·미승인 helper0·고정 오류·합성 ASCII stdin·stdout UTF8 SHA·복원을 독립 대조했다. 중복 검증 수를 합산하지 않는다. |
| 관련 오프라인 회귀 | [105 PASS/4.92초](../../../../artifacts/20261016-jev-utf8/regression.txt), [명령/시각/소스](../../../../artifacts/20261016-jev-utf8/regression-command.json): 기존 helper24+adapter50+policy31, fake HTTP/key·network none·임시 원장. |
| 정적 | [PS AST 두 파일 오류0](../../../../artifacts/20261016-jev-utf8/powershell-ast.json), 별도 수동 검토. PS 분석기 신규 설치/전체49 보안 PASS 주장은 없다. Python/product 소스는 변경하지 않아 새 Python 정적 진단으로 범위를 확대하지 않았다. |

초안 r1의 local LASTEXITCODE 초기화가 native의 global exit-code 갱신을 가려 실행 성공을 시작 실패로 오판했다. 원 실패를 보존하고 global 자동 상태를 명시해 고쳤다. 별도 검토에서 성공 exit0의 malformed/empty 출력과 Read-Host 실패의 원문 노출 가능성을 찾아 위 고정 코드로 보완·재진단했다. 작성자 native fixture는 테스트 문자열을 이중 Unicode decode해 최초 FAIL했고 fixture만 수정 후21PASS다. 첫 실제 preflight 명령의 `-File` 오기와 sandbox의 AuthorizationManager 제한도 보존했다. 전역 실행정책은 바꾸지 않았고 host 실행으로 검증했다. 이 실패들을 보안 공격 식별 PASS로 계산하지 않는다.

## 보존·가이드·한계

실제 기존 manifest SHA **`b542e3ee0cd8b8674f4679b735e8719d8dbe1f6737da75f20ac3d53a0116680f`**는 그대로다. [보존 결과](../../../../artifacts/20261016-jev-utf8/preservation-final.json): key 길이/생성·수정시각/ACL 동일, requests/manifest/disabled policy SHA 동일, ledger/authorized-run/result는 계속 없음. **키 내용의 byte/hash 비교는 하지 않았다.** key는 stat/Get-Acl metadata만 관찰했고 본문을 열지 않았다. 최초 비교가 PowerShell map property 순서 때문에 false였던 기록도 보존하고, 독립 JSON map equality로 before==after 전체 동일을 확인했다. 정밀 body 불변을 해시로 입증했다고 확대하지 않는다.

최종 [201파일 manifest](../../../../artifacts/20261016-jev-utf8/final-source/manifest.json) fingerprint **`dbdae09f5b787c5eafad4b58da43f54b0e0872f204c3d968645a6c65bf5cd1b0`**다. 실제 변경은 PS 런처·새 native regression fixture·현재 사용 설명3파일이다. 기존 PDP 정책/DB/키/승인/원장/READY/UNKNOWN·관리 plans/harness/AGENTS/skill·전역 로그인/CA/설정을 쓰지 않았다. 서비스 재시작·제품 bundle/기존 예산 초기화·증액·모델/질문 변경0이다.

필수 원문 [새 추출5페이지/원본 SHA 대조](../../../../artifacts/20261016-jev-utf8/guide-pages.json): G2 PDF133/135/137의 상세 오류·trace 노출 방지/적절한 예외 처리, G3 PDF511의 SR3-1/세션 통제, G4 PDF38의 중요정보·권한 통제를 고정 stage/code·stderr/원본문 미출력·상태 복원·키 비노출/기존 권한 보존 시험에 연결했다. Python 호출은 신뢰 executable의 고정 `-X utf8 -I`/인자 배열이며 셸 문자열을 새로 조립하지 않는다. 전체 설계20/약점49/R1·G1 적용성과 남은 공급망 범위는 [직전 변경분](../20261016-wait-jev-prep/GUIDE_APPLICABILITY.md) 및 그 전행 검토를 유지한다. 이번 변경 관련 W05/15/20/22/36~38/40/43/45를 재검토했으며 나머지를 일괄 PASS로 올리지 않는다. 새 의존성/다운로드/이미지0이다.

실제 Jev 모델 접근/응답·한국어/공격 판정·CLI 효과·전체 native/hook 장애·TLS 전수 negative/키수명·공급망 잔여는 미검증/미완료다. 사용자 preflight 준비 성공은 실제 키 인증이나 IPI 보호 성공이 아니다. 전역 DONE/MVP 판단은 관리 세션에 남긴다.

## 사용자가 이어서 실행할 정확한 명령

기존 키/계획을 그대로 사용한다. **prepare/key를 다시 실행하거나 파일을 삭제하지 않는다.**

```powershell
cd C:\sogaeding
$inspection = .\scripts\jev_eval.ps1 -Mode inspect | ConvertFrom-Json
$inspection | ConvertTo-Json -Depth 100
.\scripts\jev_eval.ps1 -Mode preflight
```

한국어 자료·질문/criteria·후보2개와 위 manifest SHA를 확인한다. preflight의 ready_for_user_opt_in=true와 default_enabled=false/live_authorized=false/paid_requests0/provider_access=NOT_VERIFIED_NO_REQUEST를 함께 확인한다. 실패 시 고정 stage/code를 인계하며 재준비/삭제/모델 변경·반복 유료 요청으로 우회하지 않는다. **evaluate와 추가 유료 CLI는 이번 작업 밖이며 실행하지 않는다.**
