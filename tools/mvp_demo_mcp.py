"""Same MCP RPC waits for separate human approval and resumes once, never Jev retry."""
import argparse
import importlib.util
import json
import math
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = helper("mvp_demo_base_mcp", Path(__file__).with_name("hookgw_mcp.py"))
hook = helper("mvp_demo_trusted_channel", Path(__file__).with_name("hookgw_hook.py"))
errors = helper("mvp_demo_file_errors", Path(__file__).resolve().parents[1] / "src/app/transparent/file_errors.py")
core.STATE_REASONS |= {"DEMO_POLICY_DENIED", "DEMO_CONFIRM_NOT_DISPATCHED", "DEMO_CONFIRM_PENDING", "DEMO_CONFIRM_REJECTED", "DEMO_CONFIRM_EXPIRED"}
WAIT_SECONDS = 600


class Stopped(Exception):
    def __init__(self, code):
        self.code = code


def pending_body(connection, value):
    return {"connection": connection, "tool": value["params"]["name"], "args": value["params"]["arguments"]}


def wait_for_approval(host, connection, value, *, duration=WAIT_SECONDS):
    deadline, reference = time.monotonic() + duration, None
    revision = " -Revision behavior-v5-1" if Path(host).parts[-3:] == ("revisions", "behavior-v5-1", "host") else ""
    sys.stderr.write("WITH_HUMAN_CONFIRM_PENDING: In a separate trusted PowerShell run .\\scripts\\mvp_confirm.ps1" + revision + " and review the exact candidate. This MCP call waits; do not ask the actor to retry.\n")
    sys.stderr.flush()
    while time.monotonic() < deadline:
        row = hook.send(host, "/demo/wait", pending_body(connection, value), timeout=5)
        if not isinstance(row, dict) or set(row) != {"status", "pending_ref", "expires_at", "resume_allowed"}:
            raise Stopped("CONFIRM_STATUS_INVALID")
        ref = row["pending_ref"]
        if not isinstance(ref, str) or not re.fullmatch(r"[a-f0-9]{64}", ref) or reference is not None and ref != reference:
            raise Stopped("CONFIRM_STOPPED_NO_RETRY")
        reference = ref
        if type(row["resume_allowed"]) is not bool:
            raise Stopped("CONFIRM_STATUS_INVALID")
        if row["status"] in {"PENDING", "APPROVED"} and (type(row["expires_at"]) not in (int, float) or not math.isfinite(row["expires_at"]) or row["expires_at"] <= 0):
            raise Stopped("CONFIRM_STATUS_INVALID")
        if row["status"] == "APPROVED" and row["resume_allowed"] is True:
            return
        if row["status"] != "PENDING" or row["resume_allowed"] is not False:
            raise Stopped("CONFIRM_STOPPED_NO_RETRY")
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise Stopped("CONFIRM_WAIT_EXPIRED_NO_RETRY")


def bootstrap(host, connection):
    profile = json.loads((host / "profile.json").read_text(encoding="utf-8-sig"))
    url = profile["gateway_url"]
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path != "/mcp"
            or parsed.query or parsed.fragment or parsed.username or not connection):
        raise ValueError("CONNECTION_UNAVAILABLE")
    context = ssl.create_default_context(cafile=str(host / "ca.pem"))
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args):
            return None
    return url, urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))


def exchange(host, connection, url, opener, value, raw, *, allow_confirmation=True):
    """One request; one exact repeat only after authenticated human approval."""
    resumed = False
    if Path(host).parts[-3:] in (("revisions", "core-auto-v5p1", "host"), ("revisions", "hands-on-1", "host"), ("revisions", "frozen-demo-1", "host")):
        allow_confirmation = False
    while True:
        request_id = uuid4().hex
        request = urllib.request.Request(url, raw, {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-03-26", "Authorization": "Bearer " + connection, "x-with-human-request": request_id})
        try:
            with opener.open(request, timeout=28) as response:
                data = response.read(65537)
                if value.get("id") is None:
                    return None
                if len(data) > 65536:
                    raise Stopped("INVALID_RPC_RESPONSE")
                result = json.loads(data)
                if not isinstance(result, dict) or result.get("jsonrpc") != "2.0" or result.get("id") != value["id"] or "error" in result:
                    raise Stopped("INVALID_RPC_RESPONSE")
                if value.get("method") == "tools/call":
                    output = result.get("result")
                    if not isinstance(output, dict) or output.get("isError") and not errors.valid_read_error(output):
                        raise Stopped("RPC_ERROR")
                    hook.send(host, "/transport-observed", {**pending_body(connection, value), "result": output}, timeout=5)
                return result
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                receipt = core.trusted_rejection(host, connection, request_id, value)
                if receipt.get("reason") == "DEMO_CONFIRM_NOT_DISPATCHED" and not resumed and allow_confirmation:
                    wait_for_approval(host, connection, value)
                    resumed = True
                    continue
                raise Stopped(receipt.get("code", "HTTP_REJECTION_UNCLASSIFIED")) from None
            raise Stopped("HTTP_UNAVAILABLE") from None


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("host", type=Path)
    host = parser.parse_args().host
    try:
        connection = os.environ["WITH_HUMAN_CONNECTION"]
        url, opener = bootstrap(host, connection)
    except Exception:
        core.diagnostic("BOOTSTRAP", "CONNECTION_UNAVAILABLE")
        return 2
    for line in sys.stdin.buffer:
        value, rid, stage = None, None, "INPUT"
        try:
            if len(line) > 65536:
                raise Stopped("INVALID_INPUT")
            value = json.loads(line)
            if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                raise Stopped("INVALID_INPUT")
            rid = value.get("id")
            stage = core.STAGES.get(value.get("method"), "INPUT")
            result = exchange(host, connection, url, opener, value, line.strip())
        except Exception as error:
            code = error.code if isinstance(error, Stopped) else "TRANSPORT_UNAVAILABLE"
            core.diagnostic(stage, "ADAPTER_UNAVAILABLE" if code.startswith("CONFIRM_") else code)
            if isinstance(value, dict) and value.get("method") == "tools/call":
                try:
                    hook.send(host, "/transport-failure", pending_body(connection, value), timeout=5)
                except Exception:
                    sys.stderr.write("WITH_HUMAN_UNKNOWN_OBSERVATION_UNAVAILABLE\n")
            result = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000,
                "message": "WITH_HUMAN_STOPPED: confirmation is no longer pending or execution was rejected/unavailable. Inspect history; no approval is inferred and no actor or model retry is permitted.",
                "data": {"server": "with_human", "stage": stage, "code": code}}}
        if rid is not None and result is not None:
            sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
