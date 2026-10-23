"""Offline stand-in for the `claude` CLI stream-json contract; no model or network.

The script is read from $CLAUDE_CONFIG_DIR/fake-script.json because the actor
passes only an allowlisted environment. Tool calls really go through the
loopback MCP bridge named in --mcp-config.
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx

LOGGED_IN = {
    "loggedIn": True,
    "authMethod": "claude.ai",
    "apiProvider": "firstParty",
    "email": "fixture@example.invalid",
    "subscriptionType": "max",
}


def emit(value):
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()


def option(argv, name):
    return argv[argv.index(name) + 1]


def main(argv):
    home = Path(os.environ["CLAUDE_CONFIG_DIR"])
    path = home / "fake-script.json"
    script = json.loads(path.read_text()) if path.exists() else {}
    if argv == ["--version"]:
        print(script.get("version", "2.1.308") + " (Claude Code)")
        return 0
    if argv == ["auth", "status", "--json"]:
        print(json.dumps(script.get("auth", LOGGED_IN)))
        return 0
    (home / "fake-invocation.json").write_text(
        json.dumps({"argv": argv, "env": dict(os.environ), "cwd": os.getcwd()})
    )
    servers = json.loads(Path(option(argv, "--mcp-config")).read_text())["mcpServers"]
    client = httpx.Client(trust_env=False, timeout=10)

    def rpc(server, method, params):
        response = client.post(
            servers[server]["url"],
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers=servers[server]["headers"],
        )
        response.raise_for_status()
        return response.json()["result"]

    tools = list(script.get("extra_tools", []))
    for server in servers:
        rpc(server, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        tools += ["mcp__%s__%s" % (server, t["name"]) for t in rpc(server, "tools/list", {})["tools"]]
    turn = 0
    for line in sys.stdin:
        json.loads(line)
        emit(
            {
                "type": "system",
                "subtype": "init",
                "apiKeySource": script.get("api_key_source", "none"),
                "claude_code_version": script.get("init_version", "2.1.308"),
                "tools": tools,
                "mcp_servers": [{"name": s, "status": "connected"} for s in servers],
                "model": script.get("init_model", option(argv, "--model")),
                "permissionMode": option(argv, "--permission-mode"),
                "plugins": script.get("plugins", [{"name": "cc-plugin-agents-md", "path": "builtin"}]),
            }
        )
        if script.get("malformed"):
            emit({"type": "assistant", "message": "not-an-object"})
        if script.get("overage"):
            emit({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "isUsingOverage": True}})
            continue
        if script.get("rate_limit"):
            # A rejected limit produces no model output, hence no tool call.
            emit({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}})
            emit(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": True,
                    "api_error_status": 429,
                    "result": "limit",
                }
            )
            continue
        outputs = []
        for call in (script.get("turns") or [[]])[turn]:
            emit(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "tool_use", "id": "toolu_%d" % len(outputs), "name": call["tool"]}
                        ]
                    },
                }
            )
            server, tool = call["tool"].split("__")[1:]
            outputs.append(rpc(server, "tools/call", {"name": tool, "arguments": call["args"]}))
        if script.get("hang"):
            time.sleep(60)
        emit(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": len(outputs) + 1,
                # "answer": a fixed final text (the consent simulator's decision).
                "result": script.get("answer", json.dumps(outputs)),
                "total_cost_usd": 0.01,
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "permission_denials": [],
            }
        )
        turn += 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
