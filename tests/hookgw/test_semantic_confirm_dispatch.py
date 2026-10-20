"""Same-invocation human exception approval: real SQLite, fake HTTP only."""
import asyncio
import base64
import json
import time
import types
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from test_host_wait_dispatch import ARGS, TOKEN, dispatch, intent, prepared
from test_jev_policy import read

from app.common import canonical, digest
from app.pdp.semantic import material
from app.transparent.engine import Engine, Rejected
from app.transparent.file_errors import missing_read_result


async def request(app, path, value=None, token="offline-human-key", method="POST"):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://control") as client:
        return await client.request(method, path, json=value, headers={"authorization": "Bearer " + token})


def pending(app):
    response = asyncio.run(request(app, "/demo/pending", method="GET"))
    assert response.status_code == 200
    return response.json()["pending"]


def status(app):
    return asyncio.run(request(app, "/demo/wait", {"connection": TOKEN, "tool": "write_file", "args": ARGS}, "offline-machine-key"))


def confirm(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch, "ambiguous")
    read(e)
    intent(e)
    response = asyncio.run(dispatch(app))
    assert response.status_code == 403 and response.json()["code"] == "DEMO_CONFIRM_NOT_DISPATCHED"
    assert len(fake.requests) == 2
    item = pending(app)[0]
    assert item["candidate"] == {"tool": "write_file", "route": "mcp", "args": ARGS}
    return e, fake, app, {"call": "w", "approve": True, "approval_binding": item["approval_binding"]}


def row(e, cid="w"):
    return next(x for x in e.history() if x["id"] == cid)


def test_same_rpc_human_approval_resume_once_without_new_analysis(tmp_path, monkeypatch):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    original = json.loads(row(e)["reason"])
    waiting = status(app).json()
    assert waiting == {"status": "PENDING", "pending_ref": digest("w"), "expires_at": pending(app)[0]["expires_at"], "resume_allowed": False}
    # Human thinking time may exceed the original semantic execution lease.
    clock = types.SimpleNamespace(time=lambda: time.time()+60)
    monkeypatch.setattr("app.transparent.demo_approval.time", clock)
    monkeypatch.setattr("app.transparent.engine.time", clock)
    assert asyncio.run(request(app, "/approval", choice)).json() == {"state": "APPROVED"}
    assert status(app).json()["resume_allowed"] is True
    assert asyncio.run(dispatch(app)).status_code == 200
    current = row(e)
    assert current["state"] == "EXECUTING" and current["decision"] == "CONFIRM"
    reason = json.loads(current["reason"])
    assert reason["analyzed_at"] == original["analyzed_at"]
    assert reason["reasons"] == original["reasons"] and reason["demo_approval"]["original_decision"] == "CONFIRM"
    assert status(app).json()["status"] == "CONSUMED"
    assert asyncio.run(dispatch(app)).status_code == 403
    assert len(fake.requests) == 2
    with e.db() as db:
        assert db.execute("SELECT consumed FROM approvals WHERE call='w'").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM audit WHERE kind='FORWARD' AND call='w'").fetchone()[0] == 1


@pytest.mark.parametrize("token", ["offline-machine-key", TOKEN, "actor-fake-token", ""])
def test_only_human_can_view_or_approve(tmp_path, monkeypatch, token):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    assert asyncio.run(request(app, "/demo/pending", token=token, method="GET")).status_code == 403
    assert asyncio.run(request(app, "/approval", choice, token)).status_code == 403
    assert row(e)["state"] == "CONFIRM" and len(fake.requests) == 2


@pytest.mark.parametrize("mutate", ["binding", "omit_binding", "truthy", "extra"])
def test_approval_requires_exact_human_proof(tmp_path, monkeypatch, mutate):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    if mutate == "binding":
        choice["approval_binding"] = "0"*64
    elif mutate == "omit_binding":
        choice.pop("approval_binding")
    elif mutate == "truthy":
        choice["approve"] = "yes"
    else:
        choice["connection"] = TOKEN
    assert asyncio.run(request(app, "/approval", choice)).status_code == 403
    assert row(e)["state"] == "CONFIRM" and len(fake.requests) == 2


def test_rejection_preserves_semantic_decision_and_blocks_new_call_analysis(tmp_path, monkeypatch):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    before = row(e)["reason"]
    assert intent(e, "repeat")["intent"] == "EXISTING_PENDING"
    assert len(e.history()) == 2
    choice["approve"] = False
    assert asyncio.run(request(app, "/approval", choice)).json() == {"state": "DENIED"}
    assert row(e)["decision"] == "CONFIRM" and row(e)["reason"] == before
    assert status(app).json()["status"] == "REJECTED"
    assert intent(e, "repeat2")["intent"] == "EXISTING_TERMINAL"
    assert asyncio.run(dispatch(app)).status_code == 403 and len(fake.requests) == 2
    assert asyncio.run(request(app, "/approval", {**choice, "approve": True})).status_code == 403


@pytest.mark.parametrize("change", ["source", "turn", "grant", "policy", "close", "expiry", "body"])
def test_stale_confirmation_cannot_be_approved_or_forwarded(tmp_path, monkeypatch, change):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    if change == "source":
        sid = str(uuid4())
        with e.db() as db:
            db.execute("INSERT INTO sources VALUES(?,?,?,?)", (sid, "s", "later", e.seal({"source_id": sid, "origin": "mcp", **material("Changed source.")})))
        assert intent(e, "changed-source-again")["intent"] == "EXISTING_TERMINAL"
    elif change == "turn":
        e.turn("m", "s", "t2", "Explicit new user task", "C:\\repo")
    elif change == "grant":
        e.grant["protected_markers"].append("new-protection")
    elif change == "policy":
        e.policy = "new-policy"
    elif change == "close":
        e.close_demo_connection("m", TOKEN)
    elif change == "expiry":
        monkeypatch.setattr("app.transparent.demo_approval.time", types.SimpleNamespace(time=lambda: time.time()+601))
    else:
        with e.db() as db:
            db.execute("UPDATE calls SET body=? WHERE id='w'", (e.seal({"route": "mcp", "tool": "write_file", "args": {**ARGS, "content": "tampered"}}),))
    assert asyncio.run(request(app, "/approval", choice)).status_code == 403
    assert not pending(app)
    assert asyncio.run(dispatch(app)).status_code == 403 and len(fake.requests) == 2


def test_approved_lease_expiry_never_reanalyzes(tmp_path, monkeypatch):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    assert asyncio.run(request(app, "/approval", choice)).status_code == 200
    monkeypatch.setattr("app.transparent.demo_approval.time", types.SimpleNamespace(time=lambda: time.time()+31))
    assert status(app).json()["status"] == "STALE"
    assert asyncio.run(dispatch(app)).status_code == 403 and len(fake.requests) == 2
    assert row(e)["state"] == "APPROVED"


@pytest.mark.parametrize("change", ["id", "metadata", "args"])
def test_rpc_binding_cannot_be_replaced_on_resume(tmp_path, monkeypatch, change):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    assert asyncio.run(request(app, "/approval", choice)).status_code == 200
    wire = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "write_file", "arguments": ARGS.copy()}}
    if change == "id":
        wire["id"] = 2
    elif change == "metadata":
        wire["params"]["_meta"] = {"untrusted": "changed"}
    else:
        wire["params"]["arguments"]["content"] = "changed"
    response = asyncio.run(request(app, "/authz", wire, TOKEN))
    assert response.status_code == 403 and row(e)["state"] == "APPROVED"
    with e.db() as db:
        assert db.execute("SELECT consumed FROM approvals WHERE call='w'").fetchone()[0] == 0
    assert asyncio.run(dispatch(app)).status_code == 200 and len(fake.requests) == 2


def test_approval_race_and_resume_race_are_single_consume(tmp_path, monkeypatch):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    def vote(approve):
        try:
            return e.approval("m", "w", approve, choice["approval_binding"])["state"]
        except Rejected:
            return "REJECTED_RACE"
    with ThreadPoolExecutor(max_workers=2) as pool:
        votes = list(pool.map(vote, [True, False]))
    assert votes.count("REJECTED_RACE") == 1
    if row(e)["state"] == "APPROVED":
        def resume(_):
            return asyncio.run(dispatch(app)).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(resume, range(2))) == [200, 403]
    else:
        assert asyncio.run(dispatch(app)).status_code == 403
    assert len(fake.requests) == 2


def test_old_demo_confirm_without_new_rpc_binding_is_never_retroapproved(tmp_path, monkeypatch):
    e, fake, _ = prepared(tmp_path, monkeypatch, "ambiguous")
    read(e)
    intent(e)
    e.claim_demo_intent("m", "s", "write_file", ARGS, TOKEN)
    assert asyncio.run(e.authorize("m", "w", demo_connection=TOKEN))["decision"] == "CONFIRM"
    before = row(e)
    with pytest.raises(Rejected, match="LEGACY_UNBOUND"):
        e.approval("m", "w", True)
    assert row(e) == before and len(fake.requests) == 2


def test_optin_policy_change_preserves_old_rows_without_new_authority(tmp_path, monkeypatch):
    e, fake, app, choice = confirm(tmp_path, monkeypatch)
    before = e.history()
    key = base64.urlsafe_b64encode(e.box._signing_key+e.box._encryption_key)
    e.policy_router.policy = "fake-optin-policy-new"
    fresh = Engine(e.path, key, e.grant, policy_router=e.policy_router, preserve_history_on_policy_change=True)
    assert fresh.history() == before
    with pytest.raises(Rejected):
        fresh.approval("m", "w", True, choice["approval_binding"])
    assert fresh.history() == before and len(fake.requests) == 2


@pytest.mark.parametrize("old_state", ["READY", "UNKNOWN", "CONFIRM"])
def test_policy_optin_never_relabels_legacy_ready_confirm_unknown(tmp_path, monkeypatch, old_state):
    e, _, _, _ = confirm(tmp_path, monkeypatch)
    with e.db() as db:
        db.execute("UPDATE calls SET state=? WHERE id='w'", (old_state,))
    before = e.history()
    key = base64.urlsafe_b64encode(e.box._signing_key+e.box._encryption_key)
    e.policy_router.policy = "explicit-new-offline-policy"
    fresh = Engine(e.path, key, e.grant, policy_router=e.policy_router, preserve_history_on_policy_change=True)
    assert fresh.history() == before
    with pytest.raises(Rejected):
        fresh.forward("m", "w", connection_token=TOKEN)
    assert fresh.history() == before


def test_confirm_metadata_is_forgotten_with_session(tmp_path, monkeypatch):
    e, _, _, _ = confirm(tmp_path, monkeypatch)
    e.purge("s")
    with e.db() as db:
        for table in ("demo_confirmations", "demo_rpc_bindings", "demo_intents"):
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


def test_exact_missing_read_observed_error_is_not_source_or_unknown(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    args = {"path": "absent.txt"}
    intent(e, "missing", args, "read_file")
    assert asyncio.run(dispatch(app, args=args, tool="read_file")).status_code == 200
    assert e.transport_observed("m", "s", "read_file", args, missing_read_result()) == {"state": "OBSERVED_ERROR"}
    for failed in (False, True):
        assert e.observe("m", "missing", "read_file", args, "untrusted", failed=failed)["state"] == "OBSERVED_ERROR"
    assert json.loads(row(e, "missing")["reason"])["execution_error"]["code"] == "FILE_NOT_FOUND"
    with e.db() as db:
        assert db.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
    # Legitimate read after creating a previously missing file is allowed again.
    assert intent(e, "new-read", args, "read_file")["intent"] == "RECORDED_NOT_AUTHORIZED"
    assert asyncio.run(dispatch(app, args=args, tool="read_file")).status_code == 200
    assert not fake.requests


@pytest.mark.parametrize("change", ["extra", "text", "type", "write", "unknown"])
def test_only_exact_typed_read_error_can_become_observed_error(tmp_path, monkeypatch, change):
    e, _, app = prepared(tmp_path, monkeypatch)
    args, tool = {"path": "absent.txt"}, "read_file"
    if change == "write":
        args, tool = ARGS, "write_file"
    intent(e, "missing", args, tool)
    assert asyncio.run(dispatch(app, args=args, tool=tool)).status_code == 200
    value = missing_read_result()
    if change == "extra":
        value["raw"] = "unexpected"
    elif change == "text":
        value["content"][0]["text"] = "different"
    elif change == "type":
        value["isError"] = 1
    elif change == "unknown":
        e.transport_failure("m", "s", tool, args)
    with pytest.raises(Rejected, match="TRANSPORT_RESULT_BINDING"):
        e.transport_observed("m", "s", tool, args, value)
    assert row(e, "missing")["state"] == ("UNKNOWN" if change == "unknown" else "EXECUTING")


def test_non_demo_legacy_approval_still_works(tmp_path, monkeypatch):
    e, fake, _ = prepared(tmp_path, monkeypatch, "ambiguous")
    read(e)
    e.register("m", "s", "t", "generic", "write_file", ARGS, "mcp")
    assert asyncio.run(e.authorize("m", "generic"))["decision"] == "CONFIRM"
    assert e.approval("m", "generic", True) == {"state": "APPROVED"}
    assert e.consume_approval("m", "generic", digest(canonical({"tool": "write_file", "args": ARGS, "route": "mcp"})))["state"] == "READY"
    e.forward("m", "generic")
    assert len(fake.requests) == 2
