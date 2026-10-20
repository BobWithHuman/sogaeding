"""R-B-002 at exposed SPEC5 roles, independent durable audit and safe failures."""
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import httpx
from cryptography.fernet import Fernet

from app.storage.auth_audit import AuthAudit
from app.transparent.engine import Engine
from app.transparent.jev import JevClient
from app.transparent.jev_core_v5p1 import JevPolicyV5P1
from app.transparent.server import create_app, public_app
from app.transparent.upstream import create_app as upstream


def engine(tmp_path):
    key = Fernet.generate_key()
    e = Engine(tmp_path / "control.sqlite3", key, {"workspace": "C:\\repo", "tools": {"mcp": ["read_file", "write_file"]}}, policy_router=JevPolicyV5P1(JevClient()))
    e.test_storage_key = key
    return e


KEYS = {"machine_id": "m", "machine": "fixture-machine", "human": "fixture-human", "ticket": lambda *_: "not-a-real-ticket"}


def request(app, path, token=None, method="POST", body=None):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://control") as client:
            return await client.request(method, path, json=body, headers={"authorization": "Bearer " + token} if token else {})
    return asyncio.run(run())


def counts(path):
    with sqlite3.connect(path) as db:
        return dict(db.execute("SELECT surface,sum(count) FROM auth_failures GROUP BY surface"))


def test_wrong_missing_cross_role_agent_expiry_and_restart_are_persistent(tmp_path, monkeypatch):
    e = engine(tmp_path)
    app = create_app(e, KEYS)
    monkeypatch.setenv("HOOKGW_DEMO_VIEWER", "1")
    canary = "PRIVATE_AUTH_CANARY_NEVER_LOGGED"
    assert request(app, "/connect", canary, body={}).status_code == 403
    assert request(app, "/connect", KEYS["human"], body={}).status_code == 403
    assert request(app, "/demo/history", method="GET").status_code == 403
    assert request(app, "/authz", canary, body={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status_code == 403
    assert request(public_app(app), "/authz", body={}).status_code == 403
    path = str(e.path) + ".auth"
    assert counts(path) == {"SERVICE": 3, "HUMAN": 1, "AGENT": 1}
    # New Engine/app instances do not clear counters or required auth records.
    again = Engine(e.path, e.test_storage_key, e.grant, policy_router=JevPolicyV5P1(JevClient()))
    app2 = create_app(again, KEYS)
    assert request(app2, "/connect", canary, body={}).status_code == 403
    assert counts(path)["SERVICE"] == 4
    assert canary.encode() not in tmp_path.joinpath("control.sqlite3.auth").read_bytes()
    with again.db() as db:
        assert db.execute("SELECT count(*) FROM calls").fetchone()[0] == 0


def test_rate_limit_survives_app_restart_and_fails_closed_on_audit_failure(tmp_path, monkeypatch):
    e = engine(tmp_path)
    for _ in range(10):
        assert request(create_app(e, KEYS), "/connect", "wrong", body={}).status_code == 403
    with e.db() as db:
        db.execute("DELETE FROM audit")  # General/session audit eviction is not an auth-limit reset.
    e = Engine(e.path, e.test_storage_key, e.grant, policy_router=JevPolicyV5P1(JevClient()))
    assert request(create_app(e, KEYS), "/connect", KEYS["machine"], body={}).status_code == 403
    assert counts(str(e.path) + ".auth")["SERVICE"] == 11
    app = create_app(e, KEYS)
    monkeypatch.setattr(app.state.auth_audit, "record", lambda *_: (_ for _ in ()).throw(OSError("PRIVATE")))
    reply = request(app, "/connect", "wrong", body={})
    assert reply.status_code == 503 and "PRIVATE" not in reply.text
    with e.db() as db:
        assert db.execute("SELECT count(*) FROM connections").fetchone()[0] == 0


def test_aggregate_audit_is_atomic_and_retained_24h(tmp_path, monkeypatch):
    path = tmp_path / "auth.sqlite3"
    clock = [1000000.]
    monkeypatch.setattr("app.storage.auth_audit.time.time", lambda: clock[0])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: AuthAudit(path).record("AGENT", 403), range(40)))
    assert counts(path) == {"AGENT": 40}
    clock[0] += 86401
    AuthAudit(path).record("HUMAN", 403)
    assert counts(path) == {"HUMAN": 1}


def test_private_upstream_bad_ticket_durable_and_zero_effect(tmp_path, monkeypatch):
    files = tmp_path / "files"
    files.mkdir()
    ledger = tmp_path / "attempts.sqlite3"
    app = upstream(files, ledger, "fake-forward-key")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "write_file", "arguments": {"path": "bad.md", "content": "not written"}}}
    assert request(app, "/mcp", body=payload).status_code == 403
    assert counts(str(ledger) + ".auth") == {"SERVICE": 1}
    monkeypatch.setattr(app.state.auth_audit, "record", lambda *_: (_ for _ in ()).throw(OSError("PRIVATE")))
    assert request(app, "/mcp", body=payload).status_code == 503
    assert not (files / "bad.md").exists()
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
