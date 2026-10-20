# 최종 후보 별도 AI 검토 — core-auto-v5p1

2026-10-17. **검토 범위에서 차단할 발견 없음. 고정 사용자 실행 준비를 수용할 수 있다.** 실제 사용자 자동 정상/위험 수용 성공이나 MVP DONE 판정은 아니다. 제품 소스 수정·실제 모델 요청·actor 시작·기존 서비스 변경은 각각 0이다. 구현자와 다른 AI 검토이며 공식 외부 보안 진단을 뜻하지 않는다.

## 검토 대상과 결론

`CORE_AUTO_FINISH_PROMPT.md`, ADR-P04, 앞선 설계 검토, 17개 후보의 source-manifest/change.diff/변경 전 원본, 관련 기존 validator/Engine/parser/auth storage, 실응답 replay 시험, 최종 gateway 증거, 준비된 USER_RUN을 대조했다. 최종 17개 후보 hash mismatch 0이다. 후보 검토 시점 manifest는 `d83c6d63268f35554fdd1006f28417a330fa35d2032049643c3f0bc7d1b7626d`다.

- `JevPolicyV5P1`는 기존 evaluate/build/wire를 재사용하고 raw A 사용 전에 동일 `validate_response`의 전체 필드·유한 수·합·argmax·confidence 일관성 검사를 수행한다. 실제 JevClient가 먼저 envelope/usage를 검증·기록하며 재검증용 null usage는 예산이나 사용량으로 기록되지 않는다. provider/computed/effective 값과 A의 LOW_CONFIDENCE/thresholded UNCERTAIN을 보존한다.
- B의 고확신 LEGITIMATE와 검증된 raw A WITHIN_TASK가 양의 근거다. 낮은 OUTSIDE/명시 UNCERTAIN/낮은 B는 CONFIRM, 고확신 A OUTSIDE나 B 위험은 DENY 우선이다. 등록 mcp/read_file/write_file/enrolled-files-1 경계에만 새 완화가 적용된다. 사용자 ref가 없거나 source/catalog/hash/응답이 invalid이면 완화로 허용되지 않는다. 원 권한·정확 인자/세션/정책·예약/승인 DB 계약은 변경하지 않았다.
- 원 V5 실제 snapshot/wire/실응답의 재합성은 정상 CONFIRM→ALLOW, 위험 DENY→DENY다. 독립 검토 시험에서도 같은 wire/관측 값 보존을 확인했다. CLI의 .86/.70 기록은 조합 근거만이며 암호화 snapshot 복원이나 새 모델 답으로 사용하지 않았다.
- 부모 이력·source/image/bundle/문서/설정·한도를 동결한 별도 runtime이다. start에는 고정 actor와 정확 batch 승인이 필요하다. verify-block은 실제 정상 read/write ALLOW/OBSERVED 2건, PDP승인0, 고정 사용자 원문/파일, 정상 CLI 종료·정리·연결 닫기, 정상 파일효과와 남은 Jev 2요청을 확인한 뒤에만 진행한다. 동일 manifest/한도의 명시 재선택이 필요하고 원자적 exclusive claim 뒤 고정 후보를 한 번만 전송한다. 실패·CONFIRM·UNKNOWN에서 추가 모델 재시도나 예산 환불 경로가 없다.
- 고정 위험 후보는 기존 hook/MCP.exchange와 실제 읽은 source로 결합한다. expected 값은 모델 wire에 주입되지 않는다. 성공은 신뢰 Control 이력의 실제 DENY/DENIED·분석 실패 제외, upstream 쓰기 증가0·금지 파일 부재·총4요청 usage complete로 판정한다. actor 피폭 시험과 분리한다. core 경로는 기존 CONFIRM 승인 대기/재개를 사용하지 않는다.
- R-B-002는 기존 credential 없는 AuthAudit를 노출 control/public-authz/private-upstream 거절에 연결한 좁은 보강이다. 독립 영속 집계와 최근60초 제한은 일반 감사 삭제/앱 재시작으로 초기화되지 않는다. 감사 저장 실패는503·금지 효과0이다. TLS handshake 전체 감사/키 수명 전체 진단은 이 근거의 범위가 아니다.

## 확인한 증거와 독립 시험

구현자의 최종 관련84 PASS, 통합366 PASS, 최종 실제 TLS agentgateway/파일 executor replay **69/69 PASS**를 원 결과/효과와 확인했다. 실제 정상 쓰기1/PDP승인0, 위험 금지 쓰기0, 기존 예외승인·재사용·변조·stale·PDP503·UNKNOWN은 fixture 의미 응답을 실제 집행한 오프라인 근거다. 실제 모델의 의미 정확도 증거로 쓰지 않는다. PS5.1 wrapper fake14 PASS, 준비된 check ready=true/JEV_RULES_ONLY/새 ledger·actor claim 없음도 확인했다.

별도 검토자가 추가한 반례 **16 PASS (5.37s)**:

- 비정상 종료/exit/정리/연결/manifest 5조합에서 위험 전송0.
- 명시승인 없음·bool 한도·증액 actor/wall 4조합에서 전송0.
- 동시 verify-block 두 요청 중 exclusive claim 1개·전송1개.
- probe 예외 이후 claim 유지·결과 UNKNOWN 보존·재시도 거부.
- 원 실제 정상/위험 snapshot·wire·답 재합성2건.
- 낮은 raw OUTSIDE/UNCERTAIN2건은 CONFIRM, 빈 실제 사용자 입력은 분석 실패.

실행은 `--network none`, read-only root, cap-drop, no-new-privileges, tmpfs Docker다. 실제 키/원장/runtime 디렉터리를 mount하지 않았다. 최초 sandbox Docker pipe 접근은 permission denied였고, 같은 격리 명령의 허용된 Docker 접근으로 실행했다. 제품 코드 실패를 성공으로 바꾼 것이 아니다. 독립 command/output/test source는 `artifacts/20261017-core-auto-finish-review/`에 저장했다.

변경 전후85개 기록 중9개는 명시된 기존 source 변경이고 나머지는 보존됐다. 현재 파일 hash와 after 기록의 drift0, 기존 ledger/result/claim/성공 파일/원HTML의 변경은 없다. 기존 source drift를 숨기거나 과거 runtime의 source가 현재와 동일하다고 주장하지 않는다.

Ruff 통과, Bandit 원결과 exit1/18건을 확인했다. B104는 mTLS/컨테이너 listener, B105는 authorization trace의 고정 설명 문자열, B108은 컨테이너 tmpfs, B404/B603은 고정 argv·shell 없는 기존 process 호출이다. 본 변경의 무검토 취약점0/전수 진단 PASS로 바꾸지 않는다.

## 적용 기준과 남은 범위

변경 관련 R1 PDF14/G1 PDF35–36(동결·검증), G2 PDF128/129/135/137(경쟁·제한·오류), G3 PDF507–508/510(서버 권한·입력·키), G4 PDF24/38(구현→검증·인증)을 기존 원문 SHA/발췌와 연결했다. R-B-002에는 `auth-guide-pages.json`의 G3 PDF110–112 영속 인증 실패 추적·제한 기준을 추가 대조했다. 설계20/약점49 전체를 이번 좁은 검토로 재완료했다고 표시하지 않는다.

ADR-P04가 명시적으로 허용한 위험은 남는다. B가 잘못 고확신 LEGITIMATE를 내고 A가 약하게 WITHIN_TASK에 동의하면 기존 V5보다 허용될 수 있다. 이는 A 점수 수리/승격이 아니라 독립 양의 필터 완화다. 새로운 실제 모델/자동 정상/고정 위험 엔진 수용은 **NOT_RUN**이다. 사용자가 공개된 manifest/한도를 선택하고 두 실제 수용 결과를 얻은 뒤 관리가 완료를 판정해야 한다. 일반 native/hook fail-open·전체 IPI·인과 증명·전체 제출보강은 미완료 범위를 유지한다.
