# 로컬 대시보드 연동

2026-10-28. 엔진의 실제 판정·실행 이력을 조회하는 대시보드다. 실행·설치는 루트 README, API·인증·DB 계약은 [백엔드 기준서](BACKEND_REFERENCE.md)를 따른다.

## 화면과 실행 경계

- 팀원 원본: https://github.com/BobWithHuman/sogaeding_dashboard
- 반영 기준: `2f6bbb33b289fbd57ec950261e541a72b03b0df0`.
- `src/app/web/observatory/`의 HTML/CSS/JavaScript를 기존 FastAPI 로컬 중계에서 제공한다. Node 빌드나 추가 YAML은 필요 없다.
- 브라우저는 같은 origin의 `/dashboard/v1/*`를 조회한다. 중계가 서버 측 토큰과 CA로 Control에 인증한다. 브라우저에 엔진 토큰·원문 DB를 전달하지 않는다.
- 원본 저장소와 공개 Sites 게시물을 수정하거나 재배포하지 않는다.

## 이번 변경

- 팀원의 디자인·차트·이력 상세를 적용하고 실제 엔진 API에 연결했다.
- 가짜 이벤트·통계를 만드는 Demo mode를 제거했다. ENGINE과 합성 검증용 ENGINE_FIXTURE는 구분한다.
- 기간·세션·도구·판정 필터, 페이지 조회, 상세 타임라인, ASK 이력, 보안 감사와 새로고침 정지/재개를 연결했다.
- npm 도구 4종을 필터와 읽기/쓰기/실행 구분에 추가했다.
- npm 설치는 신뢰된 transport에 기록된 숫자 종료코드로 결과를 표시한다. `0`은 SUCCEEDED, 그 외는 REPORTED_ERROR, 없거나 형식이 잘못되면 UNKNOWN이다. stdout/stderr와 변경 본문은 공개하지 않는다.
- 코드 검사만 수행한 후보의 Jev 상태는 NOT_RUN으로 표시한다.

ALLOW는 실행 허용이며 실행 성공과 다르다. ASK의 최초 판정과 사용자 응답 이후 최종 판정도 구분한다. 대시보드에서는 ASK 답변·승인·재실행·정책 변경을 하지 않는다. 사용자 응답은 에이전트의 네이티브 질문 양식에서 처리한다.

## 실행

기본 제품은 루트 README의 prepare/up 이후 실행한다. 이미 만든 runtime은 prepare를 반복하지 않는다.

```powershell
.\scripts\dashboard_local.ps1 -RuntimeName local
```

```sh
python3 tools/product_local.py dashboard --runtime local
```

기본 주소는 `http://127.0.0.1:8150/`이다. npm 시연은 별도 프로필이므로 [npm 시연 안내](../../demos/npm-tls/README.md)의 product_codex dashboard 명령을 사용한다.

## 검증과 한계

2026-10-28 로컬 연동 당시 대시보드/npm/gate-6/Codex 관련 시험 95개를 통과했다. 실제 npm 시연 runtime의 정상 ALLOW 이력, 설치 실패/성공, 공격 시도 DENY 상세·필터·타임라인 조회를 확인했다. 이 조회 검증 자체에서 모델이나 npm 설치를 새로 실행하지 않았다.

공유 전에는 기존 Git 기준에 이번 공유 파일만 반영한 별도 사본에서 대시보드/npm/Codex/Jev/gate-6/ASK/POSIX/보안/transport 시험 189개를 통과했다. 별도 TLS 통합 서비스가 필요한 3개는 skip이다. 네트워크와 실제 자격 없이 실행했으며 실제 모델·Mac UI 시험은 아니다. JavaScript·PowerShell 문법과 Python AST 검사도 통과했다.

- 오류를 0건이나 ONLINE으로 바꾸지 않는다. 현재 화면은 5초 polling을 사용한다.
- 에이전트 신원은 미수집이므로 `unknown`, Gateway/Upstream 실시간 생존 상태는 probe 미구현이므로 UNKNOWN이다.
- 인과 그래프와 오탐 태깅은 현재 기능이 아니다. 상세의 출처 메타데이터·타임라인과 구분한다.
- 대시보드 연동은 판정 임계값·권한·DB 스키마를 변경하지 않는다. npm 도구 지원을 위한 엔진 어댑터 변경은 별도다.
