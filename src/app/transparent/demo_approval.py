"""Human exception approval for the same exact demo RPC. Never invokes a judge.

The original CONFIRM decision/reason is retained. A fresh, human-issued 30-second
authorization follows a maximum 600-second review period; analysis time is not
rewritten. Reservation and approval consumption share one SQLite transaction.
"""
import json
import time

from app.common import canonical, digest, mask
from app.pdp.semantic import span_catalog
from app.transparent.engine import Rejected
from app.transparent.jev_policy import configuration_risk
from app.transparent.tool_schema import parse

REVIEW_SECONDS = 600
APPROVAL_SECONDS = 30


def joined(db, call):
    return db.execute("SELECT c.*,i.connection_hash AS intent_connection,i.request_hash AS intent_request,i.source_hash AS intent_source,i.grant_hash AS intent_grant,i.policy AS intent_policy,i.claimed,r.rpc_hash,d.binding,d.expires,d.approved_at,d.resumed,d.reason_hash FROM calls c JOIN demo_intents i ON i.call=c.id JOIN demo_rpc_bindings r ON r.call=c.id LEFT JOIN demo_confirmations d ON d.call=c.id WHERE c.id=?", (call,)).fetchone()


def validate(e, db, machine, row, token=None):
    if not row or row["path"] != "mcp" or row["decision"] != "CONFIRM" or row["claimed"] != 1:
        raise Rejected("DEMO_CONFIRM_BINDING")
    if token is None:
        connection = db.execute("SELECT machine,session FROM connections WHERE hash=?", (row["intent_connection"],)).fetchone()
        e.expires(db, "connection", row["intent_connection"])
        if not connection or connection["machine"] != machine or connection["session"] != row["session"]:
            raise Rejected("CONNECTION_BINDING")
        e._current(db, machine, row["session"], row["turn"])
        prompts = [e.open(x[0])["prompt"] for x in db.execute("SELECT body FROM turns WHERE session=? ORDER BY rowid", (row["session"],))]
        request = canonical({"actual_user_turns_chronological": prompts, "latest_turn": len(prompts)-1})
        sources = [e.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
        context = (row["intent_connection"], digest(request), digest(canonical(sources)))
    else:
        context = e._demo_intent_context(db, machine, row["session"], row["turn"], token)
        prompts = [e.open(x[0])["prompt"] for x in db.execute("SELECT body FROM turns WHERE session=? ORDER BY rowid", (row["session"],))]
        request = canonical({"actual_user_turns_chronological": prompts, "latest_turn": len(prompts)-1})
        sources = [e.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
    actual_grant = digest(canonical({"grant": e.grant, "policy": e.policy} if e.policy_router else e.grant))
    reason = json.loads(row["reason"])
    if (context != (row["intent_connection"], row["intent_request"], row["intent_source"])
            or row["intent_grant"] != e.grant_hash or actual_grant != e.grant_hash or row["intent_policy"] != e.policy
            or reason.get("policy") != e.policy or reason.get("grant_hash") != e.grant_hash
            or reason.get("source_hash") != context[2] or reason.get("request_hash") != context[1]
            or reason.get("action_hash") != row["hash"] or len(request.encode()) > 16384
            or len(sources) > 16 or any(not x["analysis_complete"] for x in sources)
            or db.execute("SELECT 1 FROM analysis_stops WHERE session_hash=? AND turn_hash=?", (digest(row["session"]), digest(row["turn"]))).fetchone()):
        raise Rejected("DEMO_CONFIRM_STALE")
    candidate = e.open(row["body"])
    text = canonical(candidate)
    if (digest(text) != row["hash"] or mask(text) != text or candidate.get("route") != "mcp"
            or candidate.get("tool") not in e.grant["tools"].get("mcp", [])
            or any(x.casefold() in text.casefold() for x in e.grant.get("protected_markers", []))):
        raise Rejected("DEMO_CONFIRM_STALE")
    try:
        parsed = parse(candidate, e.grant["workspace"])
        if parsed["parser"] != "enrolled-files-1" or configuration_risk(parsed):
            raise ValueError()
        span_catalog({"user_request": request, "candidate": candidate, "sources": sources}, "B")
    except Exception:
        raise Rejected("DEMO_CONFIRM_STALE") from None
    if row["binding"] is not None:
        if digest(row["reason"]) != row["reason_hash"]:
            raise Rejected("DEMO_CONFIRM_STALE")
        expected = binding(row, row["expires"], row["reason_hash"])
        if expected != row["binding"]:
            raise Rejected("DEMO_CONFIRM_BINDING")
    return candidate, request, sources, reason


def binding(row, expires, reason_hash):
    return digest(canonical({"call": row["id"], "connection": row["intent_connection"], "session": row["session"], "turn": row["turn"],
                             "action": row["hash"], "policy": row["intent_policy"], "grant": row["intent_grant"], "request": row["intent_request"],
                             "source": row["intent_source"], "rpc": row["rpc_hash"], "reason": reason_hash, "expires": expires}))


def remember(e, machine, call, token):
    with e.db() as db:
        remember_in_db(e, db, machine, call, token)


def remember_in_db(e, db, machine, call, token):
    row = joined(db, call)
    validate(e, db, machine, row, token)
    if row["state"] != "CONFIRM" or row["binding"] is not None:
        raise Rejected("DEMO_CONFIRM_BINDING")
    expires, reason_hash = time.time()+REVIEW_SECONDS, digest(row["reason"])
    proof = binding(row, expires, reason_hash)
    db.execute("INSERT INTO demo_confirmations VALUES(?,?,?,?,0,?)", (call, proof, expires, None, reason_hash))
    e.audit(db, "APPROVAL", "HUMAN_REVIEW_PENDING", call)


def find(e, db, machine, session, tool, args, token):
    current = e._current(db, machine, session)
    action = digest(canonical({"tool": tool, "args": args, "route": "mcp"}))
    rows = db.execute("SELECT c.id FROM calls c JOIN demo_intents i ON i.call=c.id JOIN demo_confirmations d ON d.call=c.id WHERE c.session=? AND c.turn=? AND c.hash=? AND i.connection_hash=? ORDER BY c.created DESC", (session, current["turn"], action, digest(token))).fetchall()
    return joined(db, rows[0][0]) if rows else None


def state(e, db, machine, row, token=None):
    if row is None:
        return "NOT_FOUND"
    if row["resumed"]:
        return "CONSUMED"
    try:
        validate(e, db, machine, row, token)
    except Rejected:
        return "STALE"
    if row["state"] == "DENIED":
        return "REJECTED"
    if time.time() > row["expires"]:
        return "EXPIRED"
    if row["state"] == "APPROVED":
        return "APPROVED" if row["approved_at"] is not None and 0 <= time.time()-row["approved_at"] <= APPROVAL_SECONDS else "STALE"
    return "PENDING" if row["state"] == "CONFIRM" else "STALE"


def wait(e, machine, session, tool, args, token):
    with e.db() as db:
        row = find(e, db, machine, session, tool, args, token)
        status = state(e, db, machine, row, token)
        return {"status": status, "pending_ref": digest(row["id"]) if row else None,
                "expires_at": row["expires"] if row else None, "resume_allowed": status == "APPROVED"}


def pending(e, machine):
    output, truncated = [], False
    with e.db() as db:
        rows = db.execute("SELECT c.id FROM calls c JOIN demo_confirmations d ON d.call=c.id WHERE c.state='CONFIRM' ORDER BY c.created DESC LIMIT 32").fetchall()
        for item in rows:
            row = joined(db, item[0])
            if state(e, db, machine, row) != "PENDING":
                continue
            candidate, request, sources, reason = validate(e, db, machine, row)
            value = {"call": row["id"], "approval_binding": row["binding"], "candidate": candidate, "request": request,
                     "source_excerpts": [{"source_ref": digest(s["source_id"]), "excerpt": mask(s["analysis_text"][:512]), "truncated": len(s["analysis_text"])>512} for s in sources[:8]],
                     "uncertainty": {"reasons": reason.get("reasons", []), "view_checks": reason.get("view_checks"), "policy_trace": reason.get("policy_trace")},
                     "expires_at": row["expires"]}
            if len(output) >= 8 or len(canonical({"pending": [*output, value]}).encode()) > 115000:
                truncated = True
                break
            output.append(value)
    return {"version": "demo-confirm-1", "pending": output, "truncated": truncated}


def approve(e, machine, call, approve_choice, proof):
    with e.db() as db:
        row = joined(db, call)
        if state(e, db, machine, row) != "PENDING" or not isinstance(proof, str) or proof != row["binding"]:
            raise Rejected("DEMO_APPROVAL_BINDING_OR_STALE")
        validate(e, db, machine, row)
        if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (row["session"], call)).fetchone():
            raise Rejected("PRIOR_RESULT_UNOBSERVED")
        if not approve_choice:
            db.execute("UPDATE calls SET state='DENIED' WHERE id=? AND state='CONFIRM'", (call,))
            e.audit(db, "APPROVAL", "HUMAN_REJECTED", call)
            return {"state": "DENIED"}
        db.execute("INSERT INTO approvals(call,hash,turn,policy) VALUES(?,?,?,?)", (call, row["hash"], row["turn"], e.policy))
        db.execute("UPDATE demo_confirmations SET approved_at=? WHERE call=? AND approved_at IS NULL", (time.time(), call))
        db.execute("UPDATE calls SET state='APPROVED' WHERE id=? AND state='CONFIRM'", (call,))
        e.audit(db, "APPROVAL", "HUMAN_APPROVED_EXACT", call)
        return {"state": "APPROVED"}


def resume(e, machine, session, tool, args, token, rpc_hash):
    """Return None only if there is no previous confirmation for this action."""
    with e.db() as db:
        row = find(e, db, machine, session, tool, args, token)
        if row is None:
            return None
        status = state(e, db, machine, row, token)
        if status == "PENDING":
            raise Rejected("DEMO_CONFIRM_NOT_DISPATCHED")
        if status != "APPROVED":
            raise Rejected("DEMO_APPROVAL_" + status)
        if row["rpc_hash"] != rpc_hash:
            raise Rejected("DEMO_RESUME_RPC_BINDING")
        _, _, _, reason = validate(e, db, machine, row, token)
        changed = db.execute("UPDATE approvals SET consumed=1 WHERE call=? AND hash=? AND turn=? AND policy=? AND consumed=0", (row["id"], row["hash"], row["turn"], e.policy))
        if changed.rowcount != 1 or db.execute("UPDATE demo_confirmations SET resumed=1 WHERE call=? AND resumed=0", (row["id"],)).rowcount != 1:
            raise Rejected("APPROVAL_BINDING_OR_REPLAY")
        reason["demo_approval"] = {"binding": row["binding"], "approved_at": row["approved_at"], "original_decision": "CONFIRM"}
        db.execute("UPDATE calls SET state='READY',reason=? WHERE id=? AND state='APPROVED'", (canonical(reason), row["id"]))
        e._forward_in_db(db, machine, row["id"], connection_token=token)
        return row["id"]
