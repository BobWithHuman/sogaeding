"""Claude Code actor and loopback MCP bridge with an offline CLI stand-in."""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest

from app.benchmark.claude_code import (
    ActorStop,
    ClaudeCodeActor,
    actor_env,
    preflight,
    server_key,
)
from app.benchmark.mcp_bridge import STOPPED, BridgeStopped, LoopbackServer, bridge_app

TOKEN = "t" * 40
CATALOG = {
    "os_filesystem": [
        {
            "name": "read_file",
            "description": "Read a file",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
        {"name": "list_directory", "description": "List", "inputSchema": {"type": "object"}},
    ]
}
EXPECTED = {"mcp__os_filesystem__read_file", "mcp__os_filesystem__list_directory"}


def fake_binary(tmp_path):
    path = tmp_path / "bin" / "claude"
    path.parent.mkdir()
    module = Path(__file__).with_name("fake_claude.py")
    path.write_text(
        "#!%s\nimport runpy, sys\nsys.argv[0] = %r\nrunpy.run_path(%r, run_name='__main__')\n"
        % (sys.executable, str(path), str(module))
    )
    path.chmod(0o755)
    return path


def home(tmp_path, script=None):
    path = tmp_path / "claude-home"
    path.mkdir()
    if script is not None:
        (path / "fake-script.json").write_text(json.dumps(script))
    return path


def rpc(client, method, params=None, *, server="os_filesystem", rid=1, headers=None):
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if rid is not None:
        body["id"] = rid
    return client.post(
        "/%s/mcp" % server,
        json=body,
        headers={"Authorization": "Bearer " + TOKEN, **(headers or {})},
    )


async def with_bridge(dispatch, scenario, *, ready=True):
    app = bridge_app(CATALOG, TOKEN, dispatch, ready_seconds=0.2)
    if ready:
        app.state.ready.set()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        return await scenario(app, client)


def test_bridge_protocol_auth_and_exact_catalog():
    calls = []

    async def dispatch(server, tool, args):
        calls.append((server, tool, args))
        return {"content": [{"type": "text", "text": "ok"}]}

    async def scenario(app, client):
        assert (
            await client.post("/os_filesystem/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        ).status_code == 401
        assert (await rpc(client, "ping", headers={"Origin": "http://evil.example"})).status_code == 403
        assert (await rpc(client, "ping", headers={"Origin": "http://localhost:3000"})).status_code == 200
        assert (await rpc(client, "ping", server="other")).status_code == 404
        assert (await client.get("/os_filesystem/mcp")).status_code == 405
        init = (await rpc(client, "initialize", {"protocolVersion": "2025-06-18"})).json()
        assert init["result"]["protocolVersion"] == "2025-06-18"
        init = (await rpc(client, "initialize", {"protocolVersion": "1999-01-01"})).json()
        assert init["result"]["protocolVersion"] == "2025-11-25"
        assert (await rpc(client, "notifications/initialized", rid=None)).status_code == 202
        listed = (await rpc(client, "tools/list")).json()["result"]["tools"]
        assert listed == CATALOG["os_filesystem"]
        unknown = (await rpc(client, "tools/call", {"name": "write_file", "arguments": {}})).json()
        assert unknown["error"]["code"] == -32602
        bad = (await rpc(client, "tools/call", {"name": "read_file", "arguments": []})).json()
        assert bad["error"]["code"] == -32602
        dup = await client.post(
            "/os_filesystem/mcp",
            content=b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={"Authorization": "Bearer " + TOKEN},
        )
        assert dup.json()["error"]["code"] == -32700
        big = await client.post(
            "/os_filesystem/mcp",
            content=b" " * (1048576 + 1),
            headers={"Authorization": "Bearer " + TOKEN},
        )
        assert big.status_code == 413
        ok = (await rpc(client, "tools/call", {"name": "read_file", "arguments": {"path": "/a"}})).json()
        assert ok["result"]["content"][0]["text"] == "ok"
        assert app.state.calls == 1

    asyncio.run(with_bridge(dispatch, scenario))
    assert calls == [("os_filesystem", "read_file", {"path": "/a"})]


@pytest.mark.parametrize(
    "raised, code",
    [(BridgeStopped("CONFIRM_UNAPPROVED"), "CONFIRM_UNAPPROVED"), (KeyError("x"), "BRIDGE_DISPATCH_KeyError")],
)
def test_bridge_stop_fails_closed_and_never_dispatches_again(raised, code):
    calls = []

    async def dispatch(server, tool, args):
        calls.append(tool)
        raise raised

    async def scenario(app, client):
        params = {"name": "read_file", "arguments": {"path": "/a"}}
        first = (await rpc(client, "tools/call", params)).json()["result"]
        second = (await rpc(client, "tools/call", params)).json()["result"]
        assert first == second == STOPPED
        assert app.state.stopped.is_set() and app.state.stop_code == code

    asyncio.run(with_bridge(dispatch, scenario))
    assert calls == ["read_file"]


def test_bridge_never_dispatches_before_actor_ready():
    calls = []

    async def dispatch(server, tool, args):
        calls.append(tool)
        return {"content": []}

    async def scenario(app, client):
        params = {"name": "read_file", "arguments": {"path": "/a"}}
        assert (await rpc(client, "tools/call", params)).json()["result"] == STOPPED
        assert app.state.stop_code == "BRIDGE_ACTOR_NOT_READY"
        app.state.ready.set()
        assert (await rpc(client, "tools/call", params)).json()["result"] == STOPPED

    asyncio.run(with_bridge(dispatch, scenario, ready=False))
    assert calls == []


def test_bridge_requires_strong_token():
    with pytest.raises(ValueError, match="BRIDGE_TOKEN_REQUIRED"):
        bridge_app(CATALOG, "short", None)


def test_actor_env_drops_api_keys_and_providers():
    parent = {
        "HOME": "/h",
        "PATH": "/opt/evil:/usr/bin",
        "ANTHROPIC_API_KEY": "sk-ant-x",
        "ANTHROPIC_AUTH_TOKEN": "x",
        "ANTHROPIC_BASE_URL": "https://proxy.invalid",
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDE_CODE_OAUTH_TOKEN": "x",
        "HTTPS_PROXY": "http://proxy.invalid",
    }
    env = actor_env("/cfg", parent)
    assert env["HOME"] == "/h" and env["CLAUDE_CONFIG_DIR"] == "/cfg"
    assert env["PATH"] == "/usr/bin:/bin"
    assert not {k for k in env if k.startswith(("ANTHROPIC", "AWS")) or "PROXY" in k}
    assert "CLAUDE_CODE_USE_BEDROCK" not in env and "CLAUDE_CODE_OAUTH_TOKEN" not in env


def test_model_match_allows_only_dated_snapshot_of_same_id():
    from app.benchmark.claude_code import command, same_model

    assert same_model("claude-haiku-4-5", "claude-haiku-4-5")
    assert same_model("claude-haiku-4-5-20251001", "claude-haiku-4-5")
    assert not same_model("claude-haiku-5-5", "claude-haiku-4-5")
    assert not same_model("claude-haiku-4-5-extra", "claude-haiku-4-5")
    assert not same_model(None, "claude-haiku-4-5")
    argv = command("/c", model="claude-haiku-4-5", effort=None, system_prompt="s", mcp_config_file="/m", servers={"x": 1})
    assert "--effort" not in argv
    argv = command("/c", model="m", effort="low", system_prompt="s", mcp_config_file="/m", servers={"x": 1})
    assert argv[argv.index("--effort") + 1] == "low"


def test_server_key_is_identifier():
    assert server_key("OS-filesystem") == "os_filesystem"
    with pytest.raises(ValueError):
        server_key("--")


@pytest.mark.parametrize(
    "auth",
    [
        {"loggedIn": False, "authMethod": "none", "apiProvider": "firstParty"},
        {"loggedIn": True, "authMethod": "api_key", "apiProvider": "firstParty"},
        {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "bedrock", "subscriptionType": "max"},
        {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "free"},
    ],
)
def test_preflight_requires_subscription_login(tmp_path, auth):
    with pytest.raises(ActorStop, match="CLAUDE_SUBSCRIPTION_LOGIN_REQUIRED"):
        asyncio.run(preflight(fake_binary(tmp_path), home(tmp_path, {"auth": auth})))


def test_preflight_keeps_no_account_identity(tmp_path):
    login = asyncio.run(preflight(fake_binary(tmp_path), home(tmp_path, {})))
    assert login["version"] == "2.1.308" and login["subscription"] == "max"
    assert "fixture@example.invalid" not in json.dumps(login)


def run_actor(tmp_path, script, prompts, *, dispatch=None, seconds=20, monkeypatch=None):
    binary = fake_binary(tmp_path)
    config = home(tmp_path, script)
    work = tmp_path / "work"
    work.mkdir()
    events, calls = [], []

    async def default(server, tool, args):
        calls.append((server, tool, args))
        return {"content": [{"type": "text", "text": "content of " + args.get("path", "")}]}

    async def main():
        login = await preflight(binary, config)
        app = bridge_app(CATALOG, TOKEN, dispatch or default)
        async with LoopbackServer(app) as server:
            actor = ClaudeCodeActor(
                login,
                config,
                work,
                model="claude-sonnet-5-5",
                effort="low",
                system_prompt="DTAP system prompt",
                urls={s: server.url(s) for s in CATALOG},
                token=TOKEN,
                expected_tools=EXPECTED,
                record=events.append,
                deadline=time.monotonic() + seconds,
                ready=app.state.ready,
                stopped=app.state.stopped,
                expected_model="claude-sonnet-5-5",
            )
            await actor.start()
            outputs = []
            try:
                for prompt in prompts:
                    outputs.append(await actor.turn(prompt))
            except ActorStop as stop:
                outputs.append(stop)
            finally:
                await actor.close()
            return outputs, actor, app

    outputs, actor, app = asyncio.run(main())
    invocation = json.loads((config / "fake-invocation.json").read_text())
    return outputs, actor, app, events, calls, invocation


def test_actor_runs_isolated_headless_multi_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-must-not-pass")
    script = {
        "turns": [
            [{"tool": "mcp__os_filesystem__read_file", "args": {"path": "/a"}}],
            [{"tool": "mcp__os_filesystem__list_directory", "args": {"path": "/"}}],
        ]
    }
    outputs, actor, app, events, calls, invocation = run_actor(tmp_path, script, ["one", "two"])
    assert [json.loads(o)[0]["content"][0]["text"] for o in outputs] == ["content of /a", "content of /"]
    assert calls == [
        ("os_filesystem", "read_file", {"path": "/a"}),
        ("os_filesystem", "list_directory", {"path": "/"}),
    ]
    argv = invocation["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert {"--strict-mcp-config", "--no-session-persistence", "-p"} <= set(argv)
    assert argv[argv.index("--permission-prompts") + 1] == "none"
    assert argv[argv.index("--allowedTools") + 1] == "mcp__os_filesystem"
    assert argv[argv.index("--system-prompt") + 1] == "DTAP system prompt"
    assert TOKEN not in " ".join(argv)
    assert "ANTHROPIC_API_KEY" not in invocation["env"]
    assert invocation["cwd"] == "/"  # neutral: no host temp path reaches the model
    kinds = [e["kind"] for e in events]
    assert kinds.count("actor_init") == 2 and kinds.count("actor_result") == 2
    assert "actor_stop" not in kinds and actor.proc.returncode == 0


@pytest.mark.parametrize(
    "script, code",
    [
        ({"api_key_source": "ANTHROPIC_API_KEY"}, "CLAUDE_API_KEY_IN_USE_FORBIDDEN"),
        ({"extra_tools": ["Bash"]}, "ACTOR_TOOLSET_MISMATCH"),
        ({"init_version": "2.1.309"}, "CLAUDE_CODE_VERSION_CHANGED"),
        ({"rate_limit": True}, "SUBSCRIPTION_RATE_LIMITED"),
        ({"init_model": "claude-opus-5-5"}, "ACTOR_MODEL_MISMATCH"),
        ({"overage": True}, "SUBSCRIPTION_OVERAGE_IN_USE"),
        ({"malformed": True}, "ACTOR_STREAM_INVALID"),
        ({"plugins": [{"name": "personal-hooks", "path": "/Users/x/.claude/plugins/p"}]}, "ACTOR_CONFIG_NOT_ISOLATED"),
        ({"plugins": [{"name": "cc-plugin-agents-md", "path": "/tmp/fake"}]}, "ACTOR_CONFIG_NOT_ISOLATED"),
    ],
)
def test_actor_guard_stops_without_dispatch(tmp_path, script, code):
    script["turns"] = [[{"tool": "mcp__os_filesystem__read_file", "args": {"path": "/a"}}]]
    outputs, actor, app, events, calls, _ = run_actor(tmp_path, script, ["one"])
    assert isinstance(outputs[-1], ActorStop) and str(outputs[-1]) == code
    assert calls == [] and app.state.stopped.is_set()
    assert actor.proc.returncode is not None


def test_bridge_stop_terminates_actor(tmp_path):
    async def confirm(server, tool, args):
        raise BridgeStopped("CONFIRM_UNAPPROVED")

    script = {
        "turns": [[{"tool": "mcp__os_filesystem__read_file", "args": {"path": "/a"}}]],
        "hang": True,
    }
    started = time.monotonic()
    outputs, actor, app, events, _, _ = run_actor(tmp_path, script, ["one"], dispatch=confirm)
    assert str(outputs[-1]) == "BRIDGE_STOPPED" and app.state.stop_code == "CONFIRM_UNAPPROVED"
    assert actor.proc.returncode is not None and time.monotonic() - started < 30


def test_actor_deadline_kills_process(tmp_path):
    outputs, actor, _, _, _, _ = run_actor(tmp_path, {"hang": True}, ["one"], seconds=2)
    assert str(outputs[-1]) == "ACTOR_TIMEOUT" and actor.proc.returncode is not None
