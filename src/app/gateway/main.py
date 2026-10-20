"""MCP SDK 2.3.0 bearer authentication; no public execution endpoint."""
import asyncio
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime

import anyio
import uvicorn
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from pydantic import AnyHttpUrl

from app.common import (
    AUDIENCE,
    RUNTIME,
    SPEC,
    TOOLS,
    SafeError,
    canonical,
    digest,
    mask,
    masked_tree,
    uid,
    validate_tool,
)
from app.control.main import RequestGuard
from app.executor.demo import DemoExecutor
from app.gateway.client import ControlClient
from app.pdp.semantic import material
from app.storage.retention import SWEEP_INTERVAL

control = ControlClient()


class SessionVerifier:
    async def verify_token(self, token):
        try:
            auth = await control.post("/internal/auth/resolve", {"agent_token": token}, "AuthContext")
            return AccessToken(token=token, client_id=auth["session_id"], subject=auth["owner_id"],
                               scopes=auth["scopes"], resource=auth["audience"],
                               expires_at=int(datetime.fromisoformat(auth["expires_at"]).timestamp()))
        except SafeError:
            return None


class StrictServer(MCPServer):
    async def call_tool(self, name, arguments, context=None):
        try:
            validate_tool(name, arguments)
        except SafeError as exc:
            return CallToolResult(content=[TextContent(type="text", text=exc.code)], is_error=True)
        return await super().call_tool(name, arguments, context)

    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            tool.input_schema = TOOLS["$defs"][tool.name]
        return tools

    def _tool_input_schema(self, name):
        return TOOLS["$defs"].get(name)


server = StrictServer("with-human", token_verifier=SessionVerifier(),
                   auth=AuthSettings(issuer_url=AnyHttpUrl("https://127.0.0.1:8000"),
                                     resource_server_url=AnyHttpUrl(AUDIENCE),
                                     required_scopes=["tools:invoke"], validate_token_resource=True),
                   log_level="CRITICAL")


async def invoke(tool, args):
    reply, reserved, receipt = None, None, None
    try:
        validate_tool(tool, args)
        token = get_access_token()
        if token is None:
            raise SafeError("AUTH_REQUIRED", 401)
        # A second resolve closes the window between handshake and tool dispatch.
        auth = await control.post("/internal/auth/resolve", {"agent_token": token.token}, "AuthContext")
        if auth["session_id"] != token.client_id:
            raise SafeError("AUTH_REQUIRED", 403)
        args = dict(args)
        resume = args.pop("resume_call_id", None)
        value = {"session_id": auth["session_id"], "client_request_id": uid(),
                 "tool_name": tool, "backend_id": "demo.v1", "args": args}
        if resume:
            value["resume_call_id"] = resume
        reply = await control.post("/internal/checks", value, "CheckReply")
        result = {"version": SPEC, "call_id": reply["call_id"], "decision": reply["decision"],
                  "execution_state": reply["execution_state"], "reason_codes": reply["reason_codes"],
                  "source_ids": reply["source_ids"], "approval_id": reply.get("approval_id"), "result": None}
        result.update({key:reply[key] for key in ('analysis_id','decision_stage','evidence_snapshot_sha256','evidence_refs')})
        if reply["decision"] == "DENY" or (reply["decision"] == "CONFIRM" and
                reply.get("approval_status") not in ("APPROVED", "CONSUMED")):
            return CallToolResult(content=[TextContent(type="text", text=canonical(result))],
                                  structured_content=result, is_error=True)
        reserved = await control.post(f"/internal/calls/{reply['call_id']}/reserve",
            {"tool_name": tool, "backend_id": "demo.v1", "args": args}, "ReservationReply")
        if not reserved["execute"]:
            result["execution_state"] = "SUCCEEDED"
            result["result"] = {"receipt": reserved["receipt"]}
            return CallToolResult(content=[TextContent(type="text", text=canonical(result))],
                                  structured_content=result)
        if datetime.fromisoformat(reserved["start_before"]).timestamp() <= time.time():
            raise SafeError("EXECUTION_OUTCOME_UNKNOWN")
        executor = DemoExecutor(os.getenv("EFFECTS_DB_PATH", "/data/effects.sqlite3"))
        raw, receipt = await asyncio.wait_for(asyncio.to_thread(executor.execute,
            reply["call_id"], auth["session_id"], tool, args), timeout=2)
        safe = masked_tree(raw)
        if tool != "post_issue_comment":
            snapshot = canonical(raw) if isinstance(raw, dict) else raw
            analysis = material(raw['title']+'\n'+raw['body'] if isinstance(raw,dict) else raw)
            source = await control.post("/internal/sources", {
                "call_id": reply["call_id"], "kind": "EXTERNAL" if tool == "get_issue" else "WORKSPACE_DATA",
                "origin_ref": f"demo:{args.get('issue_id', args.get('file_id'))}",
                "content_sha256": digest(snapshot), "masked_excerpt": mask(snapshot)[:512],
                "match_values": [mask(raw["title"])[:128]] if isinstance(raw, dict) else [], **analysis}, "SourceView")
            result["source_ids"] = [*reply["source_ids"], source["source_id"]][:16]
        await control.post(f"/internal/calls/{reply['call_id']}/report", {
            "reservation_id": reserved["reservation_id"], "state": "SUCCEEDED", "receipt": receipt}, "ExecutionView")
        result["execution_state"] = "SUCCEEDED"
        result["result"] = {"data": safe, "receipt": receipt}
        return CallToolResult(content=[TextContent(type="text", text=canonical(result))], structured_content=result)
    except asyncio.CancelledError:
        # to_thread may finish a write after its waiter is cancelled. Never run
        # it again; record uncertainty while the reservation/budget stays spent.
        if reserved and reserved["execute"]:
            try:
                with anyio.move_on_after(1.5, shield=True):
                    await control.post(f"/internal/calls/{reply['call_id']}/report", {
                        "reservation_id": reserved["reservation_id"], "state": "UNKNOWN",
                        "error_code": "EXECUTION_OUTCOME_UNKNOWN"}, "ExecutionView")
            except SafeError:
                pass  # Startup/daemon sweep is the durable fallback.
        raise
    except (SafeError, sqlite3.Error, OSError, KeyError, ValueError, asyncio.TimeoutError):
        import sys
        exc = sys.exception()
        code = exc.code if isinstance(exc, SafeError) else "EXECUTION_OUTCOME_UNKNOWN"
        state = reply["execution_state"] if reply else "NOT_STARTED"
        if reserved and reserved["execute"]:
            state = "UNKNOWN"
            try:
                await control.post(f"/internal/calls/{reply['call_id']}/report", {
                    "reservation_id": reserved["reservation_id"], "state": "UNKNOWN",
                    "error_code": "EXECUTION_OUTCOME_UNKNOWN"}, "ExecutionView")
            except SafeError:
                pass  # Control's stale-reservation sweep preserves UNKNOWN; budget stays consumed.
        value = {"version": SPEC, "call_id": reply["call_id"] if reply else uid(),
                 "decision": reply["decision"] if reply else "DENY",
                 "execution_state": state, "reason_codes": [code],
                 "source_ids": reply["source_ids"] if reply else [],
                 "approval_id": reply.get("approval_id") if reply else None, "result": None}
        value.update({key:reply[key] if reply else (None if key!='decision_stage' and key!='evidence_refs' else
                     ('POLICY' if key=='decision_stage' else []))
                     for key in ('analysis_id','decision_stage','evidence_snapshot_sha256','evidence_refs')})
        return CallToolResult(content=[TextContent(type="text", text=canonical(value))],
                              structured_content=value, is_error=True)


@server.tool(structured_output=False)
async def get_issue(issue_id: int) -> CallToolResult:
    return await invoke("get_issue", {"issue_id": issue_id})


@server.tool(structured_output=False)
async def read_workspace_file(file_id: str) -> CallToolResult:
    return await invoke("read_workspace_file", {"file_id": file_id})


@server.tool(structured_output=False)
async def post_issue_comment(issue_id: int, body: str, resume_call_id: str | None = None) -> CallToolResult:
    args = {"issue_id": issue_id, "body": body}
    if resume_call_id is not None:
        args["resume_call_id"] = resume_call_id
    return await invoke("post_issue_comment", args)


app = server.streamable_http_app(stateless_http=True, json_response=True,
                                max_request_body_size=32768,
                                transport_security=TransportSecuritySettings(
                                    enable_dns_rebinding_protection=True,
                                    allowed_hosts=["127.0.0.1:*", "localhost:*", "gateway:*"],
                                    allowed_origins=["https://127.0.0.1:*", "https://localhost:*"]))
app.add_middleware(RequestGuard, cancel_tools=True)

sdk_lifespan = app.router.lifespan_context


@asynccontextmanager
async def maintenance(app):
    executor = DemoExecutor(os.getenv("EFFECTS_DB_PATH", "/data/effects.sqlite3"))
    executor.sweep()
    async def sweep_effects():
        while True:
            await asyncio.sleep(SWEEP_INTERVAL)
            try:
                await asyncio.to_thread(executor.sweep)
            except sqlite3.Error:
                pass  # Receipt access still checks its deadline; next sweep retries.
    task = asyncio.create_task(sweep_effects())
    try:
        async with sdk_lifespan(app):
            yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app.router.lifespan_context = maintenance


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GATEWAY_PORT", "8001")),
                ssl_certfile=str(RUNTIME / "gateway.pem"), ssl_keyfile=str(RUNTIME / "gateway.key"),
                proxy_headers=False, access_log=False, log_level="critical")
