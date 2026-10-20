# WP-HOOK-GW-02 단계 A 별도 AI 검토

검토자 `/root/hookgw02_review`, 구현자 `/root`와 다른 AI 역할. 사람 개발자는 사용자 1명이며 공식 독립 보안 진단이 아니다. 작업팩14의 A만 검토한다. 유료 actor/judge 요청은0회다. 관리 계획/장부·엔진·기존 키/DB/예산은 검토자가 변경하지 않았다.

**판정: 작업팩14 단계 A의 좁은 API 실행 준비 인계는 수용 가능하다. 실제 사용자 정상 작업과 전체 자유 개발 MVP 수용은 미완료다.** HG02-R01의 기존 literal 마스킹 경로 보존을 수정·재진단했다. 전역 DONE/전체 제품 완료나 보안 배포 승인을 내리지 않는다.

## 검토 범위와 기준

`START_PROMPT.md`, 작업팩14 A/B/C, 현재 AGENTS, with-human-dev의 역할·증거 지침, 작업팩13과 이전 WP-HOOK-GW-01 RESULT/REVIEW를 대조했다. 작성 허용 범위의 `tools/hookgw_launch.py`, 신규 preflight helper, `scripts/hookgw_connect.ps1`, LIVE Compose, 관련 시험·README/SPEC5 사용설명을 읽었다. 개인 전역 로그인·config/auth/CA 보존, actor와 Control judge 인증 분리, 환경 키·지정 모델, 준비 실패 시 모델 미시작, 기존 정책/출처/ref/UNKNOWN 통제 보존이 이번 기준이다.

공식 OpenAI [구성 참조](https://learn.chatgpt.com/docs/config-file/config-reference)의 custom provider `env_key/base_url/wire_api/requires_openai_auth` 및 [인증 설명](https://learn.chatgpt.com/docs/auth)의 공유 로그인 캐시를 대조했다. 전역 `codex login`으로 인증을 바꾸는 방식은 이번 요구에 맞지 않는다. 해당 문서만으로 설치된 CLI의 실제 인증 선택을 단정하지 않고 로컬 요청을 별도로 확인했다.

필수 가이드 적용은 이전 원문 추적의 G2 시스템 명령·민감정보/오류 처리, G3 PDF507~511(SR1-4·SR2-1/5/7/8·SR3-1), G4 PDF37~39 및 G-08 진단·조치·재진단 기준을 이어받는다. 좁은 인증/설정 변경의 검토이며 설계20·약점49 전체 PASS, 공급망 clean, 공식 조치율을 선언하지 않는다.

## 발견·최초 실패·재진단

| ID | 내용 | 상태 |
|---|---|---|
| HG02-R01 | RO `/runtime`에 judge key mountpoint가 없어 최초 LIVE 준비가 실패했고, 우회로 `RUNTIME_DIR=/`를 지정하면 공통 `mask()`가 기존 `/runtime/human.token`의 literal 값을 찾지 못한다. generic 긴 토큰 regex는 Unicode 인접 문자열에서 같은 보호가 아니다. | 조치·재진단 완료. 실키 없이 `가`+합성48문자+`나`에서 literal redaction=true/generic=false를 독립 확인했다. 최종은 새 role volume에 빈 mountpoint만 준비하고 기존 `/runtime`과 literal 마스킹을 유지한다. 실제 preflight와 아래68시험이 통과했다. |
| HG02-R02 | 최상위 설정만 보면 활성/중첩 profile의 hooks·강제 인증·예약 provider와 legacy managed defaults를 숨길 수 있다. | API 경로에서 중첩 profile 충돌과 managed defaults를 거절하도록 보완했고 관련 독립 회귀가 통과했다. 개인 sandbox/승인 정책은 덮지 않는다. |
| 준비 실패 보존 | 최초 API fixture 실패, legacy `profile="personal"` 추가 시험의 CLI 설정 오류로 요청0/exit1. | 원기록 보존. 설치 CLI0.154.0이 legacy profile 문법을 지원하지 않는 설정 실패를 인증 실패나 공격 차단 PASS로 바꾸지 않았다. 정상 fixture는 별도로 재실행 PASS다. |

## 독립 실행과 관측

검토자가 `docker compose run --rm --no-deps dev python -m pytest tests/hookgw -q -p no:cacheprovider`를 직접 실행했다. 기본 sandbox의 Docker pipe 접근은 denied로 미실행됐고 정식 승격은 허용됐다. 컨테이너 `with-human-dev-run-40edd4248439`, **63 passed in2.92s**, exit0, 직후 `2026-10-16 05:02:01 UTC`. 이 수치는 기존 hookgw41개와 신규 준비/인증 시험을 포함하므로 이전 회귀와 단순 합산하지 않는다. [독립 기록](C:/sogaeding/artifacts/20261016-hook-gw-02-review/independent-checks.json)에 명령·코드 SHA를 남겼다.

실제 설치 Windows Codex도 가짜 키와 localhost Responses fixture로 독립 실행했다. [independent-api-auth.json](C:/sogaeding/artifacts/20261016-hook-gw-02-review/independent-api-auth.json), `05:05:16~21 UTC`, CLI exit0. `/v1/responses` 정확히1건, 지정 모델 `gpt-5.6-luna`, Authorization은 가짜 환경 키와 일치하고 가짜 ChatGPT 저장 자격과 불일치했다. 격리 auth/config hash는 전후 같다. 설치 exe SHA256은 `be96b992178b1e467c225800da0d65f2c86d5eba1ef0b14632f65db381cbdfde`다. 기본 sandbox의 임시 디렉터리 쓰기 실패는 요청 전 미실행이며, 정식 승격 후 같은 안전 시험이 통과했다. 자동 승인 심사의 거절은 없었다. 실제 키·개인 auth를 fixture로 복사하지 않았고 raw 요청/원문/키를 저장하지 않았다.

위 fixture는 제품 provider 설정 생성 함수를 쓰되 목적지만 test-only localhost로 치환하고 합성 무도구 요청을 준다. **제품 launcher/TUI·hook 신뢰·gateway·실제 의미 모델 전체 성공을 뜻하지 않는다.** 제품 코드에는 endpoint override나 자동 프롬프트/일괄 시나리오 입력을 넣지 않았다.

작성자의 `core-regression.txt` **108 PASS/58.72s**, 기존 `regression-a.txt`59 PASS, 실제 PS5.1 `ps51-preflight.txt`를 확인했다. preflight는 actor의 개인 저장 인증 CHATGPT와 이번 ENV_API_KEY 방식을 구별했고, 모델/endpoint·CLI 버전/hash·설정파싱·hooks 활성·application CA/TLS·LIVE_USER·각 키 가독·기존 judge12/24·남은12·DB hash불변을 별도로 보고했다. 키 유효성과 모델 접근은 NOT_VERIFIED_NO_REQUEST, `/hooks` 정의 신뢰는 미검증이다. 실패 또는 준비 전용 모드에서 `/connect`·모델 subprocess가 실행되지 않는 회귀를 확인했다. preflight 성공을 의미 판단이나 공격 식별 PASS로 해석하지 않는다.

HG02-R01 수정 후 검토자는 같은 Docker 시험 명령을 독립 재실행해 **68 passed in2.94s**, exit0을 확인했다. 컨테이너 `with-human-dev-run-9ee0975305c8`, 직후 `05:10:24 UTC`. 앞선63과 중복이므로 합산하지 않는다. 빈 mountpoint 재호출·기존 nonempty 파일 보존/거절·installer 호환, 기존 Unicode 인접 literal redaction, workspace의 Docker 실행파일 선택 거절이 포함된다.

최종 소스는 [final-source/summary.json](C:/sogaeding/artifacts/20261016-hook-gw-02-a/final-source/summary.json)의 **167파일 / `a02fb0c3905c9cb934399c1a9e0d0925d48c5c58dee420a5a753a3278a8225f0`**다. 검토자가 `05:10:56 UTC` 전체 manifest와 현재 파일 SHA256을 읽기 전용 대조해 차이0을 확인했다. [최종 독립 확인](C:/sogaeding/artifacts/20261016-hook-gw-02-review/independent-final-checks.json)에 남겼다. 변경 전163개 중 기존 파일 변경은 README/SPEC5 사용설명/connect/launch/installer의5개이며 신규 helper2개·관련 시험2개가 추가됐다. 엔진/정책·관리 문서/장부는 이 변경에 포함되지 않았다. 이는167개 전수 보안 진단 PASS를 뜻하지 않는다. 최종 Ruff 기록은 PASS다.

`tools/hookgw_key_mountpoint.py`는 새 control role의 기존9파일을 확인·해시 비교하고 `O_CREAT|O_EXCL`로 빈 regular file만 추가한다. existing nonempty/symlink/hardlink를 교체하지 않고 키를 읽거나 복사하지 않는다. 작성자의 `empty-mountpoint-prepare.txt`는 기존9파일 불변·키복사false이며 `ps51-preflight-final.txt`는 `RUNTIME_DIR=/runtime`, 실제 기존 human literal 마스킹true, key readable, LIVE_USER, budget12/24·같은DB해시를 보고했다. 새 helper와 installer의 빈 파일만 허용하는 호환 보완은14 A의 키 가시성/준비에 필요한 좁은 변경이다. preflight는 이 쓰기 준비를 자동 실행하지 않는다. 기존 서비스 PKI와 엔진 코드/정책은 바꾸지 않았다.

완성된 [RESULT](../20261016-api-preflight/RESULT.md)와 [final-index.json](C:/sogaeding/artifacts/20261016-hook-gw-02-a/final-index.json)을 마지막으로 읽었다. 좁은 installer 호환 이유·중간 RUNTIME_DIR 대안의 마스킹 문제와 철회·최종 LIVE Compose 기준선 동일·개인 config/auth 및 기존 judge key hash3/3불변 보고·기존 budget12/24·유료0·실제 모델 미실행을 구별한다. 사용자 최소 명령은 현재 머신에서 LIVE 서비스 준비→`-Api -Model gpt-5.6-luna -Preflight`→직접 `codex`이며 준비 검사를 넘기는 우회가 없다. 첫 `/hooks` 신뢰와 정상 요청1건, 이력/내용/hash/시각 대조, 실패 시 중단 조건이 기재돼 있다. 별도 opt-in mountpoint 준비는 현재 머신에서 이미 완료됐으며 preflight와 동시 실행을 거절한다. 최종 사용자 절차가 준비 검사 성공을 의미 모델 성공이나 전체 MVP 수용으로 바꾸지 않음을 확인했다.

## 남는 수용 범위

사용자는 지정 모델 API 모드로 직접 `codex`를 열고 `/hooks`의 정확한 정의를 검토·신뢰한 뒤 합성 notes 읽기·이번 표식이 있는 정상 요약 쓰기1건을 시험해야 한다. 이번 session/turn/call의 판정·실행 상태와 실제 파일 내용/hash/수정시각을 연결하며 기존 파일 존재만으로 성공을 세지 않는다. 첫 ANALYSIS_UNAVAILABLE/UNKNOWN·turn 누락·예상 밖 native 동작은 중단 조건이다. actor 비용은 judge의 기존24요청 예산과 별개다.

정상 native 편집/일반 개발 명령·native hook 프로세스 사망/timeout/malformed의 fail-open·interactive 신뢰 UX·사용자 실제 actor/judge 의미 검증·공급망 권고/도달성 확인은 남는다. 원문/ref 검증·보안 실패 차단·원자 예약·예외 CONFIRM/UNKNOWN 통제를 끄지 않았으며 기존 scripted/MCP 시험을 전체 자유 개발 완료로 확대하지 않는다. 단계 A와 사용자 첫 정상 성공은 전체 MVP/C/D 완료가 아니다.
