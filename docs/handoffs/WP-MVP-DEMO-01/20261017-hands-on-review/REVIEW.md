# T-DEMO-03 별도 AI 검토

2026-10-17. 구현자와 분리된 AI 검토이며 제품 소스 수정·모델 호출·native CLI 시작·hook 신뢰 변경·서비스 변경·키 본문 열람·원장 수정은 하지 않았다. `with-human-dev`의 diff·실행증거·역할 기준을 적용했다.

현재 코드 후보에서 추가 수정이 필요한 발견은 없다. 이 판단은 **사용자 실행 준비의 좁은 코드 검토**다. 실제 native CLI의 Pre/Post·다중 turn·정상 쓰기와 위험 차단까지의 종단 검증은 **NOT_RUN**이며, 새 hands-on 체험 성공이나 일반 native/모든 IPI 보호를 승인하지 않는다. 최종 사용자 명령의 binding까지 대조했다.

## 검토 대상과 확인

- `artifacts/20261017-hands-on/original/`의 원본과 현재 `mvp_demo.py`, `mvp_semantic_followup.py`, `mvp_demo_hook.py`, `mvp_demo_mcp.py`, `mvp_demo_viewer.py`, `mvp_semantic_probe.py`, `hookgw_connect.ps1`, `mvp_demo.ps1`의 실제 diff를 확인했다. 새 compose와 `test_hands_on.py`도 읽었다.
- 새 현재 PowerShell wrapper는 명시 전송·정확 manifest·분리 한도 선택을 요구한다. 인자 없는 `codex`만 받아 기존 검증·start·lifecycle을 실행하며 사용자 과업을 자동 입력하지 않는다. 별칭·함수의 변경 가능한 객체 대신 scriptblock/options/description을 snapshot하고 종료 후 복원한다. 새 global 설정 파일이나 로그인 설정을 쓰지 않는다. 기존 host 사용자 승인 경로는 child 실행 인자에만 적용되고 sandbox 우회 인자는 없다.
- 새 allowance는 별도 runtime/DB/ledger·8038/8048·CLI episode6만 사용한다. 8요청/입력예약512000/CLI1/1800초, 역사 포함37/2368000/CLI6을 명시한다. 소진된 부모 ledger4/4와 종료·정상효과·실제 고정 위험 DENY 결과를 검증하고 기존 bundle/image·V5P1 정책을 재사용한다. 기존 claim/ledger가 생기면 재시작을 거절하고 무조건 재시도·환불 경로를 추가하지 않는다.
- compose의 기존 core와 차이는 project/runtime/port/subnet뿐이다. 제품 bundle RO, 기존 Jev 역할키 RO, TLS/mTLS 설정·기존 인증/판정/예약/집행 경로를 유지한다. source·grant/profile·문서·bundle·parent·한도 drift를 사용자 실행 전에 검사한다.
- 직접 입력한 hook turn을 기존 adapter가 처리한다. 미래 사용자 문장을 frozen prompt로 묶거나 fake 정답을 actor prompt에 넣지 않는다. test-only fake actor/Jev oracle 변경은 별도 fixture에 한정되며 실제 엔진 정책 수정이 아니다.
- 이력은 의미 routing+정해진 위험 reason의 DENY와 규칙 DENY·UNKNOWN을 구분한다. RO 이력에서도 runtime/bundle/문서 binding을 유지하고 현재 source drift를 별도로 표시한다.

## 최초 발견과 조치

**HANDS-R1 — ALLOW를 공격무시로 확정하는 오표시.** 최초 후보는 review 읽기 뒤 review 쓰기의 ALLOW/OBSERVED만으로 `NO_ATTACK_ATTEMPT`를 부여했다. PDP false negative로 공격 내용이 쓰여도 같은 라벨이 될 수 있으므로 독립 내용 확인을 대신할 수 없다. 구현자에게 수정 요청했고 현재는 `REVIEW_WRITE_ALLOWED_ATTACK_ADOPTION_UNASSESSED`, `INDEPENDENT_CONTENT_REVIEW_REQUIRED_BEFORE_NO_ATTACK_ATTEMPT`로 바뀌었다. 의미 DENY 관측과 독립 내용 검토 후의 사람 분류를 구분하는 방향으로 해소했다. 변경된 시험 기대값도 확인했다.

## 증거와 남은 경계

- 관련 최초 시험15 PASS. 필요한 통합118 PASS/36.13초와 lint PASS를 원 명령·로그에서 확인했다. 이력 발견 수정과 consumed claim/ledger 추가 반례 뒤 관련17 PASS/5.94초·lint PASS, 예산/실패·UNKNOWN·close/host reviewer 관련 경계22 PASS/2.22초도 확인했다. 이들은 모델 없는 단위/통합 시험이며 native hook 종단 성공을 대신하지 않는다.
- `wrapper-check.json`의 함수·별칭 복원, 잘못된 manifest 실패의 기존 상태 보존, ReadOnly 별칭 거절 4시나리오를 helper 원문과 함께 확인했다. 성공 helper는 명시적으로 wrapper만 시험하며 actual native/Pre/Post를 성공으로 대체하지 않는다.
- 실제 native fixture는 preflight→wrapper→설치된 native Codex 시작/정상 종료·connection close/tree cleanup까지 관측했다. `e2e-attack-2`의 finish는 EXITED0/close VERIFIED/cleanup VERIFIED다. 전체 fixture의 실패 기록은 보존됐다. 최초 함수 복원 결함은 snapshot 수정과 wrapper 한정 재진단으로 처리했다.
- automatic approval review가 `/hooks` 신뢰 변경을 거절했고 사용자가 **“신뢰 변경 없이 나머지만 완료”**를 선택했다. 따라서 hook 신뢰를 바꾸거나 우회하지 않고, actual native Pre/Post·2turn·fake actor의 정상/위험/공격무시 종단은 미실행으로 남는다. 기존 엔진의 수용 증거와 이번 새 native 체험 검증을 혼동하지 않는다.
- 적용 P0 검토 범위는 정확 입력/출처/manifest 결합, 권한·등록 MCP 경계, 분리된 유한 한도와 단회, 오류/UNKNOWN/no unsafe retry, RO 기록, TLS·역할 mount·최소권한 유지다. 가이드 G-01~08의 기존 원문 매핑을 유지하며 설계20/약점49 전수진단·TLS negative 전체·hook 사망 강제집행·일반 native 보호를 PASS로 확장하지 않는다. 개발 AI 검토 사용량은 제품 actor/Jev 유료 호출0과 별개다.

## 준비 binding 확인

준비된 manifest의 실제 SHA256은 `dbb7ecd4cc778f33836a0dd6c9b359782936f4063814b5a927bfe34277c04a38`이며 prepare/check 출력과 일치한다. 기존 core의 bundle/image/gateway digest와 동일하고 새 episode6 claim·Jev ledger는 존재하지 않는다. policy는 disabled, live는 미승인이다. 실제 local check는 issues0이며 TLS gateway MCP initialize/initialized/tools_list만 수행했다(tools_call/user_turn/candidate0). `/hooks` 검토 전이라는 신뢰 조건을 check가 명시한다. 이 ready는 native Pre/Post 검증 완료의 의미가 아니다.

`preservation-before.json`과 `preservation-after.json`은 동일하다. 선택된 역사 파일48개와 개인 config hash·auth/hooks 파일 metadata 보존을 확인했으며 실제 키/토큰 본문을 열거나 hash하지 않았다. 정적 진단은 before/after16건으로 동일하며 도구 무경고나 전수 약점 PASS로 보고하지 않는다. `guide-pages.json`의 해당 원문 발췌와 기존 준수 매핑을 연결하는 제한된 변경 검토다.

최종 `USER_RUN.md`/`RESULT.md`도 읽었다. dot-source 기존 connector의 `-HandsOn -ConfirmSend -ApproveHandsOnLimits -ManifestSha256`와 위 실제 hash, 다음 plain `codex`, 같은 revision history 명령이 parser/코드와 일치한다. 명령에는 과업·정답·fixed 위험 후보 주입이 없다. 문서는 신뢰 미변경 선택을 먼저 명시하고 `/hooks` 조회 후 미신뢰이면 과업 없이 `/quit`, CLI 슬롯 소비·재시작/초기화 금지를 설명한다. 이미 신뢰되어 세 hook이 활성인 경우에만 정상/공격문서 권장 입력을 제시한다. 이를 전체 실행 준비 PASS나 native 종단 완료로 확대하지 않는다.

최종 manifest의 public source_hashes와 candidate-hashes의 after 값을 현재 파일에 다시 대조해 drift0을 확인했다. 준비 history는 후보0/보고서 없음/`NOT_OBSERVED`/source match true이며 기존 viewer가 새 고유 HTML만 쓴다. 사용자 실행 명령은 검토자가 실행하지 않았다.
