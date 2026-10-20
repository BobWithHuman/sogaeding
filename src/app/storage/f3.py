"""Short transaction snapshots; no model work while a DB transaction is open."""

import asyncio
import json
import os

from app.common import POLICY, SafeError, action, canonical, digest, mask, uid
from app.pdp.diagnostics import AnalysisFailure, detail, failure_details
from app.pdp.policy import decide
from app.pdp.semantic import PROMPT_VERSION, SCHEMA_VERSION, combine, validated

F3_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_modes (session_id TEXT PRIMARY KEY REFERENCES sessions(id), comment_mode TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_analysis (source_id TEXT PRIMARY KEY REFERENCES sources(id), text_cipher BLOB NOT NULL, text_sha256 TEXT NOT NULL, complete INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, call_id TEXT UNIQUE NOT NULL REFERENCES calls(id), snapshot_cipher BLOB NOT NULL, snapshot_sha256 TEXT NOT NULL, revision_sha256 TEXT NOT NULL, status TEXT NOT NULL, lease_until REAL NOT NULL, result_cipher BLOB);
CREATE TABLE IF NOT EXISTS call_metadata (call_id TEXT PRIMARY KEY REFERENCES calls(id), analysis_id TEXT, stage TEXT NOT NULL, snapshot_sha256 TEXT, refs_cipher BLOB NOT NULL);
"""


class F3Repository:
    def expire_analyses(self, db):
        for row in db.execute(
            "SELECT * FROM analyses WHERE status='PENDING' AND lease_until<=?", (self.clock(),)
        ).fetchall():
            saved = {
                "decision": "DENY",
                "reason_codes": ["ANALYSIS_UNAVAILABLE"],
                "evidence_refs": [],
                "diagnostics": [detail("LEASE_EXPIRED")],
            }
            db.execute(
                "UPDATE analyses SET status='COMPLETE',result_cipher=? WHERE id=?",
                (self.encrypt(canonical(saved)), row["id"]),
            )
            db.execute(
                "UPDATE decisions SET decision='DENY',reason_codes=? WHERE call_id=?",
                (canonical(saved["reason_codes"]), row["call_id"]),
            )

    def mode(self, db, sid):
        row = db.execute(
            "SELECT comment_mode FROM session_modes WHERE session_id=?", (sid,)
        ).fetchone()
        return row[0] if row else "EXACT"

    def revision(self, db, sid):
        rows = db.execute(
            "SELECT s.id,s.content_sha256,s.collected_at,a.text_sha256,a.complete,e.state FROM sources s LEFT JOIN source_analysis a ON a.source_id=s.id LEFT JOIN executions e ON e.call_id=s.call_id WHERE s.session_id=? ORDER BY s.id",
            (sid,),
        ).fetchall()
        return digest(canonical([dict(row) for row in rows]))

    def context(self, db, session, value):
        rows = db.execute(
            "SELECT s.*,a.text_cipher,a.text_sha256,a.complete FROM sources s JOIN executions e ON e.call_id=s.call_id LEFT JOIN source_analysis a ON a.source_id=s.id WHERE s.session_id=? AND e.state='SUCCEEDED' AND s.kind!='USER_REQUEST' ORDER BY s.collected_at,s.id",
            (session["id"],),
        ).fetchall()
        sources = []
        for row in rows:
            # Same-issue read is established from immutable call args, not origin labels.
            call = self.call(db, row["call_id"])
            args = json.loads(self.decrypt(call["canonical_cipher"]))["args"]
            same_issue = (
                call["tool_name"] == "get_issue" and args.get("issue_id") == session["issue_id"]
            )
            text = self.decrypt(row["text_cipher"]) if row["text_cipher"] else ""
            sources.append(
                {
                    "source_id": row["id"],
                    "kind": row["kind"],
                    "call_id": row["call_id"],
                    "same_issue": same_issue,
                    "collected_at": row["collected_at"],
                    "content_sha256": row["content_sha256"],
                    "analysis_text": text,
                    "analysis_text_sha256": row["text_sha256"],
                    "analysis_complete": bool(row["complete"])
                    and row["text_sha256"] == digest(text),
                }
            )
        matching = [row for row in sources if row["same_issue"]]
        mode = self.mode(db, session["id"])
        if mode == "EXACT":
            # Legacy explicit title-report candidate: a known public data field,
            # still different from the exact grant, hence human ambiguity only.
            # No automatic allowance and no inference from document instructions.
            body = value["args"].get("body", "")
            if any(
                body == "제목: " + title
                for row in rows
                for title in json.loads(self.decrypt(row["match_values"]))
                if title and mask(title) == title
            ):
                return None, None
        if mode == "ISSUE_SUMMARY" and not matching:
            return None, "SOURCE_CONTEXT_MISSING"
        if (
            len(sources) > 8
            or sum(len(x["analysis_text"]) for x in sources) > 16384
            or sum(len(x["analysis_text"].encode()) for x in sources) > 32768
            or any(not x["analysis_complete"] or not x["analysis_text"].strip() for x in sources)
        ):
            return None, "SOURCE_CONTEXT_INCOMPLETE"
        if not sources:  # Existing EXACT benign mismatch is the explicit exception path.
            return None, None
        request = self.decrypt(session["request_cipher"])
        if mask(request) != request or mask(canonical(value["args"])) != canonical(value["args"]):
            return None, "SOURCE_CONTEXT_INCOMPLETE"
        grant = {
            "task_kind": session["task_kind"],
            "issue_id": session["issue_id"],
            "comment_mode": mode,
            "write_limit": 1,
            "policy_version": session["policy_version"],
        }
        if mode == "EXACT":
            body = self.decrypt(session["comment_cipher"])
            if mask(body) != body:
                return None, "SOURCE_CONTEXT_INCOMPLETE"
            grant["allowed_comment_body"] = body
        return {
            "user_request": request,
            "server_grant": grant,
            "candidate": {
                "tool_name": value["tool_name"],
                "args": json.loads(canonical(value["args"])),
            },
            "sources": sources,
        }, None

    def begin_analysis(self, db, session, value, cid, sha, model):
        snapshot, error = self.context(db, session, value)
        if error:
            return None, "DENY", [error], "SOURCE", None
        if snapshot is None:
            reasons = ["CONTENT_REVIEW_REQUIRED"]
            if db.execute(
                "SELECT 1 FROM sources WHERE session_id=? AND kind!='USER_REQUEST'",
                (session["id"],),
            ).fetchone():
                reasons.append("SOURCE_VALUE_OBSERVED")
            return None, "CONFIRM", reasons, "SOURCE", None
        if (
            db.execute(
                "SELECT count(*) FROM analyses a JOIN calls c ON c.id=a.call_id WHERE c.session_id=?",
                (session["id"],),
            ).fetchone()[0]
            >= 2
        ):
            return None, "DENY", ["ANALYSIS_UNAVAILABLE"], "SEMANTIC", None
        aid = uid()
        revision = self.revision(db, session["id"])
        snapshot.update(
            {
                "analysis_id": aid,
                "call_id": cid,
                "session_id": session["id"],
                "backend_id": value["backend_id"],
                "args_sha256": sha,
                "policy_version": POLICY,
                "user_request_sha256": digest(snapshot["user_request"]),
                "grant_sha256": digest(canonical(snapshot["server_grant"])),
                "revision_sha256": revision,
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
            }
        )
        snapshot_sha = digest(canonical(snapshot))
        db.execute(
            "INSERT INTO analyses VALUES (?,?,?,?,?,?,?,NULL)",
            (
                aid,
                cid,
                self.encrypt(canonical(snapshot)),
                snapshot_sha,
                revision,
                "PENDING",
                self.clock() + 20,
            ),
        )
        return snapshot, "DENY", ["ANALYSIS_IN_PROGRESS"], "SEMANTIC", snapshot_sha

    def bound(self, db, analysis, call, session):
        snapshot = json.loads(self.decrypt(analysis["snapshot_cipher"]))
        valid = (
            digest(canonical(snapshot)) == analysis["snapshot_sha256"]
            and snapshot["analysis_id"] == analysis["id"]
            and snapshot["call_id"] == call["id"]
            and snapshot["session_id"] == session["id"]
            and snapshot["backend_id"] == call["backend_id"]
            and snapshot["args_sha256"] == call["args_sha256"]
            and snapshot["prompt_version"] == PROMPT_VERSION
            and snapshot["schema_version"] == SCHEMA_VERSION
            and snapshot["model"]
            == getattr(self, "analysis_model", os.getenv("WITH_HUMAN_JUDGE_MODEL", "gpt-5.6-luna"))
            and snapshot["policy_version"] == POLICY
            and snapshot["candidate"]["tool_name"] == call["tool_name"]
            and digest(
                action(
                    snapshot["candidate"]["tool_name"],
                    snapshot["candidate"]["args"],
                    snapshot["backend_id"],
                )
            )
            == call["args_sha256"]
            and digest(self.decrypt(session["request_cipher"])) == snapshot["user_request_sha256"]
            and self.revision(db, session["id"]) == analysis["revision_sha256"]
            and self.mode(db, session["id"]) == snapshot["server_grant"]["comment_mode"]
            and digest(canonical(snapshot["server_grant"])) == snapshot["grant_sha256"]
        )
        if snapshot["server_grant"]["comment_mode"] == "EXACT":
            valid = (
                valid
                and self.decrypt(session["comment_cipher"])
                == snapshot["server_grant"]["allowed_comment_body"]
            )
        if (
            session["task_kind"] != snapshot["server_grant"]["task_kind"]
            or session["issue_id"] != snapshot["server_grant"]["issue_id"]
        ):
            valid = False
        return valid

    def finish_analysis(self, snapshot, results=None, error=None):
        with self.tx() as db:
            analysis = db.execute(
                "SELECT * FROM analyses WHERE id=?", (snapshot["analysis_id"],)
            ).fetchone()
            call = self.call(db, snapshot["call_id"])
            session = self.session(db, call["session_id"], active=False)
            if analysis["status"] != "PENDING":
                return self.check_reply(db, call["id"])
            refs, reasons, decision = [], ["ANALYSIS_UNAVAILABLE"], "DENY"
            diagnostics = []
            if (
                session["status"] != "ACTIVE"
                or session["expires_at"] <= self.clock()
                or session["policy_version"] != POLICY
                or call["policy_version"] != POLICY
                or digest(canonical(snapshot)) != analysis["snapshot_sha256"]
                or not self.bound(db, analysis, call, session)
            ):
                reasons = ["ANALYSIS_STALE"]
                diagnostics = [detail("SNAPSHOT_STALE")]
            elif analysis["lease_until"] <= self.clock():
                reasons = ["ANALYSIS_UNAVAILABLE"]
                diagnostics = [detail("LEASE_EXPIRED")]
            elif error:
                diagnostics = failure_details(error)
            elif results is not None:
                try:
                    a, b = [
                        validated(result, snapshot, view)
                        for result, view in zip(results, ("A", "B"), strict=True)
                    ]
                    decision, reasons = combine(a, b)
                    if decision == "ALLOW" and snapshot["server_grant"]["comment_mode"] == "EXACT":
                        decision, reasons = "CONFIRM", ["SEMANTIC_UNCERTAIN"]
                    refs = [
                        {"view": view, **ref}
                        for view, result in (("A", a), ("B", b))
                        for ref in result["evidence_refs"]
                    ]
                except AnalysisFailure as exc:
                    diagnostics = failure_details(exc)
                except (SafeError, ValueError, TypeError):
                    diagnostics = [detail("RESULT_PAIR_INVALID", "PAIR")]
            else:
                diagnostics = [detail("RESULT_PAIR_INVALID", "PAIR")]
            db.execute(
                "UPDATE analyses SET status=?,result_cipher=? WHERE id=?",
                (
                    "COMPLETE",
                    self.encrypt(
                        canonical(
                            {"decision": decision, "reason_codes": reasons, "evidence_refs": refs,
                             "diagnostics": diagnostics}
                        )
                    ),
                    analysis["id"],
                ),
            )
            db.execute(
                "UPDATE decisions SET decision=?,reason_codes=? WHERE call_id=?",
                (decision, canonical(reasons), call["id"]),
            )
            db.execute(
                "UPDATE call_metadata SET refs_cipher=? WHERE call_id=?",
                (self.encrypt(canonical(refs)), call["id"]),
            )
            if decision == "CONFIRM":
                db.execute(
                    "INSERT INTO approvals VALUES (?,?,?,?,?,?,NULL,NULL)",
                    (uid(), call["id"], call["args_sha256"], POLICY, "PENDING", self.clock() + 300),
                )
            self.event(
                db,
                call["session_id"],
                "ANALYZED",
                {
                    "analysis_id": analysis["id"],
                    "decision": decision,
                    "reason_codes": reasons,
                    "evidence_snapshot_sha256": analysis["snapshot_sha256"],
                },
                call["id"],
            )
            return self.check_reply(db, call["id"])

    def check(self, value):
        reply, snapshot = self.prepare_check(value, "unavailable")
        return self.finish_analysis(snapshot, error=AnalysisFailure("JUDGE_NOT_CONFIGURED")) if snapshot else reply

    async def check_async(self, value, judge):
        reply, snapshot = self.prepare_check(value, judge.model)
        if not snapshot:
            return reply
        try:
            results = await asyncio.wait_for(judge.analyze(snapshot), 20)
        except asyncio.CancelledError:
            self.finish_analysis(snapshot, error=AnalysisFailure("ANALYSIS_CANCELLED"))
            raise
        except Exception as exc:
            return self.finish_analysis(snapshot, error=exc)
        return self.finish_analysis(snapshot, results)

    def analysis_diagnostics(self, sid):
        with self.tx() as db:
            session = self.session(db, sid, active=False)
            rows = []
            for row in db.execute("SELECT a.* FROM analyses a JOIN calls c ON c.id=a.call_id WHERE c.session_id=? ORDER BY c.created_at", (sid,)):
                saved = json.loads(self.decrypt(row["result_cipher"])) if row["result_cipher"] else {}
                diagnostics = saved.get("diagnostics")
                if diagnostics is None:
                    diagnostics = [detail("DETAIL_NOT_RECORDED")] if saved.get("reason_codes") == ["ANALYSIS_UNAVAILABLE"] else []
                rows.append({"analysis_id": row["id"], "call_id": row["call_id"],
                             "status": row["status"], "diagnostics": diagnostics})
            return {"session_id": sid, "task_kind": session["task_kind"], "issue_id": session["issue_id"],
                    "comment_mode": self.mode(db, sid), "policy_version": session["policy_version"],
                    "request_sha256": digest(self.decrypt(session["request_cipher"])), "analyses": rows}

    def cli_binding(self, sid, token):
        resolved = self.resolve(token)
        if resolved["session_id"] != sid:
            raise SafeError("ACTION_BINDING_MISMATCH", 403)
        return self.analysis_diagnostics(sid)

    def metadata(self, db, cid):
        row = db.execute("SELECT * FROM call_metadata WHERE call_id=?", (cid,)).fetchone()
        return {
            "analysis_id": row["analysis_id"] if row else None,
            "decision_stage": row["stage"] if row else "POLICY",
            "evidence_snapshot_sha256": row["snapshot_sha256"] if row else None,
            "evidence_refs": json.loads(self.decrypt(row["refs_cipher"])) if row else [],
        }

    def guard_analysis(self, db, call, session):
        metadata = db.execute(
            "SELECT * FROM call_metadata WHERE call_id=?", (call["id"],)
        ).fetchone()
        if metadata and metadata["analysis_id"]:
            analysis = db.execute(
                "SELECT * FROM analyses WHERE id=?", (metadata["analysis_id"],)
            ).fetchone()
            if (
                not analysis
                or analysis["status"] != "COMPLETE"
                or metadata["snapshot_sha256"] != analysis["snapshot_sha256"]
                or not self.bound(db, analysis, call, session)
            ):
                raise SafeError("ANALYSIS_STALE")
            saved = json.loads(self.decrypt(analysis["result_cipher"]))
            reply = self.check_reply(db, call["id"])
            if (
                saved["decision"] != reply["decision"]
                or saved["reason_codes"] != reply["reason_codes"]
                or saved["evidence_refs"] != reply["evidence_refs"]
            ):
                raise SafeError("ACTION_BINDING_MISMATCH")
        decision, reasons = decide(
            session,
            call["tool_name"],
            json.loads(self.decrypt(call["canonical_cipher"]))["args"],
            self.decrypt(session["comment_cipher"]),
        )
        if decision == "DENY":
            raise SafeError(reasons[0], 403)

    def require_analysis_binding(self, db, call, session):
        row = db.execute("SELECT * FROM analyses WHERE call_id=?", (call["id"],)).fetchone()
        if row and not self.bound(db, row, call, session):
            raise SafeError("ANALYSIS_STALE")
