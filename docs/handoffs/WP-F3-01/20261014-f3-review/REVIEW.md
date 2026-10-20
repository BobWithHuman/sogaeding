# WP-F3-01 별도 AI 검토

검토 run `20261014-f3-review`. 사람 개발자는 사용자1명이고, 이 검토자는 제품 작성자와 분리된 보조 AI다. 공식 독립 진단기관의 결과가 아니다. SPEC-4 / 정책 `mvp-2026-10-14-f3-v2` 후보를 검토했다. **최종 동등 제품의 독립 회귀47 PASS·장애 peer8 PASS·자체14 PASS, 세 제품 지적의 수정·재진단을 확인했다. 현재 검토 범위의 미해결 P1 제품 발견은 없다. 실제 judge·actor LIVE·ISSUE_SUMMARY 실제 의미 자동시연은 사용자가 직접 실행하기로 정한 범위이며 NOT_RUN이다. 전체 F3 수용·MVP 완료를 승인한 검토가 아니다.** 전역 DONE/MVP 상태를 판정하거나 plans/harness를 수정하지 않았다.

## 범위와 실행 경계

AGENTS, with-human-dev의 workflow/roles/evidence, START_PROMPT, 작업팩10 전체, 제품 방향09, ADR-M01, 기존 SPEC-3 권한/상태 계약 및 현재 기계 계약, 기존 WP-MVP와 HARDEN A/B RESULT/REVIEW를 대조했다. 작성자의 `semantic.py`, `judge.py`, `f3.py`, `repository.py`, `auth_audit.py`, Control/Gateway/UI/런처 변경을 먼저 읽었다.

자기 handoff와 `artifacts/20261014-f3-review/`만 작성했다. 제품·공통시험·계약·plans·harness·기존 원증거·runtime/DB의 변경은0이다. Docker 실행은 `compose run --rm --no-deps dev`의 별도 컨테이너와 자기 `/tmp` TLS/DB를 썼다. 기존 앱/B/F3 서비스 stop/restart/reset은0, 유료 API·Codex LIVE 호출은0이다. 현재 shared judge 또는 API키·role token·DB를 복사하거나 출력하지 않았다.

## 명령과 기준 소스

각 label의 `*-command.json`에는 실제 argv·UTC·exit·당시 source fingerprint, `.txt`에는 안전한 출력이 있다. 자기 fixture는 명령 전에 `*-review-fixtures/manifest.json`과 파일 사본으로 고정했다. `*-source/manifest.json`은 실행 당시 현재 작업트리다. **변경 전 재현 두 건은 argv에 명시한 작성자의 기존 동결 소스를 실제로 사용했으므로 당시 현재 작업트리 fingerprint와 혼동하면 안 된다.**

변경 전 실제 실행 소스: `artifacts/20261014-f3-01/f3-browser-profile-ca-source/source/`, 104파일, UTC `2026-10-14T07:00:33.826168+00:00`, fingerprint `d8937660b9d8e0542379890029247fdcbc7388f77c943cd34ef0991dd4b6ae27`. 첫 Python 재현에서는 이 snapshot의 src/contracts를 read-only mount했고, 첫 Firefox 재현에서는 이 snapshot의 web source를 읽었다.

최종 정본은 `artifacts/20261014-f3-01/demo-js-syntax-source/manifest.json`, 116파일, fingerprint **`5ca0e235d21adb5154f86fca71e46a63f3f83454bc8a5220a4906702ec76ea43`**다. core/peer 명령 직전의 자신의114파일 snapshot은 작성자의 `browser-b-regression-r1-source`와 같은 **`afef836d5780d69f140e0c2231de43b3058edc603b7124996ae1d5819177ae39`**였다. 최종116은 기존114파일 변경0이고 `scripts/f3_demo.ps1`, `tools/f3_demo.mjs` 두 viewer 파일만 추가됐다. 자체14 재진단은 최종116에서 실행했다. `final-full-check.json`은 current116·복사본116 모두 hash mismatch0, 114→116 기존파일 변경0을 확인한다. 새 viewer는 자신의 제품 회귀를 재실행해야 하는 Python 변경이 없고 실제 사용·실제 모델 자료로 열기는 NOT_RUN이다.

| label | 결과 | 범위 |
|---|---|---|
| initial-source-ref-reproduction | exit1 | Sandbox Docker pipe 접근 거부. 제품 시험은 시작되지 않음 |
| initial-source-ref-reproduction-r1 | exit1, 1 FAIL/6 PASS, 5.70초 | 변경 전 실제 source refs 부재인데 자동 ALLOW·댓글1 재현 |
| source-ref-correction | exit0, 7 PASS, 5.71초 | 수정 후 같은 fixture DENY·댓글0. source fingerprint `e52808366451350314cb2961d51edac78a564c217263c132474301abe18440e1` |
| auth-guard-review | exit1, 1 FAIL/2 PASS | 추가 검토 fixture의 블록 위치 오류(NameError). 제품 결함이 아님 |
| auth-guard-review-r1 | exit0, 9 PASS, 7.41초 | fixture 수정 후 실제 RequestGuard 인증 거부 기록·감사장애 fail-closed와 앞선7개 재진단 |
| guide-pages | exit0 | 원본5 PDF의 hash 일치, 관련 페이지의 기존 extraction 재사용·별도 보존 |
| unknown-ui-first | 실행기 미기동 | 검토자가 잘못 지정한 Node 실행파일 경로. source/fixture snapshot은 보존, helper가 launch 전에 예외 종료하여 command.json 없음 |
| unknown-ui-r1 | exit1 | Sandbox Firefox 신규 프로필 기동 실패. 제품 DOM 시험 미실행 |
| unknown-ui-r2 | exit1, assertion FAIL | 변경 전 Firefox DOM에 UNKNOWN인데 실제 댓글 효과0 표시 재현 |
| unknown-ui-correction | exit0, PASS | 같은 Firefox DOM fixture에서 실제 효과 불명 문구 확인 |
| adapter-budget-review | exit0, 2 PASS, 1.61초 | 외부0 SDK spy로 A/B 입력·전송 옵션·usage 확인, 새 adapter에서도24시도 한도 보존 |
| prompt-binding-first | exit1, 1 FAIL | current 프롬프트 버전 변경 후 구분석 reserve·댓글1 재현 |
| prompt-binding-correction | exit0, 1 PASS, 0.92초 | 같은 변경에서 ANALYSIS_STALE·댓글0·추가 judge0 |
| final-core | exit0, 47 PASS, 60.86초 | backend/transport/web/acceptance와 F3의 기존30+fake17. MCP 공통 경로와 direct repo fake 의미시험을 구분 |
| final-peer | exit0, 8 PASS, 33.21초 | 실제 MCP/TLS fault peer·취소·receipt 복구 회귀 |
| final-own | exit1, 13 PASS/1 FAIL | model 변경을 cachedcheck에서 더 일찍 거부하는 정상 제품 동작을 fixture가 예외로 잘못 취급 |
| final-own-r1 | exit0, 14 PASS, 10.25초 | cache 또는 reserve의 안전 거부를 허용한 같은 계약 fixture. 모든 추가 유료 호출0 |
| final-source-verify / final-source-116-verify / final-doc-browser-verify | 각각 exit0 | 114/116 실제파일·복사본 일치, 기존114 변경0, 00~07 역사 본문 보존·작성자 B8개 원증거 확인 |

중간 실패는 최종 결과로 덮어쓰지 않았다. 서로 다른 범위의 pytest 수를 전체 수용시험 수나 모델 방어율로 합산하지 않는다.

## 발견·조치·재진단

**R-F3-001 / P1 / 정탐·수정 후 제거 확인.** `semantic.validated(B)`가 `external_use=NONE`일 때 user_request/candidate만 인용해도 유효 처리했고, `combine`은 A DIRECT와 B DIRECT+NONE을 ALLOW로 합성했다. ISSUE_SUMMARY에는 실제 같은 이슈 출처를 읽었다는 조건만 있고, 최종 ALLOW에 그 출처를 실제 인용한 근거가 필수는 아니었다. 동일 사용자 요청·grant·도구·후보에서 A/B 모두 user_request만 인용하는 fake 관측을 넣어 approval 없이 실제 private DemoExecutor 댓글1을 확인했다. `no-source-ref.json`은 ALLOW/effects1이며, `corrected/no-source-ref.json`은 같은 args digest에 DENY/ANALYSIS_UNAVAILABLE/effects0이다. 작성자는 ISSUE_SUMMARY의 B 지지가 DIRECT/DATA_DEPENDENT 및 NONE/TASK_DATA이면 same_issue source ref를 필수 검증하도록 보완했다. 같은 독립 fixture7개 및 확장9개 PASS로 재진단했다. 이는 fake 관측 검증의 안전성 근거이며 실제 모델 의미 판단 정확도의 근거가 아니다.

**R-F3-002 / P2 / 정탐·수정 후 제거 확인.** 새 `decisionCards`는 receipt가 없는 UNKNOWN/RESERVED에도 기본0을 대입해 ‘실제 댓글 효과0개’를 표시했다. write 뒤 report 유실의 UNKNOWN에는 실제 댓글1이 남을 수 있으므로 결과 미확정을0으로 보여서는 안 된다. 자기 Firefox153.0의 about:blank에 동결 HTML/JS를 로드해 UNKNOWN+receipt null을 렌더하고 실제 DOM·PNG에서 문제를 확인했다(`unknown-ui-r2/`). 작성자는 UNKNOWN ‘실제 효과 불명 · 재실행하지 않습니다.’, RESERVED ‘확인 중’, NOT_STARTED ‘실행 전’, receipt 있는 상태의 확인된 건수를 구별했다. 동일 실제 Firefox DOM fixture의 `unknown-ui-correction/record.json`·PNG와 exit0으로 수정 확인했다. 이 offline 렌더 시험의 서버 호출0이며 실제 서버 effects는 NOT_OBSERVED다.

**R-F3-003 / P2 / 정탐·수정 후 제거 확인.** snapshot은 model/prompt/schema version을 저장했지만 `bound`가 현재값과 비교하지 않아, 같은 정책에서 프롬프트 버전을 변경한 뒤 이전 의미ALLOW를 예약·실행할 수 있었다. 자기 repo의 분석 이후 current PROMPT_VERSION만 바꾼 fixture에서 구분석의 실제 댓글1을 확인했다(`version-checks/changed-prompt-binding.json`). 작성자는 current prompt/schema/model 비교와 cache/resume의 실행 전 결합 확인을 추가하고 현재 모델 결합을 prepare/check 경로에 고정했다. 최종 자체14에서 prompt/schema/model 변경 모두 ANALYSIS_STALE/effects0·추가 분석0을 확인했다(`final-own-r1/changed-{prompt,schema,model}-binding.json`). model 변경은 cachedcheck에서부터 거부되는 정상 동작을 첫 fixture가 예상하지 못해 실패했고 이를 제품 결함으로 세지 않는다.

문서 사전 메모는 수정 확인했다. `f3_docs_sync.py`는 기존 SPEC3/v1 본문을 baseline에서 복원해 역사 섹션에 두고, 상단 SPEC4 정본을 분리한다. 00~07 전체가 기존 본문으로 끝나는지 줄바꿈 정규화 후 비교해 모두 참임을 확인했다(`final-full-check.json`). 버전 이름을 과거 실측 결과에 소급해 붙이지 않았다.

## 독립 확인과 해석

자체9개는 필수 source refs, forged refs 차단, 민감 본문 hard guard/model0, 분석 후 새 출처가 생길 때 reserve stale 거부, 같은 client key single-flight/pending/cache 및 다른 args 충돌, 분석 취소 후 DENY·approval 없음, 다른 두 후보의 쓰기 예산1·replay 추가0, 실제 RequestGuard의 세 surface 영속 기록, 감사 DB장애 safe503을 확인한다. schema/권한 판정은 mock하지 않았으며 의미 관측만 fake다. 읽기 기록은 자기 repo에 직접 생성하므로 전체 MCP wire 수용시험과 구분한다.

읽기 검토에서 공식 HTTPS·인증서 기본 검증, proxy/redirect 상속 제한, retry0/store:false/도구없음·2048 output token·15초/20초 제한, 사전 attempt24 원자집계, session analysis2, A에 sources를 넣지 않는 독립 입력, transaction 밖 모델 처리, call/grant/policy/revision/hash 결합, reserve의 저장 결과/ref 재검증·원자 쓰기예산·UNKNOWN 미환불을 확인했다. 이러한 코드 관찰을 실제 TLS negative 전수시험이나 유료 모델24 사용량 직접 검증으로 확대하지 않는다.

AuthAudit의 행은 시간 bucket/surface/status/count/first/last만 가진 credential-free durable 집계다. 자신의 ASGI RequestGuard를 통해 HUMAN/SERVICE/AGENT의 잘못된 bearer401 각각1행을 만들고, 새 guard instance 뒤에도 기록이 남으며 자기 fixture role credential 텍스트 hit0임을 확인했다. audit INSERT/UPDATE 장애에서는 handler 미진입과 안전503을 확인했다. 모든401/403/429를 집계하므로 정책DENY403도 포함될 수 있다. 순수 인증 실패를 구별하는 완전한 forensic trace나 다중 프로세스/재시작 후 영속 rate limit 완료로 표현하지 않는다. 기존 R-B-002의 ‘영속 기록 없음’에는 좁은 코드 보완이 들어왔지만 SR2-2 전수 완료 판정은 별도다.

추가 SDK spy2개는 외부 네트워크0인 상황에서 실제 어댑터의 A/B 입력 분리·고정 instructions/user data·tools[]/store:false/retry0/공식endpoint·usage 기록과 새 adapter를 만들어도24시도 한도가 유지됨을 확인한다. 반환 의미값의 정확도를 검증한 시험은 아니다. 최종14에는 이2개, 앞선9개, current model/prompt/schema 변경3개가 포함된다.

작성자의 `browser-b-regression-r1/cases.json`은 B-01~08 PASS8개이며 전부 afef114에 연결된다. 첫6 PASS/2 FAIL은 새 카드/JSON 접힘과 출처 발췌가 보이지 않아 기존 browser 기대와 충돌한 원본이다. primary 출처발췌·한국어 UI/서버 enum 분리 후 r1이 통과한 근거를 읽어 수용한다. 이는 작성자 실제 브라우저 REPLAY·EXACT/기존 승인/안전 출력 회귀이며, 검토자가 동일 공유 F3 환경을 새로 실행한 것도 실제 ISSUE_SUMMARY judge 시연도 아니다. 자신의 Firefox 시험은 UNKNOWN offline DOM 표시만 별도로 재현했다.

F3 전용 physical8020/8021은 기존8000/8001 logical audience/issuer를 보존하는 시험 별칭이다. 별도 새 token DB/PKI에서 실행하며, OAuth discovery 상호운용 또는 포트에 따른 새로운 audience검증을 입증했다고 주장하지 않는다. 이 설정 한계를 작성자에게 전달했고 logical identity 보존·상호운용 미주장으로 인계하기로 확인했다.

## 가이드 연결과 남은 범위

`guides/verification.json`에 R1/G1/G2/G3/G4 원본SHA256을 기존 manifest와 대조했다. 본 검토는 기존 정확 페이지 extraction을 재사용했고 PDF를 새로 추출·렌더했다고 주장하지 않는다. 직접 읽은 핵심은 G3 PDF66·69(외부/DB값 출력),110·112·509(인증 실패 제한·영속 추적),406(TOCTOU),511(예외/세션), G2 PDF123·125(인증 제한),133·135(최소 오류), G4 PDF24·37·38(요구→설계→코딩→동적 검증)이다. R1 PDF13·14와 G1 PDF35·47의 공급망/전주기 방향은 기존 의존성·변경 경계와 연결한다. G3 SR1-9/W15 입력 근거→strict refs→R-F3-001, SR3-1 및 G4 예외→UNKNOWN 상태표시→R-F3-002, SR2-2/W33→AuthAudit/RequestGuard 임시 장애·영속 시험으로 연결한다.

설계20/약점49 전수 최종 진단, 제품 TLS 전체 negative·키 생명주기, 운영 분산 제한·공급망 완전성·제출 C/D는 이 검토에서 완료하지 않았다. 사용자가 실제 모델 검증을 직접 수행하기로 한 최신 지시에 따라 작성자/검토자의 paid judge0·actor0이며, 실제 F3-03~07 의미 관측·F3-11 ISSUE_SUMMARY 자동 정상/차단/외부 데이터 시연·F3-12 LIVE는 NOT_RUN이다. fake 정책/근거/예약 안전성 PASS로 이 항목을 대체하지 않는다. 새 기능의 실제 의미·정상과업 게이트가 남으므로 전체 F3/MVP 완료를 수용하지 않는다.

사용자 준비 명령은 `./scripts/f3_verify.ps1 -IncludeActor`, 이후 실제 관측 자료의 viewer는 `./scripts/f3_demo.ps1`다. 검토자는 두 명령을 실행하지 않았다. judge2048 output token·24시도, actor180초·2episode·retry0을 코드에서 확인했다. actor의 요청당 generation token 상한은 런처에 명시 설정을 찾지 못해 별도 한계로 작성자에게 전달했다. actor 토큰 상한까지 입증됐다고 보고하지 않는다. 모델 오류·미시도는 실제 사용자 실행 후 각각 FAIL/NO_ATTACK_ATTEMPT로 남겨야 한다.

등록 MCP3도구의 검증된 경로에만 보호 해석을 한정한다. 모든 IPI·Codex 내장 셸/파일·호스트 전체 보호, 인과 증명, 공식 조치율·빌드라인 점수는 주장하지 않는다.
