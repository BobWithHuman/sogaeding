import asyncio
import sqlite3
import time

import pytest


@pytest.mark.asyncio
async def test_nt01_at01_at02_real_mcp(product):
    session = await product.session()
    read = await product.tool(session, "get_issue", {"issue_id": 42})
    assert not read.is_error and read.structured_content["execution_state"] == "SUCCEEDED"
    assert "DEMO_SECRET_DO_NOT_SEND" not in str(read)
    secret = await product.tool(session, "read_workspace_file", {"file_id": "SECRET_ENV"})
    assert secret.is_error and secret.structured_content["reason_codes"] == ["SENSITIVE_RESOURCE"]
    post = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert post.structured_content["decision"] == "DENY"
    assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    assert product.counts(session["session_id"], "read_workspace_file") == (0, 0)
    product.record("NT-01", session, read, "get_issue")
    product.record("AT-01", session, post, "post_issue_comment")
    product.record("AT-02", session, secret, "read_workspace_file")


@pytest.mark.asyncio
async def test_nt02_actual_one_effect_and_replay(product):
    session = await product.session("POST_COMMENT")
    result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not result.is_error and result.structured_content["execution_state"] == "SUCCEEDED"
    again = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료",
                                        "resume_call_id": result.structured_content["call_id"]})
    assert not again.is_error
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    from cryptography.fernet import Fernet
    with sqlite3.connect(product.effects_db) as db:
        stored = db.execute("SELECT issue_id,body_cipher,call_id FROM comments WHERE session_id=?", (session["session_id"],)).fetchone()
    assert stored[0] == 42 and stored[2] == result.structured_content["call_id"]
    assert Fernet((product.pki / "storage.key").read_bytes()).decrypt(stored[1]).decode() == "검토 완료"
    product.record("NT-02", session, result, "post_issue_comment")


@pytest.mark.asyncio
async def test_at14_different_call_write_race(product):
    session = await product.session("POST_COMMENT")
    results = await asyncio.gather(*(product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"}) for _ in range(2)))
    assert sum(not x.is_error for x in results) == 1
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    product.record("AT-14", session, next(x for x in results if not x.is_error), "post_issue_comment")


@pytest.mark.asyncio
async def test_at09_storage_failure_before_execution(product):
    session = await product.session("POST_COMMENT")
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER fail_check BEFORE INSERT ON calls BEGIN SELECT RAISE(ABORT,'fixture'); END")
    try:
        result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert result.is_error
        assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER fail_check")
    product.record("AT-09-storage-before", session, result, "post_issue_comment")


@pytest.mark.asyncio
async def test_at12_report_loss_unknown_no_repeat(product):
    session = await product.session("POST_COMMENT")
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER fail_report BEFORE UPDATE ON executions WHEN NEW.state != 'RESERVED' BEGIN SELECT RAISE(ABORT,'fixture'); END")
    try:
        result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert result.is_error and result.structured_content["execution_state"] == "UNKNOWN"
        assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
        repeat = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료",
                                         "resume_call_id": result.structured_content["call_id"]})
        assert repeat.is_error
        assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER fail_report")
    with sqlite3.connect(product.control_db) as db:
        db.row_factory = sqlite3.Row
        execution = db.execute("SELECT * FROM executions WHERE call_id=?", (result.structured_content["call_id"],)).fetchone()
        db.execute("UPDATE executions SET reserved_at=? WHERE call_id=?", (time.time() - 31, execution["call_id"]))
    product.stop()
    product.start()
    with sqlite3.connect(product.control_db) as db:
        assert db.execute("SELECT state FROM executions WHERE call_id=?", (execution["call_id"],)).fetchone()[0] == "UNKNOWN"
        assert db.execute("SELECT write_budget FROM sessions WHERE id=?", (session["session_id"],)).fetchone()[0] == 0
    other = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert other.is_error and product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    # Explicitly reconcile the actual effects receipt via the real mTLS report API.
    with sqlite3.connect(product.effects_db) as db:
        import json
        receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (execution["call_id"],)).fetchone()[0])
    reconciled = await product.request(f"/internal/calls/{execution['call_id']}/report", {
        "reservation_id": execution["reservation_id"], "state": "SUCCEEDED", "receipt": receipt,
        "reconciled": True}, role="service")
    assert reconciled.status_code == 200 and reconciled.json()["state"] == "SUCCEEDED"
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    product.record("AT-12", session, result, "post_issue_comment")
