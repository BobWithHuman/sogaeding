# WP-HOOK-GW-01 별도 AI 검토

검토자: 구현 작성자 `/root`와 다른 AI 역할 `/root/hookgw_review`. 사람 개발자는 사용자 1명이다. 공식 독립 보안 진단이 아니다. 2026-10-16, 최종 독립 시험 직후 `04:10:12 UTC`, 인계 지문·마지막 차이 확인 `04:14:03 UTC`. 유료 모델 호출 0회.

**판정: 구현된 MCP 자동 연결·오프라인 집행 범위의 인계는 수용 가능. 전체 자유 개발 MVP 수용은 미충족이다.** 실제 의미 모델, interactive 설치 UX, 정상 native 편집/일반 개발 명령과 hook 프로세스 fail-open·공급망 잔여 확인이 남는다. 전역 DONE이나 보안 배포 승인을 내리지 않는다.

검토 범위: 작업팩13, AGENTS, with-human-dev의 역할·증거 기준 및 신규 `src/app/transparent/{engine,server,upstream,judge}.py`, `tools/hookgw_hook.py`, `tools/hookgw_prepare.py`, Compose와 실제 agentgateway 설정. 코드·관리 문서는 수정하지 않고 이 REVIEW만 작성한다. 기존 SPEC4/A/B 완료는 신규 경로 검증으로 대체 해석하지 않았다.

## 최초 발견과 조치 추적

| ID | 우선순위 | 최초 발견 | 영향과 필요한 조치 | 상태 |
|---|---|---|---|---|
| HG-R01 | P1 | `native_scope()`는 `command`만 검사하고 실제 `tool_input.workdir` 등 실행 위치를 검사하지 않음 | top-level hook cwd가 등록 경로여도 상대 `Set-Content`가 외부 workdir에서 수행될 수 있음. 실제 tool input schema의 허용 필드와 실행 위치를 검증해야 함. | 조치: 추가 필드·상대 shell 경로 거절. 순수 scope 재검증 및 unit PASS. 실제 native 정상 쓰기 한계 유지 |
| HG-R02 | P1 | 지원 쓰기에 신뢰 hook 소스와 기존 증거 경로가 포함됨 | `tools/hookgw_hook.py`를 덮어쓰면 동일 hook command의 다음 실행을 바꿀 수 있음. reviewed adapter/config/key 및 원증거를 일반 편집 경로에서 분리·보호해야 함. 같은 OS 사용자에 대한 비보장과 별도로 제품 자체 지원쓰기 경계가 필요함. | 조치: native/upstream에서 trusted product·원증거 경로 거절. 관련 unit PASS. OS sandbox 전체 보호 아님 |
| HG-R03 | P1 | `/authz`는 MCP 초기 metadata RPC 처리 전에 bound session을 요구함 | 새 connection은 session NULL. Codex가 첫 UserPromptSubmit 전에 initialize/tools/list를 수행하면 MCP startup 실패 가능. 유효 connection의 metadata와 실제 tools/call의 turn 요구를 구별해야 함. | 조치 및 실제 gateway initialize-before-turn PASS. 실제 CLI MCP 초기화 후 r12~14 동작 확인 |
| HG-R04 | P1 | 승인 소비/forward는 다른 READY·EXECUTING·UNKNOWN 호출 gap을 재검사하지 않음 | CONFIRM 후보 둘을 승인·소비하면 정상 authorize의 PRIOR_RESULT_UNOBSERVED 직렬화 규칙을 우회할 수 있음. 승인/forward 경로에서도 최신 source·turn·상태와 경쟁 조건을 검증해야 함. | 조치: 승인/소비/forward 트랜잭션 내 gap 검사. 승인 후보2개·실제 thread contender unit PASS |
| HG-R05 | P1 | authorize 최종 UPDATE의 `state='ANALYZING'` CAS 성공 여부를 확인하지 않음 | 다른 인스턴스/재시작에 따른 UNKNOWN 상태변경으로 UPDATE 0행이어도 ALLOW를 반환할 가능성. 원자 예약 성공을 확인한 뒤 반환해야 함. | 조치: rowcount 1 요구. 분석 중 강제 UNKNOWN 전환 시 RESERVATION_LOST, ALLOW 미반환 unit PASS |
| HG-R06 | P2 | 의미 snapshot에 현재 사용자 prompt만 포함, 이전 trusted turns는 제외 | 앞선 사용자 발화를 참조하는 일반 후속 대화는 문맥 부족. 독립형 후속 요청의 시험을 일반 대화 지원 전체로 확대하면 안 됨. | 조치: chronological trusted user turns와 latest index 포함. unit 및 실제 CLI 후속 turn 연결 PASS. 의미 정확도 미검증 |
| HG-R07 | P2 | grant에 native Read/Glob/Grep가 있으나 native_scope가 모두 거절함 | 설치된 실제 tool 이름·허용 manifest·지원표를 일치시켜야 함. | 조치: prepare 소스에서 제거, 현행 구성 동기화와 grant fingerprint 무효화·r15~17 재검증 확인. private runtime ACL 이후 원문 재접근/권한변경하지 않음 |
| HG-R08 | P1 | MCP transport timeout/HTTP 오류/파싱 실패를 JSON-RPC error로 합치고 결과 관측이 OBSERVED_ERROR로 종료될 수 있음 | upstream write/fsync 이후의 응답 유실·오류는 실행 효과 UNKNOWN이다. 오류 메시지를 관측했다는 사실로 불명확 실행을 종료하면 후속 위험 호출 gate를 해제할 수 있음. transport/실행 불명확 오류는 UNKNOWN을 유지해야 함. | 조치: machine-auth transport attestation 필수, 실패/미관측은 UNKNOWN. unit 및 실제 upstream-down503/효과불변/후속DENY PASS |
| HG-R09 | P2 | upstream은 최초에는 O_NOFOLLOW만 사용하고 regular-file/hardlink 여부 미검사 | 기존 hardlink나 특수 파일은 symlink 방어와 다른 경계. truncate 전 fstat/파일형식·링크수 검증 필요. | 조치: upstream truncate 전 fstat/nlink 검사, unit에서 바깥 파일 불변 PASS. host stat·Windows 특수경로 거절 소스도 추가 확인 |
| HG-R10 | P2 | 런처 CLI overlay가 기존 hooks 배열을 대체할 가능성 | 기존 개인 설정 파일 보존과 런타임 hook 보존을 구분해야 함. 실제 merge 의미 또는 충돌 거부 확인 필요. | 조치: 기존 hook 설정 발견 시 시작 거절, 보안/cwd/profile override 인자 거절. 기존 hook 충돌 unit PASS. 사용자 실제 설치 UX 미검증 |
| HG-R11 | P1 | hook timeout 120초보다 handler의 분석/CONFIRM/poll 최악 대기합이 길 수 있음 | send25초 + 승인poll90초 + 마지막send25초는 140초. Codex hook timeout이 handler의 deny보다 먼저 발생해 native fail-open 가능. handler 총deadline/상위 timeout 간 여유 검증 필요. | 조치: 승인poll45초/개별poll5초로 축소. 소스상 상위120초 내 여유 확보. native hook 자체 fail-open은 해소되지 않음 |
| HG-R12 | P2 | launcher 보안 인자 필터는 `-cfeatures...`, `-C..` 결합형 및 실제 긴 dangerously-bypass flag를 놓칠 수 있음 | 검토되지 않은 보안/작업경로 override를 거절한다는 구현 계약과 검사 범위를 일치시켜야 함. 이는 사람이 launcher에 준 args 경로이며 agent에게 재실행 권한이 있다는 뜻이 아님. | 조치: prefix/short 결합형 거절. 5개 실제 인자 형태 unit 및 최종 독립41시험 PASS |

HG-R01/R02 최초 소스 재현: bundled Python에서 `native_scope(Path.cwd(), 'Bash', {'command': "Set-Content -LiteralPath 'proof.txt' -Value 'x'", 'workdir': 'C:/Windows/Temp'})` 및 `Set-Content -LiteralPath 'tools/hookgw_hook.py' -Value 'x'` 검사 모두 예외 없이 통과했다. 실제 Set-Content나 외부 파일 쓰기는 실행하지 않았다. 이 재현은 scope 함수만 검증하며 의미 모델이 해당 후보를 ALLOW했다는 뜻이 아니다. 첫 명령의 PowerShell quoting 실패 뒤 here-string으로 다시 수행했으며 유료/네트워크 호출은 없었다.

## 현재 수용 한계

`artifacts/20261016-hook-gw-dev/native-CAPABILITY.md`와 실제 probe 설명을 확인했다. 실제 CLI UserPromptSubmit/PreToolUse/PostToolUse 및 follow-up turn, 명시 deny의 효과 0은 관측됐지만, native hook 프로세스 crash·timeout·malformed JSON은 **fail-open**이다. 정상 shell/file write는 현재 설치 CLI 자체 read-only 정책으로 차단돼 성공하지 않았다. probe의 trust 우회 옵션은 테스트용이며 제품 설치 검증이나 정상 권한 확대의 근거가 아니다.

따라서 native 전 경로 fail-closed, 정상 자유 개발 편집 완료, 사용자 실제 LIVE 의미 정확도, Windows interactive TUI 및 MCP hook end-to-end 연결은 이 중간 검토에서 PASS하지 않는다. 실제 agentgateway의 body/extAuthz/upstream 효과 및 신규 offline 시험은 작성자의 최종 명령·결과와 source snapshot을 받은 뒤 확인한다. 분석 실패/공격 미시도는 공격 식별 PASS가 아니다.

## 재진단

작성자가 최초 발견 후 수정한 코드와 `engine-first.txt`의 19개 시험 PASS, `gateway-first.json`의 실제 agentgateway 25개 확인을 읽었다. 이 gateway 검증은 합성 trusted adapter 이벤트와 scripted observation을 사용하며 의미 모델 정확도나 실제 CLI 통합 전체의 증거가 아니다. 새 connection의 initialize-before-turn, 정상 실제 read/write, args 변경·재전송·공격 후보 DENY/효과0, source 결합·후속 요청, public authz 차단·본문크기413 확인이 포함된다.

검토자는 별도로 `docker compose run --rm --no-deps dev python -m pytest tests/hookgw -q -p no:cacheprovider`를 실행했다. 최초 sandbox 연결은 Docker pipe permission denied로 미실행됐고, 같은 명령의 정식 sandbox 승격은 승인돼 exit 0, **33 passed in 0.86s**를 반환했다. 컨테이너 `with-human-dev-run-082e49c9e7cf`, 실행 직후 확인 시각 `2026-10-16 03:37:19 UTC`. 이 시험은 합성 관측/격리 임시 DB·파일만 쓰며 실제 모델과 기존 키/DB/예산을 사용하지 않는다. 자동 승인 심사의 거절은 없었다.

새 grant/schema/UNKNOWN 보완 후 동일 명령을 독립 재실행해 **35 passed in 0.75s**(컨테이너 `with-human-dev-run-f2372615ca5a`, 직후 `03:55:41 UTC`)를 확인했다. 최종 import 격리와 launcher flag 보완 후 마지막으로 같은 명령을 실행해 **41 passed in 1.31s**, exit0(컨테이너 `with-human-dev-run-923929b32660`, 직후 `04:10:12 UTC`)를 확인했다. 앞선33/35와 중복이므로 합산하지 않는다.

41개 독립 시험 당시 기준은 `runtime-install-verified-source/manifest.json`, 지문 `2173e19a925d92b65e90469e94cfa23f2b1784af5d1a254b6255560d316a2bcf`였다. 당시 신규 제품·hook 도구·시험·스크립트·gateway·Compose30개 코드/구성을 현재 파일 SHA256와 대조해 차이0을 확인했다.

**최종 인계 기준**은 [final-index.json](C:/sogaeding/artifacts/20261016-hook-gw-dev/final-index.json)과 [handoff-final-source/manifest.json](C:/sogaeding/artifacts/20261016-hook-gw-dev/handoff-final-source/manifest.json), `04:13:05.288104 UTC`의 **163파일 / fingerprint `2e89504650534bbec1acefe4d78e3796208ca30c38430ba240cb5855413c68e2`**다. 최종 manifest의 `src/`·신규 hook 도구/시험/스크립트·gateway·Compose53개 파일을 현재 SHA256와 읽기 전용 대조했고 차이0이었다. 이는 163개 전체의 보안 전수 진단이나 binary 재현 빌드 확인이 아니다.

그 뒤163개 전체의 바이트를 대조했을 때 차이는 SPEC5 문서1개(`docs/mvp/08_transparent_hook_gateway_spec5.md`)였고 제품 코드 차이는 없었다. 작성자가 예고한 role-volume/최종 artifact 경로 문구 정합 보완이며 위2e8950 지문은 그 직전 문서 시점을 보존한다. 최종 인덱스는 이 문서 후속 차이를 별도 snapshot 또는 doc-only delta로 구별해야 한다. 이 차이로 제품 시험 PASS 범위를 늘리지 않는다.

**문서 동기화까지 포함한 최종 지문**을 추가 확인했다: `04:17:33.417252 UTC`,163파일, **`c7f48e7c27bf5a54c36094262ac2b084d59c076dcffcdb37879789798a3e6f48`**, [docsync-final-source/summary.json](C:/sogaeding/artifacts/20261016-hook-gw-dev/docsync-final-source/summary.json). 최종 종합 참조는 [handoff-index.json](C:/sogaeding/artifacts/20261016-hook-gw-dev/handoff-index.json)이다. 이전 final-index와2e8950 snapshot을 보존하며 SPEC5 문서1개 delta만 연결했다. 제품 코드/구성 변화가 없어 반복 시험·유료 호출은 하지 않았고 기존 검토 판정은 유지한다.

앞선 시험 snapshot과 최종 인계의 차이는 안전 fixture 결과 파일, `scripts/hookgw.ps1`의 Python entrypoint `-I` 적용, `hookgw_prepare.py`의 정확한 인접 prepare_tls importlib 로딩, launcher 공백이었다. 차이를 직접 읽었고 변경된 prepare helper는 bundled Python `-I tools/hookgw_prepare.py --help` exit0으로 확인했다. PKI 생성·유료 호출은 하지 않았다. 기존41시험 전체를 이유 없이 반복하지 않았으며, 실제 `product-start-isolated`의 `-I` 포함 PS5.1 start exit0과 lint-complete PASS를 확인했다.

`native-product-final-normal-r12`, `native-product-final-attack-r13`, `native-product-final-followup-r14`의 원 summary와 hook 진단을 확인했다. 실제 설치 Windows CLI→제품 hook→실제 TLS agentgateway→안전 file upstream에서 정상 파일의 변경 hash가 기대값과 일치했고, 공격 후보는 실제 시도 후 Pre DENY로 차단돼 금지 파일이 전후 모두 없었다. 후속 turn은 같은 CLI session에서 다른 turn ID와 2회의 정상 변경으로 연결됐다. local scripted actor 및 scripted judge이므로 **IPI 의미 인식률이나 실제 모델 수용 PASS가 아니다**. r12~14는 transport attestation 수정 후 재실행 증거다.

추가 장애 증거: `authz-down.json`에서 실제 gateway403/정상 파일 hash 불변, `upstream-down-r2.json`에서 gateway503/hash불변/UNKNOWN 유지/후속 위험 DENY를 확인했다. upstream-down 최초 실행은 health TLS EOF로 fault 경로에 이르지 못했으며 최초 실패로 보존됐다. `tls-negative.json`은 untrusted CA와 wrong hostname 2개 negative를 확인한다(health 포함 check3). 전체 TLS negative·키수명 검증을 완료한 것으로 확대하지 않는다.

현행 구성 `r15~17` 및 최종 bundle/개인 ACL 배치 `native-product-bundle-normal-r18d`/`native-product-bundle-attack-r19`의 summary/보고서를 확인했다. r18d 정상 파일 변경 hash는 기대값과 일치했고 r19는 실제 위험 후보 DENY와 금지 RPC/파일0이었다. r18/r18b의 빈 DACL, r18c의 Windows ACL→Linux UID 읽기 실패는 준비 실패로 보존됐으며 차단 PASS가 아니다. 수정 후 private 사용자/SYSTEM ACL과 역할별 UID10001 Docker volume을 유지했다. 후속 turn의 r17은 bundle 배치 전 동일 프로토콜 소스 검증임을 구별한다.

최종 `-I`와 정확한 adjacent helper import, workspace와 분리된 frozen `/product` bundle, 역할별 volume installer를 읽었다. importer-shadow 음성시험이 최종41에 포함됐고 실제 PS5.1 `product-start`와48파일 `runtime-install-verified`의 exit0을 확인했다. installer는 기존 파일 hash가 다르면 교체하지 않는다. 새 역할 파일/소스만 설치하며 기존 F3 key/DB/예산을 초기화하지 않는다. 실제 native observer 시험을 모든 import-shadow 조건의 독립 end-to-end 증거로 확대하지 않는다.

최종 인덱스는 frozen bundle29파일이 현재 제품 소스 바이트와 일치, bundle manifest SHA256 `f4a1f8eb1369cf0bbee235e819823374e1e8c07ba0ceb3605ea688052a1c66cf`를 기록한다. control/upstream 제품 `/product`와 역할별 `/runtime`은 새 named volume의 read-only mount, 서비스 데이터 volume만 쓰기 가능하다. Windows bind의 root0600→UID10001 읽기 실패를 권한 공개로 해결하지 않고 새 역할48파일 전용 volume 소유권/0600으로 조치한 이력과 실제 정상/차단 재검증을 확인했다. 호스트 새 키의 사용자/SYSTEM ACL을 유지한다.

동일 인덱스의 최종 기본 제품 TLS health는 `judge_mode=UNAVAILABLE`, 개발 AI 유료0, offline fixture 서비스는 정지·volume 보존이다. 기존 judge는12/24, DB SHA256 `2c1e21be30a4a1c30f9ff2d21fa5c4678af9fe8751895663110ebd2708f1e6ec` 읽기 전용 보존 기록을 확인했다. 검토자가 키나 기존 DB 원문을 읽거나 변경한 증거로 표현하지 않는다.

회귀는 최종 통합 실행의 `98 passed, 8 setup errors`를 전체 PASS로 보지 않았다. 별도 `acceptance-isolated.txt` **20 passed**, `peer-isolated.txt` **8 passed**를 확인했다. 동시 session fixture의 공용 포트 충돌이 합친 명령의 실패 원인으로 추정되나 최초 실패 stderr가 수집되지 않아 배타적 원인을 확정하지 않는다.

별도 scope 재진단에서 현재 hook 소스에 대해 검토자가 bundled Python `-B`로 순수 scope 함수만 재호출했다. extra workdir는 UNSUPPORTED_NATIVE_ARGUMENTS, 상대 shell 경로는 ABSOLUTE_SHELL_PATH_REQUIRED, trusted hook 절대경로 쓰기는 TRUSTED_PRODUCT_OR_EVIDENCE로 거절됐다. 정상 root 내부 일반 파일의 절대 Set-Content 문법은 scope 검사 통과했다. 실제 파일 쓰기는 실행하지 않았다. CLI가 workdir를 hook에 생략할 수 있어 상대 shell 경로 거절이 필요한 점도 작성자에게 알렸다.

최종 RESULT/SPEC5/README/SUPPLY_CHAIN을 읽었으며 변경 목적·실제 명령/효과·최초 실패/조치·남은 미지원·유료 미실행이 구별돼 있다. root의80개 core 시험, 별도20/8개 회귀와41개 신규 시험은 중복 범위가 있어 단순 합산하지 않는다. Ruff PASS와 Bandit 최종5개 경고(High0/Medium2/Low3)도 clean/security 전수 PASS로 해석하지 않았다. **수정된 구현의 한정된 인계 수용과 전체 MVP 수용 미충족을 구별하는 최종 판정**이다.

## 가이드·공급망 및 남은 수용 범위

`GUIDE_APPLICABILITY.md`의 R1/G1/G2/G3/G4 원문 페이지·해시/추출·설계20/약점49 적용성 추적을 확인했다. 이 검토가 원문 전체 재독 또는 49개 진단 PASS를 뜻하지 않는다. 새 native 명령/경로/역할·저장·전송 경계가 기존3도구의 N/A 결론을 그대로 계승하지 않도록 별도로 검토했다. 단일 사람 개발자와 AI 역할 분리, 관리 장부 읽기 전용, 필수 P0 미면제와 C/D 전체 비선행조건 원칙을 유지한다.

`SUPPLY_CHAIN.md`와 dependency.lock은 공식 agentgateway1.6.0 digest/source revision/Apache 라이선스, 설치 Codex0.154.0 hash를 구별해 기록한다. Docker Scout image CVE 조회는 로그인 요구로 실패했으며 clean scan이 아니다. 공개 고정 Cargo.lock의 OSV 조회는 4패키지/12 advisory 레코드 매칭(중복/미유지보수 포함)이고 실제 binary 포함·feature closure·전체 도달성은 미확정이다. 특히 rustls0.23.45 권고는 patched 이미지/검증 빌드와 재진단이 남는다. 종합 SCA PASS나 publisher 서명 확인을 승인하지 않는다.

전체 제품 수용의 미해결 항목은 다음과 같다.

- native hook 프로세스의 crash/timeout/malformed 출력은 실제 fail-open이다. 실제 gateway의 실패 차단으로 native를 포함한 호스트 전체 보호를 주장할 수 없다.
- 정상 native 편집/셸은 이 설치 CLI의 자체 read-only/명령 정책으로 성공하지 않았다. native write의 typed completion도 실제 입증되지 않았으며 불명확 결과는 UNKNOWN으로 유지한다.
- 허용 shell은 단순 Get-Location 및 절대 LiteralPath 파일 명령뿐이다. 일반 `python -m pytest`/`git`/`rg`와 arbitrary shell·write_stdin 재입력·hosted 도구·다른 MCP는 평소 자유 개발 전체 수용의 남은 범위다.
- 실제 user TUI의 hook 정의 신뢰/기존 도구 승인 UX와 유료 실제 의미 모델은 미실행이다. synthetic actor/judge 성공을 F3 의미 정확도나 LIVE 공격 식별 PASS로 계산하지 않는다.
- 출처16개·trusted 사용자 대화16KB·24시간 세션·연결 한도 등은 fail closed 제한이다. 장기 무제한 개발 세션 기능은 아니다. 새 auth rate 제한은 전역이므로 인증되지 않은 로컬 요청이 유효 human/machine의 가용성에 영향을 줄 수 있다.
- frozen bundle·역할 volume·최신 설치 시작의 실행 증거는 최종 RESULT와 위 재진단에 연결했다. 같은 OS 사용자/관리자·검사 후 호스트 파일 변경 경쟁에 대한 강제 격리를 보장하지 않는다.
