# T-JEV-07: 수정된 Jev adapter로 실행 가능한 후속 시험 경로 마무리

관리 배정, 실제 provider/actor 호출0. with-human-dev와 최신 AGENTS/control_state, `20261016-jev-response/RESULT.md` 및 별도 REVIEW, `docs/plans/reviews/WP-PDP-JEV-01_20261016_response_acceptance_management.md`를 읽는다. 현재203파일 fingerprint `4f0d4949f158928130f81b3424f493ec959ce635b5366975523bf625e1466214`를 기준선으로 고정한다.

## 목적과 범위

T-JEV-06의 응답 호환/필드별 안전 진단/독립 usage 수리와393·별도236 오프라인 근거를 관리가 좁게 수용했다. 사용자의 collect는 원래 S01/A 실패를 그대로 보여주는 정상 조회다. source_matches:false는 수리 소스와 기존 동결 버전이 다르기 때문이다. 실제 수리 호환성은 NOT_RUN이다. 현재 followup-plan은 disabled/NOT_EXECUTABLE 제안만 생성하고 그 계획을 evaluate하는 기능은 없다.

다음 사용자에게 계획 생성만 반복시키지 말고, **같은 평가 helper를 최소 확장해 특정 새 run의 inspect→모델0 preflight→명시 evaluate→collect까지 실제 실행 가능한 경로를 완성**한다. 새로운 평가 프레임워크/모델/질문/임계치/제품 기능을 추가하지 않는다. 개발 AI가 실제 API로 수리 여부를 확인하지 않는다.

## 구현 요구

1. 기존 runtime-jev-eval의 원 key/plan/manifest/disabled policy/authorized-run/result/ledger를 그대로 보존한다. legacy collect는 계속 읽기 전용으로 성공하고 source 차이를 표시해야 한다. 기존 run의 prepare/key/evaluate 재사용·동결 검증 무시는 금지한다.
2. 이번 배정의 한정 followup run을 명시적으로 분리하고 현재 최종 소스/image ID/정확 wire 자료·부모 manifest/원장 관측에 결합한다. 기존 safe run ID·범위/재분석·symlink/junction/ACL·no-clobber 검사를 유지한다. 새 plan은 최종 소스가 고정된 뒤 생성하며 기본 비활성·새 원장/paid0으로 둔다. 이미 생성된 비실행 proposal을 묵시적으로 활성화하거나 원 manifest를 덮지 않는다.
3. 키는 이미 준비된 경로의 안전한 RO 참조만 사용한다. 사용자 키 재입력·복사/내용/hash 출력0이다. 무모델 inspect/preflight는 metadata만 확인하고 actual provider/model access를 검증했다고 보고하지 않는다. Docker source/plan/key/config RO, 새 run ledger/results만 RW·기존 고정 image/no-pull·비root/network none 또는 명시 평가의 제한 네트워크·TLS/redirect0/proxy비상속/retry0를 유지한다.
4. S01/S02의 동일 합성 자료·분리 A/B·jev-1.13.0·기존 고정 질문/threshold0.90를 그대로 사용한다. 원 local 기대값은 wire로 보내지 않는다. 순차 A→B와 첫 필수 오류 뒤 B/다음후보0을 보존한다. 유효 usage와 안전 stage 진단이 새 run에서 실제로 수집되게 연결한다.
5. **제안 한도는 새 run 최대4요청/입력예약256000**이다. 과거 실패1/64000을 합치면 누적 최대5/320000이고, 원래4/256000 계획보다 추가1/64000이다. 이는 실행/증액 승인이 아니다. 원 소비/잔여3/192000을 분리해 보여주고 이전 실패를 환불·삭제해 새로4회 남은 것처럼 처리하지 않는다. 한정된 새 run을 실수로 반복/중복 시작해도 새 호출이 발생하지 않도록 정확 manifest·실행 승인/단회 선점·재실행 거절을 검증한다. 자동으로 임의 새 run/allowance를 계속 발급하는 기능을 만들지 않는다.
6. 사용자의 정확 RunId/ManifestSha/새 한도 및 누적 총량에 대한 명시 ConfirmSend만 새 run의 실행을 허용한다. 사용자에게 실제 평가 명령을 인계하기 전 새 계획/자료/총량·추가 비용·키 참조·기존 실패 보존을 검토 가능한 형태로 정리한다. 프로그램 exit0/프로세스 종료와 의미 성공을 분리하고 실패 뒤에는 그 run의 collect만 안내한다.
7. fake HTTP/공개 가짜 키·임시 원장/분리 fixture와 실제 Windows PS5.1 경로에서 새 run 전체 동작을 검증한다. 새 run 선택, source/plan 변조, 잘못된 run/manifest/한도·미승인 요청, 경로·권한·key 비노출, 동시 중복/재실행0, 정상·오류 후 안전 진단·부분 usage·fail-stop, legacy 보존/collect를 확인한다. 별도 AI 검토를 거친다. 실제 키 본문/provider API·제품 도구/기존 DB 변경0이다.

현재 T-JEV-06 helper 파일의 CLI hook hard-deny 보호는 미보장이다. 신뢰된 helper 실행 전제와 동일 OS 사용자 경계를 명시하며 이번 단독 합성 시험을 모든 AI 편집 방어로 확대하지 않는다. 기본 -JevRules 제품 배포·Codex CLI 통합과 일반 native/hook 장애 보완을 이 작은 평가 경로의 선행조건으로 추가하지 않는다.

쓰기: tools/jev_eval.py, scripts/jev_eval.ps1, 필요한 해당 테스트/사용 설명/후속 plan·내부 실행 schema, 새 handoff/artifacts. PDP 모델/의미정책·임계치·전역 config·기존키/계획/원장/예산·관리 plans/harness/AGENTS는 수정하지 않는다. 필수 가이드 관련 원문→계약/오류·상태/권한·비밀/재시도 방지→코드/검증을 연결한다.

새 RESULT/별도 REVIEW에는 최종 소스·무모델 회귀·실행 가능한 정확 사용자 명령과 run/manifest/전송자료·새4/256000·과거 포함5/320000·추가1/64000·과거 비용UNKNOWN, 실제 호출 NOT_RUN을 명시한다. 준비/실행 연결까지 한 번에 마무리하고 전역 DONE은 관리에 맡긴다.
