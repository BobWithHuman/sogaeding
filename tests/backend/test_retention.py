import sqlite3

import pytest

from app.common import SafeError, digest
from app.executor.demo import DemoExecutor
from app.storage.repository import Repository
from app.storage.retention import DATA_TTL, DISPOSAL_TTL


@pytest.mark.parametrize("state", ["RESERVED", "UNKNOWN"])
def test_retention_boundary_migration_atomic_purge_and_bounded_disposal(repo, state):
    now = [1000000.0]
    repo.clock = lambda: now[0]
    session = repo.create_session({"task_kind": "POST_COMMENT", "issue_id": 42,
                                  "user_request": "private-request-canary", "allowed_comment_body": "private-body-canary"})
    sid = session["session_id"]
    request = {"session_id": sid, "client_request_id": "a", "tool_name": "post_issue_comment",
               "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "private-body-canary"}}
    check = repo.check(request)
    repo.reserve(check["call_id"], {k: request[k] for k in ("tool_name", "backend_id", "args")})
    if state == "UNKNOWN":
        with repo.tx() as db:
            db.execute("UPDATE executions SET state='UNKNOWN' WHERE call_id=?", (check["call_id"],))
    effects = DemoExecutor(repo.path + ".effects", clock=lambda: now[0])
    _, receipt = effects.execute(check["call_id"], sid, request["tool_name"], request["args"])
    with repo.tx() as db:
        encrypted = [db.execute("SELECT request_cipher FROM sessions").fetchone()[0],
                     db.execute("SELECT comment_cipher FROM sessions").fetchone()[0]]
        # Recreate the pre-migration shape, retaining all existing session data.
        db.execute("DROP TABLE session_retention")
        db.execute("DROP TABLE disposals")
    repo = Repository(repo.path, clock=lambda: now[0])
    repo = Repository(repo.path, clock=lambda: now[0])
    now[0] += DATA_TTL - 0.001
    assert repo.timeline(sid)["session_id"] == sid
    assert effects.receipt(check["call_id"]) == receipt
    repo.sweep()
    now[0] += 0.001
    with pytest.raises(SafeError, match="SESSION_INACTIVE"):
        repo.timeline(sid)
    assert effects.receipt(check["call_id"]) is None
    with repo.tx() as db:
        db.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'purge-fixture'); END")
    with pytest.raises(sqlite3.Error):
        repo.sweep()
    with repo.tx() as db:
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM executions").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM disposals").fetchone()[0] == 0
        db.execute("DROP TRIGGER fail_delete")
    repo.sweep()
    effects.sweep()
    repo.sweep()
    effects.sweep()
    with repo.tx() as db:
        row = db.execute("SELECT * FROM disposals").fetchone()
        assert row["session_sha256"] == digest(sid)
        assert row["unresolved_count"] == 1 and row["write_budget"] == 0
        for table in ("sessions", "sources", "events", "calls", "approvals", "decisions", "executions", "session_tokens", "session_retention"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    with pytest.raises(SafeError):
        effects.execute(check["call_id"], sid, request["tool_name"], request["args"])
    with pytest.raises(SafeError):
        repo.resolve(session["agent_session_token"])
    for path in __import__("pathlib").Path(repo.path).parent.glob("*.sqlite3*"):
        data = path.read_bytes()
        assert not any(value in data for value in encrypted)
        assert b"private-body-canary" not in data and b"private-request-canary" not in data
        assert session["agent_session_token"].encode() not in data
    now[0] += DISPOSAL_TTL
    repo.sweep()
    effects.sweep()
    with repo.tx() as db:
        assert db.execute("SELECT count(*) FROM disposals").fetchone()[0] == 0
    with sqlite3.connect(effects.path) as db:
        assert db.execute("SELECT count(*) FROM disposals").fetchone()[0] == 0
