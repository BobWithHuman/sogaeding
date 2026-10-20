"""Control API with strict contracts and role/port separation."""
import asyncio
import hmac
import os
import sqlite3
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.common import API, SafeError, secret_file, strict_json, validate
from app.pdp.judge import OpenAIJudge
from app.storage.auth_audit import AuthAudit
from app.storage.repository import Repository
from app.storage.retention import SWEEP_INTERVAL


@asynccontextmanager
async def lifespan(app):
    app.state.repository = Repository(os.getenv("CONTROL_DB_PATH", "/data/control.sqlite3"))
    app.state.judge = OpenAIJudge()
    app.state.repository.sweep()
    async def sweeper():
        while True:
            await asyncio.sleep(SWEEP_INTERVAL)
            try:
                app.state.repository.sweep()
            except sqlite3.Error:
                # Reservations stay consumed; a subsequent request still cannot re-execute.
                pass
    task = asyncio.create_task(sweeper())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.openapi = lambda: API


class RequestGuard:
    """Bounded body/depth, duplicate keys/headers, no cross-origin credentials."""
    def __init__(self, app, control=False, cancel_tools=False):
        self.app, self.control, self.cancel_tools = app, control, cancel_tools
        self.attempts = deque(maxlen=128)
        self.failures = deque(maxlen=60)
        base = os.getenv('CONTROL_DB_PATH' if control else 'EFFECTS_DB_PATH','/data/control.sqlite3' if control else '/data/effects.sqlite3')
        self.audit = AuthAudit(os.getenv('AUTH_AUDIT_DB_PATH',base+'.auth'))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        try:
            internal_surface = scope.get('server',(None,None))[1] == int(os.getenv('INTERNAL_PORT','8443'))
            surface = ('SERVICE' if internal_surface else 'HUMAN') if self.control else 'AGENT'
            headers = scope["headers"]
            for key in (b"authorization", b"host", b"content-length"):
                if sum(k == key for k, _ in headers) > 1:
                    raise SafeError("INVALID_ARGUMENTS", 422)
            if scope.get("query_string"):
                raise SafeError("INVALID_ARGUMENTS", 422)
            if scope.get("scheme") != "https":
                raise SafeError("AUTH_REQUIRED", 403)
            now = time.monotonic()
            if len([t for t in self.failures if now - t < 10]) >= 60:
                raise SafeError("AUTH_REQUIRED", 429)
            async def limited_send(message):
                if message["type"] == "http.response.start":
                    if message["status"] in (401, 403):
                        self.failures.append(time.monotonic())
                    if message['status'] in (401,403,429):
                        self.audit.record(surface,message['status'])
                    message["headers"] = [*message.get("headers", []), (b"cache-control", b"no-store")]
                await send(message)
            origin = dict(headers).get(b"origin")
            public_port = int(os.getenv("CONTROL_PORT", "8000"))
            allowed_origins = {f"https://{host}:{public_port}".encode() for host in ("127.0.0.1", "localhost")}
            if origin and origin not in allowed_origins:
                raise SafeError("AUTH_REQUIRED", 403)
            if self.control:
                internal = scope.get("server", (None, None))[1] == int(os.getenv("INTERNAL_PORT", "8443"))
                port = scope.get("server", (None, None))[1]
                allowed = {f"{host}:{port}".encode() for host in ("127.0.0.1", "localhost", "control")}
                if dict(headers).get(b"host") not in allowed:
                    raise SafeError("INVALID_ARGUMENTS", 422)
                if scope["path"].startswith("/internal/") != internal and scope["path"] != "/healthz":
                    raise SafeError("AUTH_REQUIRED", 403)
                if scope["path"] not in ("/healthz", "/", "/ui.js"):
                    expected = secret_file("service.token" if internal else "human.token")
                    auth = dict(headers).get(b"authorization", b"").decode("ascii", errors="ignore")
                    if not hmac.compare_digest(auth, "Bearer " + expected):
                        now = time.monotonic()
                        self.attempts.append(now)
                        if len([t for t in self.attempts if now - t < 10]) >= 20:
                            raise SafeError("AUTH_REQUIRED", 429)
                        raise SafeError("AUTH_REQUIRED", 401)
            chunks = bytearray()
            while True:
                message = await asyncio.wait_for(receive(), timeout=2)
                if message["type"] == "http.disconnect":
                    return
                chunks.extend(message.get("body", b""))
                if len(chunks) > 32768:
                    raise SafeError("INVALID_ARGUMENTS", 413)
                if not message.get("more_body", False):
                    break
            parsed = strict_json(chunks) if chunks else None
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(chunks), "more_body": False}
                return await receive()
            # SDK 2.3.0's modern JSON-response path does not monitor disconnect.
            # For 2026 HTTP tools/call, closing its response stream is the MCP
            # cancellation signal. Do not apply this to older protocol eras.
            if (self.cancel_tools and isinstance(parsed, dict) and parsed.get("method") == "tools/call"
                    and dict(headers).get(b"mcp-protocol-version") == b"2026-07-28"):
                running = asyncio.create_task(self.app(scope, replay, limited_send))
                async def disconnect():
                    while (await receive())["type"] != "http.disconnect":
                        pass
                    running.cancel()
                watcher = asyncio.create_task(disconnect())
                try:
                    await running
                finally:
                    watcher.cancel()
                    try:
                        await watcher
                    except asyncio.CancelledError:
                        pass
            else:
                await self.app(scope, replay, limited_send)
        except SafeError as exc:
            if exc.status in (401, 403):
                self.failures.append(time.monotonic())
            if exc.status in (401,403,429):
                try:
                    self.audit.record(surface,exc.status)
                except (sqlite3.Error,OSError):
                    exc=SafeError('AUDIT_UNAVAILABLE',503)
            await JSONResponse({"code": exc.code, "message": exc.code}, exc.status,
                               headers={"Cache-Control": "no-store"})(scope, receive, send)
        except asyncio.TimeoutError:
            await JSONResponse({"code": "INVALID_ARGUMENTS", "message": "INVALID_ARGUMENTS"}, 408)(scope, receive, send)
        except (sqlite3.Error,OSError):
            await JSONResponse({'code':'AUDIT_UNAVAILABLE','message':'AUDIT_UNAVAILABLE'},503)(scope,receive,send)


app.add_middleware(RequestGuard, control=True)


@app.exception_handler(SafeError)
async def safe_error(request, exc):
    return JSONResponse({"code": exc.code, "message": exc.code}, exc.status)


@app.exception_handler(sqlite3.Error)
async def storage_error(request, exc):
    return JSONResponse({"code": "AUDIT_UNAVAILABLE", "message": "AUDIT_UNAVAILABLE"}, 503)


@app.exception_handler(Exception)
async def unknown_error(request, exc):
    return JSONResponse({"code": "AUDIT_UNAVAILABLE", "message": "AUDIT_UNAVAILABLE"}, 503)


async def body(request, schema):
    value = strict_json(await request.body())
    validate(schema, value)
    return value


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.get("/")
async def shell():
    return HTMLResponse((Path(__file__).parents[1] / "web/index.html").read_text(encoding="utf-8"),
        headers={"Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/ui.js")
async def ui_script():
    return Response((Path(__file__).parents[1] / "web/ui.js").read_text(encoding="utf-8"),
                    media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.post("/v1/sessions", status_code=201)
async def create_session(request: Request):
    value = await body(request, "SessionCreate")
    if value["issue_id"] not in (42, 43):
        raise SafeError("RESOURCE_OUT_OF_SCOPE", 422)
    return request.app.state.repository.create_session(value)


@app.post("/v1/sessions/{session_id}/close")
async def close_session(session_id: str, request: Request):
    await body(request, "Empty")
    return request.app.state.repository.close(session_id)


@app.post("/internal/auth/resolve")
async def resolve(request: Request):
    value = await body(request, "AuthResolve")
    return request.app.state.repository.resolve(value["agent_token"])


@app.post("/internal/checks")
async def check(request: Request):
    value = await body(request, "CheckRequest")
    return await request.app.state.repository.check_async(value,request.app.state.judge)


@app.post("/internal/calls/{call_id}/reserve")
async def reserve(call_id: str, request: Request):
    return request.app.state.repository.reserve(call_id, await body(request, "ReserveRequest"))


@app.post("/internal/calls/{call_id}/report")
async def report(call_id: str, request: Request):
    return request.app.state.repository.report(call_id, await body(request, "ReportRequest"))


@app.post("/internal/sources")
async def source(request: Request):
    return request.app.state.repository.source(await body(request, "SourceIngest"))


@app.get("/v1/sessions/{session_id}/timeline")
async def timeline(session_id: str, request: Request):
    return request.app.state.repository.timeline(session_id)


@app.get("/v1/sessions/{session_id}/diagnostics")
async def diagnostics(session_id: str, request: Request):
    return request.app.state.repository.analysis_diagnostics(session_id)


@app.get("/v1/judge-usage")
async def judge_usage(request: Request):
    return request.app.state.judge.budget_summary()


@app.post("/v1/sessions/{session_id}/cli-binding")
async def cli_binding(session_id: str, request: Request):
    value = await body(request, "CliBindingRequest")
    return request.app.state.repository.cli_binding(session_id, value["agent_session_token"])


@app.post("/v1/approvals/{approval_id}/approve")
async def approve(approval_id: str, request: Request):
    value = await body(request, "ApprovalRequest")
    return request.app.state.repository.approve(approval_id, value["expected_args_sha256"])


@app.post("/v1/approvals/{approval_id}/reject")
async def reject(approval_id: str, request: Request):
    await body(request, "Empty")
    return request.app.state.repository.approve(approval_id, reject=True)
