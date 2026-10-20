# CORE_POST_ATTEMPT_READY

2026-10-17. with-human-dev로 실제 고정 probe의 PostToolUse 누락과 실패 후 history의 current-source 재검사 결함을 수리했다. **실제 정상 자동 성공·소비된 원 claim/result·read UNKNOWN·상태방어 write DENY·원장2요청을 보존**했다. 개발 중 실제 제품 GPT/Jev·actor/새CLI·정상 재시험·예산 증액·기존 서비스 교체는 모두0이다. 개발 AI 작업/별도검토 토큰과 제품 호출0은 별개다. 새 실제 위험 의미 판정은 NOT_RUN이며 MVP완료를 주장하지 않는다.

## 최초 진단과 수리

원증거 `artifacts/management-core-risk-post-failure-20261017/observation.json`의6호출/5upstream·transport/source·claim/result·usage를 RO로 확인했다. 이전 probe는 실제 MCP response를 `/transport-observed`에 보관했지만 PostToolUse를 보내지 않았다. risk-read는 upstream OBSERVED·transport 있음/source 없음·close 뒤 UNKNOWN, 다음 risk-write intent는 PRIOR_RESULT_UNOBSERVED로 거절됐다. 위험 Jev 분석0인 상태방어 DENY를 공격 식별 PASS로 사용하지 않았다.

이제 진짜 probe가 동일 session/turn/call/tool/args의 검증된 실제 MCP result를 실제 adapter의 `tool_response`로 PostToolUse에 넘긴다. 같은 call의 OBSERVED/source 저장을 RO로 확인한 뒤에만 다음 write를 진행한다. source/snapshot이나 원 DB를 직접 수정하지 않는다. 누락/잘못된 Post·중간 거절/실패는 다음 위험행동을 중단한다. 새 위험 판단은 정확한 새 call_ref로 수집하며 이전 실패 write를 고르지 않는다. 의미 판정 이유와 SEMANTIC routing을 요구해 선행 상태 방어/분석실패 DENY를 통과시키지 않는다.

read dispatch/transport/post/source binding·위험 intent/판정·collect·close를 고정 stage/code로 구분했다. 주오류와 정리 오류를 따로 보존하고 raw 예외/키/민감 body를 출력하지 않는다. 실패 뒤 미확인 upstream delta는 null이며 파일효과는 실제 존재 여부로 수집한다. 후속 close 오류가 주오류를 덮지 않는다.

원 history의 `BEHAVIOR_SOURCE_IMAGE_PARENT_CHANGED`를 command 차단 RO shim으로 재현했다. 역사 시작은 current=False였으나 upstream compose가 current=True를 다시 호출했다. 수정 후 이력은 기존 로컬 upstream SQLite의 전체 상태를 RO 집계하며 실행용 compose/source 검사를 호출하지 않는다. 원 runtime/profile/source 문서/bundle 무결성 검사는 유지하고 역사 소스와 현재 소스 차이를 표시한다. 새 연결·claim·provider 요청을 만들지 않는다. wrapper 안내도 선택한 core-auto-v5p1 revision을 사용한다. 기존 viewer는 새 파생 HTML만 고유 이름으로 저장한다.

## 실제 연결 검증

전체 `fixed_engine_block`를 성공 stub으로 대체하지 않았다. `artifacts/20261017-core-risk-post/e2e.py`는 **복제한 실제 PS5.1 wrapper → 실제 mvp_demo.main → 실제 attempt/gate → 진짜 fixed_engine_block → 실제 hook/MCP → 실제 TLS agentgateway/Engine/JevClient(가짜 HTTP Jev) → 실제 Post/source → DENY → close → 같은 history**를 연결했다. 원2호출과 실제4호출 gate는 관련 회귀에 보존하고, 종단 시험에서는 실제4호출 정상 기록과 Post가 누락된 실제6호출 실패를 먼저 생성했다.

시험 adapter는 별도 fake workspace/DB/키·포트와 합성 부모/관리증거 hash 및 OFFLINE 건강 식별만 조정한다. 원 runtime/실제 키/원장은 mount하지 않았다. 의미 판정·gateway·probe·Post·실제 history는 우회하지 않았다. 기존 image를 재사용했고 시험 compose만 올렸다가 종료했다. fixture 의미 응답을 통한 집행 증거이며 실제 모델 정확도 증거는 아니다.

| 실행 | 결과/원증거 |
|---|---|
| 실제 기존 상태 RO 재현 | 원 history 실패→현재 history PASS, 정상4/전체6/5upstream/oldUNKNOWN/claim/usage2 보존. actual-replay.json/actual-history.json |
| 수정 중 관련 회귀 | 74 PASS/27.79초 |
| 최종 필요한 통합1회 | 177 PASS/55.29초. 이후 실패효과 미확정 표시의 좁은 보강은 최종 종단/정적으로 검증. integrated-final.txt |
| 실제 PS→진짜 probe 성공 종단 | 최초 성공12 PASS, 최종 후보 final-success12 PASS. Post/source OBSERVED 뒤 의미 DENY·위험쓰기0·fake usage4·동일 history/중복 거절 |
| Post 누락 종단 | 11 PASS. source 없음/UNKNOWN·다음 위험write0·fake usage2·실패 후 동일 history 성공 |
| 잘못된 Post+close 응답유실 종단 | 12 PASS. 주오류 READ_POST 보존·CLOSE_UNVERIFIED 병기·위험write0·fake usage2·같은 history. 최종 후보 final-negative에도 재확인 |
| PS5.1 고정 명령 전달/거절 | 실제 두hash/attempt 전달·다른mode/attempt/hash/oldresume 혼합/증액/무승인 거절8 PASS, native.json |
| 정적 | 실제 probe를 포함한 프로젝트 문맥의 최종 Ruff PASS. 최초 새 시험 E701 12건 수리. Bandit 기존범위18건 및 추가 probe 이전/현재 각9건은 모두 원결과 보존·전수 보안 PASS 아님 |
| 실제 무모델 준비 | 원 image/bundle read-only exec/inspect·health 조회 및 원/이전/new attempt binding 검증 PASS. prepare.json/ready.json |

첫 E2E는 fixture adapter의 control 포트 식별 누락으로 새 probe 실행 전에 중단됐다. TLS 검사는 유지하고 test 포트 식별만 맞춰 새 fixture에서 재검증했다. 실제 기존 history 조회는 sandbox의 loopback 소켓 거절을 받은 뒤 허용된 읽기 전용 GET으로 확인했다. 코드/모델 실패를 성공으로 바꾼 것이 아니다. 기존 원증거와 최초 failure.json을 덮어쓰지 않았다.

## 보존과 별도 단회 준비

원 manifest `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`, 이전 후속 `47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`, 소비된 claim/result와6호출/5upstream·UNKNOWN·정상334bytes/SHA `05ec632f1d805f9dcf4244b76bdd5a56a4e197cb7e9dcf3c1f4b55f26b2ab152`를 유지했다. 원 정상 call ID 전부를 검증하기 전에 기존 위험 실패를 포함한 전체6기록을 pinned 관리증거와 대조한다. 전체를 session 필터로 무시하지 않는다.

새 `post-complete-1-manifest.json` SHA는 **`5d5de664a3ed337ec65bf58d2e753321cd42c48b58f6c69f3a3dd0f4f3fbf945`**다. 기존 script/helper/probe4파일의 원/현재 hash, 원/이전 manifest, 소비 claim/result, 정상/실패 DB·원장·종료·남은2를 결합했다. 정책/질문/.90·권한/TLS·제품 source/bundle/image·고정 후보/목적지·원 총한도는 바꾸지 않았다. 허용 외 drift·usage 변화·불완전 사용량·위험쓰기·새 claim은 전송 전에 거절한다. 새 exclusive claim은 별도 파일이며 예외/UNKNOWN에도 남고 자동 재시도하지 않는다. 원 실패 세션을 다시 보내거나 사후 Post로 고치지 않는다.

원 provider2 COMPLETED/예약128000/입력3057·출력156/usage complete, 역사27/1728000·CLI5/5를 유지한다. 원 총4/256000·역사29/1856000·demo24/1536000 안에서 잔여2/128000만 별도 시험에 쓴다. [USER_RUN](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-risk-post/USER_RUN.md)의 위험 단계 전용 명령1개를 준비했다. 사용자 추가 prepare/키 입력/새 CLI/정상 재시험은 필요 없다.

원본·before/after·diff·후보6hash·명령/결과는 `artifacts/20261017-core-risk-post/`에 보존한다. 최종83개 baseline 중 허용 runner4개만 변경됐고 나머지79개 원증거의 hash와 후보6개 hash가 전부 일치했다(`preservation-final.json`). 새 attempt call/claim은0, 원 provider2/잔여2다. offline harness 파일은 초기 복사를 누락해 이번 변경만 역적용한 원본을 재구성했고, 과거 동결 SHA와 일치함을 확인했다(`harness-backup-note.json`). 모든 파일을 변경 전 완전 복사했다고 표현하지 않는다. 제품 소스는 그대로이고 관리 plans/harness/AGENTS도 수정하지 않았다.

[별도 AI REVIEW](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-risk-post-review/REVIEW.md) 완료: 수정이 필요한 발견 없음. 독립 probe 경계 반례14/14·실제 TLS 종단 증거·원/이전/새 manifest·고정 명령·최종 보존 hash를 대조했다. 보조 double 시험을 실제 gateway 종단 근거로 대신하지 않았다. 공식 외부 보안 진단은 아니다.

추가 정적 확인의 처음 분리 컨테이너는 src/first-party 문맥이 없어 기존 fixture import를 잘못 분류했다. 소스 수정 없이 원 프로젝트 src/workdir/config를 갖춘 검사에 probe를 명시해 Ruff PASS를 확인했다. probe Bandit은 이전/현재 모두 B404 Low1·B603 Low3·B108 Medium4·B104 Medium1로 동일하다. 기존 고정 argv/shell 없음·시험 tmpfs·고정 TLS listener의 문맥과 연결하며 scanner 무경고로 바꾸지 않는다.

적용 가이드는 이전 GUIDE_MAPPING과 R1 PDF14/G1 PDF35–36(동결/검증), G2 PDF128/129/135/137(완료/경쟁/오류/상한), G3 PDF507–508/510(권한/정확 입력/비밀), G4 PDF24/38(진단→조치→재진단)을 재사용한다. 현재 R-B-002 노출 인증 감사 통제는 유지했다. B 오판 가능성·일반 native/hook fail-open·전체 IPI/인과/전수 제출진단·설계20/약점49의 기존 미완료 범위를 새로 PASS 처리하지 않는다. 실제 새 의미 DENY·위험쓰기0 수용 전 전체 MVP 완료가 아니다.
