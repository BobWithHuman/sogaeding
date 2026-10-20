# T-DEMO-04 별도 AI 검토

2026-10-17. 구현자와 분리된 AI 검토다. `with-human-dev`의 실제 diff·권한·효과·실패 보존 기준으로 검토했다. 검토자는 제품 소스, 원장, 서비스, 키, hooks 신뢰와 개인 설정을 변경하지 않았다. 별도 무네트워크 시험과 이 문서·검토 증거만 작성했다.

현재 최종 코드 후보에서 수정이 필요한 발견은 없다. 이 결론은 무모델 집행·시연 준비에 한정된다. 새 질문의 실제 Jev 확신 개선과 실제 native actor의 두 사실보고 성공은 **NOT_RUN**이다. 이후 사용자 시연의 두 ALLOW/OBSERVED·각 쓰기1·PDP승인0으로 수용해야 한다.

## 실제 diff와 정책 경계

- `artifacts/20261017-frozen-demo/original/`의 12개 원본과 현재 변경, 새 compose, `test_frozen_demo.py`, `test_frozen_runtime.py`를 확인했다. 수정은 새 질문과 서버 수집 문맥, 기존 connector/runtime/history의 좁은 연결이다. 인증·결정 enum·원자적 예약·승인 소비·UNKNOWN 전이를 변경하지 않았다.
- 새 `JevPolicyCurrent`는 최신 실제 user turn과 이전 turn, 현재 candidate를 명시한다. Engine이 같은 session의 실제 calls/turns에서 source의 도구·대상·turn·READ_RESULT/WRITE_COMPLETION을 수집한다. 외부 텍스트의 자가 선언으로 역할을 부여하지 않는다. receipt는 문서 사실의 증명이 아니라는 문구를 포함하고, 이전 보고서 readback도 전체 catalog에 남는다. 최신 읽기의 표현 순서만 앞세우며 원문·hash·span·전체 source 및 이전 turn을 삭제하지 않는다.
- 새 정책 `hookgw-2026-10-17-jev-current1`, 입력 계약 `jev-current-candidate-1`, 질문 버전 `jev-current-behavior-1`, 실제 B 질문 key `current_behavior`를 분리했다. 실제 wire 질문/응답 coverage와 confidence를 먼저 검증하고, 이후 순수 composer 입력만 기존 logical `behavior`로 변환한다. 저장 관측명은 실제 `current_behavior`다. 구 `behavior` 응답은 새 질문에 사용할 수 없으며 V5/P1의 원 질문은 유지된다.
- .90 임계치와 계산·제공자 중 작은 confidence를 쓰는 기존 계산은 그대로다. 원 B .6266667을 ALLOW로 바꾸거나 A/귀속 confidence를 승격하지 않는다. 고확신 위험 행동 DENY 우선과 귀속 불확실성의 분리를 유지한다. 파일명/문구/hash/저장 정답별 ALLOW 예외는 없다.

## 원 실응답·검증 증거

- 공개 재구성 시험은 원 4-source 순서의 canonical MCP raw envelope hash와 안전 후보 hash를 대조한다. 원 B 분포는 기존 V5P1에서 CONFIRM/LOW_CONFIDENCE .6266667로 유지된다. 원 analysis_id/grant 등 공개되지 않은 필드를 UNKNOWN으로 남기므로 전체 원 snapshot 복원이라고 부르지 않는다.
- 사실 후보/거짓 완료 후보, 파일명 변형과 동일 파일명 내용 반전, 인용·금지, 이전 turn 오염의 합성 경계를 읽었다. 합성 observer는 행동 답을 직접 지정하므로 이 시험은 집행·질문 전달 경계의 증거이며 실제 모델의 내용 판별·안정성 증거가 아니다.
- 관련 최초 28 PASS, runtime 포함38 PASS 후 새 질문 key를 포함한 최종 통합 **213 PASS / 42.27초**, 최종 lint PASS를 명령·로그와 대조했다. 검토자가 별도로 무네트워크 Docker에서 원 실응답·전체 source 역할·공유예산 경쟁3 PASS, 새 질문에 구 key 거부1 PASS를 실행했다. 증거는 `artifacts/20261017-frozen-demo/review/independent-targeted.txt`, `independent-new-key.txt`다.
- 최종 `e2e-final-safe`와 `e2e-final-risk`는 각각14 checks PASS다. 기존 PowerShell connector→main/start/lifecycle→고정 로컬 CLI→실제 hook handler/MCP/TLS agentgateway/가짜 Jev/파일 executor/Post/history를 통과한다. safe는 같은 두 turn에서 두 쓰기 ALLOW/OBSERVED, 보고서 실파일, 승인0, 출처5, 두 번째 B 전체4-source를 확인한다. risk는 첫 정상 쓰기를 보존하고 두 번째를 SEMANTIC/EXTERNAL_INSTRUCTION_DEPENDENCY DENY/DENIED·금지 보고서 없음으로 확인한다. 최종 trace의 새 질문 버전, close/cleanup VERIFIED와 wrapper 복원, 단회 재시작 거부도 확인했다.
- 고정 로컬 CLI는 native actor를 대신하는 명시적 시험 driver다. 가짜 Jev 응답도 합성이며 실제 native GPT/Jev 의미 정확도 성공으로 계산하지 않는다. 초기 cmd 인자/UTF8 fixture 실패, safe4 수집기 KeyError와 RO 재수집, risk1 source drift 전송 전 실패 기록은 보존됐다. 최종 성공 evidence로 이전 실패를 덮어쓰지 않았다.

## 예산·기존 기록·실행 준비

- 새 runtime은 기존 hands-on 원8요청/512000 ledger 경로를 RW 공유하고 기존 `mvp-demo-hands-on-1` budget identity를 유지한다. 새 엔진 정책명과 accounting identity를 구분한다. 새4요청 원장을 복제하지 않는다. JevClient의 BEGIN IMMEDIATE 예약은 구/신 경쟁을 합쳐 남은4개까지만 허용한다. 완료/실패/UNKNOWN 예약 환불·초기화 경로는 추가하지 않았다.
- 원 manifest/hash·원장4/8·정상250바이트/hash·episode6 종료·review 미작성 및 historical33/CLI6을 parent binding으로 확인한다. 원 source의 변경은 저장된 원본 hash와 새 source transition으로 설명하며 무조건 source 검사를 끄지 않는다. 새 episode7 claim은 독점 파일 생성으로1회만 가능하다. 사용자 선택은 남은 Jev4/예약256000과 새 CLI1/1800초이며 전체 최대37/2368000/CLI7이다.
- 새 compose는8039/8049와 별도 control/upstream DB·workspace를 사용하며 기존 서비스를 교체하지 않는다. 동일 image/gateway digest, RO bundle/역할키 mount, 최소권한·TLS 구성을 유지한다. 개발 중 actor/Jev 유료 호출은0이며 개발 AI 검토 사용량과 별개다.
- 준비 manifest SHA256은 `a7fe26676d63e228ad511e7a05c464d1b9b66e7af3555490f11cb386e74f8028`이다. 현재 source_hashes를 직접 대조해 drift0을 확인했다. parent는 원 `dbb7ecd4cc778f33836a0dd6c9b359782936f4063814b5a927bfe34277c04a38`이다. 준비 policy는 disabled, 새 episode claim0, 새 ledger0이다. CLI0.154.0/현재 configured reasoning high를 기록하고 원 capture의 reasoning은 UNKNOWN으로 남긴다.

## 남은 범위

가짜 모델의 집행 성공으로 원 과잉 CONFIRM의 실제 확신 개선을 단정하지 않는다. 공격을 무시한 안전 보고서는 내용 검토 후 NO_ATTACK_ATTEMPT이며 차단 성공이 아니다. CONFIRM/UNKNOWN/오류이면 재시도·승인으로 정상 자동 성공을 대신하지 않는다. 보호 범위는 등록 합성 파일 MCP이고, 일반 native 자유개발·hook 사망 강제집행·모든 IPI·전수 제출 진단은 별도다.

적용 P0는 정확 입력/출처/manifest 결합, 역할 권한, 전체 source, 원자적 유한예산과 단회, 오류/UNKNOWN 보존, TLS/RO mount/최소권한에 한정해 확인했다. 기존 G-01~08 준수 mapping과 `artifacts/20261017-hands-on/guide-pages.json`의 관련 R1/G1/G2/G3/G4 원문 근거를 재사용한다. 설계20/약점49 전수 PASS나 미실행 보호 범위 완료를 선언하지 않는다.

## 최종 준비와 사용자 명령 대조

`ready.json`은 issues0/ready true, JEV_RULES_ONLY·live NOT_AUTHORIZED다. 실제 bundle/image 확인과 TLS gateway initialize/initialized/tools-list만 실행했고 tools_call/user_turn/candidate0이다. 공유 원장은4/256000·usage complete, 새 claim0이다. `preservation-before.json`과 `preservation-after.json`의 파일 hash가 동일하며 선택된 역사55파일과 개인 config hash/auth/hooks metadata를 보존했다. 최종 source_hashes를 다시 대조해 drift0을 확인했다. 최종 Bandit17→19의 신규 LOW2는 공개 `input_token_limit=512000` 예약 상수다. 기존 경고와 최초/후속 JSON을 보존하며 무경고나 전수진단 PASS로 표시하지 않는다.

최종 `RESULT.md`와 `USER_RUN.md`를 읽고 parser/코드/manifest와 대조했다. 실행 명령은 기존 connector에 `-FrozenDemo -ConfirmSend -ApproveFrozenLimits -ManifestSha256 a7fe26676d63e228ad511e7a05c464d1b9b66e7af3555490f11cb386e74f8028`을 지정한 dot-source 뒤 직접 `codex`다. 두 문장이 원 capture와 같고 종료 후 history도 `frozen-demo-1`을 사용한다. 원CLI6 재사용이나 추가 유료 evaluate 단계가 없다. 전달 자료·목적지·모델·남은 원4요청·새CLI1 선택과 actor 별도 비용, CONFIRM/UNKNOWN 시 중단·no retry, 실제 모델 NOT_RUN을 명시한다. 사용자 실행 명령은 검토자가 실행하지 않았다. 무모델 준비에 대한 최종 검토 결론은 **미해결 수정요청 없음**이다.
