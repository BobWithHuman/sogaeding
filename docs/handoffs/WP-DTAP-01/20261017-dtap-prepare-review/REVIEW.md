# T-DTAP-01 별도 AI 코드·증거 검토

검토일: 2026-10-17. 구현 담당과 다른 AI 검토자가 현재 파일·원문 배정·안전한 실행 증거를 확인했다. 코드 수정·제품 모델 호출·외부 서비스 변경은 수행하지 않았다. with-human-dev의 workflow/roles/evidence를 적용했다. 관리의 최종 상태 승인이나 공식 독립 보안 진단을 대신하지 않는다.

판단: **전수 정적 목록과 명시적 부분 연결·무모델 준비 산출물은 수용 가능하다. 전체 실행 준비 완료 및 T-DTAP-01 전체 DONE은 수용하지 않는다.** 현재 후보에서 이 부분 범위의 수용을 막는 재현 가능한 P1/P2 코드 결함은 발견하지 않았다. 아래 미완료는 다음 구현의 필수 작업이며 실제 두 arm의 유료 실행을 개방할 근거가 아니다.

## 검토한 후보

- 배정 START_PROMPT.md, RESULT.md, EVALUATION_DESIGN.md, USER_RUN.md, MANIFEST.json, SOURCE_MANIFEST.json, SECURITY_REVIEW.md 및 task/tool/domain/security coverage 표.
- `src/app/benchmark/` 9개 모듈, `tools/dtap_inventory.py`, `tools/dtap_smoke.py`, `tools/dtap_eval.py`, `scripts/dtap_eval.ps1`, `tests/hookgw/test_dtap_benchmark.py`.
- 제품 `src/app/transparent/jev_decision_v5.py`와 보존된 변경 전 파일의 차이: parser/observation 확장 메서드 두 개와 호출 지점 교체이며 기본 메서드는 기존 함수를 호출한다. 기본 제품 정책을 benchmark registry로 교체하지 않았다.
- 공식 pinned HookManager 소스와 selected filesystem MCP/환경 코드, final-benign/off/on 및 final-risk/off/on의 adapter trace·official judge·초기 선택 파일 snapshot·gateway 로그·proxy DB.

최종 SOURCE_MANIFEST.json SHA256: `06a9e4dd4a8ca1fd09b940cb54b9e8bc0cfcfe4e916a7455712e7f8c1065ce89`. 이 문서 작성 직전 명시된 **15개 소스 SHA256 모두 일치**했다. 평가 준비 manifest SHA256은 `343bac491c239b5ead01cf0df9ab2951a2af18718a1dc0a9243dd5af8c780306`이다. 이 hash 확인은 소스의 무결성 대조이며 일반 정확성 증명을 뜻하지 않는다.

## 확인 결과

1. 전수 task 목록은 6,682개·unique 6,682개이며 benign 2,806 / indirect 1,998 / direct 1,878, config/judge hash 누락0이다. COVERAGE.csv 6,682행과 TOOL_COVERAGE.csv 679행을 교차대조했다. 정적 signature 663개를 실제 검증한 runtime schema 수로 표현하지 않고, 정적 목록을 만들지 못한 서버도 UNKNOWN 행으로 남긴 점이 적절하다. selected 실제 schema18개의 별도 표는 각색 연결2개·미등록16개를 구분한다. 전수 실행 가능 과업은 **0**으로 유지한다.
2. registry는 server/tool identity, 원 schema hash, 모든 schema property의 명시 slot, unknown argument, credential override 및 permission LLM 사용을 검사한다. POSIX literal path 제한은 양 arm 공통이다. 다른 도메인을 파일 도구 별명으로 허용하지 않는다. Jev A/B validation·.90 confidence·전체 입력 무결성을 재사용하고, benchmark 전용 행동 판정과 정밀 귀속을 분리한다. trusted norm은 서버 설정에서 오며 외부 source가 권한을 발급하지 않는다.
3. pinned HookManager의 pre가 dispatch try 밖인 사실에 맞춰 DENY를 PRE에서 기록한다. 필수 hook/config/hash 누락을 fail-start하고 원 dispatch와 proxy를 이중 실행하지 않는다. 실제 gateway의 정확 body hash ticket·만료·역할 인증과 proxy SQLite primary-key 예약을 거쳐 tools/call을 1회 전달한다. 응답 유실·실행 오류·취소·Post 누락은 완료로 꾸미거나 자동 재시도/환불하지 않는다. 관련 부정·경쟁 시험을 확인했다.
4. actor는 `gpt-5.2` / Responses `reasoning.effort=low`를 전송 전에 고정하고 현재 MockTransport만 허용한다. 실제 Codex CLI 시험으로 표기하지 않는다. task/judge/공격 목표를 모델 입력으로 통째로 전달하는 경로가 없고, 실제 tool 결과가 후속 대화와 엔진 출처에 연결된다. 가짜 actor/Jev의 선택을 실제 모델 능력이나 판정 정확도 근거로 확대하지 않는다.
5. 실제 연결 증거에서 정상 off/on 각각 executor1·Post OBSERVED, 위험 off executor3·official attack_success=true, 위험 on executor1·정상 읽기 Post OBSERVED 후 semantic DENY·해당 위험 후보 Post 없음·official forbidden effect=false를 확인했다. 이는 2도구 **DTAP 기반 각색 연결 smoke**이며 원 attack injection 실행/자율 actor/전수 ASR 검증이 아니다. 초기 상태 동일성도 선택된 4개 파일 범위로 한정한다.
6. 집계는 두 arm과 indirect/benign/direct 분모를 분리한다. 오류·UNKNOWN을 공격 실패로 넣지 않고, DENY 이후 최종 공격 성공을 덮어쓰지 않는다. 각색 smoke를 공식 score 입력으로 거절한다. 현재 ASR과 감소폭은 NOT_RUN이다.
7. actor/Jev/환경/judge 한도 제안과 미확인 요율/usage를 구분하고 per-arm/합산 reserve·manifest 결합·UNKNOWN·immutable task claim을 구현했다. 전 공급자 통합 ledger·scheduler 및 완결 예산은 미구현이라고 명시한다. 제품 유료 호출0과 개발 AI 사용량을 구별한다. 고정 check는 사용자 키 없이 RO 3개 mount·network none이며 run은 FULL_RUN_DISABLED로 중지한다.

## 검증·보존 근거

작성자 실행 증거 `tests-final.txt`의 123 PASS(DTAP23+기존 정책/frozen100), Ruff PASS, Bandit 최초14→최종12(High0, Medium7, Low5)와 잔여 경고 문맥을 확인했다. 스캐너 경고를 모두 해소한 PASS나 전체 SCA 완료로 표현하지 않았다. MCP1.26 advisory 발견 뒤 benchmark 의존성1.30으로 바꾼 기록과 기본 제품 의존성 보존을 확인했다. 보안 적용성69행은 변경 경계의 분류이며 전수 DTAP/P0 진단 PASS가 아니다.

검토자 추가 명령은 기존 개발 이미지에서 `docker run --rm --network none --read-only --cap-drop ALL` 및 artifacts RO mount로 네 proxy SQLite DB를 조회한 것이다(exit0). 결과는 정상 off/on `OBSERVED:1/1`, 위험 off/on `OBSERVED:3/1`로 기록·효과 주장과 일치했다. 이미 통과한 전체 회귀를 이유 없이 반복하거나 새로운 서비스를 시작하지 않았다.

preservation-before/after의 89파일을 대조했으며 허용된 V5 확장 파일1개 외 차이는 없었다. 개인 설정 및 기존 원장/claim/성공·실패 기록의 보존 근거를 확인했다. 키 값이나 개인 auth 본문을 읽지 않았다. 사용자 check의 NOT_FULL_EXECUTION_READY/6682/ready0/paid0 및 run 부정시험 FULL_RUN_DISABLED 증거를 확인했다.

## 남은 필수 작업과 관리 인계

- 14도메인 전체 환경 lifecycle/reset/attack injection, 실제 schema/slot/resource identity, native 우회 parity, trusted domain norm, official judge trajectory 연결은 미완료다. static 전체 목록을 actual tool/environment 전수 검증 완료로 부를 수 없다.
- 43개 환경 정의의 전수 image/build chain 고정·전이 의존성 검토와 환경/permission/judge의 추가 LLM 요구량·한도는 미확정이다. HF dataset과 repo 전체 byte 동등성도 미검증이다.
- 실제 autonomous Responses loop, 실제 Jev 정확도/대형 source 호환, 모든 provider 통합 ledger·타이머와 전체 유료 run은 NOT_RUN이다. 두 도구 smoke를 유료 subset/pilot 또는 성공후보 replay로 바꾸어 완료 처리하면 안 된다.
- actor 공개 단가로 계산한 합산 약 $32,186.50은 제안된 보수 예약 상한일 뿐이다. Jev/환경/judge를 포함한 전체 비용 상한은 UNKNOWN이다. 현재 유료 승인 또는 실행 명령을 내줄 수 있는 완결 실행 후보가 아니다.

관리 담당은 부분 준비의 수용과 후속 범위를 판단할 수 있다. 현재 인계 가능한 사용자 명령은 USER_RUN.md의 **무모델 상태 확인**이며, 전체 두 arm 실행·일반 native 보호·모든 IPI 차단·인과 증명·제출 준비 완료를 승인한 검토가 아니다.
