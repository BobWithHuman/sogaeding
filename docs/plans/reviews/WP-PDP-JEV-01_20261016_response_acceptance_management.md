# T-JEV-06 수용과 보존 collect 해석

2026-10-16 관리 검토. 새 RESULT/별도 REVIEW, 현재203파일 manifest와 핵심 후속 helper 경로를 대조했다. 최종 fingerprint `4f0d4949f158928130f81b3424f493ec959ce635b5366975523bf625e1466214`, 파일별 SHA 불일치0이다. 작성자393/별도236 및 자체44는 겹치는 당시 기록이며 이번 관리에서 제품 시험을 재실행/합산하지 않았다. **응답 계약2·안전 단계별 진단·usage 보존·비활성 후속 제안의 오프라인 범위**를 수용한다.

사용자 collect는 정상이다. 결과 시각이 기존2026-10-16T10:45:33.648765Z로 같고 S01/A JEV_RESPONSE_INVALID, B 중단, S02미시도·scored0을 보존했다. semantic_summary의 ANALYSIS_FAILED_PARTIAL은 새 오류나 수리 실패를 뜻하지 않고 **원래 실행의 의미 실패**를 요약한다. current_source_matches_frozen_run:false는 의도한 수리와 과거 동결 소스의 차이다. 과거1행/A/FAILED/64000예약/usage NULL도 읽기 전용 재조회로 확인했다. 과거 사용량/비용과 정확 응답 거절 필드는 여전히UNKNOWN이다. 수리 후 실제 응답은 아직 받지 않았다.

새 client는 공식 예제 표시 정밀도에 대해 제한된 제품 호환 가정을 두고, 정책에 provider/원계산 confidence의 min을 전달해0.90 미만을 올리지 않는다. 공식 정밀도 보증이나 실제 첫 실패의 원인 확정으로 해석하지 않는다. 실제 HTTP/필드별 진단과 usage 처리는 오프라인 근거만 수용한다.

현재 followup-plan은 새 소스와 부모 원장을 참조하는 disabled proposal만 생성하며 evaluation_supported:false다. 실행 기능이 없으므로 사용자에게 proposal 생성만 시킨 뒤 실제 평가가 준비됐다고 말하지 않는다. 다음은 [T-JEV-07 실행 경로 마무리](../../handoffs/WP-PDP-JEV-01/FOLLOWUP_EXECUTION_START_PROMPT.md)다. 구현 세션이 새 run의 inspect/preflight/명시 evaluate/collect를 최소 확장하고 무모델/별도 AI 검토 후 한 번에 정확한 사용자 절차를 인계한다.

새 시험 제안은 동일 합성2후보/A-B 최대4요청/256000예약, 과거 포함 누적5/320000이다. 기존 잔여3/192000을 초과하는 추가1/64000이므로 기존 승인 재사용·실패 환불/원장 초기화로 처리하지 않는다. **현재 배정은 준비/구현뿐이며 새 유료 호출은0, 실제 후속 전송·추가 한도는 아직 사용자 직접 선택 전이다.** 기존 key/계획/결과/원장을 보존한다. 새 파일/과거 기록은 관리가 읽기 전용으로만 확인했고 키 내용/해시·API·Docker·제품 DB 변경은0이다.

실제 Jev 호환성/한국어 판정·Codex 실행 전 차단·일반 native/hook 사망·공급망 등은 여전히 미완료다. helper 자기 변조 방어의 미보장 경계도 후속 통합 검토에 남긴다. 이 항목 전체를 현재 단독 합성 평가 준비의 새 선행조건으로 확장하지 않는다.
