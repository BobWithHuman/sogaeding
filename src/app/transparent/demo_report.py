"""Human-only, bounded synthetic demo projection. No credentials or raw traces."""
import json
import math
import re
import unicodedata

from app.common import canonical, digest, mask
from app.pdp.diagnostics import detail
from app.transparent.gate_policy import POLICY as GATE_POLICY
from app.transparent.gate_policy import RULE as GATE_RULE

DEMO_SCOPE = "SYNTHETIC_REGISTERED_MCP"
PATHS = {"docs/release.md", "docs/review.md", "reports/normal.md", "reports/review.md"}
STATES = {"PENDING", "ANALYZING", "READY", "EXECUTING", "UNKNOWN", "DENIED", "CONFIRM", "APPROVED", "OBSERVED", "OBSERVED_ERROR", "STALE"}
REASONS = {"PUBLIC_ENROLLED_READ", "USER_INTENT_SUPPORTED", "TASK_DATA_SUPPORTED", "EXTERNAL_INSTRUCTION_DEPENDENCY", "OUTSIDE_TASK_SCOPE", "SEMANTIC_UNCERTAIN", "ANALYSIS_UNAVAILABLE", "POLICY_CHANGED", "TOOL_ARGUMENTS_UNPARSED_OR_SCOPE", "SECURITY_CONFIGURATION_FORBIDDEN", "SECURITY_CONFIG_PATCH_UNRESOLVED", "SECURITY_CONFIG_UNPARSED", "PROTECTED_PATH", "SENSITIVE_INPUT"}
REASONS |= {"JEV_REJECTED_HELD_CASE", "JEV_NOT_AFFIRMED_RISK_CASE", "CONSENT_CASE_A_AND_B_AFFIRMED",
            "DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED", "SENSITIVE_RESOURCE_REQUIRES_CONSENT",
            "OUTSIDE_TASK_CAPABILITY_REQUIRES_CONSENT", "PRIVATE_MUTATION_REQUIRES_CONSENT",
            "NONPUBLIC_READ_REQUIRES_CONSENT", "PROTECTED_USER_PATH_REQUIRES_CONSENT",
            "SECURITY_CONFIGURATION_REQUIRES_CONSENT", "SIDE_EFFECT_OR_CONSENT_NOT_DELEGATED"}
CHOICES = {"DIRECT", "DATA_DEPENDENT", "WITHIN_TASK", "USER", "GENERATED", "ADDED_INSTRUCTION", "OUTSIDE_TASK", "UNCERTAIN", "NONE", "TASK_DATA", "NEW_INSTRUCTION", "RECOMMENDATION", "DATA", "PROHIBITION_QUOTE", "UNRESOLVED", *(f"e{i}" for i in range(16))}
CHOICES |= {"LEGITIMATE", "EXTERNAL_ADOPTION", "SUPPORTED", "UNRELATED"}
OBSERVATION_KEYS = {"view", "question", "choice", "probabilities", "provider_confidence", "computed_confidence", "effective_confidence", "confidence", "selected_probability", "status", "threshold", "threshold_passed", "basis", "selected", "observation_status", "evidence", "source_role", "binding"}
QUESTIONS = {"task_relation", "task_evidence", "external_evidence", "external_use", "link_action", "link_target", "link_options", "link_payload", *("basis_"+role for role in ("action", "target", "options", "payload")), *(f"context_{i}" for i in range(8))}
QUESTIONS |= {"behavior", *(f"attribution_e{i}" for i in range(16))}
STATUSES = {"A", "B", "USER", "CANDIDATE", "SOURCE_DATA", "SERVER_CATALOG_EXACT_VALIDATED", "SERVER_CATALOG_BOUND_NOT_SELECTED", "ACCEPTED", "SELECTED", "VALID", "HIGH_CONFIDENCE", "LOW_CONFIDENCE", "MODEL_UNCERTAIN", "MODEL_UNRESOLVED", "EXPLICIT_UNCERTAIN", "EXPLICIT_UNRESOLVED", "UNCERTAIN", "UNRESOLVED", "NOT_RUN", "NOT_RUN_RULE", "MIN_PROVIDER_COMPUTED", "MODEL_OBSERVATION_NOT_CAUSAL_PROOF"}


def excerpt(value, limit=320):
    if not isinstance(value, str):
        return ""
    value = re.sub(r'''(?i)(["']?(?:api[_-]?key|password|secret|token)["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;}]+)''',r"\1[REDACTED]",value)
    return mask(" ".join("".join(c for c in value if not unicodedata.category(c).startswith("C")).split()))[:limit]


def source_excerpt(value):
    # Presentation only: exact-ref verification still uses the original catalog.
    if isinstance(value,str) and len(value)<=32768:
        try:
            parsed=json.loads(value)
        except (ValueError,TypeError):
            parsed=None
        if isinstance(parsed,dict) and isinstance(parsed.get("content"),list):
            texts=[part["text"] for part in parsed["content"][:4] if isinstance(part,dict) and part.get("type")=="text" and isinstance(part.get("text"),str)]
            if texts:
                return excerpt(" ".join(texts))
    return excerpt(value)


def safe_observations(value, depth=0):
    """Only known question IDs/options and bounded numbers; no dynamic names."""
    if depth > 6:
        return None
    if type(value) is bool:
        return value
    if type(value) in (float, int):
        return value if 0 <= value <= 1 and math.isfinite(value) else None
    if isinstance(value, str):
        return value if value in CHOICES | STATUSES | QUESTIONS else None
    if isinstance(value, list):
        return [safe_observations(item,depth+1) for item in value[:24]]
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:32]:
            if key in OBSERVATION_KEYS | CHOICES | QUESTIONS | {"A", "B"} or isinstance(key, str) and re.fullmatch(r"context_[0-7]", key):
                safe = safe_observations(item, depth+1)
                if safe is not None:
                    result[key] = safe
        return result
    return None


def project(engine, *, machine=None):
    if engine.grant.get("demo_scope") != DEMO_SCOPE:
        return {"version": "mvp-demo-history-1", "scope": "UNAVAILABLE", "calls": [], "truncated": False}
    calls = []
    with engine.db() as db:
        rows = db.execute("SELECT c.* FROM calls c JOIN sessions s ON s.id=c.session WHERE (? IS NULL OR s.machine=?) ORDER BY c.created DESC LIMIT 11", (machine, machine)).fetchall()
        for row in rows[:10]:
            candidate = engine.open(row["body"])
            context = engine.read_reason(row["reason"]) if row["reason"] else {}
            trace = context.get("policy_trace") or {}
            if not isinstance(trace,dict):
                trace = {}
            turn = db.execute("SELECT body FROM turns WHERE session=? AND id=?", (row["session"],row["turn"])).fetchone()
            sources = [engine.open(s[0]) for s in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid LIMIT 8", (row["session"],)).fetchall()]
            snapshot_sources = None
            for n in range(len(sources)+1):
                if digest(canonical(sources[:n])) == context.get("source_hash"):
                    snapshot_sources = sources[:n]
                    break
            # Show the source actually ingested by a read itself, or the exact
            # source prefix used at analysis. Later reads are not retroactive evidence.
            own_read = candidate.get("tool") == "read_file"
            sources = [s for s in sources if s.get("call_id") == row["id"]] if own_read else snapshot_sources or []
            safe_sources = []
            for source in sources:
                original = db.execute("SELECT body FROM calls WHERE id=?", (source.get("call_id"),)).fetchone()
                if original:
                    read = engine.open(original[0])
                    read_path = read.get("args",{}).get("path")
                    if read.get("tool") == "read_file" and isinstance(read_path,str) and read_path in PATHS:
                        safe_sources.append({"source_ref":digest(source["source_id"])[:12],"excerpt":source_excerpt(source.get("analysis_text",""))})
            args = candidate.get("args",{})
            target = args.get("path")
            in_scope = isinstance(target,str) and target in PATHS
            diagnostics = context.get("diagnostic") or []
            if isinstance(diagnostics,dict):
                diagnostics = [diagnostics]
            item = {"call_ref":digest(row["id"])[:12],"session_ref":digest(row["session"])[:12],"turn_ref":digest(row["turn"])[:12],
                    "created":row["created"],"route":row["path"] if row["path"] in {"mcp","native"} else "UNKNOWN",
                    "tool":candidate.get("tool") if candidate.get("tool") in {"read_file","write_file","Bash","apply_patch"} else "UNKNOWN",
                    "target":target if in_scope else "OUT_OF_DEMO_SCOPE", "request_excerpt":excerpt(engine.open(turn[0]).get("prompt","")) if turn else "",
                    "source_excerpts":safe_sources,"payload_excerpt":excerpt(args.get("content","")) if in_scope else "",
                    "source_snapshot_verified":snapshot_sources is not None,
                    "policy":context.get("policy") if context.get("policy") in {GATE_POLICY, "hookgw-2026-10-16-jev-v2", "hookgw-2026-10-17-jev-v3", "hookgw-2026-10-17-jev-v5","hookgw-2026-10-17-jev-v5p1"} else "UNKNOWN",
                    "causal_explanation":"NOT_ESTABLISHED",
                    "state":row["state"] if row["state"] in STATES else "UNKNOWN", "decision":row["decision"] if row["decision"] in {"ALLOW","DENY","CONFIRM"} else "UNKNOWN",
                    "reasons":[v if isinstance(v,str) and v in REASONS else "UNKNOWN_REASON" for v in context.get("reasons",[])[:8]],
                    "diagnostic":[detail(v.get("code"),v.get("view"),v) for v in diagnostics[:2] if isinstance(v,dict)],
                    "policy_trace":{"routing":trace.get("routing") if trace.get("routing") in {"RULE_ALLOW","RULE_DENY","SEMANTIC","ANALYSIS_FAILED"} else "UNKNOWN",
                                    "decision_rule_version":trace.get("decision_rule_version") if trace.get("decision_rule_version") in {GATE_RULE, "jev-b-owned-positive-1"} else "NOT_APPLIED",
                                    "positive_authorization_basis":trace.get("positive_authorization_basis") if trace.get("positive_authorization_basis") == "B_LEGITIMATE_VALIDATED_RAW_A_WITHIN_TASK" else "NOT_APPLIED",
                                    "view_observations":safe_observations(trace.get("view_observations",{}))}}
            if row["decision"] == "CONFIRM":
                item["confirmation"] = "HUMAN_APPROVAL_CONSUMED" if context.get("demo_approval") else {
                    "CONFIRM":"PENDING", "APPROVED":"APPROVED", "DENIED":"REJECTED", "STALE":"EXPIRED_OR_CLOSED"}.get(row["state"], "UNKNOWN")
            error = context.get("execution_error")
            if error == {"version":"file-error-1","code":"FILE_NOT_FOUND","operation":"READ","effect":"NO_WRITE"}:
                item["execution_error"] = "FILE_NOT_FOUND"
            calls.append(item)
    truncated = len(rows)>10
    report = {"version":"mvp-demo-history-1","scope":"REGISTERED_SYNTHETIC_MCP_ONLY","calls":calls,"truncated":truncated}
    while len(canonical(report).encode())>120000 and report["calls"]:
        report["calls"].pop()
        report["truncated"]=True
    return report
