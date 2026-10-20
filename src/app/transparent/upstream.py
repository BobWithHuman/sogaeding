"""Small enrolled file MCP upstream, not an arbitrary command executor.

Private mTLS transport + signed per-body forwarding ticket. Reservations prevent
automatic duplicate attempts, but a file write and the SQLite record are NOT atomic.
"""
import base64
import hashlib
import hmac
import os
import sqlite3
import ssl
import stat
import time
from pathlib import Path, PurePosixPath

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.common import mask, strict_json
from app.storage.auth_audit import AuthAudit
from app.transparent.file_errors import missing_read_result
from app.transparent.tool_schema import FILE_TOOLS


def open_file(root, name, write=False):
    p = PurePosixPath(name)
    if not isinstance(name, str) or not name or "\\" in name or p.is_absolute() or any(
        x in ("", ".", "..") or x.startswith(".") or x in ("artifacts", "references") for x in name.split("/")
    ) or ":" in name or name.casefold() in ("agents.md", "harness/build_tasks.json") or name.casefold().startswith("docs/plans/"):
        raise ValueError("PATH_SCOPE")
    lowered = name.casefold()
    devices = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)), *("lpt" + str(i) for i in range(1, 10))}
    if any(part.rstrip(". ") != part or part.split(".")[0] in devices for part in lowered.split("/")):
        raise ValueError("SPECIAL_PATH_UNSUPPORTED")
    if lowered.startswith(("docs/handoffs/", "src/app/", "agentgateway/", "tools/hookgw", "scripts/hookgw", "tools/mvp_", "scripts/mvp_", "compose.mvp-demo")) or lowered in ("compose.hookgw.yaml", "compose.hookgw.offline.yaml"):
        raise ValueError("TRUSTED_PRODUCT_OR_EVIDENCE")
    # Resolve each component relative to an already open directory, refusing symlinks.
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in p.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        flags = os.O_WRONLY | os.O_CREAT if write else os.O_RDONLY
        fd = os.open(p.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(fd)
            raise ValueError("REGULAR_UNLINKED_FILE_REQUIRED")
        if write:
            os.ftruncate(fd, 0)
        return fd
    finally:
        os.close(directory)


def create_app(root, ledger, forward_key):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.auth_audit = AuthAudit(str(ledger) + ".auth")
    with sqlite3.connect(ledger) as db:
        db.execute("CREATE TABLE IF NOT EXISTS attempts(call TEXT PRIMARY KEY, hash TEXT, state TEXT, at REAL)")

    @app.post("/mcp")
    async def mcp(request: Request):
        auth_pending = False
        try:
            raw = bytearray()
            async for part in request.stream():
                raw.extend(part)
                if len(raw) > 65536:
                    raise ValueError("BODY_LIMIT")
            value = strict_json(bytes(raw))
            method, rid = value.get("method"), value.get("id")
            if method == "notifications/initialized":
                return Response(status_code=202)
            if method == "initialize":
                result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "with-human-enrolled-files", "version": "0.1.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": FILE_TOOLS}
            elif method == "tools/call":
                auth_pending = True
                proof, sig = request.headers.get("x-with-human-forward", "").rsplit(".", 1)
                expected = hmac.new(forward_key.encode(), proof.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig, expected):
                    raise ValueError("FORWARD_AUTH")
                claim = strict_json(base64.urlsafe_b64decode(proof))
                if claim["expires"] < time.time() or claim["hash"] != hashlib.sha256(raw).hexdigest():
                    raise ValueError("FORWARD_BINDING")
                auth_pending = False
                params = value["params"]
                tool, args = params["name"], params["arguments"]
                required = {"path", "content"} if tool == "write_file" else {"path"}
                if tool not in ("read_file", "write_file") or set(args) != required or not isinstance(args["path"], str):
                    raise ValueError("INVALID_TOOL")
                if tool == "write_file" and (not isinstance(args["content"], str) or len(args["content"].encode()) > 16384):
                    raise ValueError("CONTENT_LIMIT")
                # Validate/open only AFTER durable reservation. A crash leaves UNKNOWN, no retry.
                with sqlite3.connect(ledger, timeout=3) as db:
                    db.execute("INSERT INTO attempts VALUES(?,?,?,?)", (claim["call"], claim["hash"], "UNKNOWN", time.time()))
                try:
                    fd = open_file(root, args["path"], tool == "write_file")
                except FileNotFoundError:
                    if tool != "read_file":
                        raise
                    # The authenticated read reached its known open failure.
                    # Persist before reporting; a ledger failure remains UNKNOWN.
                    with sqlite3.connect(ledger) as db:
                        db.execute("UPDATE attempts SET state='OBSERVED_ERROR' WHERE call=?", (claim["call"],))
                    return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": missing_read_result()})
                with os.fdopen(fd, "w" if tool == "write_file" else "r", encoding="utf-8") as stream:
                    if tool == "write_file":
                        stream.write(args["content"])
                        stream.flush()
                        os.fsync(stream.fileno())
                        text = "File write observed."
                    else:
                        text = stream.read(8193)
                        if len(text) > 8192:
                            # Do not silently present truncated evidence as complete.
                            raise ValueError("SOURCE_LIMIT")
                        if mask(text) != text:
                            raise ValueError("SENSITIVE_SOURCE")
                with sqlite3.connect(ledger) as db:
                    db.execute("UPDATE attempts SET state='OBSERVED' WHERE call=?", (claim["call"],))
                result = {"content": [{"type": "text", "text": text}], "isError": False}
            else:
                raise ValueError("UNSUPPORTED_RPC")
            return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception:
            if auth_pending:
                try:
                    app.state.auth_audit.record("SERVICE", 403)
                except Exception:
                    return JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": "UPSTREAM_REJECTED_OR_UNKNOWN"}}, status_code=403)

    return app


if __name__ == "__main__":
    runtime = Path(os.environ.get("HOOKGW_RUNTIME", "/runtime"))
    app = create_app("/files", "/data/attempts.sqlite3", (runtime / "forward.key").read_text().strip())
    uvicorn.run(app, host="0.0.0.0", port=8060, ssl_certfile=str(runtime / "upstream.pem"), ssl_keyfile=str(runtime / "upstream.key"),
                ssl_ca_certs=str(runtime / "ca.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED,
                access_log=False, proxy_headers=False, log_level="critical")
