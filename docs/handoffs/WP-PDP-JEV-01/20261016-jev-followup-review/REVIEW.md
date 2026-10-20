# T-JEV-07 한정 후속 실행 경로 별도 AI 검토

2026-10-16. with-human-dev와 FOLLOWUP_EXECUTION_START_PROMPT 전체, 최신 AGENTS/control_state·관리 response acceptance, T-JEV-06 RESULT/REVIEW를 적용했다. 작성자와 분리된 AI 검토이며 사람 개발자는 사용자1명이다. 공식 독립 보안 진단이 아니다. **고정 후속 run의 준비·모델0 진단·명시 단회 실행 연결은 오프라인 범위에서 수용 가능하며 최종 대조 완료, 현재 차단 finding0이다.** 실제 Jev 응답/의미 정확도·Codex IPI 보호 완료는 수용하지 않는다.

제품 소스와 관리 장부는 읽기 전용이다. 배정한 REVIEW/artifacts만 작성했다. 실제 provider/actor/evaluate·제품 도구 호출0, 실제 키 본문/hash 접근0, 개인 설정/인증·기존 원장/계획/결과 변경0이다. 실제 준비는 작성자가 모델 없이 수행한 것이며 검토자는 안전한 파일과 증거를 읽기만 했다.

## 계약·상태 검토

fixed `followup-response-v2` 하나만 followup-prepare로 만들 수 있고 기존 proposal을 활성화/덮어쓰지 않는다. 현재 source/PS/image·정확 합성 자료/고정 질문·부모 manifest/원장 관측을 동결한다. parent binding은 기존1회/64000과 미보고 usage를 유지하며 원장 busy/변경을 거부한다. 새 plan은 disabled이고 새 provider ledger/authorized-run/claim/result는 준비 때 만들지 않는다. key는 기존 경로의 RO 참조만 두며 새 key를 복사/해시/입력하지 않는다.

사용자가 정확 RunId/ManifestSha/ConfirmSend와 **새4/256000·누적5/320000·추가1/64000** 여섯 정수 한도를 모두 직접 선택해야 한다. 원래 잔여3/192000과 과거 UNKNOWN 비용은 따로 유지한다. 이는 기존 승인 재사용/원 실패 환불이 아니다. source/image/부모·계획을 재검사하고 모델0 preflight 뒤 승인 manifest SHA를 다시 확인한다. exclusive create로 영구 execution.claim을 먼저 만든 뒤 authorized-run/provider 순서로 진행한다. 충돌·부분 실패·timeout/중단 뒤 claim을 지우거나 재시도하지 않는다. 결과 없는 선점은 EXECUTION_STATUS_UNKNOWN과 provider UNKNOWN_RECONCILIATION_REQUIRED를 표시하며 collect만 허용한다.

inspect/preflight/collect는 키 내용 없이 동작한다. Docker preflight는 network none, source/plan/key/config RO·새 ledger/results만 RW, 기존 image ID/no-pull·비root·read-only/cap-drop/no-new-privileges를 유지한다. 명시 평가의 네트워크만 기존 TLS검증·redirect0·proxy비상속·retry0·timeout client에 연결한다. S01/S02·모델 jev-1.13.0·기존 질문과 threshold0.90, 정확 출처 검증을 유지한다. local 기대값은 wire에 넣지 않는다. A→B 순차/첫 필수 오류 뒤 B·다음 후보0, 안전 응답 진단·독립 유효 usage/부분 UNKNOWN·실패 예약 보존은 기존 응답 계약2를 재사용한다.

## 독립 검증

[독립 fixture](../../../../artifacts/20261016-jev-followup-review/test_execution_independent.py) **38건**을 포함한 관련 회귀 **250 PASS/15.84초**다. [명령](../../../../artifacts/20261016-jev-followup-review/regression-final-command.json), [출력](../../../../artifacts/20261016-jev-followup-review/regression-final.txt). network none/RO source/비root Docker에서 새 임시 root·공개 가짜 key·fake Docker 경계·실제 worker_evaluate와 MockTransport를 연결했다. 실제 runtime 키/원장/결과 경로는 마운트하지 않았다. 작성자 시험과 중복되므로 합산하지 않는다.

독립 반례는 다음을 확인했다.

- 정상4회와 ALLOW/DENY 결과·실제 파일 효과0, 원 실패1행·64000 보존, 같은 명령 재실행 provider0.
- HTTP 오류·잘못된 답/partial usage 뒤1회로 중단·64000 유지·총청구UNKNOWN; timeout의 영구 선점/결과 부재 UNKNOWN·재실행0.
- 여섯 한도 각각 누락/변경/타입 오류, 임의 run/미승인·기존 proposal 승격 거부와 claim/provider0.
- source/PS/manifest/plan/policy·부모 원장 변조, image 변경/부모 journal·wal, preflight 중 승인 manifest 교체 거부.
- symlink와 source→key symlink/hardlink를 읽기·해시 전에 거부; metadata-only 모드에서 fake key open0.
- 같은 run 동시 준비와 동시 실행은 각1winner이며 추가 allowance/실행0, legacy 읽기 전용 collect와 원 public bytes 불변.

실제 **Windows PowerShell5.1.26100.9711 34/34 PASS**다. [native 결과](../../../../artifacts/20261016-jev-followup-review/native-result.json), [명령](../../../../artifacts/20261016-jev-followup-review/native-r2-command.json). 현재와 동일 바이트의 wrapper 복사본과 fake Python만 실행했다. inspect/preflight/collect의 -X utf8/-I·한글 JSON·원 인코딩 복원, fixed RunId/정확6한도 argv, 승인8필드 누락 시 Python0·wrongrun0, 가짜 stderr 비노출/고정 stage code를 확인했다. 실제 Docker/provider/키0이며 이것은 사용자 실제 evaluate 성공 증거가 아니다. native-r1의 AuthorizationManager 실패는 샌드박스의 레지스트리 읽기 제한과 함께 기록했다. 실행정책 변경/Bypass 없이 승인된 native 실행으로 r2를 확인했다.

구현 검토 중 차단 결함은 발견하지 않았다. source 링크/최종 manifest 재검사는 작성자 통합 과정에서 추가됐고 최종 독립 반례에서 통과했다. 초기31건·확장38건/최종250·native 초기 실패와 성공 증거를 덮어쓰지 않았다.

## 최종 실제 준비·보존 대조

[RESULT](../20261016-jev-followup/RESULT.md), [사용자 절차](../20261016-jev-followup/USER_RUN.md)와 final-index/원출력을 대조했다. 최종204파일 fingerprint `c2b9455912467c907d6639ab326217ff32a2e2e8f5027462699e28080c07521a`의 현재/frozen SHA 불일치0, 독립250건을 시험한 runtime4파일 불일치0이며 native wrapper도 동일하다. 기존 NONSECRET6파일은 본 검토 기준선/T-JEV-06 최종과 같고 작성자의 key metadata/ACL 전후도 같다. 실제 key는 열거나 해시하지 않았다. RESULT/USER_RUN/REVIEW 로컬 링크 누락0이다. [최종 독립 대조](../../../../artifacts/20261016-jev-followup-review/final-check.json).

실제 고정 run은 `followup-response-v2`, manifest SHA `91cd5d7772997b376aba2609b2fff4ffad14e70c51f2eeb6cd9f112d4f8a14ce`다. 새 source38개 SHA와 원계획 네 wire·threshold가 같고 부모 manifest/원장 hash가 기존 원증거와 같다. 새 policy disabled이며 claim/authorized-run/provider ledger/result/새 key가 없다. 작성자의 actual preflight는 ready:true/default_enabled:false/paid0/actual_key_read:false/provider NOT_VERIFIED다. collect는 NOT_STARTED/NOT_RUN·source_matches:true이고 과거 실패 collect는 별개로 보존한다. 사용자가 새 한도/정확 자료/목적지를 보고 선택할 정확한6한도 명령이 RESULT에 있다. 이 준비는 실제 전송 승인이 아니다.

작성자의 frozen 기준선393 PASS/38.04초와 최종413 PASS/37.05초, Ruff PASS를 원출력과 대조했다. 별도250과 중복되므로 합산하지 않는다. Bandit은 T-JEV-06의14 LOW/1 MEDIUM에서21 LOW/1 MEDIUM/HIGH0이며 exit1이다. 추가7 LOW는 고정 argv-list subprocess3개 B603과 disabled 정책 None/2560004개 B105이고 기존 B108은 전용 container tmpfs다. 해당 사용 위치를 확인했고 clean PASS/공식 전수 진단으로 보지 않는다. 제품 PDP/의미정책·기본 JevRules 배포·기존 DB는 변경하지 않았다.

## 가이드·한계

필수5개 원문 SHA와 적용16페이지를 원 PDF에서 다시 추출해 작성자의 추출과 동일함을 독립 확인했다. [원문 대조](../../../../artifacts/20261016-jev-followup-review/guide-check.json). G3 PDF508 SR1-9·G4 PDF37/39의 보안 기능 인자/상태·경로 검증을 RunId/정확 한도·source/manifest/parent 검증과 반례에 연결했다. G3 PDF509/G4 PDF38의 중요자원 통제를 key RO·ACL·legacy 보존으로, G2 PDF133/135/137·G3 PDF511의 오류/안전 실패를 고정 진단·fail-stop·UNKNOWN/재시도0에 연결했다. G2 PDF146/G3 PDF415는 유한 요청/timeout/자원 해제, R1 PDF14/G1 PDF35~38은 고정 image/무결성·RO·검토/회귀에 연결했다. 새 SDK/의존성/이미지는 없다. 설계20/약점49의 기존 적용성·미완료를 유지하며 이번 확인을 전수 PASS/공식 조치율로 확대하지 않는다.

helper 실행은 신뢰된 실행기와 동일 OS 사용자 경계를 전제로 한다. helper 자체 AI 편집 hard-deny 방어, 키 사용 수명 전체/일반 native/hook 장애·전체 공급망은 미완료다. 기존 source manifest는 변조 가능한 helper 자체의 독립 방어가 아니다. 실제 Jev 응답 호환성/한국어·공격 정확도/holdout·Codex CLI/실제 파일 집행은 NOT_RUN이다. API/분석 오류·공격 미시도를 차단 PASS로 보지 않는다. 실제 평가·추가 한도 승인은 이 REVIEW가 아니라 사용자의 정확 명령 선택에 남긴다.
