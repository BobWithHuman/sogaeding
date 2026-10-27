"""Trusted project hook adapter. Stdlib only; no paid calls or raw event logs here.

Its explicit fail-closed reply does not cure Codex's fail-open handler crashes.
The same OS user's unrestricted processes are outside this trust boundary.
"""
import argparse
import json
import os
import re
import ssl
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

STAGES = {"INPUT_READ", "PARSE", "WORKSPACE", "NATIVE_SCOPE", "CONTROL_EVENT", "APPROVAL_POLL", "INTERNAL"}
SCOPE_CODES = {
    "SPECIAL_OR_HARDLINK_PATH", "SPECIAL_PATH_UNSUPPORTED", "PROTECTED_PATH",
    "TRUSTED_PRODUCT_OR_EVIDENCE", "UNSUPPORTED_NATIVE_ARGUMENTS", "PATCH_PATHS_REQUIRED",
    "UNSUPPORTED_SHELL_SYNTAX", "ABSOLUTE_SHELL_PATH_REQUIRED", "UNSUPPORTED_SHELL_COMMAND",
    "UNSUPPORTED_NATIVE_TOOL", "PATH_OUTSIDE_WORKSPACE",
}
CODES = SCOPE_CODES | {
    "EVENT_LIMIT", "INVALID_JSON", "EVENT_SCHEMA_INVALID", "UNSUPPORTED_HOOK_EVENT",
    "WORKSPACE_MISMATCH", "MISSING_CONNECTION", "LOCAL_TLS_REQUIRED", "TLS_ERROR",
    "HTTP_400", "HTTP_401", "HTTP_403", "HTTP_404", "HTTP_409", "HTTP_413",
    "HTTP_422", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504",
    "HTTP_ERROR", "HTTP_REDIRECT", "CONTROL_UNAVAILABLE", "CONTROL_TIMEOUT", "RESPONSE_INVALID", "ADAPTER_UNAVAILABLE",
}


class HookFailure(Exception):
    def __init__(self, stage, code):
        self.stage = stage if stage in STAGES else "INTERNAL"
        self.code = code if code in CODES else "ADAPTER_UNAVAILABLE"
        super().__init__(self.code)


def guarded(stage, operation):
    try:
        return operation()
    except HookFailure:
        raise
    except Exception as error:
        code = "ADAPTER_UNAVAILABLE"
        if isinstance(error, urllib.error.HTTPError):
            candidate = "HTTP_" + str(error.code)
            code = "HTTP_REDIRECT" if type(error.code) is int and 300 <= error.code <= 399 else candidate if candidate in CODES else "HTTP_ERROR"
        elif isinstance(error, ssl.SSLError) or isinstance(getattr(error, "reason", None), ssl.SSLError):
            code = "TLS_ERROR"
        elif isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError):
            code = "CONTROL_TIMEOUT"
        elif isinstance(error, urllib.error.URLError):
            code = "CONTROL_UNAVAILABLE"
        elif isinstance(error, json.JSONDecodeError):
            code = "INVALID_JSON" if stage == "PARSE" else "RESPONSE_INVALID"
        elif stage == "PARSE" and isinstance(error, (KeyError, TypeError, ValueError, UnicodeError)):
            code = "EVENT_SCHEMA_INVALID"
        elif isinstance(error, ValueError) and str(error) in SCOPE_CODES | {"WORKSPACE_MISMATCH", "LOCAL_TLS_REQUIRED"}:
            code = str(error)
        raise HookFailure(stage, code) from None


def event_value(value):
    if not isinstance(value, dict):
        raise HookFailure("PARSE", "EVENT_SCHEMA_INVALID")
    event = value.get("hook_event_name")
    if event not in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
        raise HookFailure("PARSE", "UNSUPPORTED_HOOK_EVENT")
    fields = ("session_id", "turn_id", "cwd") + (("prompt",) if event == "UserPromptSubmit" else ("tool_name", "tool_use_id"))
    if any(not isinstance(value.get(key), str) or not value[key] for key in fields):
        raise HookFailure("PARSE", "EVENT_SCHEMA_INVALID")
    if event != "UserPromptSubmit" and "tool_input" not in value:
        raise HookFailure("PARSE", "EVENT_SCHEMA_INVALID")
    if event == "PostToolUse" and "tool_response" not in value:
        raise HookFailure("PARSE", "EVENT_SCHEMA_INVALID")
    return value


def control_result(value, stage="CONTROL_EVENT"):
    if not isinstance(value, dict) or value.get("decision") not in ("ALLOW", "DENY", "CONFIRM", "ASK"):
        raise HookFailure(stage, "RESPONSE_INVALID")
    if stage == "CONTROL_EVENT" and value["decision"] == "CONFIRM" and not isinstance(value.get("action_hash"), str):
        raise HookFailure(stage, "RESPONSE_INVALID")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward event/Authorization to a control-supplied alternate location.
        return None


def send(host, endpoint, body, human=False, method="POST", timeout=25):
    context = ssl.create_default_context(cafile=str(host / "ca.pem"))
    token = (host / ("human.token" if human else "machine.token")).read_text().strip()
    base = json.loads((host / "profile.json").read_text(encoding="utf-8-sig"))["control_url"]
    if not base.startswith("https://127.0.0.1:"):
        raise ValueError("LOCAL_TLS_REQUIRED")
    data = json.dumps(body, ensure_ascii=False).encode() if method == "POST" else None
    req = urllib.request.Request(base + endpoint, data, {"Content-Type": "application/json", "Authorization": "Bearer " + token}, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context), NoRedirect())
    with opener.open(req, timeout=timeout) as response:
        return json.loads(response.read(131073))


def safe_path(root, name):
    path = Path(name)
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise ValueError("PATH_OUTSIDE_WORKSPACE") from None
    if resolved.exists():
        info = resolved.stat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)) or stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError("SPECIAL_OR_HARDLINK_PATH")
    # Resolve symlinks before checking; this is a hook scope check, not an OS sandbox.
    lowered = resolved.relative_to(root).as_posix().casefold()
    devices = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)), *("lpt" + str(i) for i in range(1, 10))}
    if ":" in lowered or any(part.rstrip(". ") != part or part.split(".")[0] in devices for part in Path(lowered).parts):
        raise ValueError("SPECIAL_PATH_UNSUPPORTED")
    if any(x.startswith(".") or x in ("artifacts", "references") for x in Path(lowered).parts):
        raise ValueError("PROTECTED_PATH")
    if lowered in ("agents.md", "harness/build_tasks.json") or lowered.startswith("docs/plans/"):
        raise ValueError("PROTECTED_PATH")
    if lowered.startswith(("docs/handoffs/", "src/app/", "agentgateway/", "tools/hookgw", "scripts/hookgw", "tools/mvp_", "scripts/mvp_", "compose.mvp-demo")) or lowered in ("compose.hookgw.yaml", "compose.hookgw.offline.yaml"):
        raise ValueError("TRUSTED_PRODUCT_OR_EVIDENCE")


def native_scope(root, tool, args):
    if not isinstance(args, dict) or set(args) - {"command"}:
        raise ValueError("UNSUPPORTED_NATIVE_ARGUMENTS")
    if tool == "apply_patch":
        patch = args.get("command", args.get("patch", "")) if isinstance(args, dict) else args
        paths = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
        if not paths:
            raise ValueError("PATCH_PATHS_REQUIRED")
        for path in paths:
            safe_path(root, path)
        return
    if tool == "Bash":
        cmd = args.get("command", "")
        # Supported shell subset; no interpretation of compound or interactive commands.
        if any(x in cmd for x in (";", "|", "&", "`", "$", ">", "<", "\n", "\r")):
            raise ValueError("UNSUPPORTED_SHELL_SYNTAX")
        if re.fullmatch(r"Get-Location\s*", cmd, re.I):
            return
        match = re.fullmatch(r"(?:Get-Content|Get-ChildItem)\s+-LiteralPath\s+'([^']+)'", cmd, re.I)
        if match:
            if not Path(match[1]).is_absolute():
                raise ValueError("ABSOLUTE_SHELL_PATH_REQUIRED")
            safe_path(root, match[1])
            return
        match = re.fullmatch(r"Set-Content\s+-LiteralPath\s+'([^']+)'\s+-Value\s+'([^']*)'", cmd, re.I)
        if match:
            if not Path(match[1]).is_absolute():
                raise ValueError("ABSOLUTE_SHELL_PATH_REQUIRED")
            safe_path(root, match[1])
            return
        raise ValueError("UNSUPPORTED_SHELL_COMMAND")
    # Other host tools need dedicated input/path semantics before enrollment.
    raise ValueError("UNSUPPORTED_NATIVE_TOOL")


def reply(event, allow, reason):
    if event == "PreToolUse":
        # No permissionDecision=allow: do not bypass Codex's own approval policy.
        return {} if allow else {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny", "permissionDecisionReason": reason}}
    if event == "UserPromptSubmit" and not allow:
        return {"decision": "block", "reason": reason}
    return {}


def handle(host, value, connection):
    event = value["hook_event_name"]
    profile = guarded("WORKSPACE", lambda: json.loads((host / "profile.json").read_text(encoding="utf-8-sig")))
    root = guarded("WORKSPACE", lambda: Path(profile["workspace"]).resolve())
    body = {"event": event, "connection": connection, "session": value["session_id"], "turn": value["turn_id"]}
    if guarded("WORKSPACE", lambda: Path(value["cwd"]).resolve()) != root:
        raise HookFailure("WORKSPACE", "WORKSPACE_MISMATCH")
    if event == "UserPromptSubmit":
        engine_workspace = str(root)
        if "engine_workspace" in profile:
            if (profile.get("format") != "product-codex-1" or profile["engine_workspace"] != "/files"
                    or profile.get("mcp_only") is not True):
                raise HookFailure("WORKSPACE", "WORKSPACE_MISMATCH")
            engine_workspace = profile["engine_workspace"]
        body.update(prompt=value["prompt"], cwd=engine_workspace)
        guarded("CONTROL_EVENT", lambda: send(host, "/event", body))
        return reply(event, True, "")
    original = value["tool_name"]
    tool, route = original, "native"
    prefix = "mcp__with_human__"
    if original.startswith(prefix):
        tool, route = original[len(prefix):], "mcp"
    args = value["tool_input"]
    if event == "PreToolUse" and route == "native":
        if profile.get("mcp_only") is True:
            raise HookFailure("NATIVE_SCOPE", "UNSUPPORTED_NATIVE_TOOL")
        guarded("NATIVE_SCOPE", lambda: native_scope(root, tool, args))
    body.update(call=value["session_id"] + ":" + value["tool_use_id"], tool=tool, args=args, route=route)
    if event == "PostToolUse":
        body.update(output=value["tool_response"], failed=value.get("is_error", False))
        guarded("CONTROL_EVENT", lambda: send(host, "/event", body))
        return {}
    result = guarded("CONTROL_EVENT", lambda: control_result(send(host, "/event", body)))
    if result['decision'] == 'ASK':
        # Only the MCP bridge can collect a host elicitation response. Returning
        # here does not authorize execution: private gateway authz still requires READY.
        if route == 'mcp' and profile.get('format') == 'product-codex-1':
            return {}
        return reply(event, False, 'WITH_HUMAN_ASK: execution paused; this mode cannot collect a trusted user answer')
    if result["decision"] == "CONFIRM":
        return reply(event, False, 'WITH_HUMAN_LEGACY_CONFIRM_READ_ONLY')
    return reply(event, result["decision"] == "ALLOW", "WITH_HUMAN_" + result["decision"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("host", type=Path)
    p.add_argument("action", choices=("hook", "connect", "history", "approve", "reject"), default="hook", nargs="?")
    p.add_argument("--call")
    args = p.parse_args()
    if args.action == "connect":
        print(json.dumps(send(args.host, "/connect", {})))
        return
    if args.action == "history":
        print(json.dumps(send(args.host, "/history", {}, True, "GET"), ensure_ascii=False, indent=2))
        return
    if args.action in ("approve", "reject"):
        raise SystemExit('LEGACY_CONFIRM_READ_ONLY: answer through the supported agent user form')
    event = "PreToolUse"
    try:
        data = guarded("INPUT_READ", lambda: sys.stdin.buffer.read(131073))
        if len(data) > 131072:
            raise HookFailure("INPUT_READ", "EVENT_LIMIT")
        parsed = guarded("PARSE", lambda: json.loads(data))
        if isinstance(parsed, dict) and parsed.get("hook_event_name") in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
            event = parsed["hook_event_name"]
        value = guarded("PARSE", lambda: event_value(parsed))
        event = value["hook_event_name"]
        connection = os.environ.get("WITH_HUMAN_CONNECTION")
        if not connection:
            raise HookFailure("PARSE", "MISSING_CONNECTION")
        result = guarded("INTERNAL", lambda: handle(args.host, value, connection))
    except Exception as error:
        # Never print raw inputs, exception text, credentials or tool result bytes.
        failure = error if isinstance(error, HookFailure) else HookFailure("INTERNAL", "ADAPTER_UNAVAILABLE")
        print(json.dumps({"component": "with_human_hook", "stage": failure.stage, "code": failure.code}), file=sys.stderr)
        result = reply(event, False, "WITH_HUMAN_" + failure.stage + ":" + failure.code)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
