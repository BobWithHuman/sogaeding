# semantic-confirm-1 오프라인 인계 수용·사용자 정상 시연 배정

2026-10-17 Asia/Seoul. **보완 구현/오프라인 검증/후속 실행 준비 범위에서 수용한다. 실제 V3 정상 자동 완료·공격 차단·전체 MVP는 미완료다.** 다음은 새 개발 작업이 아니라 사용자 정상 시연이다.

## 관리가 직접 대조한 범위

[관측 JSON](../../../artifacts/management-mvp-semantic-ready-20261017/observation.json). 최종 공개 source236, proposal source62, bundle39의 현재 파일과 SHA 불일치0이며 bundle manifest도 일치한다. 후속 공개 manifest는 `53b521a42358fdce9575225377233baae1b225647e9f17625c53690df336f0f8`이다. 최신 RESULT/별도 REVIEW/USER_RUN, 고정 start 승인값과 실제 activation 코드의 추가 시작1/총3·Jev 총8/예약512000·wall1800을 대조했다.

기존 시작2/2, claim3 없음, 새 Jev4행 모두 COMPLETED(입력6804/출력924·예약256000), 두 CONFIRM의 decision을 보존한 STALE, 과거 UNKNOWN1·upstream OBSERVED1/UNKNOWN1, 실제 보고서 부재가 유지된다. episode2 FINISHED는 TIMEOUT1800/tree·connection VERIFIED다. 현재 실제 health는 관리 sandbox에서 조회하지 못했으며 서비스V2라는 사실은 개발·독립 PS5.1 check 증거에 근거한다. 관리가 V3를 배포하거나 모델을 호출하지 않았다. 사용자 start 전 check를 둔다.

작성자613회귀/기존A-B30/장애8, gateway58, 검토자56반례와 대화형 gateway58은 각 인계 증거를 검토한 수치다. 관리가 전체 재실행한 수치가 아니며 가짜 provider 검증을 실제 V3 모델 정확도로 표시하지 않는다. 발견된 의미/승인/manifest 결합 문제의 최초 진단→수정→재시험을 구분했다.

## 시연 지시의 작은 불일치와 이번 선택

개발 USER_RUN의 `reports/release-summary.md`, `reports/review-summary.md`는 실제 viewer의 PATHS/효과 조회 목록에 없다. 현재 viewer는 `reports/normal.md`, `reports/review.md`를 조회한다. 새 이름으로 파일이 생겨도 화면은 OUT_OF_DEMO_SCOPE/파일 없음으로 오해시킬 수 있다. 임의 보고서 이름 표시 지원이 완료됐다고 수용하지 않는다.

이번 smoke는 **기존 화면이 지원하는 normal.md/review.md로 사용자 요청을 정렬**한다. 파일이 현재 없고 새 세션/정확 인자 판정 대상이므로 이전 CONFIRM/UNKNOWN을 재실행·해제하지 않는다. 이는 사용자 prompt 예시 선택이며 제품 소스/manifest/예산 변경이 아니다. 이 표시 범위를 고치기 위한 새 구현/전체 회귀를 이번 시연의 선행조건으로 추가하지 않는다. [관리 확정 최소 실행](../../handoffs/WP-MVP-DEMO-01/USER_NEXT_RUN.md)을 우선한다.

## 완료 상태

T-DEMO-01은 IN_PROGRESS다. 정상 ALLOW+OBSERVED+실제 보고서가 나와야 자동 정상 흐름을 수용한다. CONFIRM 후 HUMAN_APPROVAL_CONSUMED 실행은 예외 흐름 성공으로 별도 기록하며 자동 허용 성공으로 대체하지 않는다. 실제 위험 후보가 없으면 NO_ATTACK_ATTEMPT, 분석 실패/UNKNOWN은 차단 성능 PASS가 아니다. 사용자가 추가 시작1회를 선택하지 않으면 모델0 check까지만 수행한다. 기존 원장 잔여4요청은 새 예산이 아니다.

## 개발 토큰의 관측과 운영 조정

사용자가 지목한 개발 채팅 `WP-MVP-01 개발 시작`의 최근 완료 작업 metadata를 읽었다. [요약](../../../artifacts/management-mvp-semantic-ready-20261017/token_workflow_summary.json): 약29.9분, 명령62회, 그중 전체 파일 읽기 명령43회, 보조AI3경로, context compaction1회다. 비정상 exit9에는 진단 도구의 경고 exit 등이 포함될 수 있으므로 모두 불필요한 실패로 세지 않는다. 정확 raw token/input/cache/reasoning 사용량 필드는 이 read_thread 결과에 없어 비용 비중은 미확정이다.

코드 구현 외에도 새 정책·사람 승인·상태/경쟁·진단·runner·보존·가이드/인계 문서를 한 작업에 포함시킨 관리 지시가 작업량을 늘렸다. 실제 fixture 충돌/미마운트 수정과 재시험도 있었다. 명령/시험 자체가 매번 Jev 요청을 쓰는 것이 아니라, 이를 계획·분석·수정하는 개발 AI의 model work가 소비된다. 개발 인계의 유료 호출0은 제품 actor/Jev 실행0이며 개발 Codex 토큰0이 아니다.

앞으로 기본은 구현1+최종 검토1, 변경한 함수/라인 중심 읽기, 부분 시험 후 최종 통합1회, 보안 코드 변경·실패·새 우려가 있을 때만 재실행한다. 적용 P0/PDF 기준·필수 보안 검증/원증거는 유지한다. 이 원칙을 AGENTS에 반영하며 개인 모델/추론/로그인 설정은 변경하지 않는다.
