# 헤더 누락 SSE — v3 단회 확인

> 이후 사용자 v3 실행은 COMPLETED/HEADERLESS_FULL_SSE/usage12·5로 확인됐다. 아래 진단 명령은 소비됐으므로 반복하지 않는다. 현재 단계는 [상위 USER_RUN.md](../USER_RUN.md)의 stream1 DTAP 재개다. 아래 준비 안내는 역사 기록이다.

v2 실제 결과는 HTTP200·Content-Type 비어 있음·본문SSE/6357bytes였다. 구버전이 MIME만으로 거부한 지점을 수정했다. 실제 응답의 최종 완료/모델/사용량은 저장되지 않아 소급 확정하지 않는다. 원 v2 claim/result는 보존한다. 새 공유 파서는 MIME 누락일 때도 전체 SSE 구조·완료1회·정확 모델·정수 사용량·EOF를 모두 검증해야 수용한다. 명시적으로 다른 MIME·불완전/잘못된 이벤트는 계속 거부한다.

사용자가 선택해 새 공개 문장 `Reply with exactly CONNECTED.`의 Responses POST 최대1회를 실행한다. 이전 READY/OK 요청이나 DTAP UNKNOWN을 재전송하지 않는다. 계정/모델/low·API키 fallback금지·요청60초/응답2MB를 유지한다.

```powershell
& C:\sogaeding\artifacts\20261020-siwc-protocol-probe-v3\bundle\scripts\siwc_protocol_probe.ps1 -SendOneRequest -ManifestSha256 1ebfcfe637b58e7af67fcb2e05d1a88543145a1a238456c8790573dccdb0d290
```

안전한 JSON 결과만 전달한다. 오류/UNKNOWN이면 명령을 반복하지 않는다. 저장 위치는 `artifacts/20261020-siwc-protocol-probe-v3/user-one-request-3/result.json`이다. COMPLETED가 나와도 이 공개 문장의 연결 성공이며 DTAP 방어 성공은 아니다.

로그인main·Luna low·기존 trusted model-check metadata를 사용하고 필요시 정상OAuth refresh만 수행한다. API키·Jev·DTAP 도구·소켓·다른모델은 사용하지 않는다. 플랜 사용량은 실제 소비될 수 있으며 timeout/실패에서0으로 확정하지 않는다. 출력토큰 hardcap은 없다. 토큰/응답본문/임의오류는 로그에 기록하지 않는다. 보호된bundle만 실행하며 host ACL/hash 검사와 단회claim을 유지한다.

검증: 관련91PASS/역사동결검사1제외·lint·실제UID 무모델 preflight와 실제worker/가짜credential/헤더없는loopback HTTP 전체main PASS. 개발 중 실제 모델/계정API 호출0이다. 실제v3 모델 확인은NOT_RUN이며 전체DTAP 재개본은 아직 만들지 않았다.


## 이후 관측

사용자 v3 실행이 COMPLETED/HEADERLESS_FULL_SSE/usage12·5로 확인됐다. 이 단회 명령은 재실행하지 않는다. DTAP 재개는 상위 USER_RUN.md의 새 stream1 명령만 사용한다.
