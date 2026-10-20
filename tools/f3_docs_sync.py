"""Delegated SPEC-4 prose synchronization; plans and old handoffs read-only."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for path in (root/'docs/mvp').glob('0*.md'):
    original=(root/'artifacts/20261014-f3-01/baseline-product-source/source/docs/mvp'/path.name).read_text(encoding='utf-8')
    value='''

## WP-F3-01 / SPEC-4 동기화

2026-10-14 관리 작업팩10의 명시 위임. 현재 **MVP-SPEC-4**, 정책은 `mvp-2026-10-14-f3-v2`다. 이 상단 계약과 기계 schema가 현재 정본이며 실측 PASS/FAIL/NOT_RUN은 새로운 WP-F3-01 RESULT에서 확인한다. 뒤의 SPEC-3/v1 역사 기록은 당시 기준으로 보존하고 현재 개정과 충돌하는 과거 규칙을 현재 실행 규칙으로 쓰지 않는다.

POST_COMMENT에 `comment_mode: EXACT | ISSUE_SUMMARY`를 추가했다. 생략하면 EXACT, 정확 본문 필수. ISSUE_SUMMARY는 사용자가 이슈 요약 댓글1회를 직접 선택하고 본문을 사전 발급하지 않는다. SUMMARIZE_ISSUE는 읽기만 허용한다. 공개 MCP 세 도구의 입력은 유지하고 agent의 source/approved/judge 자가 선언은 권한이 아니다. 이전 정책 세션/승인은 POLICY_CHANGED로 거부하며 기록 버전은 유지한다.

판정 순서: hard 권한/민감정보/대상/예산 → 서버 성공 읽기 출처 대조 → 필요한 후보의 독립 A(사용자/권한/후보), B(같은 입력+출처) 의미 관측 → 서버 합성. 정상 외부 데이터/제목/URL/공격 문구 보고는 데이터로 사용할 수 있다. 문서의 추가 명령을 따르는 행동은 DENY, 모호한 비민감 후보만 CONFIRM. API/필수 문맥 실패는 DENY이며 승인으로 우회하지 않는다.

analysis_text는 마스킹 후 암호화 저장, 자료당8192문자/UTF8 16384byte, 외부자료8개/총16384문자·32768byte, ingest32768byte 유지. 잘림/누락은 명시하고 ISSUE_SUMMARY는 같은 이슈의 성공한 읽기 및 검증한 출처 근거가 필요하다. UI512발췌와 분석 텍스트는 별개다.

짧은 transaction에서 단회 client ID/예산/immutable snapshot·lease 고정 → transaction 밖 두 judge 요청 → revision/세션/정책/grant/인자 재확인 → 판정/근거 저장 → 기존 원자 reserve/실행. 분석ID·stage·snapshot hash·검증refs/reasons를 CheckReply/도구결과/이력에 연결한다. 문맥 변경/lease만료는 자동 유료 재분석하지 않는다. 댓글 예산1·단회 승인·UNKNOWN 미환불/미재시도는 유지한다.

Judge는 공식 SDK/HTTPS Responses, 도구0·retry0·proxy환경상속0·redirect0·store:false다. Control 전용 ignored `runtime-f3-01/control/judge.api-key`만 읽고 Gateway/브라우저/actor 문맥에 주입하지 않는다. 요청15초, A/B 합계20초, checks client25초, MCP launcher40초(최소35초), 저비용 resolve/reserve/report1초 유지. 요청당output2048, 개발 judge총24요청·semantic session후보2개·actor180초×최대2episode를 기록한다. fake 시험은 실제 의미 정확도 증거가 아니다.

현재 자동 시연 전용 host8020/8021과 새 DB/PKI는 기존8000/8001·B8010/8011을 교체하지 않는다. 보안 설계/가이드·수정/재진단·실측·독립 검토는 WP-F3-01 handoff로 인계하며 plans/harness의 상태는 관리만 바꾼다. 전체 C/D를 이번 구현의 선행조건으로 추가하지 않는다.
'''
    path.write_text(value+'\n\n---\n\n## SPEC-3 당시 문서·준비 기록 (역사 참조)\n\n'+original,encoding='utf-8')
