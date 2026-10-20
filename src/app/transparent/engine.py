"""Encrypted turn/source binding and one-shot authorization for generic adapters.

An execution reservation is NOT an upstream receipt or an idempotency guarantee.
Only authenticated adapters may write events; model-supplied provenance is ignored.
"""
import asyncio
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet

from app.common import canonical, digest, mask
from app.pdp.diagnostics import AnalysisFailure, detail, failure_details
from app.pdp.semantic import (
    SPAN_CONTRACT,
    SPAN_PROMPT_VERSION,
    combine,
    material,
    span_inputs,
    validated_spans,
)

SPEC = "MVP-SPEC-5"
POLICY = "hookgw-2026-10-16-v1"


class Rejected(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def bounded(value, limit=32768):
    if len(canonical(value).encode()) > limit:
        raise Rejected("INPUT_LIMIT")
    return value


class Engine:
    def bound_output(self, value):
        return bounded(value, 65536)

    def __init__(self, path, key, grant, judge=None, policy_router=None, *, preserve_history_on_policy_change=False):
        self.path, self.box, self.grant, self.judge = str(path), Fernet(key), json.loads(canonical(grant)), judge
        self.policy_router = policy_router
        self.policy = policy_router.policy if policy_router else POLICY
        self.grant_hash = digest(canonical({"grant": self.grant, "policy": self.policy} if policy_router else self.grant))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, machine TEXT, turn TEXT, body BLOB);
                CREATE TABLE IF NOT EXISTS turns(session TEXT, id TEXT, hash TEXT, body BLOB,
                   PRIMARY KEY(session,id));
                CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, session TEXT, turn TEXT,
                   hash TEXT, path TEXT, state TEXT, decision TEXT, reason TEXT, body BLOB, created REAL);
                CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, session TEXT, call TEXT UNIQUE, body BLOB);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at REAL, kind TEXT, code TEXT, call TEXT);
                CREATE TABLE IF NOT EXISTS approvals(call TEXT PRIMARY KEY, hash TEXT, turn TEXT,
                   policy TEXT, consumed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS connections(hash TEXT PRIMARY KEY, machine TEXT, session TEXT);
                CREATE TABLE IF NOT EXISTS expiry(kind TEXT, id TEXT, deadline REAL, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS tombstones(id TEXT PRIMARY KEY, hash TEXT, state TEXT);
                CREATE TABLE IF NOT EXISTS transport(call TEXT PRIMARY KEY, body BLOB);
                CREATE TABLE IF NOT EXISTS configuration(id INTEGER PRIMARY KEY, hash TEXT);
                CREATE TABLE IF NOT EXISTS analysis_stops(session_hash TEXT,turn_hash TEXT,details TEXT,
                   PRIMARY KEY(session_hash,turn_hash));
                CREATE TABLE IF NOT EXISTS gateway_rejections(request TEXT PRIMARY KEY,at REAL,code TEXT,call_hash TEXT);
                CREATE TABLE IF NOT EXISTS demo_intents(call TEXT PRIMARY KEY,connection_hash TEXT,
                   request_hash TEXT,source_hash TEXT,grant_hash TEXT,policy TEXT,claimed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS demo_rpc_bindings(call TEXT PRIMARY KEY,rpc_hash TEXT);
                CREATE TABLE IF NOT EXISTS demo_confirmations(call TEXT PRIMARY KEY,binding TEXT,expires REAL,
                   approved_at REAL,resumed INTEGER DEFAULT 0,reason_hash TEXT);
            """)
            # Process restart cannot establish whether the host/upstream executed.
            db.execute("UPDATE calls SET state='UNKNOWN' WHERE state IN ('ANALYZING','EXECUTING')")
            # Additive migration also protects the original failed user turn.
            # Old call rows/reasons stay byte-for-byte unchanged. No budget writes.
            for failed in db.execute("SELECT id,session,turn,reason FROM calls WHERE state='DENIED' AND reason IS NOT NULL").fetchall():
                context = json.loads(failed["reason"])
                if "ANALYSIS_UNAVAILABLE" in context.get("reasons", []):
                    diagnostics = context.get("diagnostic") or []
                    if isinstance(diagnostics, dict):
                        diagnostics = [diagnostics]
                    safe = [detail(x.get("code"), x.get("view"), x) for x in diagnostics[:2] if isinstance(x, dict)]
                    db.execute("INSERT OR IGNORE INTO analysis_stops VALUES(?,?,?)",
                               (digest(failed["session"]), digest(failed["turn"]), canonical({"diagnostic": safe, "trigger_call_hash": digest(failed["id"])})))
            old = db.execute("SELECT hash FROM configuration WHERE id=1").fetchone()
            if old is None or old[0] != self.grant_hash:
                if not preserve_history_on_policy_change:
                    db.execute("UPDATE calls SET state='DENIED',decision='DENY',reason=? WHERE state IN ('PENDING','READY','CONFIRM','APPROVED')", (canonical({"reasons": ["POLICY_CHANGED"]}),))
                    db.execute("UPDATE approvals SET consumed=1")
                db.execute("INSERT OR REPLACE INTO configuration VALUES(1,?)", (self.grant_hash,))
            self.cleanup(db)

    @contextmanager
    def db(self):
        with sqlite3.connect(self.path, timeout=3, isolation_level=None) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def seal(self, value):
        return self.box.encrypt(canonical(value).encode())

    def open(self, value):
        return json.loads(self.box.decrypt(value))

    def audit(self, db, kind, code, call=""):
        db.execute("INSERT INTO audit(at,kind,code,call) VALUES(?,?,?,?)", (time.time(), kind, code, call))
        db.execute("DELETE FROM audit WHERE id NOT IN (SELECT id FROM audit ORDER BY id DESC LIMIT 4096)")

    def forget(self, db, session):
        db.execute("INSERT OR IGNORE INTO tombstones SELECT id,hash,state FROM calls WHERE session=? AND state='UNKNOWN'", (session,))
        db.execute("DELETE FROM audit WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM approvals WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM transport WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM demo_confirmations WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM demo_rpc_bindings WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM demo_intents WHERE call IN (SELECT id FROM calls WHERE session=?)", (session,))
        db.execute("DELETE FROM sources WHERE session=?", (session,))
        db.execute("DELETE FROM calls WHERE session=?", (session,))
        db.execute("DELETE FROM turns WHERE session=?", (session,))
        db.execute("DELETE FROM sessions WHERE id=?", (session,))
        db.execute("DELETE FROM connections WHERE session=?", (session,))
        db.execute("DELETE FROM expiry WHERE kind='session' AND id=?", (session,))

    def cleanup(self, db):
        # Seven-day ciphertext retention; logical secure-delete, not SSD/backup erasure proof.
        expired = db.execute("SELECT id FROM expiry WHERE kind='session' AND deadline<?", (time.time() - 6 * 86400,)).fetchall()
        for row in expired:
            self.forget(db, row[0])
        db.execute("DELETE FROM connections WHERE hash IN (SELECT id FROM expiry WHERE kind='connection' AND deadline<?)", (time.time(),))
        db.execute("DELETE FROM expiry WHERE kind='connection' AND deadline<?", (time.time(),))

    def purge(self, session):
        with self.db() as db:
            if db.execute("SELECT 1 FROM calls WHERE session=? AND state IN ('ANALYZING','READY','EXECUTING','UNKNOWN')", (session,)).fetchone():
                raise Rejected("UNRESOLVED_EXECUTION")
            self.forget(db, session)

    def expires(self, db, kind, key):
        row = db.execute("SELECT deadline FROM expiry WHERE kind=? AND id=?", (kind, key)).fetchone()
        if not row or row[0] < time.time():
            raise Rejected("CONNECTION_OR_SESSION_EXPIRED")

    def connect(self, machine, token):
        with self.db() as db:
            self.cleanup(db)
            if db.execute("SELECT count(*) FROM connections").fetchone()[0] >= 128:
                raise Rejected("CONNECTION_LIMIT")
            db.execute("INSERT INTO connections VALUES(?,?,NULL)", (digest(token), machine))
            db.execute("INSERT INTO expiry VALUES('connection',?,?)", (digest(token), time.time() + 86400))

    def connection(self, token, session=None):
        with self.db() as db:
            self.expires(db, "connection", digest(token))
            row = db.execute("SELECT * FROM connections WHERE hash=?", (digest(token),)).fetchone()
            if not row or session and row["session"] not in (None, session):
                raise Rejected("CONNECTION_BINDING")
            if session:
                db.execute("UPDATE connections SET session=? WHERE hash=?", (session, digest(token)))
            return row["machine"], session or row["session"]

    def disconnect_metadata(self, machine, token):
        with self.db() as db:
            row = db.execute("SELECT * FROM connections WHERE hash=?", (digest(token),)).fetchone()
            if not row or row["machine"] != machine:
                raise Rejected("CONNECTION_BINDING")
            if row["session"] is not None:
                raise Rejected("CONNECTION_ALREADY_BOUND")
            db.execute("DELETE FROM connections WHERE hash=?", (digest(token),))
            db.execute("DELETE FROM expiry WHERE kind='connection' AND id=?", (digest(token),))
        return {"state": "DISCONNECTED"}

    def close_demo_connection(self, machine, token):
        """Revoke this child only; an existing forward may already have effects."""
        connection_hash = digest(token)
        with self.db() as db:
            row = db.execute("SELECT machine FROM connections WHERE hash=?", (connection_hash,)).fetchone()
            if row and row["machine"] != machine:
                raise Rejected("CONNECTION_BINDING")
            if row:
                for call in db.execute("SELECT c.id,c.state FROM calls c JOIN demo_intents i ON i.call=c.id WHERE i.connection_hash=?", (connection_hash,)).fetchall():
                    if call["state"] == "EXECUTING":
                        db.execute("UPDATE calls SET state='UNKNOWN' WHERE id=?", (call["id"],))
                        self.audit(db, "TRANSPORT", "UNKNOWN_NO_RETRY", call["id"])
                    elif call["state"] in ("PENDING", "ANALYZING", "READY", "CONFIRM", "APPROVED"):
                        db.execute("UPDATE calls SET state='STALE' WHERE id=?", (call["id"],))
                        self.audit(db, "INTENT", "CHILD_CONNECTION_CLOSED", call["id"])
                db.execute("DELETE FROM connections WHERE hash=?", (connection_hash,))
                db.execute("DELETE FROM expiry WHERE kind='connection' AND id=?", (connection_hash,))
        return {"state": "CLOSED"}

    def safe_input(self, text):
        return mask(text) == text

    def source_material(self, text):
        return material(text)

    def complete_sources(self, sources):
        return len(sources) <= 16 and all(row['analysis_complete'] for row in sources)

    def turn(self, machine, session, turn, prompt, cwd):
        bounded(prompt, 16384)
        if not all(isinstance(x, str) and 0 < len(x) <= 512 for x in (machine, session, turn, cwd)):
            raise Rejected("INVALID_EVENT")
        if not isinstance(prompt, str) or not prompt.strip() or not self.safe_input(prompt):
            raise Rejected("SENSITIVE_OR_EMPTY_REQUEST")
        if cwd.casefold().rstrip("/\\") != self.grant["workspace"].casefold().rstrip("/\\"):
            raise Rejected("WORKSPACE_MISMATCH")
        h = digest(prompt)
        with self.db() as db:
            self.cleanup(db)
            old = db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
            if old:
                self.expires(db, "session", session)
            elif db.execute("SELECT count(*) FROM sessions").fetchone()[0] >= 64:
                raise Rejected("SESSION_LIMIT")
            prior = db.execute("SELECT hash FROM turns WHERE session=? AND id=?", (session, turn)).fetchone()
            if old and old["machine"] != machine or prior and prior["hash"] != h:
                raise Rejected("TURN_FORGERY")
            if prior:
                if old["turn"] != turn:
                    raise Rejected("STALE_TURN")
                return {"turn": turn, "duplicate": True}
            db.execute("INSERT INTO turns VALUES(?,?,?,?)", (session, turn, h, self.seal({"prompt": prompt})))
            db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?)",
                       (session, machine, turn, self.seal({"cwd": cwd})))
            if not old:
                db.execute("INSERT INTO expiry VALUES('session',?,?)", (session, time.time() + 86400))
            db.execute("UPDATE calls SET state='STALE' WHERE session=? AND state IN ('PENDING','CONFIRM','READY','APPROVED','ANALYZING')", (session,))
            self.audit(db, "TURN", "RECORDED")
        return {"turn": turn}

    def _current(self, db, machine, session, turn=None):
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
        if not row or row["machine"] != machine or turn and row["turn"] != turn:
            raise Rejected("SESSION_OR_TURN_MISMATCH")
        self.expires(db, "session", session)
        return row

    def register(self, machine, session, turn, call, tool, args, path):
        bounded(args)
        if path not in ("native", "mcp") or not isinstance(call, str) or not 0 < len(call) <= 512:
            raise Rejected("INVALID_EVENT")
        candidate = {"tool": tool, "args": args, "route": path}
        h = digest(canonical(candidate))
        with self.db() as db:
            self._current(db, machine, session, turn)
            if db.execute("SELECT count(*) FROM calls WHERE session=?", (session,)).fetchone()[0] >= 1024:
                raise Rejected("CALL_LIMIT")
            if db.execute("SELECT 1 FROM calls WHERE id=? UNION SELECT 1 FROM tombstones WHERE id=?", (call, call)).fetchone():
                raise Rejected("CALL_REPLAY")
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?,'PENDING',NULL,NULL,?,?)",
                       (call, session, turn, h, path, self.seal(candidate), time.time()))
            self.audit(db, "PRE", "REGISTERED", call)
        return {"call": call, "action_hash": h}

    def pending_mcp(self, machine, session, tool, args):
        h = digest(canonical({"tool": tool, "args": args, "route": "mcp"}))
        with self.db() as db:
            s = self._current(db, machine, session)
            rows = db.execute("SELECT id FROM calls WHERE session=? AND turn=? AND hash=? AND path='mcp' AND state='READY'",
                              (session, s["turn"], h)).fetchall()
            if len(rows) != 1:
                raise Rejected("NO_UNIQUE_HOOK_BINDING")
            return rows[0]["id"]

    def _demo_intent_context(self, db, machine, session, turn, connection_token):
        """Cheap current controls only. No semantic judgment or execution lease."""
        self._current(db, machine, session, turn)
        connection_hash = digest(connection_token)
        self.expires(db, "connection", connection_hash)
        connection = db.execute("SELECT * FROM connections WHERE hash=?", (connection_hash,)).fetchone()
        if not connection or connection["machine"] != machine or connection["session"] != session:
            raise Rejected("CONNECTION_BINDING")
        actual_grant = digest(canonical({"grant": self.grant, "policy": self.policy} if self.policy_router else self.grant))
        if actual_grant != self.grant_hash:
            raise Rejected("FORWARD_SNAPSHOT_STALE")
        prompts = [self.open(row[0])["prompt"] for row in db.execute("SELECT body FROM turns WHERE session=? ORDER BY rowid", (session,))]
        request = canonical({"actual_user_turns_chronological": prompts, "latest_turn": len(prompts) - 1})
        sources = [self.open(row[0]) for row in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (session,))]
        if len(request.encode()) > 16384:
            raise Rejected("USER_CONTEXT_LIMIT")
        if not self.complete_sources(sources):
            raise Rejected("SOURCE_CONTEXT_INCOMPLETE")
        if db.execute("SELECT 1 FROM analysis_stops WHERE session_hash=? AND turn_hash=?", (digest(session), digest(turn))).fetchone():
            raise Rejected("TURN_ANALYSIS_STOPPED")
        return connection_hash, digest(request), digest(canonical(sources))

    def register_demo_intent(self, machine, session, turn, call, tool, args, connection_token):
        """The hook records a proposal before host approval, never PDP ALLOW.

        Only the demo server route exposes this. A later gateway call must claim
        the same connection/turn/args/current context before one fresh analysis.
        """
        from app.transparent.jev_policy import configuration_risk
        from app.transparent.tool_schema import parse

        bounded(args)
        if not isinstance(call, str) or not 0 < len(call) <= 512:
            raise Rejected("INVALID_EVENT")
        candidate = {"tool": tool, "args": args, "route": "mcp"}
        action_hash = digest(canonical(candidate))
        with self.db() as db:
            self._current(db, machine, session, turn)
            if db.execute("SELECT 1 FROM calls WHERE id=? UNION SELECT 1 FROM tombstones WHERE id=?", (call, call)).fetchone():
                raise Rejected("CALL_REPLAY")
            context = self._demo_intent_context(db, machine, session, turn, connection_token)
            existing = db.execute("SELECT c.id,c.state,d.expires FROM calls c JOIN demo_intents i ON i.call=c.id LEFT JOIN demo_confirmations d ON d.call=c.id WHERE c.session=? AND c.turn=? AND c.hash=? AND i.claimed=1 AND i.connection_hash=? AND i.grant_hash=? AND i.policy=? AND c.state IN ('CONFIRM','APPROVED','DENIED','STALE','EXECUTING','UNKNOWN','OBSERVED','OBSERVED_ERROR') ORDER BY c.created DESC LIMIT 1",
                                  (session, turn, action_hash, context[0], self.grant_hash, self.policy)).fetchone() if tool == "write_file" else None
            if existing:
                self.audit(db, "INTENT", "EXISTING_CONFIRM_NO_REANALYSIS", existing["id"])
                # An obsolete source/request/approval must not advertise a review
                # that the human-only pending endpoint correctly refuses to show.
                from app.transparent.demo_approval import joined, state
                terminal = state(self, db, machine, joined(db, existing["id"]), connection_token) not in ("PENDING", "APPROVED")
                return {"call": call, "intent": "EXISTING_TERMINAL" if terminal else "EXISTING_PENDING", "pending_ref": digest(existing["id"])}
            if db.execute("SELECT count(*) FROM calls WHERE session=?", (session,)).fetchone()[0] >= 1024:
                raise Rejected("CALL_LIMIT")
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?,'PENDING',NULL,NULL,?,?)", (call, session, turn, action_hash, "mcp", self.seal(candidate), time.time()))
            self.audit(db, "PRE", "REGISTERED", call)
            row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
            try:
                context = self._demo_intent_context(db, machine, session, turn, connection_token)
                if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (session, call)).fetchone():
                    raise Rejected("PRIOR_RESULT_UNOBSERVED")
                candidate = self.open(row["body"])
                text = canonical(candidate)
                if tool not in self.grant["tools"].get("mcp", []):
                    raise Rejected("UNSUPPORTED_TOOL")
                if not self.safe_input(text):
                    raise Rejected("SENSITIVE_CANDIDATE")
                if any(marker.casefold() in text.casefold() for marker in self.grant.get("protected_markers", [])):
                    raise Rejected("PROTECTED_RESOURCE")
                try:
                    parsed = parse(candidate, self.grant["workspace"])
                except (ValueError, KeyError, TypeError):
                    raise Rejected("TOOL_ARGUMENTS_UNPARSED_OR_SCOPE") from None
                if parsed["parser"] != "enrolled-files-1" or parsed["action"] not in ("READ", "WRITE"):
                    raise Rejected("UNSUPPORTED_TOOL")
                risk = configuration_risk(parsed)
                if risk:
                    raise Rejected(risk)
                db.execute("INSERT INTO demo_intents VALUES(?,?,?,?,?,?,0)", (call, *context, self.grant_hash, self.policy))
                self.audit(db, "INTENT", "HOST_APPROVAL_PENDING_NOT_AUTHORIZED", call)
            except Rejected as exc:
                db.execute("UPDATE calls SET state='DENIED',decision='DENY',reason=? WHERE id=?",
                           (canonical({"reasons": [exc.code], "policy": self.policy, "intent_only": True}), call))
                self.audit(db, "INTENT", "REJECTED", call)
                return {"call": call, "intent": "REJECTED", "code": exc.code}
        return {"call": call, "intent": "RECORDED_NOT_AUTHORIZED"}

    def claim_demo_intent(self, machine, session, tool, args, connection_token, *, rpc_hash=None):
        """One claim immediately before fresh judgment. A claim is never refunded."""
        bounded(args)
        action_hash = digest(canonical({"tool": tool, "args": args, "route": "mcp"}))
        with self.db() as db:
            current = self._current(db, machine, session)
            context = self._demo_intent_context(db, machine, session, current["turn"], connection_token)
            rows = db.execute("SELECT c.*,i.connection_hash,i.request_hash,i.source_hash,i.grant_hash,i.policy,i.claimed FROM calls c JOIN demo_intents i ON i.call=c.id WHERE c.session=? AND c.turn=? AND c.hash=? AND c.path='mcp' AND c.state='PENDING' AND i.claimed=0",
                              (session, current["turn"], action_hash)).fetchall()
            if len(rows) != 1:
                raise Rejected("NO_UNIQUE_HOOK_BINDING")
            row = rows[0]
            if (row["connection_hash"], row["request_hash"], row["source_hash"]) != context or row["grant_hash"] != self.grant_hash or row["policy"] != self.policy:
                raise Rejected("FORWARD_SNAPSHOT_STALE")
            if digest(canonical(self.open(row["body"]))) != action_hash:
                raise Rejected("FORWARD_SNAPSHOT_STALE")
            if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (session, row["id"])).fetchone():
                raise Rejected("PRIOR_RESULT_UNOBSERVED")
            changed = db.execute("UPDATE demo_intents SET claimed=1 WHERE call=? AND claimed=0", (row["id"],))
            if changed.rowcount != 1:
                raise Rejected("FORWARD_REPLAY")
            if rpc_hash is not None:
                if not isinstance(rpc_hash, str) or len(rpc_hash) != 64 or any(c not in "0123456789abcdef" for c in rpc_hash):
                    raise Rejected("INVALID_RPC")
                db.execute("INSERT INTO demo_rpc_bindings VALUES(?,?)", (row["id"], rpc_hash))
            self.audit(db, "INTENT", "POST_HOST_DISPATCH_CLAIMED", row["id"])
            return row["id"]

    def forward(self, machine, call, *, connection_token=None):
        with self.db() as db:
            return self._forward_in_db(db, machine, call, connection_token=connection_token)

    def _forward_in_db(self, db, machine, call, *, connection_token=None):
        row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
        if not row or row["state"] != "READY" or row["path"] != "mcp":
            raise Rejected("FORWARD_REPLAY")
        self._current(db, machine, row["session"], row["turn"])
        if connection_token is not None:
            connection_hash = digest(connection_token)
            self.expires(db, "connection", connection_hash)
            connection = db.execute("SELECT machine,session FROM connections WHERE hash=?", (connection_hash,)).fetchone()
            if not connection or connection["machine"] != machine or connection["session"] != row["session"]:
                raise Rejected("CONNECTION_BINDING")
        if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (row["session"], call)).fetchone():
            raise Rejected("PRIOR_RESULT_UNOBSERVED")
        current = [self.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
        context = json.loads(row["reason"])
        actual_grant = digest(canonical({"grant": self.grant, "policy": self.policy} if self.policy_router else self.grant))
        if context.get("grant_hash") != actual_grant or actual_grant != self.grant_hash or context.get("policy") != self.policy or context["source_hash"] != digest(canonical(current)):
            raise Rejected("FORWARD_SNAPSHOT_STALE")
        approval = context.get("demo_approval")
        if approval:
            proof = db.execute("SELECT d.binding,d.approved_at,d.resumed,a.consumed FROM demo_confirmations d JOIN approvals a ON a.call=d.call WHERE d.call=?", (call,)).fetchone()
            if (row["decision"] != "CONFIRM" or not proof or not proof["resumed"] or not proof["consumed"]
                    or approval != {"binding": proof["binding"], "approved_at": proof["approved_at"], "original_decision": "CONFIRM"}
                    or not 0 <= time.time()-proof["approved_at"] <= 30):
                raise Rejected("APPROVAL_SNAPSHOT_STALE")
        elif time.time() - context["analyzed_at"] > 30:
            self._revalidate_public_read(db, row, context, current)
        if db.execute("UPDATE calls SET state='EXECUTING',reason=? WHERE id=? AND state='READY'", (canonical(context), call)).rowcount != 1:
            raise Rejected("FORWARD_REPLAY")
        self.audit(db, "FORWARD", "RESERVED", call)
        return {"decision": "ALLOW", "state": "EXECUTING"}

    def _revalidate_public_read(self, db, row, context, sources):
        """No lease extension or analysis timestamp rewrite. Only new code-rule reads.

        Runs inside the same BEGIN IMMEDIATE transaction as the final reservation.
        This is not a refresh for legacy READY rows, semantic ALLOW or approvals.
        The upstream still owns the actual NOFOLLOW/open/content checks.
        """
        from app.transparent.jev_policy import JevPolicy, provenance
        from app.transparent.tool_schema import parse

        trace = context.get("policy_trace") or {}
        if (not isinstance(self.policy_router, JevPolicy)
                or self.policy_router.policy != self.policy
                or context.get("forward_revalidation") != "public-read-1"
                or row["decision"] != "ALLOW" or context.get("reasons") != ["PUBLIC_ENROLLED_READ"]
                or trace.get("routing") != "RULE_ALLOW" or trace.get("model_requests") != 0
                or context.get("diagnostic") or context.get("evidence_contract") != self.policy_router.contract
                or context.get("prompt_version") != self.policy_router.prompt_version
                or context.get("view_checks") != {v: {"status": "NOT_RUN_RULE"} for v in ("A", "B")}):
            raise Rejected("FORWARD_SNAPSHOT_STALE")
        candidate = self.open(row["body"])
        text = canonical(candidate)
        conversation = [self.open(x[0])["prompt"] for x in db.execute("SELECT body FROM turns WHERE session=? ORDER BY rowid", (row["session"],))]
        request = canonical({"actual_user_turns_chronological": conversation, "latest_turn": len(conversation) - 1})
        if (digest(text) != row["hash"] or row["hash"] != context.get("action_hash") or digest(request) != context.get("request_hash")
                or len(request.encode()) > 16384 or not self.safe_input(text)
                or any(x.casefold() in text.casefold() for x in self.grant.get("protected_markers", []))
                or candidate.get("route") != "mcp" or candidate.get("tool") != "read_file"
                or candidate["tool"] not in self.grant["tools"].get("mcp", [])
                or not self.complete_sources(sources)
                or db.execute("SELECT 1 FROM analysis_stops WHERE session_hash=? AND turn_hash=?", (digest(row["session"]), digest(row["turn"]))).fetchone()):
            raise Rejected("FORWARD_SNAPSHOT_STALE")
        try:
            parsed = parse(candidate, self.grant["workspace"])
            if parsed["action"] != "READ" or parsed["parser"] != "enrolled-files-1":
                raise ValueError()
            # Re-run complete exact source/catalog validity, not just source IDs.
            snapshot = {"analysis_id": "public-read-recheck", "user_request": request,
                        "server_grant": {**self.grant, "comment_mode": "DEVELOPMENT", "policy": self.policy},
                        "candidate": candidate, "sources": sources}
            provenance(snapshot, parsed)
        except (ValueError, TypeError, KeyError, AnalysisFailure):
            raise Rejected("FORWARD_SNAPSHOT_STALE") from None
        context["forward_check"] = {"checked_at": time.time(), "basis": "PUBLIC_ENROLLED_READ",
                                    "policy": self.policy, "grant_hash": self.grant_hash,
                                    "source_hash": context["source_hash"], "request_hash": context["request_hash"],
                                    "action_hash": row["hash"], "original_snapshot_sha256": context["snapshot_sha256"],
                                    "model_requests": 0}
        self.audit(db, "REVALIDATE", "PUBLIC_READ_CURRENT", row["id"])

    async def authorize(self, machine, call, *, demo_connection=None):
        with self.db() as db:
            row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
            if not row:
                raise Rejected("UNKNOWN_CALL")
            self._current(db, machine, row["session"], row["turn"])
            if row["state"] != "PENDING":
                raise Rejected("CALL_REPLAY")
            stopped = db.execute("SELECT details FROM analysis_stops WHERE session_hash=? AND turn_hash=?",
                                 (digest(row["session"]), digest(row["turn"]))).fetchone()
            if stopped:
                diagnostic = [detail("TURN_ANALYSIS_STOPPED")]
                reasons = ["TURN_ANALYSIS_STOPPED"]
                db.execute("UPDATE calls SET state='DENIED',decision='DENY',reason=? WHERE id=?",
                           (canonical({"reasons": reasons, "diagnostic": diagnostic, "analysis_stop": json.loads(stopped[0]), "spec": SPEC, "policy": self.policy}), call))
                self.audit(db, "DECISION", "TURN_ANALYSIS_STOPPED", call)
                return {"call": call, "decision": "DENY", "state": "DENIED", "reasons": reasons, "diagnostic": diagnostic}
            candidate = self.open(row["body"])
            gap = db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING') LIMIT 1", (row["session"], call)).fetchone()
            conversation = [self.open(x[0])["prompt"] for x in db.execute("SELECT body FROM turns WHERE session=? ORDER BY rowid", (row["session"],))]
            request = canonical({"actual_user_turns_chronological": conversation, "latest_turn": len(conversation) - 1})
            sources = [self.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
            source_hash = digest(canonical(sources))
            observation_context = None
            if getattr(self.policy_router, "current_candidate_context", False):
                turn_ids = [x[0] for x in db.execute("SELECT id FROM turns WHERE session=? ORDER BY rowid", (row["session"],))]
                events = []
                for source in sources:
                    source_call = db.execute("SELECT turn,path,body FROM calls WHERE id=? AND session=?", (source["call_id"],row["session"])).fetchone()
                    if not source_call or source_call["turn"] not in turn_ids:
                        raise Rejected("RESULT_BINDING_OR_REPLAY")
                    body = self.open(source_call["body"])
                    events.append({"source_id":source["source_id"],"call_id":source["call_id"],
                                   "turn_index":turn_ids.index(source_call["turn"]),"route":source_call["path"],
                                   "tool":body["tool"],"target":body["args"].get("path"),
                                   "result_role":"WRITE_COMPLETION" if body["tool"]=="write_file" else "READ_RESULT" if body["tool"]=="read_file" else "OTHER_RESULT"})
                observation_context = {"current_turn":turn_ids.index(row["turn"]),"actual_turns":conversation,"source_events":events}
            if demo_connection is not None:
                current = self._demo_intent_context(db, machine, row["session"], row["turn"], demo_connection)
                intent = db.execute("SELECT * FROM demo_intents WHERE call=?", (call,)).fetchone()
                if (not intent or intent["claimed"] != 1
                        or (intent["connection_hash"], intent["request_hash"], intent["source_hash"]) != current
                        or intent["grant_hash"] != self.grant_hash or intent["policy"] != self.policy):
                    raise Rejected("FORWARD_SNAPSHOT_STALE")
            db.execute("UPDATE calls SET state='ANALYZING' WHERE id=?", (call,))
        decision, reasons, diagnostic = "DENY", ["ANALYSIS_UNAVAILABLE"], None
        view_checks = {view: {"status": "NOT_RUN"} for view in ("A", "B")}
        snapshot_hash = None
        policy_trace = None
        text = canonical(candidate)
        if len(request.encode()) > 16384:
            reasons = ["USER_CONTEXT_LIMIT"]
        elif gap:
            reasons = ["PRIOR_RESULT_UNOBSERVED"]
        elif candidate["tool"] not in self.grant["tools"].get(candidate["route"], []):
            reasons = ["UNSUPPORTED_TOOL"]
        elif not self.safe_input(text):
            reasons = ["SENSITIVE_CANDIDATE"]
        elif any(x.casefold() in text.casefold() for x in self.grant.get("protected_markers", [])):
            reasons = ["PROTECTED_RESOURCE"]
        elif not self.complete_sources(sources):
            reasons = ["SOURCE_CONTEXT_INCOMPLETE"]
        else:
            snapshot = {"analysis_id": str(uuid4()), "user_request": request,
                        "server_grant": {**self.grant, "comment_mode": "DEVELOPMENT", "policy": self.policy},
                        "candidate": candidate, "sources": sources, "evidence_contract": SPAN_CONTRACT}
            if observation_context is not None:
                snapshot["observation_context"] = observation_context
            snapshot_hash = digest(canonical(snapshot))
            if self.policy_router:
                try:
                    decision, reasons, policy_trace, view_checks = await asyncio.wait_for(self.policy_router.evaluate(json.loads(canonical(snapshot))), 20)
                except (Exception, asyncio.CancelledError) as exc:
                    diagnostic = failure_details(exc, enriched=True)
                    view_checks = getattr(exc, "view_checks", {v: {"status": "INVALID_OR_UNAVAILABLE"} for v in ("A", "B")})
                    policy_trace = getattr(exc, "policy_trace", {"routing": "ANALYSIS_FAILED", "contract": self.policy_router.contract})
            else:
                decision, reasons, diagnostic, view_checks = await self._legacy_analysis(snapshot)
        with self.db() as db:
            self._current(db, machine, row["session"], row["turn"])
            fresh = [self.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
            if diagnostic:
                db.execute("INSERT OR IGNORE INTO analysis_stops VALUES(?,?,?)",
                           (digest(row["session"]), digest(row["turn"]), canonical({"diagnostic": diagnostic, "trigger_call_hash": digest(call)})))
            if digest(canonical(fresh)) != source_hash:
                decision, reasons = "DENY", ["SOURCE_CHANGED"]
            if decision == "ALLOW" and db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (row["session"], call)).fetchone():
                decision, reasons = "DENY", ["PRIOR_RESULT_UNOBSERVED"]
            state = ("READY" if row["path"] == "mcp" else "EXECUTING") if decision == "ALLOW" else "CONFIRM" if decision == "CONFIRM" else "DENIED"
            changed = db.execute("UPDATE calls SET state=?,decision=?,reason=? WHERE id=? AND state='ANALYZING'",
                       (state, decision, canonical({"reasons": reasons, "diagnostic": diagnostic, "view_checks": view_checks, "policy_trace": policy_trace, "snapshot_sha256": snapshot_hash, "evidence_contract": self.policy_router.contract if self.policy_router else SPAN_CONTRACT, "prompt_version": self.policy_router.prompt_version if self.policy_router else SPAN_PROMPT_VERSION, "source_hash": source_hash, "analyzed_at": time.time(), "grant_hash": self.grant_hash, "request_hash": digest(request), "action_hash": row["hash"], "forward_revalidation": "public-read-1", "spec": SPEC, "policy": self.policy}), call))
            if changed.rowcount != 1:
                raise Rejected("RESERVATION_LOST")
            if demo_connection is not None and decision == "CONFIRM" and db.execute("SELECT 1 FROM demo_rpc_bindings WHERE call=?", (call,)).fetchone():
                from app.transparent.demo_approval import remember_in_db
                remember_in_db(self, db, machine, call, demo_connection)
            self.audit(db, "DECISION", reasons[0], call)
        return {"call": call, "decision": decision, "state": state, "reasons": reasons, "diagnostic": diagnostic}

    async def _legacy_analysis(self, snapshot):
        decision, reasons, diagnostic = "DENY", ["ANALYSIS_UNAVAILABLE"], None
        view_checks = {view: {"status": "NOT_RUN"} for view in ("A", "B")}
        failures = []
        def failed_view(exc, view):
            result = failure_details(exc, enriched=True)[0]
            failures.append(detail(result["code"], view, result))
            view_checks[view] = {"status": "INVALID_OR_UNAVAILABLE", "code": result["code"]}
        for view in ("A", "B"):
            try:
                span_inputs(snapshot, view)
            except AnalysisFailure as exc:
                failed_view(exc, view)
        if not failures:
            try:
                if self.judge is None:
                    raise AnalysisFailure("MISSING_API_KEY")
                # Do not give an adapter a mutable reference to trusted context.
                pair = await asyncio.wait_for(self.judge.analyze(json.loads(canonical(snapshot))), 20)
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise AnalysisFailure("RESULT_PAIR_INVALID", "PAIR")
            except (Exception, asyncio.CancelledError) as exc:
                pair = [exc, exc]
            checked = []
            for view, observation in zip(("A", "B"), pair, strict=True):
                try:
                    if isinstance(observation, BaseException):
                        raise observation
                    checked.append(validated_spans(observation, snapshot, view))
                    view_checks[view] = {"status": "VALID"}
                except (Exception, asyncio.CancelledError) as exc:
                    failed_view(exc, view)
            if not failures:
                decision, reasons = combine(*checked)
        if failures:
            diagnostic = failures
        return decision, reasons, diagnostic, view_checks

    def approval(self, machine, call, approve, approval_binding=None):
        with self.db() as db:
            demo = db.execute("SELECT 1 FROM demo_confirmations WHERE call=?", (call,)).fetchone()
            if not demo and db.execute("SELECT 1 FROM demo_intents WHERE call=?", (call,)).fetchone():
                raise Rejected("DEMO_APPROVAL_LEGACY_UNBOUND")
        if demo:
            from app.transparent.demo_approval import approve as demo_approve
            return demo_approve(self, machine, call, approve, approval_binding)
        with self.db() as db:
            row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
            if not row or row["state"] != "CONFIRM":
                raise Rejected("NOT_CONFIRM")
            self._current(db, machine, row["session"], row["turn"])
            if json.loads(row["reason"]).get("policy") != self.policy:
                raise Rejected("APPROVAL_POLICY_CHANGED")
            if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (row["session"], call)).fetchone():
                raise Rejected("PRIOR_RESULT_UNOBSERVED")
            if not approve:
                db.execute("UPDATE calls SET state='DENIED',decision='DENY' WHERE id=?", (call,))
                return {"state": "DENIED"}
            db.execute("INSERT INTO approvals(call,hash,turn,policy) VALUES(?,?,?,?)", (call, row["hash"], row["turn"], self.policy))
            db.execute("UPDATE calls SET state='APPROVED' WHERE id=?", (call,))
            return {"state": "APPROVED"}

    def consume_approval(self, machine, call, action_hash):
        with self.db() as db:
            if db.execute("SELECT 1 FROM demo_intents WHERE call=?", (call,)).fetchone():
                raise Rejected("DEMO_APPROVAL_GATEWAY_ONLY")
            row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
            if not row:
                raise Rejected("UNKNOWN_CALL")
            self._current(db, machine, row["session"], row["turn"])
            if db.execute("SELECT 1 FROM calls WHERE session=? AND id<>? AND state IN ('READY','EXECUTING','UNKNOWN','ANALYZING')", (row["session"], call)).fetchone():
                raise Rejected("PRIOR_RESULT_UNOBSERVED")
            n = db.execute("UPDATE approvals SET consumed=1 WHERE call=? AND hash=? AND turn=? AND policy=? AND consumed=0 AND EXISTS(SELECT 1 FROM calls WHERE id=? AND state='APPROVED')",
                           (call, action_hash, row["turn"], self.policy, call)).rowcount
            if not n:
                raise Rejected("APPROVAL_BINDING_OR_REPLAY")
            state = "READY" if row["path"] == "mcp" else "EXECUTING"
            context = json.loads(row["reason"])
            current = [self.open(x[0]) for x in db.execute("SELECT body FROM sources WHERE session=? ORDER BY rowid", (row["session"],))]
            if (context["source_hash"] != digest(canonical(current))
                    or time.time() - context["analyzed_at"] > 30
                    or context.get("policy") != self.policy
                    or context.get("grant_hash") != self.grant_hash):
                raise Rejected("APPROVAL_SNAPSHOT_STALE")
            db.execute("UPDATE calls SET state=?,reason=? WHERE id=?", (state, canonical(context), call))
            return {"decision": "ALLOW", "state": state}

    def observe(self, machine, call, tool, args, output, failed=False):
        # Only a trusted PostToolUse adapter can call this endpoint. No caller source_ids.
        self.bound_output(output)
        with self.db() as db:
            row = db.execute("SELECT * FROM calls WHERE id=?", (call,)).fetchone()
            if not row:
                raise Rejected("UNKNOWN_CALL")
            self._current(db, machine, row["session"])
            from app.transparent.file_errors import valid_read_error
            transport = db.execute("SELECT body FROM transport WHERE call=?", (call,)).fetchone()
            typed_error = transport and tool == "read_file" and valid_read_error(self.open(transport[0]))
            if row["state"] == "OBSERVED_ERROR" and typed_error and row["hash"] == digest(canonical({"tool": tool, "args": args, "route": row["path"]})):
                return {"state": "OBSERVED_ERROR", "execution_error": "FILE_NOT_FOUND", "duplicate": True}
            if row["state"] != "EXECUTING" or row["hash"] != digest(canonical({"tool": tool, "args": args, "route": row["path"]})):
                raise Rejected("RESULT_BINDING_OR_REPLAY")
            candidate = self.open(row["body"])
            native_write = row["path"] == "native" and (tool == "apply_patch" or tool == "Bash" and str(candidate["args"].get("command", "")).casefold().startswith("set-content"))
            # A textual native result is not a typed completion acknowledgement.
            native_completion = isinstance(output, dict) and output.get("completed") is True and type(output.get("exit_code")) is int and output["exit_code"] == 0
            if failed or row["path"] == "mcp" and not transport or native_write and not native_completion:
                db.execute("UPDATE calls SET state='UNKNOWN' WHERE id=?", (call,))
                self.audit(db, "POST", "UNKNOWN_NO_RETRY", call)
                return {"state": "UNKNOWN"}
            if row["path"] == "mcp":
                output = self.open(transport[0])
            sid = str(uuid4())
            text = output if isinstance(output, str) else canonical(output)
            source = {"source_id": sid, "call_id": call, "origin": row["path"], "same_issue": False, **self.source_material(text)}
            db.execute("INSERT INTO sources VALUES(?,?,?,?)", (sid, row["session"], call, self.seal(source)))
            # OBSERVED is intentionally weaker than a transactional SUCCEEDED receipt.
            state = "OBSERVED_ERROR" if failed else "OBSERVED"
            db.execute("UPDATE calls SET state=? WHERE id=?", (state, call))
            self.audit(db, "POST", state, call)
        return {"state": state, "source_id": sid, "analysis_complete": source["analysis_complete"]}

    def transport_failure(self, machine, session, tool, args):
        h = digest(canonical({"tool": tool, "args": args, "route": "mcp"}))
        with self.db() as db:
            self._current(db, machine, session)
            rows = db.execute("SELECT id FROM calls WHERE session=? AND hash=? AND state='EXECUTING'", (session, h)).fetchall()
            for row in rows:
                db.execute("UPDATE calls SET state='UNKNOWN' WHERE id=?", (row[0],))
                self.audit(db, "TRANSPORT", "UNKNOWN_NO_RETRY", row[0])

    def transport_observed(self, machine, session, tool, args, result):
        self.bound_output(result)
        h = digest(canonical({"tool": tool, "args": args, "route": "mcp"}))
        with self.db() as db:
            self._current(db, machine, session)
            rows = db.execute("SELECT id FROM calls WHERE session=? AND hash=? AND state='EXECUTING'", (session, h)).fetchall()
            from app.transparent.file_errors import valid_read_error
            typed_error = tool == "read_file" and valid_read_error(result)
            if len(rows) != 1 or not isinstance(result, dict) or result.get("isError") and not typed_error:
                raise Rejected("TRANSPORT_RESULT_BINDING")
            db.execute("INSERT INTO transport VALUES(?,?)", (rows[0][0], self.seal(result)))
            if typed_error:
                row = db.execute("SELECT reason FROM calls WHERE id=?", (rows[0][0],)).fetchone()
                reason = json.loads(row["reason"])
                reason["execution_error"] = {"version": "file-error-1", "code": "FILE_NOT_FOUND", "operation": "READ", "effect": "NO_WRITE"}
                db.execute("UPDATE calls SET state='OBSERVED_ERROR',reason=? WHERE id=? AND state='EXECUTING'", (canonical(reason), rows[0][0]))
                self.audit(db, "TRANSPORT", "FILE_NOT_FOUND_OBSERVED", rows[0][0])
                return {"state": "OBSERVED_ERROR"}

    def history(self):
        with self.db() as db:
            return [{key: row[key] for key in ("id", "session", "turn", "path", "state", "decision", "reason", "created")} for row in db.execute("SELECT * FROM calls ORDER BY created DESC LIMIT 100")]
