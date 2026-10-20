# 필수 원문과 이번 변경의 적용성

원문5개 SHA와 PDF 페이지18개는 `artifacts/20261017-mvp-semantic-confirm/guide-pages.json`에 추출했다. 페이지는 파일의 1-based PDF 페이지다. 설계20/약점49의 기존 적용성 장부를 유지하며 이번 delta만 갱신한다. 전수 진단 완료/공식 조치율을 주장하지 않는다.

| 원문 | 위험과 통제 | 코드·검증 |
|---|---|---|
| G4 PDF24,37~39 / G3 PDF507~509 | 보안기능 입력·인증/접근통제·중요 기능 재인증. actor의 승인 위조·오래된 승인·RPC 변경·경쟁 | demo_approval/engine/server, 별도 human CLI, 정확 binding/30초/동일 transaction. test_semantic_confirm_dispatch 및 실제 gateway58 |
| G3 PDF507~508 | 작업 데이터와 권한 혼동, 원문 위치 위조, 의미 불확실성 | jev_semantic_v3: 배타적 질문·slot별 USER/TASK_DATA/GENERATED, 정확 catalog/ref와 기존 grant 유지. v3 정책시험·독립56 |
| G2 PDF133,135,137 / G3 PDF511 | 민감 오류 노출·예외 시 fail-open | file_errors/upstream/MCP: 고정 FILE_NOT_FOUND/OBSERVED_ERROR, 결과 유실 UNKNOWN 보존. 실제 gateway 파일부재/응답유실·adapter 검증 |
| G2 PDF146 / G3 PDF415 | 무제한 승인 대기·중복 유료 분석·중복 실행·자원 해제 | bounded600초/720초/1800초, 같은 intent dedup, CLI lifecycle, typed terminal stop. 실제 gateway58와 독립승인58 |
| R1 PDF14 / G1 PDF35~38 | 변경·공급망 무결성/검증 증거 소실 | 새 외부 도구·이미지·의존성 없음. 기존 pinned gateway/image 재사용, source/bundle SHA·원 ledger/manifest/claim 보존·최초 실패/조치/재진단 인계 |

이번 변경에 직접 해당하는 설계 항목은 시스템 자원/보안기능 입력 검증, 인증·권한/중요 기능 접근, 오류 처리와 자원 제한이다. 약점은 입력 검증 부재, 부적절 인가/인증, 경쟁, 오류 정보 노출, 예외 처리, 무한 대기/자원 미해제에 대응한다. SQL은 기존 parameter binding, 암호화/TLS/원자 예약은 유지하며 새 키·암호 알고리즘·웹 로그인/쿠키·업로드·XML/LDAP/역직렬화·브라우저 렌더링 엔진·native binary를 추가하지 않았다. 해당 경로의 기존 P0는 배제하지 않았고 이번 비변경 영역의 새 전수 PASS도 부여하지 않는다. 동일 OS 사용자/일반 native hook 사망·전체 TLS negative·키 수명·전수 공급망 진단은 기존 미완료로 남는다.

평가기준 연결: 요청→위험(권한 혼동/유료 반복/중복효과)→위 통제→정적 검사→가짜 provider+실제 gateway 동적시험→독립 발견 SC-SEM-01/SC-APP-02/SC-START-03→수정/재진단. 최초 fixture/포트/마운트 실패도 원증거를 보존하며 미실행을 안전 PASS로 합산하지 않는다.
