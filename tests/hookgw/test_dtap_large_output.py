"""Observe a complete large response; stop this task before partial-source analysis."""

import asyncio
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet
from test_engine import ObservationFixture

from app.benchmark.hook import GatewayHook, Stopped
from app.benchmark.proxy import MAX_MCP_RESPONSE_BYTES, rpc
from app.benchmark.runtime_continuation import inherited_snapshots
from app.benchmark.runtime_controller import Controller
from app.benchmark.runtime_policy import RuntimeEngine, SyntheticBoundary
from app.common import digest
from app.transparent.engine import Engine, Rejected
from app.transparent.server import create_app


@pytest.mark.parametrize("sse", [False, True])
def test_complete_155kb_result_is_observed_without_truncation(sse):
    value = {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "x" * 154716}]}}
    raw = json.dumps(value).encode()
    body = b"data: " + raw + b"\n\n" if sse else raw

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(
            200, content=body, headers={"content-type": "text/event-stream" if sse else "application/json"}
        ))) as client:
            actual, _ = await rpc(client, "https://synthetic/mcp", {"id": 3})
            assert actual == value
    asyncio.run(run())


def test_stream_limit_remains_bounded_and_sse_does_not_wait_for_connection_close():
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"jsonrpc":"2.0","id":3,"result":{}}\n\n'
            raise AssertionError("must stop at the matching complete event")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(
            200, stream=Stream(), headers={"content-type": "text/event-stream"}
        ))) as client:
            assert (await rpc(client, "https://synthetic/mcp", {"id": 3}))[0]["result"] == {}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(
            200, content=b"x" * (MAX_MCP_RESPONSE_BYTES + 1)
        ))) as client:
            with pytest.raises(ValueError, match="MCP_RESPONSE_LIMIT"):
                await rpc(client, "https://synthetic/mcp", {"id": 3})
    asyncio.run(run())


def test_product_limit_unchanged_benchmark_receipt_complete_but_source_incomplete(tmp_path):
    value = {"content": [{"type": "text", "text": "x" * 154716}]}
    with pytest.raises(Rejected, match="INPUT_LIMIT"):
        Engine.__new__(Engine).bound_output(value)
    guard = SyntheticBoundary(["SYNTHETIC-PROTECTED-BOUNDARY-ONLY"])
    grant = {"workspace": "C:\\repo", "tools": {"native": [], "mcp": ["read_file"]}, "protected_markers": []}
    engine = RuntimeEngine(tmp_path / "control.db", Fernet.generate_key(), grant, ObservationFixture(), boundary=guard)
    engine.turn("m", "s", "t", "Read notes.txt", "C:\\repo")
    args = {"path": "notes.txt"}
    engine.register("m", "s", "t", "c", "read_file", args, "mcp")
    assert asyncio.run(engine.authorize("m", "c"))["decision"] == "ALLOW"
    engine.forward("m", "c")
    connection = "SYNTHETIC-CONNECTION-FOR-HTTP-ONLY"
    engine.connect("m", connection)
    engine.connection(connection, "s")
    keys = {"machine_id": "m", "machine": "fixture-machine", "human": "fixture-human", "ticket": None}
    async def observe_http():
        payload = {"connection": connection, "tool": "read_file", "args": args, "result": value}
        headers = {"Authorization": "Bearer fixture-machine"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(create_app(engine, keys)), base_url="https://test") as client:
            assert (await client.post("/transport-observed", headers=headers, json=payload)).json()["code"] == "BODY_LIMIT"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(create_app(engine, keys, max_body_bytes=1114112)), base_url="https://test") as client:
            assert (await client.post("/transport-observed", headers=headers, json=payload)).status_code == 200
            response = await client.post("/event", headers=headers, json={
                "event": "PostToolUse", "connection": connection, "session": "s", "turn": "t", "call": "c",
                "tool": "read_file", "args": args, "output": value, "route": "mcp"})
            assert response.status_code == 200, response.text
            return response.json()
    observed = asyncio.run(observe_http())
    assert observed["state"] == "OBSERVED" and observed["analysis_complete"] is False
    with engine.db() as db:
        assert engine.open(db.execute("SELECT body FROM transport WHERE call='c'").fetchone()[0]) == value
        source = engine.open(db.execute("SELECT body FROM sources WHERE call='c'").fetchone()[0])
        assert source["analysis_text"] == "" and not source["analysis_complete"]


def test_post_context_limit_is_terminal_after_observation_not_unknown_or_deny():
    events = []
    hook = GatewayHook(None, None, None, "fake", "c", "s", "t", events.append)
    ctx = SimpleNamespace()
    hook.calls[id(ctx)] = {"call": "one", "tool": "read_file", "args": {}}
    async def send(_path, _value):
        return {"state": "OBSERVED", "analysis_complete": False}
    hook.send = send
    with pytest.raises(Stopped, match="SOURCE_CONTEXT_LIMIT_OBSERVED"):
        asyncio.run(hook.on_post_tool_call(ctx, SimpleNamespace(exception=None, is_error=False, raw={})))
    assert events == [{"stage": "POST", "call": "one", "state": "OBSERVED", "analysis_complete": False}]


def test_completed_off_task_keeps_identical_initial_image_for_new_on_arm(tmp_path):
    key = "official/case"
    folder = tmp_path / "snapshots" / digest(key)
    folder.mkdir(parents=True)
    ready = folder / "snapshot.json"
    ready.write_text(json.dumps({"image": "sha256:" + "a" * 64, "task_key": key,
                                 "original_setup_sha256": "setup"}))
    plan = {"manifest": {"task_keys": [key]}, "coverage": [{"task_key": key, "setup_sha256": "setup"}]}
    (tmp_path / "broker-data").mkdir()
    with sqlite3.connect(tmp_path / "broker-data/provider.sqlite3") as db:
        db.execute("CREATE TABLE jobs(task TEXT,arm TEXT,result TEXT)")
        db.execute("INSERT INTO jobs VALUES(?,?,?)", (key, "engine-off", json.dumps({"initial_snapshot": {"image": "sha256:" + "a" * 64}})))
    inherited = inherited_snapshots(tmp_path, plan)
    controller = Controller.__new__(Controller)
    controller.root = tmp_path
    controller.plan = {"manifest": {"continuation": {"inherited_initial_snapshots": inherited}}}
    controller.sandbox = SimpleNamespace(request=lambda method, path: {"Id": "sha256:" + "a" * 64})
    assert controller.initial_snapshot(key)["image"] == "sha256:" + "a" * 64
    assert inherited[key]["sha256"] == hashlib.sha256(ready.read_bytes()).hexdigest()
    ready.unlink()
    with pytest.raises(RuntimeError, match="NO_SETUP_REPLAY"):
        controller.initial_snapshot(key)
    with pytest.raises(Exception, match="PARENT_SEED_UNKNOWN"):
        inherited_snapshots(tmp_path, plan)
    folder.rmdir()
    with pytest.raises(Exception, match="INITIAL_SNAPSHOT_MISSING"):
        inherited_snapshots(tmp_path, plan)
