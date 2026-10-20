# T-JEV-05: Windows 한국어 inspect 인코딩 수리

관리 배정, 실제 모델 호출0. with-human-dev 및 최신 AGENTS를 적용한다. 사용자 키 저장은 성공했고 preflight는 ready_for_user_opt_in:true/default_enabled:false/live_authorized:false/paid_requests:0, provider 접근 미검증이다. inspect만 실패했다. 기존 키를 다시 입력/읽기/교체하지 않는다.

관리 읽기 전용 진단으로 설치 bundled Python의 `-I` 실행은 default_text_encoding=cp949/utf8_mode=0이었다. `verified(root)`는 PASS지만 inspect 분기의 `plan/requests.json.read_text()`는 UTF-8 한국어를 CP949로 읽어 UnicodeDecodeError(offset144)다. 같은 파일을 명시 UTF-8로 읽으면 JSON과 합성2후보가 정상이다. `python -X utf8 -I tools/jev_eval.py inspect`를 출력만 캡처해 검증하면 exit0·UTF-8 JSON이 원계획과 완전히 같았다. 키 본문/모델/Docker 실행0이다. 당시 manifest SHA는 `b542e3ee0cd8b8674f4679b735e8719d8dbe1f6737da75f20ac3d53a0116680f`다.

1. 기존 키/계획·manifest·disabled policy·제공자 원장/결과 유무를 보존하고 정확 실패와 소스 기준선을 고정한다. 파일 내용의 키는 열지 않는다.
2. 우선 `scripts/jev_eval.ps1`의 신뢰 Python 호출에 명시적인 UTF-8 모드와 PowerShell5.1의 UTF-8 stdout/JSON 캡처를 적용하는 최소 수리를 검토한다. `-I`는 유지하며 환경변수에만 의존하지 않는다. 콘솔/출력 인코딩을 일시 변경한다면 finally에서 원상 복원한다. 키는 기존 ASCII 숨긴 stdin 경로로 유지하고 argv/콘솔/로그에 넣지 않는다.
3. 기존 source_hashes에 PS 스크립트는 포함되지 않으므로 가능하면 동결된 helper/질문/plan을 수정하지 않는 경로를 선택한다. `tools/jev_eval.py` 등 동결 소스 수정이 필요하면 기존 manifest를 그냥 덮거나 검증을 끄지 말고, 정확 wire body/질문/한도 동일성과 키·승인/원장 보존을 증명하는 좁은 migration을 먼저 설계·기록한다. 준비/정책/예산 초기화·삭제는 하지 않는다.
4. 실제 Windows PowerShell5.1에서 기본 CP949 환경의 최초 inspect 실패와 수정 후 한국어/Unicode 보존·ConvertFrom-Json 성공을 검증한다. 비활성 상태/manifest SHA/정확한 전송 자료를 보존하고 기존 inspect/preflight/collect/evaluate의 승인·한도·no-retry 동작을 약화하지 않는다. 가짜 자료로 출력 파이프/콘솔 상태 복원도 확인한다. 실제 key 읽기·provider/actor 호출은0이다.
5. catch-all을 모든 저장/인코딩 실패로 뭉개지 말고 원문·경로·키 없는 고정 stage/code로 최소 보완한다. 별도 AI 검토 후 새 RESULT/REVIEW에 수정 범위·실행 증거·미실행과 정확 사용자 inspect/preflight 명령을 인계한다. 관련 가이드 오류처리/중요정보 노출·고정 파라미터 기준을 기존 준수표의 원문 페이지와 연결한다.

쓰기 범위: `scripts/jev_eval.ps1`, 필요한 최소 helper I/O/관련 테스트, 현재 사용 설명, 배정 handoff/artifacts. plans/harness/AGENTS·전역 설정·CLI 설치·CA·기존키/DB/원장·제품 PDP 정책은 변경하지 않는다. 실제 Jev evaluate와 추가 유료 CLI는 여전히 이번 배정 밖이다. 사용자 preflight PASS를 실제 키 인증/모델 접근 또는 IPI 식별 성공으로 표현하지 않는다.
