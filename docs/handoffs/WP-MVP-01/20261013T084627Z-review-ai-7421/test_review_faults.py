"""Independent review cases; isolated /tmp product, no shared state."""
import importlib.util
import json
import sqlite3

import pytest

spec = importlib.util.spec_from_file_location("review_product", "/workspace/tests/acceptance/conftest.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    value = module.Product(tmp_path_factory.mktemp("review-product"))
    try:
        yield value
    finally:
        value.stop()


@pytest.mark.asyncio
async def test_source_failure_blocks_followup_write(product):
    session = await product.session("POST_COMMENT")
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER review_source_failure BEFORE INSERT ON sources WHEN NEW.kind != 'USER_REQUEST' BEGIN SELECT RAISE(ABORT,'review fixture'); END")
    try:
        read = await product.tool(session, "get_issue", {"issue_id": 42})
        assert read.is_error
        assert read.structured_content["execution_state"] == "UNKNOWN"
        assert read.structured_content["result"] is None
        followup = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        observation = {
            "case_id": "REVIEW-AT09-SOURCE-FOLLOWUP",
            "session_id": session["session_id"],
            "read": {"call_id": read.structured_content["call_id"], "state": read.structured_content["execution_state"]},
            "followup": {"call_id": followup.structured_content["call_id"], "state": followup.structured_content["execution_state"], "is_error": followup.is_error},
            "post_executor_invocations": product.counts(session["session_id"], "post_issue_comment")[0],
            "actual_comments": product.counts(session["session_id"], "post_issue_comment")[1],
        }
        print("SAFE_OBSERVATION=" + json.dumps(observation))
        assert followup.is_error and product.counts(session["session_id"], "post_issue_comment") == (0, 0), "Unresolved source failure must block following risk write (SEC-07/AT-09)"
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER review_source_failure")


@pytest.mark.asyncio
async def test_public_schema_matches_real_responses(product):
    from app.common import validate
    session = await product.session()
    validate("SessionCreated", session)
    read = await product.tool(session, "get_issue", {"issue_id": 43})
    assert read.is_error
    timeline = (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).json()
    validate("SessionTimeline", timeline)
    for check in timeline["checks"]:
        validate("CheckReply", check)
    assert product.counts(session["session_id"]) == (0, 0)


@pytest.mark.asyncio
async def test_unresolved_read_recovery_requires_source_and_receipt(product):
    from app.common import canonical, digest, mask, uid
    session = await product.session("POST_COMMENT")
    # Save a legitimate call before the source fault; it must not bypass a later hold.
    checked = await product.request("/internal/checks", {
        "session_id": session["session_id"], "client_request_id": uid(),
        "tool_name": "post_issue_comment", "backend_id": "demo.v1",
        "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")
    assert checked.status_code == 200
    saved_call = checked.json()["call_id"]
    with sqlite3.connect(product.control_db) as db:
        db.execute("CREATE TRIGGER review_recovery_fault BEFORE INSERT ON sources WHEN NEW.kind != 'USER_REQUEST' BEGIN SELECT RAISE(ABORT,'review fixture'); END")
    try:
        read = await product.tool(session, "get_issue", {"issue_id": 42})
        assert read.is_error and read.structured_content["execution_state"] == "UNKNOWN"
        cid = read.structured_content["call_id"]
        with sqlite3.connect(product.control_db) as db:
            rid = db.execute("SELECT reservation_id FROM executions WHERE call_id=?", (cid,)).fetchone()[0]
        with sqlite3.connect(product.effects_db) as db:
            receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (cid,)).fetchone()[0])
        payload = {"reservation_id": rid, "state": "SUCCEEDED", "receipt": receipt, "reconciled": True}
        missing_source = await product.request(f"/internal/calls/{cid}/report", payload, role="service")
        assert missing_source.status_code == 503 and missing_source.json()["code"] == "AUDIT_UNAVAILABLE"
        blocked_reserve = await product.request(f"/internal/calls/{saved_call}/reserve", {
            "tool_name": "post_issue_comment", "backend_id": "demo.v1",
            "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")
        assert blocked_reserve.status_code == 409
        assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    finally:
        with sqlite3.connect(product.control_db) as db:
            db.execute("DROP TRIGGER review_recovery_fault")
    from pathlib import Path
    raw = json.loads(Path("/workspace/fixtures/issues.json").read_text())["42"]
    snapshot = canonical(raw)
    source = await product.request("/internal/sources", {
        "call_id": cid, "kind": "EXTERNAL", "origin_ref": "demo:42",
        "content_sha256": digest(snapshot), "masked_excerpt": mask(snapshot)[:512],
        "match_values": []}, role="service")
    assert source.status_code == 200
    reconciled = await product.request(f"/internal/calls/{cid}/report", payload, role="service")
    assert reconciled.status_code == 200 and reconciled.json()["state"] == "SUCCEEDED"
    post = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not post.is_error
    assert product.counts(session["session_id"], "get_issue") == (1, 1)
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    print("SAFE_RECOVERY=" + json.dumps({"case_id":"REVIEW-AT09-SOURCE-RECONCILE", "session_id":session["session_id"], "read_call_id":cid, "source_repair_before_report":True, "read_invocations":1, "write_effects":1, "automated_reexecution":0}))
