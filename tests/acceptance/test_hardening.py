import asyncio
import sqlite3
import time

import pytest

from app.common import digest, uid
from app.storage.retention import DATA_TTL


async def wait_for(probe, timeout=14):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if probe():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("daemon/startup deadline exceeded")


def scalar(path, sql, args=()):
    with sqlite3.connect(path) as db:
        return db.execute(sql, args).fetchone()[0]


async def reserve_write(product, session):
    payload = {"tool_name": "post_issue_comment", "backend_id": "demo.v1",
               "args": {"issue_id": 42, "body": "검토 완료"}}
    checked = await product.request("/internal/checks", {**payload, "session_id": session["session_id"],
                                    "client_request_id": uid()}, role="service")
    assert checked.status_code == 200
    cid = checked.json()["call_id"]
    reserved = await product.request(f"/internal/calls/{cid}/reserve", payload, role="service")
    assert reserved.status_code == 200 and reserved.json()["execute"]
    return cid, reserved.json()


@pytest.mark.asyncio
async def test_real_daemon_and_startup_stale_unknown_no_refund(product):
    for mode in ("daemon", "restart"):
        session = await product.session("POST_COMMENT")
        cid, _ = await reserve_write(product, session)
        if mode == "restart":
            product.stop()
        with sqlite3.connect(product.control_db) as db:
            db.execute("UPDATE executions SET reserved_at=? WHERE call_id=?", (time.time() - 31, cid))
        if mode == "restart":
            product.start()
        await wait_for(lambda cid=cid: scalar(product.control_db, "SELECT state FROM executions WHERE call_id=?", (cid,)) == "UNKNOWN")
        assert scalar(product.control_db, "SELECT write_budget FROM sessions WHERE id=?", (session["session_id"],)) == 0
        retry = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료", "resume_call_id": cid})
        other = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert retry.is_error and other.is_error
        assert product.counts(session["session_id"]) == (0, 0)
        product.record("A2-stale-" + mode, session, retry)
    fresh = await product.session("POST_COMMENT")
    good = await product.tool(fresh, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not good.is_error and product.counts(fresh["session_id"]) == (1, 1)
    product.record("A2-restart-normal-recovery", fresh, good)


@pytest.mark.asyncio
async def test_two_db_retention_failure_then_restart_no_old_access(product):
    session = await product.session("POST_COMMENT")
    write = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not write.is_error and product.counts(session["session_id"]) == (1, 1)
    approval_session = await product.session("POST_COMMENT")
    pending = await product.tool(approval_session, "post_issue_comment", {"issue_id": 42, "body": "candidate"})
    aid = pending.structured_content["approval_id"]
    assert aid
    survivor = await product.session()
    assert (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).status_code == 200
    cid = write.structured_content["call_id"]
    with sqlite3.connect(product.effects_db) as db:
        ciphertext = db.execute("SELECT body_cipher FROM comments WHERE call_id=?", (cid,)).fetchone()[0]
        db.execute("UPDATE invocations SET started_at=? WHERE call_id=?", (time.time() - DATA_TTL, cid))
        db.execute("UPDATE comments SET created_at=? WHERE call_id=?", (time.time() - DATA_TTL, cid))
        db.execute("CREATE TRIGGER fail_disposal BEFORE DELETE ON comments BEGIN SELECT RAISE(ABORT,'disposal-fixture'); END")
    with sqlite3.connect(product.control_db) as db:
        db.execute("UPDATE session_retention SET created_at=? WHERE session_id IN (?,?)",
                   (time.time() - DATA_TTL, session["session_id"], approval_session["session_id"]))
    # Access must be refused even before the independent cleanups commit.
    assert (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).status_code in (403, 404)
    assert (await product.request(f"/v1/approvals/{aid}/reject", {})).status_code in (403, 404)
    resolve = await product.request("/internal/auth/resolve", {"agent_token": session["agent_session_token"]}, role="service")
    assert resolve.status_code in (401, 403)
    reserve = await product.request(f"/internal/calls/{cid}/reserve", {
        "tool_name": "post_issue_comment", "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "검토 완료"}}, role="service")
    assert reserve.status_code in (403, 404)
    await wait_for(lambda: scalar(product.control_db, "SELECT count(*) FROM sessions WHERE id=?", (session["session_id"],)) == 0)
    # The second DB still holds its record because its DELETE failed atomically.
    assert product.counts(session["session_id"]) == (1, 1)
    with sqlite3.connect(product.effects_db) as db:
        db.execute("DROP TRIGGER fail_disposal")
    product.stop()
    product.start()
    await wait_for(lambda: product.counts(session["session_id"]) == (0, 0))
    product.stop()
    product.start()  # repeated startup is safe, no effects recovered by execution
    assert product.counts(session["session_id"]) == (0, 0)
    assert (await product.request(f"/v1/sessions/{survivor['session_id']}/timeline")).status_code == 200
    assert (await product.request(f"/v1/approvals/{aid}/approve", {"expected_args_sha256": "0" * 64})).status_code == 404
    assert (await product.request(f"/internal/calls/{cid}/report", {
        "reservation_id": uid(), "state": "UNKNOWN", "error_code": "EXECUTION_OUTCOME_UNKNOWN"}, role="service")).status_code == 404
    assert scalar(product.control_db, "SELECT count(*) FROM disposals WHERE session_sha256=?", (digest(session["session_id"]),)) == 1
    assert scalar(product.effects_db, "SELECT count(*) FROM disposals WHERE call_sha256=?", (digest(cid),)) == 1
    for database in (product.control_db, product.effects_db):
        for path in database.parent.glob(database.name + "*"):
            data = path.read_bytes()
            assert ciphertext not in data
            assert session["agent_session_token"].encode() not in data
            assert b"DEMO_SECRET_DO_NOT_SEND" not in data
    product.record("A1-two-db-failure-startup", session)
    product.records[-1].update({"effects_before_purge": 1, "additional_effects": 0, "disposed": True})


@pytest.mark.asyncio
async def test_check_reserve_mandatory_event_failure_rolls_back(product):
    for target in ("CHECKED", "RESERVED", "EXECUTIONS"):
        session = await product.session("POST_COMMENT")
        pending = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "candidate"})
        check = next(x for x in (await product.request(f"/v1/sessions/{session['session_id']}/timeline")).json()["checks"])
        assert (await product.request(f"/v1/approvals/{check['approval_id']}/approve", {
            "expected_args_sha256": check["args_sha256"]})).status_code == 200
        budget = scalar(product.control_db, "SELECT call_budget FROM sessions WHERE id=?", (session["session_id"],))
        with sqlite3.connect(product.control_db) as db:
            if target == "EXECUTIONS":
                db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON executions BEGIN SELECT RAISE(ABORT,'private-error-canary'); END")
            else:
                db.execute(f"CREATE TRIGGER fail_event BEFORE INSERT ON events WHEN NEW.event_kind='{target}' BEGIN SELECT RAISE(ABORT,'private-error-canary'); END")
        try:
            args = {"issue_id": 42, "body": "candidate"}
            if target in ("RESERVED", "EXECUTIONS"):
                args["resume_call_id"] = pending.structured_content["call_id"]
            result = await product.tool(session, "post_issue_comment", args)
            assert result.is_error and "private-error-canary" not in str(result)
            assert product.counts(session["session_id"]) == (0, 0)
            assert scalar(product.control_db, "SELECT call_budget FROM sessions WHERE id=?", (session["session_id"],)) == budget
            assert scalar(product.control_db, "SELECT write_budget FROM sessions WHERE id=?", (session["session_id"],)) == 1
            assert scalar(product.control_db, "SELECT status FROM approvals WHERE id=?", (check["approval_id"],)) == "APPROVED"
            assert scalar(product.control_db, "SELECT count(*) FROM executions WHERE call_id=?", (check["call_id"],)) == 0
        finally:
            with sqlite3.connect(product.control_db) as db:
                db.execute("DROP TRIGGER fail_event")
        good = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "candidate", "resume_call_id": check["call_id"]})
        assert not good.is_error and product.counts(session["session_id"]) == (1, 1)
        product.record("A2-mandatory-event-" + target, session, result)
        product.records[-1].update({"fault_executor_invocations": 0, "fault_actual_effects": 0, "recovery_effects": 1})


@pytest.mark.asyncio
async def test_both_real_daemons_purge_without_restart(product):
    session = await product.session("POST_COMMENT")
    result = await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    assert not result.is_error and product.counts(session["session_id"]) == (1, 1)
    with sqlite3.connect(product.control_db) as db:
        db.execute("UPDATE session_retention SET created_at=? WHERE session_id=?", (time.time() - DATA_TTL, session["session_id"]))
    with sqlite3.connect(product.effects_db) as db:
        db.execute("UPDATE invocations SET started_at=? WHERE session_id=?", (time.time() - DATA_TTL, session["session_id"]))
        db.execute("UPDATE comments SET created_at=? WHERE session_id=?", (time.time() - DATA_TTL, session["session_id"]))
    started = time.monotonic()
    await wait_for(lambda: (scalar(product.control_db, "SELECT count(*) FROM sessions WHERE id=?", (session["session_id"],)) == 0
                            and product.counts(session["session_id"]) == (0, 0)))
    product.record("A1-both-daemons", session)
    product.records[-1].update({"elapsed_ms": round((time.monotonic() - started) * 1000),
                               "effects_before_purge": 1, "additional_effects": 0, "disposed": True})
