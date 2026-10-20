# 자동 판정 후보 별도 AI 보조 검토

2026-10-17. WP-MVP-DEMO-01/AUTO_DECISION_NEXT_PROMPT.md와 with-human-dev에 따른 코드/증거 검토다. 추가 사람 또는 공식 독립 진단이 아니다. 제품 유료 요청·CLI start·키 읽기·원 runtime/원장 접근·한도 변경·배포·모델/추론 설정 변경은 0이다. 검토자는 제품 소스를 수정하지 않았다.

최종 판정: **좁은 오프라인 변경 수용 가능**. P2 1건 조치·재진단과 최종 통합 증거 확인을 마쳤고 미해결 차단 발견은 없다. 현재 배포의 자동 ALLOW/실제 공격 차단 또는 V4 활성화 수용을 뜻하지 않는다.

- P2(조치 완료): 최초 `computed_confidence()`는 Fraction→float 변환에서 .90 미만을 .90으로 올렸다. 9 choices, p=0.9111111111111111, provider=.90의 정확값 `71999999999999999/80000000000000000`(.8999999999999999875)이 float=.9/ACCEPTED였다. 수정 전 반례는 `probe-before-fix.json`에 보존했다. 작성자가 정확값보다 큰 십진 float 결과에만 nextafter로 한 단계 낮추도록 수리한 후 동일 독립 반례는 .8999999999999999/LOW_CONFIDENCE다. .92/5=.90 ACCEPTED는 유지한다. 독립 2~16 choices 경계 및 인접45개 입력의 정확 유리수 비교는 모두 일치했고 결과 표현도 정확값을 넘지 않는다(`probe-final.json`, exit0).

V3 baseline 3개 대비 변경은 shared confidence 계산 도입과 V3의 build/compose hook뿐이다. 초기 manifest 7개 해시는 모두 일치했다. V4는 별도 module이며 runtime/server profile에 선택되는 참조를 찾지 못했다. 원 기존 V3 선택/확률/provider를 그대로 넣는 정책 재현은 CONFIRM을 유지하며 실제 snapshot 복원을 주장하지 않는다. 원 실제 읽기/승인 단회소비/resumed1/쓰기 OBSERVED는 관리 observation에 보존돼 있다.

V4 검토에서 raw source/catalog/hash/원 exact span offset은 유지되며 decoded text-only envelope는 보조 표현으로만 추가된다. A는 source presentations/외부 자료가 없고 B만 출처를 받는다. 추가 지시가 연결된 target와 불명확 payload의 조합은 DENY, 추가 지시 action의 source 연결이 낮거나 target basis confidence가 낮으면 CONFIRM이라는 독립 오프라인 반례를 실행했다. 이는 synthetic composition 검증이며 실제 Jev의 의미 정확도 증거가 아니다.

분할 envelope의 decoded blocks는 전체 source 문맥을 모든 원 catalog key와 함께 보여준다. 검토 의견 후 metadata/질문에 전체 보조 문맥이 각 key의 직접 내용은 아니라는 문구가 추가됐음을 확인했다. 실제 support 질문과 raw evidence는 개별 span을 대상으로 하며 결정적인 권한 우회로 입증한 항목은 없다. 현 24 question cap 때문에 4 applicable slot×6 source span은 28질문으로 입력 fail-closed가 된다는 크기 한계는 docs/mvp/12에 명시되고 key 미존재·예산DB 미생성·network0의 거부 시험이 추가됐다.

작성자 증거 확인: 최초 관련86 PASS/통합672 PASS(85.45초)에서 발견한 P2를 고친 뒤 관련102 PASS, 최종 통합 **688 PASS/84.44초**, Ruff/Bandit exit0. 최종 integrated-command.json의 exit0와 실행 시각/명령을 확인했다. 검토자의 독립 probe는 network none/read-only Docker에서 실행했다. 최초 Docker 접근권한·import 경로·보조 파일명 inspect.py의 표준라이브러리 충돌 실패는 보존했고 이름을 manifest_probe.py로 고친 뒤 재진단 성공했다. 기존 원 runtime·키는 마운트하지 않았다. 최종 manifest7개는 `manifest-final.json`에서 실제 파일 해시와 모두 일치했다. 작성자의 `final-preservation.json`도 mismatch0이며 원 성공 normal.md·관리 observation/typed trace의 최초 SHA 보존 기록을 확인했다.

R1/G1 공급망·G2 외부입력/예외·G3 p507~508 SR1-9·G4 p24/38의 기존 추출 페이지와 원 PDF hash 증거 `guide-pages.json`을 확인했다. 입력 검증·서버 권한·실행 전 예약·UNKNOWN/TLS·기존 동작 보존 범위의 좁은 검토이며 설계20/약점49 전체 재진단 또는 미검증 항목 PASS 판정은 아니다.

실제 정상 자동 ALLOW/실제 공격 DENY, 일반 native/hook 사망 경계, 모델 보정/정확도는 NOT_RUN이다. 최종 후속 제안은 4 API 요청/추가 CLI0회(작업서 상한≤1)이며 미승인·미실행이다. 전체 이력 누적17요청/예약1088000의 제안만 준비했으며 예산은 갱신하지 않는다. 개발 AI 토큰 사용은 제품 유료 요청0과 별개다.

최종 source SHA256: jev.py `8e6d7141e4f55c968a843899da65e3756c2d7419e9fd858bf6b394dd2393fb05`, jev_policy.py `2dfbd061d28636cd3f4a0130dc54a281eccd5a27bba1ddefd74588aeafb1c189`, jev_semantic_v3.py `011c25d85589d0e462d5bdcac9cb21f3a2e00a0678d50c88d93056443a59dda9`, jev_semantic_v4.py `f901476c911e9c9729d1acc0a3b4e131c284a3b3a8909f163714eeab9ece98fa`. 시험/문서 포함7개는 `manifest-final.json`, 검토 artifact/report hash는 `review-evidence-hashes.json`에 보존한다.
