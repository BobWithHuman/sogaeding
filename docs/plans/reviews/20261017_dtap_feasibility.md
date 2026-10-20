# DTAP 활용 검토 — 실행 전 제안

2026-10-17. 사용자는 고정 시연 결과를 확인하고 DTAP을 로컬에서 실행해 엔진 DENY를 보여주는 방안을 질문했다. 공식 자료를 읽어 평가한 제안이며 설치/다운로드 실행/제품 변경/모델 호출/신규 예산 배정은 하지 않았다. 기존 무모델 시연 마감 작업과 구별한다.

## 현재 결과의 의미

악성 지시가 외부 문서에 있었으므로 IPI **시도/노출**은 있었다. actor가 그 지시를 채택하지 않아 위험 후보/공격 성공은 관측되지 않았다. 이번 frozen-demo-1은 두 사실보고 자동 ALLOW/OBSERVED·승인0을 입증하며 현재 질문의 위험후보 DENY를 입증하지 않는다. 과거 v5p1의 실제 고정위험후보 DENY는 별도 증거다.

사용자 후속 history와 원 finish 이벤트를 대조해 episode7 EXITED/exit0·616.968초·connection_closed/tree_cleanup VERIFIED·connection0을 추가 확인했다. 종료 증거는 `artifacts/management-frozen-demo-actual-20261017/closure.json`에 보존한다. 최초 관측의 finish 미기록 상태를 덮어쓰지 않는다.

화면의 정책 UNKNOWN은 `src/app/transparent/demo_report.py`의 정책 허용목록에 current1이 없기 때문이고, B current_behavior 누락은 이 파일과 viewer의 질문 허용/표시 목록에 새 키가 없기 때문이다. 원 DB에는 current1/LEGITIMATE .9866667이 있다. T-DEMO-02 오프라인 마감에서 원 판정·확신을 바꾸지 않고 표시를 고친다.

## 공식 근거

- [공식 저장소](https://github.com/AI-secure/DecodingTrust-Agent/blob/main/README.md): Docker 격리 MCP 환경, benign/direct/indirect 목록, 부분집합·사용자 agent 통합, 공개 실행 궤적을 제공한다. 이번 목적에는 indirect와 benign을 선택한다. direct 사용자 악성요청을 외부 IPI로 섞지 않는다.
- [공식 도구 hook 계약](https://github.com/AI-secure/DecodingTrust-Agent/blob/main/docs/hooks.md): pre/post 호출과 pre 예외에 의한 차단 경로를 제공한다. config 누락/잘못된 import가 hook 미적용으로 이어질 수 있고 취소 때 Post 누락 caveat가 있다. 연결 검증/실행 전 강제 관문·UNKNOWN 보존이 필요하다. 등록만 했다는 이유로 집행됐다고 판단하지 않는다.
- [공식 OS-Filesystem 도메인](https://decodingtrust-agent.com/docs/domains/os-filesystem): 파일 읽기/쓰기 외에 shell·디렉터리·권한·다른 서비스까지 포함한다. 현재 with-human은 등록 read_file/write_file만 지원하므로 전체 도메인 직접호환을 가정할 수 없다.
- [공식 공개 궤적](https://huggingface.co/datasets/AI-Secure/DTap-Bench-Agent-Trajectories): 관문 직전의 외부 입력·사용자 과업·후보를 재구성할 자료 후보. 실제 호환 trace/위험 호출을 아직 선정하거나 재현하지 않았다.

## 추천하는 소규모 비교

간접주입 3~5건과 정상 대조를 사전 고정하고, 같은 actor/도구·초기상태·공격자료에서 엔진 미적용/적용을 비교한다. 모든 효과는 격리된 합성 환경으로 한정한다. actor가 위험 호출을 실제 생성했는지, 엔진이 semantic DENY했는지, executor 금지 효과가0인지, 정상과업이 완료되는지 따로 측정한다. CONFIRM/분석 실패/지원밖 규칙거절/모델 자체 저항을 DENY 성공으로 합치지 않는다.

DTAP 기본 평가 실행만으로 with-human이 붙지 않는다. 실제 tool dispatch가 gateway의 정확 호출/인자·사용자turn·출처 결합과 실행 전 판정/예약을 거쳐야 한다. 외부 sandbox 호출을 단순 관측만 하거나 이미 실행된 뒤 분류하는 경로는 사전 집행 증거가 아니다. 현재 도구와 자연스럽게 호환되는 사례를 우선 고르고 최소 adapter 범위/가이드·보안검증 부담을 먼저 확인한다.

공식 환경·원 task·judge를 유지하면 선택한 subset 결과로 보고한다. 파일 MCP로 각색하면 “DTAP 기반 각색 시연/재현”으로 표시하고 공식 점수로 부르지 않는다. 관측 후 고른 공격 성공 사례는 시연용 선별이며 대표 공격성공률이 아니다. 평가용 subset은 소스·task ID·seed/초기상태·모델·모든 결과/제외 사유를 사전에 동결한다.

GPT가 계속 공격을 거부하면 공개 위험 궤적을 관문에서 **재생**하여 엔진의 의미 DENY/금지효과0을 검증하는 방식도 유효하다. 이것은 재생한 위험후보 집행 시험이며 새 GPT의 실제 피폭→차단 시험과 구분한다. 모델/정책 자체의 기대값을 actor/PDP 입력으로 넣지 않는다.

현재 원장은8/8 소진이다. 로컬 실행이어도 원격 actor/Jev/일부 환경·judge가 API를 부르면 비용이 발생할 수 있다. 새 실행은 task·도구 호환성·전송 자료·총 요청/토큰/시간 한도와 비용 주체를 구체화한 뒤 사용자 선택으로 분리한다. 이번 의견 검토로 무제한 벤치마크·유료 검색/공격 최적화·모델 교체를 배정하지 않는다.
