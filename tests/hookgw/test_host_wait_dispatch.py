"""Post-host-approval dispatch, fake provider only; actual gateway is in probe."""

import asyncio
import importlib.util
import json
import time
import types
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from test_jev_policy import read, setup

from app.common import canonical
from app.pdp.semantic import material
from app.transparent.engine import Engine, Rejected
from app.transparent.server import create_app

ARGS = {"path": "report.txt", "content": "Release 완료. cafile 설정을 검토한다."}
TOKEN = "fake-offline-connection-token"


def prepared(tmp_path, monkeypatch, mode="normal"):
    e, fake = setup(tmp_path, mode)
    e.connect("m", TOKEN)
    e.connection(TOKEN, "s")
    keys = {"machine": "offline-machine-key", "human": "offline-human-key", "machine_id": "m", "ticket": lambda *_: "fake-test-ticket"}
    monkeypatch.setenv("HOOKGW_DEMO_DISPATCH", "1")
    return e, fake, create_app(e, keys)


def intent(e, cid="w", args=None, tool="write_file"):
    return e.register_demo_intent("m", "s", "t", cid, tool, args or ARGS, TOKEN)


async def dispatch(app, *, args=None, token=TOKEN, tool="write_file"):
    wire = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args or ARGS}}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://control") as client:
        return await client.post("/authz", json=wire, headers={"authorization": "Bearer " + token, "x-with-human-request": uuid4().hex})


def test_wait_before_fresh_judgment_not_before_execution_lease(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    assert intent(e) == {"call": "w", "intent": "RECORDED_NOT_AUTHORIZED"}
    row = e.history()[0]
    assert row["state"] == "PENDING" and row["decision"] is None and not fake.requests
    original = time.time
    monkeypatch.setattr("app.transparent.engine.time", types.SimpleNamespace(time=lambda: original() + 45))
    response = asyncio.run(dispatch(app))
    assert response.status_code == 200 and len(fake.requests) == 2
    row = e.history()[0]
    assert row["state"] == "EXECUTING"
    context = json.loads(row["reason"])
    assert context["analyzed_at"] - row["created"] >= 45
    assert "forward_check" not in context  # Never extended/renewed a semantic lease.
    assert asyncio.run(dispatch(app)).status_code == 403
    assert len(fake.requests) == 2


@pytest.mark.parametrize("changed", ["args", "turn", "source", "grant", "connection", "revoked", "body"])
def test_waiting_intent_requires_exact_current_binding_before_provider(tmp_path, monkeypatch, changed):
    e, fake, app = prepared(tmp_path, monkeypatch)
    intent(e)
    args, token = ARGS, TOKEN
    if changed == "args":
        args = {**ARGS, "content": "Changed after approval"}
    elif changed == "turn":
        e.turn("m", "s", "t2", "Another task", "C:\\repo")
    elif changed == "source":
        sid = str(uuid4())
        value = {"source_id": sid, "origin": "mcp", **material("Changed source after hook.")}
        with e.db() as db:
            db.execute("INSERT INTO sources VALUES(?,?,?,?)", (sid, "s", "synthetic-prior-call", e.seal(value)))
    elif changed == "grant":
        e.grant["protected_markers"].append("new-protection")
    elif changed == "connection":
        token = "other-fake-offline-connection"
        e.connect("m", token)
        e.connection(token, "s")
    elif changed == "revoked":
        with e.db() as db:
            db.execute("DELETE FROM connections")
    elif changed == "body":
        with e.db() as db:
            candidate = {"tool": "write_file", "route": "mcp", "args": {**ARGS, "content": "changed encrypted body"}}
            db.execute("UPDATE calls SET body=? WHERE id='w'", (e.seal(candidate),))
    response = asyncio.run(dispatch(app, args=args, token=token))
    assert response.status_code == 403 and not fake.requests
    assert all(row["state"] != "EXECUTING" for row in e.history())


def test_source_change_after_claim_before_authorize_still_stops_before_provider(tmp_path, monkeypatch):
    e, fake, _ = prepared(tmp_path, monkeypatch)
    intent(e)
    assert e.claim_demo_intent("m", "s", "write_file", ARGS, TOKEN) == "w"
    sid = str(uuid4())
    with e.db() as db:
        db.execute("INSERT INTO sources VALUES(?,?,?,?)", (sid, "s", "source-change", e.seal({"source_id": sid, **material("later")})))
    with pytest.raises(Rejected, match="FORWARD_SNAPSHOT_STALE"):
        asyncio.run(e.authorize("m", "w", demo_connection=TOKEN))
    assert not fake.requests


@pytest.mark.parametrize("mode,expected", [("attack", "DEMO_POLICY_DENIED"), ("ambiguous", "DEMO_CONFIRM_NOT_DISPATCHED"), ("api_error", "DEMO_POLICY_DENIED")])
def test_post_host_deny_confirm_failure_have_no_forward_or_paid_retry(tmp_path, monkeypatch, mode, expected):
    e, fake, app = prepared(tmp_path, monkeypatch, mode)
    read(e)
    intent(e)
    response = asyncio.run(dispatch(app))
    assert response.status_code == 403 and response.json()["code"] == expected
    calls = len(fake.requests)
    for _ in range(2):
        assert asyncio.run(dispatch(app)).status_code == 403
    assert len(fake.requests) == calls
    assert next(row for row in e.history() if row["id"] == "w")["state"] in ("DENIED", "CONFIRM")


def test_parallel_same_intent_has_one_judgment_and_forward(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    intent(e)
    async def parallel():
        return await asyncio.gather(dispatch(app), dispatch(app))
    responses = asyncio.run(parallel())
    assert sorted(row.status_code for row in responses) == [200, 403]
    assert len(fake.requests) == 2
    with e.db() as db:
        assert db.execute("SELECT count(*) FROM audit WHERE kind='FORWARD'").fetchone()[0] == 1


def test_missing_hook_and_old_ready_are_never_reanalyzed_by_demo(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    assert asyncio.run(dispatch(app)).status_code == 403 and not fake.requests
    e.register("m", "s", "t", "old-ready", "write_file", ARGS, "mcp")
    assert asyncio.run(e.authorize("m", "old-ready"))["state"] == "READY"
    before = e.history()[0]
    assert asyncio.run(dispatch(app)).status_code == 403 and len(fake.requests) == 2
    assert e.history()[0] == before


def test_unknown_blocks_new_intent_and_preserves_claim(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    intent(e)
    assert asyncio.run(dispatch(app)).status_code == 200
    e.transport_failure("m", "s", "write_file", ARGS)
    assert intent(e, "again")["intent"] == "EXISTING_TERMINAL"
    assert len(fake.requests) == 2
    with e.db() as db:
        assert db.execute("SELECT claimed FROM demo_intents WHERE call='w'").fetchone()[0] == 1
    assert asyncio.run(dispatch(app)).status_code == 403 and len(fake.requests) == 2


def test_restart_keeps_claim_and_unknown_without_repeat_analysis(tmp_path, monkeypatch):
    original, fake, _ = prepared(tmp_path, monkeypatch)
    key = Fernet.generate_key()
    e = Engine(tmp_path / "restart.db", key, original.grant, policy_router=original.policy_router)
    e.turn("m", "s", "t", "Write a normal report", "C:\\repo")
    e.connect("m", TOKEN)
    e.connection(TOKEN, "s")
    intent(e)
    e.claim_demo_intent("m", "s", "write_file", ARGS, TOKEN)
    assert asyncio.run(e.authorize("m", "w", demo_connection=TOKEN))["state"] == "READY"
    e.forward("m", "w", connection_token=TOKEN)
    restarted = Engine(e.path, key, e.grant, policy_router=e.policy_router)
    assert restarted.history()[0]["state"] == "UNKNOWN"
    with pytest.raises(Rejected):
        restarted.claim_demo_intent("m", "s", "write_file", ARGS, TOKEN)
    assert len(fake.requests) == 2


def test_semantic_allow_still_expires_after_judgment(tmp_path, monkeypatch):
    e, fake, _ = prepared(tmp_path, monkeypatch)
    intent(e)
    e.claim_demo_intent("m", "s", "write_file", ARGS, TOKEN)
    assert asyncio.run(e.authorize("m", "w", demo_connection=TOKEN))["state"] == "READY"
    original = time.time
    monkeypatch.setattr("app.transparent.engine.time", types.SimpleNamespace(time=lambda: original() + 31))
    with pytest.raises(Rejected, match="FORWARD_SNAPSHOT_STALE"):
        e.forward("m", "w", connection_token=TOKEN)
    assert len(fake.requests) == 2


def test_intent_endpoint_gate_and_machine_auth(tmp_path, monkeypatch):
    _, fake, app = prepared(tmp_path, monkeypatch)
    event = {"event": "PreToolUse", "connection": TOKEN, "session": "s", "turn": "t", "call": "w", "tool": "write_file", "args": ARGS, "route": "mcp"}
    async def request(token=None):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://control") as client:
            return await client.post("/demo/intent", json=event, headers={"authorization": "Bearer " + token} if token else {})
    assert asyncio.run(request()).status_code == 403
    monkeypatch.delenv("HOOKGW_DEMO_DISPATCH")
    assert asyncio.run(request("offline-machine-key")).status_code == 404
    monkeypatch.setenv("HOOKGW_DEMO_DISPATCH", "1")
    result = asyncio.run(request("offline-machine-key"))
    assert result.status_code == 200 and result.json()["intent"] == "RECORDED_NOT_AUTHORIZED"
    assert "decision" not in result.json() and not fake.requests


@pytest.mark.parametrize("forwarded", [False, True])
def test_child_close_revokes_pending_or_preserves_forward_as_unknown(tmp_path, monkeypatch, forwarded):
    e, fake, app = prepared(tmp_path, monkeypatch)
    intent(e)
    if forwarded:
        assert asyncio.run(dispatch(app)).status_code == 200
    assert e.close_demo_connection("m", TOKEN) == {"state": "CLOSED"}
    assert e.history()[0]["state"] == ("UNKNOWN" if forwarded else "STALE")
    assert e.close_demo_connection("m", TOKEN) == {"state": "CLOSED"}
    before = len(fake.requests)
    assert asyncio.run(dispatch(app)).status_code == 403
    assert len(fake.requests) == before


def test_child_close_during_judgment_prevents_forward_after_response(tmp_path, monkeypatch):
    e, fake, app = prepared(tmp_path, monkeypatch)
    intent(e)
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        original = fake.respond
        async def delayed(request):
            reply = original(request)
            if len(fake.requests) == 2:
                entered.set()
            await release.wait()
            return reply
        fake.client._transport = httpx.MockTransport(delayed)
        pending = asyncio.create_task(dispatch(app))
        await asyncio.wait_for(entered.wait(), 2)
        assert len(fake.requests) == 2
        e.close_demo_connection("m", TOKEN)
        release.set()
        response = await pending
        assert response.status_code == 403
    asyncio.run(scenario())
    assert e.history()[0]["state"] == "STALE" and len(fake.requests) == 2
    with e.db() as db:
        assert db.execute("SELECT count(*) FROM audit WHERE kind='FORWARD'").fetchone()[0] == 0


def test_hook_empty_reply_is_intent_only_and_never_approval_override(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "tools/mvp_demo_hook.py"
    spec = importlib.util.spec_from_file_location("offline_demo_hook", path)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    (tmp_path / "profile.json").write_text(json.dumps({"workspace": str(tmp_path)}))
    sent = []
    def send(host, endpoint, body):
        sent.append((endpoint, body))
        return {"call": body["call"], "intent": "RECORDED_NOT_AUTHORIZED"}
    monkeypatch.setattr(hook.core, "send", send)
    value = {"hook_event_name": "PreToolUse", "session_id": "s", "turn_id": "t", "cwd": str(tmp_path), "tool_name": "mcp__with_human__write_file", "tool_use_id": "w", "tool_input": ARGS}
    assert hook.handle(tmp_path, value, TOKEN) == {}
    assert sent[0][0] == "/demo/intent"
    value["tool_name"] = "Bash"
    denied = hook.handle(tmp_path, value, TOKEN)
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "allow" not in canonical(denied).lower()
