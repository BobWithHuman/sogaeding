import asyncio
import json
import sqlite3
import time

import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["timeout", "json", "schema", "error", "list-error", "redirect"])
async def test_real_mcp_pre_execution_peer_faults(fault_product, action):
    product = fault_product
    session = await product.session("POST_COMMENT")
    product.mode({"path": "internal/checks", "action": action})
    started = time.monotonic()
    try:
        result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        elapsed = time.monotonic() - started
        assert result.is_error and result.structured_content["reason_codes"] == ["PDP_UNAVAILABLE"]
        assert elapsed < (30 if action=='timeout' else 4)
        assert product.counts(session["session_id"]) == (0, 0)
        assert "private-error-canary" not in str(result)
        assert product.human not in str(result) and product.service not in str(result)
        product.record("A2-peer-" + action, session, result)
        product.records[-1]["elapsed_ms"] = round(elapsed * 1000)
    finally:
        product.mode({})
    good = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not good.is_error and product.counts(session["session_id"]) == (1, 1)


@pytest.mark.asyncio
async def test_after_write_report_response_loss_and_real_receipt_reconciliation(fault_product):
    product = fault_product
    session = await product.session("POST_COMMENT")
    product.mode({"path": "reports", "action": "timeout", "only_success_report": True})
    try:
        result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert result.is_error and result.structured_content["execution_state"] == "UNKNOWN"
        assert product.counts(session["session_id"]) == (1, 1)
        cid = result.structured_content["call_id"]
        with sqlite3.connect(product.control_db) as db:
            state, rid = db.execute("SELECT state,reservation_id FROM executions WHERE call_id=?", (cid,)).fetchone()
            assert state == "UNKNOWN"
        same = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료", "resume_call_id": cid})
        other = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert same.is_error and other.is_error and product.counts(session["session_id"]) == (1, 1)
    finally:
        product.mode({})
    with sqlite3.connect(product.effects_db) as db:
        receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (cid,)).fetchone()[0])
    fixed = await product.request(f"/internal/calls/{cid}/report", {"reservation_id": rid, "state": "SUCCEEDED",
        "receipt": receipt, "reconciled": True}, role="service")
    assert fixed.status_code == 200 and fixed.json()["state"] == "SUCCEEDED"
    assert product.counts(session["session_id"]) == (1, 1)
    product.record("A2-report-response-loss", session, result)
    product.records[-1].update({"additional_effects": 0, "explicit_reconciliation": "SUCCEEDED"})


@pytest.mark.asyncio
async def test_real_mcp_request_cancellation_after_effect(fault_product):
    product = fault_product
    session = await product.session("POST_COMMENT")
    product.mode({"path": "reports", "action": "timeout", "only_success_report": True})
    try:
        async with httpx2.AsyncClient(verify=product.trust, trust_env=False, timeout=4,
                headers={"Authorization": "Bearer " + session["agent_session_token"]}) as http:
            async with Client(streamable_http_client("https://127.0.0.1:8001/mcp", http_client=http)) as client:
                task = asyncio.create_task(client.call_tool("post_issue_comment", {"issue_id": 42, "body": "검토 완료"}))
                until = time.monotonic() + 3
                while product.counts(session["session_id"]) != (1, 1):
                    assert time.monotonic() < until
                    await asyncio.sleep(0.01)
                started = time.monotonic()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                until = started + 0.8  # sooner than the independent 1s PDP timeout
                while True:
                    with sqlite3.connect(product.control_db) as db:
                        cid, rid, state = db.execute("SELECT e.call_id,e.reservation_id,e.state FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=?", (session["session_id"],)).fetchone()
                    if state == "UNKNOWN":
                        break
                    assert time.monotonic() < until, "request cancellation was not durably recorded before PDP timeout"
                    await asyncio.sleep(0.01)
                elapsed = time.monotonic() - started
        same = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료", "resume_call_id": cid})
        other = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert same.is_error and other.is_error and product.counts(session["session_id"]) == (1, 1)
        with sqlite3.connect(product.control_db) as db:
            assert db.execute("SELECT write_budget FROM sessions WHERE id=?", (session["session_id"],)).fetchone()[0] == 0
        product.record("A2-real-MCP-cancellation", session, same)
        product.records[-1].update({"elapsed_ms": round(elapsed * 1000), "additional_effects": 0,
                                   "cancellation_transport": "SDK response stream close"})
    finally:
        product.mode({})
    with sqlite3.connect(product.effects_db) as db:
        receipt = json.loads(db.execute("SELECT receipt FROM invocations WHERE call_id=?", (cid,)).fetchone()[0])
    fixed = await product.request(f"/internal/calls/{cid}/report", {"reservation_id": rid, "state": "SUCCEEDED",
        "receipt": receipt, "reconciled": True}, role="service")
    assert fixed.status_code == 200 and product.counts(session["session_id"]) == (1, 1)
