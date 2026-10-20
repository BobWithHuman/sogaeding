"""Approval wait: current public read checks, one reservation, no paid retry."""
import asyncio
import importlib.util
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet

from app.common import canonical, digest
from app.transparent import engine as engine_module
from app.transparent.engine import Engine, Rejected
from app.transparent.jev import JevClient
from app.transparent.jev_policy import JevPolicy
from app.transparent.server import create_app


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    clock = SimpleNamespace(now=time.time())
    monkeypatch.setattr(engine_module, "time", SimpleNamespace(time=lambda: clock.now))
    grant = {"workspace": "C:/repo", "tools": {"mcp": ["read_file", "write_file"], "native": []}, "protected_markers": [".env"]}
    e = Engine(tmp_path / "control.db", Fernet.generate_key(), grant, policy_router=JevPolicy(JevClient()))
    e.connect("machine", "connection")
    e.connection("connection", "session")
    e.turn("machine", "session", "turn", "공개 notes를 읽어 핵심 사실을 알려줘.", "C:/repo")
    args = {"path": "fixtures/hookgw/notes.txt"}
    e.register("machine", "session", "turn", "call", "read_file", args, "mcp")
    assert asyncio.run(e.authorize("machine", "call"))["state"] == "READY"
    return e, clock, args


@pytest.mark.parametrize("delay", [0, 90.074, 3600])
def test_waited_public_read_reserves_once_and_preserves_original(prepared, delay):
    e, clock, args = prepared
    original = json.loads(e.history()[0]["reason"])
    clock.now += delay
    assert e.forward("machine", "call", connection_token="connection")["state"] == "EXECUTING"
    current = json.loads(e.history()[0]["reason"])
    assert current["analyzed_at"] == original["analyzed_at"]
    assert current["snapshot_sha256"] == original["snapshot_sha256"]
    if delay > 30:
        assert current["forward_check"]["checked_at"] == clock.now
        assert current["forward_check"]["model_requests"] == 0
    with pytest.raises(Rejected, match="FORWARD_REPLAY"):
        e.forward("machine", "call")
    result = {"content": [{"type": "text", "text": "공개 배포가 완료되었습니다."}]}
    e.transport_observed("machine", "session", "read_file", args, result)
    assert e.observe("machine", "call", "read_file", args, result)["state"] == "OBSERVED"


@pytest.mark.parametrize("change", ["args", "turn", "policy", "grant", "prompt", "source", "legacy", "semantic", "unknown", "connection", "session", "analysis_stop", "protected", "scope", "marker"])
def test_wait_rejects_changed_or_ineligible_context(prepared, change):
    e, clock, _ = prepared
    clock.now += 91
    with e.db() as db:
        row = db.execute("SELECT * FROM calls WHERE id='call'").fetchone()
        context = json.loads(row["reason"])
        if change in ("args", "protected", "scope", "marker"):
            candidate = e.open(row["body"])
            candidate["args"]["path"] = {"args": "other.txt", "protected": "src/app/secret.py", "scope": "../notes.txt", "marker": ".env"}[change]
            # Even a matching action hash cannot legitimize a forbidden parser target.
            db.execute("UPDATE calls SET body=?,hash=? WHERE id='call'", (e.seal(candidate), digest(canonical(candidate)) if change != "args" else row["hash"]))
        elif change == "turn":
            db.execute("UPDATE sessions SET turn='new' WHERE id='session'")
        elif change == "policy":
            e.policy = "changed"
        elif change == "grant":
            e.grant["tools"]["mcp"] = []
        elif change == "prompt":
            db.execute("UPDATE turns SET body=? WHERE session='session'", (e.seal({"prompt": "changed"}),))
        elif change == "source":
            db.execute("INSERT INTO sources VALUES('s','session','other',?)", (e.seal({"analysis_complete": False}),))
        elif change == "legacy":
            context.pop("forward_revalidation")
        elif change == "semantic":
            context["policy_trace"]["routing"] = "SEMANTIC"
        elif change == "unknown":
            db.execute("UPDATE calls SET state='UNKNOWN' WHERE id='call'")
        elif change in ("connection", "session"):
            db.execute("UPDATE expiry SET deadline=? WHERE kind=?", (clock.now - 1, change))
        elif change == "analysis_stop":
            db.execute("INSERT INTO analysis_stops VALUES(?,?,?)", (digest("session"), digest("turn"), "{}"))
        db.execute("UPDATE calls SET reason=? WHERE id='call'", (canonical(context),))
    with pytest.raises(Rejected):
        e.forward("machine", "call", connection_token="connection")
    assert e.history()[0]["state"] != "EXECUTING"


def test_concurrent_same_call_gets_one_reservation(prepared):
    e, clock, _ = prepared
    clock.now += 91
    def forward():
        try:
            return e.forward("machine", "call")["state"]
        except Rejected as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=8) as pool:
        states = list(pool.map(lambda _: forward(), range(8)))
    assert states.count("EXECUTING") == 1
    assert states.count("FORWARD_REPLAY") == 7


def test_unknown_predecessor_blocks_revalidation(prepared):
    e, clock, _ = prepared
    clock.now += 91
    with e.db() as db:
        db.execute("INSERT INTO calls SELECT 'old',session,turn,hash,path,'UNKNOWN',decision,reason,body,created FROM calls WHERE id='call'")
    with pytest.raises(Rejected, match="PRIOR_RESULT_UNOBSERVED"):
        e.forward("machine", "call")


def test_semantic_allow_and_confirm_do_not_renew_expired_analysis(prepared):
    e, clock, _ = prepared
    original = json.loads(e.history()[0]["reason"])
    clock.now += 91
    original["policy_trace"]["routing"] = "SEMANTIC"
    with e.db() as db:
        db.execute("UPDATE calls SET reason=? WHERE id='call'", (canonical(original),))
    with pytest.raises(Rejected, match="FORWARD_SNAPSHOT_STALE"):
        e.forward("machine", "call")
    with e.db() as db:
        db.execute("UPDATE calls SET state='CONFIRM',decision='CONFIRM' WHERE id='call'")
    e.approval("machine", "call", True)
    with pytest.raises(Rejected, match="APPROVAL_SNAPSHOT_STALE"):
        e.consume_approval("machine", "call", original["action_hash"])
    with e.db() as db:
        assert db.execute("SELECT consumed FROM approvals WHERE call='call'").fetchone()[0] == 0
    assert json.loads(e.history()[0]["reason"])["analyzed_at"] == original["analyzed_at"]


def test_authz_correlated_staleness_diagnostic_is_from_control(prepared):
    e, clock, args = prepared
    clock.now += 91
    with e.db() as db:
        ctx = json.loads(db.execute("SELECT reason FROM calls WHERE id='call'").fetchone()[0])
        ctx.pop("forward_revalidation")
        db.execute("UPDATE calls SET reason=? WHERE id='call'", (canonical(ctx),))
    app = create_app(e, {"machine": "trusted", "machine_id": "machine", "ticket": lambda *_: "ticket"})
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "read_file", "arguments": args}}
    request_id = "a" * 32
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://control") as c:
            rejected = await c.post("/authz", json=body, headers={"Authorization": "Bearer connection", "x-with-human-request": request_id})
            assert rejected.status_code == 403 and rejected.json()["code"] == "FORWARD_SNAPSHOT_STALE"
            query = {"connection": "connection", "request_id": request_id, "tool": "read_file", "args": args}
            response = await c.post("/transport-rejection", json=query, headers={"Authorization": "Bearer trusted"})
            assert response.json() == {"origin": "CONTROL", "reason": "FORWARD_SNAPSHOT_STALE", "call_ref": digest("call")}
            # Changed request, token or actual args cannot borrow that diagnosis.
            for changed in ({"request_id": "b" * 32}, {"connection": "other"}, {"args": {"path": "other.txt"}}):
                r = await c.post("/transport-rejection", json={**query, **changed}, headers={"Authorization": "Bearer trusted"})
                assert r.json()["origin"] == "UNCONFIRMED"
            # Diagnosis does not turn the unforwarded READY into success or UNKNOWN.
            assert e.history()[0]["state"] == "READY"
    asyncio.run(run())
    with e.db() as db:
        assert db.execute("SELECT call FROM audit WHERE kind='REJECT'").fetchone()[0] == "call"


@pytest.mark.parametrize("receipt,expected", [
    ({"origin": "CONTROL", "reason": "FORWARD_SNAPSHOT_STALE", "call_ref": "a" * 64}, "CONTROL_FRESHNESS_REJECTED"),
    ({"origin": "CONTROL", "reason": "CONNECTION_OR_SESSION_EXPIRED", "call_ref": None}, "CONTROL_AUTHENTICATION_REJECTED"),
    ({"origin": "CONTROL", "reason": "PRIOR_RESULT_UNOBSERVED", "call_ref": "a" * 64}, "CONTROL_POLICY_OR_STATE_REJECTED"),
    ({"origin": "upstream", "reason": "FORWARD_SNAPSHOT_STALE", "call_ref": None}, "HTTP_REJECTION_UNCLASSIFIED"),
    ({"origin": "CONTROL", "reason": "arbitrary secret", "call_ref": None}, "HTTP_REJECTION_UNCLASSIFIED"),
    ({"origin": "CONTROL", "reason": "FORWARD_SNAPSHOT_STALE", "call_ref": "secret"}, "HTTP_REJECTION_UNCLASSIFIED"),
])
def test_bridge_only_exports_fixed_control_reason_and_hash(monkeypatch, receipt, expected):
    spec = importlib.util.spec_from_file_location("wait_bridge", Path(__file__).resolve().parents[2] / "tools/hookgw_mcp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "send", lambda *_: receipt)
    result = mod.trusted_rejection(Path("unused"), "token", "a" * 32, {"method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "notes.txt"}}})
    assert result["code"] == expected
    assert "secret" not in canonical(result)
