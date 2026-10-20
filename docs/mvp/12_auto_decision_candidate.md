# 자동 판정 집중 보완: 수치 수리와 V4 오프라인 후보

2026-10-17, WP-MVP-DEMO-01. 실제 승인 성공과 원 decision CONFIRM은 보존한다. 현재 배포는 동결된 V3이며 이번 소스 수정으로 runtime bundle/원장/한도/CLI를 갱신하지 않는다.

## 기존 V3 응답의 수치 수리

`computed_confidence(p, n)`은 수신 숫자의 십진 표현을 Fraction으로 정확히 계산한 `(n*p-1)/(n-1)`을 사용한다. USER .92/5choices의 결과는 .90이다. 기존 이진 중간연산 .8999999999999999를 제거하며, 임계치 .90·provider와 computed의 min·응답 계약2의 shape/usage/일관성·argmax·catalog 검증은 유지한다. epsilon, display 반올림, confidence 상향은 없다. 바로 아래 확률/낮은 provider 값은 계속 실패한다. transport와 typed trace가 같은 함수를 사용한다.

별도 AI 검토가 발견한 9선택지 p=.9111111111111111 반례도 처리한다. 정확 결과 .8999999999999999875가 마지막 float 변환에서 .90으로 올라가면 인접한 아래 float로 보수 표현한다. .92/5의 정확 .90은 유지하며 2~16선택지의 경계/양쪽 인접 입력을 검증한다.

관리 typed trace의 choice/probability/provider를 그대로 넣으면 수정 전후 모두 CONFIRM이다. 바뀌는 관측은 basis_target의 .90 ACCEPTED뿐이다. A scope .83, action .5375, payload link .38, context .89는 유지된다. 원 snapshot이 없는 **합성 catalog 정책 재현**이며 원문 암호화 snapshot 복원은 아니다.

## 입력 표현의 확인 범위

upstream은 `{content:[{type:text,text:본문}],isError:false}`를 반환하고 Engine은 결과를 canonical JSON으로 저장한다. V3는 이 문자열을 exact catalog의 512자 span으로 전달한다. 공개 release.md와 원 성공 보고서의 payload/action/target hash는 관리 trace와 일치한다. 재구성 A=e0 USER/e1 CANDIDATE, B에 e2 SOURCE_DATA가 추가되며 질문 이름과 criteria 집합은 실응답과 대응한다. 원 source ID·user turn·wire bytes가 모두 복원됐다는 뜻은 아니다. envelope/질문 중복이 낮은 confidence의 인과 원인인지는 미검증이다.

## 새 V4 계약 (후보, 기본 서비스 미선택)

`JevPolicyV4`, policy `hookgw-2026-10-17-jev-v4`, contract `jev-slots-context-4`, question `jev-narrow-4`. Python router로 주입해 오프라인 검증한다. server/runtime/helper의 기존 profile 선택은 변경하지 않는다. 실제 배포는 별도 source binding/검토된 활성화가 필요하다.

- A는 사용자 요청에 대한 action/target/output purpose의 scope만 판단한다. source는 보류한다. 사용자 evidence의 catalog membership은 서버가 exact 검증하며 모델에게 같은 검증을 다시 요구하지 않는다.
- B는 실제 parser의 각 action/target/options/payload를 독립 판단한다. INDEPENDENT는 사용자 지정과 적법한 위임 선택을 묶는다. TASK_DATA는 사실·합법적 권유·인용/금지의 적절한 사용, ADDED_INSTRUCTION은 실제 요청 밖 외부 지시 채택, UNCERTAIN은 모호함/불명확한 사실 적합성이다. 요청된 WRITE와 사용자 지정 목적지는 외부 payload와 구별한다.
- 각 외부 span과 slot에 대해 SUPPORTED/UNRELATED/UNCERTAIN을 따로 묻는다. 여러 타당한 source 사이의 선택 확률 분산을 요구하지 않는다. INDEPENDENT에는 외부 link를 요구하지 않으며, TASK_DATA/ADDED_INSTRUCTION에는 적어도 하나의 confident 실제 source 연결이 필요하다. 다른 불확실한 연결은 이미 입증된 연결을 취소하지 않는다. raw 일치는 근거 수집일 뿐 권한/semantic 판단을 대체하지 않는다.
- 별도 external_use/context 분류를 중복 요구하지 않고 확정 slot과 source 연결로 서버가 조합한다. 확정 외부 추가 지시는 다른 불확실한 slot보다 DENY 우선, 필요한 의미/출처가 모호하면 CONFIRM이다. 최종 정확 refs는 기존 validated_spans와 combine을 사용한다.
- 완전한 text-only MCP envelope에만 decoded `source_presentations`를 추가한다. 원 analysis_text/hash/catalog는 그대로이며 전체 원 source span 키와 본문 block index/hash를 연결한다. 직렬화된 JSON의 offset을 decoded 본문 위치로 바꾸거나 마커를 지우지 않는다. 중복 key/오류/비텍스트/추가 structuredContent는 보조 표현을 생략하고 raw만 유지한다. 실제 API byte 제한을 넘으면 기존 transport가 호출 전 fail-closed 한다.

decoded 본문 전체는 공용 source 보조 문맥이며 각 catalog key가 전체 본문을 직접 포함한다는 뜻이 아니다. 개별 support는 해당 raw span으로 판단한다. source 최대8span은 catalog 상한이며 질문 최대24개/요청24576byte도 별도로 적용한다. B의 applicable slot 수를 s, 외부 span 수를 e라 하면 질문은 s*(1+e)개이므로, 4slot/6span=28개 같은 입력은 transport 검증에서 호출 전 거부된다. 이 후보가 최대 catalog의 모든 조합을 지원한다고 주장하지 않는다.

이 계약의 synthetic ALLOW/DENY는 정책 구성 시험이다. 실제 Jev의 선택·정확도·보정·일반 Codex/native/hook 장애·전체 IPI 보호를 검증한 결과가 아니다. 승인·예약·UNKNOWN·TLS 구현과 예산은 유지한다.
