"""Create the assigned WP-MVP-01 draft handoff; never edit management state."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RID = (ROOT / "artifacts/wp-current-run.txt").read_text().strip()
OUT = ROOT / "docs/handoffs/WP-MVP-01" / RID
ART = ROOT / "artifacts" / RID


def table_rows(text, prefix):
    result = []
    for line in text.splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(prefix, cells[0]):
            result.append(cells)
    return result


def write(name, text):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(text.strip() + "\n", encoding="utf-8")


def main():
    now = datetime.now(UTC).isoformat()
    files = []
    for area in ("src/app", "tests/backend", "tests/acceptance", "tests/web", "tests/transport", "docs/mvp"):
        files.extend(p for p in (ROOT / area).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    files.extend(ROOT / name for name in ("compose.yaml", ".env.example", ".gitignore", "README.md",
        "scripts/dev_docker.ps1", "scripts/run_codex_live.ps1", "scripts/product.config.toml.template",
        "scripts/create_control_session.py", "tools/prepare_tls.py", "tools/product_auth_smoke.py",
        "tools/reconcile_product.py", "tools/supply_chain_inventory.py", "tools/collect_live_evidence.py"))
    manifest = [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))]
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (ART / "source-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (ART / "source-fingerprint.txt").write_text(fingerprint + "\n", encoding="utf-8")
    write("SECURITY_DESIGN.md", f"""
# WP-MVP-01 보안 설계·구현 근거

run_id: {RID}; 작성 {now}; PLAN-2, MVP-SPEC-3, policy mvp-2026-10-13-v1.
작성자/모델·DB·실행 설정 통합 소유자: 이 개발 AI 세션 1개. 사람 개발자는 사용자 1명이다.

사용자 위임, 세션 토큰, 승인, 모의 게시 저장소, 원문 digest와 이력이 자산이다. 외부 이슈·도구 인자는 불신 데이터이며 사용자/출처/승인 라벨을 발급하지 않는다. 권한은 SUMMARIZE_ISSUE 또는 POST_COMMENT와 고정 이슈·정확한 본문에서 서버가 구성한다. 실제 비밀·실제 GitHub 게시를 사용하지 않는다.

| 경계·외부 인터페이스 | 인증·허용 대상·통제 | 실패·한도 | 코드·시험 |
|---|---|---|---|
| 호스트/브라우저/런처→Control 8000 | HTTPS 앱 CA·hostname 검증; 사용자 bearer. /healthz·빈 shell·정적 JS만 공개. 내부 API 거부 | 32KiB·깊이16·중복 key/header·Origin/Host 검사; 실패 인증 제한 | control/main.py RequestGuard, scripts/create_control_session.py; 실제 TLS·AT-11/13 부분시험 |
| Codex/REPLAY→Gateway 8001/mcp | SDK2.3 opaque session bearer; scopes tools:invoke·정확한 HTTPS audience·만료; dispatch 때 resolve 재확인 | stateless MCP·32KiB; 추가 필드/타입/enum 먼저 거부 | gateway/main.py StrictServer/SessionVerifier; actual MCP expired/audience·tool-schema |
| Gateway→Control 8443 | 서버 CA/hostname 검증+mTLS client 인증+service bearer; URL 고정·redirect/proxy 상속 없음 | 요청1초·위험 쓰기 자동 재시도 없음 | gateway/client.py; TLS failure executor0 |
| Gateway→private DemoExecutor/등록 fixture | 공개 실행 API 없음; 스키마→check→reserve 성공 뒤 동일 args 사용 | executor2초·예약 시작30초; SECRET_ENV 진입0 | executor/demo.py; NT-02·AT-01/02/14 |
| 서비스→SQLite/런타임 파일 | 서비스별 volume·파일600·키 분리; 요청/정확한 인자/출처 발췌/event/댓글 Fernet 암호화; token은 secrets 생성+SHA256 검증용 digest | BEGIN IMMEDIATE·call8/write1·단회 승인; 결과 유실 UNKNOWN·budget 반환 없음 | storage/repository.py; atomic call/write race·approval race·report loss |
| Codex→OpenAI | host 환경 API키·정상 HTTPS 검증; 전용 CODEX_HOME·가짜 workspace; 사용자/서비스 토큰 child 미전달 | 정상1+공격1, gpt-5.6-luna, CLI0.154.0, rawJSONL 미보관 | run_codex_live.ps1; live-*-verified.json·실제 effects 대조 |

위협→구조적 예방→실측: SEC-01/03은 등록 file ID와 private executor 단일 경로로 경로 조작·임의 명령·비밀 읽기를 제거한다. SEC-02/04는 서버 발급 grant와 외부 출처 분리로 trusted/approved 자가 선언이 권한을 만들지 못하게 한다. SEC-05/06은 canonical UTF-8 JSON digest, 불변 call, 승인의 정확한 digest/expiry/정책 결합과 한 DB 트랜잭션의 예산/소비로 인자 교체·TOCTOU·중복 게시를 제한한다. SEC-07은 실행 전 audit/PDP 실패를 차단하고 실행 후 불명 상태를 UNKNOWN으로 보존한다. SEC-08/10은 역할·세션별 API, 비밀 마스킹, 안전한 오류, 암호화 저장, UI textContent로 이력 유출·저장형 XSS를 줄인다. 관련 실제 시험은 product-final-tests.txt와 product-traces.json에 연결한다.

코딩 표준: 입력은 checked-in JSON Schema와 strict JSON으로 검사한다. SQL 값은 parameter bind, 식별자는 고정한다. 정책에 eval/exec/shell/pickle/YAML object를 사용하지 않는다. URL/파일 경로는 도구 입력으로 받지 않는다. 난수는 secrets·검증된 cryptography API를 사용한다. httpx와 SDK httpx2 타입을 구분하고 CA 검증·timeout·context manager를 강제한다. 동적 외부 문자열은 DOM textContent, 오류는 allowlisted code만 사용한다.

원문 근거: G2 PDF15(SQL bind), 70~71(보안결정 입력); G3 PDF159~160·510(TLS), 406(TOCTOU), 511(오류/세션); G4 PDF22~24·37~39(SDLC/설계20); R1 PDF13~14(전주기), G1 PDF45~47(SBOM); C1 PDF14~15·26(정적/동적·구조예방). 원본 해시·페이지 재추출은 guide-original-read.json과 guide-pages/이다. 전체 가이드 전수 준수 PASS는 아니다.

기획서 제2항용 근거: 등록 MCP 집행 경계→strict registry/PDP/private executor→금지 호출0; 정확한 위임·단회 승인→원자 reserve→경쟁 효과1; TLS 역할 분리·토큰 digest·암호화→실제 MCP+LIVE 인증/비밀 검색; 오류→UNKNOWN/명시적 receipt reconciliation→추가 효과0. 행동 출처 이력은 SBOM이나 인과 증명이 아니다.

잔여 P0·검증: 기본24시간 보존/폐기 구현, 인증서 재발급/키회전·복구 절차의 실제 재현, Gateway 인증 flood/자원 부하, 실제 UI 브라우저 XSS/승인 조작, 제품의 만료/잘못된 client cert 전체 matrix, PDP timeout/malformed/source 저장 실패의 전체 동적 fault matrix, 새 PC 재현, OS 이미지 CVE·license/고지 완전성, 20/49 원문 항목별 전체 수동·별도 검토가 남는다. 실행 경로를 보호했다고 이 미확인을 PASS로 바꾸지 않는다. local-ingress는 호스트 공개를 위해 추가했고 OS outbound 전체 차단은 없다. CA/leaf는 7일/2일이며 만료 시 fail-closed, CA 개인키는 보관하지 않는다. Windows ACL은 사용자/SYSTEM만 허용하며 실제 read 재확인 후 기록한다.

보호 범위는 등록 MCP 3도구뿐이다. 같은 OS 계정/관리자에 의한 코드·DB 직접 접근, Codex 내장 셸/파일, 다른 MCP, 모든 IPI, 사용자 PC 전체의 보호는 주장하지 않는다.
""")
    plan = (ROOT / "docs/plans/03_guide_compliance.md").read_text(encoding="utf-8")
    design = table_rows(plan, r"SR[1-4]-\d+")
    weaknesses = table_rows(plan, r"W-\d\d")
    assert len(design) == 20 and len(weaknesses) == 49
    lines = ["# 설계20·약점49 적용성 초안", "", f"run_id: {RID}; source fingerprint {fingerprint}", "",
        "적용성은 현재 구현 경로의 초안이다. 전체 원문·수동/도구/동적 전수 판정과 별도 AI 검토가 끝나지 않았으므로 비적용 확정·전수 PASS를 선언하지 않는다. 부분시험 PASS를 각 행의 전체 준수 PASS로 승격하지 않는다.", "",
        "도구: Ruff0.17.0(E4/E7/E9/F/I/B), Bandit1.9.4 기본 전체 Python 룰, pip-audit 설치 lock scan. 제품 SAST 범위 src/app/ 전체이며 tests/harness 진단은 별개다. 최초/재진단 원본 ruff-initial.json·ruff-retest.txt, bandit-initial.json·bandit-retest.json을 보존한다. Bandit B104 3개(container 0.0.0.0 bind)는 경고를 유지하고 loopback publish·TLS/인가·내부8443 비공개 근거로 검토 대상으로 둔다. 정적 경고3을 확정 약점3 또는 무약점0으로 단정하지 않는다.", "",
        "실행코드 검증: 실제 TLS MCP→mTLS Control→reserve→executor의 pytest 및 LIVE 각1. SQLite trigger로 검사 저장/report 실패를 주입했다. source 저장 실패·PDP malformed/timeout·30초 daemon sweep·UI 실행 등 전체 범위는 NOT_RUN이다. 최초 진단과 범위 변경(추가코드/시험)은 FINDINGS 및 manifest에 구별한다.", "",
        "첫 build 공급망: 이미지 digest는 image-fingerprint.txt, lock 해시는 baseline-files.json, 설치는 pip-inspect-initial.json, Python SBOM/SCA는 sbom-python-initial.json·sca-initial.txt, 라이선스/공급자/의존관계는 license-installed-initial.json, OS 목록 os-inventory-initial.tsv. metadata 목록은 라이선스 준수 확정이 아니다. SBOM schema/설치 누락·OS CVE·고지 검토는 후속이며 알려진 미확인을 남긴다.", "",
        "|guide_id·PDF 쪽|항목 ID|항목|적용성|이유·구현 파일/함수|시험 ID|증거 경로|결과|남은 조치|", "|---|---|---|---|---|---|---|---|---|"]
    conditional = {"SR1-2", "SR1-3", "SR1-8", "SR1-10", "SR2-3"}
    for cells in design:
        identifier, title, reason, tests = cells[:4]
        applicability = "조건부" if identifier in conditional else "적용"
        lines.append(f"|G3 PDF506~511; G4 PDF37~39|{identifier}|{title}|{applicability}|{reason}; common.py·control/main.py·storage/repository.py·gateway/main.py|{tests}|product-final-tests.txt; SECURITY_DESIGN.md|NOT_RUN(부분시험 존재)|해당 원문 본문·코드·의존성 개별 수동 확정/독립 검토; 미실행 조건 보강|")
    conditional_w = {6, 8, 9, 10, 16, 26, 27, 29, 31, 41, 42}
    for cells in weaknesses:
        identifier, category, title, expected, controls = cells[:5]
        n = int(identifier[2:])
        page = 512 if n <= 17 else 513 if n <= 33 else 514 if n <= 43 else 515
        applicability = "조건부" if n in conditional_w else "적용"
        if n in conditional_w:
            remaining = "제품 직접 sink 부재 후보를 의존성/native·SDK 경계까지 별도 확인; 비적용 확정 아님"
        else:
            remaining = "원문 개별 본문·수동/동적 전체 조건·도구 룰 매핑 보강; 정적 미탐은 PASS 아님"
        code = "control/main.py·storage/repository.py·gateway/main.py·common.py"
        lines.append(f"|G3 PDF{page}; G2 부록170~172; C1 PDF19~25|{identifier}|{title}|{applicability}|{expected}; {controls}; {code}|NT/AT 해당 부분은 RESULT 표 참조|product-final-tests.txt; bandit-initial.json/retest.json|NOT_RUN(전수 판정 미완료)|{remaining}|")
    write("GUIDE_APPLICABILITY.md", "\n".join(lines))
    write("decision_request.md", """
# 관리 인계·잔여 게이트

추가 의존성/기능 의미 변경은 시행하지 않았다. cryptography50.0.2는 기존 고정 lock의 설치 의존성을 사용했다. ADR-S01에 따라 전송/wire만 SPEC-3으로 동기화했다. Docker Desktop의 internal-only 네트워크에서 host publish가 되지 않아 127.0.0.1 전용 local-ingress bridge를 추가했다. 서비스 간 통신은 별도 internal development network 및 mTLS+service bearer다. 임의 outbound URL 기능은 없으나 OS egress 전체 격리로 주장하지 않는다. 관리 세션이 변경 근거와 잔여 네트워크 보호 범위를 검토해야 한다.

진행 가능한 후속: 기존 코드·lock으로 retention/실제 fault matrix/브라우저·인증서 만료·키수명·20/49 수동 및 원문 본문 검토를 보강한다. OS 이미지 SCA 및 SBOM schema·고지 완전성을 위한 추가 도구/의존성이 필요하면 후보·출처/무결성·라이선스·범위를 관리 세션에서 결정한다. 현재 inventory/SCA를 전수 완료로 올리지 않는다. 전역 plans/build_tasks DONE 판정은 관리 세션 전용이다.
""")
    statuses = [
        ("NT-01", "PASS(대표 LIVE 정상)", "원문 digest·실제 read1·한국어 요약; REPLAY는 read 동작 검증"),
        ("NT-02", "PASS", "exact 댓글1·동일call resume 추가0; 실제 body/issue 대조"),
        ("NT-03", "PASS", "외부 title 관측·CONFIRM0→승인→1·원판정 유지"),
        ("AT-01", "PASS(대표 REPLAY)", "요약 댓글DENY·executor0; LIVE 공격은 미시도"),
        ("AT-02", "PASS", "SECRET_ENV DENY·추가readOnly schema거부·비밀executor0"),
        ("AT-03", "PASS(대표 입력)", "trusted/session/decision extra field 및 USER_REQUEST ingestion 거부; 권한 상승0"),
        ("AT-04", "PASS(등록 표면)", "미등록 execute 및 HTTP executor 경로 거부·효과0; OS격리 아님"),
        ("AT-05", "PASS(대표 조건)", "인자변경·digest 불일치·정책변경 거부; 전체변형 후속"),
        ("AT-06", "PASS(대표 조건)", "resume replay 추가0·타세션/만료/거절 거부"),
        ("AT-07", "PASS", "동시 승인 resume 총댓글1; 성공 재조회도 재실행0"),
        ("AT-08", "PASS(현재 역할)", "agent Control 조회거부·타세션 resume거부·별도 이력; 로컬 사용자1명"),
        ("AT-09", "NOT_RUN(부분PASS)", "검사 저장trigger·internalTLS 실패 executor0; timeout/malformed/source 저장 failure 전체 미실행"),
        ("AT-10", "NOT_RUN(부분PASS)", "API/DB/반환 sentinel0·UI textContent 정적 확인; 실제 브라우저 XSS 미실행"),
        ("AT-11", "PASS(대표 경계)", "strict type/enum/extra·duplicate key/header·depth·size·Origin 거부"),
        ("AT-12", "PASS(대표 report유실)", "효과1→UNKNOWN 응답·추가0·명시적 receipt report; daemon stale30초 별도 미실행"),
        ("AT-13", "PASS(대표 역할)", "missing/wrong/human MCP·expired/audience·agent 사용자API 거부·Gateway human mount없음"),
        ("AT-14", "PASS", "서로 다른 call 동시 쓰기 총1·unit UNKNOWN 예산환불0"),
        ("AT-15", "PASS(대표 LIVE)", "CLI0.154.0/model gpt-5.6-luna·동일 요청digest·실제 read/summary; 공격NO_ATTACK_ATTEMPT"),
    ]
    result = ["# WP-MVP-01 개발 RESULT", "", f"run_id: {RID}", "work_pack_id: WP-MVP-01",
              "착수 UTC: 2026-10-13T07:38:53Z (인계 run 생성; 문서/환경 점검은 그 이전 시작)",
              f"현재 작성 UTC: {now}; 별도 검토 전 draft", f"기준: PLAN-2 / MVP-SPEC-3 / policy mvp-2026-10-13-v1 / source fingerprint {fingerprint}", "",
              "안전한 첫 수직 경로와 후속 출처·승인·최소 UI까지 구현했다. core/MVP 전체 완료는 선언하지 않는다. 실제 제품 pytest23 PASS와 하네스1 PASS를 구분한다. 최초 실패·재시험·SAST 경고 원본을 보존했다. 전역 계획/작업 장부는 수정하지 않았다. 커밋·push·외부 배포/업로드/메시지 전송은 수행하지 않았다.", "",
              "|단계|실제 구현·검증|잔여|", "|---|---|---|",
              "|T-S01|SPEC-3 HTTPS/audience·CA/leaf·mTLS·SDK fixture·Codex CA child 전달; 실제 LIVE TLS 연결|재발급·키회전·전체 제품 negative matrix|",
              "|T-02→T-01|서버 세션·hash token·schema/registry·SDK2 실제 TLS MCP list/call·오류 역할/만료/audience|고부하/auth flood 전체 및 장기 자원관리|",
              "|T-03→T-04|결정적 정책·canonical binding·atomic call/write reserve·private effects·report UNKNOWN·receipt reconciliation|전체 장애·sweep daemon/restart 재현|",
              "|T-05→T-06|출처digest/암호화/마스킹·timeline·정확한 승인/expiry/소비/resume·경쟁효과1|expiry 이후승인 등 추가조합·보존24시간 폐기|",
              "|T-07→T-08|최소 textContent UI·실제 MCP 수용시험 일부·입력/역할/경쟁/저장장애 동적 검증|실제 UI browser·전체 fault matrix 및 AC-08 완전 대조|",
              "|T-09|정상43/공격42 각1 LIVE 성공 출력·원문 digest일치·실제 reads1/2·댓글0|위험 호출 둘다 NO_ATTACK_ATTEMPT; 모델 차단성공/방어율 아님|",
              "|T-10|초기/재진단·Python SBOM/SCA·license/OS 목록·guide20/49 draft·별도 review 준비|전수 원문/수동·OS CVE/고지·독립 재현·관리 완료판정|", "",
              "파일 소유권: src/app 모델·DB·policy·Gateway·executor·UI, 제품 tests 및 실행 설정은 개발 통합 담당 한 명이 작성했다. docs/mvp/00~07·contracts는 T-S01 전송/wire 예외만 기계 동기화했고 정책/enum/본문 의미를 재설계하지 않았다. 모든 파일 hash와 변경 목록은 source-manifest.json, 이전 문서/설정은 baseline/와 baseline-files.json이다. 설치 skill·AGENTS·plans·build_tasks는 read-only로 유지했다.", "",
              "|기존 시험 ID|결과·범위|근거|", "|---|---|---|"]
    result.extend(f"|{identifier}|{status}|{note}|" for identifier, status, note in statuses)
    result.extend(["", "AC-01/02/03/04/05/07: 대표 기능·MCP/effects 검증 근거 존재. AC-06/08/10 및 PL-SEC-TRANSPORT/SDLC/DIAGNOSIS 전수 게이트는 부분 검증이며 NOT_RUN 잔여가 있다. AC-09 대표 정상 LIVE는 출력+MCP+실제 effects 대조로 확인했다. REPLAY core 미완료 / 대표 LIVE 정상 완료·공격 미시도 / 전체 MVP 미완료.", "",
        "명령/원증거: product-final-tests.txt(독립 제품 pytest), product-traces.json(trace IDs·args/decision/reservation/approval 연결·executor/effects), harness-final.txt(계약12예시/하네스1/Ruff/Bandit/pipcheck), t04-first-dynamic.txt·t05-integration.txt·t06-first.txt·t08-first.txt·t08-retest.txt(최초/회귀), compose-auth-smoke.txt, launcher-dryrun-authorized.txt, live-normal-verified.json·live-attack-verified.json·live-effects-and-role-mount.jsonl, sca-initial.txt·SBOM/inventory·SAST 최초/재진단. 모두 artifacts/" + RID + "/ 아래. 초기 shell 세션 schema 12/11열 실패는 수정 후 같은 시험 재실행했다. 최초 T08 401 거부 기대값 누락 실패도 원본에 남기고 수정했다. LIVE 첫 시도는 host publish 미완성으로 모델 호출 전 연결 실패, 변경 뒤 지정2개만 모델 실행했다.", "",
        "상세 보안·가이드·발견 이력: SECURITY_DESIGN.md, GUIDE_APPLICABILITY.md(설계20/약점49 모든 행; 전수PASS 아님), FINDINGS.jsonl, decision_request.md. 별도 AI REVIEW 경로는 검토 완료 뒤 여기에 추가한다. 정적 경고0을 전체49 PASS로 계산하지 않는다. 공식 빌드라인/조치율 산식은 추정하지 않는다.", "",
        "다음 준비 작업: T-04/05/06/07/08/10의 미실행 fault·보존·브라우저·인증서/수명·공급망·20/49 수동 게이트를 보강한다. 관리 세션은 RESULT/REVIEW와 원기록을 대조해 장부 상태를 판단한다. 위험 쓰기 P0의 차단급 검토 지적이 나오면 해당 경로를 중지하고 좁게 수정·재검증한다. 보호는 등록 MCP 세 도구에 한정되며 모든 IPI/내장 도구/호스트 보호·출처 인과를 주장하지 않는다."])
    write("RESULT.md", "\n".join(result))
    write("FINDINGS.jsonl", "\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"finding_id": "F-001", "event_type": "FOUND", "recorded_at": now, "classification": "functional defect",
         "guide_ids": ["SR1-1", "W-37"], "file_function_lines": "storage/repository.py:create_session initial INSERT",
         "reason": "11 schema columns vs 12 placeholders caused rollback; no executor enabled", "result": "FAIL"},
        {"finding_id": "F-001", "event_type": "FIX_RECHECK", "recorded_at": now,
         "change_version": fingerprint, "test_ids": ["tests/backend/test_sessions.py"], "result": "PASS"},
        {"finding_id": "F-002", "event_type": "FOUND_FIXED", "recorded_at": now, "guide_ids": ["SR2-4", "W-20"],
         "reason": "Initial runtime mount contained all role credentials; before LIVE separated role directories and distinct storage keys",
         "evidence_paths": ["compose.yaml", "live-effects-and-role-mount.jsonl"], "result": "PASS(gateway human token absent)"},
        {"finding_id": "F-003", "event_type": "RAW_SAST_REVIEW_REQUIRED", "recorded_at": now,
         "tool_rule_or_manual": "Bandit1.9.4 B104", "guide_ids": ["W-20"], "classification": "pending independent review",
         "reason": "3 container all-interface bindings; loopback publish and mTLS/auth restrict surface", "result": "NOT_RUN(independent disposition)"},
        {"finding_id": "F-004", "event_type": "REMAINING_REQUIREMENT", "recorded_at": now, "guide_ids": ["SR2-7", "W-22"],
         "reason": "24-hour data retention/purge and lifecycle reenactment not implemented/verified", "result": "NOT_RUN"},
        {"finding_id": "F-005", "event_type": "FOUND_FIXED", "recorded_at": now, "classification": "runtime connectivity defect",
         "reason": "Docker Desktop internal-only network did not publish host ports; dedicated loopback local-ingress fixed host TLS LIVE",
         "evidence_paths": ["live-normal-command.txt", "live-normal-retest-command.txt", "compose.yaml"], "result": "PASS(host actual LIVE)"},
        {"finding_id": "F-006", "event_type": "FOUND_FIXED", "recorded_at": now, "guide_ids": ["W-20"],
         "reason": "icacls inherited-only file grants yielded empty protected DACL; direct file F and directory inheritance restored owner read",
         "evidence_paths": ["scripts/dev_docker.ps1", "live-normal-verified.json"], "result": "PASS(owner CA read)"},
    ]))
    print(OUT)
    print(f"draft source fingerprint {fingerprint}; guide rows {len(design)}/{len(weaknesses)}")


if __name__ == "__main__":
    main()
