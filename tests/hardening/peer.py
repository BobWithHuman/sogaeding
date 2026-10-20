"""Test-only authenticated TLS fault peer forwarding to the real PDP.

Selected via a private /tmp file, never exposed by the product or public API.
"""
import asyncio
import json
import os
import ssl
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.common import RUNTIME, tls_context

app = FastAPI()
mode_path = Path(os.environ["FAULT_MODE_PATH"])


@app.post("/{path:path}")
async def peer(path: str, request: Request):
    body = await request.body()
    mode = json.loads(mode_path.read_text())
    matches = path == mode.get("path") or (mode.get("path") == "reports" and path.startswith("internal/calls/") and path.endswith("/report"))
    if matches and mode.get("only_success_report"):
        matches = json.loads(body).get("state") == "SUCCEEDED"
    if matches:
        action = mode.get("action")
        if action == "timeout":
            await asyncio.sleep(26 if path=='internal/checks' else 2)
            return JSONResponse({"code": "private-error-canary"}, status_code=503)
        if action == "json":
            return Response("private-error-canary: not json", media_type="application/json")
        if action == "schema":
            return JSONResponse({"decision": "ALLOW", "private": "private-error-canary"})
        if action == "error":
            return JSONResponse({"code": ["private-error-canary"]}, status_code=500)
        if action == "list-error":
            return JSONResponse(["private-error-canary"], status_code=500)
    async with httpx.AsyncClient(verify=tls_context(client=True), trust_env=False, timeout=2) as client:
        response = await client.post("https://127.0.0.1:8445/" + path, content=body,
                                     headers={"Authorization": request.headers["authorization"],
                                              "Content-Type": "application/json"})
    return Response(response.content, status_code=302 if matches and mode.get("action") == "redirect" else response.status_code,
                    media_type="application/json")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8443, ssl_certfile=str(RUNTIME / "control.pem"),
                ssl_keyfile=str(RUNTIME / "control.key"), ssl_ca_certs=str(RUNTIME / "ca.pem"),
                ssl_cert_reqs=ssl.CERT_REQUIRED, access_log=False, log_level="critical",
                timeout_graceful_shutdown=2)
