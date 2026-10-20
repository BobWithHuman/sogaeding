# 사용자가 실행할 준비 확인 명령

현재 **전체 유료 실행 준비 미완료**다. 실제 actor/Jev/환경·judge 호출·서비스 교체 없이 아래 고정 명령으로 동결 상태를 확인한다.

```powershell
Set-Location -LiteralPath C:\sogaeding
.\scripts\dtap_eval.ps1 -Mode check -ManifestSha256 343bac491c239b5ead01cf0df9ab2951a2af18718a1dc0a9243dd5af8c780306
```

기대: `NOT_FULL_EXECUTION_READY`, task6682, runtime_ready0, paid_calls0와 구체적 차단 사유. network none·read-only이며 사용자 키 mount가 없다. `-Mode run`도 동일 manifest에서는 `FULL_RUN_DISABLED`로 종료한다. 전체 유료 평가를 실행할 명령으로 오인하지 않는다. 지금 비용 승인이나 시험 호출은 필요하지 않다.

검토할 파일: MANIFEST.json/sha256, EVALUATION_DESIGN.md, COVERAGE.csv, TOOL_COVERAGE.csv, DOMAIN_EXPANSION.csv, 별도 REVIEW.md. full run을 개방하려면14도메인의 실제 schema/slot·환경·주입·native·judge·추가LLM 한도를 연결하고 새 manifest에 별도 검토 및 사용자 유료 선택을 받아야 한다. 소수 유료 pilot/성공후보 replay로 전수 비교를 대체하지 않는다.

무모델 연결 원증거는 `C:\sogaeding\artifacts\20261017-dtap-prepare\final-*`다. 재실행은 개발 검증에만 해당하며 기존 폴더/claim을 재사용하지 않는다. 가짜 actor/Jev이므로 실제 모델 방어율을 산출할 수 없다. 기본 제품 런처·서비스·과거 원장에는 이 명령이 접근하지 않는다.
