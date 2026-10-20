"""Official HookManager integration; only the gateway dispatch executes tools."""

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4


class Stopped(RuntimeError):
    pass


def official_hook_module(path, expected_sha256):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("OFFICIAL_HOOK_SOURCE_CHANGED")
    config = path.parents[1] / "hooks/hooks.json"
    # Avoid the official soft loader importing arbitrary additional hooks.
    # Our required hook is explicit; its configuration must be a valid empty
    # pinned upstream auto-hook list, rather than a missing/broken loader.
    if not config.is_file() or json.loads(config.read_text()) != {"hooks": []}:
        raise ValueError("AUTO_HOOK_CONFIG_MISSING_OR_UNREVIEWED")
    spec = importlib.util.spec_from_file_location("dtap_pinned_hooks", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GatewayHook:
    def __init__(self, registry, control, gateway, machine_token, connection, session, turn, log):
        self.registry, self.control, self.gateway = registry, control, gateway
        self.machine_token, self.connection = machine_token, connection
        self.session, self.turn, self.log = session, turn, log
        self.calls = {}

    async def send(self, path, value):
        response = await self.control.post(
            path, json=value, headers={"Authorization": "Bearer " + self.machine_token}
        )
        response.raise_for_status()
        return response.json()

    async def on_pre_tool_call(self, ctx):
        self.registry.resolve(ctx.server, ctx.tool_name, ctx.arguments)
        call = str(uuid4())
        tool = self.registry.name(ctx.server, ctx.tool_name)
        args = copy.deepcopy(ctx.arguments)
        # IDs and context originate in the trusted driver, not model metadata.
        self.calls[id(ctx)] = {
            "call": call,
            "tool": tool,
            "args": args,
            "server": ctx.server,
            "name": ctx.tool_name,
            "forwarded": False,
        }
        result = await self.send(
            "/event",
            {
                "event": "PreToolUse",
                "connection": self.connection,
                "session": self.session,
                "turn": self.turn,
                "call": call,
                "tool": tool,
                "args": args,
                "route": "mcp",
            },
        )
        self.log(
            {
                "stage": "PRE",
                "call": call,
                "decision": result.get("decision"),
                "state": result.get("state"),
                "reasons": result.get("reasons", []),
                "upstream_invoked": False if result.get("decision") != "ALLOW" else None,
            }
        )
        if result.get("decision") != "ALLOW":
            # Pinned HookManager _run_pre is outside its dispatch try. Persist
            # here; a denied call intentionally has no Post callback.
            raise Stopped("DTAP_PRE_STOPPED")

    async def forward(self, ctx, args):
        binding = self.calls[id(ctx)]
        if (
            binding["forwarded"]
            or args != binding["args"]
            or ctx.server != binding["server"]
            or ctx.tool_name != binding["name"]
        ):
            raise Stopped("EXACT_ONE_SHOT_BINDING")
        binding["forwarded"] = True
        response = await self.gateway.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": binding["call"],
                "method": "tools/call",
                "params": {"name": binding["tool"], "arguments": args},
            },
            headers={
                "Authorization": "Bearer " + self.connection,
                "x-with-human-request": binding["call"],
            },
        )
        response.raise_for_status()
        result = response.json()["result"]
        await self.send(
            "/transport-observed",
            {
                "connection": self.connection,
                "tool": binding["tool"],
                "args": args,
                "result": result,
            },
        )
        return result

    async def on_post_tool_call(self, ctx, result):
        binding = self.calls[id(ctx)]
        if result.exception is not None or result.is_error:
            await self.send(
                "/transport-failure",
                {"connection": self.connection, "tool": binding["tool"], "args": binding["args"]},
            )
            self.log(
                {
                    "stage": "POST",
                    "call": binding["call"],
                    "state": "UNKNOWN",
                    "unsafe_retry": False,
                }
            )
            return
        observed = await self.send(
            "/event",
            {
                "event": "PostToolUse",
                "connection": self.connection,
                "session": self.session,
                "turn": self.turn,
                "call": binding["call"],
                "tool": binding["tool"],
                "args": binding["args"],
                "output": result.raw,
                "route": "mcp",
            },
        )
        self.log({"stage": "POST", "call": binding["call"], "state": observed.get("state"),
                  "analysis_complete": observed.get("analysis_complete")})
        if observed.get("state") == "OBSERVED" and observed.get("analysis_complete") is False:
            raise Stopped("SOURCE_CONTEXT_LIMIT_OBSERVED")


class GuardedDispatch:
    def __init__(self, module, hook):
        self.module, self.hook = module, hook
        self.manager = module.HookManager(hooks=[hook])
        if self.manager.hooks != [hook]:
            raise ValueError("HOOK_LOADER_NOT_EXACT")

    async def call(self, server, tool, args):
        if self.manager.hooks != [self.hook]:
            raise Stopped("REQUIRED_HOOK_MISSING")
        ctx = self.module.ToolCallContext(
            framework="with-human-responses-backend",
            server=server,
            tool_name=tool,
            arguments=copy.deepcopy(args),
        )
        return await self.manager.wrap(ctx, lambda bound: self.hook.forward(ctx, bound))
