"""Loopback MCP endpoint for one Claude Code actor; the driver owns every dispatch.

Stateless Streamable HTTP with JSON responses only. The actor sees the exact
collected catalog; tools/call goes to one trusted driver callback, serialized,
and nothing is dispatched after the driver stops the task.
"""

import asyncio
import copy
import hmac
import socket
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.common import SafeError, strict_json

MAX_BODY_BYTES = 1048576
# Newest first. An unknown requested version receives the newest supported one.
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
STOPPED = {
    "isError": True,
    "content": [{"type": "text", "text": "The evaluation harness stopped this task."}],
}


class BridgeStopped(RuntimeError):
    pass


def bridge_app(catalogs, token, dispatch, *, ready_seconds=30):
    """catalogs: {server: [MCP tool]}; dispatch: async (server, tool, args) -> MCP result.

    app.state.ready is set by the driver only after the actor's own startup
    report was verified; no call is dispatched before that or after stopped.
    """
    if not token or len(token) < 32:
        raise ValueError("BRIDGE_TOKEN_REQUIRED")
    names = {server: {t["name"] for t in tools} for server, tools in catalogs.items()}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ready = asyncio.Event()
    app.state.stopped = asyncio.Event()
    app.state.stop_code = None
    app.state.calls = 0
    # Held for each whole dispatch; the driver acquires it to wait out an in-flight call.
    app.state.lock = lock = asyncio.Lock()

    async def gate():
        waits = [asyncio.create_task(e.wait()) for e in (app.state.ready, app.state.stopped)]
        try:
            await asyncio.wait(waits, timeout=ready_seconds, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in waits:
                task.cancel()
        if not app.state.ready.is_set() and not app.state.stopped.is_set():
            app.state.stop_code = "BRIDGE_ACTOR_NOT_READY"
            app.state.stopped.set()
        return not app.state.stopped.is_set()

    def error(rid, code, message):
        return JSONResponse(
            {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}
        )

    @app.api_route("/{server}/mcp", methods=["GET", "DELETE"])
    async def no_stream(server: str):
        return Response(status_code=405, headers={"Allow": "POST"})

    @app.post("/{server}/mcp")
    async def rpc(server: str, request: Request):
        if not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
            return Response(status_code=401)
        origin = request.headers.get("origin")
        if origin not in (None, "null") and urlsplit(origin).hostname not in (
            "127.0.0.1",
            "localhost",
        ):
            return Response(status_code=403)
        if server not in catalogs:
            return Response(status_code=404)
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            return Response(status_code=413)
        try:
            value = strict_json(raw)
        except (ValueError, SafeError):
            return error(None, -32700, "Parse error")
        if (
            not isinstance(value, dict)
            or value.get("jsonrpc") != "2.0"
            or not isinstance(value.get("method"), str)
        ):
            return error(None, -32600, "Invalid Request")
        if "id" not in value:
            return Response(status_code=202)
        method, rid = value["method"], value["id"]
        params = value.get("params") or {}
        if not isinstance(params, dict):
            return error(rid, -32602, "Invalid params")
        if method == "initialize":
            requested = params.get("protocolVersion")
            result = {
                "protocolVersion": requested if requested in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "with-human-" + server, "version": "1"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": copy.deepcopy(catalogs[server])}
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments", {})
            if name not in names[server] or not isinstance(args, dict):
                return error(rid, -32602, "Invalid params")
            async with lock:
                if not await gate():
                    result = copy.deepcopy(STOPPED)
                else:
                    app.state.calls += 1
                    try:
                        result = await dispatch(server, name, copy.deepcopy(args))
                    except Exception as stop:
                        # Fail closed: never retry; the driver terminates the actor.
                        app.state.stop_code = (
                            str(stop)
                            if isinstance(stop, BridgeStopped)
                            else "BRIDGE_DISPATCH_" + type(stop).__name__
                        )
                        app.state.stopped.set()
                        result = copy.deepcopy(STOPPED)
        else:
            return error(rid, -32601, "Method not found")
        return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": result})

    return app


class LoopbackServer:
    """uvicorn on an already bound 127.0.0.1 ephemeral socket in the current loop."""

    def __init__(self, app):
        self.app = app
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        self.server = uvicorn.Server(
            uvicorn.Config(
                app, access_log=False, proxy_headers=False, log_level="critical", lifespan="off"
            )
        )
        self.task = None

    def url(self, server):
        return "http://127.0.0.1:%d/%s/mcp" % (self.port, server)

    async def __aenter__(self):
        self.task = asyncio.create_task(self.server.serve(sockets=[self.socket]))
        for _ in range(100):
            if self.server.started:
                return self
            if self.task.done():
                break
            await asyncio.sleep(0.02)
        raise RuntimeError("BRIDGE_START_FAILED")

    async def __aexit__(self, *exc):
        self.server.should_exit = True
        if self.task:
            done, _ = await asyncio.wait({self.task}, timeout=10)
            if not done:
                self.task.cancel()
        self.socket.close()
