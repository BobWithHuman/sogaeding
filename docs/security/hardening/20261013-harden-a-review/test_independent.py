"""Narrow reviewer fixtures; product policy/reservation code stays unchanged."""
import importlib.util
import json
import os
import sqlite3
import time
from pathlib import Path

import pytest

from app.common import SafeError, digest, uid
from app.executor.demo import DemoExecutor
from app.storage.repository import Repository
from app.storage.retention import DATA_TTL, DISPOSAL_TTL


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(name, value):
    target = Path(os.environ["EVIDENCE_DIR"])
    target.mkdir(parents=True, exist_ok=True)
    (target / (name + ".json")).write_text(json.dumps(value, indent=2))


def test_creation_deadlines_legacy_migration_and_late_disposal(tmp_path, monkeypatch):
    pki = tmp_path / "pki"
    load("prepare_tls", "/workspace/tools/prepare_tls.py").generate(pki)
    monkeypatch.setenv("RUNTIME_DIR", str(pki))
    # common.RUNTIME is import-time state; use the real cipher with a private key path.
    import app.common
    monkeypatch.setattr(app.common, "RUNTIME", pki)
    clock = [1000000.0]
    repo = Repository(tmp_path / "control.sqlite3", clock=lambda: clock[0])
    session = repo.create_session({"task_kind": "POST_COMMENT", "issue_id": 42,
        "user_request": "review-request-canary", "allowed_comment_body": "review-body-canary"})
    sid = session["session_id"]
    request = {"session_id": sid, "client_request_id": uid(), "tool_name": "post_issue_comment",
               "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "review-body-canary"}}
    checked = repo.check(request)
    repo.reserve(checked["call_id"], {k: request[k] for k in ("tool_name", "backend_id", "args")})
    with repo.tx() as db:
        preserved = db.execute("SELECT request_cipher FROM sessions").fetchone()[0]
        db.execute("DROP TABLE session_retention")
        db.execute("DROP TABLE disposals")
    repo = Repository(repo.path, clock=lambda: clock[0])
    repo = Repository(repo.path, clock=lambda: clock[0])
    with repo.tx() as db:
        assert db.execute("SELECT request_cipher FROM sessions").fetchone()[0] == preserved
        assert db.execute("SELECT created_at FROM session_retention").fetchone()[0] == 1000000.0
    clock[0] += 90
    effects = DemoExecutor(tmp_path / "effects.sqlite3", clock=lambda: clock[0])
    _, receipt = effects.execute(checked["call_id"], sid, request["tool_name"], request["args"])
    clock[0] = 1000000.0 + DATA_TTL - 0.001
    assert repo.timeline(sid)["session_id"] == sid
    clock[0] += 0.001
    with pytest.raises(SafeError, match="SESSION_INACTIVE"):
        repo.timeline(sid)
    assert effects.receipt(checked["call_id"]) == receipt
    repo.sweep()
    effects.sweep()
    with repo.tx() as db:
        row = db.execute("SELECT * FROM disposals").fetchone()
        assert row["unresolved_count"] == 1 and row["write_budget"] == 0
    clock[0] += 90
    assert effects.receipt(checked["call_id"]) is None
    effects.sweep()
    with pytest.raises(SafeError):
        effects.execute(checked["call_id"], sid, request["tool_name"], request["args"])
    # Delayed cleanup never adds seven days from restart time.
    clock[0] += DISPOSAL_TTL + 1
    repo.sweep()
    effects.sweep()
    for path in (repo.path, effects.path):
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT count(*) FROM disposals").fetchone()[0] == 0
        for file in Path(path).parent.glob(Path(path).name + "*"):
            data = file.read_bytes()
            assert b"review-body-canary" not in data and b"review-request-canary" not in data
            assert preserved not in data and session["agent_session_token"].encode() not in data
    record("independent-deadlines", {"control_deadline": 1086400, "gateway_deadline": 1086490,
        "session_ref": sid, "call_id": checked["call_id"], "arguments_digest": checked["args_sha256"],
        "policy_version": checked["policy_version"], "mode": "REPLAY", "expected_decision": "ALLOW",
        "actual_decision": checked["decision"], "tool": request["tool_name"],
        "legacy_creation_preserved": True, "unresolved_count": 1, "write_budget": 0,
        "body_cipher_journal_residual_matches": 0, "result": "PASS"})


@pytest.fixture(scope="session")
def independent_product(tmp_path_factory):
    value = load("review_product", "/workspace/tests/acceptance/conftest.py").Product(
        tmp_path_factory.mktemp("review-product"))
    import app.common
    previous_runtime = app.common.RUNTIME
    app.common.RUNTIME = value.pki
    try:
        yield value
    finally:
        value.stop()
        app.common.RUNTIME = previous_runtime


@pytest.mark.asyncio
async def test_reverse_two_db_failure_startup_and_old_token_denial(independent_product):
    product = independent_product
    session = await product.session("POST_COMMENT")
    result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not result.is_error and product.counts(session["session_id"]) == (1, 1)
    cid = result.structured_content["call_id"]
    product.stop()
    old = time.time() - DATA_TTL - 1
    with sqlite3.connect(product.control_db) as db:
        db.execute("UPDATE session_retention SET created_at=? WHERE session_id=?", (old, session["session_id"]))
        db.execute("CREATE TRIGGER review_control_delete BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'review-purge'); END")
    with sqlite3.connect(product.effects_db) as db:
        db.execute("UPDATE invocations SET started_at=? WHERE call_id=?", (old, cid))
    # Independent DBs: gateway cleanup can commit even when Control cannot.
    DemoExecutor(product.effects_db).sweep()
    with pytest.raises(sqlite3.Error):
        Repository(product.control_db).sweep()
    assert product.counts(session["session_id"]) == (0, 0)
    with sqlite3.connect(product.control_db) as db:
        assert db.execute("SELECT write_budget FROM sessions WHERE id=?", (session["session_id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM disposals").fetchone()[0] == 0
        db.execute("DROP TRIGGER review_control_delete")
    product.start()
    product.stop()
    product.start()
    assert (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).status_code == 404
    assert (await product.request("/internal/auth/resolve", {"agent_token": session["agent_session_token"]}, role="service")).status_code == 401
    assert (await product.request(f"/internal/calls/{cid}/reserve", {"tool_name": "post_issue_comment",
        "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")).status_code == 404
    assert product.counts(session["session_id"]) == (0, 0)
    fresh = await product.session("POST_COMMENT")
    good = await product.tool(fresh, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not good.is_error and product.counts(fresh["session_id"]) == (1, 1)
    record("independent-reverse-db", {"effects_before_purge": 1, "additional_effects": 0,
        "session_ref": session["session_id"], "call_id": cid, "mode": "REPLAY",
        "expected_decision": "ALLOW", "actual_decision": result.structured_content["decision"],
        "tool": "post_issue_comment",
        "failed_control_transaction_rolled_back": True, "startup_repeated": 2,
        "old_timeline": 404, "old_token": 401, "old_reserve": 404, "fresh_effects": 1, "result": "PASS"})


@pytest.mark.asyncio
async def test_receipt_reconciliation_binding_no_reexecution(independent_product):
    product = independent_product
    session = await product.session("POST_COMMENT")
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER review_report BEFORE UPDATE ON executions WHEN NEW.state!='RESERVED' BEGIN SELECT RAISE(ABORT,'review-report'); END")
    try:
        result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert result.is_error and product.counts(session["session_id"]) == (1, 1)
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER review_report")
    cid = result.structured_content["call_id"]
    with sqlite3.connect(product.control_db) as db:
        rid = db.execute("SELECT reservation_id FROM executions WHERE call_id=?", (cid,)).fetchone()[0]
        db.execute("UPDATE executions SET reserved_at=? WHERE call_id=?", (time.time() - 31, cid))
    product.stop()
    product.start()
    with sqlite3.connect(product.effects_db) as db:
        receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (cid,)).fetchone()[0])
    payload = {"reservation_id": rid, "state": "SUCCEEDED", "receipt": receipt, "reconciled": True}
    for altered in ({**payload, "reservation_id": uid()},
                    {**payload, "receipt": {**receipt, "session_id": uid()}},
                    {**payload, "reconciled": False}):
        reply = await product.request(f"/internal/calls/{cid}/report", altered, role="service")
        assert reply.status_code == 409
        assert product.counts(session["session_id"]) == (1, 1)
    for _ in range(2):
        reply = await product.request(f"/internal/calls/{cid}/report", payload, role="service")
        assert reply.status_code == 200 and reply.json()["state"] == "SUCCEEDED"
    replay = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료", "resume_call_id": cid})
    assert not replay.is_error and product.counts(session["session_id"]) == (1, 1)
    record("independent-receipt-binding", {"mismatched_reservation": 409, "mismatched_session": 409,
        "session_ref": session["session_id"], "call_id": cid, "reservation_id": rid,
        "mode": "REPLAY", "expected_decision": "ALLOW", "actual_decision": result.structured_content["decision"],
        "tool": "post_issue_comment", "actual_state_before_reconcile": "UNKNOWN",
        "missing_reconciled_flag": 409, "actual_receipt_reports": 2, "effects": 1,
        "additional_effects": 0, "result": "PASS"})
