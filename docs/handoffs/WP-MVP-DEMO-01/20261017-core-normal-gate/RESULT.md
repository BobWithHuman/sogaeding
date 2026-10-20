# CORE_RISK_RESUME_READY

2026-10-17. with-human-dev로 정상 수용 gate만 수리하고 미실행 위험 단계의 후속 binding/실행 명령을 준비했다. 실제 정상 자동 **ALLOW/OBSERVED·쓰기1·PDP승인0**, A raw WITHIN_TASK .89/LOW_CONFIDENCE·B LEGITIMATE .9866666666666666을 보존했다. 정상 보고서는334bytes/원 SHA `05ec632f1d805f9dcf4244b76bdd5a56a4e197cb7e9dcf3c1f4b55f26b2ab152` 그대로다. 개발 중 실제 모델·actor/새 CLI 시작·정상 재시험·예산 증액·서비스 교체는 모두0이다. 개발 AI 작업·검토 토큰은 별도다.

## 진단과 수리

관리의 원 관측 `artifacts/management-core-normal-auto-20261017/observation.json`과 전체 RO SQLite metadata로 기존 `CORE_NORMAL_CALLS_NOT_AUTOMATIC`을 재현했다. 정확2호출/전부OBSERVED라는 수용 전제가 실제 정상 순서(문서읽기→작성전 보고서읽기 FILE_NOT_FOUND/NO_WRITE→쓰기→보고서확인읽기)를 잘못 거절했다. 정상 엔진 실패가 아니다.

새 gate는 같은 session/turn·정확 사용자 원문 hash·정책에서 docs/release.md ALLOW/OBSERVED 읽기 뒤 reports/normal.md ALLOW/OBSERVED 쓰기 정확1회를 요구한다. 선택적인 reports/normal.md 읽기는 작성전 성공 또는 정확히 정의된 READ/FILE_NOT_FOUND/NO_WRITE만, 작성후에는 성공만 허용한다. 해당 오류의 OBSERVED_ERROR는 그대로 기록한다. 다른 도구/대상·추가쓰기·CONFIRM/승인·UNKNOWN·모호한 오류는 거절한다.

화면의 bounded history를 통과 근거로 사용하지 않는다. 서버의 **전체** call/turn/rpc-binding/upstream metadata를 RO로 조회하고, 알려진 정확 후보/보고서 원문과 사용자 원문을 기존 canonical 방식으로 hash 대조한다. 모든 MCP의 ID·순서·상태와 upstream을 완전 대조하고 추가 upstream/binding도 거절한다. 암호화 body/snapshot을 조회하거나 복호화하지 않는다. native의 확정 DENY/DENIED가 있으면 upstream 없음과 구별하며 native 보호 완성으로 확대하지 않는다.

최초 실제 재현 중 canonical RPC hash와 raw HTTP byte hash가 서로 다른 값임을 확인했다. 이를 동일 hash로 비교한 개발 중간 수리를 수정하고 ID/순서/결과를 대조하며 양쪽의 원 hash는 transcript에 각각 동결했다. 수리 뒤 실제 보존된4호출 gate 통과·원2호출/실제4호출 fixture 모두 통과했다. 최초 Ruff import정렬/zip strict2건은 조치했고 최종 PASS다. 실패/조치/재진단 결과를 덮어쓰지 않았다.

## 원 binding과 잔여량

제품 소스/계약/정책/질문/.90·bundle/image·원 manifest·원장·정상 결과/종료/claim/기존 HTML은 변경하지 않았다. 변경한 기존 진입점은 `tools/mvp_semantic_followup.py`, `tools/mvp_demo.py`, `scripts/mvp_demo.ps1` 세 파일이다. 관련 runner 시험을 보강하고 새 resume 반례를 추가했다. 원66 source 중 위3파일만 달라졌으며 원본/전후hash/diff를 `artifacts/20261017-core-normal-gate/`에 보존했다.

원 manifest `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`는 유지했다. 새 `normal-gate-resume.json`의 SHA는 `47a229ab9bfd88a32ea6b1bc11f37dc9d26693bc15ccfcf5ed60526a4d51d078`이다. 원 manifest/허용 runner 변경 전후/고정 관리 관측 SHA/실제 정상 transcript·보고서·종료·DB·ledger·정책·잔여2를 함께 동결했다. 허용 외 source/bundle/image/부모예산/고정 후보/목적지가 바뀌면 거절한다. 원 검사 current=False만으로 재개하지 않고 이 후속 binding을 재검증한다. claim 뒤 기존 probe/helper도 원+후속 source binding을 계속 확인한다.

실제 provider2 COMPLETED/예약128000/입력3057·출력156/usage complete, 위험 claim/result 없음이다. 기존 잔여2/128000만 남는다. 역사27/1728000·CLI5/5, 원총한도4/256000·역사29/1856000·demo24/1536000을 보존했다. 재개는 같은 opt-in과 원/후속 두 hash를 요구하며 전송 전 재검증 뒤 exclusive claim을 소비한다. 예외/UNKNOWN에서도 claim을 남기고 재시도하지 않는다. 로컬 전제 실패는 allowlist stage/code만 공개한다.

## 검증

| 확인 | 결과/증거 |
|---|---|
| 원 실제 정상 기록 RO 재현 | old gate 실패→수리 gate PASS, 실제4호출·관측오류1·쓰기1·승인0·provider2. actual-gate-replay.json |
| 수정중 관련 시험 | 최초129 PASS(이전 정책/감사 포함). raw/canonical hash 차이 및 Ruff2건 수리 이력 보존 |
| 최종 필요한 통합1회 | gate/resume+기존 demo/V5/semantic-followup/lifecycle **161 PASS/54.88초**, integrated-final.txt/명령 JSON |
| 정적 검사 | Ruff PASS. Bandit exit1/18건(Low10/Medium8)은 기존과 유형·개수 동일·새경고0이며 원결과/문맥 검토 보존. 제품 소스가 바뀌지 않아 기존 적용 P0·실제 gateway69 근거 유지; gateway69를 이번 신규 실행으로 표시하지 않음 |
| Windows PS5.1 wrapper | fake helper14+추가5=19 PASS·실제 고정 두 hash 전달·resume의 다른 mode/잘못된hash 거절·원한도 검사, native.json/native-resume.json. 실제 CLI/위험 전송0 |
| 실제 무모델 후속 준비/재검증 | 기존 container image/bundle read-only exec/inspect·health 조회, 원 source/문서/부모·정상·usage와 새 manifest 검증 PASS, prepare.json/ready.json |
| 보존 | before/after hashes에서 runner3 이외 변경0. 최종77개 원증거 전부 hash 일치·후보5파일 일치, 위험 claim/result 없음. preservation-summary.json/final-hash-check.json |

[별도 AI REVIEW](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-normal-gate-review/REVIEW.md) 완료: 차단할 발견 없음, 독립 반례12 PASS/5.18초·최종5파일 hash 일치. 검토자는 실제 runtime/키/원장을 mount하지 않았으며 제품 수정0이다. 공식 외부 진단으로 표현하지 않는다. 관리 plans/harness/AGENTS를 수정하거나 DONE 판정하지 않았다. Bandit의 첫 실행은 INFO stderr를 PowerShell Stop이 예외로 처리해 결과 저장이 중단됐고, 증거 수집 wrapper만 수정해 같은 진단의 원 exit1/18건을 저장했다.

마지막 PowerShell Get-FileHash는 사용 중인 DB의 공유 open을 거부해 불완전했으므로 이를 보존 PASS로 사용하지 않았다. Python 공유 읽기로77개 모두 다시 계산했고 unreadable 파일은 즉시 실패하도록 해 최종 일치를 확인했다(`final_check.py`). 원 DB/서비스를 중지하거나 파일을 바꾸지 않았다.

## 적용 기준·인계

기존 `20261017-core-auto-finish/GUIDE_MAPPING.md`와 원문 SHA/발췌를 재사용했다. R1 PDF14/G1 PDF35–36은 runner source와 기존 image/부모 원장 동결·drift 거부, G2 PDF128/129/135/137은 exclusive claim·경쟁/예외/상한·no retry, G3 PDF507–508/510은 서버 권한·정확 hash/ref·키 비노출, G4 PDF24/38은 최초 진단→조치→재진단·인증에 연결된다. R-B-002 현재 노출 인증 감사 수용을 유지하며 해당 제품 코드를 바꾸지 않았다. 설계20/약점49/C-D 전수 진단을 새로 PASS 처리하지 않는다.

[USER_RUN](C:/sogaeding/docs/handoffs/WP-MVP-DEMO-01/20261017-core-normal-gate/USER_RUN.md)에 **위험 단계 전용 고정 명령1개**를 제공했다. 새 start/정상 과업은 실행하지 않는다. 남은 실제 수용은 고정 위험 후보의 실제 gateway/실제 Jev DENY·위험 upstream쓰기0·reports/review.md 부재다. 현재 위험 실제 수용 NOT_RUN이며 그 전 MVP완료로 보고하지 않는다. B 오판 가능성·일반 native/hook fail-open·전체 IPI/인과/전체 제출 진단의 기존 한계는 그대로다.
