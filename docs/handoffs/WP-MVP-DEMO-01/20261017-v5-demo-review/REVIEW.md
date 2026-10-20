# V5 시연 통합 별도 AI 검토

2026-10-17. 구현 담당과 분리한 AI 검토 1회다. 사람 추가 개발자나 공식 보안 진단이 아니다. 관리 최종 수용/DONE 판정은 별도다.

## 결론

검토한 최종 후보에 차단할 발견 사항은 없다. `DEMO_PREPARED` 범위로 인계할 수 있다. 사용자 실제 Codex·Jev 시연, 정상 자동 판정, 일반 native/hook 사망 경계, 전체 MVP·전수 보안 완료는 확인하지 않았다. 실제 유료 모델 호출0·actor CLI 시작0·기존 서비스 변경0이며 원 키 본문 읽기/복사0·원장 쓰기0이다. 개발 AI 검토에는 토큰을 사용했다.

검토 manifest: `bf656becbe6ed3344e133cd86c2c62234d082c0e5ee5b37679dbcb783b46b33d`. [binding-review.json](C:/sogaeding/artifacts/20261017-v5-demo-review/binding-review.json)에서 동결 소스64개/최종 변경 후보13개가 현재 hash와 모두 일치한다. 원 V4/V5 결과·manifest, 역사 ledger5개, CLI claim3개, V3 정상 성공 파일의 보존 항목14개는 변경 전/후 hash와 모두 일치했다. 새 V5 provider ledger/episode4 claim은 없고 policy.enabled는 실제 boolean false다.

## 확인한 경계

- 실제 diff13개와 원본을 읽었다. server의 명시 `behavior_v5`는 표준 `JevClient`/`JevPolicyV5`로 연결되며 V2/V3 profile을 보존한다. V5 질문·조합/.90·Engine·승인DB 계약은 변경되지 않았다. `hookgw_bundle`은 제품 src/계약만 동결하므로 시험 전용 `mvp_semantic_probe`의 저장 답 oracle/MockTransport/고정 후보는 live bundle에 들어가지 않는다.
- 기존 `mvp_demo.ps1`→`mvp_demo.py`→`mvp_semantic_followup.behavior_*`를 설정해 재사용한다. 새 제품 runner/UI/평가경로를 만들지 않는다. compose의 프로젝트명·8036/8046·runtime/bundle/DB/workspace/config/ledger가 독립적이며 원 Jev key는 기존 RO mount다. 기존 서비스/성공 보고서를 교체하지 않는다.
- 정확 manifest·현재 공개 소스/실행 image·부모 역사 원장/CLI 종료·자료 원문·grant/profile·정책/설정이 시작 전에 결합된다. 새 한도는 정확히 Jev4/256000·CLI1/전체4·1800초·역사25/1600000·demo20/1280000이며 명시 사용자 start 이전 disabled다. 기존 소진 원장 증액/초기화/환불 경로가 아니다. 원자 파일생성 claim으로 episode4는 경쟁 중에도 1회만 소비한다. 실패·중단은 claim을 보존한다.
- watcher의 V5 host 선택은 기존 사람 인증 채널을 재사용한다. 사용자 안내에 번호→정확 후보→approve/reject, Enter의 전송 없는 취소, 호스트 Allow와 PDP 승인의 차이가 있다. 동일 대기 RPC의 정확 승인 단회 재개·Jev 추가 분석0, DENY 승인 불가·거절 효과0·UNKNOWN 재시도 금지를 실제 gateway 재현 증거와 기존 구현으로 대조했다.
- viewer는 `USER_DEMO`와 `OFFLINE_REPLAY`, HUMAN_CONFIRMED·자동 정상 관측·분석실패·미시도·UNKNOWN을 구분한다. 자료는 판정 입력이며 인과 미입증으로 표현한다. 후보 차단 표시는 실제 파일·upstream0 관측과 따로 대조하도록 안내한다. HTML escape/CSP가 유지된다. history는 나중 공개 소스 drift에서도 읽히며 새로운 start는 거부한다.
- USER_RUN의 start/history/watch 명령이 실제 wrapper 인자·revision·hash·한도와 일치한다. 준비·inspect·check의 실제 PowerShell5.1 결과는 disabled/JEV_RULES_ONLY·무모델 READY다. READY를 실제 모델 접근 성공으로 표시하지 않는다. 사용자 자연어 과업2개에는 고정 공격 후보/기대 DENY/평가 oracle이 없다. 위험 후보가 없으면 미시도이며 반복 유도하지 않는다.

## 실행·증거 검토

구현자의 실제 TLS agentgateway→V5 PDP→예약→파일 executor 재현 64/64 PASS의 [evidence.json](C:/sogaeding/artifacts/20261017-mvp-semantic-v5-demo/gateway-1/evidence.json)을 확인했다. 저장 V5 A/행동 확률을 재현하되 새 fixture의 정밀 귀속은 합성 UNCERTAIN이고, 높은 정상 자동 ALLOW는 별도 합성 답이다. 정상 승인/거절·중복 RPC/추가 모델0·변조·DENY 금지효과0·PDP503·전달 유실 UNKNOWN을 확인한 구현 경계 증거이며 실제 actor/모델 정확도 증거가 아니다.

관련 통합은 193 PASS/3 FAIL 후 원 V2 관측파일 RO mount를 보완하여 해당3개를 재실행해 3 PASS했다. 실패 원인·최초 로그를 보존했다. 최종 strict 숫자 변경 뒤 관련45 PASS, PowerShell5.1 fake-helper13 PASS를 대조했다. Ruff PASS. Bandit은 Low10/Medium7이 남으므로 도구 진단 전체 PASS로 바꾸지 않는다. 원진단은 [static-summary.json](C:/sogaeding/artifacts/20261017-v5-demo/static-summary.json)과 raw 로그에 있다. 고정 서버 listener/fixture tmp·검증된 argv subprocess 등의 맥락을 검토했으며 변경 경로의 새 차단 결함은 확인하지 못했다. 전수 보안 수용을 대신하지 않는다.

별도 작성한 [test_independent.py](C:/sogaeding/artifacts/20261017-v5-demo-review/test_independent.py)는 **13 PASS/4.55초**다. 12경쟁에서 episode4 claim1회, 잘못된 manifest 활성/claim0, 공개 source drift history/start 분리, enabled 엄격 boolean, 이미 소비된 check 비활성, 위조 모드/HTML 및 분석실패·미시도 표시를 추가 확인했다. 실행은 Docker network none/read-only/cap-drop/no-new-privileges, 모든 소스 RO와 /tmp만 쓰기, 원 key·runtime·실원장 mount0이었다. 첫 sandbox Docker pipe 접근은 거부됐고 같은 무네트워크 명령을 승인된 실행 경로에서 실행했다. 자동 안전검토 거절이나 제품시험 실패가 아니다. [정확 명령](C:/sogaeding/artifacts/20261017-v5-demo-review/independent-command.json) · [출력](C:/sogaeding/artifacts/20261017-v5-demo-review/independent.txt).

## 필수 기준과 한계

필요 원문은 기존 [guide-pages.json](C:/sogaeding/artifacts/20261017-auto-decision/guide-pages.json)의 원 PDF hash/해당 페이지 발췌를 재사용해 읽었다. R1 PDF14/G1 PDF35–36의 통합·무결성·검증은 소스/image/profile 동결과 별도 검토에, G3 PDF507–508 SR1-4/5/6/9는 경로/argv·사람권한·입력형·HTML 처리에, G2 PDF128/129/135/137 및 G3 PDF510/G4 관련 상태·인증 보호 기준은 단회 claim/기존 승인·UNKNOWN·bounded lifecycle/typed 오류/키 분리에 연결했다. 새 외부 인터페이스는 독립 demo revision의 기존 TLS listener와 RO key 참조이며 호스트 전체 보호로 확대하지 않는다. 기존 설계20/약점49 적용성 정본은 변경하지 않았으며 이번 검토를 전수 PASS로 표시하지 않는다.

다음 단계는 사용자 선택의 고정 start1회와 history 수집이다. 실제 실행 전까지 DEMO_VERIFIED가 아니며 추가 유료 재시도·공격 유도·임계치 하향·A 삭제 권한은 없다.
