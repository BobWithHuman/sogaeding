"""Safe derived local HTML/terminal view. No server, credentials or arbitrary DB access."""
import html
import json
import math
import re
import unicodedata
from pathlib import Path

PATHS = {"docs/release.md", "docs/review.md", "reports/normal.md", "reports/review.md"}
DECISIONS = {"ALLOW":"허용", "DENY":"차단", "CONFIRM":"예외 확인", "UNKNOWN":"미확정"}
STATES = {"OBSERVED":"실행 결과 관측", "READY":"집행 대기", "EXECUTING":"실행 중·결과 미확정", "UNKNOWN":"실행 결과 미확정·재시도 금지", "DENIED":"실행 전 차단", "CONFIRM":"사용자 확인 대기", "APPROVED":"예외 승인됨", "PENDING":"판정 대기", "ANALYZING":"분석 중", "STALE":"만료", "OBSERVED_ERROR":"오류 관측"}
REASONS = {"PUBLIC_ENROLLED_READ":"등록된 공개 파일 읽기", "USER_INTENT_SUPPORTED":"사용자 요청 범위와 일치", "TASK_DATA_SUPPORTED":"외부자료를 작업 데이터로 활용", "EXTERNAL_INSTRUCTION_DEPENDENCY":"외부 지시가 추가한 행동", "OUTSIDE_TASK_SCOPE":"사용자 요청 범위 밖 행동", "SEMANTIC_UNCERTAIN":"관련 의미 또는 근거 미확정", "ANALYSIS_UNAVAILABLE":"분석 실패·공격 식별 성공 아님", "POLICY_CHANGED":"정책 변경으로 이전 판정 무효", "UNKNOWN_REASON":"상세 사유 미확정"}
OBS_CHOICES = {"DIRECT","DATA_DEPENDENT","WITHIN_TASK","USER","GENERATED","ADDED_INSTRUCTION","OUTSIDE_TASK","UNCERTAIN","NONE","TASK_DATA","NEW_INSTRUCTION","RECOMMENDATION","DATA","PROHIBITION_QUOTE","UNRESOLVED", *(f"e{i}" for i in range(16))}
OBS_CHOICES |= {"LEGITIMATE","EXTERNAL_ADOPTION","SUPPORTED","UNRELATED"}
QUESTIONS = {"task_relation","task_evidence","external_evidence","external_use","link_action","link_target","link_options","link_payload",*("basis_"+role for role in ("action","target","options","payload")),*(f"context_{i}" for i in range(8))}
QUESTIONS |= {"behavior",*(f"attribution_e{i}" for i in range(16))}
DIAGNOSTICS = {"JEV_RESPONSE_INVALID","JEV_INPUT_INVALID","JEV_NOT_AUTHORIZED","JEV_SETTINGS_INVALID","JEV_BUDGET_BINDING","JEV_SENSITIVE_INPUT","JEV_CONTEXT_LIMIT","REQUEST_BUDGET_EXHAUSTED","B_EXTERNAL_EVIDENCE_REQUIRED","EVIDENCE_REQUIRED","UNKNOWN_SPAN","QUOTE_MISMATCH","QUOTE_BOUNDS","SOURCE_HASH_MISMATCH","TURN_ANALYSIS_STOPPED","API_TIMEOUT","API_AUTHENTICATION","API_CONNECTION","API_RATE_LIMIT","PAIR_DEADLINE","ADAPTER_ERROR","MISSING_API_KEY"}
OUTCOMES = {"EXITED":"CLI 정상 종료(작업 성공과 별도)","EXITED_NONZERO":"CLI 오류 종료", "TIMEOUT":"명시적 대화형 시간 한도 도달", "INTERRUPTED":"사용자 취소", "LAUNCH_FAILED":"CLI 시작 실패", "EXIT_STATUS_UNKNOWN":"종료 사유 기록 없음·UNKNOWN"}


def actor_events(value):
    """Lifecycle is typed local evidence, never an arbitrary process log."""
    result=[]
    for row in value[:6] if isinstance(value,list) else []:
        if not isinstance(row,dict) or type(row.get("episode")) is not int or row["episode"] not in {1,2,3,4,5}:
            continue
        item={"episode":row["episode"], "event":enum(row.get("event"),{"STARTING","FINISHED","LEGACY_UNKNOWN"}),
              "outcome":enum(row.get("outcome"),OUTCOMES,"EXIT_STATUS_UNKNOWN"),
              "elapsed_seconds":number(row.get("elapsed_seconds"),86400),
              "wall_seconds":number(row.get("wall_seconds"),1800),
              "exit_code":row.get("exit_code") if type(row.get("exit_code")) is int and -2147483648<=row["exit_code"]<=4294967295 else None,
              "tree_cleanup":enum(row.get("tree_cleanup"),{"VERIFIED","UNVERIFIED","NOT_CREATED"}),
              "connection_closed":enum(row.get("connection_closed"),{"VERIFIED","UNVERIFIED","NOT_APPLICABLE"}),
              "started":row.get("started") if type(row.get("started")) is bool else None}
        for key in ("started_utc","ended_utc"):
            timestamp=row.get(key)
            item[key]=timestamp if isinstance(timestamp,str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)",timestamp) else None
        result.append(item)
    return result


def clean(value, limit=320):
    if not isinstance(value,str):
        return ""
    value = "".join(c for c in value if not unicodedata.category(c).startswith("C"))
    value = re.sub(r'''(?i)(["']?(?:api[_-]?key|password|secret|token)["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;}]+)''',r"\1[보호됨]",value)
    value = re.sub(r"(?i)(?:bearer\s+\S+|sk-[\w-]{8,})","[보호됨]",value)
    return " ".join(value.split())[:limit]


def number(value, maximum=1):
    return value if type(value) in (int,float) and 0<=value<=maximum and math.isfinite(value) else None


def enum(value, allowed, default="UNKNOWN"):
    return value if isinstance(value,str) and value in allowed else default


def observations(value):
    result=[]
    if isinstance(value,dict):
        for view, rows in value.items():
            if view in {"A","B"} and isinstance(rows,list):
                for row in rows[:24]:
                    if isinstance(row,dict):
                        result.append({**row,"view":view})
    elif isinstance(value,list):
        result=value[:48]
    safe=[]
    for row in result:
        if not isinstance(row,dict) or enum(row.get("question"),QUESTIONS) == "UNKNOWN" or enum(row.get("choice"),OBS_CHOICES) == "UNKNOWN":
            continue
        safe.append({"question":row["question"],"view":enum(row.get("view"),{"A","B"},"?"),
                     "choice":row["choice"], "provider":number(row.get("provider_confidence")),"computed":number(row.get("computed_confidence")),
                     "effective":number(row.get("effective_confidence")),"status":enum(row.get("status"),{"ACCEPTED","LOW_CONFIDENCE","MODEL_UNCERTAIN","MODEL_UNRESOLVED"})})
        evidence=row.get("evidence")
        if isinstance(evidence,dict):
            safe[-1]["source_role"]=enum(evidence.get("source_role"),{"USER","CANDIDATE","SOURCE_DATA"})
            safe[-1]["binding"]=enum(evidence.get("binding"),{"SERVER_CATALOG_EXACT_VALIDATED","SERVER_CATALOG_BOUND_NOT_SELECTED"})
    return safe


def build_view(report):
    if not isinstance(report,dict):
        report={}
    history=report.get("history",{})
    rows=history.get("calls",[]) if isinstance(history,dict) else []
    calls=[]
    for row in rows[:10] if isinstance(rows,list) else []:
        if not isinstance(row,dict):
            continue
        reasons=row.get("reasons",[])
        reasons=[r if isinstance(r,str) and r in REASONS else "UNKNOWN_REASON" for r in reasons[:8]] if isinstance(reasons,list) else []
        trace=row.get("policy_trace",{})
        calls.append({"ref":clean(row.get("call_ref"),12),"tool":enum(row.get("tool"),{"read_file","write_file","Bash","apply_patch"}),
                      "target":row.get("target") if isinstance(row.get("target"),str) and row["target"] in PATHS else "OUT_OF_DEMO_SCOPE",
                      "request":clean(row.get("request_excerpt")),"payload":clean(row.get("payload_excerpt")),
                      "sources":[clean(s.get("excerpt")) for s in row.get("source_excerpts",[])[:8] if isinstance(s,dict)],
                      "decision":enum(row.get("decision"),DECISIONS),
                      "policy":enum(row.get("policy"),{"hookgw-2026-10-16-jev-v2","hookgw-2026-10-17-jev-v3","hookgw-2026-10-17-jev-v5","hookgw-2026-10-17-jev-v5p1"}),
                      "causal_explanation":"NOT_ESTABLISHED",
                      "state":enum(row.get("state"),STATES), "reasons":reasons,
                      "confirmation":enum(row.get("confirmation"),{"HUMAN_APPROVAL_CONSUMED","PENDING","APPROVED","REJECTED","EXPIRED_OR_CLOSED"}),
                      "execution_error":enum(row.get("execution_error"),{"FILE_NOT_FOUND"}),
                      "observations":observations(trace.get("view_observations")) if isinstance(trace,dict) else [],
                      "analysis_failed":"ANALYSIS_UNAVAILABLE" in reasons,
                      "positive_basis":enum(trace.get("positive_authorization_basis"),{"B_LEGITIMATE_VALIDATED_RAW_A_WITHIN_TASK"},"NOT_APPLIED") if isinstance(trace,dict) else "NOT_APPLIED",
                      "diagnostic":[d["code"] if isinstance(d.get("code"),str) and d["code"] in DIAGNOSTICS else "UNKNOWN_DIAGNOSTIC" for d in row.get("diagnostic",[])[:2] if isinstance(d,dict)]})
    calls.reverse()
    effects=[]
    for row in report.get("effects",[])[:2]:
        if isinstance(row,dict) and enum(row.get("path"),{"reports/normal.md","reports/review.md"})!="UNKNOWN":
            effects.append({"path":row["path"],"exists":row.get("exists") if type(row.get("exists")) is bool else None,
                            "bytes":number(row.get("bytes"),16384), "text":clean(row.get("text"),2048),
                            "sha256":row.get("sha256") if isinstance(row.get("sha256"),str) and re.fullmatch(r"[0-9a-f]{64}",row["sha256"]) else None})
    blocked=sum(c["decision"]=="DENY" and not c["analysis_failed"] and "EXTERNAL_INSTRUCTION_DEPENDENCY" in c["reasons"] for c in calls)
    provider=report.get("provider",{})
    if not isinstance(provider,dict):
        provider={}
    episodes=report.get("episodes",{})
    if not isinstance(episodes,dict):
        episodes={}
    upstream=report.get("upstream",{})
    if not isinstance(upstream,dict):
        upstream={}
    return {"calls":calls,"effects":effects,"actor_events":actor_events(report.get("actor_events")),"external_instruction_blocks":blocked,
            "attack_status":"BLOCKED_CANDIDATE_OBSERVED" if blocked else "NO_ATTACK_ATTEMPT_OR_NOT_ESTABLISHED",
            "provider_attempts":number(provider.get("requests_attempted",provider.get("attempts")),8),
            "input_reserved":number(provider.get("input_reserved"),512000),
            "usage_complete":provider.get("usage_complete") if type(provider.get("usage_complete")) is bool else None,
            "episodes_claimed":number(episodes.get("claimed"),7),
            "episodes_max":episodes.get("max") if type(episodes.get("max")) is int and episodes["max"] in {2,3,4,5,6,7} else 2,
            "upstream_observed":number(upstream.get("observed"),1024),
            "upstream_unknown":number(upstream.get("unknown"),1024),
            "mode":enum(report.get("mode"),{"OFFLINE_REPLAY","USER_DEMO","NO_MODEL_CHECK"},"NOT_ESTABLISHED"),
            "scope":"등록된 합성 파일 MCP 경로", "truncated":bool(history.get("truncated")) if isinstance(history,dict) else False}


def render(report):
    view=build_view(report)
    lines=["With Human · 요청에서 실제 파일 효과까지", "범위: "+view["scope"],"실제 모델/전체 IPI 보호 완료를 뜻하지 않습니다.",""]
    usage="완전" if view["usage_complete"] is True else "미보고/부분·총청구 UNKNOWN"
    lines.append(f'실행 모드={view["mode"]} · Jev 요청={view["provider_attempts"]} · 입력 예약={view["input_reserved"]} · 사용량={usage} · CLI 시작 예약={view["episodes_claimed"]}/{view["episodes_max"]}')
    lines.append(f'upstream 별도 관측={view["upstream_observed"]} · UNKNOWN={view["upstream_unknown"]}; 현재 파일 효과와 따로 대조합니다.')
    cards=[]
    escape=html.escape
    accounting="입력·호스트 승인 대기를 포함하는 대화형 시간 한도입니다. 종료 뒤 연결 닫기·자식 정리의 유예가 있으며, 이미 전송된 upstream 효과는 UNKNOWN일 수 있습니다."
    cards.append('<p>'+escape(accounting)+'</p><p>USER_DEMO는 실제 모델 경로이며 정확도 통과가 아닙니다. OFFLINE_REPLAY는 저장된 답 또는 합성 응답의 개발 재현입니다. bob-agentgateway:4400 경고는 별도 개인 MCP 상태입니다.</p>')
    def shown(value):
        return "UNKNOWN" if value is None else str(value)
    for event in view["actor_events"]:
        status="시작 절차 기록·종료 미기록(실행 여부 미확정)" if event["event"]=="STARTING" else OUTCOMES[event["outcome"]]
        line=f'CLI 예약 {event["episode"]}: '+status
        detail=f'시작 UTC={event["started_utc"] or "UNKNOWN"} · 종료 UTC={event["ended_utc"] or "UNKNOWN"} · 경과초={shown(event["elapsed_seconds"])} · 한도초={shown(event["wall_seconds"])} · exit={shown(event["exit_code"])} · 연결 닫기={event["connection_closed"]} · 자식 정리={event["tree_cleanup"]}'
        lines.extend([line,detail])
        cards.append('<article><h2>'+escape(line)+'</h2><p>'+escape(detail)+'</p></article>')
    lines.append("대화형 한도는 입력·호스트 승인 대기를 포함합니다. 대기/모델 계산 시간을 분리 계측하지 않습니다. bob-agentgateway:4400 경고는 별도 개인 MCP 상태이며 이 시연 성공의 증거가 아닙니다.")
    for i,c in enumerate(view["calls"],1):
        label="호스트 승인·집행 요청 대기(PDP 미실행)" if c["state"]=="PENDING" and c["decision"]=="UNKNOWN" else DECISIONS[c["decision"]]
        title=f'{i}. {label} · {c["tool"]} → {c["target"]} · {STATES[c["state"]]}'
        outcome = "UNKNOWN" if c["state"] == "UNKNOWN" else "ANALYSIS_FAILED" if c["analysis_failed"] else "HUMAN_CONFIRMED" if c["state"] == "OBSERVED" and c["confirmation"] == "HUMAN_APPROVAL_CONSUMED" else "NORMAL_AUTO_OBSERVED" if c["tool"] == "write_file" and c["state"] == "OBSERVED" and c["decision"] == "ALLOW" else "ATTACK_BLOCKED_CANDIDATE" if c["decision"] == "DENY" and "EXTERNAL_INSTRUCTION_DEPENDENCY" in c["reasons"] else "NOT_COMPLETED"
        details=["정책: "+c["policy"]+" · 결과: "+outcome,"요청: "+c["request"],*["판정에 사용한 자료(인과 미입증): "+s for s in c["sources"]],"후보 내용: "+c["payload"],"이유: "+" / ".join(REASONS[r] for r in c["reasons"])]
        if c["positive_basis"] != "NOT_APPLIED":
            details.append("양의 허용 근거: B 고확신 LEGITIMATE + 검증된 A raw WITHIN_TASK. A의 낮은 확신은 유지됩니다.")
        if c["confirmation"] != "UNKNOWN":
            details.append("PDP 예외 확인: "+{"PENDING":"별도 사용자 승인 대기", "APPROVED":"정확 후보 승인됨·단회 재개 대기", "HUMAN_APPROVAL_CONSUMED":"사용자 승인 단회 소비·원판정 CONFIRM 유지", "REJECTED":"사용자 거절·재개 금지", "EXPIRED_OR_CLOSED":"만료 또는 연결 종료·재개 금지"}[c["confirmation"]])
        if c["execution_error"] == "FILE_NOT_FOUND":
            details.append("확정된 업무 오류 FILE_NOT_FOUND: 읽을 파일 없음·쓰기 효과 없음·출처로 수집하지 않음")
        if c["diagnostic"]:
            details.append("분석 진단: "+" / ".join(c["diagnostic"]))
        observed=[]
        key_observed=[]
        for o in c["observations"]:
            status={"ACCEPTED":"확신 기준 충족","LOW_CONFIDENCE":"확신 기준 미달","MODEL_UNCERTAIN":"모델이 미확정을 선택","MODEL_UNRESOLVED":"모델이 출처 미확정을 선택"}.get(o["status"],"미확정")
            line=f'관측 {o["view"]}/{o["question"]}: {o["choice"]} · {status} · confidence 제공자/계산/유효={o["provider"]}/{o["computed"]}/{o["effective"]}'
            if "binding" in o:
                line+=' · 근거='+o["source_role"]+' / '+o["binding"]
            observed.append(line)
            if o["question"] in {"task_relation","external_use","behavior"} or o["status"]!="ACCEPTED":
                key_observed.append(line)
        lines.extend([title,*details,*key_observed[:4],""])
        cards.append('<article><h2>'+escape(title)+'</h2>'+''.join('<p>'+escape(d)+'</p>' for d in details)+('<details><summary>검증된 선택·확신 상세</summary>'+''.join('<p>'+escape(d)+'</p>' for d in observed)+'</details>' if observed else '')+'</article>')
    if not view["calls"]:
        lines.append("아직 도구 후보가 없습니다. 사용자 CLI 실행은 별도로 시작합니다.")
        cards.append('<article>아직 도구 후보가 없습니다.</article>')
    for effect in view["effects"]:
        line=f'실제 파일 {effect["path"]}: '+("존재" if effect["exists"] is True else "없음" if effect["exists"] is False else "미확정")+f' · bytes={effect["bytes"]} · SHA256={effect["sha256"] or "UNKNOWN"}'
        lines.extend([line,effect["text"]])
        cards.append('<article><h2>'+escape(line)+'</h2><pre>'+escape(effect["text"])+'</pre></article>')
    note="외부 지시 후보 차단 관측: "+str(view["external_instruction_blocks"])+"건. "
    if not view["external_instruction_blocks"]:
        note+="NO_ATTACK_ATTEMPT 또는 미확정 · 공격 식별 PASS 아님."
    note+=" 파일의 현재 존재/내용과 호출의 OBSERVED는 별도 관측이며 원자 receipt/인과 증명이 아닙니다. UNKNOWN은 재시도하지 마세요."
    if view["truncated"]:
        note+=" 최근 이력 일부만 표시합니다."
    lines.append(note)
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>With Human 시연 결과</title><style>body{font:16px system-ui;background:#f2f5f8;color:#162636;max-width:1100px;margin:32px auto;padding:0 20px}article{background:white;padding:20px;margin:16px 0;border-radius:12px;border-left:5px solid #286a92}h1{font-size:28px}h2{font-size:19px}p,pre{white-space:pre-wrap;overflow-wrap:anywhere}footer{padding:20px;background:#e2eaf1}</style><h1>With Human · 요청에서 실제 파일 효과까지</h1><p>등록된 합성 파일 MCP 시연 · 현재 상태의 읽기 전용 보고서</p><p>'+escape(lines[4])+'</p><p>'+escape(lines[5])+'</p>'+''.join(cards)+'<footer>'+escape(note)+'</footer></html>'
    return {"text":"\n".join(lines),"html":page,"view":view}


def save_report(report, output_path):
    path=Path(output_path)
    if any(part.is_symlink() or getattr(part,"is_junction",lambda:False)() for part in (path,*path.parents)) or path.suffix.lower()!=".html":
        raise ValueError("DEMO_REPORT_PATH_REJECTED")
    with path.open("x",encoding="utf-8") as stream:
        stream.write(render(report)["html"])
    return str(path.resolve())


if __name__=="__main__":
    import sys
    raw=sys.stdin.buffer.read(131073)
    if len(raw)>131072:
        raise SystemExit("DEMO_REPORT_LIMIT")
    print(render(json.loads(raw.decode("utf-8")))["text"])
