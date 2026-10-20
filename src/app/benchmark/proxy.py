"""Private one-shot DTAP upstream behind the unchanged real agentgateway."""

import base64
import hashlib
import hmac
import sqlite3
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.common import strict_json

MAX_MCP_RESPONSE_BYTES = 1048576


async def rpc(client, url, message, headers=None):
    headers = {"Accept": "application/json, text/event-stream", **(headers or {})}
    async with client.stream("POST", url, json=message, headers=headers) as response:
        response.raise_for_status()
        session = response.headers.get("mcp-session-id")
        if response.status_code == 202:
            return {}, session
        raw = bytearray()
        pending = bytearray()
        is_sse = "text/event-stream" in response.headers.get("content-type", "")
        async for block in response.aiter_bytes():
            raw.extend(block)
            if len(raw) > MAX_MCP_RESPONSE_BYTES:
                raise ValueError("MCP_RESPONSE_LIMIT")
            if is_sse:
                pending.extend(block)
                while b"\n" in pending:
                    line, _, remaining = pending.partition(b"\n")
                    pending = bytearray(remaining)
                    if not line.startswith(b"data:"):
                        continue
                    value = strict_json(line[5:].strip())
                    if value.get("id") == message.get("id"):
                        return value, session
        if is_sse:
            raise ValueError("MCP_RESPONSE_MISSING")
        return strict_json(bytes(raw)), session


async def official_call(url, tool, args, registry_entry):
    # Caller supplies only a trusted fixed endpoint, never an argument URL.
    async with httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False) as client:
        _, session = await rpc(
            client,
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "with-human-dtap", "version": "1"},
                },
            },
        )
        headers = {"mcp-session-id": session} if session else {}
        try:
            await rpc(
                client, url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers
            )
            listed, _ = await rpc(
                client, url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers
            )
            current = next(t for t in listed["result"]["tools"] if t["name"] == tool)
            from app.common import canonical, digest

            if digest(canonical(current["inputSchema"])) != registry_entry["schema_sha256"]:
                raise ValueError("ACTUAL_TOOL_SCHEMA_CHANGED")
            result, _ = await rpc(
                client,
                url,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": args},
                },
                headers,
            )
            if "error" in result or not isinstance(result.get("result"), dict):
                raise ValueError("UPSTREAM_RESULT_UNKNOWN")
            return result["result"]
        finally:
            if session:
                await client.delete(url, headers=headers)


def create_proxy(registry, endpoints, ledger, forward_key):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    with sqlite3.connect(ledger) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS attempts(call TEXT PRIMARY KEY,hash TEXT,state TEXT,at REAL)"
        )

    @app.post("/mcp")
    async def dispatch(request: Request):
        try:
            raw = await request.body()
            if len(raw) > 65536:
                raise ValueError("BODY_LIMIT")
            value = strict_json(raw)
            method = value.get("method")
            rid = value.get("id")
            if method == "notifications/initialized":
                return Response(status_code=202)
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "with-human-dtap-gateway", "version": "1"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": registry.name(e["server"], e["name"]),
                            "description": e.get("description", ""),
                            "inputSchema": e["schema"],
                        }
                        for e in registry.entries
                    ]
                }
            elif method == "tools/call":
                proof, sig = request.headers.get("x-with-human-forward", "").split(".", 1)
                if not hmac.compare_digest(
                    sig, hmac.new(forward_key.encode(), proof.encode(), hashlib.sha256).hexdigest()
                ):
                    raise ValueError("FORWARD_AUTH")
                claim = strict_json(base64.urlsafe_b64decode(proof))
                if (
                    claim["expires"] < time.time()
                    or claim["hash"] != hashlib.sha256(raw).hexdigest()
                ):
                    raise ValueError("FORWARD_BINDING")
                params = value["params"]
                server, tool = params["name"].split("::")
                entry = registry.resolve(server, tool, params["arguments"])
                with sqlite3.connect(ledger, timeout=3) as db:
                    db.execute(
                        "INSERT INTO attempts VALUES(?,?,?,?)",
                        (claim["call"], claim["hash"], "UNKNOWN", time.time()),
                    )
                result = await official_call(endpoints[server], tool, params["arguments"], entry)
                if not result.get("isError", False):
                    with sqlite3.connect(ledger) as db:
                        db.execute(
                            "UPDATE attempts SET state=? WHERE call=?", ("OBSERVED", claim["call"])
                        )
            else:
                raise ValueError("UNSUPPORTED_RPC")
            return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception:
            # A persisted UNKNOWN/duplicate is never retried or refunded.
            return JSONResponse({"code": "DTAP_FORWARD_REJECTED_OR_UNKNOWN"}, status_code=403)

    return app
