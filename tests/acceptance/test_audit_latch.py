import sqlite3

import pytest

from app.common import uid


@pytest.mark.asyncio
async def test_required_source_failure_stops_followup_writes_and_reads(product):
    session = await product.session("POST_COMMENT")
    prechecked = await product.request("/internal/checks", {"session_id": session["session_id"],
        "client_request_id": uid(), "tool_name": "post_issue_comment", "backend_id": "demo.v1",
        "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")
    assert prechecked.status_code == 200 and prechecked.json()["decision"] == "ALLOW"
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER fail_source BEFORE INSERT ON sources WHEN NEW.call_id IS NOT NULL BEGIN SELECT RAISE(ABORT,'fixture'); END")
    try:
        read = await product.tool(session, "get_issue", {"issue_id": 42})
        assert read.is_error and read.structured_content["execution_state"] == "UNKNOWN"
        post = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert post.is_error and post.structured_content["reason_codes"] == ["EXECUTION_OUTCOME_UNKNOWN"]
        follow = await product.tool(session, "read_workspace_file", {"file_id": "PUBLIC_README"})
        assert follow.is_error
        assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
        assert product.counts(session["session_id"], "read_workspace_file") == (0, 0)
        reserve = await product.request(f"/internal/calls/{prechecked.json()['call_id']}/reserve", {
            "tool_name": "post_issue_comment", "backend_id": "demo.v1",
            "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")
        assert reserve.status_code == 409 and reserve.json()["code"] == "EXECUTION_OUTCOME_UNKNOWN"
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER fail_source")
    # Reconciliation of the effect alone must not erase the missing required audit record.
    import json
    with sqlite3.connect(product.effects_db) as db:
        receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (read.structured_content["call_id"],)).fetchone()[0])
    with sqlite3.connect(product.control_db) as db:
        rid = db.execute("SELECT reservation_id FROM executions WHERE call_id=?", (read.structured_content["call_id"],)).fetchone()[0]
    response = await product.request(f"/internal/calls/{read.structured_content['call_id']}/report", {
        "reservation_id": rid, "state": "SUCCEEDED", "receipt": receipt, "reconciled": True}, role="service")
    assert response.status_code == 503 and response.json()["code"] == "AUDIT_UNAVAILABLE"
    product.record("AT-09-source-followup", session, post, "post_issue_comment")
