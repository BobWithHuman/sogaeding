import json
import os
import sqlite3
import time
from pathlib import Path

from app.common import SafeError, canonical, cipher, digest, uid
from app.storage.retention import DATA_TTL, DISPOSAL_TTL


class DemoExecutor:
    def __init__(self, path, clock=None):
        self.path, self.crypto = str(path), cipher()
        self.clock = clock or time.time
        Path(self.path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA secure_delete=ON")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS invocations (call_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
              tool_name TEXT NOT NULL, started_at REAL NOT NULL, receipt TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS comments (id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
              call_id TEXT NOT NULL, issue_id INTEGER NOT NULL, body_cipher BLOB NOT NULL,
              created_at REAL NOT NULL, UNIQUE(session_id,call_id));
            CREATE TABLE IF NOT EXISTS disposals (call_sha256 TEXT PRIMARY KEY,
              deadline REAL NOT NULL, purged_at REAL NOT NULL, retain_until REAL NOT NULL,
              state TEXT NOT NULL, write_count INTEGER NOT NULL);
            """)
        os.chmod(self.path, 0o600)

    def execute(self, cid, sid, tool, args):
        # Gateway can only reach this after reserve. No user-configurable path or URL.
        with sqlite3.connect(self.path, timeout=1) as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM disposals WHERE call_sha256=?", (digest(cid),)).fetchone():
                raise SafeError("EXECUTION_OUTCOME_UNKNOWN")
            previous = db.execute("SELECT receipt FROM invocations WHERE call_id=?", (cid,)).fetchone()
            if previous:
                raise SafeError("EXECUTION_ALREADY_SUCCEEDED")
            now = self.clock()
            comment_id = None
            if tool == "get_issue":
                fixture = Path(os.getenv("FIXTURE_DIR", "/workspace/fixtures")) / "issues.json"
                result = json.loads(fixture.read_text(encoding="utf-8"))[str(args["issue_id"])]
            elif tool == "read_workspace_file" and args["file_id"] == "PUBLIC_README":
                result = (Path(os.getenv("FIXTURE_DIR", "/workspace/fixtures")) / "PUBLIC_README.txt").read_text(encoding="utf-8")
            elif tool == "post_issue_comment":
                comment_id = uid()
                db.execute("INSERT INTO comments VALUES (?,?,?,?,?,?)", (comment_id, sid, cid,
                    args["issue_id"], self.crypto.encrypt(args["body"].encode()), now))
                result = {"comment_id": comment_id}
            else:
                raise SafeError("SENSITIVE_RESOURCE", 403)
            receipt = {"call_id": cid, "session_id": sid, "tool_name": tool, "executor_invocations": 1,
                       "write_count_for_call": int(comment_id is not None),
                       "effect_digest": digest(canonical(result)), "comment_id": comment_id}
            db.execute("INSERT INTO invocations VALUES (?,?,?,?,?)", (cid, sid, tool, now, canonical(receipt)))
        return result, receipt

    def receipt(self, cid):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT receipt FROM invocations WHERE call_id=? AND started_at+?>?",
                             (cid, DATA_TTL, self.clock())).fetchone()
        return json.loads(row[0]) if row else None

    def sweep(self):
        now = self.clock()
        with sqlite3.connect(self.path, timeout=1) as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT call_id,started_at FROM invocations WHERE started_at+?<=?", (DATA_TTL, now)).fetchall()
            for cid, created in rows:
                writes = db.execute("SELECT count(*) FROM comments WHERE call_id=?", (cid,)).fetchone()[0]
                db.execute("INSERT OR IGNORE INTO disposals VALUES (?,?,?,?,?,?)",
                           (digest(cid), created + DATA_TTL, now, created + DATA_TTL + DISPOSAL_TTL,
                            "EFFECT_RECORDED", writes))
                db.execute("DELETE FROM comments WHERE call_id=?", (cid,))
                db.execute("DELETE FROM invocations WHERE call_id=?", (cid,))
            # Legacy orphan comments are also bounded; do not retain them forever.
            db.execute("DELETE FROM comments WHERE created_at+?<=?", (DATA_TTL, now))
            db.execute("DELETE FROM disposals WHERE retain_until<=?", (now,))
