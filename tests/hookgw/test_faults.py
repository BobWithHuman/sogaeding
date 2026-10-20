import asyncio
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_engine import authorize, observe, register

from app.common import canonical
from app.transparent.engine import Engine, Rejected
from app.transparent.upstream import create_app, open_file

pytest_plugins = ["test_engine"]


def test_unknown_error_observation_never_releases_reservation(engine):
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    # No trusted bridge success attestation, even if a Post hook exists.
    result = engine.observe("machine", "c1", "write_file", {"path": "normal.txt", "content": "Release ready."}, {"error": "lost response"})
    assert result["state"] == "UNKNOWN"
    register(engine, "next")
    assert authorize(engine, "next")["reasons"] == ["PRIOR_RESULT_UNOBSERVED"]
    with pytest.raises(Rejected):
        engine.purge("session")


def test_untyped_native_write_completion_is_unknown(engine):
    values = {"command": "*** Begin Patch\n*** Add File: normal.py\n+x\n*** End Patch"}
    register(engine, path="native", tool="apply_patch", args=values)
    assert authorize(engine)["state"] == "EXECUTING"
    assert engine.observe("machine", "c1", "apply_patch", values, "some textual output")["state"] == "UNKNOWN"


def test_grant_change_revokes_ready_and_approval_without_resetting_db(engine):
    register(engine)
    authorize(engine)
    changed = {**engine.grant, "protected_markers": [".env", "normal.txt"]}
    updated = Engine(engine.path, engine.test_key, changed, engine.judge)
    assert updated.history()[0]["state"] == "DENIED"
    with pytest.raises(Rejected):
        updated.forward("machine", "c1")


def test_transport_error_after_attestation_still_unknown(engine):
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    engine.transport_observed("machine", "session", "write_file", {"path": "normal.txt", "content": "Release ready."}, {"content": []})
    engine.transport_failure("machine", "session", "write_file", {"path": "normal.txt", "content": "Release ready."})
    assert engine.history()[0]["state"] == "UNKNOWN"
    with pytest.raises(Rejected):
        observe(engine)


def test_two_forward_contenders_reserve_exactly_once(engine):
    register(engine)
    authorize(engine)
    def contender():
        try:
            engine.forward("machine", "c1")
            return True
        except Rejected:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: contender(), range(2)))
    assert sum(results) == 1


def test_cas_state_loss_never_returns_allow(engine):
    class StateLoss:
        async def analyze(self, snapshot):
            with engine.db() as db:
                db.execute("UPDATE calls SET state='UNKNOWN' WHERE id='c1'")
            from test_engine import ObservationFixture
            return await ObservationFixture().analyze(snapshot)
    engine.judge = StateLoss()
    register(engine)
    with pytest.raises(Rejected, match="RESERVATION_LOST"):
        authorize(engine)
    assert engine.history()[0]["state"] == "UNKNOWN"


def test_expiry_and_logical_erasure_retain_unknown_tombstone(engine):
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    Engine(engine.path, engine.test_key, engine.grant, engine.judge)
    with engine.db() as db:
        db.execute("UPDATE expiry SET deadline=? WHERE kind='session'", (time.time() - 8 * 86400,))
    fresh = Engine(engine.path, engine.test_key, engine.grant, engine.judge)
    assert fresh.history() == []
    fresh.turn("machine", "session", "newturn", "A fresh actual user request", "C:\\repo")
    with pytest.raises(Rejected, match="CALL_REPLAY"):
        register(fresh, turn="newturn")


def test_closed_session_purge_revokes_connections_and_sources(engine):
    engine.connect("machine", "connection")
    engine.connection("connection", "session")
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    observe(engine)
    engine.purge("session")
    with pytest.raises(Rejected):
        engine.connection("connection")
    assert engine.history() == []


@pytest.mark.parametrize("name", ["../outside", ".env", "docs/plans/edit.md", "tools/hookgw_hook.py", "docs/handoffs/old/evidence.md"])
def test_upstream_scope_rejects_protected_paths(tmp_path, name):
    with pytest.raises((ValueError, OSError)):
        open_file(tmp_path, name, True)


def test_upstream_symlink_hardlink_and_nonregular_rejected_before_truncate(tmp_path):
    secret = tmp_path.parent / "outside.txt"
    secret.write_text("preserve")
    (tmp_path / "link.txt").symlink_to(secret)
    os.link(secret, tmp_path / "hard.txt")
    (tmp_path / "directory").mkdir()
    for name in ("link.txt", "hard.txt", "directory"):
        with pytest.raises((ValueError, OSError)):
            open_file(tmp_path, name, True)
    assert secret.read_text() == "preserve"


def test_real_file_write_then_lost_ack_is_not_exactly_once_receipt(tmp_path, monkeypatch):
    root = tmp_path / "files"
    root.mkdir()
    app = create_app(root, str(tmp_path / "attempts.db"), "synthetic-key")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "write_file", "arguments": {"path": "effect.txt", "content": "effect before acknowledgement"}}}
    raw = json.dumps(payload).encode()
    claim = canonical({"call": "call-1", "hash": hashlib.sha256(raw).hexdigest(), "expires": int(time.time()) + 30})
    proof = base64.urlsafe_b64encode(claim.encode()).decode()
    sig = hmac.new(b"synthetic-key", proof.encode(), hashlib.sha256).hexdigest()
    def lost(_fd):
        raise OSError("synthetic post-effect failure")
    monkeypatch.setattr(os, "fsync", lost)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://private") as client:
            headers = {"x-with-human-forward": proof + "." + sig}
            r = await client.post("/mcp", content=raw, headers=headers)
            assert r.status_code == 403
            assert (root / "effect.txt").read_text() == "effect before acknowledgement"
            r = await client.post("/mcp", content=raw, headers=headers)
            assert r.status_code == 403
    asyncio.run(run())


def test_launch_rejects_existing_hooks_without_disclosing_settings(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text('[hooks]\nUserPromptSubmit=[]\n')
    monkeypatch.setenv("CODEX_HOME", str(home))
    spec = importlib.util.spec_from_file_location("launcher", "/workspace/tools/hookgw_launch.py")
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0, "/workspace/tools")
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit, match="reviewed merge"):
        mod.check_conflicts(tmp_path, [])


@pytest.mark.parametrize("argument", ["-cfeatures.hooks=false", "-C..", "-pother", "-sdanger-full-access", "--dangerously-bypass-approvals-and-sandbox"])
def test_launch_rejects_attached_security_flags(tmp_path, monkeypatch, argument):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "unused-home"))
    spec = importlib.util.spec_from_file_location("launcher", "/workspace/tools/hookgw_launch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit, match="separate review"):
        mod.check_conflicts(tmp_path, [argument])


def test_isolated_adapter_startup_ignores_workspace_import_shadow(tmp_path):
    import shutil
    import subprocess
    import sys
    for name in ("hookgw_hook.py", "hookgw_mcp.py", "hookgw_launch.py"):
        shutil.copyfile("/workspace/tools/" + name, tmp_path / name)
    (tmp_path / "json.py").write_text("raise RuntimeError('untrusted shadow was imported')")
    (tmp_path / "sitecustomize.py").write_text("raise RuntimeError('untrusted startup was imported')")
    for name in ("hookgw_hook.py", "hookgw_mcp.py", "hookgw_launch.py"):
        result = subprocess.run([sys.executable, "-I", str(tmp_path / name), "--help"], cwd=tmp_path,
                                capture_output=True, timeout=5, check=False)
        assert result.returncode == 0 and b"usage:" in result.stdout
