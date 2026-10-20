import asyncio
import sqlite3
import time

import pytest


async def confirmation(product):
    session = await product.session("POST_COMMENT")
    read = await product.tool(session, "get_issue", {"issue_id": 42})
    body = "제목: " + read.structured_content["result"]["data"]["title"]
    result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": body})
    assert result.is_error and result.structured_content["decision"] == "CONFIRM"
    assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    timeline = (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).json()
    check = next(x for x in timeline["checks"] if x["call_id"] == result.structured_content["call_id"])
    assert "SOURCE_VALUE_OBSERVED" in check["reason_codes"]
    return session, body, result, check


@pytest.mark.asyncio
async def test_nt03_at06_at07_exact_approval_race(product):
    session, body, result, check = await confirmation(product)
    approved = await product.request(f"/v1/approvals/{check['approval_id']}/approve",
                                     {"expected_args_sha256": check["args_sha256"]})
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    args = {"issue_id": 42, "body": body, "resume_call_id": check["call_id"]}
    results = await asyncio.gather(*(product.tool(session, "post_issue_comment", args) for _ in range(2)))
    assert any(not x.is_error for x in results)
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    replay = await product.tool(session, "post_issue_comment", args)
    assert not replay.is_error
    assert product.counts(session["session_id"], "post_issue_comment") == (1, 1)
    timeline = (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).json()
    assert timeline["approvals"][0]["status"] == "CONSUMED"
    assert next(x for x in timeline["checks"] if x["call_id"] == check["call_id"])["decision"] == "CONFIRM"
    product.record("NT-03", session, next(x for x in results if not x.is_error), "post_issue_comment")
    product.record("AT-06-replay", session, replay, "post_issue_comment")
    product.record("AT-07", session, replay, "post_issue_comment")


@pytest.mark.asyncio
async def test_at05_at06_binding_expiry_policy(product):
    session, body, result, check = await confirmation(product)
    assert (await product.request(f"/v1/approvals/{check['approval_id']}/approve",
                                 {"expected_args_sha256": "0" * 64})).status_code == 409
    changed = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": body + " ",
                                                               "resume_call_id": check["call_id"]})
    assert changed.is_error and "ACTION_BINDING_MISMATCH" in changed.structured_content["reason_codes"]
    other = await product.session("POST_COMMENT")
    cross = await product.tool(other, "post_issue_comment", {"issue_id": 42, "body": body,
                                                           "resume_call_id": check["call_id"]})
    assert cross.is_error and product.counts(other["session_id"], "post_issue_comment") == (0, 0)
    with sqlite3.connect(product.control_db) as db:
        db.execute("UPDATE approvals SET expires_at=? WHERE id=?", (time.time() - 1, check["approval_id"]))
    expired = await product.request(f"/v1/approvals/{check['approval_id']}/approve",
                                    {"expected_args_sha256": check["args_sha256"]})
    assert expired.status_code == 409 and expired.json()["code"] == "APPROVAL_EXPIRED"
    with sqlite3.connect(product.control_db) as db:
        db.execute("UPDATE sessions SET policy_version='fixture-policy-change' WHERE id=?", (session["session_id"],))
    stale = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": body,
                                                            "resume_call_id": check["call_id"]})
    assert stale.is_error and "POLICY_CHANGED" in stale.structured_content["reason_codes"]
    assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    product.record("AT-05", session, changed, "post_issue_comment")
    product.record("AT-06-expiry-cross", session, stale, "post_issue_comment")


@pytest.mark.asyncio
async def test_rejected_approval_and_deny_no_approval(product):
    session, body, result, check = await confirmation(product)
    rejected = await product.request(f"/v1/approvals/{check['approval_id']}/reject", {})
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"
    resume = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": body,
                                                             "resume_call_id": check["call_id"]})
    assert resume.is_error and product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    summary = await product.session()
    denied = await product.tool(summary, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert denied.structured_content["approval_id"] is None
