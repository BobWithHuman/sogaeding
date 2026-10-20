"""Demo intent hook: host approval precedes the one fresh gateway judgment.

No PDP ALLOW is returned here. An empty hook reply preserves Codex's own host
approval policy; the gateway still requires a bound, unclaimed exact intent.
"""

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location("mvp_demo_base_hook", Path(__file__).with_name("hookgw_hook.py"))
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

_original_handle = core.handle


def handle(host, value, connection):
    event = value["hook_event_name"]
    if event != "PreToolUse":
        return _original_handle(host, value, connection)
    profile = core.guarded("WORKSPACE", lambda: json.loads((host / "profile.json").read_text(encoding="utf-8-sig")))
    root = core.guarded("WORKSPACE", lambda: Path(profile["workspace"]).resolve())
    if core.guarded("WORKSPACE", lambda: Path(value["cwd"]).resolve()) != root:
        raise core.HookFailure("WORKSPACE", "WORKSPACE_MISMATCH")
    prefix = "mcp__with_human__"
    if not value["tool_name"].startswith(prefix):
        return core.reply(event, False, "WITH_HUMAN_DEMO_REGISTERED_MCP_ONLY")
    request = {"event": event, "connection": connection, "session": value["session_id"], "turn": value["turn_id"],
               "call": value["session_id"] + ":" + value["tool_use_id"], "tool": value["tool_name"][len(prefix):],
               "args": value["tool_input"], "route": "mcp"}
    result = core.guarded("CONTROL_EVENT", lambda: core.send(host, "/demo/intent", request))
    if not isinstance(result, dict) or result.get("call") != request["call"] or result.get("intent") not in ("RECORDED_NOT_AUTHORIZED", "REJECTED", "EXISTING_PENDING", "EXISTING_TERMINAL"):
        raise core.HookFailure("CONTROL_EVENT", "RESPONSE_INVALID")
    if result["intent"] == "EXISTING_PENDING":
        if host.parts[-3:] in (("revisions", "hands-on-1", "host"),("revisions", "frozen-demo-1", "host")):
            return core.reply(event, False, "WITH_HUMAN_CONFIRM_PENDING: inspect hands-on history. This candidate has not executed; no repeated analysis or automatic approval.")
        return core.reply(event, False, "WITH_HUMAN_EXISTING_CONFIRM_PENDING: use the trusted scripts/mvp_confirm.ps1 terminal; the original MCP call waits. No repeated analysis.")
    if result["intent"] == "EXISTING_TERMINAL":
        return core.reply(event, False, "WITH_HUMAN_EXISTING_INTENT_STOPPED: inspect history; do not retry this candidate. A new actual user turn is required for a new task.")
    return core.reply(event, result["intent"] == "RECORDED_NOT_AUTHORIZED", "WITH_HUMAN_DEMO_INTENT_REJECTED")


def main():
    core.handle = handle
    return core.main()


if __name__ == "__main__":
    main()
