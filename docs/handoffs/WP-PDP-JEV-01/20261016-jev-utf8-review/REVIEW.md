# T-JEV-05 UTF-8 inspect 수리 별도 AI 검토

2026-10-16. with-human-dev를 적용한 작성자와 분리된 AI 검토다. 사람 개발자는 사용자 1명이며 공식 독립 보안 진단이 아니다. **최소 PowerShell 수리 범위 수용 가능 / 미해결 차단 finding 0. 최종 RESULT·preflight/보존 증거 대조 완료.**

UTF8_INSPECT_REPAIR_START_PROMPT 전체와 최신 AGENTS, 현재 스크립트/동결 helper 및 이전 T-JEV-03/04 인계를 읽었다. 실제 키 파일은 직접 열거나 stat·hash하지 않았고 작성자의 안전한 metadata/ACL 전후 증거만 읽었다. 제품 서비스·Docker 평가·실제 모델·전역 로그인/설정/CA·DB/원장 변경은 검토자 0이다. 허용된 자체 증거와 이 REVIEW만 작성했다.

## 최소 변경과 보안 계약

수리는 scripts/jev_eval.ps1에서 모든 신뢰 Python 호출에 `-X utf8 -I`를 고정하고 native 출력 캡처와 기존 ASCII stdin의 인코딩을 UTF-8로 일시 설정한다. Console OutputEncoding과 PowerShell OutputEncoding은 성공·실패 경로 모두 finally에서 원래 값으로 복원한다. 환경변수나 전역 Python/PowerShell 설정을 저장하지 않는다. native stderr는 원문을 출력하지 않으며 시작 실패·비정상 종료·빈 출력·잘못된 JSON을 stage/code 고정 값으로 구분한다. JSON 객체 검증 뒤 성공 원문을 그대로 반환해 자료/질문을 재직렬화하거나 교체하지 않는다. 숨긴 입력 실패도 KEY_INPUT/HIDDEN_INPUT_FAILED로 처리한다.

키 입력은 기존 숨긴 SecureString→일시 BSTR→ASCII stdin 경로를 유지하고 argv/로그/프롬프트에 키를 넣지 않는다. 현재 사용자 명령인 inspect/preflight는 입력을 요청하지 않는다. evaluate의 기존 confirm-send/정확 manifest/4요청/256000 예약 gate·원장 재시도 거부는 그대로이며 실제 evaluate는 여전히 미승인이다. Python helper/PDP·질문·임계치·동결 자료를 바꾸거나 검증을 끄는 migration은 필요하지 않았다.

## 독립 실제 Windows 시험

[독립 시험 코드](../../../../artifacts/20261016-jev-utf8-review/run_independent.py)는 제품 스크립트 복사본과 가짜 helper만 사용한다. 실제 Windows PowerShell **5.1**에서 기본 CP949를 설정한 native 시험 **12/12 PASS**다. [최종 원증거](../../../../artifacts/20261016-jev-utf8-review/independent-final.json)에 실행 스크립트 SHA와 각 케이스를 남겼다.

- inspect/preflight/collect/evaluate의 한국어·emoji·é·漢字를 ConvertFrom-Json으로 읽고 합성 stdout 원문의 UTF-8 SHA까지 일치했다.
- 모든 실제 fake Python 실행에서 utf8_mode=1/isolated=1, 준비/키 입력의 생성된 가짜 ASCII stdin 일치, 정확 evaluate argv와 무승인 evaluate의 helper 시도 0을 확인했다. 이 evaluate는 가짜 helper이며 Docker·모델을 실행하지 않았다.
- 정상/실패 후 Console CP949와 OutputEncoding 객체/코드페이지를 복원했다. 종료 오류·경고 stderr는 노출되지 않았고, malformed/빈 출력·숨긴 입력 취소는 원문 없이 고정 stage/code로 끝났다.

UTF8-R01/P2는 초안의 함수 local LASTEXITCODE가 native global 종료 코드를 가려 실제 프로세스가 실행됐는데도 PYTHON_START_FAILED로 오판한 문제다. global native code 추적으로 수정했고 재진단했다. UTF8-R02/P2는 exit0 malformed/빈 stdout을 그대로 넘겨 호출자의 JSON 오류에 원문이 섞이거나 무결과가 되는 경로였고 단일 JSON 객체 검증/고정 진단으로 수정했다. UTF8-R03/P2는 Read-Host 원문 예외였고 고정 숨긴 입력 오류로 수정했다. [발견·조치 기록](../../../../artifacts/20261016-jev-utf8-review/findings.json).

첫 sandbox PS 실행은 AuthorizationManager에 막혀 NOT_RUN 원증거로 보존했다. 전역 실행 정책을 바꾸지 않고 host 실행 권한으로 같은 격리 fixture를 검토했다. baseline-host 이름의 파일은 동시 편집 뒤 초안 r1을 실행한 증거임을 명시하며 원래 baseline으로 주장하지 않는다. 검토 mock의 SecureString 모듈 autoload 문제와 prepare/key의 복수 출력 기대값도 제품 오류와 구분해 수정·보존했다.

## 동결 상태와 가이드

[독립 동결 대조](../../../../artifacts/20261016-jev-utf8-review/frozen-check.json)는 실제 NONSECRET manifest/plan/disabled policy와 그 안의 **37개 소스 hash**만 읽었다. manifest `b542e3ee0cd8b8674f4679b735e8719d8dbe1f6737da75f20ac3d53a0116680f`, helper `6e271c33ca7ec71e930fcc776452105bca498c2f0184d36d7ab1263002b614ab`, plan hash와 모든 소스가 일치한다. 합성 2후보·상한4/256000·enabled:false를 유지하며 provider 원장/authorized-run/결과는 없다. 키 파일에는 경로 stat조차 하지 않았다. PS 스크립트는 기존 source_hashes 대상 밖이므로 이 최소 변경으로 동결 계약이 그대로 유효하다.

기존에 원 SHA/추출을 대조해 읽은 G2 PDF133/137, G3 PDF511, G4 PDF38의 오류 최소 공개·안전한 예외·중요정보·세션 통제를 적용했다. raw native/입력 예외→고정 진단, Unicode 자료의 정확한 보존→원문 SHA/동결 비교, 일시 설정→finally 복원, 비밀→숨긴 ASCII stdin/argv 비노출로 코드·실제 시험을 연결한다. 새 패키지/이미지/SDK/다운로드는 없다. 기존 설계20/약점49 적용성·미완료와 native/hook 사망/공급망 잔여를 보존하며 전수 PASS·정량 방어율을 선언하지 않는다.

## 최종 인계 대조

[최종 RESULT](../20261016-jev-utf8/RESULT.md)와 [index](../../../../artifacts/20261016-jev-utf8/final-index.json)를 전체 읽고 실제 증거와 대조했다. 최종 **201파일 SHA 불일치0**, fingerprint `dbdae09f5b787c5eafad4b58da43f54b0e0872f204c3d968645a6c65bf5cd1b0`이며 독립 시험 스크립트 SHA와 최종 스크립트가 같다. 이전200파일에서 실제 변경은 PS 런처·새 PS fixture·사용 설명 **3파일뿐**이고 Python/product 소스 변경0이다. 안전한 preservation before/after JSON map을 독립 비교해 metadata/ACL·공개 plan/manifest/policy·원장/승인run/결과 유무가 모두 동일함을 확인했다. 키 본문 불변을 해시로 증명했다고 확대하지 않는다. [최종 대조](../../../../artifacts/20261016-jev-utf8-review/final-comparison.json), [변경 경계](../../../../artifacts/20261016-jev-utf8-review/source-delta.json).

작성자의 실제 inspect-final-r3/direct-output-r3는 한국어·JSON·원계획 전체 동일/strict UTF8·stderr 없음·인코딩 복원을 기록한다. 최종 preflight는 ready_for_user_opt_in=true/default_enabled=false/live_authorized=false/paid_requests0이며 provider/model 접근은 NOT_VERIFIED_NO_REQUEST다. collect는 source 동일/NO_ATTEMPTS다. 작성자 native21/21과 관련 회귀105 PASS/4.92초·PS AST2개 오류0은 읽어 대조했으며 독립12건과 겹치는 검증 수를 합산하지 않는다. 사용자 기존 키/준비에 prepare/key/evaluate를 재실행하지 않은 점도 명시했다.

실제 TypeSafe 인증/모델 접근·정확도·IPI 식별 및 추가 사용자 CLI 성공은 NOT_RUN이다. 이 인코딩 수리나 preflight PASS를 실제 평가 실행 동의·공격 차단 PASS로 바꾸지 않는다. 사용자에게는 기존 키 재입력/prepare 없이 inspect와 모델0 preflight 명령만 안내해야 한다.
