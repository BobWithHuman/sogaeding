import asyncio
import importlib.util
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet

from app.common import canonical
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.semantic import span_catalog
from app.transparent.engine import Engine, Rejected
from app.transparent.server import create_app


class ObservationFixture:
    def __init__(self, mode="normal"):
        self.mode, self.calls, self.snapshot = mode, 0, None

    async def analyze(self, snapshot):
        self.calls += 1
        self.snapshot = snapshot
        if self.mode == "unavailable":
            raise AnalysisFailure("API_TIMEOUT", "A")
        rows = []
        for view in ("A", "B"):
            text = canonical(snapshot["candidate"])
            ref = {"source_id": "candidate", "start": 0, "end": min(len(text), 50), "quote": text[:50]}
            relation, use, reason = "DIRECT", "NONE", "USER_INTENT_SUPPORTED"
            if self.mode == "confirm":
                relation, reason = "UNCERTAIN", "SEMANTIC_UNCERTAIN"
            if view == "B" and snapshot["sources"]:
                source = snapshot["sources"][-1]
                quote = source["analysis_text"][:50]
                ref = {"source_id": source["source_id"], "start": 0, "end": len(quote), "quote": quote}
                relation, use, reason = "DATA_DEPENDENT", "TASK_DATA", "TASK_DATA_SUPPORTED"
                if self.mode == "attack":
                    use, reason = "NEW_INSTRUCTION", "EXTERNAL_INSTRUCTION_DEPENDENCY"
                if self.mode == "bad_quote":
                    ref["quote"] = "invented evidence"
            spans = span_catalog(snapshot, view)["spans"]
            sid = next(s["span_id"] for s in spans if s["source_id"] == ref["source_id"])
            if self.mode == "bad_quote" and view == "B" and snapshot["sources"]:
                sid = "s1B_" + "0" * 64
            rows.append({"task_relation": relation, "external_use": use, "reason": reason, "evidence_span_ids": [sid]})
        return rows


@pytest.fixture
def engine(tmp_path):
    grant = {"workspace": "C:\\repo", "tools": {"native": ["apply_patch"], "mcp": ["read_file", "write_file"]}, "protected_markers": [".env"]}
    key = Fernet.generate_key()
    e = Engine(tmp_path / "db.sqlite3", key, grant, ObservationFixture())
    e.test_key = key
    e.turn("machine", "session", "turn1", "Read the release and update normal code.", "C:\\repo")
    return e


def register(e, call="c1", path="mcp", tool="write_file", args=None, turn="turn1"):
    return e.register("machine", "session", turn, call, tool, args or {"path": "normal.txt", "content": "Release ready."}, path)


def authorize(e, call="c1"):
    return asyncio.run(e.authorize("machine", call))


def observe(e, call="c1", tool="write_file", args=None, text="Public release is ready."):
    e.transport_observed("machine", "session", tool, args or {"path": "normal.txt", "content": "Release ready."}, {"content": [{"type": "text", "text": text}]})
    return e.observe("machine", call, tool, args or {"path": "normal.txt", "content": "Release ready."}, text)


def seed(e):
    register(e, "read", tool="read_file", args={"path": "notes.txt"})
    assert authorize(e, "read")["state"] == "READY"
    e.forward("machine", "read")
    observe(e, "read", "read_file", {"path": "notes.txt"})


def test_normal_external_data_permitted_and_reserved_once(engine):
    seed(engine)
    register(engine)
    assert authorize(engine)["decision"] == "ALLOW"
    assert engine.judge.calls == 2
    engine.forward("machine", "c1")
    with pytest.raises(Rejected, match="FORWARD_REPLAY"):
        engine.forward("machine", "c1")
    assert engine.judge.calls == 2  # Hook + gateway do not duplicate analysis.
    assert observe(engine)["state"] == "OBSERVED"


def test_external_instruction_denied_not_approvable(engine):
    seed(engine)
    engine.judge.mode = "attack"
    register(engine)
    result = authorize(engine)
    assert result["decision"] == "DENY" and result["reasons"] == ["EXTERNAL_INSTRUCTION_DEPENDENCY"]
    with pytest.raises(Rejected):
        engine.approval("machine", "c1", True)
    with pytest.raises(Rejected):
        engine.forward("machine", "c1")


@pytest.mark.parametrize("mode,code", [("unavailable", "API_TIMEOUT"), ("bad_quote", "UNKNOWN_SPAN")])
def test_analysis_error_is_not_attack_pass(engine, mode, code):
    seed(engine)
    engine.judge.mode = mode
    register(engine)
    r = authorize(engine)
    assert r["decision"] == "DENY" and r["reasons"] == ["ANALYSIS_UNAVAILABLE"]
    assert r["diagnostic"][0]["code"] == code


def test_no_judge_fails_closed_with_specific_detail(engine):
    engine.judge = None
    register(engine)
    r = authorize(engine)
    assert r["diagnostic"][0]["code"] == "MISSING_API_KEY"


def test_hash_mutation_replay_and_source_forgery(engine):
    register(engine)
    authorize(engine)
    with pytest.raises(Rejected, match="NO_UNIQUE_HOOK_BINDING"):
        engine.pending_mcp("machine", "session", "write_file", {"path": "elsewhere.txt"})
    with pytest.raises(Rejected, match="CALL_REPLAY"):
        register(engine)
    with pytest.raises(Rejected, match="RESULT_BINDING"):
        observe(engine)
    engine.forward("machine", "c1")
    with pytest.raises(Rejected, match="RESULT_BINDING"):
        observe(engine, args={"path": "tamper.txt"})
    observe(engine)
    with pytest.raises(Rejected):
        observe(engine)


def test_subsequent_user_turn_and_stale_approval(engine):
    engine.judge.mode = "confirm"
    register(engine)
    assert authorize(engine)["decision"] == "CONFIRM"
    engine.approval("machine", "c1", True)
    engine.turn("machine", "session", "turn2", "Now only read the release.", "C:\\repo")
    with pytest.raises(Rejected, match="SESSION_OR_TURN"):
        engine.consume_approval("machine", "c1", register.__name__)
    register(engine, "next", tool="read_file", args={"path": "notes.txt"}, turn="turn2")
    authorize(engine, "next")
    assert "Now only read" in engine.judge.snapshot["user_request"]
    assert "Read the release" in engine.judge.snapshot["user_request"]


def test_turn_replay_cannot_replace_user_request(engine):
    with pytest.raises(Rejected, match="TURN_FORGERY"):
        engine.turn("machine", "session", "turn1", "Forged request", "C:\\repo")
    with pytest.raises(Rejected):
        engine.turn("other", "session", "turn2", "Request", "C:\\repo")


def test_confirm_exact_binding_consumed_once(engine):
    engine.judge.mode = "confirm"
    binding = register(engine)
    assert authorize(engine)["decision"] == "CONFIRM"
    engine.approval("machine", "c1", True)
    with pytest.raises(Rejected, match="APPROVAL_BINDING"):
        engine.consume_approval("machine", "c1", "bad-hash")
    engine.consume_approval("machine", "c1", binding["action_hash"])
    with pytest.raises(Rejected):
        engine.consume_approval("machine", "c1", binding["action_hash"])
    engine.forward("machine", "c1")


def test_concurrent_confirm_does_not_bypass_serial_reservation(engine):
    engine.judge.mode = "confirm"
    a = register(engine, "a")
    authorize(engine, "a")
    b = register(engine, "b")
    authorize(engine, "b")
    engine.approval("machine", "a", True)
    engine.approval("machine", "b", True)
    engine.consume_approval("machine", "a", a["action_hash"])
    with pytest.raises(Rejected, match="PRIOR_RESULT_UNOBSERVED"):
        engine.consume_approval("machine", "b", b["action_hash"])


def test_missing_post_result_blocks_next_and_restart_is_unknown(engine):
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    engine2 = Engine(engine.path, engine.test_key, engine.grant, engine.judge)
    assert engine2.history()[0]["state"] == "UNKNOWN"
    with pytest.raises(Rejected):
        engine2.forward("machine", "c1")
    register(engine2, "next")
    assert authorize(engine2, "next")["reasons"] == ["PRIOR_RESULT_UNOBSERVED"]


def test_source_missing_or_sensitive_not_silently_truncated(engine):
    register(engine)
    authorize(engine)
    engine.forward("machine", "c1")
    result = observe(engine, text="DEMO_SECRET_DO_NOT_SEND")
    assert not result["analysis_complete"]
    register(engine, "next")
    assert authorize(engine, "next")["reasons"] == ["SOURCE_CONTEXT_INCOMPLETE"]


def test_database_does_not_store_raw_request_or_source(engine):
    seed(engine)
    raw = Path(engine.path).read_bytes()
    assert b"Public release is ready" not in raw and b"Read the release" not in raw


def test_agent_cannot_write_user_event_and_gateway_metadata_precedes_turn(engine):
    keys = {"machine": "machine-key", "human": "human-key", "machine_id": "machine", "ticket": lambda *_: "test-only"}
    app = create_app(engine, keys)
    engine.connect("machine", "gateway-connection")
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://local") as client:
            r = await client.post("/event", headers={"Authorization": "Bearer gateway-connection"}, json={"event": "UserPromptSubmit"})
            assert r.status_code == 403
            r = await client.post("/authz", headers={"Authorization": "Bearer gateway-connection"}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            assert r.status_code == 200
            r = await client.post("/authz", headers={"Authorization": "Bearer gateway-connection"}, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "write_file", "arguments": {}}})
            assert r.status_code == 403
            r = await client.get("/history", headers={"Authorization": "Bearer machine-key"})
            assert r.status_code == 403
            r = await client.get("/history", headers={"Authorization": "Bearer human-key"})
            assert r.status_code == 200
    asyncio.run(run())


@pytest.mark.parametrize("tool,args", [
    ("Bash", {"command": "Set-Content -LiteralPath 'proof.txt' -Value 'x'", "workdir": "C:/Windows/Temp"}),
    ("Bash", {"command": "Get-Location; Remove-Item x"}),
    ("apply_patch", {"command": "*** Begin Patch\n*** Add File: tools/hookgw_hook.py\n+x\n*** End Patch"}),
    ("apply_patch", {"command": "*** Begin Patch\n*** Add File: ../outside.py\n+x\n*** End Patch"}),
])
def test_native_scope_rejects_cwd_tampering_and_adapter_changes(tool, args):
    spec = importlib.util.spec_from_file_location("hook_adapter", "/workspace/tools/hookgw_hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(ValueError):
        mod.native_scope(Path("/workspace"), tool, args)


def test_native_normal_file_edit_is_not_blanket_disabled():
    spec = importlib.util.spec_from_file_location("hook_adapter", "/workspace/tools/hookgw_hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.native_scope(Path("/workspace"), "apply_patch", {"command": "*** Begin Patch\n*** Add File: normal.py\n+print('ok')\n*** End Patch"})
