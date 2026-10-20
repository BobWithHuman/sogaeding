# MANAGEMENT_FOLLOWUP 좁은 별도 AI 검토

2026-10-18 KST. 구현 담당과 별도의 AI가 변경 코드, 보존 v1 source와의 실제 diff, 실제 준비 config 및 무모델 실행 증거를 읽었다. 이 검토 자체의 provider/actor/Jev 호출은 0이며 AgentDojo 작업은 하지 않았다. 코드·준비본·기존 서비스·키·장부는 수정하지 않았다.

## 결론

검토 범위에서 확정된 결함은 발견하지 않았다. 기존 v1의 `No findings`를 근거로 재사용하지 않았다. v1에서는 정확한 공개조회 후보가 코드 ALLOW를 모두 소진했지만, v2는 **정확 후보목록이 비어 있는 실제 conditional consent/2 설정**에서 서버 작업 scope/실제 자원 검사를 통과한 미열거 쓰기가 B LEGITIMATE effective .60 + A raw WITHIN_TASK로 의미 ALLOW되는 경로를 갖는다. 최종 source 재동결과 실행 결합 검사는 아래 조건을 충족한 뒤 통합 담당이 마쳐야 한다.

## 확인한 근거

- `runtime_demo.prepare()`는 15개 과업의 원 사용자 요청·실제 등록부·인증 principal에 scope를 발급한다. `runtime_grant()`가 실제 Controller와 준비 설정 시험 양쪽에서 같은 capability를 사용한다. task ID/공격 기대값/정답 후보로 새 허용 예외를 만들지 않는다. capability는 서버가 위임한 고정 root·도구 범위이고 후보의 업무 적합성은 별도 의미 판정이다.
- `task_scope.precheck/check_access`는 schema의 실제 target/options, 인증 주체, 범위, 보호 경로, owner, 각 조상 lstat, symlink/type, DAC, private content 동의 및 부작용 동의를 검사한다. 경로 `..`/비정규 표현 거부는 `RuntimeRegistry.resolve`에 이미 있으며, 새 metadata 경로 길이1024/깊이32 상한도 검토했다. 실제 접근 proof가 없거나 조회가 실패하면 의미 결과로 대체하지 않는다.
- `RuntimePolicy.evaluate()`는 scope 접근 결과를 `compose()`에 전달한다. exact `authority()`는 scope가 없는 이전 경로와 코드 공개조회 최적화에 남는다. `.50` 분기는 기존 .90 위험 DENY 뒤에 적용되며 B의 공식 effective confidence와 A의 raw 선택을 사용한다. 외부 출처·모델의 승인 주장은 scope 발급 입력이 아니다. 원 source hash/완전성 검사와 Jev 응답 검증은 유지된다.
- `runtime_services.control()`은 실제 grant에서 `ResourceProbe`를 연결한다. 고정 사설 OS API·Alice 인증·절대 `/usr/bin/python3 -I`·고정 metadata 코드만 사용하고 파일 내용은 읽지 않는다. 실제 원 MCP 구현의 `ask_for_permission=True`는 simulator 승인 후 업무 실행까지 계속하므로, 해당 옵션을 자동 consent로 취급하지 않는 보완이 타당하다. `search_files`의 원 shell 인용 방식에 맞춘 literal pattern 제한도 확인했다.
- `RuntimeEngine._forward_in_db()`는 `BEGIN IMMEDIATE` 안에서 정확 저장 candidate의 자원 proof를 다시 확인하고 기존 부모의 세션/연결/turn/정책/grant/source 검증 및 READY→EXECUTING 원자 전이를 호출한다. 소비된 정확 승인이 있어도 hard 범위 검사를 통과해야 한다. 승인 없는 CONFIRM·DENY 및 재사용은 실행할 수 없다. 원 UNKNOWN 미재시도 경로를 바꾸지 않았다.
- `prepared-reachability.json`의 실제 config, `tools/engine_demo_scope_probe.py`와 원 도구 구현을 대조했다. 정상3 CODE/Jev0, 대표 정상 중간 단계4 SEMANTIC, consent/2 exact operations0에서 미열거 `Annual summary` 쓰기1/동일 call 재사용 추가0을 기록한다. `/tmp` 수신자·SSH 비밀·셸 profile·미승인 삭제는 업무 upstream0이다. 보안 metadata API 조회는 업무 MCP dispatch와 구분한다. 첫 real-OS 실패와 r2 부분 재검증이 보존돼 있으며, 이를 최초부터 전부 통과한 것으로 보고하지 않는다.
- 로그에서 관련73 PASS, 최종 관련 통합121 PASS, lint PASS를 확인했다. 마지막 경로 한도 추가 이전의 121 결과임을 구분하며 해당 추가 반례의 좁은 재검증 결과가 최종 인계에 필요하다. `absolute-probe.json`은 실제 원 API의 절대/격리 Python metadata 검사 PASS/provider0이다. 별도 전수 회귀는 반복하지 않았다.

## 검토 source 고정값

아래는 이 검토에서 읽은 현재 source SHA256이다. 최종 동결 source의 대응 파일이 같아야 한다.

| 파일 | SHA256 |
|---|---|
| `src/app/benchmark/task_scope.py` | `35a0856945725a20c8f332cdd88d308a52c51e3a2500c601fb7999288d11c7a9` |
| `src/app/benchmark/demo_policy.py` | `dd88234d942b777a9616f014bfd3019b1312c5d7d810d9b5c5d7cffe4f778b68` |
| `src/app/benchmark/runtime_demo.py` | `4cf5ee7ab8ecb60142abedeb13ec8206fda0f6e6baef5007b8c1ea7b1facc3cd` |
| `src/app/benchmark/runtime_policy.py` | `def8822ff31550e67a9a0950f055539b70dc82c796b0823c08311ac134178c55` |
| `src/app/benchmark/runtime_services.py` | `e5074d096f3a5f1f5041a965f8791bda7ea92e9e25a578cf0ad3a42c31efbe61` |
| `src/app/benchmark/runtime_controller.py` | `4e19a58557143fb9f3df2cb0419f2671dac490fcff79bc399f311bd25b0b7955` |
| `scripts/dtap_official_runtime.ps1` | `a567e5ffa3501dae54169b497435bcd26fbe3c1711440b1209e8a186fd5af0ea` |
| `tools/engine_demo_scope_probe.py` | `6c00a252da9fc42f45800dc40659682205201f8cdc39867c64c53acb4a010bc5` |
| `tests/hookgw/test_engine_demo_scope_v2.py` | `7a4f34de3faa26070abd9be6c0e033d64e25481779a757a03b0aecf808def0c9` |

## 최종 인계 조건과 한계

통합 담당은 새 source 동결 후 manifest/plan/복사 가능한 launcher 명령/broker config/원장 binding의 동일 최종 hash, 위 source 일치, 기존 parent 보존, 15개 동일 task scope 및 실제 Engine DB configuration hash 결합을 무모델로 확인해야 한다. 도달성 증거의 `67efda...`는 최초 준비 config hash로 보존하고 최종 source 동결 hash로 오인하지 않는다. 새 지출 $1.80·기소비 포함 $5.089294·Actor GPT-5.2 low·실제 Jev 설정을 유지하고 유료 실행은 사용자 명령 선택 전 NOT_RUN이다.

마지막 metadata 검사와 원 MCP syscall 사이의 외부 변경 경쟁은 완전히 제거되지 않는다. mode/owner/보호 경로 분류는 모든 내용 기반 비밀 분류를 대신하지 않으며 일반 shell·복잡 편집은 자동 위임 범위 밖이다. 실제 Jev 정확도·actor 정상 완료·공격 효과·전체 ASR은 이 무모델 검토로 입증되지 않는다. 이는 별도 AI 검토이며 공식 독립 진단·전수 가이드 적합성·모든 native/모든 IPI 보호 검증이 아니다.

## 후속 조건 확인 — 동일 검토의 최종 증거 보완

2026-10-18 KST. 두 번째 전체검토나 시험 재실행 없이 최종 결합 증거와 validation-only delta만 확인했다. 제품 소스의 위 검토 hash는 유지된다. probe는 원 MCP 쓰기 후 별도 정확한 `read_file` 후보도 Engine authorize/forward를 거쳐 읽고 `Annual summary` 실제 내용을 확인하도록 보완됐다. test는 해당 `actual_content_verified`를 확인한다. 표의 두 validation 파일 hash를 이 최종 상태로 갱신했다. 최초 검토 hash는 각각 `34e5ad209b90c995ba37e3d3836f4e441e5f5e377493a95108e67f6ead1a0e82`, `679b4f8e579f440ba4371ac798e63398d172767b57eb2e9f882848e6bfff7928`이다.

`real-os-readback.log` PASS, `prepared-reachability.json`의 actual content/readback1, `post-review-narrow-tests.log` 32 PASS, `post-review-lint.log` PASS를 확인했다. 좁은 재검증은 마지막 metadata bounds 반례와 이 증거 보완을 포함하며 기존 121 통합을 반복하지 않는다.

`verify_final.py`의 실제 검사와 산출물 `final-bindings.json` PASS를 대조해 앞의 최종 인계 조건 충족을 확인했다: 최종 manifest **`338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8`**, 동결/current source81 일치, 최초 준비와 동일한 15 scope·exact grants, 7개 실제 Engine DB configuration hash와 최종 grant/policy 결합, broker config·manifest·원장 binding 일치, parent의 reservations/settlements/resources 보존, 누적상한 $5.089294 및 provider0이다. 기존 `67efda...` 도달성 증거와 최종 manifest는 동일 scope/grant로 연결된다. 최종 실행 명령의 hash는 이 값을 사용해야 한다. 실제 유료 실행·모델 정확도는 계속 NOT_RUN이며 위 한계와 결론은 유지한다.
