"""Session state and atomic call/approval/reservation transitions."""
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from app.common import (
    AUDIENCE,
    POLICY,
    SafeError,
    action,
    canonical,
    cipher,
    digest,
    mask,
    masked_tree,
    stamp,
    uid,
)
from app.pdp.policy import decide
from app.storage.f3 import F3_SCHEMA, F3Repository
from app.storage.retention import DATA_TTL, DISPOSAL_TTL, SESSION_TTL

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, task_kind TEXT NOT NULL,
 issue_id INTEGER NOT NULL, request_cipher BLOB NOT NULL, comment_cipher BLOB,
 policy_version TEXT NOT NULL, status TEXT NOT NULL, expires_at REAL NOT NULL,
 call_budget INTEGER NOT NULL CHECK(call_budget>=0),
 write_budget INTEGER NOT NULL CHECK(write_budget>=0));
CREATE TABLE IF NOT EXISTS session_tokens (
 token_sha256 TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id),
 audience TEXT NOT NULL, expires_at REAL NOT NULL, revoked_at REAL);
CREATE TABLE IF NOT EXISTS calls (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 client_request_id TEXT NOT NULL, tool_name TEXT NOT NULL, backend_id TEXT NOT NULL,
 canonical_cipher BLOB, masked_args_json TEXT NOT NULL, args_sha256 TEXT NOT NULL,
 policy_version TEXT NOT NULL, created_at REAL NOT NULL,
 UNIQUE(session_id,client_request_id));
CREATE TABLE IF NOT EXISTS decisions (
 id TEXT PRIMARY KEY, call_id TEXT UNIQUE NOT NULL REFERENCES calls(id),
 decision TEXT NOT NULL, reason_codes TEXT NOT NULL, source_ids TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals (
 id TEXT PRIMARY KEY, call_id TEXT UNIQUE NOT NULL REFERENCES calls(id),
 args_sha256 TEXT NOT NULL, policy_version TEXT NOT NULL, status TEXT NOT NULL,
 expires_at REAL NOT NULL, approved_at REAL, consumed_at REAL);
CREATE TABLE IF NOT EXISTS executions (
 call_id TEXT PRIMARY KEY REFERENCES calls(id), reservation_id TEXT UNIQUE NOT NULL,
 state TEXT NOT NULL, reserved_at REAL NOT NULL, finished_at REAL,
 effect_receipt TEXT, error_code TEXT);
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), call_id TEXT,
 kind TEXT NOT NULL, origin_ref TEXT NOT NULL, content_sha256 TEXT NOT NULL,
 masked_excerpt TEXT NOT NULL, match_values TEXT NOT NULL, collected_at REAL NOT NULL,
 UNIQUE(call_id,content_sha256));
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), call_id TEXT,
 event_kind TEXT NOT NULL, safe_payload TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS session_retention (
 session_id TEXT PRIMARY KEY REFERENCES sessions(id), created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS disposals (
 session_sha256 TEXT PRIMARY KEY, deadline REAL NOT NULL, purged_at REAL NOT NULL,
 retain_until REAL NOT NULL, unresolved_count INTEGER NOT NULL,
 call_budget INTEGER NOT NULL, write_budget INTEGER NOT NULL);
"""


class Repository(F3Repository):
    def __init__(self, path, clock=None):
        self.path = str(path)
        self.clock = clock or time.time
        self.crypto = cipher()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.tx() as db:
            # executescript implicitly commits: execute individual DDL inside our tx.
            for statement in (SCHEMA + F3_SCHEMA).split(";"):
                if statement.strip():
                    db.execute(statement)
            # Legacy SPEC-3 sessions were issued with exactly 1800s lifetime.
            # Never use migration/startup time to extend existing retention.
            db.execute("INSERT OR IGNORE INTO session_retention SELECT id,expires_at-? FROM sessions",
                       (SESSION_TTL,))
            for row in db.execute("SELECT id,masked_excerpt,match_values FROM sources").fetchall():
                if isinstance(row["masked_excerpt"], str):
                    db.execute("UPDATE sources SET masked_excerpt=?,match_values=? WHERE id=?",
                               (self.encrypt(mask(row["masked_excerpt"])), self.encrypt(row["match_values"]), row["id"]))
            for row in db.execute("SELECT id,safe_payload FROM events").fetchall():
                if isinstance(row["safe_payload"], str):
                    db.execute("UPDATE events SET safe_payload=? WHERE id=?", (self.encrypt(row["safe_payload"]), row["id"]))
        os.chmod(self.path, 0o600)

    @contextmanager
    def tx(self):
        db = sqlite3.connect(self.path, timeout=1, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def encrypt(self, value):
        return self.crypto.encrypt(value.encode("utf-8"))

    def decrypt(self, value):
        return self.crypto.decrypt(value).decode("utf-8") if value is not None else None

    def event(self, db, sid, kind, payload, cid=None):
        db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",
                   (uid(), sid, cid, kind, self.encrypt(canonical(payload)), self.clock()))

    def create_session(self, request, owner="local-user"):
        from app.common import validate
        validate('SessionCreate',request)
        sid, token, now = uid(), secrets.token_urlsafe(48), self.clock()
        expiry = now + SESSION_TTL
        with self.tx() as db:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                sid, owner, request["task_kind"], request["issue_id"],
                self.encrypt(request["user_request"]),
                self.encrypt(request["allowed_comment_body"]) if "allowed_comment_body" in request else None,
                POLICY, "ACTIVE", expiry, 8, int(request["task_kind"] == "POST_COMMENT")))
            db.execute("INSERT INTO session_retention VALUES (?,?)", (sid, now))
            db.execute('INSERT INTO session_modes VALUES (?,?)',(sid,request.get('comment_mode','EXACT')))
            db.execute("INSERT INTO session_tokens VALUES (?,?,?,?,NULL)",
                       (digest(token), sid, AUDIENCE, expiry))
            db.execute("INSERT INTO sources VALUES (?,?,NULL,?,?,?,?,?,?)", (
                uid(), sid, "USER_REQUEST", "user-request", digest(request["user_request"]),
                self.encrypt(mask(request["user_request"])[:512]), self.encrypt("[]"), now))
            self.event(db, sid, "SESSION_CREATED", {"request_sha256": digest(request["user_request"])})
        return {"session_id": sid, "task_kind": request["task_kind"], "policy_version": POLICY,
                "expires_at": stamp(expiry), "agent_session_token": token}

    def session(self, db, sid, active=True):
        row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise SafeError("RESOURCE_OUT_OF_SCOPE", 404)
        retention = db.execute("SELECT created_at FROM session_retention WHERE session_id=?", (sid,)).fetchone()
        if retention is None or retention["created_at"] + DATA_TTL <= self.clock():
            raise SafeError("SESSION_INACTIVE", 403)
        if active and (row["status"] != "ACTIVE" or row["expires_at"] <= self.clock()):
            raise SafeError("SESSION_INACTIVE", 403)
        return row

    def resolve(self, token):
        with self.tx() as db:
            row = db.execute("SELECT * FROM session_tokens WHERE token_sha256=?", (digest(token),)).fetchone()
            if row is None or row["revoked_at"] is not None or row["expires_at"] <= self.clock():
                raise SafeError("AUTH_REQUIRED", 401)
            session = self.session(db, row["session_id"])
            if row["audience"] != AUDIENCE:
                raise SafeError("AUTH_REQUIRED", 401)
            return {"session_id": session["id"], "owner_id": session["owner_id"],
                    "audience": row["audience"], "scopes": ["tools:invoke"],
                    "expires_at": stamp(min(row["expires_at"], session["expires_at"]))}

    def close(self, sid):
        with self.tx() as db:
            self.session(db, sid, active=False)
            db.execute("UPDATE sessions SET status='CLOSED' WHERE id=?", (sid,))
            db.execute("UPDATE session_tokens SET revoked_at=? WHERE session_id=?", (self.clock(), sid))
            self.event(db, sid, "SESSION_CLOSED", {})
        return {"session_id": sid, "status": "CLOSED"}

    def call(self, db, cid):
        row = db.execute("SELECT * FROM calls WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise SafeError("RESOURCE_OUT_OF_SCOPE", 404)
        self.session(db, row["session_id"], active=False)
        return row

    def check_reply(self, db, cid):
        call = self.call(db, cid)
        decision = db.execute("SELECT * FROM decisions WHERE call_id=?", (cid,)).fetchone()
        approval = db.execute("SELECT * FROM approvals WHERE call_id=?", (cid,)).fetchone()
        execution = db.execute("SELECT * FROM executions WHERE call_id=?", (cid,)).fetchone()
        return {"call_id": cid, "decision": decision["decision"], "args_sha256": call["args_sha256"],
                "policy_version": call["policy_version"], "reason_codes": json.loads(decision["reason_codes"]),
                "source_ids": json.loads(decision["source_ids"]),
                "approval_id": approval["id"] if approval else None,
                "approval_status": approval["status"] if approval else None,
                "execution_state": execution["state"] if execution else "NOT_STARTED",
                **self.metadata(db,cid)}

    def prepare_check(self, value, model):
        self.analysis_model=model
        args, tool, sid = value["args"], value["tool_name"], value["session_id"]
        normalized = action(tool, args, value["backend_id"])
        sha = digest(normalized)
        with self.tx() as db:
            self.expire_analyses(db)
            session = self.session(db, sid)
            if session["policy_version"] != POLICY:
                raise SafeError("POLICY_CHANGED")
            if value.get("resume_call_id"):
                call = self.call(db, value["resume_call_id"])
                if call["session_id"] != sid:
                    raise SafeError("RESOURCE_OUT_OF_SCOPE", 403)
                if call["args_sha256"] != sha or call["policy_version"] != POLICY:
                    raise SafeError("ACTION_BINDING_MISMATCH")
                self.require_analysis_binding(db,call,session)
                return self.check_reply(db, call["id"]), None
            previous = db.execute("SELECT * FROM calls WHERE session_id=? AND client_request_id=?",
                                  (sid, value["client_request_id"])).fetchone()
            if previous:
                if previous["args_sha256"] != sha:
                    raise SafeError("REQUEST_KEY_CONFLICT")
                self.require_analysis_binding(db,previous,session)
                return self.check_reply(db, previous["id"]), None
            if db.execute("SELECT 1 FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=? AND e.state='UNKNOWN' LIMIT 1", (sid,)).fetchone():
                raise SafeError("EXECUTION_OUTCOME_UNKNOWN")
            if session["call_budget"] == 0:
                raise SafeError("TASK_CALL_BUDGET_EXHAUSTED")
            decision, reasons = decide(session, tool, args, self.decrypt(session["comment_cipher"]))
            source_ids = []
            for source in db.execute("SELECT * FROM sources WHERE session_id=? ORDER BY collected_at", (sid,)):
                if source["kind"] == "USER_REQUEST":
                    source_ids.append(source["id"])
                elif any(x and x in canonical(args) for x in json.loads(self.decrypt(source["match_values"]))):
                    source_ids.append(source["id"])
                    if "SOURCE_VALUE_OBSERVED" not in reasons:
                        reasons.append("SOURCE_VALUE_OBSERVED")
            cid = uid()
            db.execute("UPDATE sessions SET call_budget=call_budget-1 WHERE id=? AND call_budget>0", (sid,))
            db.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?)", (
                cid, sid, value["client_request_id"], tool, value["backend_id"],
                None if "SENSITIVE_DATA_IN_ARGUMENTS" in reasons else self.encrypt(normalized),
                canonical(masked_tree(args)), sha, POLICY, self.clock()))
            snapshot,stage,snapshot_sha = None,'POLICY',None
            if decision=='CONFIRM':
                snapshot,decision,reasons,stage,snapshot_sha = self.begin_analysis(db,session,value,cid,sha,model)
                if snapshot:
                    source_ids=[s['source_id'] for s in snapshot['sources']]
            db.execute('INSERT INTO call_metadata VALUES (?,?,?,?,?)',
                (cid,snapshot['analysis_id'] if snapshot else None,stage,snapshot_sha,self.encrypt('[]')))
            db.execute("INSERT INTO decisions VALUES (?,?,?,?,?)",
                       (uid(), cid, decision, json.dumps(reasons), json.dumps(source_ids[:16])))
            if decision == "CONFIRM":
                db.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,NULL,NULL)",
                           (uid(), cid, sha, POLICY, "PENDING", self.clock() + 300))
            self.event(db, sid, "CHECKED", {"decision": decision, "args_sha256": sha,
                "tool_name": tool, "args": masked_tree(args)}, cid)
            return self.check_reply(db, cid), snapshot

    def reserve(self, cid, value):
        with self.tx() as db:
            call = self.call(db, cid)
            session = self.session(db, call["session_id"])
            if call["policy_version"] != POLICY or session["policy_version"] != POLICY:
                raise SafeError("POLICY_CHANGED")
            normalized = action(value["tool_name"], value["args"], value["backend_id"])
            if call["args_sha256"] != digest(normalized):
                raise SafeError("ACTION_BINDING_MISMATCH")
            reply = self.check_reply(db, cid)
            if reply["decision"] == "DENY":
                raise SafeError(reply["reason_codes"][0], 403)
            self.require_analysis_binding(db,call,session)
            existing = db.execute("SELECT * FROM executions WHERE call_id=?", (cid,)).fetchone()
            if existing:
                if existing["state"] == "SUCCEEDED":
                    return {"call_id": cid, "execute": False, "state": "SUCCEEDED",
                            "reservation_id": existing["reservation_id"],
                            "receipt": json.loads(existing["effect_receipt"])}
                reasons = {"RESERVED": "EXECUTION_IN_PROGRESS", "UNKNOWN": "EXECUTION_OUTCOME_UNKNOWN",
                           "FAILED": "EXECUTION_FAILED"}
                raise SafeError(reasons[existing["state"]])
            uncertain = db.execute("SELECT 1 FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=? AND e.state='UNKNOWN' LIMIT 1", (session["id"],)).fetchone()
            if uncertain:
                raise SafeError("EXECUTION_OUTCOME_UNKNOWN")
            if call["tool_name"] == "post_issue_comment" and db.execute(
                "SELECT 1 FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=? AND e.state='RESERVED' LIMIT 1", (session["id"],)).fetchone():
                raise SafeError("EXECUTION_IN_PROGRESS")
            self.guard_analysis(db,call,session)
            if reply["decision"] == "CONFIRM":
                approval = db.execute("SELECT * FROM approvals WHERE call_id=?", (cid,)).fetchone()
                if approval["expires_at"] <= self.clock():
                    raise SafeError("APPROVAL_EXPIRED")
                if approval["status"] != "APPROVED":
                    codes = {"PENDING": "APPROVAL_PENDING", "REJECTED": "APPROVAL_REJECTED",
                             "EXPIRED": "APPROVAL_EXPIRED", "CONSUMED": "APPROVAL_CONSUMED"}
                    raise SafeError(codes[approval["status"]])
                if approval["args_sha256"] != call["args_sha256"] or approval["policy_version"] != POLICY:
                    raise SafeError("ACTION_BINDING_MISMATCH")
                db.execute("UPDATE approvals SET status='CONSUMED',consumed_at=? WHERE id=?",
                           (self.clock(), approval["id"]))
            if call["tool_name"] == "post_issue_comment":
                changed = db.execute("UPDATE sessions SET write_budget=write_budget-1 WHERE id=? AND write_budget>0",
                                     (session["id"],)).rowcount
                if changed != 1:
                    raise SafeError("TASK_WRITE_BUDGET_EXHAUSTED")
            rid, now = uid(), self.clock()
            db.execute("INSERT INTO executions VALUES (?,?, 'RESERVED',?,NULL,NULL,NULL)", (cid, rid, now))
            self.event(db, session["id"], "RESERVED", {"reservation_id": rid}, cid)
            return {"call_id": cid, "execute": True, "state": "RESERVED", "reservation_id": rid,
                    "start_before": stamp(now + 30)}

    @staticmethod
    def execution_view(row):
        return {"call_id": row["call_id"], "state": row["state"],
                "receipt": json.loads(row["effect_receipt"]) if row["effect_receipt"] else None,
                "error_code": row["error_code"],
                "finished_at": stamp(row["finished_at"]) if row["finished_at"] else None}

    def report(self, cid, value):
        with self.tx() as db:
            call = self.call(db, cid)
            row = db.execute("SELECT * FROM executions WHERE call_id=?", (cid,)).fetchone()
            if row is None or row["reservation_id"] != value["reservation_id"]:
                raise SafeError("ACTION_BINDING_MISMATCH")
            receipt = value.get("receipt")
            if receipt and (receipt["call_id"] != cid or receipt["session_id"] != call["session_id"] or
                            receipt["tool_name"] != call["tool_name"] or receipt["write_count_for_call"] !=
                            int(call["tool_name"] == "post_issue_comment")):
                raise SafeError("ACTION_BINDING_MISMATCH")
            encoded = canonical(receipt) if receipt else None
            state = value["state"]
            if row["state"] == state and row["effect_receipt"] == encoded:
                return self.execution_view(row)
            if row["state"] != "RESERVED" and not (row["state"] == "UNKNOWN" and
                    value.get("reconciled") is True and state in ("SUCCEEDED", "FAILED")):
                raise SafeError("ACTION_BINDING_MISMATCH")
            if state == "SUCCEEDED" and not receipt:
                raise SafeError("ACTION_BINDING_MISMATCH")
            if state == "SUCCEEDED" and call["tool_name"] in ("get_issue", "read_workspace_file") and not db.execute(
                "SELECT 1 FROM sources WHERE call_id=? LIMIT 1", (cid,)).fetchone():
                raise SafeError("AUDIT_UNAVAILABLE", 503)
            code = value.get("error_code")
            # Error detail is a reason identifier only. Never persist peer messages.
            if code and code not in ("EXECUTION_FAILED", "EXECUTION_OUTCOME_UNKNOWN", "AUDIT_UNAVAILABLE"):
                raise SafeError("INVALID_ARGUMENTS", 422)
            db.execute("UPDATE executions SET state=?,finished_at=?,effect_receipt=?,error_code=? WHERE call_id=?",
                       (state, self.clock(), encoded, code, cid))
            self.event(db, call["session_id"], "EXECUTION_REPORTED", {"state": state}, cid)
            return self.execution_view(db.execute("SELECT * FROM executions WHERE call_id=?", (cid,)).fetchone())

    def sweep(self, now=None):
        now = self.clock() if now is None else now
        with self.tx() as db:
            self.expire_analyses(db)
            for row in db.execute("SELECT e.* FROM executions e JOIN calls c ON c.id=e.call_id JOIN session_retention r ON r.session_id=c.session_id WHERE e.state='RESERVED' AND e.reserved_at<=? AND r.created_at+?>?", (now - 30, DATA_TTL, now)).fetchall():
                call = self.call(db, row["call_id"])
                db.execute("UPDATE executions SET state='UNKNOWN',finished_at=?,error_code='EXECUTION_OUTCOME_UNKNOWN' WHERE call_id=?",
                           (now, row["call_id"]))
                self.event(db, call["session_id"], "RESERVATION_STALE", {"state": "UNKNOWN"}, row["call_id"])
            db.execute("UPDATE approvals SET status='EXPIRED' WHERE status IN ('PENDING','APPROVED') AND expires_at<=?", (now,))
            db.execute("UPDATE sessions SET status='EXPIRED' WHERE status='ACTIVE' AND expires_at<=?", (now,))
            self.purge(db, now)

    def purge(self, db, now):
        for row in db.execute("SELECT s.*,r.created_at FROM sessions s JOIN session_retention r ON r.session_id=s.id WHERE r.created_at+?<=?", (DATA_TTL, now)).fetchall():
            sid, deadline = row["id"], row["created_at"] + DATA_TTL
            unresolved = db.execute("SELECT count(*) FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=? AND e.state IN ('RESERVED','UNKNOWN')", (sid,)).fetchone()[0]
            # RESERVED is unresolved, never successful. This body-free record is
            # bounded by the original deadline, including a late restart/purge.
            db.execute("INSERT OR IGNORE INTO disposals VALUES (?,?,?,?,?,?,?)",
                       (digest(sid), deadline, now, deadline + DISPOSAL_TTL,
                        unresolved, row["call_budget"], row["write_budget"]))
            for statement in (
                "DELETE FROM call_metadata WHERE call_id IN (SELECT id FROM calls WHERE session_id=?)",
                "DELETE FROM analyses WHERE call_id IN (SELECT id FROM calls WHERE session_id=?)",
                "DELETE FROM source_analysis WHERE source_id IN (SELECT id FROM sources WHERE session_id=?)",
                "DELETE FROM session_modes WHERE session_id=?",
                "DELETE FROM executions WHERE call_id IN (SELECT id FROM calls WHERE session_id=?)",
                "DELETE FROM approvals WHERE call_id IN (SELECT id FROM calls WHERE session_id=?)",
                "DELETE FROM decisions WHERE call_id IN (SELECT id FROM calls WHERE session_id=?)",
                "DELETE FROM sources WHERE session_id=?",
                "DELETE FROM events WHERE session_id=?",
                "DELETE FROM calls WHERE session_id=?",
                "DELETE FROM session_tokens WHERE session_id=?",
                "DELETE FROM session_retention WHERE session_id=?",
            ):
                db.execute(statement, (sid,))
            db.execute("DELETE FROM sessions WHERE id=?", (sid,))
        db.execute("DELETE FROM disposals WHERE retain_until<=?", (now,))

    def source(self, value):
        with self.tx() as db:
            call = self.call(db, value["call_id"])
            self.session(db, call["session_id"])
            expected = {"get_issue": "EXTERNAL", "read_workspace_file": "WORKSPACE_DATA"}
            if expected.get(call["tool_name"]) != value["kind"]:
                raise SafeError("RESOURCE_OUT_OF_SCOPE", 403)
            execution = db.execute("SELECT * FROM executions WHERE call_id=?", (call["id"],)).fetchone()
            if execution is None or execution["state"] not in ("RESERVED", "SUCCEEDED", "UNKNOWN"):
                raise SafeError("ACTION_BINDING_MISMATCH")
            previous = db.execute("SELECT * FROM sources WHERE call_id=? AND content_sha256=?",
                                  (call["id"], value["content_sha256"])).fetchone()
            if previous:
                return self.source_view(previous)
            source_id = uid()
            text = value.get('analysis_text','')
            from app.pdp.semantic import material
            safe = material(text)
            if (safe['analysis_text'] != text or value.get('analysis_text_sha256',digest(text))!=digest(text)):
                raise SafeError('INVALID_ARGUMENTS',422)
            db.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)", (
                source_id, call["session_id"], call["id"], value["kind"], mask(value["origin_ref"])[:256],
                value["content_sha256"], self.encrypt(mask(value["masked_excerpt"])[:512]),
                self.encrypt(json.dumps([mask(x)[:128] for x in value["match_values"]])), self.clock()))
            db.execute('INSERT INTO source_analysis VALUES (?,?,?,?)',
                (source_id,self.encrypt(text),digest(text),int(value.get('analysis_complete',False) and safe['analysis_complete'])))
            self.event(db, call["session_id"], "SOURCE_COLLECTED", {"source_id": source_id}, call["id"])
            return self.source_view(db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone())

    def source_view(self, row):
        return {"source_id": row["id"], "session_id": row["session_id"], "call_id": row["call_id"],
                "kind": row["kind"], "origin_ref": row["origin_ref"], "content_sha256": row["content_sha256"],
                "masked_excerpt": self.decrypt(row["masked_excerpt"]), "collected_at": stamp(row["collected_at"])}

    def approval_view(self, row):
        status = row["status"]
        if status in ("PENDING", "APPROVED") and row["expires_at"] <= self.clock():
            status = "EXPIRED"
        return {"approval_id": row["id"], "call_id": row["call_id"], "args_sha256": row["args_sha256"],
                "policy_version": row["policy_version"], "status": status, "expires_at": stamp(row["expires_at"])}

    def approve(self, aid, expected=None, reject=False):
        with self.tx() as db:
            row = db.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
            if row is None:
                raise SafeError("RESOURCE_OUT_OF_SCOPE", 404)
            call = self.call(db, row["call_id"])
            session = self.session(db, call["session_id"])
            if call["policy_version"] != POLICY or session["policy_version"] != POLICY:
                raise SafeError("POLICY_CHANGED")
            if row["expires_at"] <= self.clock():
                raise SafeError("APPROVAL_EXPIRED")
            if row["status"] != "PENDING":
                raise SafeError("APPROVAL_CONSUMED" if row["status"] == "CONSUMED" else "ACTION_BINDING_MISMATCH")
            if not reject and row["args_sha256"] != expected:
                raise SafeError("ACTION_BINDING_MISMATCH")
            if self.check_reply(db, call["id"])["decision"] != "CONFIRM":
                raise SafeError("ACTION_BINDING_MISMATCH")
            status = "REJECTED" if reject else "APPROVED"
            db.execute("UPDATE approvals SET status=?,approved_at=? WHERE id=?", (status, self.clock(), aid))
            self.event(db, call["session_id"], "APPROVAL_" + status, {"approval_id": aid}, call["id"])
            return self.approval_view(db.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone())

    def timeline(self, sid):
        with self.tx() as db:
            session = self.session(db, sid, active=False)
            status = session["status"]
            if status == "ACTIVE" and session["expires_at"] <= self.clock():
                status = "EXPIRED"
            calls = db.execute("SELECT id FROM calls WHERE session_id=? ORDER BY created_at", (sid,)).fetchall()
            approvals, executions = [], []
            for call in calls:
                row = db.execute("SELECT * FROM approvals WHERE call_id=?", (call["id"],)).fetchone()
                if row:
                    approvals.append(self.approval_view(row))
                row = db.execute("SELECT * FROM executions WHERE call_id=?", (call["id"],)).fetchone()
                if row:
                    executions.append(self.execution_view(row))
            events = [{"event_id": row["id"], "kind": row["event_kind"], "created_at": stamp(row["created_at"]),
                       "call_id": row["call_id"], "safe_payload": json.loads(self.decrypt(row["safe_payload"]))}
                      for row in db.execute("SELECT * FROM events WHERE session_id=? ORDER BY created_at", (sid,))]
            return {"session_id": sid, "task_kind": session["task_kind"], "status": status,
                    "policy_version": session["policy_version"], "sources": [self.source_view(row) for row in
                     db.execute("SELECT * FROM sources WHERE session_id=? ORDER BY collected_at", (sid,))],
                    "checks": [self.check_reply(db, call["id"]) for call in calls],
                    "approvals": approvals, "executions": executions, "events": events}
