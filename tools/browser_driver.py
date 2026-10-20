"""Private REPLAY/test driver. Request over stdin; never argv/log credentials."""
import asyncio
import json
import sqlite3
import sys
import time

import httpx
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.common import SafeError, secret_file, tls_context


async def request(path, value=None, role="human"):
    token = secret_file("human.token" if role == "human" else "service.token")
    internal = path.startswith("/internal/")
    async with httpx.AsyncClient(verify=tls_context(client=internal), trust_env=False, timeout=3) as client:
        url = ("https://control:8443" if internal else "https://control:8010") + path
        headers = {"Authorization": "Bearer " + token}
        response = await (client.get(url, headers=headers) if value is None else client.post(url, json=value, headers=headers))
        return {"status": response.status_code, "data": response.json()}


async def main(value):
    command = value["command"]
    if command == "tool":
        async with httpx2.AsyncClient(verify=tls_context(), trust_env=False, timeout=4,
                headers={"Authorization": "Bearer " + value["agent_token"]}) as http:
            async with Client(streamable_http_client("https://gateway:8011/mcp", http_client=http)) as client:
                result = await client.call_tool(value["tool"], value["args"])
                return {"is_error": result.is_error, "data": result.structured_content}
    sid = value.get("session_id")
    if command == "state":
        timeline = await request(f"/v1/sessions/{sid}/timeline")
        with sqlite3.connect("/effects-data/effects.sqlite3") as db:
            invocations = db.execute("SELECT count(*) FROM invocations WHERE session_id=?", (sid,)).fetchone()[0]
            comments = db.execute("SELECT count(*) FROM comments WHERE session_id=?", (sid,)).fetchone()[0]
        return {"timeline": timeline, "executor_invocations": invocations, "actual_effects": comments}
    if command == "close":
        return await request(f"/v1/sessions/{sid}/close", {})
    if command in ("expire_approval", "expire_session", "expire_retention"):
        with sqlite3.connect("/control-data/control.sqlite3") as db:
            if command == "expire_approval":
                db.execute("UPDATE approvals SET expires_at=? WHERE id=?", (time.time() - 1, value["approval_id"]))
            elif command == "expire_session":
                db.execute("UPDATE sessions SET expires_at=? WHERE id=?", (time.time() - 1, sid))
            else:
                db.execute("UPDATE session_retention SET created_at=? WHERE session_id=?", (time.time() - 86401, sid))
        return {"fixture": command, "applied": True}
    if command == "audit_fault":
        with sqlite3.connect("/control-data/control.sqlite3") as db:
            if value["enabled"]:
                db.execute("CREATE TRIGGER browser_fault BEFORE INSERT ON calls BEGIN SELECT RAISE(ABORT,'private-error-canary DEMO_SECRET_DO_NOT_SEND'); END")
            else:
                db.execute("DROP TRIGGER IF EXISTS browser_fault")
        return {"fixture": "audit_fault", "applied": True}
    if command == "fail_session_create":
        with sqlite3.connect("/control-data/control.sqlite3") as db:
            if value["enabled"]:
                db.execute("CREATE TRIGGER browser_create_fault BEFORE INSERT ON sessions BEGIN SELECT RAISE(ABORT,'private-error-canary DEMO_SECRET_DO_NOT_SEND'); END")
            else:
                db.execute("DROP TRIGGER IF EXISTS browser_create_fault")
        return {"fixture": "fail_session_create", "applied": True}
    if command == "health":
        return await request("/healthz")
    raise SafeError("INVALID_ARGUMENTS")


if __name__ == "__main__":
    try:
        incoming = json.loads(sys.stdin.read())
        print(json.dumps(asyncio.run(main(incoming)), ensure_ascii=False))
    except BaseException:
        # Peer exceptions can include input/headers. Never emit raw stack/messages.
        print(json.dumps({"driver_error": "SAFE_DRIVER_FAILURE"}))
        sys.exit(1)
